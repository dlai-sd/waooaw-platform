// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01, C6-02
// Constitutional basis: C-001, C-005, C-023, C-026, C-059, C-063, ADR-051

using System.Security.Claims;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

/// <summary>
/// The workbench HTTP surface end to end against real services: every route reaches its own operation, the
/// envelope rules (correlation, key, strong sign-in, body) hold, and every failure is a problem that names the cause.
/// </summary>
public sealed class WorkbenchSurfaceControllerCoverageTests
{
    private static readonly CancellationToken Ct = CancellationToken.None;

    private static readonly string[] ReadNames =
    [
        "workbench",
        "goals",
        "goal",
        "versions",
        "plan",
        "capabilities",
        "workItems",
        "decisions",
        "monitor",
        "narratives",
        "wallet",
        "evidence",
    ];

    private static readonly string[] PagedNames =
    [
        "goals",
        "versions",
        "workItems",
        "decisions",
        "narratives",
        "evidence",
    ];

    private static readonly string[] CommandNames =
    [
        "createGoal",
        "reviseGoal",
        "proposePlan",
        "acceptPlan",
        "capability",
        "resolve",
        "topup",
        "export",
        "stop",
        "pause",
        "handoff",
        "consume",
        "subscription",
    ];

    private static readonly string[] StrongAuthNames =
    [
        "acceptPlan",
        "capability",
        "resolve",
        "topup",
        "subscription",
    ];

    public static IEnumerable<object[]> Reads => ReadNames.Select(name => new object[] { name });

    public static IEnumerable<object[]> Commands =>
        CommandNames.Select(name => new object[] { name });

    public static IEnumerable<object[]> StrongAuthCommands =>
        StrongAuthNames.Select(name => new object[] { name });

    public static IEnumerable<object[]> BadPaging =>
        PagedNames.SelectMany(name =>
            new[]
            {
                new object[] { name, null!, 0, "limit must be 1 to 100." },
                new object[] { name, null!, 101, "limit must be 1 to 100." },
                new object[]
                {
                    name,
                    new string('c', 257),
                    10,
                    "cursor must be 1 to 256 characters.",
                },
                new object[] { name, "###", 10, "cursor is not valid." },
            }
        );

    private static Task<IActionResult> Read(
        WorkbenchController controller,
        string name,
        Guid relationship,
        Guid goal,
        string? cursor = null,
        int? limit = null
    ) =>
        name switch
        {
            "workbench" => controller.GetWorkbenchAsync(relationship, Ct),
            "goals" => controller.ListGoalsAsync(relationship, cursor, limit, Ct),
            "goal" => controller.GetGoalAsync(relationship, goal, Ct),
            "versions" => controller.ListGoalVersionsAsync(relationship, goal, cursor, limit, Ct),
            "plan" => controller.GetCurrentPlanAsync(relationship, Ct),
            "capabilities" => controller.ListCapabilitiesAsync(relationship, Ct),
            "workItems" => controller.ListWorkItemsAsync(relationship, cursor, limit, Ct),
            "decisions" => controller.ListDecisionsAsync(relationship, cursor, limit, Ct),
            "monitor" => controller.GetMonitorAsync(relationship, Ct),
            "narratives" => controller.ListNarrativesAsync(relationship, cursor, limit, Ct),
            "wallet" => controller.GetWalletAsync(relationship, Ct),
            "evidence" => controller.ListEvidenceAsync(relationship, cursor, limit, Ct),
            _ => throw new ArgumentOutOfRangeException(nameof(name), name, null),
        };

    private static Task<IActionResult> Command(
        WorkbenchController controller,
        string name,
        Guid relationship,
        Guid goal
    ) =>
        name switch
        {
            "createGoal" => controller.CreateGoalAsync(relationship, Ct),
            "reviseGoal" => controller.ReviseGoalAsync(relationship, goal, Ct),
            "proposePlan" => controller.ProposePlanAsync(relationship, Ct),
            "acceptPlan" => controller.AcceptPlanAsync(
                relationship,
                WorkbenchCommandServiceFixture.PlanVersion,
                Ct
            ),
            "capability" => controller.CommandCapabilityAsync(
                relationship,
                WorkbenchCommandServiceFixture.SkillId,
                Ct
            ),
            "resolve" => controller.ResolveDecisionAsync(relationship, goal, Ct),
            "topup" => controller.CreateTopupAsync(relationship, Ct),
            "export" => controller.ExportEvidenceAsync(relationship, Ct),
            "stop" => controller.StopAsync(relationship, Ct),
            "pause" => controller.PauseAsync(relationship, Ct),
            "handoff" => controller.CreateHandoffAsync(relationship, Ct),
            "consume" => controller.ConsumeHandoffAsync(relationship, Ct),
            "subscription" => controller.ChangeSubscriptionAsync(relationship, Ct),
            _ => throw new ArgumentOutOfRangeException(nameof(name), name, null),
        };

    private static string Json(string envelope, string members = "") =>
        members.Length == 0 ? "{" + envelope + "}" : "{" + envelope + "," + members + "}";

