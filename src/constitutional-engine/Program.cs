// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-023 (Evidence First), ADR-001 (gRPC), ADR-009 (OpenTelemetry)

using Waooaw.ConstitutionalEngine.Services;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddGrpc();

var app = builder.Build();
app.MapGrpcService<ConstitutionalEngineService>();
app.Run();
