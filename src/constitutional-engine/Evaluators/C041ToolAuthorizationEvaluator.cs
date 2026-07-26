// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Constitutional Annotation)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 Tool Authorization: every MCP tool call must appear in the contract's
/// authorized_actions list. Default deny — any unlisted or unidentifiable tool is DENIED.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: OpenTelemetry tracer scoped to the Constitutional Engine service.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Identifies the constitutional claim this evaluator enforces.
    public string ClaimId => "C-041";

    /// <summary>
    /// C-073: Evaluates whether the requested tool is listed in the contract's
    /// authorized_actions parameter. Default deny: any tool absent from the list is DENIED.
    ///
    /// Algorithm:
    ///   1. Extract "tool_name" from ActionParameters via ctx.GetParameter().
    ///   2. If tool_name is null/empty/whitespace → DENY (cannot authorize an unnamed tool).
    ///   3. Extract "authorized_actions" from ActionParameters.
    ///   4. If authorized_actions is absent or empty → DENY (no allowlist = deny all).
    ///   5. Parse authorized_actions as a JSON array (or comma-separated fallback).
    ///   6. If tool_name is present in the list → ALLOW. Otherwise → DENY.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Start a tracing span for observability (ADR-009 OpenTelemetry).
        using var activity = _tracer.StartActivity("C041ToolAuthorizationEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("constitutional.claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // Step 1: Resolve tool_name from JSON-encoded ActionParameters.
        // C-041: An action with no tool identity cannot be authorized.
        var toolName = ctx.GetParameter("tool_name");
        activity?.SetTag("tool_name", toolName ?? "<null>");

        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY — tool_name missing or blank. TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
                ctx.TenantId, ctx.ContractId, ctx.ActionType);
            activity?.SetTag("decision", "deny");
            activity?.SetTag("deny_reason", "tool_name_missing");
            return Task.FromResult(Deny(
                "C-041: 'tool_name' parameter is missing or empty — default deny applies. " +
                "Every MCP tool call must supply a non-empty tool_name."));
        }

        // Step 2: Resolve authorized_actions list from ActionParameters.
        // C-041: Absence of an allowlist means no tools are permitted.
        var authorizedActionsRaw = ctx.GetParameter("authorized_actions");

        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
        {
            _logger.LogWarning(
                "C-041 DENY — authorized_actions list absent. Tool={ToolName} TenantId={TenantId} ContractId={ContractId}",
                toolName, ctx.TenantId, ctx.ContractId);
            activity?.SetTag("decision", "deny");
            activity?.SetTag("deny_reason", "no_authorized_actions_list");
            return Task.FromResult(Deny(
                $"C-041: No authorized_actions list found in contract context — " +
                $"tool '{toolName}' cannot be approved. Default deny applies."));
        }

        // Step 3: Check if the tool appears in the authorized list.
        // C-041: If parsing fails (malformed JSON), treat as unauthorized — default deny.
        var authorized = IsToolAuthorized(toolName, authorizedActionsRaw);
        activity?.SetTag("decision", authorized ? "allow" : "deny");

        if (!authorized)
        {
            _logger.LogWarning(
                "C-041 DENY — tool not in authorized_actions list. Tool={ToolName} TenantId={TenantId} ContractId={ContractId}",
                toolName, ctx.TenantId, ctx.ContractId);
            activity?.SetTag("deny_reason", "tool_not_in_allowlist");
            return Task.FromResult(Deny(
                $"C-041: Tool '{toolName}' is not present in the contract's authorized_actions list. " +
                "Default deny applies — only explicitly authorized tools may be invoked."));
        }

        // C-041: Tool is explicitly authorized in the contract's decision space.
        _logger.LogInformation(
            "C-041 ALLOW — tool authorized by contract. Tool={ToolName} TenantId={TenantId} ContractId={ContractId}",
            toolName, ctx.TenantId, ctx.ContractId);
        return Task.FromResult(
            new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                $"C-041: Tool '{toolName}' is present in the contract's authorized_actions list."));
    }

    // ─── Private helpers ──────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Determines whether <paramref name="toolName"/> appears in the raw
    /// authorized_actions value (JSON array preferred; comma-separated as fallback).
    /// Returns false on any parse failure — enforcing default deny.
    /// </summary>
    private static bool IsToolAuthorized(string toolName, string? authorizedActionsRaw)
    {
        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
            return false;

        var trimmed = authorizedActionsRaw.AsSpan().TrimStart();

        // Primary: JSON array format (["tool_a","tool_b"]).
        if (trimmed.StartsWith("[", StringComparison.Ordinal))
            return TryParseJsonArray(authorizedActionsRaw, toolName);

        // Fallback: comma-separated plain text ("tool_a,tool_b").
        // C-041: Case-insensitive comparison to avoid case-sensitivity bypass attacks.
        var parts = authorizedActionsRaw.Split(
            ',',
            StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

        return Array.Exists(
            parts,
            part => string.Equals(part, toolName, StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>
    /// C-073: Deserializes a JSON string array and performs case-insensitive membership
    /// check for <paramref name="toolName"/>. Returns false on malformed JSON — default deny.
    /// </summary>
    private static bool TryParseJsonArray(string jsonArray, string toolName)
    {
        try
        {
            var items = JsonSerializer.Deserialize<string[]>(jsonArray);
            if (items is null or { Length: 0 })
                return false;

            // C-041: Case-insensitive match prevents case-variant bypass attacks (C-062 defense-in-depth).
            return Array.Exists(
                items,
                item => string.Equals(item, toolName, StringComparison.OrdinalIgnoreCase));
        }
        catch (JsonException)
        {
            // C-041: Malformed authorized_actions JSON cannot be trusted — default deny.
            return false;
        }
    }

    /// <summary>C-073: Produces a typed DENY result carrying this evaluator's ClaimId.</summary>
    private EvaluationResult Deny(string reason) =>
        new(ClaimId, EvaluationVerdict.Deny, reason);
}