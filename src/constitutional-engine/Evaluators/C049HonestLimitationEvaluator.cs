// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator — Honest Limitation
// Constitutional basis: C-049 (Honest Limitation)
using Waooaw.ConstitutionalEngine.Evaluators;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 Honest Limitation: the agent must not proceed when it has exceeded its stated
/// capability boundary or when its confidence is insufficient to act without human review.
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
        // --- 1. Hard capability exceeded flag ---
        var capabilityExceededRaw = ctx.GetParameter(CapabilityExceededKey);
        if (string.Equals(capabilityExceededRaw, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId:  "C-049",
                Verdict:  EvaluationVerdict.Deny,
                Reason:   "C-049: capability_exceeded flag is set — agent has declared this action beyond its competence boundary."));
        }

        // --- 2. Confidence score check ---
        var confidenceRaw = ctx.GetParameter(ConfidenceScoreKey);
        if (confidenceRaw is not null)
        {
            if (!double.TryParse(confidenceRaw, System.Globalization.NumberStyles.Any,
                    System.Globalization.CultureInfo.InvariantCulture, out var confidenceScore))
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId:  "C-049",
                    Verdict:  EvaluationVerdict.Escalate,
                    Reason:   $"C-049: confidence_score '{confidenceRaw}' could not be parsed — escalating for human review."));
            }

            if (confidenceScore < EscalateConfidenceThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId:  "C-049",
                    Verdict:  EvaluationVerdict.Escalate,
                    Reason:   $"C-049: confidence_score {confidenceScore:F4} is below escalation threshold {EscalateConfidenceThreshold} — action requires human approval."));
            }
        }

        // --- 3. Minimum history check ---
        var minHistoryRaw      = ctx.GetParameter(MinHistoryRequiredKey);
        var priorApprovalRaw   = ctx.GetParameter(PriorApprovalCountKey);

        if (minHistoryRaw is not null)
        {
            if (!int.TryParse(minHistoryRaw, out var minHistoryRequired))
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId:  "C-049",
                    Verdict:  EvaluationVerdict.Escalate,
                    Reason:   $"C-049: min_history_required '{minHistoryRaw}' could not be parsed — escalating for human review."));
            }

            if (minHistoryRequired > 0)
            {
                if (!int.TryParse(priorApprovalRaw, out var priorApprovalCount))
                {
                    // Missing or unparseable count when a minimum is declared → escalate
                    return Task.FromResult(new EvaluationResult(
                        ClaimId:  "C-049",
                        Verdict:  EvaluationVerdict.Escalate,
                        Reason:   $"C-049: min_history_required is {minHistoryRequired} but prior_approval_count is absent or invalid — escalating for human review."));
                }

                if (priorApprovalCount < minHistoryRequired)
                {
                    return Task.FromResult(new EvaluationResult(
                        ClaimId:  "C-049",
                        Verdict:  EvaluationVerdict.Escalate,
                        Reason:   $"C-049: prior_approval_count {priorApprovalCount} is below min_history_required {minHistoryRequired} — insufficient precedent to proceed autonomously."));
                }
            }
        }

        // --- All C-049 checks passed ---
        return Task.FromResult(new EvaluationResult(
            ClaimId:  "C-049",
            Verdict:  EvaluationVerdict.Allow,
            Reason:   "C-049: capability boundary respected, confidence sufficient, history requirement met."));
    }
}