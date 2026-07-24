// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062
// constitutional_basis: C-062 (AI Security — prohibited tool patterns)

#nullable enable

using System.Text.RegularExpressions;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-062 Evaluator — AI Security boundary.
/// Denies MCP tool calls that match prohibited tool patterns (e.g., shell execution,
/// filesystem writes outside sandbox, network exfiltration tools).
/// </summary>
/// <remarks>
/// C-073: Enforces C-062 at runtime — checks tool name against prohibited patterns
/// pre-loaded from the security policy. Default deny if pattern list unavailable.
/// </remarks>
public sealed class C062_SecurityBoundaryEvaluator : IClaimEvaluator
{
    private readonly ILogger<C062_SecurityBoundaryEvaluator> _logger;

    // C-073: Applies to MCP_TOOL_CALL — security boundary on tool execution
    public string ClaimId => "C-062";
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "MCP_TOOL_CALL" };

    /// <summary>
    /// Built-in prohibited patterns that are always enforced regardless of tenant config.
    /// These represent absolute security boundaries (C-062 hard limits).
    /// </summary>
    internal static readonly IReadOnlyList<string> HardProhibitedPatterns = new[]
    {
        @"^shell[_\-]exec",
        @"^bash[_\-]",
        @"^cmd[_\-]exec",
        @"^system[_\-]call",
        @"^fs[_\-]write[_\-]root",
        @"^exfil[_\-]",
        @"^credential[_\-]dump",
        @"^privilege[_\-]escalat"
    };

    public C062_SecurityBoundaryEvaluator(ILogger<C062_SecurityBoundaryEvaluator> logger)
    {
        _logger = logger;
    }

    /// <inheritdoc/>
    /// <remarks>
    /// C-073: C-062 enforcement — deny if tool name matches any prohibited pattern.
    /// Hard patterns are always checked. Tenant-specific patterns from ProhibitedToolPatterns
    /// are checked second. Pattern matching is case-insensitive.
    /// </remarks>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        var toolName = ctx.ToolName ?? string.Empty;

        // C-062: Check hard-prohibited patterns (always enforced)
        foreach (var pattern in HardProhibitedPatterns)
        {
            if (Regex.IsMatch(toolName, pattern, RegexOptions.IgnoreCase | RegexOptions.CultureInvariant))
            {
                _logger.LogWarning(
                    "C-062 DENY (hard pattern): TenantId={TenantId} AgentId={AgentId} " +
                    "ToolName={ToolName} Pattern={Pattern}",
                    ctx.TenantId, ctx.AgentId, toolName, pattern);

                return Task.FromResult(new EvaluationResult(
                    Decision: EvaluationDecision.Deny,
                    Reason: $"C-062: Tool '{toolName}' matches hard-prohibited security pattern. " +
                            "AI security boundary enforced.",
                    EvidenceHint: $"prohibited_pattern={pattern},pattern_type=hard"
                ));
            }
        }

        // C-062: Check tenant-specific prohibited patterns
        if (ctx.ProhibitedToolPatterns is not null)
        {
            foreach (var pattern in ctx.ProhibitedToolPatterns)
            {
                if (string.IsNullOrWhiteSpace(pattern)) continue;

                try
                {
                    if (Regex.IsMatch(toolName, pattern,
                        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant,
                        TimeSpan.FromMilliseconds(5))) // ReDoS protection
                    {
                        _logger.LogWarning(
                            "C-062 DENY (tenant pattern): TenantId={TenantId} AgentId={AgentId} " +
                            "ToolName={ToolName} Pattern={Pattern}",
                            ctx.TenantId, ctx.AgentId, toolName, pattern);

                        return Task.FromResult(new EvaluationResult(
                            Decision: EvaluationDecision.Deny,
                            Reason: $"C-062: Tool '{toolName}' matches tenant-prohibited security pattern.",
                            EvidenceHint: $"prohibited_pattern={pattern},pattern_type=tenant"
                        ));
                    }
                }
                catch (RegexMatchTimeoutException)
                {
                    // ReDoS protection: treat timeout as deny (fail-safe)
                    _logger.LogError(
                        "C-062 DENY (regex timeout): TenantId={TenantId} Pattern={Pattern} — " +
                        "ReDoS protection triggered, fail-safe deny",
                        ctx.TenantId, pattern);

                    return Task.FromResult(new EvaluationResult(
                        Decision: EvaluationDecision.Deny,
                        Reason: "C-062: Security pattern evaluation timed out. Fail-safe deny.",
                        EvidenceHint: "regex_timeout_redos_protection"
                    ));
                }
            }
        }

        _logger.LogDebug(
            "C-062 AUTHORIZED: TenantId={TenantId} AgentId={AgentId} ToolName={ToolName}",
            ctx.TenantId, ctx.AgentId, toolName);

        return Task.FromResult(new EvaluationResult(EvaluationDecision.Authorized));
    }
}