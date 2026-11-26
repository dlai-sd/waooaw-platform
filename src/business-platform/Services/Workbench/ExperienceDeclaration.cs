// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01, C6-06
// Constitutional basis: C-001, C-059, C-063, ADR-051

using System.Text.Json;
using Waooaw.BusinessPlatform.Services.Alerts;

namespace Waooaw.BusinessPlatform.Services.Workbench;

public sealed record ExperienceMeasure(
    string MeasureId,
    string Unit,
    string EvidenceSource,
    int FreshnessSeconds
);

public sealed record ExperienceGoalType(
    string GoalTypeId,
    IReadOnlyList<string> Parameters,
    IReadOnlyList<ExperienceMeasure> Measures,
    IReadOnlyList<string> Constraints,
    IReadOnlyList<string> Starters
);

public sealed record ExperienceCadence(string SkillId, string Trigger, string Window);

public sealed record ExperienceApprovalMode(string Mode, string Escalation);

public sealed record ExperienceTile(
    string TileId,
    string MeasureId,
    string BlockType,
    IReadOnlyList<string> Audiences
);

public sealed record ExperienceNarrative(
    string NarrativeId,
    string Cadence,
    IReadOnlyList<string> Channels,
    IReadOnlyList<string> Structure
);

public sealed record ExperienceAlert(
    string Signal,
    string Threshold,
    string Severity,
    IReadOnlyList<string> Channels
);

public sealed record ExperienceDomainBlock(
    string BlockId,
    int Version,
    IReadOnlyList<string> FallbackBlocks
);

/// <summary>What a navigation entry opens: a platform view, a composition of existing blocks, or a registered domain block.</summary>
public sealed record ExperienceNavigationSurface(
    string Kind,
    string? Target,
    IReadOnlyList<string> Blocks
);

/// <summary>One entry an agent adds to its context menu (WC171-R003): data only, rendered by the platform.</summary>
public sealed record ExperienceNavigationEntry(
    string EntryId,
    string LabelKey,
    string Label,
    string Icon,
    int Order,
    ExperienceNavigationSurface Surface,
    IReadOnlyList<string> Audiences,
    string AvailabilityGate
);

public static class ExperienceNavigationRules
{
    public const int MaximumEntries = 12;

    public static readonly IReadOnlySet<string> SurfaceKinds = new HashSet<string>(
        StringComparer.Ordinal
    )
    {
        "KERNEL_VIEW",
        "BLOCK_COMPOSITION",
        "DOMAIN_BLOCK",
    };

    /// <summary>The platform views a declared entry may open besides the fixed surfaces; the agent cannot name a new one.</summary>
    public static readonly IReadOnlySet<string> KernelViews = new HashSet<string>(
        StringComparer.Ordinal
    )
    {
        "connections",
        "calendar",
        "presence",
        "profile",
        "goals",
        "plan_tree",
        "approvals",
        "published",
        "results",
        "improve",
    };

    public static readonly IReadOnlySet<string> Icons = new HashSet<string>(StringComparer.Ordinal)
    {
        "profile",
        "calendar",
        "accounts",
        "results",
        "plan",
        "work",
        "insights",
        "documents",
    };

    public static readonly IReadOnlySet<string> Gates = new HashSet<string>(StringComparer.Ordinal)
    {
        "ALWAYS",
        "AFTER_FIRST_APPROVAL",
        "NEEDS_CONNECTED_ACCOUNTS",
    };

    public static readonly IReadOnlySet<string> CompositionBlocks = new HashSet<string>(
        StringComparer.Ordinal
    )
    {
        "TEXT",
        "CHOICES",
        "LIST",
        "LINK",
        "STATUS",
        "METRIC",
        "PLAN",
        "DECISION",
        "FORM",
        "EVIDENCE",
    };

    private static readonly char[] Markup = ['<', '>', '&', '{', '}', '[', ']', '`', '\\'];

    /// <summary>WC-174: the three fixed mode ids every agent has. An agent never invents a fourth.</summary>
    public static readonly IReadOnlyList<string> ModeIds = ["INDUCT", "GOALS", "OPERATIONS"];

    public static readonly IReadOnlySet<string> ReadinessSources = new HashSet<string>(
        StringComparer.Ordinal
    )
    {
        "INDUCTION_SUMMARY",
        "GOAL_COVERAGE",
        "OPERATION_STATUS",
    };

    public static readonly IReadOnlySet<string> GateActions = new HashSet<string>(
        StringComparer.Ordinal
    )
    {
        "PUBLISH",
        "SCHEDULE",
        "GENERATE_MEDIA",
    };

    public static readonly IReadOnlySet<string> ToolCommands = new HashSet<string>(
        StringComparer.Ordinal
    )
    {
        "ADD_EVENT",
        "ADD_PLACEHOLDER",
        "ADD_PLAN_NODE",
        "ADD_CONTENT",
        "ADD_SLOT",
        "ADD_NOTE",
    };

