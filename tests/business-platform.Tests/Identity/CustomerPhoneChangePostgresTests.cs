using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class CustomerPhoneChangeSchemaFixture : IAsyncLifetime
{
    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("waooaw")
        .WithUsername("waooaw")
        .WithPassword("synthetic-phone-owner")
        .WithResourceMapping(
            new DirectoryInfo(
                Path.GetDirectoryName(
                    RepositoryPaths.Resolve("infrastructure/postgres/init/01-schemas.sql")
                )!
            ),
            "/docker-entrypoint-initdb.d"
        )
        .Build();

    public string OwnerConnection => _postgres.GetConnectionString();
    public string AppConnection =>
        new NpgsqlConnectionStringBuilder(OwnerConnection)
        {
            Username = "business_app",
            Password = "synthetic-phone-app",
        }.ConnectionString;

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        await ExecuteAsync("ALTER ROLE business_app PASSWORD 'synthetic-phone-app'");
    }

    public async Task ExecuteAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(OwnerConnection);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    public async Task DisposeAsync() => await _postgres.DisposeAsync();
}

public sealed class CustomerPhoneChangePostgresTests(CustomerPhoneChangeSchemaFixture schema)
    : IClassFixture<CustomerPhoneChangeSchemaFixture>
{
    private static int _sequence;
    private const string Issuer = "https://synthetic.invalid/customer-phone-change";
    private readonly VerificationDispatcher _delivery = new();
    private readonly EvidenceGateway _evidence = new();
    private IdentityService Service =>
        new(
            new Factory(schema.AppConnection),
            Options.Create(new IdentityHmacOptions { Key = IdentityTestHelpers.TestHmacKey }),
            _delivery,
            _evidence
        );

    [Fact]
    public async Task RuntimeIdentityRepairMigrationIsReplayableAndPreservesLinkSourceColumns()
    {
        var migration = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/96-wc134-runtime-identity-row-lock-policy.sql"
            )
        );
        await schema.ExecuteAsync(migration);
        await schema.ExecuteAsync(migration);
        await using var connection = new NpgsqlConnection(schema.OwnerConnection);
        await connection.OpenAsync();
        foreach (
            var (column, writable) in new[]
            {
                ("actor_subject", false),
                ("tenant_id", false),
                ("verified_mobile_proof_id", false),
                ("start_evidence_id", false),
                ("state", true),
                ("approval_evidence_id", true),
                ("cancellation_evidence_id", true),
                ("confirmation_evidence_id", true),
                ("confirmation_message_digest", true),
                ("confirmed_phone_subject_hash", true),
                ("confirmed_at", true),
                ("updated_at", true),
            }
        )
        {
            await using var command = new NpgsqlCommand(
                """
                SELECT has_column_privilege(
                    'business_app', 'identity.account_links', @column, 'UPDATE')
                """,
                connection
            );
            command.Parameters.AddWithValue("column", column);
            Assert.Equal(writable, await command.ExecuteScalarAsync());
        }
    }

    [Fact]
    public async Task RuntimeIdentityOwnerCanLockCurrentOrganisationButCannotModifyIt()
    {
        var owner = await SeedAsync();
        var other = await SeedAsync();
        await using var connection = new NpgsqlConnection(schema.OwnerConnection);
        await connection.OpenAsync();
        await using var transaction = await connection.BeginTransactionAsync();
        await using var context = new NpgsqlCommand(
            """
            SET LOCAL ROLE identity_resolver_owner;
            SELECT set_config('app.identity_issuer', @issuer, true),
                set_config('app.identity_subject', @subject, true),
                set_config('app.current_tenant_id', @tenant::text, true);
            """,
            connection,
            transaction
        );
        context.Parameters.AddWithValue("issuer", Issuer);
        context.Parameters.AddWithValue("subject", owner.Actor.Subject);
        context.Parameters.AddWithValue("tenant", owner.Membership.TenantId);
        await context.ExecuteNonQueryAsync();
        await using var read = new NpgsqlCommand(
            "SELECT tenant_id FROM business.organisations WHERE tenant_id = @tenant FOR SHARE",
            connection,
            transaction
        );
        read.Parameters.AddWithValue("tenant", owner.Membership.TenantId);
        Assert.Equal(owner.Membership.TenantId, await read.ExecuteScalarAsync());
        read.Parameters["tenant"].Value = other.Membership.TenantId;
        Assert.Null(await read.ExecuteScalarAsync());
        context.Parameters["subject"].Value = other.Actor.Subject;
        await context.ExecuteNonQueryAsync();
        read.Parameters["tenant"].Value = owner.Membership.TenantId;
        Assert.Null(await read.ExecuteScalarAsync());
        context.Parameters["subject"].Value = owner.Actor.Subject;
        await context.ExecuteNonQueryAsync();
        await using var write = new NpgsqlCommand(
            "UPDATE business.organisations SET identity_status = 'ACTIVE' WHERE tenant_id = @tenant",
            connection,
            transaction
        );
        write.Parameters.AddWithValue("tenant", owner.Membership.TenantId);
        var denied = await Assert.ThrowsAsync<PostgresException>(() =>
            write.ExecuteNonQueryAsync()
        );
        Assert.Equal("42501", denied.SqlState);
        await transaction.RollbackAsync();
    }

    [Theory]
    [InlineData("phone")]
    [InlineData("profile")]
    [InlineData("snapshot")]
    [InlineData("identity")]
    public async Task CompletedRegistrationCannotChangeWithoutCompletedPhoneProof(string field)
    {
        var owner = await SeedAsync();
        await using var connection = new NpgsqlConnection(schema.AppConnection);
        await connection.OpenAsync();
        await using var transaction = await connection.BeginTransactionAsync();
        await ApplyOwnerContextAsync(connection, transaction, owner);
        var sql = field switch
        {
            "phone" =>
                "UPDATE identity.registrations SET mobile_hmac_key = repeat('d',32) WHERE registration_id = @registration",
            "profile" =>
                "UPDATE identity.registrations SET business_name = 'Changed' WHERE registration_id = @registration",
            "snapshot" =>
                "UPDATE identity.registrations SET completion_profile_snapshot = '{}'::jsonb WHERE registration_id = @registration",
            "identity" =>
                "UPDATE identity.registrations SET account_id = gen_random_uuid() WHERE registration_id = @registration",
            _ => throw new ArgumentOutOfRangeException(nameof(field)),
        };
        await using var update = new NpgsqlCommand(sql, connection, transaction);
        update.Parameters.AddWithValue("registration", owner.RegistrationId);
        var denied = await Assert.ThrowsAsync<PostgresException>(() =>
            update.ExecuteNonQueryAsync()
        );
        Assert.Equal("23514", denied.SqlState);
        await transaction.RollbackAsync();
    }

    [Theory]
    [InlineData(31)]
    [InlineData(33)]
    [InlineData(64)]
    public async Task PhoneConflictOwnerRejectsNoncanonicalIdentityMatchLength(int length)
    {
        var owner = await SeedAsync();
        await using var connection = new NpgsqlConnection(schema.AppConnection);
        await connection.OpenAsync();
        await using var transaction = await connection.BeginTransactionAsync();
        await ApplyOwnerContextAsync(connection, transaction, owner);
        await using var query = new NpgsqlCommand(
            "SELECT identity.phone_change_conflicts(@account, @candidates::jsonb)",
            connection,
            transaction
        );
        query.Parameters.AddWithValue("account", owner.Membership.AccountId);
        query.Parameters.AddWithValue(
            "candidates",
            JsonSerializer.Serialize(
                new Dictionary<string, string> { ["v1"] = new string('a', length) }
            )
        );
        var denied = await Assert.ThrowsAsync<PostgresException>(() => query.ExecuteScalarAsync());
        Assert.Equal("42501", denied.SqlState);
        await transaction.RollbackAsync();
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Confirm_AtomicallyRevokesOldLinksAndChannels_WithoutRetargetingPendingOrUnknownWork(
        bool legacyQualifiedLink
    )
    {
        var owner = await SeedAsync(legacyQualifiedLink);
        Assert.Equal(
            owner.SenderHash,
            await Service.GetConfirmedPhoneSubjectHashAsync(
                owner.LinkId,
                owner.Actor.Subject,
                owner.Membership.TenantId,
                CancellationToken.None,
                owner.Actor,
                owner.Membership
            )
        );
        var newNumber = Number();
        var startKey = Guid.NewGuid();
        var challenge = await Service.StartPhoneChangeAsync(
            owner.Actor,
            owner.Membership,
            newNumber,
            startKey,
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );
        var code = _delivery.LastCode;
        var replay = await Service.StartPhoneChangeAsync(
            owner.Actor,
            owner.Membership,
            newNumber,
            startKey,
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );
        Assert.Equal(challenge.ChallengeId, replay.ChallengeId);
        Assert.Equal(1, _delivery.Sends);
        var confirmKey = Guid.NewGuid();
        var confirmed = await Service.ConfirmPhoneChangeAsync(
            owner.Actor,
            owner.Membership,
            challenge.ChallengeId,
            code,
            true,
            confirmKey,
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );
        Assert.Equal("COMPLETED", confirmed.State);
        Assert.True(confirmed.RelationshipApprovalRequired);
        var recovered = await Service.ConfirmPhoneChangeAsync(
            owner.Actor,
            owner.Membership,
            challenge.ChallengeId,
            code,
            true,
            confirmKey,
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );
        Assert.Equal(confirmed, recovered);
        await using var db = OwnerDb();
        var registration = await db.Registrations.SingleAsync(v =>
            v.RegistrationId == owner.RegistrationId
        );
        Assert.Equal(
            Service.ComputeMatchCandidates("mobile", newNumber)["v1"],
            registration.MobileHmacKey
        );
        Assert.Equal(owner.Membership.AccountId, registration.AccountId);
        Assert.All(
            await db.AccountLinks.Where(v => v.ActorSubject == owner.Actor.Subject).ToListAsync(),
            link => Assert.Equal(IdentityAccountLinkState.Cancelled, link.State)
        );
        await using var relationships = new EmploymentRelationshipDbContext(
            new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                .UseNpgsql(schema.OwnerConnection)
                .Options
        );
        var binding = await relationships.ChannelBindings.SingleAsync(v =>
            v.BindingId == owner.BindingId
        );
        Assert.Equal("REVOKED", binding.Status);
        Assert.Equal(owner.SenderHash, binding.ExternalSubjectHash);
        Assert.NotNull(binding.RevokedEvidenceId);
        await using var connection = new NpgsqlConnection(schema.OwnerConnection);
        await connection.OpenAsync();
        await using var unchanged = new NpgsqlCommand(
            "SELECT state, recipient_binding_digest FROM business.conversation_outbox WHERE relationship_id = @relationship ORDER BY sequence",
            connection
        );
        unchanged.Parameters.AddWithValue("relationship", owner.RelationshipId);
        await using var reader = await unchanged.ExecuteReaderAsync();
        foreach (var expected in new[] { "PENDING", "UNRESOLVED" })
        {
            Assert.True(await reader.ReadAsync());
            Assert.Equal(expected, reader.GetString(0));
            Assert.Equal(owner.SenderHash, reader.GetString(1));
        }
        Assert.False(await reader.ReadAsync());
        var linked = await Service.StartAccountLinkAsync(
            owner.Actor.Subject,
            owner.Membership.TenantId,
            Guid.NewGuid(),
            "synthetic-new-link-request",
            Guid.Empty,
            DateTimeOffset.UtcNow,
            CancellationToken.None,
            owner.Actor,
            owner.Membership
        );
        Assert.Equal(IdentityAccountLinkState.PendingPortalApproval, linked.link.State);
        Assert.Equal(challenge.ChallengeId, linked.link.VerifiedMobileProofId);
    }

    [Theory]
    [InlineData(-6)]
    [InlineData(1)]
    public async Task StaleOrFutureAuthentication_DoesNotSendOtp(int minutes)
    {
        var owner = await SeedAsync();
        await Assert.ThrowsAsync<IdentityStepUpRequiredException>(() =>
            Service.StartPhoneChangeAsync(
                owner.Actor,
                owner.Membership,
                Number(),
                Guid.NewGuid(),
                DateTimeOffset.UtcNow.AddMinutes(minutes),
                CancellationToken.None
            )
        );
        Assert.Equal(0, _delivery.Sends);
    }

    [Fact]
    public async Task FiveWrongCodes_ExpireProof_AndIdenticalWrongReplayDoesNotConsumeAnotherAttempt()
    {
        var owner = await SeedAsync();
        var challenge = await StartAsync(owner);
        var wrong = _delivery.LastCode == "000000" ? "000001" : "000000";
        var firstKey = Guid.NewGuid();
        for (var attempt = 0; attempt < 5; attempt++)
        {
            var key = attempt == 0 ? firstKey : Guid.NewGuid();
            await Assert.ThrowsAsync<IdentityActionDeniedException>(() =>
                Service.ConfirmPhoneChangeAsync(
                    owner.Actor,
                    owner.Membership,
                    challenge.ChallengeId,
                    wrong,
                    true,
                    key,
                    DateTimeOffset.UtcNow,
                    CancellationToken.None
                )
            );
            if (attempt == 0)
                await Assert.ThrowsAsync<IdentityActionDeniedException>(() =>
                    Service.ConfirmPhoneChangeAsync(
                        owner.Actor,
                        owner.Membership,
                        challenge.ChallengeId,
                        wrong,
                        true,
                        key,
                        DateTimeOffset.UtcNow,
                        CancellationToken.None
                    )
                );
        }
        await using var db = OwnerDb();
        var proof = await db.VerificationChallenges.SingleAsync(v =>
            v.ChallengeId == challenge.ChallengeId
        );
        Assert.Equal(5, proof.FailedAttempts);
        Assert.Equal(IdentityVerificationState.Expired, proof.State);
        await AssertOldAuthorityAsync(owner);
    }

    [Fact]
    public async Task ForeignNumberOrForeignChallenge_IsDeniedWithoutReassignment()
    {
        var owner = await SeedAsync();
        var foreign = await SeedAsync();
        await Assert.ThrowsAsync<IdentityActionDeniedException>(() =>
            Service.StartPhoneChangeAsync(
                owner.Actor,
                owner.Membership,
                foreign.Number,
                Guid.NewGuid(),
                DateTimeOffset.UtcNow,
                CancellationToken.None
            )
        );
        Assert.Equal(0, _delivery.Sends);
        var challenge = await StartAsync(owner);
        await Assert.ThrowsAsync<IdentityResourceNotFoundException>(() =>
            Service.ConfirmPhoneChangeAsync(
                foreign.Actor,
                foreign.Membership,
                challenge.ChallengeId,
                _delivery.LastCode,
                true,
                Guid.NewGuid(),
                DateTimeOffset.UtcNow,
                CancellationToken.None
            )
        );
        await AssertOldAuthorityAsync(owner);
        await AssertOldAuthorityAsync(foreign);
    }

    [Fact]
    public async Task ConsentIsRequired_AndGenericRegistrationOtpCannotConsumePhoneChangeProof()
    {
        var owner = await SeedAsync();
        var challenge = await StartAsync(owner);
        await Assert.ThrowsAsync<ArgumentException>(() =>
            Service.ConfirmPhoneChangeAsync(
                owner.Actor,
                owner.Membership,
                challenge.ChallengeId,
                _delivery.LastCode,
                false,
                Guid.NewGuid(),
                DateTimeOffset.UtcNow,
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<IdentityResourceNotFoundException>(() =>
            Service.ConfirmMobileVerificationAsync(
                null,
                owner.Actor.Subject,
                Guid.NewGuid(),
                "synthetic",
                challenge.ChallengeId,
                _delivery.LastCode,
                CancellationToken.None,
                owner.Actor
            )
        );
        await AssertOldAuthorityAsync(owner);
    }

    [Fact]
    public async Task FailedDelivery_IsDurablyUnresolved_AndReplayDoesNotDispatchAgain()
    {
        var owner = await SeedAsync();
        _delivery.Fail = true;
        var number = Number();
        var key = Guid.NewGuid();
        for (var attempt = 0; attempt < 2; attempt++)
            await Assert.ThrowsAsync<IdentityDeliveryUnavailableException>(() =>
                Service.StartPhoneChangeAsync(
                    owner.Actor,
                    owner.Membership,
                    number,
                    key,
                    DateTimeOffset.UtcNow,
                    CancellationToken.None
                )
            );
        Assert.Equal(1, _delivery.Sends);
        var status = await Service.GetPhoneChangeAsync(
            owner.Actor,
            owner.Membership,
            CancellationToken.None
        );
        Assert.Equal("DELIVERY_UNRESOLVED", status!.State);
        await AssertOldAuthorityAsync(owner);
    }

    [Fact]
    public async Task CancellationAndRateLimit_DoNotChangeAccountOrAllowProofReuse()
    {
        var owner = await SeedAsync();
        var challenge = await StartAsync(owner);
        var cancelled = await Service.CancelPhoneChangeAsync(
            owner.Actor,
            owner.Membership,
            challenge.ChallengeId,
            Guid.NewGuid(),
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );
        Assert.Equal("EXPIRED", cancelled.State);
        await Assert.ThrowsAsync<IdentityChallengeExpiredException>(() =>
            Service.ConfirmPhoneChangeAsync(
                owner.Actor,
                owner.Membership,
                challenge.ChallengeId,
                _delivery.LastCode,
                true,
                Guid.NewGuid(),
                DateTimeOffset.UtcNow,
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<IdentityVerificationRateLimitedException>(() => StartAsync(owner));
        await AssertOldAuthorityAsync(owner);
    }

    [Fact]
    public async Task MembershipRevokedDuringEvidence_PreventsAtomicReplacement()
    {
        var owner = await SeedAsync();
        var challenge = await StartAsync(owner);
        _evidence.BeforeReturn = action =>
            action == "IDENTITY_PHONE_CHANGE_CONFIRM"
                ? schema.ExecuteAsync(
                    $"UPDATE identity.memberships SET status = 'SUSPENDED' WHERE membership_id = '{owner.Membership.MembershipId:D}'"
                )
                : Task.CompletedTask;
        await Assert.ThrowsAsync<IdentityResourceNotFoundException>(() =>
            Service.ConfirmPhoneChangeAsync(
                owner.Actor,
                owner.Membership,
                challenge.ChallengeId,
                _delivery.LastCode,
                true,
                Guid.NewGuid(),
                DateTimeOffset.UtcNow,
                CancellationToken.None
            )
        );
        await AssertOldAuthorityAsync(owner);
    }

    [Fact]
    public async Task RetiredForeignNumber_RemainsDeniedAfterItsOwnerChangesPhone()
    {
        var owner = await SeedAsync();
        var foreign = await SeedAsync();
        var change = await StartAsync(foreign);
        await Service.ConfirmPhoneChangeAsync(
            foreign.Actor,
            foreign.Membership,
            change.ChallengeId,
            _delivery.LastCode,
            true,
            Guid.NewGuid(),
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );
        var sends = _delivery.Sends;
        await Assert.ThrowsAsync<IdentityActionDeniedException>(() =>
            Service.StartPhoneChangeAsync(
                owner.Actor,
                owner.Membership,
                foreign.Number,
                Guid.NewGuid(),
                DateTimeOffset.UtcNow,
                CancellationToken.None
            )
        );
        Assert.Equal(sends, _delivery.Sends);
        await AssertOldAuthorityAsync(owner);
    }

    [Fact]
    public async Task ProofExpiresDuringEvidence_DoesNotPromoteOrRevokeOldAuthority()
    {
        var owner = await SeedAsync();
        var challenge = await StartAsync(owner);
        _evidence.BeforeReturn = action =>
            action == "IDENTITY_PHONE_CHANGE_CONFIRM"
                ? schema.ExecuteAsync(
                    $"UPDATE identity.verification_challenges SET expires_at = now() - interval '1 second' WHERE challenge_id = '{challenge.ChallengeId:D}'"
                )
                : Task.CompletedTask;
        await Assert.ThrowsAsync<IdentityChallengeExpiredException>(() =>
            Service.ConfirmPhoneChangeAsync(
                owner.Actor,
                owner.Membership,
                challenge.ChallengeId,
                _delivery.LastCode,
                true,
                Guid.NewGuid(),
                DateTimeOffset.UtcNow,
                CancellationToken.None
            )
        );
        await AssertOldAuthorityAsync(owner);
    }

    [Fact]
    public async Task OwningCommitFailure_RollsBackProfileProofLinkAndChannel()
    {
        var owner = await SeedAsync();
        var challenge = await StartAsync(owner);
        var constraint = "synthetic_phone_commit_" + Guid.NewGuid().ToString("N");
        await schema.ExecuteAsync(
            $"ALTER TABLE identity.phone_changes ADD CONSTRAINT {constraint} CHECK (challenge_id <> '{challenge.ChallengeId:D}' OR completed_at IS NULL)"
        );
        try
        {
            await Assert.ThrowsAsync<DbUpdateException>(() =>
                Service.ConfirmPhoneChangeAsync(
                    owner.Actor,
                    owner.Membership,
                    challenge.ChallengeId,
                    _delivery.LastCode,
                    true,
                    Guid.NewGuid(),
                    DateTimeOffset.UtcNow,
                    CancellationToken.None
                )
            );
            await AssertOldAuthorityAsync(owner);
            await using var db = OwnerDb();
            Assert.Equal(
                IdentityVerificationState.Pending,
                (
                    await db.VerificationChallenges.SingleAsync(v =>
                        v.ChallengeId == challenge.ChallengeId
                    )
                ).State
            );
        }
        finally
        {
            await schema.ExecuteAsync(
                $"ALTER TABLE identity.phone_changes DROP CONSTRAINT {constraint}"
            );
        }
    }

    [Fact]
    public async Task ConcurrentConfirmations_CommitOnlyOneCompletedChange()
    {
        var owner = await SeedAsync();
        var challenge = await StartAsync(owner);
        var code = _delivery.LastCode;
        var results = await Task.WhenAll(
            Enumerable
                .Range(0, 2)
                .Select(_ =>
                    Service.ConfirmPhoneChangeAsync(
                        owner.Actor,
                        owner.Membership,
                        challenge.ChallengeId,
                        code,
                        true,
                        Guid.NewGuid(),
                        DateTimeOffset.UtcNow,
                        CancellationToken.None
                    )
                )
        );
        Assert.All(results, result => Assert.Equal("COMPLETED", result.State));
        await using var db = OwnerDb();
        Assert.Single(
            await db
                .PhoneChanges.Where(v =>
                    v.ChallengeId == challenge.ChallengeId && v.CompletedAt != null
                )
                .ToListAsync()
        );
    }

    private Task<IdentityPhoneChangeResult> StartAsync(Owner owner) =>
        Service.StartPhoneChangeAsync(
            owner.Actor,
            owner.Membership,
            Number(),
            Guid.NewGuid(),
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );

    private IdentityDbContext OwnerDb() =>
        new(
            new DbContextOptionsBuilder<IdentityDbContext>()
                .UseNpgsql(schema.OwnerConnection)
                .Options
        );

    private async Task AssertOldAuthorityAsync(Owner owner)
    {
        await using var db = OwnerDb();
        Assert.Equal(
            Service.ComputeMatchCandidates("mobile", owner.Number)["v1"],
            (
                await db.Registrations.SingleAsync(v => v.RegistrationId == owner.RegistrationId)
            ).MobileHmacKey
        );
        Assert.Equal(
            IdentityAccountLinkState.Linked,
            (await db.AccountLinks.SingleAsync(v => v.LinkId == owner.LinkId)).State
        );
        await using var relationships = new EmploymentRelationshipDbContext(
            new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                .UseNpgsql(schema.OwnerConnection)
                .Options
        );
        Assert.Equal(
            "ACTIVE",
            (
                await relationships.ChannelBindings.SingleAsync(v => v.BindingId == owner.BindingId)
            ).Status
        );
    }

    private async Task<Owner> SeedAsync(bool legacyQualifiedLink = false)
    {
        var actorId = Guid.NewGuid();
        var actor = (VerifiedCustomerActor)
            Activator.CreateInstance(
                typeof(VerifiedCustomerActor),
                BindingFlags.NonPublic | BindingFlags.Instance,
                null,
                [Issuer, actorId.ToString("D")],
                null
            )!;
        var membership = new CustomerWorkspaceMembership(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            ["OWNER"]
        );
        var owner = new Owner(
            actor,
            membership,
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            Number(),
            Convert
                .ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(actor.Subject)))
                .ToLowerInvariant()
        );
        await using var connection = new NpgsqlConnection(schema.OwnerConnection);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(
            """
            BEGIN;
            INSERT INTO business.organisations(id, tenant_id, name, identity_managed, identity_status)
                VALUES (@tenant, @tenant, 'Synthetic phone change', true, 'ACTIVE');
            INSERT INTO identity.registrations(registration_id, actor_issuer, actor_subject, authentication_path,
                email_verified, mobile_verified, mobile_hmac_key, mobile_hmac_version, mobile_hmac_domain, masked_mobile,
                display_name, business_name, business_domain, language_preference)
                VALUES (@registration, @issuer, @subject, 'Google', true, true, @mobile_key, 'v1', 'mobile', '+1******0000',
                    'Synthetic owner', 'Synthetic phone change', 'retail', 'en');
            INSERT INTO identity.accounts(account_id, initial_tenant_id, origin_registration_id, status)
                VALUES (@account, @tenant, @registration, 'ACTIVE');
            INSERT INTO identity.login_methods(login_method_id, provider_issuer, broker_alias, provider_subject, account_id, status)
                VALUES (@login, 'https://synthetic.invalid/provider', 'google', @subject, @account, 'ACTIVE');
            INSERT INTO identity.actor_bindings(actor_binding_id, actor_issuer, actor_subject, login_method_id, account_id,
                status, proof_source, verified_at, auth_time, trust_config_digest, correlation_id)
                VALUES (@actor_binding, @issuer, @subject, @login, @account, 'ACTIVE', 'KEYCLOAK_FEDERATED_IDENTITY',
                    now(), now(), repeat('a', 64), gen_random_uuid());
            INSERT INTO identity.memberships(membership_id, account_id, tenant_id, roles, status)
                VALUES (@membership, @account, @tenant, ARRAY['OWNER']::text[], 'ACTIVE');
            UPDATE identity.registrations SET state = 'Completed', account_id = @account,
                actor_binding_id = @actor_binding, origin_registration_id = @registration, completed_at = now(),
                completion_outcome = 'ACCOUNT_CREATED', completion_profile_snapshot = jsonb_build_object(
                    'displayName', display_name, 'businessName', business_name, 'businessDomain', business_domain,
                    'languagePreference', language_preference, 'emailVerified', true, 'mobileVerified', mobile_verified),
                completion_status_code = 200, completion_response_body = '{}'
                WHERE registration_id = @registration;
            INSERT INTO identity.registration_events(registration_id, actor_issuer, actor_subject,
                event_type, from_state, to_state)
                VALUES (@registration, @issuer, @subject, 'RegistrationCompleted', 'ReadyToComplete', 'Completed');
            INSERT INTO identity.idempotency_ledger(registration_id, actor_issuer, actor_subject,
                idempotency_key, operation_family, canonical_hash, status_code, response_body)
                VALUES (@registration, @issuer, @subject, gen_random_uuid()::text, 'CompleteRegistration',
                    repeat('c',64), 200, '{}');
            INSERT INTO identity.verification_challenges(challenge_id, registration_id, actor_subject, purpose, state,
                code_hmac, destination_hmac_key, destination_hmac_version, destination_hmac_domain,
                delivery_state, verified_at, masked_destination, created_at, resend_after)
                VALUES (@proof, @registration, @subject, 'Mobile', 'Consumed', @code_key, @mobile_key,
                    'v1', 'mobile', 'SUBMITTED', now() - interval '1 hour', '+1******0000',
                    now() - interval '1 hour', now() - interval '59 minutes');
            INSERT INTO identity.account_links(link_id, actor_subject, tenant_id, state, masked_mobile,
                verified_mobile_proof_id, start_evidence_id, approval_evidence_id, confirmation_evidence_id,
                confirmation_message_digest, confirmed_phone_subject_hash, confirmed_at)
                VALUES (@link, @link_subject, @tenant, 'Linked', '+1******0000', @proof, gen_random_uuid(),
                    gen_random_uuid(), gen_random_uuid(), repeat('b',64), @sender, now());
            INSERT INTO business.employment_relationships(relationship_id, tenant_id, professional_type,
                evaluation_intent_id, initiating_participant_id)
                VALUES (@relationship, @tenant, 'DMA', gen_random_uuid(), @actor);
            INSERT INTO business.relationship_participants(tenant_id, relationship_id, participant_id, role, bound_evidence_id)
                VALUES (@tenant, @relationship, @actor, 'EMPLOYER', gen_random_uuid());
            INSERT INTO business.channel_bindings(binding_id, tenant_id, relationship_id, participant_id,
                participant_role, channel, external_subject_hash, conversation_id, assurance_level,
                status, prepared_evidence_id, bound_evidence_id, bound_at)
                VALUES (@binding, @tenant, @relationship, @actor, 'EMPLOYER', 'WHATSAPP', @sender,
                    @conversation::text, 'TIER_4_PORTAL_FRESH', 'ACTIVE', gen_random_uuid(), gen_random_uuid(), now());
            INSERT INTO business.conversations(tenant_id, relationship_id, conversation_id, environment)
                VALUES (@tenant, @relationship, @conversation, 'demo');
            INSERT INTO business.conversation_outbox(environment, tenant_id, relationship_id, conversation_id,
                sequence, owner, aggregate_id, operation_family, idempotency_key, payload_digest, payload_reference,
                purpose, recipient_binding_digest, state)
                VALUES ('demo', @tenant, @relationship, @conversation, 1, 'BP', 'pending', 'REPLY', gen_random_uuid(),
                    repeat('a',64), 'synthetic', 'CONVERSATION_REPLY', @sender, 'PENDING'),
                ('demo', @tenant, @relationship, @conversation, 2, 'BP', 'unknown', 'REPLY', gen_random_uuid(),
                    repeat('a',64), 'synthetic', 'CONVERSATION_REPLY', @sender, 'UNRESOLVED');
            COMMIT;
            """,
            connection
        );
        command.Parameters.AddWithValue("tenant", membership.TenantId);
        command.Parameters.AddWithValue("account", membership.AccountId);
        command.Parameters.AddWithValue("membership", membership.MembershipId);
        command.Parameters.AddWithValue("registration", owner.RegistrationId);
        command.Parameters.AddWithValue("issuer", Issuer);
        command.Parameters.AddWithValue("subject", actor.Subject);
        command.Parameters.AddWithValue("actor", actorId);
        command.Parameters.AddWithValue("login", Guid.NewGuid());
        command.Parameters.AddWithValue("actor_binding", Guid.NewGuid());
        command.Parameters.AddWithValue("proof", Guid.NewGuid());
        command.Parameters.AddWithValue("link", owner.LinkId);
        command.Parameters.AddWithValue(
            "link_subject",
            legacyQualifiedLink ? $"{Issuer}\u001f{actor.Subject}" : actor.Subject
        );
        command.Parameters.AddWithValue("relationship", owner.RelationshipId);
        command.Parameters.AddWithValue("binding", owner.BindingId);
        command.Parameters.AddWithValue("conversation", Guid.NewGuid());
        command.Parameters.AddWithValue("sender", owner.SenderHash);
        command.Parameters.AddWithValue(
            "mobile_key",
            Service.ComputeMatchCandidates("mobile", owner.Number)["v1"]
        );
        using var keyDerivation = new HMACSHA256(
            Encoding.UTF8.GetBytes(IdentityTestHelpers.TestHmacKey)
        );
        var otpKey = keyDerivation.ComputeHash(Encoding.UTF8.GetBytes("waooaw:identity:otp:v1"));
        using var codeHmac = new HMACSHA256(otpKey);
        command.Parameters.AddWithValue(
            "code_key",
            Convert
                .ToHexString(codeHmac.ComputeHash(Encoding.UTF8.GetBytes("111111"))[..16])
                .ToLowerInvariant()
        );
        await command.ExecuteNonQueryAsync();
        return owner;
    }

    private static async Task ApplyOwnerContextAsync(
        NpgsqlConnection connection,
        NpgsqlTransaction transaction,
        Owner owner
    )
    {
        await using var context = new NpgsqlCommand(
            """
            SELECT set_config('app.identity_issuer', @issuer, true),
                set_config('app.identity_subject', @subject, true),
                set_config('app.current_tenant_id', @tenant::text, true),
                set_config('app.current_membership_id', @membership::text, true);
            """,
            connection,
            transaction
        );
        context.Parameters.AddWithValue("issuer", owner.Actor.Issuer);
        context.Parameters.AddWithValue("subject", owner.Actor.Subject);
        context.Parameters.AddWithValue("tenant", owner.Membership.TenantId);
        context.Parameters.AddWithValue("membership", owner.Membership.MembershipId);
        await context.ExecuteNonQueryAsync();
    }

    private static string Number() => $"+1555{Interlocked.Increment(ref _sequence):D7}";

    private sealed record Owner(
        VerifiedCustomerActor Actor,
        CustomerWorkspaceMembership Membership,
        Guid RegistrationId,
        Guid LinkId,
        Guid RelationshipId,
        Guid BindingId,
        string Number,
        string SenderHash
    );

    private sealed class Factory(string connection) : IDbContextFactory<IdentityDbContext>
    {
        public IdentityDbContext CreateDbContext() =>
            new(new DbContextOptionsBuilder<IdentityDbContext>().UseNpgsql(connection).Options);
    }

    private sealed class VerificationDispatcher : IIdentityVerificationDispatcher
    {
        public int Sends { get; private set; }
        public string LastCode { get; private set; } = "";
        public bool Fail { get; set; }

        public Task DispatchAsync(
            IdentityVerificationPurpose purpose,
            string destination,
            string code,
            CancellationToken ct
        )
        {
            Sends++;
            LastCode = code;
            return Fail
                ? Task.FromException(
                    new IdentityDeliveryUnavailableException("synthetic unavailable")
                )
                : Task.CompletedTask;
        }
    }

    private sealed class EvidenceGateway : IIdentityConstitutionalGateway
    {
        public Func<string, Task>? BeforeReturn { get; set; }

        public async Task<Guid> AuthorizeAndRecordAsync(
            Guid tenantId,
            Guid actionInstanceId,
            string actionType,
            object actionParameters,
            CancellationToken ct
        )
        {
            if (BeforeReturn is not null)
                await BeforeReturn(actionType);
            return Guid.NewGuid();
        }
    }
}
