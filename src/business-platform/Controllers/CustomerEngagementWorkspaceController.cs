// Implements: architecture/reference/api-specs/customer-engagement-workspace-business-platform.openapi.yaml
// Constitutional basis: C-001, C-005, C-007, C-023, C-026, C-059, C-063

using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record ReplaceRelationshipWorkspacePreferencesRequest(
    int ExpectedVersion,
    string DefaultFocus,
    bool OpenProgressOnConversationFocus
);

public sealed record ResolveWorkspaceFocusRequest(string FocusToken);

public sealed record EndConversationChannelSessionRequest(
    int ExpectedVersion,
    string Confirmation,
    string? Reason
);

[ApiController]
[Authorize]
[CustomerIdentityRoute(requiresMembership: true)]
[Route("api/v1/employment/relationships/{relationshipId:guid}")]
public sealed class CustomerEngagementWorkspaceController(
    CustomerEngagementWorkspaceService service
) : ControllerBase
{
    [HttpGet("workspace/preferences")]
    public async Task<IActionResult> GetPreferencesAsync(
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return Unauthorized();
        try
        {
            return Ok(
                await service.GetPreferencesAsync(
                    tenantId,
                    participantId,
                    relationshipId,
                    cancellationToken
                )
            );
        }
        catch (CustomerEngagementNotAccessibleException)
        {
            return NotFoundProblem();
        }
    }

    [HttpPut("workspace/preferences")]
    public async Task<IActionResult> ReplacePreferencesAsync(
        Guid relationshipId,
        [FromBody] ReplaceRelationshipWorkspacePreferencesRequest request,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return Unauthorized();
        if (
            request.ExpectedVersion < 0
            || request.DefaultFocus
                is not (
                    "LIFECYCLE"
                    or "INDUCTION"
                    or "SKILLS_GOALS"
                    or "OPERATIONS"
                    or "PERFORMANCE"
                    or "BUDGET"
                    or "RIGHTS"
                )
        )
            return ProblemBody(400, "CEW_REQUEST_INVALID", "Workspace preferences are invalid.");
        try
        {
            return Ok(
                await service.ReplacePreferencesAsync(
                    tenantId,
                    participantId,
                    relationshipId,
                    request.ExpectedVersion,
                    request.DefaultFocus,
                    request.OpenProgressOnConversationFocus,
                    cancellationToken
                )
            );
        }
        catch (CustomerEngagementNotAccessibleException)
        {
            return NotFoundProblem();
        }
        catch (CustomerEngagementVersionConflictException)
        {
            return ProblemBody(
                409,
                "CEW_VERSION_CONFLICT",
                "Workspace preferences changed. Refresh before trying again."
            );
        }
    }

    [HttpGet("workspace/engagement-progress")]
    public async Task<IActionResult> GetProgressAsync(
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return Unauthorized();
        try
        {
            var progress = await service.GetProgressAsync(
                tenantId,
                participantId,
                relationshipId,
                cancellationToken
            );
            Response.Headers.ETag = $"\"{progress.ProjectionVersion}\"";
            Response.Headers.CacheControl = "no-store";
            return Ok(progress);
        }
        catch (CustomerEngagementNotAccessibleException)
        {
            return NotFoundProblem();
        }
    }

    [HttpPost("workspace/focus-resolutions")]
    public async Task<IActionResult> ResolveFocusAsync(
        Guid relationshipId,
        [FromBody] ResolveWorkspaceFocusRequest request,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return Unauthorized();
        if (string.IsNullOrWhiteSpace(request.FocusToken) || request.FocusToken.Length > 2048)
            return ProblemBody(400, "CEW_REQUEST_INVALID", "Focus reference is invalid.");
        try
        {
            Response.Headers.CacheControl = "no-store";
            return Ok(
                await service.ResolveFocusAsync(
                    tenantId,
                    participantId,
                    relationshipId,
                    request.FocusToken,
                    cancellationToken
                )
            );
        }
        catch (CustomerEngagementNotAccessibleException)
        {
            return NotFoundProblem();
        }
        catch (CustomerEngagementFocusExpiredException)
        {
            return ProblemBody(
                410,
                "CEW_FOCUS_EXPIRED",
                "This view reference expired. Refresh progress to continue."
            );
        }
        catch (CustomerEngagementFocusConflictException)
        {
            return ProblemBody(
                409,
                "CEW_FOCUS_CONFLICT",
                "Relationship context changed. Refresh progress to continue."
            );
        }
    }

    [HttpPost("conversation/channel-sessions/{channelSessionId:guid}/end")]
    public async Task<IActionResult> EndChannelSessionAsync(
        Guid relationshipId,
        Guid channelSessionId,
        [FromBody] EndConversationChannelSessionRequest request,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return Unauthorized();
        if (
            request.ExpectedVersion < 0
            || request.Confirmation != "END_CHANNEL_SESSION"
            || request.Reason?.Length > 500
            || !Request.Headers.TryGetValue("Idempotency-Key", out var idempotency)
            || string.IsNullOrWhiteSpace(idempotency)
            || idempotency.ToString().Length > 128
        )
            return ProblemBody(400, "CEW_REQUEST_INVALID", "End-session request is invalid.");
        var correlationId =
            Request.Headers.TryGetValue("X-Correlation-ID", out var correlation)
            && Guid.TryParse(correlation, out var parsed)
                ? parsed
                : Guid.NewGuid();
        try
        {
            var result = await service.EndChannelSessionAsync(
                tenantId,
                participantId,
                relationshipId,
                channelSessionId,
                idempotency.ToString(),
                Convert.ToHexStringLower(
                    SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(request)))
                ),
                request.ExpectedVersion,
                correlationId,
                cancellationToken
            );
            return Ok(
                new
                {
                    schemaVersion = "1",
                    result.ChannelSessionId,
                    result.Channel,
                    state = "ENDED",
                    result.SessionVersion,
                    result.EndedAt,
                    result.Replayed,
                    relationshipRemainsActive = true,
                    evidenceRef = result.EvidenceId.ToString("D"),
                }
            );
        }
        catch (CustomerEngagementNotAccessibleException)
        {
            return NotFoundProblem();
        }
        catch (CustomerEngagementVersionConflictException)
        {
            return ProblemBody(409, "CEW_VERSION_CONFLICT", "Channel session changed.");
        }
        catch (CustomerEngagementIdempotencyConflictException)
        {
            return ProblemBody(
                409,
                "CEW_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request."
            );
        }
        catch (ConstitutionalActionDeniedException)
        {
            return ProblemBody(
                403,
                "CEW_ACTION_DENIED",
                "Constitutional authorization denied this action."
            );
        }
    }

    private bool TryGetAuthority(out Guid tenantId, out Guid participantId)
    {
        tenantId = default;
        participantId = default;
        var tenant =
            HttpContext.Items[TenantIsolationMiddleware.TenantIdItemKey]?.ToString()
            ?? User.FindFirstValue("tenant_id");
        if (!Guid.TryParse(tenant, out tenantId))
            return false;
        if (
            HttpContext.Items[CustomerMembershipMiddleware.MembershipItem]
            is CustomerWorkspaceMembership membership
        )
        {
            participantId = membership.AccountId;
            return true;
        }
        var participant =
            User.FindFirstValue("participant_id") ?? User.FindFirstValue(ClaimTypes.NameIdentifier);
        return Guid.TryParse(participant, out participantId);
    }

    private ObjectResult NotFoundProblem() =>
        ProblemBody(
            404,
            "CEW_RESOURCE_NOT_ACCESSIBLE",
            "The requested resource was not found or is not accessible."
        );

    private ObjectResult ProblemBody(int status, string code, string title) =>
        new(
            new
            {
                type = $"https://waooaw.com/problems/{code.ToLowerInvariant().Replace('_', '-')}",
                title,
                status,
                code,
                correlationId = Guid.NewGuid(),
                retryable = status is 429 or 503,
            }
        )
        {
            StatusCode = status,
            ContentTypes = { "application/problem+json" },
        };
}
