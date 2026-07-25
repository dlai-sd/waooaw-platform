// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041: Every MCP tool call requires an explicit authorization entry in the
/// tenant's active employment contract. Unlisted tools are DENIED by default.
/// No network I/O is performed — all inputs arrive via <see cref="EvaluationContext"/>.
/// </summary>
// C-073: This class implements constitutional obligation C-041 (Tool Authorization).
//        A missing or unlisted tool MUST produce EvaluationVerdict.Deny (default-deny boundary).
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // ── OpenTelemetry tracer (C-059 Traceability) ─────────────────────────────────────────────
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    /// <inheritdoc/>
    public string ClaimId => "C-041";

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Constitutional obligation — C-041 mandates explicit authorization for every
    //        MCP tool invocation. The evaluator MUST default-deny if authorization is absent.
    /// <inheritdoc/>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("c041.tenant_id", ctx.TenantId);
        activity?.SetTag("c041.contract_id", ctx.ContractId);
        activity?.SetTag("c041.action_type", ctx.ActionType);

        // ── Guard: evaluator applies only to MCP_TOOL_CALL ───────────────────────────────────
        // C-073: C-041 is scoped to MCP tool calls. Other action types pass through unchanged.
        if (!string.Equals(ctx.ActionType, "MCP_TOOL_CALL", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogDebug(
                "C-041 skipped: ActionType={ActionType} is not MCP_TOOL_CALL",
                ctx.ActionType);

            activity?.SetTag("c041.verdict", "Allow");
            activity?.SetTag("c041.skip_reason", "not_mcp_tool_call");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                "C-041 not applicable: action type is not MCP_TOOL_CALL."));
        }

        // ── Gate 1: ContractId must be present ───────────────────────────────────────────────
        // C-073: C-041 default deny — no contract means no authority to call any tool.
        if (string.IsNullOrWhiteSpace(ctx.ContractId))
        {
            _logger.LogWarning(
                "C-041 DENY: TenantId={TenantId} has no active employment contract",
                ctx.TenantId);

            activity?.SetTag("c041.verdict", "Deny");
            activity?.SetTag("c041.deny_reason", "no_contract");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: No active employment contract found for tenant. All MCP tool calls are denied by default."));
        }

        // ── Gate 2: tool_name must be specified ──────────────────────────────────────────────
        var toolName = ctx.GetParameter("tool_name");

        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: tool_name absent in ActionParameters — TenantId={TenantId} ContractId={ContractId}",
                ctx.TenantId,
                ctx.ContractId);

            activity?.SetTag("c041.verdict", "Deny");
            activity?.SetTag("c041.deny_reason", "no_tool_name");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: ActionParameters must include 'tool_name' for MCP_TOOL_CALL. Request denied."));
        }

        activity?.SetTag("c041.tool_name", toolName);

        // ── Gate 3: authorized_tools must be present and parseable ───────────────────────────
        // C-073: C-041 default deny — absence of an allow-list denies everything.
        var authorizedToolsJson = ctx.GetParameter("authorized_tools");

        if (string.IsNullOrWhiteSpace(authorizedToolsJson))
        {
            _logger.LogWarning(
                "C-041 DENY: authorized_tools absent for TenantId={TenantId} ContractId={ContractId} ToolName={ToolName}",
                ctx.TenantId,
                ctx.ContractId,
                toolName);

            activity?.SetTag("c041.verdict", "Deny");
            activity?.SetTag("c041.deny_reason", "no_authorized_tools");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-041: Contract '{ctx.ContractId}' contains no authorized_tools list. Default deny applies to tool '{toolName}'."));
        }

        HashSet<string> authorizedTools;
        try
        {
            var parsed = JsonSerializer.Deserialize<string[]>(authorizedToolsJson);

            authorizedTools = parsed is { Length: > 0 }
                ? new HashSet<string>(parsed, StringComparer.OrdinalIgnoreCase)
                : new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        }
        catch (JsonException ex)
        {
            _logger.LogError(
                ex,
                "C-041 DENY: authorized_tools JSON is malformed — TenantId={TenantId} ContractId={ContractId}",
                ctx.TenantId,
                ctx.ContractId);

            activity?.SetTag("c041.verdict", "Deny");
            activity?.SetTag("c041.deny_reason", "malformed_authorized_tools_json");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: authorized_tools parameter contains invalid JSON. Default deny applies."));
        }

        // ── Gate 4: tool_name must appear in the authorized list ─────────────────────────────
        // C-073: C-041 default deny — explicit listing required; implicit allow is unconstitutional.
        if (!authorizedTools.Contains(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: ToolName={ToolName} not in authorized_tools (count={Count}) — TenantId={TenantId} ContractId={ContractId}",
                toolName,
                authorizedTools.Count,
                ctx.TenantId,
                ctx.ContractId);

            activity?.SetTag("c041.verdict", "Deny");
            activity?.SetTag("c041.deny_reason", "tool_not_in_authorized_list");
            activity?.SetTag("c041.authorized_count", authorizedTools.Count);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-041: Tool '{toolName}' is not explicitly authorized under contract '{ctx.ContractId}'. Default deny."));
        }

        // ── All gates passed — tool is explicitly authorized ─────────────────────────────────
        _logger.LogInformation(
            "C-041 ALLOW: ToolName={ToolName} authorized — TenantId={TenantId} ContractId={ContractId}",
            toolName,
            ctx.TenantId,
            ctx.ContractId);

        activity?.SetTag("c041.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-041: Tool '{toolName}' is explicitly authorized under contract '{ctx.ContractId}'."));
    }
}