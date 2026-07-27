// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041
// constitutional_basis: C-041 (Tool Authorization), C-059 (Traceability), C-073 (Annotated Obligations)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Annotated constitutional obligation.
/// Enforces C-041 — every MCP tool call requires CE.ValidateAction. Default deny.
/// Unlisted tool = DENY. Missing/empty contract = DENY.
/// Applies only to action type "MCP_TOOL_CALL"; all other action types receive Allow (not applicable).
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: ClaimId identifies the constitutional claim this evaluator enforces.
    /// <inheritdoc />
    public string ClaimId => "C-041";

    private const string McpToolCallActionType    = "MCP_TOOL_CALL";
    private const string ParamToolName            = "tool_name";
    private const string ParamAuthorizedTools     = "authorized_tools";

    private static readonly ActivitySource _tracer =
        new("Waooaw.ConstitutionalEngine");

    private static readonly JsonSerializerOptions _jsonOptions =
        new(JsonSerializerDefaults.Web);

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        // C-073: Constructor guards ensure evaluator is never instantiated without telemetry.
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>
    /// C-073: Evaluates C-041 Tool Authorization.
    /// Logic (in order, short-circuit on first DENY):
    ///   1. Non-MCP action type → Allow (not applicable).
    ///   2. Missing ContractId → DENY (no active contract — default deny).
    ///   3. Missing tool_name parameter → DENY (request is malformed).
    ///   4. Missing or empty authorized_tools list → DENY (default deny).
    ///   5. Malformed authorized_tools JSON → DENY (cannot confirm authorization).
    ///   6. tool_name not present in authorized_tools → DENY.
    ///   7. tool_name present → Allow.
    /// </summary>
    public async Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: Start OTel activity for full traceability of every authorization decision.
        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("claim_id",     ClaimId);
        activity?.SetTag("tenant_id",    ctx.TenantId);
        activity?.SetTag("action_type",  ctx.ActionType);
        activity?.SetTag("contract_id",  ctx.ContractId);

        // ── Step 1: Guard — only MCP_TOOL_CALL is in scope for C-041 ────────────────────
        if (!string.Equals(ctx.ActionType, McpToolCallActionType, StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogInformation(
                "C041: ActionType={ActionType} is not {McpType} — evaluator not applicable, returning Allow",
                ctx.ActionType, McpToolCallActionType);

            activity?.SetTag("verdict", "Allow");
            activity?.SetTag("skip_reason", "action_type_not_applicable");

            // No real async work needed on this fast path; satisfy the Task contract.
            await Task.CompletedTask.ConfigureAwait(false);
            return new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                $"C-041 does not apply to action type '{ctx.ActionType}'");
        }

        // ── Step 2: Missing ContractId → default deny ────────────────────────────────────
        // C-041: "Default deny" means no contract = no authorization.
        if (string.IsNullOrWhiteSpace(ctx.ContractId))
        {
            _logger.LogWarning(
                "C041: ContractId is null/empty for tenant={TenantId} — default deny (no active contract)",
                ctx.TenantId);

            activity?.SetTag("verdict",      "Deny");
            activity?.SetTag("deny_reason",  "missing_contract_id");

            await Task.CompletedTask.ConfigureAwait(false);
            return new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "No active employment contract found — MCP tool call denied by default (C-041)");
        }

        // ── Step 3: Extract tool_name from JSON-encoded ActionParameters ─────────────────
        // STACK RULE: use ctx.GetParameter() — never TryGetValue() on ActionParameters string.
        var toolName = ctx.GetParameter(ParamToolName);
        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C041: tool_name parameter missing for contract={ContractId} tenant={TenantId} — DENY",
                ctx.ContractId, ctx.TenantId);

            activity?.SetTag("verdict",     "Deny");
            activity?.SetTag("deny_reason", "missing_tool_name_parameter");

            await Task.CompletedTask.ConfigureAwait(false);
            return new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "MCP_TOOL_CALL action is missing required 'tool_name' parameter (C-041)");
        }

        activity?.SetTag("tool_name", toolName);

        // ── Step 4 & 5: Extract and parse authorized_tools from ActionParameters ──────────
        // The CE caller encodes the contract's authorized_actions[] as a JSON array
        // under the "authorized_tools" key inside ActionParameters.
        var authorizedToolsJson = ctx.GetParameter(ParamAuthorizedTools);
        if (string.IsNullOrWhiteSpace(authorizedToolsJson))
        {
            _logger.LogWarning(
                "C041: authorized_tools list absent for contract={ContractId} tool={ToolName} — default deny",
                ctx.ContractId, toolName);

            activity?.SetTag("verdict",     "Deny");
            activity?.SetTag("deny_reason", "no_authorized_tools_list");

            await Task.CompletedTask.ConfigureAwait(false);
            return new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"No authorized_tools list provided for contract '{ctx.ContractId}' — "
                + $"tool '{toolName}' denied by default (C-041)");
        }

        string[]? authorizedTools;
        try
        {
            authorizedTools = JsonSerializer.Deserialize<string[]>(authorizedToolsJson, _jsonOptions);
        }
        catch (JsonException ex)
        {
            _logger.LogError(
                ex,
                "C041: Failed to deserialize authorized_tools JSON for contract={ContractId} tool={ToolName} — default deny",
                ctx.ContractId, toolName);

            activity?.SetTag("verdict",     "Deny");
            activity?.SetTag("deny_reason", "malformed_authorized_tools_json");

            await Task.CompletedTask.ConfigureAwait(false);
            return new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"authorized_tools list is malformed JSON — tool '{toolName}' denied by default (C-041)");
        }

        // ── Step 4 (continued): Empty deserialized list → default deny ───────────────────
        if (authorizedTools is null || authorizedTools.Length == 0)
        {
            _logger.LogWarning(
                "C041: authorized_tools list is empty for contract={ContractId} tool={ToolName} — default deny",
                ctx.ContractId, toolName);

            activity?.SetTag("verdict",     "Deny");
            activity?.SetTag("deny_reason", "empty_authorized_tools_list");

            await Task.CompletedTask.ConfigureAwait(false);
            return new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"authorized_tools list is empty for contract '{ctx.ContractId}' — "
                + $"tool '{toolName}' denied by default (C-041)");
        }

        // ── Step 6 & 7: Membership check — case-insensitive ──────────────────────────────
        // C-041: unlisted tool = DENY (default deny is the starting state).
        var isAuthorized = Array.Exists(
            authorizedTools,
            t => string.Equals(t, toolName, StringComparison.OrdinalIgnoreCase));

        if (!isAuthorized)
        {
            _logger.LogWarning(
                "C041: Tool={ToolName} is NOT in authorized_tools for contract={ContractId} tenant={TenantId} — DENY",
                toolName, ctx.ContractId, ctx.TenantId);

            activity?.SetTag("verdict",     "Deny");
            activity?.SetTag("deny_reason", "tool_not_in_authorized_list");

            await Task.CompletedTask.ConfigureAwait(false);
            return new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"Tool '{toolName}' is not listed in authorized_tools for contract '{ctx.ContractId}' (C-041)");
        }

        // ── Authorized ────────────────────────────────────────────────────────────────────
        _logger.LogInformation(
            "C041: Tool={ToolName} AUTHORIZED by contract={ContractId} tenant={TenantId}",
            toolName, ctx.ContractId, ctx.TenantId);

        activity?.SetTag("verdict", "Allow");

        await Task.CompletedTask.ConfigureAwait(false);
        return new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"Tool '{toolName}' is authorized by contract '{ctx.ContractId}' (C-041)");
    }
}