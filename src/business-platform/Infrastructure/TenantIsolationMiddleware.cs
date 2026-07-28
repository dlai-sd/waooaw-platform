// Implements: architecture/reference/components/business-platform.md § Tenant Isolation
// constitutional_basis: C-005, C-023, C-026, C-059
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;
using System.Security.Claims;

namespace Waooaw.BusinessPlatform.Infrastructure;

/// <summary>
/// Constitutional basis: C-005 (Three-Ledger — tenants never share data),
/// C-026 (DB-level RLS enforcement), ADR-003 (JWT Claims Multi-Tenancy).
/// Purpose: Extracts tenant_id from Keycloak-issued JWT and sets PostgreSQL
/// session variable app.current_tenant_id so every subsequent DB query is
/// automatically RLS-scoped to the authenticated tenant.
/// </summary>
public sealed class TenantIsolationMiddleware
{
    // C-026: PostgreSQL RLS session variable name (must match migration policy definition)
    private const string PostgresTenantVariable = "app.current_tenant_id";

    // ADR-003: canonical JWT claim name for tenant identity
    private const string TenantIdClaimName = "tenant_id";

    private readonly RequestDelegate _next;
    private readonly ILogger<TenantIsolationMiddleware> _logger;

    // Paths that are exempt from tenant isolation (health check, unauthenticated webhooks)
    private static readonly HashSet<string> ExemptPaths = new(StringComparer.OrdinalIgnoreCase)
    {
        "/health",
        "/api/v1/payments/webhooks/razorpay"
    };

    public TenantIsolationMiddleware(RequestDelegate next, ILogger<TenantIsolationMiddleware> logger)
    {
        _next = next ?? throw new ArgumentNullException(nameof(next));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    public async Task InvokeAsync(HttpContext context, IDbContextTenantSetter tenantSetter)
    {
        var path = context.Request.Path.Value ?? string.Empty;

        // Exempt paths bypass tenant isolation (e.g. health, Razorpay webhook — ADR-003)
        if (ExemptPaths.Contains(path))
        {
            await _next(context);
            return;
        }

        // C-026: JWT must be authenticated before we trust any claim
        if (context.User?.Identity?.IsAuthenticated != true)
        {
            _logger.LogWarning(
                "TenantIsolation: Unauthenticated request to {Path} — returning 401",
                path);
            context.Response.StatusCode = StatusCodes.Status401Unauthorized;
            return;
        }

        // ADR-003: tenant_id is the multi-tenancy anchor — must never be taken from request body
        var tenantId = context.User.FindFirstValue(TenantIdClaimName);

        if (string.IsNullOrWhiteSpace(tenantId))
        {
            _logger.LogWarning(
                "TenantIsolation: JWT is valid but missing '{Claim}' claim for path {Path} — returning 403",
                TenantIdClaimName, path);
            context.Response.StatusCode = StatusCodes.Status403Forbidden;
            return;
        }

        // C-026: validate that tenant_id is a well-formed GUID before injecting into SQL
        if (!Guid.TryParse(tenantId, out var tenantGuid))
        {
            _logger.LogWarning(
                "TenantIsolation: '{Claim}' value '{Value}' is not a valid UUID — returning 403",
                TenantIdClaimName, tenantId);
            context.Response.StatusCode = StatusCodes.Status403Forbidden;
            return;
        }

        // Propagate tenant identity through the request scope so EF Core interceptor
        // can execute SET LOCAL app.current_tenant_id = '...' before every query.
        // C-005: This is the single enforcement point — all downstream DB access is RLS-scoped.
        try
        {
            await tenantSetter.SetTenantAsync(tenantGuid, context.RequestAborted);
        }
        catch (OperationCanceledException)
        {
            // Request was cancelled — do not log as error
            return;
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1: never swallow — log before returning
            _logger.LogError(
                ex,
                "TenantIsolation: Failed to set tenant context for tenant {TenantId} on path {Path}",
                tenantGuid, path);
            context.Response.StatusCode = StatusCodes.Status500InternalServerError;
            return;
        }

        // Attach tenant_id to HttpContext.Items so controllers and services can read it
        // without re-parsing the JWT (C-026 — single source of truth is the JWT claim)
        context.Items[TenantIdClaimName] = tenantGuid;

        _logger.LogDebug(
            "TenantIsolation: Tenant {TenantId} resolved for {Method} {Path}",
            tenantGuid, context.Request.Method, path);

        await _next(context);
    }
}

/// <summary>
/// Contract for setting the PostgreSQL session-level tenant variable.
/// C-026: Implemented by EF Core interceptor (registered in DI) so that every
/// connection obtained from the pool runs SET LOCAL app.current_tenant_id before
/// any query executes. Interface lives here to avoid circular dependencies.
/// </summary>
public interface IDbContextTenantSetter
{
    /// <summary>
    /// Sets the PostgreSQL session variable app.current_tenant_id = tenantId
    /// for all DB connections obtained during this HTTP request scope.
    /// Must be called before any EF Core query executes (C-026).
    /// </summary>
    Task SetTenantAsync(Guid tenantId, CancellationToken cancellationToken = default);
}

/// <summary>
/// Scoped service that carries the resolved tenant identity across the DI scope.
/// C-026, ADR-003: populated by TenantIsolationMiddleware, consumed by
/// TenantDbConnectionInterceptor before every EF Core query.
/// </summary>
public sealed class TenantContext
{
    private Guid? _tenantId;

