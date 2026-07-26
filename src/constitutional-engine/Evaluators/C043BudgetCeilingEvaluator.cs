// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-043 (Budget Ceiling) — denies any action whose proposed spend
/// would cause cumulative monthly spend to exceed the tenant's approved budget ceiling.
/// C-051: All budget evaluations are traceable via OpenTelemetry activity tags.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-059: Activity source name matches the canonical service tracer name.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        // C-073: Constructor validates all required dependencies per constitutional DI rules.
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>C-043: Constitutional claim identifier enforced by this evaluator.</summary>
    public string ClaimId => "C-043";

    /// <summary>
    /// C-073: Evaluates whether the proposed action spend would breach the tenant's
    /// approved budget ceiling (C-043). Returns Deny on breach, Allow otherwise.
    /// C-051: Budget figures are traced as activity tags for resource transparency.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: Constitutional obligation — evaluate budget ceiling before authorising spend.
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.Evaluate",
            ActivityKind.Internal);

        // C-051: Tag all budget figures for resource transparency / audit trail.
        activity?.SetTag("constitutional.claim", ClaimId);
        activity?.SetTag("tenant.id", ctx.TenantId);
        activity?.SetTag("budget.skill_type", ctx.BudgetSkillType);
        activity?.SetTag("budget.approved_inr_paise", ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("budget.current_spend_inr_paise", ctx.CurrentSpendInrPaise);
        activity?.SetTag("budget.proposed_spend_inr_paise", ctx.ProposedSpendInrPaise);

        // C-043: Core ceiling check.
        // BEHAVIORAL RULE: Non-nullable longs — no ?? operators permitted.
        // BEHAVIORAL RULE: Do NOT reference BudgetRemainingInrPaise — it does not exist.
        bool exceeded =
            (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            long projectedTotal = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
            long overage = projectedTotal - ctx.ApprovedBudgetInrPaise;

            // C-051: Log breach details for resource transparency.
            _logger.LogWarning(
                "C-043 budget ceiling breached: TenantId={TenantId} SkillType={SkillType} " +
                "Approved={ApprovedInrPaise} Current={CurrentInrPaise} " +
                "Proposed={ProposedInrPaise} Projected={ProjectedInrPaise} Overage={OverageInrPaise}",
                ctx.TenantId,
                ctx.BudgetSkillType,
                ctx.ApprovedBudgetInrPaise,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise,
                projectedTotal,
                overage);

            activity?.SetTag("budget.exceeded", true);
            activity?.SetTag("budget.overage_inr_paise", overage);
            activity?.SetTag("evaluation.verdict", "Deny");

            var reason =
                $"C-043 budget ceiling exceeded: proposed spend of {ctx.ProposedSpendInrPaise} paise " +
                $"added to current spend of {ctx.CurrentSpendInrPaise} paise " +
                $"would total {projectedTotal} paise, exceeding the approved ceiling of " +
                $"{ctx.ApprovedBudgetInrPaise} paise by {overage} paise " +
                $"(skill_type={ctx.BudgetSkillType}).";

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: reason));
        }

        // C-043: Spend within ceiling — authorised to proceed.
        _logger.LogInformation(
            "C-043 budget ceiling check passed: TenantId={TenantId} SkillType={SkillType} " +
            "Approved={ApprovedInrPaise} Current={CurrentInrPaise} Proposed={ProposedInrPaise}",
            ctx.TenantId,
            ctx.BudgetSkillType,
            ctx.ApprovedBudgetInrPaise,
            ctx.CurrentSpendInrPaise,
            ctx.ProposedSpendInrPaise);

        activity?.SetTag("budget.exceeded", false);
        activity?.SetTag("evaluation.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: "Proposed spend is within the approved budget ceiling."));
    }
}