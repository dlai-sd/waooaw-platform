// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Constitutional Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 Budget Ceiling: the sum of current spend and proposed spend must not exceed
/// the approved monthly budget in INR paise for the tenant's contract.
/// Deny is issued on first breach — C-051 Resource Transparency is satisfied via structured log
/// and the Reason field of EvaluationResult (recorded by caller per C-023).
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource must carry the canonical service tracer name.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        // C-073: Null guard — every constructor enforces argument safety.
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId is the canonical constitutional identifier for this evaluator.
    public string ClaimId => "C-043";

    /// <summary>
    /// C-073: Evaluate C-043 Budget Ceiling.
    /// Decision rule: DENY when (CurrentSpendInrPaise + ProposedSpendInrPaise) > ApprovedBudgetInrPaise.
    /// Fields are non-nullable long — do NOT apply ?? coalescing.
    /// No network I/O performed — pure arithmetic on EvaluationContext fields.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: Guard against null context — constitutional evaluations must never operate blind.
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("constitutional.claim", ClaimId);
        activity?.SetTag("tenant.id", ctx.TenantId);
        activity?.SetTag("contract.id", ctx.ContractId);
        activity?.SetTag("budget.skill_type", ctx.BudgetSkillType);
        activity?.SetTag("budget.approved_paise", ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("budget.current_spend_paise", ctx.CurrentSpendInrPaise);
        activity?.SetTag("budget.proposed_spend_paise", ctx.ProposedSpendInrPaise);

        // C-073: Core constitutional arithmetic — C-043 Budget Ceiling check.
        // ⛔ Do NOT use ?? — ApprovedBudgetInrPaise / CurrentSpendInrPaise / ProposedSpendInrPaise
        //    are non-nullable long as per TYPE CONTRACT.
        long totalIfApproved = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        bool exceeded = totalIfApproved > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            // C-051: Resource Transparency — log full budget breakdown so the denial is auditable.
            _logger.LogWarning(
                "C-043 budget ceiling exceeded for Tenant={TenantId} Contract={ContractId} " +
                "SkillType={SkillType}: CurrentSpend={CurrentSpend} + ProposedSpend={ProposedSpend} " +
                "= Total={Total} > Approved={Approved} (all values in INR paise)",
                ctx.TenantId,
                ctx.ContractId,
                ctx.BudgetSkillType,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise,
                totalIfApproved,
                ctx.ApprovedBudgetInrPaise);

            activity?.SetTag("budget.exceeded", true);
            activity?.SetTag("evaluation.verdict", nameof(EvaluationVerdict.Deny));

            string denyReason =
                $"C-043: Budget ceiling exceeded. " +
                $"CurrentSpend={ctx.CurrentSpendInrPaise} paise + " +
                $"ProposedSpend={ctx.ProposedSpendInrPaise} paise = " +
                $"{totalIfApproved} paise > " +
                $"ApprovedBudget={ctx.ApprovedBudgetInrPaise} paise " +
                $"(SkillType={ctx.BudgetSkillType}).";

            return Task.FromResult(
                new EvaluationResult(ClaimId, EvaluationVerdict.Deny, denyReason));
        }

        // C-051: Log remaining headroom for transparency even on Allow.
        long remainingPaise = ctx.ApprovedBudgetInrPaise - totalIfApproved;

        _logger.LogInformation(
            "C-043 budget within ceiling for Tenant={TenantId} Contract={ContractId} " +
            "SkillType={SkillType}: Total={Total} <= Approved={Approved} Remaining={Remaining} paise",
            ctx.TenantId,
            ctx.ContractId,
            ctx.BudgetSkillType,
            totalIfApproved,
            ctx.ApprovedBudgetInrPaise,
            remainingPaise);

        activity?.SetTag("budget.exceeded", false);
        activity?.SetTag("budget.remaining_paise", remainingPaise);
        activity?.SetTag("evaluation.verdict", nameof(EvaluationVerdict.Allow));

        string allowReason =
            $"C-043: Budget within ceiling. " +
            $"CurrentSpend={ctx.CurrentSpendInrPaise} paise + " +
            $"ProposedSpend={ctx.ProposedSpendInrPaise} paise = " +
            $"{totalIfApproved} paise <= " +
            $"ApprovedBudget={ctx.ApprovedBudgetInrPaise} paise " +
            $"(Remaining={remainingPaise} paise, SkillType={ctx.BudgetSkillType}).";

        return Task.FromResult(
            new EvaluationResult(ClaimId, EvaluationVerdict.Allow, allowReason));
    }
}