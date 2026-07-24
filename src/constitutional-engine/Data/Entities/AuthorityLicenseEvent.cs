// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-003 (authority licensed), C-023 (Evidence First), C-027 (append-only ledger)

namespace Waooaw.ConstitutionalEngine.Data.Entities;

/// <summary>
/// Represents an authority expansion or restriction event.
/// Append-only — never updated or deleted after creation (C-027).
/// Every event references an EvidenceRecord in the Constitutional Audit Ledger (C-023).
/// </summary>
public sealed class AuthorityLicenseEvent
{
    /// <summary>Primary key — UUID assigned by the application before INSERT.</summary>
    public Guid Id { get; init; }

    /// <summary>Tenant identifier. C-029: scope-boundary record.</summary>
    public Guid TenantId { get; init; }

    /// <summary>The contract whose authority is being modified.</summary>
    public Guid ContractId { get; init; }

    /// <summary>The session context (nullable).</summary>
    public Guid? SessionId { get; init; }

    /// <summary>
    /// "GRANT" or "REVOKE" — distinguishes expansion from restriction.
    /// C-003: authority licensed — both directions are recorded.
    /// </summary>
    public string EventType { get; init; } = string.Empty;

    /// <summary>Human-readable description of the authority being modified.</summary>
    public string AuthorityDescription { get; init; } = string.Empty;

    /// <summary>JSON array of action type strings being granted or revoked.</summary>
    public string ActionTypesJson { get; init; } = string.Empty;

    /// <summary>
    /// JSON array of evidence IDs justifying this grant (nullable for revocations).
    /// C-023: expansions require prior evidence.
    /// </summary>
    public string? JustifyingEvidenceIdsJson { get; init; }

    /// <summary>Reason for revocation (nullable — only populated for REVOKE events).</summary>
    public string? Reason { get; init; }

    /// <summary>Constitutional basis for this event. AD-008.</summary>
    public string ConstitutionalBasis { get; init; } = string.Empty;

    /// <summary>Actor authorising the change. Format: "user:{uuid}" or "system:{service-name}"</summary>
    public string Actor { get; init; } = string.Empty;

    /// <summary>
    /// Foreign key to the EvidenceRecord written for this event.
    /// Every authority event has a corresponding ledger entry (C-023).
    /// </summary>
    public Guid EvidenceRecordId { get; init; }

    /// <summary>Server-side timestamp when this event was recorded (UTC).</summary>
    public DateTimeOffset RecordedAt { get; init; }
}