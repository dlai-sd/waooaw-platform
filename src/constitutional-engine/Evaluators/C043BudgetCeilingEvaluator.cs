// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator — Budget Ceiling
// Constitutional basis: C-043 (Budget Ceiling)
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 Budget Ceiling: denies any action whose projected cumulative spend
/// (CurrentSpendInrPaise + ProposedSpendInrPaise) would exceed the tenant's
/// ApprovedBudgetInrPaise for the relevant skill type.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    public string ClaimId => "C-043";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-043 core invariant — do NOT use BudgetRemainingInrPaise (does not exist).
        // All three fields are non-nullable long; no ?? guard needed or permitted.
        bool exceeded = (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            long projected = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;

            string reason =
                $"C-043 Budget Ceiling violated: projected spend {projected} paise " +
                $"(current {ctx.CurrentSpendInrPaise} + proposed {ctx.ProposedSpendInrPaise}) " +
                $"exceeds approved budget {ctx.ApprovedBudgetInrPaise} paise " +
                $"for skill type '{ctx.BudgetSkillType}'.";

            return Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));
        }

        long remaining = ctx.ApprovedBudgetInrPaise - (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise);

        return Task.FromResult(
            new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                $"Budget within ceiling: projected {ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise} paise " +
                $"<= approved {ctx.ApprovedBudgetInrPaise} paise; " +
                $"{remaining} paise remaining after this action for skill type '{ctx.BudgetSkillType}'."));
    }
}