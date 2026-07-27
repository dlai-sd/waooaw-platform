// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator — Budget Ceiling
// constitutional_basis: C-043 (Budget Ceiling), C-059 (Traceability)

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043: an action whose total spend (current + proposed) exceeds the
/// approved monthly budget ceiling must be denied.  Actions approaching the ceiling
/// (≥ 90 %) are escalated for human review rather than silently approved.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // Multiply threshold: avoid floating-point by using integer arithmetic.
    // Escalate when: total * 10 >= budget * 9  (i.e. total >= 90 % of budget)
    private const long EscalateNumerator   = 9;
    private const long EscalateDenominator = 10;

    public string ClaimId => "C-043";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        long total    = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        long budget   = ctx.ApprovedBudgetInrPaise;

        // ── Hard ceiling: total spend strictly exceeds approved budget → DENY ──────────
        if (total > budget)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-043 budget ceiling exceeded: total spend {total} paise " +
                $"(current {ctx.CurrentSpendInrPaise} + proposed {ctx.ProposedSpendInrPaise}) " +
                $"exceeds approved budget {budget} paise " +
                $"[skill_type={ctx.BudgetSkillType}, tenant={ctx.TenantId}]."));
        }

        // ── Near ceiling: total ≥ 90 % of budget → ESCALATE ─────────────────────────
        // Guard budget > 0 to avoid the degenerate zero-budget / zero-spend case where
        // the ratio is undefined and the spend is genuinely neutral (should Allow).
        if (budget > 0 && total * EscalateDenominator >= budget * EscalateNumerator)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-043 budget near ceiling: total spend {total} paise is ≥90 % of " +
                $"approved budget {budget} paise — escalating for human review " +
                $"[skill_type={ctx.BudgetSkillType}, tenant={ctx.TenantId}]."));
        }

        // ── Within budget ─────────────────────────────────────────────────────────────
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-043 budget within ceiling: total spend {total} paise of " +
            $"approved budget {budget} paise " +
            $"[skill_type={ctx.BudgetSkillType}, tenant={ctx.TenantId}]."));
    }
}