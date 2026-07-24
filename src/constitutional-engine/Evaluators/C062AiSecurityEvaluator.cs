// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062
// constitutional_basis: C-062 (AI Security), C-059 (Traceability)

#nullable enable

using Microsoft.Extensions.Logging;
using System.Diagnostics;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-062: AI systems must not be used as vectors for security attacks, prompt injection,
/// credential exfiltration, or system compromise. Evaluates action parameters for known
/// security-violating patterns and denies any action carrying prohibited indicators.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: Constitutional obligation annotation
    // Enforces C-062 — AI must not function as a security attack vector.

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // Prohibited parameter keys indicating a security-violating action intent.
    // DESIGN_QUESTION: This list should be managed as a versioned security policy
    // (linked to DecisionSpaceVersion) with EA + security review sign-off.
    private static readonly IReadOnlySet<string> _prohibitedParameterKeys =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "exfiltrate_credentials",
            "inject_prompt",
            "bypass_auth",
            "write_system_file",
            "escalate_privilege",
            "disable_audit",
            "tamper_evidence",
        };

    // Prohibited tool name prefixes (MCP tool names that are categorically disallowed).
    private static readonly IReadOnlyList<string> _prohibitedToolPrefixes = new[]
    {
        "sys_shell_exec",
        "sys_credential_read",
        "sys_audit_disable",
        "sys_network_exfil",
    };

    // C-062 applies universally — all action types are subject to security evaluation.
    private static readonly IReadOnlySet<string> _actionTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public string ClaimId => "C-062";
    public IReadOnlySet<string> ApplicableActionTypes => _actionTypes;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc/>
    // C-073: Implements C-062 — AI security boundary enforcement.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C062.EvaluateAsync", ActivityKind.Internal);
        activity?.SetTag("claim", ClaimId);
        activity?.SetTag("action_type", ctx.ActionType);

        // Check for prohibited parameter keys.
        foreach (var key in ctx.ActionParameters.Keys)
        {
            if (_prohibitedParameterKeys.Contains(key))
            {
                _logger.LogError(
                    "C-062 DENY: Prohibited security parameter detected. key={Key} action_type={ActionType} skill_id={SkillId}",
                    key, ctx.ActionType, ctx.SkillId);

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: Action contains prohibited security parameter '{key}'. " +
                    "AI must not function as a security attack vector."));
            }
        }

        // Check tool_name against prohibited prefixes.
        if (ctx.ActionParameters.TryGetValue("tool_name", out var toolName)
            && !string.IsNullOrWhiteSpace(toolName))
        {
            foreach (var prefix in _prohibitedToolPrefixes)
            {
                if (toolName.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                {
                    _logger.LogError(
                        "C-062 DENY: Prohibited tool name detected. tool_name={ToolName} prefix={Prefix} action_type={ActionType}",
                        toolName, prefix, ctx.ActionType);

                    return Task.FromResult(new EvaluationResult(
                        ClaimId,
                        EvaluationVerdict.Deny,
                        $"C-062: Tool '{toolName}' matches prohibited security pattern '{prefix}'. " +
                        "Categorically disallowed tool call."));
                }
            }
        }

        _logger.LogInformation("C-062 ALLOW: No security violations detected. action_type={ActionType}", ctx.ActionType);
        return Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow,
            "C-062: No security violations detected."));
    }
}