// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01, C6-02
// Constitutional basis: C-001, C-005, C-023, C-026, C-059, C-063, ADR-051

using System.Text.Json;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

/// <summary>
/// The workbench wire contract: every record names its properties as the OpenAPI does, leaves optional members out
/// when they are null, and survives a round trip without loss.
/// </summary>
public sealed class WorkbenchSurfaceModelsTests
{
    private static readonly JsonSerializerOptions Web = new(JsonSerializerDefaults.Web);
    private static readonly Guid Id = Guid.Parse("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee");
    private static readonly DateTimeOffset At = new(2030, 3, 4, 5, 6, 7, TimeSpan.Zero);

    private static string Serialize<T>(T value) => JsonSerializer.Serialize(value, Web);

    private static string[] Names(string json)
    {
        using var document = JsonDocument.Parse(json);
        return document.RootElement.EnumerateObject().Select(item => item.Name).Order().ToArray();
    }

    private static void AssertContract<T>(T full, T sparse, params string[] omittedWhenNull)
    {
        var fullJson = Serialize(full);
        var sparseJson = Serialize(sparse);

        var fullNames = Names(fullJson);
        var sparseNames = Names(sparseJson);

        Assert.Equal(omittedWhenNull.Order(), fullNames.Except(sparseNames).Order());
        Assert.Empty(sparseNames.Except(fullNames));
        Assert.Equal(fullJson, Serialize(JsonSerializer.Deserialize<T>(fullJson, Web)));
        Assert.Equal(sparseJson, Serialize(JsonSerializer.Deserialize<T>(sparseJson, Web)));
    }

    private static JsonElement Data(string json) => JsonDocument.Parse(json).RootElement.Clone();

    private static readonly WorkbenchDecision Decision = new(
        Id,
        "v1",
        "Start the plan.",
        "Customer approval",
        "5 drafts",
        "Approve",
        "Not now",
        At,
        "plan:1",
        "Platform",
        "CURRENT"
    );

    private static readonly WorkbenchTile Tile = new(
        "t1",
        "reach",
        "Reach",
        "120",
        "people",
        "200",
        "UP",
        "last 7 days",
        "CURRENT",
        "Platform",
        "METRIC"
    );

    private static readonly WorkbenchComponentBalance Balance = new(
        "CONTENT_PLAN",
        "Content plan",
        3,
        5,
        At
    );

    private static readonly WorkbenchAlert Alert = new(
        "a1",
        "late_data",
        "HIGH",
        "Owner data is late.",
        At,
        "STALE"
    );

    private static readonly WorkbenchGoalSummary GoalSummary = new(
        Id,
        "grow",
        "Grow my reach",
        "PROPOSED",
        2,
        At
    );

    private static readonly ExperienceBlock Block = new(
        "status",
        "STATUS",
        1,
        "CUSTOMER",
        Data("""{"state":"READY"}"""),
        [new ExperienceFallbackBlock("TEXT", Data("""{"text":"Ready."}"""))],
        "Ready.",
        "Status"
    );

    [Theory]
    [InlineData(RelationshipParticipantRole.Employer, WorkbenchAudiences.CustomerOwner)]
    [InlineData(RelationshipParticipantRole.RelationshipManager, WorkbenchAudiences.Delegate)]
    [InlineData(RelationshipParticipantRole.ConstitutionalAuthority, WorkbenchAudiences.Steward)]
    [InlineData(RelationshipParticipantRole.Evaluator, WorkbenchAudiences.Beneficiary)]
    [InlineData(RelationshipParticipantRole.OutcomeOwner, WorkbenchAudiences.Beneficiary)]
    public void FromRole_MapsEveryRelationshipRoleToItsAudience(
        RelationshipParticipantRole role,
        string audience
    )
    {
        Assert.Equal(audience, WorkbenchAudiences.FromRole(role));
        Assert.Contains(audience, WorkbenchAudiences.All);
    }

