// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-043, C-059
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Constitutional basis: C-043 (Budget Ceiling — LAW), C-059 (Implementation Traceability)
/// Purpose: Denies any proposed action that would cause current-month spend to exceed
///          the customer-approved budget ceiling for the active skill.
/// ADR reference: ADR-001 (gRPC Constitutional Engine), ADR-016 (Budget Ceiling enforcement)
/// Spec: architecture/reference/ce-validate-action-evaluators.md
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-059: named constant with constitutional reference — no magic strings.
    private const string ClaimIdValue = "C-043";

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    /// <inheritdoc />
    /// <remarks>C-043: identifies this evaluator's constitutional authority.</remarks>
    public string ClaimId => ClaimIdValue;

    /// <inheritdoc />
    /// <remarks>
    /// C-043 (LAW): budget ceiling is a Constitutional Floor equivalent.
    /// AD-016: CE MUST reject any action that would cause projected monthly spend to exceed
    ///         the customer-approved ceiling.
    ///
    /// Budget arithmetic uses the three non-nullable long fields on EvaluationContext:
    ///   ApprovedBudgetInrPaise  — customer-approved monthly ceiling
    ///   CurrentSpendInrPaise    — spend already incurred this calendar month
    ///   ProposedSpendInrPaise   — spend this action would incur if executed
    ///
    /// ⛔ BudgetRemainingInrPaise does NOT exist on EvaluationContext — computed here.
    /// ⛔ Do NOT use ?? on budget fields — they are non-nullable long.
    /// </remarks>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();

        try
        {
            // Guard: zero ceiling means budget has not been configured.
            // Escalate rather than silently allow — customer must confirm.
            if (ctx.ApprovedBudgetInrPaise == 0L)
            {
                _logger.LogWarning(
                    "C-043: No budget ceiling configured for contract {ContractId}, skill {SkillType}. Escalating.",
                    ctx.ContractId,
                    ctx.BudgetSkillType);

                return Task.FromResult(new EvaluationResult(
                    ClaimIdValue,
                    EvaluationVerdict.Escalate,
                    "BUDGET_CEILING_NOT_CONFIGURED: No approved budget ceiling exists for this skill. " +
                    "Customer confirmation required before spend may be incurred."));
            }

            // C-043: projected spend = already incurred + proposed action cost.
            // ⛔ Do NOT subtract — compute forward to avoid underflow on unsigned-equivalent semantics.
            long projectedSpend = ctx.CurrentSpendInrPaise + ctx.ProposedSpendInrPaise;
            bool exceeded = projectedSpend > ctx.ApprovedBudgetInrPaise;

            if (exceeded)
            {
                // Remaining capacity may be negative when current spend already breached ceiling
                // (defensive: ceiling could have been reduced after spend was incurred).
                long remainingCapacityPaise = ctx.ApprovedBudgetInrPaise - ctx.CurrentSpendInrPaise;

                string reason =
                    $"BUDGET_CEILING_REACHED: Proposed spend of {ctx.ProposedSpendInrPaise} paise " +
                    $"would bring projected monthly total to {projectedSpend} paise, " +
                    $"exceeding approved ceiling of {ctx.ApprovedBudgetInrPaise} paise. " +
                    $"Current spend: {ctx.CurrentSpendInrPaise} paise. " +
                    $"Remaining capacity: {remainingCapacityPaise} paise. " +
                    $"Skill type: {ctx.BudgetSkillType}.";

                _logger.LogWarning(
                    "C-043: Budget ceiling exceeded for contract {ContractId}. " +
                    "Proposed={ProposedSpend} Current={CurrentSpend} Projected={ProjectedSpend} " +
                    "Ceiling={Ceiling} Skill={SkillType}",
                    ctx.ContractId,
                    ctx.ProposedSpendInrPaise,
                    ctx.CurrentSpendInrPaise,
                    projectedSpend,
                    ctx.ApprovedBudgetInrPaise,
                    ctx.BudgetSkillType);

                return Task.FromResult(new EvaluationResult(
                    ClaimIdValue,
                    EvaluationVerdict.Deny,
                    reason));
            }

            // Budget ceiling not exceeded — allow.
            long remainingAfterProposed = ctx.ApprovedBudgetInrPaise - projectedSpend;

            _logger.LogDebug(
                "C-043: Budget ceiling check passed for contract {ContractId}. " +
                "Projected={ProjectedSpend} Ceiling={Ceiling} RemainingAfter={RemainingAfter} Skill={SkillType}",
                ctx.ContractId,
                projectedSpend,
                ctx.ApprovedBudgetInrPaise,
                remainingAfterProposed,
                ctx.BudgetSkillType);

            return Task.FromResult(new EvaluationResult(
                ClaimIdValue,
                EvaluationVerdict.Allow,
                $"Budget ceiling not exceeded. Projected spend: {projectedSpend} paise of " +
                $"{ctx.ApprovedBudgetInrPaise} paise ceiling. " +
                $"Remaining after proposed action: {remainingAfterProposed} paise."));
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1 (C-059, C-082): never swallow — log then rethrow.
            _logger.LogError(
                ex,
                "C-043: Budget ceiling evaluation failed for contract {ContractId}",
                ctx.ContractId);
            throw;
        }
    }
}