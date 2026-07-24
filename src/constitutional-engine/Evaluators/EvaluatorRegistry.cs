// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-041 (Tool Authorization), C-043 (Budget Ceiling),
//                       C-048 (Non-Exploitation), C-049 (Honest Limitation), C-062 (AI Security)

#nullable enable

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Registry that resolves which evaluators apply to a given action type.
/// Evaluators are ordered: universal claims first, then action-specific claims.
/// </summary>
/// <remarks>
/// C-073: Implements the evaluator dispatch table for CE.ValidateAction.
/// Short-circuit on first DENY per spec.
/// </remarks>
public sealed class EvaluatorRegistry
{
    private readonly IReadOnlyList<IClaimEvaluator> _evaluators;
    private readonly ILogger<EvaluatorRegistry> _logger;

    public EvaluatorRegistry(
        IEnumerable<IClaimEvaluator> evaluators,
        ILogger<EvaluatorRegistry> logger)
    {
        // C-073: Order: universal (empty ApplicableActionTypes) first, then specific
        _evaluators = evaluators
            .OrderBy(e => e.ApplicableActionTypes.Count == 0 ? 0 : 1)
            .ThenBy(e => e.ClaimId)
            .ToList();
        _logger = logger;
    }

    /// <summary>
    /// Returns evaluators applicable to the given action type, in evaluation order.
    /// </summary>
    public IEnumerable<IClaimEvaluator> GetEvaluators(string actionType)
    {
        foreach (var evaluator in _evaluators)
        {
            if (evaluator.ApplicableActionTypes.Count == 0 ||
                evaluator.ApplicableActionTypes.Contains(actionType))
            {
                yield return evaluator;
            }
        }
    }

    /// <summary>
    /// Returns all registered evaluator claim IDs (for diagnostics/health checks).
    /// </summary>
    public IReadOnlyList<string> RegisteredClaimIds =>
        _evaluators.Select(e => e.ClaimId).ToList();
}