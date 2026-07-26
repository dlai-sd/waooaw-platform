// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Annotation), C-076 (Test Coverage)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 Budget Ceiling: the combined total of current month spend and proposed spend
/// must not exceed the approved monthly budget ceiling for the tenant contract.
/// </summary>
/// <remarks>
/// C-051 Resource Transparency: all budget fields are logged on every evaluation so that
/// resource usage is visible in structured logs and traces regardless of verdict.
/// </remarks>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: Shared ActivitySource — same logical tracer as all CE evaluators.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    /// <summary>Initializes a new instance of <see cref="C043BudgetCeilingEvaluator"/>.</summary>
    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        // C-073: Guard — DI must supply a valid logger.
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc/>
    /// <remarks>C-073: Claim identifier — matches constitutional claim file C-043.</remarks>
    public string ClaimId => "C-043";

    /// <summary>
    /// C-073: Evaluates the C-043 Budget Ceiling constraint.
    /// Decision rule (non-negotiable):
    ///   DENY  when (CurrentSpendInrPaise + ProposedSpendInrPaise) &gt; ApprovedBudgetInrPaise
    ///   ALLOW otherwise
    /// All three budget fields are non-nullable long — no null-coalescing required or permitted.
    /// No network I/O is performed; this evaluator reads only from the pre-populated EvaluationContext.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: Null guard on context — contract requires a valid context.
        ArgumentNullException.ThrowIfNull(ctx);

        // C-059: Trace every evaluation for auditability.
        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("budget_skill_type", ctx.BudgetSkillType);
        activity?.SetTag("approved_budget_inr_paise", ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("current_spend_inr_paise", ctx.CurrentSpendInrPaise);
        activity?.SetTag("proposed_spend_inr_paise", ctx.ProposedSpendInrPaise);

        // C-043: Budget ceiling enforcement.
        // ⛔ NEVER use ?? here — ApprovedBudgetInrPaise, CurrentSpendInrPaise,
        //    ProposedSpendInrPaise are non-nullable long (type contract §EvaluationContext).
        bool exceeded =
            (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            long totalIfApproved = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
            long overage = totalIfApproved - ctx.ApprovedBudgetInrPaise;

            // C-051: Resource Transparency — log all budget dimensions on denial.
            // C-073: Structured log; never string interpolation.
            _logger.LogWarning(
                "C-043 DENY: TenantId={TenantId} ContractId={ContractId} " +
                "SkillType={SkillType} ApprovedBudget={ApprovedBudget} " +
                "CurrentSpend={CurrentSpend} ProposedSpend={ProposedSpend} " +
                "TotalIfApproved={TotalIfApproved} Overage={Overage}",
                ctx.TenantId,
                ctx.ContractId,
                ctx.BudgetSkillType,
                ctx.ApprovedBudgetInrPaise,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise,
                totalIfApproved,
                overage);

            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("budget_overage_inr_paise", overage);
            activity?.SetTag("total_if_approved_inr_paise", totalIfApproved);

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason:
                    $"C-043 Budget Ceiling breached: proposed total spend of {totalIfApproved} paise " +
                    $"exceeds approved ceiling of {ctx.ApprovedBudgetInrPaise} paise " +
                    $"by {overage} paise (skill_type={ctx.BudgetSkillType}, " +
                    $"contract={ctx.ContractId})."));
        }

        // C-051: Resource Transparency — log remaining headroom on allow.
        long remaining =
            ctx.ApprovedBudgetInrPaise - ctx.CurrentSpendInrPaise - ctx.ProposedSpendInrPaise;

        _logger.LogInformation(
            "C-043 ALLOW: TenantId={TenantId} ContractId={ContractId} " +
            "SkillType={SkillType} ApprovedBudget={ApprovedBudget} " +
            "CurrentSpend={CurrentSpend} ProposedSpend={ProposedSpend} Remaining={Remaining}",
            ctx.TenantId,
            ctx.ContractId,
            ctx.BudgetSkillType,
            ctx.ApprovedBudgetInrPaise,
            ctx.CurrentSpendInrPaise,
            ctx.ProposedSpendInrPaise,
            remaining);

        activity?.SetTag("verdict", "Allow");
        activity?.SetTag("budget_remaining_inr_paise", remaining);

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason:
                $"C-043 Budget Ceiling satisfied: combined spend of " +
                $"{ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise} paise " +
                $"is within the approved ceiling of {ctx.ApprovedBudgetInrPaise} paise; " +
                $"remaining headroom {remaining} paise (skill_type={ctx.BudgetSkillType})."));
    }
}