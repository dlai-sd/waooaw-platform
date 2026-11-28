// Implements: work-contracts/WC-178-demo-live-journey-defects.md WC178-R004, WC178-R005
// Constitutional basis: C-023, C-026, C-059, C-088

using Npgsql;
using Testcontainers.PostgreSql;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

/// <summary>
/// The Trial table as Demo has it: forced row security, a CHECK on the four legacy agent codes and a 20-character column.
/// The two repair migrations must let the billing role record a Trial of a long agent type, and nobody else.
/// </summary>
public sealed class TrialAllocationsPolicyPostgresTests : IAsyncLifetime
{
    private const string WidenMigration =
        "infrastructure/postgres/init/99zzzzzzzz-wc176-03-trial-agent-type.sql";
    private const string PolicyMigration =
        "infrastructure/postgres/init/99zzzzzzzz-wc178-01-trial-allocations-billing-policy.sql";
    private const string AgentType = "DIGITAL_MARKETING_LOCAL_SERVICE";

    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("trial_policy")
        .WithUsername("test_owner")
        .WithPassword("owner-password")
        .Build();

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        await ExecuteAsync(
            """
            CREATE ROLE bp_owner; CREATE ROLE wbe_app LOGIN PASSWORD 'wbe-password'; CREATE ROLE business_app LOGIN PASSWORD 'bp-password';
            CREATE SCHEMA business AUTHORIZATION bp_owner;
            GRANT USAGE ON SCHEMA business TO wbe_app, business_app;
            SET ROLE bp_owner;
            CREATE TABLE business.trial_allocations (
                trial_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                customer_id UUID NOT NULL,
                agent_type VARCHAR(20) NOT NULL CHECK (agent_type IN ('DMA','DPA','DCA','DSA')),
                agent_version VARCHAR(32) NOT NULL,
                started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ NOT NULL,
                status VARCHAR(10) NOT NULL DEFAULT 'ACTIVE'
            );
            GRANT SELECT, INSERT, UPDATE ON business.trial_allocations TO wbe_app, business_app;
            ALTER TABLE business.trial_allocations ENABLE ROW LEVEL SECURITY;
            ALTER TABLE business.trial_allocations FORCE ROW LEVEL SECURITY;
            RESET ROLE;
            """
        );
    }

    public async Task DisposeAsync() => await _postgres.DisposeAsync();

    private async Task ExecuteAsync(string sql, string? user = null, string? password = null)
    {
        var connectionString = user is null
            ? _postgres.GetConnectionString()
            : new NpgsqlConnectionStringBuilder(_postgres.GetConnectionString())
            {
                Username = user,
                Password = password,
            }.ConnectionString;
        await using var connection = new NpgsqlConnection(connectionString);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private static string Insert(Guid customer) =>
        $"INSERT INTO business.trial_allocations (customer_id, agent_type, agent_version, expires_at) VALUES ('{customer}', '{AgentType}', '1.0.0', now() + interval '14 days')";

    private static Task<string> Migration(string path) =>
        File.ReadAllTextAsync(RepositoryPaths.Resolve(path));

    [Fact]
    public async Task ADemoShapedTrialTableRefusesAnyTrialOfALongAgentTypeBeforeTheRepairs()
    {
        await Assert.ThrowsAsync<PostgresException>(() =>
            ExecuteAsync(Insert(Guid.NewGuid()), "wbe_app", "wbe-password")
        );
    }

    [Fact]
    public async Task TheBillingRoleRecordsATrialOfALongAgentTypeAndOtherRolesStillCannot()
    {
        await ExecuteAsync(await Migration(WidenMigration));
        // Without the policy the forced row security still refuses the insert.
        var refused = await Assert.ThrowsAsync<PostgresException>(() =>
            ExecuteAsync(Insert(Guid.NewGuid()), "wbe_app", "wbe-password")
        );
        Assert.Equal("42501", refused.SqlState);

        await ExecuteAsync(await Migration(PolicyMigration));
        await ExecuteAsync(await Migration(PolicyMigration));
        var customer = Guid.NewGuid();
        await ExecuteAsync(Insert(customer), "wbe_app", "wbe-password");

        await using var connection = new NpgsqlConnection(
            new NpgsqlConnectionStringBuilder(_postgres.GetConnectionString())
            {
                Username = "wbe_app",
                Password = "wbe-password",
            }.ConnectionString
        );
        await connection.OpenAsync();
        await using var read = new NpgsqlCommand(
            $"SELECT count(*) FROM business.trial_allocations WHERE customer_id = '{customer}'",
            connection
        );
        Assert.Equal(1L, await read.ExecuteScalarAsync());

        var other = await Assert.ThrowsAsync<PostgresException>(() =>
            ExecuteAsync(Insert(Guid.NewGuid()), "business_app", "bp-password")
        );
        Assert.Equal("42501", other.SqlState);
        var shape = await Assert.ThrowsAsync<PostgresException>(() =>
            ExecuteAsync(
                "INSERT INTO business.trial_allocations (customer_id, agent_type, agent_version, expires_at) VALUES (gen_random_uuid(), 'lower_case', '1.0.0', now())",
                "wbe_app",
                "wbe-password"
            )
        );
        Assert.Equal("23514", shape.SqlState);
    }
}
