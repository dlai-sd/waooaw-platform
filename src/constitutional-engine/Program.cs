// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-023 (Evidence First), ADR-001 (gRPC), ADR-009 (OpenTelemetry), ADR-044 (AuditSink)
using Microsoft.EntityFrameworkCore;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Services;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddGrpc();
builder.Services.AddSingleton<IClaimEvaluator, C041ToolAuthorizationEvaluator>();
builder.Services.AddSingleton<IClaimEvaluator, C043BudgetCeilingEvaluator>();
builder.Services.AddSingleton<IClaimEvaluator, C048NonExploitationEvaluator>();
builder.Services.AddSingleton<IClaimEvaluator, C049HonestLimitationEvaluator>();
builder.Services.AddSingleton<IClaimEvaluator, C062AiSecurityEvaluator>();
builder.Services.AddSingleton<IClaimEvaluator, AgentAdmissionTransitionEvaluator>();
builder.Services.AddSingleton<EvaluatorRegistry>();
builder.Services
    .AddGrpcHealthChecks()
    .AddCheck("constitutional-engine", () =>
        Microsoft.Extensions.Diagnostics.HealthChecks.HealthCheckResult.Healthy());

// ── Audit Sink DbContext — WORM evidence records (ADR-044) ───────────────────
// Required for WriteAuditSinkRecordAsync on every ValidateAction call (C-059).
var auditSinkConn = builder.Configuration.GetConnectionString("AuditSink")
    ?? builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_ce;Username=ce_service_role;";
builder.Services.AddDbContextFactory<AuditSinkDbContext>(opts =>
    opts.UseNpgsql(auditSinkConn));

var app = builder.Build();
app.MapGrpcService<ConstitutionalEngineService>();
app.MapGrpcHealthChecksService();
app.Run();
