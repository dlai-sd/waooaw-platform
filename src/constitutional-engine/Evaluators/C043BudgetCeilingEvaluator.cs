// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043
// constitutional_basis: C-043 (Budget Ceiling — no agent spend may exceed approved monthly budget)
// C-073: Every method in this file implements a constitutional obligation.

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-043 Evaluator — Budget Ceiling.
/// Denies any action whose proposed spend would push cumulative monthly spend
/// above the tenant's approved monthly budget (in INR paise).
/// Applies to all action types that carry a non-zero ProposedSpendInrPaise.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc/>
    public string ClaimId => "C-043";

    /// <inheritdoc/>
    // C-073: Empty = applies to ALL action types — budget ceiling is universal per C-043.
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    /// <inheritdoc/>
    // C-073: Enforces C-043 — proposed spend must not cause cumulative monthly spend to
    // exceed the approved budget ceiling for this tenant's contract.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C043BudgetCeilingEvaluator.EvaluateAsync");
        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("proposed_spend_paise", ctx.ProposedSpendInrPaise);
        activity?.SetTag("current_spend_paise", ctx.CurrentSpendInrPaise);
        activity?.SetTag("approved_budget_paise", ctx.ApprovedBudgetInrPaise);

        // If no spend is proposed, this evaluator is not triggered.
        if (ctx.ProposedSpendInrPaise <= 0)
        {
            _logger.LogDebug(
                "C-043 ALLOW: ProposedSpend=0 — no budget check required. ContractId={ContractId}",
                ctx.ContractId);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                "C-043: No spend proposed — budget ceiling not triggered."));
        }

        // Approved budget of 0 with a proposed spend is a hard deny.
        if (ctx.ApprovedBudgetInrPaise <= 0)
        {
            _logger.LogWarning(
                "C-043 DENY: ApprovedBudget=0 with ProposedSpend={ProposedSpend}. ContractId={ContractId}",
                ctx.ProposedSpendInrPaise, ctx.ContractId);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-043: No approved budget exists for this contract. All spend denied by default."));
        }

        // Guard against negative current spend (data integrity concern — escalate for review).
        if (ctx.CurrentSpendInrPaise < 0)
        {
            _logger.LogWarning(
                "C-043 ESCALATE: CurrentSpend={CurrentSpend} is negative — data integrity concern. ContractId={ContractId}",
                ctx.CurrentSpendInrPaise, ctx.ContractId);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                "C-043: Current spend value is negative — requires human review before authorization."));
        }

        var projectedSpend = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;

        if (projectedSpend > ctx.ApprovedBudgetInrPaise)
        {
            var overrunPaise = projectedSpend - ctx.ApprovedBudgetInrPaise;

            _logger.LogWarning(
                "C-043 DENY: ProjectedSpend={ProjectedSpend} exceeds ApprovedBudget={ApprovedBudget} " +
                "by {Overrun} paise. ContractId={ContractId} SkillType={SkillType}",
                projectedSpend, ctx.ApprovedBudgetInrPaise, overrunPaise,
                ctx.ContractId, ctx.BudgetSkillType);

            activity?.SetTag("overrun_paise", overrunPaise);
            activity?.SetTag("verdict", "Deny");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-043: Action would exceed approved monthly budget by {overrunPaise} paise " +
                $"(skill: {ctx.BudgetSkillType}). Projected={projectedSpend}, Approved={ctx.ApprovedBudgetInrPaise}."));
        }

        var remainingPaise = ctx.ApprovedBudgetInrPaise - projectedSpend;

        _logger.LogDebug(
            "C-043 ALLOW: BudgetRemaining={Remaining} paise after proposed spend. ContractId={ContractId}",
            remainingPaise, ctx.ContractId);

        activity?.SetTag("remaining_paise", remainingPaise);
        activity?.SetTag("verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-043: Proposed spend within approved budget. Remaining={remainingPaise} paise."));
    }
}