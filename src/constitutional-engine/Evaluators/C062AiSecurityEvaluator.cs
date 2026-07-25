// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-062 (AI Security) — prevents AI agents from operating outside
/// their permitted security boundary: accessing prohibited security classifications,
/// targeting protected governance systems, or signalling bypass of constitutional controls.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: Shared ActivitySource per service — name must match OTel configuration in Program.cs.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-073: Security classifications that unconditionally prohibit AI agent execution.
    // DESIGN_QUESTION: Should CONFIDENTIAL be denied or escalated? Marking Escalate path not
    // implemented until EA confirms C-062 scope vs C-049 Honest Limitation boundary.
    private static readonly HashSet<string> ProhibitedClassifications =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "RESTRICTED",
            "TOP_SECRET",
            "PROHIBITED",
        };

    // C-073: Systems that AI agents must never directly access or modify.
    // Protecting constitutional governance infrastructure enforces the PAAS boundary (§2).
    private static readonly HashSet<string> ProtectedSystems =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "constitutional-engine",
            "audit-records",
            "governance",
            "identity-provider",
            "keycloak",
        };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    // C-073: Constructor — constructor injection only (C-059, DI contract).
    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc />
    // C-073: ClaimId — identifies this evaluator in audit records (C-023 Evidence First).
    public string ClaimId => "C-062";

    /// <inheritdoc />
    // C-073: EvaluateAsync implements C-062 — three-gate AI security check:
    //   Gate 1: security_classification must not be in the prohibited set.
    //   Gate 2: target_system must not be a protected governance system.
    //   Gate 3: explicit ai_security_bypass=true is unconditionally denied.
    //   Default: Allow (C-041 owns default-deny for unlisted tools).
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Gate 1: Security classification ─────────────────────────────────────────
        // C-073: C-062 prohibits AI agents from executing actions tagged with restricted
        // security classifications — these require human handling outside the AI boundary.
        var securityClassification = ctx.GetParameter("security_classification");
        if (securityClassification is not null &&
            ProhibitedClassifications.Contains(securityClassification))
        {
            _logger.LogWarning(
                "C-062 DENY: prohibited security_classification={Classification} " +
                "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                securityClassification,
                ctx.TenantId,
                ctx.ActionType,
                ctx.ContractId);

            activity?.SetTag("c062.deny_reason", "prohibited_classification");
            activity?.SetTag("c062.security_classification", securityClassification);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-062: Security classification '{securityClassification}' is prohibited " +
                "for AI agent operations. Human handling required."));
        }

        // ── Gate 2: Protected system access ─────────────────────────────────────────
        // C-073: AI agents must not directly access or modify constitutional governance
        // infrastructure. Violation would undermine the PAAS boundary (CE §2).
        var targetSystem = ctx.GetParameter("target_system");
        if (targetSystem is not null)
        {
            var matched = ProtectedSystems.FirstOrDefault(ps =>
                targetSystem.Contains(ps, StringComparison.OrdinalIgnoreCase));

            if (matched is not null)
            {
                _logger.LogWarning(
                    "C-062 DENY: AI agent targeting protected system={TargetSystem} " +
                    "MatchedBoundary={Matched} TenantId={TenantId} ActionType={ActionType}",
                    targetSystem,
                    matched,
                    ctx.TenantId,
                    ctx.ActionType);

                activity?.SetTag("c062.deny_reason", "protected_system_access");
                activity?.SetTag("c062.target_system", targetSystem);
                activity?.SetTag("c062.matched_boundary", matched);

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: AI agents may not directly access or modify protected system " +
                    $"'{targetSystem}'. Constitutional governance boundary enforced."));
            }
        }

        // ── Gate 3: Explicit bypass attempt ──────────────────────────────────────────
        // C-073: Any request carrying ai_security_bypass=true is an unconditional DENY.
        // Logged at Critical severity — this is a canary signal for adversarial probing.
        var bypassAttempt = ctx.GetParameter("ai_security_bypass");
        if (string.Equals(bypassAttempt, "true", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogCritical(
                "C-062 DENY: ai_security_bypass=true detected — possible adversarial probe. " +
                "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                ctx.TenantId,
                ctx.ActionType,
                ctx.ContractId);

            activity?.SetTag("c062.deny_reason", "bypass_attempt");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: AI security bypass attempts are unconditionally denied and escalated " +
                "to governance review."));
        }

        // ── All gates passed: Allow ───────────────────────────────────────────────────
        _logger.LogDebug(
            "C-062 Allow: TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
            ctx.TenantId,
            ctx.ActionType,
            ctx.ContractId);

        activity?.SetTag("c062.verdict", "allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-062: AI security checks passed."));
    }
}