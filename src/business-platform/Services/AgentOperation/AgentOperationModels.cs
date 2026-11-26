// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R002, R005, R007, R013, R015, R030, R036
// Constitutional basis: C-001, C-005, C-023, C-059, C-061, C-063

using System.Text.Json;
using Waooaw.BusinessPlatform.Services.Workbench;

namespace Waooaw.BusinessPlatform.Services.AgentOperation;

/// <summary>The closed platform vocabulary of Agent Operation. No agent declares a word outside it (WC174-R033).</summary>
public static class OperationVocabulary
{
    public static readonly IReadOnlyList<string> ModeIds = ["INDUCT", "GOALS", "OPERATIONS"];

    public static class Kinds
    {
        public const string Event = "EVENT";
        public const string Placeholder = "PLACEHOLDER";
        public const string PlanNode = "PLAN_NODE";
        public const string Content = "CONTENT";
        public const string Slot = "SLOT";
        public const string Note = "NOTE";
        public const string Goal = "GOAL";
        public const string ProfileLabel = "PROFILE_LABEL";
        public const string Presence = "PRESENCE";
        public const string Finding = "FINDING";
        public const string Digest = "DIGEST";

        public static readonly IReadOnlySet<string> Calendar = new HashSet<string>(
            StringComparer.Ordinal
        )
        {
            Event,
            Placeholder,
            PlanNode,
            Content,
            Slot,
            Note,
        };

        public static readonly IReadOnlySet<string> CustomerCreatable = new HashSet<string>(
            StringComparer.Ordinal
        )
        {
            Event,
            Placeholder,
            PlanNode,
            Content,
            Slot,
            Note,
        };

        public static readonly IReadOnlySet<string> AgentProposable = new HashSet<string>(
            StringComparer.Ordinal
        )
        {
            Event,
            PlanNode,
            Content,
            ProfileLabel,
            Finding,
            Digest,
            Goal,
        };
    }

    /// <summary>MD8: what the customer and the agent may do with an item right now.</summary>
    public static class AuthorStates
    {
        public const string AgentSuggested = "AGENT_SUGGESTED";
        public const string CustomerEdited = "CUSTOMER_EDITED";
        public const string CustomerOwned = "CUSTOMER_OWNED";
        public const string ApprovedVersion = "APPROVED_VERSION";
    }

    public static class States
    {
        public const string Suggested = "SUGGESTED";
        public const string Accepted = "ACCEPTED";
        public const string Hidden = "HIDDEN";
        public const string CustomerAdded = "CUSTOMER_ADDED";
        public const string Proposed = "PROPOSED";
        public const string Draft = "DRAFT";
        public const string Approved = "APPROVED";
        public const string Rejected = "REJECTED";
        public const string Inferred = "INFERRED";
        public const string Confirmed = "CONFIRMED";
        public const string PendingConfirmation = "PENDING_CONFIRMATION";
        public const string Scheduled = "SCHEDULED";
        public const string Published = "PUBLISHED";
        public const string PublishFailed = "PUBLISH_FAILED";
    }

    /// <summary>MD5: a platform's presence for one relationship.</summary>
    public static class Presence
    {
        public const string Unanswered = "UNANSWERED";
        public const string Present = "PRESENT";
        public const string NotPresent = "NOT_PRESENT";
        public const string PublicOnly = "PUBLIC_ONLY";
        public const string ConnectedTested = "CONNECTED_TESTED";
        public const string NeedsRepair = "NEEDS_REPAIR";
        public const string NotYetConnectable = "NOT_YET_CONNECTABLE";

        public static readonly IReadOnlySet<string> CustomerAnswers = new HashSet<string>(
            StringComparer.Ordinal
        )
        {
            Present,
            NotPresent,
            PublicOnly,
        };
    }

    /// <summary>How an outcome was reached; the only thing the share-by-route measure records (WC174-R032).</summary>
    public static class Routes
    {
        public const string Asked = "ASKED";
        public const string Accepted = "ACCEPTED";
        public const string Tool = "TOOL";

        public static readonly IReadOnlySet<string> All = new HashSet<string>(
            StringComparer.Ordinal
        )
        {
            Asked,
            Accepted,
            Tool,
        };
    }

    public static class Gates
    {
        public const string Publish = "PUBLISH";
        public const string Schedule = "SCHEDULE";
        public const string GenerateMedia = "GENERATE_MEDIA";
    }

    public static class Origins
    {
        public const string Agent = "AGENT";
        public const string Customer = "CUSTOMER";
    }

    public const int DefaultChatAllowance = 1000;
    public const int MaximumChatAllowance = 1_000_000;
    public const int MaximumTitleLength = 160;
    public const int MaximumBodyLength = 2000;
    public const int MaximumCustomLayers = 8;
    public const int MaximumProposalsPerCall = 100;

    private static readonly char[] Markup = ['<', '>', '{', '}', '`', '\\'];

    /// <summary>Plain words only: no markup, template tokens or control characters in anything a customer or agent writes.</summary>
    public static bool IsPlainText(string? value, int maximum) =>
        !string.IsNullOrWhiteSpace(value)
        && value.Length <= maximum
        && value.IndexOfAny(Markup) < 0
        && !value.Any(character => char.IsControl(character) && character != '\n');
}

