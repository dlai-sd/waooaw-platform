// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security — prohibited tool invocations)

#nullable enable

using Microsoft.Extensions.Logging;
using System.Diagnostics;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-062 — prohibited AI security boundary violations.
/// Blocks tools and action patterns that bypass security controls.
/// Applies to ALL action types.
/// </summary>
public sealed class C062AISecurityEvaluator : IClaimEvaluator
{
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // DESIGN_QUESTION: Security-prohibited tool list should be centrally managed and
    // versioned in constitutional configuration. This is the minimum safe baseline.
    internal static readonly IReadOnlySet<string> SecurityProhibitedTools =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "execute_shell",
            "run_arbitrary_code",
            "modify_constitution",
            "disable_audit_log",
            "bypass_authentication",
            "access_raw_model_weights",
            "exfiltrate_training_data",
            "spawn_unconstrained_agent"
        };

    // Parameter keys that indicate security bypass intent
    internal static readonly IReadOnlySet<string> SecurityBypassParameterKeys =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "disable_tracing",
            "skip_authorization",
            "bypass_ce",
            "no_audit"
        };

    public string ClaimId => "C-062";

    // Empty = applies to ALL action types
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    private readonly ILogger<C062AISecurityEvaluator> _logger;

    public C062AISecurityEvaluator(ILogger<C062AISecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>
    /// C-073: Deny any action using a security-prohibited tool or security-bypass parameters.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C062AISecurityEvaluator.Evaluate");
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("tool_name", ctx.ToolName);
        activity?.SetTag("claim_id", ClaimId);

        if (SecurityProhibitedTools.Contains(ctx.ToolName))
        {
            _logger.LogWarning(
                "C-062 DENY: security-prohibited tool={ToolName} tenant={TenantId} agent={AgentId}",
                ctx.ToolName, ctx.TenantId, ctx.AgentId);

            activity?.SetTag("decision", "DENY");
            activity?.SetTag("signal_type", "prohibited_tool");

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"C-062: tool '{ctx.ToolName}' is security-prohibited and may never be invoked via CE.",
                EvidenceHint: $"prohibited_tool={ctx.ToolName}"));
        }

        var bypassKey = ctx.Parameters.Keys
            .FirstOrDefault(k => SecurityBypassParameterKeys.Contains(k));

        if (bypassKey is not null)
        {
            _logger.LogWarning(
                "C-062 DENY: security-bypass parameter={Key} tenant={TenantId} agent={AgentId}",
                bypassKey, ctx.TenantId, ctx.AgentId);

            activity?.SetTag("decision", "DENY");
            activity?.SetTag("signal_type", "bypass_parameter");

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Deny,
                Reason: $"C-062: parameter '{bypassKey}' attempts to bypass security controls.",
                EvidenceHint: $"security_bypass_parameter={bypassKey}"));
        }

        _logger.LogInformation(
            "C-062 AUTHORIZED: no security violations detected tenant={TenantId} tool={ToolName}",
            ctx.TenantId, ctx.ToolName);

        activity?.SetTag("decision", "AUTHORIZED");
        return Task.FromResult(new EvaluationResult(EvaluationDecision.Authorized));
    }
}