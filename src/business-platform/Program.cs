// Implements: architecture/reference/components/business-platform.md § Tenant Isolation
// constitutional_basis: C-005, C-023, C-026, C-059
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

// ── Controllers + OpenAPI ────────────────────────────────────────────────────
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// ── JWT Authentication — Keycloak (ADR-003, C-026) ───────────────────────────
// tenant_id is sourced exclusively from the validated JWT claim.
// Invalid token → 401. Missing tenant_id claim → 403 (enforced in TenantIsolationMiddleware).
// ⛔ Never hardcode tenant IDs — always read from JWT claim.
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        // Keycloak realm authority — configure via appsettings / env (never hardcode).
        options.Authority = builder.Configuration["Keycloak:Authority"]
            ?? throw new InvalidOperationException(
                "Keycloak:Authority must be configured (C-026: tenant isolation requires a valid issuer).");

        options.Audience = builder.Configuration["Keycloak:Audience"] ?? "business-platform";

        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer            = true,
            ValidateAudience          = true,
            ValidateLifetime          = true,
            ValidateIssuerSigningKey  = true,
            // Keycloak tokens carry tenant_id — reject tokens that lack it (C-026, ADR-003).
            NameClaimType             = "sub",
            RoleClaimType             = "roles",
        };

        // Surface JWT errors as structured log entries (C-059, ERROR HANDLING RULE 1).
        options.Events = new JwtBearerEvents
        {
            OnAuthenticationFailed = ctx =>
            {
                var logger = ctx.HttpContext.RequestServices
                    .GetRequiredService<ILogger<Program>>();
                logger.LogError(
                    ctx.Exception,
                    "JWT authentication failed for request {Method} {Path}: {Message}",
                    ctx.HttpContext.Request.Method,
                    ctx.HttpContext.Request.Path,
                    ctx.Exception.Message);
                return Task.CompletedTask;
            },
            OnForbidden = ctx =>
            {
                var logger = ctx.HttpContext.RequestServices
                    .GetRequiredService<ILogger<Program>>();
                logger.LogWarning(
                    "Forbidden — missing or invalid tenant_id claim. Path: {Path}",
                    ctx.HttpContext.Request.Path);
                return Task.CompletedTask;
            },
        };

        // Development: allow HTTP (non-HTTPS) Keycloak endpoints.
        options.RequireHttpsMetadata = !builder.Environment.IsDevelopment();
    });

builder.Services.AddAuthorization();

// ── Build ────────────────────────────────────────────────────────────────────
var app = builder.Build();

// ── Middleware pipeline (ORDER IS CONSTITUTIONAL — do not reorder) ────────────
// OpenAPI docs
app.UseSwagger();
app.UseSwaggerUI();

// 1. JWT validation — must precede any resource access (ADR-003)
app.UseAuthentication();

// 2. Policy enforcement — must follow authentication
app.UseAuthorization();

// 3. Tenant isolation — extracts tenant_id from validated JWT claim,
//    sets PostgreSQL session variable (SET LOCAL app.current_tenant_id)
//    so every downstream EF Core query is automatically RLS-scoped.
//    Invalid/missing tenant_id → 403 before any DB contact (C-005, C-026).
app.UseTenantIsolation();

// 4. Controllers
app.MapControllers();

app.Run();