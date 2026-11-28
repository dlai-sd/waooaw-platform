// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R006
// Constitutional basis: C-023, C-026, C-059, C-063, C-078

using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.CustomerDataRequests;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record CustomerDataRequestBody(string SchemaVersion, string Kind);

/// <summary>
/// A customer asks for a copy of their data or for their account to be erased. Only the account owner may ask. The
/// platform records the request and the Founder handles it as an operator task; asking does not erase anything.
/// </summary>
[ApiController]
[Authorize]
[CustomerIdentityRoute(requiresMembership: true)]
[Route("api/v1/customer-data-requests")]
public sealed class CustomerDataRequestsController(ICustomerDataRequests requests) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> ListAsync(CancellationToken ct)
    {
        if (!TryGetTenantId(out var tenantId))
            return Unauthorized();
        var items = await requests.ListForCustomerAsync(tenantId, ct);
        return Ok(new { schemaVersion = "1.0.0", items = items.Select(ToResponse) });
    }

    [HttpPost]
    public async Task<IActionResult> RequestAsync(
        [FromBody] CustomerDataRequestBody body,
        CancellationToken ct
    )
    {
        if (!TryGetTenantId(out var tenantId))
            return Unauthorized();
        if (
            Request.HttpContext.Items[CustomerMembershipMiddleware.MembershipItem]
                is not CustomerWorkspaceMembership membership
            || !membership.Roles.Contains("OWNER", StringComparer.Ordinal)
        )
            return StatusCode(403, new { code = "DATA_REQUEST_OWNER_ONLY" });
        if (
            body.SchemaVersion != "1.0.0"
            || !CustomerDataRequestKinds.IsValid(body.Kind)
            || !Guid.TryParse(Request.Headers["Idempotency-Key"].FirstOrDefault(), out var key)
        )
            return Problem(statusCode: 400, title: "Invalid data request");
        var subject =
            User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub")
            ?? "unknown";
        var actorHash = Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(subject)));
        var (created, isNew) = await requests.RequestAsync(tenantId, actorHash, body.Kind, key, ct);
        return isNew ? StatusCode(201, ToResponse(created)) : Ok(ToResponse(created));
    }

    internal static object ToResponse(CustomerDataRequest request) =>
        new
        {
            requestId = request.RequestId,
            kind = request.Kind,
            state = request.State,
            requestedAt = request.RequestedAt,
            resolvedAt = request.ResolvedAt,
            resolutionNote = request.ResolutionNote,
        };

    private bool TryGetTenantId(out Guid tenantId)
    {
        tenantId = default;
        return HttpContext.Items.TryGetValue(
                TenantIsolationMiddleware.TenantIdItemKey,
                out var value
            )
            && value is string text
            && Guid.TryParse(text, out tenantId);
    }
}
