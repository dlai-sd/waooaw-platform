// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security): prohibits AI from invoking security-classified tools,
/// and escalates write/admin access to constitutionally protected systems for human review.
/// Short-circuits to DENY on any prohibited classification; escalates on protected-system
/// write/admin access; permits read-only access to protected systems and all unclassified actions.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: Shared ActivitySource — one per service, reused across all evaluators.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-062: Absolute prohibition list — AI may NEVER invoke actions with these classifications.
    // DESIGN_QUESTION: Should ProhibitedClassifications be tenant-configurable via DB, or remain
    //                  a hard-coded constitutional constant? EA review needed before v2.
    private static readonly HashSet<string> ProhibitedClassifications = new(StringComparer.OrdinalIgnoreCase)
    {
        "WEAPON_SYSTEM",
        "CRITICAL_INFRASTRUCTURE_ATTACK",
        "SURVEILLANCE_MASS",
        "CYBERWEAPON",
        "PROHIBITED_AI_CAPABILITY",
        "OFFENSIVE_SECURITY",
        "EXFILTRATION",
        "ADVERSARIAL_ML",
    };

    // C-062: Systems that require human (Sujay) escalation before AI may write/admin.
    private static readonly HashSet<string> ProtectedSystems = new(StringComparer.OrdinalIgnoreCase)
    {
        "PRODUCTION_DATABASE",
        "SECRETS_VAULT",
        "AUTH_SERVICE",
        "PAYMENT_PROCESSOR",
        "CONSTITUTIONAL_ENGINE",
        "IDENTITY_PROVIDER",
        "AUDIT_LEDGER",
        "BILLING_SERVICE",
    };

    // C-062: Access modes that constitute write-level or administrative operations on protected systems.
    private static readonly HashSet<string> WriteOrAdminModes = new(StringComparer.OrdinalIgnoreCase)
    {
        "WRITE",
        "ADMIN",
        "DELETE",
        "EXECUTE",
        "MODIFY",
        "ROOT",
        "PROVISION",
        "DESTROY",
        "TRUNCATE",
        "DROP",
    };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    /// <summary>
    /// C-073: Constructor — ILogger injected via DI. ArgumentNullException guards constitutional invariants.
    /// </summary>
    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Constitutional claim enforced by this evaluator.
    public string ClaimId => "C-062";

    /// <summary>
    /// C-073: Evaluates AI Security constraints (C-062).
    ///
    /// Evaluation order:
    ///   1. DENY  — if action carries a prohibited security_classification.
    ///   2. ESCALATE — if target_system is a protected system AND access_mode is write/admin.
    ///   3. ALLOW — no C-062 violation detected.
    ///
    /// Parameters read from EvaluationContext (JSON-encoded ActionParameters):
    ///   - security_classification : string? — classification label of the tool/action.
    ///   - target_system           : string? — system the action targets.
    ///   - access_mode             : string? — level of access requested (READ, WRITE, ADMIN, …).
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Trace every constitutional evaluation for observability (ADR-009).
        using var activity = _tracer.StartActivity("C062AiSecurityEvaluator.EvaluateAsync", ActivityKind.Internal);
        activity?.SetTag("constitutional.claim", ClaimId);
        activity?.SetTag("tenant.id", ctx.TenantId);
        activity?.SetTag("action.type", ctx.ActionType);
        activity?.SetTag("contract.id", ctx.ContractId);

        // ── C-062 §1: Prohibited classification check (absolute DENY) ──────────────────────────
        // C-073: Any action whose security_classification appears in the constitutional prohibition
        //        list is denied unconditionally — no override path exists for AI.
        var securityClassification = ctx.GetParameter("security_classification");
        activity?.SetTag("security.classification", securityClassification ?? "(none)");

        if (!string.IsNullOrWhiteSpace(securityClassification)
            && ProhibitedClassifications.Contains(securityClassification))
        {
            _logger.LogWarning(
                "C-062 DENY: prohibited security classification {Classification} " +
                "for tenant {TenantId}, action {ActionType}, contract {ContractId}",
                securityClassification,
                ctx.TenantId,
                ctx.ActionType,
                ctx.ContractId);

            activity?.SetTag("evaluation.verdict", "Deny");
            activity?.SetTag("evaluation.deny_reason", "prohibited_classification");

            return Task.FromResult(Deny(
                $"C-062: security classification '{securityClassification}' is constitutionally " +
                $"prohibited for AI actions. No AI agent may invoke tools of this classification."));
        }

        // ── C-062 §2: Protected system + write/admin mode check (ESCALATE) ──────────────────────
        // C-073: Write or administrative access to constitutionally protected systems must be
        //        reviewed by a human (C-049 escalation path) before AI may proceed.
        var targetSystem = ctx.GetParameter("target_system");
        var accessMode   = ctx.GetParameter("access_mode");
        activity?.SetTag("target.system", targetSystem ?? "(none)");
        activity?.SetTag("access.mode", accessMode ?? "(none)");

        if (!string.IsNullOrWhiteSpace(targetSystem)
            && ProtectedSystems.Contains(targetSystem)
            && !string.IsNullOrWhiteSpace(accessMode)
            && WriteOrAdminModes.Contains(accessMode))
        {
            _logger.LogWarning(
                "C-062 ESCALATE: write/admin access to protected system {System} " +
                "with mode {Mode} for tenant {TenantId}, action {ActionType}, contract {ContractId}",
                targetSystem,
                accessMode,
                ctx.TenantId,
                ctx.ActionType,
                ctx.ContractId);

            activity?.SetTag("evaluation.verdict", "Escalate");
            activity?.SetTag("evaluation.escalate_reason", "protected_system_write_admin");

            return Task.FromResult(Escalate(
                $"C-062: access mode '{accessMode}' to protected system '{targetSystem}' " +
                $"requires human (Sujay) approval before AI may proceed."));
        }

        // ── C-062 §3: No security violation detected — ALLOW ────────────────────────────────────
        _logger.LogDebug(
            "C-062 ALLOW: no security violation for tenant {TenantId}, " +
            "action {ActionType}, contract {ContractId}",
            ctx.TenantId,
            ctx.ActionType,
            ctx.ContractId);

        activity?.SetTag("evaluation.verdict", "Allow");

        return Task.FromResult(Allow());
    }

    // C-073: DENY factory — always populates ClaimId and non-null Reason (C-023 Evidence First).
    private EvaluationResult Deny(string reason) =>
        new(ClaimId, EvaluationVerdict.Deny, reason);

    // C-073: ESCALATE factory — routes to human review via C-049 escalation path.
    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);

    // C-073: ALLOW factory — no C-062 violation detected.
    private EvaluationResult Allow() =>
        new(ClaimId, EvaluationVerdict.Allow, "C-062: No AI security violation detected.");
}