// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-003 (authority licensed), C-023 (Evidence First), C-027 (append-only ledger)

namespace Waooaw.ConstitutionalEngine.Data.Entities;

/// <summary>
/// Represents an authority license record.
/// Grants are INSERT-only. Revocations are recorded as a new INSERT on the EvidenceRecord
/// table; the license row is updated only to set RevokedAt (a single allowed mutation
/// per the Authority License Manager spec — the grant row itself is never deleted).
/// DESIGN_QUESTION: Should revocations be a separate append-only RevocationRecord entity
/// rather than mutating the AuthorityLicense row? Flagged for EA review.
/// </summary>
public sealed class AuthorityLicense
{
    public Guid Id { get; init; }
    public Guid TenantId { get; init; }
    public Guid ContractId { get; init; }
    public string GrantedBy { get; init; } = string.Empty;
    public string AuthorityScope { get; init; } = string.Empty;
    public string[] JustificationEvidenceIds { get; init; } = Array.Empty<string>();
    public DateTimeOffset GrantedAt { get; init; }
    public DateTimeOffset? ExpiresAt { get; init; }

    // Revocation fields — set once on revocation, never changed again
    public DateTimeOffset? RevokedAt { get; set; }
    public string? RevokedBy { get; set; }
    public string? RevocationReason { get; set; }

    // FK to the evidence record that recorded this grant
    public Guid EvidenceId { get; init; }
}