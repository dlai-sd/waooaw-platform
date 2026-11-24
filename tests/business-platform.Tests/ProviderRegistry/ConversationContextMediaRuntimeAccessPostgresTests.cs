// Implements: work-contracts/WC-169-paid-hire-and-connected-accounts.md WC169-R003
// constitutional_basis: C-009, C-023, C-063, C-065

using Npgsql;
using Testcontainers.PostgreSql;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ProviderRegistry;

/// <summary>
/// Reproduces the Demo state read on 2026-11-24 (conversation tables owned by bp_owner, forced row level security with a
/// per-tenant policy, no privilege for the application role) and proves the WC-169 init file gives the application role
/// exactly what the conversation code paths need and nothing more.
/// </summary>
public sealed class ConversationContextMediaRuntimeAccessPostgresTests : IAsyncLifetime
{
    private const string Migration =
        "infrastructure/postgres/init/99zzzzzzzz-wc169-01-conversation-context-media-runtime-access.sql";

    private static readonly Guid TenantA = Guid.Parse("11111111-1111-1111-1111-111111111111");
    private static readonly Guid TenantB = Guid.Parse("22222222-2222-2222-2222-222222222222");

    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("conversation_access")
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
        var tables = new[]
        {
            (
                "conversation_context_observations",
                "observation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID NOT NULL, value_json JSONB NOT NULL DEFAULT '{}', current BOOLEAN NOT NULL DEFAULT TRUE"
            ),
            (
                "conversation_context_summaries",
                "summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID NOT NULL, payload_reference TEXT NOT NULL DEFAULT 'p', current BOOLEAN NOT NULL DEFAULT TRUE, invalidation_reason TEXT, invalidated_at TIMESTAMPTZ"
            ),
            (
                "conversation_data_right_requests",
                "request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID NOT NULL, state TEXT NOT NULL DEFAULT 'PENDING_OWNER_DECISION'"
            ),
            (
                "whatsapp_media",
                "media_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID NOT NULL, state TEXT NOT NULL DEFAULT 'QUARANTINED', payload_reference TEXT, scanner_engine_version TEXT, scanner_policy_version TEXT, scanner_signature_version TEXT, scanner_signature_published_at TIMESTAMPTZ, verdict_digest TEXT, derivative_payload_references_json JSONB NOT NULL DEFAULT '[]', legal_hold BOOLEAN NOT NULL DEFAULT FALSE, terminal_at TIMESTAMPTZ, delete_after TIMESTAMPTZ NOT NULL DEFAULT now(), relationship_id UUID NOT NULL DEFAULT gen_random_uuid()"
            ),
        };
        var tableSql = string.Join(
            "\n",
            tables.Select(table =>
                $"""
                    CREATE TABLE business.{table.Item1} ({table.Item2});
                    ALTER TABLE business.{table.Item1} ENABLE ROW LEVEL SECURITY;
                    ALTER TABLE business.{table.Item1} FORCE ROW LEVEL SECURITY;
                    CREATE POLICY {table.Item1}_tenant_isolation ON business.{table.Item1}
                        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
                        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
                    CREATE POLICY {table.Item1}_seed_owner ON business.{table.Item1} TO bp_owner USING (true) WITH CHECK (true);
                    INSERT INTO business.{table.Item1} (tenant_id) VALUES ('{TenantA}'), ('{TenantB}');
                    """
            )
        );
        await ExecuteAsAdminAsync(
            $"""
            CREATE ROLE business_app NOLOGIN;
            CREATE ROLE bp_owner NOLOGIN;
            CREATE ROLE bp_runtime LOGIN PASSWORD 'synthetic-runtime-password' IN ROLE business_app;
            GRANT bp_owner TO test_owner;
            CREATE SCHEMA business AUTHORIZATION bp_owner;
            GRANT USAGE ON SCHEMA business TO business_app;
            SET ROLE bp_owner;
            {tableSql}
            CREATE TABLE business.conversation_migration_watermarks (migration_id TEXT PRIMARY KEY);
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

    private async Task<string?> RuntimeSqlStateAsync(string tenantSql, string sql)
    {
        try
        {
            await using var connection = new NpgsqlConnection(RuntimeConnectionString);
            await connection.OpenAsync();
            await using var command = new NpgsqlCommand(
                $"SELECT set_config('app.current_tenant_id', '{tenantSql}', false); {sql}",
                connection
            );
            await command.ExecuteNonQueryAsync();
            return null;
        }
        catch (PostgresException failure)
        {
            return failure.SqlState;
        }
    }

    private async Task<long> RuntimeCountAsync(Guid tenant, string table)
    {
        await using var connection = new NpgsqlConnection(RuntimeConnectionString);
        await connection.OpenAsync();
        await using (
            var set = new NpgsqlCommand(
                $"SELECT set_config('app.current_tenant_id', '{tenant}', false)",
                connection
            )
        )
            await set.ExecuteNonQueryAsync();
        await using var command = new NpgsqlCommand(
            $"SELECT count(*) FROM business.{table}",
            connection
        );
        return Convert.ToInt64(await command.ExecuteScalarAsync());
    }

    [Theory]
    [InlineData("conversation_context_observations")]
    [InlineData("conversation_context_summaries")]
    [InlineData("conversation_data_right_requests")]
    [InlineData("whatsapp_media")]
    public async Task WC169_R003_BeforeTheFixTheApplicationRoleIsDeniedTheTable(string table)
    {
        Assert.Equal(
            "42501",
            await RuntimeSqlStateAsync(TenantA.ToString(), $"SELECT count(*) FROM business.{table}")
        );
    }

    [Theory]
    [InlineData("conversation_context_observations")]
    [InlineData("conversation_context_summaries")]
    [InlineData("conversation_data_right_requests")]
    [InlineData("whatsapp_media")]
    public async Task WC169_R003_AfterTheFixTheApplicationSeesOnlyItsOwnTenantRows(string table)
    {
        await ApplyMigrationAsync();
        Assert.Equal(1, await RuntimeCountAsync(TenantA, table));
        Assert.Equal(1, await RuntimeCountAsync(TenantB, table));
        Assert.Equal(0, await RuntimeCountAsync(Guid.Empty, table));
    }

    [Fact]
    public async Task WC169_R003_TheApplicationCanDoOnlyWhatTheCodePathsDo()
    {
        await ApplyMigrationAsync();
        var a = TenantA.ToString();

        // Correcting a customer value flips the current flag on the old observation and inserts the new one.
        Assert.Null(
            await RuntimeSqlStateAsync(
                a,
                "UPDATE business.conversation_context_observations SET current = false"
            )
        );
        Assert.Null(
            await RuntimeSqlStateAsync(
                a,
                $"INSERT INTO business.conversation_context_observations (tenant_id) VALUES ('{a}')"
            )
        );
        Assert.Equal(
            "42501",
            await RuntimeSqlStateAsync(
                a,
                "UPDATE business.conversation_context_observations SET value_json = '1'"
            )
        );

        // Summaries can be invalidated, never created or rewritten by the application.
        Assert.Null(
            await RuntimeSqlStateAsync(
                a,
                "UPDATE business.conversation_context_summaries SET current = false, invalidation_reason = 'SOURCE_CORRECTED', invalidated_at = now()"
            )
        );
        Assert.Equal(
            "42501",
            await RuntimeSqlStateAsync(
                a,
                $"INSERT INTO business.conversation_context_summaries (tenant_id) VALUES ('{a}')"
            )
        );
        Assert.Equal(
            "42501",
            await RuntimeSqlStateAsync(
                a,
                "UPDATE business.conversation_context_summaries SET payload_reference = 'x'"
            )
        );

        // Data-right requests are created and read, never changed by the application.
        Assert.Null(
            await RuntimeSqlStateAsync(
                a,
                $"INSERT INTO business.conversation_data_right_requests (tenant_id) VALUES ('{a}')"
            )
        );
        Assert.Equal(
            "42501",
            await RuntimeSqlStateAsync(
                a,
                "UPDATE business.conversation_data_right_requests SET state = 'DONE'"
            )
        );

        // Media moves through its quarantine lifecycle but its identity never changes.
        Assert.Null(
            await RuntimeSqlStateAsync(
                a,
                "UPDATE business.whatsapp_media SET state = 'CLEAN', legal_hold = true, terminal_at = now()"
            )
        );
        Assert.Equal(
            "42501",
            await RuntimeSqlStateAsync(
                a,
                "UPDATE business.whatsapp_media SET tenant_id = gen_random_uuid()"
            )
        );

        // Another tenant's row cannot be written.
        Assert.Equal(
            "42501",
            await RuntimeSqlStateAsync(
                a,
                $"INSERT INTO business.whatsapp_media (tenant_id) VALUES ('{TenantB}')"
            )
        );

        foreach (
            var table in new[]
            {
                "conversation_context_observations",
                "conversation_context_summaries",
                "conversation_data_right_requests",
                "whatsapp_media",
            }
        )
            Assert.Equal("42501", await RuntimeSqlStateAsync(a, $"DELETE FROM business.{table}"));
    }

    [Fact]
    public async Task WC169_R003_TheFixIsIdempotentAndLeavesTheUnusedWatermarkTableClosed()
    {
        await ApplyMigrationAsync();
        await ApplyMigrationAsync();
        Assert.Equal(
            "42501",
            await RuntimeSqlStateAsync(
                TenantA.ToString(),
                "SELECT count(*) FROM business.conversation_migration_watermarks"
            )
        );
    }
}
