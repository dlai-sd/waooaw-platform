// Implements: architecture/reference/product/ae01-solution-contract.md § Canonical API and Compatibility
// constitutional_basis: C-005, C-023, C-026, C-059

using System.Security.Claims;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Controllers;

internal static class LegacyEmploymentCompatibility
{
    public static bool TryGetIdentity(HttpContext context, out Guid tenantId, out Guid participantId)
    {
        tenantId = default;
        participantId = default;
        var participant = context.User.FindFirstValue("participant_id")
            ?? context.User.FindFirstValue(ClaimTypes.NameIdentifier);
        return context.Items.TryGetValue(TenantIsolationMiddleware.TenantIdItemKey, out var tenant)
            && tenant is string tenantText
            && Guid.TryParse(tenantText, out tenantId)
            && Guid.TryParse(participant, out participantId);
    }

    public static void AddDeprecationHeaders(HttpResponse response, Guid relationshipId)
    {
        response.Headers["Deprecation"] = "true";
        response.Headers.Link = $"</api/v1/employment/relationships/{relationshipId}>; rel=\"successor-version\"";
    }
}