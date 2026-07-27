// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// Constitutional basis: C-041 (Tool Authorization)

using System.Text.Json;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 (Tool Authorization): every MCP_TOOL_CALL must name a tool that is explicitly
/// listed in the tenant's active employment-contract authorized_actions[].
/// Default-deny: an absent, empty, or unlisted tool name is DENIED immediately.
/// Non-MCP_TOOL_CALL action types are passed through (Allow) because C-041 scopes only to tool calls.
/// authorized_tools is a JSON string-array pre-populated into ActionParameters by
/// EvaluationContext.FromRequest from business.employment_contracts — no DB I/O in this evaluator.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private const string McpToolCall = "MCP_TOOL_CALL";
    private static readonly JsonSerializerOptions _jsonOpts =
        new() { PropertyNameCaseInsensitive = true };

    /// <inheritdoc />
    public string ClaimId => "C-041";

    /// <inheritdoc />
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-041 applies only to MCP tool calls — all other action types are out of scope.
        if (!string.Equals(ctx.ActionType, McpToolCall, StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                "C-041: action type is not MCP_TOOL_CALL — evaluator not applicable."));
        }

        // ── Guard: tool_name must be present and non-empty ────────────────────────────
        var toolName = ctx.GetParameter("tool_name");
        if (string.IsNullOrWhiteSpace(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: tool_name parameter is absent or empty — default deny."));
        }

        // ── Guard: authorized_tools JSON array must be present ────────────────────────
        // This value is serialised into ActionParameters by EvaluationContext.FromRequest,
        // which reads authorized_actions[] from business.employment_contracts for ContractId.
        var authorizedToolsJson = ctx.GetParameter("authorized_tools");
        if (string.IsNullOrWhiteSpace(authorizedToolsJson))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-041: no authorized_tools list found for contract '{ctx.ContractId}' — default deny."));
        }

        // ── Deserialise ───────────────────────────────────────────────────────────────
        HashSet<string>? authorizedTools;
        try
        {
            authorizedTools = JsonSerializer.Deserialize<HashSet<string>>(
                authorizedToolsJson, _jsonOpts);
        }
        catch (JsonException ex)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-041: authorized_tools JSON is malformed for contract '{ctx.ContractId}' ({ex.Message}) — default deny."));
        }

        // ── Guard: list must be non-null and non-empty ────────────────────────────────
        if (authorizedTools is null || authorizedTools.Count == 0)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-041: authorized_tools list is empty for contract '{ctx.ContractId}' — default deny."));
        }

        // ── Core decision: tool must appear in the contract allow-list ────────────────
        if (!authorizedTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-041: tool '{toolName}' is not in the authorized_actions list for contract '{ctx.ContractId}' — default deny."));
        }

        // ── Tool is explicitly authorized ─────────────────────────────────────────────
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-041: tool '{toolName}' is authorized under contract '{ctx.ContractId}'."));
    }
}