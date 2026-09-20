// Implements: architecture/reference/product/wc085-identity-architecture-decision.md First Slice Defaults
// constitutional_basis: C-023, C-026, C-059

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc.Controllers;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Infrastructure;

[AttributeUsage(AttributeTargets.Method)]
public sealed class CustomerIdentityRouteAttribute(
    bool requiresMembership = false,
    bool registrationRequiredWhenMissing = false
) : Attribute
{
    public bool RequiresMembership { get; } = requiresMembership;
    public bool RegistrationRequiredWhenMissing { get; } = registrationRequiredWhenMissing;
}

public sealed class CustomerMembershipMiddleware(RequestDelegate next)
{
    public const string JourneyItem = "waooaw:customer-identity-journey";
    public const string MembershipItem = "waooaw:customer-membership";
    public const string SessionIdItem = "waooaw:customer-session-id";

    public async Task InvokeAsync(HttpContext context)
    {
        var endpoint = context.GetEndpoint();
        if (endpoint?.Metadata.GetMetadata<IAllowAnonymous>() is not null)
        {
            await next(context);
            return;
        }
        var route = endpoint?.Metadata.GetMetadata<CustomerIdentityRouteAttribute>();
        var identityController =
            endpoint?.Metadata.GetMetadata<ControllerActionDescriptor>()?.ControllerTypeInfo
            == typeof(IdentityController);
        var customer = IsCustomer(context.User);
        if (route is null && !identityController && !customer)
        {
            await next(context);
            return;
        }
        context.Response.Headers.CacheControl = "no-store";
        context.Items.Remove(TenantIsolationMiddleware.TenantIdItemKey);
        try
        {
            if (route is null)
                throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            var journey =
                context.RequestServices.GetRequiredService<CustomerIdentityJourneyService>();
            journey.ValidateActor(context.User);
            if (route.RequiresMembership)
            {
                var membership = await journey.ResolveAsync(context.User, context.RequestAborted);
                CheckHeader(context, "x-tenant-id", membership.TenantId);
                CheckHeader(context, "x-account-id", membership.AccountId);
                var sessions = context.RequestServices.GetRequiredService<IdentitySessionService>();
                var sourceSessionId =
                    context.User.FindFirstValue("sid")
                    ?? context.User.FindFirstValue("jti")
                    ?? $"{journey.ValidateActor(context.User).Subject}\u001f{TokenTime(context, "auth_time"):O}";
                var sessionId = await sessions.ObserveAsync(
                    membership.AccountId,
                    $"{journey.ValidateActor(context.User).Issuer}\u001f{journey.ValidateActor(context.User).Subject}",
                    sourceSessionId,
                    TokenTime(context, "auth_time"),
                    TokenTime(context, "exp"),
                    AssuranceClass(context),
                    ProviderClass(context),
                    context.RequestAborted
                );
                context.Items[MembershipItem] = membership;
                context.Items[SessionIdItem] = sessionId;
                context.Items[TenantIsolationMiddleware.TenantIdItemKey] =
                    membership.TenantId.ToString();
            }
            else if (
                context.Request.Headers.ContainsKey("x-tenant-id")
                || context.Request.Headers.ContainsKey("x-account-id")
            )
                throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            context.Items[JourneyItem] = true;
            await next(context);
        }
        catch (CustomerWorkspaceException exception)
        {
            var registrationRequired =
                exception.Error == CustomerWorkspaceError.MembershipRequired
                && route?.RegistrationRequiredWhenMissing == true;
            var code = registrationRequired
                ? "REGISTRATION_REQUIRED"
                : exception.Error switch
                {
                    CustomerWorkspaceError.IdempotencyConflict => "IDENTITY_IDEMPOTENCY_CONFLICT",
                    CustomerWorkspaceError.RegistrationNotFound =>
                        "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                    CustomerWorkspaceError.FreshAuthenticationRequired =>
                        "IDENTITY_STEP_UP_REQUIRED",
                    CustomerWorkspaceError.RecoveryRequired =>
                        "IDENTITY_DUPLICATE_RESOLUTION_REQUIRED",
                    CustomerWorkspaceError.RegistrationIneligible =>
                        "IDENTITY_VERIFICATION_REQUIRED",
                    CustomerWorkspaceError.MembershipRequired => "IDENTITY_ACTION_DENIED",
                    CustomerWorkspaceError.MembershipInactive => "IDENTITY_ACTION_DENIED",
                    CustomerWorkspaceError.InvalidInput => "IDENTITY_REQUEST_INVALID",
                    _ => "IDENTITY_DEPENDENCY_UNAVAILABLE",
                };
            await ProblemAsync(
                context,
                registrationRequired ? StatusCodes.Status409Conflict : exception.StatusCode,
                code
            );
        }
        catch (IdentityActionDeniedException)
        {
            await ProblemAsync(context, 403, "IDENTITY_ACTION_DENIED");
        }
        catch (Exception exception)
            when (exception is NpgsqlException or DbUpdateException
                || exception is OperationCanceledException
                    && !context.RequestAborted.IsCancellationRequested
            )
        {
            await ProblemAsync(context, 503, "IDENTITY_DEPENDENCY_UNAVAILABLE");
        }
        finally
        {
            context.Items.Remove(JourneyItem);
            context.Items.Remove(MembershipItem);
            context.Items.Remove(SessionIdItem);
            context.Items.Remove(TenantIsolationMiddleware.TenantIdItemKey);
        }
    }

