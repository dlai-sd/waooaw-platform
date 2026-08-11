// Implements: architecture/reference/components/business-platform.md § Tenant Isolation
// constitutional_basis: C-005, C-023, C-026, C-059
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Workflows;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using Temporalio.Extensions.Hosting;

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

builder.Services.AddAuthorization(options =>
{
    options.AddPolicy("InternalService", policy =>
        policy.RequireClaim("client_type", "service"));
});

// ── Tenant Isolation — C-005, C-026, ADR-003 ─────────────────────────────────
// Registers TenantIsolationMiddleware + TenantDbConnectionInterceptor.
// Interceptor sets: SET LOCAL app.current_tenant_id = '{id}' before every DB command
// so PostgreSQL RLS policies automatically scope all queries to the caller's tenant.
builder.Services.AddTenantIsolation();

// ── HttpContextAccessor — required by TenantDbConnectionInterceptor ──────────────
builder.Services.AddHttpContextAccessor();
builder.Services.AddSingleton<IProfessionalCatalog, ProfessionalCatalog>();

var workloadCredentials = builder.Configuration["WAOOAW_WORKLOAD_CREDENTIALS"];
var prWorkspaceBaseUrl = builder.Configuration["ProfessionalRuntime:RelationshipWorkspaceBaseUrl"];
var wbeWorkspaceBaseUrl = builder.Configuration["BillingEngine:RelationshipWorkspaceBaseUrl"];
if (!string.IsNullOrWhiteSpace(workloadCredentials)
    && Uri.TryCreate(prWorkspaceBaseUrl, UriKind.Absolute, out var prWorkspaceUri)
    && Uri.TryCreate(wbeWorkspaceBaseUrl, UriKind.Absolute, out var wbeWorkspaceUri))
{
    var workloadIdentity = WorkloadIdentityClient.Load(workloadCredentials);
    builder.Services.AddSingleton(workloadIdentity);
    builder.Services.AddSingleton<IRelationshipWorkspaceOwnerGateway>(
        new AuthenticatedRelationshipWorkspaceOwnerGateway(workloadIdentity, prWorkspaceUri, wbeWorkspaceUri));
}
else
{
    builder.Services.AddSingleton<IRelationshipWorkspaceOwnerGateway, UnconfiguredRelationshipWorkspaceOwnerGateway>();
}

// ── WBE (billing-engine) HttpClient — used by SubscriptionsController + Temporal activities ──
var wbeBaseUrl = builder.Configuration["BillingEngine:BaseUrl"] ?? "http://billing-engine:8140";
builder.Services.AddHttpClient("WBE", client =>
{
    client.BaseAddress = new Uri(wbeBaseUrl);
    client.Timeout     = TimeSpan.FromSeconds(30);
});

// ── Temporal worker — trial expiry saga (ADR-015, conditional on config) ─────
// Worker is skipped when Temporal:Host is not configured (e.g., in unit tests).
var temporalHost = builder.Configuration["Temporal:Host"];
if (!string.IsNullOrWhiteSpace(temporalHost))
{
    builder.Services.AddTemporalClient(opts => opts.TargetHost = temporalHost);
    builder.Services.AddSingleton<TrialExpiryActivities>();
    builder.Services.AddHostedTemporalWorker("bp-trial-worker")
        .AddWorkflow<TrialExpiryWorkflow>()
        .AddSingletonActivities<TrialExpiryActivities>();
}

// ── Payload Store DbContext — DPDPA Right-to-Erasure (ADR-044) ───────────────
var payloadStoreConn = builder.Configuration.GetConnectionString("PayloadStore")
    ?? builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_bp;Username=bp_app;";
builder.Services.AddDbContextFactory<Waooaw.BusinessPlatform.Infrastructure.PayloadStoreDbContext>(opts =>
    opts.UseNpgsql(payloadStoreConn));

// ── Provider Registry DbContext — runtime provider routing table (ADR-042) ───
var providerRegistryConn = builder.Configuration.GetConnectionString("ProviderRegistry")
    ?? builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_bp;Username=bp_app;";
builder.Services.AddDbContextFactory<Waooaw.BusinessPlatform.Infrastructure.ProviderRegistryDbContext>(opts =>
    opts.UseNpgsql(providerRegistryConn));

// ── Skill Catalog DbContext — ADR-043 §2 ─────────────────────────────────────
var skillCatalogConn = builder.Configuration.GetConnectionString("SkillCatalog")
    ?? builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_bp;Username=bp_app;";
builder.Services.AddDbContextFactory<Waooaw.BusinessPlatform.Infrastructure.SkillCatalogDbContext>(opts =>
    opts.UseNpgsql(skillCatalogConn));

// ── Employment Relationship aggregate — GOAL-005 D-03 / WC-057 ────────────
var employmentRelationshipConn = builder.Configuration.GetConnectionString("EmploymentRelationship")
    ?? builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_bp;Username=business_app;";
builder.Services.AddDbContextFactory<EmploymentRelationshipDbContext>((services, options) =>
    options
        .UseNpgsql(employmentRelationshipConn)
        .AddInterceptors(services.GetRequiredService<TenantDbConnectionInterceptor>()));
builder.Services.AddScoped<IRelationshipConstitutionalGateway, RelationshipConstitutionalGateway>();
builder.Services.AddScoped<EmploymentRelationshipService>();

// ── Identity Boundary — WC-034 F2 (identity-boundary.md) ─────────────────
// Pre-account registration paths use actor subject (JWT sub); no tenant_id required.
// Account-link and mobile-verification paths require full tenant JWT.
var identityConn = builder.Configuration.GetConnectionString("Identity")
    ?? builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_bp;Username=business_app;";
builder.Services.AddDbContextFactory<Waooaw.BusinessPlatform.Infrastructure.IdentityDbContext>((services, options) =>
    options
        .UseNpgsql(identityConn)
        .AddInterceptors(services.GetRequiredService<TenantDbConnectionInterceptor>()));
builder.Services.Configure<Waooaw.BusinessPlatform.Services.IdentityHmacOptions>(
    builder.Configuration.GetSection("Identity:Hmac"));
builder.Services.AddSingleton<Waooaw.BusinessPlatform.Services.IIdentityVerificationDispatcher,
    Waooaw.BusinessPlatform.Services.UnconfiguredVerificationDispatcher>();
builder.Services.AddScoped<Waooaw.BusinessPlatform.Services.IdentityService>();

// ── Conversation Core — WC-034 F3 ───────────────────────────────────────────
var conversationConn = builder.Configuration.GetConnectionString("Conversation")
    ?? builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_bp;Username=business_app;";
builder.Services.AddDbContextFactory<ConversationStoreDbContext>((services, options) =>
    options
        .UseNpgsql(conversationConn)
        .AddInterceptors(services.GetRequiredService<TenantDbConnectionInterceptor>()));
builder.Services.Configure<ConversationCursorOptions>(
    builder.Configuration.GetSection("Conversation:Cursor"));
builder.Services.AddSingleton<ConversationCursorCodec>();
builder.Services.AddSingleton<IConversationExecutionGateway, UnconfiguredConversationExecutionGateway>();
builder.Services.AddScoped<ConversationService>();

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

// Required for WebApplicationFactory in tests (CCT-MT-01)
public partial class Program { }