    public static readonly IReadOnlySet<string> Connectors = new HashSet<string>(
        StringComparer.Ordinal
    )
    {
        "META_FACEBOOK",
        "META_INSTAGRAM",
        "NONE",
    };

    public static readonly IReadOnlySet<string> Views = new HashSet<string>(StringComparer.Ordinal)
    {
        "MONTH",
        "WEEK",
        "PLATFORMS",
        "STORYBOARD",
    };

    public const int MaximumPlanLevels = 6;
    public const int MaximumLayers = 16;
    public const int MaximumPlatforms = 16;

    public static bool IsIdentifier(string value) =>
        value.Length is >= 3 and <= 64
        && char.IsAsciiLetterUpper(value[0])
        && value.All(character =>
            char.IsAsciiLetterUpper(character) || char.IsAsciiDigit(character) || character == '_'
        );

    /// <summary>A label is plain words: no markup, no template tokens, no control characters.</summary>
    public static bool IsPlainLabel(string value) =>
        value.Length is >= 1 and <= 40
        && value.IndexOfAny(Markup) < 0
        && !value.Any(char.IsControl);
}

public sealed record ExperienceFlyoutOption(string OptionId, string LabelKey, string Label);

public sealed record ExperienceTool(
    string ToolId,
    string LabelKey,
    string Label,
    string Icon,
    string Command,
    string? PlanLevel,
    string? ComponentId,
    IReadOnlyList<ExperienceFlyoutOption> Flyout
);

public sealed record ExperienceToolGroup(
    string GroupId,
    string LabelKey,
    string Label,
    IReadOnlyList<ExperienceTool> Tools
);

/// <summary>A gate blocks one action with a side effect until a mode is ready; it never blocks opening a screen (MD2).</summary>
public sealed record ExperienceModeGate(string Action, string RequiresMode, string MessageKey);

/// <summary>One of the three fixed modes, declared as data (WC174-R001).</summary>
public sealed record ExperienceMode(
    string ModeId,
    string LabelKey,
    string Label,
    string ReadinessSource,
    IReadOnlyList<ExperienceNavigationEntry> Entries,
    IReadOnlyList<ExperienceToolGroup> ToolGroups,
    IReadOnlyList<ExperienceModeGate> Gates
);

public sealed record ExperienceEventLayer(
    string LayerId,
    string LabelKey,
    string Label,
    bool Sensitive,
    bool DefaultOn
);

public sealed record ExperiencePlanLevel(string LevelId, string LabelKey, string Label);

public sealed record ExperiencePlatform(
    string PlatformId,
    string LabelKey,
    string Label,
    string Connector
);

public sealed record ExperienceComponent(
    string ComponentId,
    string Label,
    string Unit,
    string Kind,
    string? SkillId,
    string CountedOn,
    string Availability
);

/// <summary>What an admitted agent manifest declares about its own experience; the kernel never adds profession text.</summary>
public sealed record ExperienceDeclaration(
    string ContractVersion,
    IReadOnlyList<ExperienceGoalType> GoalTypes,
    IReadOnlyList<string> MilestoneTypes,
    IReadOnlyList<string> CalendarWindows,
    IReadOnlyList<string> WorkItemTypes,
    IReadOnlyList<ExperienceCadence> Cadence,
    IReadOnlyList<ExperienceApprovalMode> ApprovalModes,
    IReadOnlyList<ExperienceTile> Tiles,
    IReadOnlyList<ExperienceNarrative> Narratives,
    IReadOnlyList<ExperienceAlert> Alerts,
    IReadOnlyList<ExperienceDomainBlock> DomainBlocks,
    IReadOnlyList<ExperienceComponent> Components,
    IReadOnlyList<string> Audiences,
    IReadOnlyDictionary<string, IReadOnlyList<string>> ChannelSupport
)
{
    /// <summary>Optional entries after the fixed surfaces; a declaration without them shows only the fixed surfaces.</summary>
    public IReadOnlyList<ExperienceNavigationEntry> Navigation { get; init; } = [];

    /// <summary>WC-174: optional modes; a declaration without them shows the WC-171 menu (WC174-R001).</summary>
    public IReadOnlyList<ExperienceMode> Modes { get; init; } = [];

    public IReadOnlyList<ExperienceEventLayer> EventLayers { get; init; } = [];

    public IReadOnlyList<ExperiencePlanLevel> PlanLevels { get; init; } = [];

    public IReadOnlyList<ExperiencePlatform> Platforms { get; init; } = [];

    public IReadOnlyList<string> Views { get; init; } = [];

    public ExperienceGoalType? GoalTypeForMeasure(string measureId) =>
        GoalTypes.FirstOrDefault(type =>
            type.Measures.Any(measure => measure.MeasureId == measureId)
        );

    public ExperienceMeasure? Measure(string measureId) =>
        GoalTypes
            .SelectMany(type => type.Measures)
            .FirstOrDefault(measure => measure.MeasureId == measureId);

    public ExperienceCadence? CadenceFor(string skillId) =>
        Cadence.FirstOrDefault(item => item.SkillId == skillId);

    public IReadOnlyList<string> ComponentIdsFor(string skillId) =>
        Components
            .Where(item => item.SkillId == skillId)
            .Select(item => item.ComponentId)
            .ToArray();

    /// <summary>The highest approval mode the agent declares first is the safest default shown to the customer.</summary>
    public string DefaultApprovalMode =>
        ApprovalModes.Count > 0 ? ApprovalModes[0].Mode : "CUSTOMER_APPROVAL";

    /// <summary>The block types the channel renders natively; absent channels fall back to the v1 set.</summary>
    public IReadOnlyList<string> BlocksFor(string channel) =>
        ChannelSupport.TryGetValue(channel.ToLowerInvariant(), out var blocks)
            ? blocks
            : ["TEXT", "CHOICES", "LIST", "LINK"];
}

