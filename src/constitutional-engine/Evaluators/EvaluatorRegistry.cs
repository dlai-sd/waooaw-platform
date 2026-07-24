// Implements: architecture/reference/ce-validate-action-evaluators.md §Evaluator Architecture
// constitutional_basis: C-041 (Tool Authorization), C-059 (Traceability)

#nullable enable

using Microsoft.Extensions.Logging;
using System.Diagnostics;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Registry that resolves the ordered list of claim evaluators applicable to a given
/// (action_type, tool_name) pair. Short-circuit evaluation is handled by the caller
/// (ConstitutionalEngineService.ValidateAction).
/// </summary>
public interface IEvaluatorRegistry
{
    /// <summary>
    /// Returns evaluators that apply to <paramref name="actionType"/>, in enforcement order.
    /// Evaluators with an empty ApplicableActionTypes set apply to ALL action types.
    /// </summary>
    IReadOnlyList<IClaimEvaluator> GetEvaluators(string actionType);
}

/// <summary>Default implementation backed by DI-registered <see cref="IClaimEvaluator"/> instances.</summary>
public sealed class EvaluatorRegistry : IEvaluatorRegistry
{
    // C-073: Constitutional obligation — OTel tracing for every evaluation pipeline invocation
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly IReadOnlyList<IClaimEvaluator> _evaluators;
    private readonly ILogger<EvaluatorRegistry> _logger;

    public EvaluatorRegistry(
        IEnumerable<IClaimEvaluator> evaluators,
        ILogger<EvaluatorRegistry> logger)
    {
        ArgumentNullException.ThrowIfNull(evaluators);
        ArgumentNullException.ThrowIfNull(logger);

        // Stable ordering: evaluators are registered in DI order (constitution precedence order)
        _evaluators = evaluators.ToList().AsReadOnly();
        _logger = logger;
    }

    /// <inheritdoc/>
    public IReadOnlyList<IClaimEvaluator> GetEvaluators(string actionType)
    {
        using var activity = _tracer.StartActivity("EvaluatorRegistry.GetEvaluators");
        activity?.SetTag("action_type", actionType);

        var applicable = _evaluators
            .Where(e => e.ApplicableActionTypes.Count == 0
                     || e.ApplicableActionTypes.Contains(actionType, StringComparer.OrdinalIgnoreCase))
            .ToList()
            .AsReadOnly();

        _logger.LogInformation(
            "EvaluatorRegistry resolved {Count} evaluators for action_type={ActionType}",
            applicable.Count, actionType);

        activity?.SetTag("evaluator_count", applicable.Count);
        return applicable;
    }
}