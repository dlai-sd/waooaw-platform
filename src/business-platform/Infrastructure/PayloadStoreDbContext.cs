// Implements: adr/ADR-044-constitutional-audit-trail-sink.md §3
// constitutional_basis: C-078 (DPDPA Right-to-Erasure), ADR-044

using Microsoft.EntityFrameworkCore;

namespace Waooaw.BusinessPlatform.Infrastructure;

/// <summary>EF Core context for payload_store schema. Payloads are erasable on DPDPA request.</summary>
public sealed class PayloadStoreDbContext : DbContext
{
    public PayloadStoreDbContext(DbContextOptions<PayloadStoreDbContext> options) : base(options) { }

    public DbSet<OperationalPayload> OperationalPayloads => Set<OperationalPayload>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<OperationalPayload>(e =>
        {
            e.ToTable("operational_payloads", "payload_store");
            e.HasKey(p => p.Id);
            e.HasIndex(p => p.PayloadRefId).IsUnique();
        });
    }
}

/// <summary>Erasable operational payload row. payload_json set to null on DPDPA erasure.</summary>
public sealed class OperationalPayload
{
    public Guid Id { get; init; } = Guid.NewGuid();
    public Guid PayloadRefId { get; init; }
    public Guid TenantId { get; init; }
    public string AgentInstanceId { get; init; } = string.Empty;
    public string ActionType { get; init; } = string.Empty;
    public string? PayloadJson { get; set; }
    public string? PayloadBlobRef { get; set; }
    public bool PiiPresent { get; init; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? ErasedAt { get; set; }
}
