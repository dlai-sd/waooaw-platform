// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator — Honest Limitation
// constitutional_basis: C-049 (Honest Limitation), C-059 (Traceability)

using System.Globalization;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-049 (Honest Limitation): the agent must not execute actions it cannot reliably
/// perform, must not overstate its confidence, and must escalate to human oversight when
/// the confidence score is below the configured threshold or when the caller explicitly
/// signals that human review is required.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    private const string ConfidenceScoreKey     = "confidence_score";
    private const string CapabilityBreachKey    = "capability_breach";
    private const string RequiresHumanReviewKey = "requires_human_review";
    private const double DefaultConfidenceThreshold = 0.70;

    public string ClaimId => "C-049";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // ── 1. Capability breach ─────────────────────────────────────────────────────────
        // Agent has signalled it is attempting an action outside its declared capability.
        // Hard DENY — attempting the action would produce unreliable output (C-049 §1).
        var capabilityBreach = ctx.GetParameter(CapabilityBreachKey);
        if (string.Equals(capabilityBreach, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Deny(
                "C-049: capability_breach=true — agent must not execute actions " +
                "outside its declared capability boundary.");
        }

        // ── 2. Explicit human-review flag ────────────────────────────────────────────────
        // Caller or a prior evaluator has flagged that a human must review before proceeding.
        // ESCALATE per C-049 §2 honest-limitation escalation path.
        var requiresHumanReview = ctx.GetParameter(RequiresHumanReviewKey);
        if (string.Equals(requiresHumanReview, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Escalate(
                "C-049: requires_human_review=true — action escalated to human oversight " +
                "before execution is permitted.");
        }

        // ── 3. Confidence score threshold ────────────────────────────────────────────────
        // When a confidence score is supplied, it must meet the constitutional floor.
        // An unparseable value is treated as a hard DENY (malformed context is untrustworthy).
        // A parseable value below threshold triggers ESCALATE (uncertain → human review).
        var confidenceRaw = ctx.GetParameter(ConfidenceScoreKey);
        if (confidenceRaw is not null)
        {
            if (!double.TryParse(
                    confidenceRaw,
                    NumberStyles.Any,
                    CultureInfo.InvariantCulture,
                    out var confidence))
            {
                return Deny(
                    $"C-049: confidence_score value '{confidenceRaw}' is not a valid " +
                    "numeric value — context is malformed, action denied.");
            }

            if (confidence < DefaultConfidenceThreshold)
            {
                return Escalate(
                    $"C-049: confidence_score {confidence:F4} is below constitutional " +
                    $"threshold {DefaultConfidenceThreshold:F2} — escalating to human review.");
            }
        }

        // ── 4. No honest-limitation flags raised ─────────────────────────────────────────
        return Allow(
            "C-049: no capability breach, no human-review requirement, and confidence score " +
            "(if supplied) meets the constitutional threshold — action permitted.");
    }

    // ── Private result helpers ────────────────────────────────────────────────────────────

    private Task<EvaluationResult> Allow(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, reason));

    private Task<EvaluationResult> Deny(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));

    private Task<EvaluationResult> Escalate(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Escalate, reason));
}