/// <summary>One record on the relationship's workspace: an event, a plan node, a piece of content, a goal, a label.</summary>
public sealed record OperationItem(
    Guid TenantId,
    Guid RelationshipId,
    Guid ItemId,
    string Kind,
    string? Layer,
    string? LevelId,
    Guid? ParentId,
    string Title,
    string? Body,
    DateOnly? StartDate,
    DateOnly? EndDate,
    string State,
    string AuthorState,
    int VersionNo,
    int ApprovedVersionNo,
    string Origin,
    string? SourceRef,
    string? Reason,
    double? Confidence,
    string? PlatformId,
    string? ComponentId,
    JsonElement Payload,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    string UpdatedBy
)
{
    public bool IsApproved =>
        AuthorState == OperationVocabulary.AuthorStates.ApprovedVersion
        && ApprovedVersionNo == VersionNo;
}

/// <summary>Per relationship: the remembered mode, layer switches, tour flag and the conversation counter.</summary>
public sealed record RelationshipOperationState(
    Guid TenantId,
    Guid RelationshipId,
    string? LastMode,
    string? LastSurface,
    IReadOnlyDictionary<string, bool> Layers,
    IReadOnlyList<CustomLayer> CustomLayers,
    bool TourSeen,
    int ChatsUsed,
    bool PublishAuthority,
    DateTimeOffset UpdatedAt
)
{
    public static RelationshipOperationState Empty(
        Guid tenantId,
        Guid relationshipId,
        DateTimeOffset now
    ) =>
        new(
            tenantId,
            relationshipId,
            null,
            null,
            new Dictionary<string, bool>(StringComparer.Ordinal),
            [],
            false,
            0,
            false,
            now
        );
}

public sealed record CustomLayer(string LayerId, string Label);

/// <summary>Founder-set values shared by every relationship. Absent keys mean the default.</summary>
public sealed record AgentOperationSettings(
    int ChatAllowanceDefault,
    IReadOnlyDictionary<string, int> ChatAllowanceByProfessionalType,
    bool InstagramConnectEnabled,
    bool PublishSandboxOnly,
    IReadOnlyList<string> SandboxAccountIds,
    bool RegistryReadsEnabled = false
)
{
    public static AgentOperationSettings Default { get; } =
        new(
            OperationVocabulary.DefaultChatAllowance,
            new Dictionary<string, int>(StringComparer.Ordinal),
            InstagramConnectEnabled: false,
            PublishSandboxOnly: true,
            SandboxAccountIds: [],
            RegistryReadsEnabled: false
        );

    public int AllowanceFor(string professionalType) =>
        ChatAllowanceByProfessionalType.TryGetValue(professionalType, out var value)
            ? value
            : ChatAllowanceDefault;
}

/// <summary>A refusal the customer can read: a stable code plus plain words and, where it helps, the mode that fixes it.</summary>
public sealed class AgentOperationException(
    int status,
    string code,
    string detail,
    string? nextMode = null
) : Exception(detail)
{
    public int Status { get; } = status;
    public string Code { get; } = code;
    public string? NextMode { get; } = nextMode;
}

public static class AgentOperationCodes
{
    public const string Invalid = "OPERATION_REQUEST_INVALID";
    public const string NotFound = "OPERATION_ITEM_NOT_FOUND";
    public const string UnknownLayer = "OPERATION_LAYER_UNKNOWN";
    public const string LayerOff = "OPERATION_LAYER_OFF";
    public const string CustomerOwned = "OPERATION_ITEM_CUSTOMER_OWNED";
    public const string ParentNotApproved = "OPERATION_PARENT_NOT_APPROVED";
    public const string GateBlocked = "OPERATION_GATE_BLOCKED";
    public const string NotApproved = "OPERATION_NOT_APPROVED";
    public const string LimitReached = "OPERATION_PACKAGE_LIMIT_REACHED";
    public const string ChatLimitReached = "OPERATION_CHAT_ALLOWANCE_REACHED";
    public const string NotConnected = "OPERATION_ACCOUNT_NOT_CONNECTED";
    public const string SandboxOnly = "OPERATION_SANDBOX_ACCOUNT_ONLY";
    public const string PublishAuthorityMissing = "OPERATION_PUBLISH_AUTHORITY_MISSING";
    public const string Stopped = "OPERATION_RELATIONSHIP_STOPPED";
    public const string NotEnabled = "OPERATION_NOT_ENABLED_YET";
    public const string Conflict = "OPERATION_CONFLICT";
}

/// <summary>The result of one agent proposal batch: what was stored and what was refused, each with its reason.</summary>
public sealed record ProposalOutcome(int Stored, IReadOnlyList<ProposalRefusal> Refused);

public sealed record ProposalRefusal(string ProposalKey, string Code);

/// <summary>One agent proposal in platform terms. The platform stores it as a suggestion and never applies it.</summary>
public sealed record OperationProposal(
    string ProposalKey,
    string Kind,
    string? Layer,
    string? LevelId,
    string? ParentProposalKey,
    string Title,
    string? Body,
    DateOnly? StartDate,
    DateOnly? EndDate,
    string? SourceRef,
    string? Reason,
    double? Confidence,
    string? PlatformId,
    string? ComponentId,
    JsonElement? Payload
);

public sealed record OperationCaller(
    Guid TenantId,
    Guid RelationshipId,
    Guid ParticipantId,
    string Actor,
    string Audience,
    WorkbenchContext? Workbench = null
);
