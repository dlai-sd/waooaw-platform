// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-073 (Annotation), C-059 (Traceability)

#nullable enable

using System.Diagnostics;
using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-049 (Honest Limitation) — the AI must not proceed autonomously
/// when its confidence falls below the configured threshold, or when it lacks sufficient
/// prior approval history for the action class. Such actions are escalated to human
/// review (Sujay) rather than denied outright or approved by default.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource scoped to the constitutional engine telemetry pipeline (ADR-009)
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private const float DefaultConfidenceThreshold = 0.70f;
    private const int DefaultMinHistoryRequired = 0; // 0 = no history gate unless explicitly configured

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    /// <summary>
    /// C-073: Constructor enforces DI contract — logger is mandatory for structured audit trail.
    /// </summary>
    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId identifies this evaluator as the runtime enforcer of C-049
    public string ClaimId => "C-049";

    /// <summary>
    /// C-073: Evaluates C-049 (Honest Limitation).
    /// Reads synthetic approval context from ActionParameters JSON via EvaluationContext.GetParameter().
    /// Decision matrix:
    ///   • No SyntheticApprovalContext present  → Allow  (claim not applicable to this action)
    ///   • confidence_score &lt; threshold       → Escalate (insufficient confidence)
    ///   • prior_approval_count &lt; min_history → Escalate (insufficient history)
    ///   • Both checks pass                     → Allow
    /// Returns Escalate (not Deny) — C-049 is a human-review gate, not a hard block.
    /// MUST NOT perform network I/O. Completes synchronously; returns completed Task.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: Validate inputs per C-049 defensive posture
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // Extract SyntheticApprovalContext fields from JSON-encoded ActionParameters
        float? confidenceScore    = TryParseFloat(ctx.GetParameter("confidence_score"));
        float? configuredThreshold = TryParseFloat(ctx.GetParameter("configured_threshold"));
        int?   priorApprovalCount = TryParseInt(ctx.GetParameter("prior_approval_count"));
        int?   minHistoryRequired = TryParseInt(ctx.GetParameter("min_history_required"));

        // Apply defaults when the caller omits optional fields
        float effectiveThreshold  = configuredThreshold ?? DefaultConfidenceThreshold;
        int   effectiveMinHistory = minHistoryRequired  ?? DefaultMinHistoryRequired;

        activity?.SetTag("confidence_score",     confidenceScore?.ToString(CultureInfo.InvariantCulture) ?? "absent");
        activity?.SetTag("effective_threshold",  effectiveThreshold.ToString(CultureInfo.InvariantCulture));
        activity?.SetTag("prior_approval_count", priorApprovalCount?.ToString(CultureInfo.InvariantCulture) ?? "absent");
        activity?.SetTag("effective_min_history", effectiveMinHistory.ToString(CultureInfo.InvariantCulture));

        // ── Guard: if no SyntheticApprovalContext was provided, C-049 is not applicable ──
        // Not all actions carry a confidence payload (e.g., pure tool calls with no ML score).
        // Silence the evaluator rather than producing a false Escalate.
        if (confidenceScore is null && priorApprovalCount is null)
        {
            _logger.LogInformation(
                "C-049: No SyntheticApprovalContext for TenantId={TenantId} ActionType={ActionType} ContractId={ContractId} — evaluator not applicable",
                ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("c049.outcome", "allow_no_context");
            return Task.FromResult(Allow("C-049: No synthetic approval context — claim not applicable to this action"));
        }

        // ── Check 1: Confidence score vs. threshold ──────────────────────────────────────
        if (confidenceScore is not null && confidenceScore.Value < effectiveThreshold)
        {
            _logger.LogWarning(
                "C-049: Confidence below threshold for TenantId={TenantId} ActionType={ActionType} " +
                "ContractId={ContractId} ConfidenceScore={ConfidenceScore:F4} Threshold={Threshold:F4} — escalating to human review",
                ctx.TenantId, ctx.ActionType, ctx.ContractId,
                confidenceScore.Value, effectiveThreshold);

            activity?.SetTag("c049.outcome", "escalate_low_confidence");
            activity?.SetTag("c049.confidence_score", confidenceScore.Value);
            activity?.SetTag("c049.threshold", effectiveThreshold);

            return Task.FromResult(Escalate(
                $"C-049: Confidence score {confidenceScore.Value:F4} is below required threshold " +
                $"{effectiveThreshold:F4} — escalating to human review (Sujay)"));
        }

        // ── Check 2: Prior approval history vs. minimum required ─────────────────────────
        if (priorApprovalCount is not null && priorApprovalCount.Value < effectiveMinHistory)
        {
            _logger.LogWarning(
                "C-049: Insufficient approval history for TenantId={TenantId} ActionType={ActionType} " +
                "ContractId={ContractId} PriorApprovalCount={PriorApprovalCount} MinRequired={MinRequired} — escalating to human review",
                ctx.TenantId, ctx.ActionType, ctx.ContractId,
                priorApprovalCount.Value, effectiveMinHistory);

            activity?.SetTag("c049.outcome", "escalate_insufficient_history");
            activity?.SetTag("c049.prior_approval_count", priorApprovalCount.Value);
            activity?.SetTag("c049.min_history_required", effectiveMinHistory);

            return Task.FromResult(Escalate(
                $"C-049: Prior approval count {priorApprovalCount.Value} is below the minimum required " +
                $"{effectiveMinHistory} — escalating to human review (Sujay)"));
        }

        // ── All checks passed ────────────────────────────────────────────────────────────
        _logger.LogInformation(
            "C-049: Honest limitation checks passed for TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
            ctx.TenantId, ctx.ActionType, ctx.ContractId);

        activity?.SetTag("c049.outcome", "allow");
        return Task.FromResult(Allow("C-049: Confidence and history requirements satisfied"));
    }

    // ── Private helpers ──────────────────────────────────────────────────────────────────

    private EvaluationResult Allow(string reason)
        => new(ClaimId, EvaluationVerdict.Allow, reason);

    private EvaluationResult Escalate(string reason)
        => new(ClaimId, EvaluationVerdict.Escalate, reason);

    /// <summary>
    /// Parses a float from a string extracted from JSON ActionParameters.
    /// Returns null on missing, empty, or malformed input — never throws.
    /// Uses InvariantCulture so "0.70" parses correctly regardless of server locale.
    /// </summary>
    private static float? TryParseFloat(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        return float.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var value)
            ? value
            : null;
    }

    /// <summary>
    /// Parses an int from a string extracted from JSON ActionParameters.
    /// Returns null on missing, empty, or malformed input — never throws.
    /// </summary>
    private static int? TryParseInt(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        return int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out var value)
            ? value
            : null;
    }
}