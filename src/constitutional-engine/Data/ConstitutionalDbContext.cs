// Implements: architecture/reference/components/constitutional-engine.md §1
// constitutional_basis: C-027 (append-only), C-023 (Evidence First)

using Microsoft.EntityFrameworkCore;
using Waooaw.ConstitutionalEngine.Data.Entities;

namespace Waooaw.ConstitutionalEngine.Data;

/// <summary>EF Core context for the Constitutional Audit Ledger. C-027: INSERT only, no UPDATE/DELETE.</summary>
public sealed class ConstitutionalDbContext : DbContext
{
    public ConstitutionalDbContext(DbContextOptions<ConstitutionalDbContext> options) : base(options) {}
    public DbSet<EvidenceRecord> EvidenceRecords => Set<EvidenceRecord>();
}
