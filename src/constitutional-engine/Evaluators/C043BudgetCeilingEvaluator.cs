// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency), C-059 (Traceability)

#nullable enable

using Microsoft.Extensions.Logging;
using System.Diagnostics;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-043: AI-initiated spend must not exceed the per-action budget ceiling.
/// Inspects the 'estimated_cost_usd' and 'cumulative_session_cost_usd' parameters.
/// Any action whose declared cost exceeds the ceiling is denied immediately.
/// </summary>
public sealed class C043BudgetCeilingEvaluator : IClaimEvaluator
{
    // C-073: Constitutional obligation annotation
    // Enforces C-043 — AI-initiated spend must remain within approved budget ceilings.

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // DESIGN_QUESTION: Budget ceiling constants should come from tenant config / feature flags.
    // Hardcoded thresholds here are safe-side defaults pending EA approval of a config strategy.
    private const decimal SingleActionCeilingUsd = 50.00m;
    private const decimal SessionCeilingUsd = 500.00m;

    // C-043 applies to any action that may incur cost.
    private static readonly IReadOnlySet<string> _actionTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "MCP_TOOL_CALL",
            "SPEND",
            "RESOURCE_ALLOCATION",
            "API_CALL",
        };

    private readonly ILogger<C043BudgetCeilingEvaluator> _logger;

    public string ClaimId => "C-043";
    public IReadOnlySet<string> ApplicableActionTypes => _actionTypes;

    public C043BudgetCeilingEvaluator(ILogger<C043BudgetCeilingEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc/>
    // C-073: Implements C-043 — budget ceiling enforcement.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C043.EvaluateAsync", ActivityKind.Internal);
        activity?.SetTag("claim", ClaimId);
        activity?.SetTag("action_type", ctx.ActionType);

        // Check per-action estimated cost.
        if (ctx.ActionParameters.TryGetValue("estimated_cost_usd", out var rawCost)
            && decimal.TryParse(rawCost, System.Globalization.NumberStyles.Number,
                System.Globalization.CultureInfo.InvariantCulture, out var estimatedCost))
        {
            activity?.SetTag("estimated_cost_usd", estimatedCost);

            if (estimatedCost > SingleActionCeilingUsd)
            {
                _logger.LogWarning(
                    "C-043 DENY: estimated_cost_usd={Cost} exceeds ceiling={Ceiling} action_type={ActionType}",
                    estimatedCost, SingleActionCeilingUsd, ctx.ActionType);

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-043: Estimated cost ${estimatedCost:F2} exceeds per-action ceiling of ${SingleActionCeilingUsd:F2}."));
            }
        }

        // Check cumulative session cost.
        if (ctx.ActionParameters.TryGetValue("cumulative_session_cost_usd", out var rawSession)
            && decimal.TryParse(rawSession, System.Globalization.NumberStyles.Number,
                System.Globalization.CultureInfo.InvariantCulture, out var sessionCost))
        {
            activity?.SetTag("cumulative_session_cost_usd", sessionCost);

            if (sessionCost > SessionCeilingUsd)
            {
                _logger.LogWarning(
                    "C-043 DENY: cumulative_session_cost_usd={Cost} exceeds session ceiling={Ceiling}",
                    sessionCost, SessionCeilingUsd);

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-043: Cumulative session cost ${sessionCost:F2} exceeds session ceiling of ${SessionCeilingUsd:F2}."));
            }
        }

        _logger.LogInformation("C-043 ALLOW: Budget ceiling not breached. action_type={ActionType}", ctx.ActionType);
        return Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow,
            "C-043: Budget within approved ceiling."));
    }
}