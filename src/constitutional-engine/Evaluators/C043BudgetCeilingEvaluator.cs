// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator — Budget Ceiling
// constitutional_basis: C-043 (Budget Ceiling), C-059 (Traceability)
using System.Threading;
using System.Threading.Tasks;
using Waooaw.ConstitutionalEngine.Evaluators;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 Budget Ceiling: denies or escalates any action that would cause
/// total spend (current + proposed) to exceed or approach the approved monthly budget.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    private const long EscalateNumerator   = 9;
    private const long EscalateDenominator = 10;

    public string ClaimId => "C-043";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        long total    = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        long approved = ctx.ApprovedBudgetInrPaise;

        // Hard ceiling: total spend strictly exceeds approved budget → DENY
        if (total > approved)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-043: Total spend {total} paise exceeds approved budget ceiling of {approved} paise " +
                        $"(current={ctx.CurrentSpendInrPaise}, proposed={ctx.ProposedSpendInrPaise}, " +
                        $"skill={ctx.BudgetSkillType})."));
        }

        // Approaching ceiling: total ≥ 90% of approved budget → ESCALATE
        // Guard: only meaningful when approved > 0; zero-budget with zero-spend is Allow.
        if (approved > 0 && total * EscalateDenominator >= approved * EscalateNumerator)
        {
            long pct = approved > 0 ? (total * 100L / approved) : 0L;
            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Escalate,
                Reason: $"C-043: Total spend {total} paise is {pct}% of approved budget {approved} paise — " +
                        $"at or above 90% escalation threshold " +
                        $"(current={ctx.CurrentSpendInrPaise}, proposed={ctx.ProposedSpendInrPaise}, " +
                        $"skill={ctx.BudgetSkillType}). Human approval required."));
        }

        // Within safe range → ALLOW
        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: $"C-043: Total spend {total} paise is within approved budget ceiling of {approved} paise " +
                    $"(skill={ctx.BudgetSkillType})."));
    }
}