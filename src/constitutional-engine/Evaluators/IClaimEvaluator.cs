// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-041 (Tool Authorization), C-043 (Budget Ceiling),
//                       C-048 (Non-Exploitation), C-049 (Honest Limitation), C-051 (Resource Transparency),
//                       C-062 (AI Security)

#nullable enable

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Evaluation decision returned by a claim evaluator.
/// </summary>
public enum EvaluationDecision
{
    /// <summary>Action is constitutionally permitted.</summary>
    Authorized,

    /// <summary>Action is constitutionally prohibited — short-circuit and deny.</summary>
    Deny,

    /// <summary>Action is uncertain — escalate to human (C-049 path).</summary>
    Escalate
}

/// <summary>
/// Result of a single claim evaluator's assessment.
/// </summary>
/// <param name="Decision">The evaluation decision.</param>
/// <param name="Reason">Required when Decision == Deny. Logged in audit record.</param>
/// <param name="EvidenceHint">Optional extra context for the evidence record.</param>
public record EvaluationResult(
    EvaluationDecision Decision,
    string? Reason = null,
    string? EvidenceHint = null
);

/// <summary>
/// Context provided to each evaluator during ValidateAction processing.
/// Evaluators MUST NOT perform network I/O — only DB reads via this context.
/// </summary>
public sealed class EvaluationContext
{
    /// <summary>The gRPC ValidateAction request being evaluated.</summary>
    public required string TenantId { get; init; }

    /// <summary>Agent identifier making the request.</summary>
    public required string AgentId { get; init; }

    /// <summary>Action type (e.g., "MCP_TOOL_CALL", "BUDGET_SPEND", "DATA_ACCESS").</summary>
    public required string ActionType { get; init; }

    /// <summary>Tool name for MCP_TOOL_CALL actions; null for other action types.</summary>
    public string? ToolName { get; init; }

    /// <summary>Requested spend amount in USD cents (for BUDGET_SPEND actions).</summary>
    public long? RequestedSpendCents { get; init; }

    /// <summary>Arbitrary metadata from the ValidateAction request.</summary>
    public IReadOnlyDictionary<string, string> Metadata { get; init; } =
        new Dictionary<string, string>();

    /// <summary>Pre-loaded tenant budget state (populated by EvaluatorRegistry).</summary>
    public TenantBudgetState? BudgetState { get; init; }

    /// <summary>Pre-loaded authorized tools for this tenant (populated by EvaluatorRegistry).</summary>
    public IReadOnlySet<string>? AuthorizedTools { get; init; }

    /// <summary>Pre-loaded prohibited tool patterns (populated by EvaluatorRegistry).</summary>
    public IReadOnlyList<string>? ProhibitedToolPatterns { get; init; }
}

/// <summary>
/// Tenant budget state snapshot for C-043 evaluation.
/// </summary>
public sealed class TenantBudgetState
{
    public long DailyBudgetCents { get; init; }
    public long DailySpentCents { get; init; }
    public long MonthlyBudgetCents { get; init; }
    public long MonthlySpentCents { get; init; }
    public long PerCallCeilingCents { get; init; }
}

/// <summary>
/// Contract for constitutional claim evaluators used in ValidateAction.
/// </summary>
/// <remarks>
/// C-073: Every function implementing a constitutional obligation carries an annotation comment.
/// Implementations must complete within their share of the 40ms ValidateAction budget.
/// </remarks>
public interface IClaimEvaluator
{
    /// <summary>Constitutional claim ID this evaluator enforces (e.g., "C-043").</summary>
    string ClaimId { get; }

    /// <summary>
    /// Which action types trigger this evaluator.
    /// Empty set = applies to ALL action types.
    /// </summary>
    IReadOnlySet<string> ApplicableActionTypes { get; }

    /// <summary>
    /// Evaluate whether the proposed action is constitutionally permitted.
    /// MUST NOT perform network I/O — only use data pre-loaded in EvaluationContext.
    /// </summary>
    /// <param name="ctx">Pre-populated evaluation context.</param>
    /// <param name="ct">Cancellation token (honours 40ms budget).</param>
    Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct);
}