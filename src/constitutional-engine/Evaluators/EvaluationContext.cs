// Implements: architecture/reference/ce-validate-action-evaluators.md §Evaluator Architecture
// constitutional_basis: C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

using System;
using System.Collections.Generic;
using Waooaw.ConstitutionalEngine.Data.Models;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Immutable snapshot of all data an evaluator may need.
/// Built once per ValidateAction RPC call; evaluators must not perform additional I/O.
/// </summary>
/// <remarks>
/// C-073: Context construction is a constitutional obligation — it gates all evaluator access
/// to DB state, ensuring evaluators remain deterministic and testable.
/// </remarks>
public sealed class EvaluationContext
{
    // ── Request fields ────────────────────────────────────────────────────────

    /// <summary>Tenant (agent) identifier from the incoming RPC.</summary>
    public required string TenantId { get; init; }

    /// <summary>Action type being requested (e.g., "MCP_TOOL_CALL", "BUDGET_SPEND").</summary>
    public required string ActionType { get; init; }

    /// <summary>Tool name when ActionType == "MCP_TOOL_CALL"; null otherwise.</summary>
    public string? ToolName { get; init; }

    /// <summary>Proposed spend amount in USD cents (for budget evaluators).</summary>
    public long? ProposedSpendCents { get; init; }

    /// <summary>Free-form metadata from the requesting agent.</summary>
    public IReadOnlyDictionary<string, string> Metadata { get; init; }
        = new Dictionary<string, string>();

    // ── Pre-loaded DB state ───────────────────────────────────────────────────

    /// <summary>
    /// Active employment contract for this tenant.
    /// Null if no active contract exists (evaluators should DENY in that case).
    /// </summary>
    public EmploymentContract? ActiveContract { get; init; }

    /// <summary>
    /// Cumulative spend in USD cents for the current budget period.
    /// Loaded from business.budget_ledger before evaluators run.
    /// </summary>
    public long CumulativeSpendCents { get; init; }

    /// <summary>
    /// Budget ceiling in USD cents from the active contract.
    /// Zero means no contract / no budget authorised.
    /// </summary>
    public long BudgetCeilingCents { get; init; }

    /// <summary>Timestamp at which this context was built (UTC).</summary>
    public DateTimeOffset ContextBuiltAt { get; init; } = DateTimeOffset.UtcNow;
}