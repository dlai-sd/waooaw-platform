// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator — Budget Ceiling
// Constitutional basis: C-043 (Budget Ceiling), C-051 (Resource Transparency), C-059 (Traceability)

using Waooaw.ConstitutionalEngine.Evaluators;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 (Budget Ceiling): denies or escalates any action whose combined
/// current + proposed spend meets or exceeds the contract's approved monthly budget.
/// Escalates when spend reaches the 90 % warning threshold.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // Escalation fires when totalSpend / approvedBudget >= EscalateNumerator / EscalateDenominator (0.90)
    private const long EscalateNumerator   = 9;
    private const long EscalateDenominator = 10;

    public string ClaimId => "C-043";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        long total    = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        long approved = ctx.ApprovedBudgetInrPaise;

        // Hard ceiling: total spend exceeds approved budget → DENY
        if (total > approved)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-043: Budget ceiling breached. " +
                $"Total spend {total} paise exceeds approved budget {approved} paise " +
                $"(skill: {ctx.BudgetSkillType})."));
        }

        // Soft ceiling (≥ 90 %): escalate for human review — guard against zero-budget division
        if (approved > 0 && total * EscalateDenominator >= approved * EscalateNumerator)
        {
            long pct = total * 100 / approved;
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-043: Budget utilisation at {pct}% of approved ceiling ({total}/{approved} paise). " +
                $"Escalating for human approval (skill: {ctx.BudgetSkillType})."));
        }

        // Within budget — permit
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-043: Budget within ceiling. " +
            $"Total spend {total} paise of {approved} paise approved " +
            $"(skill: {ctx.BudgetSkillType})."));
    }
}