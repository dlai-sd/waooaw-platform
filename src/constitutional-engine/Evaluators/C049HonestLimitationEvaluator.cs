// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First)

using Microsoft.Extensions.Logging;
using System.Diagnostics;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049: AI agents must not act beyond their verified capability boundary.
/// When confidence is below the configured threshold and prior approval history is
/// insufficient, escalate to human (Sujay) rather than proceeding autonomously.
/// Applies to AUTONOMOUS_EXECUTION and SYNTHETIC_APPROVAL action types.
/// </summary>
// C-073: Implements constitutional obligation C-049 (Honest Limitation / Capability Boundary)
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private static readonly IReadOnlySet<string> _actionTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "AUTONOMOUS_EXECUTION",
            "SYNTHETIC_APPROVAL",
            "CAPABILITY_CLAIM"
        };

    // Default floor: confidence must be ≥ 0.70 if no threshold is configured
    private const float DefaultConfidenceThreshold = 0.70f;

    // Minimum prior approval history before synthetic approval is trusted
    private const int DefaultMinHistoryRequired = 3;

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    public string ClaimId => "C-049";
    public IReadOnlySet<string> ApplicableActionTypes => _actionTypes;

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Evaluates C-049 (Honest Limitation) — Escalate when confidence is below threshold
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C049HonestLimitationEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("action_type", ctx.ActionType);

        // Parse confidence_score from parameters
        var confidenceRaw = ctx.GetParameter("confidence_score");
        var thresholdRaw = ctx.GetParameter("configured_threshold");
        var priorCountRaw = ctx.GetParameter("prior_approval_count");
        var minHistoryRaw = ctx.GetParameter("min_history_required");

        var confidenceScore = TryParseFloat(confidenceRaw, out var cf) ? cf : (float?)null;
        var configuredThreshold = TryParseFloat(thresholdRaw, out var th) ? th : DefaultConfidenceThreshold;
        var priorApprovalCount = TryParseInt(priorCountRaw, out var pc) ? pc : 0;
        var minHistoryRequired = TryParseInt(minHistoryRaw, out var mh) ? mh : DefaultMinHistoryRequired;

        activity?.SetTag("c049.confidence_score", confidenceScore);
        activity?.SetTag("c049.threshold", configuredThreshold);
        activity?.SetTag("c049.prior_count", priorApprovalCount);

        // Insufficient prior history → escalate regardless of confidence
        if (priorApprovalCount < minHistoryRequired)
        {
            _logger.LogWarning(
                "C-049 ESCALATE: Insufficient prior history. " +
                "PriorCount={PriorCount} MinRequired={MinRequired} ContractId={ContractId}",
                priorApprovalCount, minHistoryRequired, ctx.ContractId);
            activity?.SetTag("c049.verdict", "Escalate");
            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-049",
                Verdict: EvaluationVerdict.Escalate,
                Reason: $"C-049: Insufficient prior approval history for autonomous action. " +
                        $"Have {priorApprovalCount}, need {minHistoryRequired}. " +
                        $"Escalate to human override."));
        }

        // Below confidence threshold → escalate
        if (confidenceScore.HasValue && confidenceScore.Value < configuredThreshold)
        {
            _logger.LogWarning(
                "C-049 ESCALATE: ConfidenceScore={Score} below Threshold={Threshold}. ContractId={ContractId}",
                confidenceScore.Value, configuredThreshold, ctx.ContractId);
            activity?.SetTag("c049.verdict", "Escalate");
            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-049",
                Verdict: EvaluationVerdict.Escalate,
                Reason: $"C-049: AI confidence {confidenceScore.Value:P0} is below configured threshold " +
                        $"{configuredThreshold:P0}. Human review required per C-049."));
        }

        _logger.LogInformation(
            "C-049 ALLOW: Confidence={Score} >= Threshold={Threshold} with {PriorCount} prior approvals. " +
            "ContractId={ContractId}",
            confidenceScore, configuredThreshold, priorApprovalCount, ctx.ContractId);
        activity?.SetTag("c049.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: "C-049",
            Verdict: EvaluationVerdict.Allow,
            Reason: "C-049: Confidence and history thresholds met — capability boundary respected."));
    }

    private static bool TryParseFloat(string? raw, out float value)
    {
        if (string.IsNullOrWhiteSpace(raw))
        {
            value = 0f;
            return false;
        }
        return float.TryParse(raw, System.Globalization.NumberStyles.Float,
            System.Globalization.CultureInfo.InvariantCulture, out value);
    }

    private static bool TryParseInt(string? raw, out int value)
    {
        if (string.IsNullOrWhiteSpace(raw))
        {
            value = 0;
            return false;
        }
        return int.TryParse(raw, out value);
    }
}