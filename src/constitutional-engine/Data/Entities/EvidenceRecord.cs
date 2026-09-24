// Implements: architecture/reference/components/constitutional-engine.md §1
// constitutional_basis: C-027 (append-only ledger), C-023 (Evidence First), C-059 (Traceability)

using NpgsqlTypes;

namespace Waooaw.ConstitutionalEngine.Data.Entities;

/// <summary>Append-only evidence record in the Constitutional Audit Ledger. C-027: never UPDATE or DELETE.</summary>
public sealed class EvidenceRecord
{
    public Guid Id { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid ContractId { get; init; }
    public Guid ProfessionalId { get; init; }
    public Guid ActionInstanceId { get; init; }
    public string ActionType { get; init; } = string.Empty;
    public EvidenceRecordState State { get; init; }
    public string? ProposedContent { get; init; }
    public string? ExecutedContent { get; init; }
    public bool IsScopeBoundary { get; init; }
    public string? ScopeBoundaryName { get; init; }
    public string? ScopeBoundaryAcknowledgment { get; init; }
    public int DecisionSpaceVersion { get; init; }
    public string ConstitutionalBasis { get; init; } = string.Empty;
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
}

public enum EvidenceRecordState
{
    [PgName("PROPOSED")]
    Proposed = 1,
    [PgName("AWAITING_APPROVAL")]
    AwaitingApproval = 2,
    [PgName("APPROVED")]
    Approved = 3,
    [PgName("REJECTED")]
    Rejected = 4,
    [PgName("EXECUTED")]
    Executed = 5,
    [PgName("ABANDONED")]
    Abandoned = 6,
}
