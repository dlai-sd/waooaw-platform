// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-043 (Budget Ceiling) — denies any action whose proposed spend would
/// cause the tenant's cumulative monthly spend to exceed the approved budget ceiling.
/// C-051: Remaining budget is always logged regardless of verdict (Resource Transparency).
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-059: Canonical tracer for the Constitutional Engine service.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId identifies the constitutional claim this evaluator enforces.
    /// <summary>Constitutional claim enforced: C-043 (Budget Ceiling).</summary>
    public string ClaimId => "C-043";

    // C-073: EvaluateAsync is the primary constitutional obligation implementation for C-043.
    /// <summary>
    /// Evaluates whether the proposed action falls within the tenant's approved budget ceiling.
    /// Returns <see cref="EvaluationVerdict.Deny"/> when
    /// <c>CurrentSpendInrPaise + ProposedSpendInrPaise &gt; ApprovedBudgetInrPaise</c>.
    /// </summary>
    /// <remarks>
    /// All three budget fields on <see cref="EvaluationContext"/> are non-nullable <c>long</c>;
    /// the null-coalescing operator (??) MUST NOT be applied to them.
    /// <c>BudgetRemainingInrPaise</c> does not exist as a property — it is derived here.
    /// </remarks>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Open a tracing span for observability — C-059 traceability requirement.
        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("tenant_id",                  ctx.TenantId);
        activity?.SetTag("contract_id",                ctx.ContractId);
        activity?.SetTag("budget_skill_type",          ctx.BudgetSkillType);
        activity?.SetTag("approved_budget_inr_paise",  ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("current_spend_inr_paise",    ctx.CurrentSpendInrPaise);
        activity?.SetTag("proposed_spend_inr_paise",   ctx.ProposedSpendInrPaise);

        // C-043: Core budget ceiling check.
        // ⛔ Fields are non-nullable long — do NOT apply ?? operator.
        // ⛔ BudgetRemainingInrPaise is not a property — derived below from the three canonical fields.
        long projectedTotalSpendInrPaise = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        bool ceilingExceeded             = projectedTotalSpendInrPaise > ctx.ApprovedBudgetInrPaise;

        // C-051: Derive remaining budget for transparent logging — not a property, computed here.
        long budgetRemainingInrPaise         = ctx.ApprovedBudgetInrPaise - ctx.CurrentSpendInrPaise;
        long budgetRemainingAfterProposedInrPaise = budgetRemainingInrPaise - ctx.ProposedSpendInrPaise;

        // C-051 (Resource Transparency): Always log budget state, even on Allow, so spend is visible.
        _logger.LogInformation(
            "C-043 budget evaluation: TenantId={TenantId} ContractId={ContractId} " +
            "SkillType={SkillType} ApprovedBudget={ApprovedBudget} " +
            "CurrentSpend={CurrentSpend} ProposedSpend={ProposedSpend} " +
            "ProjectedTotal={ProjectedTotal} Remaining={Remaining} Exceeded={Exceeded}",
            ctx.TenantId,
            ctx.ContractId,
            ctx.BudgetSkillType,
            ctx.ApprovedBudgetInrPaise,
            ctx.CurrentSpendInrPaise,
            ctx.ProposedSpendInrPaise,
            projectedTotalSpendInrPaise,
            budgetRemainingInrPaise,
            ceilingExceeded);

        activity?.SetTag("projected_total_inr_paise",              projectedTotalSpendInrPaise);
        activity?.SetTag("budget_remaining_inr_paise",             budgetRemainingInrPaise);
        activity?.SetTag("budget_remaining_after_proposed_paise",  budgetRemainingAfterProposedInrPaise);
        activity?.SetTag("ceiling_exceeded",                       ceilingExceeded);

        EvaluationResult result;

        if (ceilingExceeded)
        {
            // C-073: DENY path — C-043 Budget Ceiling constitutional obligation violated.
            _logger.LogWarning(
                "C-043 DENY: Budget ceiling exceeded. TenantId={TenantId} ContractId={ContractId} " +
                "ProjectedTotal={ProjectedTotal} ApprovedBudget={ApprovedBudget} Shortfall={Shortfall}",
                ctx.TenantId,
                ctx.ContractId,
                projectedTotalSpendInrPaise,
                ctx.ApprovedBudgetInrPaise,
                projectedTotalSpendInrPaise - ctx.ApprovedBudgetInrPaise);

            result = new EvaluationResult(
                ClaimId: "C-043",
                Verdict: EvaluationVerdict.Deny,
                Reason:  $"C-043 Budget Ceiling: projected total spend of {projectedTotalSpendInrPaise} paise " +
                         $"(current {ctx.CurrentSpendInrPaise} + proposed {ctx.ProposedSpendInrPaise}) " +
                         $"exceeds approved ceiling of {ctx.ApprovedBudgetInrPaise} paise " +
                         $"by {projectedTotalSpendInrPaise - ctx.ApprovedBudgetInrPaise} paise.");
        }
        else
        {
            // C-073: ALLOW path — within budget ceiling, C-043 satisfied.
            _logger.LogInformation(
                "C-043 ALLOW: Within budget ceiling. TenantId={TenantId} ContractId={ContractId} " +
                "RemainingAfterProposed={RemainingAfterProposed}",
                ctx.TenantId,
                ctx.ContractId,
                budgetRemainingAfterProposedInrPaise);

            result = new EvaluationResult(
                ClaimId: "C-043",
                Verdict: EvaluationVerdict.Allow,
                Reason:  $"C-043 Budget Ceiling satisfied: projected total spend of {projectedTotalSpendInrPaise} paise " +
                         $"is within approved ceiling of {ctx.ApprovedBudgetInrPaise} paise. " +
                         $"Remaining after proposed spend: {budgetRemainingAfterProposedInrPaise} paise.");
        }

        activity?.SetTag("verdict", result.Verdict.ToString());
        return Task.FromResult(result);
    }
}