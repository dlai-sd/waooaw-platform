// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041
// constitutional_basis: C-041 (Tool Authorization — Decision Space boundary, default deny)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-041: Tool Authorization evaluator.
/// Every MCP tool call requires CE.ValidateAction. Default deny — an unlisted tool is denied.
/// Reads tool_name and authorized_tool_names from the JSON-encoded ActionParameters.
/// MUST NOT perform network I/O — evaluation is pure in-memory / context only.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // ── Constitutional identity ────────────────────────────────────────────────

    /// <inheritdoc/>
    // C-073: constitutional obligation — ClaimId identifies the enforced claim.
    public string ClaimId => "C-041";

    /// <inheritdoc/>
    // C-073: Applies exclusively to MCP_TOOL_CALL actions — see spec §C-041.
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "MCP_TOOL_CALL" };

    // ── Infrastructure ─────────────────────────────────────────────────────────

    private static readonly ActivitySource _tracer =
        new("Waooaw.ConstitutionalEngine");

    private static readonly JsonSerializerOptions _jsonOptions = new()
    {
        PropertyNameCaseInsensitive = true
    };

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    // ── Constructor ────────────────────────────────────────────────────────────

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // ── Core evaluation ────────────────────────────────────────────────────────

    /// <inheritdoc/>
    // C-073: Enforces C-041 (Tool Authorization) — every MCP tool call default-denied
    // unless the tool name appears in the contract's authorized_tool_names list.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("claim_id",    ClaimId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("tenant_id",   ctx.TenantId);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Step 1: tool_name must be present ─────────────────────────────────
        // C-041: A tool call with no identified tool cannot be authorized.
        string? toolName = ctx.GetParameter("tool_name");

        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY — tool_name absent from ActionParameters. " +
                "ContractId={ContractId} TenantId={TenantId}",
                ctx.ContractId, ctx.TenantId);

            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("deny_reason", "tool_name_missing");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: tool_name is required for MCP_TOOL_CALL but was not present in ActionParameters."));
        }

        activity?.SetTag("tool_name", toolName);

        // ── Step 2: authorized_tool_names must be present ─────────────────────
        // C-041: Absence of an authorization list means the contract has not declared
        // any tool grants — default deny applies.
        string? authorizedToolsRaw = ctx.GetParameter("authorized_tool_names");

        if (string.IsNullOrWhiteSpace(authorizedToolsRaw))
        {
            _logger.LogWarning(
                "C-041 DENY — authorized_tool_names absent from ActionParameters (default deny). " +
                "ContractId={ContractId} TenantId={TenantId} ToolName={ToolName}",
                ctx.ContractId, ctx.TenantId, toolName);

            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("deny_reason", "authorized_tool_names_missing");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-041: No authorized_tool_names found in contract {ctx.ContractId}. Default deny."));
        }

        // ── Step 3: parse authorized_tool_names JSON array ────────────────────
        // Expected: ["tool_a","tool_b",...] — a JSON string array.
        HashSet<string>? authorizedTools;
        try
        {
            authorizedTools = JsonSerializer.Deserialize<HashSet<string>>(
                authorizedToolsRaw, _jsonOptions);
        }
        catch (JsonException ex)
        {
            _logger.LogError(ex,
                "C-041 DENY — authorized_tool_names JSON parse failure (default deny). " +
                "ContractId={ContractId} TenantId={TenantId}",
                ctx.ContractId, ctx.TenantId);

            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("deny_reason", "authorized_tool_names_parse_error");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: authorized_tool_names could not be parsed — default deny applied."));
        }

        if (authorizedTools is null || authorizedTools.Count == 0)
        {
            _logger.LogWarning(
                "C-041 DENY — authorized_tool_names list is empty (default deny). " +
                "ContractId={ContractId} TenantId={TenantId} ToolName={ToolName}",
                ctx.ContractId, ctx.TenantId, toolName);

            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("deny_reason", "authorized_tool_names_empty");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-041: authorized_tool_names is empty for contract {ctx.ContractId}. Default deny."));
        }

        activity?.SetTag("authorized_tools_count", authorizedTools.Count);

        // ── Step 4: membership check — default deny if unlisted ───────────────
        // C-041: The tool must appear explicitly in the contract's grant list.
        // Case-sensitive match: tool names are identifiers and must match exactly.
        if (!authorizedTools.Contains(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY — tool not in authorized list. " +
                "ContractId={ContractId} TenantId={TenantId} ToolName={ToolName}",
                ctx.ContractId, ctx.TenantId, toolName);

            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("deny_reason", "tool_not_authorized");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-041: Tool '{toolName}' is not in the authorized tool list for contract {ctx.ContractId}."));
        }

        // ── Step 5: tool is explicitly authorized ─────────────────────────────
        _logger.LogInformation(
            "C-041 ALLOW — tool authorized. " +
            "ContractId={ContractId} TenantId={TenantId} ToolName={ToolName}",
            ctx.ContractId, ctx.TenantId, toolName);

        activity?.SetTag("verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-041: Tool '{toolName}' is authorized under contract {ctx.ContractId}."));
    }
}