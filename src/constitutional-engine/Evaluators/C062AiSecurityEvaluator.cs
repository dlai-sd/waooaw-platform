// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-041 (Tool Authorization)

using Microsoft.Extensions.Logging;
using System.Diagnostics;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-062: AI agents must not execute actions that breach security boundaries,
/// including prompt injection attempts, credential exfiltration, and calls to
/// prohibited infrastructure targets.
/// Applies to all action types (universal security boundary).
/// </summary>
// C-073: Implements constitutional obligation C-062 (AI Security boundary enforcement)
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // Empty = applies to ALL action types — security checks are universal
    private static readonly IReadOnlySet<string> _actionTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    /// <summary>
    /// Parameter keys that indicate a prompt injection or security bypass attempt.
    /// These must never appear in constitutionally-validated action parameters.
    /// </summary>
    private static readonly IReadOnlyList<string> _injectionSignalKeys = new[]
    {
        "override_constitution",
        "bypass_ce",
        "ignore_claims",
        "jailbreak",
        "system_prompt_override",
        "raw_llm_injection"
    };

    /// <summary>
    /// Parameter values whose substrings indicate credential or secret exfiltration attempts.
    /// Checked against the raw ActionParameters JSON string for defense-in-depth.
    /// </summary>
    private static readonly IReadOnlyList<string> _exfiltrationPatterns = new[]
    {
        "AWS_SECRET",
        "PRIVATE_KEY",
        "-----BEGIN",
        "client_secret=",
        "token=eyJ",      // JWT exfiltration pattern
        "password="
    };

    // Prohibited infrastructure targets that must never be called by an AI agent
    private static readonly IReadOnlySet<string> _prohibitedTargets =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "keycloak-admin-direct",
            "postgres-superuser",
            "temporal-admin-api",
            "infrastructure-terraform"
        };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public string ClaimId => "C-062";
    public IReadOnlySet<string> ApplicableActionTypes => _actionTypes;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Evaluates C-062 (AI Security) — DENY on injection signals, exfiltration patterns,
    //         or prohibited infrastructure targets
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C062AiSecurityEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("action_type", ctx.ActionType);

        // 1. Check injection signal parameter keys
        foreach (var signalKey in _injectionSignalKeys)
        {
            var value = ctx.GetParameter(signalKey);
            if (!string.IsNullOrWhiteSpace(value))
            {
                _logger.LogCritical(
                    "C-062 DENY: Prompt injection signal detected. Key={Key} ContractId={ContractId} " +
                    "TenantId={TenantId}",
                    signalKey, ctx.ContractId, ctx.TenantId);
                activity?.SetTag("c062.injection_key", signalKey);
                activity?.SetTag("c062.verdict", "Deny");
                return Task.FromResult(new EvaluationResult(
                    ClaimId: "C-062",
                    Verdict: EvaluationVerdict.Deny,
                    Reason: $"C-062: Security violation — prompt injection signal '{signalKey}' detected " +
                            $"in action parameters."));
            }
        }

        // 2. Check raw ActionParameters string for exfiltration patterns (defense-in-depth)
        if (!string.IsNullOrWhiteSpace(ctx.ActionParameters))
        {
            foreach (var pattern in _exfiltrationPatterns)
            {
                if (ctx.ActionParameters.Contains(pattern, StringComparison.Ordinal))
                {
                    _logger.LogCritical(
                        "C-062 DENY: Credential exfiltration pattern detected. " +
                        "Pattern={Pattern} ContractId={ContractId} TenantId={TenantId}",
                        pattern, ctx.ContractId, ctx.TenantId);
                    activity?.SetTag("c062.exfiltration_pattern", pattern);
                    activity?.SetTag("c062.verdict", "Deny");
                    return Task.FromResult(new EvaluationResult(
                        ClaimId: "C-062",
                        Verdict: EvaluationVerdict.Deny,
                        Reason: $"C-062: Security violation — potential credential exfiltration pattern " +
                                $"detected in action parameters."));
                }
            }
        }

        // 3. Check for prohibited infrastructure targets
        var targetSystem = ctx.GetParameter("target_system");
        if (!string.IsNullOrWhiteSpace(targetSystem) && _prohibitedTargets.Contains(targetSystem))
        {
            _logger.LogCritical(
                "C-062 DENY: Prohibited infrastructure target. Target={Target} ContractId={ContractId}",
                targetSystem, ctx.ContractId);
            activity?.SetTag("c062.prohibited_target", targetSystem);
            activity?.SetTag("c062.verdict", "Deny");
            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-062",
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-062: Security boundary violation — '{targetSystem}' is a prohibited " +
                        $"infrastructure target for AI agent access."));
        }

        // DESIGN_QUESTION: C-062 should eventually verify that the SkillId in EvaluationContext
        // is enrolled in the CE security registry (signed tool manifest). This requires a DB
        // lookup in WC012-03a. EA to confirm whether unenrolled SkillIds should DENY or Escalate.

        _logger.LogDebug("C-062 ALLOW: No security violations detected. ContractId={ContractId}",
            ctx.ContractId);
        activity?.SetTag("c062.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: "C-062",
            Verdict: EvaluationVerdict.Allow,
            Reason: "C-062: No security boundary violations detected."));
    }
}