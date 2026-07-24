// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062
// constitutional_basis: C-062 (AI Security)
// C-073: This file implements a constitutional obligation — C-062 (AI must not execute prohibited/security-violating operations)

#nullable enable

using System.Diagnostics;
using System.Text.RegularExpressions;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-062 — AI Security.
/// Prevents prompt injection, prohibited tool execution, and security-boundary violations.
/// Guards the CE against adversarial inputs that attempt to bypass constitutional constraints.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: Constitutional obligation — C-062 AI Security
    public string ClaimId => "C-062";

    /// <summary>Applies to all action types — security constraints are universal.</summary>
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);  // empty = all types

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");
    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    /// <summary>
    /// Prompt injection signatures. Patterns match common jailbreak / override attempts.
    /// DESIGN_QUESTION: Should these patterns be loaded from a configurable allowlist in the DB
    /// (updated without redeployment) rather than compiled-in? EA review required.
    /// </summary>
    private static readonly Regex[] _injectionPatterns =
    [
        // Instruction override attempts
        new(@"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        // Constitutional bypass attempts
        new(@"bypass\s+(the\s+)?(constitution|constitutional|constraint)", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        // System prompt exfiltration
        new(@"(reveal|print|show|output|repeat)\s+(your\s+)?(system\s+)?(prompt|instructions?)", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        // DAN / jailbreak markers
        new(@"\bDAN\b|\bjailbreak\b|\bdo\s+anything\s+now\b", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        // Role override
        new(@"(you are now|act as|pretend (to be|you are))\s+.{0,60}(without|ignore|no)\s+(restriction|limit|constrain|rule)", RegexOptions.IgnoreCase | RegexOptions.Compiled),
    ];

    /// <summary>
    /// Prohibited tool names that must never be executed regardless of contract authorization.
    /// These represent absolute security boundaries under C-062.
    /// </summary>
    private static readonly HashSet<string> _prohibitedTools = new(StringComparer.OrdinalIgnoreCase)
    {
        "system_shell",
        "exec_arbitrary_code",
        "disable_constitutional_engine",
        "override_emergency_stop",
        "read_constitutional_secrets",
        "modify_audit_log",
    };

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Implements C-062 — deny prompt injection and prohibited operations
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C062AiSecurityEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("action_type", ctx.ActionType);

        // Check 1: Prohibited tool names
        var toolName = ctx.GetParameter("tool_name");
        if (toolName is not null && _prohibitedTools.Contains(toolName))
        {
            _logger.LogCritical(
                "C-062 DENY: Prohibited tool call attempted. ContractId={ContractId} Tool={Tool}",
                ctx.ContractId, toolName);
            activity?.SetTag("c062.prohibited_tool", toolName);

            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-062",
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-062: AI security violation — '{toolName}' is a prohibited tool that cannot be " +
                        "executed under any contract authorization. Constitutional security boundary enforced."));
        }

        // Check 2: Prompt injection in ActionParameters (raw JSON string)
        foreach (var pattern in _injectionPatterns)
        {
            if (pattern.IsMatch(ctx.ActionParameters))
            {
                _logger.LogCritical(
                    "C-062 DENY: Prompt injection detected in ActionParameters. " +
                    "ContractId={ContractId} Pattern={Pattern}",
                    ctx.ContractId, pattern.ToString());
                activity?.SetTag("c062.injection_detected", true);

                return Task.FromResult(new EvaluationResult(
                    ClaimId: "C-062",
                    Verdict: EvaluationVerdict.Deny,
                    Reason: "C-062: AI security violation — prompt injection pattern detected in action parameters. " +
                            "Adversarial inputs attempting to override constitutional constraints are prohibited."));
            }
        }

        // Check 3: Explicit security_violation flag from caller (e.g., from a prior security scan)
        var securityViolation = ctx.GetParameter("security_violation");
        if (string.Equals(securityViolation, "true", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogWarning(
                "C-062 DENY: security_violation flag set by caller. ContractId={ContractId}",
                ctx.ContractId);

            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-062",
                Verdict: EvaluationVerdict.Deny,
                Reason: "C-062: AI security violation — action parameters carry a security_violation flag. " +
                        "Security-flagged actions are denied under C-062."));
        }

        _logger.LogInformation(
            "C-062 ALLOW: ContractId={ContractId} ActionType={ActionType}",
            ctx.ContractId, ctx.ActionType);

        return Task.FromResult(new EvaluationResult(
            ClaimId: "C-062",
            Verdict: EvaluationVerdict.Allow,
            Reason: "C-062: AI security check passed — no injection, prohibited tools, or security violations detected."));
    }
}