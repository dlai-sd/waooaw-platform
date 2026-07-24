// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043
// constitutional_basis: C-043 (Budget Ceiling — no spend above contract ceiling)

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-043 — proposed spend must not cause cumulative period spend to exceed
/// the contract budget ceiling. Applies to BUDGET_SPEND and MCP_TOOL_CALL actions that
/// carry a ProposedSpendCents value.
/// </summary>
public sealed class C043_BudgetCeilingEvaluator : IClaimEvaluator
{
    private readonly ILogger<C043_BudgetCeilingEvaluator> _logger;

    // C-073: C-043 applies to BUDGET_SPEND and MCP_TOOL_CALL (tools can have cost)
    private static readonly IReadOnlySet<string> _applicableTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "BUDGET_SPEND",
            "MCP_TOOL_CALL"
        };

    public string ClaimId => "C-043";
    public IReadOnlySet<string> ApplicableActionTypes => _applicableTypes;

    public C043_BudgetCeilingEvaluator(ILogger<C043_BudgetCeilingEvaluator> logger)
    {
        _logger = logger;
    }

    /// <summary>
    /// C-073: Evaluates C-043 Budget Ceiling.
    /// DENY if: proposed spend + current period spend would exceed the contract ceiling.
    /// PASS-THROUGH if: no proposed spend (tool call with no cost metadata).
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-043: If no proposed spend, this evaluator does not apply
        if (ctx.ProposedSpendCents is null or 0)
        {
            _logger.LogDebug(
                "C-043 SKIP: No proposed spend for action {ActionType}, tenant {TenantId}",
                ctx.ActionType, ctx.TenantId);
            return Task.FromResult(new EvaluationResult(EvaluationDecision.Authorized));
        }

        // C-043: If no budget ceiling defined, escalate for human review (C-049 path)
        if (ctx.ContractBudgetCeilingCents is null)
        {
            _logger.LogWarning(
                "C-043 ESCALATE: No budget ceiling defined for tenant {TenantId} — escalating to human review",
                ctx.TenantId);

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Escalate,
                Reason: "No budget ceiling is defined in the employment contract. Escalating to human review (C-043, C-049).",
                EvidenceHint: $"TenantId={ctx.TenantId} ProposedSpendCents={ctx.ProposedSpendCents}"));
        }

        var projectedTotal = ctx.CurrentPeriodSpendCents + ctx.ProposedSpendCents.Value;

        if (projectedTotal > ctx.ContractBudgetCeilingCents.Value)
        {
            _logger.LogWarning(
                "C-043 DENY: Projected spend {ProjectedTotal} exceeds ceiling {Ceiling} for tenant {TenantId}",
                projectedTotal, ctx.ContractBudgetCeilingCents.Value, ctx.TenantId);

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"Proposed spend of {ctx.ProposedSpendCents.Value} cents would bring period total to " +
                        $"{projectedTotal} cents, exceeding the contract ceiling of {ctx.ContractBudgetCeilingCents.Value} cents (C-043).",
                EvidenceHint: $"TenantId={ctx.TenantId} CurrentSpend={ctx.CurrentPeriodSpendCents} " +
                              $"Proposed={ctx.ProposedSpendCents.Value} Ceiling={ctx.ContractBudgetCeilingCents.Value}"));
        }

        _logger.LogDebug(
            "C-043 AUTHORIZED: Projected spend {ProjectedTotal} within ceiling {Ceiling} for tenant {TenantId}",
            projectedTotal, ctx.ContractBudgetCeilingCents.Value, ctx.TenantId);

        return Task.FromResult(new EvaluationResult(EvaluationDecision.Authorized));
    }
}