// Implements: WC-079 AA-03, AA-05, AA-09
// constitutional_basis: C-003, C-005, C-007, C-023, C-026, C-059, C-063, C-065

using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class AgentAdmissionServiceTests
{
    [Fact]
    public async Task OwnerCanPrepareAndSubmitButCannotSelfApprove()
    {
        var context = Context();
        var prepared = await PrepareValidatedAsync(context);
        var intent = Intent(prepared.Admission);

        var submitted = await context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "SUBMIT", intent,
            context.OwnerId, "OWNER_DELEGATE", Guid.NewGuid(), Guid.NewGuid(), "demo", CancellationToken.None);

        Assert.Equal(AgentAdmissionState.ReadyForReview, submitted.Admission.State);
        Assert.Equal(1, context.Gateway.CallCount);
        await Assert.ThrowsAsync<AdmissionTransitionBlockedException>(() => context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "APPROVE", Intent(submitted.Admission),
            context.OwnerId, "ADMISSION_APPROVER", Guid.NewGuid(), Guid.NewGuid(), "demo", CancellationToken.None));
        Assert.Equal(1, context.Gateway.CallCount);
    }

    [Fact]
    public async Task NonOwnerCannotSubmitOrReachConstitutionalEngine()
    {
        var context = Context();
        var prepared = await PrepareValidatedAsync(context);

        await Assert.ThrowsAsync<AdmissionNotFoundException>(() => context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "SUBMIT", Intent(prepared.Admission),
            Guid.NewGuid(), "OWNER_DELEGATE", Guid.NewGuid(), Guid.NewGuid(), "demo", CancellationToken.None));

        Assert.Equal(0, context.Gateway.CallCount);
    }

    [Fact]
    public async Task IndependentApprovalRecordsEvidenceTransitionIdempotencyAndOutboxAtomically()
    {
        var context = Context();
        var prepared = await PrepareValidatedAsync(context);
        var submitted = await context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "SUBMIT", Intent(prepared.Admission),
            context.OwnerId, "OWNER_DELEGATE", Guid.NewGuid(), Guid.NewGuid(), "demo", CancellationToken.None);
        var key = Guid.NewGuid();
        var approver = Guid.NewGuid();
        var approvalIntent = Intent(submitted.Admission);

        var approval = await context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "APPROVE", approvalIntent,
            approver, "ADMISSION_APPROVER", key, Guid.NewGuid(), "demo", CancellationToken.None);
        var replay = await context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "APPROVE", approvalIntent,
            approver, "ADMISSION_APPROVER", key, Guid.NewGuid(), "demo", CancellationToken.None);

        Assert.Equal(AgentAdmissionState.Approved, approval.Admission.State);
        Assert.True(replay.Replayed);
        await using var db = context.Factory.CreateDbContext();
        Assert.Equal(2, await db.AgentAdmissionTransitions.CountAsync());
        Assert.Equal(2, await db.AgentAdmissionOutbox.CountAsync());
        Assert.Equal(2, context.Gateway.CallCount);
    }

    [Fact]
    public async Task DivergentIdempotencyReplayConflictsWithoutMutation()
    {
        var context = Context();
        var key = Guid.NewGuid();
        await context.Service.CreateDraftAsync(
            context.TenantId, context.Type, context.Version, context.OwnerId, context.OwnerId, key, CancellationToken.None);

        await Assert.ThrowsAsync<AdmissionIdempotencyConflictException>(() => context.Service.CreateDraftAsync(
            context.TenantId, context.Type, context.Version, Guid.NewGuid(), context.OwnerId, key, CancellationToken.None));
        await Assert.ThrowsAsync<AdmissionIdempotencyConflictException>(() => context.Service.CreateDraftAsync(
            context.TenantId, "TRADING_FO_CRYPTO", "1.8.0", context.OwnerId, context.OwnerId, key, CancellationToken.None));
    }

    [Fact]
    public async Task ApprovalCannotReplaceSubmittedEvidenceBindings()
    {
        var context = Context();
        var prepared = await PrepareValidatedAsync(context);
        var submitted = await context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "SUBMIT", Intent(prepared.Admission),
            context.OwnerId, "OWNER_DELEGATE", Guid.NewGuid(), Guid.NewGuid(), "demo", CancellationToken.None);
        var mismatched = Intent(submitted.Admission) with { EvidenceSetDigest = "sha256:" + new string('f', 64) };
        var callsBeforeApproval = context.Gateway.CallCount;

        await Assert.ThrowsAsync<AdmissionTransitionBlockedException>(() => context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "APPROVE", mismatched,
            Guid.NewGuid(), "ADMISSION_APPROVER", Guid.NewGuid(), Guid.NewGuid(), "demo", CancellationToken.None));

        Assert.Equal(callsBeforeApproval, context.Gateway.CallCount);
    }

    [Fact]
    public async Task ExactCurrentReadinessAllowsActivation()
    {
        var context = Context();
        var approved = await PrepareApprovedAsync(context);
        await AddReadinessAsync(context, approved.Admission, "PASS", DateTimeOffset.UtcNow.AddHours(1));

        var activated = await context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "ACTIVATE", Intent(approved.Admission),
            Guid.NewGuid(), "PLATFORM_ACTIVATION_AUTHORITY", Guid.NewGuid(), Guid.NewGuid(), "demo", CancellationToken.None);

        Assert.Equal(AgentAdmissionState.Active, activated.Admission.State);
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task ActivationCannotReplaceApprovedArtifactOrPolicy(bool replaceArtifact)
    {
        var context = Context();
        var approved = await PrepareApprovedAsync(context);
        await AddReadinessAsync(context, approved.Admission, "PASS", DateTimeOffset.UtcNow.AddHours(1));
        var intent = replaceArtifact
            ? Intent(approved.Admission) with { ArtifactDigest = "sha256:" + new string('b', 64) }
            : Intent(approved.Admission) with { PolicyVersion = "WC-079-2.0" };
        var callsBeforeActivation = context.Gateway.CallCount;

        await Assert.ThrowsAsync<AdmissionTransitionBlockedException>(() => context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "ACTIVATE", intent,
            Guid.NewGuid(), "PLATFORM_ACTIVATION_AUTHORITY", Guid.NewGuid(), Guid.NewGuid(), "demo", CancellationToken.None));

        Assert.Equal(callsBeforeActivation, context.Gateway.CallCount);
    }

    [Theory]
    [InlineData("UNKNOWN", 1)]
    [InlineData("PASS", -1)]
    public async Task UnknownOrExpiredReadinessBlocksBeforeCe(string status, int validHours)
    {
        var context = Context();
        var approved = await PrepareApprovedAsync(context);
        await AddReadinessAsync(context, approved.Admission, status, DateTimeOffset.UtcNow.AddHours(validHours));
        var callsBeforeActivation = context.Gateway.CallCount;

        await Assert.ThrowsAsync<AdmissionTransitionBlockedException>(() => context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "ACTIVATE", Intent(approved.Admission),
            Guid.NewGuid(), "PLATFORM_ACTIVATION_AUTHORITY", Guid.NewGuid(), Guid.NewGuid(), "demo", CancellationToken.None));
        Assert.Equal(callsBeforeActivation, context.Gateway.CallCount);
    }

    private static async Task<AdmissionMutationResult> PrepareValidatedAsync(TestContext context)
    {
        var draft = await context.Service.CreateDraftAsync(
            context.TenantId, context.Type, context.Version, context.OwnerId, context.OwnerId, Guid.NewGuid(), CancellationToken.None);
        using var contract = AgentAdmissionValidatorTests.ValidContract(context.Type, context.Version);
        var digest = AgentAdmissionCanonicalizer.Digest(contract.RootElement);
        var revised = await context.Service.PutRevisionAsync(
            context.TenantId, context.Type, context.Version, draft.Admission.AdmissionId, 1, 0,
            digest, contract.RootElement, context.OwnerId, Guid.NewGuid(), CancellationToken.None);
        var validated = await context.Service.ValidateAsync(
            context.TenantId, context.Type, context.Version, draft.Admission.AdmissionId, 1,
            digest, AgentAdmissionValidator.Profile, context.OwnerId, false, Guid.NewGuid(), CancellationToken.None);
        Assert.Equal("PASS", validated.Validation.Result);
        await using var db = context.Factory.CreateDbContext();
        return new(await db.AgentAdmissions.SingleAsync(), revised.Replayed);
    }

    private static async Task<AdmissionMutationResult> PrepareApprovedAsync(TestContext context)
    {
        var prepared = await PrepareValidatedAsync(context);
        var submitted = await context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "SUBMIT", Intent(prepared.Admission),
            context.OwnerId, "OWNER_DELEGATE", Guid.NewGuid(), Guid.NewGuid(), "demo", CancellationToken.None);
        return await context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "APPROVE", Intent(submitted.Admission),
            Guid.NewGuid(), "ADMISSION_APPROVER", Guid.NewGuid(), Guid.NewGuid(), "demo", CancellationToken.None);
    }

    private static async Task AddReadinessAsync(
        TestContext context,
        AgentAdmission admission,
        string status,
        DateTimeOffset validUntil)
    {
        var observedAt = validUntil > DateTimeOffset.UtcNow ? DateTimeOffset.UtcNow : validUntil.AddHours(-1);
        foreach (var type in new[] { "RUNTIME", "ENVIRONMENT", "PROVIDER", "BILLING", "ARTIFACT", "CONSTITUTIONAL" })
        {
            await context.Service.RecordReadinessAsync(
                context.TenantId,
                context.Type,
                context.Version,
                new(
                    type,
                    type == "ARTIFACT" ? admission.ArtifactDigest! : admission.AdmissionContentDigest!,
                    "demo",
                    status,
                    $"{type}_OWNER",
                    observedAt,
                    validUntil,
                    admission.PolicyVersion!,
                    $"evidence:{type.ToLowerInvariant()}"),
                CancellationToken.None);
        }
    }

    private static AdmissionTransitionIntent Intent(AgentAdmission admission) => new(
        admission.StateVersion,
        admission.CurrentRevision,
        admission.AdmissionContentDigest!,
        "sha256:" + new string('e', 64),
        "sha256:" + new string('a', 64),
        "WC-079-1.0",
        null,
        null);

    private static TestContext Context()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        return new(
            factory,
            gateway,
            new AgentAdmissionService(factory, new AgentAdmissionValidator(), gateway),
            Guid.NewGuid(),
            Guid.NewGuid(),
            "DIGITAL_MARKETING_LOCAL_SERVICE",
            "3.1.0");
    }

    private sealed record TestContext(
        InMemoryEmploymentRelationshipFactory Factory,
        RecordingRelationshipConstitutionalGateway Gateway,
        AgentAdmissionService Service,
        Guid TenantId,
        Guid OwnerId,
        string Type,
        string Version);
}