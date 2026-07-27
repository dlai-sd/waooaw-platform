// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Constitutional Annotation)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 Tool Authorization: every MCP tool call must reference a tool that
/// is explicitly present in the tenant contract's <c>authorized_actions</c> JSON array.
/// Decision space is DEFAULT DENY — an unlisted tool is always denied, even when the
/// list is non-empty or when no list is present at all.
/// </summary>
// C-073: Class-level annotation — this evaluator implements a binary runtime gate for C-041.
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // ── Telemetry ─────────────────────────────────────────────────────────────────────────
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // ── Dependencies ─────────────────────────────────────────────────────────────────────
    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    // ── Constructor ──────────────────────────────────────────────────────────────────────
    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // ── IClaimEvaluator ──────────────────────────────────────────────────────────────────

    // C-073: ClaimId identifies which constitutional claim this evaluator enforces.
    public string ClaimId => "C-041";

    /// <summary>
    /// Evaluates whether the requested tool is explicitly listed in the tenant contract's
    /// <c>authorized_actions</c> parameter. Returns <see cref="EvaluationVerdict.Deny"/>
    /// for any of the following conditions:
    /// <list type="bullet">
    ///   <item><description><c>tool_name</c> parameter is absent, null, or whitespace.</description></item>
    ///   <item><description><c>authorized_actions</c> parameter is absent, null, or whitespace.</description></item>
    ///   <item><description><c>authorized_actions</c> JSON is malformed.</description></item>
    ///   <item><description>The tool name is not present in the parsed <c>authorized_actions</c> array.</description></item>
    /// </list>
    /// </summary>
    // C-073: EvaluateAsync is the runtime constitutional gate for C-041 Tool Authorization.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C041.EvaluateToolAuthorization",
            ActivityKind.Internal);

        activity?.SetTag("constitutional.claim_id", ClaimId);
        activity?.SetTag("tenant_id",   ctx.TenantId);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("action_type", ctx.ActionType);

        // ── Step 1: tool_name must be present and non-blank ───────────────────────────────
        var toolName = ctx.GetParameter("tool_name");
        activity?.SetTag("tool_name", toolName ?? "<null>");

        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: tool_name parameter is absent or blank. " +
                "TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
                ctx.TenantId, ctx.ContractId, ctx.ActionType);

            activity?.SetTag("c041.decision", "deny");
            activity?.SetTag("c041.deny_reason", "missing_tool_name");

            return Task.FromResult(Deny(
                "C-041: tool_name parameter is required but was absent or blank."));
        }

        // ── Step 2: authorized_actions must be present and parseable ──────────────────────
        var authorizedActionsRaw = ctx.GetParameter("authorized_actions");

        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
        {
            _logger.LogWarning(
                "C-041 DENY: authorized_actions parameter is absent or blank — default deny applies. " +
                "TenantId={TenantId} ContractId={ContractId} ToolName={ToolName}",
                ctx.TenantId, ctx.ContractId, toolName);

            activity?.SetTag("c041.decision", "deny");
            activity?.SetTag("c041.deny_reason", "no_authorized_actions_list");

            return Task.FromResult(Deny(
                $"C-041: No authorized_actions list found for contract '{ctx.ContractId}'. " +
                "Default deny applies — tool calls require explicit authorization."));
        }

        // ── Step 3: tool_name must appear in the authorized_actions JSON array ─────────────
        bool authorized = IsToolAuthorized(toolName, authorizedActionsRaw);

        if (!authorized)
        {
            _logger.LogWarning(
                "C-041 DENY: tool '{ToolName}' is not present in authorized_actions. " +
                "TenantId={TenantId} ContractId={ContractId}",
                toolName, ctx.TenantId, ctx.ContractId);

            activity?.SetTag("c041.decision", "deny");
            activity?.SetTag("c041.deny_reason", "tool_not_in_authorized_list");

            return Task.FromResult(Deny(
                $"C-041: Tool '{toolName}' is not listed in the contract's authorized_actions. " +
                "Default deny applies."));
        }

        // ── Step 4: tool is authorized ────────────────────────────────────────────────────
        _logger.LogInformation(
            "C-041 ALLOW: tool '{ToolName}' is authorized. " +
            "TenantId={TenantId} ContractId={ContractId}",
            toolName, ctx.TenantId, ctx.ContractId);

        activity?.SetTag("c041.decision", "allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: $"C-041: Tool '{toolName}' is present in the contract's authorized_actions list."));
    }

    // ── Private helpers ──────────────────────────────────────────────────────────────────

    /// <summary>
    /// Returns <c>true</c> only when <paramref name="toolName"/> appears (case-insensitive)
    /// in the JSON array encoded in <paramref name="authorizedActionsRaw"/>.
    /// Any parse failure returns <c>false</c> (safe default deny).
    /// </summary>
    // C-073: IsToolAuthorized implements the Decision Space lookup for C-041.
    private static bool IsToolAuthorized(string toolName, string? authorizedActionsRaw)
    {
        if (string.IsNullOrWhiteSpace(authorizedActionsRaw))
            return false; // no list → nothing is authorized

        return TryParseJsonArray(authorizedActionsRaw, toolName);
    }

    /// <summary>
    /// Attempts to deserialize <paramref name="jsonArray"/> as a JSON string array and
    /// checks whether <paramref name="toolName"/> is a member (case-insensitive).
    /// Returns <c>false</c> on any <see cref="JsonException"/> — malformed JSON defaults to deny.
    /// </summary>
    // C-073: TryParseJsonArray safely deserializes the authorized_actions JSON payload.
    private static bool TryParseJsonArray(string jsonArray, string toolName)
    {
        try
        {
            var actions = JsonSerializer.Deserialize<string[]>(jsonArray);

            if (actions is null)
                return false;

            foreach (var action in actions)
            {
                if (string.Equals(action, toolName, StringComparison.OrdinalIgnoreCase))
                    return true;
            }

            return false;
        }
        catch (JsonException)
        {
            // Malformed JSON — constitutional safe default is deny.
            return false;
        }
    }

    // C-073: Deny helper produces a typed, immutable EvaluationResult with Deny verdict.
    private EvaluationResult Deny(string reason) =>
        new(ClaimId: ClaimId, Verdict: EvaluationVerdict.Deny, Reason: reason);
}