// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Annotation), C-023 (Evidence First)

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 Budget Ceiling at runtime: prevents any agent action whose projected total
/// spend (current month spend + proposed spend) would exceed the tenant's approved monthly
/// budget ceiling for the relevant skill type.
/// </summary>
// C-073: This class directly implements constitutional obligation C-043 (Budget Ceiling).
//        Every call to EvaluateAsync is a runtime enforcement point — not advisory.
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-059: Tracer scoped to the Constitutional Engine service boundary.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        // C-073: Guard ensures the evaluator is always observable (structured logging is non-optional).
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId ties every denial record back to the constitutional text of C-043.
    /// <inheritdoc/>
    public string ClaimId => "C-043";

    // C-073: Implements C-043 (Budget Ceiling) — an agent must not execute any action that
    //        would cause cumulative monthly spend to exceed the approved ceiling.
    //        C-051 (Resource Transparency) requires that the reason for denial includes
    //        the exact numeric values so the evidence record is self-explaining.
    /// <inheritdoc/>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("waooaw.claim_id",              ClaimId);
        activity?.SetTag("waooaw.tenant_id",             ctx.TenantId);
        activity?.SetTag("waooaw.contract_id",           ctx.ContractId);
        activity?.SetTag("waooaw.budget.skill_type",     ctx.BudgetSkillType);
        activity?.SetTag("waooaw.budget.approved_paise", ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("waooaw.budget.current_paise",  ctx.CurrentSpendInrPaise);
        activity?.SetTag("waooaw.budget.proposed_paise", ctx.ProposedSpendInrPaise);

        // C-043 enforcement: the ONLY arithmetic that determines the decision.
        // ApprovedBudgetInrPaise, CurrentSpendInrPaise, ProposedSpendInrPaise are non-nullable long —
        // no null-coalescing required or permitted.
        long projectedTotal = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        bool exceeded       = projectedTotal > ctx.ApprovedBudgetInrPaise;

        activity?.SetTag("waooaw.budget.projected_total_paise", projectedTotal);
        activity?.SetTag("waooaw.budget.ceiling_exceeded",      exceeded);

        if (exceeded)
        {
            // C-051: Reason string must contain the exact figures so the evidence record is
            //        self-explaining without requiring a secondary DB lookup.
            string denyReason =
                $"C-043 Budget Ceiling breached: projected spend of {projectedTotal} paise " +
                $"(current={ctx.CurrentSpendInrPaise} + proposed={ctx.ProposedSpendInrPaise}) " +
                $"exceeds approved ceiling of {ctx.ApprovedBudgetInrPaise} paise " +
                $"[skill_type={ctx.BudgetSkillType}, contract={ctx.ContractId}].";

            _logger.LogWarning(
                "C-043 budget ceiling DENY. " +
                "TenantId={TenantId} ContractId={ContractId} " +
                "CurrentSpendPaise={CurrentSpend} ProposedSpendPaise={ProposedSpend} " +
                "ProjectedTotalPaise={ProjectedTotal} ApprovedCeilingPaise={ApprovedCeiling} " +
                "SkillType={SkillType}",
                ctx.TenantId,
                ctx.ContractId,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise,
                projectedTotal,
                ctx.ApprovedBudgetInrPaise,
                ctx.BudgetSkillType);

            return Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, denyReason));
        }

        // C-051 (Resource Transparency): log remaining headroom so operators can observe
        //        budget utilisation trend without querying the database.
        long remainingAfterAction = ctx.ApprovedBudgetInrPaise - projectedTotal;

        _logger.LogDebug(
            "C-043 budget ceiling ALLOW. " +
            "TenantId={TenantId} ContractId={ContractId} " +
            "ProjectedTotalPaise={ProjectedTotal} ApprovedCeilingPaise={ApprovedCeiling} " +
            "RemainingAfterActionPaise={Remaining} SkillType={SkillType}",
            ctx.TenantId,
            ctx.ContractId,
            projectedTotal,
            ctx.ApprovedBudgetInrPaise,
            remainingAfterAction,
            ctx.BudgetSkillType);

        activity?.SetTag("waooaw.budget.remaining_after_action_paise", remainingAfterAction);

        string allowReason =
            $"C-043 Budget Ceiling: within approved ceiling. " +
            $"Projected total {projectedTotal} paise " +
            $"\u2264 {ctx.ApprovedBudgetInrPaise} paise; " +
            $"remaining headroom {remainingAfterAction} paise " +
            $"[skill_type={ctx.BudgetSkillType}, contract={ctx.ContractId}].";

        return Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, allowReason));
    }
}