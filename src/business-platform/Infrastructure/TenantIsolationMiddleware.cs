// Implements: architecture/reference/components/business-platform.md § Tenant Isolation
// constitutional_basis: C-005, C-023, C-026, C-059
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.ConstitutionalEngine.Grpc;
using System.Security.Claims;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;

namespace Waooaw.BusinessPlatform.Infrastructure;

/// <summary>
/// TenantIsolationMiddleware — C-005 (Three-Ledger), C-026 (DB-level RLS enforcement).
/// Extracts tenant_id from Keycloak JWT, validates presence, and stores it in
/// HttpContext.Items["TenantId"] for downstream DB interceptors to issue
/// SET LOCAL app.current_tenant_id before every query.
///
/// ADR-003: tenant_id claim is the authoritative multi-tenancy anchor.
/// Never trust user-supplied tenant identity outside the signed JWT.
/// </summary>
public sealed class TenantIsolationMiddleware
{
    // C-026: constitutional constant — the claim name is a protocol boundary, not a magic string.
    private const string TenantIdClaimName = "tenant_id";

    // C-026: the HttpContext.Items key consumed by TenantDbCommandInterceptor.
    public const string TenantIdItemKey = "WaooawTenantId";

    private readonly RequestDelegate _next;
    private readonly ILogger<TenantIsolationMiddleware> _logger;

    public TenantIsolationMiddleware(
        RequestDelegate next,
        ILogger<TenantIsolationMiddleware> logger)
    {
        _next = next ?? throw new ArgumentNullException(nameof(next));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    public async Task InvokeAsync(HttpContext context)
    {
        // Health endpoint and Swagger must pass through without tenant enforcement.
        var path = context.Request.Path.Value ?? string.Empty;
        if (IsAnonymousPath(path))
        {
            await _next(context);
            return;
        }

        // C-026: Authentication must have completed before we reach this middleware.
        // app.UseAuthentication() is declared before app.UseMiddleware<TenantIsolationMiddleware>()
        // in Program.cs — if the JWT is invalid the request is already anonymous here.
        if (context.User?.Identity?.IsAuthenticated != true)
        {
            _logger.LogWarning(
                "TenantIsolationMiddleware: unauthenticated request to {Path} — returning 401",
                path);
            context.Response.StatusCode = StatusCodes.Status401Unauthorized;
            await context.Response.WriteAsJsonAsync(new
            {
                type    = "https://waooaw.com/errors/unauthorized",
                title   = "Authentication required",
                status  = 401,
                detail  = "A valid Keycloak JWT Bearer token is required.",
                traceId = context.TraceIdentifier
            });
            return;
        }

        // C-026 / ADR-003: extract tenant_id from the signed JWT claim set.
        var tenantIdClaim = context.User.FindFirst(TenantIdClaimName)
                         ?? context.User.FindFirst(ClaimTypes.Actor);   // fallback — Keycloak custom claim

        var tenantIdRaw = tenantIdClaim?.Value;

        if (string.IsNullOrWhiteSpace(tenantIdRaw))
        {
            _logger.LogWarning(
                "TenantIsolationMiddleware: authenticated user {Sub} has no '{Claim}' claim — returning 403",
                context.User.FindFirst(ClaimTypes.NameIdentifier)?.Value ?? "<unknown>",
                TenantIdClaimName);

            context.Response.StatusCode = StatusCodes.Status403Forbidden;
            await context.Response.WriteAsJsonAsync(new
            {
                type    = "https://waooaw.com/errors/forbidden",
                title   = "Tenant identity missing",
                status  = 403,
                detail  = $"JWT must contain a '{TenantIdClaimName}' claim. Contact support if this persists.",
                traceId = context.TraceIdentifier
            });
            return;
        }

        // Guard: tenant_id must be a valid UUID (C-026 — never allow injected strings into
        // the PostgreSQL session variable that could escape the SET LOCAL boundary).
        if (!Guid.TryParse(tenantIdRaw, out var tenantId))
        {
            _logger.LogWarning(
                "TenantIsolationMiddleware: tenant_id claim value '{Value}' is not a valid UUID — returning 403",
                tenantIdRaw);

            context.Response.StatusCode = StatusCodes.Status403Forbidden;
            await context.Response.WriteAsJsonAsync(new
            {
                type    = "https://waooaw.com/errors/forbidden",
                title   = "Tenant identity malformed",
                status  = 403,
                detail  = "The 'tenant_id' claim must be a valid UUID.",
                traceId = context.TraceIdentifier
            });
            return;
        }

        // C-026: Store the validated tenant UUID in HttpContext.Items.
        // TenantDbCommandInterceptor reads this and executes:
        //   SET LOCAL app.current_tenant_id = '<guid>'
        // before every EF Core command, ensuring PostgreSQL RLS policy fires.
        context.Items[TenantIdItemKey] = tenantId;

        _logger.LogDebug(
            "TenantIsolationMiddleware: tenant {TenantId} resolved for {Method} {Path}",
            tenantId, context.Request.Method, path);

        await _next(context);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    /// <summary>
    /// Paths that must bypass tenant enforcement (health, Swagger, Razorpay webhook).
    /// ADR-003: Razorpay webhook is authenticated via HMAC signature, not JWT.
    /// </summary>
    private static bool IsAnonymousPath(string path) =>
        path.StartsWith("/health", StringComparison.OrdinalIgnoreCase)        ||
        path.StartsWith("/swagger", StringComparison.OrdinalIgnoreCase)       ||
        path.StartsWith("/api/v1/payments/webhooks/razorpay",
                         StringComparison.OrdinalIgnoreCase);
}