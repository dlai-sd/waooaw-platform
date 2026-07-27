// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator — Honest Limitation
// Constitutional basis: C-049 (Honest Limitation), C-059 (Traceability)

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-049 (Honest Limitation): the agent must acknowledge uncertainty and escalate
/// to human oversight when confidence falls below the configured threshold or prior approval
/// history is insufficient. Escalate (not Deny) is the correct verdict — the action is
/// uncertain, not prohibited.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    private const string ConfidenceScoreKey     = "confidence_score";
    private const string ConfiguredThresholdKey = "configured_threshold";
    private const string PriorApprovalCountKey  = "prior_approval_count";
    private const string MinHistoryRequiredKey  = "min_history_required";

    public string ClaimId => "C-049";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // ── Confidence score gate ────────────────────────────────────────────────────
        // Both parameters must be present for the gate to apply.
        // If only one is present it indicates a misconfigured caller; escalate to be safe.
        var confidenceRaw  = ctx.GetParameter(ConfidenceScoreKey);
        var thresholdRaw   = ctx.GetParameter(ConfiguredThresholdKey);

        if (confidenceRaw is not null || thresholdRaw is not null)
        {
            // At least one synthetic-approval parameter was supplied — evaluate fully.
            if (!float.TryParse(confidenceRaw, System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture, out var confidenceScore)
                || !float.TryParse(thresholdRaw, System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture, out var configuredThreshold))
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: Synthetic approval parameters present but unparseable " +
                    $"(confidence_score='{confidenceRaw}', configured_threshold='{thresholdRaw}'). " +
                    "Escalating to human oversight per honest-limitation principle."));
            }

            if (confidenceScore < configuredThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: Confidence score {confidenceScore:F4} is below configured threshold " +
                    $"{configuredThreshold:F4}. Agent acknowledges limitation — escalating to human oversight."));
            }
        }

        // ── Prior approval history gate ──────────────────────────────────────────────
        // Both parameters must be present for the gate to apply.
        var priorApprovalRaw = ctx.GetParameter(PriorApprovalCountKey);
        var minHistoryRaw    = ctx.GetParameter(MinHistoryRequiredKey);

        if (priorApprovalRaw is not null || minHistoryRaw is not null)
        {
            if (!int.TryParse(priorApprovalRaw, out var priorApprovalCount)
                || !int.TryParse(minHistoryRaw, out var minHistoryRequired))
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: Approval history parameters present but unparseable " +
                    $"(prior_approval_count='{priorApprovalRaw}', min_history_required='{minHistoryRaw}'). " +
                    "Escalating to human oversight per honest-limitation principle."));
            }

            if (priorApprovalCount < minHistoryRequired)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: Prior approval count {priorApprovalCount} is below minimum history " +
                    $"required {minHistoryRequired}. Insufficient track record — escalating to human oversight."));
            }
        }

        // ── All gates passed (or no synthetic-approval context was supplied) ─────────
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-049: Confidence and approval history within acceptable limits."));
    }
}