// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation), C-076 (Test Coverage)

#nullable enable

using System.Diagnostics;
using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-049 (Honest Limitation) — an AI agent MUST escalate to a human
/// when its confidence score falls below the configured threshold, or when its prior
/// approval history is insufficient to justify autonomous action.
/// Escalate (not Deny) is the constitutionally correct outcome: the action is not
/// prohibited, it is uncertain — the human (Sujay) resolves the uncertainty.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource shared across the constitutional engine service
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    /// <summary>
    /// Default confidence threshold below which escalation is triggered.
    /// Overridden at runtime by the <c>configured_threshold</c> action parameter.
    /// </summary>
    private const float DefaultConfidenceThreshold = 0.70f;

    /// <summary>
    /// Default minimum approval history. Zero means no history gate unless explicitly
    /// set via the <c>min_history_required</c> action parameter.
    /// </summary>
    private const int DefaultMinHistoryRequired = 0;

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    // C-073: Constructor-injected logger — no other I/O dependencies; evaluator reads
    //        only from the EvaluationContext parameter bag (C-049 is stateless at runtime).
    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId binds this evaluator to C-049 in the EvaluatorRegistry
    public string ClaimId => "C-049";

    /// <summary>
    /// C-073: Evaluate C-049 Honest Limitation.
    /// <list type="bullet">
    ///   <item>If <c>confidence_score</c> &lt; effective threshold → Escalate.</item>
    ///   <item>If <c>prior_approval_count</c> &lt; effective min history (when min &gt; 0) → Escalate.</item>
    ///   <item>Otherwise → Allow.</item>
    /// </list>
    /// MUST NOT perform network I/O. All inputs come from EvaluationContext.GetParameter().
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Trace every evaluation for C-059 observability
        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Parse action parameters (JSON-encoded; GetParameter handles extraction) ──────
        float? rawConfidence       = TryParseFloat(ctx.GetParameter("confidence_score"));
        float? rawThreshold        = TryParseFloat(ctx.GetParameter("configured_threshold"));
        int?   rawPriorCount       = TryParseInt(ctx.GetParameter("prior_approval_count"));
        int?   rawMinHistory       = TryParseInt(ctx.GetParameter("min_history_required"));

        float effectiveThreshold   = rawThreshold   ?? DefaultConfidenceThreshold;
        int   effectiveMinHistory  = rawMinHistory   ?? DefaultMinHistoryRequired;

        activity?.SetTag("confidence_score",      rawConfidence?.ToString(CultureInfo.InvariantCulture) ?? "not_provided");
        activity?.SetTag("effective_threshold",   effectiveThreshold.ToString(CultureInfo.InvariantCulture));
        activity?.SetTag("prior_approval_count",  rawPriorCount?.ToString(CultureInfo.InvariantCulture) ?? "not_provided");
        activity?.SetTag("effective_min_history", effectiveMinHistory);

        // ── Gate 1: Confidence score ──────────────────────────────────────────────────────
        // C-073: If the agent reports a confidence score and it is below threshold, the
        //        constitution requires honest acknowledgment of limitation — escalate.
        if (rawConfidence.HasValue && rawConfidence.Value < effectiveThreshold)
        {
            _logger.LogInformation(
                "C-049 confidence gate: score={ConfidenceScore:F4} below threshold={Threshold:F4} " +
                "tenant={TenantId} actionType={ActionType} — escalating to human",
                rawConfidence.Value, effectiveThreshold, ctx.TenantId, ctx.ActionType);

            activity?.SetTag("verdict", "Escalate");
            activity?.SetTag("escalate_reason", "confidence_below_threshold");

            return Task.FromResult(Escalate(
                $"Agent confidence {rawConfidence.Value:F4} is below the required threshold " +
                $"{effectiveThreshold:F4}. C-049 (Honest Limitation) requires human escalation " +
                $"when the agent cannot act with sufficient certainty."));
        }

        // ── Gate 2: Approval history ──────────────────────────────────────────────────────
        // C-073: If a minimum approval history is configured (> 0), the agent must have
        //        accrued that many prior approvals before acting autonomously.
        //        If the count is unknown (null) and minimum is set, treat as zero — conservative.
        if (effectiveMinHistory > DefaultMinHistoryRequired)
        {
            int actualCount = rawPriorCount ?? 0;

            if (actualCount < effectiveMinHistory)
            {
                _logger.LogInformation(
                    "C-049 history gate: prior_approval_count={PriorCount} below min_history={MinHistory} " +
                    "tenant={TenantId} actionType={ActionType} — escalating to human",
                    actualCount, effectiveMinHistory, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("verdict", "Escalate");
                activity?.SetTag("escalate_reason", "insufficient_approval_history");

                return Task.FromResult(Escalate(
                    $"Insufficient approval history: {actualCount} prior approval(s) recorded, " +
                    $"minimum required is {effectiveMinHistory}. C-049 (Honest Limitation) requires " +
                    $"established precedent before autonomous action is permitted."));
            }
        }

        // ── Both gates passed → Allow ─────────────────────────────────────────────────────
        _logger.LogInformation(
            "C-049 passed: tenant={TenantId} actionType={ActionType} confidence={ConfidenceScore} " +
            "priorCount={PriorCount} threshold={Threshold} minHistory={MinHistory}",
            ctx.TenantId, ctx.ActionType,
            rawConfidence?.ToString(CultureInfo.InvariantCulture) ?? "not_provided",
            rawPriorCount?.ToString(CultureInfo.InvariantCulture) ?? "not_provided",
            effectiveThreshold, effectiveMinHistory);

        activity?.SetTag("verdict", "Allow");

        return Task.FromResult(Allow(
            "Confidence score and approval history satisfy C-049 (Honest Limitation) requirements."));
    }

    // ── Private helpers ───────────────────────────────────────────────────────────────────

    // C-073: Helper produces a correctly-shaped Allow result bound to this evaluator's ClaimId
    private EvaluationResult Allow(string reason) =>
        new(ClaimId, EvaluationVerdict.Allow, reason);

    // C-073: Helper produces a correctly-shaped Escalate result bound to this evaluator's ClaimId
    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);

    /// <summary>
    /// Parses a nullable float from a string using invariant culture.
    /// Returns null when the input is null or not a valid float.
    /// </summary>
    private static float? TryParseFloat(string? raw)
    {
        if (raw is null) return null;
        return float.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var value)
            ? value
            : null;
    }

    /// <summary>
    /// Parses a nullable int from a string using invariant culture.
    /// Returns null when the input is null or not a valid integer.
    /// </summary>
    private static int? TryParseInt(string? raw)
    {
        if (raw is null) return null;
        return int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out var value)
            ? value
            : null;
    }
}