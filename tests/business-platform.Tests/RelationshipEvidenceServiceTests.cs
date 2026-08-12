// Implements: work-contracts/WC-060-goal005-ae01-continuity-evidence-stop.md WC060-05
// constitutional_basis: C-005, C-023, C-026, C-059, C-063

using Google.Protobuf.WellKnownTypes;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.ConstitutionalEngine.Grpc;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class RelationshipEvidenceServiceTests
{
    [Fact]
    public async Task CctAe01Evidence01_EvaluatorSeesTrialButNotPaymentEvidence()
    {
        var context = await CreateAsync(RelationshipParticipantRole.Evaluator);

        var items = await context.Service.ListAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId, CancellationToken.None);

        Assert.Single(items);
        Assert.Equal("TRIAL_STARTED", items[0].Subject);
    }

    [Fact]
    public async Task CctAe01Evidence01_InactiveOrForeignParticipantGetsNoExistenceDisclosure()
    {
        var context = await CreateAsync(RelationshipParticipantRole.Employer);

        await Assert.ThrowsAsync<KeyNotFoundException>(() => context.Service.ListAsync(
            context.TenantId, context.RelationshipId, Guid.NewGuid(), CancellationToken.None));
        Assert.Equal(0, context.Gateway.CallCount);
    }

    [Fact]
    public async Task EvidenceExport_IsEvidenceFirstSignedAndIdempotent()
    {
        var context = await CreateAsync(RelationshipParticipantRole.Employer);
        var idempotencyKey = Guid.NewGuid();

        var first = await context.Service.CreateExportAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            idempotencyKey, "Customer audit", CancellationToken.None);
        var replay = await context.Service.CreateExportAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            idempotencyKey, "Customer audit", CancellationToken.None);

        Assert.False(first.Replayed);
        Assert.True(replay.Replayed);
        Assert.Equal(first.ExportId, replay.ExportId);
        Assert.Equal(first.DocumentSha256, replay.DocumentSha256);
        Assert.Equal(TimeSpan.FromMinutes(15), first.ExpiresAt - first.AcceptedAt);
        Assert.StartsWith("https://", first.DownloadUrl, StringComparison.Ordinal);
        Assert.Equal(1, context.ConstitutionalGateway.CallCount);
        await Assert.ThrowsAsync<ChannelContinuityConflictException>(() => context.Service.CreateExportAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            idempotencyKey, "Different purpose", CancellationToken.None));
        await using var db = context.Factory.CreateDbContext();
        Assert.Single(await db.RelationshipEvidenceExports.ToListAsync());
    }

    private static async Task<TestContext> CreateAsync(RelationshipParticipantRole role)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new EvidenceGateway();
        var constitutionalGateway = new RecordingRelationshipConstitutionalGateway();
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var trialEvidenceId = Guid.NewGuid();
        var paymentEvidenceId = Guid.NewGuid();
        await using var db = factory.CreateDbContext();
        db.EmploymentRelationships.Add(new EmploymentRelationship
        {
            TenantId = tenantId, RelationshipId = relationshipId, ProfessionalType = "DMA",
            EvaluationIntentId = Guid.NewGuid(), InitiatingParticipantId = participantId,
        });
        db.RelationshipParticipants.Add(new RelationshipParticipant
        {
            TenantId = tenantId, RelationshipId = relationshipId, ParticipantId = participantId,
            Role = role, BoundEvidenceId = Guid.NewGuid(),
        });
        db.RelationshipStateHistory.AddRange(
            History(tenantId, relationshipId, participantId, trialEvidenceId, 1),
            History(tenantId, relationshipId, participantId, paymentEvidenceId, 2));
        await db.SaveChangesAsync();
        gateway.Records[trialEvidenceId] = Record(trialEvidenceId, "TRIAL_STARTED");
        gateway.Records[paymentEvidenceId] = Record(paymentEvidenceId, "PAYMENT_CAPTURED");
        var service = new RelationshipEvidenceService(
            factory,
            gateway,
            constitutionalGateway,
            Options.Create(new RelationshipEvidenceExportOptions
            {
                DownloadBaseUrl = "https://api.example.test",
                SigningKey = new string('k', 32),
            }));
        return new(service, factory, gateway, constitutionalGateway, tenantId, relationshipId, participantId);
    }

    private static RelationshipStateHistory History(
        Guid tenantId, Guid relationshipId, Guid participantId, Guid evidenceId, int version) => new()
    {
        TenantId = tenantId, RelationshipId = relationshipId, StateVersion = version,
        ToState = EmploymentRelationshipState.Interviewing, ActorParticipantId = participantId,
        ActorRole = RelationshipParticipantRole.Evaluator, CorrelationId = Guid.NewGuid(), EvidenceId = evidenceId,
    };

    private static CustomerVisibleEvidenceRecord Record(Guid id, string actionType) => new()
    {
        EvidenceRecordId = id.ToString(), DecisionId = Guid.NewGuid().ToString(), AgentId = "agent",
        AgentInstanceId = "relationship", ActionType = actionType, ExecutionStatus = "AUTHORIZED",
        EvidenceHash = new string('a', 64), RecordedAt = Timestamp.FromDateTimeOffset(DateTimeOffset.UtcNow),
        ErasureStatus = "NONE",
    };

    private sealed class EvidenceGateway : IRelationshipEvidenceGateway
    {
        public Dictionary<Guid, CustomerVisibleEvidenceRecord> Records { get; } = [];
        public int CallCount { get; private set; }

        public Task<IReadOnlyList<CustomerVisibleEvidenceRecord>> QueryAsync(
            Guid tenantId, IReadOnlyCollection<Guid> evidenceIds, CancellationToken cancellationToken)
        {
            CallCount++;
            return Task.FromResult<IReadOnlyList<CustomerVisibleEvidenceRecord>>(
                evidenceIds.Where(Records.ContainsKey).Select(value => Records[value]).ToList());
        }
    }

    private sealed record TestContext(
        RelationshipEvidenceService Service, InMemoryEmploymentRelationshipFactory Factory,
        EvidenceGateway Gateway, RecordingRelationshipConstitutionalGateway ConstitutionalGateway,
        Guid TenantId, Guid RelationshipId, Guid ParticipantId);
}