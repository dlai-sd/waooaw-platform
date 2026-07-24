// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041
// constitutional_basis: C-041 (Tool Authorization — Decision Space boundary)
// C-073: Every method in this file implements a constitutional obligation.

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-041 Evaluator — Tool Authorization (Decision Space boundary).
/// Enforces that every MCP tool call names a non-empty tool and that the tool name
/// does not appear on the static deny-list of universally prohibited tools.
/// 
/// DESIGN_QUESTION: Full authorization requires reading tenant's employment contract
/// authorized_actions[] from the DB (business.employment_contracts). That read is
/// deferred to WC012-03a when ConstitutionalDbContext is available. Until then this
/// evaluator enforces structural validity + the static deny-list. EA to confirm
/// whether a "contract not found → DENY" default should fire here or in WC012-03a.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-073: Static deny-list — tools universally prohibited across all tenants (C-041, C-062 overlap).
    private static readonly IReadOnlySet<string> _prohibitedTools = new HashSet<string>(
        StringComparer.OrdinalIgnoreCase)
    {
        "shell_exec",
        "bash",
        "powershell",
        "cmd",
        "eval",
        "exec",
        "system",
        "os_exec",
        "delete_all",
        "drop_database",
    };

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc/>
    public string ClaimId => "C-041";

    /// <inheritdoc/>
    // C-073: Applies only to MCP_TOOL_CALL actions per C-041 scope.
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "MCP_TOOL_CALL" };

    /// <inheritdoc/>
    // C-073: Enforces C-041 — every MCP tool call must name an authorized, non-prohibited tool.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C041ToolAuthorizationEvaluator.EvaluateAsync");
        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("action_type", ctx.ActionType);

        // Default deny — empty ContractId means no valid contract context.
        if (string.IsNullOrWhiteSpace(ctx.ContractId))
        {
            _logger.LogWarning(
                "C-041 DENY: ContractId is empty. ActionType={ActionType} TenantId={TenantId}",
                ctx.ActionType, ctx.TenantId);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: ContractId is required for MCP tool authorization. Default deny."));
        }

        var toolName = ctx.GetParameter("tool_name");

        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: tool_name parameter absent. ContractId={ContractId}",
                ctx.ContractId);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: MCP tool call must specify a non-empty tool_name parameter."));
        }

        if (_prohibitedTools.Contains(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: tool_name={ToolName} is on the universal prohibit list. ContractId={ContractId}",
                toolName, ctx.ContractId);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-041: Tool '{toolName}' is universally prohibited across all decision spaces."));
        }

        // DESIGN_QUESTION: Validate tool_name against employment_contracts.authorized_actions[]
        // once ConstitutionalDbContext is available (WC012-03a). For now, structural checks pass.

        _logger.LogDebug(
            "C-041 ALLOW: tool_name={ToolName} ContractId={ContractId}",
            toolName, ctx.ContractId);

        activity?.SetTag("tool_name", toolName);
        activity?.SetTag("verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-041: Tool name present and not on universal prohibit list."));
    }
}