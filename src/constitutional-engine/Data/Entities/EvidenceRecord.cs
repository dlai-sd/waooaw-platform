// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-027 (append-only ledger), C-023 (Evidence First), AD-003 (Audit Ledger immutability)

namespace Waooaw.ConstitutionalEngine.Data.Entities;

/// <summary>
/// Represents a single immutable record in the Constitutional Audit Ledger.
/// INVARIANT: Once written, this record must never be modified or deleted (C-027, AD-003).
/// </summary>
public sealed class EvidenceRecord
{
    // C-027: Primary key — UUID assigned at write time
    public Guid Id { get; init; } = Guid.NewGuid();

    // Idempotency key supplied by caller — prevents duplicate writes on retry
    public string IdempotencyKey { get; init; } = string.Empty;

    // Tenant isolation — extracted from gRPC metadata "x-tenant-id" (never from request body)
    public string TenantId { get; init; } = string.Empty;

    // Classification of this evidence record
    public string EvidenceType { get; init; } = string.Empty;

    // Human-readable description of the event
    public string Description { get; init; } = string.Empty;

    // Constitutional basis clause(s) — required by AD-008
    public string ConstitutionalBasis { get; init; } = string.Empty;

    // JSON-encoded event-specific payload
    public string? PayloadJson { get; init; }

    // Optional: related evidence record IDs
    public string[]? RelatedEvidenceIds { get; init; }

    // Optional: contract scope
    public string? ContractId { get; init; }

    // Optional: PAAS session scope
    public string? SessionId { get; init; }

    // Caller's event timestamp
    public DateTimeOffset EventTimestamp { get; init; }

    // Server-side commit timestamp — set by DB default (NOW())
    public DateTimeOffset LedgerTimestamp { get; init; }
}