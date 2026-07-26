// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 Budget Ceiling: the sum of current monthly spend and proposed spend
/// must not exceed the tenant's approved monthly budget ceiling.
/// Constitutional basis: C-043 (Budget Ceiling), C-051 (Resource Transparency).
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource declared as static readonly per OpenTelemetry convention
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc />
    public string ClaimId => "C-043";

    /// <summary>
    /// C-073: Evaluates C-043 Budget Ceiling.
    /// DENY when (CurrentSpendInrPaise + ProposedSpendInrPaise) > ApprovedBudgetInrPaise.
    /// ALLOW otherwise. All three budget fields are non-nullable long — no null-coalescing applied.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: constitutional obligation — budget ceiling enforcement
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("constitutional.claim", ClaimId);
        activity?.SetTag("tenant.id", ctx.TenantId);
        activity?.SetTag("budget.skill_type", ctx.BudgetSkillType);
        activity?.SetTag("budget.approved_paise", ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("budget.current_paise", ctx.CurrentSpendInrPaise);
        activity?.SetTag("budget.proposed_paise", ctx.ProposedSpendInrPaise);

        // C-043: Budget ceiling formula — non-nullable long fields, no ?? operator
        // ⛔ BudgetRemainingInrPaise does NOT exist on EvaluationContext — derived here
        long projectedTotal = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        bool ceilingExceeded = projectedTotal > ctx.ApprovedBudgetInrPaise;

        if (ceilingExceeded)
        {
            // C-051: Resource Transparency — log detail for audit trail
            _logger.LogWarning(
                "C-043 budget ceiling breached. TenantId={TenantId} SkillType={SkillType} " +
                "CurrentSpend={CurrentSpend} ProposedSpend={ProposedSpend} " +
                "ProjectedTotal={ProjectedTotal} ApprovedCeiling={ApprovedCeiling}",
                ctx.TenantId,
                ctx.BudgetSkillType,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise,
                projectedTotal,
                ctx.ApprovedBudgetInrPaise);

            activity?.SetTag("evaluation.verdict", "Deny");

            string denyReason =
                $"C-043 budget ceiling breached: current={ctx.CurrentSpendInrPaise} paise + " +
                $"proposed={ctx.ProposedSpendInrPaise} paise = {projectedTotal} paise " +
                $"exceeds approved ceiling of {ctx.ApprovedBudgetInrPaise} paise " +
                $"(skill_type={ctx.BudgetSkillType}, tenant={ctx.TenantId}).";

            return Task.FromResult(
                new EvaluationResult(ClaimId, EvaluationVerdict.Deny, denyReason));
        }

        // C-051: Resource Transparency — log headroom on allow path
        long budgetRemaining = ctx.ApprovedBudgetInrPaise - ctx.CurrentSpendInrPaise;

        _logger.LogDebug(
            "C-043 budget within ceiling. TenantId={TenantId} SkillType={SkillType} " +
            "ProposedSpend={ProposedSpend} BudgetRemaining={BudgetRemaining} ApprovedCeiling={ApprovedCeiling}",
            ctx.TenantId,
            ctx.BudgetSkillType,
            ctx.ProposedSpendInrPaise,
            budgetRemaining,
            ctx.ApprovedBudgetInrPaise);

        activity?.SetTag("evaluation.verdict", "Allow");
        activity?.SetTag("budget.remaining_paise", budgetRemaining);

        string allowReason =
            $"C-043 budget within ceiling: proposed={ctx.ProposedSpendInrPaise} paise, " +
            $"remaining headroom={budgetRemaining} paise " +
            $"(skill_type={ctx.BudgetSkillType}, tenant={ctx.TenantId}).";

        return Task.FromResult(
            new EvaluationResult(ClaimId, EvaluationVerdict.Allow, allowReason));
    }
}