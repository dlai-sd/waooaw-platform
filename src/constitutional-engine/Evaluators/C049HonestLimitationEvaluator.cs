// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation), C-076 (Test Coverage ≥90%)

#nullable enable

using System.Diagnostics;
using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 Honest Limitation Evaluator.
/// Enforces the constitutional obligation that the AI must not proceed autonomously
/// when its confidence is below the configured threshold, or when insufficient
/// prior approval history exists to justify autonomous action.
/// Low confidence → Escalate (human review). Sufficient confidence → Allow.
/// C-049 never issues a hard Deny — uncertainty is escalated, not refused.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: Constitutional annotation — static tracer scope tags every span with claim context
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    /// <summary>Default confidence threshold when none is configured on the action request.</summary>
    private const float DefaultConfidenceThreshold = 0.70f;

    /// <summary>Default minimum prior-approval history when none is specified.</summary>
    private const int DefaultMinHistoryRequired = 0;

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Constitutional obligation — ClaimId identifies the enforced claim at runtime
    /// <inheritdoc/>
    public string ClaimId => "C-049";

    /// <summary>
    /// C-073: Evaluates whether the agent has sufficient confidence and approval history
    /// to proceed autonomously.
    ///
    /// Decision logic (short-circuit, first condition wins):
    ///   1. confidence_score present AND below effective_threshold → Escalate
    ///   2. prior_approval_count present AND below effective_min_history → Escalate
    ///   3. All checks pass (or not applicable) → Allow
    ///
    /// Parameters read from <see cref="EvaluationContext.GetParameter"/>:
    ///   "confidence_score"      — float [0.0, 1.0]  (optional; if absent, step 1 skipped)
    ///   "configured_threshold"  — float [0.0, 1.0]  (optional; defaults to 0.70)
    ///   "prior_approval_count"  — int ≥ 0            (optional; if absent, step 2 skipped)
    ///   "min_history_required"  — int ≥ 0            (optional; defaults to 0)
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: Constitutional enforcement annotation — C-049 Honest Limitation
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.EvaluateAsync", ActivityKind.Internal);
        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Parse action parameters (all optional; missing → skip that check) ──────────────
        float? confidenceScore       = TryParseFloat(ctx.GetParameter("confidence_score"));
        float? configuredThreshold   = TryParseFloat(ctx.GetParameter("configured_threshold"));
        int?   priorApprovalCount    = TryParseInt(ctx.GetParameter("prior_approval_count"));
        int?   minHistoryRequired    = TryParseInt(ctx.GetParameter("min_history_required"));

        float effectiveThreshold  = configuredThreshold ?? DefaultConfidenceThreshold;
        int   effectiveMinHistory = minHistoryRequired  ?? DefaultMinHistoryRequired;

        activity?.SetTag("confidence_score",       confidenceScore?.ToString("F4", CultureInfo.InvariantCulture) ?? "absent");
        activity?.SetTag("effective_threshold",    effectiveThreshold.ToString("F4", CultureInfo.InvariantCulture));
        activity?.SetTag("prior_approval_count",   priorApprovalCount?.ToString(CultureInfo.InvariantCulture) ?? "absent");
        activity?.SetTag("effective_min_history",  effectiveMinHistory.ToString(CultureInfo.InvariantCulture));

        // ── Check 1: Confidence score below threshold → Escalate ──────────────────────────
        if (confidenceScore.HasValue && confidenceScore.Value < effectiveThreshold)
        {
            _logger.LogInformation(
                "C-049 escalating — confidence_score={ConfidenceScore:F4} below threshold={Threshold:F4}, " +
                "TenantId={TenantId}, ActionType={ActionType}, ContractId={ContractId}",
                confidenceScore.Value, effectiveThreshold, ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("verdict", "Escalate");
            activity?.SetTag("escalate_reason", "confidence_below_threshold");

            return Task.FromResult(Escalate(
                $"Confidence score {confidenceScore.Value:F4} is below the required threshold " +
                $"{effectiveThreshold:F4}. Human review is required per C-049 (Honest Limitation)."));
        }

        // ── Check 2: Insufficient prior-approval history → Escalate ─────────────────────
        if (priorApprovalCount.HasValue && priorApprovalCount.Value < effectiveMinHistory)
        {
            _logger.LogInformation(
                "C-049 escalating — prior_approval_count={Count} below min_history_required={MinHistory}, " +
                "TenantId={TenantId}, ActionType={ActionType}, ContractId={ContractId}",
                priorApprovalCount.Value, effectiveMinHistory, ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("verdict", "Escalate");
            activity?.SetTag("escalate_reason", "insufficient_approval_history");

            return Task.FromResult(Escalate(
                $"Insufficient approval history: {priorApprovalCount.Value} prior approval(s) recorded, " +
                $"minimum {effectiveMinHistory} required before autonomous action per C-049 (Honest Limitation)."));
        }

        // ── All checks passed (or parameters absent — action not scored) → Allow ─────────
        _logger.LogInformation(
            "C-049 allow — TenantId={TenantId}, ActionType={ActionType}, ContractId={ContractId}, " +
            "ConfidenceScore={ConfidenceScore}, PriorApprovalCount={PriorApprovalCount}",
            ctx.TenantId, ctx.ActionType, ctx.ContractId,
            confidenceScore?.ToString("F4", CultureInfo.InvariantCulture) ?? "not-provided",
            priorApprovalCount?.ToString(CultureInfo.InvariantCulture) ?? "not-provided");

        activity?.SetTag("verdict", "Allow");

        return Task.FromResult(Allow(
            "Confidence and approval history requirements satisfied per C-049 (Honest Limitation)."));
    }

    // ── Private result builders ───────────────────────────────────────────────────────────

    // C-073: Allow result — confidence requirements met
    private EvaluationResult Allow(string reason) =>
        new(ClaimId, EvaluationVerdict.Allow, reason);

    // C-073: Escalate result — C-049 does NOT hard-Deny; uncertainty is forwarded to human
    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);

    // ── Parameter parsing helpers ─────────────────────────────────────────────────────────

    /// <summary>
    /// Parses a float from a nullable raw parameter string.
    /// Returns null when the input is absent, whitespace, or not a valid float.
    /// Uses InvariantCulture so "0.70" parses correctly regardless of host locale.
    /// </summary>
    private static float? TryParseFloat(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return null;

        return float.TryParse(
            raw.Trim(),
            NumberStyles.Float | NumberStyles.AllowLeadingSign,
            CultureInfo.InvariantCulture,
            out var parsed)
            ? parsed
            : null;
    }

    /// <summary>
    /// Parses an int from a nullable raw parameter string.
    /// Returns null when the input is absent, whitespace, or not a valid integer.
    /// </summary>
    private static int? TryParseInt(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return null;

        return int.TryParse(raw.Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed)
            ? parsed
            : null;
    }
}