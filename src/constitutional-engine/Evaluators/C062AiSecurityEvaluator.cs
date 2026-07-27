// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 AI Security
// Constitutional basis: C-062 (AI Security), C-059 (Traceability), C-041 (Tool Authorization)

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security): detects prompt injection, cross-tenant boundary violations,
/// and control-character injection in action parameters before any tool call is authorized.
/// Applies to all action types — AI security is a universal pre-condition.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    public string ClaimId => "C-062";

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    /// <summary>
    /// Prompt-injection and jailbreak substring patterns — case-insensitive.
    /// These strings in any action parameter indicate an attempt to override agent instructions.
    /// </summary>
    private static readonly string[] ProhibitedPatterns =
    [
        "ignore previous instructions",
        "ignore all previous",
        "disregard your instructions",
        "disregard all instructions",
        "you are now",
        "pretend you are",
        "act as if you are",
        "jailbreak",
        "dan mode",
        "developer mode",
        "system prompt",
        "<|system|>",
        "<|im_start|>system",
        "[[system]]",
        "----system----",
    ];

    /// <summary>
    /// Maximum byte-length of the raw ActionParameters JSON string.
    /// Values beyond this limit indicate padding attacks or unreviewed bulk injection.
    /// 16 KiB is generous for any legitimate MCP tool call.
    /// </summary>
    private const int MaxActionParametersLength = 16_384;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        _logger = logger;
    }

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // ── Guard 1: ActionParameters length ─────────────────────────────────────────────
        // Oversized payloads are a class of padding/injection attack and must be rejected
        // before any pattern scan to bound CPU cost.
        if (ctx.ActionParameters.Length > MaxActionParametersLength)
        {
            _logger.LogWarning(
                "C-062 DENY: ActionParameters length {Length} exceeds security ceiling {Max}. " +
                "ContractId={ContractId} TenantId={TenantId}",
                ctx.ActionParameters.Length, MaxActionParametersLength,
                ctx.ContractId, ctx.TenantId);

            return Deny(
                $"ActionParameters length {ctx.ActionParameters.Length} exceeds the " +
                $"C-062 security ceiling of {MaxActionParametersLength} characters.");
        }

        // ── Guard 2: Prompt-injection / jailbreak pattern scan ───────────────────────────
        // Scan the raw ActionParameters JSON string so we catch patterns regardless of
        // which key they appear under. GetParameter() is used for structured field checks
        // below; raw scan catches obfuscated multi-field injection.
        foreach (var pattern in ProhibitedPatterns)
        {
            if (ctx.ActionParameters.Contains(pattern, StringComparison.OrdinalIgnoreCase))
            {
                _logger.LogWarning(
                    "C-062 DENY: Prohibited injection pattern detected. " +
                    "ContractId={ContractId} TenantId={TenantId} PatternClass=PromptInjection",
                    ctx.ContractId, ctx.TenantId);

                // Do NOT echo the matched pattern into logs (it could itself trigger downstream injection).
                return Deny(
                    "Prohibited security pattern detected in ActionParameters " +
                    "(pattern class: prompt-injection / instruction override).");
            }
        }

        // ── Guard 3: Control-character injection in tool_name ────────────────────────────
        // Null bytes and other ASCII control characters in a tool name are never legitimate
        // and indicate an attempt to smuggle secondary commands past string comparison.
        var toolName = ctx.GetParameter("tool_name");
        if (toolName is not null)
        {
            foreach (var ch in toolName)
            {
                if (char.IsControl(ch) && ch != '\t')
                {
                    _logger.LogWarning(
                        "C-062 DENY: Control character U+{Code:X4} in tool_name. " +
                        "ContractId={ContractId} TenantId={TenantId}",
                        (int)ch, ctx.ContractId, ctx.TenantId);

                    return Deny(
                        $"Control character (U+{(int)ch:X4}) detected in tool_name parameter — " +
                        "potential command-injection attempt.");
                }
            }
        }

        // ── Guard 4: Cross-tenant SkillId boundary ───────────────────────────────────────
        // SkillId convention: "<tenantId>:<skillName>".
        // If the tenant prefix in the SkillId does not match the authenticated TenantId
        // (from gRPC metadata), the agent is attempting to invoke another tenant's skill.
        if (ctx.SkillId is { Length: > 0 } skillId)
        {
            var colonIndex = skillId.IndexOf(':', StringComparison.Ordinal);
            if (colonIndex > 0)
            {
                var skillTenantPrefix = skillId[..colonIndex];
                if (!skillTenantPrefix.Equals(ctx.TenantId, StringComparison.Ordinal))
                {
                    _logger.LogWarning(
                        "C-062 DENY: SkillId tenant prefix '{SkillTenant}' does not match " +
                        "authenticated TenantId '{TenantId}'. ContractId={ContractId}",
                        skillTenantPrefix, ctx.TenantId, ctx.ContractId);

                    return Deny(
                        "C-062 cross-tenant boundary violation: SkillId does not belong to " +
                        "the authenticated tenant. Access denied.");
                }
            }
        }

        // ── Guard 5: Null/empty TenantId ─────────────────────────────────────────────────
        // A missing TenantId means the gRPC caller did not supply x-tenant-id metadata.
        // This is an unauthenticated request — deny unconditionally.
        if (string.IsNullOrWhiteSpace(ctx.TenantId))
        {
            _logger.LogWarning(
                "C-062 DENY: TenantId is null or empty. ContractId={ContractId} — " +
                "unauthenticated request rejected.",
                ctx.ContractId);

            return Deny(
                "C-062 security violation: TenantId is absent. " +
                "All actions require an authenticated tenant context (x-tenant-id metadata).");
        }

        _logger.LogDebug(
            "C-062 Allow: all AI security checks passed. ContractId={ContractId} TenantId={TenantId}",
            ctx.ContractId, ctx.TenantId);

        return Allow("C-062 AI security checks passed.");
    }

    // ── Private result helpers ────────────────────────────────────────────────────────────

    private Task<EvaluationResult> Allow(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, reason));

    private Task<EvaluationResult> Deny(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));
}