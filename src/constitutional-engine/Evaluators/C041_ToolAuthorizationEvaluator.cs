// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First), ADR-001 (gRPC)

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-041 Evaluator — Tool Authorization (Decision Space boundary).
/// Every MCP tool call requires CE.ValidateAction. Default deny for unknown tools.
/// </summary>
/// <remarks>
/// C-073: Enforces C-041 at runtime — checks tenant's active employment contract
/// authorized_actions[] array. If tool is not listed → DENY.
/// If no active contract exists → DENY (default deny principle).
/// </remarks>
public sealed class C041_ToolAuthorizationEvaluator : IClaimEvaluator
{
    private static readonly IReadOnlySet<string> _applicableTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "MCP_TOOL_CALL" };

    private readonly ILogger<C041_ToolAuthorizationEvaluator> _logger;

    public C041_ToolAuthorizationEvaluator(ILogger<C041_ToolAuthorizationEvaluator> logger)
    {
        _logger = logger;
    }

    /// <inheritdoc/>
    public string ClaimId => "C-041";

    /// <inheritdoc/>
    public IReadOnlySet<string> ApplicableActionTypes => _applicableTypes;

    /// <inheritdoc/>
    /// <remarks>
    /// C-073: C-041 enforcement — default deny for any tool not in authorized_actions[].
    /// </remarks>
    public async Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(ctx.ToolName))
        {
            // C-073: MCP_TOOL_CALL without a tool name is always denied — malformed request
            _logger.LogWarning(
                "C-041 DENY: MCP_TOOL_CALL with no tool_name. tenant={TenantId} agent={AgentId}",
                ctx.TenantId, ctx.AgentId);

            return new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: "C-041: MCP_TOOL_CALL must specify a tool_name. Default deny.",
                EvidenceHint: "malformed_request:missing_tool_name");
        }

        var authorizedTools = await ctx.Data.GetAuthorizedToolsAsync(ctx.TenantId, ct);

        if (authorizedTools.Count == 0)
        {
            // C-073: No active employment contract → default deny (C-041)
            _logger.LogWarning(
                "C-041 DENY: No active employment contract for tenant={TenantId}. tool={ToolName}",
                ctx.TenantId, ctx.ToolName);

            return new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"C-041: No active employment contract found for tenant '{ctx.TenantId}'. Default deny.",
                EvidenceHint: $"no_active_contract:tenant={ctx.TenantId}");
        }

        if (!authorizedTools.Contains(ctx.ToolName))
        {
            // C-073: Tool not in authorized_actions[] → deny
            _logger.LogWarning(
                "C-041 DENY: Tool not authorized. tenant={TenantId} tool={ToolName} authorized=[{Authorized}]",
                ctx.TenantId, ctx.ToolName, string.Join(",", authorizedTools));

            return new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"C-041: Tool '{ctx.ToolName}' is not in the authorized_actions list for tenant '{ctx.TenantId}'.",
                EvidenceHint: $"unauthorized_tool:{ctx.ToolName}");
        }

        _logger.LogDebug(
            "C-041 AUTHORIZED: tool={ToolName} tenant={TenantId}",
            ctx.ToolName, ctx.TenantId);

        return new EvaluationResult(EvaluationDecision.Authorized);
    }
}