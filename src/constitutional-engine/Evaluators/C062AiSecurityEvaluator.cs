// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 AI Security
// Constitutional basis: C-062 (AI Security), C-059 (Traceability), C-076 (test coverage)
using System.Globalization;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security): denies or escalates actions that present prompt-injection,
/// adversarial input, or elevated security-risk signals detected upstream by the skill layer.
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
        var aiSecurityFlag = ctx.GetParameter(AiSecurityFlagKey);
        if (string.Equals(aiSecurityFlag, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: AI security flag is set — action denied to prevent adversarial execution."));
        }

        // 2. Hard flag: prompt_injection_detected=true → immediate DENY
        var promptInjection = ctx.GetParameter(PromptInjectionKey);
        if (string.Equals(promptInjection, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: Prompt injection detected — action denied to preserve constitutional integrity."));
        }

        // 3. Numeric security risk score
        var riskScoreRaw = ctx.GetParameter(SecurityRiskScoreKey);
        if (riskScoreRaw is not null)
        {
            if (!double.TryParse(riskScoreRaw, NumberStyles.Any, CultureInfo.InvariantCulture, out var riskScore))
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: security_risk_score value '{riskScoreRaw}' is not a valid number — action denied."));
            }

            if (riskScore >= DenyThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: Security risk score {riskScore:F4} meets or exceeds deny threshold {DenyThreshold} — action denied."));
            }

            if (riskScore >= EscalateThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-062: Security risk score {riskScore:F4} meets or exceeds escalate threshold {EscalateThreshold} — forwarding to human review."));
            }
        }

        // 4. No security signals detected — allow
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-062: No AI security signals detected — action permitted."));
    }
}