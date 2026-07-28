// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator — Budget Ceiling
// Constitutional basis: C-043 (Budget Ceiling), C-059 (Traceability)

using Waooaw.ConstitutionalEngine.Evaluators;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043: proposed spend must not cause total expenditure to breach the
/// contract's approved monthly budget ceiling.  Near-ceiling spend (≥90 %) is
/// escalated so a human can review before the budget is exhausted.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // Escalate when (currentSpend + proposedSpend) / approvedBudget ≥ 9/10
    private const long EscalateNumerator   = 9;
    private const long EscalateDenominator = 10;

    public string ClaimId => "C-043";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // ApprovedBudgetInrPaise, CurrentSpendInrPaise, ProposedSpendInrPaise are non-nullable long —
        // no null-coalescing required (see BEHAVIORAL RULES).
        long total    = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        long approved = ctx.ApprovedBudgetInrPaise;

        // ── DENY: total spend exceeds approved ceiling ──────────────────────────────
        if (total > approved)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-043: total spend ({total} paise) exceeds approved budget ceiling " +
                        $"({approved} paise). ContractId={ctx.ContractId}, " +
                        $"BudgetSkillType={ctx.BudgetSkillType}."));
        }

        // ── ESCALATE: spend is at or above 90 % of approved budget ─────────────────
        // Guard: skip the ratio check when approved == 0 and total == 0 to prevent a
        // spurious Escalate (0 ≥ 0 would otherwise always be true).
        if (approved > 0)
        {
            // Use integer arithmetic to avoid floating-point imprecision.
            // total/approved ≥ 9/10  ↔  total*10 ≥ approved*9
            bool nearCeiling = total * EscalateDenominator >= approved * EscalateNumerator;
            if (nearCeiling)
            {
                long pct = approved == 0 ? 100L : total * 100L / approved;
                return Task.FromResult(new EvaluationResult(
                    ClaimId: ClaimId,
                    Verdict: EvaluationVerdict.Escalate,
                    Reason: $"C-043: total spend ({total} paise) is at {pct}% of approved budget " +
                            $"({approved} paise) — human approval required. " +
                            $"ContractId={ctx.ContractId}, BudgetSkillType={ctx.BudgetSkillType}."));
            }
        }

        // ── ALLOW ───────────────────────────────────────────────────────────────────
        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: $"C-043: total spend ({total} paise) is within approved budget " +
                    $"({approved} paise). ContractId={ctx.ContractId}, " +
                    $"BudgetSkillType={ctx.BudgetSkillType}."));
    }
}