// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator — Honest Limitation
// Constitutional basis: C-049 (Honest Limitation)
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 Honest Limitation — denies or escalates actions where the agent lacks
/// sufficient capability or confidence, enforcing honest acknowledgment of boundaries.
/// Escalate is the canonical C-049 outcome when uncertainty warrants human review.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    public string ClaimId => "C-049";

    // ActionParameters keys (JSON-encoded; extracted via ctx.GetParameter)
    private const string CapabilityExceededKey = "capability_exceeded";
    private const string ConfidenceScoreKey    = "confidence_score";
    private const string MinHistoryRequiredKey  = "min_history_required";
    private const string PriorApprovalCountKey  = "prior_approval_count";

    /// <summary>
    /// Confidence below this value triggers Escalate — agent is uncertain, not explicitly wrong.
    /// </summary>
    private const double EscalateConfidenceThreshold = 0.70;

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // ── Gate 1: Explicit capability-exceeded flag → hard Deny ─────────────────────────
        var capabilityExceeded = ctx.GetParameter(CapabilityExceededKey);
        if (string.Equals(capabilityExceeded, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-049: Action explicitly exceeds declared agent capability boundary — default deny applies."));
        }

        // ── Gate 2: Insufficient approval history → Escalate ─────────────────────────────
        var minHistoryRaw  = ctx.GetParameter(MinHistoryRequiredKey);
        var priorCountRaw  = ctx.GetParameter(PriorApprovalCountKey);

        if (int.TryParse(minHistoryRaw, out var minHistoryRequired) &&
            int.TryParse(priorCountRaw, out var priorApprovalCount) &&
            priorApprovalCount < minHistoryRequired)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-049: Insufficient approval history — {priorApprovalCount} prior approval(s), "
                + $"{minHistoryRequired} required. Escalating to human for honest-limitation review."));
        }

        // ── Gate 3: Low confidence score → Escalate ──────────────────────────────────────
        var confidenceRaw = ctx.GetParameter(ConfidenceScoreKey);
        if (double.TryParse(confidenceRaw,
                System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture,
                out var confidenceScore)
            && confidenceScore < EscalateConfidenceThreshold)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-049: Confidence score {confidenceScore:F2} is below escalation threshold "
                + $"{EscalateConfidenceThreshold:F2} — forwarding to human for review."));
        }

        // ── All gates passed → Allow ──────────────────────────────────────────────────────
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-049: Agent operating within declared capability and confidence boundaries."));
    }
}