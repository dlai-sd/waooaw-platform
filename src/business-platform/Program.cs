// Implements: architecture/reference/components/business-platform.md § Tenant Isolation
// constitutional_basis: C-005, C-023, C-026, C-059
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.ConstitutionalEngine.Grpc;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// JWT Bearer authentication — Keycloak (ADR-003, C-026)
// The tenant_id claim extracted here is the sole authoritative tenant anchor.
// It propagates: JWT → TenantIsolationMiddleware → PostgreSQL SET LOCAL app.current_tenant_id
// Invalid/missing JWT → 401. Missing tenant_id claim → 403 (enforced in TenantIsolationMiddleware).
// ⛔ Never trust a tenant_id from the request body — always read from the validated JWT claim.
builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        // Authority and Audience sourced from configuration — never hardcoded (C-026, ADR-003)
        options.Authority = builder.Configuration["Keycloak:Authority"];
        options.Audience = builder.Configuration["Keycloak:Audience"];

        // Require HTTPS in non-development environments (security hardening)
        options.RequireHttpsMetadata = !builder.Environment.IsDevelopment();

        options.TokenValidationParameters = new Microsoft.IdentityModel.Tokens.TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            // Require the tenant_id claim to be present — absence produces 403 downstream
            // (validated in TenantIsolationMiddleware.InvokeAsync, not here)
        };
    });

builder.Services.AddAuthorization();

// Register tenant isolation services — C-005 (Three-Ledger isolation), C-026 (DB-level RLS)
// Registers: TenantContext (scoped), TenantDbConnectionInterceptor (scoped),
//            IDbContextTenantSetter implementation (scoped)
builder.Services.AddTenantIsolation();

var app = builder.Build();

app.UseSwagger();
app.UseSwaggerUI();

// ─── Middleware pipeline — ORDER IS CONSTITUTIONAL (C-026, ADR-003) ─────────────────────────────
//
//   1. UseAuthentication  → validates JWT, populates HttpContext.User (Keycloak-signed claims)
//   2. UseAuthorization   → enforces [Authorize] policy gates
//   3. UseTenantIsolation → reads User.FindFirst("tenant_id") from the VALIDATED principal,
//                           writes SET LOCAL app.current_tenant_id = '{id}' before any EF query
//
// Reversing steps 1 and 3 would allow unauthenticated callers to inject a tenant_id.
// ────────────────────────────────────────────────────────────────────────────────────────────────
app.UseAuthentication();
app.UseAuthorization();

// Tenant isolation middleware — C-005, C-026
// Extracts tenant_id from the already-validated JWT principal.
// Missing tenant_id claim → responds 403 Forbidden before reaching any controller.
// Sets PostgreSQL session variable so all EF Core queries are automatically RLS-scoped.
app.UseTenantIsolation();

app.MapControllers();
app.Run();