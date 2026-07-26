// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Constitutional Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 Budget Ceiling: denies any action whose projected cumulative spend
/// (current + proposed) would exceed the tenant's approved monthly budget ceiling.
/// </summary>
/// <remarks>
/// C-073: This class implements a constitutional obligation (C-043 Budget Ceiling).
/// C-051: All budget evaluations are logged for resource transparency.
/// Evaluated fields are non-nullable long (paise) — no null-coalescing required.
/// BudgetRemainingInrPaise does NOT exist on EvaluationContext; remainder is computed inline.
/// </remarks>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: OpenTelemetry tracer shared across constitutional evaluators
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId identifies the constitutional claim enforced by this evaluator.
    /// <inheritdoc/>
    public string ClaimId => "C-043";

    /// <summary>
    /// Evaluates whether the proposed action would breach the tenant's approved budget ceiling.
    /// </summary>
    /// <remarks>
    /// C-043: projected_spend = CurrentSpendInrPaise + ProposedSpendInrPaise.
    ///        If projected_spend > ApprovedBudgetInrPaise → DENY.
    /// C-051: Resource transparency — log budget state at evaluation time regardless of verdict.
    /// C-073: Implements constitutional obligation C-043 Budget Ceiling at runtime.
    /// MUST NOT perform network I/O — reads only from EvaluationContext (pre-populated fields).
    /// </remarks>
    // C-073: EvaluateAsync enforces C-043 Budget Ceiling constitutional obligation.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("claim.id", ClaimId);
        activity?.SetTag("tenant.id", ctx.TenantId);
        activity?.SetTag("budget.skill_type", ctx.BudgetSkillType);
        activity?.SetTag("budget.approved_inr_paise", ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("budget.current_spend_inr_paise", ctx.CurrentSpendInrPaise);
        activity?.SetTag("budget.proposed_spend_inr_paise", ctx.ProposedSpendInrPaise);

        // C-043: Budget ceiling check.
        // All three fields are non-nullable long — intentionally no ?? operator.
        // BudgetRemainingInrPaise does not exist; remainder computed inline for logging only.
        bool exceeded = (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            long projectedSpend = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
            long overrunPaise = projectedSpend - ctx.ApprovedBudgetInrPaise;

            // C-051: Resource transparency — log breach details for audit trail.
            _logger.LogWarning(
                "C-043 budget ceiling breach for tenant {TenantId}: " +
                "projected={ProjectedSpend} ceiling={Ceiling} overrun={Overrun} skill_type={SkillType}",
                ctx.TenantId,
                projectedSpend,
                ctx.ApprovedBudgetInrPaise,
                overrunPaise,
                ctx.BudgetSkillType);

            activity?.SetTag("evaluation.verdict", "Deny");
            activity?.SetTag("budget.projected_spend_inr_paise", projectedSpend);
            activity?.SetTag("budget.overrun_inr_paise", overrunPaise);

            string denyReason =
                $"C-043 Budget Ceiling violated: projected spend {projectedSpend} paise " +
                $"exceeds approved ceiling {ctx.ApprovedBudgetInrPaise} paise " +
                $"(current={ctx.CurrentSpendInrPaise}, proposed={ctx.ProposedSpendInrPaise}, " +
                $"overrun={overrunPaise}, skill_type={ctx.BudgetSkillType}).";

            return Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, denyReason));
        }

        // C-051: Resource transparency — log within-budget state.
        long remainingAfterProposed = ctx.ApprovedBudgetInrPaise
            - (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise);

        _logger.LogInformation(
            "C-043 budget check passed for tenant {TenantId}: " +
            "current={CurrentSpend} proposed={ProposedSpend} ceiling={Ceiling} " +
            "remaining_after_proposed={RemainingAfterProposed} skill_type={SkillType}",
            ctx.TenantId,
            ctx.CurrentSpendInrPaise,
            ctx.ProposedSpendInrPaise,
            ctx.ApprovedBudgetInrPaise,
            remainingAfterProposed,
            ctx.BudgetSkillType);

        activity?.SetTag("evaluation.verdict", "Allow");
        activity?.SetTag("budget.remaining_after_proposed_inr_paise", remainingAfterProposed);

        return Task.FromResult(
            new EvaluationResult(ClaimId, EvaluationVerdict.Allow, "Budget ceiling check passed."));
    }
}