// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Annotation), C-023 (Evidence First)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces constitutional claim C-043: no action may cause the tenant's cumulative spend
/// to exceed the approved monthly budget ceiling.
/// Implements the "Resource Transparency" obligation (C-051) by including projected spend
/// figures in every denial reason, enabling evidence-first audit trails.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource scoped to the Constitutional Engine service.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        // C-073: Constructor validates dependencies per constitutional DI obligation.
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId is the canonical identifier of the enforced constitutional claim.
    public string ClaimId => "C-043";

    /// <summary>
    /// C-073 — Constitutional obligation: enforce C-043 Budget Ceiling.
    /// Computes projected spend as (CurrentSpendInrPaise + ProposedSpendInrPaise).
    /// DENY if projected spend exceeds ApprovedBudgetInrPaise.
    /// ALLOW otherwise.
    /// Budget fields are non-nullable long — no null-coalescing required.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: Null guard — ctx is required for constitutional evaluation.
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("tenant_id",                  ctx.TenantId);
        activity?.SetTag("action_type",                ctx.ActionType);
        activity?.SetTag("contract_id",                ctx.ContractId);
        activity?.SetTag("budget_skill_type",          ctx.BudgetSkillType);
        activity?.SetTag("approved_budget_inr_paise",  ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("current_spend_inr_paise",    ctx.CurrentSpendInrPaise);
        activity?.SetTag("proposed_spend_inr_paise",   ctx.ProposedSpendInrPaise);

        // C-043: Projected spend = current period spend + proposed action spend.
        // ⚠ Fields are non-nullable long — do NOT apply ?? operator.
        long projectedSpend = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        bool ceilingExceeded = projectedSpend > ctx.ApprovedBudgetInrPaise;

        if (ceilingExceeded)
        {
            // C-051: Denial reason must be transparent — include all spend figures.
            string reason =
                $"C-043 Budget Ceiling breached: projected spend {projectedSpend} paise " +
                $"exceeds approved ceiling {ctx.ApprovedBudgetInrPaise} paise " +
                $"(current_spend={ctx.CurrentSpendInrPaise} paise, " +
                $"proposed_spend={ctx.ProposedSpendInrPaise} paise, " +
                $"skill_type={ctx.BudgetSkillType}).";

            _logger.LogWarning(
                "C-043 budget ceiling breached for TenantId={TenantId} ContractId={ContractId}. " +
                "ProjectedSpend={ProjectedSpend} Ceiling={Ceiling} " +
                "CurrentSpend={CurrentSpend} ProposedSpend={ProposedSpend} SkillType={SkillType}",
                ctx.TenantId,
                ctx.ContractId,
                projectedSpend,
                ctx.ApprovedBudgetInrPaise,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise,
                ctx.BudgetSkillType);

            activity?.SetTag("verdict",               "Deny");
            activity?.SetTag("projected_spend",       projectedSpend);
            activity?.SetTag("ceiling_exceeded",      true);

            return Task.FromResult(new EvaluationResult(
                ClaimId:  ClaimId,
                Verdict:  EvaluationVerdict.Deny,
                Reason:   reason));
        }

        // C-051: Log allow path with remaining headroom for resource transparency.
        long remainingHeadroom = ctx.ApprovedBudgetInrPaise - projectedSpend;

        _logger.LogDebug(
            "C-043 budget ceiling check passed for TenantId={TenantId} ContractId={ContractId}. " +
            "ProjectedSpend={ProjectedSpend} Ceiling={Ceiling} " +
            "Headroom={Headroom} SkillType={SkillType}",
            ctx.TenantId,
            ctx.ContractId,
            projectedSpend,
            ctx.ApprovedBudgetInrPaise,
            remainingHeadroom,
            ctx.BudgetSkillType);

        activity?.SetTag("verdict",           "Allow");
        activity?.SetTag("projected_spend",   projectedSpend);
        activity?.SetTag("headroom_paise",    remainingHeadroom);
        activity?.SetTag("ceiling_exceeded",  false);

        return Task.FromResult(new EvaluationResult(
            ClaimId:  ClaimId,
            Verdict:  EvaluationVerdict.Allow,
            Reason:   $"Projected spend {projectedSpend} paise is within approved ceiling " +
                      $"{ctx.ApprovedBudgetInrPaise} paise " +
                      $"(headroom={remainingHeadroom} paise, skill_type={ctx.BudgetSkillType})."));
    }
}