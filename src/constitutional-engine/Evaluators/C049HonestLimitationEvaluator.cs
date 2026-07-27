// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Constitutional Annotation), C-076 (≥90% test coverage)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Implements constitutional claim C-049 (Honest Limitation).
/// When an agent's confidence score falls below the configured threshold, or when
/// it lacks sufficient prior-approval history, this evaluator escalates to human
/// review rather than proceeding autonomously.  Escalate (not Deny) is the correct
/// constitutional response — the action is uncertain, not prohibited.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: OpenTelemetry tracer — every constitutional evaluation is observable.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    /// <summary>Default confidence threshold below which escalation is required (C-049).</summary>
    private const float DefaultConfidenceThreshold = 0.70f;

    /// <summary>
    /// Default minimum number of prior approvals required before autonomous execution.
    /// Zero means no history gate is applied unless the caller specifies one.
    /// </summary>
    private const int DefaultMinHistoryRequired = 0;

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    // ── Constructor ──────────────────────────────────────────────────────────────
    // C-073: Constructor injection — no service location.
    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // ── IClaimEvaluator ──────────────────────────────────────────────────────────

    /// <summary>C-049: Honest Limitation claim identifier.</summary>
    public string ClaimId => "C-049";

    /// <summary>
    /// C-073: Evaluates whether the agent has sufficient confidence and approval history
    /// to proceed autonomously.  Returns <see cref="EvaluationVerdict.Escalate"/> whenever
    /// either gate fails — Escalate signals "forward to Sujay" rather than a hard denial.
    /// Returns <see cref="EvaluationVerdict.Allow"/> only when both gates pass.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Every constitutional evaluation is traced.
        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("tenant_id",   ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Parse action parameters ──────────────────────────────────────────────
        // ActionParameters is a JSON-encoded string; use GetParameter() — never TryGetValue().

        float?  confidenceScore     = TryParseFloat(ctx.GetParameter("confidence_score"));
        float   configuredThreshold = TryParseFloat(ctx.GetParameter("configured_threshold"))
                                      ?? DefaultConfidenceThreshold;
        int?    priorApprovalCount  = TryParseInt(ctx.GetParameter("prior_approval_count"));
        int     minHistoryRequired  = TryParseInt(ctx.GetParameter("min_history_required"))
                                      ?? DefaultMinHistoryRequired;

        activity?.SetTag("confidence_score",     confidenceScore?.ToString() ?? "absent");
        activity?.SetTag("configured_threshold", configuredThreshold);
        activity?.SetTag("prior_approval_count", priorApprovalCount?.ToString() ?? "absent");
        activity?.SetTag("min_history_required", minHistoryRequired);

        // ── Gate 1: Prior-approval history (C-049 §history gate) ────────────────
        // If a minimum history is required and the agent does not yet have it,
        // escalate — the agent has not demonstrated enough track record for this
        // action type to proceed unilaterally.
        if (minHistoryRequired > DefaultMinHistoryRequired)
        {
            int actualHistory = priorApprovalCount ?? 0;

            if (actualHistory < minHistoryRequired)
            {
                _logger.LogInformation(
                    "C-049 history gate: priorApprovalCount={PriorApprovalCount} < minHistoryRequired={MinHistoryRequired}. " +
                    "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}. Escalating.",
                    actualHistory, minHistoryRequired,
                    ctx.TenantId, ctx.ActionType, ctx.ContractId);

                activity?.SetTag("c049.gate",   "history");
                activity?.SetTag("c049.verdict", "escalate");

                return Task.FromResult(Escalate(
                    $"C-049: Insufficient approval history — " +
                    $"have {actualHistory}, require {minHistoryRequired} " +
                    $"before autonomous execution of action type '{ctx.ActionType}'."));
            }
        }

        // ── Gate 2: Confidence score (C-049 §confidence gate) ───────────────────
        // If a confidence score is supplied and falls below the threshold, the
        // agent must acknowledge its limitation and route to human review.
        // If no confidence score is supplied we allow — absence of a score is not
        // grounds for escalation (the evaluator cannot measure what was not provided).
        if (confidenceScore.HasValue)
        {
            if (confidenceScore.Value < configuredThreshold)
            {
                _logger.LogInformation(
                    "C-049 confidence gate: confidenceScore={ConfidenceScore:F4} < threshold={Threshold:F4}. " +
                    "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}. Escalating.",
                    confidenceScore.Value, configuredThreshold,
                    ctx.TenantId, ctx.ActionType, ctx.ContractId);

                activity?.SetTag("c049.gate",    "confidence");
                activity?.SetTag("c049.verdict",  "escalate");
                activity?.SetTag("c049.score",    confidenceScore.Value);
                activity?.SetTag("c049.threshold", configuredThreshold);

                return Task.FromResult(Escalate(
                    $"C-049: Confidence score {confidenceScore.Value:F4} is below " +
                    $"configured threshold {configuredThreshold:F4} for action type '{ctx.ActionType}'. " +
                    $"Escalating to human review per Honest Limitation principle."));
            }

            _logger.LogInformation(
                "C-049 confidence gate passed: confidenceScore={ConfidenceScore:F4} >= threshold={Threshold:F4}. " +
                "TenantId={TenantId} ActionType={ActionType}.",
                confidenceScore.Value, configuredThreshold,
                ctx.TenantId, ctx.ActionType);
        }
        else
        {
            _logger.LogInformation(
                "C-049: No confidence_score parameter present — skipping confidence gate. " +
                "TenantId={TenantId} ActionType={ActionType}.",
                ctx.TenantId, ctx.ActionType);
        }

        // ── Both gates passed ────────────────────────────────────────────────────
        activity?.SetTag("c049.verdict", "allow");

        _logger.LogInformation(
            "C-049 Allow: confidence and history gates passed. " +
            "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}.",
            ctx.TenantId, ctx.ActionType, ctx.ContractId);

        return Task.FromResult(Allow(
            "C-049: Confidence sufficient and approval history requirements satisfied."));
    }

    // ── Private helpers ──────────────────────────────────────────────────────────

    // C-073: Helper produces Allow result — ClaimId is always this evaluator's ID.
    private EvaluationResult Allow(string reason) =>
        new(ClaimId, EvaluationVerdict.Allow, reason);

    // C-073: Helper produces Escalate result — routes to human (Sujay) via C-049 path.
    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);

    /// <summary>
    /// Safely parses a nullable string to float.
    /// Returns null when the string is null, empty, or not a valid float.
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
    /// Safely parses a nullable string to int.
    /// Returns null when the string is null, empty, or not a valid integer.
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