// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-043 (Budget Ceiling) — denies any proposed action whose cost,
/// when added to current month spend, would exceed the tenant's approved monthly budget.
/// C-051 (Resource Transparency): all budget figures are logged for audit observability.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: Tracer scoped to Constitutional Engine service.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Identifies the constitutional claim this evaluator enforces.
    public string ClaimId => "C-043";

    /// <summary>
    /// C-073: Evaluates C-043 Budget Ceiling.
    /// DENY when (CurrentSpendInrPaise + ProposedSpendInrPaise) &gt; ApprovedBudgetInrPaise.
    /// ALLOW otherwise.
    /// No network I/O — decision is derived exclusively from EvaluationContext fields.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Instrument every evaluation for observability (C-051 Resource Transparency).
        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("tenant.id",                         ctx.TenantId);
        activity?.SetTag("contract.id",                       ctx.ContractId);
        activity?.SetTag("budget.skill_type",                 ctx.BudgetSkillType);
        activity?.SetTag("budget.approved_inr_paise",         ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("budget.current_spend_inr_paise",    ctx.CurrentSpendInrPaise);
        activity?.SetTag("budget.proposed_spend_inr_paise",   ctx.ProposedSpendInrPaise);

        // C-043: Core budget ceiling check.
        // Fields are non-nullable long — no ?? coalescing required or permitted.
        // DESIGN_QUESTION: Should overflow be guarded (checked{}) or is INR paise scale safe within long range?
        long projectedTotalInrPaise = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        bool ceilingExceeded = projectedTotalInrPaise > ctx.ApprovedBudgetInrPaise;

        if (ceilingExceeded)
        {
            // C-051: Log full budget context for resource transparency audit trail.
            _logger.LogWarning(
                "C-043 DENY: TenantId={TenantId} ContractId={ContractId} SkillType={SkillType} " +
                "CurrentSpendPaise={CurrentSpend} ProposedSpendPaise={ProposedSpend} " +
                "ProjectedTotalPaise={ProjectedTotal} ApprovedBudgetPaise={ApprovedBudget}",
                ctx.TenantId,
                ctx.ContractId,
                ctx.BudgetSkillType,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise,
                projectedTotalInrPaise,
                ctx.ApprovedBudgetInrPaise);

            activity?.SetTag("budget.decision",                  "Deny");
            activity?.SetTag("budget.projected_total_inr_paise", projectedTotalInrPaise);

            string reason =
                $"C-043 Budget Ceiling exceeded for skill type '{ctx.BudgetSkillType}': " +
                $"projected spend {projectedTotalInrPaise} paise " +
                $"(current {ctx.CurrentSpendInrPaise} + proposed {ctx.ProposedSpendInrPaise}) " +
                $"exceeds approved ceiling of {ctx.ApprovedBudgetInrPaise} paise.";

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: reason));
        }

        // C-051: Log remaining headroom for resource transparency.
        long remainingPaise = ctx.ApprovedBudgetInrPaise - projectedTotalInrPaise;

        _logger.LogInformation(
            "C-043 ALLOW: TenantId={TenantId} ContractId={ContractId} SkillType={SkillType} " +
            "CurrentSpendPaise={CurrentSpend} ProposedSpendPaise={ProposedSpend} " +
            "ProjectedTotalPaise={ProjectedTotal} ApprovedBudgetPaise={ApprovedBudget} " +
            "HeadroomPaise={Headroom}",
            ctx.TenantId,
            ctx.ContractId,
            ctx.BudgetSkillType,
            ctx.CurrentSpendInrPaise,
            ctx.ProposedSpendInrPaise,
            projectedTotalInrPaise,
            ctx.ApprovedBudgetInrPaise,
            remainingPaise);

        activity?.SetTag("budget.decision",                  "Allow");
        activity?.SetTag("budget.projected_total_inr_paise", projectedTotalInrPaise);
        activity?.SetTag("budget.headroom_inr_paise",         remainingPaise);

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: $"Budget ceiling not exceeded: projected {projectedTotalInrPaise} paise " +
                    $"within approved {ctx.ApprovedBudgetInrPaise} paise " +
                    $"({remainingPaise} paise remaining)."));
    }
}