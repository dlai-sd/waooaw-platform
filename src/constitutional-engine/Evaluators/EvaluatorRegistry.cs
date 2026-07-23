// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-041 (Tool Authorization), ADR-001 (gRPC)

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Registry that maps (action_type, tool_name) to the ordered list of evaluators
/// that must run for a given ValidateAction request.
/// </summary>
/// <remarks>
/// C-073: Implements the evaluator dispatch table — constitutional enforcement entry point.
/// Evaluators are ordered: security checks first (C-062, C-048), then authorization (C-041),
/// then budget (C-043), then limitation disclosure (C-049, C-051).
/// </remarks>
public sealed class EvaluatorRegistry
{
    private readonly IReadOnlyList<IClaimEvaluator> _allEvaluators;
    private readonly ILogger<EvaluatorRegistry> _logger;

    public EvaluatorRegistry(
        IEnumerable<IClaimEvaluator> evaluators,
        ILogger<EvaluatorRegistry> logger)
    {
        // C-073: Order matters — security denials before authorization before budget
        _allEvaluators = evaluators
            .OrderBy(e => GetEvaluatorPriority(e.ClaimId))
            .ToList()
            .AsReadOnly();
        _logger = logger;
    }

    /// <summary>
    /// Returns the ordered list of evaluators applicable to the given action type.
    /// Universal evaluators (empty ApplicableActionTypes) always included.
    /// </summary>
    public IReadOnlyList<IClaimEvaluator> GetEvaluators(string actionType)
    {
        // C-073: Filter evaluators by action type — universal evaluators always apply
        var applicable = _allEvaluators
            .Where(e => e.ApplicableActionTypes.Count == 0
                        || e.ApplicableActionTypes.Contains(actionType, StringComparer.OrdinalIgnoreCase))
            .ToList();

        _logger.LogDebug(
            "EvaluatorRegistry resolved {Count} evaluators for action_type={ActionType}: [{Claims}]",
            applicable.Count,
            actionType,
            string.Join(", ", applicable.Select(e => e.ClaimId)));

        return applicable.AsReadOnly();
    }

    /// <summary>
    /// Priority ordering: lower number = evaluated first.
    /// Security (C-062) → Exploitation (C-048) → Authorization (C-041) → Budget (C-043)
    /// → Limitation (C-049) → Transparency (C-051) → Unknown last.
    /// </summary>
    private static int GetEvaluatorPriority(string claimId) => claimId switch
    {
        "C-062" => 10,  // AI Security — prohibited tools
        "C-048" => 20,  // Non-Exploitation — agent exploitation flag
        "C-041" => 30,  // Tool Authorization — decision space boundary
        "C-043" => 40,  // Budget Ceiling — cost guard
        "C-049" => 50,  // Honest Limitation — escalate uncertain actions
        "C-051" => 60,  // Resource Transparency — spend disclosure
        _       => 99
    };
}