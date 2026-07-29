// Implements: architecture/reference/components/business-platform.md
// constitutional_basis: ADR-002 (spec-first), ADR-003 (JWT tenancy), C-026 (RLS), C-023

using Waooaw.BusinessPlatform.Controllers;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();
app.UseSwagger();
app.UseSwaggerUI();
app.MapControllers();
app.Run();
