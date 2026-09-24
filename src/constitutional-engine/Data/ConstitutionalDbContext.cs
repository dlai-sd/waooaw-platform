// Implements: architecture/reference/components/constitutional-engine.md §1
// constitutional_basis: C-027 (append-only), C-023 (Evidence First)

using Microsoft.EntityFrameworkCore;
using Waooaw.ConstitutionalEngine.Data.Entities;

namespace Waooaw.ConstitutionalEngine.Data;

/// <summary>EF Core context for the Constitutional Audit Ledger. C-027: INSERT only, no UPDATE/DELETE.</summary>
public sealed class ConstitutionalDbContext : DbContext
{
    public ConstitutionalDbContext(DbContextOptions<ConstitutionalDbContext> options)
        : base(options) { }

    public DbSet<EvidenceRecord> EvidenceRecords => Set<EvidenceRecord>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.HasPostgresEnum<EvidenceRecordState>("constitutional", "evidence_state");
        modelBuilder.Entity<EvidenceRecord>(entity =>
        {
            entity.ToTable("evidence_records", "constitutional");
            entity.HasKey(record => record.Id);
            entity.Property(record => record.Id).HasColumnName("id");
            entity.Property(record => record.TenantId).HasColumnName("tenant_id");
            entity.Property(record => record.ContractId).HasColumnName("contract_id");
            entity.Property(record => record.ProfessionalId).HasColumnName("professional_id");
            entity.Property(record => record.ActionInstanceId).HasColumnName("action_instance_id");
            entity.Property(record => record.ActionType).HasColumnName("action_type");
            entity.Property(record => record.State).HasColumnName("state");
            entity.Property(record => record.ProposedContent)
                .HasColumnName("proposed_content")
                .HasColumnType("jsonb");
            entity.Property(record => record.ExecutedContent)
                .HasColumnName("executed_content")
                .HasColumnType("jsonb");
            entity.Property(record => record.IsScopeBoundary).HasColumnName("is_scope_boundary");
            entity.Property(record => record.ScopeBoundaryName).HasColumnName("scope_boundary_name");
            entity.Property(record => record.ScopeBoundaryAcknowledgment)
                .HasColumnName("scope_boundary_acknowledgment");
            entity.Property(record => record.DecisionSpaceVersion)
                .HasColumnName("decision_space_version");
            entity.Property(record => record.ConstitutionalBasis)
                .HasColumnName("constitutional_basis");
            entity.Property(record => record.CreatedAt).HasColumnName("created_at");
            entity.HasIndex(record => new
            {
                record.TenantId,
                record.ActionInstanceId,
                record.State,
            });
        });
    }
}
