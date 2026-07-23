// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043
// constitutional_basis: C-043 (Budget Ceiling), C-023 (Evidence First), C-051 (Resource Transparency)

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-043 Evaluator — Budget Ceiling.
/// Denies any action whose estimated cost would exceed the tenant's remaining budget
/// or daily ceiling. Applies to all action types that carry a cost.
/// </summary>
/// <remarks>
/// C-073: Enforces C-043 at runtime — checks both period budget and daily ceiling.
/// Zero-cost actions (EstimatedCostUsd == 0) pass through — they are free operations.
/// Unknown budget (remaining == 0 AND daily ceiling == 0) → DENY (default deny on unknown budget).
/// </remarks>
public sealed class C043_BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: Applies to all action types that carry a cost estimate
    private static readonly IReadOnlySet<string> _applicableTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "MCP_TOOL_CALL",
            "LLM_INFERENCE",
            "DATA_READ",
            "DATA_WRITE",
            "EXTERNAL_API_CALL"
        };

    private readonly ILogger<C043_BudgetCeilingEvaluator> _logger;

    public C043_BudgetCeilingEvaluator(ILogger<C043_BudgetCeilingEvaluator> logger)
    {
        _logger = logger;
    }

    /// <inheritdoc/>
    public string ClaimId => "C-043";

    /// <inheritdoc/>
    public IReadOnlySet<string> ApplicableActionTypes => _applicableTypes;

    /// <inheritdoc/>
    /// <remarks>
    /// C-073: C-043 enforcement — period budget check then daily ceiling check.
    /// </remarks>
    public async Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // Zero-cost actions are always permitted from a budget perspective
        if (ctx.EstimatedCostUsd <= 0m)
        {
            return new EvaluationResult(EvaluationDecision.Authorized);
        }

        var remainingBudget = await ctx.Data.GetRemainingBudgetUsdAsync(ctx.TenantId, ct);
        var dailySpend = await ctx.Data.GetDailySpendUsdAsync(ctx.TenantId, ct);
        var dailyCeiling = await ctx.Data.GetDailyBudgetCeilingUsdAsync(ctx.TenantId, ct);

        // C-073: Default deny when no budget record exists
        if (remainingBudget == 0m && dailyCeiling == 0m)
        {
            _logger.LogWarning(
                "C-043 DENY: No budget record found for tenant={TenantId}. Default deny on unknown budget.",
                ctx.TenantId);

            return new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"C-043: No budget configuration found for tenant '{ctx.TenantId}'. Default deny.",
                EvidenceHint: $"no_budget_record:tenant={ctx.TenantId}");
        }

        // C-073: Check period budget ceiling
        if (ctx.EstimatedCostUsd > remainingBudget)
        {
            _logger.LogWarning(
                "C-043 DENY: Estimated cost {Cost:C} exceeds remaining period budget {Remaining:C}. tenant={TenantId}",
                ctx.EstimatedCostUsd, remainingBudget, ctx.TenantId);

            return new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"C-043: Estimated cost ${ctx.EstimatedCostUsd:F4} exceeds remaining period budget ${remainingBudget:F4}.",
                EvidenceHint: $"period_budget_exceeded:cost={ctx.EstimatedCostUsd},remaining={remainingBudget}");
        }

        // C-073: Check daily ceiling
        if (dailyCeiling > 0m && (dailySpend + ctx.EstimatedCostUsd) > dailyCeiling)
        {
            _logger.LogWarning(
                "C-043 DENY: Daily spend {DailySpend:C} + cost {Cost:C} would exceed daily ceiling {Ceiling:C}. tenant={TenantId}",
                dailySpend, ctx.EstimatedCostUsd, dailyCeiling, ctx.TenantId);

            return new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"C-043: Daily spend ${dailySpend:F4} + estimated ${ctx.EstimatedCostUsd:F4} would exceed daily ceiling ${dailyCeiling:F4}.",
                EvidenceHint: $"daily_ceiling_exceeded:daily_spend={dailySpend},cost={ctx.EstimatedCostUsd},ceiling={dailyCeiling}");
        }

        _logger.LogDebug(
            "C-043 AUTHORIZED: cost={Cost:C} remaining={Remaining:C} daily_spend={DailySpend:C} ceiling={Ceiling:C} tenant={TenantId}",
            ctx.EstimatedCostUsd, remainingBudget, dailySpend, dailyCeiling, ctx.TenantId);

        return new EvaluationResult(EvaluationDecision.Authorized);
    }
}