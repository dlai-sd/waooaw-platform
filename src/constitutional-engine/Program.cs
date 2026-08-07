// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-023 (Evidence First), ADR-001 (gRPC), ADR-009 (OpenTelemetry), ADR-044 (AuditSink)
using Microsoft.EntityFrameworkCore;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Services;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddGrpc();

// ── Audit Sink DbContext — WORM evidence records (ADR-044) ───────────────────
// Required for WriteAuditSinkRecordAsync on every ValidateAction call (C-059).
var auditSinkConn = builder.Configuration.GetConnectionString("AuditSink")
    ?? builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_ce;Username=ce_service_role;";
builder.Services.AddDbContextFactory<AuditSinkDbContext>(opts =>
    opts.UseNpgsql(auditSinkConn));

var app = builder.Build();
app.MapGrpcService<ConstitutionalEngineService>();
app.Run();