/// <summary>The result of scanning one admitted manifest for experience compatibility.</summary>
public sealed record ExperienceScanResult(
    string State,
    IReadOnlyList<string> ReasonCodes,
    ExperienceDeclaration? Declaration
)
{
    public const string Compatible = "COMPATIBLE";
    public const string NotDeclared = "NOT_DECLARED";
    public const string Incompatible = "INCOMPATIBLE";

    public bool ExperienceCapable => State == Compatible && Declaration is not null;
}

/// <summary>
/// Validates the optional `experience` section of an admitted employment interface manifest and reads it into a
/// declaration. It fails closed: any structural gap makes the manifest incompatible instead of guessing a default.
/// </summary>
public static class ExperienceManifestScanner
{
    public const string SupportedContractMajor = "1";

    public static readonly IReadOnlySet<string> BlockTypes = new HashSet<string>(
        StringComparer.Ordinal
    )
    {
        "TEXT",
        "CHOICES",
        "LIST",
        "LINK",
        "STATUS",
        "METRIC",
        "PLAN",
        "DECISION",
        "FORM",
        "EVIDENCE",
        "DOMAIN",
    };

    private static readonly string[] V1Blocks = ["TEXT", "CHOICES", "LIST", "LINK"];

    public static ExperienceScanResult Scan(JsonElement manifest)
    {
        if (
            manifest.ValueKind != JsonValueKind.Object
            || !manifest.TryGetProperty("experience", out var section)
            || section.ValueKind == JsonValueKind.Null
        )
            return new ExperienceScanResult(
                ExperienceScanResult.NotDeclared,
                ["EXPERIENCE_NOT_DECLARED"],
                null
            );
        var reasons = new SortedSet<string>(StringComparer.Ordinal);
        if (section.ValueKind != JsonValueKind.Object)
            return Incompatible(["EXPERIENCE_SECTION_INVALID"]);
        var contractVersion = Text(section, "contractVersion");
        if (contractVersion is null || contractVersion.Split('.')[0] != SupportedContractMajor)
            reasons.Add("EXPERIENCE_CONTRACT_VERSION_UNSUPPORTED");

        var goalTypes = Objects(section, "goalTypes")
            .Select(goal => new ExperienceGoalType(
                Text(goal, "goalTypeId") ?? string.Empty,
                Strings(goal, "parameters"),
                Objects(goal, "measures")
                    .Select(measure => new ExperienceMeasure(
                        Text(measure, "measureId") ?? string.Empty,
                        Text(measure, "unit") ?? string.Empty,
                        Text(measure, "evidenceSource") ?? string.Empty,
                        measure.TryGetProperty("freshnessSeconds", out var freshness)
                        && freshness.ValueKind == JsonValueKind.Number
                        && freshness.TryGetInt32(out var seconds)
                            ? seconds
                            : 0
                    ))
                    .ToArray(),
                Strings(goal, "constraints"),
                Strings(goal, "starters")
            ))
            .ToArray();
        var plan = Object(section, "plan");
        var operate = Object(section, "operate");
        var monitor = Object(section, "monitor");
        var cadence = operate is null
            ? []
            : Objects(operate.Value, "cadence")
                .Select(item => new ExperienceCadence(
                    Text(item, "skillId") ?? string.Empty,
                    Text(item, "trigger") ?? string.Empty,
                    Text(item, "window") ?? string.Empty
                ))
                .ToArray();
        var approvalModes = operate is null
            ? []
            : Objects(operate.Value, "approvalModes")
                .Select(item => new ExperienceApprovalMode(
                    Text(item, "mode") ?? string.Empty,
                    Text(item, "escalation") ?? string.Empty
                ))
                .ToArray();
        var tiles = monitor is null
            ? []
            : Objects(monitor.Value, "tiles")
                .Select(item => new ExperienceTile(
                    Text(item, "tileId") ?? string.Empty,
                    Text(item, "measureId") ?? string.Empty,
                    Text(item, "blockType") ?? string.Empty,
                    Strings(item, "audiences")
                ))
                .ToArray();
        var narratives = monitor is null
            ? []
            : Objects(monitor.Value, "narratives")
                .Select(item => new ExperienceNarrative(
                    Text(item, "narrativeId") ?? string.Empty,
                    Text(item, "cadence") ?? string.Empty,
                    Strings(item, "channels"),
                    Strings(item, "structure")
                ))
                .ToArray();
        var alerts = monitor is null
            ? []
            : Objects(monitor.Value, "alerts")
                .Select(item => new ExperienceAlert(
                    Text(item, "signal") ?? string.Empty,
                    Text(item, "threshold") ?? string.Empty,
                    Text(item, "severity") ?? string.Empty,
                    Strings(item, "channels")
                ))
                .ToArray();
        var domainBlocks = Objects(section, "domainBlocks")
            .Select(item => new ExperienceDomainBlock(
                Text(item, "blockId") ?? string.Empty,
                item.TryGetProperty("version", out var version)
                && version.ValueKind == JsonValueKind.Number
                && version.TryGetInt32(out var number)
                    ? number
                    : 0,
                Strings(item, "fallbackBlocks")
            ))
            .ToArray();
        var components = Objects(section, "components")
            .Select(item => new ExperienceComponent(
                Text(item, "componentId") ?? string.Empty,
                Text(item, "label") ?? string.Empty,
                Text(item, "unit") ?? string.Empty,
                Text(item, "kind") ?? string.Empty,
                Text(item, "skillId"),
                Text(item, "countedOn") ?? string.Empty,
                Text(item, "availability") ?? string.Empty
            ))
            .ToArray();
        var support = new Dictionary<string, IReadOnlyList<string>>(StringComparer.Ordinal);
        if (Object(section, "channelSupport") is { } channelSupport)
            foreach (var channel in channelSupport.EnumerateObject())
                support[channel.Name] = Strings(channelSupport, channel.Name);
        var audiences = Strings(section, "audiences");
        var navigation = ReadNavigation(
            section,
            domainBlocks,
            audiences,
            reasons,
            out var navigationMalformed
        );
        if (navigationMalformed)
            reasons.Add("EXPERIENCE_NAVIGATION_INVALID");
        var planLevels = ReadPlanLevels(section, reasons);
        var eventLayers = ReadEventLayers(section, reasons);
        var platforms = ReadPlatforms(section, reasons);
        var views = ReadViews(section, reasons);
        var modes = ReadModes(section, domainBlocks, audiences, planLevels, reasons);
        if (
            alerts.Any(alert =>
                AlertPolicy.ValidateDeclaration(alert.Severity, alert.Channels).Count > 0
            )
        )
            reasons.Add("EXPERIENCE_ALERT_POLICY_VIOLATION");

        if (
            goalTypes.Length == 0
            || goalTypes.Any(goal =>
                goal.GoalTypeId.Length == 0
                || goal.Measures.Count == 0
                || goal.Measures.Any(measure => measure.MeasureId.Length == 0)
            )
            || plan is null
            || operate is null
            || monitor is null
            || cadence.Length == 0
            || approvalModes.Length == 0
            || tiles.Length == 0
            || components.Any(component =>
                component.ComponentId.Length == 0 || component.Label.Length == 0
            )
            || audiences.Count == 0
        )
            reasons.Add("EXPERIENCE_SECTION_INVALID");
        if (goalTypes.Select(goal => goal.GoalTypeId).Distinct().Count() != goalTypes.Length)
            reasons.Add("EXPERIENCE_SECTION_INVALID");
        if (components.Select(item => item.ComponentId).Distinct().Count() != components.Length)
            reasons.Add("EXPERIENCE_COMPONENT_DUPLICATE");
        var cadenceSkills = cadence.Select(item => item.SkillId).ToHashSet(StringComparer.Ordinal);
        if (
            components.Any(component =>
                component.SkillId is not null && !cadenceSkills.Contains(component.SkillId)
            )
        )
            reasons.Add("EXPERIENCE_COMPONENT_SKILL_UNRESOLVED");
        if (
            components.Any(component =>
                component.Availability == "AVAILABLE" && component.SkillId is null
            )
        )
            reasons.Add("EXPERIENCE_COMPONENT_THREAD_MISSING");
        var measures = goalTypes
            .SelectMany(goal => goal.Measures)
            .Select(measure => measure.MeasureId)
            .ToHashSet(StringComparer.Ordinal);
        if (tiles.Any(tile => !measures.Contains(tile.MeasureId)))
            reasons.Add("EXPERIENCE_TILE_MEASURE_UNRESOLVED");
        if (
            audiences.Any(audience => !WorkbenchAudiences.All.Contains(audience))
            || tiles.Any(tile => tile.Audiences.Any(item => !WorkbenchAudiences.All.Contains(item)))
        )
            reasons.Add("EXPERIENCE_AUDIENCE_UNSUPPORTED");
        if (
            !support.ContainsKey("web")
            || !support.ContainsKey("whatsapp")
            || support.Values.Any(blocks =>
                blocks.Any(block => !BlockTypes.Contains(block)) || !V1Blocks.All(blocks.Contains)
            )
        )
            reasons.Add("EXPERIENCE_CHANNEL_SUPPORT_MISSING");
        if (
            domainBlocks.Any(block =>
                block.BlockId.Length == 0
                || block.FallbackBlocks.Count == 0
                || block.FallbackBlocks.Any(type => !V1Blocks.Contains(type))
            )
        )
            reasons.Add("EXPERIENCE_DOMAIN_BLOCK_FALLBACK_MISSING");

        if (reasons.Count > 0)
            return Incompatible(reasons.ToArray());
        var declaration = new ExperienceDeclaration(
            contractVersion!,
            goalTypes,
            plan is null ? [] : Strings(plan.Value, "milestoneTypes"),
            plan is null ? [] : Strings(plan.Value, "calendarWindows"),
            operate is null ? [] : Strings(operate.Value, "workItemTypes"),
            cadence,
            approvalModes,
            tiles,
            narratives,
            alerts,
            domainBlocks,
            components,
            audiences,
            support
        )
        {
            Navigation = navigation,
            Modes = modes,
            EventLayers = eventLayers,
            PlanLevels = planLevels,
            Platforms = platforms,
            Views = views,
        };
        return new ExperienceScanResult(
            ExperienceScanResult.Compatible,
            ["COMPATIBLE"],
            declaration
        );
    }

