// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01, C6-06
// Constitutional basis: C-001, C-059, C-063, ADR-051

using System.Text.Json;

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
        );
        return new ExperienceScanResult(
            ExperienceScanResult.Compatible,
            ["COMPATIBLE"],
            declaration
        );
    }

    private static ExperienceScanResult Incompatible(IReadOnlyList<string> reasons) =>
        new(ExperienceScanResult.Incompatible, reasons, null);

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
