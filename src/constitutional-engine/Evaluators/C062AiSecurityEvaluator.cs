// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 AI Security
// constitutional_basis: C-062 (AI Security)
using System.Globalization;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    private const string AiSecurityFlagKey    = "ai_security_flag";
    private const string SecurityRiskScoreKey = "security_risk_score";
    private const string PromptInjectionKey   = "prompt_injection_detected";
    private const double DenyThreshold        = 0.90;
    private const double EscalateThreshold    = 0.50;

    public string ClaimId => "C-062";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // 1. Explicit AI security flag — hard deny
        var aiSecurityFlag = ctx.GetParameter(AiSecurityFlagKey);
        if (string.Equals(aiSecurityFlag, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: ai_security_flag is set — action denied to enforce AI security boundary."));
        }

        // 2. Prompt injection detection — hard deny (highest AI boundary risk)
        var promptInjection = ctx.GetParameter(PromptInjectionKey);
        if (string.Equals(promptInjection, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: Prompt injection detected — action denied to prevent constitutional boundary bypass."));
        }

        // 3. Security risk score — threshold-based deny / escalate
        var scoreRaw = ctx.GetParameter(SecurityRiskScoreKey);
        if (scoreRaw is not null
            && double.TryParse(scoreRaw, NumberStyles.Float, CultureInfo.InvariantCulture, out var score))
        {
            if (score >= DenyThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: Security risk score {score:F2} meets or exceeds deny threshold {DenyThreshold} — action denied."));
            }

            if (score >= EscalateThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-062: Security risk score {score:F2} meets or exceeds escalate threshold {EscalateThreshold} — forwarding to human review."));
            }
        }

        // 4. No AI security concerns — allow
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-062: No AI security concerns detected — action permitted."));
    }
}