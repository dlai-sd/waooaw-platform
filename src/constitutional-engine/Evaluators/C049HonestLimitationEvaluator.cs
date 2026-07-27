// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049
// Constitutional basis: C-049 (Honest Limitation)

using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 Honest Limitation Evaluator.
/// When the agent is synthesising an approval that would normally require human judgment,
/// it MUST escalate rather than self-approve if its confidence is below threshold or if
/// it has insufficient prior approval history to establish reliable pattern recognition.
/// Applies to action type SYNTHETIC_APPROVAL.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    private const string SyntheticApprovalAction = "SYNTHETIC_APPROVAL";

    /// <summary>Fall-back threshold if not supplied in action parameters.</summary>
    private const float DefaultConfidenceThreshold = 0.80f;

    /// <summary>Fall-back minimum history count if not supplied in action parameters.</summary>
    private const int DefaultMinHistoryRequired = 3;

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        _logger = logger;
    }

    public string ClaimId => "C-049";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-049 only gates synthetic-approval actions where AI substitutes for human judgment.
        if (ctx.ActionType != SyntheticApprovalAction)
        {
            return Allow("C-049: Action type is not a synthetic approval — honest limitation check not applicable.");
        }

        // ── Confidence score gate ────────────────────────────────────────────────
        var confidenceRaw = ctx.GetParameter("confidence_score");
        if (confidenceRaw is null ||
            !float.TryParse(confidenceRaw, NumberStyles.Float, CultureInfo.InvariantCulture, out var confidenceScore))
        {
            _logger.LogWarning(
                "C-049: confidence_score missing or unparseable for action {ActionType} contract {ContractId}",
                ctx.ActionType, ctx.ContractId);
            return Escalate("C-049: Confidence score absent — honest limitation requires human review.");
        }

        // Configured threshold may be embedded in the action parameters; fall back to default.
        var thresholdRaw = ctx.GetParameter("configured_threshold");
        var threshold = DefaultConfidenceThreshold;
        if (thresholdRaw is not null &&
            float.TryParse(thresholdRaw, NumberStyles.Float, CultureInfo.InvariantCulture, out var parsedThreshold))
        {
            threshold = parsedThreshold;
        }

        if (confidenceScore < threshold)
        {
            _logger.LogInformation(
                "C-049: Confidence {Score:F3} below threshold {Threshold:F3} — escalating contract {ContractId}",
                confidenceScore, threshold, ctx.ContractId);
            return Escalate(
                $"C-049: Confidence score {confidenceScore:F3} is below required threshold {threshold:F3}. " +
                "Human review required (honest limitation).");
        }

        // ── Prior approval history gate ──────────────────────────────────────────
        var priorCountRaw  = ctx.GetParameter("prior_approval_count");
        var minHistoryRaw  = ctx.GetParameter("min_history_required");

        var priorCount = 0;
        var minHistory = DefaultMinHistoryRequired;

        if (priorCountRaw is not null && int.TryParse(priorCountRaw, out var parsedPriorCount))
        {
            priorCount = parsedPriorCount;
        }

        if (minHistoryRaw is not null && int.TryParse(minHistoryRaw, out var parsedMinHistory))
        {
            minHistory = parsedMinHistory;
        }

        if (priorCount < minHistory)
        {
            _logger.LogInformation(
                "C-049: Prior approval count {Count} below minimum {Min} — escalating contract {ContractId}",
                priorCount, minHistory, ctx.ContractId);
            return Escalate(
                $"C-049: Insufficient approval history ({priorCount} prior approvals; {minHistory} required). " +
                "Human review required (honest limitation).");
        }

        // ── All gates passed ─────────────────────────────────────────────────────
        _logger.LogDebug(
            "C-049: Confidence {Score:F3} ≥ {Threshold:F3} and history {Count} ≥ {Min} — allow for contract {ContractId}",
            confidenceScore, threshold, priorCount, minHistory, ctx.ContractId);

        return Allow(
            $"C-049: Confidence {confidenceScore:F3} meets threshold {threshold:F3} " +
            $"and approval history ({priorCount}) meets minimum ({minHistory}).");
    }

    // ── Private verdict helpers ──────────────────────────────────────────────────

    private Task<EvaluationResult> Allow(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, reason));

    private Task<EvaluationResult> Escalate(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Escalate, reason));

    private Task<EvaluationResult> Deny(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));
}