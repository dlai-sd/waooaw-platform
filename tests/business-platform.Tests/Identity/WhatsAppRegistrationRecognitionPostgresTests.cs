// Implements: WC-134 R005 registration recognition and least-privilege migration regression.
// constitutional_basis: C-023, C-026, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class WhatsAppRegistrationRecognitionPostgresTests
{
    [Fact]
    public async Task RecognitionUsesBoundConsumedProofWithoutExposingActorScopedRegistrations()
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
            .WithDatabase("synthetic_recognition")
            .WithUsername("synthetic_owner")
            .WithPassword(Guid.NewGuid().ToString("N"))
            .Build();
        await postgres.StartAsync();
        await using var owner = new NpgsqlConnection(postgres.GetConnectionString());
        await owner.OpenAsync();
        var password = Guid.NewGuid().ToString("N");
        await ExecuteAsync(
            owner,
            $"""
            CREATE ROLE business_app LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '{password}';
            CREATE ROLE unrelated_app LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '{password}';
            """
        );
        await ExecuteAsync(
            owner,
            await File.ReadAllTextAsync(
                RepositoryPaths.Resolve("infrastructure/postgres/init/20-identity-boundary.sql")
            )
        );
        await ExecuteAsync(
            owner,
            """
            GRANT USAGE ON SCHEMA identity TO business_app, unrelated_app;
            GRANT SELECT ON identity.registrations TO business_app;
            ALTER TABLE identity.registrations ENABLE ROW LEVEL SECURITY;
            ALTER TABLE identity.registrations FORCE ROW LEVEL SECURITY;
            CREATE POLICY actor_scope ON identity.registrations TO business_app
                USING (actor_subject = NULLIF(current_setting('app.identity_subject', true), ''));
            ALTER TABLE identity.verification_challenges ENABLE ROW LEVEL SECURITY;
            ALTER TABLE identity.verification_challenges FORCE ROW LEVEL SECURITY;
            """
        );
        var migration = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/74-wc134-whatsapp-registration-recognition.sql"
            )
        );
        await ExecuteAsync(owner, migration);
        await ExecuteAsync(owner, migration);
        await using (
            var policy = new NpgsqlCommand(
                """
                SELECT qual FROM pg_policies
                WHERE schemaname = 'identity'
                  AND tablename = 'registrations'
                  AND policyname = 'whatsapp_verified_registration_recognition'
                """,
                owner
            )
        )
            Assert.Equal(
                "(((state)::text = 'Completed'::text) AND mobile_verified AND (account_id IS NOT NULL))",
                await policy.ExecuteScalarAsync()
            );
        await using (
            var principal = new NpgsqlCommand(
                """
                SELECT NOT role.rolcanlogin AND NOT role.rolsuper AND NOT role.rolbypassrls
                    AND NOT pg_has_role('business_app', role.oid, 'MEMBER')
                FROM pg_roles AS role WHERE role.rolname = 'identity_whatsapp_recognizer_owner'
                """,
                owner
            )
        )
            Assert.Equal(true, await principal.ExecuteScalarAsync());
        var runtimeConnection = new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
        {
            Username = "business_app",
            Password = password,
        }.ConnectionString;
        var factory = new Factory(
            new DbContextOptionsBuilder<IdentityDbContext>().UseNpgsql(runtimeConnection).Options
        );
        var identity = IdentityTestHelpers.CreateService(factory);
        var recognition = new WhatsAppRegistrationRecognition(identity, factory);
        const string number = "+14155550100";
        var digest = identity.ComputeMatchCandidates("mobile", number)["v1"];
        var registrationId = Guid.NewGuid();
        await using (
            var seed = new NpgsqlCommand(
                """
                INSERT INTO identity.registrations
                    (registration_id, actor_subject, state, authentication_path, mobile_verified,
                     mobile_hmac_domain, mobile_hmac_version, mobile_hmac_key, account_id)
                VALUES (@registration, 'private-other-actor', 'Completed', 'Google', TRUE,
                        'mobile', 'v1', @digest, @account);
                INSERT INTO identity.verification_challenges
                    (registration_id, actor_subject, purpose, state, code_hmac, masked_destination,
                     delivery_state, verified_at, destination_hmac_domain,
                     destination_hmac_version, destination_hmac_key)
                VALUES (@registration, 'private-other-actor', 'Mobile', 'Consumed', 'synthetic-hash',
                        '***0100', 'SUBMITTED', NOW(), 'mobile', 'v1', @digest);
                """,
                owner
            )
        )
        {
            seed.Parameters.AddWithValue("registration", registrationId);
            seed.Parameters.AddWithValue("account", Guid.NewGuid());
            seed.Parameters.AddWithValue("digest", digest);
            await seed.ExecuteNonQueryAsync();
        }
        Assert.True(await recognition.IsVerifiedRegistrationAsync(number, CancellationToken.None));
        Assert.False(
            await recognition.IsVerifiedRegistrationAsync("+14155550101", CancellationToken.None)
        );
        await using (var runtime = factory.CreateDbContext())
            Assert.Equal(
                0L,
                await runtime
                    .Database.SqlQuery<long>(
                        $"""SELECT count(*) AS "Value" FROM identity.registrations"""
                    )
                    .SingleAsync()
            );
        var rotatedIdentity = new IdentityService(
            factory,
            Options.Create(
                new IdentityHmacOptions
                {
                    Key = "synthetic-new-hmac-key-material-at-least-32-characters",
                    ActiveVersion = "v2",
                    ReadOnlyVersions = new()
                    {
                        ["v1"] = "test-only-identity-hmac-key-32-bytes-minimum",
                    },
                }
            ),
            new CapturingVerificationDispatcher()
        );
        Assert.True(
            await new WhatsAppRegistrationRecognition(
                rotatedIdentity,
                factory
            ).IsVerifiedRegistrationAsync(number, CancellationToken.None)
        );
        foreach (
            var mutation in new[]
            {
                "UPDATE identity.registrations SET mobile_verified = FALSE",
                "UPDATE identity.registrations SET state = 'ReadyToComplete'",
                "UPDATE identity.registrations SET account_id = NULL",
                "UPDATE identity.verification_challenges SET state = 'Pending'",
                "UPDATE identity.verification_challenges SET delivery_state = 'DISPATCHING'",
                "UPDATE identity.verification_challenges SET verified_at = NULL",
                "UPDATE identity.verification_challenges SET destination_hmac_key = repeat('0', 32)",
                "UPDATE identity.verification_challenges SET destination_hmac_version = 'different'",
                "UPDATE identity.verification_challenges SET destination_hmac_domain = 'email'",
            }
        )
        {
            await using var transaction = await owner.BeginTransactionAsync();
            await using var change = new NpgsqlCommand(mutation, owner, transaction);
            await change.ExecuteNonQueryAsync();
            await transaction.CommitAsync();
            Assert.False(
                await recognition.IsVerifiedRegistrationAsync(number, CancellationToken.None)
            );
            await using var restore = new NpgsqlCommand(
                """
                UPDATE identity.registrations SET mobile_verified = TRUE, state = 'Completed', account_id = @account;
                UPDATE identity.verification_challenges SET state = 'Consumed',
                    delivery_state = 'SUBMITTED', verified_at = NOW(),
                    destination_hmac_domain = 'mobile', destination_hmac_version = 'v1',
                    destination_hmac_key = @digest;
                """,
                owner
            );
            restore.Parameters.AddWithValue("account", Guid.NewGuid());
            restore.Parameters.AddWithValue("digest", digest);
            await restore.ExecuteNonQueryAsync();
        }
        await using var runtimeConnectionHandle = new NpgsqlConnection(runtimeConnection);
        await runtimeConnectionHandle.OpenAsync();
        foreach (
            var arguments in new[]
            {
                "ARRAY['v1'], ARRAY['invalid']",
                "ARRAY[]::text[], ARRAY[]::text[]",
                "ARRAY['v1', 'v2'], ARRAY[repeat('0', 32)]",
                "ARRAY[NULL]::text[], ARRAY[repeat('0', 32)]",
                "ARRAY['v1'], ARRAY[NULL]::text[]",
                "ARRAY[['v1']], ARRAY[[repeat('0', 32)]]",
                "array_fill('v1'::text, ARRAY[65]), array_fill(repeat('0', 32), ARRAY[65])",
                "NULL::text[], ARRAY[repeat('0', 32)]",
            }
        )
        {
            await using var malformed = new NpgsqlCommand(
                $"SELECT identity.has_verified_whatsapp_registration({arguments})",
                runtimeConnectionHandle
            );
            var error = await Assert.ThrowsAsync<PostgresException>(() =>
                malformed.ExecuteScalarAsync()
            );
            Assert.Equal("22023", error.SqlState);
        }
        var otherConnection = new NpgsqlConnectionStringBuilder(runtimeConnection)
        {
            Username = "unrelated_app",
        }.ConnectionString;
        await using var other = new NpgsqlConnection(otherConnection);
        await other.OpenAsync();
        await using var denied = new NpgsqlCommand(
            """
            SELECT identity.has_verified_whatsapp_registration(ARRAY['v1'], ARRAY[repeat('0', 32)]);
            """,
            other
        );
        var deniedError = await Assert.ThrowsAsync<PostgresException>(() =>
            denied.ExecuteScalarAsync()
        );
        Assert.Equal("42501", deniedError.SqlState);
        Assert.True(await recognition.IsVerifiedRegistrationAsync(number, CancellationToken.None));
        await ExecuteAsync(owner, "ALTER ROLE identity_whatsapp_recognizer_owner LOGIN;");
        var unsafePrincipal = await Assert.ThrowsAsync<PostgresException>(() =>
            ExecuteAsync(owner, migration)
        );
        Assert.Equal("P0001", unsafePrincipal.SqlState);
        await ExecuteAsync(
            owner,
            """
            ROLLBACK;
            ALTER ROLE identity_whatsapp_recognizer_owner NOLOGIN;
            """
        );
        Assert.True(await recognition.IsVerifiedRegistrationAsync(number, CancellationToken.None));
        await ExecuteAsync(owner, "GRANT identity_whatsapp_recognizer_owner TO business_app;");
        var unsafeMembership = await Assert.ThrowsAsync<PostgresException>(() =>
            ExecuteAsync(owner, migration)
        );
        Assert.Equal("P0001", unsafeMembership.SqlState);
        await ExecuteAsync(
            owner,
            """
            ROLLBACK;
            REVOKE identity_whatsapp_recognizer_owner FROM business_app;
            """
        );
        await ExecuteAsync(owner, migration);
        Assert.True(await recognition.IsVerifiedRegistrationAsync(number, CancellationToken.None));
    }

    private static async Task ExecuteAsync(NpgsqlConnection connection, string sql)
    {
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private sealed class Factory(DbContextOptions<IdentityDbContext> options)
        : IDbContextFactory<IdentityDbContext>
    {
        public IdentityDbContext CreateDbContext() => new(options);
    }
}
