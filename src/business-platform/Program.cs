// Implements: architecture/reference/components/business-platform.md § Tenant Isolation
// constitutional_basis: C-005, C-023, C-026, C-059
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

// ── Authentication & JWT (ADR-003, C-026) ─────────────────────────────────────
// JWT issued by Keycloak. tenant_id claim is the authoritative multi-tenancy anchor.
// Invalid/missing JWT → 401. Missing tenant_id claim is handled by TenantIsolationMiddleware → 403.
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        // Authority is the Keycloak realm URL — configured via appsettings.json or env.
        options.Authority = builder.Configuration["Keycloak:Authority"]
            ?? throw new InvalidOperationException(
                "Keycloak:Authority configuration is required. " +
                "Set Keycloak__Authority in environment or appsettings.json.");

        options.Audience = builder.Configuration["Keycloak:Audience"] ?? "business-platform";

        // Keycloak JWKS endpoint provides signing keys — validate signature, issuer, lifetime.
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer           = true,
            ValidateAudience         = true,
            ValidateLifetime         = true,
            ValidateIssuerSigningKey = true,
            // Keycloak uses RS256 signed JWTs — keys retrieved from JWKS endpoint automatically.
            ClockSkew = TimeSpan.FromSeconds(30),
        };

        // C-059 / ERROR HANDLING RULE 1: log JWT validation failures — never swallow silently.
        options.Events = new JwtBearerEvents
        {
            OnAuthenticationFailed = ctx =>
            {
                var logger = ctx.HttpContext.RequestServices
                    .GetRequiredService<ILogger<Program>>();
                logger.LogWarning(
                    ctx.Exception,
                    "JWT authentication failed for {Path} — returning 401. " +
                    "constitutional_basis: ADR-003, C-026",
                    ctx.HttpContext.Request.Path);
                return Task.CompletedTask;
            },
            OnChallenge = ctx =>
            {
                // Keycloak-issued challenge — log at debug, not warning, to avoid noise.
                var logger = ctx.HttpContext.RequestServices
                    .GetRequiredService<ILogger<Program>>();
                logger.LogDebug(
                    "JWT challenge issued for {Path}: {Error}",
                    ctx.HttpContext.Request.Path,
                    ctx.Error ?? "no_token");
                return Task.CompletedTask;
            },
        };
    });

builder.Services.AddAuthorization();

// ── MVC / OpenAPI ─────────────────────────────────────────────────────────────
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// ── Logging (structured, for C-059 error-handling compliance) ─────────────────
builder.Logging.AddConsole();

var app = builder.Build();

// ── Middleware pipeline order — ORDER IS CONSTITUTIONAL (C-005, C-026) ─────────
// 1. OpenAPI UI (dev only — before auth so health/docs are reachable without JWT)
app.UseSwagger();
app.UseSwaggerUI();

// 2. JWT validation — must precede TenantIsolationMiddleware so HttpContext.User is populated.
//    Invalid/expired token → 401 Unauthorized (JwtBearer handles this).
app.UseAuthentication();

// 3. Authorization policy enforcement.
app.UseAuthorization();

// 4. Tenant isolation — reads JWT tenant_id claim, enforces 403 if absent,
//    sets PostgreSQL SET LOCAL app.current_tenant_id for RLS enforcement (C-026, C-005).
//    This MUST run AFTER UseAuthentication so HttpContext.User.Claims is populated.
app.UseTenantIsolation();

// 5. Controllers — all request handling downstream of tenant isolation.
app.MapControllers();

app.Run();