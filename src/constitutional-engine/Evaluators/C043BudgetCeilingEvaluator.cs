// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator — Budget Ceiling
// Constitutional basis: C-043 (Budget Ceiling), C-059 (Traceability), C-051 (Resource Transparency)
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 (Budget Ceiling): denies any proposed action whose spend would
/// push the tenant's cumulative monthly expenditure beyond the approved budget ceiling.
/// Operates entirely on pre-loaded EvaluationContext fields — no network I/O.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    public string ClaimId => "C-043";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // Constitutional rule: current + proposed must not exceed approved ceiling.
        // ApprovedBudgetInrPaise / CurrentSpendInrPaise / ProposedSpendInrPaise are
        // non-nullable longs — no null-coalescing required or permitted.
        bool exceeded =
            (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            return Deny(
                $"C-043 budget ceiling exceeded for skill type '{ctx.BudgetSkillType}': " +
                $"current spend {ctx.CurrentSpendInrPaise} paise + " +
                $"proposed spend {ctx.ProposedSpendInrPaise} paise = " +
                $"{ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise} paise " +
                $"exceeds approved ceiling of {ctx.ApprovedBudgetInrPaise} paise " +
                $"(contract: {ctx.ContractId}, tenant: {ctx.TenantId}).");
        }

        return Allow(
            $"C-043 budget within ceiling for skill type '{ctx.BudgetSkillType}': " +
            $"{ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise} paise " +
            $"of {ctx.ApprovedBudgetInrPaise} paise approved " +
            $"(contract: {ctx.ContractId}, tenant: {ctx.TenantId}).");
    }

    private Task<EvaluationResult> Allow(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, reason));

    private Task<EvaluationResult> Deny(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));
}