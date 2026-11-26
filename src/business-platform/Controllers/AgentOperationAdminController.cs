// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R022, R028, R032
// Constitutional basis: C-023, C-059, C-063, C-088

using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.AgentOperation;
using Waooaw.BusinessPlatform.Services.PlatformAccess;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record AgentOperationSettingsBody(
    int ChatAllowanceDefault,
    Dictionary<string, int>? ChatAllowanceByProfessionalType,
    bool InstagramConnectEnabled,
    bool PublishSandboxOnly,
    List<string>? SandboxAccountIds,
    bool RegistryReadsEnabled
);

/// <summary>
/// Founder screen data for Agent Operation: the conversation allowance per package (default 1,000), the connector and
/// sandbox switches, the share of outcomes reached with the assistant (a trend, never a pass or fail line, and no
/// conversation content), and what needs the operator's attention. Reads need the Founder; writes also need a step-up.
/// </summary>
[ApiController]
[Authorize]
[StaffIdentityRoute]
[Route("api/v1/admin/agent-operation")]
public sealed class AgentOperationAdminController(
    AgentOperationService operation,
    TimeProvider clock
) : ControllerBase
{
    [HttpGet("settings")]
    public async Task<IActionResult> GetSettingsAsync(CancellationToken ct) =>
        IsFounder() ? Ok(await operation.GetSettingsAsync(ct)) : Denied();

    [HttpPut("settings")]
    public async Task<IActionResult> SaveSettingsAsync(
        [FromBody] AgentOperationSettingsBody body,
        CancellationToken ct
    )
    {
        if (!IsFounder())
            return Denied();
        if (!PlatformRoles.HasStepUp(User, clock.GetUtcNow()))
            return StatusCode(403, new { code = "OPERATION_STEP_UP_REQUIRED" });
        try
        {
            var saved = await operation.SaveSettingsAsync(
                User.FindFirstValue("sub")
                    ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
                    ?? "founder",
                new AgentOperationSettings(
                    body.ChatAllowanceDefault,
                    body.ChatAllowanceByProfessionalType
                        ?? new Dictionary<string, int>(StringComparer.Ordinal),
                    body.InstagramConnectEnabled,
                    body.PublishSandboxOnly,
                    body.SandboxAccountIds ?? [],
                    body.RegistryReadsEnabled
                ),
                ct
            );
            return Ok(saved);
        }
        catch (AgentOperationException failure)
        {
            return StatusCode(
                failure.Status,
                new { code = failure.Code, detail = failure.Message }
            );
        }
    }

    [HttpGet("share")]
    public async Task<IActionResult> ShareAsync(
        [FromQuery] DateOnly? from,
        [FromQuery] DateOnly? to,
        CancellationToken ct
    )
    {
        if (!IsFounder())
            return Denied();
        var end = to ?? DateOnly.FromDateTime(clock.GetUtcNow().UtcDateTime);
        return await Range(() => operation.GetShareAsync(from ?? end.AddDays(-29), end, ct));
    }

    [HttpGet("attention")]
    public async Task<IActionResult> AttentionAsync(
        [FromQuery] DateOnly? from,
        [FromQuery] DateOnly? to,
        CancellationToken ct
    )
    {
        if (!IsFounder())
            return Denied();
        var end = to ?? DateOnly.FromDateTime(clock.GetUtcNow().UtcDateTime);
        return await Range(() => operation.GetAttentionAsync(from ?? end.AddDays(-6), end, ct));
    }

    private async Task<IActionResult> Range<T>(Func<Task<T>> read)
    {
        Response.Headers.CacheControl = "no-store";
        try
        {
            return Ok(await read());
        }
        catch (AgentOperationException failure)
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

    private ObjectResult Denied() => StatusCode(403, new { code = "OPERATION_ADMIN_FORBIDDEN" });
}
