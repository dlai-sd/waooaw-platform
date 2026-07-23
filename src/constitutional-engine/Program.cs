// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-023 (Evidence First), C-027 (append-only ledger), C-029 (scope-boundary record),
//                       ADR-001 (gRPC for Constitutional Engine), ADR-009 (OpenTelemetry)

using Microsoft.EntityFrameworkCore;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Interceptors;
using Waooaw.ConstitutionalEngine.Services;

// ── Builder ───────────────────────────────────────────────────────────────────

var builder = WebApplication.CreateBuilder(args);

// ── gRPC ──────────────────────────────────────────────────────────────────────
// ADR-001: gRPC is the only transport for the Constitutional Engine.
// C-029: TenantMetadataInterceptor enforces tenant isolation on every RPC.
builder.Services.AddGrpc(options =>
{
    options.EnableDetailedErrors = builder.Environment.IsDevelopment();
}).AddServiceOptions<ConstitutionalEngineService>(options =>
{
    // C-073: constitutional obligation — interceptor enforces tenant boundary
    options.Interceptors.Add<TenantMetadataInterceptor>();
});

builder.Services.AddSingleton<TenantMetadataInterceptor>();

// ── Entity Framework Core / PostgreSQL ────────────────────────────────────────
// C-027: append-only ledger — ConstitutionalDbContext is configured for INSERT-only operations.
var connectionString = builder.Configuration.GetConnectionString("Constitutional")
    ?? throw new InvalidOperationException(
        "Connection string 'Constitutional' is required. " +
        "Set ConnectionStrings__Constitutional in environment or appsettings.");

builder.Services.AddDbContext<ConstitutionalDbContext>(options =>
    options.UseNpgsql(connectionString, npgsql =>
    {
        npgsql.EnableRetryOnFailure(maxRetryCount: 3);
        // AD-005: latency budget — command timeout aligned with RecordEvidence 80ms target
        // DESIGN_QUESTION: Should command timeout be per-operation rather than global?
        // A global 5s timeout is safe for scaffold; tighten per-operation in WC012-02.
        npgsql.CommandTimeout(5);
    }));

// ── OpenTelemetry ─────────────────────────────────────────────────────────────
// ADR-009: all services must emit OTel traces.
var otlpEndpoint = builder.Configuration["OpenTelemetry:OtlpEndpoint"]
    ?? "http://localhost:4317";

builder.Services.AddOpenTelemetry()
    .ConfigureResource(resource => resource
        .AddService(
            serviceName: "constitutional-engine",
            serviceVersion: "0.1.0"))
    .WithTracing(tracing => tracing
        .AddAspNetCoreInstrumentation()
        .AddSource("Waooaw.ConstitutionalEngine")
        .AddOtlpExporter(otlp =>
        {
            otlp.Endpoint = new Uri(otlpEndpoint);
        }));

// ── Logging ───────────────────────────────────────────────────────────────────
builder.Logging.ClearProviders();
builder.Logging.AddConsole();

// ── Application ───────────────────────────────────────────────────────────────

var app = builder.Build();

// Health probe — internal only, not exposed externally
app.MapGet("/healthz", () => Results.Ok(new { status = "healthy", service = "constitutional-engine" }));

// ADR-001: map the gRPC service — this is the only external-facing endpoint (internal network only)
app.MapGrpcService<ConstitutionalEngineService>();

app.Run();

// Expose Program for integration test WebApplicationFactory
public partial class Program { }