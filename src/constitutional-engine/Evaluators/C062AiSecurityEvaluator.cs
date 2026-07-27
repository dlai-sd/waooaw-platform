// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-062 (AI Security) — denies actions with prohibited security classifications
/// and escalates actions targeting protected platform systems for mandatory human review.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource instruments every evaluation for OpenTelemetry (ADR-009)
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-073: ProhibitedClassifications — C-062 hard-deny boundary.
    // Any action whose tool_classification or security_classification matches is
    // unconditionally denied regardless of tenant or action type.
    private static readonly HashSet<string> ProhibitedClassifications =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "WEAPON",
            "MALWARE",
            "EXPLOIT",
            "EXFILTRATION",
            "CREDENTIAL_HARVEST",
            "RANSOMWARE",
            "SOCIAL_ENGINEERING",
            "PROMPT_INJECTION",
            "DATA_POISONING",
            "MODEL_INVERSION",
        };

    // C-073: ProtectedSystems — C-062 escalation boundary.
    // Actions targeting these systems are not denied outright but must be
    // escalated to a human (C-049 Honest Limitation path) before execution.
    private static readonly HashSet<string> ProtectedSystems =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "CONSTITUTIONAL_ENGINE",
            "AUTH_SERVICE",
            "KEYCLOAK",
            "DATABASE",
            "AUDIT_LOG",
            "EMERGENCY_STOP",
            "TEMPORAL",
            "SECRET_STORE",
            "TERRAFORM_STATE",
        };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    /// <summary>C-073: Constructor — enforces C-062 via DI-injected logger.</summary>
    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId identifies which constitutional obligation this evaluator enforces.
    /// <inheritdoc />
    public string ClaimId => "C-062";

    /// <summary>
    /// C-073: EvaluateAsync — enforces C-062 AI Security boundary.
    ///
    /// Decision matrix:
    ///   tool_classification or security_classification ∈ ProhibitedClassifications → DENY
    ///   target_system ∈ ProtectedSystems                                           → ESCALATE
    ///   otherwise                                                                  → ALLOW
    ///
    /// Completes in O(1) — no network I/O, hash-set lookups only.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Instrument every evaluation with an OpenTelemetry activity (ADR-009, C-059)
        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("tenant_id",   ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);
        activity?.SetTag("claim_id",    ClaimId);

        // ── Guard 1: Prohibited tool classification (hard deny) ──────────────────────
        // C-073: Checks tool_classification parameter — prohibited action types are never
        // authorized regardless of contract or tenant configuration (C-062 §3.1).
        var toolClassification = ctx.GetParameter("tool_classification");
        if (!string.IsNullOrWhiteSpace(toolClassification) &&
            ProhibitedClassifications.Contains(toolClassification))
        {
            _logger.LogWarning(
                "C-062 DENY: tool_classification={Classification} is in prohibited list. " +
                "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                toolClassification, ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("c062.decision",                     "deny");
            activity?.SetTag("c062.prohibited_classification",    toolClassification);
            activity?.SetTag("c062.deny_reason",                  "tool_classification");

            return Task.FromResult(Deny(
                $"C-062: tool_classification '{toolClassification}' is prohibited under AI security policy."));
        }

        // ── Guard 2: Prohibited security classification (hard deny) ──────────────────
        // C-073: Supports callers that supply the classification under the alternate key
        // 'security_classification' — both keys are authoritative for C-062 enforcement.
        var securityClassification = ctx.GetParameter("security_classification");
        if (!string.IsNullOrWhiteSpace(securityClassification) &&
            ProhibitedClassifications.Contains(securityClassification))
        {
            _logger.LogWarning(
                "C-062 DENY: security_classification={Classification} is in prohibited list. " +
                "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                securityClassification, ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("c062.decision",                          "deny");
            activity?.SetTag("c062.prohibited_security_classification", securityClassification);
            activity?.SetTag("c062.deny_reason",                       "security_classification");

            return Task.FromResult(Deny(
                $"C-062: security_classification '{securityClassification}' is prohibited under AI security policy."));
        }

        // ── Guard 3: Protected system target (escalate to human) ─────────────────────
        // C-073: Actions targeting protected platform systems are not unconditionally denied
        // but must be escalated — the human principal (C-001) must authorize access to
        // internal infrastructure systems before the agent may proceed (C-062 §3.2).
        var targetSystem = ctx.GetParameter("target_system");
        if (!string.IsNullOrWhiteSpace(targetSystem) &&
            ProtectedSystems.Contains(targetSystem))
        {
            _logger.LogWarning(
                "C-062 ESCALATE: target_system={System} is a protected system — human approval required. " +
                "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                targetSystem, ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("c062.decision",         "escalate");
            activity?.SetTag("c062.protected_system", targetSystem);

            return Task.FromResult(Escalate(
                $"C-062: target_system '{targetSystem}' is a protected platform system — " +
                "human approval required before proceeding."));
        }

        // ── All C-062 checks passed ───────────────────────────────────────────────────
        _logger.LogDebug(
            "C-062 ALLOW: AI security checks passed. " +
            "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
            ctx.TenantId, ctx.ActionType, ctx.ContractId);

        activity?.SetTag("c062.decision", "allow");

        return Task.FromResult(Allow());
    }

    // ── Private result helpers ────────────────────────────────────────────────────────

    // C-073: Deny — produces a C-062 denial result with mandatory reason text (C-023)
    private EvaluationResult Deny(string reason) =>
        new(ClaimId, EvaluationVerdict.Deny, reason);

    // C-073: Escalate — produces a C-062 escalation result for human review (C-049 path)
    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);

    // C-073: Allow — produced only when all C-062 security boundary checks pass
    private EvaluationResult Allow() =>
        new(ClaimId, EvaluationVerdict.Allow, "C-062: AI security boundary checks passed.");
}