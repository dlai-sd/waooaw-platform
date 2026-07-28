// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// Constitutional basis: C-041 (Tool Authorization), C-059 (Traceability)
using System.Text.Json;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 (Tool Authorization): every MCP tool call must be explicitly
/// listed in the contract's authorized_tools parameter. Default deny — an unlisted
/// tool is always DENY. Tools in escalation_required_tools produce ESCALATE instead
/// of ALLOW, routing to human oversight per C-049.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private const string McpToolCall        = "MCP_TOOL_CALL";
    private const string ToolNameKey        = "tool_name";
    private const string AuthorizedToolsKey = "authorized_tools";
    private const string EscalationToolsKey = "escalation_required_tools";

    private static readonly JsonSerializerOptions _jsonOpts =
        new(JsonSerializerDefaults.Web);

    /// <inheritdoc/>
    public string ClaimId => "C-041";

    /// <inheritdoc/>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-041 only governs MCP_TOOL_CALL actions; all other action types pass through.
        if (!string.Equals(ctx.ActionType, McpToolCall, StringComparison.Ordinal))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Allow,
                "Action type is not MCP_TOOL_CALL — C-041 does not apply."));
        }

        // A missing or empty tool_name cannot be authorized — default deny.
        var toolName = ctx.GetParameter(ToolNameKey);
        if (string.IsNullOrWhiteSpace(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Deny,
                "C-041: MCP tool call denied — missing or empty tool_name parameter."));
        }

        // A missing or empty ActionParameters JSON string cannot yield an authorized list — default deny.
        if (string.IsNullOrWhiteSpace(ctx.ActionParameters))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Deny,
                $"C-041: MCP tool call denied — ActionParameters is absent; cannot authorize tool '{toolName}'. Default deny."));
        }

        // Parse the authorized_tools list; absence or malformed JSON → default deny.
        var authorizedJson  = ctx.GetParameter(AuthorizedToolsKey);
        var authorizedTools = ParseStringSet(authorizedJson);
        if (authorizedTools is null || authorizedTools.Count == 0)
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Deny,
                $"C-041: MCP tool call denied — no authorized_tools list found for tool '{toolName}'. Default deny."));
        }

        // Escalation check takes precedence over plain authorization.
        // A tool present in escalation_required_tools must be reviewed by a human
        // before it may execute, even if it also appears in authorized_tools.
        var escalationJson  = ctx.GetParameter(EscalationToolsKey);
        var escalationTools = ParseStringSet(escalationJson);
        if (escalationTools is not null && escalationTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Escalate,
                $"C-041: MCP tool '{toolName}' requires human escalation before execution (escalation_required_tools)."));
        }

        // The tool must appear in authorized_tools — exact case-sensitive match required.
        if (authorizedTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Allow,
                $"C-041: MCP tool '{toolName}' is in the authorized_tools list — permitted."));
        }

        // Default deny: tool is not in the authorized list.
        return Task.FromResult(new EvaluationResult(
            "C-041",
            EvaluationVerdict.Deny,
            $"C-041: MCP tool '{toolName}' is not in the authorized_tools list. Default deny."));
    }

    /// <summary>
    /// Deserializes a JSON string array into a case-sensitive hash set.
    /// Returns <c>null</c> on null/whitespace input or any JSON parse failure.
    /// </summary>
    private static HashSet<string>? ParseStringSet(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
            return null;

        try
        {
            var list = JsonSerializer.Deserialize<List<string>>(json, _jsonOpts);
            if (list is null || list.Count == 0)
                return null;

            return new HashSet<string>(list, StringComparer.Ordinal);
        }
        catch (JsonException)
        {
            // Malformed JSON — treat as absent; caller applies default deny.
            return null;
        }
    }
}