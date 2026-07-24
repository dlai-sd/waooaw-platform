// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: ADR-001 (gRPC), ADR-009 (OpenTelemetry), C-059 (Traceability),
//                       C-023 (Evidence First), C-027 (append-only ledger)

using Microsoft.EntityFrameworkCore;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Services;

// ─── BUILDER ────────────────────────────────────────────────────────────────

var builder = WebApplication.CreateBuilder(args);

// ─── LOGGING ────────────────────────────────────────────────────────────────

builder.Logging.ClearProviders();
builder.Logging.AddConsole();

// ─── gRPC ───────────────────────────────────────────────────────────────────

// ADR-001: gRPC is the only transport for Constitutional Engine
builder.Services.AddGrpc(options =>
{
    options.EnableDetailedErrors = builder.Environment.IsDevelopment();
});

// ─── DATABASE ───────────────────────────────────────────────────────────────

// C-027: append-only ledger — EF Core configured for PostgreSQL
var connectionString = builder.Configuration.GetConnectionString("Constitutional")
    ?? throw new InvalidOperationException(
        "Connection string 'Constitutional' is required. " +
        "Set ConnectionStrings__Constitutional in environment or appsettings.");

builder.Services.AddDbContext<ConstitutionalDbContext>(options =>
{
    options.UseNpgsql(connectionString, npgsql =>
    {
        npgsql.CommandTimeout(5); // 5s hard timeout — latency budget enforcement (AD-005)
        npgsql.EnableRetryOnFailure(
            maxRetryCount: 3,
            maxRetryDelay: TimeSpan.FromMilliseconds(200),
            errorCodesToAdd: null);
    });

    if (builder.Environment.IsDevelopment())
    {
        options.EnableSensitiveDataLogging();
        options.EnableDetailedErrors();
    }
});

// ─── OPENTELEMETRY ──────────────────────────────────────────────────────────

// ADR-009: OpenTelemetry — use OpenTelemetryProtocol exporter (NOT Otlp — that package does not exist)
var otlpEndpoint = builder.Configuration["Otel:Endpoint"] ?? "http://localhost:4317";

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

// ─── APPLICATION ────────────────────────────────────────────────────────────

var app = builder.Build();

// ADR-001: Map gRPC service — Constitutional Engine is the only service on this port
// C-073: constitutional obligation — ConstitutionalEngineService implements all governance RPCs
app.MapGrpcService<ConstitutionalEngineService>();

// Health check endpoint for infrastructure probes (not exposed externally)
app.MapGet("/healthz", () => Results.Ok(new { status = "healthy", service = "constitutional-engine" }));

app.Run();

// Make Program accessible for integration test WebApplicationFactory
public partial class Program { }