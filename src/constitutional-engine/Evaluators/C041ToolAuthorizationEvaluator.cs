// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation), C-076 (Test Coverage)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041: Every MCP tool call requires CE.ValidateAction. Default deny.
/// A tool not present in the contract's authorized_actions list is DENIED unconditionally.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource used for all constitutional tracing within this evaluator.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Implements C-041 — identifies which constitutional claim this evaluator enforces.
    /// <inheritdoc />
    public string ClaimId => "C-041";

    // C-073: Constitutional obligation — C-041 Tool Authorization, default deny.
    /// <summary>
    /// Evaluates whether the requested tool is present in the contract's authorized_actions list.
    /// Any tool not explicitly listed is DENIED (C-041 default-deny posture).
    /// </summary>
    /// <remarks>
    /// ActionParameters is a JSON-encoded string; use ctx.GetParameter() to extract values.
    /// This method performs no network I/O — all data is sourced from the EvaluationContext.
    /// </remarks>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: C-041 — every MCP tool call validated here; unlisted tool = DENY.
        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("constitutional.claim_id", ClaimId);
        activity?.SetTag("constitutional.tenant_id", ctx.TenantId);
        activity?.SetTag("constitutional.contract_id", ctx.ContractId);
        activity?.SetTag("constitutional.action_type", ctx.ActionType);

        // Step 1: Extract tool_name from JSON-encoded ActionParameters.
        // C-041: A missing or blank tool_name is an immediate DENY — we cannot authorise
        //        a call to an unnamed tool.
        var toolName = ctx.GetParameter("tool_name");

        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogInformation(
                "C-041 DENY: tool_name absent or blank. TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
                ctx.TenantId, ctx.ContractId, ctx.ActionType);

            activity?.SetTag("c041.verdict", "Deny");
            activity?.SetTag("c041.deny_reason", "tool_name_missing");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: tool_name is required for MCP tool calls but was not supplied. Default deny."));
        }

        activity?.SetTag("c041.tool_name", toolName);

        // Step 2: Read the contract's authorized_actions list from ActionParameters.
        // C-041: authorized_actions must be a JSON array of permitted tool name strings.
        //        A null, empty, or unparseable list means no tools are authorized (default deny).
        var authorizedActionsRaw = ctx.GetParameter("authorized_actions");

        if (!IsToolAuthorized(toolName, authorizedActionsRaw))
        {
            _logger.LogInformation(
                "C-041 DENY: Tool={ToolName} not in authorized_actions. TenantId={TenantId} ContractId={ContractId}",
                toolName, ctx.TenantId, ctx.ContractId);

            activity?.SetTag("c041.verdict", "Deny");
            activity?.SetTag("c041.deny_reason", "tool_not_in_authorized_list");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-041: Tool '{toolName}' is not present in the contract's authorized_actions list. Default deny."));
        }

        // Step 3: Tool is explicitly authorized — ALLOW.
        _logger.LogInformation(
            "C-041 ALLOW: Tool={ToolName} is authorized. TenantId={TenantId} ContractId={ContractId}",
            toolName, ctx.TenantId, ctx.ContractId);

        activity?.SetTag("c041.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-041: Tool '{toolName}' is present in the contract's authorized_actions list."));
    }

    // C-073: Private helper — determines tool authorization from the raw authorized_actions value.
    //        Supports JSON array format (primary) and comma-separated plain text (fallback).
    //        Returns false (deny) for any null, empty, or malformed input — upholding default-deny.
    private static bool IsToolAuthorized(string toolName, string? authorizedActionsRaw)
    {
        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
            return false;

        var trimmed = authorizedActionsRaw.TrimStart();

        // Primary path: JSON array (e.g., ["tool_a","tool_b"])
        if (trimmed.StartsWith('['))
            return TryParseJsonArray(authorizedActionsRaw, toolName);

        // Fallback path: comma-separated plain text (e.g., "tool_a,tool_b")
        // DESIGN_QUESTION: Should the comma-separated fallback be removed in a future version
        //                  to enforce JSON-only encoding for authorized_actions?
        var parts = authorizedActionsRaw.Split(
            ',',
            StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

        foreach (var part in parts)
        {
            if (string.Equals(part, toolName, StringComparison.OrdinalIgnoreCase))
                return true;
        }

        return false;
    }

    // C-073: Private helper — parses a JSON string array and checks for tool membership.
    //        Returns false on any JsonException (malformed input = default deny per C-041).
    private static bool TryParseJsonArray(string jsonArray, string toolName)
    {
        try
        {
            var docOptions = new JsonDocumentOptions { AllowTrailingCommas = true };
            using var document = JsonDocument.Parse(jsonArray, docOptions);

            if (document.RootElement.ValueKind != JsonValueKind.Array)
                return false; // Not an array — default deny.

            foreach (var element in document.RootElement.EnumerateArray())
            {
                if (element.ValueKind != JsonValueKind.String)
                    continue;

                var value = element.GetString();
                if (string.Equals(value, toolName, StringComparison.OrdinalIgnoreCase))
                    return true;
            }

            return false;
        }
        catch (JsonException)
        {
            // C-041: Malformed authorized_actions JSON → cannot verify authorization → default deny.
            return false;
        }
    }
}