// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// constitutional_basis: C-041 (Tool Authorization)
using System.Text.Json;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 (Tool Authorization): every MCP tool call must be in the contract's
/// authorized_actions list. Default deny — unlisted tool = DENY.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private const string McpToolCall        = "MCP_TOOL_CALL";
    private const string ToolNameKey        = "tool_name";
    private const string AuthorizedToolsKey = "authorized_tools";
    private const string EscalationToolsKey = "escalation_required_tools";

    private static readonly JsonSerializerOptions _jsonOpts =
        new(JsonSerializerDefaults.Web);

    public string ClaimId => "C-041";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-041 only governs MCP_TOOL_CALL actions; all other action types pass through.
        if (!string.Equals(ctx.ActionType, McpToolCall, StringComparison.Ordinal))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Allow,
                "C-041 does not apply: action type is not MCP_TOOL_CALL."));
        }

        // ── 1. Extract tool_name ─────────────────────────────────────────────────
        var toolName = ctx.GetParameter(ToolNameKey);
        if (string.IsNullOrEmpty(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Deny,
                "C-041: tool_name is missing or empty in ActionParameters; default deny."));
        }

        // ── 2. Extract authorized_tools list ────────────────────────────────────
        var authorizedToolsJson = ctx.GetParameter(AuthorizedToolsKey);
        var authorizedTools = ParseStringSet(authorizedToolsJson);

        if (authorizedTools.Count == 0)
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Deny,
                $"C-041: No authorized_tools list found for contract '{ctx.ContractId}'; default deny."));
        }

        // ── 3. Escalation check (takes priority over plain authorization) ────────
        var escalationToolsJson = ctx.GetParameter(EscalationToolsKey);
        var escalationTools     = ParseStringSet(escalationToolsJson);

        if (escalationTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Escalate,
                $"C-041: Tool '{toolName}' requires human escalation before execution."));
        }

        // ── 4. Authorization check ───────────────────────────────────────────────
        if (authorizedTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Allow,
                $"C-041: Tool '{toolName}' is authorized for contract '{ctx.ContractId}'."));
        }

        // ── 5. Default deny ──────────────────────────────────────────────────────
        return Task.FromResult(new EvaluationResult(
            "C-041",
            EvaluationVerdict.Deny,
            $"C-041: Tool '{toolName}' is not in the authorized_tools list for contract '{ctx.ContractId}'; default deny."));
    }

    /// <summary>
    /// Deserializes a JSON string array into a case-sensitive HashSet.
    /// Returns an empty set on null, empty, or malformed input — never throws.
    /// </summary>
    private static HashSet<string> ParseStringSet(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
            return new HashSet<string>(StringComparer.Ordinal);

        try
        {
            var items = JsonSerializer.Deserialize<string[]>(json, _jsonOpts);
            if (items is null)
                return new HashSet<string>(StringComparer.Ordinal);

            return new HashSet<string>(items, StringComparer.Ordinal);
        }
        catch (JsonException)
        {
            // Malformed JSON → treat as empty list → default deny path applies.
            return new HashSet<string>(StringComparer.Ordinal);
        }
    }
}