// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator — Budget Ceiling
// Constitutional basis: C-043 (Budget Ceiling), C-051 (Resource Transparency), C-059 (Traceability)

using Waooaw.ConstitutionalEngine.Evaluators;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 (Budget Ceiling): denies any proposed action that would cause total spend
/// (current + proposed) to exceed the approved monthly budget in INR paise.
/// Escalates when total spend would exceed 90% of the approved ceiling.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    private const long EscalateNumerator   = 9;
    private const long EscalateDenominator = 10;

    public string ClaimId => "C-043";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        var approved  = ctx.ApprovedBudgetInrPaise;
        var current   = ctx.CurrentSpendInrPaise;
        var proposed  = ctx.ProposedSpendInrPaise;

        var totalAfter = current + proposed;

        // Hard ceiling: total spend would exceed the approved budget — DENY
        if (totalAfter > approved)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId:  "C-043",
                Verdict:  EvaluationVerdict.Deny,
                Reason:   $"C-043: Budget ceiling exceeded. " +
                          $"Approved={approved} paise, " +
                          $"Current={current} paise, " +
                          $"Proposed={proposed} paise, " +
                          $"Total={totalAfter} paise."
            ));
        }

        // Escalation band: total spend would exceed 90% of the approved budget — ESCALATE
        // Compute threshold using integer arithmetic to avoid floating-point imprecision.
        // threshold = (approved * 9) / 10  (integer division — safe because approved is non-negative long)
        var escalateThreshold = approved * EscalateNumerator / EscalateDenominator;

        if (totalAfter > escalateThreshold)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId:  "C-043",
                Verdict:  EvaluationVerdict.Escalate,
                Reason:   $"C-043: Spend within budget but exceeds 90% escalation threshold. " +
                          $"Approved={approved} paise, " +
                          $"Threshold={escalateThreshold} paise, " +
                          $"Total={totalAfter} paise."
            ));
        }

        // Within safe spend envelope — ALLOW
        return Task.FromResult(new EvaluationResult(
            ClaimId:  "C-043",
            Verdict:  EvaluationVerdict.Allow,
            Reason:   $"C-043: Spend within approved budget. " +
                      $"Approved={approved} paise, " +
                      $"Total={totalAfter} paise."
        ));
    }
}