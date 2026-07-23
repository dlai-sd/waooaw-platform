// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-041 (Tool Authorization), C-043 (Budget Ceiling),
//                       C-048 (Non-Exploitation), C-049 (Honest Limitation), C-051 (Resource Transparency),
//                       C-062 (AI Security), ADR-001 (gRPC Constitutional Engine)

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Contract for all constitutional claim evaluators registered in the CE.
/// Each evaluator enforces exactly one constitutional claim at runtime.
/// </summary>
/// <remarks>
/// C-073: Every function implementing a constitutional obligation carries an annotation comment.
/// Implementations MUST NOT perform network I/O — only DB reads via EvaluationContext.
/// Must complete within its share of the 40ms ValidateAction budget.
/// </remarks>
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
    /// Evaluate whether the proposed action is constitutionally permitted.
    /// </summary>
    /// <param name="ctx">Evaluation context containing request data and DB-backed accessors.</param>
    /// <param name="ct">Cancellation token — honour the 40ms budget ceiling.</param>
    /// <returns>EvaluationResult with Decision and optional Reason/EvidenceHint.</returns>
    Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct);
}

/// <summary>Result returned by a claim evaluator.</summary>
/// <param name="Decision">The constitutional decision.</param>
/// <param name="Reason">Required when Decision == Deny — logged in audit record.</param>
/// <param name="EvidenceHint">Optional extra context for the evidence record.</param>
public record EvaluationResult(
    EvaluationDecision Decision,
    string? Reason = null,
    string? EvidenceHint = null
);

/// <summary>Possible outcomes from a claim evaluator.</summary>
public enum EvaluationDecision
{
    /// <summary>Action is constitutionally permitted by this claim.</summary>
    Authorized,

    /// <summary>Action is constitutionally prohibited — short-circuit and deny.</summary>
    Deny,

    /// <summary>
    /// Action is uncertain — forward to human (Sujay) via C-049 path.
    /// Treated as a soft deny pending human review.
    /// </summary>
    Escalate
}