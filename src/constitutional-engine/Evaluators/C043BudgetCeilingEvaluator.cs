// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Constitutional Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 (Budget Ceiling): denies any action whose cumulative spend
/// (current month spend + proposed spend) would exceed the tenant's approved
/// monthly budget ceiling.
///
/// This evaluator is synchronous — it reads only from the pre-populated
/// <see cref="EvaluationContext"/> fields and performs no network I/O,
/// keeping latency well within the 40 ms ValidateAction budget.
/// </summary>
// C-073: Class-level annotation — implements constitutional obligation C-043 (Budget Ceiling).
// Every DENY result is evidence-eligible per C-023 (Evidence First); the caller records it.
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource shared with the Constitutional Engine service (ADR-009 / OpenTelemetry).
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    /// <summary>Initialises the evaluator with a mandatory logger (DI constructor injection).</summary>
    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        // C-073: Null guard — constitutional services must never silently degrade.
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // ── IClaimEvaluator ────────────────────────────────────────────────────────────

    /// <inheritdoc/>
    // C-073: Identifies the constitutional claim this evaluator enforces.
    public string ClaimId => "C-043";

    /// <summary>
    /// Evaluates whether the proposed spend keeps the tenant within their approved
    /// monthly budget ceiling.
    /// </summary>
    /// <remarks>
    /// Decision rule (C-043):
    ///   DENY  when (CurrentSpendInrPaise + ProposedSpendInrPaise) &gt; ApprovedBudgetInrPaise
    ///   ALLOW otherwise (including when all three values are zero)
    ///
    /// All three budget fields are non-nullable <c>long</c> — no null-coalescing applied.
    /// <c>BudgetRemainingInrPaise</c> does not exist on <see cref="EvaluationContext"/>;
    /// the remaining budget is computed inline from the three canonical fields.
    /// </remarks>
    // C-073: Implements C-043 (Budget Ceiling) runtime enforcement.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("constitutional.claim", "C-043");
        activity?.SetTag("tenant.id",                        ctx.TenantId);
        activity?.SetTag("budget.skill_type",                ctx.BudgetSkillType);
        activity?.SetTag("budget.approved_inr_paise",        ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("budget.current_spend_inr_paise",   ctx.CurrentSpendInrPaise);
        activity?.SetTag("budget.proposed_spend_inr_paise",  ctx.ProposedSpendInrPaise);

        // C-073: Core C-043 budget ceiling check.
        // ⛔ Do NOT use BudgetRemainingInrPaise — it does not exist on EvaluationContext.
        // ⛔ Do NOT use ?? — these fields are non-nullable long.
        bool exceeded = (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise)
                        > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            long projectedTotal = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;

            // C-051 (Resource Transparency): structured log so spend analytics can consume it.
            _logger.LogWarning(
                "C-043 budget ceiling breached. " +
                "TenantId={TenantId} SkillType={SkillType} " +
                "ApprovedBudgetInrPaise={ApprovedBudgetInrPaise} " +
                "CurrentSpendInrPaise={CurrentSpendInrPaise} " +
                "ProposedSpendInrPaise={ProposedSpendInrPaise} " +
                "ProjectedTotalInrPaise={ProjectedTotalInrPaise}",
                ctx.TenantId,
                ctx.BudgetSkillType,
                ctx.ApprovedBudgetInrPaise,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise,
                projectedTotal);

            activity?.SetTag("c043.verdict",                    "Deny");
            activity?.SetTag("c043.projected_total_inr_paise",  projectedTotal);
            activity?.SetTag("c043.overage_inr_paise",
                projectedTotal - ctx.ApprovedBudgetInrPaise);

            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-043",
                Verdict: EvaluationVerdict.Deny,
                Reason:  $"C-043 Budget ceiling breached: projected spend of {projectedTotal} paise " +
                         $"(current {ctx.CurrentSpendInrPaise} + proposed {ctx.ProposedSpendInrPaise}) " +
                         $"exceeds the approved ceiling of {ctx.ApprovedBudgetInrPaise} paise " +
                         $"for skill type '{ctx.BudgetSkillType}'."
            ));
        }

        // C-051 (Resource Transparency): log allowances at Information level for spend dashboards.
        _logger.LogInformation(
            "C-043 budget within ceiling. " +
            "TenantId={TenantId} SkillType={SkillType} " +
            "ApprovedBudgetInrPaise={ApprovedBudgetInrPaise} " +
            "CurrentSpendInrPaise={CurrentSpendInrPaise} " +
            "ProposedSpendInrPaise={ProposedSpendInrPaise}",
            ctx.TenantId,
            ctx.BudgetSkillType,
            ctx.ApprovedBudgetInrPaise,
            ctx.CurrentSpendInrPaise,
            ctx.ProposedSpendInrPaise);

        activity?.SetTag("c043.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: "C-043",
            Verdict: EvaluationVerdict.Allow,
            Reason:  "Proposed spend is within the approved budget ceiling."
        ));
    }
}