// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-02
// Constitutional basis: C-023, C-059, C-063, ADR-051

using Moq;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class WorkbenchCommandServicePlanTests
{
    private static ProposeWorkbenchPlanRequest Propose(
        string version,
        Guid goalId,
        List<ProposeWorkbenchPlanMilestone>? milestones = null,
        string schema = "1.0"
    ) =>
        new(
            schema,
            version,
            goalId,
            milestones ?? [new("PROFILE_CONFIRMED", " Confirm the business profile ")]
        );

    private static AcceptWorkbenchPlanRequest Accept(
        string version,
        bool acknowledged = true,
        string schema = "1.0"
    ) => new(schema, version, acknowledged);

    private static async Task<WorkbenchCommandServiceFixture> FixtureWithGoalAsync(
        string ownerState = "COMPLETED"
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        fixture.CoordinatorAnswers(ownerState);
        return fixture;
    }

    private static void VerifyCoordinated(
        WorkbenchCommandServiceFixture fixture,
        string kind,
        Times times
    ) =>
        fixture.Coordinator.Verify(
            item =>
                item.CoordinateAsync(
                    It.Is<EmploymentCommandCoordinationContext>(context =>
                        context.CommandKind == kind
                    ),
                    It.IsAny<CancellationToken>()
                ),
            times
        );

    [Fact]
    public async Task ProposePlan_SubmitsTheCurrentDraftForReviewAndReportsTheOwnersCompletion()
    {
        var fixture = await FixtureWithGoalAsync();
        var goal = await fixture.AddGoalAsync();
        var context = fixture.Employer();

        var result = await fixture.Commands.ProposePlanAsync(
            context,
            Guid.NewGuid(),
            Propose(await fixture.VersionAsync(), goal.GoalId),
            CancellationToken.None
        );

        Assert.Equal("COMPLETED", result.Body.Status);
        Assert.Equal("plan:plan-1", result.Body.ResourceRef);
        Assert.Equal("workspace-1", result.Body.Version);
        Assert.Equal(context.CorrelationId, result.Body.CorrelationId);
        fixture.Coordinator.Verify(
            item =>
                item.CoordinateAsync(
                    It.Is<EmploymentCommandCoordinationContext>(coordination =>
                        coordination.CommandKind == "SUBMIT_PLAN_FOR_REVIEW"
                        && coordination.TenantId == fixture.TenantId
                        && coordination.RelationshipId == fixture.RelationshipId
                        && coordination.ActorId == fixture.EmployerId
                        && coordination.Command.GetProperty("expectedPlanVersion").GetString()
                            == "plan-1"
                        && coordination.Command.GetProperty("subjectRef").GetString()
                            == "plan:plan-1"
                        && coordination.Command.GetProperty("expectedWorkspaceVersion").GetString()
                            == "workspace-1"
                        && coordination.Command.GetProperty("expectedManifestVersion").GetString()
                            == "manifest-1"
                    ),
                    It.IsAny<CancellationToken>()
                ),
            Times.Once()
        );
    }

    [Theory]
    [InlineData("COMPLETED", "COMPLETED")]
    [InlineData("PARTIAL", "ACCEPTED")]
    [InlineData("UNKNOWN", "ACCEPTED")]
    [InlineData("BLOCKED", "REJECTED")]
    [InlineData("FAILED", "REJECTED")]
    public async Task ProposePlan_ReportsOnlyWhatTheOwnersAnswered(
        string ownerState,
        string expected
    )
    {
        var fixture = await FixtureWithGoalAsync(ownerState);
        var goal = await fixture.AddGoalAsync();

        var result = await fixture.Commands.ProposePlanAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            Propose(await fixture.VersionAsync(), goal.GoalId),
            CancellationToken.None
        );

        Assert.Equal(expected, result.Body.Status);
    }

    [Fact]
    public async Task ProposePlan_ReplaysTheReceiptWithoutCoordinatingTwice()
    {
        var fixture = await FixtureWithGoalAsync();
        var goal = await fixture.AddGoalAsync();
        var key = Guid.NewGuid();
        var request = Propose(await fixture.VersionAsync(), goal.GoalId);

        var first = await fixture.Commands.ProposePlanAsync(
            fixture.Employer(),
            key,
            request,
            CancellationToken.None
        );
        var second = await fixture.Commands.ProposePlanAsync(
            fixture.Employer(),
            key,
            request,
            CancellationToken.None
        );

        Assert.True(second.Replayed);
        Assert.Equal(first.Body.OperationRef, second.Body.OperationRef);
        VerifyCoordinated(fixture, "SUBMIT_PLAN_FOR_REVIEW", Times.Once());
    }

    [Fact]
    public async Task ProposePlan_AfterAnOwnerOutageARetryReplaysTheStoredCommandInsteadOfCoordinatingAgain()
    {
        var fixture = await FixtureWithGoalAsync();
        var goal = await fixture.AddGoalAsync();
        fixture.CoordinatorFails(new InvalidOperationException("coordinator crashed"));
        var key = Guid.NewGuid();
        var request = Propose(await fixture.VersionAsync(), goal.GoalId);

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            fixture.Commands.ProposePlanAsync(
                fixture.Employer(),
                key,
                request,
                CancellationToken.None
            )
        );
        var retried = await fixture.Commands.ProposePlanAsync(
            fixture.Employer(),
            key,
            request,
            CancellationToken.None
        );

        Assert.Equal("ACCEPTED", retried.Body.Status);
        VerifyCoordinated(fixture, "SUBMIT_PLAN_FOR_REVIEW", Times.Once());
    }

    [Theory]
    [InlineData("EMPLOYMENT_INVALID_REQUEST", 400, WorkbenchProblemCodes.RequestInvalid)]
    [InlineData("EMPLOYMENT_VERSION_CONFLICT", 409, WorkbenchProblemCodes.VersionConflict)]
    [InlineData("EMPLOYMENT_IDEMPOTENCY_CONFLICT", 409, WorkbenchProblemCodes.IdempotencyConflict)]
    [InlineData("EMPLOYMENT_BLOCKED", 422, WorkbenchProblemCodes.RequestInvalid)]
    [InlineData("EMPLOYMENT_NOT_ACCESSIBLE", 404, WorkbenchProblemCodes.RequestInvalid)]
    [InlineData("EMPLOYMENT_SOMETHING_ELSE", 503, WorkbenchProblemCodes.Unavailable)]
    public async Task ProposePlan_MapsTheEmploymentProtocolRefusalToATypedProblem(
        string protocolCode,
        int status,
        string code
    )
    {
        var fixture = await FixtureWithGoalAsync();
        var goal = await fixture.AddGoalAsync();
        fixture.CoordinatorFails(new EmploymentProtocolException(protocolCode));

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ProposePlanAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Propose(await fixture.VersionAsync(), goal.GoalId),
                CancellationToken.None
            )
        );

        Assert.Equal(status, failure.Status);
        Assert.Equal(code, failure.Code);
    }

    public static TheoryData<string> InvalidProposals() =>
        new()
        {
            "schema",
            "no-milestones",
            "null-milestones",
            "too-many-milestones",
            "blank-type",
            "blank-title",
            "long-title",
        };

    [Theory]
    [MemberData(nameof(InvalidProposals))]
    public async Task ProposePlan_RejectsAnInvalidRequestBeforeAnyOwnerIsAsked(string defect)
    {
        var fixture = await FixtureWithGoalAsync();
        var goal = await fixture.AddGoalAsync();
        var version = await fixture.VersionAsync();
        var request = defect switch
        {
            "schema" => Propose(version, goal.GoalId, schema: "0.9"),
            "no-milestones" => Propose(version, goal.GoalId, []),
            "null-milestones" => Propose(version, goal.GoalId) with { Milestones = null! },
            "too-many-milestones" => Propose(
                version,
                goal.GoalId,
                Enumerable
                    .Range(0, 51)
                    .Select(index => new ProposeWorkbenchPlanMilestone(
                        "PROFILE_CONFIRMED",
                        $"Step {index}"
                    ))
                    .ToList()
            ),
            "blank-type" => Propose(version, goal.GoalId, [new(" ", "Title")]),
            "blank-title" => Propose(version, goal.GoalId, [new("PROFILE_CONFIRMED", " ")]),
            _ => Propose(version, goal.GoalId, [new("PROFILE_CONFIRMED", new string('t', 241))]),
        };

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ProposePlanAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                request,
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        VerifyCoordinated(fixture, "SUBMIT_PLAN_FOR_REVIEW", Times.Never());
    }

    [Fact]
    public async Task ProposePlan_IsRefusedForAnAudienceThatMayNotDecide()
    {
        var fixture = await FixtureWithGoalAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ProposePlanAsync(
                fixture.Evaluator(),
                Guid.NewGuid(),
                Propose("relationship-1", Guid.NewGuid()),
                CancellationToken.None
            )
        );

        Assert.Equal(403, failure.Status);
    }

    [Fact]
    public async Task ProposePlan_IsRefusedOnAStoppedRelationship()
    {
        var fixture = await FixtureWithGoalAsync();
        var goal = await fixture.AddGoalAsync();
        await fixture.SetStateAsync(EmploymentRelationshipState.StoppedEmergency);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ProposePlanAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Propose(await fixture.VersionAsync(), goal.GoalId),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
    }

    [Fact]
    public async Task ProposePlan_IsRefusedWhenTheCustomerSawAnOlderVersion()
    {
        var fixture = await FixtureWithGoalAsync();
        var goal = await fixture.AddGoalAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ProposePlanAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Propose("relationship-0", goal.GoalId),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.VersionConflict, failure.Code);
    }

    [Fact]
    public async Task ProposePlan_IsUnavailableWithoutAnExperienceDeclaration()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync(withDeclaration: false);
        var goal = await fixture.AddGoalAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ProposePlanAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Propose(await fixture.VersionAsync(), goal.GoalId),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
    }

    [Fact]
    public async Task ProposePlan_RefusesAMilestoneTypeTheAgentDoesNotDeclare()
    {
        var fixture = await FixtureWithGoalAsync();
        var goal = await fixture.AddGoalAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ProposePlanAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Propose(await fixture.VersionAsync(), goal.GoalId, [new("TELEPORT_TO_MARS", "Go")]),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Contains("milestone type is not declared", failure.Detail);
    }

    [Fact]
    public async Task ProposePlan_ReportsAnUnknownGoalAsNotFound()
    {
        var fixture = await FixtureWithGoalAsync();

        await Assert.ThrowsAsync<KeyNotFoundException>(async () =>
            await fixture.Commands.ProposePlanAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Propose(await fixture.VersionAsync(), Guid.NewGuid()),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task ProposePlan_IsUnavailableWhenTheAgentHasPreparedNoDraft()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync(withPlan: false);
        var goal = await fixture.AddGoalAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ProposePlanAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Propose(await fixture.VersionAsync(), goal.GoalId),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
        Assert.Contains("plan draft", failure.Detail);
    }

    [Fact]
    public async Task AcceptPlan_AsksTheOwnersToAcceptTheExactPlanVersionTheCustomerSaw()
    {
        var fixture = await FixtureWithGoalAsync();

        var result = await fixture.Commands.AcceptPlanAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            "plan-1",
            Accept(await fixture.VersionAsync()),
            CancellationToken.None
        );

        Assert.Equal("COMPLETED", result.Body.Status);
        Assert.Equal("plan:plan-1", result.Body.ResourceRef);
        fixture.Coordinator.Verify(
            item =>
                item.CoordinateAsync(
                    It.Is<EmploymentCommandCoordinationContext>(coordination =>
                        coordination.CommandKind == "ACCEPT_PLAN_VERSION"
                        && coordination.Command.GetProperty("expectedPlanVersion").GetString()
                            == "plan-1"
                        && coordination
                            .Command.GetProperty("expectedDecisionSpaceVersion")
                            .GetInt32() == 1
                        && coordination.Command.GetProperty("expectedWbeSourceVersion").GetString()
                            == "wbe-1"
                        && !string.IsNullOrWhiteSpace(
                            coordination.Command.GetProperty("acknowledgement").GetString()
                        )
                    ),
                    It.IsAny<CancellationToken>()
                ),
            Times.Once()
        );
    }

    [Fact]
    public async Task AcceptPlan_AcceptsThePlanVersionAsTheExpectedVersion()
    {
        var fixture = await FixtureWithGoalAsync("PARTIAL");

        var result = await fixture.Commands.AcceptPlanAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            "plan-1",
            Accept("plan-1"),
            CancellationToken.None
        );

        Assert.Equal("ACCEPTED", result.Body.Status);
    }

    [Fact]
    public async Task AcceptPlan_ReplaysTheReceiptWithoutCoordinatingTwice()
    {
        var fixture = await FixtureWithGoalAsync();
        var key = Guid.NewGuid();

        await fixture.Commands.AcceptPlanAsync(
            fixture.Employer(),
            key,
            "plan-1",
            Accept("plan-1"),
            CancellationToken.None
        );
        var replay = await fixture.Commands.AcceptPlanAsync(
            fixture.Employer(),
            key,
            "plan-1",
            Accept("plan-1"),
            CancellationToken.None
        );

        Assert.True(replay.Replayed);
        VerifyCoordinated(fixture, "ACCEPT_PLAN_VERSION", Times.Once());
    }

    [Theory]
    [InlineData("schema")]
    [InlineData("blank-plan")]
    [InlineData("long-plan")]
    [InlineData("unacknowledged")]
    public async Task AcceptPlan_RejectsAnInvalidRequest(string defect)
    {
        var fixture = await FixtureWithGoalAsync();
        var version = await fixture.VersionAsync();
        var plan = defect switch
        {
            "blank-plan" => " ",
            "long-plan" => new string('p', 129),
            _ => "plan-1",
        };
        var request = defect switch
        {
            "schema" => Accept(version, schema: "3.0"),
            "unacknowledged" => Accept(version, acknowledged: false),
            _ => Accept(version),
        };

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.AcceptPlanAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                plan,
                request,
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
    }

    [Fact]
    public async Task AcceptPlan_IsRefusedForAnyoneButTheEmployer()
    {
        var fixture = await FixtureWithGoalAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.AcceptPlanAsync(
                fixture.Manager(),
                Guid.NewGuid(),
                "plan-1",
                Accept("plan-1"),
                CancellationToken.None
            )
        );

        Assert.Equal(403, failure.Status);
        Assert.Equal(WorkbenchCommandService.RoleDetail, failure.Detail);
    }

    [Fact]
    public async Task AcceptPlan_IsRefusedOnAStoppedRelationship()
    {
        var fixture = await FixtureWithGoalAsync();
        await fixture.SetStateAsync(EmploymentRelationshipState.StoppedEmergency);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.AcceptPlanAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                "plan-1",
                Accept("plan-1"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
    }

    [Fact]
    public async Task AcceptPlan_IsRefusedWhenTheCustomerSawAnOlderVersion()
    {
        var fixture = await FixtureWithGoalAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.AcceptPlanAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                "plan-1",
                Accept("relationship-0"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
    }

    [Fact]
    public async Task AcceptPlan_IsRefusedWhenTheAgentHasSupersededThePlanVersion()
    {
        var fixture = await FixtureWithGoalAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.AcceptPlanAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                "plan-0",
                Accept(await fixture.VersionAsync()),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.VersionConflict, failure.Code);
        VerifyCoordinated(fixture, "ACCEPT_PLAN_VERSION", Times.Never());
    }

    [Fact]
    public async Task AcceptPlan_IsUnavailableWithoutAWorkspace()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync(withWorkspace: false);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.AcceptPlanAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                "plan-1",
                Accept(await fixture.VersionAsync()),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
        Assert.Contains("workspace", failure.Detail);
    }

    [Fact]
    public async Task AcceptPlan_MapsAnEmploymentVersionConflictToAConflict()
    {
        var fixture = await FixtureWithGoalAsync();
        fixture.CoordinatorFails(new EmploymentProtocolException("EMPLOYMENT_VERSION_CONFLICT"));

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.AcceptPlanAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                "plan-1",
                Accept("plan-1"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.VersionConflict, failure.Code);
    }
}
