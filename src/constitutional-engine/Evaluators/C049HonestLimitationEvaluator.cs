// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator — Honest Limitation
// Constitutional basis: C-049 (Honest Limitation), C-059 (Traceability)
using System.Globalization;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 Honest Limitation evaluator.
/// Enforces the constitutional requirement that the agent must not claim capabilities
/// it does not possess and must escalate to human review when confidence is insufficient.
///
/// Escalate is the primary verdict — it routes uncertain actions to Sujay for review
/// rather than issuing a hard deny when the agent is uncertain but not provably wrong.
/// Deny is reserved for explicit capability-breach declarations.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // ── Parameter keys (extracted from JSON-encoded ctx.ActionParameters via GetParameter) ──
    private const string ConfidenceScoreKey = "confidence_score";
    private const string CapabilityBreachKey = "capability_breach";
    private const string RequiresHumanReviewKey = "requires_human_review";

    /// <summary>
    /// Minimum agent-reported confidence required to proceed without human escalation.
    /// Actions below this threshold are routed to the C-049 Escalate path.
    /// </summary>
    private const double DefaultConfidenceThreshold = 0.70;

    public string ClaimId => "C-049";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // ── 1. Explicit capability-breach flag ───────────────────────────────────────────
        // If the calling agent (or upstream validator) has declared that this action
        // exceeds the agent's stated capabilities, issue a hard Deny immediately.
        var breachFlag = ctx.GetParameter(CapabilityBreachKey);
        if (string.Equals(breachFlag, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Deny(
                "Agent declared a capability breach — action falls outside stated limitations. " +
                "Constitutional claim C-049 (Honest Limitation) requires rejection.");
        }

        // ── 2. Explicit human-review request ────────────────────────────────────────────
        // The agent may self-flag uncertainty without providing a numeric confidence score.
        var reviewFlag = ctx.GetParameter(RequiresHumanReviewKey);
        if (string.Equals(reviewFlag, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Escalate(
                "Action flagged as requiring human review by the executing agent. " +
                "Escalating to human principal per C-049 (Honest Limitation).");
        }

        // ── 3. Confidence-score gate ─────────────────────────────────────────────────────
        // Agents that surface a confidence_score allow CE to enforce the C-049 threshold
        // automatically. Absence of a confidence_score is not itself a violation.
        var confidenceRaw = ctx.GetParameter(ConfidenceScoreKey);
        if (confidenceRaw is not null)
        {
            if (!double.TryParse(
                    confidenceRaw,
                    NumberStyles.Any,
                    CultureInfo.InvariantCulture,
                    out var confidence))
            {
                return Escalate(
                    $"confidence_score parameter '{confidenceRaw}' is not a valid numeric value. " +
                    "Escalating for human review rather than assuming confidence (C-049).");
            }

            if (confidence < DefaultConfidenceThreshold)
            {
                return Escalate(
                    $"Agent-reported confidence {confidence:F2} is below the C-049 threshold " +
                    $"{DefaultConfidenceThreshold:F2}. Escalating to human principal for review.");
            }
        }

        // ── 4. All checks passed ─────────────────────────────────────────────────────────
        return Allow("C-049 Honest Limitation check passed — no capability breach or low-confidence flag detected.");
    }

    // ── Verdict helpers ──────────────────────────────────────────────────────────────────

    private Task<EvaluationResult> Allow(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, reason));

    private Task<EvaluationResult> Deny(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));

    private Task<EvaluationResult> Escalate(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Escalate, reason));
}