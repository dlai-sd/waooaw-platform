// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-049 (Honest Limitation): when an AI agent's confidence is below the
/// configured threshold, or it lacks sufficient prior-approval history, the action
/// is ESCALATED to a human rather than autonomously approved.
///
/// C-049 never issues a hard DENY — it signals that the AI recognises the boundary
/// of its own competency and requests human adjudication.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: OpenTelemetry tracer — constitutional obligation tracing
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Identifies the constitutional claim this evaluator enforces
    public string ClaimId => "C-049";

    // C-073: Implements C-049 Honest Limitation.
    //        Escalates when AI confidence or approval history is below threshold.
    //        MUST NOT perform network I/O — only reads from EvaluationContext.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("contract_id", ctx.ContractId);

        // C-073: Extract synthetic-approval context parameters from JSON-encoded ActionParameters.
        //        ctx.GetParameter() handles all JSON parsing — never call TryGetValue on ActionParameters.
        var confidenceScoreRaw   = ctx.GetParameter("confidence_score");
        var configuredThresholdRaw = ctx.GetParameter("configured_threshold");
        var priorApprovalCountRaw  = ctx.GetParameter("prior_approval_count");
        var minHistoryRequiredRaw  = ctx.GetParameter("min_history_required");

        // If the request carries no synthetic-approval context, C-049 is not applicable.
        // The action may still be blocked by other evaluators (C-041, C-043, etc.).
        bool hasConfidenceContext = confidenceScoreRaw is not null || configuredThresholdRaw is not null;
        bool hasHistoryContext    = priorApprovalCountRaw is not null || minHistoryRequiredRaw is not null;

        if (!hasConfidenceContext && !hasHistoryContext)
        {
            _logger.LogInformation(
                "C-049: No synthetic approval context for TenantId={TenantId} ActionType={ActionType} — evaluator not applicable",
                ctx.TenantId, ctx.ActionType);

            activity?.SetTag("c049.verdict", "Allow");
            activity?.SetTag("c049.skip_reason", "no_synthetic_approval_context");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                "C-049: No synthetic approval context present — honest limitation check not applicable"));
        }

        // ── Confidence-score gate ────────────────────────────────────────────────────────
        // C-073: If confidence data is present, both score AND threshold must be valid and
        //        parseable. A partial or malformed pair is itself an honest-limitation signal.
        if (hasConfidenceContext)
        {
            // Both parameters must be present to perform a meaningful comparison
            if (confidenceScoreRaw is null || configuredThresholdRaw is null)
            {
                _logger.LogWarning(
                    "C-049: Partial confidence context (score={Score} threshold={Threshold}) for TenantId={TenantId} — escalating",
                    confidenceScoreRaw, configuredThresholdRaw, ctx.TenantId);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.escalation_reason", "partial_confidence_context");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    "C-049: Incomplete confidence context (one of score/threshold missing) — escalating to human review"));
            }

            if (!double.TryParse(confidenceScoreRaw, NumberStyles.Float, CultureInfo.InvariantCulture, out var confidenceScore) ||
                !double.TryParse(configuredThresholdRaw, NumberStyles.Float, CultureInfo.InvariantCulture, out var configuredThreshold))
            {
                _logger.LogWarning(
                    "C-049: Malformed confidence parameters Score={ScoreRaw} Threshold={ThresholdRaw} for TenantId={TenantId} — escalating",
                    confidenceScoreRaw, configuredThresholdRaw, ctx.TenantId);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.escalation_reason", "malformed_confidence_parameters");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    "C-049: Malformed confidence parameters — cannot assess AI competency, escalating per honest limitation principle"));
            }

            activity?.SetTag("c049.confidence_score", confidenceScore);
            activity?.SetTag("c049.configured_threshold", configuredThreshold);

            if (confidenceScore < configuredThreshold)
            {
                _logger.LogWarning(
                    "C-049: Confidence score {ConfidenceScore:F4} below threshold {ConfiguredThreshold:F4} for TenantId={TenantId} ActionType={ActionType} — escalating",
                    confidenceScore, configuredThreshold, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.escalation_reason", "confidence_below_threshold");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: AI confidence {confidenceScore:F4} is below configured threshold {configuredThreshold:F4} — honest limitation requires human review"));
            }
        }

        // ── Prior-approval history gate ──────────────────────────────────────────────────
        // C-073: Insufficient approval history means the AI is operating in unfamiliar
        //        territory. Escalate to gather explicit human authorisation.
        if (hasHistoryContext)
        {
            // Both parameters must be present to perform a meaningful comparison
            if (priorApprovalCountRaw is null || minHistoryRequiredRaw is null)
            {
                _logger.LogWarning(
                    "C-049: Partial history context (count={Count} minRequired={MinRequired}) for TenantId={TenantId} — escalating",
                    priorApprovalCountRaw, minHistoryRequiredRaw, ctx.TenantId);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.escalation_reason", "partial_history_context");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    "C-049: Incomplete approval history context (one of count/minimum missing) — escalating to human review"));
            }

            if (!int.TryParse(priorApprovalCountRaw, out var priorApprovalCount) ||
                !int.TryParse(minHistoryRequiredRaw, out var minHistoryRequired))
            {
                _logger.LogWarning(
                    "C-049: Malformed history parameters Count={CountRaw} MinRequired={MinRequiredRaw} for TenantId={TenantId} — escalating",
                    priorApprovalCountRaw, minHistoryRequiredRaw, ctx.TenantId);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.escalation_reason", "malformed_history_parameters");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    "C-049: Malformed approval history parameters — cannot verify sufficient precedent, escalating per honest limitation principle"));
            }

            activity?.SetTag("c049.prior_approval_count", priorApprovalCount);
            activity?.SetTag("c049.min_history_required", minHistoryRequired);

            if (priorApprovalCount < minHistoryRequired)
            {
                _logger.LogWarning(
                    "C-049: Prior approval count {PriorApprovalCount} below minimum required {MinHistoryRequired} for TenantId={TenantId} ActionType={ActionType} — escalating",
                    priorApprovalCount, minHistoryRequired, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.escalation_reason", "insufficient_approval_history");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: Prior approval count {priorApprovalCount} is below minimum history required {minHistoryRequired} — human approval needed to establish precedent"));
            }
        }

        // ── All checks passed ────────────────────────────────────────────────────────────
        // AI is operating within its competency bounds and has sufficient approval history.
        _logger.LogInformation(
            "C-049: Honest limitation check passed for TenantId={TenantId} ActionType={ActionType}",
            ctx.TenantId, ctx.ActionType);

        activity?.SetTag("c049.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-049: AI confidence and approval history within acceptable bounds — honest limitation satisfied"));
    }
}