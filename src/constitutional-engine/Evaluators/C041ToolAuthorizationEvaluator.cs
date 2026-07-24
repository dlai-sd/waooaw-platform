// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization — Decision Space boundary)

#nullable enable

using Microsoft.Extensions.Logging;
using System.Diagnostics;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-041 — every MCP tool call must be in the tenant's authorized
/// tool set. Default DENY for unknown or unlisted tools.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // DESIGN_QUESTION: Full authorized MCP tool list should come from a configuration
    // source (e.g., IOptions<ToolAuthorizationOptions>) once employment contracts table
    // exists (WC012-03). For now, a conservative allow-list is hardcoded.
    internal static readonly IReadOnlySet<string> KnownAuthorizedTools = new HashSet<string>(
        StringComparer.OrdinalIgnoreCase)
    {
        "web_search",
        "read_file",
        "write_file",
        "list_directory",
        "code_interpreter",
        "calculator",
        "send_message",
        "calendar_read",
        "calendar_write",
        "email_read",
        "email_send"
    };

    public string ClaimId => "C-041";

    // C-041 applies only to MCP tool calls
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "MCP_TOOL_CALL" };

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>
    /// C-073: Deny any MCP_TOOL_CALL whose tool_name is not in the authorized set.
    /// Default-deny principle: absence of explicit authorization = DENY.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C041ToolAuthorizationEvaluator.Evaluate");
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("tool_name", ctx.ToolName);
        activity?.SetTag("claim_id", ClaimId);

        if (string.IsNullOrWhiteSpace(ctx.ToolName))
        {
            _logger.LogWarning(
                "C-041 DENY: empty tool_name for tenant={TenantId} agent={AgentId}",
                ctx.TenantId, ctx.AgentId);

            activity?.SetTag("decision", "DENY");
            activity?.SetTag("deny_reason", "empty_tool_name");

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: "C-041: tool_name is empty — no tool may be invoked without explicit identification.",
                EvidenceHint: "tool_name was null or whitespace"));
        }

        if (!KnownAuthorizedTools.Contains(ctx.ToolName))
        {
            _logger.LogWarning(
                "C-041 DENY: unauthorized tool={ToolName} tenant={TenantId} agent={AgentId}",
                ctx.ToolName, ctx.TenantId, ctx.AgentId);

            activity?.SetTag("decision", "DENY");
            activity?.SetTag("deny_reason", "tool_not_authorized");

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"C-041: tool '{ctx.ToolName}' is not in the authorized tool set for this tenant. Default deny.",
                EvidenceHint: $"tool_name={ctx.ToolName}"));
        }

        _logger.LogInformation(
            "C-041 AUTHORIZED: tool={ToolName} tenant={TenantId}",
            ctx.ToolName, ctx.TenantId);

        activity?.SetTag("decision", "AUTHORIZED");
        return Task.FromResult(new EvaluationResult(EvaluationDecision.Authorized));
    }
}