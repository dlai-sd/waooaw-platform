// Implements: adr/ADR-044-constitutional-audit-trail-sink.md §2
// constitutional_basis: C-059 (Traceability), C-078 (DPDPA), ADR-044

namespace Waooaw.ConstitutionalEngine.Data.Entities;

/// <summary>WORM evidence record in audit_sink schema. C-059: never UPDATE or DELETE.</summary>
public sealed class AuditSinkEvidenceRecord
{
    public Guid Id { get; init; } = Guid.NewGuid();
    public string DecisionId { get; init; } = string.Empty;
    public Guid TenantId { get; init; }
    public string AgentId { get; init; } = string.Empty;
    public string AgentInstanceId { get; init; } = string.Empty;
    public string ActionType { get; init; } = string.Empty;
    public string? ToolName { get; init; }
    public string? ArgsHash { get; init; }
    public Guid? PayloadRefId { get; init; }
    public string? CredentialProvider { get; init; }
    public string? VaultAlias { get; init; }
    public string ExecutionStatus { get; init; } = string.Empty;  // immutable proof field
    public string[] ConstitutionalBasis { get; init; } = [];
    public string EvidenceHash { get; init; } = string.Empty;
    public DateTimeOffset RecordedAt { get; init; } = DateTimeOffset.UtcNow;
    public string ErasureStatus { get; set; } = "NONE";           // updated by RecordErasure only
    public DateTimeOffset? ErasureTimestamp { get; set; }          // set by RecordErasure
}
