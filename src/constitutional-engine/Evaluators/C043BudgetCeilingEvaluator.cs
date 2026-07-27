// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator — Budget Ceiling
// Constitutional basis: C-043 (Budget Ceiling)
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 (Budget Ceiling): denies any action whose projected spend
/// (current + proposed) exceeds the tenant's approved monthly budget.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    public string ClaimId => "C-043";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();

        // All three fields are non-nullable long — no null-coalescing required.
        long projectedSpend = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        bool exceeded = projectedSpend > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-043 budget ceiling exceeded: projected spend {projectedSpend} paise " +
                $"(current {ctx.CurrentSpendInrPaise} + proposed {ctx.ProposedSpendInrPaise}) " +
                $"exceeds approved budget {ctx.ApprovedBudgetInrPaise} paise " +
                $"for skill type '{ctx.BudgetSkillType}'."
            ));
        }

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-043 budget within ceiling: projected spend {projectedSpend} paise " +
            $"<= approved {ctx.ApprovedBudgetInrPaise} paise " +
            $"for skill type '{ctx.BudgetSkillType}'."
        ));
    }
}