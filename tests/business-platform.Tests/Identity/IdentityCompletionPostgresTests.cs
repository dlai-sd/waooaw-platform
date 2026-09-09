// Implements: architecture/reference/components/identity-boundary.md Sections 1.8 and 5
// constitutional_basis: C-059

using Microsoft.EntityFrameworkCore;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class IdentityCompletionPostgresTests : IAsyncLifetime
{
    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("identity_completion")
        .WithUsername("test_owner")
        .WithPassword("synthetic-completion-test-password")
        .Build();

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        await ExecuteOwnerAsync(await File.ReadAllTextAsync(
            RepositoryPaths.Resolve("infrastructure/postgres/init/20-identity-boundary.sql")));
        await ExecuteOwnerAsync("""
            ALTER TABLE identity.registrations
                ADD COLUMN actor_issuer varchar(256),
                ADD COLUMN actor_binding_id uuid,
                ADD COLUMN origin_registration_id uuid,
                ADD COLUMN completed_at timestamptz,
                ADD COLUMN completion_outcome varchar(24),
                ADD COLUMN completion_profile_snapshot jsonb,
                ADD COLUMN completion_status_code integer,
                ADD COLUMN completion_response_body text;
            ALTER TABLE identity.idempotency_ledger
                ADD COLUMN actor_issuer varchar(256),
                ADD COLUMN registration_id uuid;
            CREATE ROLE completion_app LOGIN PASSWORD 'synthetic-completion-app-password'
                NOSUPERUSER NOBYPASSRLS;
            GRANT USAGE ON SCHEMA identity TO completion_app;
            GRANT SELECT, INSERT, UPDATE ON identity.registrations TO completion_app;
            GRANT SELECT, INSERT ON identity.idempotency_ledger TO completion_app;
            ALTER TABLE identity.idempotency_ledger ADD CONSTRAINT reject_test_completion
                CHECK (operation_family <> 'CompleteRegistration');
            """);
    }

    public async Task DisposeAsync() => await _postgres.DisposeAsync();

    [Fact]
    public async Task F2_CompleteRegistration_PostgresFailure_RollsBackAndRetryReplays()
    {
        var connectionString = new NpgsqlConnectionStringBuilder(_postgres.GetConnectionString())
        {
            Username = "completion_app",
            Password = "synthetic-completion-app-password",
        }.ConnectionString;
        var factory = new CompletionDbContextFactory(connectionString);
        var registration = new IdentityRegistrationRecord
        {
            ActorSubject = "postgres-completion-test",
            State = IdentityRegistrationState.ReadyToComplete,
            EmailVerified = true,
            DisplayName = "Test Customer",
            BusinessName = "Test Business",
            BusinessDomain = "Consulting",
            LanguagePreference = "en",
        };
        await using (var seed = factory.CreateDbContext())
        {
            seed.Registrations.Add(registration);
            await seed.SaveChangesAsync();
        }

        var service = IdentityTestHelpers.CreateService(factory);
        var idempotencyKey = Guid.NewGuid();
        const string canonicalHash = "postgres-completion-hash";
        var failure = await Assert.ThrowsAsync<DbUpdateException>(() => service.CompleteRegistrationAsync(
            registration.RegistrationId, registration.ActorSubject, idempotencyKey,
            canonicalHash, CancellationToken.None));
        var databaseFailure = Assert.IsType<PostgresException>(failure.InnerException);
        Assert.Equal(PostgresErrorCodes.CheckViolation, databaseFailure.SqlState);
        Assert.Equal("reject_test_completion", databaseFailure.ConstraintName);

        await using (var persisted = factory.CreateDbContext())
        {
            var unchanged = await persisted.Registrations.SingleAsync();
            Assert.Null(unchanged.AccountId);
            Assert.Equal(IdentityRegistrationState.ReadyToComplete, unchanged.State);
            Assert.Empty(await persisted.IdempotencyLedger.ToListAsync());
        }

        await ExecuteOwnerAsync(
            "ALTER TABLE identity.idempotency_ledger DROP CONSTRAINT reject_test_completion;");
        var (completed, isNew) = await service.CompleteRegistrationAsync(
            registration.RegistrationId, registration.ActorSubject, idempotencyKey,
            canonicalHash, CancellationToken.None);
        var (replayed, replayIsNew) = await service.CompleteRegistrationAsync(
            registration.RegistrationId, registration.ActorSubject, idempotencyKey,
            canonicalHash, CancellationToken.None);

        Assert.True(isNew);
        Assert.False(replayIsNew);
        Assert.Equal("ACCOUNT_CREATED", completed.Outcome);
        Assert.NotEqual(Guid.Empty, completed.AccountReference);
        Assert.Equal(completed, replayed);
        await using var saved = factory.CreateDbContext();
        var committed = await saved.Registrations.SingleAsync();
        Assert.Equal(completed.AccountReference, committed.AccountId);
        Assert.Equal(IdentityRegistrationState.Completed, committed.State);
        Assert.Single(await saved.IdempotencyLedger.ToListAsync());
    }

    private async Task ExecuteOwnerAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private sealed class CompletionDbContextFactory(string connectionString)
        : IDbContextFactory<IdentityDbContext>
    {
        public IdentityDbContext CreateDbContext() =>
            new(new DbContextOptionsBuilder<IdentityDbContext>().UseNpgsql(connectionString).Options);
    }
}