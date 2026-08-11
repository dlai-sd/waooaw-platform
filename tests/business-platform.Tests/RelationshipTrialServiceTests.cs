// Implements: work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-04
// constitutional_basis: C-023, C-026, C-049, C-059, C-076, C-088

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

internal sealed class TrialOwnerGatewayStub : IRelationshipTrialOwnerGateway
{
    public WbeTrialEntitlement? Wbe { get; set; }
    public PrTrialWorkflow? Pr { get; set; }
    public int WbeCalls { get; private set; }
    public int PrCalls { get; private set; }

    public Task<WbeTrialEntitlement?> StartWbeTrialAsync(
        Guid customerId, string professionalType, Guid relationshipId, Guid correlationId,
        CancellationToken cancellationToken)
    {
        WbeCalls++;
        return Task.FromResult(Wbe);
    }

    public Task<PrTrialWorkflow?> StartPrTrialAsync(
        Guid tenantId, Guid relationshipId, Guid trialId, DateTimeOffset startsAt,
        DateTimeOffset expiresAt, Guid correlationId, CancellationToken cancellationToken)
    {
        PrCalls++;
        return Task.FromResult(Pr);
    }
}

public sealed class RelationshipTrialServiceTests
{
    [Fact]
    public async Task BothOwnersConfirmBeforeDurableRelationshipBecomesTrialActive()
    {
        var (service, relationships, factory, gateway, relationship, tenantId, actorId) = await CreateAsync();
        var startsAt = DateTimeOffset.UtcNow;
        var trialId = Guid.NewGuid();
        gateway.Wbe = new(trialId, startsAt, startsAt.AddDays(14));
        gateway.Pr = new(trialId, "TRIAL_DEMONSTRATING", startsAt.AddDays(14));

        var result = await service.StartAsync(
            tenantId, relationship.RelationshipId, actorId, Guid.NewGuid(), CancellationToken.None);

        Assert.Equal("ACTIVE", result.Status);
        Assert.Equal(EmploymentRelationshipState.TrialActive,
            (await relationships.GetAsync(tenantId, relationship.RelationshipId, CancellationToken.None))?.State);
        await using var db = factory.CreateDbContext();
        Assert.Equal("ACTIVE", (await db.RelationshipTrialBindings.SingleAsync()).Status);
    }

    [Theory]
    [InlineData("WBE")]
    [InlineData("PR")]
    public async Task OwnerUncertaintyLeavesRelationshipPreTrial(string owner)
    {
        var (service, relationships, factory, gateway, relationship, tenantId, actorId) = await CreateAsync();
        var startsAt = DateTimeOffset.UtcNow;
        var trialId = Guid.NewGuid();
        gateway.Wbe = owner == "WBE" ? null : new(trialId, startsAt, startsAt.AddDays(14));
        gateway.Pr = owner == "PR" ? null : new(trialId, "TRIAL_DEMONSTRATING", startsAt.AddDays(14));

        await Assert.ThrowsAsync<InvalidOperationException>(() => service.StartAsync(
            tenantId, relationship.RelationshipId, actorId, Guid.NewGuid(), CancellationToken.None));

        Assert.Equal(EmploymentRelationshipState.Interviewing,
            (await relationships.GetAsync(tenantId, relationship.RelationshipId, CancellationToken.None))?.State);
        await using var db = factory.CreateDbContext();
        var binding = await db.RelationshipTrialBindings.SingleAsync();
        Assert.Equal("UNRESOLVED", binding.Status);
        Assert.Equal(owner, binding.UnresolvedOwner);
    }

    [Fact]
    public async Task ActiveReplayDoesNotCallOwnersAgain()
    {
        var (service, _, _, gateway, relationship, tenantId, actorId) = await CreateAsync();
        var startsAt = DateTimeOffset.UtcNow;
        var trialId = Guid.NewGuid();
        gateway.Wbe = new(trialId, startsAt, startsAt.AddDays(14));
        gateway.Pr = new(trialId, "TRIAL_DEMONSTRATING", startsAt.AddDays(14));
        var correlationId = Guid.NewGuid();
        await service.StartAsync(tenantId, relationship.RelationshipId, actorId, correlationId, CancellationToken.None);

        var replay = await service.StartAsync(
            tenantId, relationship.RelationshipId, actorId, correlationId, CancellationToken.None);

        Assert.Equal(trialId, replay.TrialId);
        Assert.Equal(1, gateway.WbeCalls);
        Assert.Equal(1, gateway.PrCalls);
    }

    [Fact]
    public async Task PrUncertaintyRetryReusesDurableWbeConfirmation()
    {
        var (service, relationships, _, gateway, relationship, tenantId, actorId) = await CreateAsync();
        var startsAt = DateTimeOffset.UtcNow;
        var trialId = Guid.NewGuid();
        gateway.Wbe = new(trialId, startsAt, startsAt.AddDays(14));
        gateway.Pr = null;

        await Assert.ThrowsAsync<InvalidOperationException>(() => service.StartAsync(
            tenantId, relationship.RelationshipId, actorId, Guid.NewGuid(), CancellationToken.None));
        gateway.Pr = new(trialId, "TRIAL_DEMONSTRATING", startsAt.AddDays(14));

        var result = await service.StartAsync(
            tenantId, relationship.RelationshipId, actorId, Guid.NewGuid(), CancellationToken.None);

        Assert.Equal("ACTIVE", result.Status);
        Assert.Equal(1, gateway.WbeCalls);
        Assert.Equal(2, gateway.PrCalls);
        Assert.Equal(EmploymentRelationshipState.TrialActive,
            (await relationships.GetAsync(tenantId, relationship.RelationshipId, CancellationToken.None))?.State);
    }

    private static async Task<(RelationshipTrialService Service, EmploymentRelationshipService Relationships,
        InMemoryEmploymentRelationshipFactory Factory, TrialOwnerGatewayStub Gateway,
        EmploymentRelationship Relationship, Guid TenantId, Guid ActorId)> CreateAsync()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var constitutionalGateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory, constitutionalGateway, NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var actorId = Guid.NewGuid();
        var admitted = await relationships.AdmitAsync(
            tenantId, actorId, Guid.NewGuid(), "DMA", Guid.NewGuid(), CancellationToken.None);
        var relationship = await relationships.TransitionAsync(
            tenantId, admitted.Relationship.RelationshipId, actorId, RelationshipParticipantRole.Evaluator,
            EmploymentRelationshipState.Interviewing, Guid.NewGuid(), false, CancellationToken.None);
        var gateway = new TrialOwnerGatewayStub();
        return (new RelationshipTrialService(factory, relationships, gateway), relationships,
            factory, gateway, relationship!, tenantId, actorId);
    }
}