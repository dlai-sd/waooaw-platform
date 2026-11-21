// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01
// Constitutional basis: C-001, C-005, C-023, C-026, C-059, C-063, ADR-051

using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services.Workbench;

/// <summary>Everything one workbench request reads once; owners that fail leave a limitation instead of an error.</summary>
public sealed record WorkbenchData(
    EmploymentRelationship Relationship,
    string Version,
    string Audience,
    ExperienceDeclaration? Declaration,
    EmploymentWorkspaceSnapshot? Workspace,
    IReadOnlyList<RelationshipPortalGoal> Goals,
    IReadOnlyList<RelationshipSkillConfiguration> Skills,
    ExecutionOwnerProjection? Execution,
    IReadOnlyList<PerformanceReviewProjectionV1> Reviews,
    IReadOnlyList<string> Limitations
);

/// <summary>A pending decision plus the owner subject needed to apply its resolution; the subject never leaves the server.</summary>
public sealed record WorkbenchDecisionItem(
    WorkbenchDecision Decision,
    string Kind,
    Guid SubjectId,
    string SubjectVersion,
    string? SkillId,
    string? SkillVersion
);

public sealed class WorkbenchProjectionService(
    EmploymentRelationshipService relationships,
    ConversationalEmploymentService employment,
    RelationshipConfigurationService configuration,
    PerformanceReviewService reviews,
    RelationshipEvidenceService evidence,
    IRelationshipWorkspaceOwnerGateway owners,
    IAdmittedExperienceManifestSource manifests,
    IWorkbenchCommercialReader commercial,
    IWorkbenchGoalHistoryStore goalHistory,
    TimeProvider clock,
    ILogger<WorkbenchProjectionService> logger
)
{
    public const string SchemaVersion = "1.0";
    public const string NotReported = "Not yet reported";
    public const string TopUpNotOffered = "Adding to your allowance online is not available yet.";

    private static readonly string[] InductionStates =
    [
        "NOT_STARTED",
        "IN_PROGRESS",
        "READY_WITH_DEFERRED_ITEMS",
        "READY",
        "BLOCKED",
        "STALE_REASSESSMENT_REQUIRED",
    ];
    private static readonly string[] PlanStates =
    [
        "NO_PLAN",
        "DRAFT",
        "GROOMING",
        "READY_FOR_REVIEW",
        "AGREED",
        "BLOCKED",
        "STALE_REASSESSMENT_REQUIRED",
    ];
    private static readonly string[] OperationStates =
    [
        "LOCKED",
        "ELIGIBLE",
        "ACTIVE",
        "PAUSED",
        "BLOCKED",
        "REASSESSMENT_REQUIRED",
        "TERMINATED",
    ];
    private static readonly string[] PerformanceStates =
    [
        "NOT_ESTABLISHED",
        "CURRENT",
        "DEGRADED",
        "CORRECTIVE_ACTION_REQUIRED",
        "BLOCKED",
        "UNAVAILABLE",
    ];

    public static string VersionOf(EmploymentRelationship relationship) =>
        $"relationship-{relationship.StateVersion}";

    /// <summary>
    /// Narrows the audience to what the admitted agent declares: a declared audience list that lacks the caller's
    /// audience gives the caller the beneficiary view, which carries no spend, price or top-up.
    /// </summary>
    public async Task<WorkbenchContext> NarrowAsync(WorkbenchContext context, CancellationToken ct)
    {
        var declaration = await GetDeclarationAsync(context, ct);
        return declaration is not null && !declaration.Audiences.Contains(context.Audience)
            ? context with
            {
                Audience = WorkbenchAudiences.Beneficiary,
            }
            : context;
    }

    /// <summary>The experience declaration of the agent the relationship is bound to, or null when it cannot be read.</summary>
    public async Task<ExperienceDeclaration?> GetDeclarationAsync(
        WorkbenchContext context,
        CancellationToken ct
    )
    {
        var relationship =
            await relationships.GetAsync(context.TenantId, context.RelationshipId, ct)
            ?? throw new KeyNotFoundException("Relationship not found.");
        return await LoadDeclarationAsync(
            context,
            relationship,
            employment.GetWorkspace(context.TenantId, context.RelationshipId),
            new List<string>(),
            ct
        );
    }

    public async Task<WorkbenchData> LoadAsync(WorkbenchContext context, CancellationToken ct)
    {
        var relationship =
            await relationships.GetAsync(context.TenantId, context.RelationshipId, ct)
            ?? throw new KeyNotFoundException("Relationship not found.");
        var limitations = new List<string>();
        var workspace = employment.GetWorkspace(context.TenantId, context.RelationshipId);
        if (workspace is null)
            limitations.Add("The employment workspace is not available yet.");
        var declaration = await LoadDeclarationAsync(
            context,
            relationship,
            workspace,
            limitations,
            ct
        );
        var goals =
            await TryAsync(
                () =>
                    configuration.GetPortalGoalsAsync(context.TenantId, context.RelationshipId, ct),
                "Goals could not be read right now.",
                limitations
            ) ?? [];
        var skills =
            await TryAsync(
                () =>
                    configuration.GetPortalSkillsAsync(
                        context.TenantId,
                        context.RelationshipId,
                        ct
                    ),
                "Capabilities could not be read right now.",
                limitations
            ) ?? [];
        var execution = await TryOptionalAsync(
            () =>
                owners.GetExecutionAsync(
                    new RelationshipOwnerContext(
                        context.ActorSubject,
                        context.EffectiveRole,
                        context.TenantId,
                        context.RelationshipId,
                        relationship.StateVersion,
                        context.CorrelationId,
                        relationship.AgentInstanceId
                    ),
                    ct
                ),
            "Work in progress is not reported right now.",
            limitations
        );
        if (
            execution is null
            && !limitations.Contains("Work in progress is not reported right now.")
        )
            limitations.Add("Work in progress is not reported right now.");
        var performance =
            await TryAsync(
                () => reviews.ListAsync(context.TenantId, context.RelationshipId, ct),
                "Performance reviews could not be read right now.",
                limitations
            ) ?? [];
        return new WorkbenchData(
            relationship,
            VersionOf(relationship),
            context.Audience,
            declaration,
            workspace,
            goals,
            skills,
            execution,
            performance,
            limitations
        );
    }

    public async Task<WorkbenchProjection> BuildAsync(
        WorkbenchContext context,
        ChannelCapabilities capabilities,
        CancellationToken ct
    )
    {
        var timer = Stopwatch.StartNew();
        var data = await LoadAsync(context, ct);
        var limitations = data.Limitations.ToList();
        var readiness = ReadinessOf(data.Workspace);
        var phase = PhaseOf(readiness);
        var decisions = DecisionItems(data, context).Select(item => item.Decision).ToArray();
        var tiles = TilesOf(data, limitations);
        var plan = PlanOf(data, limitations);
        var goal = data.Goals.LastOrDefault(item => GoalState(item.Goal) == "ACTIVE");
        var components = await WalletComponentsAsync(context, limitations, ct);
        var next = RecommendedAction(data, decisions.Length, plan, goal is not null);
        var evidenceState = await EvidenceStateAsync(context, ct);
        var freshness =
            limitations.Count == 0 ? "CURRENT"
            : data.Workspace is null && data.Execution is null ? "UNAVAILABLE"
            : "STALE";
        var blocks = ExperienceBlockBuilder.Build(
            new WorkbenchBlockInput(
                context.RelationshipId,
                data.Audience,
                phase,
                readiness,
                decisions,
                tiles,
                plan,
                limitations,
                next,
                goal is null
                && data.Relationship.State != EmploymentRelationshipState.StoppedEmergency
                    ? data.Declaration?.GoalTypes
                    : null
            ),
            capabilities
        );
        timer.Stop();
        logger.LogInformation(
            "workbench_projection_built relationship={RelationshipHash} audience={Audience} limitations={LimitationCount} durationMs={DurationMs}",
            Hash(context.RelationshipId),
            data.Audience,
            limitations.Count,
            timer.ElapsedMilliseconds
        );
        return new WorkbenchProjection(
            SchemaVersion,
            context.RelationshipId,
            data.Audience,
            phase,
            readiness,
            goal?.Goal.GoalId,
            plan?.PlanVersion,
            decisions,
            tiles,
            components,
            [],
            evidenceState,
            freshness,
            limitations,
            next,
            AvailableCommands(data, context, plan, goal is not null),
            blocks
        );
    }

    public async Task<WorkbenchGoalList> ListGoalsAsync(
        WorkbenchContext context,
        WorkbenchPage page,
        CancellationToken ct
    )
    {
        var data = await LoadAsync(context, ct);
        var latest = await LatestVersionsAsync(context, ct);
        var (items, next) = WorkbenchPaging.Slice(
            data.Goals.Select(item => GoalSummary(item, latest)).ToArray(),
            page
        );
        return new WorkbenchGoalList(SchemaVersion, items, next);
    }

    public async Task<WorkbenchGoal?> GetGoalAsync(
        WorkbenchContext context,
        Guid goalId,
        CancellationToken ct
    )
    {
        var data = await LoadAsync(context, ct);
        var item = data.Goals.FirstOrDefault(value => value.Goal.GoalId == goalId);
        return item is null
            ? null
            : GoalDetail(item, data.Declaration, await LatestVersionsAsync(context, ct));
    }

    /// <summary>
    /// The goal's versions, newest first: every version the workbench recorded plus the current state when the goal was
    /// last changed outside the workbench. A goal revised only elsewhere shows its current version alone.
    /// </summary>
    public async Task<WorkbenchGoalVersionList?> ListGoalVersionsAsync(
        WorkbenchContext context,
        Guid goalId,
        WorkbenchPage page,
        CancellationToken ct
    )
    {
        var data = await LoadAsync(context, ct);
        var item = data.Goals.FirstOrDefault(value => value.Goal.GoalId == goalId);
        if (item is null)
            return null;
        var recorded = await RecordedVersionsAsync(context, goalId, ct);
        var versions = recorded
            .Select(entry => new WorkbenchGoalVersion(
                entry.VersionNo,
                entry.RevisedAt,
                entry.RevisedBy,
                entry.Reason,
                entry.Parameters
            ))
            .ToList();
        if (
            versions.Count == 0
            || item.Goal.UpdatedAt - versions[^1].RevisedAt > TimeSpan.FromSeconds(1)
        )
        {
            var number =
                versions.Count == 0
                    ? GoalSummary(item, new Dictionary<Guid, int>()).CurrentVersion
                    : versions[^1].VersionNo + 1;
            versions.Add(
                new WorkbenchGoalVersion(
                    number,
                    item.Goal.UpdatedAt,
                    "Customer",
                    item.CurrentDecision?.CorrectionReason,
                    ParametersOf(item.Goal)
                )
            );
        }
        var (items, next) = WorkbenchPaging.Slice(
            versions.OrderByDescending(version => version.VersionNo).ToArray(),
            page
        );
        return new WorkbenchGoalVersionList(SchemaVersion, items, next);
    }

    private async Task<IReadOnlyDictionary<Guid, int>> LatestVersionsAsync(
        WorkbenchContext context,
        CancellationToken ct
    )
    {
        try
        {
            return await goalHistory.LatestVersionsAsync(
                context.TenantId,
                context.RelationshipId,
                ct
            );
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return new Dictionary<Guid, int>();
        }
    }

    private async Task<IReadOnlyList<WorkbenchGoalVersionEntry>> RecordedVersionsAsync(
        WorkbenchContext context,
        Guid goalId,
        CancellationToken ct
    )
    {
        try
        {
            return await goalHistory.ListAsync(
                context.TenantId,
                context.RelationshipId,
                goalId,
                ct
            );
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return [];
        }
    }

    public async Task<WorkbenchPlan?> GetCurrentPlanAsync(
        WorkbenchContext context,
        CancellationToken ct
    )
    {
        var data = await LoadAsync(context, ct);
        return PlanOf(data, new List<string>());
    }

    public async Task<WorkbenchCapabilityList> ListCapabilitiesAsync(
        WorkbenchContext context,
        CancellationToken ct
    )
    {
        var data = await LoadAsync(context, ct);
        return new WorkbenchCapabilityList(SchemaVersion, CapabilitiesOf(data));
    }

    public async Task<WorkbenchWorkItemList> ListWorkItemsAsync(
        WorkbenchContext context,
        WorkbenchPage page,
        CancellationToken ct
    )
    {
        var data = await LoadAsync(context, ct);
        var now = clock.GetUtcNow();
        var all = (data.Execution?.Items ?? [])
            .Select(item => new WorkbenchWorkItem(
                item.WorkItemId.ToString("D"),
                data.Declaration?.WorkItemTypes.FirstOrDefault() ?? "WORK_ITEM",
                item.SkillId,
                ExperienceBlockBuilder.Clip(
                    $"{ExperienceBlockBuilder.Humanize(item.SkillId)}: {ExperienceBlockBuilder.Humanize(item.Effect)}",
                    120
                ),
                WorkItemState(item.State),
                "Agent",
                now - data.Execution!.ProducedAt > TimeSpan.FromHours(1) ? "STALE" : "CURRENT",
                item.UpdatedAt
            ))
            .OrderByDescending(item => item.UpdatedAt)
            .ThenBy(item => item.ItemRef, StringComparer.Ordinal)
            .ToArray();
        var (items, next) = WorkbenchPaging.Slice(all, page);
        return new WorkbenchWorkItemList(SchemaVersion, items, next);
    }

    public async Task<IReadOnlyList<WorkbenchDecisionItem>> ListDecisionItemsAsync(
        WorkbenchContext context,
        CancellationToken ct
    ) => DecisionItems(await LoadAsync(context, ct), context);

    public async Task<WorkbenchDecisionList> ListDecisionsAsync(
        WorkbenchContext context,
        ChannelCapabilities capabilities,
        WorkbenchPage page,
        CancellationToken ct
    )
    {
        var all = (await ListDecisionItemsAsync(context, ct))
            .Select(item => item.Decision)
            .ToArray();
        var (items, next) = WorkbenchPaging.Slice(all, page);
        return new WorkbenchDecisionList(
            SchemaVersion,
            items,
            ExperienceBlockBuilder.ForDecisions(items, capabilities, context.RelationshipId),
            next
        );
    }

    public async Task<WorkbenchMonitor> GetMonitorAsync(
        WorkbenchContext context,
        ChannelCapabilities capabilities,
        CancellationToken ct
    )
    {
        var data = await LoadAsync(context, ct);
        var limitations = data.Limitations.ToList();
        var tiles = TilesOf(data, limitations);
        IReadOnlyList<WorkbenchAlert> alerts = [];
        return new WorkbenchMonitor(
            SchemaVersion,
            tiles,
            alerts,
            limitations.Count == 0 ? "CURRENT" : "STALE",
            limitations,
            ExperienceBlockBuilder.ForMonitor(
                tiles,
                alerts,
                limitations,
                capabilities,
                context.RelationshipId
            )
        );
    }

    public async Task<WorkbenchNarrativeList> ListNarrativesAsync(
        WorkbenchContext context,
        WorkbenchPage page,
        CancellationToken ct
    )
    {
        var data = await LoadAsync(context, ct);
        var structure =
            data.Declaration?.Narratives.FirstOrDefault()?.Structure ?? (IReadOnlyList<string>)[];
        var now = clock.GetUtcNow();
        var all = data
            .Reviews.OrderByDescending(review => review.PeriodEnd)
            .Select(review => new WorkbenchNarrative(
                review.ReviewId.ToString("D"),
                $"{review.PeriodStart:yyyy-MM-dd} to {review.PeriodEnd:yyyy-MM-dd}",
                review.CreatedAt,
                structure
                    .Select(part => NarrativePart(part, review))
                    .Where(part => part is not null)
                    .Select(part => part!)
                    .ToArray(),
                now - review.PeriodEnd > TimeSpan.FromDays(62) ? "STALE" : "CURRENT"
            ))
            .Where(item => item.Parts.Count > 0)
            .ToArray();
        var (items, next) = WorkbenchPaging.Slice(all, page);
        return new WorkbenchNarrativeList(SchemaVersion, items, next);
    }

    public async Task<WorkbenchWallet> GetWalletAsync(
        WorkbenchContext context,
        CancellationToken ct
    )
    {
        if (!MayViewWallet(context.Audience))
            throw new WorkbenchException(403, WorkbenchProblemCodes.SpendAuthorityUnavailable);
        var snapshot = await commercial.GetWalletAsync(context, ct);
        if (!snapshot.Available || snapshot.PeriodEnd is null)
            throw new WorkbenchException(
                503,
                WorkbenchProblemCodes.SpendCommercialUnavailable,
                snapshot.Limitation
            );
        return new WorkbenchWallet(
            SchemaVersion,
            context.RelationshipId,
            snapshot.PeriodEnd.Value,
            snapshot.Components,
            // No billing route prices or collects a top-up, so no client is offered one.
            false,
            context.Audience != WorkbenchAudiences.CustomerOwner
        );
    }

    public async Task<WorkbenchEvidenceList> ListEvidenceAsync(
        WorkbenchContext context,
        WorkbenchPage page,
        CancellationToken ct
    )
    {
        try
        {
            var items = await evidence.ListAsync(
                context.TenantId,
                context.RelationshipId,
                context.ParticipantId,
                ct
            );
            var all = items
                .Select(item => new WorkbenchEvidenceEntry(
                    item.EvidenceId.ToString("D"),
                    ExperienceBlockBuilder.Humanize(item.Subject),
                    ExperienceBlockBuilder.Clip(
                        item.PayloadState == "ERASED"
                            ? "The details of this record were erased on request."
                            : $"{ExperienceBlockBuilder.Humanize(item.Subject)} was recorded.",
                        500
                    ),
                    item.RecordedAt,
                    "CURRENT"
                ))
                .OrderByDescending(entry => entry.ProducedAt)
                .ThenBy(entry => entry.EvidenceRef, StringComparer.Ordinal)
                .ToArray();
            var (slice, next) = WorkbenchPaging.Slice(all, page);
            return new WorkbenchEvidenceList(
                SchemaVersion,
                all.Length == 0 ? "PENDING" : "RECORDED",
                slice,
                next
            );
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return new WorkbenchEvidenceList(SchemaVersion, "UNAVAILABLE", []);
        }
    }

    public static bool MayViewWallet(string audience) =>
        audience is WorkbenchAudiences.CustomerOwner or WorkbenchAudiences.Delegate;

    public static string Hash(Guid value) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value.ToString("N"))))[
            ..12
        ];

    public static string GoalState(RelationshipGoal goal) =>
        goal.Status switch
        {
            "SUPERSEDED" => "SUPERSEDED",
            "CLOSED" or "CANCELLED" or "ARCHIVED" => "CLOSED",
            _ => "ACTIVE",
        };

    public static IReadOnlyDictionary<string, string> ParametersOf(RelationshipGoal goal)
    {
        var result = new SortedDictionary<string, string>(StringComparer.Ordinal);
        if (string.IsNullOrWhiteSpace(goal.Baseline))
            return result;
        try
        {
            using var document = JsonDocument.Parse(goal.Baseline);
            if (
                document.RootElement.ValueKind == JsonValueKind.Object
                && document.RootElement.TryGetProperty("parameters", out var parameters)
                && parameters.ValueKind == JsonValueKind.Object
            )
                foreach (var item in parameters.EnumerateObject())
                    if (item.Value.ValueKind == JsonValueKind.String)
                        result[item.Name] = item.Value.GetString()!;
        }
        catch (JsonException)
        {
            return result;
        }
        return result;
    }

    private async Task<ExperienceDeclaration?> LoadDeclarationAsync(
        WorkbenchContext context,
        EmploymentRelationship relationship,
        EmploymentWorkspaceSnapshot? workspace,
        List<string> limitations,
        CancellationToken ct
    )
    {
        if (workspace is null || string.IsNullOrWhiteSpace(relationship.ProfessionalVersion))
        {
            limitations.Add("The agent's experience declaration is not available yet.");
            return null;
        }
        JsonDocument? manifest = null;
        try
        {
            manifest = await manifests.GetAsync(
                new AdmittedManifestRequest(
                    relationship.ProfessionalType,
                    relationship.ProfessionalVersion,
                    workspace.ManifestVersion,
                    context.ActorSubject,
                    context.EffectiveRole,
                    context.TenantId,
                    context.RelationshipId,
                    context.CorrelationId
                ),
                ct
            );
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            manifest = null;
        }
        if (manifest is null)
        {
            limitations.Add("The agent's experience declaration could not be read right now.");
            return null;
        }
        var scan = ExperienceManifestScanner.Scan(manifest.RootElement);
        if (scan.ExperienceCapable)
            return scan.Declaration;
        limitations.Add(
            scan.State == ExperienceScanResult.NotDeclared
                ? "This agent has not declared a workbench experience, so the standard workspace applies."
                : "This agent's experience declaration is not compatible with the workbench."
        );
        return null;
    }

    private static async Task<T?> TryAsync<T>(
        Func<Task<T>> read,
        string limitation,
        List<string> limitations
    )
        where T : class
    {
        try
        {
            return await read();
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            limitations.Add(limitation);
            return null;
        }
    }

    private static async Task<T?> TryOptionalAsync<T>(
        Func<Task<T?>> read,
        string limitation,
        List<string> limitations
    )
        where T : class
    {
        try
        {
            return await read();
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            limitations.Add(limitation);
            return null;
        }
    }

    private static WorkbenchReadiness ReadinessOf(EmploymentWorkspaceSnapshot? workspace)
    {
        string Pick(string name, string[] allowed, string fallback)
        {
            if (
                workspace is not null
                && workspace.Readiness.ValueKind == JsonValueKind.Object
                && workspace.Readiness.TryGetProperty(name, out var value)
                && value.ValueKind == JsonValueKind.String
                && allowed.Contains(value.GetString())
            )
                return value.GetString()!;
            return fallback;
        }
        return new WorkbenchReadiness(
            Pick("induction", InductionStates, "NOT_STARTED"),
            Pick("plan", PlanStates, "NO_PLAN"),
            Pick("operations", OperationStates, "LOCKED"),
            Pick("performance", PerformanceStates, "UNAVAILABLE")
        );
    }

    private static string PhaseOf(WorkbenchReadiness readiness)
    {
        if (readiness.Operations is "ELIGIBLE" or "ACTIVE" or "PAUSED" or "REASSESSMENT_REQUIRED")
            return "OPERATIONS";
        return readiness.Induction is "READY" or "READY_WITH_DEFERRED_ITEMS"
            ? "PLANNING"
            : "INDUCTION";
    }

    private static WorkbenchGoalSummary GoalSummary(
        RelationshipPortalGoal item,
        IReadOnlyDictionary<Guid, int> latestVersions
    ) =>
        new(
            item.Goal.GoalId,
            item.Goal.Measure,
            ExperienceBlockBuilder.Clip(item.Goal.Goal, 200),
            GoalState(item.Goal),
            Math.Max(
                item.HasPriorDecision ? 2 : 1,
                latestVersions.TryGetValue(item.Goal.GoalId, out var latest) ? latest : 0
            ),
            item.Goal.UpdatedAt
        );

    private static WorkbenchGoal GoalDetail(
        RelationshipPortalGoal item,
        ExperienceDeclaration? declaration,
        IReadOnlyDictionary<Guid, int> latestVersions
    )
    {
        var type = declaration?.GoalTypes.FirstOrDefault(value =>
            value.GoalTypeId == item.Goal.Measure
        );
        return new WorkbenchGoal(
            SchemaVersion,
            GoalSummary(item, latestVersions),
            ParametersOf(item.Goal),
            (type?.Measures ?? [])
                .Select(measure => new WorkbenchGoalMeasure(
                    measure.MeasureId,
                    measure.Unit,
                    item.Goal.DecisionThreshold,
                    null,
                    "UNAVAILABLE"
                ))
                .ToArray(),
            type?.Constraints ?? []
        );
    }

    private static IReadOnlyList<WorkbenchDecisionItem> DecisionItems(
        WorkbenchData data,
        WorkbenchContext context
    )
    {
        var items = new List<WorkbenchDecisionItem>();
        if (
            !WorkbenchAudiences.MayDecide(context.Audience)
            && !WorkbenchAudiences.MayResolve(context.Role)
        )
            return items;
        foreach (var skill in data.Skills)
        {
            if (
                skill.Status is not ("PROPOSED" or "SELECTED")
                || skill.Applicability != "APPLICABLE"
            )
                continue;
            var version = RelationshipConfigurationService.GetSkillVersion(skill);
            var labels = (data.Declaration?.Components ?? [])
                .Where(component => component.SkillId == skill.SkillId)
                .Select(component => component.Label)
                .ToArray();
            items.Add(
                new WorkbenchDecisionItem(
                    new WorkbenchDecision(
                        skill.ConfigurationId,
                        version,
                        ExperienceBlockBuilder.Clip(
                            $"Turn on {ExperienceBlockBuilder.Humanize(skill.SkillId)} for this relationship.",
                            500
                        ),
                        "Your approval",
                        labels.Length == 0
                            ? null
                            : ExperienceBlockBuilder.Clip(
                                $"Uses {string.Join(", ", labels)} from your package.",
                                240
                            ),
                        ExperienceBlockBuilder.ApproveLabel,
                        ExperienceBlockBuilder.DeclineLabel,
                        null,
                        $"skill:{skill.SkillId}",
                        "Customer",
                        "CURRENT"
                    ),
                    "SKILL",
                    skill.ConfigurationId,
                    version,
                    skill.SkillId,
                    skill.SkillVersion
                )
            );
        }
        foreach (var goal in data.Goals)
        {
            if (
                goal.SkillId == "UNASSIGNED"
                || GoalState(goal.Goal) != "ACTIVE"
                || goal.CurrentDecision?.Decision == "VERIFIED"
            )
                continue;
            var version = RelationshipConfigurationService.GetGoalVersion(goal.Goal);
            items.Add(
                new WorkbenchDecisionItem(
                    new WorkbenchDecision(
                        goal.Goal.GoalId,
                        version,
                        ExperienceBlockBuilder.Clip($"Confirm this goal: {goal.Goal.Goal}", 500),
                        "Your confirmation",
                        null,
                        "Confirm",
                        "Change it",
                        null,
                        $"goal:{goal.Goal.GoalId:D}",
                        "Customer",
                        "CURRENT"
                    ),
                    "GOAL",
                    goal.Goal.GoalId,
                    version,
                    goal.SkillId,
                    null
                )
            );
        }
        return items;
    }

    private static IReadOnlyList<WorkbenchTile> TilesOf(
        WorkbenchData data,
        List<string> limitations
    )
    {
        if (data.Declaration is null)
            return [];
        var tiles = new List<WorkbenchTile>();
        foreach (var tile in data.Declaration.Tiles)
        {
            if (!tile.Audiences.Contains(data.Audience))
                continue;
            var measure = data.Declaration.Measure(tile.MeasureId);
            tiles.Add(
                new WorkbenchTile(
                    tile.TileId,
                    tile.MeasureId,
                    ExperienceBlockBuilder.Humanize(tile.MeasureId),
                    NotReported,
                    measure?.Unit ?? string.Empty,
                    null,
                    null,
                    null,
                    "UNAVAILABLE",
                    ExperienceBlockBuilder.Humanize(measure?.EvidenceSource ?? "owner"),
                    tile.BlockType
                )
            );
        }
        if (tiles.Count > 0)
            limitations.Add("Measure values are not yet reported by their owners.");
        return tiles;
    }

    private static WorkbenchPlan? PlanOf(WorkbenchData data, List<string> limitations)
    {
        var workspace = data.Workspace;
        if (
            workspace?.CurrentPlanVersion is null
            || !workspace.Plans.TryGetValue(workspace.CurrentPlanVersion, out var plan)
            || plan.ValueKind != JsonValueKind.Object
        )
            return null;
        var goalRef = data
            .Goals.LastOrDefault(item => GoalState(item.Goal) == "ACTIVE")
            ?.Goal.GoalId;
        var parsedGoal =
            Text(plan, "goalRef") is { } text && Guid.TryParse(text, out var value)
                ? value
                : goalRef ?? Guid.Empty;
        var state = Text(plan, "state") switch
        {
            "READY_FOR_REVIEW" => "READY_FOR_REVIEW",
            "AGREED" or "ACTIVE" or "COMPLETED" => "AGREED",
            "SUPERSEDED" or "CANCELLED" => "SUPERSEDED",
            _ => "DRAFT",
        };
        var milestones = Items(plan, "milestones")
            .Select(item => new WorkbenchMilestone(
                Text(item, "itemId") ?? Text(item, "milestoneId") ?? "milestone",
                Text(item, "milestoneTypeId") ?? "MILESTONE",
                ExperienceBlockBuilder.Clip(
                    Text(item, "label") ?? Text(item, "title") ?? "Milestone",
                    200
                ),
                ExperienceBlockBuilder.Clip(Text(item, "dueMeaning") ?? "Date not set", 240),
                Text(item, "state") ?? "PROPOSED"
            ))
            .ToArray();
        var calendar = Items(plan, "calendarCommitments")
            .Select(item => new { Item = item, When = Text(item, "localDateTime") })
            .Where(entry => entry.When is { Length: >= 10 })
            .Select(entry => new WorkbenchCalendarEntry(
                entry.When![..10],
                ExperienceBlockBuilder.Clip(
                    Text(entry.Item, "label") ?? Text(entry.Item, "title") ?? "Calendar commitment",
                    200
                )
            ))
            .ToArray();
        if (Text(plan, "state") == "BLOCKED")
            limitations.Add("The current plan is blocked and needs attention.");
        return new WorkbenchPlan(
            SchemaVersion,
            workspace.CurrentPlanVersion,
            state,
            parsedGoal,
            milestones,
            calendar,
            []
        );
    }

    private IReadOnlyList<WorkbenchCapability> CapabilitiesOf(WorkbenchData data)
    {
        var declaration = data.Declaration;
        if (declaration is null)
            return [];
        return declaration
            .Cadence.Select(cadence =>
            {
                var selected = data
                    .Skills.Where(skill => skill.SkillId == cadence.SkillId)
                    .OrderByDescending(skill => skill.UpdatedAt)
                    .FirstOrDefault();
                var components = declaration
                    .Components.Where(component => component.SkillId == cadence.SkillId)
                    .ToArray();
                var availability =
                    components.Length > 0
                    && components.All(item => item.Availability == "UNAVAILABLE")
                        ? "UNAVAILABLE"
                    : selected is null && components.Any(item => item.Availability == "DEFAULT_OFF")
                        ? "DEFAULT_OFF"
                    : "AVAILABLE";
                var state = selected?.Status switch
                {
                    "ACCEPTED" => "ACTIVE",
                    "DEFERRED" => "PAUSED",
                    _ => "NOT_ENABLED",
                };
                return new WorkbenchCapability(
                    cadence.SkillId,
                    ExperienceBlockBuilder.Humanize(cadence.SkillId),
                    availability,
                    state,
                    declaration.DefaultApprovalMode,
                    $"{ExperienceBlockBuilder.Humanize(cadence.Trigger)}; {ExperienceBlockBuilder.Humanize(cadence.Window)}",
                    components.Select(item => item.ComponentId).ToArray(),
                    availability == "UNAVAILABLE" ? "This capability is not released yet." : null
                );
            })
            .ToArray();
    }

    public IReadOnlyList<WorkbenchCapability> Capabilities(WorkbenchData data) =>
        CapabilitiesOf(data);

    private async Task<IReadOnlyList<WorkbenchComponentBalance>?> WalletComponentsAsync(
        WorkbenchContext context,
        List<string> limitations,
        CancellationToken ct
    )
    {
        if (!MayViewWallet(context.Audience))
            return null;
        var snapshot = await commercial.GetWalletAsync(context, ct);
        if (snapshot.Limitation is not null)
            limitations.Add(snapshot.Limitation);
        return snapshot.Available ? snapshot.Components : null;
    }

    private async Task<string> EvidenceStateAsync(WorkbenchContext context, CancellationToken ct) =>
        (await ListEvidenceAsync(context, WorkbenchPage.First, ct)).EvidenceState;

    private static WorkbenchRecommendedAction? RecommendedAction(
        WorkbenchData data,
        int decisionCount,
        WorkbenchPlan? plan,
        bool hasGoal
    )
    {
        if (!WorkbenchAudiences.MayDecide(data.Audience))
            return null;
        if (!hasGoal)
            return new WorkbenchRecommendedAction(
                "create_goal",
                "Set your first goal",
                "A goal lets the plan and the measures be defined."
            );
        if (plan is null)
            return new WorkbenchRecommendedAction(
                "propose_plan",
                "Propose a plan",
                "A plan turns the goal into milestones."
            );
        if (plan.State == "READY_FOR_REVIEW")
            return new WorkbenchRecommendedAction(
                "accept_plan",
                "Review the plan",
                "The plan is ready for your agreement."
            );
        return decisionCount > 0
            ? new WorkbenchRecommendedAction(
                "resolve_decision",
                "Decide what is waiting",
                $"{decisionCount} decision(s) need you."
            )
            : null;
    }

    private static IReadOnlyList<WorkbenchAvailableCommand> AvailableCommands(
        WorkbenchData data,
        WorkbenchContext context,
        WorkbenchPlan? plan,
        bool hasGoal
    )
    {
        var mayDecide = WorkbenchAudiences.MayDecide(context.Audience);
        var mayManage = WorkbenchAudiences.MayManageSpend(context.Audience);
        var stopped = data.Relationship.State == EmploymentRelationshipState.StoppedEmergency;
        const string StoppedReason = "The relationship is stopped.";
        const string NotYours = "Your role cannot do this.";
        string? Reason(bool allowed, bool blocked = false, string? other = null) =>
            !allowed ? NotYours
            : blocked ? other ?? StoppedReason
            : null;
        WorkbenchAvailableCommand Command(string id, string label, string? reason) =>
            new(id, label, reason is null, reason);
        return
        [
            Command("create_goal", "Set a goal", Reason(mayDecide, stopped)),
            Command(
                "propose_plan",
                "Propose a plan",
                Reason(mayDecide, stopped || !hasGoal, stopped ? null : "Set a goal first.")
            ),
            Command(
                "accept_plan",
                "Agree the plan",
                Reason(
                    mayDecide,
                    stopped || plan?.State != "READY_FOR_REVIEW",
                    stopped ? null : "No plan is ready for review."
                )
            ),
            Command("resolve_decision", "Decide", Reason(mayDecide, stopped)),
            Command("change_capability", "Change a capability", Reason(mayDecide, stopped)),
            Command("top_up", "Add to your allowance", TopUpNotOffered),
            Command("export_evidence", "Export evidence", Reason(mayDecide, false)),
            Command("pause", "Pause", Reason(mayManage, stopped)),
            Command(
                "stop",
                "Stop now",
                Reason(mayManage || mayDecide, stopped, "Already stopped.")
            ),
            Command("handoff", "Continue on the web", Reason(true, false)),
        ];
    }

    private static string WorkItemState(string state) =>
        state.ToUpperInvariant() switch
        {
            "PENDING" or "QUEUED" or "PROPOSED" => "PROPOSED",
            "RUNNING" or "IN_PROGRESS" or "STARTED" => "IN_PROGRESS",
            "COMPLETED" or "SUCCEEDED" or "DONE" => "COMPLETED",
            "FAILED" or "BLOCKED" => "BLOCKED",
            "CANCELLED" => "CANCELLED",
            "WAITING_APPROVAL" or "AWAITING_APPROVAL" => "WAITING_ON_CUSTOMER",
            _ => "OUTCOME_UNKNOWN",
        };

    private static WorkbenchNarrativePart? NarrativePart(
        string part,
        PerformanceReviewProjectionV1 review
    )
    {
        var text = part switch
        {
            "WHAT_HAPPENED" => review.WorkDelivery.Summary,
            "WHAT_I_LEARNED" => review.AgentQuality.Summary,
            "WHAT_I_TRIED" => review.CustomerBusinessOutcome.Summary,
            "WHAT_CHANGES_NEXT_MONTH" => review.Recommendation,
            "WHAT_I_NEED_FROM_YOU" => review.CustomerAssessment.Summary,
            _ => null,
        };
        return string.IsNullOrWhiteSpace(text)
            ? null
            : new WorkbenchNarrativePart(part, ExperienceBlockBuilder.Clip(text, 1024));
    }

    private static IEnumerable<JsonElement> Items(JsonElement parent, string name) =>
        parent.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.Array
            ? value.EnumerateArray().Where(item => item.ValueKind == JsonValueKind.Object)
            : [];

    private static string? Text(JsonElement parent, string name) =>
        parent.ValueKind == JsonValueKind.Object
        && parent.TryGetProperty(name, out var value)
        && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;
}
