// Implements: work-contracts/WC-107-fundamental-customer-journey-integrity.md R011
// constitutional_basis: C-002, C-023, C-059, C-088, C-089

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.Extensions.Logging.Abstractions;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class AcquisitionTrialPostgresIntegrationTests : IAsyncLifetime
{
    private const string Password = "wc107trialtest";
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
        await ExecuteAsync(connection, "CREATE SCHEMA business; CREATE SCHEMA payload_store;");
        await ExecuteAsync(connection, "CREATE ROLE business_app;");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/19-ae01-employment-relationship.sql");
        await ExecuteAsync(connection, "ALTER TABLE business.employment_relationships ADD COLUMN acquisition_mode VARCHAR(8);");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/20b-ae01-context-configuration.sql");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/25-agent-admission.sql");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/31-agent-instance-binding.sql");
    }

    public async Task DisposeAsync()
    {
        if (_container is not null) await _container.DisposeAsync();
    }

    [Fact]
    public async Task TrialAndOwnerBindingPersistOnceAcrossReplay()
    {
        var options = new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
            .UseNpgsql(_connectionString).Options;
        var factory = new PooledDbContextFactory<EmploymentRelationshipDbContext>(options);
        var constitutionalGateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory, constitutionalGateway, NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var actorId = Guid.NewGuid();
        var admission = new AgentAdmission
        {
            TenantId = tenantId,
            ProfessionalTypeId = "DMA",
            ProfessionalVersion = "1.0.0",
            OwnerSubjectId = Guid.NewGuid(),
            State = AgentAdmissionState.Active,
        };
        await using (var seed = await factory.CreateDbContextAsync())
        {
            seed.AgentAdmissions.Add(admission);
            await seed.SaveChangesAsync();
        }
        var admitted = await relationships.AdmitFromAcquisitionAsync(
            tenantId, actorId, Guid.NewGuid(), "DMA", admission.AdmissionId,
            admission.ProfessionalVersion, Guid.NewGuid(),
            new RelationshipAcquisitionEvidence("TRIAL", "marketplace-r1", "terms-v1", DateTimeOffset.UtcNow),
            CancellationToken.None);
        await relationships.TransitionAsync(
            tenantId, admitted.Relationship.RelationshipId, actorId,
            RelationshipParticipantRole.Evaluator, EmploymentRelationshipState.Interviewing,
            Guid.NewGuid(), false, CancellationToken.None);
        var startsAt = DateTimeOffset.UtcNow;
        var trialId = Guid.NewGuid();
        var owners = new TrialOwnerGatewayStub
        {
            Wbe = new(trialId, startsAt, startsAt.AddDays(14)),
            Pr = new(trialId, "TRIAL_DEMONSTRATING", startsAt.AddDays(14)),
        };
        var trials = new RelationshipTrialService(factory, relationships, owners);
        var correlationId = Guid.NewGuid();

        var started = await trials.StartAsync(
            tenantId, admitted.Relationship.RelationshipId, actorId, correlationId, CancellationToken.None);
        var replayed = await trials.StartAsync(
            tenantId, admitted.Relationship.RelationshipId, actorId, correlationId, CancellationToken.None);

        Assert.Equal(trialId, started.TrialId);
        Assert.Equal(started.TrialId, replayed.TrialId);
        Assert.Equal(started.Status, replayed.Status);
        Assert.InRange((started.StartsAt - replayed.StartsAt).Duration(), TimeSpan.Zero, TimeSpan.FromMilliseconds(1));
        Assert.InRange((started.ExpiresAt - replayed.ExpiresAt).Duration(), TimeSpan.Zero, TimeSpan.FromMilliseconds(1));
        Assert.Equal(1, owners.WbeCalls);
        Assert.Equal(1, owners.PrCalls);
        await using var verification = await factory.CreateDbContextAsync();
        var relationship = await verification.EmploymentRelationships.SingleAsync();
        var binding = await verification.RelationshipTrialBindings.SingleAsync();
        Assert.Equal(EmploymentRelationshipState.TrialActive, relationship.State);
        Assert.Equal("TRIAL", relationship.AcquisitionMode);
        Assert.Equal("ACTIVE", binding.Status);
        Assert.Equal(trialId, binding.TrialId);
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