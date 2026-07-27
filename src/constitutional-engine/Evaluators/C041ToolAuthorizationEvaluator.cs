// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Tool Authorization
// Constitutional basis: C-041 (Tool Authorization)

using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-041: Every MCP tool call requires CE.ValidateAction. Default deny.
/// An action is authorized only when the tool name appears in the contract's
/// authorized_actions list (surfaced in EvaluationContext via GetParameter).
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // ── IClaimEvaluator ───────────────────────────────────────────────────────
    public string ClaimId => "C-041";

    // ── Dependencies ─────────────────────────────────────────────────────────
    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        _logger = logger;
    }

    // ── Core evaluation ───────────────────────────────────────────────────────
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-041 is scoped to MCP tool calls only. All other action types pass
        // this evaluator unconditionally — their own claim evaluators apply.
        if (!string.Equals(ctx.ActionType, "MCP_TOOL_CALL", StringComparison.Ordinal))
        {
            return Allow($"C-041: ActionType '{ctx.ActionType}' is not MCP_TOOL_CALL — evaluator does not apply.");
        }

        // ── Guard: ContractId must be present ─────────────────────────────────
        if (string.IsNullOrWhiteSpace(ctx.ContractId))
        {
            _logger.LogWarning(
                "C-041 DENY: MCP_TOOL_CALL with absent ContractId. TenantId={TenantId}",
                ctx.TenantId);

            return Deny("C-041: MCP_TOOL_CALL rejected — ContractId is absent. Default deny.");
        }

        // ── Guard: tool_name must be provided ─────────────────────────────────
        var toolName = ctx.GetParameter("tool_name");

        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: MCP_TOOL_CALL missing tool_name. ContractId={ContractId} TenantId={TenantId}",
                ctx.ContractId, ctx.TenantId);

            return Deny("C-041: MCP_TOOL_CALL rejected — tool_name parameter is absent. Default deny.");
        }

        // ── Fetch authorized tool list ─────────────────────────────────────────
        // The EvaluationContext is built by EvaluatorRegistry from
        // business.employment_contracts.authorized_actions[], serialised as a
        // JSON array under the "authorized_tools" key. Absence == default deny.
        var authorizedToolsRaw = ctx.GetParameter("authorized_tools");

        if (string.IsNullOrWhiteSpace(authorizedToolsRaw))
        {
            _logger.LogWarning(
                "C-041 DENY: No authorized_tools in context. ContractId={ContractId} Tool={ToolName}",
                ctx.ContractId, toolName);

            return Deny(
                $"C-041: MCP_TOOL_CALL rejected — no authorized tools defined for contract " +
                $"'{ctx.ContractId}'. Default deny.");
        }

        // ── Deserialize authorized tool list ──────────────────────────────────
        IReadOnlyList<string>? authorizedTools;
        try
        {
            authorizedTools = JsonSerializer.Deserialize<List<string>>(authorizedToolsRaw);
        }
        catch (JsonException ex)
        {
            _logger.LogError(
                ex,
                "C-041 DENY: Failed to deserialise authorized_tools. ContractId={ContractId}",
                ctx.ContractId);

            return Deny(
                $"C-041: MCP_TOOL_CALL rejected — authorized_tools list could not be parsed " +
                $"for contract '{ctx.ContractId}'. Default deny.");
        }

        // ── Default deny: empty list == no tools authorized ───────────────────
        if (authorizedTools is null || authorizedTools.Count == 0)
        {
            _logger.LogWarning(
                "C-041 DENY: authorized_tools list is empty. ContractId={ContractId} Tool={ToolName}",
                ctx.ContractId, toolName);

            return Deny(
                $"C-041: MCP_TOOL_CALL rejected — authorized_tools list is empty for contract " +
                $"'{ctx.ContractId}'. Default deny.");
        }

        // ── Authorization check (case-sensitive, exact match) ─────────────────
        if (!authorizedTools.Contains(toolName, StringComparer.Ordinal))
        {
            _logger.LogWarning(
                "C-041 DENY: Tool '{ToolName}' not in authorized list for ContractId={ContractId}",
                toolName, ctx.ContractId);

            return Deny(
                $"C-041: MCP_TOOL_CALL rejected — tool '{toolName}' is not in the " +
                $"authorized_actions list for contract '{ctx.ContractId}'. Default deny.");
        }

        // ── ALLOW ─────────────────────────────────────────────────────────────
        _logger.LogInformation(
            "C-041 ALLOW: Tool '{ToolName}' authorized for ContractId={ContractId}",
            toolName, ctx.ContractId);

        return Allow($"C-041: Tool '{toolName}' is authorized under contract '{ctx.ContractId}'.");
    }

    // ── Result helpers ────────────────────────────────────────────────────────

    private Task<EvaluationResult> Allow(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, reason));

    private Task<EvaluationResult> Deny(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));
}