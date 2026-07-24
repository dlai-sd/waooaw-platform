// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency)
// C-073: This file implements a constitutional obligation — C-043 (no action may exceed approved budget ceiling)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-043 — Budget Ceiling.
/// No action may be executed if it would cause cumulative spend to exceed the approved monthly budget.
/// Applies to all action types that carry a BudgetContext (ProposedSpendInrPaise > 0).
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: Constitutional obligation — C-043 Budget Ceiling
    public string ClaimId => "C-043";

    /// <summary>
    /// Applies to all action types — budget ceiling is universal. Filtered by ProposedSpend == 0
    /// at evaluation time to avoid spurious denials for zero-cost actions.
    /// </summary>
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);  // empty = all types

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");
    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Implements C-043 — deny if proposed spend would exceed the approved budget ceiling
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C043BudgetCeilingEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("approved_budget_inr_paise", ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("current_spend_inr_paise", ctx.CurrentSpendInrPaise);
        activity?.SetTag("proposed_spend_inr_paise", ctx.ProposedSpendInrPaise);

        // No budget context provided — this evaluator passes (action has no cost dimension)
        if (ctx.ProposedSpendInrPaise == 0 && ctx.ApprovedBudgetInrPaise == 0)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-043",
                Verdict: EvaluationVerdict.Allow,
                Reason: "C-043: No budget context; zero-cost action permitted."));
        }

        // Approved budget must be set when a spend is proposed
        if (ctx.ApprovedBudgetInrPaise <= 0)
        {
            _logger.LogWarning(
                "C-043 DENY: ProposedSpend present but ApprovedBudget is zero or negative. " +
                "ContractId={ContractId} ProposedSpend={ProposedSpend}",
                ctx.ContractId, ctx.ProposedSpendInrPaise);

            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-043",
                Verdict: EvaluationVerdict.Deny,
                Reason: "C-043: Budget ceiling violated — no approved budget configured; " +
                        "all spending requires an explicit approved monthly budget."));
        }

        var projectedTotal = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        if (projectedTotal > ctx.ApprovedBudgetInrPaise)
        {
            var overage = projectedTotal - ctx.ApprovedBudgetInrPaise;
            _logger.LogWarning(
                "C-043 DENY: Budget ceiling exceeded. ContractId={ContractId} " +
                "Approved={Approved} Current={Current} Proposed={Proposed} Overage={Overage} SkillType={SkillType}",
                ctx.ContractId, ctx.ApprovedBudgetInrPaise, ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise, overage, ctx.BudgetSkillType);

            activity?.SetTag("c043.overage_inr_paise", overage);

            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-043",
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-043: Budget ceiling exceeded — projected spend of {projectedTotal} paise " +
                        $"exceeds approved monthly ceiling of {ctx.ApprovedBudgetInrPaise} paise " +
                        $"(overage: {overage} paise, skill type: {ctx.BudgetSkillType})."));
        }

        var remaining = ctx.ApprovedBudgetInrPaise - projectedTotal;
        _logger.LogInformation(
            "C-043 ALLOW: ContractId={ContractId} Remaining={Remaining} paise after proposed spend.",
            ctx.ContractId, remaining);

        return Task.FromResult(new EvaluationResult(
            ClaimId: "C-043",
            Verdict: EvaluationVerdict.Allow,
            Reason: $"C-043: Within budget ceiling. Remaining after action: {remaining} paise."));
    }
}