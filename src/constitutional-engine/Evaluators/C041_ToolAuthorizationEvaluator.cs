// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041
// constitutional_basis: C-041 (Tool Authorization — Decision Space boundary)

#nullable enable

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-041 Evaluator — Tool Authorization (Decision Space boundary).
/// Every MCP tool call requires CE.ValidateAction. Default deny for unknown tools.
/// </summary>
/// <remarks>
/// C-073: Enforces C-041 at runtime — every MCP_TOOL_CALL must be in the tenant's
/// authorized_actions list from their active employment contract. Default deny.
/// </remarks>
public sealed class C041_ToolAuthorizationEvaluator : IClaimEvaluator
{
    private readonly ILogger<C041_ToolAuthorizationEvaluator> _logger;

    // C-073: Action type scope — only MCP_TOOL_CALL triggers this evaluator
    public string ClaimId => "C-041";
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "MCP_TOOL_CALL" };

    public C041_ToolAuthorizationEvaluator(ILogger<C041_ToolAuthorizationEvaluator> logger)
    {
        _logger = logger;
    }

    /// <inheritdoc/>
    /// <remarks>
    /// C-073: C-041 enforcement — default deny if tool not in authorized set.
    /// AuthorizedTools is pre-loaded from business.employment_contracts by the
    /// ValidateAction handler before evaluators are invoked.
    /// </remarks>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-041: Default deny — if no authorized tools loaded, deny all
        if (ctx.AuthorizedTools is null || ctx.AuthorizedTools.Count == 0)
        {
            _logger.LogWarning(
                "C-041 DENY: TenantId={TenantId} AgentId={AgentId} ToolName={ToolName} — " +
                "no authorized tools found for tenant (default deny)",
                ctx.TenantId, ctx.AgentId, ctx.ToolName);

            return Task.FromResult(new EvaluationResult(
                Decision: EvaluationDecision.Deny,
                Reason: $"C-041: Tool '{ctx.ToolName}' is not authorized. " +
                        "No authorized tools found for tenant. Default deny.",
                EvidenceHint: "employment_contract_missing_or_empty"
            ));
        }

        var toolName = ctx.ToolName ?? string.Empty;

        // C-041: Check if tool is in the authorized set
        if (!ctx.AuthorizedTools.Contains(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: TenantId={TenantId} AgentId={AgentId} ToolName={ToolName} — " +
                "tool not in authorized set (count={AuthorizedCount})",
                ctx.TenantId, ctx.AgentId, toolName, ctx.AuthorizedTools.Count);

            return Task.FromResult(new EvaluationResult(
                Decision: EvaluationDecision.Deny,
                Reason: $"C-041: Tool '{toolName}' is not in the tenant's authorized tool list.",
                EvidenceHint: $"authorized_tools_count={ctx.AuthorizedTools.Count}"
            ));
        }

        _logger.LogDebug(
            "C-041 AUTHORIZED: TenantId={TenantId} AgentId={AgentId} ToolName={ToolName}",
            ctx.TenantId, ctx.AgentId, toolName);

        return Task.FromResult(new EvaluationResult(EvaluationDecision.Authorized));
    }
}