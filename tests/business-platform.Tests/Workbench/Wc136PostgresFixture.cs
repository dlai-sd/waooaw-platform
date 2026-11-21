// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-06, C4-08, C5-04, C6-02, C6-03
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, ADR-051
using Microsoft.EntityFrameworkCore;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

[CollectionDefinition(Wc136PostgresFixture.CollectionName)]
public sealed class Wc136PostgresCollection : ICollectionFixture<Wc136PostgresFixture>;

/// <summary>
/// One PostgreSQL container with the WC-136 init chain (spend ceiling, workbench ledger and handoffs, component-unit
/// outbox). Stores are exercised as the unprivileged <c>business_app</c> login so grants and row-level security apply;
/// the admin connection only seeds and inspects rows.
/// </summary>
public sealed class Wc136PostgresFixture : IAsyncLifetime
{
    public const string CollectionName = "wc136-postgres";
    private const string AppPassword = "app-password-for-tests";

    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder(
        "postgres:16-alpine"
    ).Build();

    public string AdminConnectionString => _postgres.GetConnectionString();

    public string AppConnectionString =>
        new NpgsqlConnectionStringBuilder(_postgres.GetConnectionString())
        {
            Username = "business_app",
            Password = AppPassword,
        }.ConnectionString;

    public IDbContextFactory<ConversationStoreDbContext> AppConversations { get; private set; } =
        null!;

    public IDbContextFactory<ConversationStoreDbContext> AdminConversations { get; private set; } =
        null!;

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        AdminConversations = new StoreFactory(AdminConnectionString);
        AppConversations = new StoreFactory(AppConnectionString);
        await ExecuteAsync(
            $"""
            CREATE ROLE bp_owner NOBYPASSRLS;
            CREATE ROLE business_app LOGIN PASSWORD '{AppPassword}' NOBYPASSRLS;
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
                "99zzzzzzzz-wc136-10-budget-authority-function.sql",
                "99zzzzzzzz-wc136-13-workbench-ledger-and-handoffs.sql",
                "99zzzzzzzz-wc136-15-component-unit-outbox.sql",
            }
        )
            await ExecuteAsync(
                await File.ReadAllTextAsync(
                    RepositoryPaths.Resolve($"infrastructure/postgres/init/{migration}")
                )
            );
    }

    public Task DisposeAsync() => _postgres.DisposeAsync().AsTask();

    public async Task<string> NewEnvironmentAsync(
        long authorityMaximumPaise = 1_000_000,
        bool active = true
    )
    {
        var environment = $"t{Guid.NewGuid():N}"[..13];
        await ExecuteAsync(
            $"""
            INSERT INTO business.environment_spend_authorities
                (environment,authority_version,maximum_paise,active,migration_complete,
                 authority_evidence_id,updated_at)
            VALUES ('{environment}',1,{authorityMaximumPaise},{(active ? "true" : "false")},true,
                gen_random_uuid(),clock_timestamp())
            """
        );
        return environment;
    }

    public async Task ExecuteAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(AdminConnectionString);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    public async Task<T> ScalarAsync<T>(string sql)
    {
        await using var connection = new NpgsqlConnection(AdminConnectionString);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        return (T)(await command.ExecuteScalarAsync())!;
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
