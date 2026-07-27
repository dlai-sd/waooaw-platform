// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation), C-076 (≥90% test coverage)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-041 — every MCP tool call is default-deny unless the tool name
/// appears in the contract's authorized_actions list carried in ActionParameters.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: Tracing span for observability of every evaluation
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId identifies the constitutional claim this evaluator enforces.
    public string ClaimId => "C-041";

    /// <summary>
    /// C-073: Evaluate whether the requested tool is explicitly authorized.
    /// Default deny — any missing or unlisted tool name returns DENY immediately.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Start an observability span for this evaluation
        using var activity = _tracer.StartActivity("C041ToolAuthorizationEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // C-073 / C-041: Extract tool name from JSON-encoded ActionParameters
        var toolName = ctx.GetParameter("tool_name");

        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY — tool_name missing or empty. TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
                ctx.TenantId, ctx.ContractId, ctx.ActionType);

            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("deny_reason", "tool_name_missing");

            return Task.FromResult(Deny("C-041: tool_name parameter is missing or empty — default deny."));
        }

        activity?.SetTag("tool_name", toolName);

        // C-073 / C-041: Read the authorized_actions list from ActionParameters
        var authorizedActionsRaw = ctx.GetParameter("authorized_actions");

        if (!IsToolAuthorized(toolName, authorizedActionsRaw))
        {
            _logger.LogWarning(
                "C-041 DENY — tool '{ToolName}' not in authorized_actions. TenantId={TenantId} ContractId={ContractId}",
                toolName, ctx.TenantId, ctx.ContractId);

            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("deny_reason", "tool_not_authorized");

            return Task.FromResult(Deny(
                $"C-041: tool '{toolName}' is not in the contract's authorized_actions list — default deny."));
        }

        _logger.LogInformation(
            "C-041 ALLOW — tool '{ToolName}' authorized. TenantId={TenantId} ContractId={ContractId}",
            toolName, ctx.TenantId, ctx.ContractId);

        activity?.SetTag("verdict", "Allow");

        return Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow,
            $"C-041: tool '{toolName}' is explicitly authorized."));
    }

    // ── Private helpers ──────────────────────────────────────────────────────────

    /// <summary>
    /// Returns true only when <paramref name="authorizedActionsRaw"/> is a non-empty
    /// JSON array that contains <paramref name="toolName"/> (case-sensitive).
    /// Any parse error or absent list returns false (default deny).
    /// </summary>
    private static bool IsToolAuthorized(string toolName, string? authorizedActionsRaw)
    {
        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
        {
            return false; // C-041: no list present → default deny
        }

        // Attempt JSON array parse; malformed JSON → default deny (no exception surfaced)
        return TryParseJsonArray(authorizedActionsRaw, toolName);
    }

    /// <summary>
    /// Parses <paramref name="jsonArray"/> as a JSON string array and returns true
    /// if <paramref name="toolName"/> appears in it.
    /// Returns false (and swallows <see cref="JsonException"/>) on malformed input.
    /// </summary>
    private static bool TryParseJsonArray(string jsonArray, string toolName)
    {
        try
        {
            // Use JsonDocument for zero-allocation enumeration
            using var doc = JsonDocument.Parse(jsonArray);
            var root = doc.RootElement;

            if (root.ValueKind != JsonValueKind.Array)
            {
                return false; // Unexpected shape → default deny
            }

            foreach (var element in root.EnumerateArray())
            {
                if (element.ValueKind == JsonValueKind.String &&
                    string.Equals(element.GetString(), toolName, StringComparison.Ordinal))
                {
                    return true;
                }
            }

            return false; // Tool not found in array
        }
        catch (JsonException)
        {
            // C-041: malformed JSON in authorized_actions → default deny, never throw
            return false;
        }
    }

    /// <summary>Convenience factory for a DENY result attributed to this evaluator.</summary>
    private EvaluationResult Deny(string reason) =>
        new(ClaimId, EvaluationVerdict.Deny, reason);
}