// Implements: architecture/reference/components/conversational-employment-solution-contract.md §4.1 BP public candidate operations
// Constitutional basis: C-001, C-005, C-023, C-026, C-059, C-063, C-079, ADR-051
// IB: N/A - Founder-assigned WC-115

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

[ApiController]
[Authorize]
[CustomerIdentityRoute(requiresMembership: true)]
[Route("api/v1/employment/relationships/{relationshipId:guid}/workspace/employment")]
public sealed class ConversationalEmploymentController(
    EmploymentRelationshipService relationships,
    IEmploymentProtocolGate gate,
    ConversationalEmploymentService employment,
    IEmploymentCommandCoordinator coordinator
) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> GetEmploymentWorkspaceAsync(
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        var context = await AuthorizedContextAsync(relationshipId, cancellationToken);
        if (context is null)
            return ProblemResult(404, "EMPLOYMENT_NOT_ACCESSIBLE");
        var workspace = employment.GetWorkspace(context.TenantId, relationshipId);
        return workspace is null
            ? ProblemResult(503, "EMPLOYMENT_SOURCE_UNAVAILABLE")
            : Ok(workspace.Workspace);
    }

    [HttpGet("phases/{phase}")]
    public async Task<IActionResult> GetEmploymentPhaseAsync(
        Guid relationshipId,
        string phase,
        CancellationToken cancellationToken
    )
    {
        var context = await AuthorizedContextAsync(relationshipId, cancellationToken);
        if (context is null)
            return ProblemResult(404, "EMPLOYMENT_NOT_ACCESSIBLE");
        var workspace = employment.GetWorkspace(context.TenantId, relationshipId);
        if (
            workspace is null
            || !workspace.Phases.TryGetValue(phase.ToUpperInvariant(), out var projection)
        )
            return workspace is null
                ? ProblemResult(503, "EMPLOYMENT_SOURCE_UNAVAILABLE")
                : ProblemResult(404, "EMPLOYMENT_NOT_ACCESSIBLE");
        return Ok(projection);
    }

    [HttpGet("readiness")]
    public async Task<IActionResult> GetEmploymentReadinessAsync(
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        var context = await AuthorizedContextAsync(relationshipId, cancellationToken);
        if (context is null)
            return ProblemResult(404, "EMPLOYMENT_NOT_ACCESSIBLE");
        var workspace = employment.GetWorkspace(context.TenantId, relationshipId);
        return workspace is null
            ? ProblemResult(503, "EMPLOYMENT_SOURCE_UNAVAILABLE")
            : Ok(workspace.Readiness);
    }

    [HttpGet("plans/current")]
    public async Task<IActionResult> GetEmploymentPlanAsync(
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        var context = await AuthorizedContextAsync(relationshipId, cancellationToken);
        if (context is null)
            return ProblemResult(404, "EMPLOYMENT_NOT_ACCESSIBLE");
        var workspace = employment.GetWorkspace(context.TenantId, relationshipId);
        if (
            workspace is null
            || workspace.CurrentPlanVersion is null
            || !workspace.Plans.TryGetValue(workspace.CurrentPlanVersion, out var plan)
        )
            return workspace is null
                ? ProblemResult(503, "EMPLOYMENT_SOURCE_UNAVAILABLE")
                : ProblemResult(404, "EMPLOYMENT_NOT_ACCESSIBLE");
        return Ok(plan);
    }

    [HttpGet("plans/{planVersion}")]
    public async Task<IActionResult> GetEmploymentPlanVersionAsync(
        Guid relationshipId,
        string planVersion,
        CancellationToken cancellationToken
    )
    {
        var context = await AuthorizedContextAsync(relationshipId, cancellationToken);
        if (context is null)
            return ProblemResult(404, "EMPLOYMENT_NOT_ACCESSIBLE");
        var workspace = employment.GetWorkspace(context.TenantId, relationshipId);
        if (workspace is null)
            return ProblemResult(503, "EMPLOYMENT_SOURCE_UNAVAILABLE");
        return workspace.Plans.TryGetValue(planVersion, out var plan)
            ? Ok(plan)
            : ProblemResult(404, "EMPLOYMENT_NOT_ACCESSIBLE");
    }

    [HttpPost("commands")]
    public async Task<IActionResult> SubmitEmploymentCommandAsync(
        Guid relationshipId,
        [FromBody] JsonElement command,
        [FromHeader(Name = "Idempotency-Key")] Guid? idempotencyKey,
        CancellationToken cancellationToken
    )
    {
        var context = await AuthorizedContextAsync(relationshipId, cancellationToken);
        if (context is null)
            return ProblemResult(404, "EMPLOYMENT_NOT_ACCESSIBLE");
        if (idempotencyKey is null)
            return ProblemResult(400, "EMPLOYMENT_INVALID_REQUEST");
        if (!HasFreshAal3())
            return ProblemResult(403, "EMPLOYMENT_ASSURANCE_REQUIRED");
        try
        {
            var result = employment.Submit(
                context.TenantId,
                relationshipId,
                context.ActorId,
                idempotencyKey.Value,
                command
            );
            if (!result.Replayed)
            {
                var workspace =
                    employment.GetWorkspace(context.TenantId, relationshipId)
                    ?? throw new EmploymentProtocolException("EMPLOYMENT_SOURCE_UNAVAILABLE");
                await coordinator.CoordinateAsync(
                    new EmploymentCommandCoordinationContext(
                        context.TenantId,
                        relationshipId,
                        context.ActorId,
                        result.Receipt.CommandId,
                        command.GetProperty("kind").GetString()!,
                        command,
                        workspace
                    ),
                    cancellationToken
                );
            }
            return result.Replayed && IsTerminal(result.Outcome.State)
                ? Ok(result.Outcome)
                : StatusCode(StatusCodes.Status202Accepted, result.Receipt);
        }
        catch (EmploymentProtocolException error)
        {
            return ProblemFor(error.Code);
        }
    }

    [HttpGet("commands/{commandId:guid}")]
    public async Task<IActionResult> GetEmploymentCommandAsync(
        Guid relationshipId,
        Guid commandId,
        CancellationToken cancellationToken
    )
    {
        var context = await AuthorizedContextAsync(relationshipId, cancellationToken);
        if (context is null)
            return ProblemResult(404, "EMPLOYMENT_NOT_ACCESSIBLE");
        var outcome = employment.GetCommand(context.TenantId, relationshipId, commandId);
        return outcome is null ? ProblemResult(404, "EMPLOYMENT_NOT_ACCESSIBLE") : Ok(outcome);
    }

    private async Task<EmploymentRequestContext?> AuthorizedContextAsync(
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        if (!gate.Snapshot().Enabled)
            return null;
        if (
            !HttpContext.Items.TryGetValue(
                TenantIsolationMiddleware.TenantIdItemKey,
                out var tenant
            )
            || tenant is not string tenantText
            || !Guid.TryParse(tenantText, out var tenantId)
        )
            return null;
        var actor =
            User.FindFirstValue("participant_id")
            ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub");
        if (
            !Guid.TryParse(actor, out var actorId)
            || !await relationships.IsActiveParticipantAsync(
                tenantId,
                relationshipId,
                actorId,
                cancellationToken
            )
        )
            return null;
        return new EmploymentRequestContext(tenantId, actorId);
    }

    private bool HasFreshAal3()
    {
        if (
            !string.Equals(
                User.FindFirstValue("authentication_assurance"),
                "AAL3_FRESH",
                StringComparison.Ordinal
            ) || !long.TryParse(User.FindFirstValue("auth_time"), out var unixTime)
        )
            return false;
        var age = DateTimeOffset.UtcNow - DateTimeOffset.FromUnixTimeSeconds(unixTime);
        return age >= TimeSpan.FromSeconds(-60) && age <= TimeSpan.FromMinutes(5);
    }

    private IActionResult ProblemFor(string code) =>
        code switch
        {
            "EMPLOYMENT_INVALID_REQUEST" => ProblemResult(400, code),
            "EMPLOYMENT_VERSION_CONFLICT" or "EMPLOYMENT_IDEMPOTENCY_CONFLICT" => ProblemResult(
                409,
                code
            ),
            "EMPLOYMENT_BLOCKED" => ProblemResult(423, code),
            "EMPLOYMENT_OUTCOME_UNKNOWN" or "EMPLOYMENT_SOURCE_UNAVAILABLE" => ProblemResult(
                503,
                code
            ),
            _ => ProblemResult(404, "EMPLOYMENT_NOT_ACCESSIBLE"),
        };

    private ObjectResult ProblemResult(int status, string code)
    {
        var response = StatusCode(
            status,
            new
            {
                type = $"https://waooaw.com/problems/{code.ToLowerInvariant().Replace('_', '-')}",
                title = "The employment workspace request could not be completed",
                status,
                code,
                correlationId = User.FindFirstValue("correlation_id")
                    ?? HttpContext.TraceIdentifier,
            }
        );
        response.ContentTypes.Add("application/problem+json");
        return response;
    }

    private static bool IsTerminal(string state) =>
        state is "COMPLETED" or "REJECTED" or "CONFLICT" or "BLOCKED";

    private sealed record EmploymentRequestContext(Guid TenantId, Guid ActorId);
}
