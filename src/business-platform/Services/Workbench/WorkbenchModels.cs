// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01, C6-02
// Constitutional basis: C-001, C-005, C-023, C-026, C-059, C-063, ADR-051

using System.Text.Json;
using System.Text.Json.Serialization;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services.Workbench;

/// <summary>Audiences of the workbench; the server decides the audience from the caller's relationship role.</summary>
public static class WorkbenchAudiences
{
    public const string CustomerOwner = "customer_owner";
    public const string Delegate = "delegate";
    public const string Beneficiary = "beneficiary";
    public const string Steward = "steward";

    public static readonly IReadOnlySet<string> All = new HashSet<string>(StringComparer.Ordinal)
    {
        CustomerOwner,
        Delegate,
        Beneficiary,
        Steward,
    };

    public static string FromRole(RelationshipParticipantRole role) =>
        role switch
        {
            RelationshipParticipantRole.Employer => CustomerOwner,
            RelationshipParticipantRole.RelationshipManager => Delegate,
            RelationshipParticipantRole.ConstitutionalAuthority => Steward,
            _ => Beneficiary,
        };

    public static bool MayManageSpend(string audience) => audience == CustomerOwner;

    public static bool MayDecide(string audience) => audience is CustomerOwner or Delegate;

    /// <summary>The goal and capability owners accept decisions only from the employer and the evaluator.</summary>
    public static bool MayResolve(RelationshipParticipantRole role) =>
        role is RelationshipParticipantRole.Employer or RelationshipParticipantRole.Evaluator;
}

/// <summary>The problem codes of the workbench OpenAPI, written exactly as the contract names them.</summary>
public static class WorkbenchProblemCodes
{
    public const string Disabled = "WORKBENCH_DISABLED";
    public const string RequestInvalid = "WORKBENCH_REQUEST_INVALID";
    public const string VersionConflict = "WORKBENCH_VERSION_CONFLICT";
    public const string IdempotencyConflict = "WORKBENCH_IDEMPOTENCY_CONFLICT";
    public const string Unavailable = "WORKBENCH_UNAVAILABLE";
    public const string SpendPurposeUnmapped = "SPEND_PURPOSE_UNMAPPED";
    public const string SpendAuthorityUnavailable = "SPEND_AUTHORITY_UNAVAILABLE";
    public const string SpendCommercialUnavailable = "SPEND_COMMERCIAL_UNAVAILABLE";
    public const string WalletInsufficient = "WALLET_INSUFFICIENT";
    public const string WalletIdempotencyConflict = "WALLET_IDEMPOTENCY_CONFLICT";
    public const string ComponentNotYetReleased = "COMPONENT_NOT_YET_RELEASED";
    public const string ProactiveAllowanceExhausted = "PROACTIVE_ALLOWANCE_EXHAUSTED";
    public const string TrialAlreadyUsed = "TRIAL_ALREADY_USED";
    public const string TrialAlreadyUsedByIdentity = "TRIAL_ALREADY_USED_BY_IDENTITY";
    public const string PackageComponentNotAvailable = "PACKAGE_COMPONENT_NOT_AVAILABLE";
}

/// <summary>A workbench failure that maps to one problem code and HTTP status.</summary>
public sealed class WorkbenchException(int status, string code, string? detail = null)
    : Exception(code)
{
    public int Status { get; } = status;
    public string Code { get; } = code;
    public string? Detail { get; } = detail;
}

public sealed record WorkbenchProblem(
    string Type,
    string Title,
    int Status,
    string Code,
    string CorrelationId,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Detail = null
);

public sealed record WorkbenchReadiness(
    string Induction,
    string Plan,
    string Operations,
    string Performance
);

public sealed record WorkbenchDecision(
    Guid DecisionId,
    string Version,
    string Effect,
    string Authority,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Cost,
    string ConfirmLabel,
    string CancelLabel,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        DateTimeOffset? ExpiresAt,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? ItemRef,
    string Owner,
    string Freshness
);

public sealed record WorkbenchTile(
    string TileId,
    string MeasureId,
    string Label,
    string Value,
    string Unit,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Target,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Trend,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Basis,
    string Freshness,
    string Owner,
    string BlockType
);

public sealed record WorkbenchComponentBalance(
    string ComponentId,
    string Label,
    int Remaining,
    int Quantity,
    DateTimeOffset PeriodEnd
);

public sealed record WorkbenchAlert(
    string AlertId,
    string Signal,
    string Severity,
    string Message,
    DateTimeOffset RaisedAt,
    string Freshness
);

public sealed record WorkbenchRecommendedAction(string CommandId, string Label, string Reason);

public sealed record WorkbenchAvailableCommand(
    string CommandId,
    string Label,
    bool Enabled,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? DisabledReason = null
);

public sealed record ExperienceFallbackBlock(string Type, JsonElement Data);

