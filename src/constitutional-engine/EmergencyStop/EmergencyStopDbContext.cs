// Implements: architecture/reference/components/constitutional-engine.md §4
// constitutional_basis: C-001 (Emergency Stop), C-027 (append-only), C-023 (Evidence First)

using Microsoft.EntityFrameworkCore;

namespace Waooaw.ConstitutionalEngine.EmergencyStop;

/// <summary>EF Core context for Emergency Stop evidence. Append-only per C-027.</summary>
public sealed class EmergencyStopDbContext : DbContext
{
    public EmergencyStopDbContext(DbContextOptions<EmergencyStopDbContext> options)
        : base(options) { }

    public DbSet<EmergencyStopEvent> EmergencyStopEvents => Set<EmergencyStopEvent>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<EmergencyStopEvent>(entity =>
        {
            entity.ToTable("emergency_stop_events", "constitutional");
            entity.HasKey(value => value.Id);
            entity.Property(value => value.Id).HasColumnName("id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.ContractId).HasColumnName("contract_id");
            entity.Property(value => value.InitiatedByUserId).HasColumnName("initiated_by_user_id");
            entity.Property(value => value.AffectedSessionIds).HasColumnName("affected_session_ids");
            entity.Property(value => value.TriggeredAt).HasColumnName("triggered_at");
            entity.Property(value => value.TemporalSignalledAt).HasColumnName("temporal_signalled_at");
            entity.Property(value => value.StopSource).HasColumnName("stop_source");
        });
    }
}
