// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation), C-076 (Test Coverage)

#nullable enable

using System.Diagnostics;
using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 Honest Limitation Evaluator.
/// Enforces the constitutional obligation that the AI must escalate to human review
/// whenever its confidence is below the configured threshold or it lacks sufficient
/// prior-approval history to act autonomously.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource for distributed tracing — every constitutional evaluation is observable.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    /// <summary>Default confidence threshold applied when the request carries no configured_threshold.</summary>
    private const float DefaultConfidenceThreshold = 0.70f;

    /// <summary>Default minimum prior-approval count when the request carries no min_history_required.</summary>
    private const int DefaultMinHistoryRequired = 0;

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId identifies the constitutional claim this evaluator enforces.
    public string ClaimId => "C-049";

    /// <summary>
    /// C-073: Implements C-049 Honest Limitation.
    /// Escalates to human review when the agent's confidence score is below the threshold
    /// or when the agent lacks the minimum prior-approval history to proceed autonomously.
    /// Never denies outright — uncertainty routes to a human, not a hard block.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Start a trace span so every C-049 evaluation decision is recorded in OTel.
        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Read synthetic approval parameters from the JSON-encoded ActionParameters ──
        // All values extracted via ctx.GetParameter() — NEVER ctx.ActionParameters.TryGetValue().
        float? confidenceScore      = TryParseFloat(ctx.GetParameter("confidence_score"));
        float? configuredThreshold  = TryParseFloat(ctx.GetParameter("configured_threshold"));
        int?   priorApprovalCount   = TryParseInt(ctx.GetParameter("prior_approval_count"));
        int?   minHistoryRequired   = TryParseInt(ctx.GetParameter("min_history_required"));

        float effectiveThreshold = configuredThreshold ?? DefaultConfidenceThreshold;
        int   effectiveMinHistory = minHistoryRequired ?? DefaultMinHistoryRequired;

        activity?.SetTag("confidence_score",     confidenceScore?.ToString(CultureInfo.InvariantCulture) ?? "absent");
        activity?.SetTag("effective_threshold",  effectiveThreshold.ToString(CultureInfo.InvariantCulture));
        activity?.SetTag("prior_approval_count", priorApprovalCount?.ToString(CultureInfo.InvariantCulture) ?? "absent");
        activity?.SetTag("effective_min_history", effectiveMinHistory.ToString(CultureInfo.InvariantCulture));

        // ── Guard: if no synthetic-approval context is present, C-049 is not applicable ──
        // An action that carries no confidence signal is not a synthetic-approval action;
        // other evaluators (C-041, C-043) cover it. Allow and continue chain.
        if (confidenceScore is null && priorApprovalCount is null)
        {
            _logger.LogDebug(
                "C-049: No confidence parameters present — not a synthetic-approval action. " +
                "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("c049_outcome", "not_applicable");
            return Task.FromResult(Allow("C-049: No synthetic approval context — claim not applicable to this action"));
        }

        // ── C-073: Check 1 — confidence score must meet or exceed the threshold ──
        if (confidenceScore is not null && confidenceScore < effectiveThreshold)
        {
            _logger.LogWarning(
                "C-049: Confidence {ConfidenceScore:F4} below threshold {Threshold:F4} — escalating to human review. " +
                "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                confidenceScore, effectiveThreshold, ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("c049_outcome", "escalate_confidence");
            return Task.FromResult(Escalate(
                $"C-049: Confidence score {confidenceScore.Value:F4} is below the required threshold " +
                $"{effectiveThreshold:F4} — human review required before autonomous execution"));
        }

        // ── C-073: Check 2 — agent must have sufficient prior-approval history ──
        if (priorApprovalCount is not null && priorApprovalCount < effectiveMinHistory)
        {
            _logger.LogWarning(
                "C-049: PriorApprovalCount {PriorApprovalCount} below MinHistoryRequired {MinHistoryRequired} " +
                "— escalating to human review. TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                priorApprovalCount, effectiveMinHistory, ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("c049_outcome", "escalate_history");
            return Task.FromResult(Escalate(
                $"C-049: Prior approval count {priorApprovalCount.Value} is below the minimum history required " +
                $"{effectiveMinHistory} — human review required before autonomous execution"));
        }

        // ── All C-049 checks passed — allow the action to continue through the evaluator chain ──
        _logger.LogInformation(
            "C-049: Allow — confidence and history requirements satisfied. " +
            "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId} " +
            "ConfidenceScore={ConfidenceScore} Threshold={Threshold} " +
            "PriorApprovalCount={PriorApprovalCount} MinHistoryRequired={MinHistoryRequired}",
            ctx.TenantId, ctx.ActionType, ctx.ContractId,
            confidenceScore?.ToString("F4", CultureInfo.InvariantCulture) ?? "absent",
            effectiveThreshold,
            priorApprovalCount?.ToString(CultureInfo.InvariantCulture) ?? "absent",
            effectiveMinHistory);

        activity?.SetTag("c049_outcome", "allow");
        return Task.FromResult(Allow(
            $"C-049: Confidence and approval-history requirements satisfied " +
            $"(score={confidenceScore?.ToString("F4", CultureInfo.InvariantCulture) ?? "N/A"} " +
            $"≥ threshold={effectiveThreshold:F4}, " +
            $"history={priorApprovalCount?.ToString(CultureInfo.InvariantCulture) ?? "N/A"} " +
            $"≥ required={effectiveMinHistory})"));
    }

    // ── Private helpers ──────────────────────────────────────────────────────────────────

    /// <summary>
    /// Constructs an Allow result for this evaluator.
    /// Allow does NOT mean the full chain is satisfied — subsequent evaluators still run.
    /// </summary>
    private EvaluationResult Allow(string reason) =>
        new(ClaimId, EvaluationVerdict.Allow, reason);

    /// <summary>
    /// Constructs an Escalate result for this evaluator.
    /// Escalate signals that the action is uncertain and must be reviewed by a human (C-049 path).
    /// The ConstitutionalEngineService treats Escalate as a non-approval outcome.
    /// </summary>
    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);

    /// <summary>
    /// Attempts to parse a float from a parameter string using invariant culture.
    /// Returns null if the string is null, empty, whitespace, or not a valid float.
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
    /// Attempts to parse an int from a parameter string.
    /// Returns null if the string is null, empty, whitespace, or not a valid integer.
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