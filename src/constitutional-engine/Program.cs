// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-023 (Evidence First), ADR-001 (gRPC), ADR-009 (OpenTelemetry), ADR-044 (AuditSink)
using Microsoft.EntityFrameworkCore;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.EmergencyStop;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Services;

var builder = WebApplication.CreateBuilder(args);
var postgresPassword = builder.Configuration["POSTGRES_PASSWORD"];
if (!string.IsNullOrWhiteSpace(postgresPassword))
{
    var connection = new Npgsql.NpgsqlConnectionStringBuilder(
        builder.Configuration.GetConnectionString("DefaultConnection")
            ?? "Host=localhost;Port=5432;Database=waooaw;Username=postgres"
    )
    {
        Password = postgresPassword,
    };
    builder.Configuration["ConnectionStrings:DefaultConnection"] = connection.ConnectionString;
}
builder.Services.AddGrpc();
builder.Services.AddSingleton<IClaimEvaluator, C041ToolAuthorizationEvaluator>();
builder.Services.AddSingleton<IClaimEvaluator, C043BudgetCeilingEvaluator>();
builder.Services.AddSingleton<IClaimEvaluator, C048NonExploitationEvaluator>();
builder.Services.AddSingleton<IClaimEvaluator, C049HonestLimitationEvaluator>();
builder.Services.AddSingleton<IClaimEvaluator, C062AiSecurityEvaluator>();
builder.Services.AddSingleton<IClaimEvaluator, AgentAdmissionTransitionEvaluator>();
builder.Services.AddSingleton<IClaimEvaluator, RelationshipAdmissionEvaluator>();
builder.Services.AddSingleton<EvaluatorRegistry>();
builder
    .Services.AddGrpcHealthChecks()
    .AddCheck(
        "constitutional-engine",
        () => Microsoft.Extensions.Diagnostics.HealthChecks.HealthCheckResult.Healthy()
    );

var defaultConnection =
    builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_ce;Username=ce_service_role;";
builder.Services.AddDbContextFactory<ConstitutionalDbContext>(opts =>
    opts.UseNpgsql(
        defaultConnection,
        npgsql => npgsql.MapEnum<EvidenceRecordState>("evidence_state", "constitutional")
    )
);
builder.Services.AddDbContextFactory<EmergencyStopDbContext>(opts =>
    opts.UseNpgsql(defaultConnection)
);

// ── Audit Sink DbContext — WORM evidence records (ADR-044) ───────────────────
// Required for WriteAuditSinkRecordAsync on every ValidateAction call (C-059).
var auditSinkConn =
    builder.Configuration.GetConnectionString("AuditSink")
    ?? defaultConnection;
builder.Services.AddDbContextFactory<AuditSinkDbContext>(opts => opts.UseNpgsql(auditSinkConn));

var app = builder.Build();
app.MapGrpcService<ConstitutionalEngineService>();
app.MapGrpcHealthChecksService();
app.Run();
