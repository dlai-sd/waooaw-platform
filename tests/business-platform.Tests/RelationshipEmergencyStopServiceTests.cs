// Implements: work-contracts/WC-060-goal005-ae01-continuity-evidence-stop.md § WC060-07
// constitutional_basis: C-001, C-005, C-023, C-024, C-059

using System.Diagnostics;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

internal sealed class InMemoryConversationStoreFactory(string databaseName)
    : IDbContextFactory<ConversationStoreDbContext>
{
    public ConversationStoreDbContext CreateDbContext() =>
        new(new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseInMemoryDatabase(databaseName)
            .Options);
}

internal sealed class RecordingEmergencyStopGateway : IRelationshipEmergencyStopGateway
{
    public Guid EvidenceId { get; } = Guid.NewGuid();
    public IReadOnlyCollection<Guid> ExecutionIds { get; private set; } = [];

    public Task<RelationshipEmergencyStopDispatch> StopAsync(
        Guid tenantId, Guid relationshipId, Guid participantId,
        IReadOnlyCollection<Guid> executionIds, CancellationToken cancellationToken)
    {
        ExecutionIds = executionIds;
        return Task.FromResult(new RelationshipEmergencyStopDispatch(EvidenceId, DateTimeOffset.UtcNow));
    }
}

public sealed class RelationshipEmergencyStopServiceTests
{
    [Fact]
    public async Task CctAe01Stop01_HaltsAllNonTerminalRelationshipExecutionsAndProjectsSameEvidence()
    {
        var relationshipFactory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var relationships = new EmploymentRelationshipService(
            relationshipFactory, new RecordingRelationshipConstitutionalGateway(), NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admitted = await relationships.AdmitAsync(
            tenantId, participantId, Guid.NewGuid(), "DMA", Guid.NewGuid(), CancellationToken.None);
        var conversationFactory = new InMemoryConversationStoreFactory(Guid.NewGuid().ToString("N"));
        var activeExecutionId = Guid.NewGuid();
        await using (var db = conversationFactory.CreateDbContext())
        {
            db.Executions.AddRange(
                new ConversationExecution { ExecutionId = activeExecutionId, TenantId = tenantId, RelationshipId = admitted.Relationship.RelationshipId, ProcessingState = "EXECUTING" },
                new ConversationExecution { TenantId = tenantId, RelationshipId = admitted.Relationship.RelationshipId, ProcessingState = "COMPLETED" },
                new ConversationExecution { TenantId = Guid.NewGuid(), RelationshipId = admitted.Relationship.RelationshipId, ProcessingState = "EXECUTING" });
            await db.SaveChangesAsync();
        }
        var gateway = new RecordingEmergencyStopGateway();
        var service = new RelationshipEmergencyStopService(conversationFactory, relationships, gateway);

        var timer = Stopwatch.StartNew();
        var stopped = await service.StopAsync(
            tenantId, admitted.Relationship.RelationshipId, participantId, RelationshipParticipantRole.Evaluator,
            Guid.NewGuid(), CancellationToken.None);
        timer.Stop();

        Assert.Equal(EmploymentRelationshipState.StoppedEmergency, stopped!.State);
        Assert.Equal([activeExecutionId], gateway.ExecutionIds);
        Assert.True(timer.ElapsedMilliseconds <= 250);
        await using var relationshipDb = relationshipFactory.CreateDbContext();
        var history = await relationshipDb.RelationshipStateHistory.SingleAsync(value => value.ToState == EmploymentRelationshipState.StoppedEmergency);
        Assert.Equal(gateway.EvidenceId, history.EvidenceId);
    }
}