    /// <summary>
    /// Reads the optional navigation entries and refuses what the contract forbids: an unknown surface kind (an embedded
    /// surface is not available), markup in a label, a duplicate id, and an entry that opens nothing.
    /// </summary>
    private static IReadOnlyList<ExperienceNavigationEntry> ReadNavigation(
        JsonElement section,
        IReadOnlyList<ExperienceDomainBlock> domainBlocks,
        IReadOnlyList<string> audiences,
        SortedSet<string> reasons,
        out bool malformed
    )
    {
        malformed = false;
        if (
            !section.TryGetProperty("navigation", out var raw)
            || raw.ValueKind == JsonValueKind.Null
        )
            return [];
        return ReadEntries(raw, domainBlocks, audiences, reasons, out malformed);
    }

    private static IReadOnlyList<ExperienceNavigationEntry> ReadEntries(
        JsonElement raw,
        IReadOnlyList<ExperienceDomainBlock> domainBlocks,
        IReadOnlyList<string> audiences,
        SortedSet<string> reasons,
        out bool malformed
    )
    {
        malformed = false;
        if (
            raw.ValueKind != JsonValueKind.Array
            || raw.GetArrayLength() > ExperienceNavigationRules.MaximumEntries
        )
        {
            malformed = true;
            return [];
        }
        var entries = new List<ExperienceNavigationEntry>();
        foreach (var item in raw.EnumerateArray())
        {
            if (item.ValueKind != JsonValueKind.Object)
            {
                malformed = true;
                continue;
            }
            var surface = Object(item, "surface");
            var kind = surface is null ? null : Text(surface.Value, "kind");
            var target = surface is null ? null : Text(surface.Value, "target");
            var blocks = surface is null ? [] : Strings(surface.Value, "blocks");
            var entryId = Text(item, "entryId");
            var labelKey = Text(item, "labelKey");
            var label = Text(item, "label");
            var icon = Text(item, "icon");
            var gate = Text(item, "availabilityGate");
            var entryAudiences = Strings(item, "audiences");
            if (
                entryId is null
                || !ExperienceNavigationRules.IsIdentifier(entryId)
                || labelKey is null
                || !ExperienceNavigationRules.IsIdentifier(labelKey)
                || label is null
                || !ExperienceNavigationRules.IsPlainLabel(label)
                || icon is null
                || !ExperienceNavigationRules.Icons.Contains(icon)
                || gate is null
                || !ExperienceNavigationRules.Gates.Contains(gate)
                || !item.TryGetProperty("order", out var orderValue)
                || orderValue.ValueKind != JsonValueKind.Number
                || !orderValue.TryGetInt32(out var order)
                || order is < 0 or > 999
                || entryAudiences.Count == 0
                || entryAudiences.Any(audience => !WorkbenchAudiences.All.Contains(audience))
                || surface is null
            )
            {
                malformed = true;
                continue;
            }
            // An entry for an audience this agent does not serve is simply never shown to anyone it does not serve.
            var served = entryAudiences.Where(audiences.Contains).ToArray();
            if (served.Length == 0)
                continue;
            if (kind is null || !ExperienceNavigationRules.SurfaceKinds.Contains(kind))
            {
                reasons.Add("EXPERIENCE_NAVIGATION_SURFACE_UNSUPPORTED");
                continue;
            }
            var opensSomething = kind switch
            {
                "KERNEL_VIEW" => target is not null
                    && ExperienceNavigationRules.KernelViews.Contains(target),
                "DOMAIN_BLOCK" => target is not null
                    && domainBlocks.Any(block => block.BlockId == target),
                _ => blocks.Count > 0
                    && blocks.All(ExperienceNavigationRules.CompositionBlocks.Contains),
            };
            if (!opensSomething)
            {
                reasons.Add("EXPERIENCE_NAVIGATION_TARGET_UNRESOLVED");
                continue;
            }
            entries.Add(
                new ExperienceNavigationEntry(
                    entryId,
                    labelKey,
                    label,
                    icon,
                    order,
                    new ExperienceNavigationSurface(kind, target, blocks),
                    served,
                    gate
                )
            );
        }
        if (
            entries.Select(entry => entry.EntryId).Distinct().Count() != entries.Count
            || entries.Select(entry => entry.LabelKey).Distinct().Count() != entries.Count
        )
            reasons.Add("EXPERIENCE_NAVIGATION_DUPLICATE");
        return entries
            .OrderBy(entry => entry.Order)
            .ThenBy(entry => entry.EntryId, StringComparer.Ordinal)
            .ToArray();
    }

