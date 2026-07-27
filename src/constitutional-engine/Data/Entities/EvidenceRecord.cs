// Implements: architecture/reference/components/constitutional-engine.md §1
// constitutional_basis: C-027 (append-only ledger), C-023 (Evidence First), C-059 (Traceability)

namespace Waooaw.ConstitutionalEngine.Data.Entities;

/// <summary>Append-only evidence record in the Constitutional Audit Ledger. C-027: never UPDATE or DELETE.</summary>
public sealed class EvidenceRecord
{
    public Guid Id { get; init; } = Guid.NewGuid();
    public string IdempotencyKey { get; init; } = string.Empty;
    public Guid TenantId { get; init; }
    public string EvidenceType { get; init; } = string.Empty;
    public string Summary { get; init; } = string.Empty;
    public string? PayloadJson { get; init; }
    public DateTimeOffset RecordedAt { get; init; } = DateTimeOffset.UtcNow;
}
