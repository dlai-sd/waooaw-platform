// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 (Honest Limitation)
// constitutional_basis: C-049 (Honest Limitation), C-059 (Traceability), C-073 (Annotated Obligations)

#nullable enable

using System.Diagnostics;
using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 Honest Limitation Evaluator.
///
/// When an action exceeds the agent's declared capability boundary, when explicit
/// uncertainty is signalled, or when the caller-supplied confidence score falls below
/// the minimum threshold, this evaluator returns <see cref="EvaluationVerdict.Escalate"/>
/// — forwarding the decision to a human principal via the C-049 escalation path rather
/// than issuing a binary Allow/Deny.
///
/// Applies to ALL action types (empty <see cref="ApplicableActionTypes"/>), because
/// honest limitation is a universal obligation of every agent action.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // ── Parameter names in the JSON-encoded ActionParameters string ─────────────
    // C-073: These constants name the JSON keys that carry C-049 signals.
    private const string ParamConfidenceScore            = "confidence_score";
    private const string ParamCapabilityBoundaryExceeded = "capability_boundary_exceeded";
    private const string ParamUncertaintyDeclared        = "uncertainty_declared";

    /// <summary>
    /// Minimum acceptable confidence score.
    /// Actions with a declared confidence below this value are escalated to a human
    /// principal in accordance with C-049 (fail-safe over silent authorisation).
    /// </summary>
    private const float MinConfidenceThreshold = 0.60f;

    private static readonly ActivitySource _tracer =
        new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    // ── IClaimEvaluator ─────────────────────────────────────────────────────────

    /// <inheritdoc />
    public string ClaimId => "C-049";

    /// <summary>
    /// Empty set — C-049 applies to ALL action types.
    /// Per the evaluator design: empty = applies to every action that reaches CE.
    /// </summary>
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    // ── Constructor ─────────────────────────────────────────────────────────────

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // ── Evaluation ──────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Enforces C-049 Honest Limitation.
    ///
    /// Evaluation order (short-circuits on first Escalate signal):
    ///   1. <c>capability_boundary_exceeded == true</c>  → Escalate
    ///   2. <c>uncertainty_declared == true</c>          → Escalate
    ///   3. <c>confidence_score &lt; 0.60</c>            → Escalate
    ///   4. <c>confidence_score</c> present but unparseable → Escalate (fail-safe)
    ///   5. All checks pass                              → Allow
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C049HonestLimitationEvaluator.Evaluate", ActivityKind.Internal);
        activity?.SetTag("claim_id",    ClaimId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("tenant_id",   ctx.TenantId);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Check 1: explicit capability-boundary-exceeded flag ─────────────────
        // C-073: If the agent declares it cannot perform the action within its
        //        capability envelope, escalate immediately (C-049).
        var capabilityRaw = ctx.GetParameter(ParamCapabilityBoundaryExceeded);
        if (bool.TryParse(capabilityRaw, out var capabilityBoundaryExceeded)
            && capabilityBoundaryExceeded)
        {
            _logger.LogWarning(
                "C-049: Capability boundary exceeded. ActionType={ActionType} TenantId={TenantId} ContractId={ContractId}",
                ctx.ActionType, ctx.TenantId, ctx.ContractId);

            activity?.SetTag("c049.escalate_reason", "capability_boundary_exceeded");
            return Task.FromResult(Escalate(
                "Action exceeds the agent's declared capability boundary — " +
                "escalating to human principal per C-049."));
        }

        // ── Check 2: explicit uncertainty declaration ───────────────────────────
        // C-073: If the agent explicitly signals it is uncertain, escalate.
        var uncertaintyRaw = ctx.GetParameter(ParamUncertaintyDeclared);
        if (bool.TryParse(uncertaintyRaw, out var uncertaintyDeclared) && uncertaintyDeclared)
        {
            _logger.LogWarning(
                "C-049: Uncertainty declared by agent. ActionType={ActionType} TenantId={TenantId} ContractId={ContractId}",
                ctx.ActionType, ctx.TenantId, ctx.ContractId);

            activity?.SetTag("c049.escalate_reason", "uncertainty_declared");
            return Task.FromResult(Escalate(
                "Agent declared uncertainty about this action — " +
                "escalating to human principal per C-049."));
        }

        // ── Check 3 & 4: confidence score threshold ────────────────────────────
        // C-073: A confidence score below MinConfidenceThreshold is treated as
        //        insufficient certainty — escalate rather than silently allow.
        //        An unparseable score is treated as fail-safe → Escalate.
        var confidenceRaw = ctx.GetParameter(ParamConfidenceScore);
        if (confidenceRaw is not null)
        {
            if (float.TryParse(confidenceRaw,
                    NumberStyles.Float,
                    CultureInfo.InvariantCulture,
                    out var confidenceScore))
            {
                activity?.SetTag("c049.confidence_score",  confidenceScore);
                activity?.SetTag("c049.min_threshold",     MinConfidenceThreshold);

                if (confidenceScore < MinConfidenceThreshold)
                {
                    _logger.LogWarning(
                        "C-049: Confidence score {ConfidenceScore:F3} below threshold {Threshold:F3}. " +
                        "ActionType={ActionType} TenantId={TenantId} ContractId={ContractId}",
                        confidenceScore, MinConfidenceThreshold,
                        ctx.ActionType, ctx.TenantId, ctx.ContractId);

                    activity?.SetTag("c049.escalate_reason", "confidence_below_threshold");
                    return Task.FromResult(Escalate(
                        $"Confidence score {confidenceScore:F3} is below the minimum threshold " +
                        $"{MinConfidenceThreshold:F3} — escalating to human principal per C-049."));
                }

                _logger.LogInformation(
                    "C-049: Confidence score {ConfidenceScore:F3} meets threshold {Threshold:F3}. " +
                    "ActionType={ActionType} TenantId={TenantId}",
                    confidenceScore, MinConfidenceThreshold, ctx.ActionType, ctx.TenantId);
            }
            else
            {
                // C-073: Unparseable score → fail-safe escalation (honest about inability
                //        to evaluate confidence = itself a form of honest limitation).
                _logger.LogWarning(
                    "C-049: Unparseable confidence_score value '{ConfidenceRaw}'. " +
                    "ActionType={ActionType} TenantId={TenantId} ContractId={ContractId}",
                    confidenceRaw, ctx.ActionType, ctx.TenantId, ctx.ContractId);

                activity?.SetTag("c049.escalate_reason", "confidence_score_unparseable");
                return Task.FromResult(Escalate(
                    $"Could not parse confidence_score value '{confidenceRaw}' — " +
                    "escalating to human principal per C-049 (fail-safe)."));
            }
        }

        // ── All C-049 checks passed ─────────────────────────────────────────────
        activity?.SetTag("c049.verdict", "allow");
        _logger.LogInformation(
            "C-049: Honest limitation checks passed. ActionType={ActionType} TenantId={TenantId} ContractId={ContractId}",
            ctx.ActionType, ctx.TenantId, ctx.ContractId);

        return Task.FromResult(Allow());
    }

    // ── Private result helpers ──────────────────────────────────────────────────

    private EvaluationResult Allow() =>
        new(ClaimId, EvaluationVerdict.Allow,
            "C-049 honest limitation checks passed — confidence and capability within bounds.");

    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);
}