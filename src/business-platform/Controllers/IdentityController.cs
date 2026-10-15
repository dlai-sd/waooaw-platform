// Implements: architecture/reference/components/identity-boundary.md §7 Canonical Public API
// constitutional_basis: C-023, C-026, C-059

using System.Net.Mail;
using System.Security.Claims;
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
    string LanguagePreference
);

public sealed record StartEmailVerificationRequest(string Email);

public sealed record StartMobileVerificationRequest(string Mobile);

public sealed record ConfirmVerificationRequest(Guid ChallengeId, string Code);

public sealed record StartAccountLinkRequest(Guid VerifiedMobileProofId);

public sealed record UpdateCustomerProfileRequest(
    string SchemaVersion,
    string DisplayName,
    string OrganizationDisplayName
);

public sealed record NotificationPreferencesRequest(
    IReadOnlyList<string> ApprovalRequests,
    IReadOnlyList<string> MaturityReports,
    IReadOnlyList<string> MonthlyNarratives,
    IReadOnlyList<string> SelfGovernanceAlerts
);

public sealed record UpdateCustomerSettingsRequest(
    string SchemaVersion,
    string Locale,
    string Theme,
    string TimestampVisibility,
    NotificationPreferencesRequest NotificationPreferences
);

public sealed record ReplaceWorkspaceLayoutPreferencesRequest(
    int ExpectedVersion,
    string NavigationVisibility,
    string ProgressVisibility,
    int ConversationWidthPercent,
    bool ReduceMotion = false
);

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
    DateTimeOffset UpdatedAt
);

public sealed record IdentityRegistrationProfileResponse(
    string? DisplayName,
    string? BusinessName,
    string? BusinessDomain,
    string? LanguagePreference
);

public sealed record IdentityVerificationChallengeResponse(
    Guid ChallengeId,
    string Purpose,
    string State,
    string MaskedDestination,
    DateTimeOffset ExpiresAt,
    DateTimeOffset ResendAfter
);

public sealed record IdentityCompletionResponse(
    string Outcome,
    Guid AccountReference,
    string AssuranceLevel,
    string DefaultTarget
);

public sealed record IdentityAccountLinkResponse(
    Guid LinkId,
    string State,
    string RequiredAssurance,
    string MaskedMobile,
    DateTimeOffset ExpiresAt,
    DateTimeOffset UpdatedAt
);

public sealed record IdentityMobileStatusResponse(
    bool MobileVerified,
    string MaskedMobile,
    DateTimeOffset VerifiedAt
);

public sealed record IdentityProviderCollectionResponse(
    IReadOnlyList<IdentityProviderProjection> Providers
);

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
    string NextAction
);

public sealed record IdentityMembershipResponse(
    Guid MembershipReference,
    Guid TenantReference,
    string Role,
    string State,
    bool SelectionEligible
);

public sealed record IdentityMembershipCollectionResponse(
    string SchemaVersion,
    IReadOnlyList<IdentityMembershipResponse> Memberships,
    string Cardinality
);

public sealed record IdentityMembershipSelectionRequest(
    string SchemaVersion,
    Guid MembershipReference
);

public sealed record IdentityMembershipSelectionResponse(
    string SchemaVersion,
    IdentityMembershipResponse Membership,
    DateTimeOffset ValidatedAt
);

public sealed record IdentityProviderLinkRequest(
    string SchemaVersion,
    string Provider,
    Guid StepUpTransactionReference
);

public sealed record IdentityProviderLinkOperationResponse(
    string SchemaVersion,
    Guid OperationReference,
    Guid? LinkReference,
    string Command,
    string Provider,
    string State,
    DateTimeOffset ExpiresAt,
    bool Replayed
);

public sealed record IdentitySessionRevocationIntentRequest(
    string SchemaVersion,
    string Scope,
    Guid? SessionFamilyReference,
    string Reason,
    Guid CorrelationId
);

public sealed record IdentitySessionRevocationReceiptResponse(
    string SchemaVersion,
    Guid RevocationReference,
    string Scope,
    string State,
    DateTimeOffset RecordedAt,
    bool Replayed
);

public sealed record CustomerProfileResponse(
    string SchemaVersion,
    string DisplayName,
    string OrganizationDisplayName,
    string Email,
    bool EmailVerified,
    bool MobileVerified,
    string ActiveRole,
    IReadOnlyList<object> SwitchableAccounts,
    DateTimeOffset UpdatedAt
);

public sealed record NotificationPreferencesResponse(
    IReadOnlyList<string> ApprovalRequests,
    IReadOnlyList<string> MaturityReports,
    IReadOnlyList<string> MonthlyNarratives,
    IReadOnlyList<string> SelfGovernanceAlerts
);

public sealed record CustomerSettingsResponse(
    string SchemaVersion,
    string Locale,
    string Theme,
    string TimestampVisibility,
    NotificationPreferencesResponse NotificationPreferences,
    IReadOnlyList<string> AvailableSecurityActions,
    DateTimeOffset UpdatedAt
);

public sealed record WorkspaceLayoutPreferencesResponse(
    string SchemaVersion,
    int PreferenceVersion,
    string NavigationVisibility,
    string ProgressVisibility,
    int ConversationWidthPercent,
    bool ReduceMotion,
    DateTimeOffset UpdatedAt
);

public sealed record CustomerLoginMethodResponse(
    string Provider,
    string State,
    string? MaskedIdentifier
);

public sealed record CustomerLoginMethodCollectionResponse(
    string SchemaVersion,
    IReadOnlyList<CustomerLoginMethodResponse> Items
);

