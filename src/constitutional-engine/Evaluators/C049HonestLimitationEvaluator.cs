// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation), C-076 (Test Coverage)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-049 (Honest Limitation).
/// When the AI is operating near or beyond its confidence boundary — as indicated by a
/// confidence_score below the configured_threshold, or by insufficient prior approval
/// history — the action is ESCALATED to a human rather than autonomously approved or denied.
/// Default: ALLOW when no confidence parameters are supplied (non-applicable action type).
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

    // C-073: Implements constitutional claim C-049 (Honest Limitation)
    public string ClaimId => "C-049";

    /// <summary>
    /// C-073: Evaluates whether the action's confidence posture satisfies C-049 (Honest Limitation).
    ///
    /// Resolution logic (in order):
    ///  1. If "confidence_score" and "configured_threshold" are present in ActionParameters
    ///     and confidence_score &lt; configured_threshold → ESCALATE.
    ///  2. If "prior_approval_count" and "min_history_required" are present
    ///     and prior_approval_count &lt; min_history_required → ESCALATE.
    ///  3. Otherwise → ALLOW (confidence requirements satisfied or not applicable).
    ///
    /// DESIGN_QUESTION: Should a missing confidence_score on a SYNTHETIC_APPROVAL action type
    /// default to ESCALATE rather than ALLOW? EA to confirm default-open vs. default-closed
    /// posture for C-049 when parameters are absent.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: Activity tracing for every constitutional evaluation
        using var activity = _tracer.StartActivity("C049.EvaluateAsync", ActivityKind.Internal);
        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Check 1: Confidence score vs. configured threshold ────────────────────────────
        // C-073: C-049 requires escalation when confidence is below the operator-configured
        //         threshold. Parameters arrive JSON-encoded in ActionParameters.
        var confidenceScoreRaw   = ctx.GetParameter("confidence_score");
        var configuredThresholdRaw = ctx.GetParameter("configured_threshold");

        if (confidenceScoreRaw is not null && configuredThresholdRaw is not null)
        {
            // C-073: Parse with invariant culture; malformed values are treated as
            //         "not present" — we do not deny on parse failure, only on clear breach.
            if (float.TryParse(confidenceScoreRaw,
                                System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture,
                                out float confidenceScore)
                && float.TryParse(configuredThresholdRaw,
                                   System.Globalization.NumberStyles.Float,
                                   System.Globalization.CultureInfo.InvariantCulture,
                                   out float configuredThreshold))
            {
                activity?.SetTag("confidence_score", confidenceScore);
                activity?.SetTag("configured_threshold", configuredThreshold);

                if (confidenceScore < configuredThreshold)
                {
                    // C-073: C-049 mandates Escalate (not Deny) — human must decide
                    _logger.LogInformation(
                        "C-049 Escalate: confidence_score={ConfidenceScore:F4} below threshold={Threshold:F4} " +
                        "for tenant={TenantId} contract={ContractId} action={ActionType}",
                        confidenceScore, configuredThreshold, ctx.TenantId, ctx.ContractId, ctx.ActionType);

                    activity?.SetTag("verdict", "Escalate");
                    activity?.SetTag("escalate_reason", "confidence_below_threshold");

                    return Task.FromResult(new EvaluationResult(
                        ClaimId,
                        EvaluationVerdict.Escalate,
                        $"Confidence score {confidenceScore:F4} is below the configured threshold " +
                        $"{configuredThreshold:F4}. Human review required per C-049 (Honest Limitation)."));
                }

                _logger.LogInformation(
                    "C-049 confidence check passed: score={ConfidenceScore:F4} >= threshold={Threshold:F4} " +
                    "for tenant={TenantId}",
                    confidenceScore, configuredThreshold, ctx.TenantId);
            }
            else
            {
                // C-073: Malformed float values — log and continue; do not escalate on bad data
                _logger.LogWarning(
                    "C-049 could not parse confidence parameters: confidence_score={RawScore} " +
                    "configured_threshold={RawThreshold} for tenant={TenantId}. Skipping confidence check.",
                    confidenceScoreRaw, configuredThresholdRaw, ctx.TenantId);
            }
        }

        // ── Check 2: Prior approval history ──────────────────────────────────────────────
        // C-073: C-049 requires escalation when insufficient historical precedent exists
        //         for autonomous approval of this action class.
        var priorApprovalCountRaw  = ctx.GetParameter("prior_approval_count");
        var minHistoryRequiredRaw  = ctx.GetParameter("min_history_required");

        if (priorApprovalCountRaw is not null && minHistoryRequiredRaw is not null)
        {
            if (int.TryParse(priorApprovalCountRaw, out int priorApprovalCount)
                && int.TryParse(minHistoryRequiredRaw, out int minHistoryRequired))
            {
                activity?.SetTag("prior_approval_count", priorApprovalCount);
                activity?.SetTag("min_history_required", minHistoryRequired);

                if (priorApprovalCount < minHistoryRequired)
                {
                    // C-073: C-049 mandates Escalate — insufficient precedent for autonomous action
                    _logger.LogInformation(
                        "C-049 Escalate: prior_approval_count={PriorCount} below min_history_required={MinRequired} " +
                        "for tenant={TenantId} contract={ContractId} action={ActionType}",
                        priorApprovalCount, minHistoryRequired, ctx.TenantId, ctx.ContractId, ctx.ActionType);

                    activity?.SetTag("verdict", "Escalate");
                    activity?.SetTag("escalate_reason", "insufficient_approval_history");

                    return Task.FromResult(new EvaluationResult(
                        ClaimId,
                        EvaluationVerdict.Escalate,
                        $"Insufficient approval history: {priorApprovalCount} prior approvals recorded, " +
                        $"{minHistoryRequired} required before autonomous execution (C-049 Honest Limitation)."));
                }

                _logger.LogInformation(
                    "C-049 history check passed: prior_approval_count={PriorCount} >= min_history_required={MinRequired} " +
                    "for tenant={TenantId}",
                    priorApprovalCount, minHistoryRequired, ctx.TenantId);
            }
            else
            {
                // C-073: Malformed integer values — log and continue
                _logger.LogWarning(
                    "C-049 could not parse history parameters: prior_approval_count={RawCount} " +
                    "min_history_required={RawMin} for tenant={TenantId}. Skipping history check.",
                    priorApprovalCountRaw, minHistoryRequiredRaw, ctx.TenantId);
            }
        }

        // ── Default: ALLOW ────────────────────────────────────────────────────────────────
        // C-073: Neither confidence nor history checks triggered an Escalate.
        //         Action may proceed — C-049 requirements satisfied.
        _logger.LogInformation(
            "C-049 Allow: honest-limitation requirements satisfied for tenant={TenantId} " +
            "contract={ContractId} action={ActionType}",
            ctx.TenantId, ctx.ContractId, ctx.ActionType);

        activity?.SetTag("verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-049 requirements satisfied: confidence and approval history meet configured thresholds."));
    }
}