public sealed record ExperienceBlock(
    string Id,
    string Type,
    int Version,
    string Sensitivity,
    JsonElement Data,
    IReadOnlyList<ExperienceFallbackBlock> Fallback,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Spoken = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Label = null
);

public sealed record WorkbenchProjection(
    string SchemaVersion,
    Guid RelationshipRef,
    string Audience,
    string Phase,
    WorkbenchReadiness Readiness,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? CurrentGoalRef,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? CurrentPlanVersion,
    IReadOnlyList<WorkbenchDecision> Decisions,
    IReadOnlyList<WorkbenchTile> Tiles,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        IReadOnlyList<WorkbenchComponentBalance>? Components,
    IReadOnlyList<WorkbenchAlert> Alerts,
    string EvidenceState,
    string SourceFreshness,
    IReadOnlyList<string> Limitations,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        WorkbenchRecommendedAction? RecommendedNextAction,
    IReadOnlyList<WorkbenchAvailableCommand> AvailableCommands,
    IReadOnlyList<ExperienceBlock> Blocks,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        IReadOnlyList<WorkbenchNavigationEntry>? Navigation = null
);

/// <summary>An entry the agent declared for its context menu, in platform terms. No layout, markup or code.</summary>
public sealed record WorkbenchNavigationEntry(
    string EntryId,
    string LabelKey,
    string Label,
    string Icon,
    int Order,
    string SurfaceKind,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Target,
    IReadOnlyList<string> Blocks,
    bool Available
);

public sealed record WorkbenchCommandReceipt(
    string SchemaVersion,
    Guid OperationRef,
    string Status,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? ResourceRef,
    string Version,
    bool Replayed,
    string CorrelationId
);

public sealed record WorkbenchGoalSummary(
    Guid GoalId,
    string GoalTypeId,
    string Title,
    string State,
    int CurrentVersion,
    DateTimeOffset UpdatedAt
);

public sealed record WorkbenchGoalList(
    string SchemaVersion,
    IReadOnlyList<WorkbenchGoalSummary> Items,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? NextCursor = null
);

public sealed record WorkbenchGoalMeasure(
    string MeasureId,
    string Unit,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Target,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Baseline,
    string Freshness
);

public sealed record WorkbenchGoal(
    string SchemaVersion,
    WorkbenchGoalSummary Goal,
    IReadOnlyDictionary<string, string> Parameters,
    IReadOnlyList<WorkbenchGoalMeasure> Measures,
    IReadOnlyList<string> Constraints
);

public sealed record WorkbenchGoalVersion(
    int VersionNo,
    DateTimeOffset RevisedAt,
    string RevisedBy,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Reason,
    IReadOnlyDictionary<string, string> Parameters
);

public sealed record WorkbenchGoalVersionList(
    string SchemaVersion,
    IReadOnlyList<WorkbenchGoalVersion> Items,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? NextCursor = null
);

public sealed record WorkbenchMilestone(
    string MilestoneId,
    string MilestoneTypeId,
    string Title,
    string DueMeaning,
    string State
);

public sealed record WorkbenchCalendarEntry(string Date, string Title);

public sealed record WorkbenchPlan(
    string SchemaVersion,
    string PlanVersion,
    string State,
    Guid GoalRef,
    IReadOnlyList<WorkbenchMilestone> Milestones,
    IReadOnlyList<WorkbenchCalendarEntry> Calendar,
    IReadOnlyList<string> Limitations
);

public sealed record WorkbenchCapability(
    string SkillId,
    string Label,
    string Availability,
    string State,
    string ApprovalMode,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? NextRunMeaning,
    IReadOnlyList<string> ComponentIds,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Limitation
);

public sealed record WorkbenchCapabilityList(
    string SchemaVersion,
    IReadOnlyList<WorkbenchCapability> Items
);

public sealed record WorkbenchCapabilityCommandResult(
    string SchemaVersion,
    string Outcome,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? OperationRef,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Message,
    string CorrelationId
);

public sealed record WorkbenchWorkItem(
    string ItemRef,
    string WorkItemType,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? SkillId,
    string Label,
    string State,
    string Owner,
    string Freshness,
    DateTimeOffset UpdatedAt
);

public sealed record WorkbenchWorkItemList(
    string SchemaVersion,
    IReadOnlyList<WorkbenchWorkItem> Items,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? NextCursor = null
);

public sealed record WorkbenchDecisionList(
    string SchemaVersion,
    IReadOnlyList<WorkbenchDecision> Items,
    IReadOnlyList<ExperienceBlock> Blocks,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? NextCursor = null
);

public sealed record WorkbenchMonitor(
    string SchemaVersion,
    IReadOnlyList<WorkbenchTile> Tiles,
    IReadOnlyList<WorkbenchAlert> Alerts,
    string SourceFreshness,
    IReadOnlyList<string> Limitations,
    IReadOnlyList<ExperienceBlock> Blocks
);

