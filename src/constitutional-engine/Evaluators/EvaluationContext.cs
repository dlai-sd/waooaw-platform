// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-041, C-059, C-043, C-062

#nullable enable
namespace Waooaw.ConstitutionalEngine.Evaluators;

using System.Text.Json;
using Waooaw.ConstitutionalEngine.Grpc;

/// <summary>
/// Immutable context derived from ValidateActionRequest + gRPC metadata.
/// Exposes all fields evaluators need — no DB access, no external calls.
/// TenantId: from gRPC metadata 'x-tenant-id' (not a proto field).
/// ActionParameters: JSON-encoded string — use GetParameter(key) to parse.
/// Budget fields: from BudgetContext nested proto message.
/// </summary>
public sealed record EvaluationContext(
    string ContractId,
    string ActionType,
    string ActionParameters,
    int DecisionSpaceVersion,
    string TenantId,
    string? SkillId = null,
    long ApprovedBudgetInrPaise = 0,
    long CurrentSpendInrPaise = 0,
    long ProposedSpendInrPaise = 0,
    string BudgetSkillType = "")
{
    /// <summary>
    /// Parse a named key from the JSON-encoded ActionParameters string.
    /// Evaluators use this instead of treating ActionParameters as a Dictionary.
    /// NEVER call .TryGetValue() on ActionParameters — it is a plain string, not a Dictionary.
    /// Example: ctx.GetParameter("tool_name") for C-041 tool authorization.
    /// </summary>
    public string? GetParameter(string key)
    {
        try
        {
            using var doc = JsonDocument.Parse(
                string.IsNullOrEmpty(ActionParameters) ? "{}" : ActionParameters);
            return doc.RootElement.TryGetProperty(key, out var val)
                ? val.GetString()
                : null;
        }
        catch { return null; }
    }

    /// <summary>
    /// Build context from gRPC request + tenant ID extracted from metadata.
    /// Called in ConstitutionalEngineService.ValidateAction before passing to evaluators.
    /// </summary>
    public static EvaluationContext FromRequest(
        ValidateActionRequest request, string tenantId) => new(
        ContractId:            request.ContractId,
        ActionType:            request.ActionType,
        ActionParameters:      request.ActionParameters,
        DecisionSpaceVersion:  request.DecisionSpaceVersion,
        TenantId:              tenantId,
        SkillId:               request.HasSkillId ? request.SkillId : null,
        ApprovedBudgetInrPaise: request.BudgetContext?.ApprovedMonthlyBudgetInrPaise ?? 0,
        CurrentSpendInrPaise:   request.BudgetContext?.CurrentMonthSpendInrPaise ?? 0,
        ProposedSpendInrPaise:  request.BudgetContext?.ProposedSpendInrPaise ?? 0,
        BudgetSkillType:        request.BudgetContext?.SkillType ?? "");
}
