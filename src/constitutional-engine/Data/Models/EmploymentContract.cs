// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-043 (Budget Ceiling),
//                       C-059 (Traceability), C-073 (Annotation)

using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace Waooaw.ConstitutionalEngine.Data.Models;

/// <summary>
/// EF Core entity mapping to business.employment_contracts.
/// Represents the active contract that governs what a tenant (agent) may do.
/// </summary>
[Table("employment_contracts", Schema = "business")]
public sealed class EmploymentContract
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("tenant_id")]
    [Required]
    public string TenantId { get; set; } = string.Empty;

    /// <summary>
    /// Array of authorized action/tool names for this tenant.
    /// C-041: tool must appear here to be authorized.
    /// </summary>
    [Column("authorized_actions")]
    public string[] AuthorizedActions { get; set; } = Array.Empty<string>();

    /// <summary>
    /// Budget ceiling in USD cents for the contract period.
    /// C-043: spend must not exceed this value.
    /// </summary>
    [Column("budget_ceiling_cents")]
    public long BudgetCeilingCents { get; set; }

    [Column("is_active")]
    public bool IsActive { get; set; }

    [Column("valid_from")]
    public DateTimeOffset ValidFrom { get; set; }

    [Column("valid_to")]
    public DateTimeOffset? ValidTo { get; set; }
}