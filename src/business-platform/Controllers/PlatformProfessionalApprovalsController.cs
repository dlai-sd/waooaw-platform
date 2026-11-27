// Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R023, R024
// Constitutional basis: C-023, C-059, C-063, C-088

using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.PlatformAccess;
using Waooaw.BusinessPlatform.Services.PlatformApprovals;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record PlatformProfessionalDecisionBody(string? Reason);

/// <summary>
/// Founder screen data for Professionals: which professional versions customers may take on Trial or Hire. Reading needs
/// the Founder; approving, suspending or retiring also needs a fresh strong sign-in, and every decision is recorded.
/// </summary>
[ApiController]
[Authorize]
[StaffIdentityRoute]
[Route("api/v1/admin/professionals")]
public sealed class PlatformProfessionalApprovalsController(
    PlatformProfessionalApprovalService approvals,
    TimeProvider clock
) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> ListAsync(CancellationToken ct) =>
        IsFounder() ? Ok(new { items = await approvals.ListAsync(ct) }) : Denied();

    // "{action}" is a reserved routing word and never matches, so the decision word has its own name.
    [HttpPost("{type}/versions/{version}/{decision}")]
    public async Task<IActionResult> DecideAsync(
        string type,
        string version,
        string decision,
        [FromBody] PlatformProfessionalDecisionBody? body,
        CancellationToken ct
    )
    {
        if (!IsFounder())
            return Denied();
        if (!PlatformRoles.HasStepUp(User, clock.GetUtcNow()))
            return StatusCode(403, new { code = "PROFESSIONAL_APPROVAL_STEP_UP_REQUIRED" });
        try
        {
            var actor =
                User.FindFirstValue("sub")
                ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
                ?? "founder";
            return Ok(
                await approvals.DecideAsync(type, version, decision, actor, body?.Reason, ct)
            );
        }
        catch (PlatformApprovalException failure)
        {
            return StatusCode(
                failure.Status,
                new { code = failure.Code, detail = failure.Message }
            );
        }
    }

    private bool IsFounder()
    {
        Response.Headers.CacheControl = "no-store";
        return User.Identity?.IsAuthenticated == true
            && (
                User.IsInRole(PlatformRoles.Founder)
                || User.Claims.Where(claim =>
                        claim.Type is ClaimTypes.Role or "role" or "participant_role"
                    )
                    .Any(claim =>
                        string.Equals(
                            claim.Value,
                            PlatformRoles.Founder,
                            StringComparison.OrdinalIgnoreCase
                        )
                    )
            );
    }

    private ObjectResult Denied() =>
        StatusCode(403, new { code = "PROFESSIONAL_APPROVAL_FORBIDDEN" });
}
