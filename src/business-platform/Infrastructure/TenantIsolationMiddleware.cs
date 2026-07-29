// Implements: architecture/reference/components/business-platform.md § Tenant Isolation
// constitutional_basis: C-005, C-023, C-026, C-059
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.ConstitutionalEngine.Grpc;
using System.Security.Claims;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;

namespace Waooaw.BusinessPlatform.Infrastructure;

/// <summary>
/// Constitutional basis: C-005 (Three-Ledger — tenants never share data),
/// C-026 (DB-level RLS enforcement), C-059 (Implementation Traceability).
///
/// Extracts the `tenant_id` claim from the Keycloak-issued JWT and stores it
/// in HttpContext.Items so that EF Core interceptors can issue
/// SET LOCAL app.current_tenant_id before every query (RLS enforcement).
///
/// Pipeline position: MUST run AFTER UseAuthentication() / UseAuthorization().
/// Invalid or missing token  → 401 Unauthorized.
/// Authenticated but missing tenant_id claim → 403 Forbidden.
/// </summary>
public sealed class TenantIsolationMiddleware
{
    // C-026: The PostgreSQL session variable name that triggers RLS policies.
    internal const string PostgresTenantVariable = "app.current_tenant_id";

    // HttpContext.Items key consumed by TenantDbConnectionInterceptor.
    public const string TenantIdItemKey = "X-Tenant-Id";

    private readonly RequestDelegate _next;
    private readonly ILogger<TenantIsolationMiddleware> _logger;

    public TenantIsolationMiddleware(RequestDelegate next, ILogger<TenantIsolationMiddleware> logger)
    {
        _next = next ?? throw new ArgumentNullException(nameof(next));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    public async Task InvokeAsync(HttpContext context)
    {
        // Skip middleware for unauthenticated paths (e.g. /health, Swagger UI).
        // Authentication middleware has already run; if the endpoint allows anonymous
        // access the user identity will be unauthenticated.
        if (context.User.Identity is not { IsAuthenticated: true })
        {
            // Not authenticated — let the Authorization middleware return 401 for
            // protected resources. Pass through for explicitly anonymous endpoints.
            await _next(context);
            return;
        }

        // C-026 / ADR-003: tenant_id is the authoritative multi-tenancy anchor.
        // It is extracted from the JWT claim — never from the request body or query string.
        var tenantId = context.User.FindFirstValue("tenant_id");

        if (string.IsNullOrWhiteSpace(tenantId))
        {
            // Authenticated user, but Keycloak did not embed tenant_id.
            // ADR-003: this is a Keycloak misconfiguration and is a fail-safe condition.
            _logger.LogWarning(
                "C-026 violation: authenticated user {Sub} has no tenant_id claim. Returning 403. Path={Path}",
                context.User.FindFirstValue(ClaimTypes.NameIdentifier) ?? "unknown",
                context.Request.Path);

            context.Response.StatusCode = StatusCodes.Status403Forbidden;
            context.Response.ContentType = "application/problem+json";
            await context.Response.WriteAsync(
                """{"type":"https://waooaw.com/problems/missing-tenant","title":"Missing tenant_id claim","status":403}""",
                context.RequestAborted);
            return;
        }

        // Validate that the claim is a well-formed GUID to prevent SQL injection
        // via the session variable (defence-in-depth: RLS also validates, but we
        // reject early here per C-026 implementation standards).
        if (!Guid.TryParse(tenantId, out var tenantGuid))
        {
            _logger.LogWarning(
                "C-026 violation: tenant_id claim '{TenantId}' is not a valid GUID for user {Sub}. Returning 403.",
                tenantId,
                context.User.FindFirstValue(ClaimTypes.NameIdentifier) ?? "unknown");

            context.Response.StatusCode = StatusCodes.Status403Forbidden;
            context.Response.ContentType = "application/problem+json";
            await context.Response.WriteAsync(
                """{"type":"https://waooaw.com/problems/invalid-tenant","title":"Invalid tenant_id format","status":403}""",
                context.RequestAborted);
            return;
        }

        // Store the canonical string representation (lowercase, hyphenated) so all
        // downstream interceptors use the same format when building the SET LOCAL statement.
        var canonicalTenantId = tenantGuid.ToString("D");

        // C-026: expose tenant identity to EF Core interceptor and any service
        // that needs to forward x-tenant-id over gRPC metadata.
        context.Items[TenantIdItemKey] = canonicalTenantId;

        _logger.LogDebug(
            "TenantIsolationMiddleware: tenant={TenantId} attached to request {Method} {Path}",
            canonicalTenantId,
            context.Request.Method,
            context.Request.Path);

        await _next(context);
    }
}

/// <summary>
/// Extension method — registers TenantIsolationMiddleware in the ASP.NET Core pipeline.
/// MUST be called AFTER app.UseAuthentication() and app.UseAuthorization().
/// Constitutional basis: C-026, ADR-003.
/// </summary>
public static class TenantIsolationMiddlewareExtensions
{
    public static IApplicationBuilder UseTenantIsolation(this IApplicationBuilder app)
        => app.UseMiddleware<TenantIsolationMiddleware>();
}