// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-06
// Constitutional basis: C-023, C-059, C-063
using Microsoft.EntityFrameworkCore;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Spend;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Spend;

/// <summary>One PostgreSQL container with the environment spend init chain; each test uses its own environment.</summary>
public sealed class EnvironmentSpendPostgresFixture : IAsyncLifetime
{
    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder(
        "postgres:16-alpine"
    ).Build();

    public IDbContextFactory<ConversationStoreDbContext> Conversations { get; private set; } =
        null!;

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        Conversations = new StoreFactory(_postgres.GetConnectionString());
        await ExecuteAsync(
            """
            CREATE ROLE bp_owner NOBYPASSRLS;
            CREATE ROLE business_app NOBYPASSRLS;
            CREATE SCHEMA business;
            GRANT USAGE, CREATE ON SCHEMA business TO bp_owner;
            GRANT USAGE ON SCHEMA business TO business_app;
            CREATE TABLE business.conversation_model_reservations (
                environment TEXT, execution_id UUID, reservation_id UUID, customer_tenant_id UUID);
            ALTER TABLE business.conversation_model_reservations OWNER TO bp_owner;
            """
        );
        foreach (
            var migration in new[]
            {
                "99zzzzzz-wc134-environment-spend.sql",
                "99zzzzzzzz-wc136-01-environment-spend-ceiling.sql",
                "99zzzzzzzz-wc136-03-spend-account-pin.sql",
                "99zzzzzzzz-wc136-04-environment-spend-leases.sql",
            }
        )
            await ExecuteAsync(
                await File.ReadAllTextAsync(
                    RepositoryPaths.Resolve($"infrastructure/postgres/init/{migration}")
                )
            );
    }

    public Task DisposeAsync() => _postgres.DisposeAsync().AsTask();

    public async Task<string> NewEnvironmentAsync(long authorityMaximumPaise = 1_000_000)
    {
        var environment = $"t{Guid.NewGuid():N}"[..13];
        await ExecuteAsync(
            $"""
            INSERT INTO business.environment_spend_authorities
                (environment,authority_version,maximum_paise,active,migration_complete,
                 authority_evidence_id,updated_at)
            VALUES ('{environment}',1,{authorityMaximumPaise},true,true,gen_random_uuid(),clock_timestamp())
            """
        );
        return environment;
    }

    public async Task ExecuteAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    public async Task<T> ScalarAsync<T>(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        return (T)(await command.ExecuteScalarAsync())!;
    }

    public async Task<EnvironmentSpendPermit> ReserveAsync(
        ConversationEnvironmentSpendOwner owner,
        string environment,
        long paise,
        long ceilingPaise,
        SpendAccountPin? pin = null,
        DateTimeOffset? now = null,
        Guid? attemptId = null
    )
    {
        await using var db = Conversations.CreateDbContext();
        await using var transaction = await db.Database.BeginTransactionAsync();
        var permit = await owner.ReserveAsync(
            db,
            environment,
            "MODEL",
            attemptId ?? Guid.NewGuid(),
            Guid.NewGuid(),
            "activation",
            new string('b', 64),
            Guid.NewGuid(),
            paise,
            ceilingPaise,
            now ?? DateTimeOffset.UtcNow,
            CancellationToken.None,
            pin
        );
        await transaction.CommitAsync();
        return permit;
    }

    public async Task SettleAsync(
        ConversationEnvironmentSpendOwner owner,
        EnvironmentSpendPermit permit,
        long actualPaise,
        bool release
    )
    {
        await using var db = Conversations.CreateDbContext();
        await using var transaction = await db.Database.BeginTransactionAsync();
        await owner.SettleAsync(
            db,
            permit.Environment,
            permit.OwnerKind,
            permit.AttemptId,
            permit.ReservationReference,
            actualPaise,
            release,
            Guid.NewGuid(),
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );
        await transaction.CommitAsync();
    }

    public Task InsertUnresolvedAttemptAsync(string environment, long paise) =>
        ExecuteAsync(
            $"""
            INSERT INTO business.environment_spend_attempts
                (environment,owner_kind,attempt_id,original_tenant_id,activation_digest,
                 request_digest,reservation_reference,reserved_paise,state,reserved_at)
            VALUES ('{environment}','MODEL',gen_random_uuid(),gen_random_uuid(),'activation',
                repeat('c',64),gen_random_uuid(),{paise},'RECONCILIATION_REQUIRED',clock_timestamp())
            """
        );

    public async Task<long> ExposureAsync(string environment, DateTimeOffset? now = null)
    {
        await using var db = Conversations.CreateDbContext();
        return await ConversationEnvironmentSpendOwner.ExposureAsync(
            db,
            environment,
            now ?? DateTimeOffset.UtcNow,
            CancellationToken.None
        );
    }

    public ConversationEnvironmentSpendOwner LeaseOwner(
        EnvironmentSpendOptions options,
        out EnvironmentSpendLeaseService leases
    )
    {
        leases = new EnvironmentSpendLeaseService(
            new PostgresEnvironmentSpendLeaseStore(Conversations),
            options
        );
        return new ConversationEnvironmentSpendOwner(options, leases);
    }

    private sealed class StoreFactory(string connection)
        : IDbContextFactory<ConversationStoreDbContext>
    {
        public ConversationStoreDbContext CreateDbContext() =>
            new(
                new DbContextOptionsBuilder<ConversationStoreDbContext>()
                    .UseNpgsql(connection)
                    .Options
            );
    }
}
