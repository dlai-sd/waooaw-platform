// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// Constitutional basis: C-041 (Tool Authorization), C-059 (Traceability)

using System.Text.Json;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041: every MCP tool call must be explicitly authorized in the contract's
/// decision space. Default deny — unlisted tool names are always rejected.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private const string McpToolCall        = "MCP_TOOL_CALL";
    private const string ToolNameKey        = "tool_name";
    private const string AuthorizedToolsKey = "authorized_tools";
    private const string EscalationToolsKey = "escalation_required_tools";

    private static readonly JsonSerializerOptions _jsonOpts =
        new JsonSerializerOptions { PropertyNameCaseInsensitive = false };

    /// <inheritdoc/>
    public string ClaimId => "C-041";

    /// <inheritdoc/>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-041 governs MCP_TOOL_CALL actions only; all other action types pass through.
        if (!string.Equals(ctx.ActionType, McpToolCall, StringComparison.Ordinal))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Allow,
                "Action type is not MCP_TOOL_CALL; C-041 does not apply."));
        }

        // Require a non-empty tool_name in ActionParameters.
        var toolName = ctx.GetParameter(ToolNameKey);
        if (string.IsNullOrEmpty(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Deny,
                "C-041: tool_name is missing or empty in ActionParameters; default deny."));
        }

        // Parse authorized and escalation tool lists from ActionParameters.
        var authorizedJson  = ctx.GetParameter(AuthorizedToolsKey);
        var escalationJson  = ctx.GetParameter(EscalationToolsKey);

        var authorizedTools = ParseStringSet(authorizedJson);
        var escalationTools = ParseStringSet(escalationJson);

        // No authorized tools defined → default deny (C-041: allowlist must be explicit).
        if (authorizedTools is null || authorizedTools.Count == 0)
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Deny,
                "C-041: authorized_tools list is absent or empty for this contract; default deny."));
        }

        // Escalation check takes priority over authorization — escalation_required_tools wins.
        if (escalationTools is not null && escalationTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Escalate,
                $"C-041: Tool '{toolName}' requires human escalation before execution."));
        }

        // Tool is in the explicit allow-list.
        if (authorizedTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Allow,
                $"C-041: Tool '{toolName}' is present in the contract's authorized_tools list."));
        }

        // Default deny — tool is not in the authorized list.
        return Task.FromResult(new EvaluationResult(
            "C-041",
            EvaluationVerdict.Deny,
            $"C-041: Tool '{toolName}' is not in the authorized_tools list; default deny."));
    }

    /// <summary>
    /// Deserializes a JSON array string (e.g. <c>["tool_a","tool_b"]</c>) into a
    /// case-sensitive <see cref="HashSet{T}"/>. Returns <c>null</c> on null/whitespace
    /// input or malformed JSON so callers can treat both cases as "not configured".
    /// </summary>
    private static HashSet<string>? ParseStringSet(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
            return null;

        try
        {
            var list = JsonSerializer.Deserialize<List<string>>(json, _jsonOpts);
            return list is null ? null : new HashSet<string>(list, StringComparer.Ordinal);
        }
        catch (JsonException)
        {
            // Malformed JSON → treat as unconfigured; callers will default-deny.
            return null;
        }
    }
}