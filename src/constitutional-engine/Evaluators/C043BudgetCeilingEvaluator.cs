// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator — Budget Ceiling
// constitutional_basis: C-043 (Budget Ceiling), C-059 (Traceability), C-023 (Evidence First)

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043: no action may cause total spend (current + proposed) to meet or exceed
/// the approved budget ceiling. Escalates when spend reaches the 90 % warning threshold.
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

        // Hard ceiling: total spend at or above approved budget → DENY
        if (total >= approved)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason:  $"C-043: Total spend ({total} paise) meets or exceeds approved budget " +
                         $"({approved} paise). Action denied to protect budget ceiling."));
        }

        // Soft ceiling: total spend at or above 90 % of approved budget → ESCALATE
        // Use integer arithmetic: total >= approved * 9 / 10
        // Integer division is intentional — errs on the side of caution for large budgets.
        long escalateThreshold = approved * EscalateNumerator / EscalateDenominator;
        if (total >= escalateThreshold)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Escalate,
                Reason:  $"C-043: Total spend ({total} paise) is at or above 90 % of approved budget " +
                         $"({approved} paise, threshold {escalateThreshold} paise). Human escalation required."));
        }

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason:  $"C-043: Total spend ({total} paise) is within approved budget ({approved} paise)."));
    }
}