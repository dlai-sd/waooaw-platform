// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// Constitutional basis: C-041 (Tool Authorization)
using System.Text.Json;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 (Tool Authorization): every MCP_TOOL_CALL must name a tool that
/// appears in the contract's authorized_tools list.  Default-deny — an unlisted tool
/// is ALWAYS denied without further evaluation.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private const string McpToolCall        = "MCP_TOOL_CALL";
    private const string ToolNameKey        = "tool_name";
    private const string AuthorizedToolsKey = "authorized_tools";
    private const string EscalationToolsKey = "escalation_required_tools";

    private static readonly JsonSerializerOptions _jsonOpts =
        new JsonSerializerOptions { PropertyNameCaseInsensitive = false };

    // ── IClaimEvaluator ──────────────────────────────────────────────────────

    public string ClaimId => "C-041";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-041 only applies to MCP_TOOL_CALL; all other action types pass through.
        if (!string.Equals(ctx.ActionType, McpToolCall, StringComparison.Ordinal))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Allow,
                $"Action type '{ctx.ActionType}' is not MCP_TOOL_CALL; C-041 does not apply."));
        }

        // ── 1. Require a non-empty tool_name ────────────────────────────────
        var toolName = ctx.GetParameter(ToolNameKey);
        if (string.IsNullOrEmpty(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Deny,
                "MCP_TOOL_CALL has a missing or empty tool_name parameter; default deny (C-041)."));
        }

        // ── 2. Require a parseable authorized_tools list ─────────────────────
        var authorizedToolsJson = ctx.GetParameter(AuthorizedToolsKey);
        var authorizedTools = ParseStringSet(authorizedToolsJson);
        if (authorizedTools is null)
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Deny,
                $"Tool '{toolName}' cannot be authorized: authorized_tools list is absent or malformed; default deny (C-041)."));
        }

        // ── 3. Escalation-required check (takes priority over authorization) ─
        var escalationToolsJson = ctx.GetParameter(EscalationToolsKey);
        var escalationTools = ParseStringSet(escalationToolsJson)
                              ?? new HashSet<string>(StringComparer.Ordinal);

        if (escalationTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Escalate,
                $"Tool '{toolName}' is listed under escalation_required_tools and requires human approval before use (C-041)."));
        }

        // ── 4. Authorization check ───────────────────────────────────────────
        if (authorizedTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Allow,
                $"Tool '{toolName}' is in the authorized_tools list for this contract (C-041)."));
        }

        // ── 5. Default deny — unlisted tool ──────────────────────────────────
        return Task.FromResult(new EvaluationResult(
            "C-041",
            EvaluationVerdict.Deny,
            $"Tool '{toolName}' is not present in the authorized_tools list; default deny (C-041)."));
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    /// <summary>
    /// Deserialises a JSON string array into a case-sensitive <see cref="HashSet{T}"/>.
    /// Returns <c>null</c> when <paramref name="json"/> is null/white-space or invalid JSON.
    /// Returns an empty set when the array is syntactically valid but contains no elements.
    /// </summary>
    private static HashSet<string>? ParseStringSet(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
            return null;

        try
        {
            var items = JsonSerializer.Deserialize<string[]>(json, _jsonOpts);
            if (items is null)
                return null;

            return new HashSet<string>(items, StringComparer.Ordinal);
        }
        catch (JsonException)
        {
            return null;
        }
    }
}