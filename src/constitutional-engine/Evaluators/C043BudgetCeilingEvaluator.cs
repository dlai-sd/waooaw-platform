// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 (Budget Ceiling): a proposed action is DENIED if the sum of
/// current-month spend and proposed spend would exceed the tenant's approved
/// monthly budget ceiling for the relevant skill type.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource — every constitutional obligation carries an OTel trace
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId identifies the constitutional obligation this evaluator enforces
    /// <summary>Constitutional claim enforced by this evaluator.</summary>
    public string ClaimId => "C-043";

    // C-073: EvaluateAsync implements the C-043 budget ceiling constitutional obligation
    /// <summary>
    /// Evaluates whether the proposed spend would cause the tenant to exceed their
    /// approved monthly budget ceiling (C-043).  No network I/O — all budget fields
    /// are resolved from <see cref="EvaluationContext"/> before this call.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Begin trace span scoped to this constitutional evaluation
        using var activity = _tracer.StartActivity(
            "C043BudgetCeiling.Evaluate", ActivityKind.Internal);

        activity?.SetTag("constitutional.claim", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("budget.skill_type", ctx.BudgetSkillType);
        activity?.SetTag("budget.approved_inr_paise", ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("budget.current_spend_inr_paise", ctx.CurrentSpendInrPaise);
        activity?.SetTag("budget.proposed_spend_inr_paise", ctx.ProposedSpendInrPaise);

        // C-043: Ceiling check — do NOT use ?? on these fields; they are non-nullable long.
        // BEHAVIORAL RULE: compute remaining from the three canonical budget fields only;
        // BudgetRemainingInrPaise does NOT exist on EvaluationContext.
        bool exceeded =
            (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            long projectedSpend  = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
            long overageInrPaise = projectedSpend - ctx.ApprovedBudgetInrPaise;

            _logger.LogWarning(
                "C-043 DENY — budget ceiling exceeded. " +
                "TenantId={TenantId} SkillType={SkillType} " +
                "Approved={ApprovedInrPaise} Current={CurrentInrPaise} " +
                "Proposed={ProposedInrPaise} Projected={ProjectedInrPaise} " +
                "Overage={OverageInrPaise}",
                ctx.TenantId,
                ctx.BudgetSkillType,
                ctx.ApprovedBudgetInrPaise,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise,
                projectedSpend,
                overageInrPaise);

            activity?.SetTag("budget.exceeded", true);
            activity?.SetTag("budget.overage_inr_paise", overageInrPaise);

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-043 budget ceiling exceeded for skill type '{ctx.BudgetSkillType}': " +
                        $"projected spend {projectedSpend} paise would exceed approved ceiling " +
                        $"{ctx.ApprovedBudgetInrPaise} paise (overage {overageInrPaise} paise)."));
        }

        long remainingInrPaise =
            ctx.ApprovedBudgetInrPaise - (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise);

        _logger.LogInformation(
            "C-043 ALLOW — budget ceiling within limit. " +
            "TenantId={TenantId} SkillType={SkillType} " +
            "Approved={ApprovedInrPaise} Current={CurrentInrPaise} " +
            "Proposed={ProposedInrPaise} RemainingAfter={RemainingInrPaise}",
            ctx.TenantId,
            ctx.BudgetSkillType,
            ctx.ApprovedBudgetInrPaise,
            ctx.CurrentSpendInrPaise,
            ctx.ProposedSpendInrPaise,
            remainingInrPaise);

        activity?.SetTag("budget.exceeded", false);
        activity?.SetTag("budget.remaining_inr_paise", remainingInrPaise);

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: $"C-043 budget ceiling satisfied: projected spend within approved limit " +
                    $"({remainingInrPaise} paise remaining) for skill type '{ctx.BudgetSkillType}'."));
    }
}