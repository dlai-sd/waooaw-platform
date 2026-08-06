// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-001, C-003, C-023, C-041, C-059
using Grpc.Core;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 (Tool Authorization): only explicitly authorized action types within
/// the customer's Decision Space may proceed. Default deny — unlisted action type = DENY.
///
/// Constitutional basis: C-041 (Tool Authorization)
/// Spec: architecture/reference/ce-validate-action-evaluators.md
/// ADR: ADR-001 (gRPC Constitutional Engine)
///
/// Decision logic (evaluated in order):
///   1. ActionType absent or empty                       → DENY  (no anonymous invocations)
///   2. ActionType in prohibited_actions parameter       → DENY  (absolute prohibition)
///   3. ActionType in always_ask_actions parameter       → ESCALATE (route to customer)
///   4. ActionType in authorized_actions parameter       → Allow
///   5. ActionType not found (or no list present)        → DENY  (default deny, C-041)
///   6. Evaluator error                                  → DENY  (fail closed, C-041)
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // ActionParameters JSON keys — populated by EvaluatorRegistry from Decision Space cache
    private const string AuthorizedActionsKey  = "authorized_actions";
    private const string ProhibitedActionsKey  = "prohibited_actions";
    private const string AlwaysAskActionsKey   = "always_ask_actions";
    private const string ToolNameKey           = "tool_name";

    // C-041 is scoped to MCP tool calls only; all other action types default-deny
    private const string McpToolCallActionType = "MCP_TOOL_CALL";

    // C-041: constitutional floor — no tool invocation may pass without an explicit allow
    private const string DenyReasonNoActionType  =
        "C-041: ActionType must be specified. No anonymous tool invocations are permitted.";
    private const string DenyReasonNoList        =
        "C-041: No authorized_actions list present in Decision Space context. Default deny applied.";

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    /// <inheritdoc />
    public string ClaimId => "C-041";

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    /// <summary>
    /// Evaluates whether <paramref name="ctx"/>.ActionType is within the customer's
    /// authorized Decision Space. Default deny: unlisted tool = DENY (C-041).
    /// Must complete within its share of the 40 ms ValidateAction budget (ADR-001).
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        try
        {
            ct.ThrowIfCancellationRequested();

            // ── Guard: ActionType must be present ──────────────────────────────────────
            if (string.IsNullOrWhiteSpace(ctx.ActionType))
            {
                _logger.LogWarning(
                    "C-041 DENY: ActionType is null or empty. " +
                    "ContractId={ContractId} TenantId={TenantId}",
                    ctx.ContractId, ctx.TenantId);

                return Task.FromResult(
                    new EvaluationResult(ClaimId, EvaluationVerdict.Deny, DenyReasonNoActionType));
            }

            var actionType = ctx.ActionType.Trim();

            // ── Guard: C-041 is scoped to MCP_TOOL_CALL only ──────────────────────────
            if (!string.Equals(actionType, McpToolCallActionType, StringComparison.Ordinal))
            {
                _logger.LogWarning(
                    "C-041 DENY: ActionType={ActionType} is not MCP_TOOL_CALL — outside C041 scope. " +
                    "ContractId={ContractId} TenantId={TenantId}",
                    actionType, ctx.ContractId, ctx.TenantId);

                return Task.FromResult(
                    new EvaluationResult(
                        ClaimId,
                        EvaluationVerdict.Deny,
                        $"C-041: ActionType '{actionType}' is not MCP_TOOL_CALL. " +
                        "C041 evaluates MCP tool invocations only. Default deny applied."));
            }

            // ── Extract tool_name from ActionParameters ────────────────────────────────
            var toolName = ctx.GetParameter(ToolNameKey);
            if (string.IsNullOrEmpty(toolName))
            {
                _logger.LogWarning(
                    "C-041 DENY: tool_name is null or empty. " +
                    "ContractId={ContractId} TenantId={TenantId}",
                    ctx.ContractId, ctx.TenantId);

                return Task.FromResult(
                    new EvaluationResult(
                        ClaimId,
                        EvaluationVerdict.Deny,
                        "C-041: tool_name must be specified in ActionParameters. No anonymous tool invocations are permitted."));
            }

            // ── Step 1: Prohibited actions (absolute — checked before allowed list) ────
            var prohibitedRaw = ctx.GetParameter(ProhibitedActionsKey);
            if (!string.IsNullOrWhiteSpace(prohibitedRaw))
            {
                var prohibited = ParseActionList(prohibitedRaw);
                if (ContainsOrdinal(prohibited, toolName))
                {
                    _logger.LogWarning(
                        "C-041 DENY: ActionType={ActionType} is explicitly prohibited. " +
                        "ContractId={ContractId} TenantId={TenantId}",
                        actionType, ctx.ContractId, ctx.TenantId);

                    return Task.FromResult(
                        new EvaluationResult(
                            ClaimId,
                            EvaluationVerdict.Deny,
                            $"C-041: Action '{actionType}' is explicitly prohibited in the Decision Space."));
                }
            }

            // ── Step 2: Always-ask actions (boundary escalation) ──────────────────────
            var alwaysAskRaw = ctx.GetParameter(AlwaysAskActionsKey);
            if (!string.IsNullOrWhiteSpace(alwaysAskRaw))
            {
                var alwaysAsk = ParseActionList(alwaysAskRaw);
                if (ContainsOrdinal(alwaysAsk, toolName))
                {
                    _logger.LogInformation(
                        "C-041 ESCALATE: tool_name={ToolName} requires customer confirmation. " +
                        "ContractId={ContractId} TenantId={TenantId}",
                        toolName, ctx.ContractId, ctx.TenantId);

                    return Task.FromResult(
                        new EvaluationResult(
                            ClaimId,
                            EvaluationVerdict.Escalate,
                            $"C-041: Tool '{toolName}' is at a scope boundary — " +
                            "explicit customer confirmation required (always-ask)."));
                }
            }

            // ── Step 3: Authorized actions — default deny if list absent or unlisted ──
            var authorizedRaw = ctx.GetParameter(AuthorizedActionsKey);
            if (string.IsNullOrWhiteSpace(authorizedRaw))
            {
                _logger.LogWarning(
                    "C-041 DENY (default): No '{Key}' parameter in context. " +
                    "ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
                    AuthorizedActionsKey, ctx.ContractId, actionType, ctx.TenantId);

                return Task.FromResult(
                    new EvaluationResult(ClaimId, EvaluationVerdict.Deny, DenyReasonNoList));
            }

            var authorized = ParseActionList(authorizedRaw);
            if (!ContainsOrdinal(authorized, toolName))
            {
                _logger.LogWarning(
                    "C-041 DENY (default): tool_name={ToolName} not in authorized list. " +
                    "ContractId={ContractId} TenantId={TenantId}",
                    toolName, ctx.ContractId, ctx.TenantId);

                return Task.FromResult(
                    new EvaluationResult(
                        ClaimId,
                        EvaluationVerdict.Deny,
                        $"C-041: Tool '{toolName}' is not listed in the authorized Decision Space. " +
                        "Default deny applied."));
            }

            // ── All checks passed — tool is constitutionally authorized ───────────────
            _logger.LogDebug(
                "C-041 Allow: tool_name={ToolName} is authorized by Decision Space. " +
                "ContractId={ContractId} TenantId={TenantId}",
                toolName, ctx.ContractId, ctx.TenantId);

            return Task.FromResult(
                new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Allow,
                    $"C-041: Tool '{toolName}' is within the authorized Decision Space."));
        }
        catch (OperationCanceledException)
        {
            // Propagate cancellation — do not swallow (ERROR HANDLING RULE 1 / C-059)
            throw;
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1: log before failing; C-041: fail closed on evaluator error
            _logger.LogError(
                ex,
                "C-041 evaluation failed: {Context}",
                $"ContractId={ctx.ContractId} ActionType={ctx.ActionType} TenantId={ctx.TenantId}");

            return Task.FromResult(
                new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-041: Evaluator error — failing closed per default-deny principle. {ex.Message}"));
        }
    }

    // ── Private helpers ───────────────────────────────────────────────────────────────

    /// <summary>
    /// Parses a comma- or semicolon-delimited action list from a raw parameter string.
    /// Whitespace is trimmed from each entry; empty entries are dropped.
    /// </summary>
    private static IReadOnlyList<string> ParseActionList(string raw)
        => raw.Split(
                new[] { ',', ';' },
                StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .ToList();

    /// <summary>
    /// Exact (case-sensitive, ordinal) membership test — tool names are case-sensitive identifiers.
    /// </summary>
    private static bool ContainsOrdinal(IReadOnlyList<string> list, string value)
    {
        foreach (var item in list)
        {
            if (string.Equals(item, value, StringComparison.Ordinal))
                return true;
        }
        return false;
    }
}