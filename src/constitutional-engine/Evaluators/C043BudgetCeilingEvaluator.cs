// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 (Budget Ceiling): denies any action whose proposed spend would cause
/// the sum of current-month spend and proposed spend to exceed the tenant's approved monthly
/// budget ceiling for the relevant skill type.
///
/// C-051 (Resource Transparency): all budget figures are emitted as OpenTelemetry tags so
/// that resource consumption is observable and auditable without querying the DB.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: Tracer shared with every evaluator in this service assembly.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    /// <summary>C-073: Constructor injection — no service-locator usage.</summary>
    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Implements IClaimEvaluator.ClaimId — identifies the constitutional claim enforced here.
    /// <inheritdoc/>
    public string ClaimId => "C-043";

    /// <summary>
    /// C-073: Evaluate whether (CurrentSpendInrPaise + ProposedSpendInrPaise) exceeds
    /// ApprovedBudgetInrPaise. Short-circuit DENY on breach; ALLOW otherwise.
    ///
    /// Budget fields are non-nullable long on EvaluationContext — no null-coalescing is applied.
    /// BudgetRemainingInrPaise is not a property on EvaluationContext; it is computed inline.
    ///
    /// Performs zero network I/O — all required data is pre-mapped onto EvaluationContext
    /// by EvaluationContext.FromRequest() from the BudgetContext proto message.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073 / ADR-009: Trace every evaluation with budget telemetry for C-051 observability.
        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.EvaluateAsync", ActivityKind.Internal);

        activity?.SetTag("constitutional.claim_id", ClaimId);
        activity?.SetTag("tenant_id",                ctx.TenantId);
        activity?.SetTag("contract_id",              ctx.ContractId);
        activity?.SetTag("budget_skill_type",         ctx.BudgetSkillType);
        activity?.SetTag("approved_budget_inr_paise", ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("current_spend_inr_paise",   ctx.CurrentSpendInrPaise);
        activity?.SetTag("proposed_spend_inr_paise",  ctx.ProposedSpendInrPaise);

        // C-043: Core budget ceiling check.
        // Fields are non-nullable long — no ?? operator needed or permitted.
        bool exceeded =
            (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) > ctx.ApprovedBudgetInrPaise;

        if (exceeded)
        {
            // Compute remaining budget inline — BudgetRemainingInrPaise does not exist on EvaluationContext.
            long remainingInrPaise = ctx.ApprovedBudgetInrPaise - ctx.CurrentSpendInrPaise;
            long projectedTotalInrPaise = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;

            // C-051: Log full budget breakdown for resource transparency.
            _logger.LogWarning(
                "C-043 budget ceiling breach. TenantId={TenantId} ContractId={ContractId} " +
                "SkillType={SkillType} ApprovedBudgetInrPaise={Approved} " +
                "CurrentSpendInrPaise={Current} ProposedSpendInrPaise={Proposed} " +
                "ProjectedTotalInrPaise={Projected} RemainingInrPaise={Remaining}",
                ctx.TenantId,
                ctx.ContractId,
                ctx.BudgetSkillType,
                ctx.ApprovedBudgetInrPaise,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise,
                projectedTotalInrPaise,
                remainingInrPaise);

            activity?.SetTag("verdict",                    "Deny");
            activity?.SetTag("projected_total_inr_paise",  projectedTotalInrPaise);
            activity?.SetTag("remaining_inr_paise",         remainingInrPaise);

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict:  EvaluationVerdict.Deny,
                Reason:   $"C-043 budget ceiling exceeded for skill '{ctx.BudgetSkillType}': " +
                          $"proposed spend of {ctx.ProposedSpendInrPaise} paise would bring total to " +
                          $"{projectedTotalInrPaise} paise, exceeding approved ceiling of " +
                          $"{ctx.ApprovedBudgetInrPaise} paise " +
                          $"(remaining before this action: {remainingInrPaise} paise)."
            ));
        }

        // C-051: Log successful pass for resource transparency.
        long remainingAfterInrPaise =
            ctx.ApprovedBudgetInrPaise - ctx.CurrentSpendInrPaise - ctx.ProposedSpendInrPaise;

        _logger.LogInformation(
            "C-043 budget ceiling check passed. TenantId={TenantId} ContractId={ContractId} " +
            "SkillType={SkillType} ApprovedBudgetInrPaise={Approved} " +
            "CurrentSpendInrPaise={Current} ProposedSpendInrPaise={Proposed} " +
            "RemainingAfterActionInrPaise={RemainingAfter}",
            ctx.TenantId,
            ctx.ContractId,
            ctx.BudgetSkillType,
            ctx.ApprovedBudgetInrPaise,
            ctx.CurrentSpendInrPaise,
            ctx.ProposedSpendInrPaise,
            remainingAfterInrPaise);

        activity?.SetTag("verdict",                         "Allow");
        activity?.SetTag("remaining_after_action_inr_paise", remainingAfterInrPaise);

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict:  EvaluationVerdict.Allow,
            Reason:   $"C-043 budget ceiling not exceeded for skill '{ctx.BudgetSkillType}': " +
                      $"projected total {ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise} paise " +
                      $"is within approved ceiling of {ctx.ApprovedBudgetInrPaise} paise " +
                      $"(remaining after action: {remainingAfterInrPaise} paise)."
        ));
    }
}