// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator — Budget Ceiling
// Constitutional basis: C-043 (Budget Ceiling), C-059 (Traceability)
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 Budget Ceiling: denies any action whose proposed spend would push
/// cumulative tenant spend past the approved monthly budget.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    public string ClaimId => "C-043";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-043 budget check — all three fields are non-nullable long; no null-coalescing needed.
        bool exceeded = (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            long remainingPaise = ctx.ApprovedBudgetInrPaise - ctx.CurrentSpendInrPaise;

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-043: Budget ceiling exceeded for skill type '{ctx.BudgetSkillType}'. " +
                $"Approved: {ctx.ApprovedBudgetInrPaise} paise, " +
                $"Current spend: {ctx.CurrentSpendInrPaise} paise, " +
                $"Proposed spend: {ctx.ProposedSpendInrPaise} paise, " +
                $"Remaining capacity: {remainingPaise} paise."
            ));
        }

        long remainingAllowedPaise = ctx.ApprovedBudgetInrPaise - ctx.CurrentSpendInrPaise - ctx.ProposedSpendInrPaise;

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-043: Budget ceiling satisfied for skill type '{ctx.BudgetSkillType}'. " +
            $"Remaining after proposed spend: {remainingAllowedPaise} paise."
        ));
    }
}