    private static ExperienceScanResult Incompatible(IReadOnlyList<string> reasons) =>
        new(ExperienceScanResult.Incompatible, reasons, null);

    private static bool Named(
        JsonElement item,
        out string id,
        out string labelKey,
        out string label,
        string idName
    )
    {
        id = Text(item, idName) ?? string.Empty;
        labelKey = Text(item, "labelKey") ?? string.Empty;
        label = Text(item, "label") ?? string.Empty;
        return ExperienceNavigationRules.IsIdentifier(id)
            && ExperienceNavigationRules.IsIdentifier(labelKey)
            && ExperienceNavigationRules.IsPlainLabel(label);
    }

    private static bool OptionalArray(
        JsonElement section,
        string name,
        int maximum,
        out JsonElement raw
    )
    {
        raw = default;
        if (!section.TryGetProperty(name, out raw) || raw.ValueKind == JsonValueKind.Null)
            return false;
        return true;
    }

    private static IReadOnlyList<ExperiencePlanLevel> ReadPlanLevels(
        JsonElement section,
        SortedSet<string> reasons
    )
    {
        if (
            !OptionalArray(
                section,
                "planLevels",
                ExperienceNavigationRules.MaximumPlanLevels,
                out var raw
            )
        )
            return [];
        var levels = new List<ExperiencePlanLevel>();
        var valid =
            raw.ValueKind == JsonValueKind.Array
            && raw.GetArrayLength() <= ExperienceNavigationRules.MaximumPlanLevels;
        if (valid)
            foreach (var item in raw.EnumerateArray())
            {
                if (
                    item.ValueKind != JsonValueKind.Object
                    || !Named(item, out var id, out var key, out var label, "levelId")
                )
                {
                    valid = false;
                    break;
                }
                levels.Add(new ExperiencePlanLevel(id, key, label));
            }
        if (!valid || levels.Select(level => level.LevelId).Distinct().Count() != levels.Count)
        {
            reasons.Add("EXPERIENCE_PLAN_LEVELS_INVALID");
            return [];
        }
        return levels;
    }

