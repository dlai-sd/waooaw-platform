// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-02
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, ADR-051

using System.Security.Claims;
using System.Text;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class WorkbenchControllerTests
{
    private static WorkbenchController Create(
        WorkbenchHarness? harness,
        bool enabled,
        Guid? tenant,
        Guid? participant,
        Dictionary<string, string>? headers = null,
        string? body = null,
        bool freshStrongAuth = false
    )
    {
        var claims = new List<Claim>();
        if (participant is { } participantId)
            claims.Add(new Claim("participant_id", participantId.ToString("D")));
        if (freshStrongAuth)
        {
            claims.Add(new Claim("authentication_assurance", "AAL3_FRESH"));
            claims.Add(
                new Claim("auth_time", DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString())
            );
        }
        var context = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity(claims, "Test")),
        };
        if (tenant is { } tenantId)
            context.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString("D");
        if (headers is not null)
            foreach (var header in headers)
                context.Request.Headers[header.Key] = header.Value;
        if (body is not null)
        {
            context.Request.ContentType = "application/json";
            context.Request.Body = new MemoryStream(Encoding.UTF8.GetBytes(body));
        }
        return new WorkbenchController(
            harness?.Relationships!,
            harness?.Projection!,
            harness?.Commands!,
            Options.Create(new WorkbenchOptions { Enabled = enabled })
        )
        {
            ControllerContext = new ControllerContext { HttpContext = context },
        };
    }

    private static Dictionary<string, string> CommandHeaders(Guid? key = null) =>
        new()
        {
            ["X-Correlation-ID"] = Guid.NewGuid().ToString("D"),
            ["Idempotency-Key"] = (key ?? Guid.NewGuid()).ToString("D"),
        };

    private static WorkbenchProblem Problem(IActionResult result, int status)
    {
        var objectResult = Assert.IsType<ObjectResult>(result);
        Assert.Equal(status, objectResult.StatusCode);
        Assert.Contains("application/problem+json", objectResult.ContentTypes);
        return Assert.IsType<WorkbenchProblem>(objectResult.Value);
    }

    [Fact]
    public async Task Read_WhenTheFlagIsOff_AnswersWorkbenchDisabledBeforeUsingAnyService()
    {
        var controller = Create(null, false, null, null);

        var problem = Problem(
            await controller.GetWorkbenchAsync(Guid.NewGuid(), CancellationToken.None),
            404
        );

        Assert.Equal(WorkbenchProblemCodes.Disabled, problem.Code);
    }

    [Fact]
    public async Task Command_WithoutACorrelationHeader_IsRejectedAsInvalid()
    {
        var controller = Create(
            null,
            true,
            Guid.NewGuid(),
            Guid.NewGuid(),
            new() { ["Idempotency-Key"] = Guid.NewGuid().ToString("D") }
        );

        var problem = Problem(
            await controller.StopAsync(Guid.NewGuid(), CancellationToken.None),
            400
        );

        Assert.Equal(WorkbenchProblemCodes.RequestInvalid, problem.Code);
    }

    [Fact]
    public async Task Command_WithoutAnIdempotencyKey_IsRejectedAsInvalid()
    {
        var controller = Create(
            null,
            true,
            Guid.NewGuid(),
            Guid.NewGuid(),
            new() { ["X-Correlation-ID"] = Guid.NewGuid().ToString("D") }
        );

        var problem = Problem(
            await controller.StopAsync(Guid.NewGuid(), CancellationToken.None),
            400
        );

        Assert.Equal(WorkbenchProblemCodes.RequestInvalid, problem.Code);
        Assert.Contains("Idempotency-Key", problem.Detail);
    }

    [Fact]
    public async Task Read_WithAnOversizedCapabilityHeader_IsRejectedAsInvalid()
    {
        var controller = Create(
            null,
            true,
            Guid.NewGuid(),
            Guid.NewGuid(),
            new() { [ChannelCapabilities.HeaderName] = new string('a', 600) }
        );

        var problem = Problem(
            await controller.GetWorkbenchAsync(Guid.NewGuid(), CancellationToken.None),
            400
        );

        Assert.Equal(WorkbenchProblemCodes.RequestInvalid, problem.Code);
    }

    [Fact]
    public async Task Read_WithoutATenantOrAParticipant_IsForbidden()
    {
        var harness = await WorkbenchHarness.CreateAsync();

        var noTenant = Create(harness, true, null, harness.ParticipantId);
        var noParticipant = Create(harness, true, harness.TenantId, null);

        Problem(
            await noTenant.GetWorkbenchAsync(harness.RelationshipId, CancellationToken.None),
            403
        );
        Problem(
            await noParticipant.GetWorkbenchAsync(harness.RelationshipId, CancellationToken.None),
            403
        );
    }

    [Fact]
    public async Task Read_ByAnotherParticipantOrAnotherRelationship_IsForbidden()
    {
        var harness = await WorkbenchHarness.CreateAsync();

        var stranger = Create(harness, true, harness.TenantId, Guid.NewGuid());
        var otherRelationship = Create(harness, true, harness.TenantId, harness.ParticipantId);

        Problem(
            await stranger.GetWorkbenchAsync(harness.RelationshipId, CancellationToken.None),
            403
        );
        Problem(
            await otherRelationship.GetWorkbenchAsync(Guid.NewGuid(), CancellationToken.None),
            403
        );
    }

    [Fact]
    public async Task Read_ByAMember_ReturnsTheProjectionWithTheRelationshipVersionAsEtag()
    {
        var harness = await WorkbenchHarness.CreateAsync();
        var controller = Create(harness, true, harness.TenantId, harness.ParticipantId);

        var result = await controller.GetWorkbenchAsync(
            harness.RelationshipId,
            CancellationToken.None
        );

        var projection = Assert.IsType<WorkbenchProjection>(
            Assert.IsType<OkObjectResult>(result).Value
        );
        Assert.Equal(harness.RelationshipId, projection.RelationshipRef);
        Assert.Equal(WorkbenchAudiences.FromRole(harness.Role), projection.Audience);
        Assert.StartsWith("\"relationship-", controller.Response.Headers.ETag.ToString());
        Assert.NotEmpty(projection.Limitations);
    }

    [Fact]
    public async Task AcceptPlan_WithoutAFreshStrongSignIn_IsForbiddenWithTheStrongAuthDetail()
    {
        var harness = await WorkbenchHarness.CreateAsync();
        var controller = Create(
            harness,
            true,
            harness.TenantId,
            harness.ParticipantId,
            CommandHeaders(),
            """{"schemaVersion":"1.0","expectedVersion":"relationship-1","acknowledgedLimitations":true}"""
        );

        var problem = Problem(
            await controller.AcceptPlanAsync(
                harness.RelationshipId,
                "plan-1",
                CancellationToken.None
            ),
            403
        );

        Assert.Equal("A fresh strong sign-in is required for this action.", problem.Detail);
    }

    [Fact]
    public async Task Stop_IsAcceptedOnceAndReplayedWithTheSameKey_AndAConflictingBodyIsRefused()
    {
        var harness = await WorkbenchHarness.CreateAsync();
        var key = Guid.NewGuid();
        const string body = """{"schemaVersion":"1.0","expectedVersion":"relationship-1"}""";

        var first = await Create(
                harness,
                true,
                harness.TenantId,
                harness.ParticipantId,
                CommandHeaders(key),
                body
            )
            .StopAsync(harness.RelationshipId, CancellationToken.None);
        var replay = await Create(
                harness,
                true,
                harness.TenantId,
                harness.ParticipantId,
                CommandHeaders(key),
                body
            )
            .StopAsync(harness.RelationshipId, CancellationToken.None);
        var conflict = await Create(
                harness,
                true,
                harness.TenantId,
                harness.ParticipantId,
                CommandHeaders(key),
                """{"schemaVersion":"1.0","expectedVersion":"relationship-1","reason":"different"}"""
            )
            .StopAsync(harness.RelationshipId, CancellationToken.None);

        var accepted = Assert.IsType<ObjectResult>(first);
        Assert.Equal(StatusCodes.Status202Accepted, accepted.StatusCode);
        var receipt = Assert.IsType<WorkbenchCommandReceipt>(accepted.Value);
        Assert.False(receipt.Replayed);
        var replayed = Assert.IsType<ObjectResult>(replay);
        Assert.Equal(StatusCodes.Status200OK, replayed.StatusCode);
        Assert.True(Assert.IsType<WorkbenchCommandReceipt>(replayed.Value).Replayed);
        Assert.Equal(WorkbenchProblemCodes.IdempotencyConflict, Problem(conflict, 409).Code);
    }

    [Fact]
    public async Task Command_WithABodyThatDoesNotMatchTheContract_IsRejectedAsInvalid()
    {
        var harness = await WorkbenchHarness.CreateAsync();
        var controller = Create(
            harness,
            true,
            harness.TenantId,
            harness.ParticipantId,
            CommandHeaders(),
            """{"schemaVersion":"1.0","expectedVersion":"relationship-1","unexpected":true}"""
        );

        var problem = Problem(
            await controller.StopAsync(harness.RelationshipId, CancellationToken.None),
            400
        );

        Assert.Equal(WorkbenchProblemCodes.RequestInvalid, problem.Code);
    }
}
