// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First)

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 Evaluator — Honest Limitation.
/// Escalates actions where the agent has declared an honest limitation for the action type.
/// Escalation routes to human (Sujay) for review rather than auto-approving uncertain actions.
/// </summary>
/// <remarks>
/// C-073: Enforces C-049 at runtime — agents must not auto-approve actions they are
/// uncertain about. Escalate = soft deny pending human review.
/// Applies to ALL action types — honest limitation is universal.
/// </remarks>
public sealed class C049_HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: Universal — applies to ALL action types
    private static readonly IReadOnlySet<string> _applicableTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    private readonly ILogger<C049_HonestLimitationEvaluator> _logger;

    public C049_HonestLimitationEvaluator(ILogger<C049_HonestLimitationEvaluator> logger)
    {
        _logger = logger;
    }

    /// <inheritdoc/>
    public string ClaimId => "C-049";

    /// <inheritdoc/>
    public IReadOnlySet<string> ApplicableActionTypes => _applicableTypes;

    /// <inheritdoc/>
    /// <remarks>
    /// C-073: C-049 enforcement — escalate when agent has declared honest limitation.
    /// </remarks>
    public async Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        var hasLimitation = await ctx.Data.HasHonestLimitationFlagAsync(
            ctx.AgentId, ctx.ActionType, ct);

        if (hasLimitation)
        {
            _logger.LogInformation(
                "C-049 ESCALATE: Agent has declared honest limitation. agent={AgentId} action={ActionType}",
                ctx.AgentId, ctx.ActionType);

            return new EvaluationResult(
                EvaluationDecision.Escalate,
                Reason: $"C-049: Agent '{ctx.AgentId}' has declared an honest limitation for action type '{ctx.ActionType}'. Escalating to human review.",
                EvidenceHint: $"honest_limitation:agent={ctx.AgentId},action_type={ctx.ActionType}");
        }

        return new EvaluationResult(EvaluationDecision.Authorized);
    }
}