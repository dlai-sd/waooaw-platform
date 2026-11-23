// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §5 and adr/ADR-055-synthetic-acceptance-tenants-and-evidence.md decision 4
// Constitutional basis: C-059 (Implementation Traceability)

using System.Security.Claims;
using System.Text.Json;
using Waooaw.BusinessPlatform.Services.PlatformAccess;

namespace Waooaw.BusinessPlatform.Services.AcceptanceSynthetic;

/// <summary>
/// Marks the internal acceptance route. It is not a customer route and carries no tenant: the web tenant-isolation
/// step is skipped for it, and the only authority is <see cref="AcceptanceProvisionerAuthority"/>.
/// </summary>
[AttributeUsage(AttributeTargets.Class)]
public sealed class AcceptanceProvisionerRouteAttribute : Attribute;

public sealed record AcceptanceProvisioner(string Issuer, string Principal);

/// <summary>
/// Decides who may write the synthetic registry: a Keycloak token already validated by JwtBearer, issued to the
/// acceptance provisioning client and carrying the realm role acceptance-provisioner (same validation family as the
/// pricing_admin role routes, but a Keycloak realm role rather than a stored grant). The role is never requestable,
/// and nothing a customer controls is read.
/// </summary>
public static class AcceptanceProvisionerAuthority
{
    public const string ClientId = "waooaw-acceptance-provisioner";

    public static bool TryResolve(ClaimsPrincipal? user, out AcceptanceProvisioner? provisioner)
    {
        provisioner = null;
        if (user?.Identity?.IsAuthenticated != true)
            return false;
        // A token that names its own roles, or that was issued to any other client, never reaches this route.
        if (user.HasClaim(claim => claim.Type == "waooaw_roles"))
            return false;
        var client = Single(user, "azp");
        var issuer = Single(user, "iss");
        if (
            !string.Equals(client, ClientId, StringComparison.Ordinal)
            || issuer is null
            || issuer.Length > 256
            || !HoldsRealmRole(user, PlatformRoles.AcceptanceProvisioner)
        )
            return false;
        var principal = Single(user, "sub") ?? Single(user, ClaimTypes.NameIdentifier) ?? client!;
        provisioner = new AcceptanceProvisioner(
            issuer,
            principal.Length > 128 ? principal[..128] : principal
        );
        return true;
    }

    private static string? Single(ClaimsPrincipal user, string type)
    {
        var values = user.FindAll(type).Select(claim => claim.Value).Distinct().ToArray();
        return values.Length == 1 && !string.IsNullOrWhiteSpace(values[0]) ? values[0] : null;
    }

    // Keycloak puts realm roles in the realm_access object; no other claim is accepted as a realm role.
    private static bool HoldsRealmRole(ClaimsPrincipal user, string role)
    {
        foreach (var claim in user.FindAll("realm_access"))
        {
            try
            {
                using var document = JsonDocument.Parse(claim.Value);
                if (
                    document.RootElement.ValueKind == JsonValueKind.Object
                    && document.RootElement.TryGetProperty("roles", out var roles)
                    && roles.ValueKind == JsonValueKind.Array
                    && roles
                        .EnumerateArray()
                        .Any(value =>
                            value.ValueKind == JsonValueKind.String && value.GetString() == role
                        )
                )
                    return true;
            }
            catch (JsonException)
            {
                // A malformed claim holds no role.
            }
        }
        return false;
    }
}
