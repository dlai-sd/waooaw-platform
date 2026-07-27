// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator — Budget Ceiling
// Constitutional basis: C-043 (Budget Ceiling), C-051 (Resource Transparency), C-059 (Traceability)
using System.Threading;
using System.Threading.Tasks;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-043 Budget Ceiling Evaluator.
/// Denies any proposed action whose spend would cause total monthly spend to exceed
/// the tenant's approved budget. Enforces the constitutional budget ceiling at runtime.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    public string ClaimId => "C-043";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-043: (CurrentSpend + ProposedSpend) must not exceed ApprovedBudget.
        // All three fields are non-nullable long — no null-coalescing required.
        bool exceeded = (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise)
                        > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            long projectedSpend = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
            string reason =
                $"C-043 Budget Ceiling violated: projected spend {projectedSpend} paise " +
                $"exceeds approved budget {ctx.ApprovedBudgetInrPaise} paise " +
                $"(current={ctx.CurrentSpendInrPaise}, proposed={ctx.ProposedSpendInrPaise}, " +
                $"skill_type={ctx.BudgetSkillType}).";

            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-043",
                Verdict: EvaluationVerdict.Deny,
                Reason: reason
            ));
        }

        return Task.FromResult(new EvaluationResult(
            ClaimId: "C-043",
            Verdict: EvaluationVerdict.Allow,
            Reason: $"Budget within ceiling: projected spend " +
                    $"{ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise} paise " +
                    $"<= approved {ctx.ApprovedBudgetInrPaise} paise."
        ));
    }
}