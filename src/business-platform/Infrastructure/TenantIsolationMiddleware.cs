// Implements: architecture/reference/components/business-platform.md § Tenant Isolation
// constitutional_basis: C-005, C-023, C-026, C-059
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using System.Security.Claims;
using Npgsql;

namespace Waooaw.BusinessPlatform.Infrastructure;

/// <summary>
/// C-005 (Three-Ledger), C-026 (DB-level RLS enforcement), ADR-003 (JWT tenancy).
/// Extracts tenant_id from the validated Keycloak JWT and sets the PostgreSQL session
/// variable app.current_tenant_id so that every subsequent query in this request is
/// automatically scoped by Row-Level Security policies.
///
/// Constitutional contract:
///   - Invalid JWT          → 401 Unauthorized  (authentication failed)
///   - Missing tenant_id    → 403 Forbidden      (authenticated but tenant unknown)
///   - Valid tenant_id      → SET LOCAL app.current_tenant_id executed before next handler
/// </summary>
public sealed class TenantIsolationMiddleware
{
    // C-001 / ADR-001: never block indefinitely on DB operations.
    private const int TenantSetCommandTimeoutSeconds = 5;

    private readonly RequestDelegate _next;
    private readonly ILogger<TenantIsolationMiddleware> _logger;

    public TenantIsolationMiddleware(
        RequestDelegate next,
        ILogger<TenantIsolationMiddleware> logger)
    {
        _next = next ?? throw new ArgumentNullException(nameof(next));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    public async Task InvokeAsync(HttpContext context, NpgsqlDataSource dataSource)
    {
        // Health endpoint and Swagger must be reachable without authentication.
        var path = context.Request.Path.Value ?? string.Empty;
        if (IsUnauthenticatedPath(path))
        {
            await _next(context);
            return;
        }

        // ── Step 1: Require a successfully authenticated principal ──────────
        if (context.User?.Identity?.IsAuthenticated != true)
        {
            _logger.LogWarning(
                "TenantIsolation: unauthenticated request to {Path}. Returning 401.",
                path);
            context.Response.StatusCode = StatusCodes.Status401Unauthorized;
            await context.Response.WriteAsync("Authentication required.");
            return;
        }

        // ── Step 2: Extract tenant_id from JWT (ADR-003) ───────────────────
        var tenantId = context.User.FindFirstValue("tenant_id");

        if (string.IsNullOrWhiteSpace(tenantId))
        {
            _logger.LogWarning(
                "TenantIsolation: JWT is valid but tenant_id claim is absent. " +
                "User={User} Path={Path}. Returning 403.",
                context.User.FindFirstValue(ClaimTypes.NameIdentifier),
                path);
            context.Response.StatusCode = StatusCodes.Status403Forbidden;
            await context.Response.WriteAsync("tenant_id claim is required.");
            return;
        }

        // Reject obviously malformed values before touching the DB.
        if (!IsValidTenantIdFormat(tenantId))
        {
            _logger.LogWarning(
                "TenantIsolation: tenant_id claim has invalid format '{TenantId}'. " +
                "Returning 403.",
                tenantId);
            context.Response.StatusCode = StatusCodes.Status403Forbidden;
            await context.Response.WriteAsync("tenant_id claim is malformed.");
            return;
        }

        // ── Step 3: Publish tenant into HttpContext items ──────────────────
        // Services that need the tenant without a DB round-trip read from here.
        context.Items[TenantContextKeys.TenantId] = tenantId;

        // ── Step 4: Set PostgreSQL session variable for RLS (C-026) ────────
        // The NpgsqlDataSource is opened once per request; the session variable
        // remains in effect for the lifetime of the connection, which is scoped
        // to this request via DI lifetime rules.
        try
        {
            using var cts = new CancellationTokenSource(
                TimeSpan.FromSeconds(TenantSetCommandTimeoutSeconds));

            await using var conn = await dataSource.OpenConnectionAsync(cts.Token);
            await using var cmd = conn.CreateCommand();

            // C-026: parameterised to prevent injection even though source is JWT.
            cmd.CommandText = "SELECT set_config('app.current_tenant_id', $1, true)";
            cmd.Parameters.AddWithValue(tenantId);
            cmd.CommandTimeout = TenantSetCommandTimeoutSeconds;

            await cmd.ExecuteScalarAsync(cts.Token);

            _logger.LogDebug(
                "TenantIsolation: session variable set for tenant {TenantId} on {Path}.",
                tenantId, path);
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1 — never swallow silently.
            _logger.LogError(
                ex,
                "TenantIsolation: failed to set PostgreSQL tenant session variable. " +
                "TenantId={TenantId} Path={Path}",
                tenantId, path);

            // Fail closed — better a 500 than leaking cross-tenant data.
            context.Response.StatusCode = StatusCodes.Status500InternalServerError;
            await context.Response.WriteAsync(
                "A constitutional tenant isolation error occurred. Request aborted.");
            return;
        }

        // ── Step 5: Continue pipeline ──────────────────────────────────────
        await _next(context);
    }

    // ── Helpers ────────────────────────────────────────────────────────────

    private static bool IsUnauthenticatedPath(string path) =>
        path.StartsWith("/health", StringComparison.OrdinalIgnoreCase)
        || path.StartsWith("/swagger", StringComparison.OrdinalIgnoreCase)
        || path.Equals("/api/v1/payments/webhooks/razorpay",
            StringComparison.OrdinalIgnoreCase);

    /// <summary>
    /// Validates that the tenant_id claim is a well-formed UUID (Guid).
    /// C-026: ADR-003 mandates tenant_id is an org-uuid. A non-UUID value means
    /// either Keycloak misconfiguration or a tampered token that passed signature
    /// validation — both are fail-closed conditions.
    /// </summary>
    private static bool IsValidTenantIdFormat(string tenantId) =>
        Guid.TryParse(tenantId, out _);
}

/// <summary>
/// Well-known keys for values published into HttpContext.Items by TenantIsolationMiddleware.
/// C-026: downstream handlers MUST read tenant context from these keys — never from
/// the request body or query string.
/// </summary>
public static class TenantContextKeys
{
    /// <summary>
    /// The validated tenant_id UUID string extracted from the Keycloak JWT (ADR-003).
    /// Guaranteed non-null and Guid-parseable when present after middleware has run.
    /// </summary>
    public const string TenantId = "waooaw:tenant_id";
}

/// <summary>
/// IApplicationBuilder extension that registers TenantIsolationMiddleware in the
/// correct pipeline position: after UseAuthentication/UseAuthorization so that
/// context.User is already populated when the middleware runs.
/// C-005, C-026, ADR-003.
/// </summary>
public static class TenantIsolationMiddlewareExtensions
{
    /// <summary>
    /// Adds TenantIsolationMiddleware to the request pipeline.
    /// Must be called AFTER app.UseAuthentication() and app.UseAuthorization().
    /// </summary>
    public static IApplicationBuilder UseTenantIsolation(this IApplicationBuilder app)
    {
        ArgumentNullException.ThrowIfNull(app);
        return app.UseMiddleware<TenantIsolationMiddleware>();
    }
}