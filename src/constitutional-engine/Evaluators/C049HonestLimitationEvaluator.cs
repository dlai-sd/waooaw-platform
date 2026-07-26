// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation), C-076 (Test Coverage)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 Honest Limitation Evaluator.
/// Enforces that the AI does not proceed when its self-assessed confidence is below the
/// configured threshold, or when it lacks sufficient prior-approval history.
/// In both cases the action is Escalated to a human (Sujay) rather than denied outright —
/// C-049 is an honesty/escalation claim, not a hard deny.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // ── OpenTelemetry ──────────────────────────────────────────────────────────────────────
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // ── Defaults ───────────────────────────────────────────────────────────────────────────
    // C-073: constitutional obligation annotation
    /// <summary>Minimum confidence score required to proceed without human escalation.</summary>
    private const float DefaultConfidenceThreshold = 0.70f;

    // C-073: constitutional obligation annotation
    /// <summary>
    /// Minimum prior-approval history required before the confidence gate is applied.
    /// 0 = no history gate unless action parameters explicitly configure one.
    /// </summary>
    private const int DefaultMinHistoryRequired = 0;

    // ── Dependencies ───────────────────────────────────────────────────────────────────────
    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // ── IClaimEvaluator ────────────────────────────────────────────────────────────────────

    /// <inheritdoc/>
    public string ClaimId => "C-049";

    // C-073: constitutional obligation annotation — enforces C-049 (Honest Limitation)
    /// <inheritdoc/>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C049HonestLimitationEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("tenant_id",  ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── 1. Parse parameters from JSON-encoded ActionParameters ──────────────────────
        // C-073: constitutional obligation annotation — reads confidence parameters per C-049
        float confidenceScore     = TryParseFloat(ctx.GetParameter("confidence_score"))     ?? 1.0f;
        float configuredThreshold = TryParseFloat(ctx.GetParameter("configured_threshold")) ?? DefaultConfidenceThreshold;
        int priorApprovalCount    = TryParseInt(ctx.GetParameter("prior_approval_count"))   ?? 0;
        int minHistoryRequired    = TryParseInt(ctx.GetParameter("min_history_required"))   ?? DefaultMinHistoryRequired;

        activity?.SetTag("confidence_score",      confidenceScore);
        activity?.SetTag("configured_threshold",  configuredThreshold);
        activity?.SetTag("prior_approval_count",  priorApprovalCount);
        activity?.SetTag("min_history_required",  minHistoryRequired);

        _logger.LogInformation(
            "C049 evaluating: tenant={TenantId} action={ActionType} confidence={Confidence:F3} " +
            "threshold={Threshold:F3} history={History}/{MinHistory}",
            ctx.TenantId, ctx.ActionType, confidenceScore, configuredThreshold,
            priorApprovalCount, minHistoryRequired);

        // ── 2. History gate (only applied when explicitly configured) ───────────────────
        // C-073: constitutional obligation annotation — history gate per C-049
        if (minHistoryRequired > 0 && priorApprovalCount < minHistoryRequired)
        {
            _logger.LogWarning(
                "C049 escalate — insufficient history: tenant={TenantId} action={ActionType} " +
                "prior_approvals={PriorApprovalCount} min_required={MinHistoryRequired}",
                ctx.TenantId, ctx.ActionType, priorApprovalCount, minHistoryRequired);

            activity?.SetTag("c049.outcome", "escalate_history_gate");

            return Task.FromResult(Escalate(
                $"Insufficient prior-approval history: {priorApprovalCount} approvals " +
                $"recorded but {minHistoryRequired} required before autonomous execution. " +
                "Escalating to human review per C-049."));
        }

        // ── 3. Confidence threshold gate ────────────────────────────────────────────────
        // C-073: constitutional obligation annotation — confidence gate per C-049
        if (confidenceScore < configuredThreshold)
        {
            _logger.LogWarning(
                "C049 escalate — confidence below threshold: tenant={TenantId} action={ActionType} " +
                "confidence={Confidence:F3} threshold={Threshold:F3}",
                ctx.TenantId, ctx.ActionType, confidenceScore, configuredThreshold);

            activity?.SetTag("c049.outcome", "escalate_confidence_gate");

            return Task.FromResult(Escalate(
                $"AI confidence score {confidenceScore:F3} is below the configured threshold " +
                $"{configuredThreshold:F3}. Honest limitation acknowledged — escalating to " +
                "human review per C-049 rather than proceeding with insufficient confidence."));
        }

        // ── 4. All gates pass ───────────────────────────────────────────────────────────
        _logger.LogInformation(
            "C049 allow: tenant={TenantId} action={ActionType} confidence={Confidence:F3} " +
            "meets threshold={Threshold:F3} history={History}/{MinHistory}",
            ctx.TenantId, ctx.ActionType, confidenceScore, configuredThreshold,
            priorApprovalCount, minHistoryRequired);

        activity?.SetTag("c049.outcome", "allow");

        return Task.FromResult(Allow(
            $"Confidence score {confidenceScore:F3} meets or exceeds threshold {configuredThreshold:F3}; " +
            $"prior approval history {priorApprovalCount} satisfies minimum {minHistoryRequired}."));
    }

    // ── Private helpers ────────────────────────────────────────────────────────────────────

    // C-073: constitutional obligation annotation — produces Allow result for C-049
    private EvaluationResult Allow(string reason) =>
        new(ClaimId, EvaluationVerdict.Allow, reason);

    // C-073: constitutional obligation annotation — produces Escalate result for C-049
    // (C-049 escalates to human; it does not hard-deny)
    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);

    /// <summary>
    /// Safely parse a float from a nullable string extracted from JSON ActionParameters.
    /// Returns null when the value is absent or unparseable.
    /// </summary>
    private static float? TryParseFloat(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return null;

        return float.TryParse(raw,
            System.Globalization.NumberStyles.Float,
            System.Globalization.CultureInfo.InvariantCulture,
            out var value)
            ? value
            : null;
    }

    /// <summary>
    /// Safely parse an int from a nullable string extracted from JSON ActionParameters.
    /// Returns null when the value is absent or unparseable.
    /// </summary>
    private static int? TryParseInt(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return null;

        return int.TryParse(raw,
            System.Globalization.NumberStyles.Integer,
            System.Globalization.CultureInfo.InvariantCulture,
            out var value)
            ? value
            : null;
    }
}