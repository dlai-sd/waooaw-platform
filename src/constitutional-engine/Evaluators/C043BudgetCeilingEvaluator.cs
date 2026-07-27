// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Budget Ceiling
// Constitutional basis: C-043 (Budget Ceiling), C-059 (Traceability)

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 (Budget Ceiling): denies any proposed action that would cause
/// cumulative spend to exceed the tenant's approved monthly budget.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    public string ClaimId => "C-043";

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        _logger = logger;
    }

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // ApprovedBudgetInrPaise, CurrentSpendInrPaise, and ProposedSpendInrPaise are
        // non-nullable longs — no null-coalescing required (per stack rules).
        bool exceeded =
            (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            long projectedSpend = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;

            _logger.LogWarning(
                "C-043 DENY — tenant={TenantId} skill={SkillId} skillType={BudgetSkillType} " +
                "projected={ProjectedPaise} approved={ApprovedPaise}",
                ctx.TenantId,
                ctx.SkillId ?? "(none)",
                ctx.BudgetSkillType,
                projectedSpend,
                ctx.ApprovedBudgetInrPaise);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"Budget ceiling exceeded: projected spend {projectedSpend} paise would exceed " +
                $"approved budget of {ctx.ApprovedBudgetInrPaise} paise " +
                $"(current={ctx.CurrentSpendInrPaise}, proposed={ctx.ProposedSpendInrPaise}, " +
                $"skillType={ctx.BudgetSkillType})."));
        }

        _logger.LogDebug(
            "C-043 ALLOW — tenant={TenantId} skill={SkillId} " +
            "current={CurrentPaise} proposed={ProposedPaise} approved={ApprovedPaise}",
            ctx.TenantId,
            ctx.SkillId ?? "(none)",
            ctx.CurrentSpendInrPaise,
            ctx.ProposedSpendInrPaise,
            ctx.ApprovedBudgetInrPaise);

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "Proposed spend is within approved budget ceiling."));
    }
}