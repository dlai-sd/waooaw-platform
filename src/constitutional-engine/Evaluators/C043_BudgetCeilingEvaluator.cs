// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043
// constitutional_basis: C-043 (Budget Ceiling — no spend beyond authorized limit)

#nullable enable

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-043 Evaluator — Budget Ceiling enforcement.
/// Denies any action that would cause daily, monthly, or per-call budget to be exceeded.
/// </summary>
/// <remarks>
/// C-073: Enforces C-043 at runtime — checks requested spend against tenant budget ceilings.
/// Applies to BUDGET_SPEND action type. Budget state is pre-loaded by ValidateAction handler.
/// </remarks>
public sealed class C043_BudgetCeilingEvaluator : IClaimEvaluator
{
    private readonly ILogger<C043_BudgetCeilingEvaluator> _logger;

    // C-073: Action type scope — only BUDGET_SPEND triggers this evaluator
    public string ClaimId => "C-043";
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "BUDGET_SPEND" };

    public C043_BudgetCeilingEvaluator(ILogger<C043_BudgetCeilingEvaluator> logger)
    {
        _logger = logger;
    }

    /// <inheritdoc/>
    /// <remarks>
    /// C-073: C-043 enforcement — deny if requested spend exceeds any budget ceiling.
    /// Checks: per-call ceiling, daily remaining, monthly remaining.
    /// </remarks>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-043: Budget state must be present for BUDGET_SPEND actions
        if (ctx.BudgetState is null)
        {
            _logger.LogError(
                "C-043 DENY: TenantId={TenantId} AgentId={AgentId} — " +
                "BudgetState not loaded for BUDGET_SPEND action (fail-safe deny)",
                ctx.TenantId, ctx.AgentId);

            return Task.FromResult(new EvaluationResult(
                Decision: EvaluationDecision.Deny,
                Reason: "C-043: Budget state unavailable — cannot verify spend ceiling. Fail-safe deny.",
                EvidenceHint: "budget_state_missing"
            ));
        }

        var requestedCents = ctx.RequestedSpendCents ?? 0L;
        var budget = ctx.BudgetState;

        // C-043: Per-call ceiling check
        if (requestedCents > budget.PerCallCeilingCents)
        {
            _logger.LogWarning(
                "C-043 DENY: TenantId={TenantId} AgentId={AgentId} — " +
                "RequestedCents={RequestedCents} exceeds PerCallCeiling={PerCallCeiling}",
                ctx.TenantId, ctx.AgentId, requestedCents, budget.PerCallCeilingCents);

            return Task.FromResult(new EvaluationResult(
                Decision: EvaluationDecision.Deny,
                Reason: $"C-043: Requested spend {requestedCents}¢ exceeds per-call ceiling " +
                        $"{budget.PerCallCeilingCents}¢.",
                EvidenceHint: $"per_call_ceiling={budget.PerCallCeilingCents}"
            ));
        }

        // C-043: Daily budget ceiling check
        var dailyRemaining = budget.DailyBudgetCents - budget.DailySpentCents;
        if (requestedCents > dailyRemaining)
        {
            _logger.LogWarning(
                "C-043 DENY: TenantId={TenantId} AgentId={AgentId} — " +
                "RequestedCents={RequestedCents} exceeds DailyRemaining={DailyRemaining}",
                ctx.TenantId, ctx.AgentId, requestedCents, dailyRemaining);

            return Task.FromResult(new EvaluationResult(
                Decision: EvaluationDecision.Deny,
                Reason: $"C-043: Requested spend {requestedCents}¢ would exceed daily budget. " +
                        $"Remaining: {dailyRemaining}¢.",
                EvidenceHint: $"daily_remaining={dailyRemaining},daily_budget={budget.DailyBudgetCents}"
            ));
        }

        // C-043: Monthly budget ceiling check
        var monthlyRemaining = budget.MonthlyBudgetCents - budget.MonthlySpentCents;
        if (requestedCents > monthlyRemaining)
        {
            _logger.LogWarning(
                "C-043 DENY: TenantId={TenantId} AgentId={AgentId} — " +
                "RequestedCents={RequestedCents} exceeds MonthlyRemaining={MonthlyRemaining}",
                ctx.TenantId, ctx.AgentId, requestedCents, monthlyRemaining);

            return Task.FromResult(new EvaluationResult(
                Decision: EvaluationDecision.Deny,
                Reason: $"C-043: Requested spend {requestedCents}¢ would exceed monthly budget. " +
                        $"Remaining: {monthlyRemaining}¢.",
                EvidenceHint: $"monthly_remaining={monthlyRemaining},monthly_budget={budget.MonthlyBudgetCents}"
            ));
        }

        _logger.LogDebug(
            "C-043 AUTHORIZED: TenantId={TenantId} AgentId={AgentId} RequestedCents={RequestedCents}",
            ctx.TenantId, ctx.AgentId, requestedCents);

        return Task.FromResult(new EvaluationResult(EvaluationDecision.Authorized));
    }
}