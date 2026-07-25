// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Constitutional Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-041 Tool Authorization Evaluator.
/// Enforces the constitutional principle that every MCP tool call requires explicit
/// authorization. Default deny: any tool not present in the context's authorized
/// action parameters is unconstitutionally invoked and must be denied.
/// </summary>
/// <remarks>
/// DESIGN_QUESTION: Should the authorized tool list be injected from an external
/// policy store (e.g., OPA or employment-contract DB row) rather than derived
/// purely from EvaluationContext? EA review needed before WC012-04.
/// </remarks>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource annotates every constitutional obligation trace.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    /// <summary>
    /// C-073: Constructor annotation — implements C-041 (Tool Authorization).
    /// Constructor injection only; no DbContext (DB access is WC012-03 scope).
    /// </summary>
    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId identifies the constitutional claim enforced by this evaluator.
    /// <inheritdoc />
    public string ClaimId => "C-041";

    /// <summary>
    /// C-073: Implements C-041 (Tool Authorization) — default deny.
    /// Every MCP tool call must carry a non-empty, non-whitespace tool_name parameter
    /// AND that tool must be present in the contract's authorized_actions list derived
    /// from EvaluationContext.ActionParameters. Any failure → DENY.
    /// </summary>
    /// <param name="ctx">Evaluation context built from the ValidateAction gRPC request.</param>
    /// <param name="ct">Cancellation token propagated from the gRPC call context.</param>
    /// <returns>
    /// <see cref="EvaluationVerdict.Deny"/> if tool_name is absent, empty, whitespace,
    /// or not found in the authorized actions list; <see cref="EvaluationVerdict.Allow"/>
    /// if the tool is explicitly authorized for this contract.
    /// </returns>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: C-041 enforcement — Tool Authorization boundary check.
        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("tenant_id", ctx.TenantId);

        // Step 1 — Extract tool_name from JSON-encoded ActionParameters.
        // C-041: NEVER use ctx.ActionParameters.TryGetValue() — it is a string, not a Dictionary.
        var toolName = ctx.GetParameter("tool_name");

        // Step 2 — Default deny: missing, empty, or whitespace tool name.
        if (string.IsNullOrWhiteSpace(toolName))
        {
            const string reason =
                "C-041 default deny: tool_name parameter is absent or blank. " +
                "Every MCP tool call must identify the tool being invoked.";

            _logger.LogWarning(
                "C041 DENY — ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}: {Reason}",
                ctx.ContractId,
                ctx.ActionType,
                ctx.TenantId,
                reason);

            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("deny_reason", "missing_tool_name");

            return Task.FromResult(
                new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));
        }

        activity?.SetTag("tool_name", toolName);

        // Step 3 — Check whether the tool is listed in authorized_actions.
        // authorized_actions is a comma-separated or JSON array embedded in
        // ActionParameters under key "authorized_actions".
        // C-041: Default deny — if authorized_actions is absent or does not contain
        // the tool_name, the action is unconstitutional.
        var authorizedActionsRaw = ctx.GetParameter("authorized_actions");

        if (!IsToolAuthorized(toolName, authorizedActionsRaw))
        {
            var reason =
                $"C-041 default deny: tool '{toolName}' is not present in the contract's " +
                $"authorized_actions list for ContractId '{ctx.ContractId}'. " +
                "Unlisted tools are constitutionally prohibited.";

            _logger.LogWarning(
                "C041 DENY — ContractId={ContractId} ActionType={ActionType} " +
                "TenantId={TenantId} ToolName={ToolName}: {Reason}",
                ctx.ContractId,
                ctx.ActionType,
                ctx.TenantId,
                toolName,
                reason);

            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("deny_reason", "tool_not_in_authorized_list");

            return Task.FromResult(
                new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));
        }

        // Step 4 — Tool is explicitly authorized for this contract.
        _logger.LogInformation(
            "C041 ALLOW — ContractId={ContractId} ActionType={ActionType} " +
            "TenantId={TenantId} ToolName={ToolName}",
            ctx.ContractId,
            ctx.ActionType,
            ctx.TenantId,
            toolName);

        activity?.SetTag("verdict", "Allow");

        return Task.FromResult(
            new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                $"C-041: tool '{toolName}' is authorized under ContractId '{ctx.ContractId}'."));
    }

    // ── Private helpers ──────────────────────────────────────────────────────

    /// <summary>
    /// Checks whether <paramref name="toolName"/> appears in the raw
    /// <paramref name="authorizedActionsRaw"/> value extracted from ActionParameters.
    /// Supports two formats produced by the orchestration layer:
    ///   • JSON array:  ["read_file","write_file"]
    ///   • CSV string:  read_file,write_file
    /// Returns <c>false</c> (default deny) when the value is null, empty, or malformed.
    /// </summary>
    /// <param name="toolName">The tool name being validated.</param>
    /// <param name="authorizedActionsRaw">Raw string from ActionParameters["authorized_actions"].</param>
    private static bool IsToolAuthorized(string toolName, string? authorizedActionsRaw)
    {
        // C-041: absent or empty authorized_actions → default deny.
        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
        {
            return false;
        }

        var trimmed = authorizedActionsRaw.Trim();

        // JSON array path: ["tool_a","tool_b"]
        if (trimmed.StartsWith('[') && trimmed.EndsWith(']'))
        {
            return TryParseJsonArray(trimmed, toolName);
        }

        // CSV fallback path: tool_a,tool_b
        var parts = trimmed.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        foreach (var part in parts)
        {
            if (string.Equals(part, toolName, StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }

        return false;
    }

    /// <summary>
    /// Minimal JSON array parser — avoids a System.Text.Json dependency for a
    /// simple string-match use-case. Strips brackets and quotes then compares entries.
    /// Malformed JSON → returns false (default deny, per C-041).
    /// </summary>
    private static bool TryParseJsonArray(string jsonArray, string toolName)
    {
        try
        {
            // Strip outer brackets: ["a","b"] → "a","b"
            var inner = jsonArray[1..^1].Trim();

            if (string.IsNullOrWhiteSpace(inner))
            {
                return false;
            }

            // Split on commas, strip surrounding quotes/whitespace from each token.
            var tokens = inner.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
            foreach (var token in tokens)
            {
                var value = token.Trim('"', '\'', ' ');
                if (string.Equals(value, toolName, StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }

            return false;
        }
        catch
        {
            // C-041: malformed JSON → default deny. Never throw from an evaluator.
            return false;
        }
    }
}