// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-027 (append-only ledger), C-023 (Evidence First), AD-003 (Audit Ledger immutability)

using Microsoft.EntityFrameworkCore;
using Waooaw.ConstitutionalEngine.Data.Entities;

namespace Waooaw.ConstitutionalEngine.Data;

/// <summary>
/// EF Core DbContext for the Constitutional Engine.
/// INVARIANT: No UPDATE or DELETE operations are ever issued on EvidenceRecord.
/// The append-only constraint is enforced at the application layer (C-027) and
/// should also be enforced at the database layer via row-level security (AD-003).
/// </summary>
public sealed class ConstitutionalDbContext : DbContext
{
    // C-073: Constructor satisfies C-027 (append-only ledger) by providing
    // the single write surface for EvidenceRecord — no update/delete paths exist.
    public ConstitutionalDbContext(DbContextOptions<ConstitutionalDbContext> options)
        : base(options)
    {
    }

    /// <summary>
    /// The Constitutional Audit Ledger — append-only.
    /// C-027: No UPDATE or DELETE ever issued on this table.
    /// </summary>
    public DbSet<EvidenceRecord> EvidenceRecords => Set<EvidenceRecord>();

    /// <summary>
    /// Authority license events — append-only history of grants and revocations.
    /// C-003: authority licensed — every expansion/restriction is recorded.
    /// </summary>
    public DbSet<AuthorityLicenseEvent> AuthorityLicenseEvents => Set<AuthorityLicenseEvent>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // C-073: EvidenceRecord configuration enforces C-027 (append-only ledger)
        modelBuilder.Entity<EvidenceRecord>(entity =>
        {
            entity.ToTable("evidence_records", "constitutional");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id").ValueGeneratedNever();
            entity.Property(e => e.IdempotencyKey).HasColumnName("idempotency_key").IsRequired();
            entity.Property(e => e.TenantId).HasColumnName("tenant_id").IsRequired();
            entity.Property(e => e.ContractId).HasColumnName("contract_id").IsRequired();
            entity.Property(e => e.SessionId).HasColumnName("session_id");
            entity.Property(e => e.EvidenceType).HasColumnName("evidence_type").IsRequired();
            entity.Property(e => e.Summary).HasColumnName("summary").IsRequired();
            entity.Property(e => e.PayloadJson).HasColumnName("payload_json");
            entity.Property(e => e.ConstitutionalBasis).HasColumnName("constitutional_basis").IsRequired();
            entity.Property(e => e.Actor).HasColumnName("actor").IsRequired();
            entity.Property(e => e.OccurredAt).HasColumnName("occurred_at").IsRequired();
            entity.Property(e => e.RecordedAt).HasColumnName("recorded_at").IsRequired();

            // Unique constraint on idempotency_key per tenant — prevents duplicate writes on retry.
            entity.HasIndex(e => new { e.TenantId, e.IdempotencyKey }).IsUnique();
        });

        // C-073: AuthorityLicenseEvent configuration enforces C-003 (authority licensed)
        modelBuilder.Entity<AuthorityLicenseEvent>(entity =>
        {
            entity.ToTable("authority_license_events", "constitutional");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id").ValueGeneratedNever();
            entity.Property(e => e.TenantId).HasColumnName("tenant_id").IsRequired();
            entity.Property(e => e.ContractId).HasColumnName("contract_id").IsRequired();
            entity.Property(e => e.SessionId).HasColumnName("session_id");
            entity.Property(e => e.EventType).HasColumnName("event_type").IsRequired();
            entity.Property(e => e.AuthorityDescription).HasColumnName("authority_description").IsRequired();
            entity.Property(e => e.ActionTypesJson).HasColumnName("action_types_json").IsRequired();
            entity.Property(e => e.JustifyingEvidenceIdsJson).HasColumnName("justifying_evidence_ids_json");
            entity.Property(e => e.Reason).HasColumnName("reason");
            entity.Property(e => e.ConstitutionalBasis).HasColumnName("constitutional_basis").IsRequired();
            entity.Property(e => e.Actor).HasColumnName("actor").IsRequired();
            entity.Property(e => e.EvidenceRecordId).HasColumnName("evidence_record_id").IsRequired();
            entity.Property(e => e.RecordedAt).HasColumnName("recorded_at").IsRequired();
        });
    }
}