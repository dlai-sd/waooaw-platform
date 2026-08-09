// Implements: architecture/reference/components/identity-boundary.md §7 Canonical Public API
// constitutional_basis: C-023, C-026, C-059

using System.Security.Claims;
using System.Net.Mail;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
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

[ApiController]
[Route("api/v1/identity")]
[Authorize]
public sealed class IdentityController(
    IdentityService identityService,
    ILogger<IdentityController> logger) : ControllerBase
{
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
    public async Task<IActionResult> StartRegistrationAsync(
        [FromBody] StartRegistrationRequest req,
        CancellationToken ct)
    {
        try
        {
            if (!LanguagePattern.IsMatch(req.LanguagePreference))
                return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "languagePreference is invalid.");

            var authPath = DeriveAuthPath(User);
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
    public async Task<IActionResult> GetRegistrationAsync(Guid registrationId, CancellationToken ct)
    {
        try
        {
            var reg = await identityService.GetRegistrationAsync(registrationId, ActorSubject, ct);
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
    public async Task<IActionResult> CompleteRegistrationAsync(
        Guid registrationId,
        CancellationToken ct)
    {
        try
        {
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
