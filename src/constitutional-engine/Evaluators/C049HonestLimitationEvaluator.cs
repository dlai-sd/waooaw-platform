// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator — Honest Limitation
// constitutional_basis: C-049 (Honest Limitation)
using System.Globalization;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 Honest Limitation — denies or escalates when the agent is operating beyond
/// its demonstrated capability or confidence boundary.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    public string ClaimId => "C-049";

    private const string CapabilityExceededKey      = "capability_exceeded";
    private const string ConfidenceScoreKey          = "confidence_score";
    private const string MinHistoryRequiredKey       = "min_history_required";
    private const string PriorApprovalCountKey       = "prior_approval_count";
    private const double EscalateConfidenceThreshold = 0.70;

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // ── 1. Explicit capability-exceeded flag ─────────────────────────────
        var capabilityExceededRaw = ctx.GetParameter(CapabilityExceededKey);
        if (string.Equals(capabilityExceededRaw, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId:  ClaimId,
                Verdict:  EvaluationVerdict.Deny,
                Reason:   "C-049: capability_exceeded flag is set — agent must not proceed beyond declared capability boundary."));
        }

        // ── 2. Confidence score below escalation threshold ───────────────────
        var confidenceRaw = ctx.GetParameter(ConfidenceScoreKey);
        if (confidenceRaw is not null)
        {
            if (!double.TryParse(confidenceRaw, NumberStyles.Float, CultureInfo.InvariantCulture, out var confidenceScore))
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId:  ClaimId,
                    Verdict:  EvaluationVerdict.Escalate,
                    Reason:   $"C-049: confidence_score '{confidenceRaw}' could not be parsed — escalating for human review."));
            }

            if (confidenceScore < EscalateConfidenceThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId:  ClaimId,
                    Verdict:  EvaluationVerdict.Escalate,
                    Reason:   $"C-049: confidence_score {confidenceScore:F4} is below required threshold {EscalateConfidenceThreshold} — escalating for human review."));
            }
        }

        // ── 3. Insufficient prior-approval history ───────────────────────────
        var minHistoryRaw    = ctx.GetParameter(MinHistoryRequiredKey);
        var priorApprovalRaw = ctx.GetParameter(PriorApprovalCountKey);

        if (minHistoryRaw is not null && priorApprovalRaw is not null)
        {
            var minParsed   = int.TryParse(minHistoryRaw,    out var minRequired);
            var priorParsed = int.TryParse(priorApprovalRaw, out var priorCount);

            if (!minParsed || !priorParsed)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId:  ClaimId,
                    Verdict:  EvaluationVerdict.Escalate,
                    Reason:   $"C-049: min_history_required or prior_approval_count could not be parsed ('{minHistoryRaw}', '{priorApprovalRaw}') — escalating for human review."));
            }

            if (priorCount < minRequired)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId:  ClaimId,
                    Verdict:  EvaluationVerdict.Escalate,
                    Reason:   $"C-049: prior_approval_count {priorCount} is below min_history_required {minRequired} — agent lacks sufficient approval history for autonomous execution."));
            }
        }

        // ── 4. All honest-limitation checks passed ───────────────────────────
        return Task.FromResult(new EvaluationResult(
            ClaimId:  ClaimId,
            Verdict:  EvaluationVerdict.Allow,
            Reason:   "C-049: agent is operating within its declared capability and confidence boundary."));
    }
}