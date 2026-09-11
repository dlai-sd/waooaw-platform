// Implements: architecture/reference/components/identity-boundary.md §7 Canonical Public API
// constitutional_basis: C-023, C-026, C-059

using System.Security.Claims;
using System.Net.Mail;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;
using Microsoft.Extensions.Logging;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

// ── Request models (no tenant_id field per contract invariant §1.7) ──────────

public sealed record StartRegistrationRequest(string LanguagePreference);

public sealed record UpdateRegistrationProfileRequest(
    string DisplayName,
    string BusinessName,
    string BusinessDomain,
    string LanguagePreference);

public sealed record StartEmailVerificationRequest(string Email);

public sealed record StartMobileVerificationRequest(string Mobile);

public sealed record ConfirmVerificationRequest(Guid ChallengeId, string Code);

public sealed record StartAccountLinkRequest(Guid VerifiedMobileProofId);

public sealed record UpdateCustomerProfileRequest(
    string SchemaVersion,
    string DisplayName,
    string OrganizationDisplayName);

public sealed record NotificationPreferencesRequest(
    IReadOnlyList<string> ApprovalRequests,
    IReadOnlyList<string> MaturityReports,
    IReadOnlyList<string> MonthlyNarratives,
    IReadOnlyList<string> SelfGovernanceAlerts);

public sealed record UpdateCustomerSettingsRequest(
    string SchemaVersion,
    string Locale,
    string Theme,
    string TimestampVisibility,
    NotificationPreferencesRequest NotificationPreferences);

// ── Response models (exactly matching OpenAPI schemas) ───────────────────────

public sealed record IdentityRegistrationResponse(
    Guid RegistrationId,
    string State,
    string NextAction,
    string AuthenticationPath,
    string? ProviderLabel,
    bool EmailVerified,
    bool MobileVerified,
    string? MaskedEmail,
    string? MaskedMobile,
    IdentityRegistrationProfileResponse Profile,
    DateTimeOffset ExpiresAt,
    DateTimeOffset UpdatedAt);

public sealed record IdentityRegistrationProfileResponse(
    string? DisplayName,
    string? BusinessName,
    string? BusinessDomain,
    string? LanguagePreference);

public sealed record IdentityVerificationChallengeResponse(
    Guid ChallengeId,
    string Purpose,
    string State,
    string MaskedDestination,
    DateTimeOffset ExpiresAt,
    DateTimeOffset ResendAfter);

public sealed record IdentityCompletionResponse(
    string Outcome,
    Guid AccountReference,
    string AssuranceLevel,
    string DefaultTarget);

public sealed record IdentityAccountLinkResponse(
    Guid LinkId,
    string State,
    string RequiredAssurance,
    string MaskedMobile,
    DateTimeOffset ExpiresAt,
    DateTimeOffset UpdatedAt);

public sealed record IdentityMobileStatusResponse(
    bool MobileVerified,
    string MaskedMobile,
    DateTimeOffset VerifiedAt);

public sealed record IdentityProviderCollectionResponse(
    IReadOnlyList<IdentityProviderProjection> Providers);

public sealed record IdentitySessionResponse(
    Guid AccountReference,
    IReadOnlyList<string> Roles,
    IReadOnlyList<string> Capabilities,
    string AssuranceLevel,
    string AuthenticationPath,
    bool EmailVerified,
    bool MobileVerified,
    DateTimeOffset AuthenticatedAt,
    DateTimeOffset ExpiresAt,
    string NextAction);

public sealed record CustomerProfileResponse(
    string SchemaVersion,
    string DisplayName,
    string OrganizationDisplayName,
    string Email,
    bool EmailVerified,
    bool MobileVerified,
    string ActiveRole,
    IReadOnlyList<object> SwitchableAccounts,
    DateTimeOffset UpdatedAt);

public sealed record NotificationPreferencesResponse(
    IReadOnlyList<string> ApprovalRequests,
    IReadOnlyList<string> MaturityReports,
    IReadOnlyList<string> MonthlyNarratives,
    IReadOnlyList<string> SelfGovernanceAlerts);

public sealed record CustomerSettingsResponse(
    string SchemaVersion,
    string Locale,
    string Theme,
    string TimestampVisibility,
    NotificationPreferencesResponse NotificationPreferences,
    IReadOnlyList<string> AvailableSecurityActions,
    DateTimeOffset UpdatedAt);

public sealed record CustomerLoginMethodResponse(
    string Provider,
    string State,
    string? MaskedIdentifier);

public sealed record CustomerLoginMethodCollectionResponse(
    string SchemaVersion,
    IReadOnlyList<CustomerLoginMethodResponse> Items);

