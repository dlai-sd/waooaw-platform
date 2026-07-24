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
    string TenantId,
    string AgentId,
    string ToolName,
    string ActionType,
    string? EmploymentContractId = null)
{
    public static EvaluationContext FromRequest(ValidateActionRequest request) => new(
        TenantId: request.TenantId,
        AgentId: request.AgentId,
        ToolName: request.ToolName,
        ActionType: request.ActionType,
        EmploymentContractId: string.IsNullOrEmpty(request.EmploymentContractId)
            ? null : request.EmploymentContractId);
}
