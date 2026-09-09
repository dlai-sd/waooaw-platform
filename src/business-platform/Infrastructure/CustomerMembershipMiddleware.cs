// Implements: architecture/reference/product/wc085-identity-architecture-decision.md First Slice Defaults
// constitutional_basis: C-023, C-026, C-059

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc.Controllers;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using System.Security.Claims;
using System.Text.Json;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Infrastructure;

[AttributeUsage(AttributeTargets.Method)]
public sealed class CustomerIdentityRouteAttribute(bool requiresMembership = false) : Attribute
{
    public bool RequiresMembership { get; } = requiresMembership;
}

public sealed class CustomerMembershipMiddleware(RequestDelegate next)
{
    public const string JourneyItem = "waooaw:customer-identity-journey";
    public const string MembershipItem = "waooaw:customer-membership";

    public async Task InvokeAsync(HttpContext context, CustomerIdentityJourneyService journey)
    {
        var endpoint = context.GetEndpoint();
        if (endpoint?.Metadata.GetMetadata<IAllowAnonymous>() is not null)
        {
            await next(context);
            return;
        }
        var route = endpoint?.Metadata.GetMetadata<CustomerIdentityRouteAttribute>();
        var identityController = endpoint?.Metadata.GetMetadata<ControllerActionDescriptor>()?.ControllerTypeInfo
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
            if (route is null) throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            journey.ValidateActor(context.User);
            if (route.RequiresMembership)
            {
                var membership = await journey.ResolveAsync(context.User, context.RequestAborted);
                CheckHeader(context, "x-tenant-id", membership.TenantId);
                CheckHeader(context, "x-account-id", membership.AccountId);
                context.Items[MembershipItem] = membership;
            }
            else if (context.Request.Headers.ContainsKey("x-tenant-id") || context.Request.Headers.ContainsKey("x-account-id"))
                throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            context.Items[JourneyItem] = true;
            await next(context);
        }
        catch (CustomerWorkspaceException exception)
        {
            var code = exception.Error switch
            {
                CustomerWorkspaceError.IdempotencyConflict => "IDENTITY_IDEMPOTENCY_CONFLICT",
                CustomerWorkspaceError.RegistrationNotFound => "IDENTITY_RESOURCE_NOT_ACCESSIBLE",
                CustomerWorkspaceError.FreshAuthenticationRequired => "IDENTITY_STEP_UP_REQUIRED",
                CustomerWorkspaceError.RecoveryRequired => "IDENTITY_DUPLICATE_RESOLUTION_REQUIRED",
                CustomerWorkspaceError.RegistrationIneligible => "IDENTITY_VERIFICATION_REQUIRED",
                CustomerWorkspaceError.MembershipRequired => "IDENTITY_ACTION_DENIED",
                CustomerWorkspaceError.InvalidInput => "IDENTITY_REQUEST_INVALID",
                _ => "IDENTITY_DEPENDENCY_UNAVAILABLE",
            };
            await ProblemAsync(context, exception.StatusCode, code);
        }
        catch (IdentityActionDeniedException)
        {
            await ProblemAsync(context, 403, "IDENTITY_ACTION_DENIED");
        }
        catch (Exception exception) when (exception is NpgsqlException or DbUpdateException
            || exception is OperationCanceledException && !context.RequestAborted.IsCancellationRequested)
        {
            await ProblemAsync(context, 503, "IDENTITY_DEPENDENCY_UNAVAILABLE");
        }
        finally
        {
            context.Items.Remove(JourneyItem);
            context.Items.Remove(MembershipItem);
            context.Items.Remove(TenantIsolationMiddleware.TenantIdItemKey);
        }
    }

    private static void CheckHeader(HttpContext context, string name, Guid expected)
    {
        if (context.Request.Headers.TryGetValue(name, out var values)
            && (values.Count != 1 || !Guid.TryParse(values[0], out var actual) || actual != expected))
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
    }

    private static bool IsCustomer(ClaimsPrincipal principal)
    {
        if (principal.HasClaim("azp", "waooaw-web") || principal.HasClaim("azp", "waooaw-mobile")
            || principal.HasClaim("idp", "google") || principal.IsInRole("customer")) return true;
        try
        {
            foreach (var claim in principal.FindAll("realm_access"))
            {
                using var realm = JsonDocument.Parse(claim.Value);
                if (realm.RootElement.GetProperty("roles").EnumerateArray().Any(role => role.GetString() == "customer"))
                    return true;
            }
            return false;
        }
        catch (Exception exception) when (exception is JsonException or KeyNotFoundException or InvalidOperationException)
        {
            return true;
        }
    }

    private static Task ProblemAsync(HttpContext context, int status, string code)
    {
        context.Response.StatusCode = status;
        return context.Response.WriteAsJsonAsync(new
        {
            type = "https://waooaw.com/errors/identity/" + code.ToLowerInvariant().Replace('_', '-'),
            title = code, status, code, detail = "The identity operation could not be completed.", correlationId = Guid.NewGuid(),
        }, options: null, contentType: "application/problem+json", cancellationToken: context.RequestAborted);
    }
}