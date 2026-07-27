// Implements: architecture/reference/components/constitutional-engine.md §4
// constitutional_basis: C-001 (Emergency Stop), C-027 (append-only), C-023 (Evidence First)

using Microsoft.EntityFrameworkCore;

namespace Waooaw.ConstitutionalEngine.EmergencyStop;

/// <summary>EF Core context for Emergency Stop evidence. Append-only per C-027.</summary>
public sealed class EmergencyStopDbContext : DbContext
{
    public EmergencyStopDbContext(DbContextOptions<EmergencyStopDbContext> options) : base(options) {}
    public DbSet<EmergencyStopEvent> EmergencyStopEvents => Set<EmergencyStopEvent>();
}
