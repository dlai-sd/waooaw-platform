// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-041, C-073, C-076

#nullable enable
namespace Waooaw.ConstitutionalEngine.Evaluators;

using Microsoft.Extensions.Logging;

/// <summary>
/// Runs all registered IClaimEvaluator instances in parallel.
/// DENY from any evaluator → ValidateAction returns DENY (C-041 default-deny).
/// </summary>
public sealed class EvaluatorRegistry
{
    private readonly IReadOnlyList<IClaimEvaluator> _evaluators;
    private readonly ILogger<EvaluatorRegistry> _logger;

    public EvaluatorRegistry(
        IEnumerable<IClaimEvaluator> evaluators,
        ILogger<EvaluatorRegistry> logger)
    {
        _evaluators = evaluators.ToList();
        _logger = logger;
    }

    public int Count => _evaluators.Count;

    public async Task<IReadOnlyList<EvaluationResult>> EvaluateAllAsync(
        EvaluationContext context,
        CancellationToken cancellationToken = default)
    {
        _logger.LogInformation(
            "Evaluating action {ActionType} for contract {ContractId} against {Count} claims",
            context.ActionType, context.ContractId, _evaluators.Count);
        var tasks = _evaluators.Select(e => e.EvaluateAsync(context, cancellationToken));
        return await Task.WhenAll(tasks);
    }
}
