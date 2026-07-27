// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043
// constitutional_basis: C-043 (Budget Ceiling), C-059 (Traceability), C-073 (Annotated Obligations)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 Budget Ceiling: an action is denied when the proposed spend
/// would cause cumulative monthly spend to exceed the approved monthly budget
/// for the tenant's skill type.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: Constitutional obligation annotation — enforces C-043 (Budget Ceiling)
    // Every action that carries a ProposedSpendInrPaise must not push
    // CurrentSpendInrPaise + ProposedSpendInrPaise beyond ApprovedBudgetInrPaise.

    /// <inheritdoc/>
    public string ClaimId => "C-043";

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc/>
    // C-073: Implements C-043 (Budget Ceiling) constitutional obligation.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("constitutional.claim", ClaimId);
        activity?.SetTag("constitutional.tenant_id", ctx.TenantId);
        activity?.SetTag("constitutional.contract_id", ctx.ContractId);
        activity?.SetTag("constitutional.budget_skill_type", ctx.BudgetSkillType);
        activity?.SetTag("constitutional.approved_budget_inr_paise", ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("constitutional.current_spend_inr_paise", ctx.CurrentSpendInrPaise);
        activity?.SetTag("constitutional.proposed_spend_inr_paise", ctx.ProposedSpendInrPaise);

        // C-073: Zero approved budget means no spend is permitted.
        if (ctx.ApprovedBudgetInrPaise == 0L)
        {
            _logger.LogWarning(
                "C-043 DENY: ApprovedBudgetInrPaise is zero for TenantId={TenantId} ContractId={ContractId} SkillType={SkillType}",
                ctx.TenantId, ctx.ContractId, ctx.BudgetSkillType);

            activity?.SetTag("constitutional.verdict", "Deny");
            activity?.SetTag("constitutional.deny_reason", "zero_approved_budget");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-043: Approved monthly budget is zero for skill type '{ctx.BudgetSkillType}'. No spend is permitted."));
        }

        // C-073: Deny when proposed spend would exceed the approved monthly ceiling.
        // BEHAVIORAL RULE: BudgetRemainingInrPaise does NOT exist on EvaluationContext —
        // compute ceiling check inline from the three non-nullable long fields.
        bool exceeded = (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            long remainingPaise = ctx.ApprovedBudgetInrPaise - ctx.CurrentSpendInrPaise;

            _logger.LogWarning(
                "C-043 DENY: Budget ceiling exceeded for TenantId={TenantId} ContractId={ContractId} " +
                "SkillType={SkillType} Proposed={ProposedSpendInrPaise} Remaining={RemainingPaise} Approved={ApprovedBudgetInrPaise}",
                ctx.TenantId, ctx.ContractId, ctx.BudgetSkillType,
                ctx.ProposedSpendInrPaise, remainingPaise, ctx.ApprovedBudgetInrPaise);

            activity?.SetTag("constitutional.verdict", "Deny");
            activity?.SetTag("constitutional.deny_reason", "budget_ceiling_exceeded");
            activity?.SetTag("constitutional.remaining_inr_paise", remainingPaise);

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-043: Proposed spend of {ctx.ProposedSpendInrPaise} paise would exceed approved " +
                        $"monthly budget of {ctx.ApprovedBudgetInrPaise} paise for skill type " +
                        $"'{ctx.BudgetSkillType}'. Remaining budget: {remainingPaise} paise."));
        }

        _logger.LogInformation(
            "C-043 Allow: Budget within ceiling for TenantId={TenantId} ContractId={ContractId} " +
            "SkillType={SkillType} Proposed={ProposedSpendInrPaise} Approved={ApprovedBudgetInrPaise}",
            ctx.TenantId, ctx.ContractId, ctx.BudgetSkillType,
            ctx.ProposedSpendInrPaise, ctx.ApprovedBudgetInrPaise);

        activity?.SetTag("constitutional.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: null));
    }
}