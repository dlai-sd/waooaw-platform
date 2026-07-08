using Microsoft.EntityFrameworkCore;

namespace Waooaw.ConstitutionalEngine.Infrastructure;

/// <summary>
/// Constitutional Audit Ledger database context.
/// Append-only: INSERT + SELECT only on constitutional schema.
/// No UPDATE. No DELETE. Enforced at DB level via PostgreSQL RULE (05-append-only-rules.sql).
/// C-027, AD-003.
/// </summary>
public class ConstitutionalDbContext : DbContext
{
    public ConstitutionalDbContext(DbContextOptions<ConstitutionalDbContext> options)
        : base(options) { }

    public DbSet<EvidenceRecord> EvidenceRecords => Set<EvidenceRecord>();
    public DbSet<AuthorityLicense> AuthorityLicenses => Set<AuthorityLicense>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.HasDefaultSchema("constitutional");

        modelBuilder.Entity<EvidenceRecord>(e =>
        {
            e.ToTable("evidence_records");
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasColumnName("id");
            e.Property(x => x.TenantId).HasColumnName("tenant_id").IsRequired();
            e.Property(x => x.ContractId).HasColumnName("contract_id").IsRequired();
            e.Property(x => x.ProfessionalId).HasColumnName("professional_id").IsRequired();
            e.Property(x => x.ActionInstanceId).HasColumnName("action_instance_id").IsRequired();
            e.Property(x => x.ActionType).HasColumnName("action_type").IsRequired();
            e.Property(x => x.State).HasColumnName("state").IsRequired();
            e.Property(x => x.ProposedContent).HasColumnName("proposed_content").HasColumnType("jsonb");
            e.Property(x => x.ExecutedContent).HasColumnName("executed_content").HasColumnType("jsonb");
            e.Property(x => x.IsScopeBoundary).HasColumnName("is_scope_boundary").IsRequired();
            e.Property(x => x.ScopeBoundaryName).HasColumnName("scope_boundary_name");
            e.Property(x => x.ScopeBoundaryAcknowledgment).HasColumnName("scope_boundary_acknowledgment");
            e.Property(x => x.DecisionSpaceVersion).HasColumnName("decision_space_version").IsRequired();
            e.Property(x => x.ConstitutionalBasis).HasColumnName("constitutional_basis").IsRequired();
            e.Property(x => x.CreatedAt).HasColumnName("created_at").IsRequired();
        });

        modelBuilder.Entity<AuthorityLicense>(e =>
        {
            e.ToTable("authority_licenses");
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasColumnName("id");
            e.Property(x => x.TenantId).HasColumnName("tenant_id").IsRequired();
            e.Property(x => x.ContractId).HasColumnName("contract_id").IsRequired();
            e.Property(x => x.ProfessionalId).HasColumnName("professional_id").IsRequired();
            e.Property(x => x.AuthorityLevel).HasColumnName("authority_level").IsRequired();
            e.Property(x => x.GrantedBy).HasColumnName("granted_by").IsRequired();
            e.Property(x => x.ConstitutionalBasis).HasColumnName("constitutional_basis").IsRequired();
            e.Property(x => x.GrantedAt).HasColumnName("granted_at").IsRequired();
        });
    }
}

// ─── Domain Entities ──────────────────────────────────────────────────────────

public class EvidenceRecord
{
    public Guid Id { get; set; }
    public Guid TenantId { get; set; }
    public Guid ContractId { get; set; }
    public Guid ProfessionalId { get; set; }
    public Guid ActionInstanceId { get; set; }
    public string ActionType { get; set; } = string.Empty;
    public string State { get; set; } = string.Empty;  // matches evidence_state enum
    public string? ProposedContent { get; set; }
    public string? ExecutedContent { get; set; }
    public bool IsScopeBoundary { get; set; }
    public string? ScopeBoundaryName { get; set; }
    public string? ScopeBoundaryAcknowledgment { get; set; }
    public int DecisionSpaceVersion { get; set; }
    public string ConstitutionalBasis { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
    // No UpdatedAt — append-only (C-027)
}

public class AuthorityLicense
{
    public Guid Id { get; set; }
    public Guid TenantId { get; set; }
    public Guid ContractId { get; set; }
    public Guid ProfessionalId { get; set; }
    public int AuthorityLevel { get; set; }
    public Guid GrantedBy { get; set; }
    public string ConstitutionalBasis { get; set; } = string.Empty;
    public Guid[] EvidenceIds { get; set; } = [];
    public DateTime GrantedAt { get; set; }
}
