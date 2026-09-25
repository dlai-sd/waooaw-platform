// Implements: adr/ADR-044-constitutional-audit-trail-sink.md §2
// constitutional_basis: C-059 (Traceability), ADR-044

using Microsoft.EntityFrameworkCore;
using Waooaw.ConstitutionalEngine.Data.Entities;

namespace Waooaw.ConstitutionalEngine.Data;

/// <summary>EF Core context for the audit_sink schema. C-059: WORM — INSERT only, no UPDATE/DELETE.</summary>
public sealed class AuditSinkDbContext : DbContext
{
    public AuditSinkDbContext(DbContextOptions<AuditSinkDbContext> options)
        : base(options) { }

    public DbSet<AuditSinkEvidenceRecord> EvidenceRecords => Set<AuditSinkEvidenceRecord>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<AuditSinkEvidenceRecord>(e =>
        {
            e.ToTable("evidence_records", "audit_sink");
            e.HasKey(r => r.Id);
            e.HasIndex(r => r.DecisionId).IsUnique();
            e.Property(r => r.Id).HasColumnName("id");
            e.Property(r => r.DecisionId).HasColumnName("decision_id");
            e.Property(r => r.TenantId).HasColumnName("tenant_id");
            e.Property(r => r.AgentId).HasColumnName("agent_id");
            e.Property(r => r.AgentInstanceId).HasColumnName("agent_instance_id");
            e.Property(r => r.ActionType).HasColumnName("action_type");
            e.Property(r => r.ToolName).HasColumnName("tool_name");
            e.Property(r => r.ArgsHash).HasColumnName("args_hash");
            e.Property(r => r.PayloadRefId).HasColumnName("payload_ref_id");
            e.Property(r => r.CredentialProvider).HasColumnName("credential_provider");
            e.Property(r => r.VaultAlias).HasColumnName("vault_alias");
            e.Property(r => r.ExecutionStatus).HasColumnName("execution_status");
            e.Property(r => r.ConstitutionalBasis)
                .HasColumnName("constitutional_basis")
                .HasColumnType("text[]");
            e.Property(r => r.EvidenceHash).HasColumnName("evidence_hash");
            e.Property(r => r.RecordedAt).HasColumnName("recorded_at");
            e.Property(r => r.ErasureStatus).HasColumnName("erasure_status");
            e.Property(r => r.ErasureTimestamp).HasColumnName("erasure_timestamp");
        });
    }
}
