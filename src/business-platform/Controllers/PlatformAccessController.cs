// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004, WC137-R005
// Constitutional basis: C-009, C-023, C-026, C-059, C-063

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.PlatformAccess;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record AccessRequestBody(string? Role, string? Justification);

public sealed record AccessDecisionBody(string? Decision, string? Reason);

public sealed record AccessRevocationBody(string? Reason);

/// <summary>
/// Staff access without self-assignment: a signed-in person with a verified email asks for a role, the Founder
/// approves it with a fresh strong sign-in, and the approval becomes a time-limited grant. Founder grants come
/// only from configuration and cannot be changed here.
/// </summary>
[ApiController]
[Authorize]
[StaffIdentityRoute]
[RequestSizeLimit(8192)]
[Route("api/v1/platform")]
public sealed class PlatformAccessController(IPlatformAccessStore store, TimeProvider clock)
    : ControllerBase
{
    private static readonly JsonSerializerOptions StrictJson = new(JsonSerializerDefaults.Web)
    {
        UnmappedMemberHandling = System.Text.Json.Serialization.JsonUnmappedMemberHandling.Disallow,
    };

    [HttpGet("me/roles")]
    public async Task<IActionResult> MyRolesAsync(CancellationToken ct)
    {
        var verified = PlatformRoles.TryIdentity(User, out var email, out var subject);
        var roles = User.FindAll(ClaimTypes.Role)
            .Select(claim => claim.Value)
            .Distinct(StringComparer.Ordinal)
            .Order(StringComparer.Ordinal)
            .ToArray();
        var requests = verified ? await store.ListRequestsAsync(null, subject, 5, ct) : [];
        Response.Headers.CacheControl = "no-store";
        return Ok(
            new
            {
                email = verified ? email : null,
                emailVerified = verified,
                roles,
                founder = roles.Contains(PlatformRoles.Founder),
                pricingAdmin = roles.Contains(PlatformRoles.PricingAdmin),
                requestableRoles = verified ? PlatformRoles.Requestable : [],
                requests = requests.Select(Present),
            }
        );
    }

    [HttpPost("access-requests")]
    public async Task<IActionResult> RequestAsync(CancellationToken ct)
    {
        if (!PlatformRoles.TryIdentity(User, out var email, out var subject))
            return Problem(
                403,
                "PLATFORM_ACCESS_VERIFIED_EMAIL_REQUIRED",
                "Sign in with an account whose email address is verified."
            );
        var body = await ReadAsync<AccessRequestBody>(ct);
        var role = body?.Role?.Trim();
        var justification = body?.Justification?.Trim();
        if (role is null || !PlatformRoles.Requestable.Contains(role))
            return Problem(400, "PLATFORM_ACCESS_ROLE_INVALID", "Choose a role from the list.");
        if (justification is null || justification.Length is < 10 or > 500)
            return Problem(
                400,
                "PLATFORM_ACCESS_JUSTIFICATION_INVALID",
                "Explain why you need this role in 10 to 500 characters."
            );
        var (result, requestId) = await store.CreateRequestAsync(
            subject,
            email,
            role,
            justification,
            clock.GetUtcNow(),
            ct
        );
        return result switch
        {
            AccessRequestResult.Created => Accepted(new { requestId, status = "PENDING" }),
            AccessRequestResult.AlreadyGranted => Problem(
                409,
                "PLATFORM_ACCESS_ALREADY_GRANTED",
                "You already hold this role."
            ),
            AccessRequestResult.AlreadyPending => Problem(
                409,
                "PLATFORM_ACCESS_REQUEST_PENDING",
                "You already have a request waiting for a decision."
            ),
            AccessRequestResult.RateLimited => Problem(
                429,
                "PLATFORM_ACCESS_RATE_LIMITED",
                "Too many requests today. Try again tomorrow."
            ),
            _ => Problem(
                503,
                "PLATFORM_ACCESS_BACKLOG_FULL",
                "Requests cannot be accepted right now."
            ),
        };
    }

    [HttpGet("access-requests")]
    public async Task<IActionResult> ListRequestsAsync(
        [FromQuery] string? status,
        CancellationToken ct
    )
    {
        if (!User.IsInRole(PlatformRoles.Founder))
            return Problem(
                403,
                "PLATFORM_ACCESS_FOUNDER_REQUIRED",
                "Only the Founder can do this."
            );
        var normalized = status?.Trim().ToUpperInvariant();
        if (normalized is not (null or "PENDING" or "APPROVED" or "REJECTED"))
            return Problem(
                400,
                "PLATFORM_ACCESS_STATUS_INVALID",
                "Use PENDING, APPROVED or REJECTED."
            );
        var requests = await store.ListRequestsAsync(normalized, null, 100, ct);
        Response.Headers.CacheControl = "no-store";
        return Ok(new { requests = requests.Select(Present) });
    }

    [HttpPost("access-requests/{requestId:guid}/decision")]
    public async Task<IActionResult> DecideAsync(Guid requestId, CancellationToken ct)
    {
        if (!User.IsInRole(PlatformRoles.Founder))
            return Problem(
                403,
                "PLATFORM_ACCESS_FOUNDER_REQUIRED",
                "Only the Founder can do this."
            );
        var body = await ReadAsync<AccessDecisionBody>(ct);
        var decision = body?.Decision?.Trim().ToUpperInvariant();
        var reason = body?.Reason?.Trim();
        if (decision is not ("APPROVE" or "REJECT"))
            return Problem(400, "PLATFORM_ACCESS_DECISION_INVALID", "Use APPROVE or REJECT.");
        if (reason is not null && reason.Length is 0 or > 500)
            return Problem(
                400,
                "PLATFORM_ACCESS_REASON_INVALID",
                "A reason is up to 500 characters."
            );
        var approve = decision == "APPROVE";
        // Granting power needs a fresh strong sign-in; declining it never does.
        if (approve && !PlatformRoles.HasStepUp(User, clock.GetUtcNow()))
            return Problem(
                403,
                "PLATFORM_ACCESS_STEP_UP_REQUIRED",
                "A fresh strong sign-in is required to approve access."
            );
        if (!PlatformRoles.TryIdentity(User, out var email, out _))
            return Problem(
                403,
                "PLATFORM_ACCESS_VERIFIED_EMAIL_REQUIRED",
                "Sign in with an account whose email address is verified."
            );
        return await store.DecideAsync(
            requestId,
            approve,
            email,
            reason,
            clock.GetUtcNow(),
            ct
        ) switch
        {
            AccessDecisionResult.Decided => Ok(
                new { requestId, status = approve ? "APPROVED" : "REJECTED" }
            ),
            AccessDecisionResult.NotFound => Problem(
                404,
                "PLATFORM_ACCESS_REQUEST_NOT_FOUND",
                "No such request."
            ),
            AccessDecisionResult.NotPending => Problem(
                409,
                "PLATFORM_ACCESS_REQUEST_DECIDED",
                "This request has already been decided."
            ),
            _ => Problem(
                403,
                "PLATFORM_ACCESS_SELF_APPROVAL_DENIED",
                "You cannot approve your own request."
            ),
        };
    }

    [HttpGet("grants")]
    public async Task<IActionResult> ListGrantsAsync(CancellationToken ct)
    {
        if (!User.IsInRole(PlatformRoles.Founder))
            return Problem(
                403,
                "PLATFORM_ACCESS_FOUNDER_REQUIRED",
                "Only the Founder can do this."
            );
        var grants = await store.ListGrantsAsync(clock.GetUtcNow(), ct);
        Response.Headers.CacheControl = "no-store";
        return Ok(
            new
            {
                grants = grants.Select(grant => new
                {
                    grantId = grant.GrantId,
                    email = grant.Email,
                    role = grant.Role,
                    source = grant.Source,
                    grantedBy = grant.GrantedBy,
                    grantedAt = grant.GrantedAt,
                    expiresAt = grant.ExpiresAt,
                    revocable = grant.Source == "APPROVAL",
                }),
            }
        );
    }

    // Revoking only removes power, so it needs the Founder but not a fresh strong sign-in.
    [HttpPost("grants/{grantId:guid}/revoke")]
    public async Task<IActionResult> RevokeAsync(Guid grantId, CancellationToken ct)
    {
        if (!User.IsInRole(PlatformRoles.Founder))
            return Problem(
                403,
                "PLATFORM_ACCESS_FOUNDER_REQUIRED",
                "Only the Founder can do this."
            );
        var body = await ReadAsync<AccessRevocationBody>(ct);
        var reason = body?.Reason?.Trim();
        if (reason is null || reason.Length is 0 or > 500)
            return Problem(
                400,
                "PLATFORM_ACCESS_REASON_INVALID",
                "Give a reason of up to 500 characters."
            );
        if (!PlatformRoles.TryIdentity(User, out var email, out _))
            return Problem(
                403,
                "PLATFORM_ACCESS_VERIFIED_EMAIL_REQUIRED",
                "Sign in with an account whose email address is verified."
            );
        return await store.RevokeAsync(grantId, email, reason, clock.GetUtcNow(), ct) switch
        {
            AccessRevocationResult.Revoked => Ok(new { grantId, revoked = true }),
            AccessRevocationResult.NotFound => Problem(
                404,
                "PLATFORM_ACCESS_GRANT_NOT_FOUND",
                "No such active grant."
            ),
            _ => Problem(
                409,
                "PLATFORM_ACCESS_FOUNDER_PROTECTED",
                "A Founder is set in the environment configuration and cannot be revoked here."
            ),
        };
    }

    private static object Present(PlatformAccessRequest request) =>
        new
        {
            requestId = request.RequestId,
            email = request.Email,
            role = request.Role,
            justification = request.Justification,
            status = request.Status,
            requestedAt = request.RequestedAt,
            decidedAt = request.DecidedAt,
            decisionReason = request.DecisionReason,
        };

    private async Task<T?> ReadAsync<T>(CancellationToken ct)
        where T : class
    {
        try
        {
            return await JsonSerializer.DeserializeAsync<T>(Request.Body, StrictJson, ct);
        }
        catch (JsonException)
        {
            return null;
        }
    }

    private ObjectResult Problem(int status, string code, string detail)
    {
        var result = new ObjectResult(
            new
            {
                type = $"https://waooaw.com/problems/{code.ToLowerInvariant().Replace('_', '-')}",
                title = code,
                status,
                code,
                detail,
                correlationId = Guid.NewGuid(),
            }
        )
        {
            StatusCode = status,
        };
        result.ContentTypes.Add("application/problem+json");
        return result;
    }
}
