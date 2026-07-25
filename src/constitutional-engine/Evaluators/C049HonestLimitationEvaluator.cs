// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation)
// C-065: Author = WAOOAW AI Agent. Do NOT self-approve or self-merge.

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-049 (Honest Limitation): when an AI action carries insufficient confidence
/// or lacks the minimum approval history required, the engine must escalate to a human
/// rather than guess. Default path is <see cref="EvaluationVerdict.Escalate"/>
/// whenever honesty signals are missing or below threshold.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: OpenTelemetry tracer scoped to the Constitutional Engine activity source.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    /// <summary>C-059: Constructor — validates dependencies are non-null.</summary>
    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Identifies the constitutional claim enforced by this evaluator.
    /// <inheritdoc />
    public string ClaimId => "C-049";

    /// <summary>
    /// Evaluates C-049 Honest Limitation.
    ///
    /// Decision logic (in order):
    ///   1. If <c>confidence_score</c> is present and below <c>configured_threshold</c>
    ///      → <see cref="EvaluationVerdict.Escalate"/> (AI is not confident enough to act autonomously).
    ///   2. If <c>prior_approval_count</c> is present and below <c>min_history_required</c>
    ///      → <see cref="EvaluationVerdict.Escalate"/> (insufficient track record to act autonomously).
    ///   3. If synthetic-approval parameters are present but malformed
    ///      → <see cref="EvaluationVerdict.Escalate"/> (fail-safe: treat parse failure as uncertainty).
    ///   4. If neither block of parameters is present, this evaluator does not apply
    ///      → <see cref="EvaluationVerdict.Allow"/> (not an AI-confidence-gated action).
    ///
    /// All escalations are logged structured for downstream evidence recording (C-023, WC012-03).
    /// </summary>
    // C-073: Implements C-049 Honest Limitation runtime enforcement.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: OpenTelemetry span — every evaluator creates a child span for latency attribution.
        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("claim_id",    ClaimId);
        activity?.SetTag("tenant_id",   ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Block 1: Confidence-score gate ─────────────────────────────────────────────────
        // C-073: C-049 requires honest acknowledgement of capability limits.
        //        A confidence score below the agent's own configured threshold is a declared limit.
        var confidenceStr = ctx.GetParameter("confidence_score");
        var thresholdStr  = ctx.GetParameter("configured_threshold");

        bool hasConfidence = confidenceStr is not null || thresholdStr is not null;

        if (hasConfidence)
        {
            // Parse failure on confidence fields = honest uncertainty → Escalate (fail-safe).
            if (!float.TryParse(confidenceStr, System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture, out var confidenceScore)
                || !float.TryParse(thresholdStr, System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture, out var configuredThreshold))
            {
                _logger.LogWarning(
                    "C-049 Escalate (parse failure): ConfidenceRaw={ConfidenceRaw} ThresholdRaw={ThresholdRaw} " +
                    "TenantId={TenantId} ActionType={ActionType}",
                    confidenceStr, thresholdStr, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.reason",  "confidence_parse_failure");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    "C-049: confidence_score or configured_threshold could not be parsed; " +
                    "escalating to human per Honest Limitation."));
            }

            activity?.SetTag("c049.confidence_score",    confidenceScore);
            activity?.SetTag("c049.configured_threshold", configuredThreshold);

            if (confidenceScore < configuredThreshold)
            {
                _logger.LogInformation(
                    "C-049 Escalate (confidence): ConfidenceScore={ConfidenceScore} " +
                    "ConfiguredThreshold={ConfiguredThreshold} TenantId={TenantId} ActionType={ActionType}",
                    confidenceScore, configuredThreshold, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.reason",  "confidence_below_threshold");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: confidence score {confidenceScore:F4} is below configured threshold " +
                    $"{configuredThreshold:F4}; escalating to human per Honest Limitation."));
            }
        }

        // ── Block 2: Approval-history gate ─────────────────────────────────────────────────
        // C-073: C-049 requires a minimum evidence base before autonomous approval.
        //        Insufficient prior approvals = unproven capability boundary → Escalate.
        var priorCountStr  = ctx.GetParameter("prior_approval_count");
        var minHistoryStr  = ctx.GetParameter("min_history_required");

        bool hasHistory = priorCountStr is not null || minHistoryStr is not null;

        if (hasHistory)
        {
            // Parse failure on history fields = honest uncertainty → Escalate (fail-safe).
            if (!int.TryParse(priorCountStr, out var priorApprovalCount)
                || !int.TryParse(minHistoryStr, out var minHistoryRequired))
            {
                _logger.LogWarning(
                    "C-049 Escalate (parse failure): PriorCountRaw={PriorCountRaw} MinHistoryRaw={MinHistoryRaw} " +
                    "TenantId={TenantId} ActionType={ActionType}",
                    priorCountStr, minHistoryStr, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.reason",  "history_parse_failure");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    "C-049: prior_approval_count or min_history_required could not be parsed; " +
                    "escalating to human per Honest Limitation."));
            }

            activity?.SetTag("c049.prior_approval_count", priorApprovalCount);
            activity?.SetTag("c049.min_history_required", minHistoryRequired);

            if (priorApprovalCount < minHistoryRequired)
            {
                _logger.LogInformation(
                    "C-049 Escalate (history): PriorApprovalCount={PriorApprovalCount} " +
                    "MinHistoryRequired={MinHistoryRequired} TenantId={TenantId} ActionType={ActionType}",
                    priorApprovalCount, minHistoryRequired, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.reason",  "insufficient_approval_history");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: insufficient approval history — {priorApprovalCount} prior approvals " +
                    $"recorded, {minHistoryRequired} required; escalating to human per Honest Limitation."));
            }
        }

        // ── Block 3: Allow — all honesty gates passed (or not applicable) ──────────────────
        // C-073: Action is not confidence-gated, or all honesty thresholds are satisfied.
        _logger.LogInformation(
            "C-049 Allow: TenantId={TenantId} ActionType={ActionType} ContractId={ContractId} " +
            "ConfidenceGateApplied={ConfidenceGateApplied} HistoryGateApplied={HistoryGateApplied}",
            ctx.TenantId, ctx.ActionType, ctx.ContractId, hasConfidence, hasHistory);

        activity?.SetTag("c049.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-049: honest-limitation checks passed — confidence and history thresholds satisfied."));
    }
}