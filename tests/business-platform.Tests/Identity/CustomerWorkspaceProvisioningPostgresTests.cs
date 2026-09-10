// Implements: architecture/reference/product/wc085-identity-provisioning-data-contract.md CURRENT Sections 1-7
// constitutional_basis: C-005, C-007, C-026, C-059

using Microsoft.EntityFrameworkCore;
using Npgsql;
using System.Reflection;
using System.Text.Json;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class CustomerWorkspaceProvisioningPostgresTests : IAsyncLifetime
{
    private const string Issuer = "https://synthetic.invalid/realms/customer";
    private const string Provider = "https://synthetic-google.invalid";
    private const string Digest = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    private const string Hash = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("customer_workspace")
        .WithUsername("test_owner")
        .WithPassword("synthetic-workspace-test-password")
        .Build();

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        await ExecuteOwnerAsync("""
            CREATE ROLE business_app LOGIN PASSWORD 'synthetic-app-password' NOSUPERUSER NOBYPASSRLS;
            CREATE ROLE constitutional_app LOGIN PASSWORD 'synthetic-app-password' NOSUPERUSER NOBYPASSRLS;
            CREATE ROLE runtime_app LOGIN PASSWORD 'synthetic-app-password' NOSUPERUSER NOBYPASSRLS;
            CREATE ROLE wbe_app LOGIN PASSWORD 'synthetic-app-password' NOSUPERUSER NOBYPASSRLS;
            CREATE SCHEMA business AUTHORIZATION business_app;
            """);
        var canonical = await File.ReadAllTextAsync(RepositoryPaths.Resolve("infrastructure/postgres/init/03-enums-and-tables.sql"));
        foreach (var table in new[] { "organisations", "business_domain_taxonomy" })
        {
            var start = canonical.IndexOf($"CREATE TABLE business.{table} (", StringComparison.Ordinal);
            var end = canonical.IndexOf(");", start, StringComparison.Ordinal) + 2;
            await ExecuteOwnerAsync(canonical[start..end]);
        }
        var taxonomyStart = canonical.IndexOf("INSERT INTO business.business_domain_taxonomy", StringComparison.Ordinal);
        var taxonomyEnd = canonical.IndexOf(';', taxonomyStart) + 1;
        await ExecuteOwnerAsync(canonical[taxonomyStart..taxonomyEnd]);
        await ExecuteOwnerAsync(await File.ReadAllTextAsync(RepositoryPaths.Resolve("infrastructure/postgres/init/20-identity-boundary.sql")));
        await ExecuteOwnerAsync("""
            GRANT ALL ON ALL TABLES IN SCHEMA business, identity TO business_app;
            GRANT SELECT ON ALL TABLES IN SCHEMA business TO constitutional_app, runtime_app, wbe_app;
            CREATE POLICY tenant_isolation ON business.organisations USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
            INSERT INTO identity.registrations(registration_id, actor_subject, state, authentication_path, account_id)
                VALUES ('00000000-0000-0000-0000-000000000085', 'legacy', 'Completed', 'Google', gen_random_uuid());
            """);
        await ExecuteOwnerAsync(await File.ReadAllTextAsync(RepositoryPaths.Resolve("infrastructure/postgres/init/29-customer-workspace-provisioning.sql")));
    }

    public async Task DisposeAsync() => await _postgres.DisposeAsync();

    [Fact]
    public async Task Migration_RestrictedBusinessRole_EmptyContextResolvesNothing()
    {
        await using var connection = new NpgsqlConnection(AppConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand("SELECT count(*) FROM identity.resolve_customer_membership()", connection);
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

        var firstResult = await service.CompleteAsync(first, firstRegistration, Guid.NewGuid(), Hash);
        var secondResult = await service.CompleteAsync(second, secondRegistration, Guid.NewGuid(), Hash);
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
    public async Task ConstraintFailure_RollsBackWholeCohortAndEvidence_ThenRetrySucceeds()
    {
        var proof = SyntheticProof("rollback", "rollback-google");
        var registration = await SeedAsync(proof);
        var key = Guid.NewGuid();
        await ExecuteOwnerAsync("""
            ALTER TABLE identity.idempotency_ledger ADD CONSTRAINT reject_test_completion
                CHECK (operation_family <> 'CompleteRegistration');
            """);

        var failure = await Assert.ThrowsAsync<CustomerWorkspaceException>(() => Service().CompleteAsync(proof, registration, key, Hash));

        Assert.Equal(CustomerWorkspaceError.InvariantViolation, failure.Error);
        var postgres = Assert.IsType<PostgresException>(failure.InnerException);
        Assert.Equal("reject_test_completion", postgres.ConstraintName);
        await AssertCountsAsync(0, 0, 0);
        Assert.Equal(1L, await OwnerScalarAsync<long>("SELECT count(*) FROM identity.registrations WHERE state = 'ReadyToComplete' AND account_id IS NULL"));
        await ExecuteOwnerAsync("ALTER TABLE identity.idempotency_ledger DROP CONSTRAINT reject_test_completion");
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
    public async Task BusinessDomain_MapsOnlyExactActiveTaxonomy_PreservesFullSnapshot(string domain, string? expected)
    {
        var proof = SyntheticProof("domain", "domain-google");
        var registration = await SeedAsync(proof, businessDomain: domain);

        await Service().CompleteAsync(proof, registration, Guid.NewGuid(), Hash);

        Assert.Equal(expected ?? "NULL", await OwnerScalarAsync<string>("SELECT COALESCE(business_domain, 'NULL') FROM business.organisations"));
        Assert.Equal(domain, await OwnerScalarAsync<string>("SELECT completion_profile_snapshot->>'businessDomain' FROM identity.registrations WHERE actor_issuer IS NOT NULL"));
    }

    [Fact]
    public async Task ResolverDatabaseFailure_IsTypedUnavailable_AndDoesNotMutate()
    {
        var proof = SyntheticProof("resolver-failure", "resolver-failure-google");
        await ExecuteOwnerAsync("REVOKE EXECUTE ON FUNCTION identity.resolve_customer_membership() FROM business_app");
        var failure = await Assert.ThrowsAsync<CustomerWorkspaceException>(() => Service().ResolveAsync(proof.Actor));
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
        Assert.Equal("Winning Profile", await OwnerScalarAsync<string>("SELECT name FROM business.organisations"));
        Assert.Equal(1L, await OwnerScalarAsync<long>("SELECT count(DISTINCT completion_profile_snapshot) FROM identity.registrations WHERE actor_issuer IS NOT NULL"));
        await AssertCountsAsync(1, 2, 3);
        await ExecuteOwnerAsync("""
            ALTER TABLE identity.registrations DISABLE TRIGGER guard_registration_identity;
            UPDATE identity.registrations SET expires_at = now() - interval '2 days' WHERE actor_issuer IS NOT NULL;
            SET CONSTRAINTS ALL IMMEDIATE;
            ALTER TABLE identity.registrations ENABLE TRIGGER guard_registration_identity;
            UPDATE identity.idempotency_ledger SET created_at = now() - interval '3 days', expires_at = now() - interval '1 day';
            """);
        Assert.Equal(completed, await Service().CompleteAsync(proof, registration, key, Hash));
        Assert.Equal(completed, await Service().CompleteAsync(proof, registration, Guid.NewGuid(), Hash));
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

        var conflict = await Assert.ThrowsAsync<CustomerWorkspaceException>(() => Service().CompleteAsync(proof, registration, key, Digest));
        var wrongRegistration = await Assert.ThrowsAsync<CustomerWorkspaceException>(() => Service().CompleteAsync(proof, continuation, key, Hash));

        Assert.Equal(CustomerWorkspaceError.IdempotencyConflict, conflict.Error);
        Assert.Equal(409, conflict.StatusCode);
        Assert.Equal(CustomerWorkspaceError.IdempotencyConflict, wrongRegistration.Error);
        await AssertCountsAsync(1, 1, 1);
        Assert.Equal(1L, await OwnerScalarAsync<long>("SELECT count(*) FROM identity.registrations WHERE state = 'ReadyToComplete'"));
    }

    [Theory]
    [InlineData(false, false)]
    [InlineData(false, true)]
    [InlineData(true, true)]
    public async Task ConcurrentSameActor_OneCohortAndImmutableWinner(bool differentRegistrations, bool differentKeys)
    {
        var proof = SyntheticProof("race", "race-google");
        var firstRegistration = await SeedAsync(proof, "First Profile");
        var secondRegistration = differentRegistrations ? await SeedAsync(proof, "Second Profile") : firstRegistration;
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
        Assert.Equal(1L, await OwnerScalarAsync<long>("SELECT count(DISTINCT completion_profile_snapshot) FROM identity.registrations WHERE actor_issuer IS NOT NULL"));
    }

    [Fact]
    public async Task ConcurrentDifferentActorsSameProvider_OneWinner_OtherRequiresUnresolvedRecovery()
    {
        var first = SyntheticProof("race-actor-one", "same-provider");
        var second = SyntheticProof("race-actor-two", "same-provider");
        var firstRegistration = await SeedAsync(first);
        var secondRegistration = await SeedAsync(second);
        var start = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        async Task<(CustomerWorkspaceCompletion? Result, CustomerWorkspaceException? Failure)> Complete(VerifiedGoogleWorkspaceProof proof, Guid registration)
        {
            await start.Task;
            try { return (await Service().CompleteAsync(proof, registration, Guid.NewGuid(), Hash), null); }
            catch (CustomerWorkspaceException failure) { return (null, failure); }
        }
        var firstTask = Complete(first, firstRegistration);
        var secondTask = Complete(second, secondRegistration);

        start.SetResult();
        var outcomes = await Task.WhenAll(firstTask, secondTask);

        Assert.Single(outcomes, outcome => outcome.Result is not null);
        var failed = Assert.Single(outcomes, outcome => outcome.Failure is not null);
        Assert.Equal(CustomerWorkspaceError.RecoveryRequired, failed.Failure!.Error);
        var losingActor = outcomes[0].Failure is not null ? first.Actor : second.Actor;
        var denied = await Assert.ThrowsAsync<CustomerWorkspaceException>(() => Service().ResolveAsync(losingActor));
        Assert.Equal(CustomerWorkspaceError.MembershipRequired, denied.Error);
        await AssertCountsAsync(1, 1, 1);
    }

    [Theory]
    [InlineData("CaseSubject", Issuer + "/other")]
    [InlineData("casesubject", Issuer)]
    [InlineData("CaseSubject", "https://synthetic.invalid/realms/Customer")]
    public async Task ExactIssuerSubjectBinding_NoCrossRegistrationOrResourceAccess(string secondSubject, string secondIssuer)
    {
        var first = SyntheticProof("CaseSubject", "first-exact-google");
        var second = SyntheticProof(secondSubject, "second-exact-google", secondIssuer);
        var firstRegistration = await SeedAsync(first);
        var secondRegistration = await SeedAsync(second);
        await Service().CompleteAsync(first, firstRegistration, Guid.NewGuid(), Hash);
        await Service(secondIssuer).CompleteAsync(second, secondRegistration, Guid.NewGuid(), Hash);
        var firstMembership = await Service().ResolveAsync(first.Actor);
        var secondMembership = await Service(secondIssuer).ResolveAsync(second.Actor);

        var denied = await Assert.ThrowsAsync<CustomerWorkspaceException>(() => Service(secondIssuer).CompleteAsync(second, firstRegistration, Guid.NewGuid(), Hash));
        Assert.Equal(CustomerWorkspaceError.RegistrationNotFound, denied.Error);
        Assert.NotEqual(firstMembership.AccountId, secondMembership.AccountId);
        Assert.Equal(0L, await ActorScalarAsync<long>(second.Actor,
            "SELECT count(*) FROM business.organisations WHERE tenant_id = @tenant", firstMembership.TenantId));
        Assert.Equal(0L, await ActorScalarAsync<long>(second.Actor,
            "SELECT count(*) FROM business.organisations", firstMembership.TenantId, forgeTenant: true));
        Assert.Equal(1L, await ActorScalarAsync<long>(second.Actor,
            "SELECT count(*) FROM business.organisations", secondMembership.TenantId, forgeTenant: true));
        Assert.Equal(0L, await ActorScalarAsync<long>(second.Actor,
            "SELECT count(*) FROM business.organisations", secondMembership.TenantId, forgeTenant: true, mismatchTenant: true));
        await AssertCountsAsync(2, 2, 2);
    }

    [Theory]
    [InlineData("constitutional_app")]
    [InlineData("runtime_app")]
    [InlineData("wbe_app")]
    public async Task ReceiverRoles_ResolverOnly_NoIdentityTableWriteSchemaOrOwnerAccess(string role)
    {
        var proof = SyntheticProof("role-customer", "role-google");
        var registration = await SeedAsync(proof);
        var result = await Service().CompleteAsync(proof, registration, Guid.NewGuid(), Hash);
        await using var connection = new NpgsqlConnection(AppConnectionString(role));
        await connection.OpenAsync();
        await using var transaction = await connection.BeginTransactionAsync();
        await SetActorAsync(connection, transaction, proof.Actor);
        await using var command = new NpgsqlCommand("SELECT account_id FROM identity.resolve_customer_membership()", connection, transaction);
        Assert.Equal(result.Result.AccountReference, await command.ExecuteScalarAsync());
        await transaction.RollbackAsync();

        foreach (var sql in new[]
        {
            "SELECT * FROM identity.accounts", "SELECT * FROM identity.registrations",
            "INSERT INTO identity.memberships DEFAULT VALUES", "UPDATE identity.memberships SET status = 'INACTIVE'",
            "CREATE TABLE identity.forbidden(value int)", "CREATE TABLE business.forbidden(value int)",
            "CREATE TABLE public.forbidden(value int)", "SET ROLE identity_resolver_owner",
            "SELECT identity.guard_registration_identity()", "SELECT identity.assert_completed_cohort()",
        }) await AssertPrivilegeDeniedAsync(role, sql);
    }

    [Fact]
    public async Task BusinessRoleAndResolverOwner_HaveOnlyBoundedPrivileges()
    {
        foreach (var sql in new[]
        {
            "UPDATE identity.accounts SET status = 'INACTIVE'", "DELETE FROM identity.actor_bindings",
            "UPDATE identity.idempotency_ledger SET status_code = 200", "DELETE FROM identity.registration_events",
            "TRUNCATE identity.memberships", "UPDATE identity.registrations SET actor_subject = 'different'",
            "UPDATE identity.registrations SET provider_issuer = 'different'", "UPDATE business.organisations SET identity_status = 'ACTIVE'",
            "CREATE TABLE identity.forbidden(value int)", "CREATE TABLE business.forbidden(value int)",
            "CREATE TABLE public.forbidden(value int)", "SET ROLE identity_resolver_owner",
        }) await AssertPrivilegeDeniedAsync("business_app", sql);
        Assert.False(await OwnerScalarAsync<bool>("SELECT rolcanlogin OR rolsuper OR rolbypassrls OR rolcreaterole FROM pg_roles WHERE rolname = 'identity_resolver_owner'"));
        Assert.False(await OwnerScalarAsync<bool>("SELECT has_column_privilege('identity_resolver_owner', 'identity.actor_bindings', 'trust_config_digest', 'SELECT')"));
        Assert.False(await OwnerScalarAsync<bool>("SELECT has_schema_privilege('identity_resolver_owner', 'identity', 'CREATE')"));
        Assert.Equal(8L, await OwnerScalarAsync<long>("""
            SELECT count(*) FROM pg_class AS relation JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
            WHERE relation.relrowsecurity AND relation.relforcerowsecurity AND (
                namespace.nspname = 'identity' AND relation.relname IN
                    ('accounts','login_methods','actor_bindings','memberships','registrations','registration_events','idempotency_ledger')
                OR namespace.nspname = 'business' AND relation.relname = 'organisations')
            """));
        await using var owner = new NpgsqlConnection(_postgres.GetConnectionString());
        await owner.OpenAsync();
        await using var command = new NpgsqlCommand("SET ROLE identity_resolver_owner", owner);
        await command.ExecuteNonQueryAsync();
        command.CommandText = "SELECT trust_config_digest FROM identity.actor_bindings";
        Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, (await Assert.ThrowsAsync<PostgresException>(() => command.ExecuteScalarAsync())).SqlState);
        command.CommandText = "INSERT INTO identity.memberships DEFAULT VALUES";
        Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, (await Assert.ThrowsAsync<PostgresException>(() => command.ExecuteNonQueryAsync())).SqlState);
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
        await using var command = new NpgsqlCommand("""
            SELECT set_config('app.identity_issuer', '', true), set_config('app.identity_subject', '', true),
                   set_config('app.tenant_id', @tenant, true), set_config('app.current_tenant_id', @tenant, true)
            """, connection, transaction);
        command.Parameters.AddWithValue("tenant", membership.TenantId.ToString());
        await command.ExecuteNonQueryAsync();
        foreach (var sql in new[] { "SELECT count(*) FROM identity.resolve_customer_membership()", "SELECT count(*) FROM business.organisations", "SELECT count(*) FROM identity.accounts" })
        {
            command.CommandText = sql;
            Assert.Equal(0L, await command.ExecuteScalarAsync());
        }
        await transaction.RollbackAsync();
        await using var db = new WorkspaceDbContextFactory(AppConnectionString()).CreateDbContext();
        await using var actorTransaction = await db.Database.BeginTransactionAsync();
        await db.Database.ExecuteSqlInterpolatedAsync($"""
            SELECT set_config('app.identity_issuer', {proof.Actor.Issuer}, true),
                   set_config('app.identity_subject', {proof.Actor.Subject}, true),
                   set_config('app.tenant_id', '', true), set_config('app.current_tenant_id', '', true)
            """);
        var foreignTenant = Guid.NewGuid();
        var denied = await Assert.ThrowsAsync<PostgresException>(() => db.Database.ExecuteSqlInterpolatedAsync($"""
            INSERT INTO business.organisations(id, tenant_id, name, identity_managed, identity_status)
                VALUES ({foreignTenant}, {foreignTenant}, 'Unbound', true, 'ACTIVE')
            """));
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
        await ExecuteOwnerAsync(inactive switch
        {
            "membership" => "UPDATE identity.memberships SET status = 'INACTIVE'",
            "account" => "UPDATE identity.accounts SET status = 'INACTIVE'",
            "organisation" => "UPDATE business.organisations SET identity_status = 'INACTIVE'",
            "actor" => "UPDATE identity.actor_bindings SET status = 'RETIRED'",
            _ => "UPDATE identity.login_methods SET status = 'RETIRED'",
        });

        var lookup = await Assert.ThrowsAsync<CustomerWorkspaceException>(() => Service().ResolveAsync(proof.Actor));
        var replay = await Assert.ThrowsAsync<CustomerWorkspaceException>(() => Service().CompleteAsync(proof, registration, key, Hash));

        Assert.Equal(CustomerWorkspaceError.MembershipRequired, lookup.Error);
        Assert.Contains(replay.Error, new[] { CustomerWorkspaceError.MembershipRequired, CustomerWorkspaceError.RecoveryRequired });
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
            "old-auth" => SyntheticProof("proof", "proof-google", authTime: DateTimeOffset.UtcNow.AddMinutes(-6)),
            "old-proof" => SyntheticProof("proof", "proof-google", verifiedAt: DateTimeOffset.UtcNow.AddMinutes(-6), authTime: DateTimeOffset.UtcNow.AddMinutes(-6)),
            "future" => SyntheticProof("proof", "proof-google", authTime: DateTimeOffset.UtcNow.AddMinutes(1)),
            "wrong-issuer" => SyntheticProof("proof", "proof-google", Issuer + "/wrong"),
            "empty-provider" => SyntheticProof("proof", ""),
            "oversize" => SyntheticProof("proof", new string('a', 257)),
            "nul" => SyntheticProof("proof", "provider\0subject"),
            _ => SyntheticProof("proof", "provider\ud800subject"),
        };

        var failure = await Assert.ThrowsAsync<CustomerWorkspaceException>(() => Service().CompleteAsync(proof, registration, Guid.NewGuid(), Hash));

        Assert.Contains(failure.Error, new[] { CustomerWorkspaceError.ProofRequired, CustomerWorkspaceError.FreshAuthenticationRequired });
        await AssertCountsAsync(0, 0, 0);
    }

    [Fact]
    public async Task ProofAgesOutBeforeCommit_RollsBackAllWrites()
    {
        var proof = SyntheticProof("aging", "aging-google");
        var registration = await SeedAsync(proof);
        var clock = new CommitExpiryTimeProvider(DateTimeOffset.UtcNow);

        var failure = await Assert.ThrowsAsync<CustomerWorkspaceException>(() => Service(time: clock).CompleteAsync(proof, registration, Guid.NewGuid(), Hash));

        Assert.Equal(CustomerWorkspaceError.FreshAuthenticationRequired, failure.Error);
        await AssertCountsAsync(0, 0, 0);
        Assert.Equal(1L, await OwnerScalarAsync<long>("SELECT count(*) FROM identity.registrations WHERE state = 'ReadyToComplete' AND account_id IS NULL"));
    }

    [Theory]
    [InlineData(IdentityRegistrationState.Cancelled, true, false)]
    [InlineData(IdentityRegistrationState.ReadyToComplete, false, false)]
    [InlineData(IdentityRegistrationState.ReadyToComplete, true, true)]
    [InlineData(IdentityRegistrationState.ProfileCompletionRequired, true, false)]
    public async Task IneligibleRegistration_Denies(IdentityRegistrationState state, bool emailVerified, bool expired)
    {
        var proof = SyntheticProof("ineligible", "ineligible-google");
        var registration = await SeedAsync(proof, state: state, emailVerified: emailVerified,
            expiresAt: expired ? DateTimeOffset.UtcNow.AddMinutes(-1) : null);

        var failure = await Assert.ThrowsAsync<CustomerWorkspaceException>(() => Service().CompleteAsync(proof, registration, Guid.NewGuid(), Hash));

        Assert.Equal(CustomerWorkspaceError.RegistrationIneligible, failure.Error);
        await AssertCountsAsync(0, 0, 0);
    }

    [Fact]
    public async Task LegacyCompletedRows_AreRetainedButCannotResolveOrReplay_AndNewNullIssuerDenied()
    {
        var proof = SyntheticProof("legacy", "legacy-google");
        var failure = await Assert.ThrowsAsync<CustomerWorkspaceException>(() => Service().CompleteAsync(proof,
            Guid.Parse("00000000-0000-0000-0000-000000000085"), Guid.NewGuid(), Hash));
        Assert.Equal(CustomerWorkspaceError.RegistrationNotFound, failure.Error);
        Assert.Equal(CustomerWorkspaceError.MembershipRequired,
            (await Assert.ThrowsAsync<CustomerWorkspaceException>(() => Service().ResolveAsync(proof.Actor))).Error);
        Assert.Equal(1L, await OwnerScalarAsync<long>("SELECT count(*) FROM identity.registrations WHERE actor_issuer IS NULL AND state = 'Completed'"));
        var invalid = await Assert.ThrowsAsync<PostgresException>(() => ExecuteOwnerAsync("""
            INSERT INTO identity.registrations(actor_subject, authentication_path) VALUES ('unknown', 'Google')
            """));
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
        var failed = await Assert.ThrowsAsync<PostgresException>(() => db.Database.ExecuteSqlInterpolatedAsync(
            $"UPDATE identity.registrations SET business_name = 'Overwrite' WHERE registration_id = {registration}"));
        Assert.Equal(PostgresErrorCodes.CheckViolation, failed.SqlState);
        await transaction.RollbackAsync();
        await AssertCountsAsync(1, 1, 1);
        var incomplete = await Assert.ThrowsAsync<PostgresException>(() => ExecuteOwnerAsync("""
            INSERT INTO identity.registrations(actor_issuer, actor_subject, authentication_path, state)
                VALUES ('synthetic', 'unproven', 'Google', 'Completed')
            """));
        Assert.Equal("registrations_completed_identity_check", incomplete.ConstraintName);
    }

    [Fact]
    public async Task PooledConnectionContext_ResetsAfterSuccessAndRollback_ResolverSetsBothTenantValues()
    {
        var proof = SyntheticProof("pool", "pool-google");
        var registration = await SeedAsync(proof);
        var pool = new NpgsqlConnectionStringBuilder(AppConnectionString()) { MaxPoolSize = 1 }.ConnectionString;
        var service = new CustomerWorkspaceProvisioningService(new WorkspaceDbContextFactory(pool),
            new CustomerWorkspaceTrust(Issuer, Provider, "google", Digest));
        await service.CompleteAsync(proof, registration, Guid.NewGuid(), Hash);
        var live = await service.ResolveAsync(proof.Actor);
        await AssertPoolEmptyAsync(pool);
        await using (var db = new WorkspaceDbContextFactory(pool).CreateDbContext())
        {
            await using var transaction = await db.Database.BeginTransactionAsync();
            await db.Database.ExecuteSqlRawAsync("""
                SELECT set_config('app.identity_issuer', 'wrong', true), set_config('app.identity_subject', 'wrong', true),
                       set_config('app.tenant_id', 'not-a-uuid', true), set_config('app.current_tenant_id', 'not-a-uuid', true)
                """);
            var resolved = await service.ResolveInTransactionAsync(db, proof.Actor);
            Assert.Equal(live.AccountId, resolved.AccountId);
            Assert.Equal(live.TenantId, resolved.TenantId);
            Assert.Equal(1, await db.Organisations.CountAsync());
            var forced = await Assert.ThrowsAsync<PostgresException>(() => db.Database.ExecuteSqlRawAsync("SELECT 1 / 0"));
            Assert.Equal(PostgresErrorCodes.DivisionByZero, forced.SqlState);
        }
        await AssertPoolEmptyAsync(pool);
        var other = SyntheticProof("other-pool-user", "other-pool-google");
        Assert.Equal(CustomerWorkspaceError.MembershipRequired,
            (await Assert.ThrowsAsync<CustomerWorkspaceException>(() => service.ResolveAsync(other.Actor))).Error);
        await AssertPoolEmptyAsync(pool);
        await using var noTransaction = new WorkspaceDbContextFactory(pool).CreateDbContext();
        await Assert.ThrowsAsync<InvalidOperationException>(() => service.ResolveInTransactionAsync(noTransaction, proof.Actor));
        Assert.Empty(typeof(VerifiedGoogleWorkspaceProof).GetConstructors());
        Assert.Empty(typeof(VerifiedCustomerActor).GetConstructors());
        Assert.Throws<NotSupportedException>(() => JsonSerializer.Deserialize<VerifiedCustomerActor>("{\"issuer\":\"forged\",\"subject\":\"forged\"}"));
    }

    private async Task AssertCountsAsync(long cohorts, long events, long entries)
    {
        foreach (var table in new[] { "identity.accounts", "identity.actor_bindings", "identity.login_methods", "identity.memberships", "business.organisations" })
            Assert.Equal(cohorts, await OwnerScalarAsync<long>($"SELECT count(*) FROM {table}"));
        Assert.Equal(events, await OwnerScalarAsync<long>("SELECT count(*) FROM identity.registration_events"));
        Assert.Equal(entries, await OwnerScalarAsync<long>("SELECT count(*) FROM identity.idempotency_ledger"));
    }

    private async Task<T> OwnerScalarAsync<T>(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        return (T)(await command.ExecuteScalarAsync())!;
    }

    private async Task AssertPoolEmptyAsync(string? connectionString = null)
    {
        await using var connection = new NpgsqlConnection(connectionString ?? AppConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand("""
            SELECT NULLIF(current_setting('app.identity_issuer', true), '') IS NULL
               AND NULLIF(current_setting('app.identity_subject', true), '') IS NULL
               AND NULLIF(current_setting('app.tenant_id', true), '') IS NULL
               AND NULLIF(current_setting('app.current_tenant_id', true), '') IS NULL
            """, connection);
        Assert.Equal(true, await command.ExecuteScalarAsync());
        command.CommandText = "SELECT count(*) FROM identity.resolve_customer_membership()";
        Assert.Equal(0L, await command.ExecuteScalarAsync());
    }

    private async Task AssertPrivilegeDeniedAsync(string role, string sql)
    {
        await using var connection = new NpgsqlConnection(AppConnectionString(role));
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        var failure = await Assert.ThrowsAsync<PostgresException>(() => command.ExecuteNonQueryAsync());
        Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, failure.SqlState);
    }

    private async Task<T> ActorScalarAsync<T>(VerifiedCustomerActor actor, string sql, Guid tenant,
        bool forgeTenant = false, bool mismatchTenant = false)
    {
        await using var connection = new NpgsqlConnection(AppConnectionString());
        await connection.OpenAsync();
        await using var transaction = await connection.BeginTransactionAsync();
        await SetActorAsync(connection, transaction, actor, forgeTenant ? tenant : null, mismatchTenant);
        await using var command = new NpgsqlCommand(sql, connection, transaction);
        command.Parameters.AddWithValue("tenant", tenant);
        return (T)(await command.ExecuteScalarAsync())!;
    }

    private static async Task SetActorAsync(NpgsqlConnection connection, NpgsqlTransaction transaction,
        VerifiedCustomerActor actor, Guid? tenant = null, bool mismatchTenant = false)
    {
        await using var command = new NpgsqlCommand("""
            SELECT set_config('app.identity_issuer', @issuer, true), set_config('app.identity_subject', @subject, true),
                   set_config('app.tenant_id', @tenant, true), set_config('app.current_tenant_id', @other, true)
            """, connection, transaction);
        command.Parameters.AddWithValue("issuer", actor.Issuer);
        command.Parameters.AddWithValue("subject", actor.Subject);
        command.Parameters.AddWithValue("tenant", tenant?.ToString() ?? "");
        command.Parameters.AddWithValue("other", mismatchTenant ? Guid.NewGuid().ToString() : tenant?.ToString() ?? "");
        await command.ExecuteNonQueryAsync();
    }

    private sealed class CommitExpiryTimeProvider(DateTimeOffset now) : TimeProvider
    {
        private int _calls;
        public override DateTimeOffset GetUtcNow() => Interlocked.Increment(ref _calls) >= 5 ? now.AddMinutes(6) : now;
    }

    private CustomerWorkspaceProvisioningService Service(string issuer = Issuer, TimeProvider? time = null) =>
        new(new WorkspaceDbContextFactory(AppConnectionString()), new CustomerWorkspaceTrust(issuer, Provider, "google", Digest), time);

    private static VerifiedGoogleWorkspaceProof SyntheticProof(string subject, string providerSubject, string issuer = Issuer,
        DateTimeOffset? verifiedAt = null, DateTimeOffset? authTime = null)
    {
        var actor = (VerifiedCustomerActor)Activator.CreateInstance(typeof(VerifiedCustomerActor),
            BindingFlags.Instance | BindingFlags.NonPublic, null, [issuer, subject], null)!;
        return (VerifiedGoogleWorkspaceProof)Activator.CreateInstance(typeof(VerifiedGoogleWorkspaceProof),
            BindingFlags.Instance | BindingFlags.NonPublic, null,
            [actor, Provider, "google", providerSubject, verifiedAt ?? DateTimeOffset.UtcNow,
                authTime ?? DateTimeOffset.UtcNow, Digest, Guid.NewGuid()], null)!;
    }

    private async Task<Guid> SeedAsync(VerifiedGoogleWorkspaceProof proof, string businessName = "Synthetic Business",
        IdentityRegistrationState state = IdentityRegistrationState.ReadyToComplete, bool emailVerified = true,
        DateTimeOffset? expiresAt = null, string businessDomain = "Consulting")
    {
        await using var db = new WorkspaceDbContextFactory(AppConnectionString()).CreateDbContext();
        await using var transaction = await db.Database.BeginTransactionAsync();
        await db.Database.ExecuteSqlInterpolatedAsync($"""
            SELECT set_config('app.identity_issuer', {proof.Actor.Issuer}, true),
                   set_config('app.identity_subject', {proof.Actor.Subject}, true),
                   set_config('app.tenant_id', '', true), set_config('app.current_tenant_id', '', true)
            """);
        var registration = new IdentityRegistrationRecord
        {
            ActorIssuer = proof.Actor.Issuer, ActorSubject = proof.Actor.Subject, State = state,
            AuthenticationPath = IdentityAuthenticationPath.Google, ProviderIssuer = proof.ProviderIssuer,
            EmailVerified = emailVerified, DisplayName = "Synthetic Customer", BusinessName = businessName,
            BusinessDomain = businessDomain, LanguagePreference = "en", ExpiresAt = expiresAt ?? DateTimeOffset.UtcNow.AddHours(2),
        };
        db.Registrations.Add(registration);
        await db.SaveChangesAsync();
        await transaction.CommitAsync();
        return registration.RegistrationId;
    }

    private string AppConnectionString(string role = "business_app") => new NpgsqlConnectionStringBuilder(_postgres.GetConnectionString())
    {
        Username = role,
        Password = "synthetic-app-password",
        MaxPoolSize = 4,
    }.ConnectionString;

    private async Task ExecuteOwnerAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private sealed class WorkspaceDbContextFactory(string connectionString) : IDbContextFactory<IdentityDbContext>
    {
        public IdentityDbContext CreateDbContext() =>
            new(new DbContextOptionsBuilder<IdentityDbContext>().UseNpgsql(connectionString).Options);
    }
}