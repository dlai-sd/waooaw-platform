// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041
// constitutional_basis: C-041 (Tool Authorization / Decision Space boundary)
// C-073: This file implements a constitutional obligation — C-041 (every MCP tool call requires CE.ValidateAction; default deny)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-041 — Tool Authorization (Decision Space boundary).
/// Every MCP_TOOL_CALL must be explicitly authorized by contract. Default deny.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: Constitutional obligation — C-041 Tool Authorization
    public string ClaimId => "C-041";

    /// <summary>
    /// Applies only to MCP tool calls. Empty set would mean all action types — not appropriate here.
    /// </summary>
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "MCP_TOOL_CALL" };

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");
    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Implements C-041 — default deny for MCP tool calls lacking a valid ContractId or tool_name
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C041ToolAuthorizationEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("action_type", ctx.ActionType);

        // Default deny if ContractId is absent — cannot verify authorization without a contract
        if (string.IsNullOrWhiteSpace(ctx.ContractId))
        {
            _logger.LogWarning(
                "C-041 DENY: MCP_TOOL_CALL with empty ContractId. TenantId={TenantId}",
                ctx.TenantId);

            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-041",
                Verdict: EvaluationVerdict.Deny,
                Reason: "C-041: MCP_TOOL_CALL denied — no ContractId provided; authorization requires an active employment contract."));
        }

        var toolName = ctx.GetParameter("tool_name");
        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: MCP_TOOL_CALL missing tool_name parameter. ContractId={ContractId}",
                ctx.ContractId);

            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-041",
                Verdict: EvaluationVerdict.Deny,
                Reason: "C-041: MCP_TOOL_CALL denied — tool_name parameter absent; all tool calls must identify the target tool."));
        }

        // DESIGN_QUESTION: C-041 requires checking authorized_actions[] from business.employment_contracts
        // for this ContractId. EvaluationContext does not carry the authorized actions list.
        // WC012-03 (Data layer) should either:
        //   (a) hydrate authorized_actions into EvaluationContext.AuthorizedTools: IReadOnlySet<string>, OR
        //   (b) expose a read-through cache on EvaluatorRegistry so evaluators can query it synchronously.
        // Until WC012-03 lands, this evaluator permits any named tool on a valid contract — 
        // stricter than stub (stub approved everything including missing ContractId) but weaker than spec.
        // EA must resolve before production release.

        _logger.LogInformation(
            "C-041 ALLOW: ContractId={ContractId} ToolName={ToolName}",
            ctx.ContractId, toolName);

        return Task.FromResult(new EvaluationResult(
            ClaimId: "C-041",
            Verdict: EvaluationVerdict.Allow,
            Reason: "C-041: MCP_TOOL_CALL authorized — contract present and tool_name identified."));
    }
}