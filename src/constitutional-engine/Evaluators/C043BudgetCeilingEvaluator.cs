// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Annotation), C-023 (Evidence First)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 Budget Ceiling: the sum of current spend and proposed spend must not exceed
/// the approved monthly budget ceiling for the tenant. Any breach is denied immediately to
/// prevent unauthorised resource consumption (C-051 Resource Transparency).
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: Static tracer — every constitutional enforcement point must be observable
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc />
    /// <remarks>C-043: Budget Ceiling claim identifier.</remarks>
    public string ClaimId => "C-043";

    /// <summary>
    /// C-073: Evaluates whether the proposed action would breach the approved monthly budget ceiling.
    ///
    /// DENY condition (C-043):
    ///   (CurrentSpendInrPaise + ProposedSpendInrPaise) > ApprovedBudgetInrPaise
    ///
    /// All three fields are non-nullable long — no null-coalescing required or permitted.
    /// BudgetRemainingInrPaise does NOT exist on EvaluationContext; compute from the three fields.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Trace every C-043 budget ceiling evaluation for audit observability (C-051)
        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("constitutional.claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("budget.skill_type", ctx.BudgetSkillType);
        activity?.SetTag("budget.approved_inr_paise", ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("budget.current_spend_inr_paise", ctx.CurrentSpendInrPaise);
        activity?.SetTag("budget.proposed_spend_inr_paise", ctx.ProposedSpendInrPaise);

        // C-043: Core budget ceiling arithmetic.
        // RULE: do NOT use ?? — all three fields are non-nullable long (see TYPE CONTRACT).
        // RULE: BudgetRemainingInrPaise does not exist — compute inline.
        bool ceilingBreached =
            (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) > ctx.ApprovedBudgetInrPaise;

        if (ceilingBreached)
        {
            long projectedTotal = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
            long overage = projectedTotal - ctx.ApprovedBudgetInrPaise;

            // C-073: Structured log — no string interpolation in log templates (structured logging rule)
            _logger.LogWarning(
                "C-043 budget ceiling breach: TenantId={TenantId} SkillType={SkillType} " +
                "Approved={ApprovedInrPaise} Current={CurrentInrPaise} " +
                "Proposed={ProposedInrPaise} Overage={OverageInrPaise}",
                ctx.TenantId,
                ctx.BudgetSkillType,
                ctx.ApprovedBudgetInrPaise,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise,
                overage);

            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("budget.overage_inr_paise", overage);

            // C-043 + C-051: Denial reason must be fully traceable — include all budget figures
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-043: Budget ceiling breach. " +
                $"Projected spend ({ctx.CurrentSpendInrPaise} + {ctx.ProposedSpendInrPaise} = {projectedTotal} paise) " +
                $"exceeds approved ceiling of {ctx.ApprovedBudgetInrPaise} paise " +
                $"by {overage} paise [skill_type={ctx.BudgetSkillType}]."
            ));
        }

        // C-051: Log every authorized budget evaluation for resource transparency
        _logger.LogInformation(
            "C-043 budget ceiling check passed: TenantId={TenantId} SkillType={SkillType} " +
            "Approved={ApprovedInrPaise} Current={CurrentInrPaise} Proposed={ProposedInrPaise}",
            ctx.TenantId,
            ctx.BudgetSkillType,
            ctx.ApprovedBudgetInrPaise,
            ctx.CurrentSpendInrPaise,
            ctx.ProposedSpendInrPaise);

        activity?.SetTag("verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-043: Proposed spend within approved budget ceiling. " +
            $"Current={ctx.CurrentSpendInrPaise}, Proposed={ctx.ProposedSpendInrPaise}, " +
            $"Approved={ctx.ApprovedBudgetInrPaise} paise [skill_type={ctx.BudgetSkillType}]."
        ));
    }
}