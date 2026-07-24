// Implements: architecture/reference/ce-validate-action-evaluators.md §Evaluator Interface
// constitutional_basis: C-023 (Evidence First), C-041 (Tool Authorization), C-043 (Budget Ceiling),
//                       C-048 (Non-Exploitation), C-062 (AI Security)

#nullable enable

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Contract for a constitutional claim evaluator that enforces a single claim
/// at ValidateAction runtime. Implementations MUST NOT perform network I/O —
/// evaluation uses only data extracted from ValidateActionRequest.
/// </summary>
public interface IClaimEvaluator
{
    /// <summary>Constitutional claim ID this evaluator enforces (e.g., "C-041").</summary>
    string ClaimId { get; }

    /// <summary>
    /// Action types that trigger this evaluator.
    /// Empty set = applies to ALL action types.
    /// </summary>
    IReadOnlySet<string> ApplicableActionTypes { get; }

    /// <summary>
    /// Evaluate whether the proposed action is constitutionally permitted.
    /// MUST complete within its share of the 40 ms ValidateAction budget.
    /// MUST NOT access any external resource — only fields on <paramref name="ctx"/>.
    /// </summary>
    Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct);
}

/// <summary>Immutable result returned by a single claim evaluator.</summary>
/// <param name="Decision">The constitutional verdict.</param>
/// <param name="Reason">Required when Decision == Deny — persisted to audit record.</param>
/// <param name="EvidenceHint">Optional extra context for the evidence record.</param>
public sealed record EvaluationResult(
    EvaluationDecision Decision,
    string? Reason = null,
    string? EvidenceHint = null);

/// <summary>Constitutional verdict produced by an evaluator.</summary>
public enum EvaluationDecision
{
    /// <summary>Action is constitutionally permitted.</summary>
    Authorized,

    /// <summary>Action is constitutionally prohibited — request denied.</summary>
    Deny,

    /// <summary>Action is uncertain — escalate to human (C-049 path).</summary>
    Escalate
}