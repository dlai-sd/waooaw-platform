// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043
// constitutional_basis: C-043 (Budget Ceiling), C-059 (Traceability), C-073 (Annotated Obligations)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 (Budget Ceiling): denies any action whose proposed spend,
/// combined with current-month spend, would exceed the tenant's approved
/// monthly budget ceiling. All figures are expressed in INR paise (integer).
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: identifies the constitutional claim this evaluator enforces
    /// <inheritdoc />
    public string ClaimId => "C-043";

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");
    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: constitutional obligation — enforces C-043 Budget Ceiling at ValidateAction time
    /// <inheritdoc />
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C043BudgetCeiling.Evaluate", ActivityKind.Internal);
        activity?.SetTag("tenant.id",                        ctx.TenantId);
        activity?.SetTag("contract.id",                      ctx.ContractId);
        activity?.SetTag("budget.skill_type",                ctx.BudgetSkillType);
        activity?.SetTag("budget.approved_inr_paise",        ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("budget.current_spend_inr_paise",   ctx.CurrentSpendInrPaise);
        activity?.SetTag("budget.proposed_spend_inr_paise",  ctx.ProposedSpendInrPaise);

        // C-043: Compute remaining budget and evaluate ceiling.
        // ApprovedBudgetInrPaise / CurrentSpendInrPaise / ProposedSpendInrPaise are
        // non-nullable long — no null-coalescing required per stack rules.
        long remainingInrPaise = ctx.ApprovedBudgetInrPaise - ctx.CurrentSpendInrPaise;
        bool ceilingExceeded   = (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise)
                                 > ctx.ApprovedBudgetInrPaise;

        activity?.SetTag("budget.remaining_inr_paise",  remainingInrPaise);
        activity?.SetTag("budget.ceiling_exceeded",      ceilingExceeded);

        if (ceilingExceeded)
        {
            _logger.LogWarning(
                "C-043 DENY: tenantId={TenantId} contractId={ContractId} skillType={SkillType} " +
                "proposedSpendInrPaise={ProposedSpend} remainingInrPaise={Remaining} " +
                "approvedBudgetInrPaise={Approved} currentSpendInrPaise={Current}",
                ctx.TenantId,
                ctx.ContractId,
                ctx.BudgetSkillType,
                ctx.ProposedSpendInrPaise,
                remainingInrPaise,
                ctx.ApprovedBudgetInrPaise,
                ctx.CurrentSpendInrPaise);

            activity?.SetStatus(ActivityStatusCode.Error, "Budget ceiling exceeded");

            return Task.FromResult(new EvaluationResult(
                ClaimId : "C-043",
                Verdict : EvaluationVerdict.Deny,
                Reason  : $"C-043 Budget Ceiling violated: proposed spend of " +
                          $"{ctx.ProposedSpendInrPaise} paise would exceed the remaining " +
                          $"budget of {remainingInrPaise} paise " +
                          $"(approved: {ctx.ApprovedBudgetInrPaise} paise, " +
                          $"current: {ctx.CurrentSpendInrPaise} paise, " +
                          $"skill-type: {ctx.BudgetSkillType})."));
        }

        _logger.LogInformation(
            "C-043 ALLOW: tenantId={TenantId} contractId={ContractId} skillType={SkillType} " +
            "proposedSpendInrPaise={ProposedSpend} remainingInrPaise={Remaining}",
            ctx.TenantId,
            ctx.ContractId,
            ctx.BudgetSkillType,
            ctx.ProposedSpendInrPaise,
            remainingInrPaise);

        return Task.FromResult(new EvaluationResult(
            ClaimId : "C-043",
            Verdict : EvaluationVerdict.Allow,
            Reason  : $"Budget within ceiling: {ctx.ProposedSpendInrPaise} paise proposed, " +
                      $"{remainingInrPaise} paise remaining."));
    }
}