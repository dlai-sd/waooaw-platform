// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-023 (Evidence First), C-027 (append-only ledger)

namespace Waooaw.ConstitutionalEngine.Data.Entities;

/// <summary>
/// Tracks caller-supplied idempotency keys to prevent duplicate evidence writes on retry.
/// Keyed by the caller-supplied UUID string.
/// </summary>
public sealed class IdempotencyKey
{
    public string Key { get; init; } = string.Empty;
    public Guid EvidenceId { get; init; }
    public DateTimeOffset CreatedAt { get; init; }
}