    private static string BodyFor(string name, string envelope, Guid goal) =>
        name switch
        {
            "createGoal" => Json(
                envelope,
                "\"goalTypeId\":\"UNDERSTAND_CURRENT_POSITION\",\"title\":\"Know where we stand\","
                    + "\"parameters\":{\"BUSINESS_DOMAIN\":\"bakery\",\"PRIMARY_LOCATION\":\"Pune\"}"
            ),
            "reviseGoal" => Json(
                envelope,
                "\"parameters\":{\"BUSINESS_DOMAIN\":\"bakery\",\"PRIMARY_LOCATION\":\"Pune\"},"
                    + "\"reason\":\"The location changed\""
            ),
            "proposePlan" => Json(
                envelope,
                $"\"goalId\":\"{goal:D}\",\"milestones\":[{{\"milestoneTypeId\":\"PROFILE_CONFIRMED\",\"title\":\"Profile confirmed\"}}]"
            ),
            "acceptPlan" => Json(envelope, "\"acknowledgedLimitations\":true"),
            "capability" => Json(envelope, "\"command\":\"PAUSE\""),
            "resolve" => Json(envelope, "\"resolution\":\"APPROVE\""),
            "topup" => Json(envelope, "\"componentId\":\"lead_batch\",\"quantity\":1"),
            "export" => Json(envelope, "\"scope\":\"RELATIONSHIP\",\"format\":\"JSON\""),
            "handoff" => Json(envelope, "\"purpose\":\"WEB_WORKBENCH\""),
            "consume" => "{\"schemaVersion\":\"1.0\",\"destinationRef\":\"unknown\"}",
            "subscription" => Json(envelope, "\"kind\":\"UPGRADE\""),
            _ => Json(envelope),
        };

    private static ObjectResult Problem(IActionResult result, int status, string code)
    {
        var objectResult = Assert.IsType<ObjectResult>(result);
        Assert.Equal(status, objectResult.StatusCode);
        Assert.Contains("application/problem+json", objectResult.ContentTypes);
        var problem = Assert.IsType<WorkbenchProblem>(objectResult.Value);
        Assert.Equal(code, problem.Code);
        Assert.Equal(status, problem.Status);
        return objectResult;
    }

    private static WorkbenchProblem Detail(IActionResult result, int status, string code)
    {
        var problem = Assert.IsType<WorkbenchProblem>(Problem(result, status, code).Value);
        Assert.NotNull(problem.Detail);
        return problem;
    }

    private static T Body<T>(IActionResult result, int status)
    {
        var objectResult = Assert.IsAssignableFrom<ObjectResult>(result);
        Assert.Equal(status, objectResult.StatusCode ?? StatusCodes.Status200OK);
        return Assert.IsType<T>(objectResult.Value);
    }

    [Theory]
    [MemberData(nameof(Reads))]
    public async Task Disabled_EveryReadAnswersWorkbenchDisabledAndEchoesTheCorrelationId(
        string name
    )
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var correlation = Guid.NewGuid();
        var controller = rig.Controller(
            rig.Fixture.EmployerId,
            enabled: false,
            configure: context =>
                context.Request.Headers["X-Correlation-ID"] = correlation
                    .ToString("D")
                    .ToUpperInvariant()
        );

        var result = await Read(controller, name, rig.RelationshipId, Guid.NewGuid());

