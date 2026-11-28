// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R006
// Constitutional basis: C-023, C-026, C-059, C-063, C-078

using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.CustomerDataRequests;
using Waooaw.BusinessPlatform.Services.PlatformAccess;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record ResolveDataRequestBody(string SchemaVersion, bool Completed, string Note);

/// <summary>The Founder's operator task list for customers' data copy and erasure requests.</summary>
[ApiController]
[Authorize]
[StaffIdentityRoute]
[Route("api/v1/operations/data-requests")]
public sealed class OperationsDataRequestsController(
    ICustomerDataRequests requests,
    TimeProvider clock
) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> ListOpenAsync(CancellationToken ct)
    {
        if (!IsFounder())
            return StatusCode(403, new { code = "OPERATIONS_FORBIDDEN" });
        var items = await requests.ListOpenForOperatorAsync(50, ct);
        return Ok(
            new
            {
                schemaVersion = "1.0.0",
                items = items.Select(value => new
                {
                    requestId = value.RequestId,
                    tenantId = value.TenantId,
                    kind = value.Kind,
                    state = value.State,
                    requestedAt = value.RequestedAt,
                }),
            }
        );
    }

    [HttpPost("{requestId:guid}/resolve")]
    public async Task<IActionResult> ResolveAsync(
        Guid requestId,
        [FromBody] ResolveDataRequestBody body,
        CancellationToken ct
    )
    {
        if (!IsFounder())
            return StatusCode(403, new { code = "OPERATIONS_FORBIDDEN" });
        if (!PlatformRoles.HasStepUp(User, clock.GetUtcNow()))
            return StatusCode(403, new { code = "OPERATIONS_STEP_UP_REQUIRED" });
        if (body.SchemaVersion != "1.0.0" || string.IsNullOrWhiteSpace(body.Note))
            return Problem(statusCode: 400, title: "Invalid data request resolution");
        var subject =
            User.FindFirstValue("participant_id")
            ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub")
            ?? "unknown";
        var resolved = await requests.ResolveAsync(
            requestId,
            body.Completed,
            subject,
            body.Note.Trim(),
            ct
        );
        return resolved is null
            ? Problem(statusCode: 409, title: "The request is not open")
            : Ok(CustomerDataRequestsController.ToResponse(resolved));
    }

    private bool IsFounder() =>
        User.IsInRole(PlatformRoles.Founder)
        || User.Claims.Where(claim => claim.Type is ClaimTypes.Role or "role" or "participant_role")
            .Any(claim =>
                string.Equals(
                    claim.Value,
                    PlatformRoles.Founder,
                    StringComparison.OrdinalIgnoreCase
                )
            );
}
