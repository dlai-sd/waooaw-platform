// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 Budget Ceiling: the sum of current monthly spend and the proposed
/// action spend must not exceed the tenant's approved monthly budget ceiling.
/// Short-circuits the evaluator chain with DENY when the ceiling would be breached.
/// </summary>
/// <remarks>
/// C-073: This class is the sole runtime enforcement point for constitutional claim C-043.
/// C-051: All budget field values are recorded in activity tags for Resource Transparency.
/// </remarks>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: Tracer scoped to the Constitutional Engine service per ADR-009
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Identifies the constitutional claim this evaluator enforces at runtime
    public string ClaimId => "C-043";

    /// <summary>
    /// Evaluates whether the proposed action's spend, when added to the tenant's
    /// current monthly spend, remains within the approved budget ceiling.
    /// </summary>
    /// <param name="ctx">Evaluation context carrying budget fields from the request.</param>
    /// <param name="ct">Cancellation token — propagated from the gRPC ServerCallContext.</param>
    /// <returns>
    /// <see cref="EvaluationVerdict.Allow"/> when projected total ≤ approved ceiling.
    /// <see cref="EvaluationVerdict.Deny"/>  when projected total  > approved ceiling.
    /// </returns>
    // C-073: EvaluateAsync enforces C-043 Budget Ceiling — DENY when spend would breach ceiling
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.Evaluate",
            ActivityKind.Internal);

        // C-051: Tag all budget fields for Resource Transparency tracing
        activity?.SetTag("claim.id",                          ClaimId);
        activity?.SetTag("tenant.id",                         ctx.TenantId);
        activity?.SetTag("budget.skill_type",                 ctx.BudgetSkillType);
        activity?.SetTag("budget.approved_inr_paise",         ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("budget.current_spend_inr_paise",    ctx.CurrentSpendInrPaise);
        activity?.SetTag("budget.proposed_spend_inr_paise",   ctx.ProposedSpendInrPaise);

        // C-073: Core C-043 ceiling check — no ?? operator; fields are non-nullable long
        // BEHAVIORAL RULE: exceeded = (current + proposed) > approved  (strict greater-than)
        long projectedTotalInrPaise = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        bool exceeded = projectedTotalInrPaise > ctx.ApprovedBudgetInrPaise;

        activity?.SetTag("budget.projected_total_inr_paise", projectedTotalInrPaise);
        activity?.SetTag("evaluation.verdict", exceeded ? "Deny" : "Allow");

        if (exceeded)
        {
            string reason =
                $"C-043 Budget Ceiling breached: projected spend {projectedTotalInrPaise} paise " +
                $"exceeds approved ceiling {ctx.ApprovedBudgetInrPaise} paise " +
                $"(current={ctx.CurrentSpendInrPaise} paise + proposed={ctx.ProposedSpendInrPaise} paise, " +
                $"skill_type='{ctx.BudgetSkillType}').";

            // C-051: Log breach with structured fields — never string interpolation in LogWarning
            _logger.LogWarning(
                "C-043 budget ceiling breach for TenantId={TenantId} SkillType={SkillType}: " +
                "projected={ProjectedInrPaise} paise exceeds approved={ApprovedInrPaise} paise",
                ctx.TenantId,
                ctx.BudgetSkillType,
                projectedTotalInrPaise,
                ctx.ApprovedBudgetInrPaise);

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: reason));
        }

        _logger.LogDebug(
            "C-043 budget ceiling within limits for TenantId={TenantId} SkillType={SkillType}: " +
            "projected={ProjectedInrPaise} paise within approved={ApprovedInrPaise} paise",
            ctx.TenantId,
            ctx.BudgetSkillType,
            projectedTotalInrPaise,
            ctx.ApprovedBudgetInrPaise);

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: $"Projected spend {projectedTotalInrPaise} paise is within " +
                    $"approved ceiling {ctx.ApprovedBudgetInrPaise} paise " +
                    $"(skill_type='{ctx.BudgetSkillType}')."));
    }
}