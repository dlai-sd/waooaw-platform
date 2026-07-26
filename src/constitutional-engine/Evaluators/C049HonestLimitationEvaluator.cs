// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 Honest Limitation Evaluator.
/// Enforces the constitutional obligation that the AI must never misrepresent its confidence
/// or operate outside its known capability boundaries without human escalation.
///
/// Decision matrix:
///   outside_known_capability == "true"               → Deny   (C-049 absolute boundary)
///   confidence_score &lt; configured_threshold           → Escalate (uncertain — route to human)
///   prior_approval_count &lt; min_history_required       → Escalate (insufficient evidence basis)
///   All checks pass                                  → Allow
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // ── Observability ─────────────────────────────────────────────────────────
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // ── Defaults ──────────────────────────────────────────────────────────────
    /// <summary>Default confidence threshold when none is supplied in action parameters.</summary>
    private const float DefaultConfidenceThreshold = 0.70f;

    /// <summary>Default minimum history count when none is supplied.</summary>
    private const int DefaultMinHistoryRequired = 0; // 0 = no history required by default

    // ── Dependencies ──────────────────────────────────────────────────────────
    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    // C-073: Constructor annotation — constitutional obligation wiring
    /// <summary>
    /// Initialises the evaluator.
    /// constitutional_annotation: C-049 (Honest Limitation) enforced via this evaluator.
    /// </summary>
    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // ── IClaimEvaluator ───────────────────────────────────────────────────────

    /// <inheritdoc/>
    public string ClaimId => "C-049";

    // C-073: Method annotation — constitutional obligation implementation
    /// <summary>
    /// Evaluates C-049 Honest Limitation.
    /// constitutional_annotation: enforces that AI acknowledges uncertainty and capability limits.
    /// No network I/O — pure in-memory evaluation from action parameters.
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

        // ── Check 1: explicit outside-capability flag (hard Deny) ─────────────
        // C-073: constitutional_obligation — C-049 absolute boundary enforcement
        var outsideCapabilityRaw = ctx.GetParameter("outside_known_capability");
        if (string.Equals(outsideCapabilityRaw?.Trim(), "true", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogWarning(
                "C-049 DENY: action explicitly marked outside_known_capability. " +
                "TenantId={TenantId} ActionType={ActionType}",
                ctx.TenantId, ctx.ActionType);

            activity?.SetTag("c049.decision", "Deny");
            activity?.SetTag("c049.reason", "outside_known_capability");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: "C-049: Action is explicitly marked as outside the AI's known capability boundary. " +
                        "Human authorisation required before proceeding."));
        }

        // ── Check 2: confidence score vs. configured threshold (Escalate) ─────
        // C-073: constitutional_obligation — uncertain actions must be escalated to human
        var confidenceRaw = ctx.GetParameter("confidence_score");
        var thresholdRaw  = ctx.GetParameter("configured_threshold");

        float? confidenceScore    = TryParseFloat(confidenceRaw);
        float  configuredThreshold = TryParseFloat(thresholdRaw) ?? DefaultConfidenceThreshold;

        if (confidenceScore.HasValue && confidenceScore.Value < configuredThreshold)
        {
            _logger.LogWarning(
                "C-049 ESCALATE: confidence_score={ConfidenceScore:F4} below threshold={Threshold:F4}. " +
                "TenantId={TenantId} ActionType={ActionType}",
                confidenceScore.Value, configuredThreshold, ctx.TenantId, ctx.ActionType);

            activity?.SetTag("c049.decision", "Escalate");
            activity?.SetTag("c049.confidence_score", confidenceScore.Value);
            activity?.SetTag("c049.configured_threshold", configuredThreshold);

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Escalate,
                Reason: $"C-049: Confidence score {confidenceScore.Value:F4} is below the " +
                        $"configured threshold {configuredThreshold:F4}. Action escalated to human review."));
        }

        // ── Check 3: prior approval count vs. minimum history required (Escalate) ──
        // C-073: constitutional_obligation — insufficient evidence basis requires human oversight
        var priorCountRaw    = ctx.GetParameter("prior_approval_count");
        var minHistoryRaw    = ctx.GetParameter("min_history_required");

        int? priorApprovalCount  = TryParseInt(priorCountRaw);
        int  minHistoryRequired  = TryParseInt(minHistoryRaw) ?? DefaultMinHistoryRequired;

        if (minHistoryRequired > 0
            && priorApprovalCount.HasValue
            && priorApprovalCount.Value < minHistoryRequired)
        {
            _logger.LogWarning(
                "C-049 ESCALATE: prior_approval_count={PriorCount} below min_history_required={MinHistory}. " +
                "TenantId={TenantId} ActionType={ActionType}",
                priorApprovalCount.Value, minHistoryRequired, ctx.TenantId, ctx.ActionType);

            activity?.SetTag("c049.decision", "Escalate");
            activity?.SetTag("c049.prior_approval_count", priorApprovalCount.Value);
            activity?.SetTag("c049.min_history_required", minHistoryRequired);

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Escalate,
                Reason: $"C-049: Insufficient approval history — {priorApprovalCount.Value} prior approvals " +
                        $"recorded, minimum {minHistoryRequired} required before autonomous execution."));
        }

        // ── All checks passed ─────────────────────────────────────────────────
        _logger.LogDebug(
            "C-049 ALLOW: honest limitation checks passed. " +
            "TenantId={TenantId} ActionType={ActionType}",
            ctx.TenantId, ctx.ActionType);

        activity?.SetTag("c049.decision", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: "C-049: Action is within known capability boundaries and confidence thresholds."));
    }

    // ── Private helpers ───────────────────────────────────────────────────────

    /// <summary>
    /// Attempts to parse a string value as a float.
    /// Returns null when the value is absent or unparseable — callers apply defaults.
    /// </summary>
    private static float? TryParseFloat(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return null;

        return float.TryParse(raw.Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out var v)
            ? v
            : null;
    }

    /// <summary>
    /// Attempts to parse a string value as an int.
    /// Returns null when the value is absent or unparseable — callers apply defaults.
    /// </summary>
    private static int? TryParseInt(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return null;

        return int.TryParse(raw.Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var v)
            ? v
            : null;
    }
}