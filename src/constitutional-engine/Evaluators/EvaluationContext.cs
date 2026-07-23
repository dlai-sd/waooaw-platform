// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-041 (Tool Authorization), C-043 (Budget Ceiling),
//                       C-048 (Non-Exploitation), C-049 (Honest Limitation), C-051 (Resource Transparency),
//                       C-062 (AI Security)

using Waooaw.ConstitutionalEngine.Data;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Immutable context passed to every claim evaluator during a ValidateAction call.
/// Provides access to request data and DB-backed read-only accessors.
/// </summary>
/// <remarks>
/// C-073: Carries all data needed for constitutional evaluation without network I/O.
/// Evaluators MUST only read from this context — no writes, no external calls.
/// </remarks>
public sealed class EvaluationContext
{
    /// <summary>Tenant identifier for the requesting agent.</summary>
    public required string TenantId { get; init; }

    /// <summary>Agent identifier making the request.</summary>
    public required string AgentId { get; init; }

    /// <summary>
    /// Action type being requested (e.g., "MCP_TOOL_CALL", "LLM_INFERENCE", "DATA_READ").
    /// </summary>
    public required string ActionType { get; init; }

    /// <summary>
    /// Tool name for MCP_TOOL_CALL actions. Null for non-tool actions.
    /// </summary>
    public string? ToolName { get; init; }

    /// <summary>
    /// Estimated cost in USD for this action (used by C-043 budget evaluator).
    /// </summary>
    public decimal EstimatedCostUsd { get; init; }

    /// <summary>
    /// Arbitrary metadata from the ValidateAction request payload.
    /// Evaluators may read but MUST NOT mutate.
    /// </summary>
    public IReadOnlyDictionary<string, string> Metadata { get; init; }
        = new Dictionary<string, string>();

    /// <summary>
    /// Read-only DB accessor — pre-loaded data for this evaluation cycle.
    /// Populated by the ValidateAction handler before evaluators run.
    /// </summary>
    public required IEvaluationDataAccessor Data { get; init; }

    /// <summary>UTC timestamp when this evaluation started (for budget tracking).</summary>
    public DateTimeOffset EvaluatedAt { get; init; } = DateTimeOffset.UtcNow;
}

/// <summary>
/// Read-only data accessor for evaluators.
/// Implementations load data from DB before the evaluator pipeline runs.
/// </summary>
public interface IEvaluationDataAccessor
{
    /// <summary>
    /// Returns the set of tool names authorized in the tenant's active employment contract.
    /// Returns empty set if no active contract exists (C-041: default deny).
    /// </summary>
    Task<IReadOnlySet<string>> GetAuthorizedToolsAsync(string tenantId, CancellationToken ct);

    /// <summary>
    /// Returns the tenant's remaining budget in USD for the current billing period.
    /// Returns 0 if no budget record exists (C-043: default deny on unknown budget).
    /// </summary>
    Task<decimal> GetRemainingBudgetUsdAsync(string tenantId, CancellationToken ct);

    /// <summary>
    /// Returns the tenant's daily spend in USD for today.
    /// </summary>
    Task<decimal> GetDailySpendUsdAsync(string tenantId, CancellationToken ct);

    /// <summary>
    /// Returns the tenant's daily budget ceiling in USD.
    /// Returns 0 if not configured (C-043: default deny).
    /// </summary>
    Task<decimal> GetDailyBudgetCeilingUsdAsync(string tenantId, CancellationToken ct);

    /// <summary>
    /// Returns true if the tool is on the C-062 prohibited tools list.
    /// </summary>
    Task<bool> IsToolSecurityProhibitedAsync(string toolName, CancellationToken ct);

    /// <summary>
    /// Returns true if the agent has an active exploitation flag (C-048).
    /// </summary>
    Task<bool> HasExploitationFlagAsync(string agentId, CancellationToken ct);

    /// <summary>
    /// Returns true if the agent has declared an honest limitation for this action type (C-049).
    /// When true, action should be escalated rather than auto-approved.
    /// </summary>
    Task<bool> HasHonestLimitationFlagAsync(string agentId, string actionType, CancellationToken ct);
}