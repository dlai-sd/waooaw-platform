// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Constitutional Annotation)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-041 Evaluator — Tool Authorization (Decision Space boundary).
///
/// Constitutional obligation: every MCP tool call must appear in the tenant's
/// authorized_actions list.  If the tool is absent, or the list is missing or
/// malformed, the evaluator returns DENY.  This is a hard default-deny boundary —
/// no tool is permitted unless explicitly listed.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource — every constitutional evaluation emits an OTel span.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // ── IClaimEvaluator ──────────────────────────────────────────────────────

    /// <inheritdoc/>
    /// C-073: Returns "C-041" — the constitutional claim this evaluator enforces.
    public string ClaimId => "C-041";

    /// <inheritdoc/>
    /// <remarks>
    /// C-073: Constitutional obligation — enforces C-041 Tool Authorization.
    ///
    /// Algorithm:
    ///   1. Extract "tool_name" from the JSON-encoded ActionParameters.
    ///   2. If tool_name is null/empty/whitespace → DENY (default deny applies).
    ///   3. Extract "authorized_actions" JSON array from ActionParameters.
    ///   4. If the array is absent, empty, malformed, or does not contain
    ///      the exact tool_name string → DENY.
    ///   5. Tool found in list → Allow.
    ///
    /// MUST NOT perform network I/O — all evaluation is synchronous/in-memory.
    /// </remarks>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Start OTel span for constitutional tracing (C-059).
        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("constitutional.claim_id", ClaimId);
        activity?.SetTag("tenant.id", ctx.TenantId);
        activity?.SetTag("action.type", ctx.ActionType);
        activity?.SetTag("contract.id", ctx.ContractId);

        // ── Step 1: Resolve tool_name ────────────────────────────────────────
        // C-073: ActionParameters is JSON-encoded — always use GetParameter(), never TryGetValue().
        var toolName = ctx.GetParameter("tool_name");

        if (string.IsNullOrWhiteSpace(toolName))
        {
            // C-073: Missing or blank tool_name — C-041 default deny.
            _logger.LogWarning(
                "C-041 DENY: tool_name parameter is missing or blank. " +
                "TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
                ctx.TenantId, ctx.ContractId, ctx.ActionType);

            activity?.SetTag("constitutional.verdict", "Deny");
            activity?.SetTag("constitutional.deny_reason", "tool_name_missing");

            return Task.FromResult(
                Deny("C-041: tool_name is required for every MCP tool call — default deny applies."));
        }

        activity?.SetTag("tool.name", toolName);

        // ── Step 2: Resolve authorized_actions ───────────────────────────────
        var authorizedActionsRaw = ctx.GetParameter("authorized_actions");

        if (!IsToolAuthorized(toolName, authorizedActionsRaw))
        {
            // C-073: Tool not listed → C-041 default deny.
            _logger.LogWarning(
                "C-041 DENY: Tool '{ToolName}' is not in the authorized_actions list. " +
                "TenantId={TenantId} ContractId={ContractId}",
                toolName, ctx.TenantId, ctx.ContractId);

            activity?.SetTag("constitutional.verdict", "Deny");
            activity?.SetTag("constitutional.deny_reason", "tool_not_authorized");

            return Task.FromResult(
                Deny($"C-041: Tool '{toolName}' is not present in the tenant's " +
                     "authorized_actions list — default deny applies."));
        }

        // ── Step 3: Tool is authorized ───────────────────────────────────────
        _logger.LogInformation(
            "C-041 ALLOW: Tool '{ToolName}' is authorized. " +
            "TenantId={TenantId} ContractId={ContractId}",
            toolName, ctx.TenantId, ctx.ContractId);

        activity?.SetTag("constitutional.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: $"C-041: Tool '{toolName}' is present in the tenant's authorized_actions list."));
    }

    // ── Private helpers ──────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Checks whether <paramref name="toolName"/> is present in the
    /// <paramref name="authorizedActionsRaw"/> JSON array.
    ///
    /// Returns <c>false</c> for any of:
    ///   • null / empty / whitespace raw value
    ///   • malformed JSON (default deny — never throw on bad input)
    ///   • JSON value is not an array
    ///   • tool not found in the array
    /// </summary>
    private static bool IsToolAuthorized(string toolName, string? authorizedActionsRaw)
    {
        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
            return false;

        return TryParseJsonArray(authorizedActionsRaw, toolName);
    }

    /// <summary>
    /// Parses <paramref name="jsonArray"/> and performs an exact-match search for
    /// <paramref name="toolName"/>.  Returns <c>false</c> on any <see cref="JsonException"/>
    /// so that malformed JSON always triggers the C-041 default deny rather than an
    /// unhandled exception.
    /// </summary>
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
                    && string.Equals(element.GetString(), toolName, StringComparison.Ordinal))
                {
                    return true;
                }
            }

            return false;
        }
        catch (JsonException)
        {
            // C-041: Malformed authorized_actions JSON → default deny.
            // Do NOT let a parse error bubble up — return false and let the
            // caller emit the DENY result with a clear constitutional reason.
            return false;
        }
    }

    /// <summary>
    /// Constructs a <see cref="EvaluationResult"/> with <see cref="EvaluationVerdict.Deny"/>
    /// attributed to this evaluator's <see cref="ClaimId"/>.
    /// </summary>
    private EvaluationResult Deny(string reason) =>
        new(ClaimId: ClaimId, Verdict: EvaluationVerdict.Deny, Reason: reason);
}