// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// constitutional_basis: C-041 (Tool Authorization)
using System.Text.Json;
using Waooaw.ConstitutionalEngine.Evaluators;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-041 Tool Authorization Evaluator.
/// Enforces the Decision Space boundary: every MCP tool call must be explicitly
/// listed in authorized_actions. Default deny — unlisted tool = DENY.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private const string McpToolCall         = "MCP_TOOL_CALL";
    private const string ToolNameKey         = "tool_name";
    private const string AuthorizedToolsKey  = "authorized_tools";
    private const string EscalationToolsKey  = "escalation_required_tools";

    private static readonly JsonSerializerOptions _jsonOpts =
        new(JsonSerializerDefaults.Web) { ReadCommentHandling = JsonCommentHandling.Skip };

    // ── IClaimEvaluator ──────────────────────────────────────────────────────

    public string ClaimId => "C-041";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // Non-MCP action types are out-of-scope for C-041; pass through.
        if (!string.Equals(ctx.ActionType, McpToolCall, StringComparison.Ordinal))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId  : ClaimId,
                Verdict  : EvaluationVerdict.Allow,
                Reason   : "Action type is not MCP_TOOL_CALL — C-041 not applicable."));
        }

        // 1. Extract tool_name from JSON-encoded ActionParameters.
        var toolName = ctx.GetParameter(ToolNameKey);

        if (string.IsNullOrWhiteSpace(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId  : ClaimId,
                Verdict  : EvaluationVerdict.Deny,
                Reason   : "C-041: MCP_TOOL_CALL denied — tool_name is missing or empty in ActionParameters."));
        }

        // 2. Parse escalation_required_tools (checked first — takes priority over authorized).
        var escalationJson  = ctx.GetParameter(EscalationToolsKey);
        var escalationTools = ParseStringSet(escalationJson);

        if (escalationTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId  : ClaimId,
                Verdict  : EvaluationVerdict.Escalate,
                Reason   : $"C-041: Tool '{toolName}' requires human escalation before execution."));
        }

        // 3. Parse authorized_tools.
        var authorizedJson  = ctx.GetParameter(AuthorizedToolsKey);
        var authorizedTools = ParseStringSet(authorizedJson);

        if (authorizedTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId  : ClaimId,
                Verdict  : EvaluationVerdict.Allow,
                Reason   : $"C-041: Tool '{toolName}' is present in the contract's authorized_actions."));
        }

        // 4. Default deny — tool not listed.
        return Task.FromResult(new EvaluationResult(
            ClaimId  : ClaimId,
            Verdict  : EvaluationVerdict.Deny,
            Reason   : $"C-041: Tool '{toolName}' is not listed in authorized_actions — default deny."));
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    /// <summary>
    /// Deserialises a JSON array string (e.g. <c>["tool_a","tool_b"]</c>) into a
    /// case-sensitive <see cref="HashSet{T}"/>. Returns an empty set on any
    /// parse failure, null input, or empty input so callers never have to
    /// guard against null.
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
            // Malformed JSON — treat as empty list → default deny path.
            return new HashSet<string>(StringComparer.Ordinal);
        }
    }
}