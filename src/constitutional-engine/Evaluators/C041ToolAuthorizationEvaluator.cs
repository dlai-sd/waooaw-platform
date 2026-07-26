// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-041 (Tool Authorization — Decision Space boundary).
/// Default deny: every MCP tool call is DENY unless the tool name appears
/// in the contract's authorized_actions list carried inside ActionParameters.
///
/// Short-circuit logic:
///   • tool_name missing or whitespace  → DENY (cannot evaluate what is not named)
///   • authorized_actions absent/empty  → DENY (no whitelist = no permission)
///   • tool_name ∉ authorized_actions   → DENY (explicit exclusion)
///   • tool_name ∈ authorized_actions   → ALLOW
///
/// This evaluator MUST NOT perform network I/O.
/// All data is sourced from the EvaluationContext built by ConstitutionalEngineService.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: Single ActivitySource shared across all CE evaluators
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        // C-073: Constructor validates all dependencies
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Identifies the constitutional claim this evaluator enforces
    public string ClaimId => "C-041";

    /// <summary>
    /// C-073: Evaluate whether the requested tool call is constitutionally authorized.
    ///
    /// Algorithm (C-041 default-deny):
    ///   1. Extract tool_name from ActionParameters JSON.
    ///   2. If absent/whitespace → DENY (cannot authorize an unnamed tool).
    ///   3. Extract authorized_actions JSON array from ActionParameters.
    ///   4. If absent/empty/malformed → DENY (no whitelist present = no permission).
    ///   5. If tool_name ∈ authorized_actions (case-sensitive) → ALLOW.
    ///   6. Otherwise → DENY.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: Guard — context must be non-null
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("constitutional.claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Step 1: Extract tool_name ──────────────────────────────────────────
        // C-073: ActionParameters is JSON-encoded — must use GetParameter(), never TryGetValue()
        var toolName = ctx.GetParameter("tool_name");

        activity?.SetTag("tool_name", toolName ?? "<absent>");

        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: tool_name parameter is absent or whitespace. " +
                "TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
                ctx.TenantId, ctx.ContractId, ctx.ActionType);

            activity?.SetTag("constitutional.decision", "DENY");
            activity?.SetTag("constitutional.deny_reason", "tool_name_missing");

            return Task.FromResult(Deny(
                "C-041: tool_name parameter is missing or empty — default deny applies"));
        }

        // ── Step 2: Extract authorized_actions whitelist ───────────────────────
        var authorizedActionsRaw = ctx.GetParameter("authorized_actions");

        activity?.SetTag("authorized_actions_present", authorizedActionsRaw != null);

        if (!IsToolAuthorized(toolName, authorizedActionsRaw))
        {
            _logger.LogWarning(
                "C-041 DENY: tool '{ToolName}' is not in authorized_actions. " +
                "TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
                toolName, ctx.TenantId, ctx.ContractId, ctx.ActionType);

            activity?.SetTag("constitutional.decision", "DENY");
            activity?.SetTag("constitutional.deny_reason", "tool_not_authorized");

            return Task.FromResult(Deny(
                $"C-041: tool '{toolName}' is not in the contract's authorized_actions list — default deny"));
        }

        // ── Step 3: Explicit allow ─────────────────────────────────────────────
        _logger.LogInformation(
            "C-041 ALLOW: tool '{ToolName}' is authorized. " +
            "TenantId={TenantId} ContractId={ContractId}",
            toolName, ctx.TenantId, ctx.ContractId);

        activity?.SetTag("constitutional.decision", "ALLOW");

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: $"C-041: tool '{toolName}' is present in the contract's authorized_actions list"));
    }

    // ── Private helpers ────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Returns true only when <paramref name="toolName"/> appears in the
    /// JSON-encoded <paramref name="authorizedActionsRaw"/> array.
    /// Any parse failure or absent whitelist returns false (default deny preserved).
    /// </summary>
    private static bool IsToolAuthorized(string toolName, string? authorizedActionsRaw)
    {
        // C-073: Absent or empty whitelist → deny (C-041 default deny)
        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
            return false;

        return TryParseJsonArray(authorizedActionsRaw, toolName);
    }

    /// <summary>
    /// C-073: Parse a JSON array string and check whether <paramref name="toolName"/>
    /// appears as a string element (case-sensitive ordinal comparison).
    /// Returns false on any JSON parse error — parse failure is treated as denial,
    /// not as an exception, so the evaluator never throws on malformed input.
    /// </summary>
    private static bool TryParseJsonArray(string jsonArray, string toolName)
    {
        try
        {
            using var doc = JsonDocument.Parse(jsonArray);

            // C-073: Root must be a JSON array — anything else is malformed → deny
            if (doc.RootElement.ValueKind != JsonValueKind.Array)
                return false;

            foreach (var element in doc.RootElement.EnumerateArray())
            {
                if (element.ValueKind == JsonValueKind.String &&
                    string.Equals(element.GetString(), toolName, StringComparison.Ordinal))
                {
                    return true;
                }
            }

            return false;
        }
        catch (JsonException)
        {
            // C-073: Malformed JSON in authorized_actions → treat as no whitelist → deny
            return false;
        }
    }

    /// <summary>Convenience factory — always sets ClaimId to this evaluator's claim.</summary>
    private EvaluationResult Deny(string reason) =>
        new(ClaimId: ClaimId, Verdict: EvaluationVerdict.Deny, Reason: reason);
}