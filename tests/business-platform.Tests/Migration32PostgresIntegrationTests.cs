// Implements: WC-088, infrastructure/postgres/init/32-relationship-skill-decisions.sql
// constitutional_basis: C-005, C-007, C-023, C-026, C-059

using Npgsql;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class Migration32PostgresIntegrationTests : IAsyncLifetime
{
    private const string Password = "wc088testpass";
    private PostgreSqlContainer? _container;
    private string _ownerConnectionString = string.Empty;
    private string _businessConnectionString = string.Empty;

    public async Task InitializeAsync()
    {
        _container = new PostgreSqlBuilder("pgvector/pgvector:pg16")
            .WithDatabase("waooaw")
            .WithUsername("waooaw")
            .WithPassword(Password)
            .Build();
        await _container.StartAsync();
        _ownerConnectionString = _container.GetConnectionString();
        await using var connection = new NpgsqlConnection(_ownerConnectionString);
        await connection.OpenAsync();
        await ExecuteAsync(connection, "CREATE SCHEMA IF NOT EXISTS business; CREATE SCHEMA IF NOT EXISTS payload_store;");
        await ExecuteAsync(connection, $"""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'business_app') THEN
                    CREATE ROLE business_app LOGIN PASSWORD '{Password}';
                END IF;
            END $$;
            GRANT USAGE ON SCHEMA business, payload_store TO business_app;
            """);
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/19-ae01-employment-relationship.sql");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/20b-ae01-context-configuration.sql");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/25-agent-admission.sql");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/31-agent-instance-binding.sql");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/32-relationship-skill-decisions.sql");
        _businessConnectionString = new NpgsqlConnectionStringBuilder(_ownerConnectionString)
        {
            Username = "business_app",
            Password = Password,
        }.ConnectionString;
    }

    public async Task DisposeAsync()
    {
        if (_container is not null) await _container.DisposeAsync();
    }

    [Fact]
    public async Task SkillDecisionIsRelationshipBoundAppendOnlyAndTenantIsolated()
    {
        var tenantId = Guid.NewGuid();
        var otherTenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var otherRelationshipId = Guid.NewGuid();
        var configurationId = Guid.NewGuid();
        var decisionId = Guid.NewGuid();
        await using (var owner = new NpgsqlConnection(_ownerConnectionString))
        {
            await owner.OpenAsync();
            await ExecuteAsync(owner, $"""
                INSERT INTO business.employment_relationships
                    (relationship_id, tenant_id, professional_type, evaluation_intent_id, initiating_participant_id)
                VALUES
                    ('{relationshipId:D}', '{tenantId:D}', 'DMA', gen_random_uuid(), gen_random_uuid()),
                    ('{otherRelationshipId:D}', '{tenantId:D}', 'DMA', gen_random_uuid(), gen_random_uuid());
                INSERT INTO business.relationship_skill_configuration
                    (configuration_id, tenant_id, relationship_id, skill_id, skill_version)
                VALUES ('{configurationId:D}', '{tenantId:D}', '{relationshipId:D}', 'local-seo', '1.0.0');
                INSERT INTO business.relationship_skill_decisions
                    (decision_id, tenant_id, relationship_id, configuration_id, skill_id, skill_version,
                     decision, actor_participant_id, expected_workspace_version, expected_subject_version,
                     idempotency_key, material_request_hash, evidence_id)
                VALUES ('{decisionId:D}', '{tenantId:D}', '{relationshipId:D}', '{configurationId:D}',
                    'local-seo', '1.0.0', 'ACCEPT_SKILL', gen_random_uuid(), 'relationship-1',
                    'skill-1', gen_random_uuid(), repeat('a', 64), gen_random_uuid());
                UPDATE business.relationship_skill_configuration
                SET status = 'SELECTED'
                WHERE configuration_id = '{configurationId:D}';
                """);

            var crossRelationship = await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync(owner, $"""
                INSERT INTO business.relationship_skill_decisions
                    (tenant_id, relationship_id, configuration_id, skill_id, skill_version,
                     decision, actor_participant_id, expected_workspace_version, expected_subject_version,
                     idempotency_key, material_request_hash, evidence_id)
                VALUES ('{tenantId:D}', '{otherRelationshipId:D}', '{configurationId:D}',
                    'local-seo', '1.0.0', 'SELECT_SKILL', gen_random_uuid(), 'relationship-1',
                    'skill-1', gen_random_uuid(), repeat('b', 64), gen_random_uuid());
                """));
            Assert.Equal(PostgresErrorCodes.ForeignKeyViolation, crossRelationship.SqlState);

            var update = await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync(owner,
                $"UPDATE business.relationship_skill_decisions SET decision = 'DEFER_SKILL' WHERE decision_id = '{decisionId:D}';"));
            Assert.Contains("append-only", update.MessageText);
            var delete = await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync(owner,
                $"DELETE FROM business.relationship_skill_decisions WHERE decision_id = '{decisionId:D}';"));
            Assert.Contains("append-only", delete.MessageText);
        }

        await using var business = new NpgsqlConnection(_businessConnectionString);
        await business.OpenAsync();
        await ExecuteAsync(business, $"SET app.current_tenant_id = '{otherTenantId:D}';");
        await using var command = business.CreateCommand();
        command.CommandText = "SELECT count(*) FROM business.relationship_skill_decisions WHERE decision_id = @decision_id";
        command.Parameters.AddWithValue("decision_id", decisionId);
        Assert.Equal(0L, (long)(await command.ExecuteScalarAsync())!);
    }

    [Fact]
    public async Task ConcurrentIdenticalSkillDecisionAppendsOnceAndReplays()
    {
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var configurationId = Guid.NewGuid();
        await using (var owner = new NpgsqlConnection(_ownerConnectionString))
        {
            await owner.OpenAsync();
            await ExecuteAsync(owner, $"""
                INSERT INTO business.employment_relationships
                    (relationship_id, tenant_id, professional_type, evaluation_intent_id, initiating_participant_id)
                VALUES ('{relationshipId:D}', '{tenantId:D}', 'DMA', gen_random_uuid(), gen_random_uuid());
                INSERT INTO business.relationship_skill_configuration
                    (configuration_id, tenant_id, relationship_id, skill_id, skill_version)
                VALUES ('{configurationId:D}', '{tenantId:D}', '{relationshipId:D}', 'local-seo', '1.0.0');
                """);
        }
        var options = new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
            .UseNpgsql(_ownerConnectionString)
            .Options;
        var factory = new PooledDbContextFactory<EmploymentRelationshipDbContext>(options);
        var gateway = new CountingGateway();
        var service = new RelationshipConfigurationService(factory, gateway);
        var key = Guid.NewGuid();
        string skillVersion;
        await using (var db = await factory.CreateDbContextAsync())
        {
            skillVersion = RelationshipConfigurationService.GetSkillVersion(
                await db.RelationshipSkillConfigurations.SingleAsync(item => item.ConfigurationId == configurationId));
        }

        var results = await Task.WhenAll(Enumerable.Range(0, 2).Select(_ => service.DecideSkillAsync(
            tenantId, relationshipId, Guid.NewGuid(), key, new string('f', 64), "relationship-0",
            skillVersion, configurationId, "local-seo", "1.0.0", "ACCEPT_SKILL",
            Guid.NewGuid(), CancellationToken.None)));

        Assert.Equal(results[0].Decision.DecisionId, results[1].Decision.DecisionId);
        Assert.Single(results, result => result.Replayed);
        Assert.Equal(1, gateway.CallCount);
        await using var verificationDb = await factory.CreateDbContextAsync();
        Assert.Equal(1, await verificationDb.RelationshipSkillDecisions.CountAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId));
    }

    private static async Task ExecuteAsync(NpgsqlConnection connection, string sql)
    {
        await using var command = connection.CreateCommand();
        command.CommandText = sql;
        await command.ExecuteNonQueryAsync();
    }

    private static async Task ExecuteFileAsync(NpgsqlConnection connection, string relativePath) =>
        await ExecuteAsync(connection, await File.ReadAllTextAsync(RepositoryPaths.Resolve(relativePath)));

    private sealed class CountingGateway : IRelationshipConstitutionalGateway
    {
        private int _callCount;
        public int CallCount => _callCount;

        public async Task<Guid> AuthorizeAndRecordAsync(
            Guid tenantId, Guid relationshipId, string professionalType, string actionType,
            Guid correlationId, object actionParameters, CancellationToken cancellationToken)
        {
            Interlocked.Increment(ref _callCount);
            await Task.Delay(100, cancellationToken);
            return Guid.NewGuid();
        }
    }
}