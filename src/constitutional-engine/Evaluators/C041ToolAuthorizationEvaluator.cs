// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First), C-059 (Traceability)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 (Tool Authorization) — every MCP tool call must be explicitly listed
/// in the tenant's employment contract authorized_actions[]. Default deny applies:
/// a tool not present in the authorized list is DENIED regardless of other context.
/// </summary>
/// <remarks>
/// Action type filter: MCP_TOOL_CALL only.
/// All other action types receive Allow immediately (evaluator not applicable).
///
/// DESIGN_QUESTION: EvaluationContext exposes no DB repository/read mechanism.
/// The spec (§C-041) requires reading authorized_actions[] from
/// business.employment_contracts keyed on ContractId. Current implementation
/// reads "authorized_tools" from ActionParameters, expecting the gRPC caller /
/// orchestrator to have pre-loaded and serialised the contract's authorized_actions
/// into the ValidateActionRequest payload.
/// EA to confirm: should EvaluationContext carry a pre-loaded IReadOnlySet{string}
/// AuthorizedTools, or should a read-only IContractRepository be injected into
/// the evaluator so it can perform its own DB read within the 40 ms budget?
/// </remarks>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // ── OpenTelemetry tracer ───────────────────────────────────────────────
    private static readonly ActivitySource _tracer =
        new("Waooaw.ConstitutionalEngine");

    // ── Well-known ActionParameters keys ──────────────────────────────────
    internal const string ParamToolName       = "tool_name";
    internal const string ParamAuthorizedTools = "authorized_tools";
    internal const string McpToolCallActionType = "MCP_TOOL_CALL";

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // ── IClaimEvaluator ───────────────────────────────────────────────────

    // C-073: ClaimId identifies the constitutional obligation this evaluator enforces.
    public string ClaimId => "C-041";

    // C-073: EvaluateAsync enforces C-041 Tool Authorization — default deny for any
    //        MCP tool call whose tool_name is absent from the contract's authorized_tools list.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("claim_id",     ClaimId);
        activity?.SetTag("action_type",  ctx.ActionType);
        activity?.SetTag("tenant_id",    ctx.TenantId);
        activity?.SetTag("contract_id",  ctx.ContractId);

        var result = Evaluate(ctx, activity);
        activity?.SetTag("verdict", result.Verdict.ToString());
        return Task.FromResult(result);
    }

    // ── Private evaluation logic (sync — no I/O) ──────────────────────────

    private EvaluationResult Evaluate(EvaluationContext ctx, Activity? activity)
    {
        // ── Guard: only applicable to MCP_TOOL_CALL ──────────────────────
        if (!string.Equals(ctx.ActionType, McpToolCallActionType,
                           StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogInformation(
                "C041 not applicable. ActionType={ActionType} TenantId={TenantId}",
                ctx.ActionType, ctx.TenantId);

            return Allow($"C-041 evaluator does not apply to action type '{ctx.ActionType}'.");
        }

        // ── Extract tool_name ─────────────────────────────────────────────
        var toolName = ctx.GetParameter(ParamToolName);

        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C041 DENY: MCP_TOOL_CALL missing '{Param}'. TenantId={TenantId} ContractId={ContractId}",
                ParamToolName, ctx.TenantId, ctx.ContractId);
            activity?.SetTag("deny_reason", "missing_tool_name");

            return Deny(
                $"C-041: MCP_TOOL_CALL must supply '{ParamToolName}' parameter. Default deny.");
        }

        activity?.SetTag("tool_name", toolName);

        // ── Extract authorized_tools JSON array ───────────────────────────
        var authorizedToolsJson = ctx.GetParameter(ParamAuthorizedTools);

        if (string.IsNullOrWhiteSpace(authorizedToolsJson))
        {
            _logger.LogWarning(
                "C041 DENY: No '{Param}' found for ContractId={ContractId} TenantId={TenantId}. Default deny.",
                ParamAuthorizedTools, ctx.ContractId, ctx.TenantId);
            activity?.SetTag("deny_reason", "no_authorized_tools_list");

            return Deny(
                $"C-041: No authorized tool list found for contract '{ctx.ContractId}'. Default deny.");
        }

        // ── Deserialize authorized tools ──────────────────────────────────
        IReadOnlyList<string> authorizedTools;
        try
        {
            authorizedTools = JsonSerializer.Deserialize<List<string>>(authorizedToolsJson)
                              ?? [];
        }
        catch (JsonException ex)
        {
            _logger.LogError(
                ex,
                "C041 DENY: Malformed '{Param}' JSON for ContractId={ContractId} TenantId={TenantId}.",
                ParamAuthorizedTools, ctx.ContractId, ctx.TenantId);
            activity?.SetTag("deny_reason", "malformed_authorized_tools_json");

            return Deny(
                $"C-041: '{ParamAuthorizedTools}' parameter is malformed JSON. Default deny.");
        }

        // ── Default-deny: tool must be explicitly listed ──────────────────
        var authorized = authorizedTools.Any(t =>
            string.Equals(t, toolName, StringComparison.OrdinalIgnoreCase));

        if (!authorized)
        {
            _logger.LogWarning(
                "C041 DENY: Tool='{ToolName}' not in authorized list for ContractId={ContractId} TenantId={TenantId}.",
                toolName, ctx.ContractId, ctx.TenantId);
            activity?.SetTag("deny_reason", "tool_not_in_authorized_list");

            return Deny(
                $"C-041: Tool '{toolName}' is not authorized under contract '{ctx.ContractId}'. Default deny.");
        }

        // ── Allow ─────────────────────────────────────────────────────────
        _logger.LogInformation(
            "C041 ALLOW: Tool='{ToolName}' authorized. ContractId={ContractId} TenantId={TenantId}.",
            toolName, ctx.ContractId, ctx.TenantId);

        return Allow($"C-041: Tool '{toolName}' is authorized under contract '{ctx.ContractId}'.");
    }

    // ── Result factories ──────────────────────────────────────────────────

    private EvaluationResult Allow(string reason) =>
        new(ClaimId, EvaluationVerdict.Allow, reason);

    private EvaluationResult Deny(string reason) =>
        new(ClaimId, EvaluationVerdict.Deny, reason);
}