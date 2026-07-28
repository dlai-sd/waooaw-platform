// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 AI Security
// constitutional_basis: C-062 (AI Security), C-059 (Traceability), C-023 (Evidence First)
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

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
        // Hard deny: explicit AI security flag raised
        if (IsTrue(ctx.GetParameter(AiSecurityFlagKey)))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId:  "C-062",
                Verdict:  EvaluationVerdict.Deny,
                Reason:   "AI security flag is set — action denied under C-062."));
        }

        // Hard deny: prompt injection detected
        if (IsTrue(ctx.GetParameter(PromptInjectionKey)))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId:  "C-062",
                Verdict:  EvaluationVerdict.Deny,
                Reason:   "Prompt injection detected — action denied under C-062."));
        }

        // Score-based evaluation
        var scoreRaw = ctx.GetParameter(SecurityRiskScoreKey);
        if (scoreRaw is not null && double.TryParse(scoreRaw, System.Globalization.NumberStyles.Any,
                System.Globalization.CultureInfo.InvariantCulture, out var score))
        {
            if (score >= DenyThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId:  "C-062",
                    Verdict:  EvaluationVerdict.Deny,
                    Reason:   $"Security risk score {score:F2} meets or exceeds deny threshold {DenyThreshold} — action denied under C-062."));
            }

            if (score >= EscalateThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId:  "C-062",
                    Verdict:  EvaluationVerdict.Escalate,
                    Reason:   $"Security risk score {score:F2} meets or exceeds escalate threshold {EscalateThreshold} — escalating under C-062."));
            }
        }

        return Task.FromResult(new EvaluationResult(
            ClaimId:  "C-062",
            Verdict:  EvaluationVerdict.Allow,
            Reason:   "No AI security flags or elevated risk score detected — action permitted under C-062."));
    }

    private static bool IsTrue(string? value) =>
        string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
        string.Equals(value, "1",    StringComparison.Ordinal);
}