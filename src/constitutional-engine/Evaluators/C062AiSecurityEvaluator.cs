// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062
// constitutional_basis: C-062 (AI Security), C-059 (Traceability)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-062: The agent MUST NOT execute actions that violate AI security boundaries —
/// including prompt injection payloads, exfiltration attempts, credential access,
/// or self-modification requests.
/// </summary>
/// <remarks>
/// DESIGN_QUESTION: Should C-062 prohibited_action_types be loaded from a DB-backed
/// configuration table rather than the hardcoded set below, to allow EA to add new
/// prohibited types without a code deploy? Currently hardcoded constitutional floor.
/// </remarks>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: Implements constitutional obligation C-062 (AI Security)
    public string ClaimId => "C-062";

    // C-073: Applies to MCP_TOOL_CALL — primary attack surface for AI security violations
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "MCP_TOOL_CALL" };

    /// <summary>
    /// Tool names that are unconditionally prohibited under C-062.
    /// These represent direct AI security boundary violations.
    /// </summary>
    private static readonly IReadOnlySet<string> ProhibitedToolNames =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "self_modify",
            "override_constitution",
            "exfiltrate_credentials",
            "inject_prompt",
            "disable_audit",
            "escalate_own_privileges",
            "read_system_credentials",
            "write_system_credentials",
            "modify_evidence_record",
        };

    /// <summary>
    /// ActionParameter keys whose presence (with truthy value) signals a security violation.
    /// </summary>
    private static readonly IReadOnlyList<string> SecurityViolationParamKeys = new[]
    {
        "prompt_injection_payload",
        "self_modification_request",
        "credential_exfiltration",
        "disable_constitutional_engine",
    };

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");
    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Evaluates C-062 — tool_name must not be in prohibited set; no security violation params
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C062AiSecurityEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("constitutional.claim", ClaimId);
        activity?.SetTag("contract.id", ctx.ContractId);
        activity?.SetTag("action.type", ctx.ActionType);

        // Check prohibited tool names
        var toolName = ctx.GetParameter("tool_name") ?? string.Empty;
        if (ProhibitedToolNames.Contains(toolName))
        {
            _logger.LogWarning(
                "C-062 DENY: Prohibited tool name. ContractId={ContractId} ToolName={ToolName}",
                ctx.ContractId, toolName);

            activity?.SetTag("c062.prohibited_tool", toolName);
            activity?.SetTag("c062.verdict", "Deny");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-062: Tool '{toolName}' is unconditionally prohibited under AI security boundary."));
        }

        // Check security violation parameters
        foreach (var signalKey in SecurityViolationParamKeys)
        {
            var value = ctx.GetParameter(signalKey);
            if (!string.IsNullOrWhiteSpace(value) &&
                !value.Equals("false", StringComparison.OrdinalIgnoreCase) &&
                !value.Equals("0", StringComparison.Ordinal))
            {
                _logger.LogWarning(
                    "C-062 DENY: Security violation parameter. ContractId={ContractId} " +
                    "ParamKey={ParamKey} ActionType={ActionType}",
                    ctx.ContractId, signalKey, ctx.ActionType);

                activity?.SetTag("c062.security_signal", signalKey);
                activity?.SetTag("c062.verdict", "Deny");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: Security violation signal '{signalKey}' detected. " +
                    "Action denied on AI security grounds."));
            }
        }

        _logger.LogInformation(
            "C-062 ALLOW: No security violations. ContractId={ContractId} ToolName={ToolName}",
            ctx.ContractId, toolName);

        activity?.SetTag("c062.verdict", "Allow");
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-062: AI security boundary check passed."));
    }
}