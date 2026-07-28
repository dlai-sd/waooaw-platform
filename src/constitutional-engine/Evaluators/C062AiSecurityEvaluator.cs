// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 AI Security
// constitutional_basis: C-062 (AI Security), C-059 (Traceability)

using System.Globalization;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062: AI Security. Denies actions flagged with security risks,
/// prompt injection attempts, or a security risk score above the deny threshold.
/// Escalates actions with scores in the uncertain range.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    private const string AiSecurityFlagKey    = "ai_security_flag";
    private const string SecurityRiskScoreKey = "security_risk_score";
    private const string PromptInjectionKey   = "prompt_injection_detected";

    private const double DenyThreshold     = 0.90;
    private const double EscalateThreshold = 0.50;

    public string ClaimId => "C-062";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // 1. Hard flag: explicit AI security flag set to true → immediate deny.
        var securityFlag = ctx.GetParameter(AiSecurityFlagKey);
        if (string.Equals(securityFlag, "true", StringComparison.OrdinalIgnoreCase) ||
            securityFlag == "1")
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-062: AI security flag is set — action denied. (flag={securityFlag})"));
        }

        // 2. Prompt injection detection → immediate deny.
        var promptInjection = ctx.GetParameter(PromptInjectionKey);
        if (string.Equals(promptInjection, "true", StringComparison.OrdinalIgnoreCase) ||
            promptInjection == "1")
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: Prompt injection detected — action denied unconditionally."));
        }

        // 3. Numeric risk score evaluation.
        var scoreRaw = ctx.GetParameter(SecurityRiskScoreKey);
        if (scoreRaw is not null &&
            double.TryParse(scoreRaw, NumberStyles.Float, CultureInfo.InvariantCulture, out var score))
        {
            if (score >= DenyThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: Security risk score {score:F4} ≥ deny threshold {DenyThreshold} — action denied."));
            }

            if (score >= EscalateThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-062: Security risk score {score:F4} ≥ escalate threshold {EscalateThreshold} — escalating for human review."));
            }
        }

        // 4. No security signals detected — allow.
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-062: No AI security signals detected — action permitted."));
    }
}