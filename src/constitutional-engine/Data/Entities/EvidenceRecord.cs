// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-027 (append-only ledger), C-023 (Evidence First), AD-003 (Audit Ledger immutability)

namespace Waooaw.ConstitutionalEngine.Data.Entities;

/// <summary>
/// Represents a single append-only record in the Constitutional Audit Ledger.
/// INVARIANT: This entity is NEVER updated or deleted (C-027, AD-003).
/// </summary>
public sealed class EvidenceRecord
{
    public Guid Id { get; init; }
    public Guid TenantId { get; init; }
    public string EvidenceType { get; init; } = string.Empty;
    public string ActorId { get; init; } = string.Empty;
    public Guid? ContractId { get; init; }
    public Guid? SessionId { get; init; }
    public string? ActionType { get; init; }
    public string? PayloadJson { get; init; }

    // AD-008: every permission decision must name its constitutional basis
    public string ConstitutionalBasis { get; init; } = string.Empty;
    public string? IdempotencyKey { get; init; }
    public DateTimeOffset RecordedAt { get; init; }
}