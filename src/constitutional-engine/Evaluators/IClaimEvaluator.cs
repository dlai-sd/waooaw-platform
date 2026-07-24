// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-041 (Tool Authorization), C-043 (Budget Ceiling),
//                       C-048 (Non-Exploitation), C-049 (Honest Limitation), C-062 (AI Security)

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Every function implementing a constitutional obligation carries an annotation comment.
/// This interface defines the contract for all runtime claim evaluators registered in CE.
/// </summary>
public interface IClaimEvaluator
{
    /// <summary>Constitutional claim ID this evaluator enforces (e.g., "C-043").</summary>
    string ClaimId { get; }

    /// <summary>
    /// Which action types trigger this evaluator.
    /// Empty set = applies to ALL action types (use sparingly — only for universal claims like C-041).
    /// </summary>
    IReadOnlySet<string> ApplicableActionTypes { get; }

    /// <summary>
    /// C-073: Evaluate whether the proposed action is constitutionally permitted.
    /// Must complete within its share of the 40ms ValidateAction budget.
    /// MUST NOT perform network I/O — only reads pre-loaded data from EvaluationContext.
    /// </summary>
    Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct);
}

public record EvaluationResult(
    EvaluationDecision Decision,
    string? Reason = null,       // Required when Decision == Deny — logged in audit record
    string? EvidenceHint = null  // Optional: extra context for the evidence record
);

public enum EvaluationDecision
{
    Authorized,
    Deny,
    Escalate  // Action is uncertain — forward to human (Sujay) via C-049 path
}