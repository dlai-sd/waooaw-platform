// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator — Honest Limitation
// constitutional_basis: C-049 (Honest Limitation)

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 Honest Limitation: the agent must not proceed when it has flagged capability
/// exceedance, insufficient confidence, or inadequate approval history.
/// Deny  — capability_exceeded == "true"
/// Escalate — confidence_score below threshold OR prior approvals below minimum history
/// Allow — all checks pass
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
        // ── 1. Capability-exceeded flag — explicit DENY ───────────────────────────
        var capabilityExceededRaw = ctx.GetParameter(CapabilityExceededKey);
        if (string.Equals(capabilityExceededRaw, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-049: Agent flagged capability_exceeded=true — action exceeds declared competency boundary."));
        }

        // ── 2. Confidence score — low confidence → ESCALATE ──────────────────────
        var confidenceRaw = ctx.GetParameter(ConfidenceScoreKey);
        if (confidenceRaw is not null)
        {
            if (!double.TryParse(confidenceRaw,
                    System.Globalization.NumberStyles.Any,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out var confidenceScore))
            {
                // Unparseable score is treated as zero confidence — escalate
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: confidence_score value '{confidenceRaw}' could not be parsed — escalating to human review."));
            }

            if (confidenceScore < EscalateConfidenceThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: confidence_score {confidenceScore:F4} is below the {EscalateConfidenceThreshold:F2} threshold — escalating to human review."));
            }
        }

        // ── 3. Prior approval history — insufficient history → ESCALATE ──────────
        var minHistoryRaw     = ctx.GetParameter(MinHistoryRequiredKey);
        var priorApprovalRaw  = ctx.GetParameter(PriorApprovalCountKey);

        if (minHistoryRaw is not null && priorApprovalRaw is not null)
        {
            var parsedMin   = int.TryParse(minHistoryRaw,    out var minRequired)    ? (int?)minRequired    : null;
            var parsedPrior = int.TryParse(priorApprovalRaw, out var priorApprovals) ? (int?)priorApprovals : null;

            if (parsedMin is null)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: min_history_required value '{minHistoryRaw}' could not be parsed — escalating to human review."));
            }

            if (parsedPrior is null)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: prior_approval_count value '{priorApprovalRaw}' could not be parsed — escalating to human review."));
            }

            if (parsedPrior.Value < parsedMin.Value)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: prior_approval_count {parsedPrior.Value} is below min_history_required {parsedMin.Value} — escalating to human review."));
            }
        }
        else if (minHistoryRaw is not null && priorApprovalRaw is null)
        {
            // Minimum history specified but no count provided — conservative escalation
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-049: min_history_required is set to '{minHistoryRaw}' but prior_approval_count was not provided — escalating to human review."));
        }

        // ── 4. All checks passed ──────────────────────────────────────────────────
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-049: Honest limitation checks passed — capability within bounds, confidence sufficient, approval history adequate."));
    }
}