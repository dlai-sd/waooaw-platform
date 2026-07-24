// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 (Budget Ceiling)
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Annotated Obligations)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 (Budget Ceiling): denies any action whose proposed spend would cause the
/// tenant's cumulative monthly spend to exceed the contractually approved budget ceiling.
///
/// Algorithm:
///   1. If ProposedSpendInrPaise == 0 → Allow (no spend, ceiling not applicable).
///   2. ProjectedSpend = CurrentSpendInrPaise + ProposedSpendInrPaise
///   3. If ProjectedSpend > ApprovedBudgetInrPaise → Deny (ceiling breached).
///   4. Otherwise → Allow.
///
/// Applies to ALL action types (empty ApplicableActionTypes set) because budget ceiling
/// is a universal constitutional constraint — every action that proposes spend must pass it.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: OpenTelemetry tracer — every constitutional evaluator must emit spans
    private static readonly ActivitySource _tracer =
        new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    /// <inheritdoc />
    // C-073: ClaimId identifies which constitutional obligation this evaluator enforces
    public string ClaimId => "C-043";

    /// <inheritdoc />
    // Empty set → EvaluatorRegistry applies this evaluator to ALL action types.
    // C-043 is a universal financial constraint; no action type is exempt from budget ceiling.
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>
    /// Evaluates whether the proposed spend is within the approved monthly budget ceiling.
    /// </summary>
    // C-073: Constitutional obligation — budget ceiling must be evaluated before any spend is authorised
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Every evaluation produces an OpenTelemetry span for audit traceability (C-051)
        using var activity = _tracer.StartActivity(
            "C043BudgetCeilingEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("waooaw.claim_id",                 ClaimId);
        activity?.SetTag("waooaw.tenant_id",                ctx.TenantId);
        activity?.SetTag("waooaw.contract_id",              ctx.ContractId);
        activity?.SetTag("waooaw.action_type",              ctx.ActionType);
        activity?.SetTag("waooaw.budget_skill_type",        ctx.BudgetSkillType);
        activity?.SetTag("waooaw.approved_budget_paise",    ctx.ApprovedBudgetInrPaise);
        activity?.SetTag("waooaw.current_spend_paise",      ctx.CurrentSpendInrPaise);
        activity?.SetTag("waooaw.proposed_spend_paise",     ctx.ProposedSpendInrPaise);

        // ── Fast path: no spend proposed ────────────────────────────────────────────────
        if (ctx.ProposedSpendInrPaise == 0L)
        {
            _logger.LogInformation(
                "C-043 Allow (no spend): ContractId={ContractId} TenantId={TenantId} ActionType={ActionType}",
                ctx.ContractId, ctx.TenantId, ctx.ActionType);

            activity?.SetTag("waooaw.verdict", "Allow");
            activity?.SetTag("waooaw.fast_path", "no_spend_proposed");

            return Task.FromResult(Allow("No spend proposed; budget ceiling not applicable."));
        }

        // ── Budget ceiling check ─────────────────────────────────────────────────────────
        // Guarded against overflow: both operands are long, sum fits in long for realistic budgets.
        // DESIGN_QUESTION: Should we add overflow protection (checked arithmetic) for adversarial inputs?
        var projectedSpend  = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
        var approvedBudget  = ctx.ApprovedBudgetInrPaise;
        var headroomPaise   = approvedBudget - ctx.CurrentSpendInrPaise;

        activity?.SetTag("waooaw.projected_spend_paise", projectedSpend);
        activity?.SetTag("waooaw.headroom_paise",        headroomPaise);

        if (projectedSpend > approvedBudget)
        {
            // C-073: Denial reason must be human-readable and include all numeric evidence (C-023)
            var reason =
                $"C-043 Budget Ceiling breached: proposed spend of {ctx.ProposedSpendInrPaise} paise " +
                $"(skill_type={ctx.BudgetSkillType}) would bring cumulative monthly spend to " +
                $"{projectedSpend} paise, exceeding the approved ceiling of {approvedBudget} paise. " +
                $"Available headroom: {headroomPaise} paise.";

            _logger.LogWarning(
                "C-043 DENY: ContractId={ContractId} TenantId={TenantId} " +
                "ProposedSpend={ProposedSpend} ProjectedSpend={ProjectedSpend} " +
                "ApprovedBudget={ApprovedBudget} SkillType={SkillType}",
                ctx.ContractId, ctx.TenantId,
                ctx.ProposedSpendInrPaise, projectedSpend,
                approvedBudget, ctx.BudgetSkillType);

            activity?.SetTag("waooaw.verdict", "Deny");
            return Task.FromResult(Denied(reason));
        }

        // ── Within ceiling ────────────────────────────────────────────────────────────────
        _logger.LogInformation(
            "C-043 Allow: ContractId={ContractId} TenantId={TenantId} " +
            "ProjectedSpend={ProjectedSpend} ApprovedBudget={ApprovedBudget} Headroom={Headroom}",
            ctx.ContractId, ctx.TenantId,
            projectedSpend, approvedBudget, headroomPaise);

        activity?.SetTag("waooaw.verdict", "Allow");
        return Task.FromResult(Allow(
            $"Projected spend of {projectedSpend} paise is within approved ceiling of {approvedBudget} paise " +
            $"(headroom: {headroomPaise} paise)."));
    }

    // ── Private helpers ──────────────────────────────────────────────────────────────────

    private EvaluationResult Allow(string reason) =>
        new(ClaimId: ClaimId, Verdict: EvaluationVerdict.Allow, Reason: reason);

    private EvaluationResult Denied(string reason) =>
        new(ClaimId: ClaimId, Verdict: EvaluationVerdict.Deny, Reason: reason);
}