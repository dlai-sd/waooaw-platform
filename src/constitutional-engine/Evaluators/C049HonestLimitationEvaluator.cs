// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Constitutional Annotation)

#nullable enable

using System.Diagnostics;
using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 Honest Limitation Evaluator.
///
/// Constitutional obligation: the agent MUST acknowledge uncertainty and escalate
/// to a human (Sujay) when it lacks the confidence or prior approval history to
/// act autonomously. An agent that suppresses its own uncertainty violates C-049.
///
/// Escalation logic:
///   • confidence_score present AND below effective threshold → Escalate
///   • min_history_required > 0 AND prior_approval_count absent → Escalate
///   • min_history_required > 0 AND prior_approval_count < min_history_required → Escalate
///   • All checks pass → Allow
///
/// Parameters consumed from EvaluationContext.ActionParameters (JSON-encoded):
///   "confidence_score"     — float 0..1, agent's self-assessed confidence for this action
///   "configured_threshold" — float 0..1, override threshold (defaults to 0.70)
///   "prior_approval_count" — int, number of prior human approvals for equivalent actions
///   "min_history_required" — int, minimum prior approvals required (defaults to 0)
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource for constitutional obligation tracing (ADR-009 OpenTelemetry)
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    /// <summary>
    /// Default minimum confidence score (0–1.0) an agent must have before acting autonomously.
    /// Configurable per-action via the "configured_threshold" parameter.
    /// </summary>
    private const float DefaultConfidenceThreshold = 0.70f;

    /// <summary>
    /// Default minimum number of prior human approvals required.
    /// Zero means no prior-history gate applies unless explicitly requested by the caller.
    /// </summary>
    private const int DefaultMinHistoryRequired = 0;

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    /// <summary>
    /// C-073: Constructor injection — logger required for constitutional audit trail.
    /// </summary>
    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>Constitutional claim enforced by this evaluator.</summary>
    public string ClaimId => "C-049";

    /// <summary>
    /// C-073: Evaluates C-049 Honest Limitation.
    ///
    /// Short-circuits via the EvaluatorRegistry on first Escalate (treated as non-DENY
    /// by the registry but surfaces to ValidateAction for human routing).
    /// MUST NOT perform network I/O — reads only from the JSON action parameters.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Trace constitutional evaluation span
        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Parameter extraction ────────────────────────────────────────────────
        // ctx.GetParameter() parses the JSON-encoded ActionParameters string.
        // Returns null when the key is absent — we apply defaults below.

        float? confidenceScore    = TryParseFloat(ctx.GetParameter("confidence_score"));
        float? configuredThreshold = TryParseFloat(ctx.GetParameter("configured_threshold"));
        int?   priorApprovalCount  = TryParseInt(ctx.GetParameter("prior_approval_count"));
        int?   minHistoryRequired  = TryParseInt(ctx.GetParameter("min_history_required"));

        float effectiveThreshold  = configuredThreshold ?? DefaultConfidenceThreshold;
        int   effectiveMinHistory = minHistoryRequired  ?? DefaultMinHistoryRequired;

        activity?.SetTag("confidence_score",      confidenceScore?.ToString("F4", CultureInfo.InvariantCulture) ?? "absent");
        activity?.SetTag("effective_threshold",   effectiveThreshold.ToString("F4", CultureInfo.InvariantCulture));
        activity?.SetTag("prior_approval_count",  priorApprovalCount?.ToString(CultureInfo.InvariantCulture)    ?? "absent");
        activity?.SetTag("effective_min_history", effectiveMinHistory.ToString(CultureInfo.InvariantCulture));

        // ── Check 1: Confidence below threshold ────────────────────────────────
        // C-049: Agent must not proceed when it knows its confidence is inadequate.
        if (confidenceScore.HasValue && confidenceScore.Value < effectiveThreshold)
        {
            var reason = string.Format(
                CultureInfo.InvariantCulture,
                "C-049: Agent confidence {0:F4} is below required threshold {1:F4}. " +
                "Escalating to human — agent must acknowledge its limitation.",
                confidenceScore.Value,
                effectiveThreshold);

            _logger.LogInformation(
                "C049 Escalate: confidence_score={ConfidenceScore:F4} threshold={Threshold:F4} " +
                "tenant={TenantId} contract={ContractId}",
                confidenceScore.Value, effectiveThreshold, ctx.TenantId, ctx.ContractId);

            activity?.SetTag("decision", "Escalate");
            activity?.SetTag("escalation_reason", "confidence_below_threshold");

            return Task.FromResult(Escalate(reason));
        }

        // ── Check 2: Insufficient prior approval history (count absent) ────────
        // C-049: When a minimum history gate is configured and no count is supplied,
        // we cannot verify the gate — safe path is to escalate.
        if (effectiveMinHistory > DefaultMinHistoryRequired && !priorApprovalCount.HasValue)
        {
            var reason = string.Format(
                CultureInfo.InvariantCulture,
                "C-049: prior_approval_count parameter absent but min_history_required={0}. " +
                "Escalating — cannot verify approval history without a count.",
                effectiveMinHistory);

            _logger.LogInformation(
                "C049 Escalate: prior_approval_count absent, min_history_required={MinHistory} " +
                "tenant={TenantId} contract={ContractId}",
                effectiveMinHistory, ctx.TenantId, ctx.ContractId);

            activity?.SetTag("decision", "Escalate");
            activity?.SetTag("escalation_reason", "approval_history_absent");

            return Task.FromResult(Escalate(reason));
        }

        // ── Check 3: Prior approval count below required minimum ───────────────
        // C-049: Agent has not accumulated enough human-validated history for this
        // action class. Escalate rather than proceed on insufficient precedent.
        if (effectiveMinHistory > DefaultMinHistoryRequired
            && priorApprovalCount.HasValue
            && priorApprovalCount.Value < effectiveMinHistory)
        {
            var reason = string.Format(
                CultureInfo.InvariantCulture,
                "C-049: prior_approval_count={0} is below min_history_required={1}. " +
                "Escalating — agent must build approval history before acting autonomously.",
                priorApprovalCount.Value,
                effectiveMinHistory);

            _logger.LogInformation(
                "C049 Escalate: prior_approval_count={PriorCount} min_history_required={MinHistory} " +
                "tenant={TenantId} contract={ContractId}",
                priorApprovalCount.Value, effectiveMinHistory, ctx.TenantId, ctx.ContractId);

            activity?.SetTag("decision", "Escalate");
            activity?.SetTag("escalation_reason", "insufficient_approval_history");

            return Task.FromResult(Escalate(reason));
        }

        // ── All checks passed ──────────────────────────────────────────────────
        // Agent confidence is adequate (or not asserted) and approval history
        // meets any configured minimum. C-049 is satisfied.
        _logger.LogInformation(
            "C049 Allow: confidence={ConfidenceScore} threshold={Threshold} " +
            "priorCount={PriorCount} minHistory={MinHistory} " +
            "tenant={TenantId} contract={ContractId}",
            confidenceScore.HasValue
                ? confidenceScore.Value.ToString("F4", CultureInfo.InvariantCulture)
                : "absent",
            effectiveThreshold.ToString("F4", CultureInfo.InvariantCulture),
            priorApprovalCount.HasValue
                ? priorApprovalCount.Value.ToString(CultureInfo.InvariantCulture)
                : "absent",
            effectiveMinHistory,
            ctx.TenantId,
            ctx.ContractId);

        activity?.SetTag("decision", "Allow");

        return Task.FromResult(Allow(
            "C-049: Agent confidence meets the honest limitation threshold and " +
            "prior approval history is sufficient for autonomous action."));
    }

    // ── Private helpers ──────────────────────────────────────────────────────────

    // C-073: Constructs an Allow result attributed to C-049
    private EvaluationResult Allow(string reason) =>
        new(ClaimId, EvaluationVerdict.Allow, reason);

    // C-073: Constructs an Escalate result attributed to C-049
    // Escalate = action is uncertain → forward to human (Sujay) via C-049 path
    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);

    /// <summary>
    /// Parses a nullable float from a raw string parameter value.
    /// Returns null when the input is null, empty, whitespace, or not parseable.
    /// Uses InvariantCulture so "0.70" is always interpreted as 0.70 (not locale-dependent).
    /// </summary>
    private static float? TryParseFloat(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return null;

        return float.TryParse(
            raw,
            NumberStyles.Float | NumberStyles.AllowLeadingSign,
            CultureInfo.InvariantCulture,
            out var value)
            ? value
            : null;
    }

    /// <summary>
    /// Parses a nullable int from a raw string parameter value.
    /// Returns null when the input is null, empty, whitespace, or not parseable.
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