// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-041 (Tool Authorization) — every MCP tool call requires explicit
/// authorization in the tenant's contract. Default deny: any tool not listed is DENIED.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");
    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId annotation — this evaluator is authoritative for C-041.
    public string ClaimId => "C-041";

    /// <summary>
    /// C-073: Evaluates whether the requested tool is explicitly authorized in the tenant's
    /// contract decision space. Default deny — unlisted tool = DENY (C-041).
    /// No network I/O. Completes synchronously within 1ms nominal path.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: OpenTelemetry trace span for constitutional audit trail (C-059).
        using var activity = _tracer.StartActivity("C041.EvaluateToolAuthorization", ActivityKind.Internal);
        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // C-073: Extract tool_name from JSON-encoded ActionParameters (STACK RULE: use GetParameter).
        var toolName = ctx.GetParameter("tool_name");

        // C-041 §Default Deny — missing, empty, or whitespace tool name is always DENY.
        if (string.IsNullOrWhiteSpace(toolName))
        {
            activity?.SetTag("deny_reason", "missing_tool_name");
            _logger.LogWarning(
                "C-041 DENY: tool_name parameter is missing or empty. TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
                ctx.TenantId, ctx.ContractId, ctx.ActionType);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: tool_name parameter is required and must not be empty. Default deny."));
        }

        // C-073: Extract authorized_tools JSON array from contract parameters.
        var authorizedActionsRaw = ctx.GetParameter("authorized_tools");

        // C-041 §Default Deny — no authorized list = DENY.
        if (!IsToolAuthorized(toolName, authorizedActionsRaw))
        {
            activity?.SetTag("deny_reason", "tool_not_authorized");
            activity?.SetTag("tool_name", toolName);
            _logger.LogWarning(
                "C-041 DENY: tool={ToolName} is not in the authorized tools list. TenantId={TenantId} ContractId={ContractId}",
                toolName, ctx.TenantId, ctx.ContractId);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-041: Tool '{toolName}' is not in the authorized tools list. Default deny applies."));
        }

        // C-041 §Authorization granted — tool is explicitly listed.
        activity?.SetTag("verdict", "allow");
        activity?.SetTag("tool_name", toolName);
        _logger.LogInformation(
            "C-041 ALLOW: tool={ToolName} is authorized. TenantId={TenantId} ContractId={ContractId}",
            toolName, ctx.TenantId, ctx.ContractId);

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-041: Tool '{toolName}' is explicitly authorized in the contract decision space."));
    }

    /// <summary>
    /// C-073: Determines whether <paramref name="toolName"/> appears in the
    /// <paramref name="authorizedActionsRaw"/> JSON array. Default deny when list is absent or unparseable.
    /// </summary>
    private static bool IsToolAuthorized(string toolName, string? authorizedActionsRaw)
    {
        // C-041 §Default Deny: null or whitespace authorized list → deny.
        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
        {
            return false;
        }

        // Attempt JSON array parse — malformed input → deny (no exception propagation).
        return TryParseJsonArray(authorizedActionsRaw, toolName);
    }

    /// <summary>
    /// C-073: Parses <paramref name="jsonArray"/> as a JSON string array and performs
    /// case-insensitive lookup for <paramref name="toolName"/>.
    /// Returns false (deny) on any parse failure — never throws.
    /// </summary>
    private static bool TryParseJsonArray(string jsonArray, string toolName)
    {
        try
        {
            // C-041: Case-insensitive comparison — tool names are not case-sensitive
            // in the WAOOAW MCP registry but we match exactly as declared in contract.
            using var doc = JsonDocument.Parse(jsonArray);
            var root = doc.RootElement;

            if (root.ValueKind != JsonValueKind.Array)
            {
                // Non-array JSON → default deny.
                return false;
            }

            foreach (var element in root.EnumerateArray())
            {
                if (element.ValueKind == JsonValueKind.String)
                {
                    var authorized = element.GetString();
                    if (string.Equals(authorized, toolName, StringComparison.OrdinalIgnoreCase))
                    {
                        return true;
                    }
                }
            }

            return false;
        }
        catch (JsonException)
        {
            // C-041 §Default Deny: malformed JSON in authorized_tools → deny, do not throw.
            return false;
        }
        catch (Exception)
        {
            // C-041 §Default Deny: any unexpected parse error → deny, do not throw.
            return false;
        }
    }
}