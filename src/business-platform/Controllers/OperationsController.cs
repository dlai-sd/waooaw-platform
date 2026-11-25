// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R008, WC171-R009, WC171-R010
// Constitutional basis: C-001, C-005, C-007, C-023, C-049, C-059, C-063
// IB: IB-171

using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Operations;
using Waooaw.BusinessPlatform.Services.PlatformAccess;
using Waooaw.BusinessPlatform.Services.RealWork;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record BlockedMessageResolveRequest(
    string SchemaVersion,
    string Action,
    string Reason
);

public sealed record SpendDiscrepancyResolveRequest(
    string SchemaVersion,
    Guid TenantId,
    Guid EvidenceId
);

/// <summary>
/// The operations console (alerts-oversight.openapi.yaml). Staff route, never a customer route. The Founder and the
/// operations authority read; only the Founder writes, and a write needs a step-up. Nothing here returns a recipient,
/// a message body or another tenant's content beyond what an operator needs to act.
/// </summary>
[ApiController]
[Authorize]
[StaffIdentityRoute]
[Route("api/v1/operations")]
public sealed class OperationsController(
    OperationsConsoleService console,
    OperatorPageService pages,
    RealWorkTimelineService timeline,
    ISpendChainReader spendChain,
    TimeProvider clock
) : ControllerBase
{
    public const string OperationsAuthority = "operations_authority";

    [HttpGet("overview")]
    public async Task<IActionResult> OverviewAsync(CancellationToken cancellationToken) =>
        !CanRead()
            ? Forbidden()
            : Ok(await console.OverviewAsync(clock.GetUtcNow(), cancellationToken));

    [HttpGet("blocked-messages")]
    public async Task<IActionResult> ListBlockedAsync(CancellationToken cancellationToken)
    {
        if (!CanRead())
            return Forbidden();
        try
        {
            return Ok(
                new
                {
                    schemaVersion = "1.0.0",
                    items = await console.ListBlockedAsync(clock.GetUtcNow(), cancellationToken),
                }
            );
        }
        catch (WhatsAppCapabilityUnavailableException unavailable)
        {
            return StatusCode(
                503,
                new { code = "OPERATIONS_WHATSAPP_INACTIVE", reason = unavailable.ReasonCode }
            );
        }
    }

    [HttpPost("blocked-messages/{outboxId:guid}/resolve")]
    public async Task<IActionResult> ResolveBlockedAsync(
        Guid outboxId,
        [FromBody] BlockedMessageResolveRequest request,
        [FromHeader(Name = "Idempotency-Key")] string? idempotencyKey,
        CancellationToken cancellationToken
    )
    {
        if (!IsRole(PlatformRoles.Founder))
            return Forbidden();
        if (!PlatformRoles.HasStepUp(User, clock.GetUtcNow()))
            return StatusCode(403, new { code = "OPERATIONS_STEP_UP_REQUIRED" });
        if (request.SchemaVersion != "1.0.0" || !Guid.TryParse(idempotencyKey, out var key))
            return Problem(statusCode: 400, title: "Invalid resolution");
        try
        {
            var result = await console.ResolveBlockedAsync(
                outboxId,
                request.Action,
                request.Reason,
                Subject(),
                key,
                clock.GetUtcNow(),
                cancellationToken
            );
            return result.Replayed ? Ok(result) : StatusCode(201, result);
        }
        catch (ArgumentException)
        {
            return Problem(statusCode: 400, title: "Invalid resolution");
        }
        catch (KeyNotFoundException)
        {
            return NotFound();
        }
        catch (BlockedMessageStateException)
        {
            return Conflict(new { code = "OPERATIONS_MESSAGE_NOT_BLOCKED" });
        }
        catch (BlockedMessageConflictException)
        {
            return Conflict(new { code = "OPERATIONS_IDEMPOTENCY_CONFLICT" });
        }
        catch (WhatsAppCapabilityUnavailableException unavailable)
        {
            return StatusCode(
                503,
                new { code = "OPERATIONS_WHATSAPP_INACTIVE", reason = unavailable.ReasonCode }
            );
        }
    }

    [HttpGet("pages")]
    public async Task<IActionResult> ListPagesAsync(CancellationToken cancellationToken)
    {
        if (!CanRead())
            return Forbidden();
        var items = await pages.RecentAsync(50, cancellationToken);
        return Ok(
            new
            {
                schemaVersion = "1.0.0",
                items = items.Select(value => new
                {
                    signal = value.Signal,
                    outcome = value.Outcome,
                    reason = value.Reason,
                    recordedAt = value.RecordedAt,
                }),
            }
        );
    }

    [HttpPost("pages/{code}/acknowledge")]
    public async Task<IActionResult> AcknowledgePageAsync(
        string code,
        CancellationToken cancellationToken
    )
    {
        if (!IsRole(PlatformRoles.Founder))
            return Forbidden();
        if (
            code.Length is < 3 or > 160
            || !code.All(character =>
                char.IsAsciiLetterUpper(character)
                || char.IsAsciiDigit(character)
                || character == '_'
            )
        )
            return Problem(statusCode: 400, title: "Invalid page code");
        await pages.AcknowledgeAsync(code, Subject(), cancellationToken);
        return Accepted(
            new
            {
                code,
                acknowledgedForMinutes = (int)
                    OperatorPageService.AcknowledgementWindow.TotalMinutes,
            }
        );
    }

    [HttpGet("relationships/{relationshipId:guid}/work-timeline")]
    public IActionResult GetWorkTimeline(Guid relationshipId, [FromQuery] Guid tenantId) =>
        !CanRead() ? Forbidden()
        : tenantId == Guid.Empty ? Problem(statusCode: 400, title: "tenantId is required")
        : Ok(timeline.Read(tenantId, relationshipId));

    [HttpGet("relationships/{relationshipId:guid}/spend-chain")]
    public async Task<IActionResult> GetSpendChainAsync(
        Guid relationshipId,
        [FromQuery] Guid tenantId,
        CancellationToken cancellationToken
    )
    {
        if (!CanRead())
            return Forbidden();
        if (tenantId == Guid.Empty)
            return Problem(statusCode: 400, title: "tenantId is required");
        try
        {
            return Ok(await spendChain.ReadAsync(tenantId, relationshipId, cancellationToken));
        }
        catch (SpendChainUnavailableException)
        {
            return StatusCode(503, new { code = "SPEND_CHAIN_READ_UNAVAILABLE" });
        }
    }

    [HttpPost("relationships/{relationshipId:guid}/spend-discrepancies/{resultId:guid}/resolve")]
    public async Task<IActionResult> ResolveDiscrepancyAsync(
        Guid relationshipId,
        Guid resultId,
        [FromBody] SpendDiscrepancyResolveRequest request,
        CancellationToken cancellationToken
    )
    {
        if (!IsRole(PlatformRoles.Founder))
            return Forbidden();
        if (!PlatformRoles.HasStepUp(User, clock.GetUtcNow()))
            return StatusCode(403, new { code = "OPERATIONS_STEP_UP_REQUIRED" });
        if (
            request.SchemaVersion != "1.0.0"
            || request.TenantId == Guid.Empty
            || request.EvidenceId == Guid.Empty
        )
            return Problem(statusCode: 400, title: "Invalid resolution");
        try
        {
            var resolved = await spendChain.ResolveDiscrepancyAsync(
                request.TenantId,
                relationshipId,
                resultId,
                request.EvidenceId,
                cancellationToken
            );
            return resolved ? Ok(new { resultId, state = "RESOLVED" }) : NotFound();
        }
        catch (SpendChainUnavailableException)
        {
            return StatusCode(503, new { code = "SPEND_CHAIN_READ_UNAVAILABLE" });
        }
    }

    private bool CanRead() => IsRole(PlatformRoles.Founder) || IsRole(OperationsAuthority);

    private ObjectResult Forbidden() => StatusCode(403, new { code = "OPERATIONS_FORBIDDEN" });

    private string Subject() =>
        User.FindFirstValue("participant_id")
        ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
        ?? User.FindFirstValue("sub")
        ?? "unknown";

    private bool IsRole(string role) =>
        User.IsInRole(role)
        || User.Claims.Where(claim => claim.Type is ClaimTypes.Role or "role" or "participant_role")
            .Any(claim => string.Equals(claim.Value, role, StringComparison.OrdinalIgnoreCase));
}
