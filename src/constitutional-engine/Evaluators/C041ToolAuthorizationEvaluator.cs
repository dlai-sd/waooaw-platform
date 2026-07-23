// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-059 (Traceability), C-073 (Annotation)

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-041 — Tool Authorization evaluator.
/// Every MCP tool call requires CE.ValidateAction. Default deny.
/// A tool is authorized only if it appears in the tenant's active contract's
/// authorized_actions[] array.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    // C-073: ClaimId is a constitutional obligation — links runtime enforcement to the claim.
    public string ClaimId => "C-041";

    // C-073: Applies only to MCP_TOOL_CALL — default deny for unknown tools.
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "MCP_TOOL_CALL" };

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    /// <inheritdoc />
    // C-073: EvaluateAsync implements C-041 — Tool Authorization (Decision Space boundary).
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // No active contract → default deny (C-041: default deny).
        if (ctx.ActiveContract is null)
        {
            _logger.LogWarning(
                "C-041 DENY: TenantId={TenantId} has no active employment contract",
                ctx.TenantId);

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: "No active employment contract — tool calls are not authorized (C-041 default deny).",
                EvidenceHint: $"TenantId={ctx.TenantId}"));
        }

        // No tool name provided → deny (cannot authorize an unnamed tool).
        if (string.IsNullOrWhiteSpace(ctx.ToolName))
        {
            _logger.LogWarning(
                "C-041 DENY: TenantId={TenantId} MCP_TOOL_CALL with no ToolName",
                ctx.TenantId);

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: "MCP_TOOL_CALL must specify a tool name (C-041 default deny).",
                EvidenceHint: $"TenantId={ctx.TenantId}"));
        }

        var authorizedActions = ctx.ActiveContract.AuthorizedActions
            ?? Array.Empty<string>();

        // C-073: Tool must appear in contract's authorized_actions[] — default deny otherwise.
        var isAuthorized = Array.Exists(
            authorizedActions,
            a => string.Equals(a, ctx.ToolName, StringComparison.OrdinalIgnoreCase));

        if (!isAuthorized)
        {
            _logger.LogWarning(
                "C-041 DENY: TenantId={TenantId} ToolName={ToolName} not in authorized_actions",
                ctx.TenantId,
                ctx.ToolName);

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"Tool '{ctx.ToolName}' is not in the tenant's authorized_actions list (C-041 default deny).",
                EvidenceHint: $"TenantId={ctx.TenantId}, ToolName={ctx.ToolName}"));
        }

        _logger.LogDebug(
            "C-041 AUTHORIZED: TenantId={TenantId} ToolName={ToolName}",
            ctx.TenantId,
            ctx.ToolName);

        return Task.FromResult(new EvaluationResult(EvaluationDecision.Authorized));
    }
}