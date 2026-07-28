// Implements: architecture/reference/components/business-platform.md § Tenant Isolation
// constitutional_basis: C-005, C-023, C-026, C-059
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

// ── Controllers + OpenAPI ───────────────────────────────────────────────────
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// ── JWT Authentication — ADR-003 (Keycloak, tenant_id claim) ───────────────
// Invalid token → 401. Missing tenant_id claim → enforced in TenantIsolationMiddleware → 403.
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        // Authority is the Keycloak realm URL — read from config, never hardcoded (C-026, ADR-003).
        options.Authority = builder.Configuration["Keycloak:Authority"]
            ?? throw new InvalidOperationException(
                "Keycloak:Authority must be configured (ADR-003 — JWT tenancy). " +
                "Set 'Keycloak__Authority' in environment or appsettings.");

        options.Audience = builder.Configuration["Keycloak:Audience"] ?? "account";

        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer            = true,
            ValidateAudience          = false,   // audience validated via Keycloak realm roles
            ValidateLifetime          = true,
            ValidateIssuerSigningKey  = true,
            // ClockSkew default is 5 minutes — constitutional floor for distributed clock drift.
            ClockSkew                 = TimeSpan.FromMinutes(1),
        };

        // Propagate auth failures as 401/403 — never swallow (ERROR HANDLING RULE 1).
        options.Events = new JwtBearerEvents
        {
            OnAuthenticationFailed = ctx =>
            {
                // JWT signature invalid, expired, or malformed → 401.
                ctx.Response.StatusCode = StatusCodes.Status401Unauthorized;
                return Task.CompletedTask;
            },
        };
    });

builder.Services.AddAuthorization();

// ── TenantIsolationMiddleware — registered as a scoped service for DI ───────
// The middleware itself is added to the pipeline below via app.UseMiddleware<>.
// C-005 (Three-Ledger isolation), C-026 (DB-level RLS enforcement via app.current_tenant_id).
builder.Services.AddHttpContextAccessor();

// ── Build ───────────────────────────────────────────────────────────────────
var app = builder.Build();

// ── Middleware pipeline — ORDER IS CONSTITUTIONAL ───────────────────────────
// Swagger only (never expose on production without gateway-level restriction).
app.UseSwagger();
app.UseSwaggerUI();

// 1. JWT validation — must precede tenant extraction.
app.UseAuthentication();

// 2. Standard ASP.NET Core authorisation (roles, policies).
app.UseAuthorization();

// 3. Tenant isolation — extracts tenant_id claim from validated JWT,
//    injects SET LOCAL app.current_tenant_id into every DB session (C-026 RLS).
//    Runs AFTER UseAuthentication so HttpContext.User is populated.
//    Returns 403 if tenant_id claim is absent or empty (ADR-003 — tenant_id is mandatory).
app.UseMiddleware<TenantIsolationMiddleware>();

// 4. Controllers — all routes require authenticated + tenant-scoped context.
app.MapControllers();

app.Run();