// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation), C-076 (Test Coverage)

#nullable enable

using System.Diagnostics;
using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-049 (Honest Limitation) at ValidateAction time.
///
/// C-049 requires the AI to be honest about the boundaries of its competence.
/// When a proposed action carries a confidence score below the configured threshold,
/// or when there is insufficient prior approval history to establish a reliable pattern,
/// the evaluator escalates the action to human oversight (Sujay) rather than permitting
/// autonomous execution.
///
/// Escalate is the C-049 path — NOT Deny. The action is not unconstitutional; the AI
/// is simply acknowledging its limitation and deferring to a human decision-maker.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource must be shared across all evaluators (single logical tracer unit)
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    /// <summary>
    /// Platform default confidence threshold. Actions whose confidence_score parameter
    /// is below this value are escalated unless the request supplies configured_threshold.
    /// </summary>
    private const float DefaultConfidenceThreshold = 0.70f;

    /// <summary>
    /// Platform default minimum prior approval history. Zero means no history gate by default;
    /// individual contracts may supply a higher requirement via min_history_required.
    /// </summary>
    private const int DefaultMinHistoryRequired = 0;

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    // C-073: Constructor enforces C-049 Honest Limitation claim at runtime via DI registration.
    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc />
    public string ClaimId => "C-049";

    /// <summary>
    /// C-073: Evaluates C-049 (Honest Limitation).
    ///
    /// Algorithm:
    ///   1. Extract confidence_score, configured_threshold, prior_approval_count,
    ///      and min_history_required from the JSON-encoded ActionParameters.
    ///   2. If prior_approval_count &lt; min_history_required → Escalate (insufficient history).
    ///   3. If confidence_score &lt; threshold → Escalate (AI below competence boundary).
    ///   4. Otherwise → Allow.
    ///
    /// MUST NOT perform network I/O. All reads are from EvaluationContext only.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Trace every evaluation for constitutional auditability (C-059)
        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.Evaluate", ActivityKind.Internal);
        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Step 1: Extract parameters from JSON-encoded ActionParameters ──────────
        // DESIGN_QUESTION: Should an absent confidence_score default to Allow (assume full
        // confidence) or Escalate (assume unknown = uncertain)? Current choice: absent score
        // is treated as fully confident (rawConfidence == null → skip threshold check).
        // EA review requested if C-049 should invert this default.

        float? rawConfidence = TryParseFloat(ctx.GetParameter("confidence_score"));
        float? rawThreshold  = TryParseFloat(ctx.GetParameter("configured_threshold"));
        int?   rawHistory    = TryParseInt(ctx.GetParameter("prior_approval_count"));
        int?   rawMinHistory = TryParseInt(ctx.GetParameter("min_history_required"));

        float threshold          = rawThreshold  ?? DefaultConfidenceThreshold;
        int   priorApprovalCount = rawHistory    ?? 0;
        int   minHistoryRequired = rawMinHistory ?? DefaultMinHistoryRequired;

        activity?.SetTag("c049.confidence_score",      rawConfidence?.ToString(CultureInfo.InvariantCulture) ?? "absent");
        activity?.SetTag("c049.configured_threshold",  threshold);
        activity?.SetTag("c049.prior_approval_count",  priorApprovalCount);
        activity?.SetTag("c049.min_history_required",  minHistoryRequired);

        // ── Step 2: History gate ──────────────────────────────────────────────────
        // C-073: C-049 — escalate when the approval history is too thin to be reliable.
        if (priorApprovalCount < minHistoryRequired)
        {
            _logger.LogWarning(
                "C-049 Escalate: insufficient prior approval history. " +
                "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId} " +
                "PriorApprovalCount={PriorApprovalCount} MinHistoryRequired={MinHistoryRequired}",
                ctx.TenantId, ctx.ActionType, ctx.ContractId,
                priorApprovalCount, minHistoryRequired);

            activity?.SetTag("c049.outcome", "escalate_insufficient_history");

            return Task.FromResult(Escalate(
                $"C-049: Insufficient prior approval history for autonomous execution. " +
                $"Required={minHistoryRequired}, Actual={priorApprovalCount}. " +
                $"Escalating to human oversight."));
        }

        // ── Step 3: Confidence threshold gate ────────────────────────────────────
        // C-073: C-049 — escalate when expressed confidence is below the agreed threshold.
        // Only checked when a confidence_score was actually supplied; absent score passes through.
        if (rawConfidence.HasValue && rawConfidence.Value < threshold)
        {
            _logger.LogWarning(
                "C-049 Escalate: confidence score below threshold. " +
                "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId} " +
                "ConfidenceScore={ConfidenceScore:F4} Threshold={Threshold:F4}",
                ctx.TenantId, ctx.ActionType, ctx.ContractId,
                rawConfidence.Value, threshold);

            activity?.SetTag("c049.outcome", "escalate_low_confidence");

            return Task.FromResult(Escalate(
                $"C-049: Confidence score {rawConfidence.Value:F2} is below the required " +
                $"threshold {threshold:F2}. Escalating to human oversight."));
        }

        // ── Step 4: Allow ─────────────────────────────────────────────────────────
        _logger.LogInformation(
            "C-049 Allow: confidence within limits and history sufficient. " +
            "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId} " +
            "ConfidenceScore={ConfidenceScore} Threshold={Threshold:F4}",
            ctx.TenantId, ctx.ActionType, ctx.ContractId,
            rawConfidence.HasValue ? rawConfidence.Value.ToString("F4", CultureInfo.InvariantCulture) : "absent",
            threshold);

        activity?.SetTag("c049.outcome", "allow");

        return Task.FromResult(Allow(
            "C-049: Confidence and approval history satisfy constitutional requirements."));
    }

    // ── Private helpers ───────────────────────────────────────────────────────────

    private EvaluationResult Allow(string reason) =>
        new(ClaimId, EvaluationVerdict.Allow, reason);

    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);

    /// <summary>
    /// Parses a nullable float from a JSON parameter string value.
    /// Uses InvariantCulture to handle "0.70" regardless of host locale.
    /// Returns null when the raw value is absent, empty, or unparseable.
    /// </summary>
    private static float? TryParseFloat(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return null;

        return float.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var value)
            ? value
            : null;
    }

    /// <summary>
    /// Parses a nullable int from a JSON parameter string value.
    /// Returns null when the raw value is absent, empty, or unparseable.
    /// </summary>
    private static int? TryParseInt(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return null;

        return int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out var value)
            ? value
            : null;
    }
}