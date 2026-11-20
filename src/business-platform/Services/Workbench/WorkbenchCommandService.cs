// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-02
// Constitutional basis: C-001, C-005, C-023, C-026, C-059, C-063, ADR-051

using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.Extensions.Logging;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services.Workbench;

/// <summary>The body of a command answer and whether it replays an earlier identical command.</summary>
public sealed record WorkbenchCommandResult<T>(T Body, bool Replayed)
    where T : class;

/// <summary>
/// Maps every workbench command onto the owner that decides it. The workbench never decides: goal, skill, plan, stop,
/// evidence and commercial changes are submitted to their owners, and the receipt says only what the owner answered.
/// </summary>
public sealed class WorkbenchCommandService(
    EmploymentRelationshipService relationships,
    ConversationalEmploymentService employment,
    IEmploymentCommandCoordinator coordinator,
    RelationshipConfigurationService configuration,
    RelationshipEmergencyStopService emergencyStops,
    RelationshipEvidenceService evidence,
    WorkbenchProjectionService projection,
    IWorkbenchCommercialReader commercial,
    IPackageCatalogGateway packages,
    IWorkbenchGoalHistoryStore goalHistory,
    WorkbenchCommandLedger ledger,
    WorkbenchHandoffService handoffs,
    ILogger<WorkbenchCommandService> logger
)
{
    public const string RoleDetail = "Your role cannot do this.";
    private const string UnavailableDetail =
        "The owner of this change did not answer. Nothing was changed; try again.";
    private const string AcknowledgementText = "The stated limitations are acknowledged.";
    private const int MaximumPackagePages = 10;

    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    private static readonly HashSet<string> SubscriptionKinds = new(StringComparer.Ordinal)
    {
        "UPGRADE",
        "DOWNGRADE",
        "PAUSE",
        "RESUME",
        "TERMINATE",
    };

    public async Task<WorkbenchCommandResult<WorkbenchCommandReceipt>> CreateGoalAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        CreateWorkbenchGoalRequest request,
        CancellationToken ct
    )
    {
        RequireEnvelope(request.SchemaVersion, request.ExpectedVersion);
        RequireDecider(context);
        Require(!string.IsNullOrWhiteSpace(request.GoalTypeId), "goalTypeId is required.");
        Require(
            !string.IsNullOrWhiteSpace(request.Title) && request.Title.Trim().Length <= 240,
            "title must be 1 to 240 characters."
        );
        var baseline = BaselineOf(request.Parameters);
        return await ReceiptAsync(
            "createGoal",
            context,
            idempotencyKey,
            WorkbenchCommandLedger.Digest("createGoal", Resource(context), request),
            async () =>
            {
                var relationship = await RelationshipAsync(context, ct);
                RequireNotStopped(relationship);
                CheckVersion(request.ExpectedVersion, relationship);
                var declaration = await DeclarationAsync(context, ct);
                var type = declaration.GoalTypes.FirstOrDefault(item =>
                    item.GoalTypeId == request.GoalTypeId
                );
                Require(type is not null, "goalTypeId is not declared by this agent.");
                RequireParameters(request.Parameters, type!);
                var goal = await OwnerAsync(() =>
                    configuration.SaveGoalAsync(
                        context.TenantId,
                        context.RelationshipId,
                        request.Title.Trim(),
                        baseline,
                        type!.GoalTypeId,
                        null,
                        "workbench:v1",
                        "PROPOSED",
                        ct
                    )
                );
                await RecordGoalVersionAsync(
                    context,
                    goal.GoalId,
                    new WorkbenchGoalVersionEntry(
                        0,
                        goal.UpdatedAt,
                        RevisedBy(context),
                        null,
                        request.Title.Trim(),
                        new SortedDictionary<string, string>(
                            request.Parameters,
                            StringComparer.Ordinal
                        )
                    ),
                    ct
                );
                return Receipt(
                    context,
                    Guid.NewGuid(),
                    "ACCEPTED",
                    goal.GoalId.ToString("D"),
                    RelationshipConfigurationService.GetGoalVersion(goal)
                );
            },
            ct
        );
    }

    public async Task<WorkbenchCommandResult<WorkbenchCommandReceipt>> ReviseGoalAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        Guid goalId,
        ReviseWorkbenchGoalRequest request,
        CancellationToken ct
    )
    {
        RequireEnvelope(request.SchemaVersion, request.ExpectedVersion);
        RequireDecider(context);
        Require(
            !string.IsNullOrWhiteSpace(request.Reason) && request.Reason.Trim().Length <= 500,
            "reason must be 1 to 500 characters."
        );
        Require(
            request.Title is null
                || (
                    !string.IsNullOrWhiteSpace(request.Title) && request.Title.Trim().Length <= 240
                ),
            "title must be 1 to 240 characters."
        );
        var baseline = BaselineOf(request.Parameters);
        return await ReceiptAsync(
            "reviseGoal",
            context,
            idempotencyKey,
            WorkbenchCommandLedger.Digest("reviseGoal", $"{Resource(context)}:{goalId:D}", request),
            async () =>
            {
                var relationship = await RelationshipAsync(context, ct);
                var goals = await configuration.GetPortalGoalsAsync(
                    context.TenantId,
                    context.RelationshipId,
                    ct
                );
                var item =
                    goals.FirstOrDefault(value => value.Goal.GoalId == goalId)
                    ?? throw new KeyNotFoundException("Goal not found.");
                var goalVersion = RelationshipConfigurationService.GetGoalVersion(item.Goal);
                CheckVersion(request.ExpectedVersion, relationship, goalVersion);
                var declaration = await DeclarationAsync(context, ct);
                var type = declaration.GoalTypes.FirstOrDefault(value =>
                    value.GoalTypeId == item.Goal.Measure
                );
                Require(type is not null, "The goal type is no longer declared by this agent.");
                RequireParameters(request.Parameters, type!);
                await SnapshotGoalAsync(context, item, ct);
                var revised = await OwnerAsync(() =>
                    configuration.ReviseGoalAsync(
                        context.TenantId,
                        context.RelationshipId,
                        goalId,
                        WorkbenchProjectionService.VersionOf(relationship),
                        goalVersion,
                        request.Title?.Trim() ?? item.Goal.Goal,
                        baseline,
                        ct
                    )
                );
                await RecordGoalVersionAsync(
                    context,
                    goalId,
                    new WorkbenchGoalVersionEntry(
                        0,
                        revised.UpdatedAt,
                        RevisedBy(context),
                        request.Reason.Trim(),
                        request.Title?.Trim() ?? item.Goal.Goal,
                        new SortedDictionary<string, string>(
                            request.Parameters,
                            StringComparer.Ordinal
                        )
                    ),
                    ct
                );
                return Receipt(
                    context,
                    Guid.NewGuid(),
                    "ACCEPTED",
                    goalId.ToString("D"),
                    RelationshipConfigurationService.GetGoalVersion(revised)
                );
            },
            ct
        );
    }

    public async Task<WorkbenchCommandResult<WorkbenchCommandReceipt>> ProposePlanAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        ProposeWorkbenchPlanRequest request,
        CancellationToken ct
    )
    {
        RequireEnvelope(request.SchemaVersion, request.ExpectedVersion);
        RequireDecider(context);
        Require(
            request.Milestones is { Count: >= 1 and <= 50 },
            "milestones must hold 1 to 50 items."
        );
        Require(
            request.Milestones!.All(item =>
                !string.IsNullOrWhiteSpace(item.MilestoneTypeId)
                && !string.IsNullOrWhiteSpace(item.Title)
                && item.Title.Trim().Length <= 240
            ),
            "Every milestone needs a type and a title of up to 240 characters."
        );
        return await ReceiptAsync(
            "proposePlan",
            context,
            idempotencyKey,
            WorkbenchCommandLedger.Digest("proposePlan", Resource(context), request),
            async () =>
            {
                var relationship = await RelationshipAsync(context, ct);
                RequireNotStopped(relationship);
                CheckVersion(request.ExpectedVersion, relationship);
                var declaration = await DeclarationAsync(context, ct);
                Require(
                    request.Milestones.All(item =>
                        declaration.MilestoneTypes.Contains(item.MilestoneTypeId)
                    ),
                    "A milestone type is not declared by this agent."
                );
                var goals = await configuration.GetPortalGoalsAsync(
                    context.TenantId,
                    context.RelationshipId,
                    ct
                );
                if (goals.All(item => item.Goal.GoalId != request.GoalId))
                    throw new KeyNotFoundException("Goal not found.");
                var workspace = Workspace(context);
                if (workspace.CurrentPlanVersion is null)
                    throw new WorkbenchException(
                        503,
                        WorkbenchProblemCodes.Unavailable,
                        "The agent has not prepared a plan draft yet, so there is nothing to submit for review."
                    );
                var submission = await SubmitEmploymentAsync(
                    context,
                    idempotencyKey,
                    "SUBMIT_PLAN_FOR_REVIEW",
                    $"plan:{workspace.CurrentPlanVersion}",
                    workspace,
                    new Dictionary<string, object?>
                    {
                        ["expectedPlanVersion"] = workspace.CurrentPlanVersion,
                    },
                    ct
                );
                return submission;
            },
            ct
        );
    }

    public async Task<WorkbenchCommandResult<WorkbenchCommandReceipt>> AcceptPlanAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        string planVersion,
        AcceptWorkbenchPlanRequest request,
        CancellationToken ct
    )
    {
        RequireEnvelope(request.SchemaVersion, request.ExpectedVersion);
        Require(
            !string.IsNullOrWhiteSpace(planVersion) && planVersion.Length <= 128,
            "planVersion is invalid."
        );
        Require(request.AcknowledgedLimitations, "The plan's limitations must be acknowledged.");
        if (context.Role != RelationshipParticipantRole.Employer)
            throw new WorkbenchException(403, WorkbenchProblemCodes.RequestInvalid, RoleDetail);
        return await ReceiptAsync(
            "acceptPlan",
            context,
            idempotencyKey,
            WorkbenchCommandLedger.Digest(
                "acceptPlan",
                $"{Resource(context)}:{planVersion}",
                request
            ),
            async () =>
            {
                var relationship = await RelationshipAsync(context, ct);
                RequireNotStopped(relationship);
                CheckVersion(request.ExpectedVersion, relationship, planVersion);
                var workspace = Workspace(context);
                if (
                    !string.Equals(
                        workspace.CurrentPlanVersion,
                        planVersion,
                        StringComparison.Ordinal
                    )
                )
                    throw new WorkbenchException(409, WorkbenchProblemCodes.VersionConflict);
                return await SubmitEmploymentAsync(
                    context,
                    idempotencyKey,
                    "ACCEPT_PLAN_VERSION",
                    $"plan:{planVersion}",
                    workspace,
                    new Dictionary<string, object?>
                    {
                        ["expectedPlanVersion"] = planVersion,
                        ["expectedDecisionSpaceVersion"] = workspace.DecisionSpaceVersion,
                        ["expectedWbeSourceVersion"] = workspace.WbeSourceVersion,
                        ["acknowledgement"] = AcknowledgementText,
                    },
                    ct
                );
            },
            ct
        );
    }

    public async Task<
        WorkbenchCommandResult<WorkbenchCapabilityCommandResult>
    > CommandCapabilityAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        string skillId,
        WorkbenchCapabilityCommandRequest request,
        CancellationToken ct
    )
    {
        RequireEnvelope(request.SchemaVersion, request.ExpectedVersion);
        Require(
            !string.IsNullOrWhiteSpace(skillId) && skillId.Length <= 160,
            "skillId is invalid."
        );
        Require(
            request.Command
                is "ENABLE"
                    or "PAUSE"
                    or "RESUME"
                    or "RUN_NOW"
                    or "CHANGE_APPROVAL_MODE",
            "command is not supported."
        );
        Require(
            request.Command != "CHANGE_APPROVAL_MODE"
                || (
                    !string.IsNullOrWhiteSpace(request.ApprovalMode)
                    && request.ApprovalMode.Length <= 160
                ),
            "approvalMode is required to change the approval mode."
        );
        RequireResolver(context);
        var timer = Stopwatch.StartNew();
        var (body, replayed) = await ledger.RunAsync(
            context,
            idempotencyKey,
            WorkbenchCommandLedger.Digest(
                "commandCapability",
                $"{Resource(context)}:{skillId}",
                request
            ),
            async () =>
            {
                var relationship = await RelationshipAsync(context, ct);
                RequireNotStopped(relationship);
                var declaration = await DeclarationAsync(context, ct);
                if (declaration.CadenceFor(skillId) is null)
                    throw new KeyNotFoundException("Capability not found.");
                // The contract names no owner that runs a skill on request or stores a per-skill approval mode:
                // the approval ladder is declared per agent version and the employment command set is closed. The
                // workbench therefore refuses these two commands deterministically and shows no control for them.
                if (request.Command is "RUN_NOW" or "CHANGE_APPROVAL_MODE")
                    throw new WorkbenchException(
                        400,
                        WorkbenchProblemCodes.RequestInvalid,
                        request.Command == "RUN_NOW"
                            ? "This capability runs on its declared schedule; it cannot be run on request."
                            : "The approval mode of this capability is set by the agent and cannot be changed here."
                    );
                var skills = await configuration.GetPortalSkillsAsync(
                    context.TenantId,
                    context.RelationshipId,
                    ct
                );
                var skill =
                    skills
                        .Where(item => item.SkillId == skillId)
                        .OrderByDescending(item => item.UpdatedAt)
                        .FirstOrDefault()
                    ?? throw new KeyNotFoundException("Capability is not configured.");
                var skillVersion = RelationshipConfigurationService.GetSkillVersion(skill);
                CheckVersion(request.ExpectedVersion, relationship, skillVersion);
                var decision = request.Command switch
                {
                    "ENABLE" => "ACCEPT_SKILL",
                    "PAUSE" => "DEFER_SKILL",
                    _ => "SELECT_SKILL",
                };
                var result = await OwnerAsync(() =>
                    configuration.DecideSkillAsync(
                        context.TenantId,
                        context.RelationshipId,
                        context.ParticipantId,
                        idempotencyKey,
                        WorkbenchCommandLedger.Digest("decideSkill", skillVersion, request),
                        WorkbenchProjectionService.VersionOf(relationship),
                        skillVersion,
                        skill.ConfigurationId,
                        skill.SkillId,
                        skill.SkillVersion,
                        decision,
                        CorrelationGuid(context),
                        ct
                    )
                );
                return new WorkbenchCapabilityCommandResult(
                    WorkbenchProjectionService.SchemaVersion,
                    request.Command == "RESUME" ? "NEEDS_APPROVAL" : "COMPLETED",
                    result.Decision.DecisionId,
                    request.Command == "RESUME"
                        ? "The capability is selected again and waits for your approval."
                        : null,
                    context.CorrelationId
                );
            },
            ct
        );
        Log("commandCapability", context, body.Outcome, timer);
        return new WorkbenchCommandResult<WorkbenchCapabilityCommandResult>(body, replayed);
    }

    public async Task<WorkbenchCommandResult<WorkbenchCommandReceipt>> ResolveDecisionAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        Guid decisionId,
        ResolveWorkbenchDecisionRequest request,
        CancellationToken ct
    )
    {
        RequireEnvelope(request.SchemaVersion, request.ExpectedVersion);
        Require(
            request.Resolution is "APPROVE" or "DECLINE" or "DEFER",
            "resolution must be APPROVE, DECLINE or DEFER."
        );
        Require(
            request.Note is null || request.Note.Trim().Length is >= 1 and <= 500,
            "note must be 1 to 500 characters."
        );
        RequireResolver(context);
        return await ReceiptAsync(
            "resolveDecision",
            context,
            idempotencyKey,
            WorkbenchCommandLedger.Digest(
                "resolveDecision",
                $"{Resource(context)}:{decisionId:D}",
                request
            ),
            async () =>
            {
                var relationship = await RelationshipAsync(context, ct);
                RequireNotStopped(relationship);
                var items = await projection.ListDecisionItemsAsync(context, ct);
                var item =
                    items.FirstOrDefault(value => value.Decision.DecisionId == decisionId)
                    ?? throw new KeyNotFoundException("Decision not found.");
                CheckVersion(request.ExpectedVersion, relationship, item.SubjectVersion);
                if (request.Resolution == "DEFER")
                    return Receipt(
                        context,
                        Guid.NewGuid(),
                        "COMPLETED",
                        decisionId.ToString("D"),
                        item.SubjectVersion
                    );
                var hash = WorkbenchCommandLedger.Digest(
                    "resolveDecision",
                    item.SubjectVersion,
                    request
                );
                var workspaceVersion = WorkbenchProjectionService.VersionOf(relationship);
                if (item.Kind == "GOAL")
                {
                    var verified = request.Resolution == "APPROVE";
                    Require(
                        verified || !string.IsNullOrWhiteSpace(request.Note),
                        "A note is required to ask for changes."
                    );
                    var result = await OwnerAsync(() =>
                        configuration.VerifyGoalAsync(
                            context.TenantId,
                            context.RelationshipId,
                            context.ParticipantId,
                            idempotencyKey,
                            hash,
                            workspaceVersion,
                            item.SubjectVersion,
                            item.SubjectId,
                            item.SubjectVersion,
                            verified ? "VERIFIED" : "CHANGES_REQUESTED",
                            verified ? null : request.Note!.Trim(),
                            CorrelationGuid(context),
                            ct
                        )
                    );
                    return Receipt(
                        context,
                        result.Decision.DecisionId,
                        "COMPLETED",
                        decisionId.ToString("D"),
                        item.SubjectVersion
                    );
                }
                var skillResult = await OwnerAsync(() =>
                    configuration.DecideSkillAsync(
                        context.TenantId,
                        context.RelationshipId,
                        context.ParticipantId,
                        idempotencyKey,
                        hash,
                        workspaceVersion,
                        item.SubjectVersion,
                        item.SubjectId,
                        item.SkillId!,
                        item.SkillVersion!,
                        request.Resolution == "APPROVE" ? "ACCEPT_SKILL" : "DEFER_SKILL",
                        CorrelationGuid(context),
                        ct
                    )
                );
                return Receipt(
                    context,
                    skillResult.Decision.DecisionId,
                    "COMPLETED",
                    decisionId.ToString("D"),
                    item.SubjectVersion
                );
            },
            ct
        );
    }

    public Task<WorkbenchCommandResult<WorkbenchTopupReceipt>> CreateTopupAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        CreateWorkbenchTopupRequest request,
        CancellationToken ct
    )
    {
        RequireEnvelope(request.SchemaVersion, request.ExpectedVersion);
        Require(
            !string.IsNullOrWhiteSpace(request.ComponentId) && request.ComponentId.Length <= 160,
            "componentId is required."
        );
        Require(request.Quantity is >= 1 and <= 1000, "quantity must be 1 to 1000.");
        RequireSpendAuthority(context);
        // The billing owner publishes no top-up price or payment route (Track G delivered the projection, the lifecycle commands and the
        // settle/release/consume routes only), so a top-up is refused deterministically and no client offers it.
        return Task.FromException<WorkbenchCommandResult<WorkbenchTopupReceipt>>(
            new WorkbenchException(
                503,
                WorkbenchProblemCodes.SpendCommercialUnavailable,
                WorkbenchProjectionService.TopUpNotOffered
            )
        );
    }

    public async Task<WorkbenchCommandResult<SubscriptionChangeReceipt>> ChangeSubscriptionAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        SubscriptionChangeRequest request,
        CancellationToken ct
    )
    {
        RequireEnvelope(request.SchemaVersion, request.ExpectedVersion);
        Require(
            request.Kind is not null && SubscriptionKinds.Contains(request.Kind),
            "kind is not supported."
        );
        Require(
            request.Kind is not ("UPGRADE" or "DOWNGRADE") || request.TargetPackageId is not null,
            "targetPackageId is required to change the package."
        );
        Require(
            request.Selections is null || request.Selections.Count <= 50,
            "selections may hold at most 50 items."
        );
        Require(
            string.IsNullOrWhiteSpace(request.SkillId),
            "Pausing or resuming one capability is done from the capabilities panel; a plan change covers the whole relationship."
        );
        Require(
            request.Selections is null or { Count: 0 }
                || (
                    request.Kind == "DOWNGRADE"
                    && request.Selections.All(item =>
                        !string.IsNullOrWhiteSpace(item.ComponentId)
                        && item.ComponentId.Length <= 100
                        && item.SelectedItemRefs is null or { Count: 0 }
                    )
                ),
            "Only a downgrade takes the components to keep; choosing items inside a component is not part of a plan change."
        );
        Require(
            request.Reason is null || request.Reason.Trim().Length is >= 1 and <= 500,
            "reason must be 1 to 500 characters."
        );
        RequireSpendAuthority(context);
        var timer = Stopwatch.StartNew();
        var (body, replayed) = await ledger.RunAsync(
            context,
            idempotencyKey,
            WorkbenchCommandLedger.Digest("changeSubscription", Resource(context), request),
            async () =>
            {
                var relationship = await RelationshipAsync(context, ct);
                CheckVersion(request.ExpectedVersion, relationship);
                var snapshot = await commercial.GetWalletAsync(context, ct);
                if (!snapshot.Available)
                    throw new WorkbenchException(
                        503,
                        WorkbenchProblemCodes.SpendCommercialUnavailable,
                        snapshot.Limitation
                    );
                var payload = new JsonObject
                {
                    ["commandKind"] = request.Kind switch
                    {
                        "UPGRADE" => "UPGRADE_PACKAGE",
                        "DOWNGRADE" => "DOWNGRADE_PACKAGE",
                        "PAUSE" => "PAUSE_RELATIONSHIP",
                        "RESUME" => "RESUME_RELATIONSHIP",
                        _ => "TERMINATE_RELATIONSHIP",
                    },
                };
                if (request.TargetPackageId is { } targetId)
                    payload["targetPackageCode"] = await PackageCodeAsync(
                        context,
                        relationship,
                        targetId,
                        ct
                    );
                if (request.Kind is "DOWNGRADE" && request.Selections is { Count: > 0 })
                    payload["componentIds"] = new JsonArray(
                        request
                            .Selections.Select(item =>
                                (JsonNode?)JsonValue.Create(item.ComponentId)
                            )
                            .ToArray()
                    );
                var answer = await CommercialAsync(
                    context,
                    idempotencyKey,
                    snapshot.ProjectionVersion,
                    payload,
                    ct
                );
                var effective =
                    Text(answer.Outcome, "effectiveAt") is { } text
                    && DateTimeOffset.TryParse(text, out var parsed)
                        ? parsed
                        : DateTimeOffset.UtcNow;
                return new SubscriptionChangeReceipt(
                    WorkbenchProjectionService.SchemaVersion,
                    answer.CommandId == Guid.Empty ? Guid.NewGuid() : answer.CommandId,
                    request.Kind!,
                    answer.Status switch
                    {
                        "COMPLETED" => "COMPLETED",
                        "BLOCKED" => "BLOCKED",
                        _ when effective > DateTimeOffset.UtcNow => "SCHEDULED",
                        _ => "ACCEPTED",
                    },
                    effective,
                    request.Kind == "UPGRADE"
                        ? Long(answer.Outcome, "proratedFeeDifferencePaise")
                        : null,
                    request.Kind is "PAUSE" or "TERMINATE"
                        ? Long(answer.Outcome, "refundFeePaise")
                        : null,
                    "GST_INCLUSIVE",
                    Text(answer.Outcome, "blockedReason") is { } reason
                        ? ExperienceBlockBuilder.Humanize(reason)
                        : null,
                    context.CorrelationId
                );
            },
            ct
        );
        Log("changeSubscription", context, body.Status, timer);
        return new WorkbenchCommandResult<SubscriptionChangeReceipt>(body, replayed);
    }

    public async Task<WorkbenchCommandResult<WorkbenchCommandReceipt>> ExportEvidenceAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        ExportWorkbenchEvidenceRequest request,
        CancellationToken ct
    )
    {
        RequireEnvelope(request.SchemaVersion, request.ExpectedVersion);
        Require(
            request.Scope is "GOAL" or "PLAN" or "PERIOD" or "RELATIONSHIP",
            "scope is not supported."
        );
        Require(request.Format is "PDF" or "JSON", "format is not supported.");
        Require(
            request.ScopeRef is null || (request.ScopeRef.Length is >= 1 and <= 128),
            "scopeRef must be 1 to 128 characters."
        );
        Require(
            request.Scope != "PERIOD"
                || (
                    DateOnly.TryParse(request.PeriodFrom, out var periodStart)
                    && DateOnly.TryParse(request.PeriodTo, out var periodEnd)
                    && periodStart <= periodEnd
                ),
            "A period export needs periodFrom and periodTo dates, the first not after the second."
        );
        return await ReceiptAsync(
            "exportEvidence",
            context,
            idempotencyKey,
            WorkbenchCommandLedger.Digest("exportEvidence", Resource(context), request),
            async () =>
            {
                var relationship = await RelationshipAsync(context, ct);
                CheckVersion(request.ExpectedVersion, relationship);
                var result = await OwnerAsync(() =>
                    evidence.CreateExportAsync(
                        context.TenantId,
                        context.RelationshipId,
                        context.ParticipantId,
                        idempotencyKey,
                        $"workbench {request.Scope.ToLowerInvariant()} {request.Format.ToLowerInvariant()} export",
                        ct
                    )
                );
                return Receipt(
                    context,
                    result.ExportId,
                    result.Status is "COMPLETED" or "READY" ? "COMPLETED" : "ACCEPTED",
                    result.ExportId.ToString("D"),
                    WorkbenchProjectionService.VersionOf(relationship)
                );
            },
            ct
        );
    }

    public async Task<WorkbenchCommandResult<WorkbenchCommandReceipt>> StopAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        WorkbenchControlRequest request,
        CancellationToken ct
    )
    {
        RequireEnvelope(request.SchemaVersion, request.ExpectedVersion);
        RequireReason(request.Reason);
        return await ReceiptAsync(
            "stop",
            context,
            idempotencyKey,
            WorkbenchCommandLedger.Digest("stop", Resource(context), request),
            async () =>
            {
                var relationship = await RelationshipAsync(context, ct);
                // An emergency stop never waits for a version match; a stale view must not delay a stop.
                if (relationship.State != EmploymentRelationshipState.StoppedEmergency)
                    relationship =
                        await OwnerAsync(() =>
                            emergencyStops.StopAsync(
                                context.TenantId,
                                context.RelationshipId,
                                context.ParticipantId,
                                context.Role,
                                CorrelationGuid(context),
                                ct
                            )
                        ) ?? relationship;
                return Receipt(
                    context,
                    Guid.NewGuid(),
                    relationship.State == EmploymentRelationshipState.StoppedEmergency
                        ? "COMPLETED"
                        : "ACCEPTED",
                    context.RelationshipId.ToString("D"),
                    WorkbenchProjectionService.VersionOf(relationship)
                );
            },
            ct
        );
    }

    public async Task<WorkbenchCommandResult<WorkbenchCommandReceipt>> PauseAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        WorkbenchControlRequest request,
        CancellationToken ct
    )
    {
        RequireEnvelope(request.SchemaVersion, request.ExpectedVersion);
        RequireReason(request.Reason);
        RequireDecider(context);
        return await ReceiptAsync(
            "pause",
            context,
            idempotencyKey,
            WorkbenchCommandLedger.Digest("pause", Resource(context), request),
            async () =>
            {
                var relationship = await RelationshipAsync(context, ct);
                RequireNotStopped(relationship);
                CheckVersion(request.ExpectedVersion, relationship);
                var paused = relationship;
                if (relationship.State != EmploymentRelationshipState.Paused)
                    paused =
                        await OwnerAsync(() =>
                            relationships.TransitionAsync(
                                context.TenantId,
                                context.RelationshipId,
                                context.ParticipantId,
                                context.Role,
                                EmploymentRelationshipState.Paused,
                                CorrelationGuid(context),
                                false,
                                ct
                            )
                        ) ?? relationship;
                return Receipt(
                    context,
                    Guid.NewGuid(),
                    paused.State == EmploymentRelationshipState.Paused ? "COMPLETED" : "ACCEPTED",
                    context.RelationshipId.ToString("D"),
                    WorkbenchProjectionService.VersionOf(paused)
                );
            },
            ct
        );
    }

    public async Task<WorkbenchCommandResult<WorkbenchHandoff>> CreateHandoffAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        CreateWorkbenchHandoffRequest request,
        CancellationToken ct
    )
    {
        RequireEnvelope(request.SchemaVersion, request.ExpectedVersion);
        Require(
            request.Purpose is not null && WorkbenchHandoffService.IsPurpose(request.Purpose),
            "purpose is not supported."
        );
        Require(
            request.ContextRef is null || (request.ContextRef.Length is >= 1 and <= 128),
            "contextRef must be 1 to 128 characters."
        );
        var (body, replayed) = await ledger.RunAsync(
            context,
            idempotencyKey,
            WorkbenchCommandLedger.Digest("createHandoff", Resource(context), request),
            async () =>
            {
                var relationship = await RelationshipAsync(context, ct);
                CheckVersion(request.ExpectedVersion, relationship);
                return await handoffs.CreateAsync(
                    context,
                    request.Purpose!,
                    request.ContextRef,
                    ct
                );
            },
            ct
        );
        return new WorkbenchCommandResult<WorkbenchHandoff>(body, replayed);
    }

    /// <summary>
    /// Redeems a one-time handoff link exactly once. Unknown, expired, already used and foreign links are
    /// indistinguishable on purpose.
    /// </summary>
    public async Task<WorkbenchHandoffConsumption> ConsumeHandoffAsync(
        WorkbenchContext context,
        ConsumeWorkbenchHandoffRequest request,
        CancellationToken ct
    )
    {
        Require(
            request.SchemaVersion == WorkbenchProjectionService.SchemaVersion,
            "schemaVersion must be 1.0."
        );
        Require(
            !string.IsNullOrWhiteSpace(request.DestinationRef)
                && request.DestinationRef.Length <= 128,
            "destinationRef is required."
        );
        var redemption = await handoffs.TryConsumeAsync(
            request.DestinationRef,
            context.TenantId,
            context.RelationshipId,
            context.ParticipantId,
            ct
        );
        if (redemption is null)
            throw new WorkbenchException(
                404,
                WorkbenchProblemCodes.RequestInvalid,
                "This link is not valid any more. Ask for a new one."
            );
        return new WorkbenchHandoffConsumption(
            WorkbenchProjectionService.SchemaVersion,
            redemption.Purpose,
            redemption.ContextRef
        );
    }

    private static string RevisedBy(WorkbenchContext context) => "Customer";

    // The owner has already changed the goal, so a history failure is logged and never fails the command.
    private async Task RecordGoalVersionAsync(
        WorkbenchContext context,
        Guid goalId,
        WorkbenchGoalVersionEntry entry,
        CancellationToken ct
    )
    {
        try
        {
            await goalHistory.AppendAsync(
                context.TenantId,
                context.RelationshipId,
                goalId,
                entry,
                ct
            );
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            logger.LogWarning(
                exception,
                "Workbench goal history append failed for goal {GoalId}",
                goalId
            );
        }
    }

    private async Task SnapshotGoalAsync(
        WorkbenchContext context,
        RelationshipPortalGoal item,
        CancellationToken ct
    )
    {
        try
        {
            var recorded = await goalHistory.ListAsync(
                context.TenantId,
                context.RelationshipId,
                item.Goal.GoalId,
                ct
            );
            if (recorded.Count > 0)
                return;
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            logger.LogWarning(
                exception,
                "Workbench goal history read failed for goal {GoalId}",
                item.Goal.GoalId
            );
            return;
        }
        await RecordGoalVersionAsync(
            context,
            item.Goal.GoalId,
            new WorkbenchGoalVersionEntry(
                0,
                item.Goal.UpdatedAt,
                RevisedBy(context),
                null,
                item.Goal.Goal,
                WorkbenchProjectionService.ParametersOf(item.Goal)
            ),
            ct
        );
    }

    private async Task<WorkbenchCommandResult<WorkbenchCommandReceipt>> ReceiptAsync(
        string operation,
        WorkbenchContext context,
        Guid idempotencyKey,
        string digest,
        Func<Task<WorkbenchCommandReceipt>> execute,
        CancellationToken ct
    )
    {
        var timer = Stopwatch.StartNew();
        var (receipt, replayed) = await ledger.RunAsync(
            context,
            idempotencyKey,
            digest,
            execute,
            ct
        );
        Log(operation, context, receipt.Status, timer);
        return new WorkbenchCommandResult<WorkbenchCommandReceipt>(
            replayed ? receipt with { Replayed = true } : receipt,
            replayed
        );
    }

    private async Task<WorkbenchCommandReceipt> SubmitEmploymentAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        string kind,
        string subjectRef,
        EmploymentWorkspaceSnapshot workspace,
        Dictionary<string, object?> fields,
        CancellationToken ct
    )
    {
        var body = new Dictionary<string, object?>
        {
            ["schemaVersion"] = "1.0",
            ["kind"] = kind,
            ["subjectRef"] = subjectRef,
            ["expectedWorkspaceVersion"] = workspace.WorkspaceVersion,
            ["expectedManifestVersion"] = workspace.ManifestVersion,
        };
        foreach (var field in fields)
            body[field.Key] = field.Value;
        var command = JsonSerializer.SerializeToElement(body, Json);
        try
        {
            var submission = employment.Submit(
                context.TenantId,
                context.RelationshipId,
                context.ParticipantId,
                idempotencyKey,
                command
            );
            var outcome = submission.Outcome;
            if (!submission.Replayed)
            {
                await coordinator.CoordinateAsync(
                    new EmploymentCommandCoordinationContext(
                        context.TenantId,
                        context.RelationshipId,
                        context.ParticipantId,
                        submission.Receipt.CommandId,
                        kind,
                        command,
                        workspace
                    ),
                    ct
                );
                outcome =
                    employment.GetCommand(
                        context.TenantId,
                        context.RelationshipId,
                        submission.Receipt.CommandId
                    ) ?? outcome;
            }
            return Receipt(
                context,
                outcome.CommandId,
                outcome.State switch
                {
                    "COMPLETED" => "COMPLETED",
                    "REJECTED" or "BLOCKED" or "CONFLICT" => "REJECTED",
                    _ => "ACCEPTED",
                },
                subjectRef.Length <= 128 ? subjectRef : null,
                outcome.ResultingVersions.WorkspaceVersion
            );
        }
        catch (EmploymentProtocolException exception)
        {
            throw exception.Code switch
            {
                "EMPLOYMENT_INVALID_REQUEST" => new WorkbenchException(
                    400,
                    WorkbenchProblemCodes.RequestInvalid
                ),
                "EMPLOYMENT_VERSION_CONFLICT" => new WorkbenchException(
                    409,
                    WorkbenchProblemCodes.VersionConflict
                ),
                "EMPLOYMENT_IDEMPOTENCY_CONFLICT" => new WorkbenchException(
                    409,
                    WorkbenchProblemCodes.IdempotencyConflict
                ),
                "EMPLOYMENT_BLOCKED" => new WorkbenchException(
                    422,
                    WorkbenchProblemCodes.RequestInvalid,
                    "The owner blocked this change."
                ),
                "EMPLOYMENT_NOT_ACCESSIBLE" => new WorkbenchException(
                    404,
                    WorkbenchProblemCodes.RequestInvalid
                ),
                _ => new WorkbenchException(
                    503,
                    WorkbenchProblemCodes.Unavailable,
                    UnavailableDetail
                ),
            };
        }
    }

    private async Task<WorkbenchCommercialCommandResult> CommercialAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        string projectionVersion,
        JsonObject payload,
        CancellationToken ct
    )
    {
        var answer = await commercial.SubmitAsync(
            context,
            idempotencyKey,
            projectionVersion,
            payload,
            ct
        );
        if (answer is null)
            throw new WorkbenchException(
                503,
                WorkbenchProblemCodes.SpendCommercialUnavailable,
                UnavailableDetail
            );
        if (answer.ProblemCode is not null)
            throw CommercialProblem(answer.ProblemCode);
        return answer.Status switch
        {
            "COMPLETED" or "PENDING" or "BLOCKED" => answer,
            "CONFLICT" => throw new WorkbenchException(409, WorkbenchProblemCodes.VersionConflict),
            "REJECTED" => throw new WorkbenchException(
                400,
                WorkbenchProblemCodes.RequestInvalid,
                "Billing did not accept this change."
            ),
            _ => throw new WorkbenchException(
                503,
                WorkbenchProblemCodes.SpendCommercialUnavailable,
                UnavailableDetail
            ),
        };
    }

    /// <summary>Resolves the customer-facing package id to the code the billing owner commands by, among the packages on sale for the agent version.</summary>
    private async Task<string> PackageCodeAsync(
        WorkbenchContext context,
        EmploymentRelationship relationship,
        Guid packageId,
        CancellationToken ct
    )
    {
        string? cursor = null;
        try
        {
            for (var page = 0; page < MaximumPackagePages; page++)
            {
                var listed = await packages.ListAsync(
                    context.TenantId,
                    context.ActorSubject,
                    relationship.ProfessionalType,
                    relationship.ProfessionalVersion ?? string.Empty,
                    cursor,
                    PackageCatalogService.MaximumLimit,
                    context.CorrelationId,
                    ct
                );
                var match = listed.Items.FirstOrDefault(item => item.PackageId == packageId);
                if (match is not null)
                    return match.PackageCode;
                cursor = listed.NextCursor;
                if (string.IsNullOrEmpty(cursor))
                    break;
            }
        }
        catch (Exception exception)
            when (exception is PackageCatalogUnavailableException or PackageCatalogCursorException)
        {
            throw new WorkbenchException(
                503,
                WorkbenchProblemCodes.SpendCommercialUnavailable,
                UnavailableDetail
            );
        }
        throw new WorkbenchException(
            400,
            WorkbenchProblemCodes.RequestInvalid,
            "targetPackageId is not a package on sale for this agent."
        );
    }

    private static WorkbenchException CommercialProblem(string code) =>
        code switch
        {
            "WBE_COMMERCIAL_CONFLICT" => new WorkbenchException(
                409,
                WorkbenchProblemCodes.VersionConflict
            ),
            "WBE_COMMERCIAL_UNAUTHORIZED" or "WBE_COMMERCIAL_NOT_ACCESSIBLE" =>
                new WorkbenchException(403, WorkbenchProblemCodes.SpendAuthorityUnavailable),
            "WBE_COMMERCIAL_INVALID" or "HTTP_400" or "HTTP_422" => new WorkbenchException(
                400,
                WorkbenchProblemCodes.RequestInvalid
            ),
            "WBE_COMMERCIAL_BLOCKED" => new WorkbenchException(
                422,
                WorkbenchProblemCodes.PackageComponentNotAvailable
            ),
            WorkbenchProblemCodes.WalletInsufficient => new WorkbenchException(409, code),
            WorkbenchProblemCodes.WalletIdempotencyConflict => new WorkbenchException(409, code),
            WorkbenchProblemCodes.TrialAlreadyUsed => new WorkbenchException(409, code),
            WorkbenchProblemCodes.TrialAlreadyUsedByIdentity => new WorkbenchException(409, code),
            WorkbenchProblemCodes.ComponentNotYetReleased => new WorkbenchException(422, code),
            WorkbenchProblemCodes.PackageComponentNotAvailable => new WorkbenchException(422, code),
            WorkbenchProblemCodes.ProactiveAllowanceExhausted => new WorkbenchException(429, code),
            _ => new WorkbenchException(
                503,
                WorkbenchProblemCodes.SpendCommercialUnavailable,
                UnavailableDetail
            ),
        };

    private static async Task<T> OwnerAsync<T>(Func<Task<T>> call)
    {
        try
        {
            return await call();
        }
        catch (Exception exception)
            when (exception
                    is RelationshipGoalVersionConflictException
                        or RelationshipSkillVersionConflictException
            )
        {
            throw new WorkbenchException(409, WorkbenchProblemCodes.VersionConflict);
        }
        catch (RelationshipConfigurationConflictException)
        {
            throw new WorkbenchException(409, WorkbenchProblemCodes.IdempotencyConflict);
        }
        catch (ConstitutionalActionDeniedException)
        {
            throw new WorkbenchException(
                422,
                WorkbenchProblemCodes.RequestInvalid,
                "The constitutional boundary does not allow this change right now."
            );
        }
        catch (IllegalRelationshipTransitionException)
        {
            throw new WorkbenchException(
                422,
                WorkbenchProblemCodes.RequestInvalid,
                "That change is not allowed in the relationship's current state."
            );
        }
        catch (Exception exception)
            when (exception
                    is not OperationCanceledException
                        and not KeyNotFoundException
                        and not WorkbenchException
            )
        {
            throw new WorkbenchException(503, WorkbenchProblemCodes.Unavailable, UnavailableDetail);
        }
    }

    private async Task<EmploymentRelationship> RelationshipAsync(
        WorkbenchContext context,
        CancellationToken ct
    ) =>
        await relationships.GetAsync(context.TenantId, context.RelationshipId, ct)
        ?? throw new KeyNotFoundException("Relationship not found.");

    private async Task<ExperienceDeclaration> DeclarationAsync(
        WorkbenchContext context,
        CancellationToken ct
    ) =>
        await projection.GetDeclarationAsync(context, ct)
        ?? throw new WorkbenchException(
            503,
            WorkbenchProblemCodes.Unavailable,
            "The agent's experience declaration is not available right now."
        );

    private EmploymentWorkspaceSnapshot Workspace(WorkbenchContext context) =>
        employment.GetWorkspace(context.TenantId, context.RelationshipId)
        ?? throw new WorkbenchException(
            503,
            WorkbenchProblemCodes.Unavailable,
            "The employment workspace is not available right now."
        );

    private static WorkbenchCommandReceipt Receipt(
        WorkbenchContext context,
        Guid operationRef,
        string status,
        string? resourceRef,
        string version
    ) =>
        new(
            WorkbenchProjectionService.SchemaVersion,
            operationRef,
            status,
            resourceRef,
            version,
            false,
            context.CorrelationId
        );

    private static string Resource(WorkbenchContext context) =>
        context.RelationshipId.ToString("D");

    private static Guid CorrelationGuid(WorkbenchContext context) =>
        Guid.TryParse(context.CorrelationId, out var value) ? value : Guid.NewGuid();

    private static void CheckVersion(
        string expected,
        EmploymentRelationship relationship,
        string? subjectVersion = null
    )
    {
        if (
            expected == WorkbenchProjectionService.VersionOf(relationship)
            || (subjectVersion is not null && expected == subjectVersion)
        )
            return;
        throw new WorkbenchException(409, WorkbenchProblemCodes.VersionConflict);
    }

    private static void RequireNotStopped(EmploymentRelationship relationship)
    {
        if (relationship.State == EmploymentRelationshipState.StoppedEmergency)
            throw new WorkbenchException(
                409,
                WorkbenchProblemCodes.VersionConflict,
                "The relationship is stopped, so no change is accepted."
            );
    }

    private static void Require(bool condition, string detail)
    {
        if (!condition)
            throw new WorkbenchException(400, WorkbenchProblemCodes.RequestInvalid, detail);
    }

    private static void RequireEnvelope(string? schemaVersion, string? expectedVersion) =>
        Require(
            schemaVersion == WorkbenchProjectionService.SchemaVersion
                && !string.IsNullOrWhiteSpace(expectedVersion)
                && expectedVersion.Length <= 128,
            "schemaVersion must be 1.0 and expectedVersion must be 1 to 128 characters."
        );

    private static void RequireReason(string? reason) =>
        Require(
            reason is null || reason.Trim().Length is >= 1 and <= 500,
            "reason must be 1 to 500 characters."
        );

    private static void RequireDecider(WorkbenchContext context)
    {
        if (!WorkbenchAudiences.MayDecide(context.Audience))
            throw new WorkbenchException(403, WorkbenchProblemCodes.RequestInvalid, RoleDetail);
    }

    private static void RequireResolver(WorkbenchContext context)
    {
        if (!WorkbenchAudiences.MayResolve(context.Role))
            throw new WorkbenchException(403, WorkbenchProblemCodes.RequestInvalid, RoleDetail);
    }

    private static void RequireSpendAuthority(WorkbenchContext context)
    {
        if (!WorkbenchAudiences.MayManageSpend(context.Audience))
            throw new WorkbenchException(
                403,
                WorkbenchProblemCodes.SpendAuthorityUnavailable,
                "Only the account owner can change spend."
            );
    }

    private static void RequireParameters(
        Dictionary<string, string> parameters,
        ExperienceGoalType type
    ) =>
        Require(
            parameters.Keys.All(key => type.Parameters.Contains(key)),
            "A parameter is not declared for this goal type."
        );

    private static string? BaselineOf(Dictionary<string, string>? parameters)
    {
        Require(
            parameters is not null && parameters.Count <= 20,
            "parameters may hold at most 20 values."
        );
        Require(
            parameters!.All(item =>
                !string.IsNullOrWhiteSpace(item.Key)
                && item.Key.Length <= 80
                && !string.IsNullOrWhiteSpace(item.Value)
                && item.Value.Length <= 200
            ),
            "Every parameter needs a name of up to 80 and a value of up to 200 characters."
        );
        var sorted = new SortedDictionary<string, string>(parameters!, StringComparer.Ordinal);
        var text = JsonSerializer.Serialize(new { parameters = sorted }, Json);
        Require(text.Length <= 2000, "parameters are too long.");
        return text;
    }

    private static long? Long(JsonElement? outcome, string name) =>
        outcome is { ValueKind: JsonValueKind.Object } value
        && value.TryGetProperty(name, out var number)
        && number.ValueKind == JsonValueKind.Number
        && number.TryGetInt64(out var parsed)
        && parsed >= 0
            ? parsed
            : null;

    private static string? Text(JsonElement? outcome, string name) =>
        outcome is { ValueKind: JsonValueKind.Object } value
        && value.TryGetProperty(name, out var text)
        && text.ValueKind == JsonValueKind.String
        && !string.IsNullOrWhiteSpace(text.GetString())
            ? text.GetString()
            : null;

    private void Log(string operation, WorkbenchContext context, string status, Stopwatch timer)
    {
        timer.Stop();
        logger.LogInformation(
            "workbench_command operation={Operation} relationship={RelationshipHash} audience={Audience} status={Status} durationMs={DurationMs}",
            operation,
            WorkbenchProjectionService.Hash(context.RelationshipId),
            context.Audience,
            status,
            timer.ElapsedMilliseconds
        );
    }
}
