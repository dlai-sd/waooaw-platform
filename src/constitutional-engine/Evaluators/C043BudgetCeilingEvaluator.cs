// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency), C-059 (Traceability)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-043: An agent MUST NOT execute any action whose total projected spend would exceed the
/// approved monthly budget ceiling. ProposedSpend + CurrentSpend > ApprovedBudget → DENY.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: Implements constitutional obligation C-043 (Budget Ceiling)
    public string ClaimId => "C-043";

    // C-073: Applies to all action types — budget ceiling is universal
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");
    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Evaluates C-043 — projected total spend must not exceed approved budget ceiling
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C043BudgetCeilingEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("constitutional.claim", ClaimId);
        activity?.SetTag("contract.id", ctx.ContractId);

        // BudgetRemainingInrPaise is long? (nullable) — use ?? 0L per stack rules
        var approved = ctx.ApprovedBudgetInrPaise;
        var current  = ctx.CurrentSpendInrPaise;
        var proposed = ctx.ProposedSpendInrPaise;

        activity?.SetTag("budget.approved_paise", approved);
        activity?.SetTag("budget.current_spend_paise", current);
        activity?.SetTag("budget.proposed_spend_paise", proposed);

        // If no budget context was provided (all zeros), allow — budget gate not applicable
        if (approved == 0L && proposed == 0L)
        {
            _logger.LogInformation(
                "C-043 ALLOW: No budget context provided. ContractId={ContractId}", ctx.ContractId);
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                "C-043: No budget context — ceiling check not applicable."));
        }

        var projectedTotal = current + proposed;
        if (projectedTotal > approved)
        {
            _logger.LogWarning(
                "C-043 DENY: Budget ceiling exceeded. ContractId={ContractId} " +
                "Approved={Approved} Current={Current} Proposed={Proposed} Projected={Projected}",
                ctx.ContractId, approved, current, proposed, projectedTotal);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-043: Projected spend {projectedTotal} paise exceeds approved ceiling " +
                $"{approved} paise. Remaining: {approved - current} paise."));
        }

        _logger.LogInformation(
            "C-043 ALLOW: ContractId={ContractId} Projected={Projected} Approved={Approved}",
            ctx.ContractId, projectedTotal, approved);

        activity?.SetTag("c043.verdict", "Allow");
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-043: Budget within ceiling. Remaining: {approved - projectedTotal} paise."));
    }
}