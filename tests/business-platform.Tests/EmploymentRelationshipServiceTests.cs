// Implements: work-contracts/WC-057-goal005-ae01-employment-journey-foundation.md § Constitutional Compliance Tests
// constitutional_basis: C-005, C-023, C-026, C-059

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

internal sealed class InMemoryEmploymentRelationshipFactory(string databaseName)
    : IDbContextFactory<EmploymentRelationshipDbContext>
{
    public EmploymentRelationshipDbContext CreateDbContext() =>
        new(new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
            .UseInMemoryDatabase(databaseName)
            .Options);
}

internal sealed class RecordingRelationshipConstitutionalGateway : IRelationshipConstitutionalGateway
{
    public int CallCount { get; private set; }
    public bool FailNext { get; set; }
    public int? FailOnCall { get; set; }

    public Task<Guid> AuthorizeAndRecordAsync(
        Guid tenantId,
        Guid relationshipId,
        string professionalType,
        string actionType,
        Guid correlationId,
        object actionParameters,
        CancellationToken cancellationToken)
    {
        CallCount += 1;
        if (FailNext || CallCount == FailOnCall)
        {
            FailNext = false;
            FailOnCall = null;
            throw new InvalidOperationException("Evidence commitment unavailable.");
        }

        return Task.FromResult(Guid.NewGuid());
    }
}

public sealed class EmploymentRelationshipServiceTests
{
    [Fact]
    public async Task CctAe01Rel01_DuplicateAdmissionReusesRelationship()
    {
        var (service, factory, gateway) = CreateService();
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var evaluationIntentId = Guid.NewGuid();

        var first = await service.AdmitAsync(
            tenantId, participantId, evaluationIntentId, "dma", Guid.NewGuid(), CancellationToken.None);
        var replay = await service.AdmitAsync(
            tenantId, participantId, evaluationIntentId, " DMA ", Guid.NewGuid(), CancellationToken.None);

        Assert.True(first.Created);
        Assert.False(replay.Created);
        Assert.Equal(first.Relationship.RelationshipId, replay.Relationship.RelationshipId);
        Assert.Equal(1, gateway.CallCount);

        await using var db = factory.CreateDbContext();
        Assert.Equal(1, await db.EmploymentRelationships.CountAsync());
        Assert.Equal(1, await db.RelationshipParticipants.CountAsync());
        Assert.Equal(1, await db.RelationshipStateHistory.CountAsync());
    }

    [Fact]
    public async Task CctAe01Tenant01_OtherTenantCannotReadRelationshipOrTimeline()
    {
        var (service, _, _) = CreateService();
        var admitted = await AdmitAsync(service);
        var otherTenantId = Guid.NewGuid();

        var relationship = await service.GetAsync(
            otherTenantId, admitted.Relationship.RelationshipId, CancellationToken.None);
        var timeline = await service.GetTimelineAsync(
            otherTenantId, admitted.Relationship.RelationshipId, CancellationToken.None);

        Assert.Null(relationship);
        Assert.Empty(timeline);
    }

    [Fact]
    public async Task CctAe01State01_IllegalTransitionHasZeroMutation()
    {
        var (service, factory, gateway) = CreateService();
        var admitted = await AdmitAsync(service);

        await Assert.ThrowsAsync<IllegalRelationshipTransitionException>(() => service.TransitionAsync(
            admitted.Relationship.TenantId,
            admitted.Relationship.RelationshipId,
            admitted.Relationship.InitiatingParticipantId,
            RelationshipParticipantRole.Evaluator,
            EmploymentRelationshipState.Active,
            Guid.NewGuid(),
            false,
            CancellationToken.None));

        Assert.Equal(1, gateway.CallCount);
        await AssertRelationshipUnchangedAsync(factory, admitted.Relationship.RelationshipId);
    }

    [Fact]
    public async Task CctAe01State01_UnboundRoleCannotTransition()
    {
        var (service, factory, gateway) = CreateService();
        var admitted = await AdmitAsync(service);

        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() => service.TransitionAsync(
            admitted.Relationship.TenantId,
            admitted.Relationship.RelationshipId,
            admitted.Relationship.InitiatingParticipantId,
            RelationshipParticipantRole.Employer,
            EmploymentRelationshipState.Interviewing,
            Guid.NewGuid(),
            false,
            CancellationToken.None));

        Assert.Equal(1, gateway.CallCount);
        await AssertRelationshipUnchangedAsync(factory, admitted.Relationship.RelationshipId);
    }

    [Fact]
    public async Task CctAe01Ef01_EvidenceFailurePreventsTransitionMutation()
    {
        var (service, factory, gateway) = CreateService();
        var admitted = await AdmitAsync(service);
        gateway.FailNext = true;

        await Assert.ThrowsAsync<InvalidOperationException>(() => service.TransitionAsync(
            admitted.Relationship.TenantId,
            admitted.Relationship.RelationshipId,
            admitted.Relationship.InitiatingParticipantId,
            RelationshipParticipantRole.Evaluator,
            EmploymentRelationshipState.Interviewing,
            Guid.NewGuid(),
            false,
            CancellationToken.None));

        Assert.Equal(2, gateway.CallCount);
        await AssertRelationshipUnchangedAsync(factory, admitted.Relationship.RelationshipId);
    }

    [Fact]
    public async Task LegalTransitionCommitsEvidenceLinkedHistory()
    {
        var (service, factory, gateway) = CreateService();
        var admitted = await AdmitAsync(service);

        var relationship = await service.TransitionAsync(
            admitted.Relationship.TenantId,
            admitted.Relationship.RelationshipId,
            admitted.Relationship.InitiatingParticipantId,
            RelationshipParticipantRole.Evaluator,
            EmploymentRelationshipState.Interviewing,
            Guid.NewGuid(),
            false,
            CancellationToken.None);

        Assert.NotNull(relationship);
        Assert.Equal(EmploymentRelationshipState.Interviewing, relationship.State);
        Assert.Equal(1, relationship.StateVersion);
        Assert.Equal(2, gateway.CallCount);

        await using var db = factory.CreateDbContext();
        var history = await db.RelationshipStateHistory
            .OrderBy(value => value.StateVersion)
            .ToListAsync();
        Assert.Equal(2, history.Count);
        Assert.NotEqual(Guid.Empty, history[1].EvidenceId);
    }

    private static (EmploymentRelationshipService Service, InMemoryEmploymentRelationshipFactory Factory, RecordingRelationshipConstitutionalGateway Gateway) CreateService()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var service = new EmploymentRelationshipService(
            factory,
            gateway,
            NullLogger<EmploymentRelationshipService>.Instance);
        return (service, factory, gateway);
    }

    private static async Task<AdmitRelationshipResult> AdmitAsync(EmploymentRelationshipService service) =>
        await service.AdmitAsync(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            "DMA",
            Guid.NewGuid(),
            CancellationToken.None);

    private static async Task AssertRelationshipUnchangedAsync(
        InMemoryEmploymentRelationshipFactory factory,
        Guid relationshipId)
    {
        await using var db = factory.CreateDbContext();
        var relationship = await db.EmploymentRelationships.SingleAsync(
            value => value.RelationshipId == relationshipId);
        Assert.Equal(EmploymentRelationshipState.Discovered, relationship.State);
        Assert.Equal(0, relationship.StateVersion);
        Assert.Equal(1, await db.RelationshipStateHistory.CountAsync());
    }
}