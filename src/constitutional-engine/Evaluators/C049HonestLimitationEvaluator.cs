// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator — Honest Limitation
// constitutional_basis: C-049 (Honest Limitation), C-059 (Traceability)

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 Honest Limitation evaluator.
/// Denies or escalates any action where the agent signals it has exceeded its capability
/// or lacks sufficient confidence / approval history to proceed without human oversight.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // ── Constitutional claim ────────────────────────────────────────────────
    public string ClaimId => "C-049";

    // ── Parameter keys (sourced from ctx.ActionParameters JSON) ────────────
    private const string CapabilityExceededKey      = "capability_exceeded";
    private const string ConfidenceScoreKey         = "confidence_score";
    private const string MinHistoryRequiredKey      = "min_history_required";
    private const string PriorApprovalCountKey      = "prior_approval_count";

    // ── Thresholds ──────────────────────────────────────────────────────────
    /// <summary>
    /// Confidence scores below this threshold trigger an Escalate verdict —
    /// the agent is uncertain enough that a human must review before proceeding.
    /// </summary>
    private const double EscalateConfidenceThreshold = 0.70;

    // ── Evaluation ──────────────────────────────────────────────────────────
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // ── 1. Explicit capability-exceeded flag ────────────────────────────
        // Any truthy value ("true", "1", "yes") means the agent itself
        // acknowledges it cannot perform the action reliably → hard DENY.
        var capabilityExceededRaw = ctx.GetParameter(CapabilityExceededKey);
        if (IsTrue(capabilityExceededRaw))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId:  ClaimId,
                Verdict:  EvaluationVerdict.Deny,
                Reason:   "C-049: Agent signalled capability_exceeded=true — action denied. " +
                          "The agent must not proceed beyond its verified capability boundary."));
        }

        // ── 2. Confidence score below escalation threshold ──────────────────
        // A low confidence score means the agent is uncertain; escalate so a
        // human can decide rather than letting a low-confidence action execute.
        var confidenceRaw = ctx.GetParameter(ConfidenceScoreKey);
        if (confidenceRaw is not null)
        {
            if (!double.TryParse(confidenceRaw,
                    System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out var confidenceScore))
            {
                // Unparseable score is treated conservatively as zero → escalate.
                return Task.FromResult(new EvaluationResult(
                    ClaimId: ClaimId,
                    Verdict: EvaluationVerdict.Escalate,
                    Reason:  $"C-049: confidence_score value '{confidenceRaw}' is not a valid number — " +
                             "escalating to human review per honest-limitation principle."));
            }

            if (confidenceScore < EscalateConfidenceThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId: ClaimId,
                    Verdict: EvaluationVerdict.Escalate,
                    Reason:  $"C-049: confidence_score {confidenceScore:F4} is below the " +
                             $"escalation threshold of {EscalateConfidenceThreshold:F2}. " +
                             "Escalating to human review."));
            }
        }

        // ── 3. Insufficient approval history ───────────────────────────────
        // If the action requires a minimum number of prior approvals before the
        // agent may proceed autonomously, verify that the threshold is met.
        var minHistoryRaw      = ctx.GetParameter(MinHistoryRequiredKey);
        var priorApprovalRaw   = ctx.GetParameter(PriorApprovalCountKey);

        if (minHistoryRaw is not null || priorApprovalRaw is not null)
        {
            // Default to 0 when one side is absent — conservative interpretation.
            if (!int.TryParse(minHistoryRaw,
                    System.Globalization.NumberStyles.Integer,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out var minHistory))
            {
                minHistory = 0;
            }

            if (!int.TryParse(priorApprovalRaw,
                    System.Globalization.NumberStyles.Integer,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out var priorApprovals))
            {
                priorApprovals = 0;
            }

            if (priorApprovals < minHistory)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId: ClaimId,
                    Verdict: EvaluationVerdict.Escalate,
                    Reason:  $"C-049: prior_approval_count ({priorApprovals}) is below " +
                             $"min_history_required ({minHistory}). " +
                             "Agent lacks sufficient approval history — escalating to human review."));
            }
        }

        // ── 4. All honest-limitation checks passed → allow ─────────────────
        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason:  "C-049: No honest-limitation signals detected. " +
                     "Capability within bounds, confidence sufficient, approval history adequate."));
    }

    // ── Helpers ─────────────────────────────────────────────────────────────

    /// <summary>
    /// Returns true when <paramref name="value"/> represents a truthy boolean
    /// ("true", "1", "yes" — case-insensitive).  Null/absent → false.
    /// </summary>
    private static bool IsTrue(string? value)
    {
        if (value is null) return false;
        return value.Equals("true", StringComparison.OrdinalIgnoreCase)
            || value.Equals("1",    StringComparison.Ordinal)
            || value.Equals("yes",  StringComparison.OrdinalIgnoreCase);
    }
}