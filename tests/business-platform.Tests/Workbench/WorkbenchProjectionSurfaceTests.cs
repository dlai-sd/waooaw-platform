// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, ADR-051

using System.Text.Json;
using System.Text.Json.Nodes;
using Google.Protobuf.WellKnownTypes;
using Moq;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Workbench;
using Waooaw.ConstitutionalEngine.Grpc;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class WorkbenchProjectionSurfaceTests
{
    private static readonly ChannelCapabilities FullWeb = ChannelCapabilities.Parse(
        "channel=WEB;modality=text;blocks=TEXT:1,CHOICES:1,LIST:1,LINK:1,FORM:1,METRIC:1,PLAN:1,DECISION:1,STATUS:1"
    )!;

    private static readonly DateTimeOffset T0 = WorkbenchProjectionFixture.Now.AddDays(-20);

    private static IReadOnlyDictionary<string, string> Plans(string json) =>
        new Dictionary<string, string> { ["plan-1"] = json };

    private static ExecutionOwnerWorkItem Item(
        string state,
        string skill = "CONTENT_STRATEGY_AND_CALENDAR",
        string effect = "DRAFT_DELIVERED",
        DateTimeOffset? updatedAt = null,
        Guid? id = null
    ) =>
        new(
            id ?? Guid.NewGuid(),
            Guid.NewGuid(),
            skill,
            "1.0.0",
            Guid.NewGuid(),
            1,
            state,
            effect,
            null,
            updatedAt ?? WorkbenchProjectionFixture.Now
        );

    [Fact]
    public async Task Goals_AreSummarisedWithTheirStateAndTheHighestVersionKnown()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        var plain = await fixture.AddGoalAsync("Plain goal", createdAt: T0);
        var revised = await fixture.AddGoalAsync("Revised goal", createdAt: T0.AddMinutes(1));
        await fixture.AddGoalDecisionAsync(revised, "CORRECTED", "Wrong city", "goal-older");
        var tracked = await fixture.AddGoalAsync("Tracked goal", createdAt: T0.AddMinutes(2));
        await fixture.GoalHistoryRecords.AppendAsync(
            fixture.TenantId,
            fixture.RelationshipId,
            tracked.GoalId,
            new WorkbenchGoalVersionEntry(
                0,
                T0,
                "Customer",
                null,
                "Tracked goal",
                new Dictionary<string, string>()
            ),
            default
        );
        await fixture.GoalHistoryRecords.AppendAsync(
            fixture.TenantId,
            fixture.RelationshipId,
            tracked.GoalId,
            new WorkbenchGoalVersionEntry(
                0,
                T0,
                "Customer",
                null,
                "Tracked goal",
                new Dictionary<string, string>()
            ),
            default
        );
        await fixture.GoalHistoryRecords.AppendAsync(
            fixture.TenantId,
            fixture.RelationshipId,
            tracked.GoalId,
            new WorkbenchGoalVersionEntry(
                0,
                T0,
                "Customer",
                null,
                "Tracked goal",
                new Dictionary<string, string>()
            ),
            default
        );
        var closed = await fixture.AddGoalAsync(
            "Closed goal",
            status: "CLOSED",
            createdAt: T0.AddMinutes(3)
        );
        var superseded = await fixture.AddGoalAsync(
            new string('x', 300),
            status: "SUPERSEDED",
            createdAt: T0.AddMinutes(4)
        );

        var list = await fixture.Service.ListGoalsAsync(
            fixture.Context(),
            WorkbenchPage.First,
            default
        );

        Assert.Equal(5, list.Items.Count);
        Assert.Null(list.NextCursor);
        WorkbenchGoalSummary Find(Guid id) => list.Items.Single(item => item.GoalId == id);
        Assert.Equal(1, Find(plain.GoalId).CurrentVersion);
        Assert.Equal(2, Find(revised.GoalId).CurrentVersion);
        Assert.Equal(3, Find(tracked.GoalId).CurrentVersion);
        Assert.Equal("ACTIVE", Find(plain.GoalId).State);
        Assert.Equal("CLOSED", Find(closed.GoalId).State);
        Assert.Equal("SUPERSEDED", Find(superseded.GoalId).State);
        Assert.Equal("UNDERSTAND_CURRENT_POSITION", Find(plain.GoalId).GoalTypeId);
        Assert.Equal(200, Find(superseded.GoalId).Title.Length);
        Assert.EndsWith("…", Find(superseded.GoalId).Title);
    }

    [Fact]
    public async Task Goals_ArePagedWithAnOpaqueCursor()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        for (var i = 0; i < 3; i++)
            await fixture.AddGoalAsync($"Goal {i}", createdAt: T0.AddMinutes(i));

        var first = await fixture.Service.ListGoalsAsync(
            fixture.Context(),
            new WorkbenchPage(0, 2),
            default
        );
        var second = await fixture.Service.ListGoalsAsync(
            fixture.Context(),
            new WorkbenchPage(2, 2),
            default
        );

        Assert.Equal(2, first.Items.Count);
        Assert.NotNull(first.NextCursor);
        Assert.Single(second.Items);
        Assert.Null(second.NextCursor);
    }

    [Fact]
    public async Task Goals_StillListWhenTheHistoryStoreIsDown()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        await fixture.AddGoalAsync();
        fixture.GoalHistory.Failure = new InvalidOperationException("history down");

        var list = await fixture.Service.ListGoalsAsync(
            fixture.Context(),
            WorkbenchPage.First,
            default
        );

        Assert.Equal(1, Assert.Single(list.Items).CurrentVersion);
    }

    [Fact]
    public async Task Goals_PropagateCancellationFromTheHistoryStore()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        var goal = await fixture.AddGoalAsync();
        fixture.GoalHistory.Failure = new OperationCanceledException();

        await Assert.ThrowsAsync<OperationCanceledException>(() =>
            fixture.Service.ListGoalsAsync(fixture.Context(), WorkbenchPage.First, default)
        );
        await Assert.ThrowsAsync<OperationCanceledException>(() =>
            fixture.Service.ListGoalVersionsAsync(
                fixture.Context(),
                goal.GoalId,
                WorkbenchPage.First,
                default
            )
        );
    }

    [Fact]
    public async Task Goal_IsDescribedWithItsParametersAndTheMeasuresItsTypeDeclares()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        var goal = await fixture.AddGoalAsync(
            baseline: """{"parameters":{"PRIMARY_LOCATION":"Pune","BUSINESS_DOMAIN":"Dental"}}""",
            threshold: "80"
        );

        var detail = await fixture.Service.GetGoalAsync(fixture.Context(), goal.GoalId, default);

        Assert.NotNull(detail);
        Assert.Equal(["BUSINESS_DOMAIN", "PRIMARY_LOCATION"], detail.Parameters.Keys);
        Assert.Equal("Pune", detail.Parameters["PRIMARY_LOCATION"]);
        Assert.Equal(
            ["PROFILE_COVERAGE", "MATURITY_EVIDENCE_COVERAGE"],
            detail.Measures.Select(item => item.MeasureId)
        );
        Assert.All(detail.Measures, measure => Assert.Equal("UNAVAILABLE", measure.Freshness));
        Assert.All(detail.Measures, measure => Assert.Equal("80", measure.Target));
        Assert.Equal(["NO_PUBLICATION_AUTHORITY"], detail.Constraints);
    }

    [Fact]
    public async Task Goal_OfATypeTheAgentDoesNotDeclare_HasNoMeasures_AndAnUnknownGoalIsMissing()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        var goal = await fixture.AddGoalAsync(measure: "SOMETHING_ELSE");

        var detail = await fixture.Service.GetGoalAsync(fixture.Context(), goal.GoalId, default);
        var missing = await fixture.Service.GetGoalAsync(
            fixture.Context(),
            Guid.NewGuid(),
            default
        );

        Assert.Empty(detail!.Measures);
        Assert.Empty(detail.Constraints);
        Assert.Null(missing);
    }

    [Fact]
    public async Task GoalVersions_OfAnUnknownGoal_AreMissing()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();

        var versions = await fixture.Service.ListGoalVersionsAsync(
            fixture.Context(),
            Guid.NewGuid(),
            WorkbenchPage.First,
            default
        );

        Assert.Null(versions);
    }

    [Fact]
    public async Task GoalVersions_WithoutRecordedHistory_ShowTheCurrentStateAsTheCustomersVersion()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        var goal = await fixture.AddGoalAsync(
            baseline: """{"parameters":{"PRIMARY_LOCATION":"Pune"}}""",
            updatedAt: T0
        );
        await fixture.AddGoalDecisionAsync(goal, "CORRECTED", "Wrong city", "goal-older");

        var list = await fixture.Service.ListGoalVersionsAsync(
            fixture.Context(),
            goal.GoalId,
            WorkbenchPage.First,
            default
        );

        var version = Assert.Single(list!.Items);
        Assert.Equal(2, version.VersionNo);
        Assert.Equal("Customer", version.RevisedBy);
        Assert.Equal(T0, version.RevisedAt);
        Assert.Equal("Pune", version.Parameters["PRIMARY_LOCATION"]);
    }

    [Fact]
    public async Task GoalVersions_AppendTheCurrentStateOnlyWhenTheGoalChangedAfterTheLastRecordedVersion()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        var inSync = await fixture.AddGoalAsync("In sync", updatedAt: T0.AddHours(2));
        var drifted = await fixture.AddGoalAsync("Drifted", updatedAt: T0.AddHours(5));
        foreach (
            var (goal, at) in new[]
            {
                (inSync, T0.AddHours(1)),
                (inSync, T0.AddHours(2)),
                (drifted, T0.AddHours(1)),
            }
        )
            await fixture.GoalHistoryRecords.AppendAsync(
                fixture.TenantId,
                fixture.RelationshipId,
                goal.GoalId,
                new WorkbenchGoalVersionEntry(
                    0,
                    at,
                    "Customer",
                    "reason",
                    goal.Goal,
                    new Dictionary<string, string>()
                ),
                default
            );

        var first = await fixture.Service.ListGoalVersionsAsync(
            fixture.Context(),
            inSync.GoalId,
            WorkbenchPage.First,
            default
        );
        var second = await fixture.Service.ListGoalVersionsAsync(
            fixture.Context(),
            drifted.GoalId,
            WorkbenchPage.First,
            default
        );

        Assert.Equal([2, 1], first!.Items.Select(item => item.VersionNo));
        Assert.Equal([2, 1], second!.Items.Select(item => item.VersionNo));
        Assert.Equal(T0.AddHours(5), second.Items[0].RevisedAt);
        Assert.Equal("reason", first.Items[0].Reason);
    }

    [Fact]
    public async Task GoalVersions_ArePagedNewestFirst()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        var goal = await fixture.AddGoalAsync(updatedAt: T0.AddHours(3));
        for (var i = 1; i <= 3; i++)
            await fixture.GoalHistoryRecords.AppendAsync(
                fixture.TenantId,
                fixture.RelationshipId,
                goal.GoalId,
                new WorkbenchGoalVersionEntry(
                    0,
                    T0.AddHours(i),
                    "Customer",
                    null,
                    goal.Goal,
                    new Dictionary<string, string>()
                ),
                default
            );

        var page = await fixture.Service.ListGoalVersionsAsync(
            fixture.Context(),
            goal.GoalId,
            new WorkbenchPage(0, 2),
            default
        );

        Assert.Equal([3, 2], page!.Items.Select(item => item.VersionNo));
        Assert.NotNull(page.NextCursor);
    }

    [Theory]
    [InlineData("PROPOSED", "ACTIVE")]
    [InlineData("ACTIVE", "ACTIVE")]
    [InlineData("SUPERSEDED", "SUPERSEDED")]
    [InlineData("CLOSED", "CLOSED")]
    [InlineData("CANCELLED", "CLOSED")]
    [InlineData("ARCHIVED", "CLOSED")]
    public void GoalState_FoldsTheOwnersStatusesIntoThreeStates(string status, string expected) =>
        Assert.Equal(
            expected,
            WorkbenchProjectionService.GoalState(new RelationshipGoal { Status = status })
        );

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("not json")]
    [InlineData("""["parameters"]""")]
    [InlineData("""{"parameters":["a"]}""")]
    [InlineData("""{"other":{"a":"b"}}""")]
    [InlineData("""{"parameters":{"a":1,"b":null,"c":true}}""")]
    public void ParametersOf_IgnoresAnythingThatIsNotAStringParameter(string? baseline) =>
        Assert.Empty(
            WorkbenchProjectionService.ParametersOf(new RelationshipGoal { Baseline = baseline })
        );

    [Fact]
    public void ParametersOf_KeepsOnlyTheStringValuesInOrdinalOrder()
    {
        var parameters = WorkbenchProjectionService.ParametersOf(
            new RelationshipGoal
            {
                Baseline = """{"parameters":{"b":"2","B":"upper","a":"1","n":3}}""",
            }
        );

        Assert.Equal(["B", "a", "b"], parameters.Keys);
        Assert.Equal("upper", parameters["B"]);
    }

    [Fact]
    public async Task Plan_IsAbsentUntilTheWorkspaceNamesOneThatExists()
    {
        var none = await WorkbenchProjectionFixture.CreateAsync();
        var unnamed = await WorkbenchProjectionFixture.CreateAsync();
        unnamed.SetWorkspace();
        var unknown = await WorkbenchProjectionFixture.CreateAsync();
        unknown.SetWorkspace("{}", Plans("""{"state":"AGREED"}"""), "plan-9");
        var malformed = await WorkbenchProjectionFixture.CreateAsync();
        malformed.SetWorkspace("{}", Plans("\"text\""), "plan-1");

        Assert.Null(await none.Service.GetCurrentPlanAsync(none.Context(), default));
        Assert.Null(await unnamed.Service.GetCurrentPlanAsync(unnamed.Context(), default));
        Assert.Null(await unknown.Service.GetCurrentPlanAsync(unknown.Context(), default));
        Assert.Null(await malformed.Service.GetCurrentPlanAsync(malformed.Context(), default));
    }

    [Theory]
    [InlineData("READY_FOR_REVIEW", "READY_FOR_REVIEW")]
    [InlineData("AGREED", "AGREED")]
    [InlineData("ACTIVE", "AGREED")]
    [InlineData("COMPLETED", "AGREED")]
    [InlineData("SUPERSEDED", "SUPERSEDED")]
    [InlineData("CANCELLED", "SUPERSEDED")]
    [InlineData("DRAFT", "DRAFT")]
    [InlineData("BLOCKED", "DRAFT")]
    [InlineData("whatever", "DRAFT")]
    public async Task Plan_FoldsTheOwnersStateIntoTheWorkbenchStates(string raw, string expected)
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace("{}", Plans($$"""{"state":"{{raw}}"}"""), "plan-1");

        var plan = await fixture.Service.GetCurrentPlanAsync(fixture.Context(), default);
        var projection = await fixture.Service.BuildAsync(fixture.Context(), FullWeb, default);

        Assert.Equal(expected, plan!.State);
        Assert.Equal("plan-1", plan.PlanVersion);
        Assert.Equal(
            raw == "BLOCKED",
            projection.Limitations.Contains("The current plan is blocked and needs attention.")
        );
        Assert.Equal("plan-1", projection.CurrentPlanVersion);
    }

    [Fact]
    public async Task Plan_TakesItsGoalFromThePlan_ThenTheActiveGoal_ThenNothing()
    {
        var named = Guid.NewGuid();
        var explicitGoal = await WorkbenchProjectionFixture.CreateAsync();
        explicitGoal.SetWorkspace("{}", Plans($$"""{"goalRef":"{{named}}"}"""), "plan-1");
        await explicitGoal.AddGoalAsync(status: "ACTIVE");
        var bad = await WorkbenchProjectionFixture.CreateAsync();
        bad.SetWorkspace("{}", Plans("""{"goalRef":"not-a-guid"}"""), "plan-1");
        var closed = await bad.AddGoalAsync(status: "CLOSED", createdAt: T0);
        var active = await bad.AddGoalAsync(status: "ACTIVE", createdAt: T0.AddMinutes(1));
        var orphan = await WorkbenchProjectionFixture.CreateAsync();
        orphan.SetWorkspace("{}", Plans("{}"), "plan-1");

        var first = await explicitGoal.Service.GetCurrentPlanAsync(explicitGoal.Context(), default);
        var second = await bad.Service.GetCurrentPlanAsync(bad.Context(), default);
        var third = await orphan.Service.GetCurrentPlanAsync(orphan.Context(), default);

        Assert.Equal(named, first!.GoalRef);
        Assert.Equal(active.GoalId, second!.GoalRef);
        Assert.NotEqual(closed.GoalId, second.GoalRef);
        Assert.Equal(Guid.Empty, third!.GoalRef);
    }

    [Fact]
    public async Task Plan_ReadsMilestonesAndCalendarWithSafeDefaults()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace(
            "{}",
            Plans(
                """
                {
                  "state":"READY_FOR_REVIEW",
                  "milestones":[
                    {"itemId":"m-1","milestoneTypeId":"PROFILE_CONFIRMED","label":"Confirm the profile","dueMeaning":"Before the first post","state":"DONE"},
                    {"milestoneId":"m-2","title":"Review the brief"},
                    {},
                    "ignored"
                  ],
                  "calendarCommitments":[
                    {"localDateTime":"2030-07-01T09:00:00","label":"Month review"},
                    {"localDateTime":"2030-07-02","title":"Brief"},
                    {"localDateTime":"2030-07-0"},
                    {"label":"No date"},
                    {"localDateTime":"2030-07-03T10:00:00"}
                  ]
                }
                """
            ),
            "plan-1"
        );

        var plan = await fixture.Service.GetCurrentPlanAsync(fixture.Context(), default);

        Assert.Equal(
            [
                new WorkbenchMilestone(
                    "m-1",
                    "PROFILE_CONFIRMED",
                    "Confirm the profile",
                    "Before the first post",
                    "DONE"
                ),
                new WorkbenchMilestone(
                    "m-2",
                    "MILESTONE",
                    "Review the brief",
                    "Date not set",
                    "PROPOSED"
                ),
                new WorkbenchMilestone(
                    "milestone",
                    "MILESTONE",
                    "Milestone",
                    "Date not set",
                    "PROPOSED"
                ),
            ],
            plan!.Milestones
        );
        Assert.Equal(
            [
                new WorkbenchCalendarEntry("2030-07-01", "Month review"),
                new WorkbenchCalendarEntry("2030-07-02", "Brief"),
                new WorkbenchCalendarEntry("2030-07-03", "Calendar commitment"),
            ],
            plan.Calendar
        );
        Assert.Empty(plan.Limitations);
    }

    [Fact]
    public async Task Capabilities_FollowTheDeclarationAndTheSkillTheCustomerChose()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        await fixture.AddSkillAsync(
            "SOCIAL_CONTENT_CREATION_AND_PUBLISHING",
            "ACCEPTED",
            updatedAt: T0
        );
        await fixture.AddSkillAsync(
            "SOCIAL_CONTENT_CREATION_AND_PUBLISHING",
            "DEFERRED",
            updatedAt: T0.AddDays(1)
        );
        await fixture.AddSkillAsync("VISUAL_AND_VIDEO_CONTENT", "ACCEPTED");
        await fixture.AddSkillAsync("MARKETING_PERFORMANCE_AND_IMPROVEMENT", "PROPOSED");

        var list = await fixture.Service.ListCapabilitiesAsync(fixture.Context(), default);

        WorkbenchCapability Find(string id) => list.Items.Single(item => item.SkillId == id);
        Assert.Equal(4, list.Items.Count);
        var content = Find("CONTENT_STRATEGY_AND_CALENDAR");
        Assert.Equal("DEFAULT_OFF", content.Availability);
        Assert.Equal("NOT_ENABLED", content.State);
        Assert.Equal(["CONTENT_PLAN"], content.ComponentIds);
        Assert.Equal("Content strategy and calendar", content.Label);
        Assert.Equal("CUSTOMER_APPROVAL", content.ApprovalMode);
        Assert.Equal("Monthly; Month end review last 3 working days", content.NextRunMeaning);
        Assert.Null(content.Limitation);
        var social = Find("SOCIAL_CONTENT_CREATION_AND_PUBLISHING");
        Assert.Equal("PAUSED", social.State);
        Assert.Equal("AVAILABLE", social.Availability);
        Assert.Equal(["CONTENT_DRAFT", "SOCIAL_PUBLICATION"], social.ComponentIds);
        Assert.Equal("ACTIVE", Find("VISUAL_AND_VIDEO_CONTENT").State);
        Assert.Equal("NOT_ENABLED", Find("MARKETING_PERFORMANCE_AND_IMPROVEMENT").State);
    }

    [Fact]
    public async Task Capabilities_WhoseComponentsAreAllUnreleased_SayTheyAreNotReleased()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync(mutateManifest: manifest =>
        {
            foreach (var component in manifest["experience"]!["components"]!.AsArray())
                if (component!["skillId"]?.GetValue<string>() == "VISUAL_AND_VIDEO_CONTENT")
                    component["availability"] = "UNAVAILABLE";
        });
        fixture.SetWorkspace();
        await fixture.AddSkillAsync("VISUAL_AND_VIDEO_CONTENT", "ACCEPTED");

        var data = await fixture.Service.LoadAsync(fixture.Context(), default);
        var capabilities = fixture.Service.Capabilities(data);

        var visual = capabilities.Single(item => item.SkillId == "VISUAL_AND_VIDEO_CONTENT");
        Assert.Equal("UNAVAILABLE", visual.Availability);
        Assert.Equal("This capability is not released yet.", visual.Limitation);
        Assert.Equal("ACTIVE", visual.State);
    }

    [Fact]
    public async Task Capabilities_WithoutADeclaration_AreEmpty()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();

        var list = await fixture.Service.ListCapabilitiesAsync(fixture.Context(), default);

        Assert.Empty(list.Items);
    }

    [Fact]
    public async Task WorkItems_ShowTheExecutionOwnersWorkNewestFirstWithTheStateTheCustomerCanRead()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        var states = new[]
        {
            ("PENDING", "PROPOSED"),
            ("queued", "PROPOSED"),
            ("PROPOSED", "PROPOSED"),
            ("RUNNING", "IN_PROGRESS"),
            ("IN_PROGRESS", "IN_PROGRESS"),
            ("STARTED", "IN_PROGRESS"),
            ("COMPLETED", "COMPLETED"),
            ("SUCCEEDED", "COMPLETED"),
            ("DONE", "COMPLETED"),
            ("FAILED", "BLOCKED"),
            ("BLOCKED", "BLOCKED"),
            ("CANCELLED", "CANCELLED"),
            ("WAITING_APPROVAL", "WAITING_ON_CUSTOMER"),
            ("AWAITING_APPROVAL", "WAITING_ON_CUSTOMER"),
            ("SOMETHING_NEW", "OUTCOME_UNKNOWN"),
        };
        var items = states
            .Select(
                (entry, index) =>
                    Item(entry.Item1, updatedAt: WorkbenchProjectionFixture.Now.AddMinutes(-index))
            )
            .ToArray();
        fixture.SetExecution(
            new ExecutionOwnerProjection("e-1", "CURRENT", WorkbenchProjectionFixture.Now, items)
        );

        var list = await fixture.Service.ListWorkItemsAsync(
            fixture.Context(),
            new WorkbenchPage(0, 100),
            default
        );

        Assert.Equal(states.Select(entry => entry.Item2), list.Items.Select(item => item.State));
        Assert.All(list.Items, item => Assert.Equal("PROFILE_CONFIRMATION", item.WorkItemType));
        Assert.All(list.Items, item => Assert.Equal("CURRENT", item.Freshness));
        Assert.All(list.Items, item => Assert.Equal("Agent", item.Owner));
        Assert.Equal("Content strategy and calendar: Draft delivered", list.Items[0].Label);
        Assert.Equal(items[0].WorkItemId.ToString("D"), list.Items[0].ItemRef);
    }

    [Fact]
    public async Task WorkItems_AreStaleWhenTheOwnerReportedMoreThanAnHourAgo_AndTypedGenericallyWithoutADeclaration()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync(withDeclaration: false);
        fixture.SetWorkspace();
        fixture.SetExecution(
            new ExecutionOwnerProjection(
                "e-1",
                "CURRENT",
                WorkbenchProjectionFixture.Now.AddMinutes(-61),
                [Item("RUNNING", effect: new string('e', 300))]
            )
        );

        var list = await fixture.Service.ListWorkItemsAsync(
            fixture.Context(),
            WorkbenchPage.First,
            default
        );

        var item = Assert.Single(list.Items);
        Assert.Equal("STALE", item.Freshness);
        Assert.Equal("WORK_ITEM", item.WorkItemType);
        Assert.Equal(120, item.Label.Length);
    }

    [Fact]
    public async Task WorkItems_OrderTiesByReferenceAndPage()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        var low = Guid.Parse("00000000-0000-0000-0000-000000000001");
        var high = Guid.Parse("00000000-0000-0000-0000-000000000002");
        fixture.SetExecution(
            new ExecutionOwnerProjection(
                "e-1",
                "CURRENT",
                WorkbenchProjectionFixture.Now,
                [Item("DONE", id: high), Item("DONE", id: low)]
            )
        );
        var empty = await WorkbenchProjectionFixture.CreateAsync();
        empty.SetWorkspace();
        empty.SetExecution(
            new ExecutionOwnerProjection("e-1", "CURRENT", WorkbenchProjectionFixture.Now)
        );

        var first = await fixture.Service.ListWorkItemsAsync(
            fixture.Context(),
            new WorkbenchPage(0, 1),
            default
        );
        var none = await empty.Service.ListWorkItemsAsync(
            empty.Context(),
            WorkbenchPage.First,
            default
        );

        Assert.Equal(low.ToString("D"), Assert.Single(first.Items).ItemRef);
        Assert.NotNull(first.NextCursor);
        Assert.Empty(none.Items);
    }

    [Fact]
    public async Task WorkItems_WithNoExecutionReport_AreEmpty()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();

        var list = await fixture.Service.ListWorkItemsAsync(
            fixture.Context(),
            WorkbenchPage.First,
            default
        );

        Assert.Empty(list.Items);
    }

    [Fact]
    public async Task Decisions_ListWhatTheCustomerMustApprove_AndNothingForAnAudienceThatCannotDecide()
    {
        var owner = await WorkbenchProjectionFixture.CreateAsync();
        owner.SetWorkspace();
        var proposed = await owner.AddSkillAsync("CONTENT_STRATEGY_AND_CALENDAR", "PROPOSED");
        await owner.AddSkillAsync("VISUAL_AND_VIDEO_CONTENT", "SELECTED");
        await owner.AddSkillAsync("SOCIAL_CONTENT_CREATION_AND_PUBLISHING", "ACCEPTED");
        await owner.AddSkillAsync(
            "MARKETING_PERFORMANCE_AND_IMPROVEMENT",
            "PROPOSED",
            applicability: "NOT_APPLICABLE"
        );
        var beneficiary = await WorkbenchProjectionFixture.CreateAsync(
            RelationshipParticipantRole.OutcomeOwner
        );
        beneficiary.SetWorkspace();
        await beneficiary.AddSkillAsync("CONTENT_STRATEGY_AND_CALENDAR", "PROPOSED");

        var items = await owner.Service.ListDecisionItemsAsync(owner.Context(), default);
        var none = await beneficiary.Service.ListDecisionItemsAsync(beneficiary.Context(), default);

        Assert.Equal(2, items.Count);
        var first = items.Single(item => item.SkillId == "CONTENT_STRATEGY_AND_CALENDAR");
        Assert.Equal("SKILL", first.Kind);
        Assert.Equal(proposed.ConfigurationId, first.SubjectId);
        Assert.Equal("skill:CONTENT_STRATEGY_AND_CALENDAR", first.Decision.ItemRef);
        Assert.Equal(
            "Turn on Content strategy and calendar for this relationship.",
            first.Decision.Effect
        );
        Assert.Equal("Uses Content plans from your package.", first.Decision.Cost);
        Assert.Equal(ExperienceBlockBuilder.ApproveLabel, first.Decision.ConfirmLabel);
        Assert.Equal(
            RelationshipConfigurationService.GetSkillVersion(proposed),
            first.SubjectVersion
        );
        Assert.Equal("1.0.0", first.SkillVersion);
        Assert.Empty(none);
    }

    [Fact]
    public async Task Decisions_IncludeTheGoalsTheCustomerHasNotYetConfirmed()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        var goal = await fixture.AddGoalAsync(
            "Grow weekly enquiries",
            status: "ACTIVE",
            updatedAt: T0
        );
        var verified = await fixture.AddGoalAsync(
            "Verified goal",
            status: "ACTIVE",
            updatedAt: T0,
            createdAt: T0.AddMinutes(1)
        );
        var closed = await fixture.AddGoalAsync(
            "Closed goal",
            status: "CLOSED",
            updatedAt: T0,
            createdAt: T0.AddMinutes(2)
        );
        await fixture.AddGoalDecisionAsync(verified, "VERIFIED");
        await fixture.AddSkillAsync(
            "CONTENT_STRATEGY_AND_CALENDAR",
            "ACCEPTED",
            goalId: goal.GoalId
        );
        await fixture.AddSkillAsync(
            "CONTENT_STRATEGY_AND_CALENDAR",
            "ACCEPTED",
            goalId: verified.GoalId
        );
        await fixture.AddSkillAsync(
            "CONTENT_STRATEGY_AND_CALENDAR",
            "ACCEPTED",
            goalId: closed.GoalId
        );

        var items = await fixture.Service.ListDecisionItemsAsync(fixture.Context(), default);

        var item = Assert.Single(items);
        Assert.Equal("GOAL", item.Kind);
        Assert.Equal(goal.GoalId, item.SubjectId);
        Assert.Equal($"goal:{goal.GoalId:D}", item.Decision.ItemRef);
        Assert.Equal("Confirm this goal: Grow weekly enquiries", item.Decision.Effect);
        Assert.Equal(RelationshipConfigurationService.GetGoalVersion(goal), item.SubjectVersion);
        Assert.Null(item.SkillVersion);
        Assert.Equal("Confirm", item.Decision.ConfirmLabel);
    }

    [Fact]
    public async Task Decisions_AreOfferedToAnEvaluatorWhoMayResolveThemEvenWithoutADecidingAudience()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync(
            RelationshipParticipantRole.Evaluator
        );
        fixture.SetWorkspace();
        await fixture.AddSkillAsync("CONTENT_STRATEGY_AND_CALENDAR", "PROPOSED");

        var items = await fixture.Service.ListDecisionItemsAsync(fixture.Context(), default);

        Assert.Single(items);
    }

    [Fact]
    public async Task Decisions_AreListedWithBlocksAndPaged()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        await fixture.AddSkillAsync("CONTENT_STRATEGY_AND_CALENDAR", "PROPOSED");
        await fixture.AddSkillAsync("VISUAL_AND_VIDEO_CONTENT", "PROPOSED");

        var first = await fixture.Service.ListDecisionsAsync(
            fixture.Context(),
            FullWeb,
            new WorkbenchPage(0, 1),
            default
        );
        var all = await fixture.Service.ListDecisionsAsync(
            fixture.Context(),
            FullWeb,
            WorkbenchPage.First,
            default
        );

        Assert.Single(first.Items);
        Assert.NotNull(first.NextCursor);
        Assert.NotEmpty(first.Blocks);
        Assert.Equal(2, all.Items.Count);
        Assert.Null(all.NextCursor);
    }

    [Fact]
    public async Task Monitor_ListsTheVisibleTilesAndAdmitsWhatIsNotYetMeasured()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        var empty = await WorkbenchProjectionFixture.CreateAsync(
            mutateManifest: WorkbenchProjectionFixture.TilesForStewardsOnly
        );
        empty.SetWorkspace();
        empty.SetExecution(
            new ExecutionOwnerProjection("e", "CURRENT", WorkbenchProjectionFixture.Now)
        );

        var monitor = await fixture.Service.GetMonitorAsync(fixture.Context(), FullWeb, default);
        var current = await empty.Service.GetMonitorAsync(empty.Context(), FullWeb, default);

        Assert.Equal(5, monitor.Tiles.Count);
        Assert.Equal("STALE", monitor.SourceFreshness);
        Assert.Contains(
            "Measure values are not yet reported by their owners.",
            monitor.Limitations
        );
        Assert.Empty(monitor.Alerts);
        Assert.NotEmpty(monitor.Blocks);
        Assert.Equal("CURRENT", current.SourceFreshness);
        Assert.Empty(current.Limitations);
    }

    private static async Task<WorkbenchProjectionFixture> WithReviewsAsync(
        Action<JsonNode>? mutateManifest = null
    )
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync(mutateManifest: mutateManifest);
        fixture.SetWorkspace();
        await fixture.AddReviewAsync(
            "CONTINUE_CURRENT_MANDATE",
            WorkbenchProjectionFixture.Now.AddDays(-5)
        );
        return fixture;
    }

    [Fact]
    public async Task Narratives_AreComposedFromTheReviewInTheOrderTheDeclarationNames()
    {
        var fixture = await WithReviewsAsync();

        var list = await fixture.Service.ListNarrativesAsync(
            fixture.Context(),
            WorkbenchPage.First,
            default
        );

        var narrative = Assert.Single(list.Items);
        Assert.Equal(
            [
                new WorkbenchNarrativePart("WHAT_HAPPENED", "work"),
                new WorkbenchNarrativePart("WHAT_I_LEARNED", "quality"),
                new WorkbenchNarrativePart("WHAT_I_TRIED", "outcome"),
                new WorkbenchNarrativePart("WHAT_CHANGES_NEXT_MONTH", "CONTINUE_CURRENT_MANDATE"),
                new WorkbenchNarrativePart("WHAT_I_NEED_FROM_YOU", "assessment"),
            ],
            narrative.Parts
        );
        Assert.Equal("CURRENT", narrative.Freshness);
        Assert.Equal("2030-05-11 to 2030-06-10", narrative.PeriodLabel);
    }

    [Fact]
    public async Task Narratives_OfAReviewOlderThanTwoMonths_AreStale()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        await fixture.AddReviewAsync(
            "CONTINUE_CURRENT_MANDATE",
            WorkbenchProjectionFixture.Now.AddDays(-63)
        );

        var list = await fixture.Service.ListNarrativesAsync(
            fixture.Context(),
            WorkbenchPage.First,
            default
        );

        Assert.Equal("STALE", Assert.Single(list.Items).Freshness);
    }

    [Fact]
    public async Task Narratives_UseOnlyThePartsTheDeclarationKnows_AndAreDroppedWhenNoneRemain()
    {
        var unknownParts = await WithReviewsAsync(manifest =>
            manifest["experience"]!["monitor"]!["narratives"]![0]!["structure"] = new JsonArray(
                "WHAT_HAPPENED",
                "SOMETHING_ELSE"
            )
        );
        var onlyUnknown = await WithReviewsAsync(manifest =>
            manifest["experience"]!["monitor"]!["narratives"]![0]!["structure"] = new JsonArray(
                "SOMETHING_ELSE"
            )
        );
        var noDeclaration = await WorkbenchProjectionFixture.CreateAsync(withDeclaration: false);
        noDeclaration.SetWorkspace();
        await noDeclaration.AddReviewAsync(
            "CONTINUE_CURRENT_MANDATE",
            WorkbenchProjectionFixture.Now.AddDays(-5)
        );

        var first = await unknownParts.Service.ListNarrativesAsync(
            unknownParts.Context(),
            WorkbenchPage.First,
            default
        );
        var second = await onlyUnknown.Service.ListNarrativesAsync(
            onlyUnknown.Context(),
            WorkbenchPage.First,
            default
        );
        var third = await noDeclaration.Service.ListNarrativesAsync(
            noDeclaration.Context(),
            WorkbenchPage.First,
            default
        );

        Assert.Equal(["WHAT_HAPPENED"], Assert.Single(first.Items).Parts.Select(part => part.Part));
        Assert.Empty(second.Items);
        Assert.Empty(third.Items);
    }

    [Fact]
    public async Task Wallet_IsRefusedToAudiencesThatMayNotSeeIt()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync(
            RelationshipParticipantRole.OutcomeOwner
        );

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Service.GetWalletAsync(fixture.Context(), default)
        );

        Assert.Equal(403, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.SpendAuthorityUnavailable, failure.Code);
    }

    [Fact]
    public async Task Wallet_IsUnavailableWhenBillingCannotSayWhenThePeriodEnds()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        var noPeriod = await WorkbenchProjectionFixture.CreateAsync();
        noPeriod
            .Commercial.Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ReturnsAsync(new WorkbenchCommercialSnapshot(true, "v1", null, [], false, null));

        var unavailable = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Service.GetWalletAsync(fixture.Context(), default)
        );
        var missing = await Assert.ThrowsAsync<WorkbenchException>(() =>
            noPeriod.Service.GetWalletAsync(noPeriod.Context(), default)
        );

        Assert.Equal(503, unavailable.Status);
        Assert.Equal(WorkbenchProblemCodes.SpendCommercialUnavailable, unavailable.Code);
        Assert.Equal("Billing is not reachable.", unavailable.Detail);
        Assert.Equal(503, missing.Status);
    }

    [Theory]
    [InlineData(RelationshipParticipantRole.Employer, false)]
    [InlineData(RelationshipParticipantRole.RelationshipManager, true)]
    public async Task Wallet_ReportsTheBalancesAndNeverOffersATopUp(
        RelationshipParticipantRole role,
        bool askAccountOwner
    )
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync(role);
        var end = WorkbenchProjectionFixture.Now.AddDays(9);
        var component = new WorkbenchComponentBalance(
            "CONTENT_DRAFT",
            "Content drafts",
            2,
            10,
            end
        );
        fixture
            .Commercial.Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ReturnsAsync(
                new WorkbenchCommercialSnapshot(true, "v1", end, [component], true, null)
            );

        var wallet = await fixture.Service.GetWalletAsync(fixture.Context(), default);

        Assert.Equal(fixture.RelationshipId, wallet.RelationshipRef);
        Assert.Equal(end, wallet.PeriodEnd);
        Assert.Equal([component], wallet.Components);
        Assert.False(wallet.TopUpAvailable);
        Assert.Equal(askAccountOwner, wallet.AskAccountOwner);
    }

    [Fact]
    public async Task Evidence_IsListedNewestFirstWithErasureStatedPlainly()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        var older = Guid.Parse("00000000-0000-0000-0000-0000000000a1");
        var newer = Guid.Parse("00000000-0000-0000-0000-0000000000a2");
        CustomerVisibleEvidenceRecord Record(
            Guid id,
            string action,
            DateTimeOffset at,
            string erasure
        ) =>
            new()
            {
                EvidenceRecordId = id.ToString(),
                DecisionId = Guid.NewGuid().ToString(),
                AgentId = "agent",
                AgentInstanceId = fixture.AgentInstanceId.ToString(),
                ActionType = action,
                ExecutionStatus = "AUTHORIZED",
                EvidenceHash = new string('a', 64),
                RecordedAt = Timestamp.FromDateTimeOffset(at),
                ErasureStatus = erasure,
            };
        fixture
            .EvidenceGateway.Setup(item =>
                item.QueryAsync(
                    It.IsAny<Guid>(),
                    It.IsAny<IReadOnlyCollection<Guid>>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync([
                Record(older, "STATE_CHANGED", WorkbenchProjectionFixture.Now.AddDays(-2), "NONE"),
                Record(newer, "PLAN_AGREED", WorkbenchProjectionFixture.Now.AddDays(-1), "ERASED"),
            ]);

        var list = await fixture.Service.ListEvidenceAsync(
            fixture.Context(),
            WorkbenchPage.First,
            default
        );
        var paged = await fixture.Service.ListEvidenceAsync(
            fixture.Context(),
            new WorkbenchPage(0, 1),
            default
        );

        Assert.Equal("RECORDED", list.EvidenceState);
        Assert.Equal(
            [newer.ToString("D"), older.ToString("D")],
            list.Items.Select(item => item.EvidenceRef)
        );
        Assert.Equal("The details of this record were erased on request.", list.Items[0].Summary);
        Assert.Equal("Plan agreed", list.Items[0].Kind);
        Assert.Equal("State changed was recorded.", list.Items[1].Summary);
        Assert.Equal(WorkbenchProjectionFixture.Now.AddDays(-1), list.Items[0].ProducedAt);
        Assert.NotNull(paged.NextCursor);
    }

    [Fact]
    public async Task Evidence_ThatCannotBeRead_IsReportedUnavailableRatherThanFailing()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.EvidenceStore.FailNth(1);
        var cancelled = await WorkbenchProjectionFixture.CreateAsync();
        cancelled
            .EvidenceGateway.Setup(item =>
                item.QueryAsync(
                    It.IsAny<Guid>(),
                    It.IsAny<IReadOnlyCollection<Guid>>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ThrowsAsync(new OperationCanceledException());

        var list = await fixture.Service.ListEvidenceAsync(
            fixture.Context(),
            WorkbenchPage.First,
            default
        );

        Assert.Equal("UNAVAILABLE", list.EvidenceState);
        Assert.Empty(list.Items);
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            cancelled.Service.ListEvidenceAsync(cancelled.Context(), WorkbenchPage.First, default)
        );
    }
}
