// Implements: architecture/reference/components/business-platform.md § Tenant Isolation
// constitutional_basis: C-005, C-023, C-026, C-059
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using System;
using System.Data.Common;
using System.Security.Claims;
using System.Threading;
using System.Threading.Tasks;

namespace Waooaw.BusinessPlatform.Infrastructure;

/// <summary>
/// C-005, C-026: Extracts the tenant_id claim from the validated Keycloak JWT and stores it
/// in HttpContext.Items so that TenantDbConnectionInterceptor can issue
/// SET LOCAL app.current_tenant_id before every PostgreSQL query.
/// Invalid / missing token → 401. Authenticated but missing tenant_id claim → 403.
/// </summary>
public sealed class TenantIsolationMiddleware
{
    /// <summary>HttpContext.Items key used by TenantDbConnectionInterceptor.</summary>
    public const string TenantIdItemKey = "waooaw:tenant_id";

    private const string TenantIdClaimType = "tenant_id";

    private readonly RequestDelegate _next;
    private readonly ILogger<TenantIsolationMiddleware> _logger;

    public TenantIsolationMiddleware(RequestDelegate next, ILogger<TenantIsolationMiddleware> logger)
    {
        _next = next ?? throw new ArgumentNullException(nameof(next));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    public async Task InvokeAsync(HttpContext context)
    {
        // Health endpoint is unauthenticated — pass through without tenant extraction.
        if (context.Request.Path.StartsWithSegments("/health", StringComparison.OrdinalIgnoreCase))
        {
            await _next(context);
            return;
        }

        // Razorpay webhook is authenticated by signature, not by JWT.
        if (context.Request.Path.StartsWithSegments("/api/v1/payments/webhooks/razorpay",
                StringComparison.OrdinalIgnoreCase))
        {
            await _next(context);
            return;
        }

        // Pre-account identity registration paths use a Keycloak pre-account JWT (PreAccountBearerAuth)
        // that carries a `sub` claim but no `tenant_id`. Authentication is enforced by JwtBearer;
        // the tenant_id requirement is deliberately absent per identity-boundary.md §1.7.
        if (context.Request.Path.StartsWithSegments("/api/v1/identity/registrations",
                StringComparison.OrdinalIgnoreCase))
        {
            await _next(context);
            return;
        }

        // C-026: The user must be authenticated before we can extract the tenant claim.
        if (context.User?.Identity is null || !context.User.Identity.IsAuthenticated)
        {
            _logger.LogWarning(
                "TenantIsolation: unauthenticated request to {Path} — returning 401",
                context.Request.Path);

            context.Response.StatusCode = StatusCodes.Status401Unauthorized;
            await context.Response.WriteAsJsonAsync(new
            {
                type    = "https://waooaw.com/errors/unauthorized",
                title   = "Authentication required",
                status  = 401,
                detail  = "A valid Keycloak-issued Bearer token is required.",
                traceId = context.TraceIdentifier
            });
            return;
        }

        // C-005, C-026: Extract tenant_id. Per ADR-003 this claim is mandatory;
        // its absence is treated as a forbidden request, NOT a 500.
        var tenantIdValue = context.User.FindFirstValue(TenantIdClaimType);

        if (string.IsNullOrWhiteSpace(tenantIdValue))
        {
            _logger.LogWarning(
                "TenantIsolation: authenticated user {Subject} has no tenant_id claim — returning 403",
                context.User.FindFirstValue(ClaimTypes.NameIdentifier) ?? "<unknown>");

            context.Response.StatusCode = StatusCodes.Status403Forbidden;
            await context.Response.WriteAsJsonAsync(new
            {
                type    = "https://waooaw.com/errors/missing-tenant-claim",
                title   = "Tenant identity missing",
                status  = 403,
                detail  = "The JWT does not carry the required tenant_id claim. " +
                          "This indicates a Keycloak misconfiguration — contact support.",
                traceId = context.TraceIdentifier
            });
            return;
        }

        // Validate that the value is a well-formed UUID (ADR-003 — tenant_id is an org-uuid).
        if (!Guid.TryParse(tenantIdValue, out var tenantId))
        {
            _logger.LogWarning(
                "TenantIsolation: tenant_id claim '{Value}' is not a valid UUID — returning 403",
                tenantIdValue);

            context.Response.StatusCode = StatusCodes.Status403Forbidden;
            await context.Response.WriteAsJsonAsync(new
            {
                type    = "https://waooaw.com/errors/invalid-tenant-claim",
                title   = "Tenant identity invalid",
                status  = 403,
                detail  = "The tenant_id claim is not a valid UUID.",
                traceId = context.TraceIdentifier
            });
            return;
        }

        // Store the validated, canonical string form of the tenant UUID.
        // TenantDbConnectionInterceptor reads this before every DB command.
        context.Items[TenantIdItemKey] = tenantId.ToString("D");

        _logger.LogDebug(
            "TenantIsolation: tenant {TenantId} resolved for {Method} {Path}",
            tenantId,
            context.Request.Method,
            context.Request.Path);

        await _next(context);
    }
}

/// <summary>
/// C-026: EF Core DbCommandInterceptor that issues
///     SET LOCAL app.current_tenant_id = '{tenant_id}'
/// before every database command, enabling PostgreSQL RLS enforcement.
/// Reads the tenant from IHttpContextAccessor — populated by TenantIsolationMiddleware.
/// </summary>
public sealed class TenantDbConnectionInterceptor : DbCommandInterceptor
{
    private readonly IHttpContextAccessor _httpContextAccessor;
    private readonly ILogger<TenantDbConnectionInterceptor> _logger;

