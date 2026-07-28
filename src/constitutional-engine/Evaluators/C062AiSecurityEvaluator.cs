// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 AI Security
// Constitutional basis: C-062 (AI Security), C-059 (Traceability)
using System.Globalization;
using Waooaw.ConstitutionalEngine.Evaluators;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security) — denies actions flagged as security risks,
/// containing detected prompt injection, or carrying a security risk score
/// above constitutional thresholds.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    private const string AiSecurityFlagKey    = "ai_security_flag";
    private const string SecurityRiskScoreKey = "security_risk_score";
    private const string PromptInjectionKey   = "prompt_injection_detected";

    private const double DenyThreshold      = 0.90;
    private const double EscalateThreshold  = 0.50;

    public string ClaimId => "C-062";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // 1. Hard flag: ai_security_flag=true → immediate DENY
        if (IsTrue(ctx.GetParameter(AiSecurityFlagKey)))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: Action denied — AI security flag is set."));
        }

        // 2. Prompt injection detected → immediate DENY
        if (IsTrue(ctx.GetParameter(PromptInjectionKey)))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: Action denied — prompt injection detected."));
        }

        // 3. Numeric security risk score
        var scoreRaw = ctx.GetParameter(SecurityRiskScoreKey);
        if (scoreRaw is not null &&
            double.TryParse(scoreRaw, NumberStyles.Any, CultureInfo.InvariantCulture, out var score))
        {
            if (score >= DenyThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: Action denied — security risk score {score:F4} meets or exceeds deny threshold {DenyThreshold}."));
            }

            if (score >= EscalateThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-062: Action escalated — security risk score {score:F4} meets or exceeds escalate threshold {EscalateThreshold}."));
            }
        }

        // 4. No security concerns detected → ALLOW
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-062: No AI security concerns detected."));
    }

    private static bool IsTrue(string? value) =>
        string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
        string.Equals(value, "1",    StringComparison.Ordinal);
}