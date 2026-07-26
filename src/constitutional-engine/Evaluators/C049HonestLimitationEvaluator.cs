// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-049 Honest Limitation at ValidateAction time.
///
/// An action is Escalated (forwarded to human review) when:
///   (a) The agent's confidence_score parameter is absent or unparseable.
///   (b) confidence_score is below the effective threshold
///       (configured_threshold parameter, or DefaultConfidenceThreshold = 0.70 if absent).
///   (c) prior_approval_count is below min_history_required
///       (min_history_required parameter, or DefaultMinHistoryRequired = 0 if absent).
///
/// An action is Allowed only when both confidence and history conditions are satisfied.
/// This evaluator never returns Deny — uncertainty routes to human, not hard rejection.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: OpenTelemetry tracer shared across all constitutional evaluators
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-073: constitutional thresholds — EA-approved defaults for C-049
    private const float DefaultConfidenceThreshold = 0.70f;
    private const int DefaultMinHistoryRequired = 0;

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: IClaimEvaluator — identifies the constitutional claim enforced here
    public string ClaimId => "C-049";

    /// <summary>
    /// C-073: Enforces C-049 Honest Limitation.
    ///
    /// Evaluation flow:
    ///   1. Parse confidence_score — missing/invalid → Escalate immediately (unknown confidence = uncertain).
    ///   2. Resolve effective threshold (configured_threshold parameter or 0.70 default).
    ///   3. If confidence_score &lt; threshold → Escalate.
    ///   4. Resolve prior_approval_count and min_history_required.
    ///   5. If prior_approval_count &lt; min_history_required → Escalate.
    ///   6. Both conditions satisfied → Allow.
    ///
    /// MUST NOT perform network I/O — all inputs come from EvaluationContext parameters.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: trace every evaluation with constitutional claim tagging
        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Step 1: confidence_score is mandatory for C-049 ──────────────────────
        // ctx.GetParameter() parses the JSON-encoded ActionParameters string.
        // NEVER use ActionParameters.TryGetValue() — it is a string, not a Dictionary.
        var rawConfidence = ctx.GetParameter("confidence_score");
        var confidenceScore = TryParseFloat(rawConfidence);

        if (confidenceScore is null)
        {
            _logger.LogInformation(
                "C-049: confidence_score missing or unparseable for TenantId={TenantId} ActionType={ActionType}; escalating to human review",
                ctx.TenantId,
                ctx.ActionType);

            activity?.SetTag("escalate_reason", "missing_confidence_score");
            activity?.SetTag("verdict", nameof(EvaluationVerdict.Escalate));

            return Task.FromResult(Escalate(
                "C-049: confidence_score parameter is absent or unparseable — " +
                "cannot assert honest limitation; escalating to human review"));
        }

        // ── Step 2: resolve effective confidence threshold ────────────────────────
        var rawThreshold = ctx.GetParameter("configured_threshold");
        var threshold = TryParseFloat(rawThreshold) ?? DefaultConfidenceThreshold;

        activity?.SetTag("confidence_score", confidenceScore.Value);
        activity?.SetTag("effective_threshold", threshold);

        // ── Step 3: confidence below threshold → Escalate ────────────────────────
        if (confidenceScore.Value < threshold)
        {
            _logger.LogInformation(
                "C-049: confidence {Score:F4} < threshold {Threshold:F4} for TenantId={TenantId} ActionType={ActionType}; escalating",
                confidenceScore.Value,
                threshold,
                ctx.TenantId,
                ctx.ActionType);

            activity?.SetTag("escalate_reason", "confidence_below_threshold");
            activity?.SetTag("verdict", nameof(EvaluationVerdict.Escalate));

            return Task.FromResult(Escalate(
                $"C-049: confidence score {confidenceScore.Value:F4} is below " +
                $"effective threshold {threshold:F4} — escalating to human review"));
        }

        // ── Step 4: resolve prior approval history ────────────────────────────────
        var rawPriorCount = ctx.GetParameter("prior_approval_count");
        var rawMinHistory = ctx.GetParameter("min_history_required");

        var priorApprovalCount = TryParseInt(rawPriorCount) ?? 0;
        var minHistoryRequired = TryParseInt(rawMinHistory) ?? DefaultMinHistoryRequired;

        activity?.SetTag("prior_approval_count", priorApprovalCount);
        activity?.SetTag("min_history_required", minHistoryRequired);

        // ── Step 5: insufficient history → Escalate ───────────────────────────────
        if (priorApprovalCount < minHistoryRequired)
        {
            _logger.LogInformation(
                "C-049: prior_approval_count {Count} < min_history_required {Min} for TenantId={TenantId} ActionType={ActionType}; escalating",
                priorApprovalCount,
                minHistoryRequired,
                ctx.TenantId,
                ctx.ActionType);

            activity?.SetTag("escalate_reason", "insufficient_prior_history");
            activity?.SetTag("verdict", nameof(EvaluationVerdict.Escalate));

            return Task.FromResult(Escalate(
                $"C-049: prior approval count {priorApprovalCount} is below " +
                $"minimum required history {minHistoryRequired} — escalating to human review"));
        }

        // ── Step 6: all C-049 conditions satisfied → Allow ────────────────────────
        _logger.LogInformation(
            "C-049: Allow — confidence={Score:F4} >= threshold={Threshold:F4}, " +
            "history={Count} >= min={Min} for TenantId={TenantId} ActionType={ActionType}",
            confidenceScore.Value,
            threshold,
            priorApprovalCount,
            minHistoryRequired,
            ctx.TenantId,
            ctx.ActionType);

        activity?.SetTag("verdict", nameof(EvaluationVerdict.Allow));

        return Task.FromResult(Allow(
            $"C-049: confidence {confidenceScore.Value:F4} meets threshold {threshold:F4}; " +
            $"prior approvals {priorApprovalCount} meets minimum {minHistoryRequired}"));
    }

    // C-073: factory helpers — ensure ClaimId is always populated on results
    private EvaluationResult Allow(string reason) =>
        new(ClaimId, EvaluationVerdict.Allow, reason);

    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);

    /// <summary>
    /// Parses a float string using invariant culture.
    /// Returns null for null, empty, whitespace, or unparseable input.
    /// </summary>
    private static float? TryParseFloat(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        return float.TryParse(
            raw,
            NumberStyles.Float,
            CultureInfo.InvariantCulture,
            out var value)
            ? value
            : null;
    }

    /// <summary>
    /// Parses an integer string.
    /// Returns null for null, empty, whitespace, or unparseable input.
    /// </summary>
    private static int? TryParseInt(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        return int.TryParse(raw, out var value) ? value : null;
    }
}