    public TenantDbConnectionInterceptor(
        IHttpContextAccessor httpContextAccessor,
        ILogger<TenantDbConnectionInterceptor> logger)
    {
        _httpContextAccessor = httpContextAccessor ?? throw new ArgumentNullException(nameof(httpContextAccessor));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    // ── Synchronous intercepts ───────────────────────────────────────────────

    public override InterceptionResult<DbDataReader> ReaderExecuting(
        DbCommand command,
        CommandEventData eventData,
        InterceptionResult<DbDataReader> result)
    {
        SetTenantLocal(command);
        return base.ReaderExecuting(command, eventData, result);
    }

    public override InterceptionResult<object?> ScalarExecuting(
        DbCommand command,
        CommandEventData eventData,
        InterceptionResult<object?> result)
    {
        SetTenantLocal(command);
        return base.ScalarExecuting(command, eventData, result);
    }

    public override InterceptionResult<int> NonQueryExecuting(
        DbCommand command,
        CommandEventData eventData,
        InterceptionResult<int> result)
    {
        SetTenantLocal(command);
        return base.NonQueryExecuting(command, eventData, result);
    }

    // ── Asynchronous intercepts ──────────────────────────────────────────────

    public override ValueTask<InterceptionResult<DbDataReader>> ReaderExecutingAsync(
        DbCommand command,
        CommandEventData eventData,
        InterceptionResult<DbDataReader> result,
        CancellationToken cancellationToken = default)
    {
        SetTenantLocal(command);
        return base.ReaderExecutingAsync(command, eventData, result, cancellationToken);
    }

    public override ValueTask<InterceptionResult<object?>> ScalarExecutingAsync(
        DbCommand command,
        CommandEventData eventData,
        InterceptionResult<object?> result,
        CancellationToken cancellationToken = default)
    {
        SetTenantLocal(command);
        return base.ScalarExecutingAsync(command, eventData, result, cancellationToken);
    }

    public override ValueTask<InterceptionResult<int>> NonQueryExecutingAsync(
        DbCommand command,
        CommandEventData eventData,
        InterceptionResult<int> result,
        CancellationToken cancellationToken = default)
    {
        SetTenantLocal(command);
        return base.NonQueryExecutingAsync(command, eventData, result, cancellationToken);
    }

    // ── Private helpers ──────────────────────────────────────────────────────

    /// <summary>
    /// C-026: Prepends SET LOCAL app.current_tenant_id = '...' to the command text
    /// so that PostgreSQL RLS policies evaluate the correct tenant before any data access.
    /// If no tenant is present in context (e.g. health check) the command is left unmodified.
    /// </summary>
    private void SetTenantLocal(DbCommand command)
    {
        var httpContext = _httpContextAccessor.HttpContext;
        if (httpContext is null)
        {
            // Non-HTTP context (migrations, background jobs) — skip RLS injection.
            return;
        }

        if (!httpContext.Items.TryGetValue(TenantIsolationMiddleware.TenantIdItemKey, out var tenantObj)
            || tenantObj is not string tenantId
            || string.IsNullOrWhiteSpace(tenantId))
        {
            // Tenant not resolved — middleware would have already rejected the request
            // for API paths. Background/health paths legitimately have no tenant.
            return;
        }

        // Guard against injection: tenantId is a validated UUID string from TenantIsolationMiddleware.
        // We validated Guid.TryParse upstream so this cannot carry SQL-injection characters.
        var setLocal = $"SET LOCAL app.current_tenant_id = '{tenantId}';";

        // Prepend to the existing command text so it executes in the same statement batch.
        command.CommandText = setLocal + command.CommandText;

        _logger.LogTrace(
            "TenantDbInterceptor: injected SET LOCAL app.current_tenant_id for tenant {TenantId}",
            tenantId);
    }
}

/// <summary>
/// Extension methods to register tenant isolation into the DI container and middleware pipeline.
/// C-005, C-026.
/// </summary>
public static class TenantIsolationMiddlewareExtensions
{
    /// <summary>
    /// Registers IHttpContextAccessor and TenantDbConnectionInterceptor as singletons.
    /// Call from Program.cs before builder.Build().
    /// </summary>
    public static IServiceCollection AddTenantIsolation(this IServiceCollection services)
    {
        services.AddHttpContextAccessor();
        services.AddSingleton<TenantDbConnectionInterceptor>();
        return services;
    }

    /// <summary>
    /// Inserts TenantIsolationMiddleware into the pipeline.
    /// Must be called AFTER UseAuthentication() and UseAuthorization().
    /// </summary>
    public static IApplicationBuilder UseTenantIsolation(this IApplicationBuilder app)
    {
        return app.UseMiddleware<TenantIsolationMiddleware>();
    }
}