// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 Tool Authorization: every MCP tool call requires explicit authorization.
/// Default deny — any tool not positively identified as authorized is DENIED.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // C-059: ActivitySource for constitutional audit tracing (OpenTelemetry)
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    // C-073: Constructor satisfies DI; null guard enforces runtime safety
    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId identifies the constitutional claim this evaluator enforces
    /// <summary>Constitutional claim ID enforced by this evaluator.</summary>
    public string ClaimId => "C-041";

    // C-073: EvaluateAsync is the primary constitutional enforcement point for C-041.
    // Default deny: absence of a recognized tool name → DENY without exception.
    //
    // DESIGN_QUESTION(EA): Spec §C-041 mandates reading authorized_actions[] from
    // business.employment_contracts, but IClaimEvaluator prohibits network/DB I/O,
    // and EvaluationContext carries no AuthorizedTools collection. Until EvaluationContext
    // is extended (or a pre-evaluation DB hydration step is introduced in EvaluationContext.FromRequest),
    // this evaluator implements pure default-deny: any non-empty tool name is also denied
    // because no allowlist is available. EA must resolve before ALLOW paths can be opened.
    /// <summary>
    /// Evaluate whether the proposed MCP tool call is constitutionally authorized (C-041).
    /// Applies default-deny: missing/blank tool_name → DENY; any present tool name → DENY
    /// until an authorized_actions allowlist is available on <see cref="EvaluationContext"/>.
    /// MUST NOT perform network or DB I/O.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-059 / C-073: Open telemetry span covering the full evaluation
        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("constitutional.claim_id", ClaimId);
        activity?.SetTag("action.type",              ctx.ActionType);
        activity?.SetTag("tenant.id",                ctx.TenantId);
        activity?.SetTag("contract.id",              ctx.ContractId);

        // C-041: Extract tool_name from JSON-encoded ActionParameters.
        // ctx.GetParameter() parses the JSON string; never call TryGetValue() on ActionParameters.
        var toolName = ctx.GetParameter("tool_name");

        // C-041 §Default deny — null / empty / whitespace tool name
        if (string.IsNullOrWhiteSpace(toolName))
        {
            // C-073: Log every denial for C-023 (Evidence First) downstream recording
            _logger.LogWarning(
                "C-041 DENY: tool_name parameter is absent or blank. " +
                "ContractId={ContractId} TenantId={TenantId} ActionType={ActionType}",
                ctx.ContractId,
                ctx.TenantId,
                ctx.ActionType);

            activity?.SetTag("c041.verdict",     "Deny");
            activity?.SetTag("c041.deny_reason", "tool_name_missing");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason:  "C-041: tool_name parameter is required and must not be empty. Default deny applies."));
        }

        // C-041 §Default deny — tool present but not in an authorized list.
        // DESIGN_QUESTION(EA): Replace this block with an allowlist check once
        // EvaluationContext.AuthorizedTools (IReadOnlySet<string>) is available.
        _logger.LogWarning(
            "C-041 DENY: Tool '{ToolName}' is not in the contract authorized_actions list. " +
            "ContractId={ContractId} TenantId={TenantId} ActionType={ActionType}",
            toolName,
            ctx.ContractId,
            ctx.TenantId,
            ctx.ActionType);

        activity?.SetTag("c041.verdict",     "Deny");
        activity?.SetTag("c041.deny_reason", "tool_not_authorized");
        activity?.SetTag("c041.tool_name",   toolName);

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Deny,
            Reason:  $"C-041: Tool '{toolName}' is not present in the contract's authorized_actions list. Default deny applies."));
    }
}