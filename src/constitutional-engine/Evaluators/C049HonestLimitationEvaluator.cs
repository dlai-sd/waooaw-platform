// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049
// constitutional_basis: C-049 (Honest Limitation — agent must not act beyond acknowledged capability)
// C-073: Every method in this file implements a constitutional obligation.

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 Evaluator — Honest Limitation.
/// Escalates when an agent operates in a skill domain it has not acknowledged
/// competency in (missing SkillId), or when a synthetic approval confidence score
/// falls below the configured threshold with insufficient approval history.
///
/// Escalate (not Deny) is the constitutional response — C-049 mandates transparency
/// and human escalation rather than outright denial of uncertain capability.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-073: Minimum history required when no explicit MinHistoryRequired is provided.
    private const int FallbackMinHistory = 3;

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc/>
    public string ClaimId => "C-049";

    /// <inheritdoc/>
    // C-073: Empty = applies to ALL action types — honest limitation is universal per C-049.
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    /// <inheritdoc/>
    // C-073: Enforces C-049 — agent must not claim capability it has not demonstrated or acknowledged.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C049HonestLimitationEvaluator.EvaluateAsync");
        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("skill_id", ctx.SkillId ?? "(none)");

        // Check 1: Skill domain acknowledgment.
        // If the action carries a skill_required parameter but no SkillId is declared
        // in the request, the agent is acting beyond its acknowledged domain.
        var skillRequired = ctx.GetParameter("skill_required");

        if (!string.IsNullOrWhiteSpace(skillRequired)
            && string.IsNullOrWhiteSpace(ctx.SkillId))
        {
            _logger.LogWarning(
                "C-049 ESCALATE: skill_required='{SkillRequired}' but SkillId is absent. " +
                "ContractId={ContractId}",
                skillRequired, ctx.ContractId);

            activity?.SetTag("verdict", "Escalate");
            activity?.SetTag("escalate_reason", "missing_skill_id");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-049: Action requires skill '{skillRequired}' but no SkillId was declared — human validation required."));
        }

        // Check 2: Synthetic approval confidence vs threshold.
        var confidenceRaw = ctx.GetParameter("synthetic_confidence_score");
        var thresholdRaw = ctx.GetParameter("synthetic_confidence_threshold");
        var priorApprovalRaw = ctx.GetParameter("synthetic_prior_approval_count");
        var minHistoryRaw = ctx.GetParameter("synthetic_min_history_required");

        if (confidenceRaw is not null)
        {
            if (!float.TryParse(confidenceRaw,
                    System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out var confidence))
            {
                _logger.LogWarning(
                    "C-049 ESCALATE: synthetic_confidence_score='{Raw}' is not parseable. ContractId={ContractId}",
                    confidenceRaw, ctx.ContractId);

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: synthetic_confidence_score value '{confidenceRaw}' is not parseable — escalating."));
            }

            float threshold = 0.80f; // default constitutional threshold
            if (thresholdRaw is not null
                && float.TryParse(thresholdRaw,
                    System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out var parsedThreshold))
            {
                threshold = parsedThreshold;
            }

            int priorApprovals = 0;
            if (priorApprovalRaw is not null)
                int.TryParse(priorApprovalRaw, out priorApprovals);

            int minHistory = FallbackMinHistory;
            if (minHistoryRaw is not null)
                int.TryParse(minHistoryRaw, out minHistory);

            activity?.SetTag("synthetic_confidence", confidence);
            activity?.SetTag("synthetic_threshold", threshold);
            activity?.SetTag("prior_approvals", priorApprovals);
            activity?.SetTag("min_history", minHistory);

            if (confidence < threshold || priorApprovals < minHistory)
            {
                _logger.LogWarning(
                    "C-049 ESCALATE: confidence={Confidence:F3} < threshold={Threshold:F3} " +
                    "or priorApprovals={Prior} < minHistory={Min}. ContractId={ContractId}",
                    confidence, threshold, priorApprovals, minHistory, ctx.ContractId);

                activity?.SetTag("verdict", "Escalate");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: Synthetic approval confidence={confidence:F3} below threshold={threshold:F3} " +
                    $"or insufficient history ({priorApprovals}/{minHistory}) — human review required."));
            }
        }

        _logger.LogDebug(
            "C-049 ALLOW: Skill domain and capability checks passed. ContractId={ContractId}",
            ctx.ContractId);

        activity?.SetTag("verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-049: Agent capability and skill acknowledgment verified."));
    }
}