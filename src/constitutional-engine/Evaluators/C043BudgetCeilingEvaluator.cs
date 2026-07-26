// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Constitutional Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-043 (Budget Ceiling) — denies any proposed action whose cost,
/// when added to current month spend, would exceed the tenant's approved monthly budget.
/// C-051 (Resource Transparency): remaining budget is logged on every evaluation so
/// the audit trail reflects resource consumption state at decision time.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: OpenTelemetry tracer scoped to the Constitutional Engine activity source.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>C-073: Constitutional claim ID enforced by this evaluator.</summary>
    public string ClaimId => "C-043";

    /// <summary>
    /// C-073: Evaluate C-043 (Budget Ceiling).
    /// Decision: DENY when CurrentSpendInrPaise + ProposedSpendInrPaise > ApprovedBudgetInrPaise.
    /// Budget fields are non-nullable long — never apply ?? null-coalescing to them.
    /// No network I/O is performed: all values are resolved into EvaluationContext upstream.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-059: Structured telemetry span for every constitutional evaluation.
        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("budget_skill_type", ctx.BudgetSkillType);
        activity?.SetTag("approved_budget_inr_paise", ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("current_spend_inr_paise", ctx.CurrentSpendInrPaise);
        activity?.SetTag("proposed_spend_inr_paise", ctx.ProposedSpendInrPaise);

        // C-073: C-043 ceiling check — BudgetRemainingInrPaise does NOT exist on
        // EvaluationContext; derive it from the three authoritative budget fields.
        long projectedSpend = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        bool exceeded = projectedSpend > ctx.ApprovedBudgetInrPaise;

        // C-051: Compute remaining budget for transparent audit logging.
        long remainingAfterCurrent = ctx.ApprovedBudgetInrPaise - ctx.CurrentSpendInrPaise;
        long remainingAfterProposed = ctx.ApprovedBudgetInrPaise - projectedSpend;

        activity?.SetTag("projected_spend_inr_paise", projectedSpend);
        activity?.SetTag("remaining_after_current_inr_paise", remainingAfterCurrent);
        activity?.SetTag("budget_ceiling_exceeded", exceeded);

        if (exceeded)
        {
            // C-051: Log full resource state at denial time for audit transparency.
            _logger.LogWarning(
                "C-043 Budget ceiling EXCEEDED for TenantId={TenantId} ContractId={ContractId} " +
                "SkillType={BudgetSkillType}. Approved={ApprovedBudgetInrPaise} paise, " +
                "CurrentSpend={CurrentSpendInrPaise} paise, Proposed={ProposedSpendInrPaise} paise, " +
                "Projected={ProjectedSpend} paise, RemainingBeforeAction={RemainingAfterCurrent} paise.",
                ctx.TenantId,
                ctx.ContractId,
                ctx.BudgetSkillType,
                ctx.ApprovedBudgetInrPaise,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise,
                projectedSpend,
                remainingAfterCurrent);

            activity?.SetTag("decision", "Deny");

            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-043",
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-043: Action denied — proposed spend of {ctx.ProposedSpendInrPaise} paise " +
                        $"would bring cumulative monthly spend to {projectedSpend} paise, " +
                        $"exceeding the approved ceiling of {ctx.ApprovedBudgetInrPaise} paise. " +
                        $"Remaining budget before this action: {remainingAfterCurrent} paise " +
                        $"(skill_type={ctx.BudgetSkillType})."));
        }

        // C-051: Log resource consumption state on every ALLOW for transparency.
        _logger.LogInformation(
            "C-043 Budget ceiling satisfied for TenantId={TenantId} ContractId={ContractId} " +
            "SkillType={BudgetSkillType}. Approved={ApprovedBudgetInrPaise} paise, " +
            "CurrentSpend={CurrentSpendInrPaise} paise, Proposed={ProposedSpendInrPaise} paise, " +
            "RemainingAfterAction={RemainingAfterProposed} paise.",
            ctx.TenantId,
            ctx.ContractId,
            ctx.BudgetSkillType,
            ctx.ApprovedBudgetInrPaise,
            ctx.CurrentSpendInrPaise,
            ctx.ProposedSpendInrPaise,
            remainingAfterProposed);

        activity?.SetTag("decision", "Allow");
        activity?.SetTag("remaining_after_proposed_inr_paise", remainingAfterProposed);

        return Task.FromResult(new EvaluationResult(
            ClaimId: "C-043",
            Verdict: EvaluationVerdict.Allow,
            Reason: $"C-043: Proposed spend of {ctx.ProposedSpendInrPaise} paise is within the " +
                    $"approved monthly ceiling of {ctx.ApprovedBudgetInrPaise} paise. " +
                    $"Remaining after action: {remainingAfterProposed} paise " +
                    $"(skill_type={ctx.BudgetSkillType})."));
    }
}