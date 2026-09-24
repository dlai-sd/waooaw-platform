// Implements: work-contracts/WC-096-conversational-customer-portal.md §5
// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R004
// constitutional_basis: C-005, C-026, C-049, C-059, C-063

using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

[ApiController]
[Authorize]
[Route("api/v1/customer-portal/interactions/portal/messages")]
public sealed class PortalInteractionsController(
    PortalInteractionService service,
    ILogger<PortalInteractionsController> logger
) : ControllerBase
{
    [HttpGet]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> ListAsync(
        [FromQuery] string? cursor,
        [FromQuery] int limit = 40,
        CancellationToken cancellationToken = default
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return SessionRequired();
        try
        {
            return Ok(
                await service.ListAsync(tenantId, participantId, cursor, limit, cancellationToken)
            );
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            LogUnexpectedFailure(exception, tenantId, participantId);
            return MapProblem(exception);
        }
    }

    [HttpPost]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> SendAsync(
        [FromBody] SendPortalInteractionMessageRequestV1 request,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return SessionRequired();
        if (
            !Guid.TryParse(
                Request.Headers["Idempotency-Key"].FirstOrDefault(),
                out var idempotencyKey
            )
        )
        {
            return Problem(
                StatusCodes.Status400BadRequest,
                "PORTAL_INTERACTION_REQUEST_INVALID",
                "A UUID Idempotency-Key header is required."
            );
        }
        try
        {
            var result = await service.SendAsync(
                tenantId,
                participantId,
                idempotencyKey,
                request,
                cancellationToken
            );
            return result.Replayed ? Ok(result.Value) : Accepted(result.Value);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            LogUnexpectedFailure(exception, tenantId, participantId);
            return MapProblem(exception);
        }
    }

    private void LogUnexpectedFailure(Exception exception, Guid tenantId, Guid participantId)
    {
        if (
            exception
                is ConversationRequestException
                    or ConversationIdempotencyConflictException
                    or ConversationStateConflictException
                    or ConversationCursorExpiredException
        )
        {
            return;
        }

        logger.LogError(
            exception,
            "Portal interaction failed for tenant {TenantId}, participant {ParticipantId}, trace {TraceIdentifier}.",
            tenantId,
            participantId,
            HttpContext.TraceIdentifier
        );
    }

    private bool TryGetAuthority(out Guid tenantId, out Guid participantId)
    {
        if (
            HttpContext.Items.TryGetValue(
                CustomerMembershipMiddleware.MembershipItem,
                out var value
            ) && value is CustomerWorkspaceMembership membership
        )
        {
            tenantId = membership.TenantId;
            participantId = membership.AccountId;
            return true;
        }
        tenantId = default;
        participantId = default;
        var tenantValid =
            HttpContext.Items.TryGetValue(
                TenantIsolationMiddleware.TenantIdItemKey,
                out var tenantValue
            )
            && tenantValue is string tenantText
            && Guid.TryParse(tenantText, out tenantId);
        var participantValue =
            User.FindFirstValue("participant_id")
            ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub");
        return tenantValid && Guid.TryParse(participantValue, out participantId);
    }

    private IActionResult MapProblem(Exception exception) =>
        exception switch
        {
            ConversationRequestException => Problem(
                StatusCodes.Status400BadRequest,
                "PORTAL_INTERACTION_REQUEST_INVALID",
                "Portal interaction request is malformed or unsupported."
            ),
            ConversationIdempotencyConflictException => Problem(
                StatusCodes.Status409Conflict,
                "PORTAL_INTERACTION_IDEMPOTENCY_CONFLICT",
                "Idempotency identity conflicts with a prior request."
            ),
            ConversationStateConflictException => Problem(
                StatusCodes.Status409Conflict,
                "PORTAL_INTERACTION_STATE_CONFLICT",
                "Authoritative portal interaction state must be reconciled."
            ),
            ConversationCursorExpiredException => Problem(
                StatusCodes.Status410Gone,
                "PORTAL_INTERACTION_CURSOR_EXPIRED",
                "Portal interaction cursor can no longer be resumed."
            ),
            _ => Problem(
                StatusCodes.Status503ServiceUnavailable,
                "PORTAL_INTERACTION_UNAVAILABLE",
                "Portal interaction is temporarily unavailable."
            ),
        };

    private ObjectResult SessionRequired() =>
        Problem(
            StatusCodes.Status401Unauthorized,
            "PORTAL_INTERACTION_SESSION_REQUIRED",
            "Authenticated portal session required."
        );

    private ObjectResult Problem(int status, string code, string title) =>
        new(
            new
            {
                type = $"https://api.waooaw.com/problems/{code.ToLowerInvariant().Replace('_', '-')}",
                title,
                status,
                code,
                correlationId = Guid.NewGuid(),
            }
        )
        {
            StatusCode = status,
            ContentTypes = { "application/problem+json" },
        };
}