        var problem = Assert.IsType<WorkbenchProblem>(
            Problem(result, 404, WorkbenchProblemCodes.Disabled).Value
        );
        Assert.Equal(correlation.ToString("D"), problem.CorrelationId);
        Assert.Equal(
            correlation.ToString("D"),
            controller.Response.Headers["X-Correlation-ID"].ToString()
        );
        Assert.Equal("https://waooaw.com/problems/workbench-disabled", problem.Type);
    }

    [Theory]
    [MemberData(nameof(Commands))]
    public async Task Disabled_EveryCommandAnswersWorkbenchDisabledBeforeReadingTheBody(string name)
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var controller = rig.Controller(rig.Fixture.EmployerId, enabled: false);

        var result = await Command(controller, name, rig.RelationshipId, Guid.NewGuid());

        Problem(result, 404, WorkbenchProblemCodes.Disabled);
    }

    [Theory]
    [MemberData(nameof(Reads))]
    public async Task Read_ByTheEmployer_ReturnsItsProjectionWithTheRelationshipVersionAsEtag(
        string name
    )
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var goal = await rig.Fixture.AddGoalAsync();
        rig.Fixture.Commercial.Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ReturnsAsync(
                new WorkbenchCommercialSnapshot(
                    true,
                    "wallet-1",
                    DateTimeOffset.UtcNow.AddDays(10),
                    [],
                    true,
                    null
                )
            );
        var controller = rig.Owner();

        var result = await Read(controller, name, rig.RelationshipId, goal.GoalId);

        var ok = Assert.IsType<OkObjectResult>(result);
        Assert.Equal(
            name switch
            {
                "workbench" => typeof(WorkbenchProjection),
                "goals" => typeof(WorkbenchGoalList),
                "goal" => typeof(WorkbenchGoal),
                "versions" => typeof(WorkbenchGoalVersionList),
                "plan" => typeof(WorkbenchPlan),
                "capabilities" => typeof(WorkbenchCapabilityList),
                "workItems" => typeof(WorkbenchWorkItemList),
                "decisions" => typeof(WorkbenchDecisionList),
                "monitor" => typeof(WorkbenchMonitor),
                "narratives" => typeof(WorkbenchNarrativeList),
                "wallet" => typeof(WorkbenchWallet),
                _ => typeof(WorkbenchEvidenceList),
            },
            ok.Value!.GetType()
        );
        Assert.Equal("\"relationship-1\"", controller.Response.Headers.ETag.ToString());
    }

    [Fact]
    public async Task Read_OfGoals_ReturnsTheStoredGoalsAndTheGoalByItsId()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var goal = await rig.Fixture.AddGoalAsync(title: "Know where we stand");
        var second = await rig.Fixture.AddGoalAsync(title: "Find new customers", skillId: null);

        var list = Body<WorkbenchGoalList>(
            await rig.Owner().ListGoalsAsync(rig.RelationshipId, null, null, Ct),
            200
        );
        var one = Body<WorkbenchGoal>(
            await rig.Owner().GetGoalAsync(rig.RelationshipId, goal.GoalId, Ct),
            200
        );

        Assert.Equal(
            new[] { goal.GoalId, second.GoalId }.Order(),
            list.Items.Select(item => item.GoalId).Order()
        );
        Assert.Equal(goal.GoalId, one.Goal.GoalId);
        Assert.Equal("Know where we stand", one.Goal.Title);
        Assert.Equal("bakery", one.Parameters["BUSINESS_DOMAIN"]);
    }

    [Fact]
    public async Task Read_OfGoalsWithAPageLimit_ReturnsACursorThatContinuesTheList()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var first = await rig.Fixture.AddGoalAsync(title: "One", skillId: null);
        var second = await rig.Fixture.AddGoalAsync(title: "Two", skillId: null);

        var page = Body<WorkbenchGoalList>(
            await rig.Owner().ListGoalsAsync(rig.RelationshipId, null, 1, Ct),
            200
        );
        var next = Body<WorkbenchGoalList>(
            await rig.Owner().ListGoalsAsync(rig.RelationshipId, page.NextCursor, 1, Ct),
            200
        );

        Assert.Single(page.Items);
        Assert.NotNull(page.NextCursor);
        Assert.Single(next.Items);
        Assert.NotEqual(page.Items[0].GoalId, next.Items[0].GoalId);
        Assert.Equal(
            new[] { first.GoalId, second.GoalId }.Order(),
            new[] { page.Items[0].GoalId, next.Items[0].GoalId }.Order()
        );
    }

    [Theory]
    [MemberData(nameof(BadPaging))]
    public async Task Read_OfAPagedList_WithABadCursorOrLimit_IsRejectedWithTheViolation(
        string name,
        string? cursor,
        int limit,
        string expected
    )
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();

        var result = await Read(
            rig.Owner(),
            name,
            rig.RelationshipId,
            Guid.NewGuid(),
            cursor,
            limit
        );

        Assert.Equal(expected, Detail(result, 400, WorkbenchProblemCodes.RequestInvalid).Detail);
    }

    [Theory]
    [InlineData("goal")]
    [InlineData("versions")]
    public async Task Read_OfAnUnknownGoal_IsNotFound(string name)
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();

        var result = await Read(rig.Owner(), name, rig.RelationshipId, Guid.NewGuid());

        Assert.Equal(
            "The resource was not found.",
            Detail(result, 404, WorkbenchProblemCodes.RequestInvalid).Detail
        );
    }

    [Fact]
    public async Task Read_OfThePlanWithoutAWorkspace_IsNotFoundAndLeavesNoEtag()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync(withWorkspace: false);
        var controller = rig.Owner();

        var result = await controller.GetCurrentPlanAsync(rig.RelationshipId, Ct);

        Problem(result, 404, WorkbenchProblemCodes.RequestInvalid);
        Assert.False(controller.Response.Headers.ContainsKey("ETag"));
    }

    [Fact]
    public async Task Read_WithAnInvalidCorrelationHeader_IsRejectedAndTheFallbackIdentifiesTheProblem()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var controller = rig.Controller(
            rig.Fixture.EmployerId,
            configure: context => context.Request.Headers["X-Correlation-ID"] = "not-a-uuid"
        );
        controller.HttpContext.TraceIdentifier = "trace-7";

        var problem = Detail(
            await controller.GetWorkbenchAsync(rig.RelationshipId, Ct),
            400,
            WorkbenchProblemCodes.RequestInvalid
        );

        Assert.Equal("X-Correlation-ID must be a UUID.", problem.Detail);
        Assert.Equal("trace-7", problem.CorrelationId);
    }

    [Fact]
    public async Task Read_WithoutACorrelationHeader_UsesTheTokenClaimThenTheTraceIdentifier()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var withClaim = rig.Controller(
            rig.Fixture.EmployerId,
            enabled: false,
            configure: context => context.Request.Headers.Remove("X-Correlation-ID"),
            extraClaims: [new Claim("correlation_id", "claim-corr-1")]
        );
        var withoutClaim = rig.Controller(
            rig.Fixture.EmployerId,
            enabled: false,
            configure: context =>
            {
                context.Request.Headers.Remove("X-Correlation-ID");
                context.TraceIdentifier = "trace-9";
            }
        );

        var fromClaim = Assert.IsType<WorkbenchProblem>(
            Problem(
                await withClaim.GetWorkbenchAsync(rig.RelationshipId, Ct),
                404,
                WorkbenchProblemCodes.Disabled
            ).Value
        );
        var fromTrace = Assert.IsType<WorkbenchProblem>(
            Problem(
                await withoutClaim.GetWorkbenchAsync(rig.RelationshipId, Ct),
                404,
                WorkbenchProblemCodes.Disabled
            ).Value
        );

        Assert.Equal("claim-corr-1", fromClaim.CorrelationId);
        Assert.Equal("trace-9", fromTrace.CorrelationId);
    }

    [Fact]
    public async Task Command_WithAnInvalidCorrelationHeader_IsRejectedAsInvalid()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var controller = rig.Controller(
            rig.Fixture.EmployerId,
            Json(await rig.EnvelopeAsync()),
            configure: context => context.Request.Headers["X-Correlation-ID"] = "nope"
        );

        var problem = Detail(
            await controller.StopAsync(rig.RelationshipId, Ct),
            400,
            WorkbenchProblemCodes.RequestInvalid
        );

        Assert.Equal("X-Correlation-ID is required and must be a UUID.", problem.Detail);
    }

    [Theory]
    [InlineData(ClaimTypes.NameIdentifier)]
    [InlineData("sub")]
    public async Task Read_IdentifiesTheCallerFromTheFallbackSubjectClaims(string claimType)
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var controller = rig.Controller(rig.Fixture.EmployerId, participantClaim: claimType);

        var result = await controller.GetWorkbenchAsync(rig.RelationshipId, Ct);

        var projection = Body<WorkbenchProjection>(result, 200);
        Assert.Equal(rig.RelationshipId, projection.RelationshipRef);
    }

    [Fact]
    public async Task Read_PrefersTheParticipantClaimOverTheOtherSubjectClaims()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var controller = rig.Controller(
            rig.Fixture.EmployerId,
            extraClaims:
            [
                new Claim(ClaimTypes.NameIdentifier, Guid.NewGuid().ToString("D")),
                new Claim("sub", "not-a-guid"),
            ]
        );

        var result = await controller.GetWorkbenchAsync(rig.RelationshipId, Ct);

        Assert.IsType<OkObjectResult>(result);
    }

    [Theory]
    [InlineData("not-a-guid")]
    [InlineData("")]
    public async Task Read_WithASubjectThatIsNotAParticipantId_IsForbidden(string subject)
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var controller = rig.Controller(
            rig.Fixture.EmployerId,
            participantClaim: null,
            extraClaims: [new Claim("sub", subject)]
        );

        var result = await controller.GetWorkbenchAsync(rig.RelationshipId, Ct);

        Assert.Equal(
            "The relationship is not accessible.",
            Detail(result, 403, WorkbenchProblemCodes.RequestInvalid).Detail
        );
    }

    [Theory]
    [InlineData("not-a-guid")]
    [InlineData("")]
    public async Task Read_WithATenantThatIsNotAGuid_IsForbidden(string tenant)
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var controller = rig.Controller(
            rig.Fixture.EmployerId,
            configure: context => context.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenant
        );

        var result = await controller.GetWorkbenchAsync(rig.RelationshipId, Ct);

        Problem(result, 403, WorkbenchProblemCodes.RequestInvalid);
    }

    [Fact]
    public async Task Read_WithATenantThatIsNotText_IsForbidden()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var controller = rig.Controller(
            rig.Fixture.EmployerId,
            configure: context =>
                context.Items[TenantIsolationMiddleware.TenantIdItemKey] = rig.Fixture.TenantId
        );

        var result = await controller.GetWorkbenchAsync(rig.RelationshipId, Ct);

        Problem(result, 403, WorkbenchProblemCodes.RequestInvalid);
    }

    [Fact]
    public async Task Wallet_ForTheAccountOwner_ReportsTheReaderSnapshot()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var periodEnd = DateTimeOffset.UtcNow.AddDays(12);
        rig.Fixture.Commercial.Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ReturnsAsync(
                new WorkbenchCommercialSnapshot(true, "wallet-3", periodEnd, [], true, null)
            );

        var wallet = Body<WorkbenchWallet>(
            await rig.Owner().GetWalletAsync(rig.RelationshipId, Ct),
            200
        );

        Assert.Equal(rig.RelationshipId, wallet.RelationshipRef);
        Assert.Equal(periodEnd, wallet.PeriodEnd);
        Assert.False(wallet.TopUpAvailable);
        Assert.False(wallet.AskAccountOwner);
    }

    [Fact]
    public async Task Wallet_WhenBillingIsUnavailable_NamesTheCommercialOwnerAsTheCause()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();

        var result = await rig.Owner().GetWalletAsync(rig.RelationshipId, Ct);

        Detail(result, 503, "SPEND_COMMERCIAL_UNAVAILABLE");
    }

    [Fact]
    public async Task Wallet_ForAParticipantWhoCannotManageSpend_IsRefusedWithoutAskingBilling()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();

        var result = await rig.Controller(rig.Fixture.EvaluatorId)
            .GetWalletAsync(rig.RelationshipId, Ct);

        Problem(result, 403, "SPEND_AUTHORITY_UNAVAILABLE");
        rig.Fixture.Commercial.Verify(
            item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>()),
            Times.Never
        );
    }

    [Fact]
    public async Task Read_WhenAnOwnerFailsUnexpectedly_AnswersUnavailableWithoutLeakingTheCause()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        rig.Fixture.Commercial.Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ThrowsAsync(new InvalidOperationException("secret connection string"));

        var result = await rig.Owner().GetWalletAsync(rig.RelationshipId, Ct);

        var problem = Detail(result, 503, WorkbenchProblemCodes.Unavailable);
        Assert.DoesNotContain("secret", problem.Detail);
        Assert.Contains("Nothing was changed", problem.Detail);
    }

    [Fact]
    public async Task Read_WhenAnOwnerThrowsAWorkbenchException_KeepsItsStatusCodeAndAdvisesRetry()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        rig.Fixture.Commercial.Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ThrowsAsync(new WorkbenchException(429, "WORKBENCH_RATE_LIMITED", "Slow down."));
        var controller = rig.Owner();

        var result = await controller.GetWalletAsync(rig.RelationshipId, Ct);

        Assert.Equal("Slow down.", Detail(result, 429, "WORKBENCH_RATE_LIMITED").Detail);
        Assert.Equal("60", controller.Response.Headers.RetryAfter.ToString());
    }

    [Fact]
    public async Task Read_WhenAnOwnerReportsNothingFound_IsNotFound()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        rig.Fixture.Commercial.Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ThrowsAsync(new KeyNotFoundException());

        var result = await rig.Owner().GetWalletAsync(rig.RelationshipId, Ct);

        Assert.Equal(
            "The resource was not found.",
            Detail(result, 404, WorkbenchProblemCodes.RequestInvalid).Detail
        );
    }

    [Fact]
    public async Task Read_WhenTheCallerCancels_TheCancellationPropagatesInsteadOfBecomingAProblem()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        rig.Fixture.Commercial.Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ThrowsAsync(new OperationCanceledException());

        await Assert.ThrowsAsync<OperationCanceledException>(() =>
            rig.Owner().GetWalletAsync(rig.RelationshipId, Ct)
        );
    }

    [Theory]
    [InlineData("createGoal")]
    [InlineData("reviseGoal")]
    [InlineData("proposePlan")]
    [InlineData("acceptPlan")]
    [InlineData("pause")]
    public async Task Command_ByAnEvaluator_IsRefusedForTheRole(string name)
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var goal = await rig.Fixture.AddGoalAsync();
        var controller = rig.Controller(
            rig.Fixture.EvaluatorId,
            BodyFor(name, await rig.EnvelopeAsync(), goal.GoalId)
        );

        var result = await Command(controller, name, rig.RelationshipId, goal.GoalId);

        Assert.Equal(
            "Your role cannot do this.",
            Detail(result, 403, WorkbenchProblemCodes.RequestInvalid).Detail
        );
    }

    [Theory]
    [InlineData("capability")]
    [InlineData("resolve")]
    public async Task Command_ByAManager_IsRefusedBecauseOnlyTheEmployerAndEvaluatorResolve(
        string name
    )
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var goal = await rig.Fixture.AddGoalAsync();
        var controller = rig.Controller(
            rig.Fixture.ManagerId,
            BodyFor(name, await rig.EnvelopeAsync(), goal.GoalId)
        );

        var result = await Command(controller, name, rig.RelationshipId, goal.GoalId);

        Assert.Equal(
            "Your role cannot do this.",
            Detail(result, 403, WorkbenchProblemCodes.RequestInvalid).Detail
        );
    }

    [Fact]
    public async Task CreateGoal_IsAcceptedOnceAndReplayedForTheSameKey()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var key = Guid.NewGuid();
        var body = BodyFor("createGoal", await rig.EnvelopeAsync(), Guid.Empty);

        var first = await rig.Controller(rig.Fixture.EmployerId, body, idempotencyKey: key)
            .CreateGoalAsync(rig.RelationshipId, Ct);
        var replay = await rig.Controller(rig.Fixture.EmployerId, body, idempotencyKey: key)
            .CreateGoalAsync(rig.RelationshipId, Ct);

        var accepted = Body<WorkbenchCommandReceipt>(first, 202);
        var replayed = Body<WorkbenchCommandReceipt>(replay, 200);
        Assert.False(accepted.Replayed);
        Assert.True(replayed.Replayed);
        Assert.Equal(accepted.OperationRef, replayed.OperationRef);
        var goals = await rig.Fixture.Configuration.GetPortalGoalsAsync(
            rig.Fixture.TenantId,
            rig.RelationshipId,
            Ct
        );
        Assert.Equal(accepted.ResourceRef, Assert.Single(goals).Goal.GoalId.ToString("D"));
    }

    [Fact]
    public async Task ReviseGoal_RoutesTheGoalIdFromTheUrlAndRecordsTheRevision()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var goal = await rig.Fixture.AddGoalAsync();

        var result = await rig.Owner(BodyFor("reviseGoal", await rig.EnvelopeAsync(), goal.GoalId))
            .ReviseGoalAsync(rig.RelationshipId, goal.GoalId, Ct);

        var receipt = Body<WorkbenchCommandReceipt>(result, 202);
        Assert.Equal(goal.GoalId.ToString("D"), receipt.ResourceRef);
        var history = Body<WorkbenchGoalVersionList>(
            await rig.Owner()
                .ListGoalVersionsAsync(rig.RelationshipId, goal.GoalId, null, null, Ct),
            200
        );
        Assert.Contains(history.Items, item => item.Reason == "The location changed");
    }

    [Fact]
    public async Task ProposePlan_WithoutMilestones_IsRejectedWithTheServiceValidation()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var body = Json(
            await rig.EnvelopeAsync(),
            $"\"goalId\":\"{Guid.NewGuid():D}\",\"milestones\":[]"
        );

        var result = await rig.Owner(body).ProposePlanAsync(rig.RelationshipId, Ct);

        Assert.Equal(
            "milestones must hold 1 to 50 items.",
            Detail(result, 400, WorkbenchProblemCodes.RequestInvalid).Detail
        );
    }

    [Fact]
    public async Task ProposePlan_ForAKnownGoal_IsAnsweredByThePlanOwnerOrRefusedByName()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        rig.Fixture.CoordinatorAnswers("COMPLETED");
        var goal = await rig.Fixture.AddGoalAsync();

        var result = await rig.Owner(BodyFor("proposePlan", await rig.EnvelopeAsync(), goal.GoalId))
            .ProposePlanAsync(rig.RelationshipId, Ct);

        var objectResult = Assert.IsType<ObjectResult>(result);
        Assert.NotEqual(500, objectResult.StatusCode);
        if (objectResult.StatusCode == 202)
            Assert.IsType<WorkbenchCommandReceipt>(objectResult.Value);
        else
            Assert.IsType<WorkbenchProblem>(objectResult.Value);
    }

    [Fact]
    public async Task AcceptPlan_WithAFreshStrongSignIn_IsAcceptedForThePlanVersionInTheUrl()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        rig.Fixture.CoordinatorAnswers("COMPLETED");

        var result = await rig.Owner(BodyFor("acceptPlan", await rig.EnvelopeAsync(), Guid.Empty))
            .AcceptPlanAsync(rig.RelationshipId, WorkbenchCommandServiceFixture.PlanVersion, Ct);

        var receipt = Body<WorkbenchCommandReceipt>(result, 202);
        Assert.Equal("COMPLETED", receipt.Status);
    }

    [Fact]
    public async Task AcceptPlan_ForAPlanVersionThatIsNotCurrent_IsRefused()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        rig.Fixture.CoordinatorAnswers("COMPLETED");

        var result = await rig.Owner(BodyFor("acceptPlan", await rig.EnvelopeAsync(), Guid.Empty))
            .AcceptPlanAsync(rig.RelationshipId, "plan-99", Ct);

        var objectResult = Assert.IsType<ObjectResult>(result);
        Assert.IsType<WorkbenchProblem>(objectResult.Value);
        Assert.True(objectResult.StatusCode is >= 400 and < 600);
    }

    [Fact]
    public async Task CapabilityCommand_RoutesTheSkillFromTheUrl_AndRefusesAnUnsupportedCommand()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        rig.Fixture.CoordinatorAnswers("COMPLETED");
        await rig.Fixture.AddSkillAsync();

        var accepted = await rig.Owner(BodyFor("capability", await rig.EnvelopeAsync(), Guid.Empty))
            .CommandCapabilityAsync(rig.RelationshipId, WorkbenchCommandServiceFixture.SkillId, Ct);
        var refused = await rig.Owner(Json(await rig.EnvelopeAsync(), "\"command\":\"START\""))
            .CommandCapabilityAsync(rig.RelationshipId, WorkbenchCommandServiceFixture.SkillId, Ct);

        var result = Body<WorkbenchCapabilityCommandResult>(accepted, 202);
        Assert.False(string.IsNullOrWhiteSpace(result.Outcome));
        Assert.Equal(
            "command is not supported.",
            Detail(refused, 400, WorkbenchProblemCodes.RequestInvalid).Detail
        );
    }

    [Fact]
    public async Task ResolveDecision_ByTheEmployer_IsAcceptedAsAReceiptForTheDecision()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        rig.Fixture.CoordinatorAnswers("COMPLETED");
        var goal = await rig.Fixture.AddGoalAsync();

        var result = await rig.Owner(BodyFor("resolve", await rig.EnvelopeAsync(), goal.GoalId))
            .ResolveDecisionAsync(rig.RelationshipId, goal.GoalId, Ct);

        var receipt = Body<WorkbenchCommandReceipt>(result, 202);
        Assert.Equal("COMPLETED", receipt.Status);
    }

    [Fact]
    public async Task Topup_WhenBillingDoesNotOfferIt_IsRefusedAsCommercialUnavailable()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();

        var result = await rig.Owner(BodyFor("topup", await rig.EnvelopeAsync(), Guid.Empty))
            .CreateTopupAsync(rig.RelationshipId, Ct);

        Problem(result, 503, "SPEND_COMMERCIAL_UNAVAILABLE");
    }

    [Fact]
    public async Task Topup_ByAParticipantWhoCannotManageSpend_IsRefusedAsAuthorityUnavailable()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();

        var result = await rig.Controller(
                rig.Fixture.ManagerId,
                BodyFor("topup", await rig.EnvelopeAsync(), Guid.Empty)
            )
            .CreateTopupAsync(rig.RelationshipId, Ct);

        Problem(result, 403, "SPEND_AUTHORITY_UNAVAILABLE");
    }

    [Fact]
    public async Task ExportEvidence_WithAnUnsupportedFormat_IsRejectedAndWithAValidOneAnsweredByTheOwner()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var envelope = await rig.EnvelopeAsync();

        var invalid = await rig.Owner(
                Json(envelope, "\"scope\":\"RELATIONSHIP\",\"format\":\"CSV\"")
            )
            .ExportEvidenceAsync(rig.RelationshipId, Ct);
        var valid = await rig.Owner(BodyFor("export", envelope, Guid.Empty))
            .ExportEvidenceAsync(rig.RelationshipId, Ct);

        Assert.Equal(
            "format is not supported.",
            Detail(invalid, 400, WorkbenchProblemCodes.RequestInvalid).Detail
        );
        Assert.Equal("COMPLETED", Body<WorkbenchCommandReceipt>(valid, 202).Status);
    }

    [Fact]
    public async Task Pause_IsAcceptedForTheEmployerWithoutAStrongSignIn()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();

        var result = await rig.Owner(
                BodyFor("pause", await rig.EnvelopeAsync(), Guid.Empty),
                strongAuth: false
            )
            .PauseAsync(rig.RelationshipId, Ct);

        Assert.Equal("COMPLETED", Body<WorkbenchCommandReceipt>(result, 202).Status);
    }

    [Fact]
    public async Task Stop_IsAcceptedOnceAndReplayedForTheSameKey()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var key = Guid.NewGuid();
        var body = BodyFor("stop", await rig.EnvelopeAsync(), Guid.Empty);

        var first = await rig.Controller(rig.Fixture.EmployerId, body, idempotencyKey: key)
            .StopAsync(rig.RelationshipId, Ct);
        var replay = await rig.Controller(rig.Fixture.EmployerId, body, idempotencyKey: key)
            .StopAsync(rig.RelationshipId, Ct);

        Assert.False(Body<WorkbenchCommandReceipt>(first, 202).Replayed);
        Assert.True(Body<WorkbenchCommandReceipt>(replay, 200).Replayed);
        Assert.Equal(
            EmploymentRelationshipState.StoppedEmergency,
            (await rig.Fixture.RelationshipAsync()).State
        );
    }

    [Fact]
    public async Task Handoff_IsCreatedAsASingleUseLinkAndConsumedExactlyOnceWithoutAnIdempotencyKey()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var envelope = await rig.EnvelopeAsync();

        var created = Body<WorkbenchHandoff>(
            await rig.Owner(BodyFor("handoff", envelope, Guid.Empty))
                .CreateHandoffAsync(rig.RelationshipId, Ct),
            201
        );
        var consumeBody =
            "{\"schemaVersion\":\"1.0\",\"destinationRef\":\"" + created.DestinationRef + "\"}";
        var consumed = await rig.Controller(
                rig.Fixture.EmployerId,
                consumeBody,
                configure: context => context.Request.Headers.Remove("Idempotency-Key")
            )
            .ConsumeHandoffAsync(rig.RelationshipId, Ct);
        var again = await rig.Controller(rig.Fixture.EmployerId, consumeBody)
            .ConsumeHandoffAsync(rig.RelationshipId, Ct);

        Assert.True(created.SingleUse);
        Assert.Equal("WEB_WORKBENCH", Body<WorkbenchHandoffConsumption>(consumed, 200).Purpose);
        Assert.Equal(
            "This link is not valid any more. Ask for a new one.",
            Detail(again, 404, WorkbenchProblemCodes.RequestInvalid).Detail
        );
    }

    [Fact]
    public async Task Handoff_WithAnUnknownPurpose_IsRejected()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();

        var result = await rig.Owner(Json(await rig.EnvelopeAsync(), "\"purpose\":\"ELSEWHERE\""))
            .CreateHandoffAsync(rig.RelationshipId, Ct);

        Assert.Equal(
            "purpose is not supported.",
            Detail(result, 400, WorkbenchProblemCodes.RequestInvalid).Detail
        );
    }

    [Fact]
    public async Task SubscriptionChange_WithoutATargetPackage_IsRejectedWithTheServiceValidation()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();

        var result = await rig.Owner(BodyFor("subscription", await rig.EnvelopeAsync(), Guid.Empty))
            .ChangeSubscriptionAsync(rig.RelationshipId, Ct);

        Assert.Equal(
            "targetPackageId is required to change the package.",
            Detail(result, 400, WorkbenchProblemCodes.RequestInvalid).Detail
        );
    }

    [Theory]
    [MemberData(nameof(StrongAuthCommands))]
    public async Task StrongAuthCommand_WithoutAFreshStrongSignIn_IsForbiddenWithTheStrongAuthDetail(
        string name
    )
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var goal = await rig.Fixture.AddGoalAsync();
        var controller = rig.Owner(
            BodyFor(name, await rig.EnvelopeAsync(), goal.GoalId),
            strongAuth: false
        );

        var result = await Command(controller, name, rig.RelationshipId, goal.GoalId);

        Assert.Equal(
            "A fresh strong sign-in is required for this action.",
            Detail(result, 403, WorkbenchProblemCodes.RequestInvalid).Detail
        );
    }

    [Theory]
    [InlineData("AAL2", 0, false)]
    [InlineData("AAL3_FRESH", 0, true)]
    [InlineData("AAL3_FRESH", -120, true)]
    [InlineData("AAL3_FRESH", -600, false)]
    [InlineData("AAL3_FRESH", 30, true)]
    [InlineData("AAL3_FRESH", 300, false)]
    public async Task StrongAuthCommand_AcceptsOnlyAFreshAal3Assertion(
        string assurance,
        int ageSecondsFromNow,
        bool accepted
    )
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        rig.Fixture.CoordinatorAnswers("COMPLETED");
        var authTime = DateTimeOffset.UtcNow.AddSeconds(ageSecondsFromNow);
        var controller = rig.Owner(
            BodyFor("acceptPlan", await rig.EnvelopeAsync(), Guid.Empty),
            strongAuth: false
        );
        var identity = (ClaimsIdentity)controller.HttpContext.User.Identity!;
        identity.AddClaim(new Claim("authentication_assurance", assurance));
        identity.AddClaim(new Claim("auth_time", authTime.ToUnixTimeSeconds().ToString()));

        var result = await controller.AcceptPlanAsync(
            rig.RelationshipId,
            WorkbenchCommandServiceFixture.PlanVersion,
            Ct
        );

        if (accepted)
            Body<WorkbenchCommandReceipt>(result, 202);
        else
            Assert.Equal(
                "A fresh strong sign-in is required for this action.",
                Detail(result, 403, WorkbenchProblemCodes.RequestInvalid).Detail
            );
    }

    [Fact]
    public async Task StrongAuthCommand_WithANonNumericAuthTime_IsForbidden()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var controller = rig.Owner(
            BodyFor("acceptPlan", await rig.EnvelopeAsync(), Guid.Empty),
            strongAuth: false
        );
        var identity = (ClaimsIdentity)controller.HttpContext.User.Identity!;
        identity.AddClaim(new Claim("authentication_assurance", "AAL3_FRESH"));
        identity.AddClaim(new Claim("auth_time", "yesterday"));

        var result = await controller.AcceptPlanAsync(
            rig.RelationshipId,
            WorkbenchCommandServiceFixture.PlanVersion,
            Ct
        );

        Problem(result, 403, WorkbenchProblemCodes.RequestInvalid);
    }

    [Theory]
    [InlineData("null")]
    [InlineData("{not json")]
    [InlineData("[]")]
    [InlineData("""{"schemaVersion":1,"expectedVersion":"relationship-1"}""")]
    public async Task Command_WithAMissingOrMalformedBody_IsRejectedAsInvalid(string body)
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();

        var result = await rig.Owner(body).StopAsync(rig.RelationshipId, Ct);

        Assert.Equal(
            "The request body is missing or does not match the contract.",
            Detail(result, 400, WorkbenchProblemCodes.RequestInvalid).Detail
        );
    }

    [Fact]
    public async Task Command_WithAnInvalidIdempotencyKey_IsRejectedBeforeTheBodyIsRead()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var controller = rig.Controller(
            rig.Fixture.EmployerId,
            Json(await rig.EnvelopeAsync()),
            configure: context => context.Request.Headers["Idempotency-Key"] = "key"
        );

        var result = await controller.StopAsync(rig.RelationshipId, Ct);

        Assert.Equal(
            "Idempotency-Key must be a UUID.",
            Detail(result, 400, WorkbenchProblemCodes.RequestInvalid).Detail
        );
        Assert.True(controller.Request.Body.CanRead);
        Assert.Equal(0, controller.Request.Body.Position);
    }

    [Fact]
    public async Task Command_WithAnExpectedVersionThatIsStale_IsAConflictNamingTheVersion()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var stale = $"{WorkbenchSurfaceRig.Schema},\"expectedVersion\":\"relationship-0\"";

        var result = await rig.Owner(Json(stale)).PauseAsync(rig.RelationshipId, Ct);

        Problem(result, 409, WorkbenchProblemCodes.VersionConflict);
    }

    [Fact]
    public async Task Command_WithACapabilityHeaderThatIsInvalid_IsRejectedBeforeAnyChange()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();
        var controller = rig.Controller(
            rig.Fixture.EmployerId,
            Json(await rig.EnvelopeAsync()),
            configure: context =>
                context.Request.Headers[ChannelCapabilities.HeaderName] = new string('a', 600)
        );

        var result = await controller.PauseAsync(rig.RelationshipId, Ct);

        Assert.Equal(
            "X-Experience-Capabilities is invalid.",
            Detail(result, 400, WorkbenchProblemCodes.RequestInvalid).Detail
        );
    }

    [Fact]
    public async Task Command_OnAnUnreachableRelationship_IsForbiddenForAStranger()
    {
        var rig = await WorkbenchSurfaceRig.CreateAsync();

        var result = await rig.Controller(Guid.NewGuid(), Json(await rig.EnvelopeAsync()))
            .StopAsync(rig.RelationshipId, Ct);

        Problem(result, 403, WorkbenchProblemCodes.RequestInvalid);
    }
}
