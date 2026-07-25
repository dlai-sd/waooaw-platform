// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-049 (Honest Limitation).
/// The AI must not proceed autonomously when its confidence score is below a configured
/// threshold, or when the action lacks sufficient prior approval history to establish
/// safe precedent. Such actions are Escalated to human review — uncertainty is not
/// a denial; it is an honest acknowledgement of capability boundary.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: Named tracer matches service-wide ActivitySource convention
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    /// <inheritdoc/>
    public string ClaimId => "C-049";

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>
    /// C-073: Evaluates C-049 (Honest Limitation).
    /// Escalates if:
    ///   (a) confidence_score parameter is present and below configured_threshold, OR
    ///   (b) prior_approval_count parameter is present and below min_history_required.
    /// Both conditions are checked in order; first match short-circuits to Escalate.
    /// Returns Allow only when all present parameters satisfy their thresholds.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Branch (a): Confidence score vs configured threshold ──────────────────
        // C-073: ActionParameters is JSON-encoded; use GetParameter() exclusively.
        var confidenceRaw  = ctx.GetParameter("confidence_score");
        var thresholdRaw   = ctx.GetParameter("configured_threshold");

        if (confidenceRaw is not null && thresholdRaw is not null)
        {
            bool confidenceParsed = float.TryParse(
                confidenceRaw, NumberStyles.Float, CultureInfo.InvariantCulture,
                out var confidenceScore);

            bool thresholdParsed = float.TryParse(
                thresholdRaw, NumberStyles.Float, CultureInfo.InvariantCulture,
                out var configuredThreshold);

            if (!confidenceParsed || !thresholdParsed)
            {
                // C-073: Unparseable confidence parameters are themselves a limitation —
                // escalate rather than silently allow an action with opaque confidence data.
                _logger.LogWarning(
                    "C-049: Could not parse confidence parameters. " +
                    "confidence_score={RawConfidence} configured_threshold={RawThreshold} " +
                    "TenantId={TenantId} ActionType={ActionType}",
                    confidenceRaw, thresholdRaw, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("verdict", "Escalate");
                activity?.SetTag("reason", "unparseable_confidence_parameters");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    "C-049: Confidence parameters present but could not be parsed. " +
                    "Escalating for human review per honest-limitation principle."));
            }

            activity?.SetTag("confidence_score", confidenceScore);
            activity?.SetTag("configured_threshold", configuredThreshold);

            if (confidenceScore < configuredThreshold)
            {
                _logger.LogInformation(
                    "C-049 Escalate: confidence {ConfidenceScore:F4} < threshold {ConfiguredThreshold:F4} " +
                    "TenantId={TenantId} ActionType={ActionType}",
                    confidenceScore, configuredThreshold, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("verdict", "Escalate");
                activity?.SetTag("reason", "confidence_below_threshold");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: Confidence score {confidenceScore:F4} is below configured threshold " +
                    $"{configuredThreshold:F4}. Action escalated for human review."));
            }
        }

        // ── Branch (b): Prior approval count vs minimum history requirement ────────
        // C-073: Insufficient precedent history is a second form of honest limitation.
        var priorCountRaw  = ctx.GetParameter("prior_approval_count");
        var minHistoryRaw  = ctx.GetParameter("min_history_required");

        if (priorCountRaw is not null && minHistoryRaw is not null)
        {
            bool priorParsed   = int.TryParse(priorCountRaw,  out var priorApprovalCount);
            bool minParsed     = int.TryParse(minHistoryRaw,  out var minHistoryRequired);

            if (!priorParsed || !minParsed)
            {
                _logger.LogWarning(
                    "C-049: Could not parse history parameters. " +
                    "prior_approval_count={RawCount} min_history_required={RawMin} " +
                    "TenantId={TenantId} ActionType={ActionType}",
                    priorCountRaw, minHistoryRaw, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("verdict", "Escalate");
                activity?.SetTag("reason", "unparseable_history_parameters");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    "C-049: Prior approval history parameters present but could not be parsed. " +
                    "Escalating for human review per honest-limitation principle."));
            }

            activity?.SetTag("prior_approval_count", priorApprovalCount);
            activity?.SetTag("min_history_required", minHistoryRequired);

            if (priorApprovalCount < minHistoryRequired)
            {
                _logger.LogInformation(
                    "C-049 Escalate: prior approvals {PriorCount} < minimum {MinRequired} " +
                    "TenantId={TenantId} ActionType={ActionType}",
                    priorApprovalCount, minHistoryRequired, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("verdict", "Escalate");
                activity?.SetTag("reason", "insufficient_approval_history");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: Prior approval count {priorApprovalCount} is below minimum required " +
                    $"{minHistoryRequired}. Action escalated for human review."));
            }
        }

        // ── All checks passed — action is within declared capability bounds ────────
        _logger.LogInformation(
            "C-049 Allow: action within honest capability bounds. " +
            "TenantId={TenantId} ActionType={ActionType}",
            ctx.TenantId, ctx.ActionType);

        activity?.SetTag("verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-049: Action is within declared capability bounds."));
    }
}