// Implements: architecture/reference/ce-validate-action-evaluators.md §C-051
// constitutional_basis: C-051 (Resource Transparency), C-023 (Evidence First)

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-051 Evaluator — Resource Transparency.
/// Denies actions where the estimated cost is not disclosed (missing cost metadata)
/// for cost-bearing action types. Ensures agents cannot hide resource consumption.
/// </summary>
/// <remarks>
/// C-073: Enforces C-051 at runtime — cost-bearing actions must declare their
/// estimated cost. Actions with no cost estimate on cost-bearing types are denied.
/// </remarks>
public sealed class C051_ResourceTransparencyEvaluator : IClaimEvaluator
{
    // C-073: Applies to action types that inherently consume billable resources
    private static readonly IReadOnlySet<string> _applicableTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "LLM_INFERENCE",
            "EXTERNAL_API_CALL"
        };

    private readonly ILogger<C051_ResourceTransparencyEvaluator> _logger;

    public C051_ResourceTransparencyEvaluator(ILogger<C051_ResourceTransparencyEvaluator> logger)
    {
        _logger = logger;
    }

    /// <inheritdoc/>
    public string ClaimId => "C-051";

    /// <inheritdoc/>
    public IReadOnlySet<string> ApplicableActionTypes => _applicableTypes;

    /// <inheritdoc/>
    /// <remarks>
    /// C-073: C-051 enforcement — cost-bearing actions must declare estimated cost.
    /// </remarks>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: LLM_INFERENCE and EXTERNAL_API_CALL must declare a cost estimate
        if (ctx.EstimatedCostUsd <= 0m)
        {
            _logger.LogWarning(
                "C-051 DENY: Cost-bearing action missing cost estimate. action={ActionType} agent={AgentId}",
                ctx.ActionType, ctx.AgentId);

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"C-051: Action type '{ctx.ActionType}' must declare a positive EstimatedCostUsd for resource transparency. Received: {ctx.EstimatedCostUsd}.",
                EvidenceHint: $"missing_cost_estimate:action_type={ctx.ActionType}"));
        }

        _logger.LogDebug(
            "C-051 AUTHORIZED: cost={Cost:C} action={ActionType} agent={AgentId}",
            ctx.EstimatedCostUsd, ctx.ActionType, ctx.AgentId);

        return Task.FromResult(new EvaluationResult(EvaluationDecision.Authorized));
    }
}