// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator — Honest Limitation
// constitutional_basis: C-049 (Honest Limitation), C-059 (Traceability)

using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-049 (Honest Limitation): when the agent's confidence in an action falls below the
/// configured threshold, or when there is insufficient prior approval history to make a safe
/// autonomous decision, the evaluator returns <see cref="EvaluationVerdict.Escalate"/> so that the
/// action is forwarded to a human reviewer rather than autonomously approved or denied.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // ── ActionParameters keys ─────────────────────────────────────────────────────────────────
    private const string ConfidenceScoreKey     = "confidence_score";
    private const string ConfiguredThresholdKey = "configured_threshold";
    private const string PriorApprovalCountKey  = "prior_approval_count";
    private const string MinHistoryRequiredKey  = "min_history_required";

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        _logger = logger;
    }

    /// <inheritdoc />
    public string ClaimId => "C-049";

    /// <inheritdoc />
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // ── 1. confidence_score is mandatory ────────────────────────────────────────────────
        var confidenceRaw = ctx.GetParameter(ConfidenceScoreKey);

        if (confidenceRaw is null
            || !float.TryParse(confidenceRaw, NumberStyles.Float, CultureInfo.InvariantCulture, out var confidenceScore))
        {
            _logger.LogWarning(
                "C-049: {Key} absent or unparseable for ContractId={ContractId}, ActionType={ActionType} — escalating",
                ConfidenceScoreKey, ctx.ContractId, ctx.ActionType);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                "C-049: confidence_score not provided — honest limitation requires escalation to human review."));
        }

        // ── 2. configured_threshold is mandatory ────────────────────────────────────────────
        var thresholdRaw = ctx.GetParameter(ConfiguredThresholdKey);

        if (thresholdRaw is null
            || !float.TryParse(thresholdRaw, NumberStyles.Float, CultureInfo.InvariantCulture, out var configuredThreshold))
        {
            _logger.LogWarning(
                "C-049: {Key} absent or unparseable for ContractId={ContractId}, ActionType={ActionType} — escalating",
                ConfiguredThresholdKey, ctx.ContractId, ctx.ActionType);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                "C-049: configured_threshold not provided — honest limitation requires escalation to human review."));
        }

        // ── 3. Confidence gate ───────────────────────────────────────────────────────────────
        if (confidenceScore < configuredThreshold)
        {
            _logger.LogInformation(
                "C-049: confidence {Score:F4} < threshold {Threshold:F4} — escalating ContractId={ContractId}",
                confidenceScore, configuredThreshold, ctx.ContractId);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-049: Agent confidence score {confidenceScore:F4} is below configured threshold {configuredThreshold:F4} — escalating to human review."));
        }

        // ── 4. Prior-approval history gate (optional — only checked when both keys are present)
        var priorCountRaw  = ctx.GetParameter(PriorApprovalCountKey);
        var minHistoryRaw  = ctx.GetParameter(MinHistoryRequiredKey);

        if (priorCountRaw is not null && minHistoryRaw is not null)
        {
            if (int.TryParse(priorCountRaw,  NumberStyles.Integer, CultureInfo.InvariantCulture, out var priorApprovalCount)
             && int.TryParse(minHistoryRaw,  NumberStyles.Integer, CultureInfo.InvariantCulture, out var minHistoryRequired))
            {
                if (priorApprovalCount < minHistoryRequired)
                {
                    _logger.LogInformation(
                        "C-049: prior_approval_count {Count} < min_history_required {Min} — escalating ContractId={ContractId}",
                        priorApprovalCount, minHistoryRequired, ctx.ContractId);

                    return Task.FromResult(new EvaluationResult(
                        ClaimId,
                        EvaluationVerdict.Escalate,
                        $"C-049: Insufficient approval history ({priorApprovalCount} approvals, minimum {minHistoryRequired} required) — escalating to human review."));
                }
            }
            else
            {
                // Keys were present but could not be parsed — treat as honest uncertainty.
                _logger.LogWarning(
                    "C-049: {PriorKey} or {MinKey} present but unparseable for ContractId={ContractId} — escalating",
                    PriorApprovalCountKey, MinHistoryRequiredKey, ctx.ContractId);

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    "C-049: prior_approval_count or min_history_required could not be parsed — escalating to human review."));
            }
        }

        // ── 5. All checks passed ─────────────────────────────────────────────────────────────
        _logger.LogDebug(
            "C-049: Allow — confidence {Score:F4} ≥ threshold {Threshold:F4} for ContractId={ContractId}",
            confidenceScore, configuredThreshold, ctx.ContractId);

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-049: Agent confidence meets threshold and history requirements."));
    }
}