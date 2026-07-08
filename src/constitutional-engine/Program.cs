using Microsoft.EntityFrameworkCore;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Waooaw.ConstitutionalEngine.Infrastructure;
using Waooaw.ConstitutionalEngine.Services;

var builder = WebApplication.CreateBuilder(args);

// ─── gRPC ─────────────────────────────────────────────────────────────────────
builder.Services.AddGrpc();
builder.Services.AddGrpcHealthChecks();

// ─── Database (EF Core + PostgreSQL) ─────────────────────────────────────────
builder.Services.AddDbContext<ConstitutionalDbContext>(opts =>
    opts.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection"),
        npgsql => npgsql.MigrationsHistoryTable("__EFMigrationsHistory", "constitutional")));

// ─── Observability (ADR-009) ──────────────────────────────────────────────────
builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("constitutional-engine"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddEntityFrameworkCoreInstrumentation()
        .AddOtlpExporter(o => o.Endpoint = new Uri(
            builder.Configuration["OTLP_ENDPOINT"] ?? "http://jaeger:4317")));

var app = builder.Build();

// ─── Routes ───────────────────────────────────────────────────────────────────
app.MapGrpcService<ConstitutionalServiceImpl>();
app.MapGrpcHealthChecksService();  // grpc.health.v1.Health — required for health probes

app.MapGet("/", () => "Constitutional Engine — gRPC only. Use a gRPC client.");

app.Run();
