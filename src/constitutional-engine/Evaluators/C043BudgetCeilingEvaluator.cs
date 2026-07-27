// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043
// Constitutional basis: C-043 (Budget Ceiling)
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 (Budget Ceiling): denies any proposed action that would cause
/// cumulative spend to exceed the tenant's approved monthly budget.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        _logger = logger;
    }

    public string ClaimId => "C-043";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        long projectedSpend = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        bool exceeded = projectedSpend > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            _logger.LogWarning(
                "C-043 budget ceiling exceeded for tenant={TenantId} contract={ContractId} " +
                "skillType={BudgetSkillType}: approved={ApprovedBudgetInrPaise} " +
                "current={CurrentSpendInrPaise} proposed={ProposedSpendInrPaise} projected={ProjectedSpend}",
                ctx.TenantId,
                ctx.ContractId,
                ctx.BudgetSkillType,
                ctx.ApprovedBudgetInrPaise,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise,
                projectedSpend);

            return Deny(
                $"C-043: proposed spend of {ctx.ProposedSpendInrPaise} paise would bring cumulative spend " +
                $"to {projectedSpend} paise, exceeding approved ceiling of {ctx.ApprovedBudgetInrPaise} paise " +
                $"for skill type '{ctx.BudgetSkillType}'.");
        }

        _logger.LogDebug(
            "C-043 budget ceiling OK for tenant={TenantId}: projected={ProjectedSpend} of {ApprovedBudgetInrPaise}",
            ctx.TenantId,
            projectedSpend,
            ctx.ApprovedBudgetInrPaise);

        return Allow(
            $"C-043: projected spend {projectedSpend} paise is within approved ceiling of " +
            $"{ctx.ApprovedBudgetInrPaise} paise.");
    }

    // ── helpers ──────────────────────────────────────────────────────────────

    private Task<EvaluationResult> Allow(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, reason));

    private Task<EvaluationResult> Deny(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));
}