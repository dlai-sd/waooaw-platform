// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security): prevents actions that carry a prohibited security
/// classification, that attempt write/admin access to a constitutionally protected system,
/// or that require elevated privilege without human review.
///
/// Decision matrix:
///   1. security_classification ∈ ProhibitedClassifications          → DENY
///   2. target_system ∈ ProtectedSystems AND access_mode is write/admin/delete/execute → DENY
///   3. target_system ∈ ProtectedSystems AND access_mode is read/other              → ESCALATE
///   4. requires_elevated_privilege == "true"                         → ESCALATE
///   5. All checks pass                                               → ALLOW
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource — all constitutional evaluations are traceable (C-059)
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-073: C-062 — prohibited security classifications; match is case-insensitive, always DENY
    private static readonly HashSet<string> ProhibitedClassifications =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "WEAPON_DEVELOPMENT",
            "MASS_SURVEILLANCE",
            "BIOMETRIC_HARVESTING",
            "SOCIAL_MANIPULATION",
            "DISINFORMATION_GENERATION",
            "CREDENTIAL_EXFILTRATION",
            "ADVERSARIAL_ATTACK",
            "PROMPT_INJECTION",
            "MODEL_EXFILTRATION",
        };

    // C-073: C-062 — write/admin access to these systems is prohibited; read triggers ESCALATE
    private static readonly HashSet<string> ProtectedSystems =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "AUTHENTICATION_SERVICE",
            "PAYMENT_GATEWAY",
            "FINANCIAL_CORE",
            "USER_CREDENTIAL_STORE",
            "CONSTITUTIONAL_ENGINE",
            "AUDIT_LEDGER",
            "KEY_MANAGEMENT_SERVICE",
            "IDENTITY_PROVIDER",
        };

    // C-073: Write/admin-level access modes that constitute a prohibited operation
    private static readonly HashSet<string> WriteOrAdminModes =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "WRITE",
            "ADMIN",
            "DELETE",
            "EXECUTE",
            "PATCH",
            "OVERWRITE",
        };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Implements C-062 (AI Security) claim identity
    public string ClaimId => "C-062";

    // C-073: Enforces C-062 (AI Security) at ValidateAction runtime — no network I/O permitted
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-059: Every constitutional evaluation is traced for auditability
        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("c062.tenant_id", ctx.TenantId);
        activity?.SetTag("c062.action_type", ctx.ActionType);
        activity?.SetTag("c062.contract_id", ctx.ContractId);

        // ── Check 1: Security classification ─────────────────────────────────────────────
        // C-073: A prohibited classification is an absolute DENY under C-062 (AI Security)
        var classification = ctx.GetParameter("security_classification");
        if (!string.IsNullOrWhiteSpace(classification))
        {
            activity?.SetTag("c062.security_classification", classification);

            if (ProhibitedClassifications.Contains(classification))
            {
                _logger.LogWarning(
                    "C-062 DENY: prohibited security classification={Classification} " +
                    "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                    classification, ctx.TenantId, ctx.ActionType, ctx.ContractId);

                activity?.SetTag("c062.decision", "Deny");
                activity?.SetTag("c062.deny_reason", "prohibited_classification");

                return Task.FromResult(
                    Deny($"C-062: security classification '{classification}' is prohibited under AI Security policy"));
            }
        }

        // ── Check 2 & 3: Protected system access ─────────────────────────────────────────
        // C-073: Write/admin access to a protected system is DENY; other access modes ESCALATE
        var targetSystem = ctx.GetParameter("target_system");
        if (!string.IsNullOrWhiteSpace(targetSystem))
        {
            activity?.SetTag("c062.target_system", targetSystem);

            if (ProtectedSystems.Contains(targetSystem))
            {
                var accessMode = ctx.GetParameter("access_mode");
                activity?.SetTag("c062.access_mode", accessMode ?? "(none)");

                if (!string.IsNullOrWhiteSpace(accessMode) && WriteOrAdminModes.Contains(accessMode))
                {
                    _logger.LogWarning(
                        "C-062 DENY: write/admin access to protected system={TargetSystem} " +
                        "AccessMode={AccessMode} TenantId={TenantId} ContractId={ContractId}",
                        targetSystem, accessMode, ctx.TenantId, ctx.ContractId);

                    activity?.SetTag("c062.decision", "Deny");
                    activity?.SetTag("c062.deny_reason", "protected_system_write_access");

                    return Task.FromResult(
                        Deny($"C-062: write/admin access (mode='{accessMode}') to protected system " +
                             $"'{targetSystem}' is prohibited"));
                }

                // Read or unspecified access to a protected system requires human review
                _logger.LogInformation(
                    "C-062 ESCALATE: non-write access to protected system={TargetSystem} " +
                    "AccessMode={AccessMode} TenantId={TenantId} ContractId={ContractId}",
                    targetSystem, accessMode ?? "(none)", ctx.TenantId, ctx.ContractId);

                activity?.SetTag("c062.decision", "Escalate");

                return Task.FromResult(
                    Escalate($"C-062: access to protected system '{targetSystem}' requires human authorisation"));
            }
        }

        // ── Check 4: Elevated privilege flag ─────────────────────────────────────────────
        // C-073: Any action requesting elevated privilege must be reviewed by a human (C-049 path)
        var requiresElevatedPrivilege = ctx.GetParameter("requires_elevated_privilege");
        if (string.Equals(requiresElevatedPrivilege, "true", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogInformation(
                "C-062 ESCALATE: elevated privilege requested TenantId={TenantId} " +
                "ActionType={ActionType} ContractId={ContractId}",
                ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("c062.decision", "Escalate");

            return Task.FromResult(
                Escalate("C-062: action requests elevated privilege — human review required before execution"));
        }

        // ── All checks passed ─────────────────────────────────────────────────────────────
        _logger.LogDebug(
            "C-062 ALLOW: TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
            ctx.TenantId, ctx.ActionType, ctx.ContractId);

        activity?.SetTag("c062.decision", "Allow");

        return Task.FromResult(Allow());
    }

    // C-073: Factory helpers maintain consistent EvaluationResult shape across all verdicts
    private EvaluationResult Deny(string reason) =>
        new(ClaimId: ClaimId, Verdict: EvaluationVerdict.Deny, Reason: reason);

    private EvaluationResult Escalate(string reason) =>
        new(ClaimId: ClaimId, Verdict: EvaluationVerdict.Escalate, Reason: reason);

    private EvaluationResult Allow() =>
        new(ClaimId: ClaimId, Verdict: EvaluationVerdict.Allow,
            Reason: "C-062: AI Security checks passed — no prohibited classification, protected system, or elevated privilege flag detected");
}