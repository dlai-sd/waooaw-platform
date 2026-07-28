// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator — Honest Limitation
// Constitutional basis: C-049 (Honest Limitation), C-059 (Traceability)
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-049 (Honest Limitation): the agent must not proceed when it lacks sufficient
/// confidence or historical approval basis to act. Escalates to human review when confidence
/// is below threshold or prior approvals are insufficient; denies when capability is explicitly
/// flagged as exceeded.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    public string ClaimId => "C-049";

    private const string CapabilityExceededKey       = "capability_exceeded";
    private const string ConfidenceScoreKey           = "confidence_score";
    private const string MinHistoryRequiredKey        = "min_history_required";
    private const string PriorApprovalCountKey        = "prior_approval_count";
    private const double EscalateConfidenceThreshold  = 0.70;

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // 1. Hard deny: capability_exceeded flag set to "true"
        var capabilityExceeded = ctx.GetParameter(CapabilityExceededKey);
        if (string.Equals(capabilityExceeded, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId:  "C-049",
                Verdict:  EvaluationVerdict.Deny,
                Reason:   "C-049: Agent capability explicitly flagged as exceeded for this action; action denied per Honest Limitation principle."
            ));
        }

        // 2. Escalate: confidence score below threshold
        var confidenceRaw = ctx.GetParameter(ConfidenceScoreKey);
        if (confidenceRaw is not null &&
            double.TryParse(confidenceRaw, System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture, out var confidence))
        {
            if (confidence < EscalateConfidenceThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId: "C-049",
                    Verdict: EvaluationVerdict.Escalate,
                    Reason:  $"C-049: Confidence score {confidence:F4} is below required threshold {EscalateConfidenceThreshold:F4}; escalating to human review."
                ));
            }
        }

        // 3. Escalate: insufficient prior approval history
        var minHistoryRaw     = ctx.GetParameter(MinHistoryRequiredKey);
        var priorApprovalRaw  = ctx.GetParameter(PriorApprovalCountKey);

        if (minHistoryRaw is not null && priorApprovalRaw is not null)
        {
            if (int.TryParse(minHistoryRaw,    out var minHistory) &&
                int.TryParse(priorApprovalRaw, out var priorApprovals))
            {
                if (priorApprovals < minHistory)
                {
                    return Task.FromResult(new EvaluationResult(
                        ClaimId: "C-049",
                        Verdict: EvaluationVerdict.Escalate,
                        Reason:  $"C-049: Prior approval count {priorApprovals} is below minimum required history {minHistory}; escalating to human review."
                    ));
                }
            }
        }

        // 4. All checks passed — allow
        return Task.FromResult(new EvaluationResult(
            ClaimId: "C-049",
            Verdict: EvaluationVerdict.Allow,
            Reason:  "C-049: Honest limitation checks passed; capability not exceeded and confidence is sufficient."
        ));
    }
}