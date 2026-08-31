// Implements: WC-079 AA-03, AA-05, AA-09
// constitutional_basis: C-003, C-005, C-007, C-023, C-026, C-059, C-063, C-065

using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class AgentAdmissionServiceTests
{
    [Theory]
    [InlineData(AgentAdmissionState.Draft, "DRAFT")]
    [InlineData(AgentAdmissionState.Validating, "VALIDATING")]
    [InlineData(AgentAdmissionState.RemediationRequired, "REMEDIATION_REQUIRED")]
    [InlineData(AgentAdmissionState.Validated, "VALIDATED")]
    [InlineData(AgentAdmissionState.ReadyForReview, "READY_FOR_REVIEW")]
    [InlineData(AgentAdmissionState.Approved, "APPROVED")]
    [InlineData(AgentAdmissionState.Active, "ACTIVE")]
    [InlineData(AgentAdmissionState.Suspended, "SUSPENDED")]
    [InlineData(AgentAdmissionState.Superseded, "SUPERSEDED")]
    [InlineData(AgentAdmissionState.Retired, "RETIRED")]
    [InlineData(AgentAdmissionState.Rejected, "REJECTED")]
    public void AdmissionStateCodec_RoundTripsEveryPersistedState(AgentAdmissionState state, string stored)
    {
        Assert.Equal(stored, AgentAdmissionStateCodec.ToDatabase(state));
        Assert.Equal(state, AgentAdmissionStateCodec.FromDatabase(stored));
    }

    [Fact]
    public void AdmissionStateCodec_RejectsUnknownValues()
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => AgentAdmissionStateCodec.ToDatabase((AgentAdmissionState)(-1)));
        Assert.Throws<ArgumentOutOfRangeException>(() => AgentAdmissionStateCodec.FromDatabase("UNKNOWN"));
    }

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
    public async Task ExactCreateIdempotencyReplayReturnsExistingAdmission()
    {
        var context = Context();
        var key = Guid.NewGuid();
        var created = await context.Service.CreateDraftAsync(
            context.TenantId, context.Type, context.Version, context.OwnerId, context.OwnerId, key, CancellationToken.None);

        var replayed = await context.Service.CreateDraftAsync(
            context.TenantId, context.Type, context.Version, context.OwnerId, context.OwnerId, key, CancellationToken.None);

        Assert.True(replayed.Replayed);
        Assert.Equal(created.Admission.AdmissionId, replayed.Admission.AdmissionId);
    }

    [Theory]
    [InlineData("[]")]
    [InlineData("{}")]
    [InlineData("{\"contractSchemaVersion\":1}")]
    public async Task RevisionWithoutStringSchemaStoresEmptyVersion(string contentJson)
    {
        var context = Context();
        var draft = await context.Service.CreateDraftAsync(
            context.TenantId, context.Type, context.Version, context.OwnerId, context.OwnerId, Guid.NewGuid(), CancellationToken.None);
        using var content = JsonDocument.Parse(contentJson);
        var digest = AgentAdmissionCanonicalizer.Digest(content.RootElement);

        await context.Service.PutRevisionAsync(
            context.TenantId, context.Type, context.Version, draft.Admission.AdmissionId, 1, 0,
            digest, content.RootElement, context.OwnerId, Guid.NewGuid(), CancellationToken.None);

        await using var db = context.Factory.CreateDbContext();
        Assert.Equal(string.Empty, (await db.AgentAdmissionRevisions.SingleAsync()).ContractSchemaVersion);
    }

    [Fact]
    public async Task RevisionRejectsMismatchedCanonicalDigest()
    {
        var context = Context();
        using var content = JsonDocument.Parse("{}");

        await Assert.ThrowsAsync<ArgumentException>(() => context.Service.PutRevisionAsync(
            context.TenantId, context.Type, context.Version, Guid.NewGuid(), 1, 0,
            "sha256:" + new string('0', 64), content.RootElement, context.OwnerId, Guid.NewGuid(), CancellationToken.None));
    }

    [Fact]
    public async Task ValidationRejectsUnsupportedProfile()
    {
        var context = Context();

        await Assert.ThrowsAsync<ArgumentException>(() => context.Service.ValidateAsync(
            context.TenantId, context.Type, context.Version, Guid.NewGuid(), 1,
            "sha256:" + new string('0', 64), "unsupported", context.OwnerId, false, Guid.NewGuid(), CancellationToken.None));
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

    [Theory]
    [InlineData("REJECT", AgentAdmissionState.Rejected)]
    [InlineData("SUSPEND", AgentAdmissionState.Suspended)]
    [InlineData("SUPERSEDE", AgentAdmissionState.Superseded)]
    [InlineData("RETIRE", AgentAdmissionState.Retired)]
    public async Task IndependentAuthorityCanCompleteTerminalLifecycleTransitions(
        string operation,
        AgentAdmissionState expectedState)
    {
        var context = Context();
        var admission = operation == "REJECT"
            ? (await PrepareSubmittedAsync(context)).Admission
            : (await PrepareActiveAsync(context)).Admission;
        var intent = Intent(admission) with
        {
            ReasonCategory = operation is "REJECT" or "SUSPEND" ? "POLICY" : null,
            SuccessorVersion = operation == "SUPERSEDE" ? "3.2.0" : null,
        };

        var transitioned = await context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, operation, intent,
            Guid.NewGuid(), "ADMISSION_APPROVER", Guid.NewGuid(), Guid.NewGuid(), "demo", CancellationToken.None);

        Assert.Equal(expectedState, transitioned.Admission.State);
    }

    [Fact]
    public async Task RejectionRequiresReasonCategory()
    {
        var context = Context();
        var submitted = await PrepareSubmittedAsync(context);

        await Assert.ThrowsAsync<ArgumentException>(() => context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "REJECT", Intent(submitted.Admission),
            Guid.NewGuid(), "ADMISSION_APPROVER", Guid.NewGuid(), Guid.NewGuid(), "demo", CancellationToken.None));
    }

    [Theory]
    [InlineData("assertionType")]
    [InlineData("environment")]
    [InlineData("status")]
    [InlineData("validity")]
    [InlineData("authority")]
    [InlineData("evidence")]
    public async Task MalformedReadinessObservationsFailClosed(string invalidField)
    {
        var context = Context();
        var now = DateTimeOffset.UtcNow;
        var observation = new AdmissionReadinessObservation(
            "RUNTIME", "sha256:" + new string('a', 64), "demo", "PASS", "RUNTIME_OWNER",
            now, now.AddHours(1), "WC-079-1.0", "evidence:runtime");
        observation = invalidField switch
        {
            "assertionType" => observation with { AssertionType = "UNKNOWN" },
            "environment" => observation with { Environment = "local" },
            "status" => observation with { Status = "MAYBE" },
            "validity" => observation with { ValidUntil = now },
            "authority" => observation with { SourceAuthority = " " },
            "evidence" => observation with { EvidenceRef = " " },
            _ => observation,
        };

        await Assert.ThrowsAsync<ArgumentException>(() => context.Service.RecordReadinessAsync(
            context.TenantId, context.Type, context.Version, observation, CancellationToken.None));
    }

    [Fact]
    public async Task ReadinessCannotBindBeforeApproval()
    {
        var context = Context();
        var draft = await context.Service.CreateDraftAsync(
            context.TenantId, context.Type, context.Version, context.OwnerId, context.OwnerId, Guid.NewGuid(), CancellationToken.None);
        var now = DateTimeOffset.UtcNow;
        var observation = new AdmissionReadinessObservation(
            "RUNTIME", draft.Admission.AdmissionContentDigest ?? string.Empty, "demo", "PASS", "RUNTIME_OWNER",
            now, now.AddHours(1), "WC-079-1.0", "evidence:runtime");

        await Assert.ThrowsAsync<AdmissionTransitionBlockedException>(() => context.Service.RecordReadinessAsync(
            context.TenantId, context.Type, context.Version, observation, CancellationToken.None));
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
        var submitted = await PrepareSubmittedAsync(context);
        return await context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "APPROVE", Intent(submitted.Admission),
            Guid.NewGuid(), "ADMISSION_APPROVER", Guid.NewGuid(), Guid.NewGuid(), "demo", CancellationToken.None);
    }

    private static async Task<AdmissionMutationResult> PrepareSubmittedAsync(TestContext context)
    {
        var prepared = await PrepareValidatedAsync(context);
        return await context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "SUBMIT", Intent(prepared.Admission),
            context.OwnerId, "OWNER_DELEGATE", Guid.NewGuid(), Guid.NewGuid(), "demo", CancellationToken.None);
    }

    private static async Task<AdmissionMutationResult> PrepareActiveAsync(TestContext context)
    {
        var approved = await PrepareApprovedAsync(context);
        await AddReadinessAsync(context, approved.Admission, "PASS", DateTimeOffset.UtcNow.AddHours(1));
        return await context.Service.TransitionAsync(
            context.TenantId, context.Type, context.Version, "ACTIVATE", Intent(approved.Admission),
            Guid.NewGuid(), "PLATFORM_ACTIVATION_AUTHORITY", Guid.NewGuid(), Guid.NewGuid(), "demo", CancellationToken.None);
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