    private static IReadOnlyList<ExperienceEventLayer> ReadEventLayers(
        JsonElement section,
        SortedSet<string> reasons
    )
    {
        if (
            !OptionalArray(
                section,
                "eventLayers",
                ExperienceNavigationRules.MaximumLayers,
                out var raw
            )
        )
            return [];
        var layers = new List<ExperienceEventLayer>();
        var valid =
            raw.ValueKind == JsonValueKind.Array
            && raw.GetArrayLength() <= ExperienceNavigationRules.MaximumLayers;
        if (valid)
            foreach (var item in raw.EnumerateArray())
            {
                if (
                    item.ValueKind != JsonValueKind.Object
                    || !Named(item, out var id, out var key, out var label, "layerId")
                    || !item.TryGetProperty("sensitive", out var sensitive)
                    || sensitive.ValueKind is not (JsonValueKind.True or JsonValueKind.False)
                    || !item.TryGetProperty("defaultOn", out var defaultOn)
                    || defaultOn.ValueKind is not (JsonValueKind.True or JsonValueKind.False)
                    // A sensitive layer (religion, politics) always starts off (MD4, C-061).
                    || (sensitive.GetBoolean() && defaultOn.GetBoolean())
                )
                {
                    valid = false;
                    break;
                }
                layers.Add(
                    new ExperienceEventLayer(
                        id,
                        key,
                        label,
                        sensitive.GetBoolean(),
                        defaultOn.GetBoolean()
                    )
                );
            }
        if (!valid || layers.Select(layer => layer.LayerId).Distinct().Count() != layers.Count)
        {
            reasons.Add("EXPERIENCE_EVENT_LAYERS_INVALID");
            return [];
        }
        return layers;
    }

