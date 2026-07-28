// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// constitutional_basis: C-041 (Tool Authorization), C-059 (Traceability)
using System.Text.Json;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private const string McpToolCall        = "MCP_TOOL_CALL";
    private const string ToolNameKey        = "tool_name";
    private const string AuthorizedToolsKey = "authorized_tools";
    private const string EscalationToolsKey = "escalation_required_tools";

    private static readonly JsonSerializerOptions _jsonOpts =
        new JsonSerializerOptions { PropertyNameCaseInsensitive = false };

    public string ClaimId => "C-041";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // Non-MCP actions are not governed by C-041 — pass through
        if (!string.Equals(ctx.ActionType, McpToolCall, StringComparison.Ordinal))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                "C-041: Action type is not MCP_TOOL_CALL — evaluator does not apply."));
        }

        // Default deny: tool_name must be present and non-empty
        var toolName = ctx.GetParameter(ToolNameKey);
        if (string.IsNullOrEmpty(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: tool_name is missing or empty in ActionParameters — default deny."));
        }

        // Escalation check takes priority over authorization
        var escalationJson  = ctx.GetParameter(EscalationToolsKey);
        var escalationTools = ParseStringSet(escalationJson);
        if (escalationTools != null && escalationTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-041: Tool '{toolName}' requires human escalation before execution."));
        }

        // Authorized tools list must be present and non-empty
        var authorizedJson  = ctx.GetParameter(AuthorizedToolsKey);
        var authorizedTools = ParseStringSet(authorizedJson);
        if (authorizedTools == null || authorizedTools.Count == 0)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: No authorized_tools list found in ActionParameters — default deny."));
        }

        // Allow only if the tool appears (exact, case-sensitive) in the authorized set
        if (authorizedTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                $"C-041: Tool '{toolName}' is present in authorized_tools — permitted."));
        }

        // Default deny: tool is not in the authorized set
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Deny,
            $"C-041: Tool '{toolName}' is not in the authorized_tools list — default deny."));
    }

    private static HashSet<string>? ParseStringSet(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
            return null;

        try
        {
            var list = JsonSerializer.Deserialize<List<string>>(json, _jsonOpts);
            if (list == null)
                return null;

            return new HashSet<string>(list, StringComparer.Ordinal);
        }
        catch (JsonException)
        {
            return null;
        }
    }
}