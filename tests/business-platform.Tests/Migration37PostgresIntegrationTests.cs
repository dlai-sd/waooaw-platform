// Implements: WC-095 Sections 10 and 13, infrastructure/postgres/init/37-wc095-performance-review-windows.sql
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063, C-079

using Npgsql;
using Testcontainers.PostgreSql;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class Migration37PostgresIntegrationTests : IAsyncLifetime
{
    private const string Password = "wc095reviewtest";
    private PostgreSqlContainer? _container;
    private string _ownerConnectionString = string.Empty;
    private string _businessConnectionString = string.Empty;

    public async Task InitializeAsync()
    {
        _container = new PostgreSqlBuilder("pgvector/pgvector:pg16")
            .WithDatabase("waooaw").WithUsername("waooaw").WithPassword(Password).Build();
        await _container.StartAsync();
        _ownerConnectionString = _container.GetConnectionString();
        await using var connection = new NpgsqlConnection(_ownerConnectionString);
        await connection.OpenAsync();
        await ExecuteAsync(connection, "CREATE SCHEMA IF NOT EXISTS business;");
        await ExecuteAsync(connection, $"""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'business_app') THEN
                    CREATE ROLE business_app LOGIN PASSWORD '{Password}';
                END IF;
            END $$;
            GRANT USAGE ON SCHEMA business TO business_app;
            """);
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/19-ae01-employment-relationship.sql");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/37-wc095-performance-review-windows.sql");
        _businessConnectionString = new NpgsqlConnectionStringBuilder(_ownerConnectionString)
        {
            Username = "business_app", Password = Password,
        }.ConnectionString;
    }

    public async Task DisposeAsync()
    {
        if (_container is not null) await _container.DisposeAsync();
    }

    [Fact]
    public async Task ReviewWindowsEnforceDimensionsOutcomesAppendOnlyAndTenantIsolation()
    {
        var tenantId = Guid.NewGuid();
        var otherTenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var reviewId = Guid.NewGuid();
        await using (var owner = new NpgsqlConnection(_ownerConnectionString))
        {
            await owner.OpenAsync();
            await ExecuteAsync(owner, $$"""
                INSERT INTO business.employment_relationships
                    (relationship_id, tenant_id, professional_type, evaluation_intent_id, initiating_participant_id)
                VALUES ('{{relationshipId:D}}', '{{tenantId:D}}', 'DMA', gen_random_uuid(), gen_random_uuid());
                INSERT INTO business.performance_review_windows
                    (review_id, tenant_id, relationship_id, agent_instance_id, skill_id, skill_version,
                     revision, policy_version, period_start, period_end, source_versions_json,
                     work_delivery_json, agent_quality_json, constitutional_performance_json,
                     commercial_usage_json, customer_business_outcome_json, customer_assessment_json,
                     trust_autonomy_json, recommendation, evidence_id)
                VALUES ('{{reviewId:D}}', '{{tenantId:D}}', '{{relationshipId:D}}', gen_random_uuid(),
                    'CUSTOMER_PROFILING', '1.0.0', 1, 'review-policy-1', NOW() - INTERVAL '30 days', NOW(),
                    '{"pr":"17","ce":"9","wbe":"12"}',
                    '{"state":"DELIVERED"}', '{"state":"GOOD"}', '{"state":"CONFORMANT"}',
                    '{"state":"WITHIN_ALLOWANCE"}', '{"state":"POOR","attributionLimits":"No causal guarantee"}',
                    '{"state":"CUSTOMER_DISPUTED"}', '{"state":"UNCHANGED"}',
                    'REASSESSMENT_REQUIRED', gen_random_uuid());
                """);

            var invalidOutcome = await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync(owner, $"""
                INSERT INTO business.performance_review_windows
                    (tenant_id, relationship_id, agent_instance_id, skill_id, skill_version, revision,
                     policy_version, period_start, period_end, source_versions_json, work_delivery_json,
                     agent_quality_json, constitutional_performance_json, commercial_usage_json,
                     customer_business_outcome_json, customer_assessment_json, trust_autonomy_json,
                     recommendation, evidence_id)
                SELECT tenant_id, relationship_id, agent_instance_id, skill_id, skill_version, 2,
                    policy_version, period_start, period_end, source_versions_json, work_delivery_json,
                    agent_quality_json, constitutional_performance_json, commercial_usage_json,
                    customer_business_outcome_json, customer_assessment_json, trust_autonomy_json,
                    'PROMOTE_OWN_PROMPT', gen_random_uuid()
                FROM business.performance_review_windows WHERE review_id = '{reviewId:D}';
                """));
            Assert.Equal(PostgresErrorCodes.CheckViolation, invalidOutcome.SqlState);

            var update = await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync(owner,
                $"UPDATE business.performance_review_windows SET recommendation = 'CONTINUE_CURRENT_MANDATE' WHERE review_id = '{reviewId:D}';"));
            Assert.Contains("append-only", update.MessageText);
            var delete = await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync(owner,
                $"DELETE FROM business.performance_review_windows WHERE review_id = '{reviewId:D}';"));
            Assert.Contains("append-only", delete.MessageText);
        }

        await using var business = new NpgsqlConnection(_businessConnectionString);
        await business.OpenAsync();
        await ExecuteAsync(business, $"SET app.current_tenant_id = '{otherTenantId:D}';");
        await using var command = business.CreateCommand();
        command.CommandText = "SELECT count(*) FROM business.performance_review_windows WHERE review_id = @review_id";
        command.Parameters.AddWithValue("review_id", reviewId);
        Assert.Equal(0L, (long)(await command.ExecuteScalarAsync())!);
    }

    private static async Task ExecuteAsync(NpgsqlConnection connection, string sql)
    {
        await using var command = connection.CreateCommand();
        command.CommandText = sql;
        await command.ExecuteNonQueryAsync();
    }

    private static async Task ExecuteFileAsync(NpgsqlConnection connection, string relativePath) =>
        await ExecuteAsync(connection, await File.ReadAllTextAsync(RepositoryPaths.Resolve(relativePath)));
}
