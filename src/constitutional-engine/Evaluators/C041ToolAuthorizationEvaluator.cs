// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Constitutional Annotation)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-041 (Tool Authorization) — every MCP tool call must appear in the
/// tenant's authorized_actions list extracted from their active employment contract.
/// Default-deny principle: if the tool is not explicitly listed, the action is DENIED.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-059: Named tracer aligns with platform-wide OpenTelemetry source convention.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId identifies which constitutional obligation this evaluator enforces.
    public string ClaimId => "C-041";

    /// <summary>
    /// C-073: Evaluates C-041 (Tool Authorization).
    /// Reads tool_name and authorized_actions from the JSON-encoded ActionParameters.
    /// Default deny: missing tool_name, absent authorized_actions, or unlisted tool → DENY.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-059: Every evaluation is a traced span for audit correlation.
        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // C-041: Extract tool_name from JSON-encoded action parameters.
        // STACK RULE: use GetParameter(), never TryGetValue() — ActionParameters is a JSON string.
        var toolName = ctx.GetParameter("tool_name");
        activity?.SetTag("tool_name", toolName ?? "<null>");

        // C-041: Default deny — a missing or blank tool_name cannot be authorized.
        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: tool_name is absent or blank. TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("c041.decision", "Deny");
            activity?.SetTag("c041.reason", "tool_name_missing");
            return Task.FromResult(Deny(
                "tool_name parameter is missing or empty — C-041 default deny applies"));
        }

        // C-041: Read authorized_actions list from action parameters.
        // The contract's authorized_actions[] is expected as a JSON string array,
        // e.g. authorized_actions: ["read_file","write_file","search_web"].
        var authorizedActionsRaw = ctx.GetParameter("authorized_actions");
        activity?.SetTag("c041.has_authorized_actions", authorizedActionsRaw is not null);

        // C-041: Default deny — no authorization list means no tool is permitted.
        if (!IsToolAuthorized(toolName, authorizedActionsRaw))
        {
            _logger.LogWarning(
                "C-041 DENY: tool={ToolName} not found in authorized_actions. TenantId={TenantId} ContractId={ContractId}",
                toolName, ctx.TenantId, ctx.ContractId);

            activity?.SetTag("c041.decision", "Deny");
            activity?.SetTag("c041.reason", "tool_not_authorized");
            return Task.FromResult(Deny(
                $"Tool '{toolName}' is not in the tenant's authorized_actions list — C-041 default deny applies"));
        }

        _logger.LogInformation(
            "C-041 ALLOW: tool={ToolName} is authorized. TenantId={TenantId} ContractId={ContractId}",
            toolName, ctx.TenantId, ctx.ContractId);

        activity?.SetTag("c041.decision", "Allow");
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"Tool '{toolName}' is present in the tenant's authorized_actions list"));
    }

    // C-073: Implements the C-041 default-deny check against the authorized actions list.
    // Returns false (deny) when: list is null/blank, JSON is malformed, or tool is absent.
    private static bool IsToolAuthorized(string toolName, string? authorizedActionsRaw)
    {
        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
            return false;

        return TryParseJsonArray(authorizedActionsRaw, toolName);
    }

    // C-073: Parses the JSON string array and performs case-insensitive membership check.
    // Any parse failure returns false — malformed authorization data is treated as deny.
    private static bool TryParseJsonArray(string jsonArray, string toolName)
    {
        try
        {
            using var doc = JsonDocument.Parse(jsonArray);
            var root = doc.RootElement;

            if (root.ValueKind != JsonValueKind.Array)
                return false;

            foreach (var element in root.EnumerateArray())
            {
                if (element.ValueKind == JsonValueKind.String
                    && string.Equals(
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
            // C-041: Malformed JSON in authorized_actions = deny.
            // Do not propagate — caller interprets false as DENY.
            return false;
        }
    }

    // C-073: Factory helper that creates a consistently-shaped DENY result carrying the claim ID.
    private EvaluationResult Deny(string reason) =>
        new(ClaimId, EvaluationVerdict.Deny, reason);
}