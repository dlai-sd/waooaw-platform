// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-03
// Constitutional basis: C-001, C-059, C-063, ADR-051

using System.Text.Json;
using System.Text.Json.Serialization;

namespace Waooaw.BusinessPlatform.Services.Workbench;

public sealed record WorkbenchBlockInput(
    Guid RelationshipId,
    string Audience,
    string Phase,
    WorkbenchReadiness Readiness,
    IReadOnlyList<WorkbenchDecision> Decisions,
    IReadOnlyList<WorkbenchTile> Tiles,
    WorkbenchPlan? Plan,
    IReadOnlyList<string> Limitations,
    WorkbenchRecommendedAction? NextAction,
    IReadOnlyList<ExperienceGoalType>? GoalStarters = null
);

/// <summary>
/// Builds the kernel blocks of a workbench reply from the projection and negotiates them against what the channel
/// renders. Every block carries a fallback made only of TEXT, CHOICES, LIST and LINK, so a client that renders
/// less never loses the meaning. No profession wording lives here; labels come from declarations and owners.
/// </summary>
public static class ExperienceBlockBuilder
{
    public const int MaxBlocks = 6;
    public const int MaxChoiceLabel = 20;
    public const int MaxText = 1024;
    public const string ApproveLabel = "Approve";
    public const string DeclineLabel = "Not now";
    public const string DeferLabel = "Ask me later";
    public const string WorkbenchLinkLabel = "Open workbench";

    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    public static string WorkbenchRef(Guid relationshipId) =>
        $"workbench:{relationshipId.ToString("D")}";

    public static IReadOnlyList<ExperienceBlock> Build(
        WorkbenchBlockInput input,
        ChannelCapabilities capabilities
    )
    {
        var blocks = new List<ExperienceBlock> { StatusBlock(input, capabilities) };
        var decisionCap = capabilities.Supports("DECISION", 1) ? 2 : 1;
        if (WorkbenchAudiences.MayDecide(input.Audience))
            blocks.AddRange(
                input.Decisions.Take(decisionCap).Select(item => DecisionBlock(item, capabilities))
            );
        if (input.GoalStarters is not null && WorkbenchAudiences.MayDecide(input.Audience))
            blocks.AddRange(
                input
                    .GoalStarters.Where(type => type.Parameters.Count > 0)
                    .Take(3)
                    .Select(type => GoalFormBlock(type, capabilities))
            );
        var metric = input.Tiles.FirstOrDefault(tile => tile.BlockType == "METRIC");
        if (metric is not null)
            blocks.Add(MetricBlock(metric, capabilities));
        if (input.Plan is not null)
            blocks.Add(PlanBlock(input.Plan, capabilities));
        if (input.Limitations.Count > 0)
            blocks.Add(TextBlock("limitation", input.Limitations[0], "PUBLIC", capabilities));
        var body = blocks.Take(MaxBlocks - 1).ToList();
        body.Add(LinkBlock(input.RelationshipId, capabilities));
        return Negotiate(body, capabilities);
    }

    public static IReadOnlyList<ExperienceBlock> ForDecisions(
        IReadOnlyList<WorkbenchDecision> decisions,
        ChannelCapabilities capabilities,
        Guid relationshipId
    )
    {
        var blocks = decisions
            .Take(MaxBlocks - 1)
            .Select(item => DecisionBlock(item, capabilities))
            .ToList();
        if (blocks.Count == 0)
            blocks.Add(
                TextBlock(
                    "no-decisions",
                    "Nothing is waiting for your decision.",
                    "PUBLIC",
                    capabilities
                )
            );
        blocks.Add(LinkBlock(relationshipId, capabilities));
        return Negotiate(blocks, capabilities);
    }

    public static IReadOnlyList<ExperienceBlock> ForMonitor(
        IReadOnlyList<WorkbenchTile> tiles,
        IReadOnlyList<WorkbenchAlert> alerts,
        IReadOnlyList<string> limitations,
        ChannelCapabilities capabilities,
        Guid relationshipId
    )
    {
        var blocks = tiles
            .Where(tile => tile.BlockType == "METRIC")
            .Take(3)
            .Select(tile => MetricBlock(tile, capabilities))
            .ToList();
        foreach (var alert in alerts.Take(1))
            blocks.Add(
                TextBlock($"alert-{alert.AlertId}", alert.Message, "CUSTOMER", capabilities)
            );
        if (limitations.Count > 0)
            blocks.Add(TextBlock("limitation", limitations[0], "PUBLIC", capabilities));
        if (blocks.Count == 0)
            blocks.Add(
                TextBlock("no-monitor", "No measures are reported yet.", "PUBLIC", capabilities)
            );
        blocks = blocks.Take(MaxBlocks - 1).ToList();
        blocks.Add(LinkBlock(relationshipId, capabilities));
        return Negotiate(blocks, capabilities);
    }

