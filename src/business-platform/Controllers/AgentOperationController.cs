// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R002, R005, R007, R013, R015, R017, R018, R030, R036
// Constitutional basis: C-001, C-005, C-023, C-059, C-061, C-063

using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.AgentOperation;
using Waooaw.BusinessPlatform.Services.Workbench;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record SetModeRequest(string ModeId, string? Surface);

public sealed record LayerSwitchRequest(bool On, string? Route);

public sealed record CustomLayerRequest(string Label);

public sealed record RouteRequest(string? Route);

public sealed record ApproveRequest(int Version, string? Route);

public sealed record MoveRequest(DateOnly Start, DateOnly? End, string? Route);

public sealed record ConfirmLabelRequest(string? CorrectedTitle, string? Route);

public sealed record AnswerPlatformRequest(string Answer, string? Route);

public sealed record GoalBody(
    string Baseline,
    string Target,
    string EvidenceSource,
    string Cadence,
    string AuthorityState,
    string? Route
);

public sealed record DecideRequest(bool Accept, string? Route);

public sealed record ScheduleRequest(
    Guid ContentId,
    string PlatformId,
    DateOnly Date,
    string? Route
);

public sealed record PublishAuthorityRequest(bool Granted);

public sealed record EditBody(
    string? Title,
    string? Body,
    DateOnly? StartDate,
    DateOnly? EndDate,
    int ExpectedVersion,
    string? Route
);

