// Implements: architecture/reference/ce-validate-action-evaluators.md §Evaluator Architecture
// constitutional_basis: C-041 (Tool Authorization), C-059 (Traceability), C-073 (Annotation)

using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Resolves the ordered list of claim evaluators that apply to a given action.
/// Evaluators are applied in registration order; first DENY short-circuits.
/// </summary>
/// <remarks>
/// C-073: Registry is a constitutional obligation — it ensures every action is evaluated
/// against all applicable claims before authorization is granted.
/// </remarks>
public sealed class EvaluatorRegistry
{
    private readonly IReadOnlyList<IClaimEvaluator> _evaluators;
    private readonly ILogger<EvaluatorRegistry> _logger;

    public EvaluatorRegistry(
        IEnumerable<IClaimEvaluator> evaluators,
        ILogger<EvaluatorRegistry> logger)
    {
        _evaluators = evaluators?.ToList()
            ?? throw new ArgumentNullException(nameof(evaluators));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));

        _logger.LogInformation(
            "EvaluatorRegistry initialised with {Count} evaluators: {Claims}",
            _evaluators.Count,
            string.Join(", ", _evaluators.Select(e => e.ClaimId)));
    }

    /// <summary>
    /// Returns evaluators applicable to the given action type, in registration order.
    /// An evaluator with an empty ApplicableActionTypes set applies to ALL action types.
    /// </summary>
    // C-073: Evaluator selection is a constitutional obligation — universal evaluators (empty set)
    // must always be included so no action type can bypass a universal claim.
    public IReadOnlyList<IClaimEvaluator> GetEvaluators(string actionType)
    {
        if (string.IsNullOrWhiteSpace(actionType))
            throw new ArgumentException("Action type must not be empty.", nameof(actionType));

        var applicable = _evaluators
            .Where(e =>
                e.ApplicableActionTypes.Count == 0 ||          // universal evaluator
                e.ApplicableActionTypes.Contains(actionType))  // action-specific evaluator
            .ToList();

        _logger.LogDebug(
            "Resolved {Count} evaluators for action type '{ActionType}'",
            applicable.Count,
            actionType);

        return applicable;
    }
}