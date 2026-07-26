// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 Tool Authorization: every MCP tool call must be explicitly listed in the
/// contract's authorized_actions parameter. Default deny — unlisted tool = DENY.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: OpenTelemetry ActivitySource for constitutional traceability (C-059)
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>Constitutional claim ID enforced by this evaluator.</summary>
    public string ClaimId => "C-041";

    /// <summary>
    /// C-073: Evaluate whether the requested tool is within the contract's authorized decision space.
    /// Algorithm:
    ///   1. Extract tool_name from JSON-encoded ActionParameters — missing/blank = DENY.
    ///   2. Extract authorized_actions JSON array from ActionParameters — absent = DENY.
    ///   3. Tool name must appear (case-insensitive) in the authorized_actions array — else DENY.
    ///   4. All other outcomes = ALLOW.
    /// MUST NOT perform network I/O. CancellationToken is checked before work begins.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);
        ct.ThrowIfCancellationRequested();

        // C-073: Start OpenTelemetry span for this constitutional evaluation (C-059)
        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.EvaluateAsync", ActivityKind.Internal);
        activity?.SetTag("claim_id",    ClaimId);
        activity?.SetTag("tenant_id",   ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Step 1: tool_name must be present and non-blank ──────────────────────────────
        // C-073: ActionParameters is JSON-encoded — use GetParameter(), never TryGetValue()
        var toolName = ctx.GetParameter("tool_name");

        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: tool_name parameter is absent or blank. " +
                "TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
                ctx.TenantId, ctx.ContractId, ctx.ActionType);

            activity?.SetTag("verdict",     "Deny");
            activity?.SetTag("deny_reason", "tool_name_missing");

            return Task.FromResult(Deny(
                "C-041: tool_name parameter is missing or empty — default deny applies."));
        }

        activity?.SetTag("tool_name", toolName);

        // ── Step 2 & 3: tool_name must appear in authorized_actions list ─────────────────
        // C-073: authorized_actions comes from the contract's decision space parameters
        var authorizedActionsRaw = ctx.GetParameter("authorized_actions");

        if (!IsToolAuthorized(toolName, authorizedActionsRaw))
        {
            _logger.LogWarning(
                "C-041 DENY: Tool '{ToolName}' is not in authorized_actions. " +
                "TenantId={TenantId} ContractId={ContractId}",
                toolName, ctx.TenantId, ctx.ContractId);

            activity?.SetTag("verdict",     "Deny");
            activity?.SetTag("deny_reason", "tool_not_in_authorized_actions");

            return Task.FromResult(Deny(
                $"C-041: Tool '{toolName}' is not listed in the contract's authorized_actions — default deny applies."));
        }

        // ── Step 4: ALLOW ────────────────────────────────────────────────────────────────
        _logger.LogInformation(
            "C-041 ALLOW: Tool '{ToolName}' is authorized. TenantId={TenantId} ContractId={ContractId}",
            toolName, ctx.TenantId, ctx.ContractId);

        activity?.SetTag("verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason:  $"C-041: Tool '{toolName}' is present in the contract's authorized_actions list."));
    }

    // ── Private helpers ───────────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Returns true only when toolName appears in the authorized list.
    /// Supports JSON array (primary) and comma-separated fallback for defensive parsing.
    /// Returns false — deny — on any parse failure (fail-safe constitution enforcement).
    /// </summary>
    private static bool IsToolAuthorized(string toolName, string? authorizedActionsRaw)
    {
        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
            return false; // no authorized_actions declared → default deny (C-041)

        var trimmed = authorizedActionsRaw.TrimStart();

        // Primary: JSON array — expected contract format
        if (trimmed.StartsWith('['))
            return TryParseJsonArray(authorizedActionsRaw, toolName);

        // Defensive fallback: comma-separated plain text list
        // DESIGN_QUESTION: Should the comma-separated fallback be removed to enforce
        //                  strict JSON-only contract parameters? Flag for EA review.
        return authorizedActionsRaw
            .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Any(entry => string.Equals(entry, toolName, StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>
    /// C-073: Parse a JSON array and test for tool name membership (case-insensitive).
    /// Returns false on any JsonException — fail-safe = deny (C-041 default deny).
    /// </summary>
    private static bool TryParseJsonArray(string jsonArray, string toolName)
    {
        try
        {
            using var doc = JsonDocument.Parse(jsonArray);

            if (doc.RootElement.ValueKind != JsonValueKind.Array)
                return false; // malformed — not an array → deny

            foreach (var element in doc.RootElement.EnumerateArray())
            {
                if (element.ValueKind == JsonValueKind.String &&
                    string.Equals(element.GetString(), toolName, StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }

            return false; // tool not found in array → deny
        }
        catch (JsonException)
        {
            // Malformed JSON — fail safe: deny (C-041 default deny applies)
            return false;
        }
    }

    /// <summary>C-073: Convenience factory for a Deny result carrying ClaimId.</summary>
    private EvaluationResult Deny(string reason) =>
        new(ClaimId: ClaimId, Verdict: EvaluationVerdict.Deny, Reason: reason);
}