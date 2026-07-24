// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency)

#nullable enable

using Microsoft.Extensions.Logging;
using System.Diagnostics;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-043 — no single action may exceed the per-action cost ceiling.
/// Applies to ALL action types (resource consumption is universal).
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // DESIGN_QUESTION: Budget ceiling should be tenant-configurable (IOptions<BudgetOptions>)
    // once employment contracts table is available (WC012-03). Hardcoded conservative default.
    internal const double DefaultPerActionCeilingUsd = 10.00;

    // Parameter key that callers may use to declare a custom ceiling for this action
    internal const string CeilingOverrideParameterKey = "budget_ceiling_usd";

    public string ClaimId => "C-043";

    // Empty = applies to ALL action types
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>
    /// C-073: Deny any action whose estimated_cost_usd exceeds the per-action ceiling.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C043BudgetCeilingEvaluator.Evaluate");
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("estimated_cost_usd", ctx.EstimatedCostUsd);
        activity?.SetTag("claim_id", ClaimId);

        var ceiling = DefaultPerActionCeilingUsd;

        if (ctx.Parameters.TryGetValue(CeilingOverrideParameterKey, out var overrideStr)
            && double.TryParse(overrideStr, out var overrideVal)
            && overrideVal > 0)
        {
            // Only reduce, never increase, the ceiling via caller parameters (defensive)
            ceiling = Math.Min(ceiling, overrideVal);
        }

        if (ctx.EstimatedCostUsd < 0)
        {
            activity?.SetTag("decision", "DENY");
            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: "C-043: estimated_cost_usd must be non-negative.",
                EvidenceHint: $"estimated_cost_usd={ctx.EstimatedCostUsd}"));
        }

        if (ctx.EstimatedCostUsd > ceiling)
        {
            _logger.LogWarning(
                "C-043 DENY: cost={Cost:F4} exceeds ceiling={Ceiling:F4} tenant={TenantId} agent={AgentId}",
                ctx.EstimatedCostUsd, ceiling, ctx.TenantId, ctx.AgentId);

            activity?.SetTag("decision", "DENY");
            activity?.SetTag("ceiling_usd", ceiling);

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"C-043: estimated cost ${ctx.EstimatedCostUsd:F4} exceeds per-action ceiling ${ceiling:F4}.",
                EvidenceHint: $"estimated_cost_usd={ctx.EstimatedCostUsd} ceiling={ceiling}"));
        }

        _logger.LogInformation(
            "C-043 AUTHORIZED: cost={Cost:F4} within ceiling={Ceiling:F4} tenant={TenantId}",
            ctx.EstimatedCostUsd, ceiling, ctx.TenantId);

        activity?.SetTag("decision", "AUTHORIZED");
        return Task.FromResult(new EvaluationResult(EvaluationDecision.Authorized));
    }
}