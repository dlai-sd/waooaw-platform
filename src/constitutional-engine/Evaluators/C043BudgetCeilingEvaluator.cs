// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 (Budget Ceiling): denies any action whose proposed spend,
/// added to current monthly spend, would exceed the tenant's approved budget ceiling.
/// Short-circuit deny protects against over-spend before any execution occurs.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: OpenTelemetry ActivitySource — budget ceiling decisions must be traceable (C-051)
    private static readonly ActivitySource _tracer =
        new("Waooaw.ConstitutionalEngine", "1.0");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    /// <summary>
    /// Initialises the evaluator with a required logger.
    /// Constructor injection only — never instantiate with new() outside DI.
    /// </summary>
    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        // C-073: Null guard — constitutional services must not silently degrade
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Constitutional claim identifier — links this evaluator to C-043 at runtime
    /// <inheritdoc />
    public string ClaimId => "C-043";

    // C-073: Implements C-043 (Budget Ceiling) — evaluates whether proposed spend
    //        would breach the tenant's approved monthly budget.
    /// <inheritdoc />
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: Null guard on context — missing context is a constitutional failure
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C043BudgetCeiling.Evaluate",
            ActivityKind.Internal);

        // C-051 (Resource Transparency): tag all budget dimensions for observability
        activity?.SetTag("tenant_id",                   ctx.TenantId);
        activity?.SetTag("contract_id",                 ctx.ContractId);
        activity?.SetTag("action_type",                 ctx.ActionType);
        activity?.SetTag("budget_skill_type",           ctx.BudgetSkillType);
        activity?.SetTag("approved_budget_inr_paise",   ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("current_spend_inr_paise",     ctx.CurrentSpendInrPaise);
        activity?.SetTag("proposed_spend_inr_paise",    ctx.ProposedSpendInrPaise);

        var result = EvaluateBudgetCeiling(ctx, activity);
        return Task.FromResult(result);
    }

    // C-073: Core C-043 enforcement logic — synchronous computation over context values only.
    //        MUST NOT perform network I/O. Budget fields are non-nullable long — no ?? needed.
    private EvaluationResult EvaluateBudgetCeiling(EvaluationContext ctx, Activity? activity)
    {
        // C-043: Canonical ceiling formula (from spec — non-negotiable, no ?? operator)
        // Fields ApprovedBudgetInrPaise / CurrentSpendInrPaise / ProposedSpendInrPaise are
        // non-nullable long on EvaluationContext — direct arithmetic is safe.
        bool exceeded =
            (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) > ctx.ApprovedBudgetInrPaise;

        // C-051: Compute derived telemetry values for transparency — BudgetRemainingInrPaise
        //        does NOT exist on EvaluationContext, computed locally here.
        long projectedTotalInrPaise = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        long remainingInrPaise      = ctx.ApprovedBudgetInrPaise - ctx.CurrentSpendInrPaise;

        activity?.SetTag("c043.projected_total_inr_paise", projectedTotalInrPaise);
        activity?.SetTag("c043.remaining_inr_paise",       remainingInrPaise);
        activity?.SetTag("c043.ceiling_exceeded",          exceeded);

        if (exceeded)
        {
            // C-073: C-043 DENY path — log at Warning level, include all budget dimensions
            _logger.LogWarning(
                "C-043 DENY: Budget ceiling exceeded for ContractId={ContractId} " +
                "TenantId={TenantId} SkillType={SkillType} " +
                "ApprovedBudgetInrPaise={ApprovedBudget} " +
                "CurrentSpendInrPaise={CurrentSpend} " +
                "ProposedSpendInrPaise={ProposedSpend} " +
                "ProjectedTotalInrPaise={Projected} " +
                "RemainingInrPaise={Remaining}",
                ctx.ContractId,
                ctx.TenantId,
                ctx.BudgetSkillType,
                ctx.ApprovedBudgetInrPaise,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise,
                projectedTotalInrPaise,
                remainingInrPaise);

            activity?.SetTag("c043.verdict", "Deny");

            return new EvaluationResult(
                ClaimId: "C-043",
                Verdict: EvaluationVerdict.Deny,
                Reason:  $"C-043 Budget Ceiling exceeded: projected spend of " +
                         $"{projectedTotalInrPaise} paise would exceed the approved " +
                         $"monthly budget of {ctx.ApprovedBudgetInrPaise} paise " +
                         $"(remaining allowance: {remainingInrPaise} paise, " +
                         $"skill type: {ctx.BudgetSkillType}).");
        }

        // C-073: C-043 Allow path — budget ceiling not breached
        _logger.LogInformation(
            "C-043 Allow: Budget within ceiling for ContractId={ContractId} " +
            "TenantId={TenantId} SkillType={SkillType} " +
            "ProjectedTotalInrPaise={Projected} " +
            "ApprovedBudgetInrPaise={ApprovedBudget} " +
            "RemainingInrPaise={Remaining}",
            ctx.ContractId,
            ctx.TenantId,
            ctx.BudgetSkillType,
            projectedTotalInrPaise,
            ctx.ApprovedBudgetInrPaise,
            remainingInrPaise);

        activity?.SetTag("c043.verdict", "Allow");

        return new EvaluationResult(
            ClaimId: "C-043",
            Verdict: EvaluationVerdict.Allow,
            Reason:  $"C-043 Budget Ceiling satisfied: projected spend of " +
                     $"{projectedTotalInrPaise} paise is within the approved " +
                     $"monthly budget of {ctx.ApprovedBudgetInrPaise} paise " +
                     $"(remaining allowance: {remainingInrPaise} paise).");
    }
}