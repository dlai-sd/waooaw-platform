// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-027 (append-only ledger), C-023 (Evidence First), AD-003 (Audit Ledger immutability)

using Microsoft.EntityFrameworkCore;
using Waooaw.ConstitutionalEngine.Data.Entities;

namespace Waooaw.ConstitutionalEngine.Data;

/// <summary>
/// EF Core DbContext for the Constitutional Engine.
/// INVARIANT: No UPDATE or DELETE operations are ever issued on EvidenceRecord or AuthorityLicense.
/// All writes are INSERT-only (append-only ledger — C-027, AD-003).
/// </summary>
public sealed class ConstitutionalDbContext : DbContext
{
    // C-027: append-only ledger — these sets are INSERT-only at the application layer
    public DbSet<EvidenceRecord> EvidenceRecords => Set<EvidenceRecord>();
    public DbSet<AuthorityLicense> AuthorityLicenses => Set<AuthorityLicense>();
    public DbSet<IdempotencyKey> IdempotencyKeys => Set<IdempotencyKey>();

    public ConstitutionalDbContext(DbContextOptions<ConstitutionalDbContext> options)
        : base(options) { }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // C-027: Evidence records are append-only — configure schema accordingly
        modelBuilder.Entity<EvidenceRecord>(entity =>
        {
            entity.ToTable("evidence_records", "constitutional");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id").ValueGeneratedNever();
            entity.Property(e => e.TenantId).HasColumnName("tenant_id").IsRequired();
            entity.Property(e => e.EvidenceType).HasColumnName("evidence_type").IsRequired();
            entity.Property(e => e.ActorId).HasColumnName("actor_id").IsRequired();
            entity.Property(e => e.ContractId).HasColumnName("contract_id");
            entity.Property(e => e.SessionId).HasColumnName("session_id");
            entity.Property(e => e.ActionType).HasColumnName("action_type");
            entity.Property(e => e.PayloadJson).HasColumnName("payload_json").HasColumnType("jsonb");
            entity.Property(e => e.ConstitutionalBasis).HasColumnName("constitutional_basis").IsRequired();
            entity.Property(e => e.IdempotencyKey).HasColumnName("idempotency_key");
            entity.Property(e => e.RecordedAt).HasColumnName("recorded_at").IsRequired();

            entity.HasIndex(e => e.TenantId).HasDatabaseName("ix_evidence_records_tenant_id");
            entity.HasIndex(e => e.IdempotencyKey)
                  .IsUnique()
                  .HasFilter("idempotency_key IS NOT NULL")
                  .HasDatabaseName("ix_evidence_records_idempotency_key");
        });

        modelBuilder.Entity<AuthorityLicense>(entity =>
        {
            entity.ToTable("authority_licenses", "constitutional");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id").ValueGeneratedNever();
            entity.Property(e => e.TenantId).HasColumnName("tenant_id").IsRequired();
            entity.Property(e => e.ContractId).HasColumnName("contract_id").IsRequired();
            entity.Property(e => e.GrantedBy).HasColumnName("granted_by").IsRequired();
            entity.Property(e => e.AuthorityScope).HasColumnName("authority_scope").IsRequired();
            entity.Property(e => e.JustificationEvidenceIds).HasColumnName("justification_evidence_ids").HasColumnType("text[]");
            entity.Property(e => e.GrantedAt).HasColumnName("granted_at").IsRequired();
            entity.Property(e => e.ExpiresAt).HasColumnName("expires_at");
            entity.Property(e => e.RevokedAt).HasColumnName("revoked_at");
            entity.Property(e => e.RevokedBy).HasColumnName("revoked_by");
            entity.Property(e => e.RevocationReason).HasColumnName("revocation_reason");
            entity.Property(e => e.EvidenceId).HasColumnName("evidence_id").IsRequired();

            entity.HasIndex(e => e.TenantId).HasDatabaseName("ix_authority_licenses_tenant_id");
            entity.HasIndex(e => e.ContractId).HasDatabaseName("ix_authority_licenses_contract_id");
        });

        modelBuilder.Entity<IdempotencyKey>(entity =>
        {
            entity.ToTable("idempotency_keys", "constitutional");
            entity.HasKey(e => e.Key);
            entity.Property(e => e.Key).HasColumnName("key").IsRequired();
            entity.Property(e => e.EvidenceId).HasColumnName("evidence_id").IsRequired();
            entity.Property(e => e.CreatedAt).HasColumnName("created_at").IsRequired();
        });
    }
}