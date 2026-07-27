// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// Constitutional basis: C-041 (Tool Authorization)

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041: every MCP tool call requires a valid, active employment contract.
/// Default deny — unlisted tool or missing contract = DENY.
/// Full authorized_actions[] DB validation is phased in at WC012-03 (Data layer sprint).
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private const string McpToolCall = "MCP_TOOL_CALL";

    /// <inheritdoc/>
    public string ClaimId => "C-041";

    /// <inheritdoc/>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-041 applies only to MCP tool calls — pass non-MCP actions straight through.
        if (!string.Equals(ctx.ActionType, McpToolCall, StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                "C-041: Action type is not MCP_TOOL_CALL; evaluator does not apply."));
        }

        // Default deny: a valid employment contract must be present.
        if (string.IsNullOrWhiteSpace(ctx.ContractId))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: No active employment contract found for tenant. MCP tool call denied (default deny)."));
        }

        // Default deny: tool_name must be supplied in ActionParameters (JSON-encoded).
        var toolName = ctx.GetParameter("tool_name");
        if (string.IsNullOrWhiteSpace(toolName))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: ActionParameters did not supply 'tool_name'. MCP tool call denied (default deny)."));
        }

        // Contract present and tool name specified — allow.
        // Authorized_actions[] membership check is enforced in WC012-03 (Data layer).
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-041: Tool '{toolName}' authorized under contract '{ctx.ContractId}'."));
    }
}