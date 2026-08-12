// Implements: work-contracts/WC-060-goal005-ae01-continuity-evidence-stop.md WC060-03
// constitutional_basis: C-005, C-023, C-026, C-059

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ChannelContinuityServiceTests
{
    private const string HmacKey = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=";

    [Fact]
    public async Task CctAe01Replay01_IdenticalPrepareReplaysAndDivergentMaterialConflicts()
    {
        var context = await CreateContextAsync();
        var idempotencyKey = Guid.NewGuid();
        var request = new PrepareChannelHandoff("WEB", "web-conversation", "CONTINUE", Guid.NewGuid(), idempotencyKey);

        var first = await context.Service.PrepareAsync(
            context.TenantId, context.RelationshipId, context.SourceIdentity, request, CancellationToken.None);
        var replay = await context.Service.PrepareAsync(
            context.TenantId, context.RelationshipId, context.SourceIdentity, request, CancellationToken.None);

        Assert.False(first.Replayed);
        Assert.True(replay.Replayed);
        Assert.Equal(first.HandoffId, replay.HandoffId);
        Assert.Equal(first.ContinuityEnvelope, replay.ContinuityEnvelope);
        Assert.Equal(1, context.Gateway.CallCount);
        await Assert.ThrowsAsync<ChannelContinuityConflictException>(() => context.Service.PrepareAsync(
            context.TenantId,
            context.RelationshipId,
            context.SourceIdentity,
            request with { TargetConversationId = "divergent" },
            CancellationToken.None));
        await using var db = context.Factory.CreateDbContext();
        Assert.Equal(1, await db.ContinuityCheckpoints.CountAsync());
        Assert.Equal(2, await db.ChannelBindings.CountAsync());
    }

    [Fact]
    public async Task CctAe01Handoff03_ModifiedEnvelopeLeavesSourceActiveAndTargetPrepared()
    {
        var context = await CreateContextAsync();
        var prepared = await PrepareAsync(context);
        var targetIdentity = TargetIdentity(context.ParticipantId);
        var request = new ActivateChannelHandoff(
            "web-conversation", Guid.NewGuid(), prepared.ContinuityEnvelope.IdempotencyKey,
            prepared.ContinuityEnvelope with { CommandPurpose = "MODIFIED" });

        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() => context.Service.ActivateAsync(
            context.TenantId, context.RelationshipId, prepared.HandoffId, targetIdentity, request, CancellationToken.None));

        await AssertBindingsAsync(context, "ACTIVE", "PREPARED");
        Assert.Equal(1, context.Gateway.CallCount);
    }

    [Fact]
    public async Task CctAe01Handoff02_EvidenceFailureLeavesSourceActiveAndTargetPrepared()
    {
        var context = await CreateContextAsync();
        var prepared = await PrepareAsync(context);
        context.Gateway.FailNext = true;

        await Assert.ThrowsAsync<InvalidOperationException>(() => context.Service.ActivateAsync(
            context.TenantId,
            context.RelationshipId,
            prepared.HandoffId,
            TargetIdentity(context.ParticipantId),
            new ActivateChannelHandoff(
                "web-conversation", Guid.NewGuid(), prepared.ContinuityEnvelope.IdempotencyKey,
                prepared.ContinuityEnvelope),
            CancellationToken.None));

        await AssertBindingsAsync(context, "ACTIVE", "PREPARED");
    }

    [Fact]
    public async Task CctAe01Handoff01_ActivationCommitsTargetWithoutRevokingSource()
    {
        var context = await CreateContextAsync();
        var prepared = await PrepareAsync(context);

        var activated = await context.Service.ActivateAsync(
            context.TenantId,
            context.RelationshipId,
            prepared.HandoffId,
            TargetIdentity(context.ParticipantId),
            new ActivateChannelHandoff(
                "web-conversation", Guid.NewGuid(), prepared.ContinuityEnvelope.IdempotencyKey,
                prepared.ContinuityEnvelope),
            CancellationToken.None);

        Assert.Equal("COMMITTED", activated.Status);
        Assert.NotNull(activated.ResolutionEvidenceId);
        await AssertBindingsAsync(context, "ACTIVE", "ACTIVE");
    }

    [Fact]
    public async Task CctAe01Stop02_StoppedRelationshipBlocksPrepareWithoutEvidenceOrMutation()
    {
        var context = await CreateContextAsync(EmploymentRelationshipState.StoppedEmergency);

        await Assert.ThrowsAsync<ChannelContinuityLockedException>(() => PrepareAsync(context));

        Assert.Equal(0, context.Gateway.CallCount);
        await using var db = context.Factory.CreateDbContext();
        Assert.Empty(await db.ContinuityCheckpoints.ToListAsync());
        Assert.Single(await db.ChannelBindings.ToListAsync());
    }

    private static async Task<ChannelHandoffResult> PrepareAsync(TestContext context) =>
        await context.Service.PrepareAsync(
            context.TenantId,
            context.RelationshipId,
            context.SourceIdentity,
            new PrepareChannelHandoff("WEB", "web-conversation", "CONTINUE", Guid.NewGuid(), Guid.NewGuid()),
            CancellationToken.None);

    private static ChannelContinuityIdentity TargetIdentity(Guid participantId) => new(
        participantId,
        "WEB",
        "web-conversation",
        new string('b', 64),
        "TIER_4_PORTAL_FRESH",
        DateTimeOffset.UtcNow);

    private static async Task AssertBindingsAsync(TestContext context, string sourceStatus, string targetStatus)
    {
        await using var db = context.Factory.CreateDbContext();
        var bindings = await db.ChannelBindings.OrderBy(value => value.CreatedAt).ToListAsync();
        Assert.Equal(sourceStatus, bindings.Single(value => value.Channel == "WHATSAPP").Status);
        Assert.Equal(targetStatus, bindings.Single(value => value.Channel == "WEB").Status);
    }

    private static async Task<TestContext> CreateContextAsync(
        EmploymentRelationshipState state = EmploymentRelationshipState.Active)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var service = new ChannelContinuityService(
            factory,
            gateway,
            Options.Create(new ChannelContinuityOptions { EnvelopeHmacKey = HmacKey }));
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var authoritySnapshotId = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;
        await using var db = factory.CreateDbContext();
        db.EmploymentRelationships.Add(new EmploymentRelationship
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ProfessionalType = "DMA",
            EvaluationIntentId = Guid.NewGuid(),
            InitiatingParticipantId = participantId,
            State = state,
            AuthoritySnapshotId = authoritySnapshotId,
        });
        db.RelationshipParticipants.Add(new RelationshipParticipant
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ParticipantId = participantId,
            Role = RelationshipParticipantRole.Employer,
            BoundEvidenceId = Guid.NewGuid(),
        });
        db.ChannelBindings.Add(new ChannelBinding
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ParticipantId = participantId,
            ParticipantRole = "EMPLOYER",
            Channel = "WHATSAPP",
            ExternalSubjectHash = new string('a', 64),
            ConversationId = "whatsapp-conversation",
            AssuranceLevel = "TIER_3_MPIN",
            Status = "ACTIVE",
            PreparedEvidenceId = Guid.NewGuid(),
            BoundEvidenceId = Guid.NewGuid(),
            CreatedAt = now,
            BoundAt = now,
        });
        await db.SaveChangesAsync();
        return new TestContext(
            service,
            factory,
            gateway,
            tenantId,
            relationshipId,
            participantId,
            new ChannelContinuityIdentity(
                participantId,
                "WHATSAPP",
                "whatsapp-conversation",
                new string('a', 64),
                "TIER_3_MPIN",
                now));
    }

    private sealed record TestContext(
        ChannelContinuityService Service,
        InMemoryEmploymentRelationshipFactory Factory,
        RecordingRelationshipConstitutionalGateway Gateway,
        Guid TenantId,
        Guid RelationshipId,
        Guid ParticipantId,
        ChannelContinuityIdentity SourceIdentity);
}