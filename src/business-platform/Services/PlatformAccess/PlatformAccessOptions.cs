// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004
// Constitutional basis: C-009, C-023, C-026, C-059, C-063

using System.Net.Mail;
using System.Security.Claims;
using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services.PlatformAccess;

public sealed class ConfiguredFounder
{
    public string Email { get; set; } = string.Empty;
    public string? Subject { get; set; }

    public string NormalizedEmail => PlatformRoles.NormalizeEmail(Email);
}

/// <summary>
/// Founder identities come only from the environment configuration (PlatformAccess:Founders). The Business
/// Platform re-asserts them at every start, which is why they survive redeploys and database resets.
/// </summary>
public sealed class PlatformAccessOptions
{
    public const string SectionName = "PlatformAccess";

    public List<ConfiguredFounder> Founders { get; set; } = [];
    public int ApprovedGrantDays { get; set; } = 90;
    public int MaximumRequestsPerDay { get; set; } = 3;
    public int MaximumPendingRequests { get; set; } = 100;
    public int ResolutionCacheSeconds { get; set; } = 15;
}

public sealed class PlatformAccessOptionsValidator : IValidateOptions<PlatformAccessOptions>
{
    public ValidateOptionsResult Validate(string? name, PlatformAccessOptions options)
    {
        if (options.ApprovedGrantDays is < 1 or > 365)
            return ValidateOptionsResult.Fail("PlatformAccess:ApprovedGrantDays must be 1 to 365.");
        if (options.MaximumRequestsPerDay is < 1 or > 20)
            return ValidateOptionsResult.Fail(
                "PlatformAccess:MaximumRequestsPerDay must be 1 to 20."
            );
        if (options.MaximumPendingRequests is < 1 or > 1000)
            return ValidateOptionsResult.Fail(
                "PlatformAccess:MaximumPendingRequests must be 1 to 1000."
            );
        if (options.ResolutionCacheSeconds is < 0 or > 60)
            return ValidateOptionsResult.Fail(
                "PlatformAccess:ResolutionCacheSeconds must be 0 to 60."
            );
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var founder in options.Founders)
        {
            if (!PlatformRoles.IsValidEmail(founder.Email))
                return ValidateOptionsResult.Fail(
                    "Every PlatformAccess:Founders entry needs a valid email address."
                );
            if (
                founder.Subject is not null
                && (
                    founder.Subject.Length is < 8 or > 128 || founder.Subject.Any(char.IsWhiteSpace)
                )
            )
                return ValidateOptionsResult.Fail(
                    "PlatformAccess:Founders subject must be 8 to 128 characters without spaces."
                );
            if (!seen.Add(founder.NormalizedEmail))
                return ValidateOptionsResult.Fail(
                    "PlatformAccess:Founders must not repeat an email address."
                );
        }
        return ValidateOptionsResult.Success;
    }
}

public static class PlatformRoles
{
    public const string Founder = "founder";
    public const string PricingAdmin = "pricing_admin";

    // A Keycloak realm role held by the acceptance provisioning client only; it is never a stored grant or requestable.
    public const string AcceptanceProvisioner = "acceptance-provisioner";
    public const string ClaimSourceMarker = "waooaw.platform-access";

    // Every role the Business Platform checks, other than the Founder, which only configuration can assign.
    public static readonly IReadOnlyList<string> Requestable =
    [
        PricingAdmin,
        "admission_operator",
        "validator_operator",
        "admission_reviewer",
        "admission_approver",
        "platform_activation_authority",
        "constitutional_authority",
        "operations_authority",
        "lifecycle_authority",
    ];

    public static string NormalizeEmail(string email) => email.Trim().ToLowerInvariant();

    public static bool IsValidEmail(string? email) =>
        !string.IsNullOrWhiteSpace(email)
        && email.Length <= 254
        && MailAddress.TryCreate(email.Trim(), out var parsed)
        && parsed.Address == email.Trim();

    /// <summary>A verified email and a subject are both required; an unverified email never earns a role.</summary>
    public static bool TryIdentity(ClaimsPrincipal user, out string email, out string subject)
    {
        email = string.Empty;
        // JwtBearer maps inbound claims by default (sub -> NameIdentifier, email -> Email); accept both forms.
        subject =
            user.FindFirstValue("sub")
            ?? user.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? string.Empty;
        var claimed = user.FindFirstValue("email") ?? user.FindFirstValue(ClaimTypes.Email);
        if (
            user.Identity?.IsAuthenticated != true
            || subject.Length is < 8 or > 128
            || !string.Equals(
                user.FindFirstValue("email_verified"),
                "true",
                StringComparison.OrdinalIgnoreCase
            )
            || !IsValidEmail(claimed)
        )
            return false;
        email = NormalizeEmail(claimed!);
        return true;
    }

    // JwtBearer maps acr/amr to these long names by default; a real token only ever shows the mapped form.
    private const string MappedAcr = "http://schemas.microsoft.com/claims/authnclassreference";
    private const string MappedAmr = "http://schemas.microsoft.com/claims/authnmethodsreferences";

    /// <summary>The same bar as the identity lifecycle step-up: fresh sign-in, assurance level 2 or 3, strong method.</summary>
    public static bool HasStepUp(ClaimsPrincipal user, DateTimeOffset now) =>
        user.FindFirstValue("auth_time") is string authTime
        && long.TryParse(authTime, out var authenticatedAt)
        && now - DateTimeOffset.FromUnixTimeSeconds(authenticatedAt) is var age
        && age >= TimeSpan.FromSeconds(-30)
        && age <= TimeSpan.FromMinutes(5)
        && (user.FindFirstValue("acr") ?? user.FindFirstValue(MappedAcr))
            is "2"
                or "3"
                or "urn:waooaw:aal2"
                or "urn:waooaw:aal3"
        && user.Claims.Where(claim => claim.Type is "amr" or MappedAmr)
            .SelectMany(claim => claim.Value.Split(' ', StringSplitOptions.RemoveEmptyEntries))
            .Any(method => method is "mfa" or "otp" or "webauthn");
}
