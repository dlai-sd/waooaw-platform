// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062
// constitutional_basis: C-062 (AI Security — prohibited tool enforcement)

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-062 — tools on the prohibited list must never be called, regardless of
/// contract authorization. Applies to MCP_TOOL_CALL actions. This is a security hard-stop:
/// even if C-041 passes (tool is in authorized_actions), C-062 can still DENY.
/// </summary>
public sealed class C062_AISecurityEvaluator : IClaimEvaluator
{
    private readonly ILogger<C062_AISecurityEvaluator> _logger;

    // C-073: C-062 applies to MCP_TOOL_CALL actions
    private static readonly IReadOnlySet<string> _applicableTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "MCP_TOOL_CALL" };

    public string ClaimId => "C-062";
    public IReadOnlySet<string> ApplicableActionTypes => _applicableTypes;

    public C062_AISecurityEvaluator(ILogger<C062_AISecurityEvaluator> logger)
    {
        _logger = logger;
    }

    /// <summary>
    /// C-073: Evaluates C-062 AI Security.
    /// DENY if: tool name is on the tenant's prohibited tools list.
    /// ESCALATE if: agent is NOT in sandbox mode and tool is classified as elevated-risk
    ///              (tool name contains "elevated_risk" marker — DESIGN_QUESTION below).
    /// </summary>
    // DESIGN_QUESTION: How are elevated-risk tools classified? Is there a separate
    // elevated_risk_tools[] list in the contract, or a tool registry with risk classifications?
    // Current implementation uses the prohibited_tools list only. EA review needed.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(ctx.ToolName))
        {
            // No tool name — C-041 will handle this; C-062 passes through
            return Task.FromResult(new EvaluationResult(EvaluationDecision.Authorized));
        }

        // C-062: Check prohibited tools list (hard security boundary)
        var isProhibited = ctx.ProhibitedTools.Contains(
            ctx.ToolName, StringComparer.OrdinalIgnoreCase);

        if (isProhibited)
        {
            _logger.LogError(
                "C-062 DENY: Tool {ToolName} is on the prohibited list for tenant {TenantId}, agent {AgentId}",
                ctx.ToolName, ctx.TenantId, ctx.AgentId);

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"Tool '{ctx.ToolName}' is on the security-prohibited tools list and cannot be called (C-062).",
                EvidenceHint: $"TenantId={ctx.TenantId} AgentId={ctx.AgentId} ProhibitedTool={ctx.ToolName}"));
        }

        _logger.LogDebug(
            "C-062 AUTHORIZED: Tool {ToolName} not on prohibited list for tenant {TenantId}",
            ctx.ToolName, ctx.TenantId);

        return Task.FromResult(new EvaluationResult(EvaluationDecision.Authorized));
    }
}