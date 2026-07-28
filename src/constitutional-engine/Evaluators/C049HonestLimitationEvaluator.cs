// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator — Honest Limitation
// Constitutional basis: C-049 (Honest Limitation)
using System.Globalization;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-049 (Honest Limitation): the agent must not proceed when it has declared that
/// its capability is exceeded, its confidence is too low, or it lacks sufficient prior-approval
/// history to act autonomously.  Uncertain cases are escalated to a human rather than denied
/// outright, preserving the agent's ability to act once a human grants explicit approval.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    public string ClaimId => "C-049";

    private const string CapabilityExceededKey       = "capability_exceeded";
    private const string ConfidenceScoreKey          = "confidence_score";
    private const string MinHistoryRequiredKey       = "min_history_required";
    private const string PriorApprovalCountKey       = "prior_approval_count";
    private const double EscalateConfidenceThreshold = 0.70;

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // ── Gate 1: explicit capability-exceeded flag ──────────────────────────────
        // If the caller (or a prior enrichment step) has flagged that the proposed
        // action is beyond what this agent can reliably perform, we must DENY.
        // Honest Limitation means we do not attempt things we cannot do.
        if (IsTrue(ctx.GetParameter(CapabilityExceededKey)))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-049: Action exceeds declared capability boundary — honest limitation requires denial."));
        }

        // ── Gate 2: confidence score too low → ESCALATE ────────────────────────────
        // A score below 0.70 does not warrant outright denial; the action may still be
        // valid once a human reviews the uncertainty.  Escalate rather than block.
        var confidenceRaw = ctx.GetParameter(ConfidenceScoreKey);
        if (confidenceRaw is not null &&
            double.TryParse(
                confidenceRaw,
                NumberStyles.Float,
                CultureInfo.InvariantCulture,
                out var confidence) &&
            confidence < EscalateConfidenceThreshold)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-049: Confidence score {confidence:F2} is below threshold "
                + $"{EscalateConfidenceThreshold:F2} — escalating for human review."));
        }

        // ── Gate 3: insufficient prior-approval history → ESCALATE ────────────────
        // When an action requires N prior approvals to be trusted autonomously and the
        // agent has fewer, a human must review before we proceed.
        var minHistoryRaw  = ctx.GetParameter(MinHistoryRequiredKey);
        var priorCountRaw  = ctx.GetParameter(PriorApprovalCountKey);

        if (minHistoryRaw is not null &&
            int.TryParse(minHistoryRaw, NumberStyles.Integer, CultureInfo.InvariantCulture, out var minHistory) &&
            minHistory > 0)
        {
            var priorCount = 0;
            if (priorCountRaw is not null)
            {
                // Ignore parse failure — treat as 0 (safest default).
                int.TryParse(priorCountRaw, NumberStyles.Integer, CultureInfo.InvariantCulture, out priorCount);
            }

            if (priorCount < minHistory)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: Prior approval count {priorCount} is below minimum required "
                    + $"{minHistory} — escalating for human review."));
            }
        }

        // ── All gates passed → ALLOW ───────────────────────────────────────────────
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-049: Action is within declared capability boundaries and confidence thresholds."));
    }

    private static bool IsTrue(string? value) =>
        string.Equals(value, "true", StringComparison.OrdinalIgnoreCase);
}