/// <summary>
/// The customer's workspace for one relationship: modes, calendar, plan, goals, platforms, approvals and the docked
/// conversation's context. Every route is agent-neutral; the declaration the agent admitted decides what is shown.
/// A change goes through one command whether it was asked for in words or made with a tool.
/// </summary>
[ApiController]
[Authorize]
[CustomerIdentityRoute(requiresMembership: true)]
[RequestSizeLimit(65536)]
[Route("api/v1/employment/relationships/{relationshipId:guid}/operation")]
public sealed class AgentOperationController(
    EmploymentRelationshipService relationships,
    WorkbenchProjectionService projection,
    AgentOperationService operation,
    IOptions<WorkbenchOptions> options
) : ControllerBase
{
    [HttpGet("frame")]
    public Task<IActionResult> FrameAsync(
        Guid relationshipId,
        [FromQuery] string? mode,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.GetFrameAsync(caller, mode, token),
            ct
        );

    [HttpPut("mode")]
    public Task<IActionResult> SetModeAsync(
        Guid relationshipId,
        [FromBody] SetModeRequest body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            async (caller, token) =>
            {
                await operation.SetModeAsync(caller, body.ModeId, body.Surface, token);
                return new { ok = true };
            },
            ct
        );

    [HttpPost("tour-seen")]
    public Task<IActionResult> TourSeenAsync(Guid relationshipId, CancellationToken ct) =>
        RunAsync(
            relationshipId,
            false,
            async (caller, token) =>
            {
                await operation.MarkTourSeenAsync(caller, token);
                return new { ok = true };
            },
            ct
        );

    [HttpGet("calendar")]
    public Task<IActionResult> CalendarAsync(
        Guid relationshipId,
        [FromQuery] DateOnly from,
        [FromQuery] DateOnly to,
        [FromQuery] bool includeHidden,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.GetCalendarAsync(caller, from, to, includeHidden, token),
            ct
        );

    [HttpGet("plan-tree")]
    public Task<IActionResult> PlanTreeAsync(Guid relationshipId, CancellationToken ct) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.GetPlanTreeAsync(caller, token),
            ct
        );

    [HttpGet("items")]
    public Task<IActionResult> ItemsAsync(
        Guid relationshipId,
        [FromQuery] string? kind,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.ListAsync(caller, kind, token),
            ct
        );

    [HttpGet("items/{itemId:guid}/versions")]
    public Task<IActionResult> VersionsAsync(
        Guid relationshipId,
        Guid itemId,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.VersionsAsync(caller, itemId, token),
            ct
        );

    [HttpGet("context")]
    public Task<IActionResult> ContextAsync(
        Guid relationshipId,
        [FromQuery] string? mode,
        [FromQuery] string? view,
        [FromQuery] Guid? selected,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.GetContextAsync(caller, mode, view, selected, token),
            ct
        );

    [HttpPut("layers/{layerId}")]
    public Task<IActionResult> LayerAsync(
        Guid relationshipId,
        string layerId,
        [FromBody] LayerSwitchRequest body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            async (caller, token) =>
            {
                await operation.SetLayerAsync(
                    caller,
                    layerId,
                    body.On,
                    body.Route ?? OperationVocabulary.Routes.Tool,
                    token
                );
                return new { layerId, on = body.On };
            },
            ct
        );

    [HttpPost("layers")]
    public Task<IActionResult> CustomLayerAsync(
        Guid relationshipId,
        [FromBody] CustomLayerRequest body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.AddCustomLayerAsync(caller, body.Label, Key(), token),
            ct,
            requireKey: true,
            created: true
        );

    [HttpPost("items")]
    public Task<IActionResult> CreateAsync(
        Guid relationshipId,
        [FromBody] CreateItemRequest body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.CreateItemAsync(caller, Key(), body, token),
            ct,
            requireKey: true,
            created: true
        );

    [HttpPatch("items/{itemId:guid}")]
    public Task<IActionResult> EditAsync(
        Guid relationshipId,
        Guid itemId,
        [FromBody] EditBody body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) =>
                operation.EditAsync(
                    caller,
                    itemId,
                    new EditItemRequest(
                        body.Title,
                        body.Body,
                        body.StartDate,
                        body.EndDate,
                        body.ExpectedVersion
                    ),
                    body.Route,
                    token
                ),
            ct
        );

    [HttpPost("items/{itemId:guid}/accept")]
    public Task<IActionResult> AcceptAsync(
        Guid relationshipId,
        Guid itemId,
        [FromBody] RouteRequest? body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.AcceptAsync(caller, itemId, body?.Route, token),
            ct
        );

    [HttpPost("items/{itemId:guid}/hide")]
    public Task<IActionResult> HideAsync(
        Guid relationshipId,
        Guid itemId,
        [FromBody] RouteRequest? body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.HideAsync(caller, itemId, body?.Route, token),
            ct
        );

    [HttpPost("items/{itemId:guid}/restore")]
    public Task<IActionResult> RestoreAsync(
        Guid relationshipId,
        Guid itemId,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.RestoreAsync(caller, itemId, token),
            ct
        );

    [HttpPost("items/{itemId:guid}/hand-over")]
    public Task<IActionResult> HandOverAsync(
        Guid relationshipId,
        Guid itemId,
        [FromBody] RouteRequest? body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.HandOverAsync(caller, itemId, body?.Route, token),
            ct
        );

    [HttpPost("items/{itemId:guid}/take-back")]
    public Task<IActionResult> TakeBackAsync(
        Guid relationshipId,
        Guid itemId,
        [FromBody] RouteRequest? body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.TakeBackAsync(caller, itemId, body?.Route, token),
            ct
        );

    [HttpPost("items/{itemId:guid}/undo")]
    public Task<IActionResult> UndoAsync(Guid relationshipId, Guid itemId, CancellationToken ct) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.UndoAsync(caller, itemId, token),
            ct
        );

    [HttpPost("items/{itemId:guid}/approve")]
    public Task<IActionResult> ApproveAsync(
        Guid relationshipId,
        Guid itemId,
        [FromBody] ApproveRequest body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) =>
                operation.ApproveAsync(caller, itemId, body.Version, body.Route, token),
            ct
        );

    [HttpPost("items/{itemId:guid}/reject")]
    public Task<IActionResult> RejectAsync(
        Guid relationshipId,
        Guid itemId,
        [FromBody] RouteRequest? body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.RejectAsync(caller, itemId, body?.Route, token),
            ct
        );

    [HttpPost("items/{itemId:guid}/move")]
    public Task<IActionResult> MoveAsync(
        Guid relationshipId,
        Guid itemId,
        [FromBody] MoveRequest body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) =>
                operation.MoveAsync(caller, itemId, body.Start, body.End, body.Route, token),
            ct
        );

    [HttpPost("labels/{itemId:guid}/confirm")]
    public Task<IActionResult> ConfirmLabelAsync(
        Guid relationshipId,
        Guid itemId,
        [FromBody] ConfirmLabelRequest body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) =>
                operation.ConfirmLabelAsync(caller, itemId, body.CorrectedTitle, body.Route, token),
            ct
        );

    [HttpPut("platforms/{platformId}/answer")]
    public Task<IActionResult> AnswerPlatformAsync(
        Guid relationshipId,
        string platformId,
        [FromBody] AnswerPlatformRequest body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) =>
                operation.AnswerPlatformAsync(caller, platformId, body.Answer, body.Route, token),
            ct
        );

    [HttpPost("platforms/{platformId}/test")]
    public Task<IActionResult> TestPlatformAsync(
        Guid relationshipId,
        string platformId,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.TestPlatformAsync(caller, platformId, token),
            ct
        );

    [HttpPut("goals/{skillId}")]
    public Task<IActionResult> SetGoalAsync(
        Guid relationshipId,
        string skillId,
        [FromBody] GoalBody body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) =>
                operation.SetGoalAsync(
                    caller,
                    skillId,
                    new GoalRequest(
                        body.Baseline,
                        body.Target,
                        body.EvidenceSource,
                        body.Cadence,
                        body.AuthorityState
                    ),
                    body.Route,
                    token
                ),
            ct
        );

    [HttpPost("goals/{skillId}/decision")]
    public Task<IActionResult> DecideGoalAsync(
        Guid relationshipId,
        string skillId,
        [FromBody] DecideRequest body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) =>
                operation.ConfirmGoalAsync(caller, skillId, body.Accept, body.Route, token),
            ct
        );

    [HttpPost("digests/{digestId:guid}/decision")]
    public Task<IActionResult> DecideDigestAsync(
        Guid relationshipId,
        Guid digestId,
        [FromBody] DecideRequest body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.DecideDigestAsync(caller, digestId, body.Accept, token),
            ct
        );

    [HttpPost("schedule")]
    public Task<IActionResult> ScheduleAsync(
        Guid relationshipId,
        [FromBody] ScheduleRequest body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) =>
                operation.ScheduleAsync(
                    caller,
                    Key(),
                    body.ContentId,
                    body.PlatformId,
                    body.Date,
                    body.Route,
                    token
                ),
            ct,
            requireKey: true,
            created: true
        );

    [HttpPut("publish-authority")]
    public Task<IActionResult> PublishAuthorityAsync(
        Guid relationshipId,
        [FromBody] PublishAuthorityRequest body,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            true,
            async (caller, token) =>
            {
                await operation.SetPublishAuthorityAsync(caller, body.Granted, token);
                return new { granted = body.Granted };
            },
            ct
        );

    [HttpPost("slots/{slotId:guid}/publish")]
    public Task<IActionResult> PublishAsync(
        Guid relationshipId,
        Guid slotId,
        CancellationToken ct
    ) =>
        RunAsync(
            relationshipId,
            true,
            (caller, token) => operation.PublishAsync(caller, slotId, token),
            ct
        );

    [HttpPost("conversation/chats")]
    public Task<IActionResult> ChatAsync(Guid relationshipId, CancellationToken ct) =>
        RunAsync(
            relationshipId,
            false,
            (caller, token) => operation.RecordChatAsync(caller, token),
            ct
        );

    private Guid Key() =>
        Guid.TryParse(Request.Headers["Idempotency-Key"].FirstOrDefault(), out var key)
            ? key
            : Guid.Empty;

    private async Task<IActionResult> RunAsync<T>(
        Guid relationshipId,
        bool strongAuth,
        Func<OperationCaller, CancellationToken, Task<T>> action,
        CancellationToken ct,
        bool requireKey = false,
        bool created = false
    )
    {
        Response.Headers.CacheControl = "no-store";
        if (!options.Value.Enabled)
            return Problem(404, "OPERATION_DISABLED", "Agent operation is not available yet.");
        if (requireKey && Key() == Guid.Empty)
            return Problem(400, AgentOperationCodes.Invalid, "Idempotency-Key must be a UUID.");
        try
        {
            if (
                !HttpContext.Items.TryGetValue(
                    TenantIsolationMiddleware.TenantIdItemKey,
                    out var tenant
                )
                || tenant is not string tenantText
                || !Guid.TryParse(tenantText, out var tenantId)
            )
                return Problem(
                    403,
                    AgentOperationCodes.NotFound,
                    "The relationship is not accessible."
                );
            var actor =
                User.FindFirstValue("participant_id")
                ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
                ?? User.FindFirstValue("sub");
            if (!Guid.TryParse(actor, out var participantId))
                return Problem(
                    403,
                    AgentOperationCodes.NotFound,
                    "The relationship is not accessible."
                );
            var role = await relationships.GetActiveRoleAsync(
                tenantId,
                relationshipId,
                participantId,
                ct
            );
            if (role is null)
                return Problem(
                    403,
                    AgentOperationCodes.NotFound,
                    "The relationship is not accessible."
                );
            if (strongAuth && !HasFreshAal3())
                return Problem(
                    403,
                    "OPERATION_STEP_UP_REQUIRED",
                    "A fresh strong sign-in is required for this action."
                );
            var context = await projection.NarrowAsync(
                new WorkbenchContext(
                    tenantId,
                    relationshipId,
                    actor!,
                    participantId,
                    role.Value,
                    WorkbenchAudiences.FromRole(role.Value),
                    HttpContext.TraceIdentifier
                ),
                ct
            );
            var caller = new OperationCaller(
                tenantId,
                relationshipId,
                participantId,
                actor!,
                context.Audience,
                context
            );
            var result = await action(caller, ct);
            return created ? StatusCode(StatusCodes.Status201Created, result) : Ok(result);
        }
        catch (AgentOperationException failure)
        {
            return Problem(failure.Status, failure.Code, failure.Message, failure.NextMode);
        }
        catch (KeyNotFoundException)
        {
            return Problem(404, AgentOperationCodes.NotFound, "The relationship was not found.");
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return Problem(
                503,
                "OPERATION_UNAVAILABLE",
                "A required service did not answer. Nothing was changed; try again."
            );
        }
    }

    private ObjectResult Problem(int status, string code, string detail, string? nextMode = null)
    {
        var response = StatusCode(
            status,
            new
            {
                type = $"https://waooaw.com/problems/{code.ToLowerInvariant().Replace('_', '-')}",
                title = "The request could not be completed",
                status,
                code,
                detail,
                nextMode,
            }
        );
        response.ContentTypes.Add("application/problem+json");
        return response;
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
}
