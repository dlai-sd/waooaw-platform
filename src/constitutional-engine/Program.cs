// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-023 (Evidence First), C-027 (append-only ledger), C-029 (scope-boundary record),
//                       ADR-001 (gRPC for Constitutional Engine), ADR-009 (OpenTelemetry)

using Microsoft.EntityFrameworkCore;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Infrastructure;
using Waooaw.ConstitutionalEngine.Services;

// ─── Builder ─────────────────────────────────────────────────────────────────

var builder = WebApplication.CreateBuilder(args);

// ─── gRPC ─────────────────────────────────────────────────────────────────────
// ADR-001: Constitutional Engine communicates exclusively via gRPC.
// INTERNAL ONLY — never exposed to the internet.
builder.Services.AddGrpc(options =>
{
    options.EnableDetailedErrors = builder.Environment.IsDevelopment();
});

// ─── Database ─────────────────────────────────────────────────────────────────
// C-027: Append-only ledger — EF Core is configured for PostgreSQL.
// Connection string key: "ConstitutionalDb"
var connectionString = builder.Configuration.GetConnectionString("ConstitutionalDb")
    ?? throw new InvalidOperationException(
        "Connection string 'ConstitutionalDb' is not configured. " +
        "This is required for the Constitutional Audit Ledger (C-027).");

builder.Services.AddDbContext<ConstitutionalDbContext>(options =>
    options.UseNpgsql(connectionString, npgsql =>
    {
        // Command timeout aligned with the most constrained latency budget:
        // TriggerEmergencyStop target <100ms (AD-001). Set to 5s to allow for
        // transient load while still failing fast relative to connection timeouts.
        npgsql.CommandTimeout(5);
    }));

// ─── Infrastructure ───────────────────────────────────────────────────────────
// C-029: Tenant metadata extractor — enforces scope-boundary on every RPC call.
builder.Services.AddSingleton<ITenantMetadataExtractor, TenantMetadataExtractor>();

// ─── OpenTelemetry ────────────────────────────────────────────────────────────
// ADR-009: All services emit OTel traces. Exporter: OpenTelemetryProtocol (OTLP).
// NOTE: Package is 'OpenTelemetry.Exporter.OpenTelemetryProtocol' — NOT 'Otlp'.
var otlpEndpoint = builder.Configuration["OpenTelemetry:OtlpEndpoint"]
    ?? "http://localhost:4317";

builder.Services.AddOpenTelemetry()
    .ConfigureResource(resource => resource
        .AddService(
            serviceName: "constitutional-engine",
            serviceVersion: "1.0.0"))
    .WithTracing(tracing => tracing
        .AddSource("Waooaw.ConstitutionalEngine")
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter(otlp =>
        {
            otlp.Endpoint = new Uri(otlpEndpoint);
        }));

// ─── Logging ──────────────────────────────────────────────────────────────────
builder.Logging.ClearProviders();
builder.Logging.AddConsole();

// ─── Application ─────────────────────────────────────────────────────────────

var app = builder.Build();

// gRPC requires HTTP/2. Kestrel is configured via appsettings / environment.
// Port 5002 is the internal gRPC port (constitutional-engine.md).
app.MapGrpcService<ConstitutionalEngineService>();

// Health check endpoint — used by Kubernetes liveness/readiness probes.
// DESIGN_QUESTION: Should this be a gRPC health check (Grpc.HealthCheck) or
// a plain HTTP endpoint? Kubernetes gRPC health probes require grpc-health-probe.
// Recommend gRPC health check for consistency — awaiting EA confirmation.
app.MapGet("/healthz", () => Results.Ok(new { status = "healthy", service = "constitutional-engine" }));

app.Run();

// Make Program accessible to integration test projects (C-076).
public partial class Program { }