    public static ExperienceBlock StatusBlock(
        WorkbenchBlockInput input,
        ChannelCapabilities capabilities
    )
    {
        var state = PhaseState(input.Phase, input.Readiness);
        var line = $"{Humanize(input.Phase)}: {Humanize(state).ToLowerInvariant()}.";
        if (input.NextAction is not null)
            line = $"{line} Next: {input.NextAction.Label}. {input.NextAction.Reason}";
        return new ExperienceBlock(
            "status",
            "STATUS",
            1,
            "CUSTOMER",
            Data(
                new
                {
                    itemRef = $"phase:{input.Phase}",
                    state,
                    owner = "Platform",
                    freshness = "CURRENT",
                }
            ),
            [new ExperienceFallbackBlock("TEXT", TextData(line))],
            Spoken(line, capabilities),
            Clip(Humanize(input.Phase), 120)
        );
    }

    public static ExperienceBlock DecisionBlock(
        WorkbenchDecision decision,
        ChannelCapabilities capabilities
    )
    {
        var id = decision.DecisionId.ToString("D");
        var line = $"{decision.Effect} Authority: {decision.Authority}.";
        if (decision.Cost is not null)
            line = $"{line} Cost: {decision.Cost}.";
        var approve = Clip(decision.ConfirmLabel, MaxChoiceLabel);
        var decline = Clip(decision.CancelLabel, MaxChoiceLabel);
        if (string.Equals(decline, approve, StringComparison.OrdinalIgnoreCase))
            decline = DeclineLabel;
        var choices = new List<object>
        {
            new { choiceId = $"approve:{id}", label = approve },
            new { choiceId = $"decline:{id}", label = decline },
            new { choiceId = $"defer:{id}", label = DeferLabel },
        };
        return new ExperienceBlock(
            $"decision-{id}",
            "DECISION",
            1,
            "SENSITIVE",
            Data(
                new
                {
                    decisionId = id,
                    effect = decision.Effect,
                    authority = decision.Authority,
                    cost = decision.Cost,
                    confirmLabel = decision.ConfirmLabel,
                    cancelLabel = decision.CancelLabel,
                    expiresAt = decision.ExpiresAt,
                }
            ),
            [
                new ExperienceFallbackBlock("TEXT", TextData(line)),
                new ExperienceFallbackBlock("CHOICES", Data(new { choices })),
            ],
            Spoken(line, capabilities)
        );
    }

    public static ExperienceBlock MetricBlock(WorkbenchTile tile, ChannelCapabilities capabilities)
    {
        var line =
            $"{tile.Label}: {tile.Value}{(tile.Unit.Length > 0 ? " " + tile.Unit : string.Empty)}.";
        return new ExperienceBlock(
            $"metric-{tile.TileId}",
            "METRIC",
            1,
            "CUSTOMER",
            Data(
                new
                {
                    measureId = tile.MeasureId,
                    value = tile.Value,
                    unit = tile.Unit,
                    target = tile.Target,
                    trend = tile.Trend,
                    freshness = tile.Freshness,
                }
            ),
            [new ExperienceFallbackBlock("TEXT", TextData(line))],
            Spoken(line, capabilities),
            Clip(tile.Label, 120)
        );
    }

    public static ExperienceBlock PlanBlock(WorkbenchPlan plan, ChannelCapabilities capabilities)
    {
        var milestones = plan
            .Milestones.Take(5)
            .Select(item => new
            {
                milestoneId = item.MilestoneId,
                title = Clip(item.Title, 120),
                dueMeaning = Clip(item.DueMeaning, 240),
            })
            .ToArray();
        var calendar = plan
            .Calendar.Take(5)
            .Select(item => new { date = item.Date, title = Clip(item.Title, 120) })
            .ToArray();
        var line =
            $"Plan {plan.PlanVersion} ({Humanize(plan.State).ToLowerInvariant()}): "
            + (
                milestones.Length == 0
                    ? "no milestones yet."
                    : string.Join("; ", milestones.Select(item => item.title)) + "."
            );
        return new ExperienceBlock(
            "plan",
            "PLAN",
            1,
            "CUSTOMER",
            Data(
                new
                {
                    planVersion = plan.PlanVersion,
                    milestones,
                    calendar,
                }
            ),
            [new ExperienceFallbackBlock("TEXT", TextData(line))],
            Spoken(line, capabilities),
            "Plan"
        );
    }

