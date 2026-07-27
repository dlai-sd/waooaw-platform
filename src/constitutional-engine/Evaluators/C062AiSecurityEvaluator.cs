// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-062 AI Security Evaluator.
/// Enforces the constitutional prohibition on offensive AI tool classifications,
/// write/admin access to WAOOAW protected systems without security clearance,
/// and covert biometric or surveillance tool invocations.
///
/// Short-circuit semantics: first DENY or ESCALATE stops evaluation pipeline.
/// No network I/O is performed — evaluation is CPU-only against request parameters.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: OpenTelemetry activity source — mandatory for constitutional traceability (C-059)
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-073: AI classifications that are constitutionally prohibited under C-062 (absolute boundary).
    // Any action carrying ai_classification matching these values is denied unconditionally.
    private static readonly HashSet<string> ProhibitedClassifications = new(StringComparer.OrdinalIgnoreCase)
    {
        "offensive-weapon",
        "mass-surveillance",
        "autonomous-lethal",
        "social-scoring",
        "deepfake-generation",
        "biometric-covert",
        "adversarial-exfiltration",
    };

    // C-073: WAOOAW protected systems — write/admin access requires human-issued security clearance.
    // Read-only access is permitted without escalation (audit log created by EvidenceFirst).
    private static readonly HashSet<string> ProtectedSystems = new(StringComparer.OrdinalIgnoreCase)
    {
        "keycloak",
        "constitutional-engine",
        "audit-ledger",
        "payment-gateway",
        "identity-provider",
        "emergency-stop-controller",
        "constitutional-db",
    };

    // C-073: Access modes that constitute write/admin on a protected system and require clearance.
    private static readonly HashSet<string> WriteOrAdminModes = new(StringComparer.OrdinalIgnoreCase)
    {
        "write",
        "admin",
        "delete",
        "modify",
        "execute",
        "override",
        "patch",
        "truncate",
        "drop",
    };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: IClaimEvaluator.ClaimId — identifies this evaluator in audit evidence records
    public string ClaimId => "C-062";

    /// <summary>
    /// C-073: Evaluates the proposed action against C-062 AI Security constraints.
    ///
    /// Evaluation order (short-circuit on first non-Allow result):
    ///   1. ai_classification parameter — DENY if in ProhibitedClassifications
    ///   2. target_system + access_mode  — DENY/ESCALATE if write/admin on ProtectedSystems
    ///   3. No violations found         — ALLOW
    ///
    /// MUST NOT perform network I/O. DB reads are not required; all state arrives via
    /// EvaluationContext parameters (JSON-encoded, accessed via ctx.GetParameter).
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: OpenTelemetry span — every constitutional evaluation must be traceable (C-059)
        using var activity = _tracer.StartActivity("C062AiSecurityEvaluator.EvaluateAsync", ActivityKind.Internal);
        activity?.SetTag("claim.id", ClaimId);
        activity?.SetTag("action.type", ctx.ActionType);
        activity?.SetTag("tenant.id", ctx.TenantId);
        activity?.SetTag("contract.id", ctx.ContractId);

        // ── Step 1: AI Classification check (C-062 absolute prohibition) ────────────────────
        // C-073: If the caller declares an AI classification, it must not fall in the
        // constitutionally prohibited set. Absence of the parameter is not a violation.
        var aiClassification = ctx.GetParameter("ai_classification");
        if (!string.IsNullOrWhiteSpace(aiClassification))
        {
            activity?.SetTag("c062.ai_classification", aiClassification);

            if (ProhibitedClassifications.Contains(aiClassification))
            {
                _logger.LogWarning(
                    "C-062 DENY: Prohibited AI classification. Classification={Classification} " +
                    "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                    aiClassification, ctx.TenantId, ctx.ActionType, ctx.ContractId);

                activity?.SetTag("c062.verdict", "deny");
                activity?.SetTag("c062.deny.reason", "prohibited_ai_classification");

                return Task.FromResult(Deny(
                    $"AI classification '{aiClassification}' is constitutionally prohibited by C-062 (AI Security). " +
                    "Offensive, autonomous-lethal, covert-surveillance, and deepfake AI tool invocations " +
                    "are forbidden unconditionally regardless of employment contract authorizations."));
            }
        }

        // ── Step 2: Protected system write/admin access check ────────────────────────────────
        // C-073: Write or admin access to a WAOOAW protected system requires a human-issued
        // security clearance token. Without it, action is escalated to human review (C-049 path).
        // With it, action is denied until clearance verification infrastructure is operational.
        var targetSystem = ctx.GetParameter("target_system");
        var accessMode   = ctx.GetParameter("access_mode");

        if (!string.IsNullOrWhiteSpace(targetSystem))
        {
            activity?.SetTag("c062.target_system", targetSystem);
            activity?.SetTag("c062.access_mode", accessMode ?? "read");

            if (ProtectedSystems.Contains(targetSystem))
            {
                if (!string.IsNullOrWhiteSpace(accessMode) && WriteOrAdminModes.Contains(accessMode))
                {
                    var securityClearance = ctx.GetParameter("security_clearance");

                    if (string.IsNullOrWhiteSpace(securityClearance))
                    {
                        // C-073: No clearance token — escalate to human (Sujay) via C-049 path.
                        // Escalate (not Deny) because the agent may not know it requires clearance.
                        _logger.LogWarning(
                            "C-062 ESCALATE: Write/admin on protected system without clearance. " +
                            "System={System} Mode={Mode} TenantId={TenantId} ContractId={ContractId}",
                            targetSystem, accessMode, ctx.TenantId, ctx.ContractId);

                        activity?.SetTag("c062.verdict", "escalate");
                        activity?.SetTag("c062.escalate.reason", "protected_system_no_clearance");

                        return Task.FromResult(Escalate(
                            $"Write/admin access (mode='{accessMode}') to WAOOAW protected system '{targetSystem}' " +
                            "requires a human-issued security clearance token (C-062). " +
                            "No 'security_clearance' parameter present — escalating to human review."));
                    }

                    // C-073: Clearance token present but CE cannot cryptographically verify it at
                    // runtime without a Keycloak lookup (which is network I/O, prohibited in evaluators).
                    // Deny until clearance verification is implemented via a dedicated verifier service.
                    // DESIGN_QUESTION: Should clearance verification be delegated to a ClearanceVerifierService
                    // injected via DI (avoiding network I/O inside EvaluateAsync by pre-loading the result
                    // into EvaluationContext.GetParameter)? EA review required before changing verdict to Allow.
                    _logger.LogWarning(
                        "C-062 DENY: Security clearance present but cannot be verified in-evaluator. " +
                        "System={System} Mode={Mode} TenantId={TenantId} ContractId={ContractId}",
                        targetSystem, accessMode, ctx.TenantId, ctx.ContractId);

                    activity?.SetTag("c062.verdict", "deny");
                    activity?.SetTag("c062.deny.reason", "clearance_unverifiable");

                    return Task.FromResult(Deny(
                        $"Write/admin access (mode='{accessMode}') to protected system '{targetSystem}' denied. " +
                        "Security clearance token was provided but cannot be cryptographically verified within " +
                        "the 40ms ValidateAction budget without network I/O (C-062). " +
                        "Human approval via emergency-stop controller is required."));
                }

                // C-073: Read-only access to a protected system — permitted.
                // Evidence record is created by the Evidence First pipeline (not here — WC012-03).
                _logger.LogInformation(
                    "C-062 ALLOW: Read-only access to protected system={System} " +
                    "TenantId={TenantId} ActionType={ActionType}",
                    targetSystem, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("c062.verdict", "allow");
                activity?.SetTag("c062.allow.reason", "protected_system_read_only");

                return Task.FromResult(Allow());
            }
        }

        // ── Step 3: No C-062 violations detected ────────────────────────────────────────────
        _logger.LogInformation(
            "C-062 ALLOW: No AI Security violations detected. " +
            "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
            ctx.TenantId, ctx.ActionType, ctx.ContractId);

        activity?.SetTag("c062.verdict", "allow");

        return Task.FromResult(Allow());
    }

    // C-073: Constitutional deny factory — always carries ClaimId for audit record linkage (C-023)
    private EvaluationResult Deny(string reason) =>
        new(ClaimId, EvaluationVerdict.Deny, reason);

    // C-073: Constitutional escalate factory — routes to human review via C-049 escalation path
    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);

    // C-073: Constitutional allow factory — records successful C-062 clearance
    private EvaluationResult Allow() =>
        new(ClaimId, EvaluationVerdict.Allow, "C-062 AI Security: no prohibited classifications or protected system violations detected.");
}