using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Waooaw.BusinessPlatform.Infrastructure;

var builder = WebApplication.CreateBuilder(args);

// ─── API ─────────────────────────────────────────────────────────────────────
builder.Services.AddControllers();
builder.Services.AddHealthChecks()
    .AddNpgsql(builder.Configuration.GetConnectionString("DefaultConnection")!);

// ─── JWT Authentication (ADR-008, security-architecture.md §2) ────────────────
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority = builder.Configuration["Keycloak:Authority"];
        options.Audience = builder.Configuration["Keycloak:Audience"];
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            // Algorithm enforcement — prevent JWT confusion attacks (security-architecture.md)
            ValidAlgorithms = ["RS256"]
        };
    });
builder.Services.AddAuthorization();

// ─── gRPC client for Constitutional Engine (ADR-001) ──────────────────────────
builder.Services.AddGrpcClient<Constitutional.V1.ConstitutionalService.ConstitutionalServiceClient>(
    options => options.Address = new Uri(
        builder.Configuration["ConstitutionalEngine:Address"] ?? "http://constitutional-engine:5002"));

// ─── Database (EF Core + PostgreSQL) ─────────────────────────────────────────
builder.Services.AddDbContext<BusinessDbContext>(opts =>
    opts.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection"),
        npgsql => npgsql.MigrationsHistoryTable("__EFMigrationsHistory", "business")));

// ─── Tenant isolation interceptor (security-architecture.md §2, engineering-standards §10) ──
builder.Services.AddHttpContextAccessor();
builder.Services.AddSingleton<TenantDbCommandInterceptor>();

// ─── Observability (ADR-009) ──────────────────────────────────────────────────
builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("business-platform"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddEntityFrameworkCoreInstrumentation()
        .AddGrpcClientInstrumentation()
        .AddOtlpExporter(o => o.Endpoint = new Uri(
            builder.Configuration["OTLP_ENDPOINT"] ?? "http://jaeger:4317")));

var app = builder.Build();

// ─── Middleware pipeline (JWT before tenant extraction) ───────────────────────
app.UseAuthentication();
app.UseAuthorization();

// Tenant ID extraction middleware — after JWT validation, before controllers
// Sets HttpContext.Items["tenant_id"] from JWT claim (security-architecture.md §2)
app.Use(async (context, next) =>
{
    var tenantClaim = context.User.FindFirst("tenant_id");
    if (tenantClaim != null)
        context.Items["tenant_id"] = tenantClaim.Value;
    await next();
});

app.MapControllers();
app.MapHealthChecks("/health");

app.Run();
