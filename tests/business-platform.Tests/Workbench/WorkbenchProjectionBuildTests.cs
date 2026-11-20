// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, ADR-051

using System.Text.Json;
using System.Text.Json.Nodes;
using Moq;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class WorkbenchProjectionBuildTests
{
    private static readonly ChannelCapabilities FullWeb = ChannelCapabilities.Parse(
        "channel=WEB;modality=text;blocks=TEXT:1,CHOICES:1,LIST:1,LINK:1,FORM:1,METRIC:1,PLAN:1,DECISION:1,STATUS:1"
    )!;

    private static readonly ExecutionOwnerProjection Execution = new(
        "execution-1",
        "CURRENT",
        WorkbenchProjectionFixture.Now,
        []
    );

    private const string PlanJson = """
        {"planVersion":"plan-1","state":"READY_FOR_REVIEW","milestones":[],"calendarCommitments":[]}
        """;

    private static IReadOnlyDictionary<string, string> Plan(string json = PlanJson) =>
        new Dictionary<string, string> { ["plan-1"] = json };

    private static WorkbenchAvailableCommand Command(WorkbenchProjection value, string id) =>
        value.AvailableCommands.Single(item => item.CommandId == id);

    [Fact]
    public async Task Declaration_IsReadForTheBoundAgentVersionAndManifestVersion()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        AdmittedManifestRequest? asked = null;
        fixture
            .Manifests.Setup(item =>
                item.GetAsync(It.IsAny<AdmittedManifestRequest>(), It.IsAny<CancellationToken>())
            )
            .Callback<AdmittedManifestRequest, CancellationToken>((request, _) => asked = request)
            .ReturnsAsync(() => WorkbenchProjectionFixture.Manifest());
        var context = fixture.Context();

        var declaration = await fixture.Service.GetDeclarationAsync(context, default);

        Assert.NotNull(declaration);
        Assert.Contains(
            declaration.GoalTypes,
            item => item.GoalTypeId == "PLAN_CONTENT_AND_CAMPAIGNS"
        );
        Assert.Equal(WorkbenchProjectionFixture.AgentType, asked!.AgentType);
        Assert.Equal("1.0.0", asked.AgentVersion);
        Assert.Equal("1.1.0", asked.ManifestVersion);
        Assert.Equal(context.ActorSubject, asked.ActorSubject);
        Assert.Equal(context.CorrelationId, asked.CorrelationId);
    }

    [Fact]
    public async Task Declaration_OfAnUnknownRelationship_IsNotFound()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        var stranger = fixture.Context() with { RelationshipId = Guid.NewGuid() };

        await Assert.ThrowsAsync<KeyNotFoundException>(() =>
            fixture.Service.GetDeclarationAsync(stranger, default)
        );
        await Assert.ThrowsAsync<KeyNotFoundException>(() =>
            fixture.Service.LoadAsync(stranger, default)
        );
    }

    [Fact]
    public async Task Narrowing_GivesTheBeneficiaryViewToAnAudienceTheAgentDoesNotDeclare()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync(mutateManifest: manifest =>
            manifest["experience"]!["audiences"] = new JsonArray("customer_owner")
        );
        fixture.SetWorkspace();

        var delegated = await fixture.Service.NarrowAsync(
            fixture.Context(WorkbenchAudiences.Delegate),
            default
        );
        var owner = await fixture.Service.NarrowAsync(
            fixture.Context(WorkbenchAudiences.CustomerOwner),
            default
        );

        Assert.Equal(WorkbenchAudiences.Beneficiary, delegated.Audience);
        Assert.Equal(WorkbenchAudiences.CustomerOwner, owner.Audience);
    }

    [Fact]
    public async Task Load_WithoutAWorkspace_SaysSoAndHasNoDeclaration()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();

        var data = await fixture.Service.LoadAsync(fixture.Context(), default);

        Assert.Null(data.Workspace);
        Assert.Null(data.Declaration);
        Assert.Contains("The employment workspace is not available yet.", data.Limitations);
        Assert.Contains(
            "The agent's experience declaration is not available yet.",
            data.Limitations
        );
        Assert.Equal("relationship-7", data.Version);
        Assert.Equal(WorkbenchAudiences.CustomerOwner, data.Audience);
        fixture.Manifests.Verify(
            item =>
                item.GetAsync(It.IsAny<AdmittedManifestRequest>(), It.IsAny<CancellationToken>()),
            Times.Never
        );
    }

    [Fact]
    public async Task Load_ForARelationshipBoundToNoAgentVersion_HasNoDeclaration()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync(professionalVersion: null);
        fixture.SetWorkspace();

        var data = await fixture.Service.LoadAsync(fixture.Context(), default);

        Assert.NotNull(data.Workspace);
        Assert.Null(data.Declaration);
        Assert.Contains(
            "The agent's experience declaration is not available yet.",
            data.Limitations
        );
    }

    [Fact]
    public async Task Load_WhenTheManifestCannotBeRead_SaysSoInsteadOfFailing()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync(withDeclaration: false);
        fixture.SetWorkspace();
        fixture
            .Manifests.SetupSequence(item =>
                item.GetAsync(It.IsAny<AdmittedManifestRequest>(), It.IsAny<CancellationToken>())
            )
            .ThrowsAsync(new HttpRequestException("adapter down"))
            .ReturnsAsync((System.Text.Json.JsonDocument?)null);

        var thrown = await fixture.Service.LoadAsync(fixture.Context(), default);
        var empty = await fixture.Service.LoadAsync(fixture.Context(), default);

        const string Expected = "The agent's experience declaration could not be read right now.";
        Assert.Contains(Expected, thrown.Limitations);
        Assert.Contains(Expected, empty.Limitations);
        Assert.Null(thrown.Declaration);
        Assert.Null(empty.Declaration);
    }

    [Fact]
    public async Task Load_DistinguishesAnUndeclaredExperienceFromAnIncompatibleOne()
    {
        var undeclared = await WorkbenchProjectionFixture.CreateAsync(mutateManifest: manifest =>
            manifest.AsObject().Remove("experience")
        );
        undeclared.SetWorkspace();
        var incompatible = await WorkbenchProjectionFixture.CreateAsync(mutateManifest: manifest =>
            manifest["experience"]!["contractVersion"] = "2.0.0"
        );
        incompatible.SetWorkspace();

        var first = await undeclared.Service.LoadAsync(undeclared.Context(), default);
        var second = await incompatible.Service.LoadAsync(incompatible.Context(), default);

        Assert.Contains(
            "This agent has not declared a workbench experience, so the standard workspace applies.",
            first.Limitations
        );
        Assert.Contains(
            "This agent's experience declaration is not compatible with the workbench.",
            second.Limitations
        );
        Assert.Null(first.Declaration);
        Assert.Null(second.Declaration);
    }

    [Fact]
    public async Task Load_WhenAnOwnerFails_LeavesALimitationPerOwnerAndKeepsTheRest()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        fixture.SetExecution(Execution);
        fixture.ConfigurationStore.FailNth(1, 2);
        fixture.ReviewStore.FailNth(1);

        var data = await fixture.Service.LoadAsync(fixture.Context(), default);

        Assert.Empty(data.Goals);
        Assert.Empty(data.Skills);
        Assert.Empty(data.Reviews);
        Assert.Same(Execution, data.Execution);
        Assert.Contains("Goals could not be read right now.", data.Limitations);
        Assert.Contains("Capabilities could not be read right now.", data.Limitations);
        Assert.Contains("Performance reviews could not be read right now.", data.Limitations);
        Assert.DoesNotContain("Work in progress is not reported right now.", data.Limitations);
    }

    [Fact]
    public async Task Load_WhenTheExecutionOwnerIsSilentOrFails_ReportsItExactlyOnce()
    {
        const string Silent = "Work in progress is not reported right now.";
        var silent = await WorkbenchProjectionFixture.CreateAsync();
        silent.SetWorkspace();
        silent.SetExecution(null);
        var failing = await WorkbenchProjectionFixture.CreateAsync();
        failing.SetWorkspace();
        failing
            .Owners.Setup(item =>
                item.GetExecutionAsync(
                    It.IsAny<RelationshipOwnerContext>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ThrowsAsync(new TimeoutException());

        var first = await silent.Service.LoadAsync(silent.Context(), default);
        var second = await failing.Service.LoadAsync(failing.Context(), default);

        Assert.Single(first.Limitations, Silent);
        Assert.Single(second.Limitations, Silent);
        Assert.Null(first.Execution);
        Assert.Null(second.Execution);
    }

    [Fact]
    public async Task Load_PassesTheCallerAndTheRelationshipVersionToTheExecutionOwner()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        RelationshipOwnerContext? asked = null;
        fixture
            .Owners.Setup(item =>
                item.GetExecutionAsync(
                    It.IsAny<RelationshipOwnerContext>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .Callback<RelationshipOwnerContext, CancellationToken>((value, _) => asked = value)
            .ReturnsAsync(Execution);
        var context = fixture.Context();

        await fixture.Service.LoadAsync(context, default);

        Assert.Equal("customer-subject", asked!.ActorSubject);
        Assert.Equal(context.EffectiveRole, asked.EffectiveRole);
        Assert.Equal(7, asked.RelationshipVersion);
        Assert.Equal(fixture.AgentInstanceId, asked.AgentInstanceId);
        Assert.Equal(context.CorrelationId, asked.CorrelationId);
    }

    [Fact]
    public async Task Load_NeverSwallowsCancellation()
    {
        var manifest = await WorkbenchProjectionFixture.CreateAsync(withDeclaration: false);
        manifest.SetWorkspace();
        manifest
            .Manifests.Setup(item =>
                item.GetAsync(It.IsAny<AdmittedManifestRequest>(), It.IsAny<CancellationToken>())
            )
            .ThrowsAsync(new OperationCanceledException());
        var owner = await WorkbenchProjectionFixture.CreateAsync();
        owner.SetWorkspace();
        owner
            .Owners.Setup(item =>
                item.GetExecutionAsync(
                    It.IsAny<RelationshipOwnerContext>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ThrowsAsync(new OperationCanceledException());
        var goals = await WorkbenchProjectionFixture.CreateAsync();
        goals.SetWorkspace();
        using var cancelled = new CancellationTokenSource();
        await cancelled.CancelAsync();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            manifest.Service.LoadAsync(manifest.Context(), default)
        );
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            owner.Service.LoadAsync(owner.Context(), default)
        );
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            goals.Service.LoadAsync(goals.Context(), cancelled.Token)
        );
    }

    [Theory]
    [InlineData(
        """{"induction":"READY","plan":"AGREED","operations":"ACTIVE","performance":"CURRENT"}""",
        "OPERATIONS",
        "READY",
        "AGREED",
        "ACTIVE",
        "CURRENT"
    )]
    [InlineData(
        """{"induction":"READY","operations":"PAUSED"}""",
        "OPERATIONS",
        "READY",
        "NO_PLAN",
        "PAUSED",
        "UNAVAILABLE"
    )]
    [InlineData(
        """{"operations":"ELIGIBLE"}""",
        "OPERATIONS",
        "NOT_STARTED",
        "NO_PLAN",
        "ELIGIBLE",
        "UNAVAILABLE"
    )]
    [InlineData(
        """{"operations":"REASSESSMENT_REQUIRED"}""",
        "OPERATIONS",
        "NOT_STARTED",
        "NO_PLAN",
        "REASSESSMENT_REQUIRED",
        "UNAVAILABLE"
    )]
    [InlineData(
        """{"induction":"READY"}""",
        "PLANNING",
        "READY",
        "NO_PLAN",
        "LOCKED",
        "UNAVAILABLE"
    )]
    [InlineData(
        """{"induction":"READY_WITH_DEFERRED_ITEMS","plan":"GROOMING"}""",
        "PLANNING",
        "READY_WITH_DEFERRED_ITEMS",
        "GROOMING",
        "LOCKED",
        "UNAVAILABLE"
    )]
    [InlineData(
        """{"induction":"IN_PROGRESS","operations":"BLOCKED"}""",
        "INDUCTION",
        "IN_PROGRESS",
        "NO_PLAN",
        "BLOCKED",
        "UNAVAILABLE"
    )]
    [InlineData(
        """{"induction":"invented","plan":7,"operations":null,"performance":"nonsense"}""",
        "INDUCTION",
        "NOT_STARTED",
        "NO_PLAN",
        "LOCKED",
        "UNAVAILABLE"
    )]
    [InlineData(
        """["induction"]""",
        "INDUCTION",
        "NOT_STARTED",
        "NO_PLAN",
        "LOCKED",
        "UNAVAILABLE"
    )]
    public async Task Readiness_IsTakenFromTheWorkspaceOnlyWhenItIsAKnownState(
        string readiness,
        string phase,
        string induction,
        string plan,
        string operations,
        string performance
    )
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace(readiness);

        var projection = await fixture.Service.BuildAsync(fixture.Context(), FullWeb, default);

        Assert.Equal(phase, projection.Phase);
        Assert.Equal(
            new WorkbenchReadiness(induction, plan, operations, performance),
            projection.Readiness
        );
    }

    [Fact]
    public async Task Readiness_WithoutAWorkspace_IsTheLockedDefault()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();

        var projection = await fixture.Service.BuildAsync(fixture.Context(), FullWeb, default);

        Assert.Equal("INDUCTION", projection.Phase);
        Assert.Equal(
            new WorkbenchReadiness("NOT_STARTED", "NO_PLAN", "LOCKED", "UNAVAILABLE"),
            projection.Readiness
        );
    }

    [Fact]
    public async Task Build_OfACompleteRelationship_ReportsCurrentWhenNothingIsMissing()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync(
            mutateManifest: WorkbenchProjectionFixture.TilesForStewardsOnly
        );
        fixture.SetWorkspace(
            """{"induction":"READY","plan":"AGREED","operations":"ACTIVE"}""",
            Plan(),
            "plan-1"
        );
        fixture.SetExecution(Execution);
        fixture
            .Commercial.Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ReturnsAsync(
                new WorkbenchCommercialSnapshot(
                    true,
                    "v1",
                    WorkbenchProjectionFixture.Now.AddDays(10),
                    [
                        new WorkbenchComponentBalance(
                            "CONTENT_DRAFT",
                            "Content drafts",
                            4,
                            10,
                            WorkbenchProjectionFixture.Now.AddDays(10)
                        ),
                    ],
                    false,
                    null
                )
            );
        var goal = await fixture.AddGoalAsync(status: "ACTIVE");

        var projection = await fixture.Service.BuildAsync(fixture.Context(), FullWeb, default);

        Assert.Empty(projection.Limitations);
        Assert.Equal("CURRENT", projection.SourceFreshness);
        Assert.Equal(goal.GoalId, projection.CurrentGoalRef);
        Assert.Equal("plan-1", projection.CurrentPlanVersion);
        Assert.Equal(WorkbenchProjectionService.SchemaVersion, projection.SchemaVersion);
        Assert.Equal("Content drafts", Assert.Single(projection.Components!).Label);
        Assert.Empty(projection.Alerts);
        Assert.Equal("PENDING", projection.EvidenceState);
        Assert.Empty(projection.Tiles);
        Assert.NotEmpty(projection.Blocks);
    }

    [Fact]
    public async Task Build_WithSomeOwnersMissing_IsStale_AndWithNoneIsUnavailable()
    {
        var stale = await WorkbenchProjectionFixture.CreateAsync();
        stale.SetWorkspace();
        stale.SetExecution(null);
        var unavailable = await WorkbenchProjectionFixture.CreateAsync();

        var partial = await stale.Service.BuildAsync(stale.Context(), FullWeb, default);
        var none = await unavailable.Service.BuildAsync(unavailable.Context(), FullWeb, default);

        Assert.Equal("STALE", partial.SourceFreshness);
        Assert.Equal("UNAVAILABLE", none.SourceFreshness);
        Assert.Contains("Work in progress is not reported right now.", partial.Limitations);
    }

    [Fact]
    public async Task Build_ListsTheTilesTheAudienceMaySee_AndAdmitsTheyAreNotYetMeasured()
    {
        var owner = await WorkbenchProjectionFixture.CreateAsync();
        owner.SetWorkspace();
        var steward = await WorkbenchProjectionFixture.CreateAsync(
            RelationshipParticipantRole.ConstitutionalAuthority
        );
        steward.SetWorkspace();
        var beneficiary = await WorkbenchProjectionFixture.CreateAsync(
            RelationshipParticipantRole.OutcomeOwner
        );
        beneficiary.SetWorkspace();

        var ownerView = await owner.Service.BuildAsync(owner.Context(), FullWeb, default);
        var stewardView = await steward.Service.BuildAsync(steward.Context(), FullWeb, default);
        var beneficiaryView = await beneficiary.Service.BuildAsync(
            beneficiary.Context(),
            FullWeb,
            default
        );

        Assert.Equal(5, ownerView.Tiles.Count);
        Assert.Equal(4, stewardView.Tiles.Count);
        Assert.DoesNotContain(stewardView.Tiles, tile => tile.TileId == "PLAN_REVIEW_TILE");
        Assert.Empty(beneficiaryView.Tiles);
        var tile = ownerView.Tiles.Single(item => item.TileId == "PROFILE_COVERAGE_TILE");
        Assert.Equal("PROFILE_COVERAGE", tile.MeasureId);
        Assert.Equal("Profile coverage", tile.Label);
        Assert.Equal(WorkbenchProjectionService.NotReported, tile.Value);
        Assert.Equal("PERCENT", tile.Unit);
        Assert.Equal("UNAVAILABLE", tile.Freshness);
        Assert.Equal("Customer confirmation", tile.Owner);
        Assert.Equal("METRIC", tile.BlockType);
        Assert.Contains(
            "Measure values are not yet reported by their owners.",
            ownerView.Limitations
        );
        Assert.DoesNotContain(
            "Measure values are not yet reported by their owners.",
            beneficiaryView.Limitations
        );
    }

    [Fact]
    public async Task Build_OffersTheGoalFormsOnlyWhileThereIsNoGoalAndTheRelationshipRuns()
    {
        var open = await WorkbenchProjectionFixture.CreateAsync();
        open.SetWorkspace();
        var withGoal = await WorkbenchProjectionFixture.CreateAsync();
        withGoal.SetWorkspace();
        await withGoal.AddGoalAsync(status: "ACTIVE");
        var stopped = await WorkbenchProjectionFixture.CreateAsync(
            state: EmploymentRelationshipState.StoppedEmergency
        );
        stopped.SetWorkspace();

        var first = await open.Service.BuildAsync(open.Context(), FullWeb, default);
        var second = await withGoal.Service.BuildAsync(withGoal.Context(), FullWeb, default);
        var third = await stopped.Service.BuildAsync(stopped.Context(), FullWeb, default);

        Assert.Contains(first.Blocks, block => block.Id == "goal-form-PLAN_CONTENT_AND_CAMPAIGNS");
        Assert.DoesNotContain(second.Blocks, block => block.Id.StartsWith("goal-form-"));
        Assert.DoesNotContain(third.Blocks, block => block.Id.StartsWith("goal-form-"));
    }

    [Fact]
    public async Task Build_ShowsTheWalletOnlyToAudiencesThatMayViewIt()
    {
        var snapshot = new WorkbenchCommercialSnapshot(
            true,
            "v1",
            WorkbenchProjectionFixture.Now.AddDays(5),
            [
                new WorkbenchComponentBalance(
                    "CONTENT_DRAFT",
                    "Content drafts",
                    1,
                    3,
                    WorkbenchProjectionFixture.Now.AddDays(5)
                ),
            ],
            false,
            AuthenticatedWorkbenchCommercialReader.FiguresMayBeStale
        );
        var owner = await WorkbenchProjectionFixture.CreateAsync();
        owner.SetWorkspace();
        owner
            .Commercial.Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ReturnsAsync(snapshot);
        var beneficiary = await WorkbenchProjectionFixture.CreateAsync(
            RelationshipParticipantRole.OutcomeOwner
        );
        beneficiary.SetWorkspace();

        var ownerView = await owner.Service.BuildAsync(owner.Context(), FullWeb, default);
        var beneficiaryView = await beneficiary.Service.BuildAsync(
            beneficiary.Context(),
            FullWeb,
            default
        );

        Assert.Single(ownerView.Components!);
        Assert.Contains(
            AuthenticatedWorkbenchCommercialReader.FiguresMayBeStale,
            ownerView.Limitations
        );
        Assert.Null(beneficiaryView.Components);
        beneficiary.Commercial.Verify(
            item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>()),
            Times.Never
        );
    }

    [Fact]
    public async Task Build_WhenBillingIsUnavailable_OmitsTheWalletAndSaysWhy()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();

        var projection = await fixture.Service.BuildAsync(fixture.Context(), FullWeb, default);

        Assert.Null(projection.Components);
        Assert.Contains("Billing is not reachable.", projection.Limitations);
    }

    [Fact]
    public async Task Build_ReportsEvidenceStateFromTheLedgerAndFallsBackWhenItIsUnreadable()
    {
        var recorded = await WorkbenchProjectionFixture.CreateAsync();
        recorded.SetWorkspace();
        RecordEvidence(recorded, "STATE_CHANGED");
        var unreadable = await WorkbenchProjectionFixture.CreateAsync();
        unreadable.SetWorkspace();
        unreadable.EvidenceStore.FailNth(1);

        var first = await recorded.Service.BuildAsync(recorded.Context(), FullWeb, default);
        var second = await unreadable.Service.BuildAsync(unreadable.Context(), FullWeb, default);

        Assert.Equal("RECORDED", first.EvidenceState);
        Assert.Equal("UNAVAILABLE", second.EvidenceState);
    }

    [Fact]
    public async Task Build_RecommendsTheNextStepInOrderOfWhatIsMissing()
    {
        var noGoal = await WorkbenchProjectionFixture.CreateAsync();
        noGoal.SetWorkspace();
        var noPlan = await WorkbenchProjectionFixture.CreateAsync();
        noPlan.SetWorkspace();
        await noPlan.AddGoalAsync(status: "ACTIVE");
        var review = await WorkbenchProjectionFixture.CreateAsync();
        review.SetWorkspace("{}", Plan(), "plan-1");
        await review.AddGoalAsync(status: "ACTIVE");
        var decide = await WorkbenchProjectionFixture.CreateAsync();
        decide.SetWorkspace("{}", Plan("""{"state":"AGREED"}"""), "plan-1");
        await decide.AddGoalAsync(status: "ACTIVE");
        await decide.AddSkillAsync("CONTENT_STRATEGY_AND_CALENDAR");
        await decide.AddSkillAsync("VISUAL_AND_VIDEO_CONTENT", status: "SELECTED");
        var idle = await WorkbenchProjectionFixture.CreateAsync();
        idle.SetWorkspace("{}", Plan("""{"state":"AGREED"}"""), "plan-1");
        await idle.AddGoalAsync(status: "ACTIVE");
        var beneficiary = await WorkbenchProjectionFixture.CreateAsync(
            RelationshipParticipantRole.OutcomeOwner
        );
        beneficiary.SetWorkspace();

        var first = await noGoal.Service.BuildAsync(noGoal.Context(), FullWeb, default);
        var second = await noPlan.Service.BuildAsync(noPlan.Context(), FullWeb, default);
        var third = await review.Service.BuildAsync(review.Context(), FullWeb, default);
        var fourth = await decide.Service.BuildAsync(decide.Context(), FullWeb, default);
        var fifth = await idle.Service.BuildAsync(idle.Context(), FullWeb, default);
        var sixth = await beneficiary.Service.BuildAsync(beneficiary.Context(), FullWeb, default);

        Assert.Equal("create_goal", first.RecommendedNextAction!.CommandId);
        Assert.Equal("propose_plan", second.RecommendedNextAction!.CommandId);
        Assert.Equal("accept_plan", third.RecommendedNextAction!.CommandId);
        Assert.Equal("resolve_decision", fourth.RecommendedNextAction!.CommandId);
        Assert.Contains("2 decision(s) need you.", fourth.RecommendedNextAction.Reason);
        Assert.Null(fifth.RecommendedNextAction);
        Assert.Null(sixth.RecommendedNextAction);
    }

    [Fact]
    public async Task Commands_ForTheOwnerOfARunningRelationship_AreEnabledWhereTheStateAllows()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace("{}", Plan(), "plan-1");
        await fixture.AddGoalAsync(status: "ACTIVE");

        var projection = await fixture.Service.BuildAsync(fixture.Context(), FullWeb, default);

        Assert.Equal(
            [
                "create_goal",
                "propose_plan",
                "accept_plan",
                "resolve_decision",
                "change_capability",
                "top_up",
                "export_evidence",
                "pause",
                "stop",
                "handoff",
            ],
            projection.AvailableCommands.Select(item => item.CommandId)
        );
        foreach (
            var id in new[]
            {
                "create_goal",
                "propose_plan",
                "accept_plan",
                "resolve_decision",
                "change_capability",
                "export_evidence",
                "pause",
                "stop",
                "handoff",
            }
        )
            Assert.True(Command(projection, id).Enabled, id);
        var topUp = Command(projection, "top_up");
        Assert.False(topUp.Enabled);
        Assert.Equal(WorkbenchProjectionService.TopUpNotOffered, topUp.DisabledReason);
    }

    [Fact]
    public async Task Commands_ExplainWhyAStepIsNotYetPossible()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace("{}", Plan("""{"state":"DRAFT"}"""), "plan-1");

        var projection = await fixture.Service.BuildAsync(fixture.Context(), FullWeb, default);

        Assert.Equal("Set a goal first.", Command(projection, "propose_plan").DisabledReason);
        Assert.Equal(
            "No plan is ready for review.",
            Command(projection, "accept_plan").DisabledReason
        );
        Assert.True(Command(projection, "create_goal").Enabled);
    }

    [Fact]
    public async Task Commands_OfAStoppedRelationship_AreRefusedWithTheStoppedReason()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync(
            state: EmploymentRelationshipState.StoppedEmergency
        );
        fixture.SetWorkspace("{}", Plan(), "plan-1");
        await fixture.AddGoalAsync(status: "ACTIVE");

        var projection = await fixture.Service.BuildAsync(fixture.Context(), FullWeb, default);

        foreach (
            var id in new[]
            {
                "create_goal",
                "propose_plan",
                "accept_plan",
                "resolve_decision",
                "change_capability",
                "pause",
            }
        )
            Assert.Equal("The relationship is stopped.", Command(projection, id).DisabledReason);
        Assert.Equal("Already stopped.", Command(projection, "stop").DisabledReason);
        Assert.True(Command(projection, "export_evidence").Enabled);
        Assert.True(Command(projection, "handoff").Enabled);
    }

    [Fact]
    public async Task Commands_ForADelegate_CannotManageSpendOrPause_ButMayDecide()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync(
            RelationshipParticipantRole.RelationshipManager
        );
        fixture.SetWorkspace();

        var projection = await fixture.Service.BuildAsync(fixture.Context(), FullWeb, default);

        Assert.True(Command(projection, "create_goal").Enabled);
        Assert.True(Command(projection, "stop").Enabled);
        Assert.Equal("Your role cannot do this.", Command(projection, "pause").DisabledReason);
    }

    [Fact]
    public async Task Commands_ForABeneficiary_AreRefusedExceptTheHandoff()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync(
            RelationshipParticipantRole.OutcomeOwner
        );
        fixture.SetWorkspace();

        var projection = await fixture.Service.BuildAsync(fixture.Context(), FullWeb, default);

        Assert.Equal(WorkbenchAudiences.Beneficiary, projection.Audience);
        foreach (
            var id in new[]
            {
                "create_goal",
                "propose_plan",
                "accept_plan",
                "resolve_decision",
                "change_capability",
                "export_evidence",
                "pause",
                "stop",
            }
        )
            Assert.Equal("Your role cannot do this.", Command(projection, id).DisabledReason);
        Assert.True(Command(projection, "handoff").Enabled);
    }

    [Fact]
    public void Hash_IsAStableTwelveCharacterDigestThatHidesTheIdentifier()
    {
        var id = Guid.Parse("11111111-2222-3333-4444-555555555555");

        var hash = WorkbenchProjectionService.Hash(id);

        Assert.Equal(12, hash.Length);
        Assert.Matches("^[0-9a-f]{12}$", hash);
        Assert.Equal(hash, WorkbenchProjectionService.Hash(id));
        Assert.NotEqual(hash, WorkbenchProjectionService.Hash(Guid.NewGuid()));
        Assert.DoesNotContain(hash, id.ToString("N"));
    }

    [Theory]
    [InlineData("customer_owner", true)]
    [InlineData("delegate", true)]
    [InlineData("steward", false)]
    [InlineData("beneficiary", false)]
    public void Wallet_IsViewableOnlyByTheOwnerAndTheirDelegate(string audience, bool expected) =>
        Assert.Equal(expected, WorkbenchProjectionService.MayViewWallet(audience));

    internal static void RecordEvidence(WorkbenchProjectionFixture fixture, params string[] actions)
    {
        var records = actions
            .Select(action => new Waooaw.ConstitutionalEngine.Grpc.CustomerVisibleEvidenceRecord
            {
                EvidenceRecordId = Guid.NewGuid().ToString(),
                DecisionId = Guid.NewGuid().ToString(),
                AgentId = "agent",
                AgentInstanceId = "relationship",
                ActionType = action,
                ExecutionStatus = "AUTHORIZED",
                EvidenceHash = new string('a', 64),
                RecordedAt = Google.Protobuf.WellKnownTypes.Timestamp.FromDateTimeOffset(
                    WorkbenchProjectionFixture.Now
                ),
                ErasureStatus = "NONE",
            })
            .ToArray();
        fixture
            .EvidenceGateway.Setup(item =>
                item.QueryAsync(
                    It.IsAny<Guid>(),
                    It.IsAny<IReadOnlyCollection<Guid>>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync(records);
    }
}
