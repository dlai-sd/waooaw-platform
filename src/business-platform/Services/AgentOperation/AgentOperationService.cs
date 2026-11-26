// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R002, R005, R006, R007, R013, R014, R015, R017, R018, R020, R021, R030, R031, R032, R036
// Constitutional basis: C-001, C-005, C-023, C-059, C-061, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Waooaw.BusinessPlatform.Services.Workbench;

namespace Waooaw.BusinessPlatform.Services.AgentOperation;

public sealed record ItemView(
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
    bool IsApproved,
    bool IsSuggestion,
    string Origin,
    string? SourceRef,
    string? Reason,
    double? Confidence,
    string? PlatformId,
    string? ComponentId,
    JsonElement Payload,
    DateTimeOffset UpdatedAt
);

public sealed record NextStep(
    string ModeId,
    string TextKey,
    string Text,
    string PrimaryLabel,
    string Command,
    string? Target
);

public sealed record ModeReadiness(
    string ModeId,
    string State,
    int Done,
    int Total,
    string Line,
    NextStep? Next
);

public sealed record ModeView(ExperienceMode Mode, ModeReadiness Readiness);

public sealed record LayerView(
    string LayerId,
    string LabelKey,
    string Label,
    bool Sensitive,
    bool On,
    bool Custom
);

public sealed record PlatformView(
    string PlatformId,
    string LabelKey,
    string Label,
    string Connector,
    string Presence,
    bool CanConnect,
    Guid? ConnectionId,
    string? AccountName,
    string Note
);

public sealed record ChatAllowanceView(int Allowed, int Used, int Remaining, bool Reached);

public sealed record LimitView(
    string ComponentId,
    string Label,
    int? Remaining,
    int Committed,
    bool Known
);

public sealed record GoalSkillView(string SkillId, string State, ItemView? Goal);

public sealed record OperationFrame(
    string SchemaVersion,
    bool ModesDeclared,
    IReadOnlyList<ModeView> Modes,
    IReadOnlyList<LayerView> Layers,
    IReadOnlyList<ExperiencePlanLevel> PlanLevels,
    IReadOnlyList<PlatformView> Platforms,
    IReadOnlyList<string> Views,
    string? LastMode,
    string? LastSurface,
    bool TourSeen,
    NextStep? Next,
    ChatAllowanceView Chats,
    bool PublishAuthority,
    bool Stopped,
    DateTimeOffset GeneratedAt,
    IReadOnlyList<GoalSkillView> GoalSkills,
    IReadOnlyList<string> ApprovalModes
);

public sealed record CalendarView(
    string SchemaVersion,
    DateOnly From,
    DateOnly To,
    IReadOnlyList<ItemView> Entries,
    IReadOnlyList<LayerView> Layers,
    IReadOnlyList<LimitView> Limits,
    string EvidenceState,
    DateTimeOffset? SourceFreshness
);

public sealed record PlanTreeView(
    string SchemaVersion,
    IReadOnlyList<ExperiencePlanLevel> Levels,
    IReadOnlyList<ItemView> Nodes
);

public sealed record OperationContext(
    string SchemaVersion,
    string? Mode,
    string? View,
    ItemView? Selected,
    NextStep? Gap,
    ChatAllowanceView Chats,
    IReadOnlyList<LimitView> Limits,
    int PendingSuggestions,
    int CustomerOwned
);

public sealed record CreateItemRequest(
    string Kind,
    string? Layer,
    string? LevelId,
    Guid? ParentId,
    string Title,
    string? Body,
    DateOnly? StartDate,
    DateOnly? EndDate,
    string? PlatformId,
    string? ComponentId,
    string? Route
);

public sealed record EditItemRequest(
    string? Title,
    string? Body,
    DateOnly? StartDate,
    DateOnly? EndDate,
    int ExpectedVersion
);

public sealed record GoalRequest(
    string Baseline,
    string Target,
    string EvidenceSource,
    string Cadence,
    string AuthorityState
);

public sealed record ShareDay(
    DateOnly Day,
    int Asked,
    int Accepted,
    int Tool,
    double? AssistantShare
);

public sealed record ShareView(
    string SchemaVersion,
    IReadOnlyList<ShareDay> Days,
    int RelationshipsCounted,
    double? AssistantShare
);

public sealed record AttentionRow(
    string RelationshipRef,
    string Metric,
    int Total,
    DateOnly LastDay
);

