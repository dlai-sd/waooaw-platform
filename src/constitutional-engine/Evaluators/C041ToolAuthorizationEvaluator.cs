// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041
// Constitutional basis: C-041 (Tool Authorization)
using System.Text.Json;
using Waooaw.ConstitutionalEngine.Evaluators;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 (Tool Authorization): every MCP tool call must be explicitly listed in the
/// tenant contract's authorized decision space. Unlisted tool = DENY (default deny principle).
///
/// Authorized tools are pre-populated into ActionParameters as "authorized_tools" (JSON string
/// array) by EvaluationContext.FromRequest when the contract is loaded from the DB. The tool
/// being requested is passed as ActionParameters "tool_name".
///
/// This evaluator performs NO network I/O — all data arrives via EvaluationContext.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private const string McpToolCallAction = "MCP_TOOL_CALL";

    // ── IClaimEvaluator ────────────────────────────────────────────────────────────────────────

    public string ClaimId => "C-041";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-041 applies only to MCP_TOOL_CALL actions. All other action types pass through.
        if (!string.Equals(ctx.ActionType, McpToolCallAction, StringComparison.OrdinalIgnoreCase))
        {
            return Allow("Action type is not MCP_TOOL_CALL — C-041 does not apply.");
        }

        // ── Step 1: ContractId must be present ─────────────────────────────────────────────────
        if (string.IsNullOrWhiteSpace(ctx.ContractId))
        {
            return Deny("C-041: No ContractId present in evaluation context — default deny.");
        }

        // ── Step 2: tool_name must be specified ────────────────────────────────────────────────
        var toolName = ctx.GetParameter("tool_name");
        if (string.IsNullOrWhiteSpace(toolName))
        {
            return Deny(
                "C-041: ActionParameters does not contain 'tool_name' — " +
                "cannot authorise an unnamed tool call (default deny).");
        }

        // ── Step 3: authorized_tools list must exist for this contract ─────────────────────────
        var authorizedToolsJson = ctx.GetParameter("authorized_tools");
        if (string.IsNullOrWhiteSpace(authorizedToolsJson))
        {
            return Deny(
                $"C-041: No 'authorized_tools' list found for contract '{ctx.ContractId}' " +
                $"(tenant '{ctx.TenantId}') — default deny.");
        }

        // ── Step 4: Parse the authorized_tools JSON array ──────────────────────────────────────
        HashSet<string>? authorizedTools;
        try
        {
            authorizedTools = JsonSerializer.Deserialize<HashSet<string>>(
                authorizedToolsJson,
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
        }
        catch (JsonException ex)
        {
            return Deny(
                $"C-041: 'authorized_tools' parameter for contract '{ctx.ContractId}' contains " +
                $"malformed JSON — default deny. Parse error: {ex.Message}");
        }

        if (authorizedTools is null || authorizedTools.Count == 0)
        {
            return Deny(
                $"C-041: Authorized tools list for contract '{ctx.ContractId}' is empty — " +
                "default deny (no tools are authorized under this contract).");
        }

        // ── Step 5: Tool must appear in the authorized list ────────────────────────────────────
        // Case-insensitive comparison: tool names are normalized to lower-case at enrollment time.
        var normalized = toolName.Trim();
        if (!authorizedTools.Contains(normalized) &&
            !authorizedTools.Contains(normalized.ToLowerInvariant()))
        {
            return Deny(
                $"C-041: Tool '{normalized}' is not in the authorized decision space for " +
                $"contract '{ctx.ContractId}' (tenant '{ctx.TenantId}', " +
                $"DecisionSpaceVersion={ctx.DecisionSpaceVersion}) — default deny.");
        }

        // ── All checks passed ──────────────────────────────────────────────────────────────────
        return Allow(
            $"C-041: Tool '{normalized}' is present in the authorized decision space for " +
            $"contract '{ctx.ContractId}'.");
    }

    // ── Helpers ───────────────────────────────────────────────────────────────────────────────

    private Task<EvaluationResult> Allow(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, reason));

    private Task<EvaluationResult> Deny(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));
}