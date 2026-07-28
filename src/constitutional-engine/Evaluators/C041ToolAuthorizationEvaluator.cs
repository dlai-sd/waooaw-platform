// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// constitutional_basis: C-041 (Tool Authorization), C-059 (Traceability)
using System.Text.Json;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 Tool Authorization: every MCP tool call must be explicitly listed
/// in the contract's authorized_tools. Default deny — unlisted tool = DENY.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private const string McpToolCall        = "MCP_TOOL_CALL";
    private const string ToolNameKey        = "tool_name";
    private const string AuthorizedToolsKey = "authorized_tools";
    private const string EscalationToolsKey = "escalation_required_tools";

    private static readonly JsonSerializerOptions _jsonOpts =
        new() { PropertyNameCaseInsensitive = false };

    public string ClaimId => "C-041";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // Non-MCP actions are outside the scope of this evaluator — pass through.
        if (!string.Equals(ctx.ActionType, McpToolCall, StringComparison.Ordinal))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                "C-041: Action type is not MCP_TOOL_CALL — evaluator not applicable."));
        }

        // ── Step 1: extract tool_name from JSON-encoded ActionParameters ──────────
        var toolName = ctx.GetParameter(ToolNameKey);
        if (string.IsNullOrWhiteSpace(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: MCP tool call denied — tool_name is missing or empty in ActionParameters."));
        }

        // ── Step 2: load the authorized_tools list ────────────────────────────────
        var authorizedTools = ParseStringSet(ctx.GetParameter(AuthorizedToolsKey));
        if (authorizedTools is null || authorizedTools.Count == 0)
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-041: MCP tool call denied — no authorized_tools list configured " +
                $"(tool='{toolName}')."));
        }

        // ── Step 3: check escalation_required_tools (takes priority over allow) ──
        var escalationTools = ParseStringSet(ctx.GetParameter(EscalationToolsKey));
        if (escalationTools is not null && escalationTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-041: MCP tool call '{toolName}' requires human escalation — " +
                $"listed in escalation_required_tools."));
        }

        // ── Step 4: authorize if explicitly listed ────────────────────────────────
        if (authorizedTools.Contains(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                $"C-041: MCP tool call '{toolName}' is authorized."));
        }

        // ── Step 5: default deny — unlisted tool ─────────────────────────────────
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Deny,
            $"C-041: MCP tool call denied — '{toolName}' is not in the authorized_tools list."));
    }

    /// <summary>
    /// Parses a JSON array of strings into a case-sensitive HashSet.
    /// Returns null on null/empty input or any JSON parse error.
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
            return null;
        }
    }
}