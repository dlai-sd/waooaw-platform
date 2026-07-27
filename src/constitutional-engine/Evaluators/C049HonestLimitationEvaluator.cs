// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049
// constitutional_basis: C-049 (Honest Limitation), C-059 (Traceability), C-073 (Annotated Obligations)

#nullable enable

using System.Diagnostics;
using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-049 (Honest Limitation): the agent must declare uncertainty when its
/// confidence falls below the tenant-configured threshold, and must escalate to a
/// human when it has insufficient historical approval context for the proposed action.
/// </summary>
/// <remarks>
/// Applies to ALL action types — honest limitation is a universal constraint on
/// autonomous agent behaviour. No ApplicableActionTypes filtering is performed
/// because IClaimEvaluator does not expose that member (per TYPE CONTRACT).
/// </remarks>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // ── C-059: ClaimId enables traceability in every audit record ────────────
    public string ClaimId => "C-049";

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    // Parameter keys extracted from the JSON-encoded ActionParameters string
    private const string ParamConfidenceScore     = "confidence_score";
    private const string ParamConfiguredThreshold = "configured_threshold";
    private const string ParamPriorApprovalCount  = "prior_approval_count";
    private const string ParamMinHistoryRequired  = "min_history_required";

    // Conservative fallback threshold when tenant has not configured one
    private const float DefaultConfidenceThreshold = 0.85f;

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: This method is the C-049 runtime enforcement point.
    // Decision tree:
    //   1. confidence_score absent or unparseable         → ESCALATE (cannot assess confidence)
    //   2. confidence_score < configured_threshold        → DENY    (agent must admit limitation)
    //   3. prior_approval_count < min_history_required    → ESCALATE (insufficient precedent)
    //   4. all checks pass                               → ALLOW
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: C-049 enforcement — honest limitation gate
        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("tenant_id",    ctx.TenantId);
        activity?.SetTag("action_type",  ctx.ActionType);
        activity?.SetTag("contract_id",  ctx.ContractId);
        activity?.SetTag("claim_id",     ClaimId);

        // ── Step 1: Parse confidence_score ────────────────────────────────────
        var confidenceRaw = ctx.GetParameter(ParamConfidenceScore);

        if (confidenceRaw is null ||
            !float.TryParse(
                confidenceRaw,
                NumberStyles.Float,
                CultureInfo.InvariantCulture,
                out var confidenceScore))
        {
            _logger.LogWarning(
                "C049: Parameter '{Param}' is absent or unparseable for tenant={TenantId} action={ActionType}; escalating — cannot assess agent confidence",
                ParamConfidenceScore, ctx.TenantId, ctx.ActionType);

            activity?.SetTag("verdict", "Escalate");
            activity?.SetTag("deny_reason", "missing_confidence_score");

            // Cannot determine confidence → must escalate to human (C-049 path)
            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Escalate,
                Reason:  $"C-049: Parameter '{ParamConfidenceScore}' is absent or not a valid float — " +
                         "agent confidence cannot be assessed; escalating to human review per C-049."));
        }

        // ── Step 2: Parse configured_threshold (with conservative default) ────
        var thresholdRaw = ctx.GetParameter(ParamConfiguredThreshold);

        float configuredThreshold;
        if (thresholdRaw is null ||
            !float.TryParse(
                thresholdRaw,
                NumberStyles.Float,
                CultureInfo.InvariantCulture,
                out configuredThreshold))
        {
            _logger.LogWarning(
                "C049: Parameter '{Param}' is absent or unparseable for tenant={TenantId}; defaulting to {Default}",
                ParamConfiguredThreshold, ctx.TenantId, DefaultConfidenceThreshold);

            configuredThreshold = DefaultConfidenceThreshold;
        }

        activity?.SetTag("confidence_score",     confidenceScore);
        activity?.SetTag("configured_threshold", configuredThreshold);

        // ── Step 3: Deny if confidence below threshold ────────────────────────
        if (confidenceScore < configuredThreshold)
        {
            _logger.LogInformation(
                "C049: DENY — confidence_score={ConfidenceScore:F4} < threshold={Threshold:F4} " +
                "for tenant={TenantId} action={ActionType}",
                confidenceScore, configuredThreshold, ctx.TenantId, ctx.ActionType);

            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("deny_reason", "confidence_below_threshold");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason:  $"C-049: Agent confidence {confidenceScore:F4} is below the required " +
                         $"threshold {configuredThreshold:F4}. The agent must declare its limitation " +
                         "and must not proceed autonomously (C-049 Honest Limitation)."));
        }

        // ── Step 4: Parse prior_approval_count ────────────────────────────────
        var priorCountRaw = ctx.GetParameter(ParamPriorApprovalCount);

        int priorApprovalCount;
        if (priorCountRaw is null || !int.TryParse(priorCountRaw, out priorApprovalCount))
        {
            _logger.LogWarning(
                "C049: Parameter '{Param}' is absent or unparseable for tenant={TenantId}; defaulting to 0",
                ParamPriorApprovalCount, ctx.TenantId);

            priorApprovalCount = 0;
        }

        // ── Step 5: Parse min_history_required ────────────────────────────────
        var minHistoryRaw = ctx.GetParameter(ParamMinHistoryRequired);

        int minHistoryRequired;
        if (minHistoryRaw is null || !int.TryParse(minHistoryRaw, out minHistoryRequired))
        {
            _logger.LogWarning(
                "C049: Parameter '{Param}' is absent or unparseable for tenant={TenantId}; defaulting to 0",
                ParamMinHistoryRequired, ctx.TenantId);

            minHistoryRequired = 0;
        }

        activity?.SetTag("prior_approval_count",  priorApprovalCount);
        activity?.SetTag("min_history_required",  minHistoryRequired);

        // ── Step 6: Escalate if insufficient precedent ────────────────────────
        if (priorApprovalCount < minHistoryRequired)
        {
            _logger.LogInformation(
                "C049: ESCALATE — prior_approval_count={PriorCount} < min_history_required={MinHistory} " +
                "for tenant={TenantId} action={ActionType}; insufficient precedent for autonomous approval",
                priorApprovalCount, minHistoryRequired, ctx.TenantId, ctx.ActionType);

            activity?.SetTag("verdict", "Escalate");
            activity?.SetTag("deny_reason", "insufficient_approval_history");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Escalate,
                Reason:  $"C-049: Insufficient approval history — {priorApprovalCount} prior " +
                         $"approval(s) recorded, {minHistoryRequired} required. Escalating to " +
                         "human oversight to establish precedent."));
        }

        // ── Step 7: All checks passed ─────────────────────────────────────────
        _logger.LogInformation(
            "C049: ALLOW — confidence_score={ConfidenceScore:F4} >= threshold={Threshold:F4}, " +
            "prior_approvals={PriorCount} >= min_history={MinHistory} for tenant={TenantId} action={ActionType}",
            confidenceScore, configuredThreshold, priorApprovalCount, minHistoryRequired,
            ctx.TenantId, ctx.ActionType);

        activity?.SetTag("verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason:  null));
    }
}