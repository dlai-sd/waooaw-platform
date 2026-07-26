// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 (Tool Authorization): every MCP tool call requires CE.ValidateAction.
/// Default deny — a tool not present in the tenant's authorized_actions list is DENIED.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource for OpenTelemetry span tracing of constitutional decisions.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    /// <summary>
    /// C-073: Constructor — receives logger via DI; null guard per C-059.
    /// </summary>
    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>Constitutional claim ID enforced by this evaluator.</summary>
    public string ClaimId => "C-041";

    /// <summary>
    /// C-073 / C-041: Evaluates whether the requested tool is present in the tenant's
    /// authorized_actions list. Default deny: an unlisted or missing tool name → DENY.
    /// MUST NOT perform network I/O — reads only from EvaluationContext parameters.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: Null guard — invalid context is a hard fault.
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: OpenTelemetry span scoped to this evaluation.
        using var activity = _tracer.StartActivity(
            "C041.EvaluateToolAuthorization",
            ActivityKind.Internal);
        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("action_type", ctx.ActionType);

        // C-073: Respect cooperative cancellation before any CPU work.
        ct.ThrowIfCancellationRequested();

        // C-041: Extract tool_name from JSON-encoded ActionParameters.
        // ctx.GetParameter() is the ONLY safe accessor — ActionParameters is a raw JSON string.
        string? toolName = ctx.GetParameter("tool_name");

        // C-041: Missing or blank tool name → default deny (cannot authorize unknown tool).
        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: tool_name parameter is missing or empty. " +
                "ContractId={ContractId} TenantId={TenantId} ActionType={ActionType}",
                ctx.ContractId, ctx.TenantId, ctx.ActionType);

            activity?.SetTag("decision", "Deny");
            activity?.SetTag("deny_reason", "tool_name_missing_or_empty");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: "C-041: tool_name parameter is missing or empty — default deny applies."));
        }

        activity?.SetTag("tool_name", toolName);

        // C-041: Read the tenant contract's authorized_actions JSON array from parameters.
        // This is injected by EvaluationContext.FromRequest() from the ValidateActionRequest payload.
        string? authorizedActionsRaw = ctx.GetParameter("authorized_actions");

        bool authorized = IsToolAuthorized(toolName, authorizedActionsRaw);

        if (!authorized)
        {
            _logger.LogWarning(
                "C-041 DENY: Tool={ToolName} is not in authorized_actions. " +
                "ContractId={ContractId} TenantId={TenantId}",
                toolName, ctx.ContractId, ctx.TenantId);

            activity?.SetTag("decision", "Deny");
            activity?.SetTag("deny_reason", "tool_not_in_authorized_actions");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-041: Tool '{toolName}' is not listed in the tenant's " +
                        $"authorized_actions — default deny applies."));
        }

        _logger.LogInformation(
            "C-041 ALLOW: Tool={ToolName} ContractId={ContractId} TenantId={TenantId}",
            toolName, ctx.ContractId, ctx.TenantId);

        activity?.SetTag("decision", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: $"C-041: Tool '{toolName}' is present in the authorized_actions list."));
    }

    // C-073: Determines whether the given tool name appears in the contract's
    // authorized_actions. Returns false (deny) when the list is absent or empty.
    private static bool IsToolAuthorized(string toolName, string? authorizedActionsRaw)
    {
        // C-041: No authorized_actions declared → nothing is permitted (default deny).
        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
        {
            return false;
        }

        return TryParseJsonArray(authorizedActionsRaw, toolName);
    }

    // C-073: Parses the JSON array and performs a case-insensitive match against toolName.
    // Returns false on malformed JSON (defensive default deny — C-041 §Default Deny).
    private static bool TryParseJsonArray(string jsonArray, string toolName)
    {
        try
        {
            using JsonDocument doc = JsonDocument.Parse(jsonArray);
            JsonElement root = doc.RootElement;

            // C-041: Only a JSON array is a valid authorized_actions value.
            if (root.ValueKind != JsonValueKind.Array)
            {
                return false;
            }

            foreach (JsonElement element in root.EnumerateArray())
            {
                // C-041: Case-insensitive comparison — tool names are not case-sensitive.
                if (element.ValueKind == JsonValueKind.String &&
                    string.Equals(
                        element.GetString(),
                        toolName,
                        StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }

            return false;
        }
        catch (JsonException)
        {
            // C-041: Malformed JSON in authorized_actions → cannot determine authorization
            // → default deny. Do not re-throw; caller records DENY evidence.
            return false;
        }
    }
}