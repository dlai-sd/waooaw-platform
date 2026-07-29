// Implements: architecture/reference/components/business-platform.md § Tenant Isolation
// constitutional_basis: C-005, C-023, C-026, C-059
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

// ── REST + OpenAPI ────────────────────────────────────────────────────────────
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// ── JWT Authentication — Keycloak (ADR-003, C-026) ───────────────────────────
// tenant_id extracted in TenantIsolationMiddleware after token is validated.
// Invalid token → 401. Missing tenant_id claim → 403 (enforced in middleware).
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority = builder.Configuration["Keycloak:Authority"]
            ?? throw new InvalidOperationException(
                "Keycloak:Authority is required (C-026 — tenant isolation cannot function without JWT issuer).");
        options.Audience = builder.Configuration["Keycloak:Audience"] ?? "business-platform";
        options.RequireHttpsMetadata = !builder.Environment.IsDevelopment();

        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer            = true,
            ValidateAudience          = true,
            ValidateLifetime          = true,
            ValidateIssuerSigningKey  = true,
            // Clock skew: tight on purpose — stale tokens violate tenant contract guarantees
            ClockSkew                 = TimeSpan.FromSeconds(30),
        };

        options.Events = new JwtBearerEvents
        {
            OnChallenge = ctx =>
            {
                // Log every rejected token challenge for constitutional audit visibility
                var logger = ctx.HttpContext.RequestServices
                    .GetRequiredService<ILogger<Program>>();
                logger.LogWarning(
                    "JWT challenge fired: {ErrorDescription} — path={Path} (C-026 enforcement)",
                    ctx.ErrorDescription,
                    ctx.Request.Path);
                return Task.CompletedTask;
            },
        };
    });

builder.Services.AddAuthorization();

// ── Tenant Isolation — C-005, C-026, ADR-003 ─────────────────────────────────
// Registers TenantIsolationMiddleware + TenantDbConnectionInterceptor.
// Interceptor sets: SET LOCAL app.current_tenant_id = '{id}' before every DB command
// so PostgreSQL RLS policies automatically scope all queries to the caller's tenant.
builder.Services.AddTenantIsolation();

// ── HttpContextAccessor — required by TenantDbConnectionInterceptor ───────────
builder.Services.AddHttpContextAccessor();

// ─────────────────────────────────────────────────────────────────────────────
var app = builder.Build();

// ── Middleware pipeline (order is constitutional — do NOT reorder) ────────────
//   1. Swagger UI (dev only)
//   2. Routing
//   3. Authentication  ← must precede Authorization (ASP.NET Core requirement)
//   4. Authorization   ← must precede TenantIsolation (tenant id lives in validated JWT)
//   5. TenantIsolation ← extracts tenant_id from validated JWT, sets RLS session var
//   6. Controllers

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseRouting();

// C-026: authentication MUST be validated before any tenant context is extracted.
// An unauthenticated request must never reach TenantIsolationMiddleware with
// a user-supplied x-tenant-id — it would bypass RLS.
app.UseAuthentication();
app.UseAuthorization();

// C-005 / C-026: sets PostgreSQL session variable from JWT tenant_id claim.
// Returns 403 if tenant_id claim is absent from a successfully authenticated token.
app.UseTenantIsolation();

app.MapControllers();

app.Run();