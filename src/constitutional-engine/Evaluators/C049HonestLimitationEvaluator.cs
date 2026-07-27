// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Honest Limitation
// Constitutional basis: C-049 (Honest Limitation), C-059 (Traceability)

using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-049 (Honest Limitation): an agent must not attempt actions that exceed
/// its declared capability. If the reported confidence score falls below the configured
/// threshold, or if a skill-typed action has no registered SkillId, the evaluator
/// escalates to human review rather than permitting or outright denying the action.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    public string ClaimId => "C-049";

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        _logger = logger;
    }

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // ── Guard 1: Confidence score vs configured threshold ────────────────────────
        // ActionParameters is JSON-encoded; GetParameter extracts by key.
        var confidenceRaw  = ctx.GetParameter("confidence_score");
        var thresholdRaw   = ctx.GetParameter("configured_threshold");

        if (confidenceRaw is not null && thresholdRaw is not null)
        {
            bool confidenceParsed = float.TryParse(
                confidenceRaw,
                NumberStyles.Float,
                CultureInfo.InvariantCulture,
                out var confidence);

            bool thresholdParsed = float.TryParse(
                thresholdRaw,
                NumberStyles.Float,
                CultureInfo.InvariantCulture,
                out var threshold);

            if (confidenceParsed && thresholdParsed)
            {
                if (confidence < threshold)
                {
                    _logger.LogWarning(
                        "C-049 Escalate: confidence {Confidence:F4} < threshold {Threshold:F4} " +
                        "for ActionType={ActionType} ContractId={ContractId}",
                        confidence, threshold, ctx.ActionType, ctx.ContractId);

                    return Escalate(
                        $"Agent confidence score {confidence:F4} is below the configured " +
                        $"threshold {threshold:F4}. Human review required per C-049 (Honest Limitation).");
                }
            }
            else
            {
                // Malformed parameters — cannot assert the agent is within capability bounds.
                _logger.LogWarning(
                    "C-049 Escalate: unable to parse confidence/threshold parameters " +
                    "(confidence_score='{ConfidenceRaw}', configured_threshold='{ThresholdRaw}') " +
                    "for ContractId={ContractId}",
                    confidenceRaw, thresholdRaw, ctx.ContractId);

                return Escalate(
                    $"Confidence or threshold parameter could not be parsed " +
                    $"(confidence_score='{confidenceRaw}', configured_threshold='{thresholdRaw}'). " +
                    $"Escalating per C-049 (Honest Limitation).");
            }
        }

        // ── Guard 2: Skill-typed action requires a registered SkillId ────────────────
        // BudgetSkillType is non-empty only when the action is bound to a particular skill
        // capability class. A missing SkillId means the agent has not declared which
        // registered skill authorises this operation — escalate for human oversight.
        if (!string.IsNullOrWhiteSpace(ctx.BudgetSkillType) &&
            string.IsNullOrWhiteSpace(ctx.SkillId))
        {
            _logger.LogWarning(
                "C-049 Escalate: BudgetSkillType='{BudgetSkillType}' requires a SkillId " +
                "but none is registered for ContractId={ContractId}",
                ctx.BudgetSkillType, ctx.ContractId);

            return Escalate(
                $"Action requires skill capability class '{ctx.BudgetSkillType}' " +
                $"but no SkillId is registered on the request. " +
                $"Escalating per C-049 (Honest Limitation).");
        }

        // ── All checks pass ──────────────────────────────────────────────────────────
        _logger.LogDebug(
            "C-049 Allow: ActionType={ActionType} is within declared capability bounds " +
            "for ContractId={ContractId}",
            ctx.ActionType, ctx.ContractId);

        return Allow("Action is within the agent's declared capability bounds (C-049).");
    }

    // ── Private helpers ──────────────────────────────────────────────────────────────

    private Task<EvaluationResult> Allow(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, reason));

    private Task<EvaluationResult> Escalate(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Escalate, reason));
}