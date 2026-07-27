// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-041 Tool Authorization Evaluator.
/// Default-deny: every MCP tool call must appear in the tenant's authorized_tools list
/// (passed as a JSON array in ActionParameters["authorized_tools"]) or the action is DENIED.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource for distributed tracing — required by ADR-009 (OpenTelemetry)
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId — declares which constitutional claim this evaluator enforces
    /// <inheritdoc />
    public string ClaimId => "C-041";

    // C-073: EvaluateAsync — enforces C-041 (Tool Authorization) default-deny boundary
    /// <inheritdoc />
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("tenant_id", ctx.TenantId);

        // C-041: Step 1 — extract tool_name from JSON-encoded ActionParameters.
        //        ctx.GetParameter() is the ONLY valid accessor (ActionParameters is a JSON string).
        var toolName = ctx.GetParameter("tool_name");

        if (string.IsNullOrWhiteSpace(toolName))
        {
            // C-041: No tool name supplied — default deny applies immediately.
            _logger.LogInformation(
                "C-041 DENY: tool_name missing or empty. TenantId={TenantId} ActionType={ActionType}",
                ctx.TenantId,
                ctx.ActionType);

            activity?.SetTag("decision", "Deny");
            activity?.SetTag("deny_reason", "missing_tool_name");

            return Task.FromResult(
                Deny("C-041: tool_name parameter is missing or empty — default deny applies."));
        }

        activity?.SetTag("tool_name", toolName);

        // C-041: Step 2 — read the tenant's authorized_tools JSON array from ActionParameters.
        var authorizedToolsRaw = ctx.GetParameter("authorized_tools");

        if (!IsToolAuthorized(toolName, authorizedToolsRaw))
        {
            // C-041: Tool is not in the authorized list — default deny.
            _logger.LogInformation(
                "C-041 DENY: tool={ToolName} not in authorized_tools list. TenantId={TenantId} ActionType={ActionType}",
                toolName,
                ctx.TenantId,
                ctx.ActionType);

            activity?.SetTag("decision", "Deny");
            activity?.SetTag("deny_reason", "tool_not_authorized");

            return Task.FromResult(
                Deny($"C-041: Tool '{toolName}' is not in the authorized tools list — default deny applies."));
        }

        // C-041: Tool explicitly found in the authorized list — allow.
        _logger.LogInformation(
            "C-041 ALLOW: tool={ToolName} found in authorized_tools list. TenantId={TenantId}",
            toolName,
            ctx.TenantId);

        activity?.SetTag("decision", "Allow");

        return Task.FromResult(
            new EvaluationResult(ClaimId, EvaluationVerdict.Allow,
                $"C-041: Tool '{toolName}' is authorized for this tenant."));
    }

    // C-073: IsToolAuthorized — implements C-041 default-deny check
    //        Returns false for null/empty raw JSON (default deny) and for malformed JSON (safe fail-closed).
    private static bool IsToolAuthorized(string toolName, string? authorizedActionsRaw)
    {
        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
        {
            // No authorized_tools parameter supplied — default deny.
            return false;
        }

        return TryParseJsonArray(authorizedActionsRaw, toolName);
    }

    // C-073: TryParseJsonArray — parses authorized_tools JSON array and checks membership.
    //        Returns false on any JSON parse failure (fail-closed per C-041 default deny).
    private static bool TryParseJsonArray(string jsonArray, string toolName)
    {
        try
        {
            using var doc = JsonDocument.Parse(jsonArray);

            if (doc.RootElement.ValueKind != JsonValueKind.Array)
            {
                // Not a JSON array — cannot authorize, default deny.
                return false;
            }

            foreach (var element in doc.RootElement.EnumerateArray())
            {
                if (element.ValueKind == JsonValueKind.String &&
                    string.Equals(element.GetString(), toolName, StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }

            // Tool not found in array.
            return false;
        }
        catch (JsonException)
        {
            // Malformed JSON — fail closed (default deny).
            return false;
        }
    }

    // C-073: Deny factory — ensures ClaimId is always populated on denial records (C-023 Evidence First)
    private EvaluationResult Deny(string reason) =>
        new(ClaimId, EvaluationVerdict.Deny, reason);
}