public sealed record WorkbenchNarrativePart(string Part, string Text);

public sealed record WorkbenchNarrative(
    string NarrativeId,
    string PeriodLabel,
    DateTimeOffset PublishedAt,
    IReadOnlyList<WorkbenchNarrativePart> Parts,
    string Freshness
);

public sealed record WorkbenchNarrativeList(
    string SchemaVersion,
    IReadOnlyList<WorkbenchNarrative> Items,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? NextCursor = null
);

public sealed record WorkbenchWallet(
    string SchemaVersion,
    Guid RelationshipRef,
    DateTimeOffset PeriodEnd,
    IReadOnlyList<WorkbenchComponentBalance> Components,
    bool TopUpAvailable,
    bool AskAccountOwner
);

public sealed record WorkbenchTopupReceipt(
    string SchemaVersion,
    Guid OperationRef,
    string Status,
    string ComponentId,
    int Quantity,
    long PriceInclGstPaise,
    long BasePricePaise,
    long GstPaise,
    string TaxTreatment,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? CheckoutHandoffRef,
    string CorrelationId
);

public sealed record WorkbenchEvidenceEntry(
    string EvidenceRef,
    string Kind,
    string Summary,
    DateTimeOffset ProducedAt,
    string Freshness
);

public sealed record WorkbenchEvidenceList(
    string SchemaVersion,
    string EvidenceState,
    IReadOnlyList<WorkbenchEvidenceEntry> Items,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? NextCursor = null
);

public sealed record WorkbenchHandoff(
    string SchemaVersion,
    Guid HandoffRef,
    string DestinationRef,
    DateTimeOffset ExpiresAt,
    bool SingleUse
);

public sealed record ConsumeWorkbenchHandoffRequest(string SchemaVersion, string DestinationRef);

public sealed record WorkbenchHandoffConsumption(
    string SchemaVersion,
    string Purpose,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? ContextRef
);

public sealed record SubscriptionChangeReceipt(
    string SchemaVersion,
    Guid OperationRef,
    string Kind,
    string Status,
    DateTimeOffset EffectiveAt,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        long? ProratedFeeDifferencePaise,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] long? RefundFeePaise,
    string TaxTreatment,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? BlockedReason,
    string CorrelationId
);

public sealed record CreateWorkbenchGoalRequest(
    string SchemaVersion,
    string ExpectedVersion,
    string GoalTypeId,
    string Title,
    Dictionary<string, string> Parameters,
    string? StarterRef = null
);

public sealed record ReviseWorkbenchGoalRequest(
    string SchemaVersion,
    string ExpectedVersion,
    Dictionary<string, string> Parameters,
    string Reason,
    string? Title = null
);

public sealed record ProposeWorkbenchPlanMilestone(
    string MilestoneTypeId,
    string Title,
    string? DueDate = null
);

public sealed record ProposeWorkbenchPlanRequest(
    string SchemaVersion,
    string ExpectedVersion,
    Guid GoalId,
    List<ProposeWorkbenchPlanMilestone> Milestones,
    List<string>? CalendarWindows = null
);

public sealed record AcceptWorkbenchPlanRequest(
    string SchemaVersion,
    string ExpectedVersion,
    bool AcknowledgedLimitations
);

public sealed record WorkbenchCapabilityCommandRequest(
    string SchemaVersion,
    string ExpectedVersion,
    string Command,
    string? ApprovalMode = null
);

public sealed record ResolveWorkbenchDecisionRequest(
    string SchemaVersion,
    string ExpectedVersion,
    string Resolution,
    string? Note = null
);

public sealed record CreateWorkbenchTopupRequest(
    string SchemaVersion,
    string ExpectedVersion,
    string ComponentId,
    int Quantity
);

public sealed record ExportWorkbenchEvidenceRequest(
    string SchemaVersion,
    string ExpectedVersion,
    string Scope,
    string Format,
    string? ScopeRef = null,
    string? PeriodFrom = null,
    string? PeriodTo = null
);

public sealed record WorkbenchControlRequest(
    string SchemaVersion,
    string ExpectedVersion,
    string? Reason = null
);

public sealed record CreateWorkbenchHandoffRequest(
    string SchemaVersion,
    string ExpectedVersion,
    string Purpose,
    string? ContextRef = null
);

public sealed record SubscriptionChangeSelection(
    string ComponentId,
    List<string>? SelectedItemRefs = null
);

public sealed record SubscriptionChangeRequest(
    string SchemaVersion,
    string ExpectedVersion,
    string Kind,
    Guid? TargetPackageId = null,
    string? SkillId = null,
    List<SubscriptionChangeSelection>? Selections = null,
    string? Reason = null
);
