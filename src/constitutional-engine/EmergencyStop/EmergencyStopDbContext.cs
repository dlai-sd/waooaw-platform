// Implements: architecture/reference/components/constitutional-engine.md §4 Emergency Stop Handler
// constitutional_basis: C-001 (Emergency Stop absolute), AD-002 (Evidence First), C-059 (Traceability)

using Microsoft.EntityFrameworkCore;

namespace Waooaw.ConstitutionalEngine.EmergencyStop;

/// <summary>
/// EF Core DbContext scoped to the constitutional.emergency_stop_events table.
/// Kept separate from the main CE DbContext to allow independent migration cadence.
/// </summary>
// DESIGN_QUESTION: Should this merge into a shared ConstitutionalEngineDbContext or remain isolated?
//                  EA review requested — isolation chosen here for blast-radius minimisation.
public sealed class EmergencyStopDbContext : DbContext
{
    public EmergencyStopDbContext(DbContextOptions<EmergencyStopDbContext> options)
        : base(options) { }

    // C-073: Constitutional obligation — evidence table for all Emergency Stop events
    public DbSet<EmergencyStopEvent> EmergencyStopEvents => Set<EmergencyStopEvent>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // C-073: Constitutional obligation — schema isolation for constitutional data
        modelBuilder.HasDefaultSchema("constitutional");

        modelBuilder.Entity<EmergencyStopEvent>(entity =>
        {
            entity.ToTable("emergency_stop_events");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                  .HasColumnName("id")
                  .ValueGeneratedNever(); // We set the GUID in application code for traceability

            entity.Property(e => e.ContractId)
                  .HasColumnName("contract_id")
                  .IsRequired();

            entity.Property(e => e.InitiatedByUserId)
                  .HasColumnName("initiated_by_user_id")
                  .HasMaxLength(256)
                  .IsRequired();

            entity.Property(e => e.AffectedSessionIds)
                  .HasColumnName("affected_session_ids")
                  .HasColumnType("text[]")
                  .IsRequired();

            entity.Property(e => e.TriggeredAt)
                  .HasColumnName("triggered_at")
                  .IsRequired();

            entity.Property(e => e.TemporalSignalledAt)
                  .HasColumnName("temporal_signalled_at");

            entity.Property(e => e.TraceId)
                  .HasColumnName("trace_id")
                  .HasMaxLength(128);

            entity.Property(e => e.StopSource)
                  .HasColumnName("stop_source")
                  .HasMaxLength(32)
                  .IsRequired();

            entity.Property(e => e.Status)
                  .HasColumnName("status")
                  .HasConversion<string>()
                  .HasMaxLength(32)
                  .IsRequired();

            // Index for fast lookup by contract (common query pattern)
            entity.HasIndex(e => e.ContractId)
                  .HasDatabaseName("ix_emergency_stop_events_contract_id");

            // Index for audit queries by user
            entity.HasIndex(e => e.InitiatedByUserId)
                  .HasDatabaseName("ix_emergency_stop_events_user_id");
        });
    }
}