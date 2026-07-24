// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First), C-059 (Traceability)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-041: Every MCP tool call requires CE.ValidateAction. Default deny if tool_name is absent
/// or empty. Full contract authorized_actions[] enforcement is deferred to WC012-03 once the
/// DB layer is available.
/// </summary>
/// <remarks>
/// DESIGN_QUESTION: Should we short-circuit to Deny when ContractId is empty/whitespace,
/// or treat that as an Escalate (unknown tenant) for human review? Currently Deny.
/// </remarks>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: Implements constitutional obligation C-041 (Tool Authorization)
    public string ClaimId => "C-041";

    // C-073: Applies only to MCP_TOOL_CALL action type per C-041 decision space boundary
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "MCP_TOOL_CALL" };

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");
    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Evaluates C-041 — tool_name must be present and non-empty; ContractId must be non-empty
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C041ToolAuthorizationEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("constitutional.claim", ClaimId);
        activity?.SetTag("contract.id", ctx.ContractId);
        activity?.SetTag("action.type", ctx.ActionType);

        // Default deny: ContractId must be present
        if (string.IsNullOrWhiteSpace(ctx.ContractId))
        {
            _logger.LogWarning("C-041 DENY: ContractId is absent. ActionType={ActionType}", ctx.ActionType);
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: ContractId is required. Default deny — no employment contract identified."));
        }

        // tool_name parameter must be present and non-empty
        var toolName = ctx.GetParameter("tool_name");
        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: tool_name parameter absent or empty. ContractId={ContractId}",
                ctx.ContractId);
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: tool_name parameter is required for MCP_TOOL_CALL. Default deny."));
        }

        // DESIGN_QUESTION: WC012-03 will inject IContractRepository to check authorized_actions[].
        // Until then, structural validation only — presence of tool_name satisfies minimum gate.
        _logger.LogInformation(
            "C-041 ALLOW (structural gate only): ContractId={ContractId} ToolName={ToolName}",
            ctx.ContractId, toolName);

        activity?.SetTag("tool.name", toolName);
        activity?.SetTag("c041.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-041: tool_name present; structural gate passed."));
    }
}