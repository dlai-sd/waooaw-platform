// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041
// constitutional_basis: C-041 (Tool Authorization / Decision Space boundary), C-059 (Traceability)

#nullable enable

using Microsoft.Extensions.Logging;
using System.Diagnostics;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-041: Every MCP tool call must be authorized within the agent's Decision Space.
/// Default-deny: any request lacking a ContractId or a declared tool name is rejected.
/// Full authorized_actions[] cross-check against employment contracts is performed
/// by the data layer introduced in WC012-03; this evaluator enforces the structural
/// pre-conditions that must pass before a DB lookup is warranted.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-073: Constitutional obligation annotation
    // Enforces C-041 — every MCP tool call requires CE.ValidateAction; default deny.

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");
    private static readonly IReadOnlySet<string> _actionTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "MCP_TOOL_CALL" };

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public string ClaimId => "C-041";
    public IReadOnlySet<string> ApplicableActionTypes => _actionTypes;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc/>
    // C-073: Implements C-041 — tool authorization boundary enforcement.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C041.EvaluateAsync", ActivityKind.Internal);
        activity?.SetTag("claim", ClaimId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId ?? "<null>");

        // C-041: Default deny — no ContractId means no employment contract boundary established.
        if (string.IsNullOrWhiteSpace(ctx.ContractId))
        {
            _logger.LogWarning(
                "C-041 DENY: ContractId absent for action_type={ActionType} skill_id={SkillId}",
                ctx.ActionType, ctx.SkillId);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: No active employment contract identified. Tool calls require a bound ContractId."));
        }

        // C-041: tool_name must be declared in the request parameters.
        if (!ctx.ActionParameters.TryGetValue("tool_name", out var toolName)
            || string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: tool_name missing from ActionParameters. ContractId={ContractId}",
                ctx.ContractId);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-041: ActionParameters must contain 'tool_name'. Unidentified tool calls are denied."));
        }

        // DESIGN_QUESTION: Full authorized_actions[] lookup against business.employment_contracts
        // requires DB access (WC012-03). Until that evaluator layer is wired, structural
        // pre-conditions above are the enforced boundary. Flag for EA review when WC012-03 lands.

        activity?.SetTag("tool_name", toolName);
        _logger.LogInformation(
            "C-041 ALLOW: ContractId={ContractId} tool_name={ToolName}",
            ctx.ContractId, toolName);

        return Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow,
            "C-041: Structural pre-conditions met."));
    }
}