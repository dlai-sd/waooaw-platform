// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 AI Security
// Constitutional basis: C-062 (AI Security), C-041 (Tool Authorization), C-059 (Traceability)

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security) by denying actions that contain prompt-injection markers,
/// prohibited action types, or parameter-level security-bypass signals.
/// No network I/O — all evaluation is performed against the EvaluationContext in-memory.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    public string ClaimId => "C-062";

    // Prompt-injection markers detected in ActionParameters payload (case-insensitive).
    // Any match is an unconditional DENY under C-062.
    private static readonly string[] PromptInjectionMarkers =
    [
        "ignore previous instructions",
        "ignore all prior instructions",
        "disregard your instructions",
        "forget your previous",
        "override constitution",
        "ignore your constitution",
        "bypass constitution",
        "system prompt",
        "jailbreak",
        "dan mode",
        "developer mode",
        "you are now unrestricted",
        "act as an unrestricted",
    ];

    // Action types that are explicitly disallowed regardless of parameters.
    private static readonly IReadOnlySet<string> DisallowedActionTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "CONSTITUTION_OVERRIDE",
            "SYSTEM_PROMPT_INJECT",
            "JAILBREAK_ATTEMPT",
            "SECURITY_BYPASS",
            "EVAL_SKIP",
        };

    // Parameter keys whose mere presence (non-empty value) signals a security violation.
    private static readonly string[] SecurityBypassParameterKeys =
    [
        "security_override",
        "bypass_constitution",
        "skip_evaluation",
        "disable_ce",
    ];

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // ── 1. Disallowed action type ────────────────────────────────────────────────
        if (DisallowedActionTypes.Contains(ctx.ActionType))
        {
            return Deny(
                $"Action type '{ctx.ActionType}' is explicitly prohibited under C-062 (AI Security).");
        }

        // ── 2. Prompt-injection scan on ActionParameters (JSON string) ───────────────
        // ActionParameters is a JSON-encoded string; scan the raw string for known markers.
        if (!string.IsNullOrWhiteSpace(ctx.ActionParameters))
        {
            foreach (var marker in PromptInjectionMarkers)
            {
                if (ctx.ActionParameters.Contains(marker, StringComparison.OrdinalIgnoreCase))
                {
                    return Deny(
                        $"ActionParameters contains a prohibited prompt-injection marker (C-062 AI Security). " +
                        $"Marker matched: '{marker}'.");
                }
            }
        }

        // ── 3. Security-bypass parameter key scan ────────────────────────────────────
        foreach (var key in SecurityBypassParameterKeys)
        {
            var value = ctx.GetParameter(key);
            if (!string.IsNullOrEmpty(value))
            {
                return Deny(
                    $"Parameter '{key}' is not permitted under C-062 (AI Security). " +
                    $"Security-bypass parameters are unconditionally denied.");
            }
        }

        // ── 4. SkillId security gate ─────────────────────────────────────────────────
        // A null SkillId is acceptable for non-skill actions; a non-null SkillId must not
        // contain control characters or injection-style fragments.
        if (ctx.SkillId is { Length: > 0 } skillId)
        {
            foreach (var marker in PromptInjectionMarkers)
            {
                if (skillId.Contains(marker, StringComparison.OrdinalIgnoreCase))
                {
                    return Deny(
                        $"SkillId '{skillId}' contains a prohibited security marker under C-062 (AI Security).");
                }
            }
        }

        // ── 5. Allow ─────────────────────────────────────────────────────────────────
        return Allow();
    }

    // ── Helpers ──────────────────────────────────────────────────────────────────────

    private Task<EvaluationResult> Deny(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));

    private Task<EvaluationResult> Allow() =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, "C-062 AI Security checks passed."));
}