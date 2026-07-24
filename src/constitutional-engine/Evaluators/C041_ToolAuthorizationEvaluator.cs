// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041
// constitutional_basis: C-041 (Tool Authorization — Decision Space boundary)

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-041 — every MCP tool call must be explicitly authorized in the tenant's
/// active employment contract. Default deny: if the tool is not in authorized_actions[], DENY.
/// </summary>
public sealed class C041_ToolAuthorizationEvaluator : IClaimEvaluator
{
    private readonly ILogger<C041_ToolAuthorizationEvaluator> _logger;

    // C-073: C-041 applies only to MCP_TOOL_CALL actions
    private static readonly IReadOnlySet<string> _applicableTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "MCP_TOOL_CALL" };

    public string ClaimId => "C-041";
    public IReadOnlySet<string> ApplicableActionTypes => _applicableTypes;

    public C041_ToolAuthorizationEvaluator(ILogger<C041_ToolAuthorizationEvaluator> logger)
    {
        _logger = logger;
    }

    /// <summary>
    /// C-073: Evaluates C-041 Tool Authorization.
    /// DENY if: no active contract, tool name missing, or tool not in authorized_actions[].
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-041: No active contract → default deny
        if (ctx.ContractAuthorizedActions is null)
        {
            _logger.LogWarning(
                "C-041 DENY: No active employment contract for tenant {TenantId}, agent {AgentId}",
                ctx.TenantId, ctx.AgentId);

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: "No active employment contract found for tenant. All tool calls require an authorized contract (C-041).",
                EvidenceHint: $"TenantId={ctx.TenantId} AgentId={ctx.AgentId}"));
        }

        // C-041: Tool name must be present for MCP_TOOL_CALL
        if (string.IsNullOrWhiteSpace(ctx.ToolName))
        {
            _logger.LogWarning(
                "C-041 DENY: MCP_TOOL_CALL with no tool name for tenant {TenantId}, agent {AgentId}",
                ctx.TenantId, ctx.AgentId);

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: "MCP_TOOL_CALL action requires a non-empty tool name (C-041).",
                EvidenceHint: $"TenantId={ctx.TenantId} AgentId={ctx.AgentId}"));
        }

        // C-041: Tool must be in the contract's authorized_actions[]
        var isAuthorized = ctx.ContractAuthorizedActions.Contains(
            ctx.ToolName, StringComparer.OrdinalIgnoreCase);

        if (!isAuthorized)
        {
            _logger.LogWarning(
                "C-041 DENY: Tool {ToolName} not in authorized_actions for tenant {TenantId}",
                ctx.ToolName, ctx.TenantId);

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"Tool '{ctx.ToolName}' is not in the tenant's authorized_actions list (C-041). Default deny applies.",
                EvidenceHint: $"TenantId={ctx.TenantId} ToolName={ctx.ToolName}"));
        }

        _logger.LogDebug(
            "C-041 AUTHORIZED: Tool {ToolName} is authorized for tenant {TenantId}",
            ctx.ToolName, ctx.TenantId);

        return Task.FromResult(new EvaluationResult(EvaluationDecision.Authorized));
    }
}