    private static DateTimeOffset TokenTime(HttpContext context, string claim) =>
        context.User.FindFirstValue(claim) is string value && long.TryParse(value, out var seconds)
            ? DateTimeOffset.FromUnixTimeSeconds(seconds)
            : throw new IdentityActionDeniedException("IDENTITY_SESSION_REQUIRED");

    private static string AssuranceClass(HttpContext context) =>
        DateTimeOffset.UtcNow - TokenTime(context, "auth_time") <= TimeSpan.FromMinutes(5)
            ? "AAL3"
            : "AAL2";

    private static string ProviderClass(HttpContext context) =>
        (context.User.FindFirstValue("identity_provider") ?? context.User.FindFirstValue("idp"))
            ?.ToLowerInvariant() switch
        {
            "google" => "GOOGLE",
            "facebook" => "FACEBOOK",
            "apple" => "APPLE",
            "email" => "EMAIL",
            _ => "UNKNOWN",
        };

    private static void CheckHeader(HttpContext context, string name, Guid expected)
    {
        if (
            context.Request.Headers.TryGetValue(name, out var values)
            && (
                values.Count != 1 || !Guid.TryParse(values[0], out var actual) || actual != expected
            )
        )
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
    }

    private static bool IsCustomer(ClaimsPrincipal principal)
    {
        if (
            principal.HasClaim("azp", "waooaw-web")
            || principal.HasClaim("azp", "waooaw-mobile")
            || principal.HasClaim("idp", "google")
            || principal.IsInRole("customer")
        )
            return true;
        try
        {
            return principal
                .FindAll("realm_access")
                .Select(claim =>
                {
                    using var realm = JsonDocument.Parse(claim.Value);
                    return realm
                        .RootElement.GetProperty("roles")
                        .EnumerateArray()
                        .Any(role => role.GetString() == "customer");
                })
                .Any(isCustomer => isCustomer);
        }
        catch (Exception exception)
            when (exception is JsonException or KeyNotFoundException or InvalidOperationException)
        {
            return true;
        }
    }

    private static Task ProblemAsync(HttpContext context, int status, string code)
    {
        context.Response.StatusCode = status;
        return context.Response.WriteAsJsonAsync(
            new
            {
                type = "https://waooaw.com/errors/identity/"
                    + code.ToLowerInvariant().Replace('_', '-'),
                title = code,
                status,
                code,
                detail = "The identity operation could not be completed.",
                correlationId = Guid.NewGuid(),
            },
            options: null,
            contentType: "application/problem+json",
            cancellationToken: context.RequestAborted
        );
    }
}
