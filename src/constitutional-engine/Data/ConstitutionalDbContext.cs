// Implements: architecture/reference/ce-validate-action-evaluators.md §Evaluator Architecture
// constitutional_basis: C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

using Microsoft.EntityFrameworkCore;
using Waooaw.ConstitutionalEngine.Data.Models;

namespace Waooaw.ConstitutionalEngine.Data;

/// <summary>
/// EF Core DbContext for the Constitutional Engine.
/// Provides access to employment contracts and audit records.
/// </summary>
public class ConstitutionalDbContext : DbContext
{
    public ConstitutionalDbContext(DbContextOptions<ConstitutionalDbContext> options)
        : base(options) { }

    public DbSet<EmploymentContract> EmploymentContracts => Set<EmploymentContract>();
    public DbSet<AuditRecord> AuditRecords => Set<AuditRecord>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // C-073: Index on tenant_id + is_active for fast contract lookup during ValidateAction.
        modelBuilder.Entity<EmploymentContract>()
            .HasIndex(c => new { c.TenantId, c.IsActive })
            .HasDatabaseName("ix_employment_contracts_tenant_active");

        // C-073: Index on tenant_id + recorded_at for audit queries.
        modelBuilder.Entity<AuditRecord>()
            .HasIndex(r => new { r.TenantId, r.RecordedAt })
            .HasDatabaseName("ix_audit_records_tenant_recorded_at");
    }
}