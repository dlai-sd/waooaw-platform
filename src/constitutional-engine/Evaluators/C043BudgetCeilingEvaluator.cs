// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator — Budget Ceiling
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency), C-059 (Traceability)

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-043 Budget Ceiling Evaluator.
/// Denies any proposed action whose cost would cause cumulative monthly spend
/// to exceed the tenant's approved budget ceiling.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    public string ClaimId => "C-043";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // All three fields are non-nullable long — no null-coalescing required.
        bool exceeded =
            (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            long projectedSpend = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;

            var deny = new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-043 Budget ceiling exceeded: projected spend {projectedSpend} paise " +
                        $"(current {ctx.CurrentSpendInrPaise} + proposed {ctx.ProposedSpendInrPaise}) " +
                        $"exceeds approved ceiling {ctx.ApprovedBudgetInrPaise} paise " +
                        $"[skill_type={ctx.BudgetSkillType}, tenant={ctx.TenantId}]."
            );

            return Task.FromResult(deny);
        }

        var allow = new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: $"C-043 Budget ceiling satisfied: projected spend " +
                    $"{ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise} paise " +
                    $"<= approved {ctx.ApprovedBudgetInrPaise} paise."
        );

        return Task.FromResult(allow);
    }
}