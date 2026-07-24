// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-027 (append-only ledger), C-023 (Evidence First), AD-003 (Audit Ledger immutability)

namespace Waooaw.ConstitutionalEngine.Data.Entities;

/// <summary>
/// Represents a single record in the Constitutional Audit Ledger.
/// INVARIANT (C-027): This entity is NEVER updated or deleted after creation.
/// All writes are INSERT-only. EF Core change tracking must never issue UPDATE
/// or DELETE statements against this table.
/// </summary>
public sealed class EvidenceRecord
{
    /// <summary>Primary key — UUID assigned by the application before INSERT.</summary>
    public Guid Id { get; init; }

    /// <summary>
    /// Caller-supplied idempotency key. Unique per tenant.
    /// Enables safe retry without duplicate ledger entries.
    /// </summary>
    public string IdempotencyKey { get; init; } = string.Empty;

    /// <summary>
    /// Tenant identifier extracted from gRPC metadata "x-tenant-id".
    /// C-029: scope-boundary record — every record is tenant-scoped.
    /// </summary>
    public Guid TenantId { get; init; }

    /// <summary>The contract this evidence belongs to.</summary>
    public Guid ContractId { get; init; }

    /// <summary>The Professional Runtime session (nullable — not all events are session-scoped).</summary>
    public Guid? SessionId { get; init; }

    /// <summary>Classification of this evidence record. C-023.</summary>
    public string EvidenceType { get; init; } = string.Empty;

    /// <summary>Human-readable summary stored verbatim in the ledger.</summary>
    public string Summary { get; init; } = string.Empty;

    /// <summary>JSON-encoded domain-specific payload. Stored verbatim; never interpreted by CE.</summary>
    public string? PayloadJson { get; init; }

    /// <summary>
    /// Constitutional basis string. AD-008: required on every evidence record.
    /// Example: "C-023 Evidence First; C-027 Append-Only Ledger"
    /// </summary>
    public string ConstitutionalBasis { get; init; } = string.Empty;

    /// <summary>Actor who caused this event. Format: "user:{uuid}" or "system:{service-name}"</summary>
    public string Actor { get; init; } = string.Empty;

    /// <summary>Wall-clock time of the originating event (caller's clock, UTC).</summary>
    public DateTimeOffset OccurredAt { get; init; }

    /// <summary>Server-side timestamp when the record was committed to the ledger (UTC).</summary>
    public DateTimeOffset RecordedAt { get; init; }
}