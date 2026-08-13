// Implements: WC-065 WC065-06, infrastructure/postgres/init/24-offerability-decision.sql
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class Migration24PostgresFixture : IAsyncLifetime
{
    private const string Password = "wc065testpass";
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
        await ExecuteAsync(connection, "CREATE SCHEMA IF NOT EXISTS business;");
        await ExecuteAsync(connection, $"""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'business_app') THEN
                    CREATE ROLE business_app LOGIN PASSWORD '{Password}';
                END IF;
            END $$;
            GRANT USAGE ON SCHEMA business TO business_app;
            """);
        await ExecuteFileAsync(connection, RepoPath("infrastructure/postgres/init/19-ae01-employment-relationship.sql"));
        await ExecuteFileAsync(connection, RepoPath("infrastructure/postgres/init/24-offerability-decision.sql"));
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

    public static string RepoPath(string relative) =>
        new[] { Path.Combine("/workspace", relative), Path.Combine("/workspaces/waooaw-platform", relative) }
            .First(File.Exists);

    public static async Task ExecuteAsync(NpgsqlConnection connection, string sql)
    {
        await using var command = connection.CreateCommand();
        command.CommandText = sql;
        await command.ExecuteNonQueryAsync();
    }

    private static async Task ExecuteFileAsync(NpgsqlConnection connection, string path) =>
        await ExecuteAsync(connection, await File.ReadAllTextAsync(path));
}

[CollectionDefinition("Migration24Postgres")]
public sealed class Migration24PostgresCollection : ICollectionFixture<Migration24PostgresFixture> { }

[Collection("Migration24Postgres")]
public sealed class Migration24PostgresIntegrationTests(Migration24PostgresFixture fixture)
{
    [Fact]
    public async Task ConcurrentIdenticalEvaluationRecordsOwnerAndEvidenceOnce()
    {
        var tenantId = Guid.NewGuid();
        var relationshipId = await InsertRelationshipAsync(tenantId);
        var options = new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
            .UseNpgsql(fixture.OwnerConnectionString)
            .Options;
        var factory = new PooledDbContextFactory<EmploymentRelationshipDbContext>(options);
        var owner = new DelayedOwnerGateway();
        var constitutional = new CountingConstitutionalGateway();
        var service = new OfferabilityOrchestrationService(
            owner,
            constitutional,
            factory,
            new OfferabilityService());
        var request = new OfferabilityEvaluationRequest(
            tenantId,
            relationshipId,
            1,
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            "dma-starter-v1",
            "DMA",
            "STARTER",
            7_000);

        var decisions = await Task.WhenAll(
            service.EvaluateAsync(request, CancellationToken.None),
            service.EvaluateAsync(request, CancellationToken.None));

        Assert.Equal(decisions[0].DecisionId, decisions[1].DecisionId);
        Assert.Equal(1, owner.CallCount);
        Assert.Equal(1, constitutional.CallCount);
    }

    [Fact]
    public async Task ForcedRlsHidesAnotherTenantsDecision()
    {
        var tenantA = Guid.NewGuid();
        var tenantB = Guid.NewGuid();
        var relationshipId = await InsertRelationshipAndDecisionAsync(tenantA);
        await using var business = new NpgsqlConnection(fixture.BusinessConnectionString);
        await business.OpenAsync();
        await Migration24PostgresFixture.ExecuteAsync(business, $"SET app.current_tenant_id = '{tenantB:D}';");
        await using var command = business.CreateCommand();
        command.CommandText = "SELECT count(*) FROM business.offerability_decisions WHERE relationship_id = @relationship_id";
        command.Parameters.AddWithValue("relationship_id", relationshipId);

        Assert.Equal(0L, (long)(await command.ExecuteScalarAsync())!);
    }

    [Fact]
    public async Task DecisionCannotBeUpdatedOrDeleted()
    {
        var tenantId = Guid.NewGuid();
        var relationshipId = await InsertRelationshipAndDecisionAsync(tenantId);
        await using var owner = new NpgsqlConnection(fixture.OwnerConnectionString);
        await owner.OpenAsync();

        var update = await Assert.ThrowsAsync<PostgresException>(() => Migration24PostgresFixture.ExecuteAsync(
            owner, $"UPDATE business.offerability_decisions SET disposition = 'BLOCK' WHERE relationship_id = '{relationshipId:D}';"));
        Assert.Contains("append-only", update.MessageText);
        var delete = await Assert.ThrowsAsync<PostgresException>(() => Migration24PostgresFixture.ExecuteAsync(
            owner, $"DELETE FROM business.offerability_decisions WHERE relationship_id = '{relationshipId:D}';"));
        Assert.Contains("append-only", delete.MessageText);
    }

    private async Task<Guid> InsertRelationshipAndDecisionAsync(Guid tenantId)
    {
        var relationshipId = await InsertRelationshipAsync(tenantId);
        await using var owner = new NpgsqlConnection(fixture.OwnerConnectionString);
        await owner.OpenAsync();
        await Migration24PostgresFixture.ExecuteAsync(owner, $"""
            INSERT INTO business.offerability_decisions
                (tenant_id, relationship_id, idempotency_key, material_request_hash,
                 relationship_state_version, policy_version,
                 disposition, direct_contribution_amount, owner_versions_json, reasons_json,
                 evidence_id, expires_at)
                VALUES ('{tenantId:D}', '{relationshipId:D}', gen_random_uuid(), repeat('a', 64),
                    1, 'FA-047-v1', 'ALLOW', 2000,
                    jsonb_build_object('WBE', 'validation-7'), '[]', gen_random_uuid(), now() + interval '1 day');
            """);
        return relationshipId;
    }

    private async Task<Guid> InsertRelationshipAsync(Guid tenantId)
    {
        var relationshipId = Guid.NewGuid();
        await using var owner = new NpgsqlConnection(fixture.OwnerConnectionString);
        await owner.OpenAsync();
        await Migration24PostgresFixture.ExecuteAsync(owner, $"""
            INSERT INTO business.employment_relationships
                (relationship_id, tenant_id, professional_type, evaluation_intent_id,
                 initiating_participant_id, state, state_version)
            VALUES ('{relationshipId:D}', '{tenantId:D}', 'DMA', gen_random_uuid(), gen_random_uuid(), 'DISCOVERED', 1);
            """);
        return relationshipId;
    }

    private sealed class DelayedOwnerGateway : IOfferabilityOwnerGateway
    {
        private int _callCount;
        public int CallCount => _callCount;

        public async Task<OwnerOfferabilityValidation?> ValidateAsync(
            OfferabilityEvaluationRequest request,
            CancellationToken cancellationToken)
        {
            Interlocked.Increment(ref _callCount);
            await Task.Delay(100, cancellationToken);
            return new OwnerOfferabilityValidation(
                "APPROVED",
                5_000,
                6_250,
                request.ProposedPricePaise,
                2_000,
                "wbe-validation-7",
                DateTimeOffset.UtcNow);
        }
    }

    private sealed class CountingConstitutionalGateway : IRelationshipConstitutionalGateway
    {
        private int _callCount;
        public int CallCount => _callCount;

        public Task<Guid> AuthorizeAndRecordAsync(
            Guid tenantId,
            Guid relationshipId,
            string professionalType,
            string actionType,
            Guid correlationId,
            object actionParameters,
            CancellationToken cancellationToken)
        {
            Interlocked.Increment(ref _callCount);
            return Task.FromResult(Guid.NewGuid());
        }
    }
}