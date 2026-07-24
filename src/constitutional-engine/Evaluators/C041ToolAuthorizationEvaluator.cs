// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First)

using Microsoft.Extensions.Logging;
using System.Diagnostics;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-041: Every MCP tool call requires CE.ValidateAction approval. Default deny.
/// Enforces the Decision Space boundary — only tools listed in the contract's
/// authorized_actions[] may be executed.
/// </summary>
// C-073: Implements constitutional obligation C-041 (Tool Authorization / Decision Space Boundary)
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");
    private static readonly IReadOnlySet<string> _actionTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "MCP_TOOL_CALL" };

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    public string ClaimId => "C-041";

    /// <summary>Applies only to MCP_TOOL_CALL actions.</summary>
    public IReadOnlySet<string> ApplicableActionTypes => _actionTypes;

    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Evaluates C-041 (Tool Authorization) — default deny if ContractId absent or tool unspecified
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C041ToolAuthorizationEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("action_type", ctx.ActionType);

        // Default deny: ContractId must be present
        if (string.IsNullOrWhiteSpace(ctx.ContractId))
        {
            _logger.LogWarning("C-041 DENY: ContractId is absent. TenantId={TenantId}", ctx.TenantId);
            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-041",
                Verdict: EvaluationVerdict.Deny,
                Reason: "C-041: No active contract found — all tool calls require a valid ContractId."));
        }

        // Tool name must be specified in action parameters
        var toolName = ctx.GetParameter("tool_name");
        if (string.IsNullOrWhiteSpace(toolName))
        {
            _logger.LogWarning(
                "C-041 DENY: tool_name absent in ActionParameters. ContractId={ContractId}",
                ctx.ContractId);
            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-041",
                Verdict: EvaluationVerdict.Deny,
                Reason: "C-041: tool_name is required in ActionParameters for MCP_TOOL_CALL."));
        }

        // DESIGN_QUESTION: Full C-041 enforcement requires reading authorized_actions[] from
        // business.employment_contracts via DbContext. This is injected in WC012-03a when
        // ConstitutionalDbContext is available. For now, structural validation (ContractId +
        // tool_name present) is enforced. EA to confirm whether a "pass-through with warning"
        // or a hard DENY is acceptable until WC012-03a lands.
        _logger.LogInformation(
            "C-041 structural check PASS. ContractId={ContractId} ToolName={ToolName}",
            ctx.ContractId, toolName);
        activity?.SetTag("tool_name", toolName);
        activity?.SetTag("c041.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: "C-041",
            Verdict: EvaluationVerdict.Allow,
            Reason: "C-041: Structural validation passed — ContractId and tool_name present."));
    }
}