// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Annotation), C-076 (Test Coverage)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces constitutional claim C-043 (Budget Ceiling) at runtime.
/// Denies any action whose projected cumulative monthly spend would exceed
/// the tenant's approved budget for the relevant skill type.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource shared across the constitutional engine service boundary.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>Constitutional claim ID this evaluator enforces.</summary>
    public string ClaimId => "C-043";

    /// <summary>
    /// C-073: Constitutional obligation — enforces C-043 Budget Ceiling at action-evaluation time.
    ///
    /// Decision rule:
    ///   DENY  when (CurrentSpendInrPaise + ProposedSpendInrPaise) > ApprovedBudgetInrPaise
    ///   ALLOW otherwise
    ///
    /// Budget fields are non-nullable long (paise = 1/100 INR). No null-coalescing required.
    /// No network I/O is performed — all inputs arrive via EvaluationContext.
    /// Completes synchronously (Task.FromResult) to stay within the 40 ms ValidateAction budget.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Trace every budget evaluation for C-051 Resource Transparency.
        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("skill_type", ctx.BudgetSkillType);
        activity?.SetTag("approved_budget_inr_paise", ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("current_spend_inr_paise", ctx.CurrentSpendInrPaise);
        activity?.SetTag("proposed_spend_inr_paise", ctx.ProposedSpendInrPaise);

        // C-073: C-043 enforcement — projected total must not exceed approved ceiling.
        // ⛔ Do NOT use ?? — all three fields are non-nullable long by type contract.
        bool exceeded =
            (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            long projectedTotal = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;

            // C-051: Log full budget breakdown for resource transparency audit trail.
            _logger.LogWarning(
                "C-043 DENY TenantId={TenantId} SkillType={SkillType} " +
                "ApprovedBudgetInrPaise={ApprovedBudget} CurrentSpendInrPaise={CurrentSpend} " +
                "ProposedSpendInrPaise={ProposedSpend} ProjectedTotalInrPaise={ProjectedTotal}",
                ctx.TenantId,
                ctx.BudgetSkillType,
                ctx.ApprovedBudgetInrPaise,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise,
                projectedTotal);

            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("projected_total_inr_paise", projectedTotal);

            string reason =
                $"C-043 Budget Ceiling exceeded: projected spend of {projectedTotal} paise " +
                $"(current {ctx.CurrentSpendInrPaise} + proposed {ctx.ProposedSpendInrPaise}) " +
                $"exceeds approved budget of {ctx.ApprovedBudgetInrPaise} paise " +
                $"for skill_type '{ctx.BudgetSkillType}'.";

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: reason));
        }

        // C-051: Log approval with remaining headroom for transparency.
        long remaining = ctx.ApprovedBudgetInrPaise - ctx.CurrentSpendInrPaise - ctx.ProposedSpendInrPaise;

        _logger.LogInformation(
            "C-043 ALLOW TenantId={TenantId} SkillType={SkillType} " +
            "ApprovedBudgetInrPaise={ApprovedBudget} CurrentSpendInrPaise={CurrentSpend} " +
            "ProposedSpendInrPaise={ProposedSpend} RemainingHeadroomInrPaise={Remaining}",
            ctx.TenantId,
            ctx.BudgetSkillType,
            ctx.ApprovedBudgetInrPaise,
            ctx.CurrentSpendInrPaise,
            ctx.ProposedSpendInrPaise,
            remaining);

        activity?.SetTag("verdict", "Allow");
        activity?.SetTag("remaining_headroom_inr_paise", remaining);

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: $"Budget ceiling not exceeded. Remaining headroom: {remaining} paise."));
    }
}