    private static IReadOnlyList<ExperiencePlatform> ReadPlatforms(
        JsonElement section,
        SortedSet<string> reasons
    )
    {
        if (
            !OptionalArray(
                section,
                "platforms",
                ExperienceNavigationRules.MaximumPlatforms,
                out var raw
            )
        )
            return [];
        var platforms = new List<ExperiencePlatform>();
        var valid =
            raw.ValueKind == JsonValueKind.Array
            && raw.GetArrayLength() <= ExperienceNavigationRules.MaximumPlatforms;
        if (valid)
            foreach (var item in raw.EnumerateArray())
            {
                var connector =
                    item.ValueKind == JsonValueKind.Object ? Text(item, "connector") : null;
                if (
                    item.ValueKind != JsonValueKind.Object
                    || !Named(item, out var id, out var key, out var label, "platformId")
                    || connector is null
                    || !ExperienceNavigationRules.Connectors.Contains(connector)
                )
                {
                    valid = false;
                    break;
                }
                platforms.Add(new ExperiencePlatform(id, key, label, connector));
            }
        if (
            !valid
            || platforms.Select(platform => platform.PlatformId).Distinct().Count()
                != platforms.Count
        )
        {
            reasons.Add("EXPERIENCE_PLATFORMS_INVALID");
            return [];
        }
        return platforms;
    }

    private static IReadOnlyList<string> ReadViews(JsonElement section, SortedSet<string> reasons)
    {
        if (!OptionalArray(section, "views", 4, out var raw))
            return [];
        string[] views =
            raw.ValueKind == JsonValueKind.Array
                ? raw.EnumerateArray()
                    .Select(item =>
                        item.ValueKind == JsonValueKind.String ? item.GetString()! : string.Empty
                    )
                    .ToArray()
                : [];
        if (
            raw.ValueKind != JsonValueKind.Array
            || views.Length > 4
            || views.Distinct().Count() != views.Length
            || views.Any(view => !ExperienceNavigationRules.Views.Contains(view))
        )
        {
            reasons.Add("EXPERIENCE_VIEWS_INVALID");
            return [];
        }
        return views;
    }

    /// <summary>
    /// Reads the optional modes (WC174-R001) and refuses a fourth mode, a duplicate mode, markup, an unknown readiness
    /// source, gate action or tool command, and any entry that opens nothing. Entries follow the same rules as the
    /// WC-171 navigation entries.
    /// </summary>
    private static IReadOnlyList<ExperienceMode> ReadModes(
        JsonElement section,
        IReadOnlyList<ExperienceDomainBlock> domainBlocks,
        IReadOnlyList<string> audiences,
        IReadOnlyList<ExperiencePlanLevel> planLevels,
        SortedSet<string> reasons
    )
    {
        if (!OptionalArray(section, "modes", 3, out var raw))
            return [];
        if (raw.ValueKind != JsonValueKind.Array || raw.GetArrayLength() > 3)
        {
            reasons.Add("EXPERIENCE_MODES_INVALID");
            return [];
        }
        var modes = new List<ExperienceMode>();
        foreach (var item in raw.EnumerateArray())
        {
            if (
                item.ValueKind != JsonValueKind.Object
                || Text(item, "modeId") is not { } modeId
                || !ExperienceNavigationRules.ModeIds.Contains(modeId)
                || !Named(item, out _, out var labelKey, out var label, "modeId")
                || Text(item, "readinessSource") is not { } source
                || !ExperienceNavigationRules.ReadinessSources.Contains(source)
            )
            {
                reasons.Add("EXPERIENCE_MODES_INVALID");
                continue;
            }
            var entries = (IReadOnlyList<ExperienceNavigationEntry>)[];
            var entriesMalformed = !item.TryGetProperty("entries", out var rawEntries);
            if (!entriesMalformed)
                entries = ReadEntries(
                    rawEntries,
                    domainBlocks,
                    audiences,
                    reasons,
                    out entriesMalformed
                );
            if (entriesMalformed)
                reasons.Add("EXPERIENCE_MODES_INVALID");
            var groups = ReadToolGroups(item, planLevels, reasons);
            var gates = ReadGates(item, reasons);
            modes.Add(new ExperienceMode(modeId, labelKey, label, source, entries, groups, gates));
        }
        if (modes.Select(mode => mode.ModeId).Distinct().Count() != modes.Count)
            reasons.Add("EXPERIENCE_MODES_DUPLICATE");
        var entryIds = modes
            .SelectMany(mode => mode.Entries)
            .Select(entry => entry.EntryId)
            .ToArray();
        if (entryIds.Distinct().Count() != entryIds.Length)
            reasons.Add("EXPERIENCE_NAVIGATION_DUPLICATE");
        return ExperienceNavigationRules
            .ModeIds.Select(id => modes.FirstOrDefault(mode => mode.ModeId == id))
            .Where(mode => mode is not null)
            .Select(mode => mode!)
            .ToArray();
    }