    /// <summary>
    /// The authoritative tenant GUID for the current HTTP request.
    /// ADR-003: always sourced from JWT claim — never from request body.
    /// </summary>
    public Guid TenantId
    {
        get => _tenantId ?? throw new InvalidOperationException(
            "TenantContext.TenantId accessed before TenantIsolationMiddleware resolved the tenant. " +
            "Ensure app.UseMiddleware<TenantIsolationMiddleware>() is registered before app.MapControllers().");
        private set => _tenantId = value;
    }

    public bool IsResolved => _tenantId.HasValue;

    /// <summary>
    /// Called once per request by TenantIsolationMiddleware. C-026 invariant:
    /// must be called exactly once, before any DB operation.
    /// </summary>
    internal void Resolve(Guid tenantId)
    {
        if (_tenantId.HasValue)
            throw new InvalidOperationException("TenantContext.Resolve called more than once in the same request scope.");

        TenantId = tenantId;
    }
}

/// <summary>
/// EF Core connection interceptor that executes SET LOCAL app.current_tenant_id
/// before every database command. C-026: PostgreSQL RLS depends on this variable
/// being set on the session before any tenant-scoped query executes.
/// </summary>
public sealed class TenantDbConnectionInterceptor
    : Microsoft.EntityFrameworkCore.Diagnostics.DbConnectionInterceptor
{
    private readonly TenantContext _tenantContext;
    private readonly ILogger<TenantDbConnectionInterceptor> _logger;

    public TenantDbConnectionInterceptor(
        TenantContext tenantContext,
        ILogger<TenantDbConnectionInterceptor> logger)
    {
        _tenantContext = tenantContext;
        _logger = logger;
    }

    public override async Task ConnectionOpenedAsync(
        System.Data.Common.DbConnection connection,
        Microsoft.EntityFrameworkCore.Diagnostics.ConnectionEndEventData eventData,
        CancellationToken cancellationToken = default)
    {
        if (!_tenantContext.IsResolved)
        {
            // Exempt paths (health, webhook) open connections without a tenant — skip RLS injection
            await base.ConnectionOpenedAsync(connection, eventData, cancellationToken);
            return;
        }

        // C-026: SET LOCAL scopes the variable to the current transaction/command;
        // if the connection is reused from the pool, the previous tenant variable is cleared.
        var tenantId = _tenantContext.TenantId.ToString();

        try
        {
            using var cmd = connection.CreateCommand();
            // ERROR HANDLING RULE 4: timeout on external DB call
            cmd.CommandTimeout = 5;
            cmd.CommandText = $"SET LOCAL app.current_tenant_id = '{tenantId}'";
            await cmd.ExecuteNonQueryAsync(cancellationToken);

            _logger.LogDebug(
                "TenantDbConnectionInterceptor: SET LOCAL app.current_tenant_id = {TenantId}",
                tenantId);
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1: log before rethrowing — never swallow
            _logger.LogError(
                ex,
                "TenantDbConnectionInterceptor: Failed to set PostgreSQL tenant variable for tenant {TenantId}",
                tenantId);
            throw;
        }

        await base.ConnectionOpenedAsync(connection, eventData, cancellationToken);
    }
}

/// <summary>
/// Default implementation of IDbContextTenantSetter.
/// Resolves the scoped TenantContext so the interceptor knows which tenant to inject.
/// </summary>
public sealed class TenantContextSetter : IDbContextTenantSetter
{
    private readonly TenantContext _tenantContext;

    public TenantContextSetter(TenantContext tenantContext)
    {
        _tenantContext = tenantContext;
    }

    public Task SetTenantAsync(Guid tenantId, CancellationToken cancellationToken = default)
    {
        _tenantContext.Resolve(tenantId);
        return Task.CompletedTask;
    }
}

/// <summary>
/// Extension methods to register tenant isolation services and middleware.
/// C-026, ADR-003: centralises registration so Program.cs stays concise.
/// </summary>
public static class TenantIsolationServiceExtensions
{
    /// <summary>
    /// Registers TenantContext (scoped), IDbContextTenantSetter, and
    /// TenantDbConnectionInterceptor into the DI container.
    /// C-026: must be called before AddDbContext / AddDbContextFactory.
    /// </summary>
    public static IServiceCollection AddTenantIsolation(this IServiceCollection services)
    {
        services.AddScoped<TenantContext>();
        services.AddScoped<IDbContextTenantSetter, TenantContextSetter>();
        services.AddScoped<TenantDbConnectionInterceptor>();
        return services;
    }

    /// <summary>
    /// Registers the TenantIsolationMiddleware into the ASP.NET Core pipeline.
    /// MUST be called after app.UseAuthentication() and app.UseAuthorization()
    /// so that context.User is populated before the middleware reads claims. (ADR-003)
    /// </summary>
    public static IApplicationBuilder UseTenantIsolation(this IApplicationBuilder app)
    {
        return app.UseMiddleware<TenantIsolationMiddleware>();
    }
}