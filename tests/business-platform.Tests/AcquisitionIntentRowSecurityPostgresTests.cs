// Implements: work-contracts/WC-172-safe-to-charge-real-customers.md (Demo defect repairs: trial refused by row security)
// constitutional_basis: C-023, C-026, C-059, C-063

using Npgsql;
using Testcontainers.PostgreSql;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

/// <summary>
/// Reproduces the Demo failure (forced row security, no policy: every insert refused) with the real init files and proves
/// the policy lets a person who has not registered write and read only their own intent, and a tenant its own.
/// </summary>
public sealed class AcquisitionIntentRowSecurityPostgresTests : IAsyncLifetime
{
    private const string BaseTable =
        "infrastructure/postgres/init/49-wc112-acquisition-intents.sql";
    private const string QuoteMigration =
        "infrastructure/postgres/init/99zzzzzzzz-wc169-02-acquisition-hire-quote.sql";
    private const string RowSecurityMigration =
        "infrastructure/postgres/init/99zzzzzzzz-wc172-04-acquisition-intent-row-security.sql";
    private const string RowSecurityViolation = "42501";

    private static readonly string ActorOne = new('a', 64);
    private static readonly string ActorTwo = new('e', 64);
    private static readonly Guid Tenant = Guid.NewGuid();

    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("intent_rls")
        .WithUsername("test_owner")
        .WithPassword("synthetic-owner-password")
        .Build();

    private string RuntimeConnectionString =>
        new NpgsqlConnectionStringBuilder(_postgres.GetConnectionString())
        {
            Username = "bp_runtime",
            Password = "synthetic-runtime-password",
        }.ConnectionString;

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        await ExecuteAsAdminAsync(
            """
            CREATE ROLE business_app NOLOGIN;
            CREATE ROLE bp_owner NOLOGIN;
            CREATE ROLE bp_runtime LOGIN PASSWORD 'synthetic-runtime-password' IN ROLE business_app;
            GRANT bp_owner TO test_owner;
            CREATE SCHEMA business AUTHORIZATION bp_owner;
            GRANT USAGE ON SCHEMA business TO business_app;
            """
        );
        await ExecuteAsAdminAsync(
            "SET ROLE bp_owner;\n"
                + await File.ReadAllTextAsync(RepositoryPaths.Resolve(BaseTable))
                + "\nRESET ROLE;"
        );
        await ExecuteAsAdminAsync(
            await File.ReadAllTextAsync(RepositoryPaths.Resolve(QuoteMigration))
        );
        // What migration 60 does to every business table that has a tenant_id.
        await ExecuteAsAdminAsync(
            """
            SET ROLE bp_owner;
            ALTER TABLE business.acquisition_intents ENABLE ROW LEVEL SECURITY;
            ALTER TABLE business.acquisition_intents FORCE ROW LEVEL SECURITY;
            RESET ROLE;
            """
        );
    }

    public async Task DisposeAsync() => await _postgres.DisposeAsync();

    private async Task ExecuteAsAdminAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private async Task ApplyPolicyAsync()
    {
        var sql = await File.ReadAllTextAsync(RepositoryPaths.Resolve(RowSecurityMigration));
        // Applying the file twice must leave the same schema.
        await ExecuteAsAdminAsync(sql);
        await ExecuteAsAdminAsync(sql);
    }

    private static string Insert(Guid id, string actor, string tenant) =>
        $"""
            INSERT INTO business.acquisition_intents (
                acquisition_intent_id, actor_identity_hash, idempotency_key, tenant_id, professional_type,
                professional_version, mode, disclosure_revision, contract_version, contract_document_uri,
                contract_hash, material_request_hash, status, contract_accepted_at, expires_at)
            VALUES ('{id}', '{actor}', '{id}', {tenant}, 'DMA', '1.0.0', 'TRIAL', '1.0.0', '2026-07-18', '/c',
                '{new string('b', 64)}', '{new string('c', 64)}', 'PENDING_REGISTRATION', now(),
                now() + interval '1 hour')
            """;

    /// <summary>Runs the statements in one transaction as the application role; returns the SQLSTATE of a refusal, or null.</summary>
    private async Task<(string? SqlState, long Visible)> RunAsync(
        string? actorHash,
        string? tenant,
        string? insert
    )
    {
        await using var connection = new NpgsqlConnection(RuntimeConnectionString);
        await connection.OpenAsync();
        await using var transaction = await connection.BeginTransactionAsync();
        try
        {
            if (actorHash is not null)
                await using (
                    var set = new NpgsqlCommand(
                        $"SELECT set_config('app.acquisition_actor_hash', '{actorHash}', true)",
                        connection,
                        transaction
                    )
                )
                    await set.ExecuteNonQueryAsync();
            if (tenant is not null)
                await using (
                    var set = new NpgsqlCommand(
                        $"SELECT set_config('app.current_tenant_id', '{tenant}', true)",
                        connection,
                        transaction
                    )
                )
                    await set.ExecuteNonQueryAsync();
            if (insert is not null)
                await using (var write = new NpgsqlCommand(insert, connection, transaction))
                    await write.ExecuteNonQueryAsync();
            await using var count = new NpgsqlCommand(
                "SELECT count(*) FROM business.acquisition_intents",
                connection,
                transaction
            );
            var visible = (long)(await count.ExecuteScalarAsync())!;
            await transaction.CommitAsync();
            return (null, visible);
        }
        catch (PostgresException failure)
        {
            return (failure.SqlState, 0);
        }
    }

    [Fact]
    public async Task WithoutAPolicyForcedRowSecurityRefusesEveryTrialIntent()
    {
        var (state, _) = await RunAsync(ActorOne, null, Insert(Guid.NewGuid(), ActorOne, "NULL"));

        Assert.Equal(RowSecurityViolation, state);
    }

    [Fact]
    public async Task APersonWhoHasNotRegisteredWritesAndReadsOnlyTheirOwnIntent()
    {
        await ApplyPolicyAsync();
        var own = Guid.NewGuid();

        Assert.Equal((null, 1), await RunAsync(ActorOne, null, Insert(own, ActorOne, "NULL")));
        Assert.Equal((null, 1), await RunAsync(ActorOne, null, null));
        Assert.Equal((null, 0), await RunAsync(ActorTwo, null, null));
        Assert.Equal((null, 0), await RunAsync(null, null, null));
        Assert.Equal(
            RowSecurityViolation,
            (await RunAsync(null, null, Insert(Guid.NewGuid(), ActorOne, "NULL"))).SqlState
        );
        Assert.Equal(
            RowSecurityViolation,
            (await RunAsync(ActorTwo, null, Insert(Guid.NewGuid(), ActorOne, "NULL"))).SqlState
        );
    }

    [Fact]
    public async Task ATenantSeesItsOwnIntentsAndNobodyElses()
    {
        await ApplyPolicyAsync();
        var other = Guid.NewGuid();

        Assert.Equal(
            (null, 1),
            await RunAsync(null, Tenant.ToString(), Insert(Guid.NewGuid(), ActorOne, $"'{Tenant}'"))
        );
        Assert.Equal((null, 1), await RunAsync(null, Tenant.ToString(), null));
        Assert.Equal((null, 0), await RunAsync(null, other.ToString(), null));
        Assert.Equal(
            RowSecurityViolation,
            (
                await RunAsync(
                    null,
                    Tenant.ToString(),
                    Insert(Guid.NewGuid(), ActorTwo, $"'{other}'")
                )
            ).SqlState
        );
    }
}
