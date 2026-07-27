// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 Budget Ceiling: the cumulative projected spend
/// (current monthly spend + proposed action spend) must not exceed
/// the tenant's approved monthly budget ceiling.
///
/// Constitutional basis:
///   C-043 — AI agent must not cause spend beyond approved budget ceiling.
///   C-051 — Resource consumption must be transparent and bounded.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource scoped to the ConstitutionalEngine telemetry pipeline.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        // C-073: Constructor guard — null logger would silently drop audit trail.
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>Constitutional claim ID enforced by this evaluator.</summary>
    public string ClaimId => "C-043";

    // C-073: This method implements the runtime C-043 budget ceiling gate.
    // Any action whose projected spend would breach the approved ceiling MUST be denied.
    // Computation rule (C-043):
    //   bool exceeded = (CurrentSpendInrPaise + ProposedSpendInrPaise) > ApprovedBudgetInrPaise
    // IMPORTANT: Budget fields are non-nullable long — do NOT use ?? or null-coalescing operators.
    /// <inheritdoc/>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("tenant.id", ctx.TenantId);
        activity?.SetTag("budget.skill_type", ctx.BudgetSkillType);
        activity?.SetTag("budget.approved_inr_paise", ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("budget.current_spend_inr_paise", ctx.CurrentSpendInrPaise);
        activity?.SetTag("budget.proposed_spend_inr_paise", ctx.ProposedSpendInrPaise);

        // C-043: Projected spend is the authoritative comparison value.
        // Fields are non-nullable long — arithmetic is safe without null guards.
        long projectedSpend = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        bool exceeded = projectedSpend > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            string reason =
                $"C-043 Budget Ceiling exceeded: projected spend {projectedSpend} paise " +
                $"(current={ctx.CurrentSpendInrPaise} + proposed={ctx.ProposedSpendInrPaise}) " +
                $"exceeds approved ceiling {ctx.ApprovedBudgetInrPaise} paise " +
                $"for skill type '{ctx.BudgetSkillType}'.";

            // C-051: Log the breach with structured fields for resource transparency audit trail.
            _logger.LogWarning(
                "C-043 budget ceiling breach: TenantId={TenantId} SkillType={SkillType} " +
                "Projected={ProjectedPaise} Ceiling={CeilingPaise} " +
                "Current={CurrentPaise} Proposed={ProposedPaise}",
                ctx.TenantId,
                ctx.BudgetSkillType,
                projectedSpend,
                ctx.ApprovedBudgetInrPaise,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise);

            activity?.SetTag("evaluation.verdict", "Deny");
            activity?.SetTag("budget.projected_spend_inr_paise", projectedSpend);

            return Task.FromResult(
                new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));
        }

        // C-051: Log approval to provide full resource transparency on both paths.
        _logger.LogDebug(
            "C-043 budget within ceiling: TenantId={TenantId} SkillType={SkillType} " +
            "Projected={ProjectedPaise} Ceiling={CeilingPaise}",
            ctx.TenantId,
            ctx.BudgetSkillType,
            projectedSpend,
            ctx.ApprovedBudgetInrPaise);

        activity?.SetTag("evaluation.verdict", "Allow");
        activity?.SetTag("budget.projected_spend_inr_paise", projectedSpend);

        string allowReason =
            $"Budget within ceiling: projected spend {projectedSpend} paise " +
            $"<= approved {ctx.ApprovedBudgetInrPaise} paise " +
            $"for skill type '{ctx.BudgetSkillType}'.";

        return Task.FromResult(
            new EvaluationResult(ClaimId, EvaluationVerdict.Allow, allowReason));
    }
}