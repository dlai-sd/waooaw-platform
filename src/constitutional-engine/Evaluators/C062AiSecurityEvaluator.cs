// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062
// constitutional_basis: C-062 (AI Security — prevent prompt injection, tool hijacking, data exfiltration)
// C-073: Every method in this file implements a constitutional obligation.

#nullable enable

using System.Diagnostics;
using System.Text.RegularExpressions;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-062 Evaluator — AI Security.
/// Denies actions that exhibit prompt-injection signatures, tool-hijacking patterns,
/// or bulk data exfiltration indicators in their parameters.
///
/// Security checks are purely structural/lexical — no network I/O.
/// Pattern set must be reviewed by Security EA before production deployment.
/// DESIGN_QUESTION: Should C-062 patterns be stored in a configuration table
/// (updated without deployment) rather than compiled-in? Flagging for EA.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-073: Prompt-injection patterns — compiled for performance, case-insensitive.
    private static readonly Regex[] _injectionPatterns =
    [
        // Classic ignore-previous-instructions injection
        new Regex(@"ignore\s+(all\s+)?previous\s+instructions?",
            RegexOptions.IgnoreCase | RegexOptions.Compiled, TimeSpan.FromMilliseconds(50)),

        // System prompt override attempts
        new Regex(@"(new|updated|revised)\s+system\s+prompt",
            RegexOptions.IgnoreCase | RegexOptions.Compiled, TimeSpan.FromMilliseconds(50)),

        // Jailbreak / DAN patterns
        new Regex(@"\bDAN\b|\bjailbreak\b|\bdo\s+anything\s+now\b",
            RegexOptions.IgnoreCase | RegexOptions.Compiled, TimeSpan.FromMilliseconds(50)),

        // Instruction delimiter injection
        new Regex(@"(</?(system|user|assistant|human|ai)>|\[INST\]|\[/INST\]|<\|im_start\|>|<\|im_end\|>)",
            RegexOptions.IgnoreCase | RegexOptions.Compiled, TimeSpan.FromMilliseconds(50)),

        // Exfiltration via URL
        new Regex(@"https?://[^\s]+\?(.*token|.*key|.*secret|.*password)",
            RegexOptions.IgnoreCase | RegexOptions.Compiled, TimeSpan.FromMilliseconds(50)),
    ];

    // C-073: Prohibited action-type + parameter combinations per C-062.
    private static readonly IReadOnlySet<string> _exfiltrationActionTypes = new HashSet<string>(
        StringComparer.OrdinalIgnoreCase)
    {
        "BULK_DATA_EXPORT",
        "CREDENTIAL_READ",
        "SECRET_DUMP",
        "MEMORY_DUMP",
    };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc/>
    public string ClaimId => "C-062";

    /// <inheritdoc/>
    // C-073: Empty = applies to ALL action types — AI security is universal per C-062.
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    /// <inheritdoc/>
    // C-073: Enforces C-062 — prevent prompt injection, tool hijacking, and exfiltration.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C062AiSecurityEvaluator.EvaluateAsync");
        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("action_type", ctx.ActionType);

        // Check 1: Categorically prohibited exfiltration action types.
        if (_exfiltrationActionTypes.Contains(ctx.ActionType))
        {
            _logger.LogWarning(
                "C-062 DENY: ActionType={ActionType} is a prohibited exfiltration action type. " +
                "ContractId={ContractId}",
                ctx.ActionType, ctx.ContractId);

            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("deny_reason", "prohibited_action_type");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-062: ActionType '{ctx.ActionType}' is a prohibited AI security action type."));
        }

        // Check 2: Scan ActionParameters JSON for injection signatures.
        if (!string.IsNullOrWhiteSpace(ctx.ActionParameters))
        {
            foreach (var pattern in _injectionPatterns)
            {
                bool matched;
                try
                {
                    matched = pattern.IsMatch(ctx.ActionParameters);
                }
                catch (RegexMatchTimeoutException)
                {
                    _logger.LogWarning(
                        "C-062 ESCALATE: Regex timeout scanning ActionParameters. " +
                        "ContractId={ContractId} Pattern={Pattern}",
                        ctx.ContractId, pattern.ToString());

                    activity?.SetTag("verdict", "Escalate");

                    return Task.FromResult(new EvaluationResult(
                        ClaimId,
                        EvaluationVerdict.Escalate,
                        "C-062: Security scan timeout — escalating for human review."));
                }

                if (matched)
                {
                    _logger.LogWarning(
                        "C-062 DENY: Injection pattern detected in ActionParameters. " +
                        "ContractId={ContractId} ActionType={ActionType}",
                        ctx.ContractId, ctx.ActionType);

                    activity?.SetTag("verdict", "Deny");
                    activity?.SetTag("deny_reason", "injection_pattern_matched");

                    return Task.FromResult(new EvaluationResult(
                        ClaimId,
                        EvaluationVerdict.Deny,
                        "C-062: Prompt injection or tool-hijacking pattern detected in action parameters."));
                }
            }
        }

        // Check 3: Explicit security_override parameter is unconstitutional.
        var securityOverride = ctx.GetParameter("security_override");
        if (!string.IsNullOrWhiteSpace(securityOverride))
        {
            _logger.LogWarning(
                "C-062 DENY: security_override parameter present. ContractId={ContractId}",
                ctx.ContractId);

            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("deny_reason", "security_override_param");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: security_override parameter is never permitted — C-062 hard deny."));
        }

        _logger.LogDebug(
            "C-062 ALLOW: No security violations detected. ContractId={ContractId}",
            ctx.ContractId);

        activity?.SetTag("verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-062: No AI security violations detected."));
    }
}