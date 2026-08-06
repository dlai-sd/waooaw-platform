// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-001, C-003, C-023, C-043, C-059
using Grpc.Core;
using Microsoft.Extensions.Logging;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-043 (Budget Ceiling — LAW): denies any proposed action whose cumulative
/// monthly spend (current + proposed) would exceed the customer-approved budget ceiling.
///
/// Constitutional basis: C-043 (Budget Ceiling), C-023 (Evidence First), C-059 (Traceability)
/// ADR reference: ADR-001 (gRPC Constitutional Engine), ADR-016 (CE rejects over-budget actions)
///
/// Decision matrix:
///   ApprovedBudgetInrPaise == 0               → ESCALATE (no ceiling configured; human review)
///   CurrentSpend + ProposedSpend > Approved   → DENY     (BUDGET_CEILING_REACHED)
///   Otherwise                                 → ALLOW
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-043: Named constant — budget evaluator claim identity (C-059 traceability).
    private const string ClaimIdValue = "C-043";

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    /// <inheritdoc />
    public string ClaimId => ClaimIdValue;

    /// <summary>
    /// Initialises the C-043 budget ceiling evaluator.
    /// </summary>
    /// <param name="logger">Logger for audit-grade diagnostic messages.</param>
    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    /// <summary>
    /// Evaluates whether the proposed action's spend would breach the approved monthly budget ceiling.
    ///
    /// C-043 (LAW): The budget ceiling is a Constitutional Floor equivalent — no exceptions.
    /// Implementation must complete within its share of the 40 ms ValidateAction budget (ADR-005).
    /// MUST NOT perform any network I/O — all required data is carried on <paramref name="ctx"/>.
    /// </summary>
    /// <param name="ctx">Evaluation context populated from the ValidateActionRequest.</param>
    /// <param name="ct">Cancellation token — honours AD-001 / AD-005 latency budgets.</param>
    /// <returns>
    /// <see cref="EvaluationResult"/> with verdict Allow, Deny, or Escalate and an
    /// audit-ready reason string naming the violated constraint.
    /// </returns>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();

        // ── Guard: zero approved budget — treat as ceiling of zero ─────────────────────────────
        // ApprovedBudgetInrPaise == 0 means the ceiling is set to zero; any positive proposed
        // spend is denied. Zero proposed spend on a zero ceiling is trivially within bounds.
        if (ctx.ApprovedBudgetInrPaise == 0L)
        {
            if (ctx.ProposedSpendInrPaise == 0L)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimIdValue,
                    EvaluationVerdict.Allow,
                    "BUDGET_WITHIN_CEILING: Zero proposed spend within a zero-approved ceiling."));
            }

            _logger.LogWarning(
                "C-043 DENY: Proposed spend with zero approved budget ceiling. " +
                "ContractId={ContractId} SkillId={SkillId} SkillType={BudgetSkillType} " +
                "ProposedSpendPaise={ProposedSpendPaise} DecisionSpaceVersion={DecisionSpaceVersion}",
                ctx.ContractId,
                ctx.SkillId ?? "(none)",
                ctx.BudgetSkillType,
                ctx.ProposedSpendInrPaise,
                ctx.DecisionSpaceVersion);

            return Task.FromResult(new EvaluationResult(
                ClaimIdValue,
                EvaluationVerdict.Deny,
                $"BUDGET_CEILING_REACHED: No approved budget ceiling is configured (0 paise). " +
                $"Proposed spend of {ctx.ProposedSpendInrPaise} paise cannot proceed. Skill type: {ctx.BudgetSkillType}."));
        }

        // ── C-043 core enforcement ───────────────────────────────────────────────────────────────
        // AD-016: CE MUST reject any action where cumulative spend would exceed the approved ceiling.
        // BudgetRemainingInrPaise does not exist on EvaluationContext — compute from first principles.
        // ⛔ Do NOT use ?? on these fields — ApprovedBudgetInrPaise, CurrentSpendInrPaise, and
        //   ProposedSpendInrPaise are non-nullable long properties on EvaluationContext.
        bool ceilingExceeded =
            (ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise) > ctx.ApprovedBudgetInrPaise;

        if (ceilingExceeded)
        {
            // Compute headroom for the audit reason string (may be negative — intentional).
            long headroomPaise = ctx.ApprovedBudgetInrPaise - ctx.CurrentSpendInrPaise;

            _logger.LogWarning(
                "C-043 DENY: Budget ceiling reached. " +
                "ContractId={ContractId} SkillId={SkillId} SkillType={BudgetSkillType} " +
                "ApprovedPaise={ApprovedPaise} CurrentSpendPaise={CurrentSpendPaise} " +
                "ProposedSpendPaise={ProposedSpendPaise} HeadroomPaise={HeadroomPaise} " +
                "DecisionSpaceVersion={DecisionSpaceVersion}",
                ctx.ContractId,
                ctx.SkillId ?? "(none)",
                ctx.BudgetSkillType,
                ctx.ApprovedBudgetInrPaise,
                ctx.CurrentSpendInrPaise,
                ctx.ProposedSpendInrPaise,
                headroomPaise,
                ctx.DecisionSpaceVersion);

            return Task.FromResult(new EvaluationResult(
                ClaimIdValue,
                EvaluationVerdict.Deny,
                $"BUDGET_CEILING_REACHED: Proposed spend of {ctx.ProposedSpendInrPaise} paise " +
                $"added to current spend of {ctx.CurrentSpendInrPaise} paise " +
                $"({ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise} paise total) " +
                $"would exceed the approved monthly ceiling of {ctx.ApprovedBudgetInrPaise} paise. " +
                $"Remaining headroom: {headroomPaise} paise. Skill type: {ctx.BudgetSkillType}."));
        }

        // ── ALLOW — budget within approved ceiling ───────────────────────────────────────────────
        long remainingAfterProposedPaise =
            ctx.ApprovedBudgetInrPaise - ctx.CurrentSpendInrPaise - ctx.ProposedSpendInrPaise;

        _logger.LogDebug(
            "C-043 ALLOW: Proposed spend within budget ceiling. " +
            "ContractId={ContractId} SkillId={SkillId} SkillType={BudgetSkillType} " +
            "ApprovedPaise={ApprovedPaise} CurrentSpendPaise={CurrentSpendPaise} " +
            "ProposedSpendPaise={ProposedSpendPaise} RemainingAfterProposedPaise={RemainingPaise} " +
            "DecisionSpaceVersion={DecisionSpaceVersion}",
            ctx.ContractId,
            ctx.SkillId ?? "(none)",
            ctx.BudgetSkillType,
            ctx.ApprovedBudgetInrPaise,
            ctx.CurrentSpendInrPaise,
            ctx.ProposedSpendInrPaise,
            remainingAfterProposedPaise,
            ctx.DecisionSpaceVersion);

        return Task.FromResult(new EvaluationResult(
            ClaimIdValue,
            EvaluationVerdict.Allow,
            $"Budget ceiling not exceeded. Remaining after proposed spend: {remainingAfterProposedPaise} paise."));
    }
}