    private static IReadOnlyList<ExperienceToolGroup> ReadToolGroups(
        JsonElement mode,
        IReadOnlyList<ExperiencePlanLevel> planLevels,
        SortedSet<string> reasons
    )
    {
        if (!mode.TryGetProperty("toolGroups", out var raw) || raw.ValueKind == JsonValueKind.Null)
            return [];
        var groups = new List<ExperienceToolGroup>();
        var valid = raw.ValueKind == JsonValueKind.Array && raw.GetArrayLength() <= 6;
        if (valid)
            foreach (var group in raw.EnumerateArray())
            {
                if (
                    group.ValueKind != JsonValueKind.Object
                    || !Named(
                        group,
                        out var groupId,
                        out var groupKey,
                        out var groupLabel,
                        "groupId"
                    )
                    || !group.TryGetProperty("tools", out var rawTools)
                    || rawTools.ValueKind != JsonValueKind.Array
                    || rawTools.GetArrayLength() is 0 or > 8
                )
                {
                    valid = false;
                    break;
                }
                var tools = new List<ExperienceTool>();
                foreach (var tool in rawTools.EnumerateArray())
                {
                    var icon = tool.ValueKind == JsonValueKind.Object ? Text(tool, "icon") : null;
                    var command =
                        tool.ValueKind == JsonValueKind.Object ? Text(tool, "command") : null;
                    var level =
                        tool.ValueKind == JsonValueKind.Object ? Text(tool, "planLevel") : null;
                    var toolComponent =
                        tool.ValueKind == JsonValueKind.Object ? Text(tool, "componentId") : null;
                    if (
                        tool.ValueKind != JsonValueKind.Object
                        || !Named(
                            tool,
                            out var toolId,
                            out var toolKey,
                            out var toolLabel,
                            "toolId"
                        )
                        || icon is null
                        || !ExperienceNavigationRules.Icons.Contains(icon)
                        || command is null
                        || !ExperienceNavigationRules.ToolCommands.Contains(command)
                        || (level is not null && !planLevels.Any(item => item.LevelId == level))
                    )
                    {
                        valid = false;
                        break;
                    }
                    var options = new List<ExperienceFlyoutOption>();
                    if (
                        tool.TryGetProperty("flyout", out var rawFlyout)
                        && rawFlyout.ValueKind != JsonValueKind.Null
                    )
                    {
                        if (
                            rawFlyout.ValueKind != JsonValueKind.Array
                            || rawFlyout.GetArrayLength() > 6
                        )
                        {
                            valid = false;
                            break;
                        }
                        foreach (var option in rawFlyout.EnumerateArray())
                        {
                            if (
                                option.ValueKind != JsonValueKind.Object
                                || !Named(
                                    option,
                                    out var optionId,
                                    out var optionKey,
                                    out var optionLabel,
                                    "optionId"
                                )
                            )
                            {
                                valid = false;
                                break;
                            }
                            options.Add(
                                new ExperienceFlyoutOption(optionId, optionKey, optionLabel)
                            );
                        }
                    }
                    tools.Add(
                        new ExperienceTool(
                            toolId,
                            toolKey,
                            toolLabel,
                            icon,
                            command,
                            level,
                            toolComponent,
                            options
                        )
                    );
                }
                if (!valid)
                    break;
                groups.Add(new ExperienceToolGroup(groupId, groupKey, groupLabel, tools));
            }
        if (!valid || groups.Select(group => group.GroupId).Distinct().Count() != groups.Count)
        {
            reasons.Add("EXPERIENCE_MODES_INVALID");
            return [];
        }
        return groups;
    }

    private static IReadOnlyList<ExperienceModeGate> ReadGates(
        JsonElement mode,
        SortedSet<string> reasons
    )
    {
        if (!mode.TryGetProperty("gates", out var raw) || raw.ValueKind == JsonValueKind.Null)
            return [];
        var gates = new List<ExperienceModeGate>();
        var valid = raw.ValueKind == JsonValueKind.Array && raw.GetArrayLength() <= 8;
        if (valid)
            foreach (var item in raw.EnumerateArray())
            {
                if (
                    item.ValueKind != JsonValueKind.Object
                    || Text(item, "action") is not { } action
                    || !ExperienceNavigationRules.GateActions.Contains(action)
                    || Text(item, "requiresMode") is not { } requires
                    || !ExperienceNavigationRules.ModeIds.Contains(requires)
                    || Text(item, "messageKey") is not { } messageKey
                    || !ExperienceNavigationRules.IsIdentifier(messageKey)
                )
                {
                    valid = false;
                    break;
                }
                gates.Add(new ExperienceModeGate(action, requires, messageKey));
            }
        if (!valid)
        {
            reasons.Add("EXPERIENCE_MODES_INVALID");
            return [];
        }
        return gates;
    }

    private static JsonElement? Object(JsonElement parent, string name) =>
        parent.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.Object
            ? value
            : null;

    private static IEnumerable<JsonElement> Objects(JsonElement parent, string name) =>
        parent.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.Array
            ? value.EnumerateArray().Where(item => item.ValueKind == JsonValueKind.Object)
            : [];

    private static string? Text(JsonElement parent, string name) =>
        parent.TryGetProperty(name, out var value)
        && value.ValueKind == JsonValueKind.String
        && !string.IsNullOrWhiteSpace(value.GetString())
            ? value.GetString()
            : null;

    private static IReadOnlyList<string> Strings(JsonElement parent, string name) =>
        parent.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.Array
            ? value
                .EnumerateArray()
                .Where(item => item.ValueKind == JsonValueKind.String)
                .Select(item => item.GetString()!)
                .ToArray()
            : [];
}