[ApiController]
[Route("api/v1/identity")]
[Authorize]
public sealed class IdentityController(
    IdentityService identityService,
    IdentityProviderProjectionService providerProjectionService,
    ILogger<IdentityController> logger,
    CustomerIdentityJourneyService? customerJourney = null,
    IdentitySecurityEventService? securityEvents = null,
    IdentityLifecycleService? lifecycleService = null
) : ControllerBase, IAsyncActionFilter
{
    [NonAction]
    public async Task OnActionExecutionAsync(
        ActionExecutingContext context,
        ActionExecutionDelegate next
    )
    {
        if (context.ActionDescriptor.EndpointMetadata.OfType<IAllowAnonymous>().Any())
        {
            await next();
            return;
        }
        if (
            customerJourney is null
            || !HttpContext.Items.ContainsKey(CustomerMembershipMiddleware.JourneyItem)
        )
        {
            context.Result = IdentityProblem(
                503,
                "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "The customer identity boundary is unavailable."
            );
            return;
        }
        var executed = await next();
        if (securityEvents is not null)
            await RecordObservedEventAsync(context, executed);
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    private string SubjectClaim =>
        User.FindFirstValue(ClaimTypes.NameIdentifier)
        ?? User.FindFirstValue("sub")
        ?? throw new UnauthorizedAccessException("No subject claim in token.");

    private string ProviderIssuer => User.FindFirstValue("iss") ?? "keycloak-local";

    private string ActorSubject => $"{ProviderIssuer}\u001f{SubjectClaim}";

    private string SourceSessionId =>
        User.FindFirstValue("sid")
        ?? User.FindFirstValue("jti")
        ?? $"{ActorSubject}\u001f{User.FindFirstValue("auth_time")}";

    private DateTimeOffset TokenTime(string claim) =>
        User.FindFirstValue(claim) is string value && long.TryParse(value, out var seconds)
            ? DateTimeOffset.FromUnixTimeSeconds(seconds)
            : throw new IdentityActionDeniedException("IDENTITY_SESSION_REQUIRED");

    private async Task RecordObservedEventAsync(
        ActionExecutingContext context,
        ActionExecutedContext executed
    )
    {
        var actionName = context.ActionDescriptor.RouteValues["action"];
        var status = executed.Result switch
        {
            ObjectResult result => result.StatusCode ?? StatusCodes.Status200OK,
            StatusCodeResult result => result.StatusCode,
            _ when executed.Exception is not null => StatusCodes.Status500InternalServerError,
            _ => StatusCodes.Status200OK,
        };
        var eventType = actionName switch
        {
            nameof(StartRegistrationAsync) when status < 400 => "REGISTRATION_START",
            nameof(StartRegistrationAsync) => "REGISTRATION_FAILURE",
            nameof(CompleteRegistrationAsync) when status < 400 => "REGISTRATION_COMPLETION",
            nameof(CompleteRegistrationAsync) => "REGISTRATION_FAILURE",
            nameof(GetSessionAsync) when status < 400 => "SESSION_ESTABLISHMENT",
            nameof(GetSessionAsync) => "AUTHORIZATION_DENIAL",
            nameof(StartAccountLinkAsync) when status >= 400 => "AUTHORIZATION_DENIAL",
            nameof(ApproveAccountLinkAsync) when status >= 400 => "AUTHORIZATION_DENIAL",
            _ => null,
        };
        if (eventType is null)
            return;

        var trace = HttpContext.TraceIdentifier;
        var sourceDigest = Convert
            .ToHexString(
                System.Security.Cryptography.SHA256.HashData(
                    System.Text.Encoding.UTF8.GetBytes($"{eventType}:{trace}")
                )
            )
            .ToLowerInvariant();
        var correlationBytes = System.Security.Cryptography.SHA256.HashData(
            System.Text.Encoding.UTF8.GetBytes($"correlation:{trace}")
        );
        await securityEvents!.RecordAsync(
            new IdentitySecurityEventInput(
                new Guid(correlationBytes.AsSpan(0, 16)),
                $"http:{sourceDigest}",
                eventType,
                ProviderClass,
                status < 400 ? "SUCCEEDED"
                    : status < 500 ? "DENIED"
                    : "FAILED",
                status < 400 ? "IDENTITY_OPERATION_COMPLETED" : $"HTTP_{status}",
                AssuranceClass,
                "BUSINESS_PLATFORM",
                ActorSubject,
                User.FindFirstValue("sid")
            ),
            HttpContext.RequestAborted
        );
    }

    private string ProviderClass =>
        (
            User.FindFirstValue("identity_provider") ?? User.FindFirstValue("idp")
        )?.ToLowerInvariant() switch
        {
            "google" => "GOOGLE",
            "facebook" => "FACEBOOK",
            "apple" => "APPLE",
            "email" => "EMAIL",
            _ => "UNKNOWN",
        };

    private string AssuranceClass =>
        User.FindFirstValue("auth_time") is null ? "UNKNOWN"
        : DateTimeOffset.UtcNow - AuthTime <= TimeSpan.FromMinutes(5) ? "AAL3"
        : "AAL2";

    private static readonly Regex LanguagePattern = new(
        "^[a-z]{2}(-[A-Z]{2})?$",
        RegexOptions.CultureInvariant
    );
    private static readonly Regex MobilePattern = new(
        "^\\+[1-9][0-9]{7,14}$",
        RegexOptions.CultureInvariant
    );
    private static readonly Regex VerificationCodePattern = new(
        "^[0-9]{6}$",
        RegexOptions.CultureInvariant
    );
    private static readonly Regex LocalePattern = new(
        "^[a-z]{2}(-[A-Z]{2})?$",
        RegexOptions.CultureInvariant
    );

    private const string CustomerPortalSchemaVersion = "1.0.0";

    private CustomerWorkspaceMembership? CurrentMembership =>
        HttpContext.Items[CustomerMembershipMiddleware.MembershipItem]
        as CustomerWorkspaceMembership;

    private Guid? TenantIdFromContext => CurrentMembership?.TenantId;

    private static string ComputeHash(object? body)
    {
        var json = body is null ? "{}" : JsonSerializer.Serialize(body);
        var bytes = System.Security.Cryptography.SHA256.HashData(
            System.Text.Encoding.UTF8.GetBytes(json)
        );
        return Convert.ToHexString(bytes).ToLowerInvariant()[..16];
    }

    private static bool IsValidEmail(string value)
    {
        if (value.Length > 254)
            return false;
        var separator = value.IndexOf('@');
        if (separator <= 0 || separator != value.LastIndexOf('@') || separator == value.Length - 1)
            return false;

        try
        {
            return new MailAddress(value).Address == value;
        }
        catch (Exception exception) when (exception is ArgumentException or FormatException)
        {
            return false;
        }
    }

    private static IdentityAuthenticationPath DeriveAuthPath(ClaimsPrincipal user)
    {
        var provider = user.FindFirstValue("identity_provider");
        return provider?.ToLowerInvariant() switch
        {
            "google" => IdentityAuthenticationPath.Google,
            "facebook" => IdentityAuthenticationPath.Meta,
            "apple" => IdentityAuthenticationPath.Apple,
            _ => IdentityAuthenticationPath.Credential,
        };
    }

    private DateTimeOffset AuthTime =>
        User.FindFirstValue("auth_time") is string s && long.TryParse(s, out var ts)
            ? DateTimeOffset.FromUnixTimeSeconds(ts)
            : DateTimeOffset.UtcNow;

    private IReadOnlyList<string> CustomerRoles => CurrentMembership?.Roles ?? [];

    private bool IsOwner => CustomerRoles.Contains("OWNER", StringComparer.Ordinal);

    private bool HasLifecycleStepUp =>
        User.FindFirstValue("auth_time") is string authTime
        && long.TryParse(authTime, out var authenticatedAt)
        && DateTimeOffset.UtcNow - DateTimeOffset.FromUnixTimeSeconds(authenticatedAt) is var age
        && age >= TimeSpan.FromSeconds(-30)
        && age <= TimeSpan.FromMinutes(5)
        && User.FindFirstValue("acr") is "2" or "3" or "urn:waooaw:aal2" or "urn:waooaw:aal3"
        && User.FindAll("amr")
            .SelectMany(claim => claim.Value.Split(' ', StringSplitOptions.RemoveEmptyEntries))
            .Any(method => method is "mfa" or "otp" or "webauthn");

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
        if (ScreamingOverrides.TryGetValue(name, out var overridden))
            return overridden;
        var sb = new System.Text.StringBuilder();
        for (var i = 0; i < name.Length; i++)
        {
            if (i > 0 && char.IsUpper(name[i]))
                sb.Append('_');
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
                reg.DisplayName,
                reg.BusinessName,
                reg.BusinessDomain,
                reg.LanguagePreference
            ),
            reg.ExpiresAt,
            reg.UpdatedAt
        );

    private static string ComputeNextAction(IdentityRegistrationRecord reg) =>
        reg.State switch
        {
            IdentityRegistrationState.FederatedIdentityAccepted => "COMPLETE_PROFILE",
            IdentityRegistrationState.Started
            or IdentityRegistrationState.CredentialIdentityAccepted
            or IdentityRegistrationState.EmailVerificationRequired => "VERIFY_EMAIL",
            IdentityRegistrationState.ProfileCompletionRequired => "COMPLETE_PROFILE",
            IdentityRegistrationState.ReadyToComplete => "COMPLETE_REGISTRATION",
            IdentityRegistrationState.DuplicateResolutionRequired => "RESOLVE_DUPLICATE",
            IdentityRegistrationState.Completed => "CONTINUE_TO_DEFAULT_TARGET",
            _ => "NONE",
        };

    private static IdentityProviderLinkOperationResponse ToResponse(
        IdentityLifecycleOperation operation
    ) =>
        new(
            "1.0",
            operation.OperationReference,
            operation.LinkReference,
            operation.Command.ToString().ToUpperInvariant(),
            operation.Provider.ToString().ToUpperInvariant(),
            operation.State,
            operation.ExpiresAt,
            operation.Replayed
        );

    private static readonly IReadOnlySet<string> SessionRevocationReasons = new HashSet<string>(
        [
            "LOGOUT",
            "LOGOUT_ALL",
            "SWITCH_ACCOUNT",
            "SECURITY_EVENT",
            "ACCOUNT_RECOVERY",
            "ACCOUNT_ERASURE",
        ],
        StringComparer.Ordinal
    );

    private static IdentityVerificationChallengeResponse ToResponse(
        IdentityVerificationChallengeRecord c
    ) =>
        new(
            c.ChallengeId,
            c.Purpose.ToString().ToUpperInvariant(),
            c.State.ToString().ToUpperInvariant(),
            c.MaskedDestination,
            c.ExpiresAt,
            c.ResendAfter
        );

    private static IdentityAccountLinkResponse ToResponse(IdentityAccountLinkRecord l) =>
        new(
            l.LinkId,
            ToScreamingSnakeCase(l.State.ToString()),
            "AAL3_FRESH",
            l.MaskedMobile,
            l.ExpiresAt,
            l.UpdatedAt
        );

    private string? EmailClaim => User.FindFirstValue("email");

    private IActionResult? ValidatePortalSession(out Guid tenantId)
    {
        var candidate = TenantIdFromContext;
        if (candidate is null || CustomerRoles.Count == 0)
        {
            tenantId = default;
            return IdentityProblem(
                401,
                "IDENTITY_SESSION_REQUIRED",
                "A complete customer session is required."
            );
        }
        tenantId = candidate.Value;
        return null;
    }

    private CustomerProfileResponse ToProfileResponse(CustomerPortalProfileState state) =>
        new(
            CustomerPortalSchemaVersion,
            state.DisplayName,
            state.OrganizationDisplayName,
            EmailClaim ?? string.Empty,
            state.EmailVerified,
            state.MobileVerified,
            ActiveCustomerRole,
            [],
            state.UpdatedAt
        );

    private string ActiveCustomerRole =>
        CustomerRoles.Contains("OWNER", StringComparer.Ordinal) ? "OWNER"
        : CustomerRoles.Contains("MANAGER", StringComparer.Ordinal) ? "MANAGER"
        : "VIEWER";

    private static CustomerSettingsResponse ToSettingsResponse(CustomerPortalSettingsState state) =>
        new(
            CustomerPortalSchemaVersion,
            state.Locale,
            state.Theme,
            state.TimestampVisibility,
            new NotificationPreferencesResponse(
                state.ApprovalRequests,
                state.MaturityReports,
                state.MonthlyNarratives,
                state.SelfGovernanceAlerts
            ),
            ["STEP_UP", "CHANGE_PASSWORDLESS_METHODS", "LINK_WHATSAPP", "REMOVE_LOGIN_METHOD"],
            state.UpdatedAt
        );

    private static WorkspaceLayoutPreferencesResponse ToWorkspaceLayoutResponse(
        WorkspaceLayoutPreferenceState state
    ) =>
        new(
            "1",
            state.PreferenceVersion,
            state.NavigationVisibility,
            state.ProgressVisibility,
            state.ConversationWidthPercent,
            state.ReduceMotion,
            state.UpdatedAt
        );

    [HttpGet("memberships")]
    [CustomerIdentityRoute]
    public async Task<IActionResult> ListMembershipsAsync(
        [FromQuery] int limit = 100,
        CancellationToken ct = default
    )
    {
        if (customerJourney is null)
            return IdentityProblem(
                503,
                "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "Membership authority is unavailable."
            );
        if (limit is < 1 or > 100)
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Invalid membership limit.");
        var memberships = (await customerJourney.ListMembershipsAsync(User, ct))
            .Take(limit)
            .Select(ToMembershipResponse)
            .ToArray();
        return Ok(
            new IdentityMembershipCollectionResponse(
                "1.0",
                memberships,
                memberships.Length switch
                {
                    0 => "ZERO",
                    1 => "ONE",
                    _ => "MANY",
                }
            )
        );
    }

    [HttpPost("membership-selections/validate")]
    [CustomerIdentityRoute]
    public async Task<IActionResult> ValidateMembershipSelectionAsync(
        [FromBody] IdentityMembershipSelectionRequest request,
        CancellationToken ct
    )
    {
        if (
            customerJourney is null
            || request.SchemaVersion != "1.0"
            || request.MembershipReference == Guid.Empty
        )
            return IdentityProblem(
                customerJourney is null ? 503 : 400,
                customerJourney is null
                    ? "IDENTITY_DEPENDENCY_UNAVAILABLE"
                    : "IDENTITY_REQUEST_INVALID",
                "Membership selection could not be validated."
            );
        try
        {
            _ = IdempotencyKey;
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "Invalid or missing Idempotency-Key header."
            );
        }
        var membership = await customerJourney.ValidateMembershipSelectionAsync(
            User,
            request.MembershipReference,
            ct
        );
        return Ok(
            new IdentityMembershipSelectionResponse(
                "1.0",
                ToMembershipResponse(
                    new CustomerWorkspaceMembershipProjection(
                        membership.AccountId,
                        membership.TenantId,
                        membership.MembershipId,
                        membership.Roles,
                        "ACTIVE"
                    )
                ),
                DateTimeOffset.UtcNow
            )
        );
    }

    private static IdentityMembershipResponse ToMembershipResponse(
        CustomerWorkspaceMembershipProjection membership
    ) =>
        new(
            membership.MembershipId,
            membership.TenantId,
            membership.Roles.Single(),
            membership.Status,
            membership.Status == "ACTIVE"
        );

    [HttpGet("session")]
    [CustomerIdentityRoute(requiresMembership: true, registrationRequiredWhenMissing: true)]
    public async Task<IActionResult> GetSessionAsync(CancellationToken ct)
    {
        var membership =
            HttpContext.Items[CustomerMembershipMiddleware.MembershipItem]
            as CustomerWorkspaceMembership;
        if (membership is null && customerJourney is null)
            return IdentityProblem(
                503,
                "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "Current membership authority is unavailable."
            );
        membership ??= await customerJourney!.ResolveAsync(User, ct);
        if (
            HttpContext.Items[CustomerMembershipMiddleware.AuthenticationTimeItem]
            is not DateTimeOffset authenticatedAt
        )
            return Problem(
                statusCode: StatusCodes.Status401Unauthorized,
                title: "Identity session is unavailable"
            );
        return Ok(
            new IdentitySessionResponse(
                membership.AccountId,
                membership.Roles,
                [],
                "AAL2_ACCOUNT",
                "PORTAL",
                true,
                false,
                authenticatedAt,
                DateTimeOffset.FromUnixTimeSeconds(
                    long.Parse(VerifiedIdentityProofAdapter.SingleClaim(User, "exp")!)
                ),
                "CONTINUE_TO_DEFAULT_TARGET"
            )
        );
    }

    [HttpGet("profile")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> GetCustomerProfileAsync(CancellationToken ct)
    {
        if (ValidatePortalSession(out var tenantId) is { } error)
            return error;
        try
        {
            var profile = await identityService.GetCustomerProfileAsync(ActorSubject, tenantId, ct);
            return Ok(ToProfileResponse(profile));
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(
                404,
                "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Account profile not found or not accessible."
            );
        }
    }

    [HttpPut("profile")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> UpdateCustomerProfileAsync(
        [FromBody] UpdateCustomerProfileRequest req,
        CancellationToken ct
    )
    {
        if (ValidatePortalSession(out var tenantId) is { } error)
            return error;
        if (!IsOwner)
            return IdentityProblem(
                403,
                "IDENTITY_ACTION_DENIED",
                "Owner authorization is required."
            );
        if (
            req.SchemaVersion != CustomerPortalSchemaVersion
            || string.IsNullOrWhiteSpace(req.DisplayName)
            || req.DisplayName.Length > 200
            || string.IsNullOrWhiteSpace(req.OrganizationDisplayName)
            || req.OrganizationDisplayName.Length > 200
        )
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Profile fields are invalid.");
        try
        {
            var profile = await identityService.UpdateCustomerProfileAsync(
                ActorSubject,
                tenantId,
                IdempotencyKey,
                ComputeHash(req),
                req.DisplayName.Trim(),
                req.OrganizationDisplayName.Trim(),
                ct
            );
            return Ok(ToProfileResponse(profile));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request."
            );
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(
                404,
                "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Account profile not found or not accessible."
            );
        }
        catch (ConstitutionalActionDeniedException)
        {
            return IdentityProblem(
                403,
                "IDENTITY_ACTION_DENIED",
                "Constitutional authorization denied the account link."
            );
        }
        catch (IdentityConstitutionalUnavailableException)
        {
            return IdentityProblem(
                503,
                "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "Constitutional evidence is unavailable."
            );
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "Invalid or missing Idempotency-Key header."
            );
        }
    }

    [HttpGet("settings")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> GetCustomerSettingsAsync(CancellationToken ct)
    {
        if (ValidatePortalSession(out var tenantId) is { } error)
            return error;
        try
        {
            return Ok(
                ToSettingsResponse(
                    await identityService.GetCustomerSettingsAsync(ActorSubject, tenantId, ct)
                )
            );
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(
                404,
                "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Account settings not found or not accessible."
            );
        }
    }

    [HttpPut("settings")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> UpdateCustomerSettingsAsync(
        [FromBody] UpdateCustomerSettingsRequest req,
        CancellationToken ct
    )
    {
        if (ValidatePortalSession(out var tenantId) is { } error)
            return error;
        if (
            req.SchemaVersion != CustomerPortalSchemaVersion
            || !LocalePattern.IsMatch(req.Locale)
            || req.Theme is not ("LIGHT" or "DARK")
            || req.TimestampVisibility is not ("RELATIVE" or "ABSOLUTE")
            || !ValidChannels(req.NotificationPreferences)
        )
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "Settings fields are invalid.");
        try
        {
            var preferences = req.NotificationPreferences;
            var settings = await identityService.UpdateCustomerSettingsAsync(
                ActorSubject,
                tenantId,
                IdempotencyKey,
                ComputeHash(req),
                req.Locale,
                req.Theme,
                req.TimestampVisibility,
                preferences.ApprovalRequests,
                preferences.MaturityReports,
                preferences.MonthlyNarratives,
                preferences.SelfGovernanceAlerts,
                ct
            );
            return Ok(ToSettingsResponse(settings));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request."
            );
        }
        catch (ConstitutionalActionDeniedException)
        {
            return IdentityProblem(
                403,
                "IDENTITY_ACTION_DENIED",
                "Constitutional authorization denied the account link."
            );
        }
        catch (IdentityConstitutionalUnavailableException)
        {
            return IdentityProblem(
                503,
                "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "Constitutional evidence is unavailable."
            );
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(
                404,
                "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Account settings not found or not accessible."
            );
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "Invalid or missing Idempotency-Key header."
            );
        }
    }

    [HttpGet("settings/workspace-layout")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> GetWorkspaceLayoutPreferencesAsync(CancellationToken ct)
    {
        if (ValidatePortalSession(out var tenantId) is { } error)
            return error;
        try
        {
            return Ok(
                ToWorkspaceLayoutResponse(
                    await identityService.GetWorkspaceLayoutPreferencesAsync(
                        ActorSubject,
                        tenantId,
                        ct
                    )
                )
            );
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(
                404,
                "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Workspace layout settings are not accessible."
            );
        }
    }

    [HttpPut("settings/workspace-layout")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> ReplaceWorkspaceLayoutPreferencesAsync(
        [FromBody] ReplaceWorkspaceLayoutPreferencesRequest request,
        CancellationToken ct
    )
    {
        if (ValidatePortalSession(out var tenantId) is { } error)
            return error;
        if (
            request.ExpectedVersion < 0
            || request.NavigationVisibility is not ("VISIBLE" or "COLLAPSED" or "HIDDEN")
            || request.ProgressVisibility is not ("VISIBLE" or "COLLAPSED" or "HIDDEN")
            || request.ConversationWidthPercent is < 35 or > 75
        )
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "Workspace layout fields are invalid."
            );
        try
        {
            return Ok(
                ToWorkspaceLayoutResponse(
                    await identityService.ReplaceWorkspaceLayoutPreferencesAsync(
                        ActorSubject,
                        tenantId,
                        IdempotencyKey,
                        ComputeHash(request),
                        request.ExpectedVersion,
                        request.NavigationVisibility,
                        request.ProgressVisibility,
                        request.ConversationWidthPercent,
                        request.ReduceMotion,
                        ct
                    )
                )
            );
        }
        catch (IdentityPreferenceVersionConflictException)
        {
            return IdentityProblem(
                409,
                "IDENTITY_VERSION_CONFLICT",
                "Workspace layout settings changed. Refresh before trying again."
            );
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request."
            );
        }
    }

    [HttpGet("login-methods")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public IActionResult ListCustomerLoginMethods()
    {
        if (ValidatePortalSession(out _) is { } error)
            return error;
        var activeProvider = User.FindFirstValue("identity_provider")?.ToUpperInvariant() switch
        {
            "META" => "FACEBOOK",
            "GOOGLE" => "GOOGLE",
            "APPLE" => "APPLE",
            _ => "EMAIL",
        };
        var maskedEmail = EmailClaim is { Length: > 0 } email
            ? IdentityService.MaskEmail(email)
            : null;
        var methods = providerProjectionService
            .GetProviders()
            .Select(provider => new CustomerLoginMethodResponse(
                provider.Id,
                provider.Id == activeProvider ? "ACTIVE"
                    : provider.Availability == "AVAILABLE" ? "AVAILABLE_TO_LINK"
                    : "BLOCKED",
                provider.Id == activeProvider ? maskedEmail : null
            ))
            .ToArray();
        return Ok(new CustomerLoginMethodCollectionResponse(CustomerPortalSchemaVersion, methods));
    }

    private static bool ValidChannels(NotificationPreferencesRequest preferences)
    {
        var allowed = new HashSet<string>(["IN_APP", "EMAIL", "WHATSAPP"], StringComparer.Ordinal);
        return preferences is not null
            && new[]
            {
                preferences.ApprovalRequests,
                preferences.MaturityReports,
                preferences.MonthlyNarratives,
                preferences.SelfGovernanceAlerts,
            }.All(channels => channels is not null && channels.All(allowed.Contains));
    }

    private static IReadOnlyList<string> CapabilitiesFor(IReadOnlyList<string> roles)
    {
        var capabilities = new HashSet<string>(StringComparer.Ordinal) { "READ_ACCOUNT" };
        if (
            roles.Contains("MANAGER", StringComparer.Ordinal)
            || roles.Contains("OWNER", StringComparer.Ordinal)
        )
            capabilities.Add("MANAGE_ROUTINE_ACTIONS");
        if (roles.Contains("OWNER", StringComparer.Ordinal))
        {
            capabilities.UnionWith([
                "MANAGE_ACCOUNT",
                "LINK_WHATSAPP",
                "ACCEPT_CONTRACT",
                "HIRE_PROFESSIONAL",
                "MANAGE_AUTHORITY",
            ]);
        }
        return capabilities.OrderBy(value => value, StringComparer.Ordinal).ToArray();
    }

    private IActionResult IdentityProblem(
        int status,
        string code,
        string detail,
        Guid? stepUpIntentId = null
    )
    {
        var correlationId = Guid.NewGuid();
        logger.LogWarning(
            "IdentityProblem status={Status} code={Code} correlationId={Id} path={Path}",
            status,
            code,
            correlationId,
            Request.Path
        );

        return IdentityProblemResponses.Create(status, code, detail, stepUpIntentId, correlationId);
    }

    // ── POST /api/v1/identity/registrations ──────────────────────────────────

    [HttpPost("registrations")]
    [CustomerIdentityRoute]
    public async Task<IActionResult> StartRegistrationAsync(
        [FromBody] StartRegistrationRequest req,
        CancellationToken ct
    )
    {
        try
        {
            if (!LanguagePattern.IsMatch(req.LanguagePreference))
                return IdentityProblem(
                    400,
                    "IDENTITY_REQUEST_INVALID",
                    "languagePreference is invalid."
                );

            if (customerJourney is not null)
            {
                var started = await customerJourney.StartAsync(
                    User,
                    IdempotencyKey,
                    req.LanguagePreference,
                    ct
                );
                return started.isNew
                    ? StatusCode(201, ToResponse(started.reg))
                    : Ok(ToResponse(started.reg));
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
                return IdentityProblem(
                    403,
                    "IDENTITY_ACTION_DENIED",
                    "Authentication path is unavailable."
                );
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);

            var emailClaim = User.FindFirstValue("email");
            var emailVerified = User.FindFirstValue("email_verified") == "true";
            var maskedEmail =
                emailVerified && emailClaim is not null
                    ? IdentityService.MaskEmail(emailClaim)
                    : null;

            var (reg, isNew) = await identityService.StartRegistrationAsync(
                ActorSubject,
                idempotencyKey,
                hash,
                req.LanguagePreference,
                authPath,
                providerLabel: User.FindFirstValue("identity_provider"),
                providerIssuer: ProviderIssuer,
                emailVerifiedByClaim: emailVerified,
                maskedEmail: maskedEmail,
                emailHmacKey: null,
                ct: ct
            );

            return isNew ? StatusCode(201, ToResponse(reg)) : Ok(ToResponse(reg));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request."
            );
        }
        catch (IdentityActionDeniedException ex)
        {
            return IdentityProblem(403, "IDENTITY_ACTION_DENIED", ex.Message);
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "Invalid or missing Idempotency-Key header."
            );
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
            return IdentityProblem(
                404,
                "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Registration not found or not accessible."
            );
        }
    }

    // ── PUT /api/v1/identity/registrations/{registrationId}/profile ───────────

    [HttpPut("registrations/{registrationId:guid}/profile")]
    [CustomerIdentityRoute]
    public async Task<IActionResult> UpdateProfileAsync(
        Guid registrationId,
        [FromBody] UpdateRegistrationProfileRequest req,
        CancellationToken ct
    )
    {
        if (
            string.IsNullOrWhiteSpace(req.DisplayName)
            || req.DisplayName.Length > 120
            || req.DisplayName.Contains('\0')
            || string.IsNullOrWhiteSpace(req.BusinessName)
            || req.BusinessName.Length > 160
            || req.BusinessName.Contains('\0')
            || string.IsNullOrWhiteSpace(req.BusinessDomain)
            || req.BusinessDomain.Length > 100
            || req.BusinessDomain.Contains('\0')
            || string.IsNullOrWhiteSpace(req.LanguagePreference)
            || !LanguagePattern.IsMatch(req.LanguagePreference)
        )
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "Registration profile is invalid."
            );
        }

        try
        {
            if (customerJourney is not null)
            {
                var updated = await customerJourney.UpdateAsync(
                    User,
                    registrationId,
                    IdempotencyKey,
                    req.DisplayName,
                    req.BusinessName,
                    req.BusinessDomain,
                    req.LanguagePreference,
                    ct
                );
                return Ok(ToResponse(updated.reg));
            }
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);

            var (reg, _) = await identityService.UpdateProfileAsync(
                registrationId,
                ActorSubject,
                idempotencyKey,
                hash,
                req.DisplayName,
                req.BusinessName,
                req.BusinessDomain,
                req.LanguagePreference,
                ct
            );

            return Ok(ToResponse(reg));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request."
            );
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(
                404,
                "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Registration not found or not accessible."
            );
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "Invalid or missing Idempotency-Key header."
            );
        }
    }

    // ── POST /api/v1/identity/registrations/{registrationId}/email-verifications

    [HttpPost("registrations/{registrationId:guid}/email-verifications")]
    [CustomerIdentityRoute]
    public async Task<IActionResult> StartEmailVerificationAsync(
        Guid registrationId,
        [FromBody] StartEmailVerificationRequest req,
        CancellationToken ct
    )
    {
        if (!IsValidEmail(req.Email))
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "email is invalid.");

        try
        {
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);

            var (challenge, _) = customerJourney is not null
                ? await customerJourney.StartEmailVerificationAsync(
                    User,
                    registrationId,
                    idempotencyKey,
                    hash,
                    req.Email,
                    ct
                )
                : await identityService.StartEmailVerificationAsync(
                    registrationId,
                    ActorSubject,
                    idempotencyKey,
                    hash,
                    req.Email,
                    ct
                );

            return StatusCode(202, ToResponse(challenge));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request."
            );
        }
        catch (IdentityDeliveryUnavailableException)
        {
            return IdentityProblem(
                503,
                "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "Verification delivery is temporarily unavailable."
            );
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(
                404,
                "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Registration not found or not accessible."
            );
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "Invalid or missing Idempotency-Key header."
            );
        }
    }

    // ── POST /registrations/{id}/email-verifications/confirm ─────────────────

    [HttpPost("registrations/{registrationId:guid}/email-verifications/confirm")]
    [CustomerIdentityRoute]
    public async Task<IActionResult> ConfirmEmailVerificationAsync(
        Guid registrationId,
        [FromBody] ConfirmVerificationRequest req,
        CancellationToken ct
    )
    {
        if (!VerificationCodePattern.IsMatch(req.Code))
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "verification code is invalid."
            );

        try
        {
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);

            var (reg, _) = await identityService.ConfirmEmailVerificationAsync(
                registrationId,
                ActorSubject,
                idempotencyKey,
                hash,
                req.ChallengeId,
                req.Code,
                ct
            );

            return Ok(ToResponse(reg));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request."
            );
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(
                404,
                "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Resource not found or not accessible."
            );
        }
        catch (IdentityChallengeExpiredException)
        {
            return IdentityProblem(
                410,
                "IDENTITY_CHALLENGE_EXPIRED",
                "Challenge is no longer usable."
            );
        }
        catch (IdentityActionDeniedException)
        {
            return IdentityProblem(
                403,
                "IDENTITY_ACTION_DENIED",
                "Verification could not be completed."
            );
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "Invalid or missing Idempotency-Key header."
            );
        }
    }

    // ── POST /registrations/{id}/mobile-verifications ─────────────────────────

    [HttpPost("registrations/{registrationId:guid}/mobile-verifications")]
    [CustomerIdentityRoute]
    public async Task<IActionResult> StartRegistrationMobileVerificationAsync(
        Guid registrationId,
        [FromBody] StartMobileVerificationRequest req,
        CancellationToken ct
    )
    {
        if (!MobilePattern.IsMatch(req.Mobile))
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "mobile is invalid.");

        try
        {
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);

            var (challenge, _) = customerJourney is not null
                ? await customerJourney.StartMobileVerificationAsync(
                    User,
                    registrationId,
                    idempotencyKey,
                    req.Mobile,
                    ct
                )
                : await identityService.StartMobileVerificationAsync(
                    registrationId,
                    ActorSubject,
                    idempotencyKey,
                    hash,
                    req.Mobile,
                    ct
                );

            return StatusCode(202, ToResponse(challenge));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request."
            );
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(
                404,
                "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Registration not found or not accessible."
            );
        }
        catch (IdentityDeliveryUnavailableException)
        {
            return IdentityProblem(
                503,
                "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "Verification delivery is temporarily unavailable."
            );
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "Invalid or missing Idempotency-Key header."
            );
        }
    }

    // ── POST /registrations/{id}/mobile-verifications/confirm ─────────────────

    [HttpPost("registrations/{registrationId:guid}/mobile-verifications/confirm")]
    [CustomerIdentityRoute]
    public async Task<IActionResult> ConfirmRegistrationMobileVerificationAsync(
        Guid registrationId,
        [FromBody] ConfirmVerificationRequest req,
        CancellationToken ct
    )
    {
        if (!VerificationCodePattern.IsMatch(req.Code))
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "verification code is invalid."
            );

        try
        {
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);
            var actor = customerJourney?.ValidateActor(User);

            var (result, _) = await identityService.ConfirmMobileVerificationAsync(
                registrationId,
                actor?.Subject ?? ActorSubject,
                idempotencyKey,
                hash,
                req.ChallengeId,
                req.Code,
                ct,
                actor
            );

            if (result is IdentityRegistrationRecord reg)
                return Ok(ToResponse(reg));

            return Ok(result);
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request."
            );
        }
        catch (IdentityChallengeExpiredException)
        {
            return IdentityProblem(
                410,
                "IDENTITY_CHALLENGE_EXPIRED",
                "Challenge is no longer usable."
            );
        }
        catch (IdentityActionDeniedException)
        {
            return IdentityProblem(
                403,
                "IDENTITY_ACTION_DENIED",
                "Verification could not be completed."
            );
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(
                404,
                "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Resource not found or not accessible."
            );
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "Invalid or missing Idempotency-Key header."
            );
        }
    }

    // ── POST /registrations/{id}/complete ─────────────────────────────────────

    [HttpPost("registrations/{registrationId:guid}/complete")]
    [CustomerIdentityRoute]
    public async Task<IActionResult> CompleteRegistrationAsync(
        Guid registrationId,
        CancellationToken ct
    )
    {
        try
        {
            if (customerJourney is not null)
            {
                var completed = await customerJourney.CompleteAsync(
                    User,
                    registrationId,
                    IdempotencyKey,
                    ct
                );
                return new ContentResult
                {
                    StatusCode = completed.StatusCode,
                    ContentType = "application/json",
                    Content = completed.ResponseBody,
                };
            }
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(new { registrationId });

            var (result, _) = await identityService.CompleteRegistrationAsync(
                registrationId,
                ActorSubject,
                idempotencyKey,
                hash,
                ct
            );

            return Ok(
                new IdentityCompletionResponse(
                    result.Outcome,
                    result.AccountReference,
                    result.AssuranceLevel,
                    result.DefaultTarget
                )
            );
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request."
            );
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(
                404,
                "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Registration not found or not accessible."
            );
        }
        catch (IdentityVerificationRequiredException ex)
        {
            return IdentityProblem(409, "IDENTITY_VERIFICATION_REQUIRED", ex.Message);
        }
        catch (IdentityDuplicateResolutionRequiredException ex)
        {
            return IdentityProblem(409, "DUPLICATE_RESOLUTION_REQUIRED", ex.Message);
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "A valid Idempotency-Key is required for registration completion."
            );
        }
    }

    // ── POST /api/v1/identity/mobile-verifications (progressive) ─────────────

    [HttpPost("mobile-verifications")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> StartAccountMobileVerificationAsync(
        [FromBody] StartMobileVerificationRequest req,
        CancellationToken ct
    )
    {
        if (!MobilePattern.IsMatch(req.Mobile))
            return IdentityProblem(400, "IDENTITY_REQUEST_INVALID", "mobile is invalid.");

        try
        {
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);
            var actor = customerJourney?.ValidateActor(User);

            var (challenge, _) = actor is null
                ? await identityService.StartMobileVerificationAsync(
                    null,
                    ActorSubject,
                    idempotencyKey,
                    hash,
                    req.Mobile,
                    ct
                )
                : await identityService.StartMobileVerificationAsync(
                    null,
                    actor,
                    idempotencyKey,
                    hash,
                    req.Mobile,
                    ct
                );

            return StatusCode(202, ToResponse(challenge));
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request."
            );
        }
        catch (IdentityDeliveryUnavailableException)
        {
            return IdentityProblem(
                503,
                "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "Verification delivery is temporarily unavailable."
            );
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "Invalid or missing Idempotency-Key header."
            );
        }
    }

    // ── POST /api/v1/identity/mobile-verifications/confirm (progressive) ──────

    [HttpPost("mobile-verifications/confirm")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> ConfirmAccountMobileVerificationAsync(
        [FromBody] ConfirmVerificationRequest req,
        CancellationToken ct
    )
    {
        if (!VerificationCodePattern.IsMatch(req.Code))
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "verification code is invalid."
            );

        try
        {
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);
            var actor = customerJourney?.ValidateActor(User);

            var (result, _) = await identityService.ConfirmMobileVerificationAsync(
                null,
                actor?.Subject ?? ActorSubject,
                idempotencyKey,
                hash,
                req.ChallengeId,
                req.Code,
                ct,
                actor
            );

            var status = (IdentityMobileStatusResult)result;
            return Ok(
                new IdentityMobileStatusResponse(
                    status.MobileVerified,
                    status.MaskedMobile,
                    status.VerifiedAt
                )
            );
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request."
            );
        }
        catch (IdentityChallengeExpiredException)
        {
            return IdentityProblem(
                410,
                "IDENTITY_CHALLENGE_EXPIRED",
                "Challenge is no longer usable."
            );
        }
        catch (IdentityActionDeniedException)
        {
            return IdentityProblem(
                403,
                "IDENTITY_ACTION_DENIED",
                "Verification could not be completed."
            );
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(
                404,
                "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Resource not found or not accessible."
            );
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "Invalid or missing Idempotency-Key header."
            );
        }
    }

    // ── POST /api/v1/identity/session-revocations ─────────────────────────────

    [HttpPost("session-revocations")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> RecordSessionRevocationAsync(
        [FromBody] IdentitySessionRevocationIntentRequest request,
        CancellationToken ct
    )
    {
        if (securityEvents is null || CurrentMembership is null)
            return IdentityProblem(
                503,
                "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "Session revocation evidence is unavailable."
            );
        if (
            request.SchemaVersion != "1.0"
            || request.CorrelationId == Guid.Empty
            || !SessionRevocationReasons.Contains(request.Reason)
            || request.Scope is not ("FAMILY" or "ALL")
            || (request.Scope == "FAMILY" && request.SessionFamilyReference is null)
            || (request.Scope == "ALL" && request.SessionFamilyReference is not null)
        )
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "The session revocation receipt is invalid."
            );
        try
        {
            var idempotencyKey = IdempotencyKey;
            var inserted = await securityEvents.RecordAsync(
                new IdentitySecurityEventInput(
                    request.CorrelationId,
                    $"web-revocation:{idempotencyKey:D}",
                    request.Scope == "ALL" ? "SESSION_REVOCATION_ALL" : "SESSION_REVOCATION_ONE",
                    "INTERNAL",
                    "SUCCEEDED",
                    request.Reason,
                    AssuranceClass,
                    "BUSINESS_PLATFORM",
                    ActorSubject,
                    request.SessionFamilyReference?.ToString("D")
                ),
                ct
            );
            return Accepted(
                new IdentitySessionRevocationReceiptResponse(
                    "1.0",
                    idempotencyKey,
                    request.Scope,
                    "RECORDED",
                    DateTimeOffset.UtcNow,
                    !inserted
                )
            );
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "A valid Idempotency-Key is required."
            );
        }
    }

    // ── POST /api/v1/identity/provider-links ──────────────────────────────────

    [HttpPost("provider-links")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> StartProviderLinkAsync(
        [FromBody] IdentityProviderLinkRequest request,
        CancellationToken ct
    )
    {
        if (lifecycleService is null || customerJourney is null || CurrentMembership is null)
            return IdentityProblem(
                503,
                "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "The identity lifecycle boundary is unavailable."
            );
        if (!HasLifecycleStepUp)
            return IdentityProblem(
                403,
                "IDENTITY_STEP_UP_REQUIRED",
                "A recent operation-bound step-up is required.",
                request.StepUpTransactionReference
            );
        if (
            request.SchemaVersion != "1.0"
            || !Enum.TryParse<IdentityLifecycleProvider>(request.Provider, true, out var provider)
        )
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "The provider-link request is invalid."
            );
        try
        {
            var operation = await lifecycleService.BeginLinkAsync(
                customerJourney.ValidateActor(User),
                provider,
                request.StepUpTransactionReference,
                IdempotencyKey,
                RequestCorrelationId(),
                ct
            );
            return Accepted(ToResponse(operation));
        }
        catch (IdentityLifecycleConflictException)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with different input."
            );
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "A valid Idempotency-Key is required."
            );
        }
    }

    [HttpDelete("provider-links/{linkId:guid}")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> StartProviderUnlinkAsync(Guid linkId, CancellationToken ct)
    {
        if (lifecycleService is null || customerJourney is null || CurrentMembership is null)
            return IdentityProblem(
                503,
                "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "The identity lifecycle boundary is unavailable."
            );
        if (!HasLifecycleStepUp)
            return IdentityProblem(
                403,
                "IDENTITY_STEP_UP_REQUIRED",
                "A recent operation-bound step-up is required."
            );
        try
        {
            var operation = await lifecycleService.BeginUnlinkAsync(
                customerJourney.ValidateActor(User),
                linkId,
                IdempotencyKey,
                RequestCorrelationId(),
                ct
            );
            return Accepted(ToResponse(operation));
        }
        catch (IdentityActionDeniedException)
        {
            return IdentityProblem(
                404,
                "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Provider link not found or not accessible."
            );
        }
        catch (IdentityLifecycleConflictException)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with different input."
            );
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "A valid Idempotency-Key is required."
            );
        }
    }

    private Guid RequestCorrelationId()
    {
        var bytes = System.Security.Cryptography.SHA256.HashData(
            System.Text.Encoding.UTF8.GetBytes($"wc123:lifecycle:{HttpContext.TraceIdentifier}")
        );
        return new Guid(bytes.AsSpan(0, 16));
    }

    // ── POST /api/v1/identity/account-links ───────────────────────────────────

    [HttpPost("account-links")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> StartAccountLinkAsync(
        [FromBody] StartAccountLinkRequest req,
        CancellationToken ct
    )
    {
        var tenantId = TenantIdFromContext;
        if (tenantId is null)
            return IdentityProblem(
                401,
                "IDENTITY_SESSION_REQUIRED",
                "Authenticated account session required."
            );
        if (!IsOwner)
            return IdentityProblem(
                403,
                "IDENTITY_ACTION_DENIED",
                "Owner authorization is required."
            );

        try
        {
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(req);

            var (link, isNew) = await identityService.StartAccountLinkAsync(
                ActorSubject,
                tenantId.Value,
                idempotencyKey,
                hash,
                req.VerifiedMobileProofId,
                AuthTime,
                ct
            );

            return isNew ? StatusCode(201, ToResponse(link)) : Ok(ToResponse(link));
        }
        catch (IdentityStepUpRequiredException ex)
        {
            return IdentityProblem(
                403,
                "IDENTITY_STEP_UP_REQUIRED",
                "A freshly authenticated session is required.",
                ex.IntentId
            );
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request."
            );
        }
        catch (ConstitutionalActionDeniedException)
        {
            return IdentityProblem(
                403,
                "IDENTITY_ACTION_DENIED",
                "Constitutional authorization denied the account link."
            );
        }
        catch (IdentityConstitutionalUnavailableException)
        {
            return IdentityProblem(
                503,
                "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "Constitutional evidence is unavailable."
            );
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "Invalid or missing Idempotency-Key header."
            );
        }
    }

    // ── POST /api/v1/identity/account-links/{linkId}/approve ─────────────────

    [HttpPost("account-links/{linkId:guid}/approve")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> ApproveAccountLinkAsync(Guid linkId, CancellationToken ct)
    {
        var tenantId = TenantIdFromContext;
        if (tenantId is null)
            return IdentityProblem(
                401,
                "IDENTITY_SESSION_REQUIRED",
                "Authenticated account session required."
            );
        if (!IsOwner)
            return IdentityProblem(
                403,
                "IDENTITY_ACTION_DENIED",
                "Owner authorization is required."
            );

        try
        {
            var idempotencyKey = IdempotencyKey;
            var hash = ComputeHash(new { linkId });

            var (link, _) = await identityService.ApproveAccountLinkAsync(
                linkId,
                ActorSubject,
                tenantId.Value,
                idempotencyKey,
                hash,
                AuthTime,
                ct
            );

            return Ok(ToResponse(link));
        }
        catch (IdentityStepUpRequiredException ex)
        {
            return IdentityProblem(
                403,
                "IDENTITY_STEP_UP_REQUIRED",
                "A freshly authenticated session is required.",
                ex.IntentId
            );
        }
        catch (IdentityIdempotencyConflict)
        {
            return IdentityProblem(
                409,
                "IDENTITY_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request."
            );
        }
        catch (ConstitutionalActionDeniedException)
        {
            return IdentityProblem(
                403,
                "IDENTITY_ACTION_DENIED",
                "Constitutional authorization denied the account link."
            );
        }
        catch (IdentityConstitutionalUnavailableException)
        {
            return IdentityProblem(
                503,
                "IDENTITY_DEPENDENCY_UNAVAILABLE",
                "Constitutional evidence is unavailable."
            );
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(
                404,
                "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Link not found or not accessible."
            );
        }
        catch (IdentityChallengeExpiredException)
        {
            return IdentityProblem(
                410,
                "IDENTITY_CHALLENGE_EXPIRED",
                "Link challenge has expired."
            );
        }
        catch (ArgumentException)
        {
            return IdentityProblem(
                400,
                "IDENTITY_REQUEST_INVALID",
                "Invalid or missing Idempotency-Key header."
            );
        }
    }

    // ── GET /api/v1/identity/account-links/{linkId} ───────────────────────────

    [HttpGet("account-links/{linkId:guid}")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> GetAccountLinkAsync(Guid linkId, CancellationToken ct)
    {
        var tenantId = TenantIdFromContext;
        if (tenantId is null)
            return IdentityProblem(
                401,
                "IDENTITY_SESSION_REQUIRED",
                "Authenticated account session required."
            );
        if (!IsOwner)
            return IdentityProblem(
                403,
                "IDENTITY_ACTION_DENIED",
                "Owner authorization is required."
            );

        try
        {
            var link = await identityService.GetAccountLinkAsync(
                linkId,
                ActorSubject,
                tenantId.Value,
                ct
            );
            return Ok(ToResponse(link));
        }
        catch (IdentityResourceNotFoundException)
        {
            return IdentityProblem(
                404,
                "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                "Link not found or not accessible."
            );
        }
    }
}
