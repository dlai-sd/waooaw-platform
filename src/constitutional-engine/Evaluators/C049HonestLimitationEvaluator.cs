// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator — Honest Limitation
// constitutional_basis: C-049 (Honest Limitation), C-059 (Traceability), C-023 (Evidence First)

using Waooaw.ConstitutionalEngine.Evaluators;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-049 (Honest Limitation): the agent must declare when it lacks
/// sufficient confidence or capability, and must escalate rather than proceed
/// when below the confidence threshold or when prior approval history is insufficient.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    private const string CapabilityExceededKey       = "capability_exceeded";
    private const string ConfidenceScoreKey          = "confidence_score";
    private const string MinHistoryRequiredKey       = "min_history_required";
    private const string PriorApprovalCountKey       = "prior_approval_count";
    private const double EscalateConfidenceThreshold = 0.70;

    public string ClaimId => "C-049";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // 1. Capability exceeded — agent self-reports it cannot perform this action.
        //    Hard DENY: proceeding would violate C-049 honesty obligation.
        var capabilityExceededRaw = ctx.GetParameter(CapabilityExceededKey);
        if (IsTrue(capabilityExceededRaw))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: "C-049: Agent has declared this action exceeds its capability boundary. " +
                        "Proceeding would violate the honest limitation constitutional claim."));
        }

        // 2. Confidence score below threshold — agent is uncertain.
        //    Escalate to human (Sujay) rather than allow or deny autonomously.
        var confidenceRaw = ctx.GetParameter(ConfidenceScoreKey);
        if (confidenceRaw is not null)
        {
            if (double.TryParse(confidenceRaw,
                    System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out var confidenceScore))
            {
                if (confidenceScore < EscalateConfidenceThreshold)
                {
                    return Task.FromResult(new EvaluationResult(
                        ClaimId: ClaimId,
                        Verdict: EvaluationVerdict.Escalate,
                        Reason: $"C-049: Confidence score {confidenceScore:F4} is below the " +
                                $"required threshold of {EscalateConfidenceThreshold:F2}. " +
                                "Action requires human review before proceeding."));
                }
            }
            else
            {
                // Unparseable confidence score — treat as missing confidence → Escalate.
                return Task.FromResult(new EvaluationResult(
                    ClaimId: ClaimId,
                    Verdict: EvaluationVerdict.Escalate,
                    Reason: $"C-049: Confidence score parameter '{confidenceRaw}' could not be parsed. " +
                            "Cannot confirm sufficient confidence — escalating for human review."));
            }
        }

        // 3. Prior approval history check — ensure the agent has sufficient precedent
        //    before autonomous execution. Escalate when history is thin.
        var minHistoryRaw    = ctx.GetParameter(MinHistoryRequiredKey);
        var priorApprovalRaw = ctx.GetParameter(PriorApprovalCountKey);

        if (minHistoryRaw is not null && priorApprovalRaw is not null)
        {
            if (int.TryParse(minHistoryRaw,    out var minHistory)
             && int.TryParse(priorApprovalRaw, out var priorApprovals))
            {
                if (priorApprovals < minHistory)
                {
                    return Task.FromResult(new EvaluationResult(
                        ClaimId: ClaimId,
                        Verdict: EvaluationVerdict.Escalate,
                        Reason: $"C-049: Prior approval count ({priorApprovals}) is below the " +
                                $"minimum required history ({minHistory}). " +
                                "Insufficient precedent for autonomous execution — escalating."));
                }
            }
        }
        else if (minHistoryRaw is not null && priorApprovalRaw is null)
        {
            // min_history_required is declared but no prior_approval_count provided — cannot satisfy.
            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Escalate,
                Reason: "C-049: Minimum history requirement is declared but prior approval count " +
                        "is absent. Cannot confirm sufficient precedent — escalating."));
        }

        // All C-049 checks passed — Allow.
        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: "C-049: Capability within bounds, confidence meets threshold, " +
                    "and prior approval history is sufficient."));
    }

    private static bool IsTrue(string? value) =>
        string.Equals(value, "true", StringComparison.OrdinalIgnoreCase)
     || string.Equals(value, "1",    StringComparison.Ordinal)
     || string.Equals(value, "yes",  StringComparison.OrdinalIgnoreCase);
}