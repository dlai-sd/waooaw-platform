// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041
// constitutional_basis: C-041 (Tool Authorization), C-059 (Traceability), C-073 (Annotated Obligations)

#nullable enable
#pragma warning disable CS1998 // Async method lacks await — intentional, interface requires Task<T>

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041: Every MCP tool call requires CE.ValidateAction. Default deny.
/// A tool not present in the contract's authorized_actions list is denied unconditionally.
/// </summary>
// C-073: This class implements a constitutional obligation (C-041 Tool Authorization).
//         Every code path that reaches a DENY returns EvaluationVerdict.Deny — no silent pass-through.
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: ClaimId links every denial audit record back to the constitutional claim.
    public string ClaimId => "C-041";

    private const string McpToolCallActionType = "MCP_TOOL_CALL";

    // C-073: Tracer provides audit-grade observability for every evaluation decision.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private static readonly JsonSerializerOptions _jsonOptions = new(JsonSerializerDefaults.Web)
    {
        // Case-insensitive deserialization — tool names must match exactly after normalisation.
        PropertyNameCaseInsensitive = false
    };

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        // C-073: Null check ensures logger is always available for constitutional audit trail.
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>
    /// Evaluates whether the requested MCP tool is in the tenant's contract authorized_actions list.
    /// C-041: Default deny — an absent or unlisted tool MUST return EvaluationVerdict.Deny.
    /// </summary>
    // C-073: This method is the runtime enforcement point for C-041 (Tool Authorization).
    public async Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Guard 1: This evaluator only applies to MCP_TOOL_CALL actions ──────────────────────
        // Non-MCP actions are not subject to C-041 tool authorization; pass through to other claims.
        if (!string.Equals(ctx.ActionType, McpToolCallActionType, StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogDebug(
                "C-041 skip: ActionType={ActionType} is not {McpType}. TenantId={TenantId}",
                ctx.ActionType, McpToolCallActionType, ctx.TenantId);

            activity?.SetTag("c041.outcome", "skip_not_mcp");
            return new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                $"Action type '{ctx.ActionType}' is not {McpToolCallActionType} — C-041 not applicable.");
        }

        // ── Guard 2: C-041 default deny — no contract means no authorization ─────────────────
        // An empty ContractId indicates no active employment contract is bound to the request.
        if (string.IsNullOrWhiteSpace(ctx.ContractId))
        {
            _logger.LogWarning(
                "C-041 DENY: No ContractId present. TenantId={TenantId} ActionType={ActionType}",
                ctx.TenantId, ctx.ActionType);

            activity?.SetTag("c041.outcome", "deny_no_contract");
            return new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041 default deny: No active employment contract — MCP tool call not authorized.");
        }

        // ── Guard 3: tool_name must be specified in ActionParameters ─────────────────────────
        // ActionParameters is a JSON-encoded string; use GetParameter() — never TryGetValue().
        var toolName = ctx.GetParameter("tool_name");
        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: tool_name absent from ActionParameters. ContractId={ContractId} TenantId={TenantId}",
                ctx.ContractId, ctx.TenantId);

            activity?.SetTag("c041.outcome", "deny_no_tool_name");
            return new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041 default deny: tool_name not specified in action parameters.");
        }

        activity?.SetTag("tool_name", toolName);

        // ── Guard 4: authorized_tools must be pre-loaded into ActionParameters ───────────────
        // EvaluationContext.FromRequest is responsible for injecting the contract's
        // authorized_actions[] as the JSON array "authorized_tools" in ActionParameters.
        // DESIGN_QUESTION: Should EvaluationContext.FromRequest load authorized_tools from DB,
        //   or should a middleware layer inject them before the evaluator chain runs?
        //   Current assumption: FromRequest embeds them as JSON array in ActionParameters.
        var authorizedToolsJson = ctx.GetParameter("authorized_tools");
        if (string.IsNullOrWhiteSpace(authorizedToolsJson))
        {
            _logger.LogWarning(
                "C-041 DENY: authorized_tools not found in ActionParameters. " +
                "ContractId={ContractId} TenantId={TenantId}",
                ctx.ContractId, ctx.TenantId);

            activity?.SetTag("c041.outcome", "deny_no_authorized_tools_list");
            return new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041 default deny: No authorized_tools list found for contract — tool call denied.");
        }

        // ── Parse JSON authorized tools list ─────────────────────────────────────────────────
        HashSet<string>? authorizedTools;
        try
        {
            authorizedTools = JsonSerializer.Deserialize<HashSet<string>>(
                authorizedToolsJson,
                _jsonOptions);
        }
        catch (JsonException ex)
        {
            _logger.LogError(ex,
                "C-041 DENY: Failed to parse authorized_tools JSON. " +
                "ContractId={ContractId} TenantId={TenantId}",
                ctx.ContractId, ctx.TenantId);

            activity?.SetTag("c041.outcome", "deny_malformed_authorized_tools");
            return new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041 default deny: Malformed authorized_tools JSON — cannot verify authorization.");
        }

        if (authorizedTools is null || authorizedTools.Count == 0)
        {
            _logger.LogWarning(
                "C-041 DENY: authorized_tools list is empty. " +
                "ContractId={ContractId} TenantId={TenantId} Tool={ToolName}",
                ctx.ContractId, ctx.TenantId, toolName);

            activity?.SetTag("c041.outcome", "deny_empty_authorized_tools");
            return new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-041 default deny: Contract '{ctx.ContractId}' has no authorized tools — '{toolName}' denied.");
        }

        // ── C-041 authorization check — exact match, case-sensitive ──────────────────────────
        // Tool names are contract identifiers; case-sensitive matching prevents spoofing.
        if (!authorizedTools.Contains(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: Tool={ToolName} not in authorized list. " +
                "ContractId={ContractId} TenantId={TenantId}",
                toolName, ctx.ContractId, ctx.TenantId);

            activity?.SetTag("c041.outcome", "deny_tool_not_authorized");
            activity?.SetTag("denied_tool", toolName);
            return new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-041 default deny: Tool '{toolName}' is not in the authorized_actions list for contract '{ctx.ContractId}'.");
        }

        // ── Authorization granted ─────────────────────────────────────────────────────────────
        _logger.LogInformation(
            "C-041 ALLOW: Tool={ToolName} is authorized. ContractId={ContractId} TenantId={TenantId}",
            toolName, ctx.ContractId, ctx.TenantId);

        activity?.SetTag("c041.outcome", "allow");
        return new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-041: Tool '{toolName}' is authorized by contract '{ctx.ContractId}'.");
    }
}