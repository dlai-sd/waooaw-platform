// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-027 (append-only ledger), C-023 (Evidence First), AD-003 (Audit Ledger immutability)

using Microsoft.EntityFrameworkCore;
using Waooaw.ConstitutionalEngine.Data.Entities;

namespace Waooaw.ConstitutionalEngine.Data;

/// <summary>
/// EF Core DbContext for the Constitutional Audit Ledger.
/// INVARIANT: No UPDATE or DELETE operations are ever issued on EvidenceRecord.
/// All writes are INSERT-only (append-only ledger — C-027, AD-003).
/// </summary>
public sealed class ConstitutionalDbContext : DbContext
{
    // C-027: append-only ledger — EvidenceRecords are INSERT-only
    public DbSet<EvidenceRecord> EvidenceRecords => Set<EvidenceRecord>();

    public ConstitutionalDbContext(DbContextOptions<ConstitutionalDbContext> options)
        : base(options)
    {
    }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // C-027: Evidence record is append-only — configure schema accordingly
        modelBuilder.Entity<EvidenceRecord>(entity =>
        {
            entity.ToTable("evidence_records", "constitutional");

            entity.HasKey(e => e.Id);

            entity.Property(e => e.Id)
                  .HasColumnName("id")
                  .ValueGeneratedOnAdd();

            entity.Property(e => e.IdempotencyKey)
                  .HasColumnName("idempotency_key")
                  .HasMaxLength(36)
                  .IsRequired();

            entity.HasIndex(e => e.IdempotencyKey)
                  .IsUnique()
                  .HasDatabaseName("ix_evidence_records_idempotency_key");

            entity.Property(e => e.TenantId)
                  .HasColumnName("tenant_id")
                  .HasMaxLength(36)
                  .IsRequired();

            entity.HasIndex(e => e.TenantId)
                  .HasDatabaseName("ix_evidence_records_tenant_id");

            entity.Property(e => e.EvidenceType)
                  .HasColumnName("evidence_type")
                  .HasMaxLength(64)
                  .IsRequired();

            entity.Property(e => e.Description)
                  .HasColumnName("description")
                  .HasMaxLength(2048)
                  .IsRequired();

            entity.Property(e => e.ConstitutionalBasis)
                  .HasColumnName("constitutional_basis")
                  .HasMaxLength(512)
                  .IsRequired();

            entity.Property(e => e.PayloadJson)
                  .HasColumnName("payload_json")
                  .HasColumnType("jsonb");

            entity.Property(e => e.ContractId)
                  .HasColumnName("contract_id")
                  .HasMaxLength(36);

            entity.Property(e => e.SessionId)
                  .HasColumnName("session_id")
                  .HasMaxLength(36);

            entity.Property(e => e.RelatedEvidenceIds)
                  .HasColumnName("related_evidence_ids")
                  .HasColumnType("text[]");

            entity.Property(e => e.EventTimestamp)
                  .HasColumnName("event_timestamp")
                  .IsRequired();

            entity.Property(e => e.LedgerTimestamp)
                  .HasColumnName("ledger_timestamp")
                  .IsRequired()
                  .HasDefaultValueSql("NOW()");

            // AD-003: Immutability — no row-level security bypass; enforce at application layer
            // DESIGN_QUESTION: Should we add a PostgreSQL trigger to prevent UPDATE/DELETE at DB level?
        });
    }
}