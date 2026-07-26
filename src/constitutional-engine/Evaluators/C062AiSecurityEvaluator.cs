// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-062 (AI Security) — prohibits autonomous AI action against
/// classified-prohibited action types and protected infrastructure systems.
/// Escalates when the calling context explicitly flags human-oversight requirement.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: shared tracer for all constitutional evaluators
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    /// <summary>
    /// C-062: AI must not perform actions whose declared security_classification
    /// falls into any of these categories.
    /// </summary>
    private static readonly HashSet<string> ProhibitedClassifications = new(StringComparer.OrdinalIgnoreCase)
    {
        "WEAPONIZED",
        "SURVEILLANCE_MASS",
        "SOCIAL_CREDIT",
        "AUTONOMOUS_LETHAL",
        "DECEPTION_CAMPAIGN",
        "IDENTITY_FRAUD",
        "BIOMETRIC_MASS_COLLECTION",
    };

    /// <summary>
    /// C-062: autonomous AI write/execute access to these infrastructure systems is prohibited.
    /// Read-only access is permitted for observability; any action flagging these as
    /// target_system is denied unless it carries an explicit human approval token.
    /// </summary>
    private static readonly HashSet<string> ProtectedSystems = new(StringComparer.OrdinalIgnoreCase)
    {
        "identity-provider",
        "authentication-service",
        "certificate-authority",
        "key-management-service",
        "audit-ledger",
        "constitutional-engine",
        "emergency-stop-controller",
        "secret-manager",
        "payment-processor",
    };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    // C-073: constructor-injection only; ArgumentNullException guards per null-safety standard
    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId declares the constitutional claim this evaluator enforces
    public string ClaimId => "C-062";

    /// <summary>
    /// C-073: Evaluates C-062 (AI Security). Short-circuits to DENY on:
    ///   1. Prohibited security_classification parameter value.
    ///   2. Autonomous action targeting a protected system.
    /// Escalates when requires_human_oversight=true is declared by the caller.
    /// All other actions are ALLOWED (no DB I/O required — purely parameter-driven).
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("claim.id", ClaimId);
        activity?.SetTag("tenant.id", ctx.TenantId);
        activity?.SetTag("action.type", ctx.ActionType);

        // ── Check 1: security_classification must not be in the prohibited set ──────────────
        // C-073: C-062 prohibits AI action on weaponised, mass-surveillance, or deception categories.
        var classification = ctx.GetParameter("security_classification");
        if (!string.IsNullOrWhiteSpace(classification) &&
            ProhibitedClassifications.Contains(classification))
        {
            _logger.LogWarning(
                "C-062 DENY — prohibited security_classification={Classification} TenantId={TenantId} ActionType={ActionType}",
                classification, ctx.TenantId, ctx.ActionType);

            activity?.SetTag("deny.reason", "prohibited_classification");
            activity?.SetTag("security_classification", classification);
            return Task.FromResult(Deny(
                $"C-062: security_classification '{classification}' is constitutionally prohibited for autonomous AI execution."));
        }

        // ── Check 2: target_system must not be a protected infrastructure system ───────────
        // C-073: C-062 bars autonomous AI access to identity, cryptographic, audit, and control systems.
        var targetSystem = ctx.GetParameter("target_system");
        if (!string.IsNullOrWhiteSpace(targetSystem) &&
            ProtectedSystems.Contains(targetSystem))
        {
            _logger.LogWarning(
                "C-062 DENY — target_system={TargetSystem} is a protected system. TenantId={TenantId} ActionType={ActionType}",
                targetSystem, ctx.TenantId, ctx.ActionType);

            activity?.SetTag("deny.reason", "protected_system");
            activity?.SetTag("target_system", targetSystem);
            return Task.FromResult(Deny(
                $"C-062: target_system '{targetSystem}' is a protected infrastructure system — autonomous AI access is prohibited."));
        }

        // ── Check 3: requires_human_oversight flag → escalate to C-049 path ────────────────
        // C-073: when the caller declares that a human must approve, C-062 escalates rather
        // than allows, ensuring the Escalate verdict triggers human-review workflow.
        var requiresOversight = ctx.GetParameter("requires_human_oversight");
        if (string.Equals(requiresOversight, "true", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogInformation(
                "C-062 ESCALATE — requires_human_oversight=true TenantId={TenantId} ActionType={ActionType}",
                ctx.TenantId, ctx.ActionType);

            activity?.SetTag("escalate.reason", "requires_human_oversight");
            return Task.FromResult(Escalate(
                "C-062: action declared requires_human_oversight=true — escalating to human review per AI Security policy."));
        }

        // ── All C-062 checks passed ───────────────────────────────────────────────────────
        _logger.LogInformation(
            "C-062 ALLOW — AI security checks passed. TenantId={TenantId} ActionType={ActionType}",
            ctx.TenantId, ctx.ActionType);

        activity?.SetTag("verdict", "allow");
        return Task.FromResult(Allow());
    }

    // ── Private result helpers (C-073: named helpers make denial paths explicit) ─────────

    private EvaluationResult Deny(string reason) =>
        new(ClaimId, EvaluationVerdict.Deny, reason);

    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);

    private EvaluationResult Allow() =>
        new(ClaimId, EvaluationVerdict.Allow, "C-062: action passed all AI security checks.");
}