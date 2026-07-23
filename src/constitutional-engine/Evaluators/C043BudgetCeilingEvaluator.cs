// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Annotation)

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-043 — Budget Ceiling evaluator.
/// Denies any action that would cause cumulative spend to exceed the contract's
/// budget ceiling. Applies to BUDGET_SPEND action type.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    // C-073: ClaimId links runtime enforcement to C-043.
    public string ClaimId => "C-043";

    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "BUDGET_SPEND" };

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    /// <inheritdoc />
    // C-073: EvaluateAsync implements C-043 — Budget Ceiling enforcement.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // No active contract → no budget authorized → deny.
        if (ctx.ActiveContract is null || ctx.BudgetCeilingCents <= 0)
        {
            _logger.LogWarning(
                "C-043 DENY: TenantId={TenantId} no active contract or zero budget ceiling",
                ctx.TenantId);

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: "No active contract or budget ceiling is zero — spend not authorized (C-043).",
                EvidenceHint: $"TenantId={ctx.TenantId}, BudgetCeilingCents={ctx.BudgetCeilingCents}"));
        }

        // ProposedSpendCents must be provided for BUDGET_SPEND actions.
        if (ctx.ProposedSpendCents is null or <= 0)
        {
            _logger.LogWarning(
                "C-043 DENY: TenantId={TenantId} BUDGET_SPEND with no valid ProposedSpendCents",
                ctx.TenantId);

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: "BUDGET_SPEND action must specify a positive ProposedSpendCents (C-043).",
                EvidenceHint: $"TenantId={ctx.TenantId}"));
        }

        var projectedTotal = ctx.CumulativeSpendCents + ctx.ProposedSpendCents.Value;

        // C-073: Ceiling check — projected total must not exceed contract ceiling.
        if (projectedTotal > ctx.BudgetCeilingCents)
        {
            _logger.LogWarning(
                "C-043 DENY: TenantId={TenantId} ProjectedTotal={ProjectedTotal} > Ceiling={Ceiling}",
                ctx.TenantId,
                projectedTotal,
                ctx.BudgetCeilingCents);

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"Projected spend {projectedTotal} cents would exceed budget ceiling " +
                        $"{ctx.BudgetCeilingCents} cents (C-043).",
                EvidenceHint: $"TenantId={ctx.TenantId}, Cumulative={ctx.CumulativeSpendCents}, " +
                              $"Proposed={ctx.ProposedSpendCents}, Ceiling={ctx.BudgetCeilingCents}"));
        }

        _logger.LogDebug(
            "C-043 AUTHORIZED: TenantId={TenantId} ProjectedTotal={ProjectedTotal} within Ceiling={Ceiling}",
            ctx.TenantId,
            projectedTotal,
            ctx.BudgetCeilingCents);

        return Task.FromResult(new EvaluationResult(EvaluationDecision.Authorized));
    }
}