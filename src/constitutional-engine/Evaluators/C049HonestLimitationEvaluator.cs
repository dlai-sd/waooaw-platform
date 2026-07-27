// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049
// constitutional_basis: C-049 (Honest Limitation), C-059 (Traceability), C-073 (Annotated Obligations)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-049 (Honest Limitation): when an action relies on synthetic/pattern-based
/// approval rather than explicit human authorization, the AI must acknowledge its
/// epistemic limitation. Actions with confidence below threshold, or with insufficient
/// approval history, are escalated to the human principal rather than auto-authorized.
/// </summary>
/// <remarks>
/// Escalate (not Deny) is the correct verdict — the action is not constitutionally prohibited,
/// but uncertainty is too high for autonomous execution. This maps to the C-049 escalation
/// path described in ce-validate-action-evaluators.md.
/// </remarks>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: constitutional obligation annotation
    /// <summary>Claim enforced by this evaluator.</summary>
    public string ClaimId => "C-049";

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    // Parameter keys expected in JSON-encoded ActionParameters
    private const string ParamConfidenceScore      = "confidence_score";
    private const string ParamConfiguredThreshold  = "configured_threshold";
    private const string ParamPriorApprovalCount   = "prior_approval_count";
    private const string ParamMinHistoryRequired   = "min_history_required";

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: this method directly implements C-049 constitutional obligation
    /// <inheritdoc />
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("contract_id",   ctx.ContractId);
        activity?.SetTag("action_type",   ctx.ActionType);
        activity?.SetTag("tenant_id",     ctx.TenantId);
        activity?.SetTag("claim_id",      ClaimId);

        // ── Applicability gate ──────────────────────────────────────────────────────────
        // C-049 only applies when the request carries a synthetic approval context.
        // Absence of confidence_score means the action is not pattern-based; pass through.
        var confidenceScoreRaw = ctx.GetParameter(ParamConfidenceScore);
        if (confidenceScoreRaw is null)
        {
            _logger.LogDebug(
                "C-049 not applicable: no synthetic approval context present. " +
                "ContractId={ContractId} ActionType={ActionType}",
                ctx.ContractId, ctx.ActionType);

            activity?.SetTag("c049.applicable", false);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                "C-049 not applicable: no synthetic approval context present"));
        }

        activity?.SetTag("c049.applicable", true);

        // ── Parse confidence_score ──────────────────────────────────────────────────────
        if (!float.TryParse(
                confidenceScoreRaw,
                System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture,
                out var confidenceScore))
        {
            _logger.LogWarning(
                "C-049 Escalate: malformed confidence_score value '{Value}'. " +
                "ContractId={ContractId} ActionType={ActionType}",
                confidenceScoreRaw, ctx.ContractId, ctx.ActionType);

            activity?.SetTag("c049.verdict",        "Escalate");
            activity?.SetTag("c049.escalate_reason", "malformed_confidence_score");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-049 honest limitation: malformed confidence_score '{confidenceScoreRaw}' — " +
                "cannot assess epistemic confidence; escalating to human principal"));
        }

        // ── Parse configured_threshold ──────────────────────────────────────────────────
        var configuredThresholdRaw = ctx.GetParameter(ParamConfiguredThreshold);
        if (configuredThresholdRaw is null ||
            !float.TryParse(
                configuredThresholdRaw,
                System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture,
                out var configuredThreshold))
        {
            _logger.LogWarning(
                "C-049 Escalate: missing or malformed configured_threshold '{Value}'. " +
                "ContractId={ContractId} ActionType={ActionType}",
                configuredThresholdRaw, ctx.ContractId, ctx.ActionType);

            activity?.SetTag("c049.verdict",        "Escalate");
            activity?.SetTag("c049.escalate_reason", "malformed_configured_threshold");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-049 honest limitation: missing or malformed configured_threshold — " +
                "cannot assess confidence boundary; escalating to human principal"));
        }

        activity?.SetTag("c049.confidence_score",    confidenceScore);
        activity?.SetTag("c049.configured_threshold", configuredThreshold);

        // ── Confidence threshold check ──────────────────────────────────────────────────
        // C-073: constitutional obligation — agent must not proceed when confidence is
        // below the tenant-configured threshold. Escalate, do not Deny.
        if (confidenceScore < configuredThreshold)
        {
            _logger.LogWarning(
                "C-049 Escalate: confidence {ConfidenceScore:F4} below threshold {Threshold:F4}. " +
                "ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
                confidenceScore, configuredThreshold, ctx.ContractId, ctx.ActionType, ctx.TenantId);

            activity?.SetTag("c049.verdict",        "Escalate");
            activity?.SetTag("c049.escalate_reason", "confidence_below_threshold");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-049 honest limitation: confidence score {confidenceScore:F4} is below " +
                $"configured threshold {configuredThreshold:F4} — escalating to human principal"));
        }

        // ── Parse prior_approval_count and min_history_required ────────────────────────
        // Default prior_approval_count to 0 (no history = no evidence of safe pattern).
        // Default min_history_required to 1 (at least one prior explicit approval required).
        var priorApprovalCountRaw  = ctx.GetParameter(ParamPriorApprovalCount);
        var minHistoryRequiredRaw  = ctx.GetParameter(ParamMinHistoryRequired);

        // DESIGN_QUESTION: should a missing prior_approval_count default to 0 (conservative)
        // or to min_history_required - 1 (fail-secure)? Currently defaults to 0 (conservative).
        var priorApprovalCount = 0;
        if (priorApprovalCountRaw is not null &&
            !int.TryParse(priorApprovalCountRaw, out priorApprovalCount))
        {
            _logger.LogWarning(
                "C-049 Escalate: malformed prior_approval_count '{Value}'. " +
                "ContractId={ContractId} ActionType={ActionType}",
                priorApprovalCountRaw, ctx.ContractId, ctx.ActionType);

            activity?.SetTag("c049.verdict",        "Escalate");
            activity?.SetTag("c049.escalate_reason", "malformed_prior_approval_count");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-049 honest limitation: malformed prior_approval_count '{priorApprovalCountRaw}' — " +
                "cannot assess approval history; escalating to human principal"));
        }

        // Default min_history_required to 1 (safe default — at least one prior approval needed).
        var minHistoryRequired = 1;
        if (minHistoryRequiredRaw is not null &&
            !int.TryParse(minHistoryRequiredRaw, out minHistoryRequired))
        {
            _logger.LogWarning(
                "C-049 Escalate: malformed min_history_required '{Value}'. " +
                "ContractId={ContractId} ActionType={ActionType}",
                minHistoryRequiredRaw, ctx.ContractId, ctx.ActionType);

            activity?.SetTag("c049.verdict",        "Escalate");
            activity?.SetTag("c049.escalate_reason", "malformed_min_history_required");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-049 honest limitation: malformed min_history_required '{minHistoryRequiredRaw}' — " +
                "cannot assess history threshold; escalating to human principal"));
        }

        activity?.SetTag("c049.prior_approval_count", priorApprovalCount);
        activity?.SetTag("c049.min_history_required",  minHistoryRequired);

        // ── History sufficiency check ───────────────────────────────────────────────────
        // C-073: constitutional obligation — synthetic approval is only safe when the
        // pattern has been validated by sufficient prior explicit human approvals.
        if (priorApprovalCount < minHistoryRequired)
        {
            _logger.LogWarning(
                "C-049 Escalate: insufficient approval history {PriorCount} < {MinRequired}. " +
                "ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
                priorApprovalCount, minHistoryRequired,
                ctx.ContractId, ctx.ActionType, ctx.TenantId);

            activity?.SetTag("c049.verdict",        "Escalate");
            activity?.SetTag("c049.escalate_reason", "insufficient_approval_history");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-049 honest limitation: prior approval count {priorApprovalCount} is below " +
                $"minimum history required {minHistoryRequired} — " +
                "insufficient evidence base for autonomous action; escalating to human principal"));
        }

        // ── All checks passed ───────────────────────────────────────────────────────────
        _logger.LogInformation(
            "C-049 Allow: confidence {ConfidenceScore:F4} >= {Threshold:F4}, " +
            "history {PriorCount} >= {MinRequired}. " +
            "ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
            confidenceScore, configuredThreshold,
            priorApprovalCount, minHistoryRequired,
            ctx.ContractId, ctx.ActionType, ctx.TenantId);

        activity?.SetTag("c049.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-049 satisfied: confidence {confidenceScore:F4} >= {configuredThreshold:F4}, " +
            $"history {priorApprovalCount} >= {minHistoryRequired}"));
    }
}