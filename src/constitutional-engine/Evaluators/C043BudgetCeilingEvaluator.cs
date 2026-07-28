// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator — Budget Ceiling
// constitutional_basis: C-043 (Budget Ceiling), C-059 (Traceability)
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 (Budget Ceiling): denies any action that would meet or exceed the
/// approved monthly budget, and escalates when total spend reaches ≥90 % of the ceiling.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // Escalation fires at 90 % of approved budget (9/10).
    private const long EscalateNumerator   = 9;
    private const long EscalateDenominator = 10;

    public string ClaimId => "C-043";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // All three fields are non-nullable long — no null-coalescing needed (see stack rules).
        long total    = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        long approved = ctx.ApprovedBudgetInrPaise;

        // Hard ceiling: total spend meets or exceeds approved budget → DENY.
        // "Exactly equal" is also denied: the agent has consumed every authorised rupee.
        if (total >= approved)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-043: Budget ceiling reached. Total spend {total} paise >= approved {approved} paise " +
                $"(skill: {ctx.BudgetSkillType}, contract: {ctx.ContractId})."));
        }

        // Escalation window: spend is within 10 % of the ceiling → ESCALATE to human.
        long escalateThreshold = approved * EscalateNumerator / EscalateDenominator;
        if (total >= escalateThreshold)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-043: Spend approaching budget ceiling ({EscalateNumerator * 100 / EscalateDenominator} % threshold). " +
                $"Total spend {total} paise against approved {approved} paise " +
                $"(skill: {ctx.BudgetSkillType}, contract: {ctx.ContractId})."));
        }

        // Spend is safely within the approved ceiling.
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-043: Budget within ceiling. Total spend {total} paise < approved {approved} paise " +
            $"(skill: {ctx.BudgetSkillType}, contract: {ctx.ContractId})."));
    }
}