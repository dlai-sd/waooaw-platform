// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-001, C-003, C-023, C-041, C-059
using Grpc.Core;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.Extensions.Logging;
using System.Globalization;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 (Honest Limitation) Evaluator.
/// Enforces the constitutional requirement that agents must not act beyond their
/// known competence boundary. When a caller signals uncertainty — via the
/// "uncertainty_acknowledged" parameter or a "confidence_score" below the
/// constitutional floor — this evaluator returns <see cref="EvaluationVerdict.Escalate"/>
/// so the action is routed to the customer for explicit authorisation.
///
/// Constitutional basis: C-049 (Honest Limitation)
/// ADR reference: ADR-001 (gRPC Constitutional Engine)
/// Spec: architecture/reference/ce-validate-action-evaluators.md
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // ── Constitutional constants (C-049: must be named and source-referenced) ──────────────
    // The minimum confidence a caller may self-report before C-049 mandates escalation.
    // Below this value the agent is constitutionally obliged to declare a limitation.
    private const double MinimumConfidenceThreshold = 0.70; // C-049: honest limitation floor

    // ActionParameters keys used by C-049 logic.
    private const string UncertaintyAcknowledgedKey = "uncertainty_acknowledged"; // C-049
    private const string ConfidenceScoreKey = "confidence_score";                 // C-049

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    /// <summary>Constitutional claim ID this evaluator enforces.</summary>
    public string ClaimId => "C-049";

    /// <summary>
    /// Initialises the evaluator.
    /// Use <c>NullLogger&lt;C049HonestLimitationEvaluator&gt;.Instance</c> in tests.
    /// </summary>
    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    /// <summary>
    /// Evaluates the action against C-049.
    ///
    /// Rules (applied in order):
    ///   1. If <c>uncertainty_acknowledged=true</c> is present → <see cref="EvaluationVerdict.Escalate"/>.
    ///   2. If <c>confidence_score</c> is present but not parseable as a double → Escalate (fail-safe).
    ///   3. If <c>confidence_score</c> is present and below <see cref="MinimumConfidenceThreshold"/> → Escalate.
    ///   4. Otherwise → <see cref="EvaluationVerdict.Allow"/>.
    ///
    /// Must complete within its share of the 40 ms ValidateAction budget (ADR-001).
    /// MUST NOT perform network I/O.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        try
        {
            ct.ThrowIfCancellationRequested();

            // ── Rule 1: Explicit uncertainty declaration ─────────────────────────────────
            // C-049: If the caller explicitly signals it is at its limitation, escalate
            // immediately — the agent must not proceed without customer confirmation.
            var uncertaintyFlag = ctx.GetParameter(UncertaintyAcknowledgedKey);
            if (string.Equals(uncertaintyFlag, "true", StringComparison.OrdinalIgnoreCase))
            {
                _logger.LogInformation(
                    "C-049: uncertainty_acknowledged=true on ContractId={ContractId} " +
                    "ActionType={ActionType} TenantId={TenantId} — escalating to customer",
                    ctx.ContractId, ctx.ActionType, ctx.TenantId);

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    "C-049: Agent declared honest limitation (uncertainty_acknowledged=true) — " +
                    "action escalated for explicit customer authorisation."));
            }

            // ── Rule 2 & 3: Confidence score below constitutional floor ─────────────────
            // C-049: If the caller provides a self-assessed confidence score, the
            // Constitutional Engine enforces the floor.  An unparseable value is treated
            // as zero-confidence (fail-safe escalation rather than silent allow).
            var confidenceRaw = ctx.GetParameter(ConfidenceScoreKey);
            if (confidenceRaw is not null)
            {
                if (!double.TryParse(
                        confidenceRaw,
                        NumberStyles.Float,
                        CultureInfo.InvariantCulture,
                        out double confidenceScore))
                {
                    _logger.LogWarning(
                        "C-049: confidence_score present but not parseable as double " +
                        "(raw={Raw}) on ContractId={ContractId} TenantId={TenantId} — " +
                        "escalating for constitutional safety",
                        confidenceRaw, ctx.ContractId, ctx.TenantId);

                    return Task.FromResult(new EvaluationResult(
                        ClaimId,
                        EvaluationVerdict.Escalate,
                        $"C-049: confidence_score parameter value '{confidenceRaw}' could not be " +
                        "parsed as a numeric score — escalating for constitutional safety."));
                }

                if (confidenceScore < MinimumConfidenceThreshold)
                {
                    _logger.LogInformation(
                        "C-049: confidence_score={Score:F4} below constitutional floor {Threshold:F4} " +
                        "on ContractId={ContractId} ActionType={ActionType} TenantId={TenantId} — escalating",
                        confidenceScore, MinimumConfidenceThreshold, ctx.ContractId, ctx.ActionType, ctx.TenantId);

                    return Task.FromResult(new EvaluationResult(
                        ClaimId,
                        EvaluationVerdict.Escalate,
                        $"C-049: Reported confidence {confidenceScore:F4} is below the constitutional " +
                        $"floor of {MinimumConfidenceThreshold:F4} — action escalated to customer."));
                }

                _logger.LogDebug(
                    "C-049: confidence_score={Score:F4} meets floor {Threshold:F4} " +
                    "on ContractId={ContractId} ActionType={ActionType}",
                    confidenceScore, MinimumConfidenceThreshold, ctx.ContractId, ctx.ActionType);
            }

            // ── Default: no limitation signal detected → allow ───────────────────────────
            _logger.LogDebug(
                "C-049: Allow — no honest limitation signal on ContractId={ContractId} " +
                "ActionType={ActionType} TenantId={TenantId}",
                ctx.ContractId, ctx.ActionType, ctx.TenantId);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                "C-049: No honest limitation signal detected — action proceeds."));
        }
        catch (OperationCanceledException)
        {
            // Propagate cancellation — do not log as an error; caller owns the token.
            throw;
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1: never swallow; log before rethrowing.
            _logger.LogError(
                ex,
                "C-049: EvaluateAsync failed for ContractId={ContractId} ActionType={ActionType}",
                ctx.ContractId, ctx.ActionType);
            throw;
        }
    }
}