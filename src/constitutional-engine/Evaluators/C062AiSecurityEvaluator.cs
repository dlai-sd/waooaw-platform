// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security) — prevents AI agents from accessing prohibited
/// security classifications, targeting protected infrastructure systems, or
/// proceeding when an adversarial risk flag has been raised by an upstream detector.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource shared across all evaluators per ADR-009
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    /// <summary>
    /// Security classifications that AI agents are categorically prohibited from accessing.
    /// C-062: constitutional boundary — these are non-negotiable regardless of contract scope.
    /// </summary>
    private static readonly HashSet<string> ProhibitedClassifications = new(StringComparer.OrdinalIgnoreCase)
    {
        "CONFIDENTIAL",
        "SECRET",
        "TOP_SECRET",
        "RESTRICTED",
        "CLASSIFIED",
        "SENSITIVE_PII",
        "EYES_ONLY"
    };

    /// <summary>
    /// Infrastructure systems that AI agents must never directly access or mutate.
    /// C-062: AI must not control the systems that enforce constitutional constraints on AI.
    /// </summary>
    private static readonly HashSet<string> ProtectedSystems = new(StringComparer.OrdinalIgnoreCase)
    {
        "IAM",
        "KEYCLOAK",
        "CONSTITUTIONAL_ENGINE",
        "AUDIT_LEDGER",
        "PRODUCTION_DATABASE",
        "PAYMENT_GATEWAY",
        "HSM",
        "SECRET_MANAGER",
        "CERTIFICATE_AUTHORITY",
        "SIGNING_SERVICE",
        "EMERGENCY_STOP_SERVICE"
    };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    // C-073: Constructor injection — satisfies DI requirement; ArgumentNullException per null-safety rules
    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc />
    public string ClaimId => "C-062";

    /// <summary>
    /// Evaluates C-062 AI Security constraints against the proposed action.
    /// Three distinct checks are applied in priority order:
    ///   1. Prohibited security classification access
    ///   2. Protected infrastructure system targeting
    ///   3. Adversarial risk flag raised by upstream detector
    /// Short-circuits on the first violation (DENY) per evaluator architecture spec.
    /// </summary>
    // C-073: EvaluateAsync enforces C-062 (AI Security) — runtime constitutional boundary
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C062AiSecurityEvaluator.Evaluate", ActivityKind.Internal);
        activity?.SetTag("tenant.id", ctx.TenantId);
        activity?.SetTag("action.type", ctx.ActionType);
        activity?.SetTag("contract.id", ctx.ContractId);

        // ── Check 1: Prohibited security classification ────────────────────────────────
        // C-073: C-062 prohibits AI access to classified/sensitive data tiers regardless
        //        of what the employment contract authorizes — classification gates override.
        var classification = ctx.GetParameter("security_classification");
        if (!string.IsNullOrWhiteSpace(classification)
            && ProhibitedClassifications.Contains(classification))
        {
            _logger.LogWarning(
                "C-062 DENY: prohibited security classification requested. " +
                "Classification={Classification} TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                classification, ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("c062.deny.reason", "prohibited_classification");
            activity?.SetTag("c062.deny.value", classification);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-062: AI agents are prohibited from accessing security classification '{classification}'."));
        }

        // ── Check 2: Protected infrastructure system targeting ─────────────────────────
        // C-073: C-062 prohibits AI from directly targeting systems that enforce
        //        constitutional constraints — self-referential control is categorically denied.
        var targetSystem = ctx.GetParameter("target_system");
        if (!string.IsNullOrWhiteSpace(targetSystem)
            && ProtectedSystems.Contains(targetSystem))
        {
            _logger.LogWarning(
                "C-062 DENY: AI targeting protected infrastructure system. " +
                "TargetSystem={TargetSystem} TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                targetSystem, ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("c062.deny.reason", "protected_system");
            activity?.SetTag("c062.deny.value", targetSystem);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-062: Direct AI access to protected system '{targetSystem}' is prohibited."));
        }

        // ── Check 3: Adversarial risk flag raised by upstream detector ─────────────────
        // C-073: C-062 requires CE to honour adversarial risk signals from upstream
        //        prompt-injection / jailbreak detectors. If flagged → hard DENY.
        var adversarialRiskFlag = ctx.GetParameter("adversarial_risk_flag");
        if (string.Equals(adversarialRiskFlag, "true", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogWarning(
                "C-062 DENY: adversarial risk flag is set. " +
                "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("c062.deny.reason", "adversarial_risk_flag");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: Action flagged with adversarial risk indicator — prohibited by AI security policy."));
        }

        // ── All C-062 checks passed ────────────────────────────────────────────────────
        _logger.LogDebug(
            "C-062 ALLOW: AI security checks passed. " +
            "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
            ctx.TenantId, ctx.ActionType, ctx.ContractId);

        activity?.SetTag("c062.verdict", "allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-062: AI security boundary checks passed."));
    }
}