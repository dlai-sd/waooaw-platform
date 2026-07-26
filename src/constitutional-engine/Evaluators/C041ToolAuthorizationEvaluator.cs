// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Constitutional Annotation)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041: every MCP tool call must be explicitly listed in the tenant's
/// employment contract authorized_actions[]. Default deny — unlisted tool = DENY.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource annotated for OpenTelemetry tracing of constitutional enforcement
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    /// <summary>
    /// C-073: Constructor satisfies C-041 enforcement wiring via DI.
    /// </summary>
    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId identifies the constitutional claim this evaluator enforces.
    /// <inheritdoc />
    public string ClaimId => "C-041";

    /// <summary>
    /// C-073: Enforces C-041 Tool Authorization — default deny.
    /// Reads tool_name and authorized_actions from the JSON-encoded ActionParameters.
    /// Returns DENY if tool_name is absent, empty, or not present in the authorized list.
    /// Returns ALLOW only when the tool appears explicitly in the tenant contract's
    /// authorized_actions JSON array.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: OpenTelemetry span per C-059 traceability requirement
        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.EvaluateAsync",
            ActivityKind.Internal);
        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // C-041: tool_name is mandatory — absence is an immediate DENY (default deny)
        var toolName = ctx.GetParameter("tool_name");

        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: tool_name parameter is null or empty. TenantId={TenantId} ContractId={ContractId}",
                ctx.TenantId, ctx.ContractId);

            activity?.SetTag("c041.verdict", "Deny");
            activity?.SetTag("c041.deny_reason", "missing_tool_name");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: "C-041: tool_name parameter is missing or empty — default deny applies"));
        }

        activity?.SetTag("tool_name", toolName);

        // C-041: authorized_actions is the JSON array from the employment contract
        var authorizedActionsRaw = ctx.GetParameter("authorized_actions");

        if (!IsToolAuthorized(toolName, authorizedActionsRaw))
        {
            _logger.LogWarning(
                "C-041 DENY: tool '{ToolName}' is not in authorized_actions. TenantId={TenantId} ContractId={ContractId}",
                toolName, ctx.TenantId, ctx.ContractId);

            activity?.SetTag("c041.verdict", "Deny");
            activity?.SetTag("c041.deny_reason", "tool_not_authorized");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-041: tool '{toolName}' is not listed in the contract's authorized_actions — default deny applies"));
        }

        _logger.LogInformation(
            "C-041 ALLOW: tool '{ToolName}' is authorized. TenantId={TenantId} ContractId={ContractId}",
            toolName, ctx.TenantId, ctx.ContractId);

        activity?.SetTag("c041.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: $"C-041: tool '{toolName}' is present in authorized_actions"));
    }

    /// <summary>
    /// C-073: Enforces C-041 default-deny contract.
    /// Returns false when authorized_actions is absent, empty, not valid JSON, or does not
    /// contain toolName. Returns true ONLY on an explicit case-insensitive match.
    /// </summary>
    private static bool IsToolAuthorized(string toolName, string? authorizedActionsRaw)
    {
        // C-041: absent or empty authorized list → default deny
        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
            return false;

        return TryParseJsonArray(authorizedActionsRaw, toolName);
    }

    /// <summary>
    /// C-073: Parses the JSON-encoded authorized_actions array and performs a
    /// case-insensitive lookup for toolName.
    /// Returns false on any parse failure (malformed JSON → default deny per C-041).
    /// </summary>
    private static bool TryParseJsonArray(string jsonArray, string toolName)
    {
        try
        {
            using var document = JsonDocument.Parse(jsonArray);
            var root = document.RootElement;

            // C-041: authorized_actions must be a JSON array — any other shape → default deny
            if (root.ValueKind != JsonValueKind.Array)
                return false;

            foreach (var element in root.EnumerateArray())
            {
                if (element.ValueKind == JsonValueKind.String &&
                    string.Equals(element.GetString(), toolName, StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }

            // C-041: tool not found in array → default deny
            return false;
        }
        catch (JsonException)
        {
            // C-041: malformed JSON in authorized_actions → cannot verify authorization → default deny
            return false;
        }
    }
}