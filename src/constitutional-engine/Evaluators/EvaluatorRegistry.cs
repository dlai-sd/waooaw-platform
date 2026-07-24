// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-041 (Tool Authorization), C-043 (Budget Ceiling),
//                       C-048 (Non-Exploitation), C-062 (AI Security)

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Registry that resolves the ordered list of claim evaluators applicable to a given
/// action type. Evaluators are short-circuited on first DENY (see evaluator architecture spec).
/// </summary>
public sealed class EvaluatorRegistry
{
    private readonly IReadOnlyList<IClaimEvaluator> _evaluators;
    private readonly ILogger<EvaluatorRegistry> _logger;

    public EvaluatorRegistry(
        IEnumerable<IClaimEvaluator> evaluators,
        ILogger<EvaluatorRegistry> logger)
    {
        // C-073: Evaluators are ordered by claim ID for deterministic evaluation order
        _evaluators = evaluators.OrderBy(e => e.ClaimId).ToList();
        _logger = logger;
    }

    /// <summary>
    /// C-073: Returns evaluators applicable to the given action type, in evaluation order.
    /// An evaluator with an empty ApplicableActionTypes set applies to ALL action types.
    /// </summary>
    public IReadOnlyList<IClaimEvaluator> GetEvaluators(string actionType)
    {
        var applicable = _evaluators
            .Where(e => e.ApplicableActionTypes.Count == 0
                        || e.ApplicableActionTypes.Contains(actionType, StringComparer.OrdinalIgnoreCase))
            .ToList();

        _logger.LogDebug(
            "EvaluatorRegistry resolved {Count} evaluators for action type {ActionType}: [{Claims}]",
            applicable.Count,
            actionType,
            string.Join(", ", applicable.Select(e => e.ClaimId)));

        return applicable;
    }
}