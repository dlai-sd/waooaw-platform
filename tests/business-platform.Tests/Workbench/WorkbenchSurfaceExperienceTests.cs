// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-03, C6-06
// Constitutional basis: C-001, C-059, C-063, ADR-051

using System.Text.Json;
using System.Text.Json.Nodes;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class WorkbenchSurfaceExperienceTests
{
    private const string Rich =
        "channel=WEB;blocks=TEXT:1,CHOICES:1,LIST:1,LINK:1,STATUS:1,DECISION:1,METRIC:1,PLAN:1,FORM:1";

    private static readonly Guid RelationshipId = Guid.Parse(
        "11111111-2222-3333-4444-555555555555"
    );
    private static readonly DateTimeOffset At = new(2030, 3, 4, 5, 6, 7, TimeSpan.Zero);

    private static ChannelCapabilities Caps(string header) =>
        ChannelCapabilities.Parse(header) ?? throw new InvalidOperationException("header rejected");

    private static WorkbenchReadiness Readiness(string phase, string value) =>
        phase switch
        {
            "OPERATIONS" => new("READY", "AGREED", value, "NOT_STARTED"),
            "PLANNING" => new("READY", value, "ACTIVE", "NOT_STARTED"),
            _ => new(value, "AGREED", "ACTIVE", "NOT_STARTED"),
        };

    private static WorkbenchDecision Decision(
        string confirm = "Approve plan",
        string cancel = "Not now",
        string? cost = "5 content drafts",
        DateTimeOffset? expires = null
    ) =>
        new(
            Guid.NewGuid(),
            "v1",
            "Start the agreed plan.",
            "Customer approval",
            cost,
            confirm,
            cancel,
            expires,
            null,
            "Platform",
            "CURRENT"
        );

    private static WorkbenchTile Tile(
        string id,
        string blockType = "METRIC",
        string unit = "people",
        string? target = "200",
        string? trend = "UP"
    ) =>
        new(
            id,
            "reach",
            $"Reach {id}",
            "120",
            unit,
            target,
            trend,
            null,
            "CURRENT",
            "Platform",
            blockType
        );

    private static WorkbenchAlert Alert(string id = "a1") =>
        new(id, "late_data", "HIGH", "Owner data is late.", At, "STALE");

    private static ExperienceGoalType GoalType(
        string id,
        string[]? parameters = null,
        string[]? starters = null
    ) => new(id, parameters ?? ["audience"], [], [], starters ?? []);

    private static WorkbenchBlockInput Input(
        string audience = WorkbenchAudiences.CustomerOwner,
        string phase = "OPERATIONS",
        IReadOnlyList<WorkbenchDecision>? decisions = null,
        IReadOnlyList<WorkbenchTile>? tiles = null,
        WorkbenchPlan? plan = null,
        IReadOnlyList<string>? limitations = null,
        WorkbenchRecommendedAction? next = null,
        IReadOnlyList<ExperienceGoalType>? starters = null
    ) =>
        new(
            RelationshipId,
            audience,
            phase,
            new WorkbenchReadiness("READY", "AGREED", "ACTIVE", "NOT_STARTED"),
            decisions ?? [],
            tiles ?? [],
            plan,
            limitations ?? [],
            next,
            starters
        );

    private static string TextOf(ExperienceBlock block) =>
        block.Data.GetProperty("text").GetString()!;

    [Fact]
    public void ForDecisions_OnARichClient_KeepsAtMostFiveDecisionBlocksBeforeTheLink()
    {
        var decisions = Enumerable.Range(0, 7).Select(_ => Decision()).ToArray();

        var blocks = ExperienceBlockBuilder.ForDecisions(decisions, Caps(Rich), RelationshipId);

        Assert.Equal(ExperienceBlockBuilder.MaxBlocks, blocks.Count);
        Assert.All(blocks.Take(5), block => Assert.Equal("DECISION", block.Type));
        Assert.Equal(
            decisions.Take(5).Select(item => $"decision-{item.DecisionId:D}"),
            blocks.Take(5).Select(block => block.Id)
        );
        Assert.Equal(
            ExperienceBlockBuilder.WorkbenchRef(RelationshipId),
            blocks[^1].Data.GetProperty("destinationRef").GetString()
        );
    }

    [Fact]
    public void ForDecisions_WhenNothingWaits_SaysSoInsteadOfReturningAnEmptyReply()
    {
        var blocks = ExperienceBlockBuilder.ForDecisions(
            [],
            ChannelCapabilities.Default,
            RelationshipId
        );

        Assert.Equal(new[] { "no-decisions", "workbench-link" }, blocks.Select(item => item.Id));
        Assert.Equal("Nothing is waiting for your decision.", TextOf(blocks[0]));
        Assert.Equal("PUBLIC", blocks[0].Sensitivity);
    }

    [Fact]
    public void ForMonitor_ShowsThreeMetricsOneAlertAndTheFirstLimitation_ThenTheLink()
    {
        var tiles = new[]
        {
            Tile("t1"),
            Tile("status-tile", "STATUS"),
            Tile("t2"),
            Tile("t3"),
            Tile("t4"),
        };

        var blocks = ExperienceBlockBuilder.ForMonitor(
            tiles,
            [Alert("a1"), Alert("a2")],
            ["Owner data is late.", "Second limitation."],
            Caps(Rich),
            RelationshipId
        );

        Assert.Equal(
            new[]
            {
                "metric-t1",
                "metric-t2",
                "metric-t3",
                "alert-a1",
                "limitation",
                "workbench-link",
            },
            blocks.Select(item => item.Id)
        );
        Assert.Equal("CUSTOMER", blocks[3].Sensitivity);
        Assert.Equal("Owner data is late.", TextOf(blocks[3]));
        Assert.Equal("PUBLIC", blocks[4].Sensitivity);
        Assert.Equal("Owner data is late.", TextOf(blocks[4]));
    }

    [Fact]
    public void ForMonitor_WithNothingToReport_SaysNoMeasuresAreReportedYet()
    {
        var blocks = ExperienceBlockBuilder.ForMonitor(
            [Tile("only-status", "STATUS")],
            [],
            [],
            ChannelCapabilities.Default,
            RelationshipId
        );

        Assert.Equal(new[] { "no-monitor", "workbench-link" }, blocks.Select(item => item.Id));
        Assert.Equal("No measures are reported yet.", TextOf(blocks[0]));
    }

    [Fact]
    public void ForMonitor_ForAClientWithoutMetricBlocks_DegradesEachMetricToText()
    {
        var blocks = ExperienceBlockBuilder.ForMonitor(
            [Tile("t1", unit: "")],
            [],
            [],
            ChannelCapabilities.Default,
            RelationshipId
        );

        var metric = blocks[0];
        Assert.Equal("TEXT", metric.Type);
        Assert.Equal("metric-t1.1", metric.Id);
        Assert.Equal("Reach t1: 120.", TextOf(metric));
    }

    [Fact]
    public void Build_OnARichClient_KeepsTheStatusFirstTheLinkLastAndAtMostSixBlocks()
    {
        var decisions = new[] { Decision(), Decision(), Decision() };
        var starters = new[] { GoalType("g1"), GoalType("g2"), GoalType("g3"), GoalType("g4") };

        var blocks = ExperienceBlockBuilder.Build(
            Input(
                decisions: decisions,
                starters: starters,
                tiles: [Tile("t1")],
                limitations: ["Late."]
            ),
            Caps(Rich)
        );

        Assert.Equal(
            new[]
            {
                "status",
                $"decision-{decisions[0].DecisionId:D}",
                $"decision-{decisions[1].DecisionId:D}",
                "goal-form-g1",
                "goal-form-g2",
                "workbench-link",
            },
            blocks.Select(item => item.Id)
        );
    }

    [Fact]
    public void Build_ShowsMetricPlanAndFirstLimitation_WhenThereIsRoomForThem()
    {
        var plan = new WorkbenchPlan("1.0", "plan-3", "AGREED", Guid.NewGuid(), [], [], []);

        var blocks = ExperienceBlockBuilder.Build(
            Input(tiles: [Tile("s", "STATUS"), Tile("t1")], plan: plan, limitations: ["Late."]),
            Caps(Rich)
        );

        Assert.Equal(
            new[] { "status", "metric-t1", "plan", "limitation", "workbench-link" },
            blocks.Select(item => item.Id)
        );
    }

    [Fact]
    public void Build_ForAClientWithoutDecisionBlocks_ShowsOneDecisionAsItsFallbackOnly()
    {
        var decisions = new[] { Decision(), Decision() };

        var blocks = ExperienceBlockBuilder.Build(
            Input(decisions: decisions),
            ChannelCapabilities.Default
        );

        Assert.Single(blocks, block => block.Type == "CHOICES");
        Assert.Contains(blocks, block => block.Id == $"decision-{decisions[0].DecisionId:D}.2");
        Assert.DoesNotContain(
            blocks,
            block => block.Id.StartsWith($"decision-{decisions[1].DecisionId:D}")
        );
    }

    [Fact]
    public void Build_ForAStewardOrBeneficiary_NeverOffersADecisionOrGoalForm()
    {
        var steward = ExperienceBlockBuilder.Build(
            Input(
                audience: WorkbenchAudiences.Steward,
                decisions: [Decision()],
                starters: [GoalType("g1")]
            ),
            Caps(Rich)
        );

        Assert.Equal(new[] { "status", "workbench-link" }, steward.Select(item => item.Id));
    }

    [Theory]
    [InlineData("OPERATIONS", "ACTIVE", "IN_PROGRESS")]
    [InlineData("OPERATIONS", "ELIGIBLE", "READY")]
    [InlineData("OPERATIONS", "PAUSED", "DEFERRED")]
    [InlineData("OPERATIONS", "BLOCKED", "BLOCKED")]
    [InlineData("OPERATIONS", "REASSESSMENT_REQUIRED", "WAITING_ON_CUSTOMER")]
    [InlineData("OPERATIONS", "TERMINATED", "CANCELLED")]
    [InlineData("OPERATIONS", "SOMETHING_NEW", "PROPOSED")]
    [InlineData("PLANNING", "AGREED", "COMPLETED")]
    [InlineData("PLANNING", "READY_FOR_REVIEW", "WAITING_ON_CUSTOMER")]
    [InlineData("PLANNING", "BLOCKED", "BLOCKED")]
    [InlineData("PLANNING", "NO_PLAN", "PROPOSED")]
    [InlineData("PLANNING", "STALE_REASSESSMENT_REQUIRED", "WAITING_ON_CUSTOMER")]
    [InlineData("PLANNING", "DRAFTING", "IN_PROGRESS")]
    [InlineData("INDUCTION", "READY", "COMPLETED")]
    [InlineData("INDUCTION", "READY_WITH_DEFERRED_ITEMS", "COMPLETED")]
    [InlineData("INDUCTION", "BLOCKED", "BLOCKED")]
    [InlineData("INDUCTION", "NOT_STARTED", "PROPOSED")]
    [InlineData("INDUCTION", "STALE_REASSESSMENT_REQUIRED", "WAITING_ON_CUSTOMER")]
    [InlineData("INDUCTION", "IN_PROGRESS_SOMEHOW", "IN_PROGRESS")]
    public void PhaseState_ReadsTheReadinessOfTheCurrentPhaseOnly(
        string phase,
        string readiness,
        string expected
    ) =>
        Assert.Equal(
            expected,
            ExperienceBlockBuilder.PhaseState(phase, Readiness(phase, readiness))
        );

    [Fact]
    public void StatusBlock_NamesThePhaseItsStateAndTheNextActionInCustomerWording()
    {
        var input = Input(
            phase: "PLANNING",
            next: new WorkbenchRecommendedAction("accept", "Review the plan", "It is ready.")
        ) with
        {
            Readiness = Readiness("PLANNING", "READY_FOR_REVIEW"),
        };

        var block = ExperienceBlockBuilder.StatusBlock(input, ChannelCapabilities.Default);

        Assert.Equal("Planning", block.Label);
        Assert.Equal(
            "Planning: waiting on customer. Next: Review the plan. It is ready.",
            block.Fallback[0].Data.GetProperty("text").GetString()
        );
        Assert.Equal("phase:PLANNING", block.Data.GetProperty("itemRef").GetString());
        Assert.Equal("WAITING_ON_CUSTOMER", block.Data.GetProperty("state").GetString());
        Assert.Null(block.Spoken);
    }

    [Fact]
    public void StatusBlock_ForAVoiceClient_CarriesTheSameLineAsSpokenText()
    {
        var voice = new ChannelCapabilities("WEB", true, ChannelCapabilities.Default.Blocks);

        var block = ExperienceBlockBuilder.StatusBlock(Input(), voice);

        Assert.Equal("Operations: in progress.", block.Spoken);
        Assert.Equal(block.Spoken, block.Fallback[0].Data.GetProperty("text").GetString());
    }

    [Fact]
    public void DecisionBlock_StatesCostAndExpiryOnlyWhenTheOwnerReportedThem()
    {
        var costed = ExperienceBlockBuilder.DecisionBlock(
            Decision(expires: At),
            ChannelCapabilities.Default
        );
        var free = ExperienceBlockBuilder.DecisionBlock(
            Decision(cost: null),
            ChannelCapabilities.Default
        );

        Assert.Equal(
            "Start the agreed plan. Authority: Customer approval. Cost: 5 content drafts.",
            costed.Fallback[0].Data.GetProperty("text").GetString()
        );
        Assert.Equal(At, costed.Data.GetProperty("expiresAt").GetDateTimeOffset());
        Assert.Equal("SENSITIVE", costed.Sensitivity);
        Assert.Equal(
            "Start the agreed plan. Authority: Customer approval.",
            free.Fallback[0].Data.GetProperty("text").GetString()
        );
        Assert.False(free.Data.TryGetProperty("cost", out _));
        Assert.False(free.Data.TryGetProperty("expiresAt", out _));
    }

    [Fact]
    public void MetricBlock_OmitsAnUndeclaredTargetAndTrend_AndDropsAnEmptyUnitFromTheLine()
    {
        var block = ExperienceBlockBuilder.MetricBlock(
            Tile("t1", unit: "", target: null, trend: null),
            new ChannelCapabilities("WEB", true, ChannelCapabilities.Default.Blocks)
        );
        var withUnit = ExperienceBlockBuilder.MetricBlock(Tile("t2"), ChannelCapabilities.Default);

        Assert.Equal("Reach t1: 120.", block.Spoken);
        Assert.False(block.Data.TryGetProperty("target", out _));
        Assert.False(block.Data.TryGetProperty("trend", out _));
        Assert.Equal("reach", block.Data.GetProperty("measureId").GetString());
        Assert.Equal(
            "Reach t2: 120 people.",
            withUnit.Fallback[0].Data.GetProperty("text").GetString()
        );
        Assert.Equal("200", withUnit.Data.GetProperty("target").GetString());
        Assert.Equal("Reach t2", withUnit.Label);
    }

    [Fact]
    public void PlanBlock_ShowsFiveMilestonesAndFiveCalendarEntriesWithClippedWording()
    {
        var milestones = Enumerable
            .Range(1, 7)
            .Select(index => new WorkbenchMilestone(
                $"m{index}",
                "LAUNCH",
                index == 1 ? new string('T', 200) : $"Step {index}",
                new string('D', 300),
                "PROPOSED"
            ))
            .ToArray();
        var calendar = Enumerable
            .Range(1, 7)
            .Select(index => new WorkbenchCalendarEntry($"2030-03-0{index}", $"Day {index}"))
            .ToArray();
        var plan = new WorkbenchPlan(
            "1.0",
            "plan-3",
            "STALE_REASSESSMENT_REQUIRED",
            Guid.NewGuid(),
            milestones,
            calendar,
            []
        );

        var block = ExperienceBlockBuilder.PlanBlock(plan, ChannelCapabilities.Default);

        var shown = block.Data.GetProperty("milestones").EnumerateArray().ToArray();
        Assert.Equal(5, shown.Length);
        Assert.Equal(120, shown[0].GetProperty("title").GetString()!.Length);
        Assert.EndsWith("…", shown[0].GetProperty("title").GetString());
        Assert.Equal(240, shown[0].GetProperty("dueMeaning").GetString()!.Length);
        Assert.Equal(5, block.Data.GetProperty("calendar").GetArrayLength());
        Assert.Equal("plan-3", block.Data.GetProperty("planVersion").GetString());
        Assert.Equal("Plan", block.Label);
        Assert.StartsWith(
            "Plan plan-3 (stale reassessment required): ",
            block.Fallback[0].Data.GetProperty("text").GetString()
        );
        Assert.Contains(
            "; Step 2; Step 3; Step 4; Step 5.",
            block.Fallback[0].Data.GetProperty("text").GetString()
        );
    }

    [Fact]
    public void PlanBlock_WithoutMilestones_SaysThereAreNoneYet()
    {
        var plan = new WorkbenchPlan("1.0", "plan-1", "PROPOSED", Guid.NewGuid(), [], [], []);

        var block = ExperienceBlockBuilder.PlanBlock(plan, ChannelCapabilities.Default);

        Assert.Equal(
            "Plan plan-1 (proposed): no milestones yet.",
            block.Fallback[0].Data.GetProperty("text").GetString()
        );
        Assert.Equal(0, block.Data.GetProperty("milestones").GetArrayLength());
    }

    [Fact]
    public void GoalFormBlock_UsesTheFirstStarterAsItsTitleAndAtMostTwelveHumanizedFields()
    {
        var parameters = Enumerable.Range(1, 14).Select(index => $"PARAM_{index}").ToArray();

        var block = ExperienceBlockBuilder.GoalFormBlock(
            GoalType("GROW", parameters, ["Grow my reach", "Another"]),
            Caps(Rich)
        );

        Assert.Equal("Grow my reach", block.Label);
        Assert.Equal("goal-form-GROW", block.Id);
        var fields = block.Data.GetProperty("fields").EnumerateArray().ToArray();
        Assert.Equal(12, fields.Length);
        Assert.Equal("PARAM_1", fields[0].GetProperty("fieldId").GetString());
        Assert.Equal("Param 1", fields[0].GetProperty("label").GetString());
        Assert.True(fields[0].GetProperty("required").GetBoolean());
        Assert.Equal(
            "Grow my reach. Open the workbench to set this goal.",
            block.Fallback[0].Data.GetProperty("text").GetString()
        );
    }

    [Fact]
    public void GoalFormBlock_WithoutAStarter_NamesTheGoalTypeInPlainWords()
    {
        var block = ExperienceBlockBuilder.GoalFormBlock(
            GoalType(new string('X', 80) + "_GOAL"),
            ChannelCapabilities.Default
        );

        Assert.Equal(64, block.Id.Length);
        Assert.EndsWith("…", block.Id);
        Assert.Equal("X" + new string('x', 79) + " goal", block.Label);
    }

    [Fact]
    public void DecisionChoices_ClipLongLabelsAndKeepDistinctDeclineWording()
    {
        var block = ExperienceBlockBuilder.DecisionBlock(
            Decision("Approve the whole quarterly plan", "approve the whole quarterly plan"),
            ChannelCapabilities.Default
        );

        var labels = block
            .Fallback[1]
            .Data.GetProperty("choices")
            .EnumerateArray()
            .Select(choice => choice.GetProperty("label").GetString()!)
            .ToArray();

        Assert.Equal(
            new[]
            {
                "Approve the whole q…",
                ExperienceBlockBuilder.DeclineLabel,
                ExperienceBlockBuilder.DeferLabel,
            },
            labels
        );
    }

    [Fact]
    public void Negotiate_KeepsOnlySupportedFallbackBlocks_AndSpeaksOnlyThroughTheFirstFallback()
    {
        var voice = new ChannelCapabilities(
            "WEB",
            true,
            new Dictionary<string, int> { ["CHOICES"] = 1, ["LINK"] = 1 }
        );
        var block = ExperienceBlockBuilder.DecisionBlock(
            Decision(),
            new ChannelCapabilities("WEB", true, ChannelCapabilities.Default.Blocks)
        );

        var result = ExperienceBlockBuilder.Negotiate([block], voice);

        var only = Assert.Single(result);
        Assert.Equal("CHOICES", only.Type);
        Assert.Equal($"{block.Id}.2", only.Id);
        Assert.Equal("SENSITIVE", only.Sensitivity);
        Assert.Null(only.Spoken);
        Assert.Empty(only.Fallback);
    }

    [Fact]
    public void Negotiate_SpeaksTheFirstFallbackAndKeepsTheSensitivityOfTheReplacedBlock()
    {
        var block = ExperienceBlockBuilder.DecisionBlock(
            Decision(),
            new ChannelCapabilities("WEB", true, ChannelCapabilities.Default.Blocks)
        );

        var result = ExperienceBlockBuilder.Negotiate(
            [block],
            new ChannelCapabilities("WEB", true, ChannelCapabilities.Default.Blocks)
        );

        Assert.Equal(new[] { $"{block.Id}.1", $"{block.Id}.2" }, result.Select(item => item.Id));
        Assert.Equal(block.Spoken, result[0].Spoken);
        Assert.Null(result[1].Spoken);
        Assert.All(result, item => Assert.Equal("SENSITIVE", item.Sensitivity));
    }

    [Fact]
    public void Negotiate_DropsAnUnsupportedBlockThatHasNoFallback()
    {
        var data = JsonSerializer.SerializeToElement(new { text = "x" });
        var bare = new ExperienceBlock("status", "STATUS", 1, "CUSTOMER", data, []);
        var text = new ExperienceBlock("t", "TEXT", 1, "PUBLIC", data, []);

        var result = ExperienceBlockBuilder.Negotiate([bare, text], ChannelCapabilities.Default);

        Assert.Equal("t", Assert.Single(result).Id);
    }

    [Fact]
    public void Negotiate_WithoutALink_KeepsTheFirstSixBlocks_AndMovesAnEarlyLinkToTheEnd()
    {
        var data = JsonSerializer.SerializeToElement(new { text = "x" });
        var texts = Enumerable
            .Range(0, 8)
            .Select(index => new ExperienceBlock($"t{index}", "TEXT", 1, "PUBLIC", data, []))
            .ToArray();

        var withoutLink = ExperienceBlockBuilder.Negotiate(texts, ChannelCapabilities.Default);
        var early = ExperienceBlockBuilder.Negotiate(
            [
                ExperienceBlockBuilder.LinkBlock(RelationshipId, ChannelCapabilities.Default),
                .. texts.Take(2),
            ],
            ChannelCapabilities.Default
        );

        Assert.Equal(texts.Take(6).Select(item => item.Id), withoutLink.Select(item => item.Id));
        Assert.Equal(new[] { "t0", "t1", "workbench-link" }, early.Select(item => item.Id));
    }

    [Fact]
    public void TextBlock_ClipsItsIdAndTextToTheirLimits_AndSpeaksOnlyForVoice()
    {
        var voice = new ChannelCapabilities("WEB", true, ChannelCapabilities.Default.Blocks);

        var block = ExperienceBlockBuilder.TextBlock(
            new string('i', 100),
            new string('w', 2000),
            "PUBLIC",
            voice
        );
        var silent = ExperienceBlockBuilder.TextBlock(
            "a",
            "b",
            "PUBLIC",
            ChannelCapabilities.Default
        );
        var empty = ExperienceBlockBuilder.TextBlock("a", "", "PUBLIC", voice);

        Assert.Equal(64, block.Id.Length);
        Assert.Equal(ExperienceBlockBuilder.MaxText, TextOf(block).Length);
        Assert.Equal(ExperienceBlockBuilder.MaxText, block.Spoken!.Length);
        Assert.Null(silent.Spoken);
        Assert.Null(empty.Spoken);
    }

    [Theory]
    [InlineData("PROFILE_COVERAGE", "Profile coverage")]
    [InlineData("grow-my_reach", "Grow my reach")]
    [InlineData("  spaced  ", "Spaced")]
    [InlineData("___", "___")]
    [InlineData("", "")]
    public void Humanize_TurnsDeclaredIdentifiersIntoCustomerWording(
        string identifier,
        string expected
    ) => Assert.Equal(expected, ExperienceBlockBuilder.Humanize(identifier));

    [Theory]
    [InlineData("  short  ", 10, "short")]
    [InlineData("exactly", 7, "exactly")]
    [InlineData("abcdefghij", 5, "abcd…")]
    [InlineData("abc defgh", 5, "abc…")]
    public void Clip_TrimsAndEndsWithAnEllipsisWithinTheLimit(
        string value,
        int max,
        string expected
    ) => Assert.Equal(expected, ExperienceBlockBuilder.Clip(value, max));

    private static JsonObject Manifest() =>
        JsonNode
            .Parse(
                """
                {
                  "experience": {
                    "contractVersion": "1.2",
                    "goalTypes": [
                      {
                        "goalTypeId": "grow",
                        "parameters": ["audience", "channel"],
                        "measures": [
                          { "measureId": "reach", "unit": "people", "evidenceSource": "analytics", "freshnessSeconds": 3600 },
                          { "measureId": "leads", "unit": "count", "evidenceSource": "crm" }
                        ],
                        "constraints": ["budget"],
                        "starters": ["Grow my reach"]
                      },
                      {
                        "goalTypeId": "retain",
                        "measures": [ { "measureId": "churn", "unit": "percent", "evidenceSource": "billing" } ]
                      }
                    ],
                    "plan": { "milestoneTypes": ["LAUNCH", "REVIEW"], "calendarWindows": ["WEEKLY"] },
                    "operate": {
                      "workItemTypes": ["POST"],
                      "cadence": [
                        { "skillId": "SKILL_A", "trigger": "WEEKLY", "window": "MON" },
                        { "skillId": "SKILL_B", "trigger": "DAILY", "window": "AM" }
                      ],
                      "approvalModes": [
                        { "mode": "AUTO_WITH_REVIEW", "escalation": "OWNER" },
                        { "mode": "CUSTOMER_APPROVAL", "escalation": "NONE" }
                      ]
                    },
                    "monitor": {
                      "tiles": [
                        { "tileId": "t1", "measureId": "reach", "blockType": "METRIC", "audiences": ["customer_owner", "delegate"] }
                      ],
                      "narratives": [
                        { "narrativeId": "n1", "cadence": "WEEKLY", "channels": ["web"], "structure": ["SUMMARY"] }
                      ],
                      "alerts": [
                        { "signal": "late_data", "threshold": "24h", "severity": "HIGH", "channels": ["web", "whatsapp"] }
                      ]
                    },
                    "domainBlocks": [
                      { "blockId": "calendar", "version": 2, "fallbackBlocks": ["TEXT", "LIST"] },
                      { "blockId": "legacy", "fallbackBlocks": ["TEXT"] }
                    ],
                    "components": [
                      {
                        "componentId": "CONTENT_PLAN", "label": "Content plan", "unit": "posts", "kind": "QUOTA",
                        "skillId": "SKILL_A", "countedOn": "RUN", "availability": "AVAILABLE"
                      },
                      {
                        "componentId": "REPORTS", "label": "Reports", "unit": "reports", "kind": "QUOTA",
                        "countedOn": "RUN", "availability": "PLANNED"
                      }
                    ],
                    "audiences": ["customer_owner", "delegate", "beneficiary"],
                    "channelSupport": {
                      "web": ["TEXT", "CHOICES", "LIST", "LINK", "STATUS", "DECISION"],
                      "whatsapp": ["TEXT", "CHOICES", "LIST", "LINK", 7]
                    }
                  }
                }
                """
            )!
            .AsObject();

    private static JsonObject Section(JsonObject manifest) => manifest["experience"]!.AsObject();

    private static ExperienceScanResult Scan(JsonNode manifest) =>
        ExperienceManifestScanner.Scan(JsonDocument.Parse(manifest.ToJsonString()).RootElement);

    [Fact]
    public void Scan_WithANonNumericFreshness_FailsClosedLikeAMissingValue()
    {
        var typed = Manifest();
        typed["experience"]!["goalTypes"]![0]!["measures"]![0]!["freshnessSeconds"] = "soon";
        var missing = Manifest();
        ((JsonObject)missing["experience"]!["goalTypes"]![0]!["measures"]![0]!).Remove(
            "freshnessSeconds"
        );

        Assert.Equal(Scan(missing).ReasonCodes, Scan(typed).ReasonCodes);
        Assert.Equal(Scan(missing).State, Scan(typed).State);
    }

    [Fact]
    public void Scan_WithANonNumericBlockVersion_FailsClosedLikeAMissingValue()
    {
        var typed = Manifest();
        typed["experience"]!["domainBlocks"]![1]!["version"] = "two";
        var missing = Manifest();
        ((JsonObject)missing["experience"]!["domainBlocks"]![1]!).Remove("version");

        Assert.Equal(Scan(missing).ReasonCodes, Scan(typed).ReasonCodes);
        Assert.Equal(Scan(missing).State, Scan(typed).State);
    }

    [Fact]
    public void Scan_ReadsMissingOptionalTextsAsEmptyAndKeepsTheManifestCompatible()
    {
        var manifest = Manifest();
        var section = Section(manifest);
        section["goalTypes"] = JsonNode.Parse(
            """[{ "goalTypeId": "grow", "measures": [{ "measureId": "reach" }] }]"""
        );
        section["operate"] = JsonNode.Parse(
            """{ "cadence": [{ "skillId": "SKILL_A" }], "approvalModes": [{}] }"""
        );
        section["monitor"] = JsonNode.Parse(
            """{ "tiles": [{ "measureId": "reach" }], "narratives": [{}], "alerts": [{}] }"""
        );
        section["components"] = JsonNode.Parse(
            """[{ "componentId": "C1", "label": "One", "skillId": "SKILL_A" }]"""
        );

        var declaration = Scan(manifest).Declaration!;

        Assert.Equal(
            new ExperienceMeasure("reach", string.Empty, string.Empty, 0),
            declaration.GoalTypes[0].Measures[0]
        );
        Assert.Empty(declaration.GoalTypes[0].Parameters);
        Assert.Equal(
            new ExperienceCadence("SKILL_A", string.Empty, string.Empty),
            declaration.Cadence[0]
        );
        Assert.Equal(
            new ExperienceApprovalMode(string.Empty, string.Empty),
            declaration.ApprovalModes[0]
        );
        Assert.Equal(string.Empty, declaration.Tiles[0].TileId);
        Assert.Equal(string.Empty, declaration.Tiles[0].BlockType);
        Assert.Empty(declaration.Tiles[0].Audiences);
        Assert.Equal(string.Empty, declaration.Narratives[0].NarrativeId);
        Assert.Equal(string.Empty, declaration.Narratives[0].Cadence);
        Assert.Empty(declaration.Narratives[0].Channels);
        Assert.Equal(string.Empty, declaration.Alerts[0].Signal);
        Assert.Equal(string.Empty, declaration.Alerts[0].Threshold);
        Assert.Equal(string.Empty, declaration.Alerts[0].Severity);
        Assert.Equal(string.Empty, declaration.Components[0].Unit);
        Assert.Equal(string.Empty, declaration.Components[0].Kind);
        Assert.Equal(string.Empty, declaration.Components[0].CountedOn);
        Assert.Equal(string.Empty, declaration.Components[0].Availability);
        Assert.Equal(string.Empty, declaration.DefaultApprovalMode);
    }

    [Fact]
    public void Scan_ReadsEveryDeclaredSectionIntoTheDeclaration()
    {
        var scan = Scan(Manifest());

        Assert.Equal(ExperienceScanResult.Compatible, scan.State);
        Assert.True(scan.ExperienceCapable);
        Assert.Equal(new[] { "COMPATIBLE" }, scan.ReasonCodes);
        var declaration = scan.Declaration!;
        Assert.Equal("1.2", declaration.ContractVersion);
        var grow = declaration.GoalTypes[0];
        Assert.Equal(new[] { "audience", "channel" }, grow.Parameters);
        Assert.Equal(new[] { "budget" }, grow.Constraints);
        Assert.Equal(new[] { "Grow my reach" }, grow.Starters);
        Assert.Equal(new ExperienceMeasure("reach", "people", "analytics", 3600), grow.Measures[0]);
        Assert.Equal(0, grow.Measures[1].FreshnessSeconds);
        Assert.Equal(
            new ExperienceMeasure("churn", "percent", "billing", 0),
            declaration.GoalTypes[1].Measures[0]
        );
        Assert.Empty(declaration.GoalTypes[1].Parameters);
        Assert.Equal(new[] { "LAUNCH", "REVIEW" }, declaration.MilestoneTypes);
        Assert.Equal(new[] { "WEEKLY" }, declaration.CalendarWindows);
        Assert.Equal(new[] { "POST" }, declaration.WorkItemTypes);
        Assert.Equal(new ExperienceCadence("SKILL_A", "WEEKLY", "MON"), declaration.Cadence[0]);
        Assert.Equal(
            new ExperienceApprovalMode("AUTO_WITH_REVIEW", "OWNER"),
            declaration.ApprovalModes[0]
        );
        Assert.Equal("t1", declaration.Tiles[0].TileId);
        Assert.Equal("METRIC", declaration.Tiles[0].BlockType);
        Assert.Equal(new[] { "customer_owner", "delegate" }, declaration.Tiles[0].Audiences);
        var narrative = declaration.Narratives[0];
        Assert.Equal("n1", narrative.NarrativeId);
        Assert.Equal("WEEKLY", narrative.Cadence);
        Assert.Equal(new[] { "web" }, narrative.Channels);
        Assert.Equal(new[] { "SUMMARY" }, narrative.Structure);
        var alert = declaration.Alerts[0];
        Assert.Equal("late_data", alert.Signal);
        Assert.Equal("24h", alert.Threshold);
        Assert.Equal("HIGH", alert.Severity);
        Assert.Equal(new[] { "web", "whatsapp" }, alert.Channels);
        Assert.Equal(2, declaration.DomainBlocks[0].Version);
        Assert.Equal(0, declaration.DomainBlocks[1].Version);
        var component = declaration.Components[0];
        Assert.Equal("Content plan", component.Label);
        Assert.Equal("posts", component.Unit);
        Assert.Equal("QUOTA", component.Kind);
        Assert.Equal("SKILL_A", component.SkillId);
        Assert.Equal("RUN", component.CountedOn);
        Assert.Equal("AVAILABLE", component.Availability);
        Assert.Null(declaration.Components[1].SkillId);
        Assert.Equal(3, declaration.Audiences.Count);
        Assert.Equal(4, declaration.ChannelSupport["whatsapp"].Count);
    }

    [Fact]
    public void Declaration_LooksUpMeasuresCadenceAndComponentsByTheirDeclaredIds()
    {
        var declaration = Scan(Manifest()).Declaration!;

        Assert.Equal("grow", declaration.GoalTypeForMeasure("leads")?.GoalTypeId);
        Assert.Equal("retain", declaration.GoalTypeForMeasure("churn")?.GoalTypeId);
        Assert.Null(declaration.GoalTypeForMeasure("unknown"));
        Assert.Equal("billing", declaration.Measure("churn")?.EvidenceSource);
        Assert.Null(declaration.Measure("unknown"));
        Assert.Equal("DAILY", declaration.CadenceFor("SKILL_B")?.Trigger);
        Assert.Null(declaration.CadenceFor("SKILL_X"));
        Assert.Equal(new[] { "CONTENT_PLAN" }, declaration.ComponentIdsFor("SKILL_A"));
        Assert.Empty(declaration.ComponentIdsFor("SKILL_X"));
    }

    [Fact]
    public void Declaration_DefaultsToTheFirstDeclaredApprovalModeOrCustomerApproval()
    {
        var declared = Scan(Manifest()).Declaration!;
        var none = declared with { ApprovalModes = [] };

        Assert.Equal("AUTO_WITH_REVIEW", declared.DefaultApprovalMode);
        Assert.Equal("CUSTOMER_APPROVAL", none.DefaultApprovalMode);
    }

    [Fact]
    public void Declaration_BlocksFor_AnswersTheChannelCaseInsensitivelyAndFallsBackToTheV1Set()
    {
        var declaration = Scan(Manifest()).Declaration!;

        Assert.Contains("DECISION", declaration.BlocksFor("WEB"));
        Assert.Equal(new[] { "TEXT", "CHOICES", "LIST", "LINK" }, declaration.BlocksFor("mobile"));
    }

    [Fact]
    public void Scan_WithoutAnExperienceSection_IsNotDeclaredAndNotCapable()
    {
        var manifest = Manifest();
        manifest.Remove("experience");
        var explicitNull = new JsonObject { ["experience"] = null };

        foreach (var scan in new[] { Scan(manifest), Scan(explicitNull), Scan(new JsonArray()) })
        {
            Assert.Equal(ExperienceScanResult.NotDeclared, scan.State);
            Assert.Equal(new[] { "EXPERIENCE_NOT_DECLARED" }, scan.ReasonCodes);
            Assert.Null(scan.Declaration);
            Assert.False(scan.ExperienceCapable);
        }
    }

    [Fact]
    public void Scan_WithAnExperienceSectionThatIsNotAnObject_IsIncompatible()
    {
        var manifest = Manifest();
        manifest["experience"] = "nope";

        var scan = Scan(manifest);

        Assert.Equal(ExperienceScanResult.Incompatible, scan.State);
        Assert.Equal(new[] { "EXPERIENCE_SECTION_INVALID" }, scan.ReasonCodes);
        Assert.False(scan.ExperienceCapable);
    }

    [Theory]
    [InlineData("contractVersion.missing", "EXPERIENCE_CONTRACT_VERSION_UNSUPPORTED")]
    [InlineData("contractVersion.major2", "EXPERIENCE_CONTRACT_VERSION_UNSUPPORTED")]
    [InlineData("goalTypes.none", "EXPERIENCE_SECTION_INVALID")]
    [InlineData("goalTypes.noId", "EXPERIENCE_SECTION_INVALID")]
    [InlineData("goalTypes.noMeasures", "EXPERIENCE_SECTION_INVALID")]
    [InlineData("goalTypes.noMeasureId", "EXPERIENCE_SECTION_INVALID")]
    [InlineData("goalTypes.duplicate", "EXPERIENCE_SECTION_INVALID")]
    [InlineData("plan.missing", "EXPERIENCE_SECTION_INVALID")]
    [InlineData("operate.missing", "EXPERIENCE_SECTION_INVALID")]
    [InlineData("monitor.missing", "EXPERIENCE_SECTION_INVALID")]
    [InlineData("cadence.none", "EXPERIENCE_SECTION_INVALID")]
    [InlineData("approvalModes.none", "EXPERIENCE_SECTION_INVALID")]
    [InlineData("tiles.none", "EXPERIENCE_SECTION_INVALID")]
    [InlineData("components.noLabel", "EXPERIENCE_SECTION_INVALID")]
    [InlineData("components.noId", "EXPERIENCE_SECTION_INVALID")]
    [InlineData("audiences.none", "EXPERIENCE_SECTION_INVALID")]
    [InlineData("components.duplicate", "EXPERIENCE_COMPONENT_DUPLICATE")]
    [InlineData("components.skillUnresolved", "EXPERIENCE_COMPONENT_SKILL_UNRESOLVED")]
    [InlineData("components.availableWithoutSkill", "EXPERIENCE_COMPONENT_THREAD_MISSING")]
    [InlineData("tiles.measureUnresolved", "EXPERIENCE_TILE_MEASURE_UNRESOLVED")]
    [InlineData("audiences.unsupported", "EXPERIENCE_AUDIENCE_UNSUPPORTED")]
    [InlineData("tiles.audienceUnsupported", "EXPERIENCE_AUDIENCE_UNSUPPORTED")]
    [InlineData("channels.noWhatsapp", "EXPERIENCE_CHANNEL_SUPPORT_MISSING")]
    [InlineData("channels.noWeb", "EXPERIENCE_CHANNEL_SUPPORT_MISSING")]
    [InlineData("channels.unknownBlock", "EXPERIENCE_CHANNEL_SUPPORT_MISSING")]
    [InlineData("channels.missingV1Block", "EXPERIENCE_CHANNEL_SUPPORT_MISSING")]
    [InlineData("domainBlocks.noId", "EXPERIENCE_DOMAIN_BLOCK_FALLBACK_MISSING")]
    [InlineData("domainBlocks.noFallback", "EXPERIENCE_DOMAIN_BLOCK_FALLBACK_MISSING")]
    [InlineData("domainBlocks.richFallback", "EXPERIENCE_DOMAIN_BLOCK_FALLBACK_MISSING")]
    public void Scan_FailsClosedWithTheReasonForEachStructuralGap(string gap, string reason)
    {
        var manifest = Manifest();
        var section = Section(manifest);
        switch (gap)
        {
            case "contractVersion.missing":
                section.Remove("contractVersion");
                break;
            case "contractVersion.major2":
                section["contractVersion"] = "2.0";
                break;
            case "goalTypes.none":
                section["goalTypes"] = new JsonArray();
                break;
            case "goalTypes.noId":
                section["goalTypes"]![0]!.AsObject().Remove("goalTypeId");
                break;
            case "goalTypes.noMeasures":
                section["goalTypes"]![0]!["measures"] = new JsonArray();
                break;
            case "goalTypes.noMeasureId":
                section["goalTypes"]![0]!["measures"]![0]!.AsObject().Remove("measureId");
                break;
            case "goalTypes.duplicate":
                section["goalTypes"]![1]!["goalTypeId"] = "grow";
                break;
            case "plan.missing":
                section.Remove("plan");
                break;
            case "operate.missing":
                section.Remove("operate");
                break;
            case "monitor.missing":
                section.Remove("monitor");
                break;
            case "cadence.none":
                section["operate"]!["cadence"] = new JsonArray();
                break;
            case "approvalModes.none":
                section["operate"]!["approvalModes"] = new JsonArray();
                break;
            case "tiles.none":
                section["monitor"]!["tiles"] = new JsonArray();
                break;
            case "components.noLabel":
                section["components"]![0]!.AsObject().Remove("label");
                break;
            case "components.noId":
                section["components"]![0]!.AsObject().Remove("componentId");
                break;
            case "audiences.none":
                section["audiences"] = new JsonArray();
                break;
            case "components.duplicate":
                section["components"]![1]!["componentId"] = "CONTENT_PLAN";
                break;
            case "components.skillUnresolved":
                section["components"]![0]!["skillId"] = "SKILL_X";
                break;
            case "components.availableWithoutSkill":
                section["components"]![1]!["availability"] = "AVAILABLE";
                break;
            case "tiles.measureUnresolved":
                section["monitor"]!["tiles"]![0]!["measureId"] = "unknown";
                break;
            case "audiences.unsupported":
                section["audiences"]!.AsArray().Add("auditor");
                break;
            case "tiles.audienceUnsupported":
                section["monitor"]!["tiles"]![0]!["audiences"]!.AsArray().Add("auditor");
                break;
            case "channels.noWhatsapp":
                section["channelSupport"]!.AsObject().Remove("whatsapp");
                break;
            case "channels.noWeb":
                section["channelSupport"]!.AsObject().Remove("web");
                break;
            case "channels.unknownBlock":
                section["channelSupport"]!["web"]!.AsArray().Add("HOLOGRAM");
                break;
            case "channels.missingV1Block":
                section["channelSupport"]!["web"] = new JsonArray("TEXT", "LINK");
                break;
            case "domainBlocks.noId":
                section["domainBlocks"]![0]!.AsObject().Remove("blockId");
                break;
            case "domainBlocks.noFallback":
                section["domainBlocks"]![0]!["fallbackBlocks"] = new JsonArray();
                break;
            case "domainBlocks.richFallback":
                section["domainBlocks"]![0]!["fallbackBlocks"] = new JsonArray("STATUS");
                break;
            default:
                throw new InvalidOperationException(gap);
        }

        var scan = Scan(manifest);

        Assert.Equal(ExperienceScanResult.Incompatible, scan.State);
        Assert.Contains(reason, scan.ReasonCodes);
        Assert.Null(scan.Declaration);
        Assert.False(scan.ExperienceCapable);
    }

    [Fact]
    public void Scan_IgnoresEntriesOfTheWrongJsonKind_ButStillRequiresWhatItNeeds()
    {
        var manifest = Manifest();
        var section = Section(manifest);
        section["goalTypes"]!.AsArray().Add("not an object");
        section["goalTypes"]![0]!["parameters"]!.AsArray().Add(5);
        section["goalTypes"]![0]!["constraints"] = "not an array";
        section["components"]![0]!["label"] = "   ";

        var scan = Scan(manifest);

        Assert.Equal(ExperienceScanResult.Incompatible, scan.State);
        Assert.Contains("EXPERIENCE_SECTION_INVALID", scan.ReasonCodes);
        section["components"]![0]!["label"] = "Content plan";
        var repaired = Scan(manifest).Declaration!;
        Assert.Equal(2, repaired.GoalTypes.Count);
        Assert.Equal(new[] { "audience", "channel" }, repaired.GoalTypes[0].Parameters);
        Assert.Empty(repaired.GoalTypes[0].Constraints);
    }

    [Fact]
    public void Scan_ReportsEveryGapAtOnceInSortedOrder()
    {
        var manifest = Manifest();
        var section = Section(manifest);
        section["components"]![1]!["componentId"] = "CONTENT_PLAN";
        section["audiences"]!.AsArray().Add("auditor");

        var scan = Scan(manifest);

        Assert.Equal(
            new[] { "EXPERIENCE_AUDIENCE_UNSUPPORTED", "EXPERIENCE_COMPONENT_DUPLICATE" },
            scan.ReasonCodes
        );
    }
}
