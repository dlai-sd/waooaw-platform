// Implements: architecture/reference/ce-validate-action-evaluators.md §Evaluator Interface
// constitutional_basis: C-041 (Tool Authorization), C-059 (Traceability), C-073 (Annotation)

using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Decision returned by a claim evaluator.
/// </summary>
public enum EvaluationDecision
{
    /// <summary>Action is constitutionally permitted by this evaluator.</summary>
    Authorized,

    /// <summary>Action is constitutionally prohibited — short-circuit and deny.</summary>
    Deny,

    /// <summary>
    /// Action is uncertain — escalate to human (Sujay) via C-049 path.
    /// </summary>
    Escalate
}

/// <summary>
/// Result produced by a single claim evaluator.
/// </summary>
/// <param name="Decision">The evaluator's decision.</param>
/// <param name="Reason">Required when Decision == Deny. Logged in audit record.</param>
/// <param name="EvidenceHint">Optional extra context for the evidence record.</param>
public record EvaluationResult(
    EvaluationDecision Decision,
    string? Reason = null,
    string? EvidenceHint = null
);

/// <summary>
/// Contract for all constitutional claim evaluators registered in CE.
/// Each evaluator enforces exactly one constitutional claim at runtime.
/// </summary>
/// <remarks>
/// C-073: Every function implementing a constitutional obligation carries an annotation comment.
/// MUST NOT perform network I/O — only DB reads via the provided EvaluationContext.
/// Must complete within its share of the 40 ms ValidateAction budget.
/// </remarks>
public interface IClaimEvaluator
{
    /// <summary>Constitutional claim ID this evaluator enforces (e.g., "C-043").</summary>
    string ClaimId { get; }

    /// <summary>
    /// Which action types trigger this evaluator.
    /// Empty set = applies to ALL action types (use sparingly — only for universal claims).
    /// </summary>
    IReadOnlySet<string> ApplicableActionTypes { get; }

    /// <summary>
    /// Evaluate whether the proposed action is constitutionally permitted.
    /// </summary>
    /// <param name="ctx">Evaluation context — pre-loaded from DB, no further I/O allowed.</param>
    /// <param name="ct">Cancellation token — honour the 40 ms budget.</param>
    Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct);
}