// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-049, C-059
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)
/// Purpose: Escalates any action whose parameters indicate the agent is operating beyond
///          its honest capability or knowledge boundary. The agent must never silently attempt
///          actions it cannot perform reliably — uncertain actions must be routed to the customer.
/// ADR reference: ADR-001 (gRPC Constitutional Engine)
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-059: Named constants — no magic strings (CODING-STANDARDS §1.4)
    private const string ClaimIdValue                = "C-049";
    private const string BeyondCapabilityKey         = "beyond_capability";
    private const string RequiresExpertJudgmentKey   = "requires_expert_judgment";
    private const string CapabilityVerifiedKey       = "capability_verified";

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    public string ClaimId => ClaimIdValue;

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    /// <summary>
    /// Evaluates whether the proposed action falls within the agent's honest capability boundary.
    /// Returns Escalate when any limitation signal is detected; Allow when none are present.
    /// Never returns Deny — limitation is uncertainty, not prohibition (that is C-041's domain).
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        try
        {
            // C-049: An action explicitly flagged as beyond the agent's capability must be escalated
            // to the customer rather than attempted and failed silently.
            var beyondCapability = ctx.GetParameter(BeyondCapabilityKey);
            if (string.Equals(beyondCapability, "true", StringComparison.OrdinalIgnoreCase))
            {
                _logger.LogWarning(
                    "C-049 HonestLimitation: action {ActionType} on contract {ContractId} " +
                    "carries beyond_capability=true — escalating to human review",
                    ctx.ActionType,
                    ctx.ContractId);

                return Task.FromResult(new EvaluationResult(
                    ClaimIdValue,
                    EvaluationVerdict.Escalate,
                    "C-049: Action is flagged as beyond agent capability boundary — customer review required before proceeding"));
            }

            // C-049: Actions that require expert judgment are at the agent's honest knowledge boundary.
            // Route to the customer rather than emit a potentially incorrect result.
            var requiresExpertJudgment = ctx.GetParameter(RequiresExpertJudgmentKey);
            if (string.Equals(requiresExpertJudgment, "true", StringComparison.OrdinalIgnoreCase))
            {
                _logger.LogWarning(
                    "C-049 HonestLimitation: action {ActionType} on contract {ContractId} " +
                    "requires expert judgment — escalating to human review",
                    ctx.ActionType,
                    ctx.ContractId);

                return Task.FromResult(new EvaluationResult(
                    ClaimIdValue,
                    EvaluationVerdict.Escalate,
                    "C-049: Action requires expert judgment that exceeds the agent's honest capability — customer review required"));
            }

            // C-049: A capability_verified=false signal indicates the calling agent could not confirm
            // it has the prerequisite capability to execute this action reliably.
            var capabilityVerified = ctx.GetParameter(CapabilityVerifiedKey);
            if (string.Equals(capabilityVerified, "false", StringComparison.OrdinalIgnoreCase))
            {
                _logger.LogWarning(
                    "C-049 HonestLimitation: action {ActionType} on contract {ContractId} " +
                    "has capability_verified=false — escalating to human review",
                    ctx.ActionType,
                    ctx.ContractId);

                return Task.FromResult(new EvaluationResult(
                    ClaimIdValue,
                    EvaluationVerdict.Escalate,
                    "C-049: Agent capability for this action could not be verified — customer review required before proceeding"));
            }

            // No honest-limitation signals detected. Allow this evaluator to pass.
            // Other evaluators (C-041, C-043, C-048, C-062) enforce their own constitutional claims.
            _logger.LogDebug(
                "C-049 HonestLimitation: action {ActionType} on contract {ContractId} passed honest-limitation check",
                ctx.ActionType,
                ctx.ContractId);

            return Task.FromResult(new EvaluationResult(
                ClaimIdValue,
                EvaluationVerdict.Allow,
                "C-049: No honest-limitation indicators detected — action is within agent capability boundary"));
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1 (C-059): Never swallow exceptions silently.
            _logger.LogError(
                ex,
                "C-049 HonestLimitation: evaluator failed for action {ActionType} on contract {ContractId}",
                ctx.ActionType,
                ctx.ContractId);

            // C-049 fail-safe: evaluator failure is itself a limitation signal.
            // Escalate rather than silently allow an action through a broken evaluator.
            return Task.FromResult(new EvaluationResult(
                ClaimIdValue,
                EvaluationVerdict.Escalate,
                $"C-049: Evaluator encountered an internal error — escalating for safety. Detail: {ex.Message}"));
        }
    }
}