    [Fact]
    public void Audiences_OnlyTheOwnerManagesSpend_AndOnlyOwnerAndDelegateDecide()
    {
        Assert.Equal(4, WorkbenchAudiences.All.Count);
        Assert.Equal(
            new[] { WorkbenchAudiences.CustomerOwner },
            WorkbenchAudiences.All.Where(WorkbenchAudiences.MayManageSpend)
        );
        Assert.Equal(
            new[] { WorkbenchAudiences.CustomerOwner, WorkbenchAudiences.Delegate }.Order(),
            WorkbenchAudiences.All.Where(WorkbenchAudiences.MayDecide).Order()
        );
        Assert.False(WorkbenchAudiences.MayDecide("unknown"));
    }

    [Fact]
    public void MayResolve_IsLimitedToTheEmployerAndTheEvaluator()
    {
        var allowed = Enum.GetValues<RelationshipParticipantRole>()
            .Where(WorkbenchAudiences.MayResolve);

        Assert.Equal(
            new[]
            {
                RelationshipParticipantRole.Evaluator,
                RelationshipParticipantRole.Employer,
            }.Order(),
            allowed.Order()
        );
    }

    [Fact]
    public void WorkbenchException_CarriesItsStatusCodeAndDetail_AndUsesTheCodeAsItsMessage()
    {
        var failure = new WorkbenchException(
            409,
            WorkbenchProblemCodes.VersionConflict,
            "The version moved."
        );
        var bare = new WorkbenchException(503, WorkbenchProblemCodes.Unavailable);

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.VersionConflict, failure.Code);
        Assert.Equal(WorkbenchProblemCodes.VersionConflict, failure.Message);
        Assert.Equal("The version moved.", failure.Detail);
        Assert.Null(bare.Detail);
    }

    [Fact]
    public void Problem_WritesItsDetailOnlyWhenThereIsOne()
    {
        AssertContract(
            new WorkbenchProblem("urn:t", "Title", 400, "CODE", "corr", "Why."),
            new WorkbenchProblem("urn:t", "Title", 400, "CODE", "corr"),
            "detail"
        );
    }

    [Fact]
    public void Decision_OmitsCostExpiryAndItemRefWhenAbsent()
    {
        AssertContract(
            Decision,
            Decision with
            {
                Cost = null,
                ExpiresAt = null,
                ItemRef = null,
            },
            "cost",
            "expiresAt",
            "itemRef"
        );
    }

    [Fact]
    public void Tile_OmitsTargetTrendAndBasisWhenAbsent()
    {
        AssertContract(
            Tile,
            Tile with
            {
                Target = null,
                Trend = null,
                Basis = null,
            },
            "target",
            "trend",
            "basis"
        );
    }

    [Fact]
    public void ComponentBalanceAlertAndReadiness_RoundTripWithoutOptionalMembers()
    {
        AssertContract(Balance, Balance);
        AssertContract(Alert, Alert);
        var readiness = new WorkbenchReadiness("READY", "AGREED", "ACTIVE", "NOT_STARTED");
        AssertContract(readiness, readiness);
        var action = new WorkbenchRecommendedAction("resolve_decision", "Review", "One waits.");
        AssertContract(action, action);
    }

    [Fact]
    public void AvailableCommand_WritesTheDisabledReasonOnlyWhenDisabled()
    {
        AssertContract(
            new WorkbenchAvailableCommand("stop", "Stop", false, "Already stopped."),
            new WorkbenchAvailableCommand("stop", "Stop", true),
            "disabledReason"
        );
    }

    [Fact]
    public void ExperienceBlock_KeepsItsDataAndFallbackAndOmitsSpokenAndLabelWhenAbsent()
    {
        AssertContract(Block, Block with { Spoken = null, Label = null }, "spoken", "label");

        var parsed = JsonSerializer.Deserialize<ExperienceBlock>(Serialize(Block), Web)!;

        Assert.Equal("READY", parsed.Data.GetProperty("state").GetString());
        var fallback = Assert.Single(parsed.Fallback);
        Assert.Equal("TEXT", fallback.Type);
        Assert.Equal("Ready.", fallback.Data.GetProperty("text").GetString());
    }

    [Fact]
    public void Projection_OmitsGoalPlanComponentsAndRecommendationWhenAbsent()
    {
        var full = new WorkbenchProjection(
            "1.0",
            Id,
            WorkbenchAudiences.CustomerOwner,
            "OPERATIONS",
            new WorkbenchReadiness("READY", "AGREED", "ACTIVE", "NOT_STARTED"),
            Id,
            "plan-3",
            [Decision],
            [Tile],
            [Balance],
            [Alert],
            "CURRENT",
            "CURRENT",
            ["Owner data is late."],
            new WorkbenchRecommendedAction("resolve_decision", "Review", "One waits."),
            [new WorkbenchAvailableCommand("stop", "Stop", true)],
            [Block]
        );

        AssertContract(
            full,
            full with
            {
                CurrentGoalRef = null,
                CurrentPlanVersion = null,
                Components = null,
                RecommendedNextAction = null,
            },
            "currentGoalRef",
            "currentPlanVersion",
            "components",
            "recommendedNextAction"
        );
        var parsed = JsonSerializer.Deserialize<WorkbenchProjection>(Serialize(full), Web)!;
        Assert.Equal(Id, parsed.CurrentGoalRef);
        Assert.Equal("plan-3", parsed.CurrentPlanVersion);
        Assert.Equal(3, Assert.Single(parsed.Components!).Remaining);
        Assert.Equal("resolve_decision", parsed.RecommendedNextAction!.CommandId);
    }

    [Fact]
    public void CommandReceipt_AndCapabilityResult_OmitOptionalMembersWhenAbsent()
    {
        AssertContract(
            new WorkbenchCommandReceipt(
                "1.0",
                Id,
                "ACCEPTED",
                "goal-1",
                "relationship-2",
                true,
                "c"
            ),
            new WorkbenchCommandReceipt("1.0", Id, "ACCEPTED", null, "relationship-2", false, "c"),
            "resourceRef"
        );
        AssertContract(
            new WorkbenchCapabilityCommandResult("1.0", "APPLIED", Id, "Done.", "c"),
            new WorkbenchCapabilityCommandResult("1.0", "APPLIED", null, null, "c"),
            "operationRef",
            "message"
        );
    }

    [Fact]
    public void Lists_WriteTheNextCursorOnlyWhenThereIsAnotherPage()
    {
        AssertContract(
            new WorkbenchGoalList("1.0", [GoalSummary], "o1.MQ"),
            new WorkbenchGoalList("1.0", [GoalSummary]),
            "nextCursor"
        );
        var version = new WorkbenchGoalVersion(
            1,
            At,
            "Customer",
            "Reworded",
            new Dictionary<string, string> { ["audience"] = "locals" }
        );
        AssertContract(
            new WorkbenchGoalVersionList("1.0", [version], "o1.MQ"),
            new WorkbenchGoalVersionList("1.0", [version]),
            "nextCursor"
        );
        var item = new WorkbenchWorkItem(
            "item:1",
            "POST",
            "SKILL_A",
            "Write a post",
            "IN_PROGRESS",
            "Agent",
            "CURRENT",
            At
        );
        AssertContract(
            new WorkbenchWorkItemList("1.0", [item], "o1.MQ"),
            new WorkbenchWorkItemList("1.0", [item]),
            "nextCursor"
        );
        AssertContract(
            new WorkbenchDecisionList("1.0", [Decision], [Block], "o1.MQ"),
            new WorkbenchDecisionList("1.0", [Decision], [Block]),
            "nextCursor"
        );
        var narrative = new WorkbenchNarrative(
            "n1",
            "Week 12",
            At,
            [new WorkbenchNarrativePart("SUMMARY", "A good week.")],
            "CURRENT"
        );
        AssertContract(
            new WorkbenchNarrativeList("1.0", [narrative], "o1.MQ"),
            new WorkbenchNarrativeList("1.0", [narrative]),
            "nextCursor"
        );
        var evidence = new WorkbenchEvidenceEntry("e1", "REPORT", "Summary", At, "CURRENT");
        AssertContract(
            new WorkbenchEvidenceList("1.0", "AVAILABLE", [evidence], "o1.MQ"),
            new WorkbenchEvidenceList("1.0", "AVAILABLE", [evidence]),
            "nextCursor"
        );
    }

    [Fact]
    public void GoalAndItsMeasuresAndVersions_OmitUndeclaredTargetsBaselinesAndReasons()
    {
        var measure = new WorkbenchGoalMeasure("reach", "people", "200", "100", "CURRENT");
        AssertContract(
            measure,
            measure with
            {
                Target = null,
                Baseline = null,
            },
            "target",
            "baseline"
        );
        var goal = new WorkbenchGoal(
            "1.0",
            GoalSummary,
            new Dictionary<string, string> { ["audience"] = "locals" },
            [measure],
            ["budget"]
        );
        AssertContract(goal, goal);
        var version = new WorkbenchGoalVersion(
            1,
            At,
            "Customer",
            "Reworded",
            new Dictionary<string, string>()
        );
        AssertContract(version, version with { Reason = null }, "reason");
        Assert.Equal(
            "locals",
            JsonSerializer.Deserialize<WorkbenchGoal>(Serialize(goal), Web)!.Parameters["audience"]
        );
    }

    [Fact]
    public void PlanAndCapabilities_RoundTrip_AndOmitUnstatedMeanings()
    {
        var plan = new WorkbenchPlan(
            "1.0",
            "plan-3",
            "AGREED",
            Id,
            [new WorkbenchMilestone("m1", "LAUNCH", "Launch", "By the first Friday", "PROPOSED")],
            [new WorkbenchCalendarEntry("2030-03-04", "Kick-off")],
            ["Estimates only."]
        );
        AssertContract(plan, plan);
        var capability = new WorkbenchCapability(
            "SKILL_A",
            "Posting",
            "AVAILABLE",
            "ACTIVE",
            "CUSTOMER_APPROVAL",
            "Next Monday",
            ["CONTENT_PLAN"],
            "Limited to 5 posts."
        );
        AssertContract(
            capability,
            capability with
            {
                NextRunMeaning = null,
                Limitation = null,
            },
            "nextRunMeaning",
            "limitation"
        );
        AssertContract(
            new WorkbenchCapabilityList("1.0", [capability]),
            new WorkbenchCapabilityList("1.0", [capability])
        );
    }

    [Fact]
    public void WorkItem_OmitsTheSkillWhenNoSkillOwnsIt()
    {
        var item = new WorkbenchWorkItem(
            "item:1",
            "POST",
            "SKILL_A",
            "Write a post",
            "IN_PROGRESS",
            "Agent",
            "CURRENT",
            At
        );

        AssertContract(item, item with { SkillId = null }, "skillId");
    }

    [Fact]
    public void MonitorWalletTopupAndHandoff_RoundTrip()
    {
        var monitor = new WorkbenchMonitor("1.0", [Tile], [Alert], "CURRENT", ["Late."], [Block]);
        AssertContract(monitor, monitor);
        var wallet = new WorkbenchWallet("1.0", Id, At, [Balance], false, true);
        AssertContract(wallet, wallet);
        var handoff = new WorkbenchHandoff("1.0", Id, "handoff:abc", At, true);
        AssertContract(handoff, handoff);
        var topup = new WorkbenchTopupReceipt(
            "1.0",
            Id,
            "ACCEPTED",
            "CONTENT_PLAN",
            2,
            11800,
            10000,
            1800,
            "GST_INCLUSIVE",
            "checkout:1",
            "c"
        );
        AssertContract(topup, topup with { CheckoutHandoffRef = null }, "checkoutHandoffRef");
        Assert.Equal(
            1800,
            JsonSerializer.Deserialize<WorkbenchTopupReceipt>(Serialize(topup), Web)!.GstPaise
        );
    }

    [Fact]
    public void HandoffConsumption_OmitsTheContextRefWhenNoneWasGiven()
    {
        AssertContract(
            new WorkbenchHandoffConsumption("1.0", "WEB_WORKBENCH", "goal:1"),
            new WorkbenchHandoffConsumption("1.0", "WEB_WORKBENCH", null),
            "contextRef"
        );
        var request = new ConsumeWorkbenchHandoffRequest("1.0", "handoff:abc");
        AssertContract(request, request);
    }

    [Fact]
    public void SubscriptionReceipt_OmitsFeeFiguresThatDoNotApplyToTheChange()
    {
        var full = new SubscriptionChangeReceipt(
            "1.0",
            Id,
            "UPGRADE",
            "ACCEPTED",
            At,
            1500,
            700,
            "GST_INCLUSIVE",
            "Waiting for the account owner.",
            "c"
        );

        AssertContract(
            full,
            full with
            {
                ProratedFeeDifferencePaise = null,
                RefundFeePaise = null,
                BlockedReason = null,
            },
            "proratedFeeDifferencePaise",
            "refundFeePaise",
            "blockedReason"
        );
    }

    [Fact]
    public void GoalRequests_TakeTheirOptionalMembersFromAbsentJsonProperties()
    {
        var create = JsonSerializer.Deserialize<CreateWorkbenchGoalRequest>(
            """{"schemaVersion":"1.0","expectedVersion":"relationship-1","goalTypeId":"grow","title":"Grow","parameters":{"audience":"locals"}}""",
            Web
        )!;
        var revise = JsonSerializer.Deserialize<ReviseWorkbenchGoalRequest>(
            """{"schemaVersion":"1.0","expectedVersion":"goal-2","parameters":{},"reason":"Wider"}""",
            Web
        )!;

        Assert.Null(create.StarterRef);
        Assert.Equal("locals", create.Parameters["audience"]);
        Assert.Null(revise.Title);
        Assert.Equal("Wider", revise.Reason);
        Assert.Equal(
            "starter-1",
            JsonSerializer
                .Deserialize<CreateWorkbenchGoalRequest>(
                    Serialize(create with { StarterRef = "starter-1" }),
                    Web
                )!
                .StarterRef
        );
    }

    [Fact]
    public void PlanRequests_TakeMilestonesAndOptionalCalendarWindows()
    {
        var propose = JsonSerializer.Deserialize<ProposeWorkbenchPlanRequest>(
            $$$"""{"schemaVersion":"1.0","expectedVersion":"relationship-1","goalId":"{{{Id}}}","milestones":[{"milestoneTypeId":"LAUNCH","title":"Launch"},{"milestoneTypeId":"REVIEW","title":"Review","dueDate":"2030-04-01"}]}""",
            Web
        )!;
        var accept = JsonSerializer.Deserialize<AcceptWorkbenchPlanRequest>(
            """{"schemaVersion":"1.0","expectedVersion":"plan-3","acknowledgedLimitations":true}""",
            Web
        )!;

        Assert.Equal(Id, propose.GoalId);
        Assert.Null(propose.CalendarWindows);
        Assert.Null(propose.Milestones[0].DueDate);
        Assert.Equal("2030-04-01", propose.Milestones[1].DueDate);
        Assert.True(accept.AcknowledgedLimitations);
    }

    [Fact]
    public void CommandRequests_ReadOptionalMembersAsNullWhenTheClientOmitsThem()
    {
        var capability = JsonSerializer.Deserialize<WorkbenchCapabilityCommandRequest>(
            """{"schemaVersion":"1.0","expectedVersion":"relationship-1","command":"PAUSE"}""",
            Web
        )!;
        var resolve = JsonSerializer.Deserialize<ResolveWorkbenchDecisionRequest>(
            """{"schemaVersion":"1.0","expectedVersion":"relationship-1","resolution":"APPROVE","note":"Go."}""",
            Web
        )!;
        var control = JsonSerializer.Deserialize<WorkbenchControlRequest>(
            """{"schemaVersion":"1.0","expectedVersion":"relationship-1"}""",
            Web
        )!;
        var handoff = JsonSerializer.Deserialize<CreateWorkbenchHandoffRequest>(
            """{"schemaVersion":"1.0","expectedVersion":"relationship-1","purpose":"WEB_WORKBENCH"}""",
            Web
        )!;
        var topup = JsonSerializer.Deserialize<CreateWorkbenchTopupRequest>(
            """{"schemaVersion":"1.0","expectedVersion":"relationship-1","componentId":"CONTENT_PLAN","quantity":2}""",
            Web
        )!;

        Assert.Null(capability.ApprovalMode);
        Assert.Equal("Go.", resolve.Note);
        Assert.Null(control.Reason);
        Assert.Null(handoff.ContextRef);
        Assert.Equal(2, topup.Quantity);
    }

    [Fact]
    public void ExportRequest_ReadsItsScopeAndPeriodWhenGiven()
    {
        var period = JsonSerializer.Deserialize<ExportWorkbenchEvidenceRequest>(
            """{"schemaVersion":"1.0","expectedVersion":"relationship-1","scope":"PERIOD","format":"PDF","periodFrom":"2030-01-01","periodTo":"2030-01-31"}""",
            Web
        )!;
        var goal = JsonSerializer.Deserialize<ExportWorkbenchEvidenceRequest>(
            """{"schemaVersion":"1.0","expectedVersion":"relationship-1","scope":"GOAL","format":"JSON","scopeRef":"goal:1"}""",
            Web
        )!;

        Assert.Equal("2030-01-01", period.PeriodFrom);
        Assert.Equal("2030-01-31", period.PeriodTo);
        Assert.Null(period.ScopeRef);
        Assert.Equal("goal:1", goal.ScopeRef);
        Assert.Null(goal.PeriodFrom);
        Assert.Null(goal.PeriodTo);
    }

    [Fact]
    public void SubscriptionChangeRequest_ReadsPackageSelectionsAndReason()
    {
        var upgrade = JsonSerializer.Deserialize<SubscriptionChangeRequest>(
            $$$"""{"schemaVersion":"1.0","expectedVersion":"relationship-1","kind":"UPGRADE","targetPackageId":"{{{Id}}}"}""",
            Web
        )!;
        var downgrade = JsonSerializer.Deserialize<SubscriptionChangeRequest>(
            """{"schemaVersion":"1.0","expectedVersion":"relationship-1","kind":"DOWNGRADE","selections":[{"componentId":"CONTENT_PLAN","selectedItemRefs":["a","b"]},{"componentId":"REPORTS"}],"reason":"Too much."}""",
            Web
        )!;

        Assert.Equal(Id, upgrade.TargetPackageId);
        Assert.Null(upgrade.SkillId);
        Assert.Null(upgrade.Selections);
        Assert.Null(downgrade.TargetPackageId);
        Assert.Equal("Too much.", downgrade.Reason);
        Assert.Equal("CONTENT_PLAN", downgrade.Selections![0].ComponentId);
        Assert.Equal("REPORTS", downgrade.Selections[1].ComponentId);
        Assert.Equal(new[] { "a", "b" }, downgrade.Selections[0].SelectedItemRefs);
        Assert.Null(downgrade.Selections[1].SelectedItemRefs);
    }

    [Fact]
    public void Records_CompareByValue_SoAReplayedReceiptEqualsTheStoredOne()
    {
        var receipt = new WorkbenchCommandReceipt("1.0", Id, "ACCEPTED", "r", "v", false, "c");

        Assert.Equal(receipt, receipt with { });
        Assert.NotEqual(receipt, receipt with { Replayed = true });
        Assert.Equal(
            new WorkbenchHandoff("1.0", Id, "d", At, true),
            new WorkbenchHandoff("1.0", Id, "d", At, true)
        );
    }
}
