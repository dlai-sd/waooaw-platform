// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R007
// Constitutional basis: C-023, C-059, C-063, C-083, C-084

using Microsoft.EntityFrameworkCore;

namespace Waooaw.BusinessPlatform.Infrastructure;

public static class CustomerConnectionStatuses
{
    public const string Connected = "CONNECTED";
    public const string NeedsRepair = "NEEDS_REPAIR";
    public const string Revoked = "REVOKED";
}

/// <summary>A customer's connected provider account. The token itself lives only in Key Vault under secret_name.</summary>
public sealed class CustomerProviderConnection
{
    public Guid Id { get; set; }
    public Guid TenantId { get; set; }
    public string Provider { get; set; } = string.Empty;
    public string Status { get; set; } = CustomerConnectionStatuses.Connected;
    public string AccountId { get; set; } = string.Empty;
    public string AccountName { get; set; } = string.Empty;
    public List<string> Scopes { get; set; } = [];
    public string SecretName { get; set; } = string.Empty;
    public string SecretVersion { get; set; } = string.Empty;
    public DateTimeOffset? ExpiresAt { get; set; }
    public DateTimeOffset ConnectedAt { get; set; }
    public DateTimeOffset? RevokedAt { get; set; }
    public Guid CreatedBy { get; set; }
}

/// <summary>A single-use OAuth state, stored only as its SHA-256 digest and bound to one tenant and actor.</summary>
public sealed class ProviderConnectionState
{
    public string StateHash { get; set; } = string.Empty;
    public Guid TenantId { get; set; }
    public Guid ActorId { get; set; }
    public string Provider { get; set; } = string.Empty;
    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset ExpiresAt { get; set; }
    public DateTimeOffset? ConsumedAt { get; set; }
}

public sealed class CustomerConnectionsDbContext : DbContext
{
    public CustomerConnectionsDbContext(DbContextOptions<CustomerConnectionsDbContext> options)
        : base(options) { }

    public DbSet<CustomerProviderConnection> Connections => Set<CustomerProviderConnection>();
    public DbSet<ProviderConnectionState> States => Set<ProviderConnectionState>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<CustomerProviderConnection>(e =>
        {
            e.ToTable("customer_provider_connections", "business");
            e.HasKey(c => c.Id);
            e.Property(c => c.Id).HasColumnName("id").ValueGeneratedNever();
            e.Property(c => c.TenantId).HasColumnName("tenant_id");
            e.Property(c => c.Provider).HasColumnName("provider");
            e.Property(c => c.Status).HasColumnName("status");
            e.Property(c => c.AccountId).HasColumnName("account_id");
            e.Property(c => c.AccountName).HasColumnName("account_name");
            e.Property(c => c.Scopes).HasColumnName("scopes").HasColumnType("text[]");
            e.Property(c => c.SecretName).HasColumnName("secret_name");
            e.Property(c => c.SecretVersion).HasColumnName("secret_version");
            e.Property(c => c.ExpiresAt).HasColumnName("expires_at");
            e.Property(c => c.ConnectedAt).HasColumnName("connected_at");
            e.Property(c => c.RevokedAt).HasColumnName("revoked_at");
            e.Property(c => c.CreatedBy).HasColumnName("created_by");
        });

        modelBuilder.Entity<ProviderConnectionState>(e =>
        {
            e.ToTable("provider_connection_states", "business");
            e.HasKey(s => s.StateHash);
            e.Property(s => s.StateHash).HasColumnName("state_hash");
            e.Property(s => s.TenantId).HasColumnName("tenant_id");
            e.Property(s => s.ActorId).HasColumnName("actor_id");
            e.Property(s => s.Provider).HasColumnName("provider");
            e.Property(s => s.CreatedAt).HasColumnName("created_at");
            e.Property(s => s.ExpiresAt).HasColumnName("expires_at");
            e.Property(s => s.ConsumedAt).HasColumnName("consumed_at");
        });
    }
}
