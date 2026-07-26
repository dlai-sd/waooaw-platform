// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-041 — Tool Authorization (Decision Space boundary).
/// Every MCP tool call must be explicitly present in the tenant's authorized_actions list.
/// Default-deny: any tool not listed in authorized_actions is unconditionally denied.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: Shared ActivitySource for OpenTelemetry tracing across constitutional evaluators
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Identifies the constitutional claim this evaluator enforces
    public string ClaimId => "C-041";

    /// <summary>
    /// C-073: Evaluates whether the requested tool is authorized under the tenant's
    /// employment contract (C-041). Default deny — unlisted tool = DENY.
    ///
    /// Decision logic:
    ///   1. Extract "tool_name" from ActionParameters via ctx.GetParameter().
    ///   2. If tool_name is null/empty/whitespace → DENY (cannot authorize unnamed tool).
    ///   3. Extract "authorized_actions" JSON array from ActionParameters.
    ///   4. If authorized_actions is absent or empty → DENY (no whitelist = deny all).
    ///   5. Parse JSON array; if tool_name is found (case-insensitive) → Allow.
    ///   6. Otherwise → DENY.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Start telemetry span for this constitutional evaluation
        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("constitutional.claim_id", ClaimId);
        activity?.SetTag("tenant.id", ctx.TenantId);
        activity?.SetTag("action.type", ctx.ActionType);
        activity?.SetTag("contract.id", ctx.ContractId);

        // Step 1 — Extract tool name from JSON-encoded ActionParameters
        // C-073: ctx.GetParameter() is the ONLY correct way to read ActionParameters (it is a JSON string)
        var toolName = ctx.GetParameter("tool_name");

        if (string.IsNullOrWhiteSpace(toolName))
        {
            // C-073: C-041 default deny — cannot authorize a nameless tool
            _logger.LogWarning(
                "C-041 DENY: tool_name parameter is null, empty, or whitespace. " +
                "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("c041.decision", "DENY");
            activity?.SetTag("c041.deny_reason", "tool_name_missing_or_empty");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: "C-041: tool_name parameter is required but was null, empty, or whitespace. " +
                        "Default deny — cannot authorize an unnamed tool call."
            ));
        }

        activity?.SetTag("c041.tool_name", toolName);

        // Step 2 — Extract the contract's authorized_actions JSON array
        var authorizedActionsRaw = ctx.GetParameter("authorized_actions");

        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
        {
            // C-073: C-041 default deny — no authorized list present means deny all
            _logger.LogWarning(
                "C-041 DENY: authorized_actions is absent or empty. " +
                "TenantId={TenantId} ToolName={ToolName} ContractId={ContractId}",
                ctx.TenantId, toolName, ctx.ContractId);

            activity?.SetTag("c041.decision", "DENY");
            activity?.SetTag("c041.deny_reason", "authorized_actions_absent");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-041: No authorized_actions list found for contract '{ctx.ContractId}'. " +
                        $"Tool '{toolName}' is denied by default."
            ));
        }

        // Step 3 — Check membership in the authorized_actions JSON array
        bool isAuthorized = IsToolAuthorized(toolName, authorizedActionsRaw);

        if (!isAuthorized)
        {
            // C-073: C-041 default deny — tool not found in the whitelist
            _logger.LogWarning(
                "C-041 DENY: tool '{ToolName}' is not listed in authorized_actions. " +
                "TenantId={TenantId} ContractId={ContractId}",
                toolName, ctx.TenantId, ctx.ContractId);

            activity?.SetTag("c041.decision", "DENY");
            activity?.SetTag("c041.deny_reason", "tool_not_in_authorized_list");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-041: Tool '{toolName}' is not present in the authorized actions list " +
                        $"for contract '{ctx.ContractId}'. Default deny."
            ));
        }

        // C-073: Tool is explicitly whitelisted — Allow
        _logger.LogInformation(
            "C-041 ALLOW: tool '{ToolName}' is authorized. " +
            "TenantId={TenantId} ContractId={ContractId}",
            toolName, ctx.TenantId, ctx.ContractId);

        activity?.SetTag("c041.decision", "ALLOW");

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: $"C-041: Tool '{toolName}' is present in the authorized actions list " +
                    $"for contract '{ctx.ContractId}'."
        ));
    }

    /// <summary>
    /// C-073: Delegates to JSON parsing to determine if toolName appears in
    /// the authorized_actions array. Returns false on any parse failure (safe default deny).
    /// </summary>
    private static bool IsToolAuthorized(string toolName, string? authorizedActionsRaw)
    {
        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
            return false;

        return TryParseJsonArray(authorizedActionsRaw, toolName);
    }

    /// <summary>
    /// C-073: Parses a JSON array string and checks whether toolName is a member
    /// (case-insensitive string comparison). Returns false on malformed JSON — never throws.
    /// This preserves the default-deny posture: a parse failure is treated as unauthorized.
    /// </summary>
    private static bool TryParseJsonArray(string jsonArray, string toolName)
    {
        try
        {
            using var doc = JsonDocument.Parse(jsonArray);

            if (doc.RootElement.ValueKind != JsonValueKind.Array)
            {
                // Malformed — not a JSON array; treat as unauthorized (default deny)
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

            return false;
        }
        catch (JsonException)
        {
            // C-073: Malformed JSON is treated as unauthorized — default deny is preserved
            return false;
        }
    }
}