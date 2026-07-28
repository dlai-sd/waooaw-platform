// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-041, C-073

#nullable enable
namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Constitutional claim evaluator contract.
/// Each implementation enforces one constitutional claim against a ValidateAction request.
/// </summary>
public interface IClaimEvaluator
{
    string ClaimId { get; }
    Task<EvaluationResult> EvaluateAsync(
        EvaluationContext context,
        CancellationToken cancellationToken = default);
}
