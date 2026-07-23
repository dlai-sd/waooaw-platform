// Implements: architecture/reference/ce-validate-action-evaluators.md §Evaluator Architecture
// constitutional_basis: C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace Waooaw.ConstitutionalEngine.Data.Models;

/// <summary>
/// EF Core entity mapping to constitutional.audit_records.
/// Every DENY and every AUTHORIZED decision is recorded here (C-023 Evidence First).
/// </summary>
[Table("audit_records", Schema = "constitutional")]
public sealed class AuditRecord
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Column("tenant_id")]
    [Required]
    public string TenantId { get; set; } = string.Empty;

    [Column("action_type")]
    [Required]
    public string ActionType { get; set; } = string.Empty;

    [Column("tool_name")]
    public string? ToolName { get; set; }

    /// <summary>
    /// "VALIDATION_DENY" | "VALIDATION_AUTHORIZED" | "VALIDATION_ESCALATE"
    /// </summary>
    [Column("event_type")]
    [Required]
    public string EventType { get; set; } = string.Empty;

    /// <summary>Constitutional claim ID that produced this record (e.g., "C-043").</summary>
    [Column("constitutional_basis")]
    public string? ConstitutionalBasis { get; set; }

    [Column("reason")]
    public string? Reason { get; set; }

    [Column("evidence_hint")]
    public string? EvidenceHint { get; set; }

    [Column("recorded_at")]
    public DateTimeOffset RecordedAt { get; set; } = DateTimeOffset.UtcNow;
}