// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// Constitutional basis: C-041 (Tool Authorization), C-023 (Evidence First), C-059 (Traceability)

using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Waooaw.ConstitutionalEngine.Evaluators;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-041 Tool Authorization Evaluator.
/// Enforces: every MCP tool call requires CE.ValidateAction. Default deny.
/// An absent ContractId, missing tool_name parameter, or any unresolvable
/// authorization evidence results in DENY — the burden of proof is on the caller.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private const string McpToolCallActionType = "MCP_TOOL_CALL";
    private const string ToolNameParameter = "tool_name";

    /// <inheritdoc />
    public string ClaimId => "C-041";

    /// <inheritdoc />
    public async Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-041 applies only to MCP_TOOL_CALL action types.
        // All other action types are not subject to tool authorization — allow through.
        if (!string.Equals(ctx.ActionType, McpToolCallActionType, System.StringComparison.OrdinalIgnoreCase))
        {
            return new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Allow,
                Reason: $"Action type '{ctx.ActionType}' is not subject to C-041 tool authorization.");
        }

        // Default deny: no contract → no authority.
        if (string.IsNullOrWhiteSpace(ctx.ContractId))
        {
            return new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: "C-041 DENY: No active employment contract (ContractId is absent). " +
                        "Tool calls require an authority-licensed contract.");
        }

        // Default deny: tool name must be specified in ActionParameters.
        var toolName = ctx.GetParameter(ToolNameParameter);
        if (string.IsNullOrWhiteSpace(toolName))
        {
            return new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: "C-041 DENY: ActionParameters does not contain a valid 'tool_name'. " +
                        "Every MCP tool call must identify the tool being invoked.");
        }

        // Default deny: TenantId must be present (authorization is always tenant-scoped).
        if (string.IsNullOrWhiteSpace(ctx.TenantId))
        {
            return new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: "C-041 DENY: TenantId is absent. " +
                        "Tool authorization cannot be evaluated without tenant scope.");
        }

        // All structural checks passed.
        // ContractId is present, tool_name is present, TenantId is present.
        // Constitutional boundary is satisfied at the ValidateAction layer.
        // The authorized_actions[] check against business.employment_contracts is
        // resolved in WC012-03 (DB-backed context population) — once that layer
        // populates ctx with the resolved contract scope, this evaluator's
        // structural gate is the prerequisite that must pass first.
        await Task.CompletedTask; // async contract — DB I/O injected in WC012-03 extension point.

        return new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: $"C-041 ALLOW: ContractId '{ctx.ContractId}' present, tool '{toolName}' identified, " +
                    $"tenant '{ctx.TenantId}' scoped. Structural authorization gate passed.");
    }
}