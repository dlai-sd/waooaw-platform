// Implements: adr/ADR-044-constitutional-audit-trail-sink.md §2
// constitutional_basis: C-059 (Traceability), ADR-044

using Microsoft.EntityFrameworkCore;
using Waooaw.ConstitutionalEngine.Data.Entities;

namespace Waooaw.ConstitutionalEngine.Data;

/// <summary>EF Core context for the audit_sink schema. C-059: WORM — INSERT only, no UPDATE/DELETE.</summary>
public sealed class AuditSinkDbContext : DbContext
{
    public AuditSinkDbContext(DbContextOptions<AuditSinkDbContext> options) : base(options) { }

    public DbSet<AuditSinkEvidenceRecord> EvidenceRecords => Set<AuditSinkEvidenceRecord>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<AuditSinkEvidenceRecord>(e =>
        {
            e.ToTable("evidence_records", "audit_sink");
            e.HasKey(r => r.Id);
            e.HasIndex(r => r.DecisionId).IsUnique();
            e.Property(r => r.ConstitutionalBasis).HasColumnType("text[]");
        });
    }
}
