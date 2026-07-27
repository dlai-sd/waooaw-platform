// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// constitutional_basis: C-041 (Tool Authorization)
using System.Text.Json;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 (Tool Authorization): every MCP tool call must be explicitly authorized
/// in the contract's decision space. Default deny — unlisted tool is always DENY.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private const string McpToolCall = "MCP_TOOL_CALL";

    // ActionParameters JSON keys
    private const string ToolNameKey              = "tool_name";
    private const string AuthorizedToolsKey       = "authorized_tools";
    private const string EscalationToolsKey       = "escalation_required_tools";

    private static readonly JsonSerializerOptions _jsonOpts =
        new JsonSerializerOptions { PropertyNameCaseInsensitive = true };

    /// <inheritdoc />
    public string ClaimId => "C-041";

    /// <inheritdoc />
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-041 applies only to MCP_TOOL_CALL actions; all other types are out of scope.
        if (!string.Equals(ctx.ActionType, McpToolCall, StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                "C-041 does not apply: action type is not MCP_TOOL_CALL."));
        }

        // ── Step 1: extract tool_name ────────────────────────────────────────────
        string? toolName;
        try
        {
            toolName = ctx.GetParameter(ToolNameKey);
        }
        catch (JsonException)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: ActionParameters is malformed JSON — cannot extract tool_name. Default deny."));
        }

        if (string.IsNullOrWhiteSpace(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: tool_name is missing or empty in ActionParameters. Default deny."));
        }

        // ── Step 2: build escalation set ────────────────────────────────────────
        HashSet<string> escalationTools;
        try
        {
            escalationTools = ParseStringSet(ctx.GetParameter(EscalationToolsKey));
        }
        catch (JsonException)
        {
            escalationTools = new HashSet<string>(StringComparer.Ordinal);
        }

        if (escalationTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-041: Tool '{toolName}' requires human escalation before execution."));
        }

        // ── Step 3: build authorized set ────────────────────────────────────────
        HashSet<string> authorizedTools;
        try
        {
            authorizedTools = ParseStringSet(ctx.GetParameter(AuthorizedToolsKey));
        }
        catch (JsonException)
        {
            authorizedTools = new HashSet<string>(StringComparer.Ordinal);
        }

        // ── Step 4: default-deny — unlisted tool is rejected ────────────────────
        if (!authorizedTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-041: Tool '{toolName}' is not listed in the contract's authorized_tools. Default deny."));
        }

        // ── All checks passed ────────────────────────────────────────────────────
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-041: Tool '{toolName}' is authorized by the employment contract."));
    }

    // ── Helpers ─────────────────────────────────────────────────────────────────

    /// <summary>
    /// Deserializes a JSON array string (e.g., <c>["tool-a","tool-b"]</c>) into a
    /// case-sensitive <see cref="HashSet{T}"/>.  Returns an empty set for null, empty,
    /// or whitespace-only input; propagates <see cref="JsonException"/> to the caller
    /// so the evaluator can surface a meaningful denial reason.
    /// </summary>
    private static HashSet<string> ParseStringSet(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
            return new HashSet<string>(StringComparer.Ordinal);

        // Let JsonException propagate — callers wrap this in try/catch.
        var list = JsonSerializer.Deserialize<List<string>>(json, _jsonOpts);
        return list is not null
            ? new HashSet<string>(list, StringComparer.Ordinal)
            : new HashSet<string>(StringComparer.Ordinal);
    }
}