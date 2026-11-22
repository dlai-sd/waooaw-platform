// Implements: adr/ADR-042-provider-registry-constitutional-tool-gateway.md §1
// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R001
// constitutional_basis: C-031 (ADR on file), C-041 (tool authorization), C-059 (traceability)

using Microsoft.EntityFrameworkCore;

namespace Waooaw.BusinessPlatform.Infrastructure;

/// <summary>EF Core context for provider_configs and its credential version history. BP-owned; PR/AIR read via internal API.</summary>
public sealed class ProviderRegistryDbContext : DbContext
{
    public ProviderRegistryDbContext(DbContextOptions<ProviderRegistryDbContext> options)
        : base(options) { }

    public DbSet<ProviderConfig> ProviderConfigs => Set<ProviderConfig>();
    public DbSet<ProviderCredentialVersion> ProviderCredentialVersions =>
        Set<ProviderCredentialVersion>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<ProviderConfig>(e =>
        {
            e.ToTable("provider_configs", "business");
            e.HasKey(p => p.Id);
            e.Property(p => p.Id).HasColumnName("id");
            e.Property(p => p.TenantId).HasColumnName("tenant_id");
            e.Property(p => p.ProviderName).HasColumnName("provider_name");
            e.Property(p => p.AuthMethod).HasColumnName("auth_method").HasMaxLength(32);
            e.Property(p => p.McpServerUrl).HasColumnName("mcp_server_url");
            e.Property(p => p.ScopeSet).HasColumnName("scope_set").HasColumnType("text[]");
            e.Property(p => p.VaultPathKey).HasColumnName("vault_path_key");
            e.Property(p => p.Active).HasColumnName("active");
            e.Property(p => p.CreatedAt).HasColumnName("created_at");
            e.Property(p => p.DisplayName).HasColumnName("display_name");
            e.Property(p => p.Category).HasColumnName("category");
            e.Property(p => p.AgentTypeId).HasColumnName("agent_type_id");
            e.Property(p => p.TestUrl).HasColumnName("test_url");
            e.Property(p => p.TestAuthScheme).HasColumnName("test_auth_scheme");
            e.Property(p => p.TestAuthHeader).HasColumnName("test_auth_header");
            e.Property(p => p.ActiveCredentialVersionId)
                .HasColumnName("active_credential_version_id");
            e.HasIndex(p => new { p.TenantId, p.ProviderName }).IsUnique();
        });

        modelBuilder.Entity<ProviderCredentialVersion>(e =>
        {
            e.ToTable("provider_credential_versions", "business");
            e.HasKey(v => v.Id);
            e.Property(v => v.Id).HasColumnName("id");
            e.Property(v => v.ProviderConfigId).HasColumnName("provider_config_id");
            e.Property(v => v.VersionNo).HasColumnName("version_no");
            e.Property(v => v.VaultSecretName).HasColumnName("vault_secret_name");
            e.Property(v => v.VaultSecretVersion).HasColumnName("vault_secret_version");
            e.Property(v => v.Status).HasColumnName("status");
            e.Property(v => v.TestOutcome).HasColumnName("test_outcome");
            e.Property(v => v.CreatedBySubject).HasColumnName("created_by_subject");
            e.Property(v => v.CreatedAt).HasColumnName("created_at");
            e.Property(v => v.ActivatedAt).HasColumnName("activated_at");
            e.HasIndex(v => new { v.ProviderConfigId, v.VersionNo }).IsUnique();
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
    public string? DisplayName { get; init; }

    /// <summary>PLATFORM_LLM or AGENT_API; null for rows that hold no Founder-managed credential.</summary>
    public string? Category { get; init; }
    public string? AgentTypeId { get; init; }
    public string? TestUrl { get; init; }

    /// <summary>BEARER, X_API_KEY, X_GOOG_API_KEY or HEADER (the header named by TestAuthHeader).</summary>
    public string? TestAuthScheme { get; init; }
    public string? TestAuthHeader { get; init; }
    public Guid? ActiveCredentialVersionId { get; set; }
}

/// <summary>One recorded credential version: names a Key Vault secret version and never holds the value.</summary>
public sealed class ProviderCredentialVersion
{
    public Guid Id { get; init; } = Guid.NewGuid();
    public Guid ProviderConfigId { get; init; }
    public int VersionNo { get; init; }
    public string VaultSecretName { get; init; } = string.Empty;
    public string VaultSecretVersion { get; init; } = string.Empty;
    public string Status { get; set; } = ProviderCredentialStatuses.Active;
    public string TestOutcome { get; init; } = string.Empty;
    public string CreatedBySubject { get; init; } = string.Empty;
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? ActivatedAt { get; set; }
}

public static class ProviderCredentialStatuses
{
    public const string Active = "ACTIVE";
    public const string Superseded = "SUPERSEDED";
}
