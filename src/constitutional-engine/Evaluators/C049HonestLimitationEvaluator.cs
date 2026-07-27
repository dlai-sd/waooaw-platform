// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First), C-059 (Traceability),
//                       C-073 (Constitutional Annotation), C-076 (Test Coverage)

#nullable enable

using System.Diagnostics;
using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 Honest Limitation Evaluator.
///
/// Constitutional obligation: the AI must not autonomously execute an action when it lacks
/// sufficient confidence or approval history. Instead it must Escalate to human review
/// (Sujay) rather than attempt-and-fail or silently degrade.
///
/// Escalation triggers (short-circuit on first match):
///   1. confidence_score parameter absent or unparseable.
///   2. confidence_score &lt; configured_threshold (default 0.80 when threshold absent).
///   3. prior_approval_count &lt; min_history_required (when both parameters present).
///   4. prior_approval_count / min_history_required unparseable (conservative path).
///
/// Allow path: confidence meets threshold AND (history parameters absent OR count ≥ minimum).
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource for tracing constitutional evaluation span
    private static readonly ActivitySource _tracer =
        new("Waooaw.ConstitutionalEngine", "1.0");

    /// <summary>EvaluationContext parameter key for the AI's self-reported confidence score (float 0–1).</summary>
    internal const string ParamConfidenceScore = "confidence_score";

    /// <summary>EvaluationContext parameter key for the operator-configured minimum confidence threshold (float 0–1).</summary>
    internal const string ParamConfiguredThreshold = "configured_threshold";

    /// <summary>EvaluationContext parameter key for the count of prior human-approved instances of this action type.</summary>
    internal const string ParamPriorApprovalCount = "prior_approval_count";

    /// <summary>EvaluationContext parameter key for the minimum prior-approval history required for autonomous execution.</summary>
    internal const string ParamMinHistoryRequired = "min_history_required";

    /// <summary>
    /// Default minimum confidence threshold applied when configured_threshold parameter is absent.
    /// Conservative: 80% confidence required to proceed autonomously.
    /// </summary>
    internal const float DefaultConfidenceThreshold = 0.80f;

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    // C-073: Constructor — constitutional DI injection
    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId — identifies the constitutional claim this evaluator enforces
    public string ClaimId => "C-049";

    // C-073: EvaluateAsync — entry point for constitutional evaluation pipeline
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        var result = Evaluate(ctx, activity);

        activity?.SetTag("verdict", result.Verdict.ToString());

        _logger.LogInformation(
            "C-049 evaluation complete. TenantId={TenantId} ActionType={ActionType} " +
            "ContractId={ContractId} Verdict={Verdict} Reason={Reason}",
            ctx.TenantId, ctx.ActionType, ctx.ContractId, result.Verdict, result.Reason);

        return Task.FromResult(result);
    }

    // C-073: Core evaluation — synchronous inner method, called within traced span
    private EvaluationResult Evaluate(EvaluationContext ctx, Activity? activity)
    {
        // ── Step 1: Resolve confidence_score ────────────────────────────────────────
        // C-073: confidence_score absent → limitation unknown → escalate (C-049 honest path)
        var confidenceRaw = ctx.GetParameter(ParamConfidenceScore);
        if (confidenceRaw is null)
        {
            _logger.LogWarning(
                "C-049: confidence_score parameter absent. TenantId={TenantId} ActionType={ActionType}",
                ctx.TenantId, ctx.ActionType);
            activity?.SetTag("escalate_reason", "confidence_score_absent");
            return Escalate(
                "C-049: confidence_score parameter not provided — honest limitation cannot " +
                "be assessed; escalating to human review.");
        }

        if (!float.TryParse(
                confidenceRaw,
                NumberStyles.Float,
                CultureInfo.InvariantCulture,
                out var confidenceScore))
        {
            _logger.LogWarning(
                "C-049: confidence_score parameter is not a valid float. " +
                "Value={Value} TenantId={TenantId} ActionType={ActionType}",
                confidenceRaw, ctx.TenantId, ctx.ActionType);
            activity?.SetTag("escalate_reason", "confidence_score_unparseable");
            return Escalate(
                $"C-049: confidence_score '{confidenceRaw}' is not a valid float — " +
                "escalating to human review.");
        }

        activity?.SetTag("confidence_score", confidenceScore);

        // ── Step 2: Resolve configured_threshold (default to conservative 0.80) ───
        var thresholdRaw = ctx.GetParameter(ParamConfiguredThreshold);
        float configuredThreshold = DefaultConfidenceThreshold;

        if (thresholdRaw is not null)
        {
            if (!float.TryParse(
                    thresholdRaw,
                    NumberStyles.Float,
                    CultureInfo.InvariantCulture,
                    out configuredThreshold))
            {
                _logger.LogWarning(
                    "C-049: configured_threshold parameter is not a valid float. " +
                    "Value={Value} TenantId={TenantId} — applying default {Default}",
                    thresholdRaw, ctx.TenantId, DefaultConfidenceThreshold);
                configuredThreshold = DefaultConfidenceThreshold;
            }
        }

        activity?.SetTag("configured_threshold", configuredThreshold);

        // ── Step 3: Confidence gate ──────────────────────────────────────────────────
        // C-073: If AI confidence is below threshold, escalate per C-049 honest limitation
        if (confidenceScore < configuredThreshold)
        {
            _logger.LogInformation(
                "C-049: Confidence below threshold. Score={Score:F4} Threshold={Threshold:F4} " +
                "TenantId={TenantId} ActionType={ActionType}",
                confidenceScore, configuredThreshold, ctx.TenantId, ctx.ActionType);
            activity?.SetTag("escalate_reason", "confidence_below_threshold");
            return Escalate(
                $"C-049: confidence score {confidenceScore:F4} is below configured threshold " +
                $"{configuredThreshold:F4} — escalating to human review.");
        }

        // ── Step 4: Approval history gate (optional — only when both params present) ─
        var priorApprovalRaw = ctx.GetParameter(ParamPriorApprovalCount);
        var minHistoryRaw    = ctx.GetParameter(ParamMinHistoryRequired);

        // C-073: Only evaluate history when both parameters are supplied
        if (priorApprovalRaw is not null && minHistoryRaw is not null)
        {
            var priorParsed = int.TryParse(priorApprovalRaw, out var priorApprovalCount);
            var minParsed   = int.TryParse(minHistoryRaw,    out var minHistoryRequired);

            if (!priorParsed || !minParsed)
            {
                _logger.LogWarning(
                    "C-049: Approval history parameters unparseable. " +
                    "prior_approval_count={PriorRaw} min_history_required={MinRaw} TenantId={TenantId}",
                    priorApprovalRaw, minHistoryRaw, ctx.TenantId);
                activity?.SetTag("escalate_reason", "history_params_unparseable");
                return Escalate(
                    "C-049: approval history parameters are not valid integers — " +
                    "escalating to human review.");
            }

            activity?.SetTag("prior_approval_count", priorApprovalCount);
            activity?.SetTag("min_history_required", minHistoryRequired);

            // C-073: Insufficient prior history → honest limitation → escalate
            if (priorApprovalCount < minHistoryRequired)
            {
                _logger.LogInformation(
                    "C-049: Insufficient approval history. " +
                    "PriorApprovals={PriorApprovals} MinRequired={MinRequired} " +
                    "TenantId={TenantId} ActionType={ActionType}",
                    priorApprovalCount, minHistoryRequired, ctx.TenantId, ctx.ActionType);
                activity?.SetTag("escalate_reason", "insufficient_approval_history");
                return Escalate(
                    $"C-049: prior approval count {priorApprovalCount} is below minimum " +
                    $"history required {minHistoryRequired} — escalating to human review.");
            }
        }

        // ── Step 5: All checks passed — AI is confident with sufficient history ─────
        _logger.LogInformation(
            "C-049: Allow. Score={Score:F4} Threshold={Threshold:F4} TenantId={TenantId}",
            confidenceScore, configuredThreshold, ctx.TenantId);

        return Allow(
            $"C-049: confidence score {confidenceScore:F4} meets threshold {configuredThreshold:F4} " +
            "and approval history is sufficient.");
    }

    // C-073: Verdict factory helpers — keep verdict construction co-located with ClaimId binding

    private EvaluationResult Allow(string reason) =>
        new(ClaimId, EvaluationVerdict.Allow, reason);

    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);
}