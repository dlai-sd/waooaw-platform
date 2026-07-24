// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-041 (Tool Authorization), C-043 (Budget Ceiling),
//                       C-048 (Non-Exploitation), C-062 (AI Security)

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Pre-loaded context passed to every claim evaluator.
/// All DB reads happen BEFORE evaluators run — evaluators are pure functions over this context.
/// This ensures the 40ms ValidateAction budget is not consumed by repeated DB round-trips.
/// </summary>
public sealed class EvaluationContext
{
    // ── Request fields (from ValidateActionRequest proto) ──────────────────────────────────────

    /// <summary>Tenant identifier (maps to business.employment_contracts.tenant_id).</summary>
    public required string TenantId { get; init; }

    /// <summary>Agent identifier performing the action.</summary>
    public required string AgentId { get; init; }

    /// <summary>Action type (e.g., "MCP_TOOL_CALL", "BUDGET_SPEND", "DATA_ACCESS").</summary>
    public required string ActionType { get; init; }

    /// <summary>Tool name for MCP_TOOL_CALL actions; null for other action types.</summary>
    public string? ToolName { get; init; }

    /// <summary>Proposed spend amount in USD cents (for BUDGET_SPEND actions).</summary>
    public long? ProposedSpendCents { get; init; }

    /// <summary>Free-form action payload metadata (JSON string from proto).</summary>
    public string? ActionPayload { get; init; }

    // ── Pre-loaded DB data (populated by ValidateActionContextBuilder) ─────────────────────────

    /// <summary>
    /// Authorized actions from the tenant's active employment contract.
    /// Null if no active contract exists (C-041 evaluator will DENY).
    /// </summary>
    public IReadOnlyList<string>? ContractAuthorizedActions { get; init; }

    /// <summary>
    /// Budget ceiling in USD cents from the tenant's active contract (C-043).
    /// Null if no active contract or no budget defined.
    /// </summary>
    public long? ContractBudgetCeilingCents { get; init; }

    /// <summary>
    /// Total spend in USD cents for the current billing period (C-043).
    /// Loaded from constitutional.budget_ledger or equivalent.
    /// </summary>
    public long CurrentPeriodSpendCents { get; init; }

    /// <summary>
    /// Whether the tenant has an active exploitation-risk flag (C-048).
    /// Set by compliance workflows when exploitation patterns are detected.
    /// </summary>
    public bool TenantHasExploitationFlag { get; init; }

    /// <summary>
    /// List of prohibited tool names for this tenant (C-062 AI Security).
    /// Loaded from constitutional.prohibited_tools or contract security policy.
    /// </summary>
    public IReadOnlyList<string> ProhibitedTools { get; init; } = Array.Empty<string>();

    /// <summary>
    /// Whether the agent is currently operating in a sandboxed/safe mode context.
    /// Used by C-062 evaluator for elevated-risk tool calls.
    /// </summary>
    public bool AgentInSandboxMode { get; init; }

    // ── Timestamp ─────────────────────────────────────────────────────────────────────────────

    /// <summary>UTC timestamp when this context was built (for audit records).</summary>
    public DateTimeOffset EvaluatedAt { get; init; } = DateTimeOffset.UtcNow;
}