    public static ExperienceBlock GoalFormBlock(
        ExperienceGoalType type,
        ChannelCapabilities capabilities
    )
    {
        var title = Clip(
            type.Starters.Count > 0 ? type.Starters[0] : Humanize(type.GoalTypeId),
            120
        );
        var fields = type
            .Parameters.Take(12)
            .Select(parameter => new
            {
                fieldId = Clip(parameter, 128),
                label = Clip(Humanize(parameter), 120),
                type = "TEXT",
                required = true,
            })
            .ToArray();
        var line = $"{title}. Open the workbench to set this goal.";
        return new ExperienceBlock(
            Clip($"goal-form-{type.GoalTypeId}", 64),
            "FORM",
            1,
            "CUSTOMER",
            Data(new { formId = Clip($"goal:{type.GoalTypeId}", 128), fields }),
            [new ExperienceFallbackBlock("TEXT", TextData(line))],
            Spoken(line, capabilities),
            title
        );
    }

    public static ExperienceBlock TextBlock(
        string id,
        string text,
        string sensitivity,
        ChannelCapabilities capabilities
    ) => new(Clip(id, 64), "TEXT", 1, sensitivity, TextData(text), [], Spoken(text, capabilities));

    public static ExperienceBlock LinkBlock(
        Guid relationshipId,
        ChannelCapabilities capabilities
    ) =>
        new(
            "workbench-link",
            "LINK",
            1,
            "CUSTOMER",
            Data(new { label = WorkbenchLinkLabel, destinationRef = WorkbenchRef(relationshipId) }),
            [],
            null
        );

    /// <summary>
    /// Replaces every block the client cannot render with the blocks of its fallback, keeps at most one LINK and at
    /// most six blocks, and keeps the LINK last when it fits.
    /// </summary>
    public static IReadOnlyList<ExperienceBlock> Negotiate(
        IReadOnlyList<ExperienceBlock> blocks,
        ChannelCapabilities capabilities
    )
    {
        var result = new List<ExperienceBlock>();
        foreach (var block in blocks)
        {
            if (capabilities.Supports(block.Type, block.Version))
            {
                result.Add(block);
                continue;
            }
            var index = 0;
            foreach (var fallback in block.Fallback)
            {
                index++;
                if (!capabilities.Supports(fallback.Type, 1))
                    continue;
                result.Add(
                    new ExperienceBlock(
                        Clip($"{block.Id}.{index}", 64),
                        fallback.Type,
                        1,
                        block.Sensitivity,
                        fallback.Data,
                        [],
                        index == 1 ? block.Spoken : null,
                        null
                    )
                );
            }
        }
        var link = result.FirstOrDefault(item => item.Type == "LINK");
        var body = result.Where(item => item.Type != "LINK").ToList();
        if (link is null)
            return body.Take(MaxBlocks).ToArray();
        body = body.Take(MaxBlocks - 1).ToList();
        body.Add(link);
        return body;
    }

    public static string PhaseState(string phase, WorkbenchReadiness readiness) =>
        phase switch
        {
            "OPERATIONS" => readiness.Operations switch
            {
                "ACTIVE" => "IN_PROGRESS",
                "ELIGIBLE" => "READY",
                "PAUSED" => "DEFERRED",
                "BLOCKED" => "BLOCKED",
                "REASSESSMENT_REQUIRED" => "WAITING_ON_CUSTOMER",
                "TERMINATED" => "CANCELLED",
                _ => "PROPOSED",
            },
            "PLANNING" => readiness.Plan switch
            {
                "AGREED" => "COMPLETED",
                "READY_FOR_REVIEW" => "WAITING_ON_CUSTOMER",
                "BLOCKED" => "BLOCKED",
                "NO_PLAN" => "PROPOSED",
                "STALE_REASSESSMENT_REQUIRED" => "WAITING_ON_CUSTOMER",
                _ => "IN_PROGRESS",
            },
            _ => readiness.Induction switch
            {
                "READY" or "READY_WITH_DEFERRED_ITEMS" => "COMPLETED",
                "BLOCKED" => "BLOCKED",
                "NOT_STARTED" => "PROPOSED",
                "STALE_REASSESSMENT_REQUIRED" => "WAITING_ON_CUSTOMER",
                _ => "IN_PROGRESS",
            },
        };

    /// <summary>Turns a declared identifier such as PROFILE_COVERAGE into customer wording, "Profile coverage".</summary>
    public static string Humanize(string identifier)
    {
        var words = identifier.Replace('_', ' ').Replace('-', ' ').Trim().ToLowerInvariant();
        return words.Length == 0 ? identifier : char.ToUpperInvariant(words[0]) + words[1..];
    }

    public static string Clip(string value, int max)
    {
        var text = value.Trim();
        return text.Length <= max ? text : text[..(max - 1)].TrimEnd() + "…";
    }

    private static string? Spoken(string text, ChannelCapabilities capabilities) =>
        capabilities.Voice && text.Length > 0 ? Clip(text, MaxText) : null;

    private static JsonElement TextData(string text) => Data(new { text = Clip(text, MaxText) });

    private static JsonElement Data(object value) => JsonSerializer.SerializeToElement(value, Json);
}
