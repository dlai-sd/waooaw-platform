// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-041, C-059

#nullable enable
namespace Waooaw.ConstitutionalEngine.Evaluators;

using Waooaw.ConstitutionalEngine.Grpc;

/// <summary>
/// Immutable context derived from ValidateActionRequest.
/// Contains ONLY data from the gRPC request — no database access.
/// </summary>
public sealed record EvaluationContext(
    string ContractId,
    string ActionType,
    string ActionParameters,
    int DecisionSpaceVersion,
    string? SkillId = null)
{
    public static EvaluationContext FromRequest(ValidateActionRequest request) => new(
        ContractId: request.ContractId,
        ActionType: request.ActionType,
        ActionParameters: request.ActionParameters,
        DecisionSpaceVersion: request.DecisionSpaceVersion,
        SkillId: string.IsNullOrEmpty(request.SkillId) ? null : request.SkillId);
}
