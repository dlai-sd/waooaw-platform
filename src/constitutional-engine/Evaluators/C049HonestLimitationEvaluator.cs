// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator — Honest Limitation
// constitutional_basis: C-049 (Honest Limitation), C-059 (Traceability)
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-049 (Honest Limitation): the agent must not proceed when it has
/// exceeded its stated capability boundary, lacks sufficient confidence, or does
/// not have enough historical approvals to justify autonomous action.
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
        // 1. Hard deny when the caller explicitly signals capability has been exceeded.
        var capabilityExceededRaw = ctx.GetParameter(CapabilityExceededKey);
        if (string.Equals(capabilityExceededRaw, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: "C-049: Action denied — capability_exceeded flag is set. " +
                        "The agent has acknowledged it is operating outside its competence boundary."));
        }

        // 2. Escalate when confidence score is below the minimum acceptable threshold.
        var confidenceRaw = ctx.GetParameter(ConfidenceScoreKey);
        if (confidenceRaw is not null)
        {
            if (!double.TryParse(confidenceRaw,
                    System.Globalization.NumberStyles.Any,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out var confidenceScore))
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId: ClaimId,
                    Verdict: EvaluationVerdict.Deny,
                    Reason: $"C-049: Action denied — confidence_score '{confidenceRaw}' is not a valid number."));
            }

            if (confidenceScore < EscalateConfidenceThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId: ClaimId,
                    Verdict: EvaluationVerdict.Escalate,
                    Reason: $"C-049: Action escalated — confidence score {confidenceScore:F4} " +
                            $"is below the required threshold of {EscalateConfidenceThreshold:F2}. " +
                            "Human review required before proceeding."));
            }
        }

        // 3. Escalate when the agent does not have enough prior approval history.
        var minHistoryRaw    = ctx.GetParameter(MinHistoryRequiredKey);
        var priorApprovalRaw = ctx.GetParameter(PriorApprovalCountKey);

        if (minHistoryRaw is not null && priorApprovalRaw is not null)
        {
            if (!int.TryParse(minHistoryRaw,
                    System.Globalization.NumberStyles.Integer,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out var minHistoryRequired))
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId: ClaimId,
                    Verdict: EvaluationVerdict.Deny,
                    Reason: $"C-049: Action denied — min_history_required '{minHistoryRaw}' is not a valid integer."));
            }

            if (!int.TryParse(priorApprovalRaw,
                    System.Globalization.NumberStyles.Integer,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out var priorApprovalCount))
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId: ClaimId,
                    Verdict: EvaluationVerdict.Deny,
                    Reason: $"C-049: Action denied — prior_approval_count '{priorApprovalRaw}' is not a valid integer."));
            }

            if (priorApprovalCount < minHistoryRequired)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId: ClaimId,
                    Verdict: EvaluationVerdict.Escalate,
                    Reason: $"C-049: Action escalated — prior approval count {priorApprovalCount} " +
                            $"is below the minimum required history of {minHistoryRequired}. " +
                            "Insufficient precedent for autonomous action."));
            }
        }
        else if (minHistoryRaw is not null && priorApprovalRaw is null)
        {
            // min_history_required is specified but we have no evidence of prior approvals at all.
            if (!int.TryParse(minHistoryRaw,
                    System.Globalization.NumberStyles.Integer,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out var minHistoryRequired))
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId: ClaimId,
                    Verdict: EvaluationVerdict.Deny,
                    Reason: $"C-049: Action denied — min_history_required '{minHistoryRaw}' is not a valid integer."));
            }

            if (minHistoryRequired > 0)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId: ClaimId,
                    Verdict: EvaluationVerdict.Escalate,
                    Reason: $"C-049: Action escalated — min_history_required is {minHistoryRequired} " +
                            "but no prior_approval_count was provided. " +
                            "Cannot verify sufficient approval history; human review required."));
            }
        }

        // 4. All C-049 checks passed.
        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: "C-049: Action permitted — capability boundary respected, " +
                    "confidence meets threshold, and prior approval history is sufficient."));
    }
}