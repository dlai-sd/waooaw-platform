// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-041, C-059
using Microsoft.Extensions.Logging;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 (Tool Authorization): only explicitly authorized action types may proceed.
/// Default deny principle — any action type not in the approved set returns DENY.
/// Constitutional basis: C-041 (Tool Authorization), C-059 (Implementation Traceability)
/// ADR reference: ADR-001 (gRPC Constitutional Engine), ADR-020 (MCP pattern)
/// Purpose: Evaluates whether a proposed MCP tool call is within the customer's Decision Space.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-041: The authorized action types are the constitutional floor.
    // Any action type not in this set is denied by default (unlisted = unauthorized).
    private static readonly IReadOnlySet<string> AllowedActionTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "MARKETING_POST",
            "CALENDAR_INVITE",
            "TRADE_ORDER",
            "SCOPE_BOUNDARY_CONFIRMATION",
            "AUTHORITY_GRANT",
            "EMERGENCY_STOP",
            "SEND_EMAIL",
            "CREATE_DOCUMENT",
            "READ_CALENDAR",
            "UPDATE_CALENDAR",
            "READ_EMAIL",
            "SEARCH_WEB",
            "CREATE_TASK",
            "UPDATE_TASK",
        };

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    /// <inheritdoc />
    public string ClaimId => "C-041";

    /// <inheritdoc />
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        try
        {
            ct.ThrowIfCancellationRequested();

            if (string.IsNullOrWhiteSpace(ctx.ActionType))
            {
                _logger.LogWarning(
                    "C-041: Empty ActionType on contract {ContractId} — default deny applies",
                    ctx.ContractId);

                return Task.FromResult(new EvaluationResult(
                    "C-041",
                    EvaluationVerdict.Deny,
                    "C-041: ActionType is empty — default deny applies. All tools must be explicitly authorized."));
            }

            // Check for an explicit MCP tool_name parameter first (ADR-020 MCP pattern).
            // If provided, it takes precedence over the top-level ActionType for authorization.
            var toolName = ctx.GetParameter("tool_name");
            var effectiveAction = !string.IsNullOrWhiteSpace(toolName) ? toolName : ctx.ActionType;

            if (!AllowedActionTypes.Contains(effectiveAction))
            {
                _logger.LogWarning(
                    "C-041: Action '{EffectiveAction}' (ActionType={ActionType}, tool_name={ToolName}) " +
                    "on contract {ContractId} is not in the authorized list — DENY",
                    effectiveAction,
                    ctx.ActionType,
                    toolName ?? "(not set)",
                    ctx.ContractId);

                return Task.FromResult(new EvaluationResult(
                    "C-041",
                    EvaluationVerdict.Deny,
                    $"C-041: Action '{effectiveAction}' is not in the authorized action list. " +
                    "Default deny applies — all tools must be explicitly authorized by the customer's Decision Space."));
            }

            _logger.LogDebug(
                "C-041: Action '{EffectiveAction}' on contract {ContractId} — ALLOW",
                effectiveAction,
                ctx.ContractId);

            return Task.FromResult(new EvaluationResult(
                "C-041",
                EvaluationVerdict.Allow,
                $"C-041: Action '{effectiveAction}' is within the authorized tool set."));
        }
        catch (OperationCanceledException)
        {
            // Propagate cancellation — do not log as an error; this is a normal shutdown path.
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(
                ex,
                "C-041: EvaluateAsync failed unexpectedly for contract {ContractId}, ActionType={ActionType}",
                ctx.ContractId,
                ctx.ActionType);

            // Re-throw: callers must not receive a silent Allow on evaluator failure.
            // C-059 error handling obligation: never swallow exceptions that affect authorization.
            throw;
        }
    }
}