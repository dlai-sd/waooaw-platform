// Implements: architecture/reference/product/ae02-real-work-solution-contract.md section 2 Activation contract (WC170-R001, WC170-R002)
// Constitutional basis: C-023, C-049, C-059, C-063
// IB: IB-170

using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.PlatformAccess;

namespace Waooaw.BusinessPlatform.Controllers;

/// <summary>
/// Founder-only read-back of whether the real-work chain can run. It reports the deployed gate and epoch, and a named
/// BLOCKED-BY-FLAG reason for every fact that is not ready. It never returns a credential value.
/// </summary>
[ApiController]
[Authorize]
[StaffIdentityRoute]
[Route("api/v1/admin/employment/readiness")]
public sealed class EmploymentReadinessController(EmploymentReadinessService readiness)
    : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> GetAsync(CancellationToken cancellationToken)
    {
        Response.Headers.CacheControl = "no-store";
        if (User.Identity?.IsAuthenticated != true)
            return StatusCode(401, new { code = "EMPLOYMENT_READINESS_FORBIDDEN" });
        var isFounder =
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
                );
        if (!isFounder)
            return StatusCode(403, new { code = "EMPLOYMENT_READINESS_FORBIDDEN" });
        return Ok(await readiness.ReportAsync(cancellationToken));
    }
}
