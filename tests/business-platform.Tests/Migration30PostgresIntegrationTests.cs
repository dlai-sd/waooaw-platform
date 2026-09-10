// Implements: WC-085 D-GOAL, infrastructure/postgres/init/30-relationship-goal-decisions.sql
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

using Npgsql;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class Migration30PostgresFixture : IAsyncLifetime
{
    private const string Password = "wc085testpass";
    private PostgreSqlContainer? _container;

    public string OwnerConnectionString { get; private set; } = string.Empty;
    public string BusinessConnectionString { get; private set; } = string.Empty;

    public async Task InitializeAsync()
    {
        _container = new PostgreSqlBuilder("pgvector/pgvector:pg16")
            .WithDatabase("waooaw")
            .WithUsername("waooaw")
            .WithPassword(Password)
            .Build();
        await _container.StartAsync();
        OwnerConnectionString = _container.GetConnectionString();
        await using var connection = new NpgsqlConnection(OwnerConnectionString);
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
        await ExecuteFileAsync(connection, RepositoryPaths.Resolve("infrastructure/postgres/init/19-ae01-employment-relationship.sql"));
        await ExecuteFileAsync(connection, RepositoryPaths.Resolve("infrastructure/postgres/init/20b-ae01-context-configuration.sql"));
        await ExecuteFileAsync(connection, RepositoryPaths.Resolve("infrastructure/postgres/init/30-relationship-goal-decisions.sql"));
        BusinessConnectionString = new NpgsqlConnectionStringBuilder(OwnerConnectionString)
        {
            Username = "business_app",
            Password = Password,
        }.ConnectionString;
    }

    public async Task DisposeAsync()
    {
        if (_container is not null) await _container.DisposeAsync();
    }

    public static async Task ExecuteAsync(NpgsqlConnection connection, string sql)
    {
        await using var command = connection.CreateCommand();
        command.CommandText = sql;
        await command.ExecuteNonQueryAsync();
    }

    private static async Task ExecuteFileAsync(NpgsqlConnection connection, string path) =>
        await ExecuteAsync(connection, await File.ReadAllTextAsync(path));
}

[CollectionDefinition("Migration30Postgres")]
public sealed class Migration30PostgresCollection : ICollectionFixture<Migration30PostgresFixture> { }

