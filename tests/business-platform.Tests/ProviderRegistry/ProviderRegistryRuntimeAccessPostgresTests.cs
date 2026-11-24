// Implements: work-contracts/WC-168-operator-console-works-on-demo.md WC168-R003, WC168-R005
// constitutional_basis: C-009, C-023, C-063, C-065

using Npgsql;
using Testcontainers.PostgreSql;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ProviderRegistry;

/// <summary>
/// Reproduces the Demo state read on 2026-11-24 (table owned by bp_owner, row level security enabled and forced, no policy,
/// no privilege for the application role) and proves the WC-168 init file gives the application role exactly what the
/// Founder provider screen needs and nothing more.
/// </summary>
public sealed class ProviderRegistryRuntimeAccessPostgresTests : IAsyncLifetime
{
    private const string Migration =
        "infrastructure/postgres/init/99zzzzzzzz-wc168-01-provider-registry-runtime-access.sql";

    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("provider_registry")
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
            CREATE ROLE bp_verifier NOLOGIN;
            CREATE ROLE bp_runtime LOGIN PASSWORD 'synthetic-runtime-password' IN ROLE business_app;
            GRANT bp_owner TO test_owner;
            CREATE SCHEMA business AUTHORIZATION bp_owner;
            GRANT USAGE ON SCHEMA business TO business_app;
            SET ROLE bp_owner;
            CREATE TABLE business.provider_configs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID,
                provider_name TEXT NOT NULL,
                active BOOLEAN NOT NULL DEFAULT true,
                active_credential_version_id UUID
            );
            GRANT SELECT ON business.provider_configs TO bp_verifier;
            ALTER TABLE business.provider_configs ENABLE ROW LEVEL SECURITY;
            ALTER TABLE business.provider_configs FORCE ROW LEVEL SECURITY;
            CREATE POLICY seed_owner ON business.provider_configs TO bp_owner USING (true) WITH CHECK (true);
            INSERT INTO business.provider_configs (tenant_id, provider_name)
            VALUES (NULL, 'meta'), (gen_random_uuid(), 'tenant-only');
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

    private async Task ApplyMigrationAsync() =>
        await ExecuteAsAdminAsync(await File.ReadAllTextAsync(RepositoryPaths.Resolve(Migration)));

    private async Task<long> RuntimeScalarAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(RuntimeConnectionString);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        return Convert.ToInt64(await command.ExecuteScalarAsync());
    }

    private async Task<string?> RuntimeSqlStateAsync(string sql)
    {
        try
        {
            await using var connection = new NpgsqlConnection(RuntimeConnectionString);
            await connection.OpenAsync();
            await using var command = new NpgsqlCommand(sql, connection);
            await command.ExecuteNonQueryAsync();
            return null;
        }
        catch (PostgresException failure)
        {
            return failure.SqlState;
        }
    }

    [Fact]
    public async Task WC168_R003_BeforeTheFixTheApplicationRoleIsDeniedTheTable()
    {
        Assert.Equal(
            "42501",
            await RuntimeSqlStateAsync("SELECT count(*) FROM business.provider_configs")
        );
    }

    [Fact]
    public async Task WC168_R003_AfterTheFixTheApplicationReadsPlatformRowsOnlyWhenNoTenantIsSet()
    {
        await ApplyMigrationAsync();
        Assert.Equal(1, await RuntimeScalarAsync("SELECT count(*) FROM business.provider_configs"));
    }

    [Fact]
    public async Task WC168_R005_TheApplicationCanCreateAPlatformProviderAndActivateACredentialVersionButNothingElse()
    {
        await ApplyMigrationAsync();
        Assert.Null(
            await RuntimeSqlStateAsync(
                "INSERT INTO business.provider_configs (tenant_id, provider_name) VALUES (NULL, 'openai')"
            )
        );
        Assert.Null(
            await RuntimeSqlStateAsync(
                "UPDATE business.provider_configs SET active_credential_version_id = gen_random_uuid() WHERE provider_name = 'meta'"
            )
        );
        // A tenant row cannot be created through the platform provider screen (row level security refuses it).
        Assert.Equal(
            "42501",
            await RuntimeSqlStateAsync(
                "INSERT INTO business.provider_configs (tenant_id, provider_name) VALUES (gen_random_uuid(), 'x')"
            )
        );
        // No other column can be changed and no row can be deleted.
        Assert.Equal(
            "42501",
            await RuntimeSqlStateAsync(
                "UPDATE business.provider_configs SET provider_name = 'z' WHERE provider_name = 'meta'"
            )
        );
        Assert.Equal(
            "42501",
            await RuntimeSqlStateAsync(
                "DELETE FROM business.provider_configs WHERE provider_name = 'openai'"
            )
        );
    }

    [Fact]
    public async Task WC168_R003_TheFixIsIdempotentAndKeepsTheVerifierReadOnly()
    {
        await ApplyMigrationAsync();
        await ApplyMigrationAsync();
        Assert.Equal(1, await RuntimeScalarAsync("SELECT count(*) FROM business.provider_configs"));
        Assert.Equal(
            1,
            await RuntimeScalarAsync(
                "SELECT CASE WHEN has_table_privilege('bp_verifier', 'business.provider_configs', 'SELECT') AND NOT has_table_privilege('bp_verifier', 'business.provider_configs', 'INSERT') THEN 1 ELSE 0 END"
            )
        );
    }
}
