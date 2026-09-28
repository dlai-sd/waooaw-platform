// Implements: work-contracts/WC-107-fundamental-customer-journey-integrity.md R015-R016
// constitutional_basis: C-002, C-023, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class MyAgentsSelectionPostgresIntegrationTests : IAsyncLifetime
{
    private const string Password = "wc107selectiontest";
    private PostgreSqlContainer? _container;
    private string _connectionString = string.Empty;

    public async Task InitializeAsync()
    {
        _container = new PostgreSqlBuilder("pgvector/pgvector:pg16")
            .WithDatabase("waooaw").WithUsername("waooaw").WithPassword(Password).Build();
        await _container.StartAsync();
        _connectionString = _container.GetConnectionString();
        await using var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync();
        await ExecuteAsync(connection, "CREATE SCHEMA business; CREATE SCHEMA payload_store; CREATE ROLE business_app;");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/19-ae01-employment-relationship.sql");
        await ExecuteAsync(connection, "ALTER TABLE business.employment_relationships ADD COLUMN acquisition_mode VARCHAR(8);");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/20b-ae01-context-configuration.sql");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/25-agent-admission.sql");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/31-agent-instance-binding.sql");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/46-my-agents-selection-flash.sql");
    }

    public async Task DisposeAsync()
    {
        if (_container is not null) await _container.DisposeAsync();
    }

    [Fact]
    public async Task SelectionIsConsumedExactlyOnceAndDatabaseEnforcesFiveMinuteExpiry()
    {
        var factory = new PooledDbContextFactory<EmploymentRelationshipDbContext>(
            new DbContextOptionsBuilder<EmploymentRelationshipDbContext>().UseNpgsql(_connectionString).Options);
        var clock = new AdjustableTimeProvider(new DateTimeOffset(2026, 9, 28, 12, 0, 0, TimeSpan.Zero));
        var service = new MyAgentsSelectionService(factory, clock);
        var tenantId = Guid.NewGuid();
        var actorId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        await using (var db = await factory.CreateDbContextAsync())
        {
            db.EmploymentRelationships.Add(new EmploymentRelationship
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                InitiatingParticipantId = actorId,
                ProfessionalType = "DMA",
                AcquisitionMode = "TRIAL",
                State = EmploymentRelationshipState.TrialActive,
            });
            db.RelationshipParticipants.Add(new RelationshipParticipant
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ParticipantId = actorId,
                Role = RelationshipParticipantRole.Evaluator,
                BoundEvidenceId = Guid.NewGuid(),
            });
            db.RelationshipTrialBindings.Add(new RelationshipTrialBinding
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                CustomerId = actorId,
                CorrelationId = Guid.NewGuid(),
                TrialId = Guid.NewGuid(),
                StartsAt = clock.GetUtcNow(),
                ExpiresAt = clock.GetUtcNow().AddDays(14),
                Status = "ACTIVE",
            });
            await db.SaveChangesAsync();
        }
        var created = await service.CreateAsync(
            tenantId, actorId, relationshipId, "TRIAL_STARTED", CancellationToken.None);

        var attempts = await Task.WhenAll(
            service.ConsumeAsync(tenantId, actorId, created.Handle, CancellationToken.None),
            service.ConsumeAsync(tenantId, actorId, created.Handle, CancellationToken.None));

        Assert.Single(attempts, result => result is not null);
        await using var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync();
        var invalidExpiry = await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync(connection, $"""
            INSERT INTO business.my_agents_selection_flash
                (handle_hash, tenant_id, actor_participant_id, relationship_id, outcome_kind, created_at, expires_at)
            VALUES (repeat('f', 64), '{tenantId:D}', '{actorId:D}', '{relationshipId:D}',
                'TRIAL_STARTED', NOW(), NOW() + INTERVAL '6 minutes');
            """));
        Assert.Equal(PostgresErrorCodes.CheckViolation, invalidExpiry.SqlState);
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