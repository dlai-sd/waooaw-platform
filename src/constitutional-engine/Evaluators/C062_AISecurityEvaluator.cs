// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-041 (Tool Authorization)

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-062 Evaluator — AI Security.
/// Denies calls to tools on the security-prohibited list regardless of employment contract.
/// Evaluated first (highest priority) — security overrides authorization.
/// </summary>
/// <remarks>
/// C-073: Enforces C-062 at runtime — prohibited tools are denied even if they appear
/// in the tenant's authorized_actions[]. Security prohibition is absolute.
/// Applies to MCP_TOOL_CALL only — other action types have no tool-level security list.
/// </remarks>
public sealed class C062_AISecurityEvaluator : IClaimEvaluator
{
    private static readonly IReadOnlySet<string> _applicableTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "MCP_TOOL_CALL" };

    private readonly ILogger<C062_AISecurityEvaluator> _logger;

    public C062_AISecurityEvaluator(ILogger<C062_AISecurityEvaluator> logger)
    {
        _logger = logger;
    }

    /// <inheritdoc/>
    public string ClaimId => "C-062";

    /// <inheritdoc/>
    public IReadOnlySet<string> ApplicableActionTypes => _applicableTypes;

    /// <inheritdoc/>
    /// <remarks>
    /// C-073: C-062 enforcement — security-prohibited tools are always denied.
    /// </remarks>
    public async Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(ctx.ToolName))
        {
            // No tool name — C-041 will handle this; pass through here
            return new EvaluationResult(EvaluationDecision.Authorized);
        }

        var isProhibited = await ctx.Data.IsToolSecurityProhibitedAsync(ctx.ToolName, ct);

        if (isProhibited)
        {
            _logger.LogWarning(
                "C-062 DENY: Tool is on security-prohibited list. tool={ToolName} agent={AgentId} tenant={TenantId}",
                ctx.ToolName, ctx.AgentId, ctx.TenantId);

            return new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"C-062: Tool '{ctx.ToolName}' is on the AI security prohibited list. Access denied regardless of contract authorization.",
                EvidenceHint: $"security_prohibited_tool:{ctx.ToolName}");
        }

        return new EvaluationResult(EvaluationDecision.Authorized);
    }
}