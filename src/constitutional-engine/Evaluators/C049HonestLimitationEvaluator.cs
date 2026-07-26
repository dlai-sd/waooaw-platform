// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-049 Honest Limitation: when the AI agent lacks sufficient confidence or
/// insufficient approval history to proceed autonomously, it MUST escalate to human
/// oversight (Sujay) rather than guess. Escalate is not failure — it is constitutional.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");
    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc/>
    public string ClaimId => "C-049";

    // C-073: Constitutional obligation annotation — enforces C-049 Honest Limitation at runtime.
    // The agent must not act beyond its honest capability boundary. When confidence is below
    // the tenant-configured threshold, or when insufficient approval history exists, the
    // evaluator returns Escalate so the action is routed to human review, not autonomously
    // approved or silently denied.
    /// <inheritdoc/>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── C-049 Gate 1: Confidence score below configured threshold ──────────────────
        // SyntheticApprovalContext fields arrive via ActionParameters JSON.
        // ctx.GetParameter() safely parses the JSON-encoded string — never TryGetValue().
        var confidenceRaw   = ctx.GetParameter("confidence_score");
        var thresholdRaw    = ctx.GetParameter("configured_threshold");

        if (confidenceRaw is not null && thresholdRaw is not null)
        {
            if (double.TryParse(confidenceRaw, System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture, out var confidence) &&
                double.TryParse(thresholdRaw,  System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture, out var threshold))
            {
                activity?.SetTag("confidence_score", confidence);
                activity?.SetTag("configured_threshold", threshold);

                if (confidence < threshold)
                {
                    _logger.LogInformation(
                        "C-049 ESCALATE: confidence_score={ConfidenceScore:F4} below configured_threshold={Threshold:F4} " +
                        "for tenant={TenantId} action_type={ActionType}",
                        confidence, threshold, ctx.TenantId, ctx.ActionType);

                    activity?.SetTag("escalation_reason", "low_confidence");
                    activity?.SetTag("verdict", "Escalate");

                    return Task.FromResult(new EvaluationResult(
                        ClaimId: ClaimId,
                        Verdict: EvaluationVerdict.Escalate,
                        Reason: $"C-049: Confidence score {confidence:F4} is below the configured threshold " +
                                $"{threshold:F4}. Escalating to human oversight rather than proceeding autonomously."
                    ));
                }
            }
            else
            {
                // Malformed confidence parameters — cannot assess, must escalate (honest limitation).
                _logger.LogWarning(
                    "C-049 ESCALATE: malformed confidence parameters confidence_score={Raw1} " +
                    "configured_threshold={Raw2} for tenant={TenantId}",
                    confidenceRaw, thresholdRaw, ctx.TenantId);

                activity?.SetTag("escalation_reason", "malformed_confidence_parameters");
                activity?.SetTag("verdict", "Escalate");

                return Task.FromResult(new EvaluationResult(
                    ClaimId: ClaimId,
                    Verdict: EvaluationVerdict.Escalate,
                    Reason: "C-049: Confidence parameters are present but malformed — cannot assess limitation boundary. " +
                            "Escalating to human oversight."
                ));
            }
        }

        // ── C-049 Gate 2: Insufficient approval history ────────────────────────────────
        // prior_approval_count < min_history_required → not enough track record for autonomous action.
        var priorApprovalRaw = ctx.GetParameter("prior_approval_count");
        var minHistoryRaw    = ctx.GetParameter("min_history_required");

        if (priorApprovalRaw is not null && minHistoryRaw is not null)
        {
            if (int.TryParse(priorApprovalRaw, out var priorApprovals) &&
                int.TryParse(minHistoryRaw,    out var minHistory))
            {
                activity?.SetTag("prior_approval_count", priorApprovals);
                activity?.SetTag("min_history_required", minHistory);

                // Only escalate when a minimum history is actually required (minHistory > 0).
                // minHistory == 0 means the tenant has waived history requirements.
                if (minHistory > 0 && priorApprovals < minHistory)
                {
                    _logger.LogInformation(
                        "C-049 ESCALATE: prior_approval_count={PriorApprovals} below min_history_required={MinHistory} " +
                        "for tenant={TenantId} action_type={ActionType}",
                        priorApprovals, minHistory, ctx.TenantId, ctx.ActionType);

                    activity?.SetTag("escalation_reason", "insufficient_history");
                    activity?.SetTag("verdict", "Escalate");

                    return Task.FromResult(new EvaluationResult(
                        ClaimId: ClaimId,
                        Verdict: EvaluationVerdict.Escalate,
                        Reason: $"C-049: Prior approval count {priorApprovals} is below the minimum history " +
                                $"required {minHistory}. Insufficient track record for autonomous action. " +
                                "Escalating to human oversight."
                    ));
                }
            }
            else
            {
                // Malformed history parameters — cannot assess, must escalate.
                _logger.LogWarning(
                    "C-049 ESCALATE: malformed history parameters prior_approval_count={Raw1} " +
                    "min_history_required={Raw2} for tenant={TenantId}",
                    priorApprovalRaw, minHistoryRaw, ctx.TenantId);

                activity?.SetTag("escalation_reason", "malformed_history_parameters");
                activity?.SetTag("verdict", "Escalate");

                return Task.FromResult(new EvaluationResult(
                    ClaimId: ClaimId,
                    Verdict: EvaluationVerdict.Escalate,
                    Reason: "C-049: History parameters are present but malformed — cannot assess approval history. " +
                            "Escalating to human oversight."
                ));
            }
        }

        // ── All C-049 gates passed — action is within honest limitation bounds ─────────
        _logger.LogInformation(
            "C-049 ALLOW: action within honest limitation bounds for tenant={TenantId} action_type={ActionType}",
            ctx.TenantId, ctx.ActionType);

        activity?.SetTag("verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: "C-049: Action is within honest limitation bounds."
        ));
    }
}