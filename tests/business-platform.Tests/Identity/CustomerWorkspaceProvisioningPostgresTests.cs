// Implements: architecture/reference/product/wc085-identity-provisioning-data-contract.md CURRENT Sections 1-7
// constitutional_basis: C-005, C-007, C-026, C-059

using System.Reflection;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Npgsql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;
using VerifiedGoogleWorkspaceProof = Waooaw.BusinessPlatform.Services.VerifiedIdentityProof;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class CustomerWorkspaceProvisioningPostgresTests(
    IdentityPostgresServerFixture fixture
) : IClassFixture<IdentityPostgresServerFixture>, IAsyncLifetime
{
    private const string Issuer = "https://synthetic.invalid/realms/customer";
    private const string Provider = "https://synthetic-google.invalid";
    private const string Digest =
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    private const string Hash = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
    private string _ownerConnectionString = string.Empty;

    public async Task InitializeAsync()
    {
        _ownerConnectionString = await fixture.CreateDatabaseAsync("customer_workspace");
        await ExecuteOwnerAsync(
            """
            CREATE SCHEMA business AUTHORIZATION business_app;
            """
        );
        var canonical = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve("infrastructure/postgres/init/03-enums-and-tables.sql")
        );
        foreach (var table in new[] { "organisations", "business_domain_taxonomy" })
        {
            var start = canonical.IndexOf(
                $"CREATE TABLE IF NOT EXISTS business.{table} (",
                StringComparison.Ordinal
            );
            var end = canonical.IndexOf(");", start, StringComparison.Ordinal) + 2;
            await ExecuteOwnerAsync(canonical[start..end]);
        }
        var taxonomyStart = canonical.IndexOf(
            "INSERT INTO business.business_domain_taxonomy",
            StringComparison.Ordinal
        );
        var taxonomyEnd = canonical.IndexOf(';', taxonomyStart) + 1;
        await ExecuteOwnerAsync(canonical[taxonomyStart..taxonomyEnd]);
        await ExecuteOwnerAsync(
            await File.ReadAllTextAsync(
                RepositoryPaths.Resolve("infrastructure/postgres/init/20-identity-boundary.sql")
            )
        );
        await ExecuteOwnerAsync(
            await File.ReadAllTextAsync(
                RepositoryPaths.Resolve(
                    "infrastructure/postgres/init/26-customer-portal-identity.sql"
                )
            )
        );
        await ExecuteOwnerAsync(
            """
            ALTER TABLE identity.customer_portal_preferences
                ADD COLUMN workspace_layout_version integer NOT NULL DEFAULT 0,
                ADD COLUMN navigation_visibility varchar(16) NOT NULL DEFAULT 'VISIBLE',
                ADD COLUMN progress_visibility varchar(16) NOT NULL DEFAULT 'VISIBLE',
                ADD COLUMN conversation_width_percent integer NOT NULL DEFAULT 50,
                ADD COLUMN reduce_motion boolean NOT NULL DEFAULT false;
            ALTER TABLE identity.customer_portal_preferences
                ADD CONSTRAINT ck_customer_portal_workspace_layout CHECK (
                    workspace_layout_version >= 0
                    AND navigation_visibility IN ('VISIBLE', 'COLLAPSED', 'HIDDEN')
                    AND progress_visibility IN ('VISIBLE', 'COLLAPSED', 'HIDDEN')
                    AND conversation_width_percent BETWEEN 35 AND 75
                );
            """
        );
        await ExecuteOwnerAsync(
            """
            GRANT ALL ON ALL TABLES IN SCHEMA business, identity TO business_app;
            GRANT SELECT ON ALL TABLES IN SCHEMA business TO constitutional_app, runtime_app, wbe_app;
            CREATE POLICY tenant_isolation ON business.organisations USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
            INSERT INTO identity.registrations(registration_id, actor_subject, state, authentication_path, account_id)
                VALUES ('00000000-0000-0000-0000-000000000085', 'legacy', 'Completed', 'Google', gen_random_uuid());
            """
        );
        await ExecuteOwnerAsync(
            await File.ReadAllTextAsync(
                RepositoryPaths.Resolve(
                    "infrastructure/postgres/init/29-customer-workspace-provisioning.sql"
                )
            )
        );
        await ExecuteOwnerAsync(
            await File.ReadAllTextAsync(
                RepositoryPaths.Resolve(
                    "infrastructure/postgres/init/56-wc123-current-membership.sql"
                )
            )
        );
        await ExecuteOwnerAsync(
            await File.ReadAllTextAsync(
                RepositoryPaths.Resolve(
                    "infrastructure/postgres/init/57-wc123-identity-lifecycle.sql"
                )
            )
        );
    }

    public async Task DisposeAsync() => await fixture.DropDatabaseAsync(_ownerConnectionString);

    [Fact]
    public async Task Migration_RestrictedBusinessRole_EmptyContextResolvesNothing()
    {
        await using var connection = new NpgsqlConnection(AppConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(
            "SELECT count(*) FROM identity.resolve_customer_membership()",
            connection
        );
        Assert.Equal(0L, await command.ExecuteScalarAsync());
        command.CommandText = "SELECT count(*) FROM identity.registrations";
        Assert.Equal(0L, await command.ExecuteScalarAsync());
    }

    [Fact]
    public async Task Complete_TwoSyntheticIdentities_CreateDistinctAccountsWorkspacesAndOwnerMemberships()
    {
        var first = SyntheticProof("customer-one", "google-one");
        var second = SyntheticProof("customer-two", "google-two");
        var firstRegistration = await SeedAsync(first);
        var secondRegistration = await SeedAsync(second);
        var service = Service();

        var firstResult = await service.CompleteAsync(
            first,
            firstRegistration,
            Guid.NewGuid(),
            Hash
        );
        var secondResult = await service.CompleteAsync(
            second,
            secondRegistration,
            Guid.NewGuid(),
            Hash
        );
        var firstMembership = await service.ResolveAsync(first.Actor);
        var secondMembership = await service.ResolveAsync(second.Actor);

        Assert.Equal(200, firstResult.StatusCode);
        Assert.Equal("ACCOUNT_CREATED", firstResult.Result.Outcome);
        Assert.Equal(firstResult.Result.AccountReference, firstMembership.AccountId);
        Assert.Equal(secondResult.Result.AccountReference, secondMembership.AccountId);
        Assert.NotEqual(firstMembership.AccountId, firstMembership.TenantId);
        Assert.NotEqual(secondMembership.AccountId, secondMembership.TenantId);
        Assert.NotEqual(firstMembership.AccountId, secondMembership.AccountId);
        Assert.NotEqual(firstMembership.TenantId, secondMembership.TenantId);
        Assert.Equal(new[] { "OWNER" }, firstMembership.Roles);
        Assert.Equal(new[] { "OWNER" }, secondMembership.Roles);
    }

    [Fact]
    public async Task CompletedRegistration_FirstPortalReadPersistsTenantIsolatedDefaults()
    {
        var proof = SyntheticProof("portal-layout-owner", "portal-layout-google");
        var registration = await SeedAsync(proof);
        var provisioning = Service();
        await provisioning.CompleteAsync(proof, registration, Guid.NewGuid(), Hash);
        var membership = await provisioning.ResolveAsync(proof.Actor);
        var identity = IdentityTestHelpers.CreateService(
            new WorkspaceDbContextFactory(AppConnectionString())
        );

        var layout = await identity.GetWorkspaceLayoutPreferencesAsync(
            proof.Actor.Issuer,
            proof.Actor.Subject,
            membership,
            CancellationToken.None
        );

        Assert.Equal(0, layout.PreferenceVersion);
        await using (var owner = new WorkspaceDbContextFactory(
            _ownerConnectionString
        ).CreateDbContext())
        {
            var preference = await owner.CustomerPortalPreferences.SingleAsync(value =>
                value.ActorSubject == proof.Actor.Subject
                && value.TenantId == membership.TenantId
            );
            Assert.Equal(0, preference.WorkspaceLayoutVersion);
        }

        var otherProof = SyntheticProof("other-portal-owner", "other-portal-google");
        var otherRegistration = await SeedAsync(otherProof);
        await provisioning.CompleteAsync(
            otherProof,
            otherRegistration,
            Guid.NewGuid(),
            Hash
        );
        var otherMembership = await provisioning.ResolveAsync(otherProof.Actor);

        await Assert.ThrowsAsync<IdentityResourceNotFoundException>(() =>
            identity.GetWorkspaceLayoutPreferencesAsync(
                proof.Actor.Issuer,
                proof.Actor.Subject,
                otherMembership,
                CancellationToken.None
            )
        );
        await using var persisted = new WorkspaceDbContextFactory(
            _ownerConnectionString
        ).CreateDbContext();
        Assert.DoesNotContain(
            await persisted.CustomerPortalPreferences.ToListAsync(),
            value =>
                value.ActorSubject == proof.Actor.Subject
                && value.TenantId == otherMembership.TenantId
        );
    }

    [Fact]
    public async Task CurrentMembership_ManyRequiresExactSelection_AndSuspensionDeniesImmediately()
    {
        var proof = SyntheticProof("multi-membership", "multi-membership-google");
        var registration = await SeedAsync(proof);
        var service = Service();
        var completed = await service.CompleteAsync(proof, registration, Guid.NewGuid(), Hash);
        var initial = await service.ResolveAsync(proof.Actor);
        var secondTenant = Guid.NewGuid();
        var secondMembership = Guid.NewGuid();
        await ExecuteOwnerAsync(
            $"""
            INSERT INTO business.organisations (
                id, tenant_id, name, identity_managed, identity_status
            ) VALUES (
                '{secondTenant:D}', '{secondTenant:D}', 'Second workspace', TRUE, 'ACTIVE'
            );
            INSERT INTO identity.memberships (
                membership_id, account_id, tenant_id, roles, status
            ) VALUES (
                '{secondMembership:D}', '{completed.Result.AccountReference:D}',
                '{secondTenant:D}', ARRAY['VIEWER']::text[], 'ACTIVE'
            );
            """
        );

        var memberships = await service.ListAsync(proof.Actor);
        Assert.Equal(2, memberships.Count);
        Assert.Equal(
            CustomerWorkspaceError.MembershipInactive,
            (
                await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
                    service.ResolveAsync(proof.Actor)
                )
            ).Error
        );
        Assert.Equal(
            initial.MembershipId,
            (await service.ValidateSelectionAsync(proof.Actor, initial.MembershipId)).MembershipId
        );
        Assert.Equal(
            new[] { "VIEWER" },
            (await service.ValidateSelectionAsync(proof.Actor, secondMembership)).Roles
        );
        Assert.Equal(
            CustomerWorkspaceError.MembershipInactive,
            (
                await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
                    service.ValidateSelectionAsync(proof.Actor, Guid.NewGuid())
                )
            ).Error
        );

        await ExecuteOwnerAsync(
            $"UPDATE identity.memberships SET status = 'SUSPENDED' WHERE membership_id = '{secondMembership:D}'"
        );
        Assert.Equal(
            CustomerWorkspaceError.MembershipInactive,
            (
                await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
                    service.ValidateSelectionAsync(proof.Actor, secondMembership)
                )
            ).Error
        );
        Assert.Contains(
            await service.ListAsync(proof.Actor),
            membership =>
                membership.MembershipId == secondMembership && membership.Status == "SUSPENDED"
        );
        await ExecuteOwnerAsync(
            $"UPDATE identity.memberships SET roles = ARRAY['MANAGER']::text[] WHERE membership_id = '{initial.MembershipId:D}'"
        );
        Assert.Equal(
            new[] { "MANAGER" },
            (await service.ValidateSelectionAsync(proof.Actor, initial.MembershipId)).Roles
        );
    }

    [Fact]
    public async Task LifecyclePersistence_ReservesOpaqueKeys_AndIsActorScopedImmutableHistory()
    {
        var proof = SyntheticProof("lifecycle-owner", "lifecycle-owner-google");
        var foreign = SyntheticProof("lifecycle-foreign", "lifecycle-foreign-google");
        await CompleteAsync(proof);
        await CompleteAsync(foreign);
        var operationId = Guid.NewGuid();
        var linkId = Guid.NewGuid();
        var bindingReference = Guid.NewGuid();
        var globalUserId = Guid.NewGuid();
        var correlationId = Guid.NewGuid();

        await ActorExecuteAsync(
            proof.Actor,
            $"""
            INSERT INTO identity.lifecycle_operations (
                operation_id, actor_issuer, actor_subject, command_type,
                provider_class, idempotency_key_version, idempotency_digest, target_link_reference,
                state, correlation_id
            ) VALUES (
                '{operationId:D}', '{proof.Actor.Issuer}', '{proof.Actor.Subject}', 'LINK',
                'GOOGLE', 'v1', 'digest-one', '{linkId:D}', 'IDP_COMMITTED', '{correlationId:D}'
            );
            INSERT INTO identity.provider_link_projections (
                link_id, global_user_id, provider_class, binding_reference, state
            ) VALUES (
                '{linkId:D}', '{globalUserId:D}', 'GOOGLE', '{bindingReference:D}', 'ACTIVE'
            );
            """
        );

        Assert.Equal(
            1L,
            await ActorScalarAsync<long>(
                proof.Actor,
                "SELECT count(*) FROM identity.provider_link_projections",
                Guid.Empty
            )
        );
        Assert.Equal(
            0L,
            await ActorScalarAsync<long>(
                foreign.Actor,
                "SELECT count(*) FROM identity.provider_link_projections",
                Guid.Empty
            )
        );

        var keyMutation = await Assert.ThrowsAsync<PostgresException>(() =>
            ActorExecuteAsync(
                proof.Actor,
                $"UPDATE identity.provider_link_projections SET binding_reference = '{Guid.NewGuid():D}' WHERE link_id = '{linkId:D}'"
            )
        );
        Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, keyMutation.SqlState);

        var duplicate = await Assert.ThrowsAsync<PostgresException>(() =>
            ActorExecuteAsync(
                proof.Actor,
                $"""
                INSERT INTO identity.lifecycle_operations (
                    operation_id, actor_issuer, actor_subject, command_type,
                    provider_class, idempotency_key_version, idempotency_digest, target_link_reference,
                    state, correlation_id
                ) VALUES (
                    '{Guid.NewGuid():D}', '{proof.Actor.Issuer}', '{proof.Actor.Subject}', 'LINK',
                    'GOOGLE', 'v1', 'digest-one', '{Guid.NewGuid():D}', 'PROOF_REQUIRED', '{Guid.NewGuid():D}'
                )
                """
            )
        );
        Assert.Equal(PostgresErrorCodes.UniqueViolation, duplicate.SqlState);

        await ActorExecuteAsync(
            proof.Actor,
            $"""
            UPDATE identity.lifecycle_operations
               SET state = 'COMPLETED', version = version + 1, terminal_at = now()
             WHERE operation_id = '{operationId:D}';
            UPDATE identity.provider_link_projections
               SET state = 'RETIRED', retired_at = now()
             WHERE link_id = '{linkId:D}';
            """
        );
        var delete = await Assert.ThrowsAsync<PostgresException>(() =>
            ActorExecuteAsync(
                proof.Actor,
                $"DELETE FROM identity.lifecycle_operations WHERE operation_id = '{operationId:D}'"
            )
        );
        Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, delete.SqlState);
    }

    [Fact]
    public async Task LifecycleService_ReplaysSameInput_AndRejectsChangedInput()
    {
        var proof = SyntheticProof("lifecycle-service", "lifecycle-service-google");
        await CompleteAsync(proof);
        var service = new IdentityLifecycleService(
            new WorkspaceDbContextFactory(AppConnectionString()),
            Options.Create(
                new IdentityHmacOptions
                {
                    Key = new string('k', IdentityHmacOptions.MinKeyLength),
                    ActiveVersion = "v1",
                }
            )
        );
        var idempotencyKey = Guid.NewGuid();
        var stepUp = Guid.NewGuid();
        var first = await service.BeginLinkAsync(
            proof.Actor,
            IdentityLifecycleProvider.Google,
            stepUp,
            idempotencyKey,
            Guid.NewGuid()
        );
        var replay = await service.BeginLinkAsync(
            proof.Actor,
            IdentityLifecycleProvider.Google,
            stepUp,
            idempotencyKey,
            Guid.NewGuid()
        );

        Assert.False(first.Replayed);
        Assert.True(replay.Replayed);
        Assert.Equal(first.OperationReference, replay.OperationReference);
        Assert.Equal(first.LinkReference, replay.LinkReference);
        Assert.Equal("PROOF_REQUIRED", replay.State);
        await Assert.ThrowsAsync<IdentityLifecycleConflictException>(() =>
            service.BeginLinkAsync(
                proof.Actor,
                IdentityLifecycleProvider.Apple,
                stepUp,
                idempotencyKey,
                Guid.NewGuid()
            )
        );
        Assert.Equal(
            1L,
            await OwnerScalarAsync<long>("SELECT count(*) FROM identity.lifecycle_operations")
        );
        await AssertPoolEmptyAsync();
    }

    [Fact]
    public async Task LifecycleSaga_ReadsBack_CompletesAndProtectsLastMethod()
    {
        var proof = SyntheticProof("lifecycle-saga", "lifecycle-saga-google");
        await CompleteAsync(proof);
        var writer = new SyntheticLifecycleWriter();
        var service = LifecycleService(writer);
        var googleBinding = new KeycloakFederatedBinding(
            "google",
            "opaque-google-id",
            "opaque-google-user"
        );
        var google = await service.BeginLinkAsync(
            proof.Actor,
            IdentityLifecycleProvider.Google,
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid()
        );
        var linked = await service.CompleteLinkAsync(
            proof.Actor,
            google.OperationReference,
            proof.Actor.Subject,
            googleBinding
        );
        var replay = await service.CompleteLinkAsync(
            proof.Actor,
            google.OperationReference,
            proof.Actor.Subject,
            googleBinding
        );

        Assert.Equal("COMPLETED", linked.State);
        Assert.True(replay.Replayed);
        Assert.Equal(1, writer.AddCount);
        var firstUnlink = await service.BeginUnlinkAsync(
            proof.Actor,
            google.LinkReference,
            Guid.NewGuid(),
            Guid.NewGuid()
        );
        await Assert.ThrowsAsync<IdentityLifecycleLastMethodException>(() =>
            service.CompleteUnlinkAsync(
                proof.Actor,
                firstUnlink.OperationReference,
                proof.Actor.Subject
            )
        );

        var appleBinding = new KeycloakFederatedBinding(
            "apple",
            "opaque-apple-id",
            "opaque-apple-user"
        );
        var apple = await service.BeginLinkAsync(
            proof.Actor,
            IdentityLifecycleProvider.Apple,
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid()
        );
        await service.CompleteLinkAsync(
            proof.Actor,
            apple.OperationReference,
            proof.Actor.Subject,
            appleBinding
        );
        var unlinked = await service.CompleteUnlinkAsync(
            proof.Actor,
            firstUnlink.OperationReference,
            proof.Actor.Subject
        );

        Assert.Equal("COMPLETED", unlinked.State);
        Assert.Equal(1, writer.RemoveCount);
        Assert.Equal(
            1L,
            await OwnerScalarAsync<long>(
                "SELECT count(*) FROM identity.provider_link_projections WHERE state = 'ACTIVE'"
            )
        );
        Assert.Equal(
            1L,
            await OwnerScalarAsync<long>(
                "SELECT count(*) FROM identity.provider_link_projections WHERE state = 'RETIRED'"
            )
        );
        await AssertPoolEmptyAsync();
    }

    [Fact]
    public async Task LifecycleSaga_ReconcilesCommittedUnknown_AndQuarantinesUnconfirmedUnknown()
    {
        var proof = SyntheticProof("lifecycle-unknown", "lifecycle-unknown-google");
        await CompleteAsync(proof);
        var writer = new SyntheticLifecycleWriter { UnknownAddCommits = true };
        var service = LifecycleService(writer);
        var google = await service.BeginLinkAsync(
            proof.Actor,
            IdentityLifecycleProvider.Google,
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid()
        );
        var committed = await service.CompleteLinkAsync(
            proof.Actor,
            google.OperationReference,
            proof.Actor.Subject,
            new KeycloakFederatedBinding("google", "unknown-google-id", "unknown-google-user")
        );
        Assert.Equal("COMPLETED", committed.State);

        writer.UnknownAddCommits = false;
        writer.UnknownAddDoesNotCommit = true;
        var apple = await service.BeginLinkAsync(
            proof.Actor,
            IdentityLifecycleProvider.Apple,
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid()
        );
        await Assert.ThrowsAsync<IdentityLifecycleRecoveryRequiredException>(() =>
            service.CompleteLinkAsync(
                proof.Actor,
                apple.OperationReference,
                proof.Actor.Subject,
                new KeycloakFederatedBinding("apple", "unknown-apple-id", "unknown-apple-user")
            )
        );
        Assert.Equal(
            "RECOVERY_REQUIRED",
            await OwnerScalarAsync<string>(
                $"SELECT state FROM identity.lifecycle_operations WHERE operation_id = '{apple.OperationReference:D}'"
            )
        );
        Assert.Equal(
            1L,
            await OwnerScalarAsync<long>("SELECT count(*) FROM identity.provider_link_projections")
        );
    }

    [Fact]
    public async Task LifecycleSaga_CompensatesConfirmedProjectionFailure()
    {
        var proof = SyntheticProof("lifecycle-compensation", "lifecycle-compensation-google");
        await CompleteAsync(proof);
        await ExecuteOwnerAsync(
            """
            ALTER TABLE identity.provider_link_projections
                ADD CONSTRAINT reject_synthetic_google_projection
                CHECK (provider_class <> 'GOOGLE');
            """
        );
        var writer = new SyntheticLifecycleWriter();
        var service = LifecycleService(writer);
        var operation = await service.BeginLinkAsync(
            proof.Actor,
            IdentityLifecycleProvider.Google,
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid()
        );
        await Assert.ThrowsAsync<IdentityActionDeniedException>(() =>
            service.CompleteLinkAsync(
                proof.Actor,
                operation.OperationReference,
                proof.Actor.Subject,
                new KeycloakFederatedBinding(
                    "google",
                    "compensated-google-id",
                    "compensated-google-user"
                )
            )
        );

        Assert.Equal(1, writer.AddCount);
        Assert.Equal(1, writer.RemoveCount);
        Assert.Empty(await writer.ReadBindingsAsync(proof.Actor.Subject, default));
        Assert.Equal(
            "FAILED",
            await OwnerScalarAsync<string>(
                $"SELECT state FROM identity.lifecycle_operations WHERE operation_id = '{operation.OperationReference:D}'"
            )
        );
        Assert.Equal(
            0L,
            await OwnerScalarAsync<long>("SELECT count(*) FROM identity.provider_link_projections")
        );
    }

    [Fact]
    public async Task ConstraintFailure_RollsBackWholeCohortAndEvidence_ThenRetrySucceeds()
    {
        var proof = SyntheticProof("rollback", "rollback-google");
        var registration = await SeedAsync(proof);
        var key = Guid.NewGuid();
        await ExecuteOwnerAsync(
            """
            ALTER TABLE identity.idempotency_ledger ADD CONSTRAINT reject_test_completion
                CHECK (operation_family <> 'CompleteRegistration');
            """
        );

        var failure = await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            Service().CompleteAsync(proof, registration, key, Hash)
        );

        Assert.Equal(CustomerWorkspaceError.InvariantViolation, failure.Error);
        var postgres = Assert.IsType<PostgresException>(failure.InnerException);
        Assert.Equal("reject_test_completion", postgres.ConstraintName);
        await AssertCountsAsync(0, 0, 0);
        Assert.Equal(
            1L,
            await OwnerScalarAsync<long>(
                "SELECT count(*) FROM identity.registrations WHERE state = 'ReadyToComplete' AND account_id IS NULL"
            )
        );
        await ExecuteOwnerAsync(
            "ALTER TABLE identity.idempotency_ledger DROP CONSTRAINT reject_test_completion"
        );
        var completed = await Service().CompleteAsync(proof, registration, key, Hash);
        var replay = await Service().CompleteAsync(proof, registration, key, Hash);
        Assert.Equal(completed, replay);
        await AssertCountsAsync(1, 1, 1);
        await AssertPoolEmptyAsync();
    }

    [Theory]
    [InlineData("DENTAL_CLINIC", "DENTAL_CLINIC")]
    [InlineData("dental_clinic", null)]
    [InlineData("Consulting with an accepted free-text domain longer than fifty characters", null)]
    public async Task BusinessDomain_MapsOnlyExactActiveTaxonomy_PreservesFullSnapshot(
        string domain,
        string? expected
    )
    {
        var proof = SyntheticProof("domain", "domain-google");
        var registration = await SeedAsync(proof, businessDomain: domain);

        await Service().CompleteAsync(proof, registration, Guid.NewGuid(), Hash);

        Assert.Equal(
            expected ?? "NULL",
            await OwnerScalarAsync<string>(
                "SELECT COALESCE(business_domain, 'NULL') FROM business.organisations"
            )
        );
        Assert.Equal(
            domain,
            await OwnerScalarAsync<string>(
                "SELECT completion_profile_snapshot->>'businessDomain' FROM identity.registrations WHERE actor_issuer IS NOT NULL"
            )
        );
    }

    [Fact]
    public async Task ResolverDatabaseFailure_IsTypedUnavailable_AndDoesNotMutate()
    {
        var proof = SyntheticProof("resolver-failure", "resolver-failure-google");
        await ExecuteOwnerAsync(
            "REVOKE EXECUTE ON FUNCTION identity.resolve_customer_membership() FROM business_app"
        );
        var failure = await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            Service().ResolveAsync(proof.Actor)
        );
        Assert.Equal(CustomerWorkspaceError.DependencyUnavailable, failure.Error);
        Assert.Equal(503, failure.StatusCode);
        await AssertCountsAsync(0, 0, 0);
    }

    [Fact]
    public async Task SameAndDifferentKeysAndRegistrations_KeepOriginalResponseAndProfile_AfterExpiry()
    {
        var proof = SyntheticProof("retry", "retry-google");
        var registration = await SeedAsync(proof, "Winning Profile");
        var key = Guid.NewGuid();
        var completed = await Service().CompleteAsync(proof, registration, key, Hash);

        var replay = await Service().CompleteAsync(proof, registration, key, Hash);
        var otherKey = await Service().CompleteAsync(proof, registration, Guid.NewGuid(), Hash);
        var continuation = await SeedAsync(proof, "Must Not Replace Winner");
        var reused = await Service().CompleteAsync(proof, continuation, Guid.NewGuid(), Hash);

        Assert.Equal(completed, replay);
        Assert.Equal(completed, otherKey);
        Assert.Equal(completed, reused);
        Assert.Equal(
            "Winning Profile",
            await OwnerScalarAsync<string>("SELECT name FROM business.organisations")
        );
        Assert.Equal(
            1L,
            await OwnerScalarAsync<long>(
                "SELECT count(DISTINCT completion_profile_snapshot) FROM identity.registrations WHERE actor_issuer IS NOT NULL"
            )
        );
        await AssertCountsAsync(1, 2, 3);
        await ExecuteOwnerAsync(
            """
            ALTER TABLE identity.registrations DISABLE TRIGGER guard_registration_identity;
            UPDATE identity.registrations SET expires_at = now() - interval '2 days' WHERE actor_issuer IS NOT NULL;
            SET CONSTRAINTS ALL IMMEDIATE;
            ALTER TABLE identity.registrations ENABLE TRIGGER guard_registration_identity;
            UPDATE identity.idempotency_ledger SET created_at = now() - interval '3 days', expires_at = now() - interval '1 day';
            """
        );
        Assert.Equal(completed, await Service().CompleteAsync(proof, registration, key, Hash));
        Assert.Equal(
            completed,
            await Service().CompleteAsync(proof, registration, Guid.NewGuid(), Hash)
        );
        await AssertCountsAsync(1, 2, 4);
    }

    [Fact]
    public async Task ConflictingHashAndCrossRegistrationKeyReuse_DenyWithoutMutation()
    {
        var proof = SyntheticProof("conflict", "conflict-google");
        var registration = await SeedAsync(proof);
        var key = Guid.NewGuid();
        await Service().CompleteAsync(proof, registration, key, Hash);
        var continuation = await SeedAsync(proof);

        var conflict = await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            Service().CompleteAsync(proof, registration, key, Digest)
        );
        var wrongRegistration = await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            Service().CompleteAsync(proof, continuation, key, Hash)
        );

        Assert.Equal(CustomerWorkspaceError.IdempotencyConflict, conflict.Error);
        Assert.Equal(409, conflict.StatusCode);
        Assert.Equal(CustomerWorkspaceError.IdempotencyConflict, wrongRegistration.Error);
        await AssertCountsAsync(1, 1, 1);
        Assert.Equal(
            1L,
            await OwnerScalarAsync<long>(
                "SELECT count(*) FROM identity.registrations WHERE state = 'ReadyToComplete'"
            )
        );
    }

    [Theory]
    [InlineData(false, false)]
    [InlineData(false, true)]
    [InlineData(true, true)]
    public async Task ConcurrentSameActor_OneCohortAndImmutableWinner(
        bool differentRegistrations,
        bool differentKeys
    )
    {
        var proof = SyntheticProof("race", "race-google");
        var firstRegistration = await SeedAsync(proof, "First Profile");
        var secondRegistration = differentRegistrations
            ? await SeedAsync(proof, "Second Profile")
            : firstRegistration;
        var firstKey = Guid.NewGuid();
        var secondKey = differentKeys ? Guid.NewGuid() : firstKey;
        var start = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        async Task<CustomerWorkspaceCompletion> Complete(Guid registration, Guid key)
        {
            await start.Task;
            return await Service().CompleteAsync(proof, registration, key, Hash);
        }
        var firstTask = Complete(firstRegistration, firstKey);
        var secondTask = Complete(secondRegistration, secondKey);

        start.SetResult();
        var results = await Task.WhenAll(firstTask, secondTask);

        Assert.Equal(results[0], results[1]);
        await AssertCountsAsync(1, differentRegistrations ? 2 : 1, differentKeys ? 2 : 1);
        Assert.Equal(
            1L,
            await OwnerScalarAsync<long>(
                "SELECT count(DISTINCT completion_profile_snapshot) FROM identity.registrations WHERE actor_issuer IS NOT NULL"
            )
        );
    }

    [Fact]
    public async Task ConcurrentDifferentActorsSameProvider_OneWinner_OtherRequiresUnresolvedRecovery()
    {
        var first = SyntheticProof("race-actor-one", "same-provider");
        var second = SyntheticProof("race-actor-two", "same-provider");
        var firstRegistration = await SeedAsync(first);
        var secondRegistration = await SeedAsync(second);
        var start = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        async Task<(
            CustomerWorkspaceCompletion? Result,
            CustomerWorkspaceException? Failure
        )> Complete(VerifiedGoogleWorkspaceProof proof, Guid registration)
        {
            await start.Task;
            try
            {
                return (
                    await Service().CompleteAsync(proof, registration, Guid.NewGuid(), Hash),
                    null
                );
            }
            catch (CustomerWorkspaceException failure)
            {
                return (null, failure);
            }
        }
        var firstTask = Complete(first, firstRegistration);
        var secondTask = Complete(second, secondRegistration);

        start.SetResult();
        var outcomes = await Task.WhenAll(firstTask, secondTask);

        Assert.Single(outcomes, outcome => outcome.Result is not null);
        var failed = Assert.Single(outcomes, outcome => outcome.Failure is not null);
        Assert.Equal(CustomerWorkspaceError.RecoveryRequired, failed.Failure!.Error);
        var losingActor = outcomes[0].Failure is not null ? first.Actor : second.Actor;
        var denied = await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            Service().ResolveAsync(losingActor)
        );
        Assert.Equal(CustomerWorkspaceError.MembershipRequired, denied.Error);
        await AssertCountsAsync(1, 1, 1);
    }

    [Theory]
    [InlineData("CaseSubject", Issuer + "/other")]
    [InlineData("casesubject", Issuer)]
    [InlineData("CaseSubject", "https://synthetic.invalid/realms/Customer")]
    public async Task ExactIssuerSubjectBinding_NoCrossRegistrationOrResourceAccess(
        string secondSubject,
        string secondIssuer
    )
    {
        var first = SyntheticProof("CaseSubject", "first-exact-google");
        var second = SyntheticProof(secondSubject, "second-exact-google", secondIssuer);
        var firstRegistration = await SeedAsync(first);
        var secondRegistration = await SeedAsync(second);
        await Service().CompleteAsync(first, firstRegistration, Guid.NewGuid(), Hash);
        await Service(secondIssuer).CompleteAsync(second, secondRegistration, Guid.NewGuid(), Hash);
        var firstMembership = await Service().ResolveAsync(first.Actor);
        var secondMembership = await Service(secondIssuer).ResolveAsync(second.Actor);

        var denied = await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            Service(secondIssuer).CompleteAsync(second, firstRegistration, Guid.NewGuid(), Hash)
        );
        Assert.Equal(CustomerWorkspaceError.RegistrationNotFound, denied.Error);
        Assert.NotEqual(firstMembership.AccountId, secondMembership.AccountId);
        Assert.Equal(
            0L,
            await ActorScalarAsync<long>(
                second.Actor,
                "SELECT count(*) FROM business.organisations WHERE tenant_id = @tenant",
                firstMembership.TenantId
            )
        );
        Assert.Equal(
            0L,
            await ActorScalarAsync<long>(
                second.Actor,
                "SELECT count(*) FROM business.organisations",
                firstMembership.TenantId,
                forgeTenant: true
            )
        );
        Assert.Equal(
            1L,
            await ActorScalarAsync<long>(
                second.Actor,
                "SELECT count(*) FROM business.organisations",
                secondMembership.TenantId,
                forgeTenant: true
            )
        );
        Assert.Equal(
            0L,
            await ActorScalarAsync<long>(
                second.Actor,
                "SELECT count(*) FROM business.organisations",
                secondMembership.TenantId,
                forgeTenant: true,
                mismatchTenant: true
            )
        );
        await AssertCountsAsync(2, 2, 2);
    }

    [Theory]
    [InlineData("constitutional_app")]
    [InlineData("runtime_app")]
    [InlineData("wbe_app")]
    public async Task ReceiverRoles_ResolverOnly_NoIdentityTableWriteSchemaOrOwnerAccess(
        string role
    )
    {
        var proof = SyntheticProof("role-customer", "role-google");
        var registration = await SeedAsync(proof);
        var result = await Service().CompleteAsync(proof, registration, Guid.NewGuid(), Hash);
        await using var connection = new NpgsqlConnection(AppConnectionString(role));
        await connection.OpenAsync();
        await using var transaction = await connection.BeginTransactionAsync();
        await SetActorAsync(connection, transaction, proof.Actor);
        await using var command = new NpgsqlCommand(
            "SELECT account_id FROM identity.resolve_customer_membership()",
            connection,
            transaction
        );
        Assert.Equal(result.Result.AccountReference, await command.ExecuteScalarAsync());
        await transaction.RollbackAsync();

        foreach (
            var sql in new[]
            {
                "SELECT * FROM identity.accounts",
                "SELECT * FROM identity.registrations",
                "INSERT INTO identity.memberships DEFAULT VALUES",
                "UPDATE identity.memberships SET status = 'INACTIVE'",
                "CREATE TABLE identity.forbidden(value int)",
                "CREATE TABLE business.forbidden(value int)",
                "CREATE TABLE public.forbidden(value int)",
                "SET ROLE identity_resolver_owner",
                "SELECT identity.guard_registration_identity()",
                "SELECT identity.assert_completed_cohort()",
            }
        )
            await AssertPrivilegeDeniedAsync(role, sql);
    }

    [Fact]
    public async Task BusinessRoleAndResolverOwner_HaveOnlyBoundedPrivileges()
    {
        foreach (
            var sql in new[]
            {
                "UPDATE identity.accounts SET status = 'INACTIVE'",
                "DELETE FROM identity.actor_bindings",
                "UPDATE identity.idempotency_ledger SET status_code = 200",
                "DELETE FROM identity.registration_events",
                "TRUNCATE identity.memberships",
                "UPDATE identity.registrations SET actor_subject = 'different'",
                "UPDATE identity.registrations SET provider_issuer = 'different'",
                "UPDATE business.organisations SET identity_status = 'ACTIVE'",
                "CREATE TABLE identity.forbidden(value int)",
                "CREATE TABLE business.forbidden(value int)",
                "CREATE TABLE public.forbidden(value int)",
                "SET ROLE identity_resolver_owner",
            }
        )
            await AssertPrivilegeDeniedAsync("business_app", sql);
        Assert.False(
            await OwnerScalarAsync<bool>(
                "SELECT rolcanlogin OR rolsuper OR rolbypassrls OR rolcreaterole FROM pg_roles WHERE rolname = 'identity_resolver_owner'"
            )
        );
        Assert.False(
            await OwnerScalarAsync<bool>(
                "SELECT has_column_privilege('identity_resolver_owner', 'identity.actor_bindings', 'trust_config_digest', 'SELECT')"
            )
        );
        Assert.False(
            await OwnerScalarAsync<bool>(
                "SELECT has_schema_privilege('identity_resolver_owner', 'identity', 'CREATE')"
            )
        );
        Assert.Equal(
            8L,
            await OwnerScalarAsync<long>(
                """
                SELECT count(*) FROM pg_class AS relation JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
                WHERE relation.relrowsecurity AND relation.relforcerowsecurity AND (
                    namespace.nspname = 'identity' AND relation.relname IN
                        ('accounts','login_methods','actor_bindings','memberships','registrations','registration_events','idempotency_ledger')
                    OR namespace.nspname = 'business' AND relation.relname = 'organisations')
                """
            )
        );
        await using var owner = new NpgsqlConnection(_ownerConnectionString);
        await owner.OpenAsync();
        await using var command = new NpgsqlCommand("SET ROLE identity_resolver_owner", owner);
        await command.ExecuteNonQueryAsync();
        command.CommandText = "SELECT trust_config_digest FROM identity.actor_bindings";
        Assert.Equal(
            PostgresErrorCodes.InsufficientPrivilege,
            (
                await Assert.ThrowsAsync<PostgresException>(() => command.ExecuteScalarAsync())
            ).SqlState
        );
        command.CommandText = "INSERT INTO identity.memberships DEFAULT VALUES";
        Assert.Equal(
            PostgresErrorCodes.InsufficientPrivilege,
            (
                await Assert.ThrowsAsync<PostgresException>(() => command.ExecuteNonQueryAsync())
            ).SqlState
        );
    }

    [Fact]
    public async Task MissingActorContext_DeniesReadsAndUnboundOrganisationWrites_EvenWithGuessedTenant()
    {
        var proof = SyntheticProof("context", "context-google");
        var registration = await SeedAsync(proof);
        await Service().CompleteAsync(proof, registration, Guid.NewGuid(), Hash);
        var membership = await Service().ResolveAsync(proof.Actor);
        await using var connection = new NpgsqlConnection(AppConnectionString());
        await connection.OpenAsync();
        await using var transaction = await connection.BeginTransactionAsync();
        await using var command = new NpgsqlCommand(
            """
            SELECT set_config('app.identity_issuer', '', true), set_config('app.identity_subject', '', true),
                   set_config('app.tenant_id', @tenant, true), set_config('app.current_tenant_id', @tenant, true)
            """,
            connection,
            transaction
        );
        command.Parameters.AddWithValue("tenant", membership.TenantId.ToString());
        await command.ExecuteNonQueryAsync();
        foreach (
            var sql in new[]
            {
                "SELECT count(*) FROM identity.resolve_customer_membership()",
                "SELECT count(*) FROM business.organisations",
                "SELECT count(*) FROM identity.accounts",
            }
        )
        {
            command.CommandText = sql;
            Assert.Equal(0L, await command.ExecuteScalarAsync());
        }
        await transaction.RollbackAsync();
        await using var db = new WorkspaceDbContextFactory(AppConnectionString()).CreateDbContext();
        await using var actorTransaction = await db.Database.BeginTransactionAsync();
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            SELECT set_config('app.identity_issuer', {proof.Actor.Issuer}, true),
                   set_config('app.identity_subject', {proof.Actor.Subject}, true),
                   set_config('app.tenant_id', '', true), set_config('app.current_tenant_id', '', true)
            """
        );
        var foreignTenant = Guid.NewGuid();
        var denied = await Assert.ThrowsAsync<PostgresException>(() =>
            db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                INSERT INTO business.organisations(id, tenant_id, name, identity_managed, identity_status)
                    VALUES ({foreignTenant}, {foreignTenant}, 'Unbound', true, 'ACTIVE')
                """
            )
        );
        Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, denied.SqlState);
    }

    [Theory]
    [InlineData("membership")]
    [InlineData("account")]
    [InlineData("organisation")]
    [InlineData("actor")]
    [InlineData("login")]
    public async Task InactiveOrRetiredCohort_DeniesLookupAndReplayWithoutReminting(string inactive)
    {
        var proof = SyntheticProof("inactive", "inactive-google");
        var registration = await SeedAsync(proof);
        var key = Guid.NewGuid();
        await Service().CompleteAsync(proof, registration, key, Hash);
        await ExecuteOwnerAsync(
            inactive switch
            {
                "membership" => "UPDATE identity.memberships SET status = 'SUSPENDED'",
                "account" => "UPDATE identity.accounts SET status = 'INACTIVE'",
                "organisation" => "UPDATE business.organisations SET identity_status = 'INACTIVE'",
                "actor" => "UPDATE identity.actor_bindings SET status = 'RETIRED'",
                _ => "UPDATE identity.login_methods SET status = 'RETIRED'",
            }
        );

        var lookup = await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            Service().ResolveAsync(proof.Actor)
        );
        var replay = await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            Service().CompleteAsync(proof, registration, key, Hash)
        );

        Assert.Equal(CustomerWorkspaceError.MembershipInactive, lookup.Error);
        Assert.Contains(
            replay.Error,
            new[]
            {
                CustomerWorkspaceError.MembershipRequired,
                CustomerWorkspaceError.RecoveryRequired,
            }
        );
        await AssertCountsAsync(1, 1, 1);
    }

    [Theory]
    [InlineData("null")]
    [InlineData("old-auth")]
    [InlineData("old-proof")]
    [InlineData("future")]
    [InlineData("wrong-issuer")]
    [InlineData("empty-provider")]
    [InlineData("oversize")]
    [InlineData("nul")]
    [InlineData("invalid-utf16")]
    public async Task MissingInvalidOrExpiredSyntheticProof_DeniesBeforeMutation(string invalid)
    {
        var valid = SyntheticProof("proof", "proof-google");
        var registration = await SeedAsync(valid);
        var proof = invalid switch
        {
            "null" => null!,
            "old-auth" => SyntheticProof(
                "proof",
                "proof-google",
                authTime: DateTimeOffset.UtcNow.AddMinutes(-6)
            ),
            "old-proof" => SyntheticProof(
                "proof",
                "proof-google",
                verifiedAt: DateTimeOffset.UtcNow.AddMinutes(-6),
                authTime: DateTimeOffset.UtcNow.AddMinutes(-6)
            ),
            "future" => SyntheticProof(
                "proof",
                "proof-google",
                authTime: DateTimeOffset.UtcNow.AddMinutes(1)
            ),
            "wrong-issuer" => SyntheticProof("proof", "proof-google", Issuer + "/wrong"),
            "empty-provider" => SyntheticProof("proof", ""),
            "oversize" => SyntheticProof("proof", new string('a', 257)),
            "nul" => SyntheticProof("proof", "provider\0subject"),
            _ => SyntheticProof("proof", "provider\ud800subject"),
        };

        var failure = await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            Service().CompleteAsync(proof, registration, Guid.NewGuid(), Hash)
        );

        Assert.Contains(
            failure.Error,
            new[]
            {
                CustomerWorkspaceError.ProofRequired,
                CustomerWorkspaceError.FreshAuthenticationRequired,
            }
        );
        await AssertCountsAsync(0, 0, 0);
    }

    [Fact]
    public async Task ProofAgesOutBeforeCommit_RollsBackAllWrites()
    {
        var proof = SyntheticProof("aging", "aging-google");
        var registration = await SeedAsync(proof);
        var clock = new CommitExpiryTimeProvider(DateTimeOffset.UtcNow);

        var failure = await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            Service(time: clock).CompleteAsync(proof, registration, Guid.NewGuid(), Hash)
        );

        Assert.Equal(CustomerWorkspaceError.FreshAuthenticationRequired, failure.Error);
        await AssertCountsAsync(0, 0, 0);
        Assert.Equal(
            1L,
            await OwnerScalarAsync<long>(
                "SELECT count(*) FROM identity.registrations WHERE state = 'ReadyToComplete' AND account_id IS NULL"
            )
        );
    }

    [Theory]
    [InlineData(IdentityRegistrationState.Cancelled, true, false)]
    [InlineData(IdentityRegistrationState.ReadyToComplete, false, false)]
    [InlineData(IdentityRegistrationState.ReadyToComplete, true, true)]
    [InlineData(IdentityRegistrationState.ProfileCompletionRequired, true, false)]
    public async Task IneligibleRegistration_Denies(
        IdentityRegistrationState state,
        bool emailVerified,
        bool expired
    )
    {
        var proof = SyntheticProof("ineligible", "ineligible-google");
        var registration = await SeedAsync(
            proof,
            state: state,
            emailVerified: emailVerified,
            expiresAt: expired ? DateTimeOffset.UtcNow.AddMinutes(-1) : null
        );

        var failure = await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            Service().CompleteAsync(proof, registration, Guid.NewGuid(), Hash)
        );

        Assert.Equal(CustomerWorkspaceError.RegistrationIneligible, failure.Error);
        await AssertCountsAsync(0, 0, 0);
    }

    [Fact]
    public async Task LegacyCompletedRows_AreRetainedButCannotResolveOrReplay_AndNewNullIssuerDenied()
    {
        var proof = SyntheticProof("legacy", "legacy-google");
        var failure = await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            Service()
                .CompleteAsync(
                    proof,
                    Guid.Parse("00000000-0000-0000-0000-000000000085"),
                    Guid.NewGuid(),
                    Hash
                )
        );
        Assert.Equal(CustomerWorkspaceError.RegistrationNotFound, failure.Error);
        Assert.Equal(
            CustomerWorkspaceError.MembershipRequired,
            (
                await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
                    Service().ResolveAsync(proof.Actor)
                )
            ).Error
        );
        Assert.Equal(
            1L,
            await OwnerScalarAsync<long>(
                "SELECT count(*) FROM identity.registrations WHERE actor_issuer IS NULL AND state = 'Completed'"
            )
        );
        var invalid = await Assert.ThrowsAsync<PostgresException>(() =>
            ExecuteOwnerAsync(
                """
                INSERT INTO identity.registrations(actor_subject, authentication_path) VALUES ('unknown', 'Google')
                """
            )
        );
        Assert.Equal("registrations_issuer_required", invalid.ConstraintName);
        await AssertCountsAsync(0, 0, 0);
    }

    [Fact]
    public async Task CompletedFieldsAreImmutable_AndIncompleteCohortCannotCommit()
    {
        var proof = SyntheticProof("immutable", "immutable-google");
        var registration = await SeedAsync(proof);
        await Service().CompleteAsync(proof, registration, Guid.NewGuid(), Hash);
        await using var db = new WorkspaceDbContextFactory(AppConnectionString()).CreateDbContext();
        await using var transaction = await db.Database.BeginTransactionAsync();
        await Service().ResolveInTransactionAsync(db, proof.Actor);
        var failed = await Assert.ThrowsAsync<PostgresException>(() =>
            db.Database.ExecuteSqlInterpolatedAsync(
                $"UPDATE identity.registrations SET business_name = 'Overwrite' WHERE registration_id = {registration}"
            )
        );
        Assert.Equal(PostgresErrorCodes.CheckViolation, failed.SqlState);
        await transaction.RollbackAsync();
        await AssertCountsAsync(1, 1, 1);
        var incomplete = await Assert.ThrowsAsync<PostgresException>(() =>
            ExecuteOwnerAsync(
                """
                INSERT INTO identity.registrations(actor_issuer, actor_subject, authentication_path, state)
                    VALUES ('synthetic', 'unproven', 'Google', 'Completed')
                """
            )
        );
        Assert.Equal("registrations_completed_identity_check", incomplete.ConstraintName);
    }

    [Fact]
    public async Task PooledConnectionContext_ResetsAfterSuccessAndRollback_ResolverSetsBothTenantValues()
    {
        var proof = SyntheticProof("pool", "pool-google");
        var registration = await SeedAsync(proof);
        var pool = new NpgsqlConnectionStringBuilder(AppConnectionString())
        {
            MaxPoolSize = 1,
        }.ConnectionString;
        var service = new CustomerWorkspaceProvisioningService(
            new WorkspaceDbContextFactory(pool),
            new CustomerWorkspaceTrust(Issuer, Provider, "google", Digest)
        );
        await service.CompleteAsync(proof, registration, Guid.NewGuid(), Hash);
        var live = await service.ResolveAsync(proof.Actor);
        await AssertPoolEmptyAsync(pool);
        await using (var db = new WorkspaceDbContextFactory(pool).CreateDbContext())
        {
            await using var transaction = await db.Database.BeginTransactionAsync();
            await db.Database.ExecuteSqlRawAsync(
                """
                SELECT set_config('app.identity_issuer', 'wrong', true), set_config('app.identity_subject', 'wrong', true),
                       set_config('app.tenant_id', 'not-a-uuid', true), set_config('app.current_tenant_id', 'not-a-uuid', true)
                """
            );
            var resolved = await service.ResolveInTransactionAsync(db, proof.Actor);
            Assert.Equal(live.AccountId, resolved.AccountId);
            Assert.Equal(live.TenantId, resolved.TenantId);
            Assert.Equal(1, await db.Organisations.CountAsync());
            var forced = await Assert.ThrowsAsync<PostgresException>(() =>
                db.Database.ExecuteSqlRawAsync("SELECT 1 / 0")
            );
            Assert.Equal(PostgresErrorCodes.DivisionByZero, forced.SqlState);
        }
        await AssertPoolEmptyAsync(pool);
        var other = SyntheticProof("other-pool-user", "other-pool-google");
        Assert.Equal(
            CustomerWorkspaceError.MembershipRequired,
            (
                await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
                    service.ResolveAsync(other.Actor)
                )
            ).Error
        );
        await AssertPoolEmptyAsync(pool);
        await using var noTransaction = new WorkspaceDbContextFactory(pool).CreateDbContext();
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            service.ResolveInTransactionAsync(noTransaction, proof.Actor)
        );
        Assert.Empty(typeof(VerifiedGoogleWorkspaceProof).GetConstructors());
        Assert.Empty(typeof(VerifiedCustomerActor).GetConstructors());
        Assert.Throws<NotSupportedException>(() =>
            JsonSerializer.Deserialize<VerifiedCustomerActor>(
                "{\"issuer\":\"forged\",\"subject\":\"forged\"}"
            )
        );
    }

    private async Task AssertCountsAsync(long cohorts, long events, long entries)
    {
        foreach (
            var table in new[]
            {
                "identity.accounts",
                "identity.actor_bindings",
                "identity.login_methods",
                "identity.memberships",
                "business.organisations",
            }
        )
            Assert.Equal(cohorts, await OwnerScalarAsync<long>($"SELECT count(*) FROM {table}"));
        Assert.Equal(
            events,
            await OwnerScalarAsync<long>("SELECT count(*) FROM identity.registration_events")
        );
        Assert.Equal(
            entries,
            await OwnerScalarAsync<long>("SELECT count(*) FROM identity.idempotency_ledger")
        );
    }

    private async Task<T> OwnerScalarAsync<T>(string sql)
    {
        await using var connection = new NpgsqlConnection(_ownerConnectionString);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        return (T)(await command.ExecuteScalarAsync())!;
    }

    private async Task AssertPoolEmptyAsync(string? connectionString = null)
    {
        await using var connection = new NpgsqlConnection(
            connectionString ?? AppConnectionString()
        );
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(
            """
            SELECT NULLIF(current_setting('app.identity_issuer', true), '') IS NULL
               AND NULLIF(current_setting('app.identity_subject', true), '') IS NULL
               AND NULLIF(current_setting('app.tenant_id', true), '') IS NULL
               AND NULLIF(current_setting('app.current_tenant_id', true), '') IS NULL
            """,
            connection
        );
        Assert.Equal(true, await command.ExecuteScalarAsync());
        command.CommandText = "SELECT count(*) FROM identity.resolve_customer_membership()";
        Assert.Equal(0L, await command.ExecuteScalarAsync());
    }

    private async Task AssertPrivilegeDeniedAsync(string role, string sql)
    {
        await using var connection = new NpgsqlConnection(AppConnectionString(role));
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        var failure = await Assert.ThrowsAsync<PostgresException>(() =>
            command.ExecuteNonQueryAsync()
        );
        Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, failure.SqlState);
    }

    private async Task<T> ActorScalarAsync<T>(
        VerifiedCustomerActor actor,
        string sql,
        Guid tenant,
        bool forgeTenant = false,
        bool mismatchTenant = false
    )
    {
        await using var connection = new NpgsqlConnection(AppConnectionString());
        await connection.OpenAsync();
        await using var transaction = await connection.BeginTransactionAsync();
        await SetActorAsync(
            connection,
            transaction,
            actor,
            forgeTenant ? tenant : null,
            mismatchTenant
        );
        await using var command = new NpgsqlCommand(sql, connection, transaction);
        command.Parameters.AddWithValue("tenant", tenant);
        return (T)(await command.ExecuteScalarAsync())!;
    }

    private async Task ActorExecuteAsync(VerifiedCustomerActor actor, string sql)
    {
        await using var connection = new NpgsqlConnection(AppConnectionString());
        await connection.OpenAsync();
        await using var transaction = await connection.BeginTransactionAsync();
        await SetActorAsync(connection, transaction, actor);
        await using var command = new NpgsqlCommand(sql, connection, transaction);
        await command.ExecuteNonQueryAsync();
        await transaction.CommitAsync();
    }

    private static async Task SetActorAsync(
        NpgsqlConnection connection,
        NpgsqlTransaction transaction,
        VerifiedCustomerActor actor,
        Guid? tenant = null,
        bool mismatchTenant = false
    )
    {
        await using var command = new NpgsqlCommand(
            """
            SELECT set_config('app.identity_issuer', @issuer, true), set_config('app.identity_subject', @subject, true),
                   set_config('app.tenant_id', @tenant, true), set_config('app.current_tenant_id', @other, true)
            """,
            connection,
            transaction
        );
        command.Parameters.AddWithValue("issuer", actor.Issuer);
        command.Parameters.AddWithValue("subject", actor.Subject);
        command.Parameters.AddWithValue("tenant", tenant?.ToString() ?? "");
        command.Parameters.AddWithValue(
            "other",
            mismatchTenant ? Guid.NewGuid().ToString() : tenant?.ToString() ?? ""
        );
        await command.ExecuteNonQueryAsync();
    }

    private sealed class CommitExpiryTimeProvider(DateTimeOffset now) : TimeProvider
    {
        private int _calls;

        public override DateTimeOffset GetUtcNow() =>
            Interlocked.Increment(ref _calls) >= 5 ? now.AddMinutes(6) : now;
    }

    private CustomerWorkspaceProvisioningService Service(
        string issuer = Issuer,
        TimeProvider? time = null
    ) =>
        new(
            new WorkspaceDbContextFactory(AppConnectionString()),
            new CustomerWorkspaceTrust(issuer, Provider, "google", Digest),
            time
        );

    private IdentityLifecycleService LifecycleService(IKeycloakIdentityLifecycleWriter writer) =>
        new(
            new WorkspaceDbContextFactory(AppConnectionString()),
            Options.Create(
                new IdentityHmacOptions
                {
                    Key = new string('k', IdentityHmacOptions.MinKeyLength),
                    ActiveVersion = "v1",
                }
            ),
            writer
        );

    private static VerifiedGoogleWorkspaceProof SyntheticProof(
        string subject,
        string providerSubject,
        string issuer = Issuer,
        DateTimeOffset? verifiedAt = null,
        DateTimeOffset? authTime = null
    )
    {
        var actor = (VerifiedCustomerActor)
            Activator.CreateInstance(
                typeof(VerifiedCustomerActor),
                BindingFlags.Instance | BindingFlags.NonPublic,
                null,
                [issuer, subject],
                null
            )!;
        return (VerifiedGoogleWorkspaceProof)
            Activator.CreateInstance(
                typeof(VerifiedGoogleWorkspaceProof),
                BindingFlags.Instance | BindingFlags.NonPublic,
                null,
                [
                    actor,
                    Provider,
                    "google",
                    providerSubject,
                    verifiedAt ?? DateTimeOffset.UtcNow,
                    authTime ?? DateTimeOffset.UtcNow,
                    Digest,
                    Guid.NewGuid(),
                ],
                null
            )!;
    }

    private async Task<Guid> SeedAsync(
        VerifiedGoogleWorkspaceProof proof,
        string businessName = "Synthetic Business",
        IdentityRegistrationState state = IdentityRegistrationState.ReadyToComplete,
        bool emailVerified = true,
        DateTimeOffset? expiresAt = null,
        string businessDomain = "Consulting"
    )
    {
        await using var db = new WorkspaceDbContextFactory(AppConnectionString()).CreateDbContext();
        await using var transaction = await db.Database.BeginTransactionAsync();
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            SELECT set_config('app.identity_issuer', {proof.Actor.Issuer}, true),
                   set_config('app.identity_subject', {proof.Actor.Subject}, true),
                   set_config('app.tenant_id', '', true), set_config('app.current_tenant_id', '', true)
            """
        );
        var registration = new IdentityRegistrationRecord
        {
            ActorIssuer = proof.Actor.Issuer,
            ActorSubject = proof.Actor.Subject,
            State = state,
            AuthenticationPath = IdentityAuthenticationPath.Google,
            ProviderIssuer = proof.ProviderIssuer,
            EmailVerified = emailVerified,
            DisplayName = "Synthetic Customer",
            BusinessName = businessName,
            BusinessDomain = businessDomain,
            LanguagePreference = "en",
            ExpiresAt = expiresAt ?? DateTimeOffset.UtcNow.AddHours(2),
        };
        db.Registrations.Add(registration);
        await db.SaveChangesAsync();
        await transaction.CommitAsync();
        return registration.RegistrationId;
    }

    private async Task CompleteAsync(VerifiedGoogleWorkspaceProof proof)
    {
        var registration = await SeedAsync(proof);
        await Service(proof.Actor.Issuer).CompleteAsync(proof, registration, Guid.NewGuid(), Hash);
    }

    private string AppConnectionString(string role = "business_app") =>
        new NpgsqlConnectionStringBuilder(_ownerConnectionString)
        {
            Username = role,
            Password = "synthetic-app-password",
            MaxPoolSize = 4,
        }.ConnectionString;

    private async Task ExecuteOwnerAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_ownerConnectionString);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private sealed class WorkspaceDbContextFactory(string connectionString)
        : IDbContextFactory<IdentityDbContext>
    {
        public IdentityDbContext CreateDbContext() =>
            new(
                new DbContextOptionsBuilder<IdentityDbContext>().UseNpgsql(connectionString).Options
            );
    }

    private sealed class SyntheticLifecycleWriter : IKeycloakIdentityLifecycleWriter
    {
        private readonly List<KeycloakFederatedBinding> _bindings = [];
        public bool IsConfigured => true;
        public int AddCount { get; private set; }
        public int RemoveCount { get; private set; }
        public bool UnknownAddCommits { get; set; }
        public bool UnknownAddDoesNotCommit { get; set; }

        public Task<bool> UserExistsAsync(string userId, CancellationToken ct) =>
            Task.FromResult(true);

        public Task<IReadOnlyList<KeycloakFederatedBinding>> ReadBindingsAsync(
            string userId,
            CancellationToken ct
        ) => Task.FromResult<IReadOnlyList<KeycloakFederatedBinding>>(_bindings.ToArray());

        public Task AddBindingAsync(
            string userId,
            KeycloakFederatedBinding binding,
            CancellationToken ct
        )
        {
            AddCount++;
            if (UnknownAddDoesNotCommit)
                throw new KeycloakLifecycleUnknownOutcomeException();
            _bindings.Add(binding);
            if (UnknownAddCommits)
            {
                UnknownAddCommits = false;
                throw new KeycloakLifecycleUnknownOutcomeException();
            }
            return Task.CompletedTask;
        }

        public Task RemoveBindingAsync(string userId, string providerAlias, CancellationToken ct)
        {
            RemoveCount++;
            _bindings.RemoveAll(binding => binding.ProviderAlias == providerAlias);
            return Task.CompletedTask;
        }
    }
}
