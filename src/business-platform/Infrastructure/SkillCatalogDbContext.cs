// Implements: adr/ADR-043-skill-architecture-standard.md §2 Skill Catalog
// constitutional_basis: C-036 (skills are constitutional units), C-059 (traceability)

using Microsoft.EntityFrameworkCore;
using System.Text.Json;

namespace Waooaw.BusinessPlatform.Infrastructure;

/// <summary>EF Core context for business.skills catalog table. BP-owned; PR reads via API.</summary>
public sealed class SkillCatalogDbContext : DbContext
{
    public SkillCatalogDbContext(DbContextOptions<SkillCatalogDbContext> options) : base(options) { }

    public DbSet<SkillEntry> Skills => Set<SkillEntry>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<SkillEntry>(e =>
        {
            e.ToTable("skills", "business");
            e.HasKey(s => s.Id);
            e.HasIndex(s => new { s.SkillId, s.Version }).IsUnique();
            e.HasIndex(s => s.Status);
            e.Property(s => s.Definition).HasColumnType("jsonb");
            e.Property(s => s.CctSuite).HasColumnType("text[]");
        });
    }
}

/// <summary>
/// A single versioned skill entry in the Skill Catalog.
/// ADR-043 §2: status ∈ {DRAFT, PUBLISHED, DEPRECATED}.
/// </summary>
public sealed class SkillEntry
{
    public Guid Id { get; init; } = Guid.NewGuid();
    public string SkillId { get; init; } = string.Empty;
    public string Version { get; init; } = string.Empty;
    public string DisplayName { get; init; } = string.Empty;
    /// <summary>Full skill YAML as JSON — definition blob (ADR-043 §1 schema).</summary>
    public string Definition { get; init; } = "{}";
    public string[] CctSuite { get; init; } = [];
    public string Status { get; set; } = "DRAFT";
    public DateTimeOffset? PublishedAt { get; set; }
    public DateTimeOffset? DeprecatedAt { get; set; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
}
