// Implements: adr/ADR-042-provider-registry-constitutional-tool-gateway.md §1
// constitutional_basis: C-031 (ADR on file), C-041 (tool authorization), C-059 (traceability)

using Microsoft.EntityFrameworkCore;

namespace Waooaw.BusinessPlatform.Infrastructure;

/// <summary>EF Core context for provider_configs table. BP-owned; PR/AIR read via internal API.</summary>
public sealed class ProviderRegistryDbContext : DbContext
{
    public ProviderRegistryDbContext(DbContextOptions<ProviderRegistryDbContext> options) : base(options) { }

    public DbSet<ProviderConfig> ProviderConfigs => Set<ProviderConfig>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<ProviderConfig>(e =>
        {
            e.ToTable("provider_configs", "business");
            e.HasKey(p => p.Id);
            e.HasIndex(p => new { p.TenantId, p.ProviderName }).IsUnique();
            e.Property(p => p.ScopeSet).HasColumnType("text[]");
            e.Property(p => p.AuthMethod)
             .HasConversion<string>()
             .HasMaxLength(32);
        });
    }
}

/// <summary>Platform or per-tenant provider routing config. Adding a new provider = inserting a row.</summary>
public sealed class ProviderConfig
{
    public Guid Id { get; init; } = Guid.NewGuid();
    /// <summary>NULL = platform-level (e.g. OpenAI API key shared across platform).</summary>
    public Guid? TenantId { get; init; }
    public string ProviderName { get; init; } = string.Empty;
    public string AuthMethod { get; init; } = string.Empty;
    public string? McpServerUrl { get; init; }
    public string[] ScopeSet { get; init; } = [];
    public string VaultPathKey { get; init; } = string.Empty;
    public bool Active { get; init; } = true;
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
}