[ApiController]
[Route("api/v1/identity")]
[Authorize]
public sealed class IdentityController(
    IdentityService identityService,
    IdentityProviderProjectionService providerProjectionService,
    ILogger<IdentityController> logger,
    CustomerIdentityJourneyService? customerJourney = null) : ControllerBase, IAsyncActionFilter
{
    [NonAction]
    public async Task OnActionExecutionAsync(ActionExecutingContext context, ActionExecutionDelegate next)
    {
        if (context.ActionDescriptor.EndpointMetadata.OfType<IAllowAnonymous>().Any())
        {
            await next();
            return;
        }
        if (customerJourney is null || !HttpContext.Items.ContainsKey(CustomerMembershipMiddleware.JourneyItem))
        {
            context.Result = IdentityProblem(503, "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "The customer identity boundary is unavailable.");
            return;
        }
        await next();
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    private string SubjectClaim =>
        User.FindFirstValue(ClaimTypes.NameIdentifier)
        ?? User.FindFirstValue("sub")
        ?? throw new UnauthorizedAccessException("No subject claim in token.");

    private string ProviderIssuer =>
        User.FindFirstValue("iss") ?? "keycloak-local";

    private string ActorSubject => $"{ProviderIssuer}\u001f{SubjectClaim}";

    private static readonly Regex LanguagePattern = new(
        "^[a-z]{2}(-[A-Z]{2})?$", RegexOptions.CultureInvariant);
    private static readonly Regex MobilePattern = new(
        "^\\+[1-9][0-9]{7,14}$", RegexOptions.CultureInvariant);
    private static readonly Regex VerificationCodePattern = new(
        "^[0-9]{6}$", RegexOptions.CultureInvariant);
    private static readonly Regex LocalePattern = new(
        "^[a-z]{2}(-[A-Z]{2})?$", RegexOptions.CultureInvariant);

    private const string CustomerPortalSchemaVersion = "1.0.0";

    private Guid? TenantIdFromContext =>
        HttpContext.Items.TryGetValue(TenantIsolationMiddleware.TenantIdItemKey, out var v)
            && v is string s && Guid.TryParse(s, out var g) ? g : null;

    private static string ComputeHash(object? body)
    {
        var json = body is null ? "{}" : JsonSerializer.Serialize(body);
        var bytes = System.Security.Cryptography.SHA256.HashData(
            System.Text.Encoding.UTF8.GetBytes(json));
        return Convert.ToHexString(bytes).ToLowerInvariant()[..16];
    }

    private static bool IsValidEmail(string value)
    {
        try
        {
            return new MailAddress(value).Address == value;
        }
        catch (FormatException)
        {
            return false;
        }
    }

    private static IdentityAuthenticationPath DeriveAuthPath(ClaimsPrincipal user)
    {
        var provider = user.FindFirstValue("identity_provider");
        return provider?.ToLowerInvariant() switch
        {
            "google"   => IdentityAuthenticationPath.Google,
            "facebook" => IdentityAuthenticationPath.Meta,
            "apple"    => IdentityAuthenticationPath.Apple,
            _          => IdentityAuthenticationPath.Credential,
        };
    }

    private DateTimeOffset AuthTime =>
        User.FindFirstValue("auth_time") is string s && long.TryParse(s, out var ts)
            ? DateTimeOffset.FromUnixTimeSeconds(ts)
            : DateTimeOffset.UtcNow;

    private IReadOnlyList<string> CustomerRoles
    {
        get
        {
            var roles = User.FindAll("waooaw_roles")
                .SelectMany(claim => claim.Value.TrimStart().StartsWith('[')
                    ? JsonSerializer.Deserialize<string[]>(claim.Value) ?? []
                    : claim.Value.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
                .Where(role => role is "OWNER" or "MANAGER" or "VIEWER")
                .Distinct(StringComparer.Ordinal)
                .OrderBy(role => role, StringComparer.Ordinal)
                .ToArray();
            return roles;
        }
    }

    private bool IsOwner => CustomerRoles.Contains("OWNER", StringComparer.Ordinal);

    private Guid IdempotencyKey
    {
        get
        {
            var header = Request.Headers["Idempotency-Key"].FirstOrDefault();
            if (string.IsNullOrEmpty(header) || !Guid.TryParse(header, out var key))
                throw new ArgumentException("Invalid or missing Idempotency-Key header.");
            return key;
        }
    }

    private static readonly Dictionary<string, string> ScreamingOverrides = new()
    {
        { "WhatsApp", "WHATSAPP" },
        { "WhatsAppIdentityAccepted", "WHATSAPP_IDENTITY_ACCEPTED" },
        { "PendingWhatsAppConfirmation", "PENDING_WHATSAPP_CONFIRMATION" },
    };

    private static string ToScreamingSnakeCase(string name)
    {
        if (ScreamingOverrides.TryGetValue(name, out var overridden)) return overridden;
        var sb = new System.Text.StringBuilder();
        for (var i = 0; i < name.Length; i++)
        {
            if (i > 0 && char.IsUpper(name[i])) sb.Append('_');
            sb.Append(char.ToUpperInvariant(name[i]));
        }
        return sb.ToString();
    }

    private static IdentityRegistrationResponse ToResponse(IdentityRegistrationRecord reg) =>
        new(
            reg.RegistrationId,
            ToScreamingSnakeCase(reg.State.ToString()),
            ComputeNextAction(reg),
            ToScreamingSnakeCase(reg.AuthenticationPath.ToString()),
            reg.ProviderLabel,
            reg.EmailVerified,
            reg.MobileVerified,
            reg.MaskedEmail,
            reg.MaskedMobile,
            new IdentityRegistrationProfileResponse(
                reg.DisplayName, reg.BusinessName, reg.BusinessDomain, reg.LanguagePreference),
            reg.ExpiresAt,
            reg.UpdatedAt);

    private static string ComputeNextAction(IdentityRegistrationRecord reg) =>
        reg.State switch
        {
            IdentityRegistrationState.FederatedIdentityAccepted               => "COMPLETE_PROFILE",
            IdentityRegistrationState.Started or
            IdentityRegistrationState.CredentialIdentityAccepted or
            IdentityRegistrationState.EmailVerificationRequired                => "VERIFY_EMAIL",
            IdentityRegistrationState.ProfileCompletionRequired                => "COMPLETE_PROFILE",
            IdentityRegistrationState.ReadyToComplete                          => "COMPLETE_REGISTRATION",
            IdentityRegistrationState.DuplicateResolutionRequired              => "RESOLVE_DUPLICATE",
            IdentityRegistrationState.Completed                                => "CONTINUE_TO_DEFAULT_TARGET",
            _                                                                   => "NONE",
        };

    private static IdentityVerificationChallengeResponse ToResponse(IdentityVerificationChallengeRecord c) =>
        new(c.ChallengeId, c.Purpose.ToString().ToUpperInvariant(),
            c.State.ToString().ToUpperInvariant(), c.MaskedDestination, c.ExpiresAt, c.ResendAfter);

    private static IdentityAccountLinkResponse ToResponse(IdentityAccountLinkRecord l) =>
        new(l.LinkId, ToScreamingSnakeCase(l.State.ToString()), "AAL3_FRESH", l.MaskedMobile, l.ExpiresAt, l.UpdatedAt);

    private string? EmailClaim => User.FindFirstValue("email");

    private IActionResult? ValidatePortalSession(out Guid tenantId)
    {
        var candidate = TenantIdFromContext;
        if (candidate is null || CustomerRoles.Count == 0)
        {
            tenantId = default;
            return IdentityProblem(401, "IDENTITY_SESSION_REQUIRED", "A complete customer session is required.");
        }
        tenantId = candidate.Value;
        return null;
    }

    private CustomerProfileResponse ToProfileResponse(CustomerPortalProfileState state) =>
        new(CustomerPortalSchemaVersion, state.DisplayName, state.OrganizationDisplayName,
            EmailClaim ?? string.Empty, state.EmailVerified, state.MobileVerified,
            ActiveCustomerRole, [], state.UpdatedAt);

    private string ActiveCustomerRole =>
        CustomerRoles.Contains("OWNER", StringComparer.Ordinal) ? "OWNER"
        : CustomerRoles.Contains("MANAGER", StringComparer.Ordinal) ? "MANAGER"
        : "VIEWER";

    private static CustomerSettingsResponse ToSettingsResponse(CustomerPortalSettingsState state) =>
        new(CustomerPortalSchemaVersion, state.Locale, state.Theme, state.TimestampVisibility,
            new NotificationPreferencesResponse(state.ApprovalRequests, state.MaturityReports,
                state.MonthlyNarratives, state.SelfGovernanceAlerts),
            ["STEP_UP", "CHANGE_PASSWORDLESS_METHODS", "LINK_WHATSAPP", "REMOVE_LOGIN_METHOD"],
            state.UpdatedAt);

    [HttpGet("session")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> GetSessionAsync(CancellationToken ct)
    {
        if (customerJourney is not null)
        {
            var membership = HttpContext.Items[CustomerMembershipMiddleware.MembershipItem] as CustomerWorkspaceMembership
                ?? await customerJourney.ResolveAsync(User, ct);
            return Ok(new IdentitySessionResponse(membership.AccountId, membership.Roles, [], "AAL2_ACCOUNT", "PORTAL",
                true, false, DateTimeOffset.FromUnixTimeSeconds(long.Parse(GoogleWorkspaceProofAdapter.SingleClaim(User, "auth_time")!)),
                DateTimeOffset.FromUnixTimeSeconds(long.Parse(GoogleWorkspaceProofAdapter.SingleClaim(User, "exp")!)), "CONTINUE_TO_DEFAULT_TARGET"));
        }
        var tenantId = TenantIdFromContext;
        var roles = CustomerRoles;
        var expiresAtValue = User.FindFirstValue("exp");
        if (tenantId is null || roles.Count == 0
            || expiresAtValue is null || !long.TryParse(expiresAtValue, out var expiresAtSeconds))
        {
            return IdentityProblem(401, "IDENTITY_SESSION_REQUIRED", "A complete customer session is required.");
        }

        try
        {
            var state = await identityService.GetSessionStateAsync(ActorSubject, ct);
            var capabilities = CapabilitiesFor(roles);
            var authenticationPath = User.FindFirstValue("auth_path") == "MOBILE" ? "MOBILE" : "PORTAL";
            var assurance = state.EmailVerified ? "AAL2_ACCOUNT" : "AAL1_CHANNEL";
            if (state.MobileVerified && DateTimeOffset.UtcNow - AuthTime <= TimeSpan.FromMinutes(5))
                assurance = "AAL3_FRESH";

            var nextAction = !state.EmailVerified
                ? "VERIFY_EMAIL"
                : !state.MobileVerified ? "VERIFY_MOBILE" : "NONE";

            return Ok(new IdentitySessionResponse(
                state.AccountReference,
                roles,
                capabilities,
                assurance,
                authenticationPath,
                state.EmailVerified,
                state.MobileVerified,
                AuthTime,
                DateTimeOffset.FromUnixTimeSeconds(expiresAtSeconds),
                nextAction));
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(404, "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Account session not found or not accessible.");
        }
    }

    [HttpGet("profile")]
    public async Task<IActionResult> GetCustomerProfileAsync(CancellationToken ct)
    {
        if (ValidatePortalSession(out var tenantId) is { } error) return error;
        try
        {
            var profile = await identityService.GetCustomerProfileAsync(ActorSubject, tenantId, ct);
            return Ok(ToProfileResponse(profile));
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(404, "IDENTITY_RESOURCE_NOT_ACCESSIBLE", "Account profile not found or not accessible.");
        }
    }

    [HttpPut("profile")]
    public async Task<IActionResult> UpdateCustomerProfileAsync(
        [FromBody] UpdateCustomerProfileRequest req, CancellationToken ct)
    {
        if (ValidatePortalSession(out var tenantId) is { } error) return error;
        if (!IsOwner) return IdentityProblem(403, "IDENTITY_ACTION_DENIED", "Owner authorization is required.");
        if (req.SchemaVersion != CustomerPortalSchemaVersion
            || string.IsNullOrWhiteSpace(req.DisplayName) || req.DisplayName.Length > 200
            || string.IsNullOrWhiteSpace(req.OrganizationDisplayName) || req.OrganizationDisplayName.Length > 200)
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Profile fields are invalid.");
        try
        {
            var profile = await identityService.UpdateCustomerProfileAsync(
                ActorSubject, tenantId, IdempotencyKey, ComputeHash(req),
                req.DisplayName.Trim(), req.OrganizationDisplayName.Trim(), ct);
            return Ok(ToProfileResponse(profile));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(409, "IDENTITY_IDEMPOTENCY_CONFLICT", "The idempotency key was already used with a different request.");
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(404, "IDENTITY_RESOURCE_NOT_ACCESSIBLE", "Account profile not found or not accessible.");
        }
        catch (ArgumentException)
        {
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Invalid or missing Idempotency-Key header.");
        }
    }

    [HttpGet("settings")]
    public async Task<IActionResult> GetCustomerSettingsAsync(CancellationToken ct)
    {
        if (ValidatePortalSession(out var tenantId) is { } error) return error;
        try
        {
            return Ok(ToSettingsResponse(await identityService.GetCustomerSettingsAsync(ActorSubject, tenantId, ct)));
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(404, "IDENTITY_RESOURCE_NOT_ACCESSIBLE", "Account settings not found or not accessible.");
        }
    }

    [HttpPut("settings")]
    public async Task<IActionResult> UpdateCustomerSettingsAsync(
        [FromBody] UpdateCustomerSettingsRequest req, CancellationToken ct)
    {
        if (ValidatePortalSession(out var tenantId) is { } error) return error;
        if (req.SchemaVersion != CustomerPortalSchemaVersion || !LocalePattern.IsMatch(req.Locale)
            || req.Theme is not ("SYSTEM" or "LIGHT" or "DARK")
            || req.TimestampVisibility is not ("RELATIVE" or "ABSOLUTE")
            || !ValidChannels(req.NotificationPreferences))
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Settings fields are invalid.");
        try
        {
            var preferences = req.NotificationPreferences;
            var settings = await identityService.UpdateCustomerSettingsAsync(
                ActorSubject, tenantId, IdempotencyKey, ComputeHash(req), req.Locale, req.Theme,
                req.TimestampVisibility, preferences.ApprovalRequests, preferences.MaturityReports,
                preferences.MonthlyNarratives, preferences.SelfGovernanceAlerts, ct);
            return Ok(ToSettingsResponse(settings));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(409, "IDENTITY_IDEMPOTENCY_CONFLICT", "The idempotency key was already used with a different request.");
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(404, "IDENTITY_RESOURCE_NOT_ACCESSIBLE", "Account settings not found or not accessible.");
        }
        catch (ArgumentException)
        {
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Invalid or missing Idempotency-Key header.");
        }
    }

    [HttpGet("login-methods")]
    public IActionResult ListCustomerLoginMethods()
    {
        if (ValidatePortalSession(out _) is { } error) return error;
        var activeProvider = User.FindFirstValue("identity_provider")?.ToUpperInvariant() switch
        {
            "META" => "FACEBOOK",
            "GOOGLE" => "GOOGLE",
            "APPLE" => "APPLE",
            _ => "EMAIL",
        };
        var maskedEmail = EmailClaim is { Length: > 0 } email ? IdentityService.MaskEmail(email) : null;
        var methods = providerProjectionService.GetProviders().Select(provider =>
            new CustomerLoginMethodResponse(
                provider.Id,
                provider.Id == activeProvider ? "ACTIVE" : provider.Availability == "AVAILABLE" ? "AVAILABLE_TO_LINK" : "BLOCKED",
                provider.Id == activeProvider ? maskedEmail : null)).ToArray();
        return Ok(new CustomerLoginMethodCollectionResponse(CustomerPortalSchemaVersion, methods));
    }

    private static bool ValidChannels(NotificationPreferencesRequest preferences)
    {
        var allowed = new HashSet<string>(["IN_APP", "EMAIL", "WHATSAPP"], StringComparer.Ordinal);
        return preferences is not null
            && new[] { preferences.ApprovalRequests, preferences.MaturityReports,
                preferences.MonthlyNarratives, preferences.SelfGovernanceAlerts }
                .All(channels => channels is not null && channels.All(allowed.Contains));
    }

    private static IReadOnlyList<string> CapabilitiesFor(IReadOnlyList<string> roles)
    {
        var capabilities = new HashSet<string>(StringComparer.Ordinal) { "READ_ACCOUNT" };
        if (roles.Contains("MANAGER", StringComparer.Ordinal) || roles.Contains("OWNER", StringComparer.Ordinal))
            capabilities.Add("MANAGE_ROUTINE_ACTIONS");
        if (roles.Contains("OWNER", StringComparer.Ordinal))
        {
            capabilities.UnionWith([
                "MANAGE_ACCOUNT", "LINK_WHATSAPP", "ACCEPT_CONTRACT",
                "HIRE_PROFESSIONAL", "MANAGE_AUTHORITY"]);
        }
        return capabilities.OrderBy(value => value, StringComparer.Ordinal).ToArray();
    }

    private IActionResult IdentityProblem(int status, string code, string detail, Guid? stepUpIntentId = null)
    {
        var correlationId = Guid.NewGuid();
        logger.LogWarning(
            "IdentityProblem status={Status} code={Code} correlationId={Id} path={Path}",
            status, code, correlationId, Request.Path);

        var body = new
        {
            type          = $"https://waooaw.com/errors/identity/{code.ToLowerInvariant().Replace('_', '-')}",
            title         = code,
            status,
            detail,
            code,
            correlationId,
            stepUpIntentId,
        };
        return StatusCode(status, body);
    }

    // ── POST /api/v1/identity/registrations ──────────────────────────────────

    [HttpPost("registrations")]
    [CustomerIdentityRoute]
    public async Task<IActionResult> StartRegistrationAsync(
        [FromBody] StartRegistrationRequest req,
        CancellationToken ct)
    {
        try
        {
            if (!LanguagePattern.IsMatch(req.LanguagePreference))
                return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "languagePreference is invalid.");

            if (customerJourney is not null)
            {
                var started = await customerJourney.StartAsync(User, IdempotencyKey, req.LanguagePreference, ct);
                return started.isNew ? StatusCode(201, ToResponse(started.reg)) : Ok(ToResponse(started.reg));
            }
            var authPath = DeriveAuthPath(User);
            var providerId = authPath switch
            {
                IdentityAuthenticationPath.Google => "GOOGLE",
                IdentityAuthenticationPath.Meta => "FACEBOOK",
                IdentityAuthenticationPath.Apple => "APPLE",
                _ => "EMAIL",
            };
            if (!providerProjectionService.IsAvailable(providerId))
                return IdentityProblem(403, "IDENTITY_ACTION_DENIED", "Authentication path is unavailable.");
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);

            var emailClaim = User.FindFirstValue("email");
            var emailVerified = User.FindFirstValue("email_verified") == "true";
            var maskedEmail = emailVerified && emailClaim is not null
                ? IdentityService.MaskEmail(emailClaim) : null;

            var (reg, isNew) = await identityService.StartRegistrationAsync(
                ActorSubject, idempotencyKey, hash,
                req.LanguagePreference, authPath,
                providerLabel: User.FindFirstValue("identity_provider"),
                providerIssuer: ProviderIssuer,
                emailVerifiedByClaim: emailVerified,
                maskedEmail: maskedEmail,
                emailHmacKey: null,
                ct: ct);

            return isNew ? StatusCode(201, ToResponse(reg)) : Ok(ToResponse(reg));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(409, "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request.");
        }
        catch (IdentityActionDeniedException ex)
        {
            return IdentityProblem(403, "IDENTITY_ACTION_DENIED", ex.Message);
        }
        catch (ArgumentException)
        {
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Invalid or missing Idempotency-Key header.");
        }
    }

    // ── GET /api/v1/identity/registrations/{registrationId} ──────────────────

    [HttpGet("registrations/{registrationId:guid}")]
    [CustomerIdentityRoute]
    public async Task<IActionResult> GetRegistrationAsync(Guid registrationId, CancellationToken ct)
    {
        try
        {
            var reg = customerJourney is not null
                ? await customerJourney.GetAsync(User, registrationId, ct)
                : await identityService.GetRegistrationAsync(registrationId, ActorSubject, ct);
            return Ok(ToResponse(reg));
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(404, "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Registration not found or not accessible.");
        }
    }

    // ── PUT /api/v1/identity/registrations/{registrationId}/profile ───────────

    [HttpPut("registrations/{registrationId:guid}/profile")]
    [CustomerIdentityRoute]
    public async Task<IActionResult> UpdateProfileAsync(
        Guid registrationId,
        [FromBody] UpdateRegistrationProfileRequest req,
        CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(req.DisplayName) || req.DisplayName.Length > 120
            || string.IsNullOrWhiteSpace(req.BusinessName) || req.BusinessName.Length > 160
            || string.IsNullOrWhiteSpace(req.BusinessDomain) || req.BusinessDomain.Length > 100
            || string.IsNullOrWhiteSpace(req.LanguagePreference)
            || !LanguagePattern.IsMatch(req.LanguagePreference))
        {
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Registration profile is invalid.");
        }

        try
        {
            if (customerJourney is not null)
            {
                var updated = await customerJourney.UpdateAsync(User, registrationId, IdempotencyKey,
                    req.DisplayName, req.BusinessName, req.BusinessDomain, req.LanguagePreference, ct);
                return Ok(ToResponse(updated.reg));
            }
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);

            var (reg, _) = await identityService.UpdateProfileAsync(
                registrationId, ActorSubject, idempotencyKey, hash,
                req.DisplayName, req.BusinessName, req.BusinessDomain, req.LanguagePreference, ct);

            return Ok(ToResponse(reg));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(409, "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request.");
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(404, "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Registration not found or not accessible.");
        }
        catch (ArgumentException)
        {
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Invalid or missing Idempotency-Key header.");
        }
    }

    // ── POST /api/v1/identity/registrations/{registrationId}/email-verifications

    [HttpPost("registrations/{registrationId:guid}/email-verifications")]
    public async Task<IActionResult> StartEmailVerificationAsync(
        Guid registrationId,
        [FromBody] StartEmailVerificationRequest req,
        CancellationToken ct)
    {
        if (!IsValidEmail(req.Email))
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "email is invalid.");

        try
        {
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);

            var (challenge, _) = await identityService.StartEmailVerificationAsync(
                registrationId, ActorSubject, idempotencyKey, hash, req.Email, ct);

            return StatusCode(202, ToResponse(challenge));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(409, "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request.");
        }
        catch (IdentityDeliveryUnavailableException)
        {
            return IdentityProblem(503, "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "Verification delivery is temporarily unavailable.");
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(404, "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Registration not found or not accessible.");
        }
        catch (ArgumentException)
        {
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Invalid or missing Idempotency-Key header.");
        }
    }

    // ── POST /registrations/{id}/email-verifications/confirm ─────────────────

    [HttpPost("registrations/{registrationId:guid}/email-verifications/confirm")]
    public async Task<IActionResult> ConfirmEmailVerificationAsync(
        Guid registrationId,
        [FromBody] ConfirmVerificationRequest req,
        CancellationToken ct)
    {
        if (!VerificationCodePattern.IsMatch(req.Code))
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "verification code is invalid.");

        try
        {
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);

            var (reg, _) = await identityService.ConfirmEmailVerificationAsync(
                registrationId, ActorSubject, idempotencyKey, hash,
                req.ChallengeId, req.Code, ct);

            return Ok(ToResponse(reg));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(409, "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request.");
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(404, "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Resource not found or not accessible.");
        }
        catch (IdentityChallengeExpiredException)
        {
            return IdentityProblem(410, "IDENTITY_CHALLENGE_EXPIRED", "Challenge is no longer usable.");
        }
        catch (IdentityActionDeniedException)
        {
            return IdentityProblem(403, "IDENTITY_ACTION_DENIED", "Verification could not be completed.");
        }
        catch (ArgumentException)
        {
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Invalid or missing Idempotency-Key header.");
        }
    }

    // ── POST /registrations/{id}/mobile-verifications ─────────────────────────

    [HttpPost("registrations/{registrationId:guid}/mobile-verifications")]
    public async Task<IActionResult> StartRegistrationMobileVerificationAsync(
        Guid registrationId,
        [FromBody] StartMobileVerificationRequest req,
        CancellationToken ct)
    {
        if (!MobilePattern.IsMatch(req.Mobile))
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "mobile is invalid.");

        try
        {
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);

            var (challenge, _) = await identityService.StartMobileVerificationAsync(
                registrationId, ActorSubject, idempotencyKey, hash, req.Mobile, ct);

            return StatusCode(202, ToResponse(challenge));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(409, "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request.");
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(404, "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Registration not found or not accessible.");
        }
        catch (IdentityDeliveryUnavailableException)
        {
            return IdentityProblem(503, "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "Verification delivery is temporarily unavailable.");
        }
        catch (ArgumentException)
        {
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Invalid or missing Idempotency-Key header.");
        }
    }

    // ── POST /registrations/{id}/mobile-verifications/confirm ─────────────────

    [HttpPost("registrations/{registrationId:guid}/mobile-verifications/confirm")]
    public async Task<IActionResult> ConfirmRegistrationMobileVerificationAsync(
        Guid registrationId,
        [FromBody] ConfirmVerificationRequest req,
        CancellationToken ct)
    {
        if (!VerificationCodePattern.IsMatch(req.Code))
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "verification code is invalid.");

        try
        {
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);

            var (result, _) = await identityService.ConfirmMobileVerificationAsync(
                registrationId, ActorSubject, idempotencyKey, hash,
                req.ChallengeId, req.Code, ct);

            if (result is IdentityRegistrationRecord reg)
                return Ok(ToResponse(reg));

            return Ok(result);
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(409, "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request.");
        }
        catch (IdentityChallengeExpiredException)
        {
            return IdentityProblem(410, "IDENTITY_CHALLENGE_EXPIRED", "Challenge is no longer usable.");
        }
        catch (IdentityActionDeniedException)
        {
            return IdentityProblem(403, "IDENTITY_ACTION_DENIED", "Verification could not be completed.");
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(404, "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Resource not found or not accessible.");
        }
        catch (ArgumentException)
        {
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Invalid or missing Idempotency-Key header.");
        }
    }

    // ── POST /registrations/{id}/complete ─────────────────────────────────────

    [HttpPost("registrations/{registrationId:guid}/complete")]
    [CustomerIdentityRoute]
    public async Task<IActionResult> CompleteRegistrationAsync(
        Guid registrationId,
        CancellationToken ct)
    {
        try
        {
            if (customerJourney is not null)
            {
                var completed = await customerJourney.CompleteAsync(User, registrationId, IdempotencyKey, ct);
                return new ContentResult { StatusCode = completed.StatusCode, ContentType = "application/json",
                    Content = completed.ResponseBody };
            }
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(new { registrationId });

            var (result, _) = await identityService.CompleteRegistrationAsync(
                registrationId, ActorSubject, idempotencyKey, hash, ct);

            return Ok(new IdentityCompletionResponse(
                result.Outcome, result.AccountReference,
                result.AssuranceLevel, result.DefaultTarget));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(409, "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request.");
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(404, "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Registration not found or not accessible.");
        }
        catch (IdentityVerificationRequiredException ex)
        {
            return IdentityProblem(422, "IDENTITY_VERIFICATION_REQUIRED", ex.Message);
        }
        catch (ArgumentException)
        {
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Invalid or missing Idempotency-Key header.");
        }
    }

    // ── POST /api/v1/identity/mobile-verifications (progressive) ─────────────

    [HttpPost("mobile-verifications")]
    public async Task<IActionResult> StartAccountMobileVerificationAsync(
        [FromBody] StartMobileVerificationRequest req,
        CancellationToken ct)
    {
        if (!MobilePattern.IsMatch(req.Mobile))
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "mobile is invalid.");

        try
        {
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);

            var (challenge, _) = await identityService.StartMobileVerificationAsync(
                null, ActorSubject, idempotencyKey, hash, req.Mobile, ct);

            return StatusCode(202, ToResponse(challenge));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(409, "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request.");
        }
        catch (IdentityDeliveryUnavailableException)
        {
            return IdentityProblem(503, "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "Verification delivery is temporarily unavailable.");
        }
        catch (ArgumentException)
        {
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Invalid or missing Idempotency-Key header.");
        }
    }

    // ── POST /api/v1/identity/mobile-verifications/confirm (progressive) ──────

    [HttpPost("mobile-verifications/confirm")]
    public async Task<IActionResult> ConfirmAccountMobileVerificationAsync(
        [FromBody] ConfirmVerificationRequest req,
        CancellationToken ct)
    {
        if (!VerificationCodePattern.IsMatch(req.Code))
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "verification code is invalid.");

        try
        {
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);

            var (result, _) = await identityService.ConfirmMobileVerificationAsync(
                null, ActorSubject, idempotencyKey, hash,
                req.ChallengeId, req.Code, ct);

            var status = (IdentityMobileStatusResult)result;
            return Ok(new IdentityMobileStatusResponse(
                status.MobileVerified, status.MaskedMobile, status.VerifiedAt));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(409, "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request.");
        }
        catch (IdentityChallengeExpiredException)
        {
            return IdentityProblem(410, "IDENTITY_CHALLENGE_EXPIRED", "Challenge is no longer usable.");
        }
        catch (IdentityActionDeniedException)
        {
            return IdentityProblem(403, "IDENTITY_ACTION_DENIED", "Verification could not be completed.");
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(404, "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Resource not found or not accessible.");
        }
        catch (ArgumentException)
        {
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Invalid or missing Idempotency-Key header.");
        }
    }

    // ── POST /api/v1/identity/account-links ───────────────────────────────────

    [HttpPost("account-links")]
    public async Task<IActionResult> StartAccountLinkAsync(
        [FromBody] StartAccountLinkRequest req,
        CancellationToken ct)
    {
        var tenantId = TenantIdFromContext;
        if (tenantId is null)
            return IdentityProblem(401, "IDENTITY_SESSION_REQUIRED", "Authenticated account session required.");
        if (!IsOwner)
            return IdentityProblem(403, "IDENTITY_ACTION_DENIED", "Owner authorization is required.");

        try
        {
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);

            var (link, isNew) = await identityService.StartAccountLinkAsync(
                ActorSubject, tenantId.Value, idempotencyKey, hash,
                req.VerifiedMobileProofId, AuthTime, ct);

            return isNew ? StatusCode(201, ToResponse(link)) : Ok(ToResponse(link));
        }
        catch (IdentityStepUpRequiredException ex)
        {
            return IdentityProblem(403, "IDENTITY_STEP_UP_REQUIRED",
                "A freshly authenticated session is required.", ex.IntentId);
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(409, "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request.");
        }
        catch (ArgumentException)
        {
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Invalid or missing Idempotency-Key header.");
        }
    }

    // ── POST /api/v1/identity/account-links/{linkId}/approve ─────────────────

    [HttpPost("account-links/{linkId:guid}/approve")]
    public async Task<IActionResult> ApproveAccountLinkAsync(Guid linkId, CancellationToken ct)
    {
        var tenantId = TenantIdFromContext;
        if (tenantId is null)
            return IdentityProblem(401, "IDENTITY_SESSION_REQUIRED", "Authenticated account session required.");
        if (!IsOwner)
            return IdentityProblem(403, "IDENTITY_ACTION_DENIED", "Owner authorization is required.");

        try
        {
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(new { linkId });

            var (link, _) = await identityService.ApproveAccountLinkAsync(
                linkId, ActorSubject, tenantId.Value, idempotencyKey, hash, AuthTime, ct);

            return Ok(ToResponse(link));
        }
        catch (IdentityStepUpRequiredException ex)
        {
            return IdentityProblem(403, "IDENTITY_STEP_UP_REQUIRED",
                "A freshly authenticated session is required.", ex.IntentId);
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(409, "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request.");
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(404, "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Link not found or not accessible.");
        }
        catch (IdentityChallengeExpiredException)
        {
            return IdentityProblem(410, "IDENTITY_CHALLENGE_EXPIRED", "Link challenge has expired.");
        }
        catch (ArgumentException)
        {
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Invalid or missing Idempotency-Key header.");
        }
    }

    // ── GET /api/v1/identity/account-links/{linkId} ───────────────────────────

    [HttpGet("account-links/{linkId:guid}")]
    public async Task<IActionResult> GetAccountLinkAsync(Guid linkId, CancellationToken ct)
    {
        var tenantId = TenantIdFromContext;
        if (tenantId is null)
            return IdentityProblem(401, "IDENTITY_SESSION_REQUIRED", "Authenticated account session required.");
        if (!IsOwner)
            return IdentityProblem(403, "IDENTITY_ACTION_DENIED", "Owner authorization is required.");

        try
        {
            var link = await identityService.GetAccountLinkAsync(
                linkId, ActorSubject, tenantId.Value, ct);
            return Ok(ToResponse(link));
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(404, "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Link not found or not accessible.");
        }
    }
}
