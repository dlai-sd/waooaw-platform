// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-059 (Traceability), C-073 (Annotation)

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-062 — AI Security evaluator.
/// Denies MCP tool calls to tools that are on the prohibited-tools list.
/// Applies to MCP_TOOL_CALL action type.
/// </summary>
/// <remarks>
/// DESIGN_QUESTION: The prohibited tools list is currently hard-coded. EA should confirm
/// whether this list should be loaded from a DB table (constitutional.prohibited_tools)
/// or remain a compile-time constant for auditability.
/// </remarks>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: Prohibited tools list is a constitutional obligation under C-062.
    // These tools are unconditionally denied regardless of contract authorization.
    private static readonly HashSet<string> ProhibitedTools = new(StringComparer.OrdinalIgnoreCase)
    {
        "shell_exec",
        "arbitrary_code_exec",
        "filesystem_write_unrestricted",
        "network_exfiltrate",
        "credential_dump",
    };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    // C-073: ClaimId links runtime enforcement to C-062.
    public string ClaimId => "C-062";

    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "MCP_TOOL_CALL" };

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    /// <inheritdoc />
    // C-073: EvaluateAsync implements C-062 — AI Security prohibited-tool boundary.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        if (!string.IsNullOrWhiteSpace(ctx.ToolName) &&
            ProhibitedTools.Contains(ctx.ToolName))
        {
            _logger.LogWarning(
                "C-062 DENY: TenantId={TenantId} ToolName={ToolName} is on the prohibited-tools list",
                ctx.TenantId,
                ctx.ToolName);

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"Tool '{ctx.ToolName}' is on the C-062 prohibited-tools list — unconditional deny.",
                EvidenceHint: $"TenantId={ctx.TenantId}, ToolName={ctx.ToolName}"));
        }

        _logger.LogDebug(
            "C-062 AUTHORIZED: TenantId={TenantId} ToolName={ToolName} not prohibited",
            ctx.TenantId,
            ctx.ToolName);

        return Task.FromResult(new EvaluationResult(EvaluationDecision.Authorized));
    }
}