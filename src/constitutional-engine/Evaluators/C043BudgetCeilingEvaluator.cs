// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency), C-023 (Evidence First)

using Microsoft.Extensions.Logging;
using System.Diagnostics;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-043: No action may cause cumulative spend to exceed the approved monthly budget ceiling.
/// Applies to all action types that carry a BudgetContext (ProposedSpendInrPaise > 0).
/// </summary>
// C-073: Implements constitutional obligation C-043 (Budget Ceiling enforcement)
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // Empty set = evaluator registers for ALL action types; budget check applies universally.
    private static readonly IReadOnlySet<string> _actionTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public string ClaimId => "C-043";
    public IReadOnlySet<string> ApplicableActionTypes => _actionTypes;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Evaluates C-043 (Budget Ceiling) — DENY if proposed spend would breach approved ceiling
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C043BudgetCeilingEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("approved_budget_inr_paise", ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("current_spend_inr_paise", ctx.CurrentSpendInrPaise);
        activity?.SetTag("proposed_spend_inr_paise", ctx.ProposedSpendInrPaise);

        // No budget context attached — skip ceiling check (action is budget-neutral)
        if (ctx.ProposedSpendInrPaise == 0 && ctx.ApprovedBudgetInrPaise == 0)
        {
            _logger.LogDebug(
                "C-043 skipped: no budget context. ContractId={ContractId}", ctx.ContractId);
            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-043",
                Verdict: EvaluationVerdict.Allow,
                Reason: "C-043: No budget context — ceiling check not applicable."));
        }

        // Zero approved budget with a non-zero proposed spend is an immediate denial
        if (ctx.ApprovedBudgetInrPaise == 0 && ctx.ProposedSpendInrPaise > 0)
        {
            _logger.LogWarning(
                "C-043 DENY: ApprovedBudget is zero but ProposedSpend={ProposedSpend}. ContractId={ContractId}",
                ctx.ProposedSpendInrPaise, ctx.ContractId);
            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-043",
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-043: Approved monthly budget is zero. ProposedSpend={ctx.ProposedSpendInrPaise} paise cannot be authorised."));
        }

        var projectedTotal = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        var remaining = ctx.ApprovedBudgetInrPaise - ctx.CurrentSpendInrPaise;

        activity?.SetTag("projected_total_inr_paise", projectedTotal);
        activity?.SetTag("remaining_inr_paise", remaining);

        if (projectedTotal > ctx.ApprovedBudgetInrPaise)
        {
            _logger.LogWarning(
                "C-043 DENY: ProjectedTotal={ProjectedTotal} exceeds ApprovedBudget={ApprovedBudget}. " +
                "ContractId={ContractId} SkillType={SkillType}",
                projectedTotal, ctx.ApprovedBudgetInrPaise, ctx.ContractId, ctx.BudgetSkillType);
            activity?.SetTag("c043.verdict", "Deny");
            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-043",
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-043: Action would breach budget ceiling. " +
                        $"Projected={projectedTotal} paise, Approved={ctx.ApprovedBudgetInrPaise} paise, " +
                        $"Remaining={remaining} paise, SkillType={ctx.BudgetSkillType}."));
        }

        _logger.LogInformation(
            "C-043 ALLOW: Remaining={Remaining} paise after proposed spend. ContractId={ContractId}",
            remaining - ctx.ProposedSpendInrPaise, ctx.ContractId);
        activity?.SetTag("c043.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: "C-043",
            Verdict: EvaluationVerdict.Allow,
            Reason: $"C-043: Spend within ceiling. Remaining after action: {remaining - ctx.ProposedSpendInrPaise} paise."));
    }
}