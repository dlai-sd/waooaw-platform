// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using Microsoft.Extensions.Logging;
using System.Diagnostics;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-041 (Tool Authorization) — every MCP tool call requires an active
/// employment contract. Default deny: unlisted tool or absent contract → DENY.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource for OpenTelemetry tracing of constitutional evaluation
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Identifies this evaluator as the runtime enforcer of constitutional claim C-041
    public string ClaimId => "C-041";

    /// <summary>
    /// C-073: Evaluate tool authorization per C-041.
    /// Decision rules (in order — short-circuit on first DENY):
    ///   1. ContractId must be non-empty — no contract = no authorization (default deny).
    ///   2. tool_name parameter must be present in ActionParameters (JSON-encoded).
    ///   3. action_type must be MCP_TOOL_CALL — other action types are outside C-041 scope.
    ///   4. All conditions satisfied → Allow.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Start trace span for constitutional evaluation
        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("constitutional.claim", ClaimId);
        activity?.SetTag("tenant.id", ctx.TenantId);
        activity?.SetTag("contract.id", ctx.ContractId);
        activity?.SetTag("action.type", ctx.ActionType);

        // C-041: Non-MCP_TOOL_CALL actions are outside this evaluator's scope → Allow
        // Other evaluators (C-043, C-048, C-062) cover remaining action types.
        if (!string.Equals(ctx.ActionType, "MCP_TOOL_CALL", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogInformation(
                "C041 ALLOW: ActionType={ActionType} is not MCP_TOOL_CALL — outside C-041 scope for Tenant={TenantId}",
                ctx.ActionType, ctx.TenantId);

            activity?.SetTag("constitutional.verdict", "Allow");
            activity?.SetTag("constitutional.reason", "non-mcp-action-type");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                $"Action type '{ctx.ActionType}' is not subject to C-041 MCP tool authorization."));
        }

        // C-041: Default deny — no active employment contract = no authorization for any tool
        if (string.IsNullOrWhiteSpace(ctx.ContractId))
        {
            _logger.LogWarning(
                "C041 DENY: No active employment contract for Tenant={TenantId} ActionType={ActionType}",
                ctx.TenantId, ctx.ActionType);

            activity?.SetTag("constitutional.verdict", "Deny");
            activity?.SetTag("constitutional.reason", "no-active-contract");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041 default deny: no active employment contract found for tenant. " +
                "MCP tool calls require an authorized contract."));
        }

        // C-041: tool_name must be present — unidentified tools are denied by default
        // ActionParameters is JSON-encoded; use GetParameter() per stack rules.
        var toolName = ctx.GetParameter("tool_name");
        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C041 DENY: tool_name not specified in ActionParameters for Tenant={TenantId} ContractId={ContractId}",
                ctx.TenantId, ctx.ContractId);

            activity?.SetTag("constitutional.verdict", "Deny");
            activity?.SetTag("constitutional.reason", "missing-tool-name");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041 default deny: 'tool_name' parameter is required for MCP_TOOL_CALL actions " +
                "but was absent or empty in ActionParameters."));
        }

        activity?.SetTag("tool.name", toolName);

        // DESIGN_QUESTION: The spec references reading authorized_actions[] from
        // business.employment_contracts, but IClaimEvaluator forbids network/DB I/O and
        // EvaluationContext carries no authorized-actions list. If the authorized_actions
        // whitelist check is required at this layer, EvaluationContext must be extended with
        // IReadOnlySet<string> AuthorizedToolNames populated by EvaluationContext.FromRequest().
        // Current implementation: presence of ContractId + named tool_name satisfies C-041
        // boundary check. EA review required before WC012-03 to confirm whether the whitelist
        // check belongs here or in the context factory.

        // C-041: Contract present + tool named → authorized under current contract scope
        _logger.LogInformation(
            "C041 ALLOW: Tool={ToolName} authorized under ContractId={ContractId} for Tenant={TenantId}",
            toolName, ctx.ContractId, ctx.TenantId);

        activity?.SetTag("constitutional.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"Tool '{toolName}' is authorized under active contract '{ctx.ContractId}' (C-041)."));
    }
}