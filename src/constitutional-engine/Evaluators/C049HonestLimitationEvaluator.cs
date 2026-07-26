// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation), C-076 (≥90% coverage)

#nullable enable

using System.Diagnostics;
using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-049 Honest Limitation at runtime.
/// An AI agent MUST escalate to human review whenever:
///   (a) its confidence score falls below the caller-supplied threshold, or
///   (b) it has insufficient prior-approval history to act autonomously.
/// Absence of confidence metadata when threshold data is partially present is
/// treated conservatively as insufficient information → Escalate.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource enables distributed-trace attribution per evaluator invocation.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    // C-073: Constructor injection; ArgumentNullException.ThrowIfNull enforces non-null contracts.
    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId identifies the constitutional obligation enforced by this evaluator.
    public string ClaimId => "C-049";

    /// <summary>
    /// C-073: Enforces C-049 Honest Limitation.
    /// Evaluation sequence:
    ///   1. If confidence_score + configured_threshold are both present:
    ///      - If confidence &lt; threshold → Escalate (human must review).
    ///      - If either value cannot be parsed → Escalate (ambiguity = limitation).
    ///   2. If prior_approval_count + min_history_required are both present:
    ///      - If prior_approval_count &lt; min_history_required → Escalate.
    ///   3. All checks pass → Allow.
    ///
    /// MUST NOT perform network I/O.  No CancellationToken awaits are needed here
    /// (synchronous evaluation) but ct is accepted for interface compliance.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Activity span for distributed tracing per ADR-009 (OpenTelemetry).
        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.Evaluate", ActivityKind.Internal);
        activity?.SetTag("c049.tenant_id", ctx.TenantId);
        activity?.SetTag("c049.action_type", ctx.ActionType);
        activity?.SetTag("c049.claim_id", ClaimId);

        // ── Step 1: Confidence score check ───────────────────────────────────────────
        // Parameters sourced from SyntheticApprovalContext fields forwarded by the caller.
        // ActionParameters is JSON-encoded; GetParameter() handles extraction.
        var confidenceRaw = ctx.GetParameter("confidence_score");
        var thresholdRaw  = ctx.GetParameter("configured_threshold");

        if (confidenceRaw is not null || thresholdRaw is not null)
        {
            // At least one of the two paired fields was supplied — treat pair as a unit.
            bool confidenceParsed = float.TryParse(
                confidenceRaw, NumberStyles.Float, CultureInfo.InvariantCulture, out float confidence);
            bool thresholdParsed  = float.TryParse(
                thresholdRaw,  NumberStyles.Float, CultureInfo.InvariantCulture, out float threshold);

            if (!confidenceParsed || !thresholdParsed)
            {
                // C-049: Partial or malformed confidence data — honest position is uncertainty.
                _logger.LogWarning(
                    "C-049 Escalate: Unable to parse confidence parameters. " +
                    "confidence_score_raw={ConfidenceRaw} configured_threshold_raw={ThresholdRaw} " +
                    "TenantId={TenantId} ActionType={ActionType}",
                    confidenceRaw, thresholdRaw, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.escalation_reason", "parse_failure");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    "C-049: Confidence parameters present but unparseable — " +
                    "action escalated for human review to honour Honest Limitation."));
            }

            // C-073: Core C-049 enforcement — confidence below threshold triggers Escalate.
            if (confidence < threshold)
            {
                _logger.LogInformation(
                    "C-049 Escalate: confidence={Confidence:F4} below threshold={Threshold:F4}. " +
                    "TenantId={TenantId} ActionType={ActionType}",
                    confidence, threshold, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.confidence", confidence);
                activity?.SetTag("c049.threshold", threshold);

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: Confidence score {confidence:F4} is below the configured threshold " +
                    $"{threshold:F4}. Action must be reviewed by a human before proceeding."));
            }

            // Confidence check passed — log and fall through to history check.
            activity?.SetTag("c049.confidence", confidence);
            activity?.SetTag("c049.threshold", threshold);
            _logger.LogInformation(
                "C-049 confidence check passed: confidence={Confidence:F4} >= threshold={Threshold:F4}. " +
                "TenantId={TenantId}",
                confidence, threshold, ctx.TenantId);
        }

        // ── Step 2: Prior approval history check ────────────────────────────────────
        // Reflects SyntheticApprovalContext.PriorApprovalCount / MinHistoryRequired.
        var priorCountRaw  = ctx.GetParameter("prior_approval_count");
        var minHistoryRaw  = ctx.GetParameter("min_history_required");

        if (priorCountRaw is not null || minHistoryRaw is not null)
        {
            bool priorParsed  = int.TryParse(priorCountRaw,  out int priorCount);
            bool minParsed    = int.TryParse(minHistoryRaw,   out int minHistory);

            if (!priorParsed || !minParsed)
            {
                // C-049: Partial history metadata — treat as unknown → Escalate.
                _logger.LogWarning(
                    "C-049 Escalate: Unable to parse history parameters. " +
                    "prior_approval_count_raw={PriorRaw} min_history_required_raw={MinRaw} " +
                    "TenantId={TenantId} ActionType={ActionType}",
                    priorCountRaw, minHistoryRaw, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.escalation_reason", "history_parse_failure");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    "C-049: Approval history parameters present but unparseable — " +
                    "action escalated for human review to honour Honest Limitation."));
            }

            // C-073: Core C-049 enforcement — insufficient history triggers Escalate.
            if (priorCount < minHistory)
            {
                _logger.LogInformation(
                    "C-049 Escalate: prior_approval_count={PriorCount} < min_history_required={MinHistory}. " +
                    "TenantId={TenantId} ActionType={ActionType}",
                    priorCount, minHistory, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.prior_count", priorCount);
                activity?.SetTag("c049.min_history", minHistory);

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: Insufficient autonomous approval history — " +
                    $"{priorCount} prior approval(s) recorded, minimum {minHistory} required. " +
                    "Action must be reviewed by a human before proceeding."));
            }

            activity?.SetTag("c049.prior_count", priorCount);
            activity?.SetTag("c049.min_history", minHistory);
            _logger.LogInformation(
                "C-049 history check passed: prior_approval_count={PriorCount} >= min_history_required={MinHistory}. " +
                "TenantId={TenantId}",
                priorCount, minHistory, ctx.TenantId);
        }

        // ── Step 3: All C-049 checks passed ─────────────────────────────────────────
        activity?.SetTag("c049.verdict", "Allow");
        _logger.LogInformation(
            "C-049 Allow: all honest-limitation checks passed. TenantId={TenantId} ActionType={ActionType}",
            ctx.TenantId, ctx.ActionType);

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-049: Confidence and approval-history checks passed — agent may proceed."));
    }
}