[Collection("Migration30Postgres")]
public sealed class Migration30PostgresIntegrationTests(Migration30PostgresFixture fixture)
{
    [Fact]
    public async Task ConcurrentIdenticalVerificationAppendsOneDecisionAndOneEvidenceRecord()
    {
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var actorId = Guid.NewGuid();
        var goalId = Guid.NewGuid();
        await using (var owner = new NpgsqlConnection(fixture.OwnerConnectionString))
        {
            await owner.OpenAsync();
            await Migration30PostgresFixture.ExecuteAsync(owner, $"""
                INSERT INTO business.employment_relationships
                    (relationship_id, tenant_id, professional_type, evaluation_intent_id,
                     initiating_participant_id, state, state_version)
                VALUES ('{relationshipId:D}', '{tenantId:D}', 'DMA', gen_random_uuid(), '{actorId:D}', 'DISCOVERED', 1);
                INSERT INTO business.relationship_goals
                    (goal_id, tenant_id, relationship_id, goal, measure, status)
                VALUES ('{goalId:D}', '{tenantId:D}', '{relationshipId:D}', 'Increase bookings', 'Confirmed bookings', 'ACCEPTED');
                INSERT INTO business.relationship_skill_configuration
                    (tenant_id, relationship_id, skill_id, skill_version, goal_id, status)
                VALUES ('{tenantId:D}', '{relationshipId:D}', 'local-seo', '1.0.0', '{goalId:D}', 'ACCEPTED');
                """);
        }
        var options = new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
            .UseNpgsql(fixture.OwnerConnectionString)
            .Options;
        var factory = new PooledDbContextFactory<EmploymentRelationshipDbContext>(options);
        var gateway = new CountingGateway();
        var service = new RelationshipConfigurationService(factory, gateway);
        var key = Guid.NewGuid();
        var hash = new string('a', 64);
        string goalVersion;
        await using (var db = await factory.CreateDbContextAsync())
        {
            goalVersion = RelationshipConfigurationService.GetGoalVersion(
                await db.RelationshipGoals.SingleAsync(item => item.GoalId == goalId));
        }

        var results = await Task.WhenAll(
            service.VerifyGoalAsync(
                tenantId, relationshipId, actorId, key, hash, "relationship-1", goalVersion,
                goalId, goalVersion, "VERIFIED", null, Guid.NewGuid(), CancellationToken.None),
            service.VerifyGoalAsync(
                tenantId, relationshipId, actorId, key, hash, "relationship-1", goalVersion,
                goalId, goalVersion, "VERIFIED", null, Guid.NewGuid(), CancellationToken.None));

        Assert.Equal(results[0].Decision.DecisionId, results[1].Decision.DecisionId);
        Assert.Single(results, result => result.Replayed);
        Assert.Equal(1, gateway.CallCount);
        await using var verificationDb = await factory.CreateDbContextAsync();
        Assert.Equal(1, await verificationDb.RelationshipGoalDecisions.CountAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId));
    }

    [Fact]
    public async Task GoalDecisionIsAppendOnlyAndTenantIsolated()
    {
        var tenantId = Guid.NewGuid();
        var otherTenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var goalId = Guid.NewGuid();
        var decisionId = Guid.NewGuid();
        await using (var owner = new NpgsqlConnection(fixture.OwnerConnectionString))
        {
            await owner.OpenAsync();
            await Migration30PostgresFixture.ExecuteAsync(owner, $"""
                INSERT INTO business.employment_relationships
                    (relationship_id, tenant_id, professional_type, evaluation_intent_id,
                     initiating_participant_id, state, state_version)
                VALUES ('{relationshipId:D}', '{tenantId:D}', 'DMA', gen_random_uuid(), gen_random_uuid(), 'DISCOVERED', 1);
                INSERT INTO business.relationship_goals
                    (goal_id, tenant_id, relationship_id, goal, measure, status)
                VALUES ('{goalId:D}', '{tenantId:D}', '{relationshipId:D}', 'Increase bookings', 'Confirmed bookings', 'ACCEPTED');
                INSERT INTO business.relationship_goal_decisions
                    (decision_id, tenant_id, relationship_id, goal_id, goal_version,
                     skill_id, skill_version, measure, review_cadence_months, decision,
                     actor_participant_id, expected_workspace_version, expected_subject_version,
                     idempotency_key, material_request_hash, evidence_id)
                VALUES ('{decisionId:D}', '{tenantId:D}', '{relationshipId:D}', '{goalId:D}', 'goal-1',
                    'local-seo', '1.0.0', 'Confirmed bookings', 2, 'VERIFIED',
                    gen_random_uuid(), 'relationship-1', 'goal-1', gen_random_uuid(), repeat('a', 64), gen_random_uuid());
                """);

            var update = await Assert.ThrowsAsync<PostgresException>(() => Migration30PostgresFixture.ExecuteAsync(
                owner, $"UPDATE business.relationship_goal_decisions SET decision = 'CHANGES_REQUESTED' WHERE decision_id = '{decisionId:D}';"));
            Assert.Contains("append-only", update.MessageText);
            var delete = await Assert.ThrowsAsync<PostgresException>(() => Migration30PostgresFixture.ExecuteAsync(
                owner, $"DELETE FROM business.relationship_goal_decisions WHERE decision_id = '{decisionId:D}';"));
            Assert.Contains("append-only", delete.MessageText);
            await Assert.ThrowsAsync<PostgresException>(() => Migration30PostgresFixture.ExecuteAsync(owner, $"""
                INSERT INTO business.relationship_goal_decisions
                    (tenant_id, relationship_id, goal_id, goal_version, skill_id, skill_version,
                     measure, review_cadence_months, decision, actor_participant_id,
                     expected_workspace_version, expected_subject_version, idempotency_key,
                     material_request_hash, evidence_id)
                VALUES ('{tenantId:D}', '{relationshipId:D}', '{goalId:D}', 'goal-1', 'local-seo', '1.0.0',
                    'Confirmed bookings', 2, 'CHANGES_REQUESTED', gen_random_uuid(),
                    'relationship-1', 'goal-1', gen_random_uuid(), repeat('b', 64), gen_random_uuid());
                """));
        }

        await using var business = new NpgsqlConnection(fixture.BusinessConnectionString);
        await business.OpenAsync();
        await Migration30PostgresFixture.ExecuteAsync(business, $"SET app.current_tenant_id = '{otherTenantId:D}';");
        await using var command = business.CreateCommand();
        command.CommandText = "SELECT count(*) FROM business.relationship_goal_decisions WHERE decision_id = @decision_id";
        command.Parameters.AddWithValue("decision_id", decisionId);
        Assert.Equal(0L, (long)(await command.ExecuteScalarAsync())!);
    }

    private sealed class CountingGateway : IRelationshipConstitutionalGateway
    {
        private int _callCount;
        public int CallCount => _callCount;

        public async Task<Guid> AuthorizeAndRecordAsync(
            Guid tenantId,
            Guid relationshipId,
            string professionalType,
            string actionType,
            Guid correlationId,
            object actionParameters,
            CancellationToken cancellationToken)
        {
            Interlocked.Increment(ref _callCount);
            await Task.Delay(100, cancellationToken);
            return Guid.NewGuid();
        }
    }
}