public sealed class AgentOperationService(
    IAgentOperationStore store,
    IOperationRelationshipSource relationships,
    IOperationPackageLimits limits,
    ICustomerConnectionInterface connections,
    IOperationAlertSink alerts,
    TimeProvider clock
)
{
    public const string SchemaVersion = "1.0";

    private static readonly JsonElement EmptyPayload = JsonDocument.Parse("{}").RootElement.Clone();
    private static readonly IReadOnlySet<string> Cadences = new HashSet<string>(
        StringComparer.Ordinal
    )
    {
        "DAILY",
        "WEEKLY",
        "MONTHLY",
        "TWO_MONTHLY",
        "QUARTERLY",
    };

    private DateTimeOffset Now => clock.GetUtcNow();
    private DateOnly Today => DateOnly.FromDateTime(clock.GetUtcNow().UtcDateTime);

    public static Guid Derive(Guid relationshipId, string purpose, string key)
    {
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes($"{relationshipId:N}|{purpose}|{key}"));
        return new Guid(hash.AsSpan(0, 16));
    }

    public static ItemView View(OperationItem item) =>
        new(
            item.ItemId,
            item.Kind,
            item.Layer,
            item.LevelId,
            item.ParentId,
            item.Title,
            item.Body,
            item.StartDate,
            item.EndDate,
            item.State,
            item.AuthorState,
            item.VersionNo,
            item.ApprovedVersionNo,
            item.IsApproved,
            IsSuggestion(item),
            item.Origin,
            item.SourceRef,
            item.Reason,
            item.Confidence,
            item.PlatformId,
            item.ComponentId,
            item.Payload,
            item.UpdatedAt
        );

    /// <summary>A suggestion is an agent's proposal the customer has not accepted; it is shown and never applied (MD8).</summary>
    public static bool IsSuggestion(OperationItem item) =>
        item.Origin == OperationVocabulary.Origins.Agent
        && item.AuthorState == OperationVocabulary.AuthorStates.AgentSuggested
        && item.State
            is OperationVocabulary.States.Suggested
                or OperationVocabulary.States.Proposed
                or OperationVocabulary.States.Inferred;

    // ───────────────────────── reads ─────────────────────────

    private async Task<(
        OperationRelationship Relationship,
        ExperienceDeclaration Declaration
    )> LoadAsync(OperationCaller caller, CancellationToken ct)
    {
        var relationship =
            await relationships.GetAsync(caller, ct)
            ?? throw new AgentOperationException(
                404,
                AgentOperationCodes.NotFound,
                "The relationship was not found."
            );
        return (relationship, relationship.Declaration ?? EmptyDeclaration);
    }

    private static readonly ExperienceDeclaration EmptyDeclaration = new(
        "0",
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        new Dictionary<string, IReadOnlyList<string>>()
    );

    private async Task<IReadOnlyList<ConnectionFacts>> ConnectionsAsync(
        Guid tenantId,
        CancellationToken ct
    )
    {
        try
        {
            return await connections.ListAsync(tenantId, ct);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return [];
        }
    }

    public async Task<OperationFrame> GetFrameAsync(
        OperationCaller caller,
        string? mode,
        CancellationToken ct
    )
    {
        var (relationship, declaration) = await LoadAsync(caller, ct);
        var state = await store.GetStateAsync(caller.TenantId, caller.RelationshipId, Now, ct);
        var settings = await store.GetSettingsAsync(ct);
        var items = await store.ListAsync(caller.TenantId, caller.RelationshipId, ct);
        var platforms = BuildPlatforms(
            declaration,
            items,
            await ConnectionsAsync(caller.TenantId, ct),
            settings
        );
        var readiness = OperationVocabulary
            .ModeIds.Select(id => ReadinessOf(id, declaration, items, platforms))
            .ToArray();
        var modes = declaration
            .Modes.Select(item => new ModeView(
                item,
                readiness.First(value => value.ModeId == item.ModeId)
            ))
            .ToArray();
        var focus =
            mode is not null && OperationVocabulary.ModeIds.Contains(mode)
                ? readiness.First(value => value.ModeId == mode)
                : readiness.FirstOrDefault(value => value.State != "READY") ?? readiness[^1];
        return new OperationFrame(
            SchemaVersion,
            declaration.Modes.Count > 0,
            modes,
            BuildLayers(declaration, state),
            declaration.PlanLevels,
            platforms,
            declaration.Views,
            state.LastMode,
            state.LastSurface,
            state.TourSeen,
            focus.Next,
            ChatsOf(settings, relationship, state),
            state.PublishAuthority,
            relationship.Stopped,
            Now,
            declaration
                .Cadence.Select(cadence => cadence.SkillId)
                .Distinct()
                .Select(skill =>
                {
                    var goal = items.FirstOrDefault(item =>
                        item.Kind == OperationVocabulary.Kinds.Goal && GoalSkill(item) == skill
                    );
                    return new GoalSkillView(
                        skill,
                        goal?.State ?? "NOT_SET",
                        goal is null ? null : View(goal)
                    );
                })
                .ToArray(),
            declaration.ApprovalModes.Select(mode => mode.Mode).ToArray()
        );
    }

    private static ChatAllowanceView ChatsOf(
        AgentOperationSettings settings,
        OperationRelationship relationship,
        RelationshipOperationState state
    )
    {
        var allowed = settings.AllowanceFor(relationship.ProfessionalType);
        var remaining = Math.Max(0, allowed - state.ChatsUsed);
        return new ChatAllowanceView(allowed, state.ChatsUsed, remaining, remaining == 0);
    }

    private static IReadOnlyList<LayerView> BuildLayers(
        ExperienceDeclaration declaration,
        RelationshipOperationState state
    )
    {
        var layers = declaration
            .EventLayers.Select(layer => new LayerView(
                layer.LayerId,
                layer.LabelKey,
                layer.Label,
                layer.Sensitive,
                state.Layers.TryGetValue(layer.LayerId, out var on)
                    ? on
                    : layer.DefaultOn && !layer.Sensitive,
                false
            ))
            .ToList();
        layers.AddRange(
            state.CustomLayers.Select(layer => new LayerView(
                layer.LayerId,
                "LAYER_CUSTOM",
                layer.Label,
                false,
                !state.Layers.TryGetValue(layer.LayerId, out var on) || on,
                true
            ))
        );
        return layers;
    }

    private static bool LayerOn(
        ExperienceDeclaration declaration,
        RelationshipOperationState state,
        string layerId
    ) =>
        BuildLayers(declaration, state).FirstOrDefault(layer => layer.LayerId == layerId)?.On
        == true;

    private static bool LayerKnown(
        ExperienceDeclaration declaration,
        RelationshipOperationState state,
        string layerId
    ) => BuildLayers(declaration, state).Any(layer => layer.LayerId == layerId);

    private static IReadOnlyList<PlatformView> BuildPlatforms(
        ExperienceDeclaration declaration,
        IReadOnlyList<OperationItem> items,
        IReadOnlyList<ConnectionFacts> facts,
        AgentOperationSettings settings
    ) =>
        declaration
            .Platforms.Select(platform =>
            {
                var answer = items.FirstOrDefault(item =>
                    item.Kind == OperationVocabulary.Kinds.Presence
                    && item.PlatformId == platform.PlatformId
                );
                var connection =
                    platform.Connector == "NONE"
                        ? null
                        : facts.FirstOrDefault(fact => fact.Connector == platform.Connector);
                var connectable =
                    platform.Connector == "META_FACEBOOK"
                    || (platform.Connector == "META_INSTAGRAM" && settings.InstagramConnectEnabled);
                string presence;
                if (connection is not null)
                    presence =
                        connection.Status == "CONNECTED"
                            ? OperationVocabulary.Presence.ConnectedTested
                            : OperationVocabulary.Presence.NeedsRepair;
                else if (answer is null)
                    presence = OperationVocabulary.Presence.Unanswered;
                else if (
                    answer.State
                    is OperationVocabulary.Presence.NotPresent
                        or OperationVocabulary.Presence.PublicOnly
                )
                    presence = answer.State;
                else
                    presence = connectable
                        ? OperationVocabulary.Presence.Present
                        : OperationVocabulary.Presence.NotYetConnectable;
                var note = presence switch
                {
                    OperationVocabulary.Presence.NotYetConnectable =>
                        "WAOOAW cannot connect to this one yet. Public information is read instead.",
                    OperationVocabulary.Presence.NeedsRepair =>
                        "The connection needs to be renewed.",
                    OperationVocabulary.Presence.ConnectedTested => "Connected and tested.",
                    OperationVocabulary.Presence.Present when connectable =>
                        "You can connect it, and WAOOAW will test it.",
                    OperationVocabulary.Presence.Unanswered => "Is your business on this platform?",
                    _ => string.Empty,
                };
                return new PlatformView(
                    platform.PlatformId,
                    platform.LabelKey,
                    platform.Label,
                    platform.Connector,
                    presence,
                    connectable
                        && (
                            presence
                            is OperationVocabulary.Presence.Present
                                or OperationVocabulary.Presence.NeedsRepair
                                or OperationVocabulary.Presence.PublicOnly
                        ),
                    connection?.ConnectionId,
                    connection?.AccountName,
                    note
                );
            })
            .ToArray();

    private static ModeReadiness ReadinessOf(
        string modeId,
        ExperienceDeclaration declaration,
        IReadOnlyList<OperationItem> items,
        IReadOnlyList<PlatformView> platforms
    )
    {
        var visible = items
            .Where(item => item.State != OperationVocabulary.States.Hidden)
            .ToArray();
        switch (modeId)
        {
            case "INDUCT":
            {
                var labels = visible
                    .Where(item => item.Kind == OperationVocabulary.Kinds.ProfileLabel)
                    .ToArray();
                var confirmed = labels.Count(item =>
                    item.State == OperationVocabulary.States.Confirmed
                );
                var answered = platforms.Count(platform =>
                    platform.Presence != OperationVocabulary.Presence.Unanswered
                );
                var total = labels.Length + platforms.Count;
                var done = confirmed + answered;
                var line = $"{done} of {total} items confirmed";
                if (labels.Length == 0)
                    return new ModeReadiness(
                        modeId,
                        "NOT_STARTED",
                        done,
                        total,
                        total == 0 ? "Nothing to confirm yet" : line,
                        Step(
                            modeId,
                            "OP_NEXT_START_CONVERSATION",
                            "Tell me about your business.",
                            "Start",
                            "OPEN_CONVERSATION",
                            null
                        )
                    );
                if (confirmed < labels.Length)
                    return new ModeReadiness(
                        modeId,
                        "IN_PROGRESS",
                        done,
                        total,
                        line,
                        Step(
                            modeId,
                            "OP_NEXT_CONFIRM_PROFILE",
                            "Confirm what I understood about your business.",
                            "Confirm profile",
                            "CONFIRM_LABELS",
                            null
                        )
                    );
                var unanswered = platforms.FirstOrDefault(platform =>
                    platform.Presence == OperationVocabulary.Presence.Unanswered
                );
                if (unanswered is not null)
                    return new ModeReadiness(
                        modeId,
                        "IN_PROGRESS",
                        done,
                        total,
                        line,
                        Step(
                            modeId,
                            "OP_NEXT_ANSWER_PLATFORM",
                            $"Tell me whether you are on {unanswered.Label}.",
                            "Answer",
                            "ANSWER_PLATFORM",
                            unanswered.PlatformId
                        )
                    );
                return new ModeReadiness(modeId, "READY", done, total, line, null);
            }
            case "GOALS":
            {
                var skills = declaration
                    .Cadence.Select(cadence => cadence.SkillId)
                    .Distinct()
                    .ToArray();
                var goals = visible
                    .Where(item => item.Kind == OperationVocabulary.Kinds.Goal)
                    .ToArray();
                var done = skills.Count(skill =>
                    goals.Any(goal =>
                        GoalSkill(goal) == skill
                        && goal.State == OperationVocabulary.States.Confirmed
                    )
                );
                var line = $"{done} of {skills.Length} goals set";
                if (skills.Length == 0)
                    return new ModeReadiness(modeId, "NOT_STARTED", 0, 0, "No goals to set", null);
                var pending = goals.FirstOrDefault(goal =>
                    goal.State
                        is OperationVocabulary.States.PendingConfirmation
                            or OperationVocabulary.States.Proposed
                );
                if (pending is not null)
                    return new ModeReadiness(
                        modeId,
                        "IN_PROGRESS",
                        done,
                        skills.Length,
                        line,
                        Step(
                            modeId,
                            "OP_NEXT_CONFIRM_GOAL",
                            "Confirm this goal.",
                            "Confirm goal",
                            "CONFIRM_GOAL",
                            GoalSkill(pending)
                        )
                    );
                var next = skills.FirstOrDefault(skill =>
                    !goals.Any(goal =>
                        GoalSkill(goal) == skill
                        && goal.State == OperationVocabulary.States.Confirmed
                    )
                );
                if (next is not null)
                    return new ModeReadiness(
                        modeId,
                        done == 0 ? "NOT_STARTED" : "IN_PROGRESS",
                        done,
                        skills.Length,
                        line,
                        Step(
                            modeId,
                            "OP_NEXT_SET_GOAL",
                            "Set the next goal.",
                            "Set goal",
                            "SET_GOAL",
                            next
                        )
                    );
                var nodes = visible
                    .Where(item => item.Kind == OperationVocabulary.Kinds.PlanNode)
                    .ToArray();
                if (nodes.Length == 0 || !nodes.Any(node => node.IsApproved))
                    return new ModeReadiness(
                        modeId,
                        "IN_PROGRESS",
                        done,
                        skills.Length,
                        line,
                        Step(
                            modeId,
                            "OP_NEXT_PLAN_MONTH",
                            "Plan your month on the calendar.",
                            "Plan month",
                            "OPEN_PLAN",
                            null
                        )
                    );
                return new ModeReadiness(modeId, "READY", done, skills.Length, line, null);
            }
            default:
            {
                var content = visible
                    .Where(item => item.Kind == OperationVocabulary.Kinds.Content)
                    .ToArray();
                var pending = content
                    .Where(item =>
                        !item.IsApproved && item.State != OperationVocabulary.States.Rejected
                    )
                    .ToArray();
                var slots = visible
                    .Where(item => item.Kind == OperationVocabulary.Kinds.Slot)
                    .ToArray();
                var scheduled = slots.Count(item =>
                    item.State == OperationVocabulary.States.Scheduled
                );
                var published = slots.Count(item =>
                    item.State == OperationVocabulary.States.Published
                );
                var line =
                    $"{pending.Length} to approve · {scheduled} scheduled · {published} published";
                var unscheduled = content.FirstOrDefault(item =>
                    item.IsApproved
                    && !slots.Any(slot =>
                        slot.ParentId == item.ItemId
                        && slot.State
                            is OperationVocabulary.States.Scheduled
                                or OperationVocabulary.States.Published
                    )
                );
                if (pending.Length > 0)
                    return new ModeReadiness(
                        modeId,
                        "IN_PROGRESS",
                        published,
                        pending.Length + published,
                        line,
                        Step(
                            modeId,
                            "OP_NEXT_APPROVE",
                            $"Approve {pending.Length} item{(pending.Length == 1 ? string.Empty : "s")}.",
                            "Approve",
                            "OPEN_APPROVALS",
                            pending[0].ItemId.ToString("D")
                        )
                    );
                if (unscheduled is not null)
                    return new ModeReadiness(
                        modeId,
                        "IN_PROGRESS",
                        published,
                        content.Length,
                        line,
                        Step(
                            modeId,
                            "OP_NEXT_SCHEDULE",
                            "Schedule your approved post.",
                            "Schedule",
                            "OPEN_SCHEDULE",
                            unscheduled.ItemId.ToString("D")
                        )
                    );
                if (scheduled > 0)
                    return new ModeReadiness(
                        modeId,
                        "IN_PROGRESS",
                        published,
                        scheduled + published,
                        line,
                        Step(
                            modeId,
                            "OP_NEXT_PUBLISH",
                            $"Publish {scheduled} approved post{(scheduled == 1 ? string.Empty : "s")}.",
                            "Publish",
                            "OPEN_PUBLISHED",
                            null
                        )
                    );
                if (published == 0 && content.Length == 0)
                    return new ModeReadiness(modeId, "NOT_STARTED", 0, 0, line, null);
                return new ModeReadiness(
                    modeId,
                    "READY",
                    published,
                    published,
                    line,
                    Step(
                        modeId,
                        "OP_NEXT_RESULTS",
                        "See how your goals are going.",
                        "See results",
                        "OPEN_RESULTS",
                        null
                    )
                );
            }
        }
    }

    private static NextStep Step(
        string modeId,
        string key,
        string text,
        string label,
        string command,
        string? target
    ) => new(modeId, key, text, label, command, target);

    private static string? GoalSkill(OperationItem goal) =>
        goal.Payload.ValueKind == JsonValueKind.Object
        && goal.Payload.TryGetProperty("skillId", out var skill)
        && skill.ValueKind == JsonValueKind.String
            ? skill.GetString()
            : null;

    public async Task<IReadOnlyList<ItemView>> ListAsync(
        OperationCaller caller,
        string? kind,
        CancellationToken ct
    )
    {
        await LoadAsync(caller, ct);
        var items = await store.ListAsync(caller.TenantId, caller.RelationshipId, ct);
        return items.Where(item => kind is null || item.Kind == kind).Select(View).ToArray();
    }

    public async Task<IReadOnlyList<ItemView>> VersionsAsync(
        OperationCaller caller,
        Guid itemId,
        CancellationToken ct
    )
    {
        await LoadAsync(caller, ct);
        return (await store.VersionsAsync(caller.TenantId, caller.RelationshipId, itemId, ct))
            .Select(View)
            .ToArray();
    }

    public async Task<CalendarView> GetCalendarAsync(
        OperationCaller caller,
        DateOnly from,
        DateOnly to,
        bool includeHidden,
        CancellationToken ct
    )
    {
        if (to < from || to.DayNumber - from.DayNumber > 400)
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "The date range is not valid."
            );
        var (_, declaration) = await LoadAsync(caller, ct);
        var state = await store.GetStateAsync(caller.TenantId, caller.RelationshipId, Now, ct);
        var items = await store.ListAsync(caller.TenantId, caller.RelationshipId, ct);
        var layers = BuildLayers(declaration, state);
        var entries = items
            .Where(item => OperationVocabulary.Kinds.Calendar.Contains(item.Kind))
            .Where(item => includeHidden || item.State != OperationVocabulary.States.Hidden)
            .Where(item =>
                item.StartDate is null
                || (item.StartDate <= to && (item.EndDate ?? item.StartDate) >= from)
            )
            .Where(item =>
                item.Kind != OperationVocabulary.Kinds.Event
                || item.Origin == OperationVocabulary.Origins.Customer
                || item.Layer is null
                || layers.FirstOrDefault(layer => layer.LayerId == item.Layer)?.On == true
            )
            .OrderBy(item => item.StartDate ?? DateOnly.MaxValue)
            .ThenBy(item => item.Kind, StringComparer.Ordinal)
            .ThenBy(item => item.ItemId)
            .Select(View)
            .ToArray();
        return new CalendarView(
            SchemaVersion,
            from,
            to,
            entries,
            layers,
            await LimitsAsync(caller, declaration, items, ct),
            entries.Any(entry => entry.IsSuggestion)
                ? "AGENT_SUGGESTED_PRESENT"
                : "CUSTOMER_AND_APPROVED",
            items.Count == 0 ? null : items.Max(item => item.UpdatedAt)
        );
    }

    private async Task<IReadOnlyList<LimitView>> LimitsAsync(
        OperationCaller caller,
        ExperienceDeclaration declaration,
        IReadOnlyList<OperationItem> items,
        CancellationToken ct
    )
    {
        var remaining = await limits.RemainingAsync(caller, ct);
        return declaration
            .Components.Where(component => component.Kind is "COUNTED" or "SELECTED" or "CAPACITY")
            .Select(component =>
            {
                var committed = items.Count(item =>
                    item.ComponentId == component.ComponentId
                    && item.Kind is OperationVocabulary.Kinds.Slot
                    && item.State == OperationVocabulary.States.Scheduled
                );
                var known = remaining is not null && remaining.ContainsKey(component.ComponentId);
                return new LimitView(
                    component.ComponentId,
                    component.Label,
                    known ? remaining![component.ComponentId] : null,
                    committed,
                    known
                );
            })
            .ToArray();
    }

    public async Task<PlanTreeView> GetPlanTreeAsync(OperationCaller caller, CancellationToken ct)
    {
        var (_, declaration) = await LoadAsync(caller, ct);
        var items = await store.ListAsync(caller.TenantId, caller.RelationshipId, ct);
        return new PlanTreeView(
            SchemaVersion,
            declaration.PlanLevels,
            items
                .Where(item =>
                    item.Kind == OperationVocabulary.Kinds.PlanNode
                    && item.State != OperationVocabulary.States.Hidden
                )
                .OrderBy(item => LevelIndex(declaration, item.LevelId))
                .ThenBy(item => item.StartDate ?? DateOnly.MaxValue)
                .Select(View)
                .ToArray()
        );
    }

    private static int LevelIndex(ExperienceDeclaration declaration, string? levelId) =>
        levelId is null
            ? -1
            : declaration.PlanLevels.ToList().FindIndex(level => level.LevelId == levelId);

    public async Task<OperationContext> GetContextAsync(
        OperationCaller caller,
        string? mode,
        string? view,
        Guid? selectedItemId,
        CancellationToken ct
    )
    {
        var frame = await GetFrameAsync(caller, mode, ct);
        var items = await store.ListAsync(caller.TenantId, caller.RelationshipId, ct);
        var selected = selectedItemId is null
            ? null
            : items.FirstOrDefault(item => item.ItemId == selectedItemId);
        var (_, declaration) = await LoadAsync(caller, ct);
        return new OperationContext(
            SchemaVersion,
            mode ?? frame.LastMode,
            view,
            selected is null ? null : View(selected),
            frame.Next,
            frame.Chats,
            await LimitsAsync(caller, declaration, items, ct),
            items.Count(IsSuggestion),
            items.Count(item => item.AuthorState == OperationVocabulary.AuthorStates.CustomerOwned)
        );
    }

    // ───────────────────────── state commands ─────────────────────────

    public async Task SetModeAsync(
        OperationCaller caller,
        string modeId,
        string? surface,
        CancellationToken ct
    )
    {
        if (
            !OperationVocabulary.ModeIds.Contains(modeId)
            || (surface is not null && surface.Length > 64)
        )
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "That mode is not available."
            );
        await LoadAsync(caller, ct);
        var state = await store.GetStateAsync(caller.TenantId, caller.RelationshipId, Now, ct);
        await store.SaveStateAsync(
            state with
            {
                LastMode = modeId,
                LastSurface = surface,
                UpdatedAt = Now,
            },
            ct
        );
    }

    public async Task MarkTourSeenAsync(OperationCaller caller, CancellationToken ct)
    {
        await LoadAsync(caller, ct);
        var state = await store.GetStateAsync(caller.TenantId, caller.RelationshipId, Now, ct);
        await store.SaveStateAsync(state with { TourSeen = true, UpdatedAt = Now }, ct);
    }

    public async Task SetLayerAsync(
        OperationCaller caller,
        string layerId,
        bool on,
        string route,
        CancellationToken ct
    )
    {
        var (_, declaration) = await LoadAsync(caller, ct);
        var state = await store.GetStateAsync(caller.TenantId, caller.RelationshipId, Now, ct);
        if (!LayerKnown(declaration, state, layerId))
            throw new AgentOperationException(
                400,
                AgentOperationCodes.UnknownLayer,
                "That layer is not available."
            );
        var layers = new Dictionary<string, bool>(state.Layers, StringComparer.Ordinal)
        {
            [layerId] = on,
        };
        await store.SaveStateAsync(state with { Layers = layers, UpdatedAt = Now }, ct);
        await CountRouteAsync(caller, route, ct);
    }

    public async Task<LayerView> AddCustomLayerAsync(
        OperationCaller caller,
        string label,
        Guid key,
        CancellationToken ct
    )
    {
        if (!OperationVocabulary.IsPlainText(label, 40))
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "Use plain words, up to 40 characters."
            );
        await LoadAsync(caller, ct);
        var state = await store.GetStateAsync(caller.TenantId, caller.RelationshipId, Now, ct);
        var layerId =
            "CUSTOM_"
            + Derive(caller.RelationshipId, "layer", key.ToString("N"))
                .ToString("N")[..12]
                .ToUpperInvariant();
        if (state.CustomLayers.Any(layer => layer.LayerId == layerId))
            return new LayerView(layerId, "LAYER_CUSTOM", label, false, true, true);
        if (state.CustomLayers.Count >= OperationVocabulary.MaximumCustomLayers)
            throw new AgentOperationException(
                409,
                AgentOperationCodes.LimitReached,
                "You have reached the number of layers you can add."
            );
        await store.SaveStateAsync(
            state with
            {
                CustomLayers = [.. state.CustomLayers, new CustomLayer(layerId, label)],
                UpdatedAt = Now,
            },
            ct
        );
        return new LayerView(layerId, "LAYER_CUSTOM", label, false, true, true);
    }

    public async Task SetPublishAuthorityAsync(
        OperationCaller caller,
        bool granted,
        CancellationToken ct
    )
    {
        await LoadAsync(caller, ct);
        var state = await store.GetStateAsync(caller.TenantId, caller.RelationshipId, Now, ct);
        await store.SaveStateAsync(state with { PublishAuthority = granted, UpdatedAt = Now }, ct);
    }

    // ───────────────────────── item commands ─────────────────────────

    private async Task CountRouteAsync(OperationCaller caller, string route, CancellationToken ct)
    {
        if (!OperationVocabulary.Routes.All.Contains(route))
            return;
        await store.CountAsync(
            Today,
            OperationMetrics.RefOf(caller.RelationshipId),
            OperationMetrics.ForRoute(route),
            1,
            ct
        );
    }

    private static string NormalizeRoute(string? route, string fallback) =>
        route is not null && OperationVocabulary.Routes.All.Contains(route) ? route : fallback;

    private async Task<OperationItem> SaveNextAsync(
        OperationItem current,
        Func<OperationItem, OperationItem> change,
        string actor,
        CancellationToken ct
    )
    {
        var next = change(current) with
        {
            VersionNo = current.VersionNo + 1,
            UpdatedAt = Now,
            UpdatedBy = actor,
        };
        if (!await store.UpdateAsync(next, current.VersionNo, ct))
            throw new AgentOperationException(
                409,
                AgentOperationCodes.Conflict,
                "This changed while you were working. Reload and try again."
            );
        return next;
    }

    private async Task<OperationItem> RequireAsync(
        OperationCaller caller,
        Guid itemId,
        CancellationToken ct
    ) =>
        await store.GetAsync(caller.TenantId, caller.RelationshipId, itemId, ct)
        ?? throw new AgentOperationException(
            404,
            AgentOperationCodes.NotFound,
            "That item was not found."
        );

    private static void RequireText(string? value, int maximum, string what)
    {
        if (!OperationVocabulary.IsPlainText(value, maximum))
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                $"{what} must be plain words, up to {maximum} characters."
            );
    }

    public async Task<ItemView> CreateItemAsync(
        OperationCaller caller,
        Guid key,
        CreateItemRequest request,
        CancellationToken ct
    )
    {
        var (relationship, declaration) = await LoadAsync(caller, ct);
        if (relationship.Stopped)
            throw new AgentOperationException(
                409,
                AgentOperationCodes.Stopped,
                "This relationship is stopped."
            );
        if (!OperationVocabulary.Kinds.CustomerCreatable.Contains(request.Kind))
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "That kind of item cannot be added."
            );
        RequireText(request.Title, OperationVocabulary.MaximumTitleLength, "The title");
        if (request.Body is not null)
            RequireText(request.Body, OperationVocabulary.MaximumBodyLength, "The text");
        if (request.EndDate < request.StartDate)
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "The end date is before the start date."
            );
        var state = await store.GetStateAsync(caller.TenantId, caller.RelationshipId, Now, ct);
        var items = await store.ListAsync(caller.TenantId, caller.RelationshipId, ct);
        if (request.Layer is not null && !LayerKnown(declaration, state, request.Layer))
            throw new AgentOperationException(
                400,
                AgentOperationCodes.UnknownLayer,
                "That layer is not available."
            );
        if (
            request.PlatformId is not null
            && !declaration.Platforms.Any(platform => platform.PlatformId == request.PlatformId)
        )
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "That platform is not available."
            );
        if (
            request.ComponentId is not null
            && !declaration.Components.Any(component =>
                component.ComponentId == request.ComponentId
            )
        )
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "That package item is not available."
            );
        if (request.Kind == OperationVocabulary.Kinds.PlanNode)
            ValidatePlanNode(
                declaration,
                items,
                request.LevelId,
                request.ParentId,
                requireApprovedParent: false
            );
        if (request.Kind == OperationVocabulary.Kinds.Slot)
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "Use Schedule to place an approved post on the calendar."
            );
        if (request.Kind == OperationVocabulary.Kinds.Event && request.StartDate is null)
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "An event needs a date."
            );

        var itemId = Derive(caller.RelationshipId, "create", key.ToString("N"));
        var existing = await store.GetAsync(caller.TenantId, caller.RelationshipId, itemId, ct);
        if (existing is not null)
            return View(existing);
        var now = Now;
        var item = new OperationItem(
            caller.TenantId,
            caller.RelationshipId,
            itemId,
            request.Kind,
            request.Layer,
            request.LevelId,
            request.ParentId,
            request.Title.Trim(),
            request.Body?.Trim(),
            request.StartDate,
            request.EndDate,
            request.Kind == OperationVocabulary.Kinds.Event
                ? OperationVocabulary.States.CustomerAdded
                : OperationVocabulary.States.Draft,
            OperationVocabulary.AuthorStates.CustomerOwned,
            1,
            0,
            OperationVocabulary.Origins.Customer,
            null,
            null,
            null,
            request.PlatformId,
            request.ComponentId,
            EmptyPayload,
            now,
            now,
            caller.Actor
        );
        if (await store.InsertAsync(item, ct))
            await CountRouteAsync(
                caller,
                NormalizeRoute(request.Route, OperationVocabulary.Routes.Tool),
                ct
            );
        return View(item);
    }

    private static void ValidatePlanNode(
        ExperienceDeclaration declaration,
        IReadOnlyList<OperationItem> items,
        string? levelId,
        Guid? parentId,
        bool requireApprovedParent
    )
    {
        var index = LevelIndex(declaration, levelId);
        if (index < 0)
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "That plan level is not available."
            );
        if (index == 0)
        {
            if (parentId is not null)
                throw new AgentOperationException(
                    400,
                    AgentOperationCodes.Invalid,
                    "The first level has no parent."
                );
            return;
        }
        var parent = parentId is null
            ? null
            : items.FirstOrDefault(item => item.ItemId == parentId);
        if (
            parent is null
            || parent.Kind != OperationVocabulary.Kinds.PlanNode
            || LevelIndex(declaration, parent.LevelId) != index - 1
        )
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "Choose a parent from the level above."
            );
        if (requireApprovedParent && !parent.IsApproved)
            throw new AgentOperationException(
                409,
                AgentOperationCodes.ParentNotApproved,
                "Approve the level above first."
            );
    }

    public async Task<ItemView> AcceptAsync(
        OperationCaller caller,
        Guid itemId,
        string? route,
        CancellationToken ct
    )
    {
        var item = await RequireAsync(caller, itemId, ct);
        if (!IsSuggestion(item))
            return View(item);
        var target =
            item.Kind == OperationVocabulary.Kinds.ProfileLabel
                ? OperationVocabulary.States.Confirmed
                : OperationVocabulary.States.Accepted;
        var saved = await SaveNextAsync(
            item,
            value => value with { State = target },
            caller.Actor,
            ct
        );
        await CountRouteAsync(
            caller,
            NormalizeRoute(route, OperationVocabulary.Routes.Accepted),
            ct
        );
        return View(saved);
    }

    public async Task<ItemView> HideAsync(
        OperationCaller caller,
        Guid itemId,
        string? route,
        CancellationToken ct
    )
    {
        var item = await RequireAsync(caller, itemId, ct);
        if (item.State == OperationVocabulary.States.Hidden)
            return View(item);
        var saved = await SaveNextAsync(
            item,
            value => value with { State = OperationVocabulary.States.Hidden },
            caller.Actor,
            ct
        );
        await CountRouteAsync(caller, NormalizeRoute(route, OperationVocabulary.Routes.Tool), ct);
        return View(saved);
    }

    public async Task<ItemView> RestoreAsync(
        OperationCaller caller,
        Guid itemId,
        CancellationToken ct
    )
    {
        var item = await RequireAsync(caller, itemId, ct);
        if (item.State != OperationVocabulary.States.Hidden)
            return View(item);
        var previous = (
            await store.VersionsAsync(caller.TenantId, caller.RelationshipId, itemId, ct)
        ).LastOrDefault(version => version.State != OperationVocabulary.States.Hidden);
        var target = previous?.State ?? OperationVocabulary.States.Accepted;
        return View(
            await SaveNextAsync(item, value => value with { State = target }, caller.Actor, ct)
        );
    }

    public async Task<ItemView> EditAsync(
        OperationCaller caller,
        Guid itemId,
        EditItemRequest request,
        string? route,
        CancellationToken ct
    )
    {
        var item = await RequireAsync(caller, itemId, ct);
        if (request.ExpectedVersion != item.VersionNo)
            throw new AgentOperationException(
                409,
                AgentOperationCodes.Conflict,
                "This changed while you were working. Reload and try again."
            );
        if (request.Title is not null)
            RequireText(request.Title, OperationVocabulary.MaximumTitleLength, "The title");
        if (request.Body is not null)
            RequireText(request.Body, OperationVocabulary.MaximumBodyLength, "The text");
        var startDate = request.StartDate ?? item.StartDate;
        var endDate = request.EndDate ?? item.EndDate;
        if (endDate < startDate)
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "The end date is before the start date."
            );
        var saved = await SaveNextAsync(
            item,
            value =>
                value with
                {
                    Title = request.Title?.Trim() ?? value.Title,
                    Body = request.Body?.Trim() ?? value.Body,
                    StartDate = startDate,
                    EndDate = endDate,
                    AuthorState =
                        value.AuthorState == OperationVocabulary.AuthorStates.CustomerOwned
                            ? OperationVocabulary.AuthorStates.CustomerOwned
                            : OperationVocabulary.AuthorStates.CustomerEdited,
                    // A change after approval is a new version that needs its own approval (R017).
                    State =
                        value.IsApproved || IsSuggestion(value)
                            ? OperationVocabulary.States.Proposed
                            : value.State,
                },
            caller.Actor,
            ct
        );
        await CountRouteAsync(caller, NormalizeRoute(route, OperationVocabulary.Routes.Tool), ct);
        return View(saved);
    }

    public async Task<ItemView> HandOverAsync(
        OperationCaller caller,
        Guid itemId,
        string? route,
        CancellationToken ct
    )
    {
        var item = await RequireAsync(caller, itemId, ct);
        if (item.AuthorState == OperationVocabulary.AuthorStates.CustomerOwned)
            return View(item);
        var saved = await SaveNextAsync(
            item,
            value =>
                value with
                {
                    AuthorState = OperationVocabulary.AuthorStates.CustomerOwned,
                    State = IsSuggestion(value) ? OperationVocabulary.States.Proposed : value.State,
                },
            caller.Actor,
            ct
        );
        await CountRouteAsync(caller, NormalizeRoute(route, OperationVocabulary.Routes.Asked), ct);
        return View(saved);
    }

    public async Task<ItemView> TakeBackAsync(
        OperationCaller caller,
        Guid itemId,
        string? route,
        CancellationToken ct
    )
    {
        var item = await RequireAsync(caller, itemId, ct);
        if (item.AuthorState != OperationVocabulary.AuthorStates.CustomerOwned)
            return View(item);
        var saved = await SaveNextAsync(
            item,
            value => value with { AuthorState = OperationVocabulary.AuthorStates.CustomerEdited },
            caller.Actor,
            ct
        );
        await CountRouteAsync(caller, NormalizeRoute(route, OperationVocabulary.Routes.Asked), ct);
        return View(saved);
    }

    /// <summary>Undo writes the previous version as a new version. Nothing is deleted.</summary>
    public async Task<ItemView> UndoAsync(OperationCaller caller, Guid itemId, CancellationToken ct)
    {
        var item = await RequireAsync(caller, itemId, ct);
        var versions = await store.VersionsAsync(
            caller.TenantId,
            caller.RelationshipId,
            itemId,
            ct
        );
        if (versions.Count < 2)
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "There is nothing to undo."
            );
        var previous = versions[^2];
        // Undo never reapplies an approval that the later change withdrew.
        var saved = await SaveNextAsync(
            item,
            _ => previous with { ApprovedVersionNo = item.ApprovedVersionNo },
            caller.Actor,
            ct
        );
        return View(saved);
    }

    public async Task<ItemView> ApproveAsync(
        OperationCaller caller,
        Guid itemId,
        int exactVersion,
        string? route,
        CancellationToken ct
    )
    {
        var item = await RequireAsync(caller, itemId, ct);
        if (
            item.Kind
            is not (OperationVocabulary.Kinds.PlanNode or OperationVocabulary.Kinds.Content)
        )
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "That item is not approved this way."
            );
        if (exactVersion != item.VersionNo)
            throw new AgentOperationException(
                409,
                AgentOperationCodes.Conflict,
                "That is not the version you are looking at. Reload and approve again."
            );
        if (item.IsApproved)
            return View(item);
        if (
            item.Kind == OperationVocabulary.Kinds.Content
            && item.Origin == OperationVocabulary.Origins.Agent
            && !ReviewChecksPassed(item.Payload)
        )
            throw new AgentOperationException(
                409,
                AgentOperationCodes.NotApproved,
                "The checks on this draft have not all passed."
            );
        var saved = await SaveNextAsync(
            item,
            value =>
                value with
                {
                    State = OperationVocabulary.States.Approved,
                    AuthorState = OperationVocabulary.AuthorStates.ApprovedVersion,
                    ApprovedVersionNo = value.VersionNo + 1,
                },
            caller.Actor,
            ct
        );
        await CountRouteAsync(caller, NormalizeRoute(route, OperationVocabulary.Routes.Tool), ct);
        return View(saved);
    }

    public async Task<ItemView> RejectAsync(
        OperationCaller caller,
        Guid itemId,
        string? route,
        CancellationToken ct
    )
    {
        var item = await RequireAsync(caller, itemId, ct);
        if (item.State == OperationVocabulary.States.Rejected)
            return View(item);
        var saved = await SaveNextAsync(
            item,
            value =>
                value with
                {
                    State = OperationVocabulary.States.Rejected,
                    AuthorState =
                        value.AuthorState == OperationVocabulary.AuthorStates.ApprovedVersion
                            ? OperationVocabulary.AuthorStates.CustomerEdited
                            : value.AuthorState,
                },
            caller.Actor,
            ct
        );
        await CountRouteAsync(caller, NormalizeRoute(route, OperationVocabulary.Routes.Tool), ct);
        return View(saved);
    }

    public async Task<ItemView> MoveAsync(
        OperationCaller caller,
        Guid itemId,
        DateOnly start,
        DateOnly? end,
        string? route,
        CancellationToken ct
    )
    {
        var item = await RequireAsync(caller, itemId, ct);
        if (!OperationVocabulary.Kinds.Calendar.Contains(item.Kind) || end < start)
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "That item cannot be moved there."
            );
        if (
            item.Kind == OperationVocabulary.Kinds.Slot
            && item.State != OperationVocabulary.States.Scheduled
        )
            throw new AgentOperationException(
                409,
                AgentOperationCodes.Conflict,
                "A published post cannot be moved."
            );
        if (item.StartDate == start && item.EndDate == end)
            return View(item);
        // A move follows the approval rule of the item: an approved version that moves needs approval again.
        var saved = await SaveNextAsync(
            item,
            value =>
                value with
                {
                    StartDate = start,
                    EndDate = end,
                    AuthorState =
                        value.AuthorState == OperationVocabulary.AuthorStates.CustomerOwned
                            ? value.AuthorState
                            : OperationVocabulary.AuthorStates.CustomerEdited,
                    State =
                        value.IsApproved && value.Kind != OperationVocabulary.Kinds.Slot
                            ? OperationVocabulary.States.Proposed
                            : value.State,
                },
            caller.Actor,
            ct
        );
        await CountRouteAsync(caller, NormalizeRoute(route, OperationVocabulary.Routes.Tool), ct);
        return View(saved);
    }

    private static bool ReviewChecksPassed(JsonElement payload) =>
        payload.ValueKind == JsonValueKind.Object
        && payload.TryGetProperty("reviewChecks", out var checks)
        && checks.ValueKind == JsonValueKind.Array
        && checks.GetArrayLength() > 0
        && checks
            .EnumerateArray()
            .All(check =>
                check.ValueKind == JsonValueKind.Object
                && check.TryGetProperty("passed", out var passed)
                && passed.ValueKind == JsonValueKind.True
            );

    // ───────────────────────── profile, platforms, goals ─────────────────────────

    public async Task<ItemView> ConfirmLabelAsync(
        OperationCaller caller,
        Guid itemId,
        string? correctedTitle,
        string? route,
        CancellationToken ct
    )
    {
        var item = await RequireAsync(caller, itemId, ct);
        if (item.Kind != OperationVocabulary.Kinds.ProfileLabel)
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "That is not a profile label."
            );
        if (correctedTitle is not null)
            RequireText(correctedTitle, OperationVocabulary.MaximumTitleLength, "The label");
        var corrected = correctedTitle is not null && correctedTitle.Trim() != item.Title;
        if (item.State == OperationVocabulary.States.Confirmed && !corrected)
            return View(item);
        var wasSuggestion = IsSuggestion(item);
        var saved = await SaveNextAsync(
            item,
            value =>
                value with
                {
                    Title = corrected ? correctedTitle!.Trim() : value.Title,
                    State = OperationVocabulary.States.Confirmed,
                    AuthorState =
                        corrected || !wasSuggestion
                            ? OperationVocabulary.AuthorStates.CustomerEdited
                            : value.AuthorState,
                },
            caller.Actor,
            ct
        );
        await CountRouteAsync(
            caller,
            NormalizeRoute(
                route,
                wasSuggestion && !corrected
                    ? OperationVocabulary.Routes.Accepted
                    : OperationVocabulary.Routes.Tool
            ),
            ct
        );
        return View(saved);
    }

    public async Task<PlatformView> AnswerPlatformAsync(
        OperationCaller caller,
        string platformId,
        string answer,
        string? route,
        CancellationToken ct
    )
    {
        var (_, declaration) = await LoadAsync(caller, ct);
        var platform =
            declaration.Platforms.FirstOrDefault(value => value.PlatformId == platformId)
            ?? throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "That platform is not available."
            );
        if (!OperationVocabulary.Presence.CustomerAnswers.Contains(answer))
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "Answer present, not present or public only."
            );
        var itemId = Derive(caller.RelationshipId, "presence", platformId);
        var existing = await store.GetAsync(caller.TenantId, caller.RelationshipId, itemId, ct);
        if (existing is null)
        {
            var now = Now;
            await store.InsertAsync(
                new OperationItem(
                    caller.TenantId,
                    caller.RelationshipId,
                    itemId,
                    OperationVocabulary.Kinds.Presence,
                    null,
                    null,
                    null,
                    platform.Label,
                    null,
                    null,
                    null,
                    answer,
                    OperationVocabulary.AuthorStates.CustomerOwned,
                    1,
                    0,
                    OperationVocabulary.Origins.Customer,
                    null,
                    null,
                    null,
                    platformId,
                    null,
                    EmptyPayload,
                    now,
                    now,
                    caller.Actor
                ),
                ct
            );
            await CountRouteAsync(
                caller,
                NormalizeRoute(route, OperationVocabulary.Routes.Asked),
                ct
            );
        }
        else if (existing.State != answer)
        {
            await SaveNextAsync(existing, value => value with { State = answer }, caller.Actor, ct);
            await CountRouteAsync(
                caller,
                NormalizeRoute(route, OperationVocabulary.Routes.Asked),
                ct
            );
        }
        var items = await store.ListAsync(caller.TenantId, caller.RelationshipId, ct);
        var settings = await store.GetSettingsAsync(ct);
        return BuildPlatforms(
                declaration,
                items,
                await ConnectionsAsync(caller.TenantId, ct),
                settings
            )
            .First(value => value.PlatformId == platformId);
    }

    /// <summary>Reads the connection again through the one interface; a connection that needs repair raises an alert once.</summary>
    public async Task<PlatformView> TestPlatformAsync(
        OperationCaller caller,
        string platformId,
        CancellationToken ct
    )
    {
        var (_, declaration) = await LoadAsync(caller, ct);
        if (!declaration.Platforms.Any(value => value.PlatformId == platformId))
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "That platform is not available."
            );
        var items = await store.ListAsync(caller.TenantId, caller.RelationshipId, ct);
        var settings = await store.GetSettingsAsync(ct);
        var view = BuildPlatforms(
                declaration,
                items,
                await ConnectionsAsync(caller.TenantId, ct),
                settings
            )
            .First(value => value.PlatformId == platformId);
        if (view.Presence == OperationVocabulary.Presence.NeedsRepair)
            await RaiseRepairAsync(caller.TenantId, caller.RelationshipId, platformId, ct);
        return view;
    }

    private async Task RaiseRepairAsync(
        Guid tenantId,
        Guid relationshipId,
        string platformId,
        CancellationToken ct
    )
    {
        await store.CountAsync(
            Today,
            OperationMetrics.RefOf(relationshipId),
            OperationMetrics.ConnectionRepair,
            1,
            ct
        );
        await alerts.RaiseAsync(
            tenantId,
            relationshipId,
            "CONNECTION_NEEDS_REPAIR",
            "HIGH",
            $"repair-{platformId}-{Today:yyyyMMdd}",
            "A connected account needs to be renewed before anything more can be published.",
            ct
        );
    }

    public async Task<ItemView> SetGoalAsync(
        OperationCaller caller,
        string skillId,
        GoalRequest request,
        string? route,
        CancellationToken ct
    )
    {
        var (_, declaration) = await LoadAsync(caller, ct);
        ValidateGoal(declaration, skillId, request);
        var itemId = Derive(caller.RelationshipId, "goal", skillId);
        var payload = GoalPayload(skillId, request);
        var existing = await store.GetAsync(caller.TenantId, caller.RelationshipId, itemId, ct);
        var now = Now;
        if (existing is null)
        {
            var item = new OperationItem(
                caller.TenantId,
                caller.RelationshipId,
                itemId,
                OperationVocabulary.Kinds.Goal,
                null,
                null,
                null,
                $"Goal: {skillId}",
                null,
                null,
                null,
                OperationVocabulary.States.Confirmed,
                OperationVocabulary.AuthorStates.CustomerEdited,
                1,
                0,
                OperationVocabulary.Origins.Customer,
                request.EvidenceSource,
                null,
                null,
                null,
                null,
                payload,
                now,
                now,
                caller.Actor
            );
            await store.InsertAsync(item, ct);
            await CountRouteAsync(
                caller,
                NormalizeRoute(route, OperationVocabulary.Routes.Tool),
                ct
            );
            return View(item);
        }
        var saved = await SaveNextAsync(
            existing,
            value =>
                value with
                {
                    Payload = payload,
                    State = OperationVocabulary.States.Confirmed,
                    AuthorState = OperationVocabulary.AuthorStates.CustomerEdited,
                    SourceRef = request.EvidenceSource,
                },
            caller.Actor,
            ct
        );
        await CountRouteAsync(caller, NormalizeRoute(route, OperationVocabulary.Routes.Tool), ct);
        return View(saved);
    }

    private static void ValidateGoal(
        ExperienceDeclaration declaration,
        string skillId,
        GoalRequest request
    )
    {
        if (!declaration.Cadence.Any(cadence => cadence.SkillId == skillId))
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "That skill is not available."
            );
        RequireText(request.Baseline, 160, "The baseline");
        RequireText(request.Target, 160, "The target");
        RequireText(request.EvidenceSource, 160, "The evidence source");
        if (!Cadences.Contains(request.Cadence))
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "Choose how often this goal is reviewed."
            );
        if (!declaration.ApprovalModes.Any(mode => mode.Mode == request.AuthorityState))
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "That approval level is not available."
            );
    }

    private static JsonElement GoalPayload(string skillId, GoalRequest request) =>
        JsonSerializer.SerializeToElement(
            new
            {
                skillId,
                baseline = request.Baseline.Trim(),
                target = request.Target.Trim(),
                evidenceSource = request.EvidenceSource.Trim(),
                cadence = request.Cadence,
                authorityState = request.AuthorityState,
            }
        );

    /// <summary>Confirms an agent's goal proposal (new, or a revision held as pending); nothing applies before this.</summary>
    public async Task<ItemView> ConfirmGoalAsync(
        OperationCaller caller,
        string skillId,
        bool accept,
        string? route,
        CancellationToken ct
    )
    {
        var item =
            await store.GetAsync(
                caller.TenantId,
                caller.RelationshipId,
                Derive(caller.RelationshipId, "goal", skillId),
                ct
            )
            ?? throw new AgentOperationException(
                404,
                AgentOperationCodes.NotFound,
                "That goal was not found."
            );
        if (
            item.State
            is not (
                OperationVocabulary.States.PendingConfirmation
                or OperationVocabulary.States.Proposed
            )
        )
            return View(item);
        var pending =
            item.Payload.ValueKind == JsonValueKind.Object
            && item.Payload.TryGetProperty("pending", out var value)
                ? value
                : (JsonElement?)null;
        var saved = await SaveNextAsync(
            item,
            current =>
                current with
                {
                    Payload =
                        accept && pending is { } applied
                            ? applied
                            : WithoutPending(current.Payload),
                    State =
                        accept || current.State == OperationVocabulary.States.PendingConfirmation
                            ? OperationVocabulary.States.Confirmed
                            : OperationVocabulary.States.Rejected,
                    AuthorState = accept
                        ? OperationVocabulary.AuthorStates.CustomerEdited
                        : current.AuthorState,
                },
            caller.Actor,
            ct
        );
        await CountRouteAsync(
            caller,
            NormalizeRoute(route, OperationVocabulary.Routes.Accepted),
            ct
        );
        return View(saved);
    }

    private static JsonElement WithoutPending(JsonElement payload)
    {
        if (payload.ValueKind != JsonValueKind.Object)
            return payload;
        var copy = payload
            .EnumerateObject()
            .Where(property => property.Name != "pending")
            .ToDictionary(property => property.Name, property => property.Value);
        return JsonSerializer.SerializeToElement(copy);
    }

    /// <summary>Accepting a digest turns its goal changes into the next goal versions (WC174-R021).</summary>
    public async Task<ItemView> DecideDigestAsync(
        OperationCaller caller,
        Guid digestId,
        bool accept,
        CancellationToken ct
    )
    {
        var digest = await RequireAsync(caller, digestId, ct);
        if (digest.Kind != OperationVocabulary.Kinds.Digest)
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "That is not a digest."
            );
        if (
            digest.State
            is OperationVocabulary.States.Accepted
                or OperationVocabulary.States.Rejected
        )
            return View(digest);
        if (
            accept
            && digest.Payload.ValueKind == JsonValueKind.Object
            && digest.Payload.TryGetProperty("goalChanges", out var changes)
            && changes.ValueKind == JsonValueKind.Array
        )
        {
            var (_, declaration) = await LoadAsync(caller, ct);
            foreach (var change in changes.EnumerateArray())
            {
                var skill = change.TryGetProperty("skillId", out var s) ? s.GetString() : null;
                var target = change.TryGetProperty("target", out var t) ? t.GetString() : null;
                if (
                    skill is null
                    || target is null
                    || !declaration.Cadence.Any(cadence => cadence.SkillId == skill)
                )
                    continue;
                var goal = await store.GetAsync(
                    caller.TenantId,
                    caller.RelationshipId,
                    Derive(caller.RelationshipId, "goal", skill),
                    ct
                );
                if (goal is null || goal.Payload.ValueKind != JsonValueKind.Object)
                    continue;
                var request = new GoalRequest(
                    goal.Payload.GetProperty("baseline").GetString() ?? string.Empty,
                    target,
                    goal.Payload.GetProperty("evidenceSource").GetString() ?? string.Empty,
                    goal.Payload.GetProperty("cadence").GetString() ?? string.Empty,
                    goal.Payload.GetProperty("authorityState").GetString() ?? string.Empty
                );
                ValidateGoal(declaration, skill, request);
                await SaveNextAsync(
                    goal,
                    value =>
                        value with
                        {
                            Payload = GoalPayload(skill, request),
                            State = OperationVocabulary.States.Confirmed,
                        },
                    caller.Actor,
                    ct
                );
            }
        }
        var saved = await SaveNextAsync(
            digest,
            value =>
                value with
                {
                    State = accept
                        ? OperationVocabulary.States.Accepted
                        : OperationVocabulary.States.Rejected,
                },
            caller.Actor,
            ct
        );
        await CountRouteAsync(caller, OperationVocabulary.Routes.Accepted, ct);
        return View(saved);
    }

    // ───────────────────────── scheduling and publishing ─────────────────────────

    private static ExperienceModeGate? GateFor(ExperienceDeclaration declaration, string action) =>
        declaration
            .Modes.SelectMany(mode => mode.Gates)
            .FirstOrDefault(gate => gate.Action == action);

    private void RequireGate(
        ExperienceDeclaration declaration,
        string action,
        IReadOnlyList<OperationItem> items,
        IReadOnlyList<PlatformView> platforms
    )
    {
        var gate = GateFor(declaration, action);
        if (gate is null)
            return;
        var readiness = ReadinessOf(gate.RequiresMode, declaration, items, platforms);
        if (readiness.State != "READY")
            throw new AgentOperationException(
                409,
                AgentOperationCodes.GateBlocked,
                $"Finish this first: {readiness.Next?.Text ?? readiness.Line}",
                gate.RequiresMode
            );
    }

    public async Task<ItemView> ScheduleAsync(
        OperationCaller caller,
        Guid key,
        Guid contentId,
        string platformId,
        DateOnly date,
        string? route,
        CancellationToken ct
    )
    {
        var (relationship, declaration) = await LoadAsync(caller, ct);
        if (relationship.Stopped)
            throw new AgentOperationException(
                409,
                AgentOperationCodes.Stopped,
                "This relationship is stopped, so nothing can be scheduled."
            );
        var content = await RequireAsync(caller, contentId, ct);
        if (content.Kind != OperationVocabulary.Kinds.Content || !content.IsApproved)
            throw new AgentOperationException(
                409,
                AgentOperationCodes.NotApproved,
                "Approve this exact version before scheduling it."
            );
        if (date < Today)
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "Choose today or a later day."
            );
        var items = await store.ListAsync(caller.TenantId, caller.RelationshipId, ct);
        var settings = await store.GetSettingsAsync(ct);
        var platforms = BuildPlatforms(
            declaration,
            items,
            await ConnectionsAsync(caller.TenantId, ct),
            settings
        );
        RequireGate(declaration, OperationVocabulary.Gates.Schedule, items, platforms);
        var platform =
            platforms.FirstOrDefault(value => value.PlatformId == platformId)
            ?? throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "That platform is not available."
            );
        if (platform.Presence != OperationVocabulary.Presence.ConnectedTested)
            throw new AgentOperationException(
                409,
                AgentOperationCodes.NotConnected,
                $"Connect {platform.Label} first. It is tested before anything is scheduled.",
                "INDUCT"
            );
        var slotId = Derive(caller.RelationshipId, "slot", key.ToString("N"));
        var existing = await store.GetAsync(caller.TenantId, caller.RelationshipId, slotId, ct);
        if (existing is not null)
            return View(existing);
        if (content.ComponentId is not null)
        {
            var remaining = await limits.RemainingAsync(caller, ct);
            var committed = items.Count(item =>
                item.Kind == OperationVocabulary.Kinds.Slot
                && item.ComponentId == content.ComponentId
                && item.State == OperationVocabulary.States.Scheduled
            );
            if (
                remaining is null
                || !remaining.TryGetValue(content.ComponentId, out var left)
                || left - committed < 1
            )
                throw new AgentOperationException(
                    409,
                    AgentOperationCodes.LimitReached,
                    "Your package has no posts left to schedule."
                );
        }
        var now = Now;
        var slot = new OperationItem(
            caller.TenantId,
            caller.RelationshipId,
            slotId,
            OperationVocabulary.Kinds.Slot,
            content.Layer,
            null,
            content.ItemId,
            content.Title,
            null,
            date,
            null,
            OperationVocabulary.States.Scheduled,
            OperationVocabulary.AuthorStates.CustomerOwned,
            1,
            0,
            OperationVocabulary.Origins.Customer,
            null,
            null,
            null,
            platformId,
            content.ComponentId,
            JsonSerializer.SerializeToElement(new { contentVersion = content.ApprovedVersionNo }),
            now,
            now,
            caller.Actor
        );
        if (await store.InsertAsync(slot, ct))
            await CountRouteAsync(
                caller,
                NormalizeRoute(route, OperationVocabulary.Routes.Tool),
                ct
            );
        return View(slot);
    }

    public async Task<ItemView> PublishAsync(
        OperationCaller caller,
        Guid slotId,
        CancellationToken ct
    )
    {
        var (relationship, declaration) = await LoadAsync(caller, ct);
        var slot = await RequireAsync(caller, slotId, ct);
        if (slot.Kind != OperationVocabulary.Kinds.Slot)
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "That is not a scheduled post."
            );
        if (slot.State == OperationVocabulary.States.Published)
            return View(slot);
        if (relationship.Stopped)
            throw new AgentOperationException(
                409,
                AgentOperationCodes.Stopped,
                "This relationship is stopped, so nothing is published."
            );
        var content = await RequireAsync(caller, slot.ParentId ?? Guid.Empty, ct);
        var scheduledVersion =
            slot.Payload.TryGetProperty("contentVersion", out var version)
            && version.TryGetInt32(out var number)
                ? number
                : -1;
        // Published means the exact version the customer approved and scheduled, nothing newer, nothing else.
        if (!content.IsApproved || content.ApprovedVersionNo != scheduledVersion)
            throw new AgentOperationException(
                409,
                AgentOperationCodes.NotApproved,
                "This post changed after you approved it. Approve the new version."
            );
        var state = await store.GetStateAsync(caller.TenantId, caller.RelationshipId, Now, ct);
        if (!state.PublishAuthority)
            throw new AgentOperationException(
                409,
                AgentOperationCodes.PublishAuthorityMissing,
                "Give WAOOAW permission to publish for you first."
            );
        var items = await store.ListAsync(caller.TenantId, caller.RelationshipId, ct);
        var settings = await store.GetSettingsAsync(ct);
        var facts = await ConnectionsAsync(caller.TenantId, ct);
        var platforms = BuildPlatforms(declaration, items, facts, settings);
        RequireGate(declaration, OperationVocabulary.Gates.Publish, items, platforms);
        var platform = platforms.First(value => value.PlatformId == slot.PlatformId);
        if (
            platform.Presence != OperationVocabulary.Presence.ConnectedTested
            || platform.ConnectionId is null
        )
            throw new AgentOperationException(
                409,
                AgentOperationCodes.NotConnected,
                $"Connect {platform.Label} first.",
                "INDUCT"
            );
        var connection = facts.First(fact => fact.ConnectionId == platform.ConnectionId);
        if (
            settings.PublishSandboxOnly
            && !settings.SandboxAccountIds.Contains(connection.AccountId, StringComparer.Ordinal)
        )
            throw new AgentOperationException(
                409,
                AgentOperationCodes.SandboxOnly,
                "Publishing is limited to test accounts in this environment."
            );
        try
        {
            var post = await connections.PublishAsync(
                caller.TenantId,
                caller.ParticipantId,
                platform.ConnectionId.Value,
                content.Body ?? content.Title,
                $"Approved version {content.ApprovedVersionNo}",
                ct
            );
            var saved = await SaveNextAsync(
                slot,
                value =>
                    value with
                    {
                        State = OperationVocabulary.States.Published,
                        Payload = JsonSerializer.SerializeToElement(
                            new
                            {
                                contentVersion = scheduledVersion,
                                providerPostId = post.ProviderPostId,
                                publishedAt = post.PublishedAt,
                            }
                        ),
                    },
                caller.Actor,
                ct
            );
            await store.CountAsync(
                Today,
                OperationMetrics.RefOf(caller.RelationshipId),
                OperationMetrics.Published,
                1,
                ct
            );
            return View(saved);
        }
        catch (ConnectionNeedsRepairException)
        {
            await SaveNextAsync(
                slot,
                value => value with { State = OperationVocabulary.States.PublishFailed },
                caller.Actor,
                ct
            );
            await store.CountAsync(
                Today,
                OperationMetrics.RefOf(caller.RelationshipId),
                OperationMetrics.PublishFailed,
                1,
                ct
            );
            await RaiseRepairAsync(caller.TenantId, caller.RelationshipId, platform.PlatformId, ct);
            throw new AgentOperationException(
                409,
                AgentOperationCodes.NotConnected,
                $"{platform.Label} needs to be reconnected. Nothing was published.",
                "INDUCT"
            );
        }
        catch (Exception exception)
            when (exception is not (AgentOperationException or OperationCanceledException))
        {
            await SaveNextAsync(
                slot,
                value => value with { State = OperationVocabulary.States.PublishFailed },
                caller.Actor,
                ct
            );
            await store.CountAsync(
                Today,
                OperationMetrics.RefOf(caller.RelationshipId),
                OperationMetrics.PublishFailed,
                1,
                ct
            );
            await alerts.RaiseAsync(
                caller.TenantId,
                caller.RelationshipId,
                "PUBLISH_FAILED",
                "HIGH",
                $"publish-{slotId:N}",
                "A scheduled post could not be published.",
                ct
            );
            throw new AgentOperationException(
                502,
                AgentOperationCodes.Conflict,
                "The post could not be published. Nothing was posted; you can try again."
            );
        }
    }

    // ───────────────────────── agent proposals ─────────────────────────

    /// <summary>
    /// Stores what an agent proposed as suggestions. Nothing is applied: a suggestion waits for the customer. A proposal
    /// is refused, with its reason, when it would reach a layer the customer has off, touch an item the customer owns,
    /// skip an unapproved level, carry failed review checks or read a source the Founder has not allowed.
    /// </summary>
    public async Task<ProposalOutcome> ProposeAsync(
        OperationCaller caller,
        IReadOnlyList<OperationProposal> proposals,
        CancellationToken ct
    )
    {
        if (proposals.Count is 0 or > OperationVocabulary.MaximumProposalsPerCall)
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "A call carries between 1 and 100 proposals."
            );
        var (relationship, declaration) = await LoadAsync(caller, ct);
        if (relationship.Stopped)
            throw new AgentOperationException(
                409,
                AgentOperationCodes.Stopped,
                "This relationship is stopped."
            );
        var state = await store.GetStateAsync(caller.TenantId, caller.RelationshipId, Now, ct);
        var settings = await store.GetSettingsAsync(ct);
        var items = (await store.ListAsync(caller.TenantId, caller.RelationshipId, ct)).ToList();
        var refused = new List<ProposalRefusal>();
        var stored = 0;
        foreach (var proposal in proposals)
        {
            var code = Validate(
                proposal,
                caller.RelationshipId,
                declaration,
                state,
                settings,
                items
            );
            if (code is not null)
            {
                refused.Add(new ProposalRefusal(proposal.ProposalKey, code));
                continue;
            }
            var itemId =
                proposal.Kind == OperationVocabulary.Kinds.Goal
                    ? Derive(caller.RelationshipId, "goal", GoalSkillOf(proposal)!)
                    : Derive(
                        caller.RelationshipId,
                        "proposal",
                        $"{proposal.Kind}:{proposal.ProposalKey}"
                    );
            var existing = items.FirstOrDefault(item => item.ItemId == itemId);
            if (existing is not null)
            {
                if (proposal.Kind == OperationVocabulary.Kinds.Goal)
                {
                    stored += await ProposeGoalRevisionAsync(existing, proposal, ct);
                    continue;
                }
                if (!IsSuggestion(existing))
                {
                    refused.Add(
                        new ProposalRefusal(proposal.ProposalKey, AgentOperationCodes.CustomerOwned)
                    );
                    continue;
                }
            }
            var parentId =
                proposal.ParentProposalKey is null ? (Guid?)null
                : Guid.TryParse(proposal.ParentProposalKey, out var existingParent) ? existingParent
                : Derive(
                    caller.RelationshipId,
                    "proposal",
                    $"{OperationVocabulary.Kinds.PlanNode}:{proposal.ParentProposalKey}"
                );
            var now = Now;
            var payload = proposal.Payload ?? EmptyPayload;
            var item = new OperationItem(
                caller.TenantId,
                caller.RelationshipId,
                itemId,
                proposal.Kind,
                proposal.Layer,
                proposal.LevelId,
                parentId,
                proposal.Title.Trim(),
                proposal.Body?.Trim(),
                proposal.StartDate,
                proposal.EndDate,
                proposal.Kind switch
                {
                    OperationVocabulary.Kinds.Event => OperationVocabulary.States.Suggested,
                    OperationVocabulary.Kinds.ProfileLabel => OperationVocabulary.States.Inferred,
                    _ => OperationVocabulary.States.Proposed,
                },
                OperationVocabulary.AuthorStates.AgentSuggested,
                1,
                0,
                OperationVocabulary.Origins.Agent,
                proposal.SourceRef,
                proposal.Reason,
                proposal.Confidence,
                proposal.PlatformId,
                proposal.ComponentId,
                payload,
                now,
                now,
                "AGENT"
            );
            if (existing is null)
            {
                if (!await store.InsertAsync(item, ct))
                    continue;
                items.Add(item);
            }
            else
            {
                var revised = item with
                {
                    VersionNo = existing.VersionNo + 1,
                    CreatedAt = existing.CreatedAt,
                };
                if (!await store.UpdateAsync(revised, existing.VersionNo, ct))
                    continue;
                items.Remove(existing);
                items.Add(revised);
            }
            stored++;
            if (proposal.Kind == OperationVocabulary.Kinds.Digest)
                await RaiseBehindPaceAsync(caller, payload, ct);
        }
        return new ProposalOutcome(stored, refused);
    }

    private async Task<int> ProposeGoalRevisionAsync(
        OperationItem existing,
        OperationProposal proposal,
        CancellationToken ct
    )
    {
        // A confirmed goal is the customer's; a revision is held as pending until the customer confirms it.
        if (
            existing.State
            is OperationVocabulary.States.PendingConfirmation
                or OperationVocabulary.States.Proposed
        )
            return 0;
        var fields = existing
            .Payload.EnumerateObject()
            .Where(property => property.Name != "pending")
            .ToDictionary(property => property.Name, property => property.Value);
        fields["pending"] = proposal.Payload!.Value;
        await SaveNextAsync(
            existing,
            value =>
                value with
                {
                    Payload = JsonSerializer.SerializeToElement(fields),
                    State = OperationVocabulary.States.PendingConfirmation,
                },
            "AGENT",
            ct
        );
        return 1;
    }

    private static string? GoalSkillOf(OperationProposal proposal) =>
        proposal.Payload is { ValueKind: JsonValueKind.Object } payload
        && payload.TryGetProperty("skillId", out var skill)
        && skill.ValueKind == JsonValueKind.String
            ? skill.GetString()
            : null;

    private static string? Validate(
        OperationProposal proposal,
        Guid relationshipId,
        ExperienceDeclaration declaration,
        RelationshipOperationState state,
        AgentOperationSettings settings,
        IReadOnlyList<OperationItem> items
    )
    {
        Guid? ParentIdOf(string? key) =>
            key is null ? null
            : Guid.TryParse(key, out var existing) ? existing
            : Derive(relationshipId, "proposal", $"{OperationVocabulary.Kinds.PlanNode}:{key}");

        if (
            !OperationVocabulary.Kinds.AgentProposable.Contains(proposal.Kind)
            || !OperationVocabulary.IsPlainText(proposal.ProposalKey, 120)
            || !OperationVocabulary.IsPlainText(
                proposal.Title,
                OperationVocabulary.MaximumTitleLength
            )
            || (
                proposal.Body is not null
                && !OperationVocabulary.IsPlainText(
                    proposal.Body,
                    OperationVocabulary.MaximumBodyLength
                )
            )
            || (
                proposal.Reason is not null
                && !OperationVocabulary.IsPlainText(proposal.Reason, 400)
            )
            || (
                proposal.SourceRef is not null
                && !OperationVocabulary.IsPlainText(proposal.SourceRef, 400)
            )
            || proposal.Confidence is < 0 or > 1
            || proposal.EndDate < proposal.StartDate
        )
            return AgentOperationCodes.Invalid;
        if (proposal.Layer is not null)
        {
            if (!LayerKnown(declaration, state, proposal.Layer))
                return AgentOperationCodes.UnknownLayer;
            // Nothing is suggested on a layer the customer has off, and a sensitive layer starts off (MD4, C-061).
            if (!LayerOn(declaration, state, proposal.Layer))
                return AgentOperationCodes.LayerOff;
        }
        if (
            proposal.PlatformId is not null
            && !declaration.Platforms.Any(platform => platform.PlatformId == proposal.PlatformId)
        )
            return AgentOperationCodes.Invalid;
        if (
            proposal.ComponentId is not null
            && !declaration.Components.Any(component =>
                component.ComponentId == proposal.ComponentId
            )
        )
            return AgentOperationCodes.Invalid;
        switch (proposal.Kind)
        {
            case OperationVocabulary.Kinds.Event:
                if (
                    proposal.Layer is null
                    || proposal.StartDate is null
                    || proposal.SourceRef is null
                    || proposal.Reason is null
                    || proposal.Confidence is null
                )
                    return AgentOperationCodes.Invalid;
                break;
            case OperationVocabulary.Kinds.PlanNode:
            {
                var index = LevelIndex(declaration, proposal.LevelId);
                if (index < 0)
                    return AgentOperationCodes.Invalid;
                if (index > 0)
                {
                    var parentId = ParentIdOf(proposal.ParentProposalKey);
                    var parent = parentId is null
                        ? null
                        : items.FirstOrDefault(item =>
                            item.Kind == OperationVocabulary.Kinds.PlanNode
                            && item.ItemId == parentId
                        );
                    if (parent is null || LevelIndex(declaration, parent.LevelId) != index - 1)
                        return AgentOperationCodes.Invalid;
                    if (!parent.IsApproved)
                        return AgentOperationCodes.ParentNotApproved;
                }
                break;
            }
            case OperationVocabulary.Kinds.Content:
                if (
                    proposal.PlatformId is null
                    || !ReviewChecksPassed(proposal.Payload ?? EmptyPayload)
                )
                    return "OPERATION_REVIEW_CHECKS_FAILED";
                break;
            case OperationVocabulary.Kinds.Finding:
                if (proposal.SourceRef is null || proposal.Reason is null)
                    return AgentOperationCodes.Invalid;
                if (
                    proposal.Payload is { ValueKind: JsonValueKind.Object } findingPayload
                    && findingPayload.TryGetProperty("basis", out var basis)
                    && basis.GetString() == "REGISTRY"
                    && !settings.RegistryReadsEnabled
                )
                    return AgentOperationCodes.NotEnabled;
                break;
            case OperationVocabulary.Kinds.Goal:
                if (
                    GoalSkillOf(proposal) is not { } skill
                    || !declaration.Cadence.Any(cadence => cadence.SkillId == skill)
                )
                    return AgentOperationCodes.Invalid;
                break;
        }
        return null;
    }

    private async Task RaiseBehindPaceAsync(
        OperationCaller caller,
        JsonElement payload,
        CancellationToken ct
    )
    {
        if (
            payload.ValueKind != JsonValueKind.Object
            || !payload.TryGetProperty("behindPace", out var behind)
            || behind.ValueKind != JsonValueKind.Array
        )
            return;
        foreach (
            var skill in behind
                .EnumerateArray()
                .Where(value => value.ValueKind == JsonValueKind.String)
                .Select(value => value.GetString()!)
                .Take(8)
        )
            await alerts.RaiseAsync(
                caller.TenantId,
                caller.RelationshipId,
                "GOAL_BEHIND_PACE",
                "WARNING",
                $"pace-{skill}-{Today:yyyyMM}",
                "A goal is behind pace this month.",
                ct
            );
    }

    // ───────────────────────── conversation allowance ─────────────────────────

    /// <summary>Counts one chat against the package allowance. At the limit it says so plainly and counts nothing.</summary>
    public async Task<ChatAllowanceView> RecordChatAsync(
        OperationCaller caller,
        CancellationToken ct
    )
    {
        var (relationship, _) = await LoadAsync(caller, ct);
        var settings = await store.GetSettingsAsync(ct);
        var state = await store.GetStateAsync(caller.TenantId, caller.RelationshipId, Now, ct);
        var current = ChatsOf(settings, relationship, state);
        if (current.Reached)
            throw new AgentOperationException(
                409,
                AgentOperationCodes.ChatLimitReached,
                "You have used all the conversations in your package for now. Your work and approvals are still available."
            );
        state = state with { ChatsUsed = state.ChatsUsed + 1, UpdatedAt = Now };
        await store.SaveStateAsync(state, ct);
        var after = ChatsOf(settings, relationship, state);
        if (after.Remaining * 10 <= after.Allowed && current.Remaining * 10 > current.Allowed)
            await alerts.RaiseAsync(
                caller.TenantId,
                caller.RelationshipId,
                "CHAT_ALLOWANCE_LOW",
                "WARNING",
                $"chats-{Today:yyyyMM}",
                "Your conversation allowance is nearly used.",
                ct
            );
        return after;
    }

    // ───────────────────────── Founder settings and measures ─────────────────────────

    public Task<AgentOperationSettings> GetSettingsAsync(CancellationToken ct) =>
        store.GetSettingsAsync(ct);

    public async Task<AgentOperationSettings> SaveSettingsAsync(
        string actor,
        AgentOperationSettings settings,
        CancellationToken ct
    )
    {
        if (
            settings.ChatAllowanceDefault is < 1 or > OperationVocabulary.MaximumChatAllowance
            || settings.ChatAllowanceByProfessionalType.Count > 50
            || settings.ChatAllowanceByProfessionalType.Any(pair =>
                !OperationVocabulary.IsPlainText(pair.Key, 100)
                || pair.Value is < 1 or > OperationVocabulary.MaximumChatAllowance
            )
            || settings.SandboxAccountIds.Count > 20
            || settings.SandboxAccountIds.Any(id => !OperationVocabulary.IsPlainText(id, 100))
        )
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "The conversation allowance must be a whole number from 1 to 1,000,000."
            );
        await store.SaveSettingsAsync(settings, actor, ct);
        return settings;
    }

    public async Task<ShareView> GetShareAsync(DateOnly from, DateOnly to, CancellationToken ct)
    {
        if (to < from || to.DayNumber - from.DayNumber > 366)
            throw new AgentOperationException(
                400,
                AgentOperationCodes.Invalid,
                "The date range is not valid."
            );
        var counters = await store.CountersAsync(from, to, ct);
        var routes = counters
            .Where(counter => counter.Metric.StartsWith("ROUTE_", StringComparison.Ordinal))
            .ToArray();
        static double? Share(int asked, int accepted, int tool) =>
            asked + accepted + tool == 0
                ? null
                : Math.Round((double)(asked + accepted) / (asked + accepted + tool), 4);
        var days = routes
            .GroupBy(counter => counter.Day)
            .OrderBy(group => group.Key)
            .Select(group =>
            {
                var asked = group
                    .Where(counter => counter.Metric == OperationMetrics.RouteAsked)
                    .Sum(counter => counter.Count);
                var accepted = group
                    .Where(counter => counter.Metric == OperationMetrics.RouteAccepted)
                    .Sum(counter => counter.Count);
                var tool = group
                    .Where(counter => counter.Metric == OperationMetrics.RouteTool)
                    .Sum(counter => counter.Count);
                return new ShareDay(group.Key, asked, accepted, tool, Share(asked, accepted, tool));
            })
            .ToArray();
        return new ShareView(
            SchemaVersion,
            days,
            routes.Select(counter => counter.RelationshipRef).Distinct().Count(),
            Share(
                days.Sum(day => day.Asked),
                days.Sum(day => day.Accepted),
                days.Sum(day => day.Tool)
            )
        );
    }

    public async Task<IReadOnlyList<AttentionRow>> GetAttentionAsync(
        DateOnly from,
        DateOnly to,
        CancellationToken ct
    ) =>
        (await store.CountersAsync(from, to, ct))
            .Where(counter =>
                counter.Metric
                    is OperationMetrics.PublishFailed
                        or OperationMetrics.ConnectionRepair
            )
            .GroupBy(counter => (counter.RelationshipRef, counter.Metric))
            .Select(group => new AttentionRow(
                group.Key.RelationshipRef,
                group.Key.Metric,
                group.Sum(counter => counter.Count),
                group.Max(counter => counter.Day)
            ))
            .OrderByDescending(row => row.LastDay)
            .ToArray();
}
