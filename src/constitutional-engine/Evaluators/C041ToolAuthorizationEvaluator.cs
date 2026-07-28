// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// Constitutional basis: C-041 (Tool Authorization)

using System.Text.Json;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 (Tool Authorization): every MCP tool call must be explicitly
/// authorised in the tenant's active employment contract decision space.
/// Default deny — an unlisted tool is always DENY.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // ── IClaimEvaluator ────────────────────────────────────────────────────────

    public string ClaimId => "C-041";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // Guard 1 — an active employment contract must be present.
        // ContractId is populated by EvaluationContext.FromRequest when a valid contract
        // exists for the tenant.  Empty ContractId → no active contract → default deny.
        if (string.IsNullOrWhiteSpace(ctx.ContractId))
        {
            return Deny(
                $"No active employment contract found for tenant '{ctx.TenantId}'. " +
                "Default deny per C-041 (Tool Authorization).");
        }

        // Guard 2 — the request must name the tool being called.
        // ActionParameters is JSON-encoded; use GetParameter() — never TryGetValue().
        var toolName = ctx.GetParameter("tool_name");
        if (string.IsNullOrWhiteSpace(toolName))
        {
            return Deny(
                "MCP_TOOL_CALL request is missing the required 'tool_name' parameter. " +
                "Default deny per C-041 (Tool Authorization).");
        }

        // Guard 3 — the contract's authorised tool list must be present in context.
        // The list is pre-loaded from business.employment_contracts by the context factory
        // and encoded as a JSON array under the key 'authorized_tools'.
        var authorizedToolsJson = ctx.GetParameter("authorized_tools");
        if (string.IsNullOrWhiteSpace(authorizedToolsJson))
        {
            return Deny(
                $"Contract '{ctx.ContractId}' carries no 'authorized_tools' decision-space entry. " +
                "Default deny per C-041 (Tool Authorization).");
        }

        // Parse the authorised-tools JSON array.
        // Malformed JSON is treated as an absent list → default deny.
        HashSet<string>? authorizedTools;
        try
        {
            authorizedTools = JsonSerializer.Deserialize<HashSet<string>>(
                authorizedToolsJson,
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
        }
        catch (JsonException ex)
        {
            return Deny(
                $"Malformed 'authorized_tools' JSON on contract '{ctx.ContractId}': {ex.Message}. " +
                "Default deny per C-041 (Tool Authorization).");
        }

        // Guard 4 — the tool must appear in the whitelist (case-sensitive; tool names are
        // canonical identifiers and must match exactly as registered in the decision space).
        if (authorizedTools is null || !authorizedTools.Contains(toolName))
        {
            return Deny(
                $"Tool '{toolName}' is not listed in the authorized_tools for contract " +
                $"'{ctx.ContractId}' (decision-space v{ctx.DecisionSpaceVersion}). " +
                "Default deny per C-041 (Tool Authorization).");
        }

        // All guards passed — tool is explicitly authorised.
        return Allow(
            $"Tool '{toolName}' is authorised under contract '{ctx.ContractId}' " +
            $"(decision-space v{ctx.DecisionSpaceVersion}).");
    }

    // ── Private helpers ────────────────────────────────────────────────────────

    private Task<EvaluationResult> Deny(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));

    private Task<EvaluationResult> Allow(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, reason));
}