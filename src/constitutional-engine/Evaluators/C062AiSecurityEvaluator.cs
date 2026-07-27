// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability),
//                       ADR-001 (gRPC Constitutional Engine)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security): prevents AI actions that violate PAAS security boundaries.
/// Evaluates three independent security signals — sandbox escape, cross-tenant isolation,
/// and AI security risk level — in order of severity (most critical first).
/// Short-circuits to DENY on the first critical violation.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource for tracing constitutional evaluation spans (C-059 traceability)
    private static readonly ActivitySource _tracer =
        new("Waooaw.ConstitutionalEngine.C062AiSecurityEvaluator");

    // ── ActionParameters keys (JSON-encoded; extracted via ctx.GetParameter) ────────────
    internal const string ParamAiSecurityRiskLevel   = "ai_security_risk_level";
    internal const string ParamSandboxEscapeAttempt  = "sandbox_escape_attempt";
    internal const string ParamCrossTenantDataAccess = "cross_tenant_data_access";

    // ── Risk level constants (case-normalised in switch) ─────────────────────────────────
    internal const string RiskLevelProhibited = "PROHIBITED";
    internal const string RiskLevelHigh       = "HIGH";
    internal const string RiskLevelMedium     = "MEDIUM";

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        // C-073: Constructor enforces non-null dependency injection (C-059 constructor discipline)
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: ClaimId binds this evaluator to constitutional claim C-062
    public string ClaimId => "C-062";

    // C-073: EvaluateAsync enforces C-062 AI Security PAAS boundary validation at runtime
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.Evaluate", ActivityKind.Internal);

        activity?.SetTag("tenant_id",    ctx.TenantId);
        activity?.SetTag("action_type",  ctx.ActionType);
        activity?.SetTag("contract_id",  ctx.ContractId);
        activity?.SetTag("claim_id",     ClaimId);

        var result = Evaluate(ctx, activity);

        activity?.SetTag("verdict", result.Verdict.ToString());

        // C-073: Structured log satisfies C-023 (Evidence First) audit trail requirement
        _logger.LogInformation(
            "C-062 AI Security evaluation: TenantId={TenantId} ActionType={ActionType} " +
            "ContractId={ContractId} Verdict={Verdict} Reason={Reason}",
            ctx.TenantId, ctx.ActionType, ctx.ContractId, result.Verdict, result.Reason);

        return Task.FromResult(result);
    }

    // C-073: Synchronous core evaluation — no I/O permitted (40ms budget constraint)
    private EvaluationResult Evaluate(EvaluationContext ctx, Activity? activity)
    {
        // ── Signal 1: Sandbox escape attempt ─────────────────────────────────────────────
        // C-073: Sandbox escape is a critical security boundary violation — immediate DENY.
        // Evaluated first: any indication of escape overrides all other signals.
        var sandboxEscape = ctx.GetParameter(ParamSandboxEscapeAttempt);
        if (string.Equals(sandboxEscape, "true", StringComparison.OrdinalIgnoreCase))
        {
            activity?.SetTag("deny_reason", "sandbox_escape_attempt");
            _logger.LogWarning(
                "C-062 DENY: Sandbox escape attempt detected. TenantId={TenantId} ActionType={ActionType}",
                ctx.TenantId, ctx.ActionType);
            return Deny(
                "C-062: Sandbox escape attempt detected — action denied per AI security policy (PAAS boundary violation).");
        }

        // ── Signal 2: Cross-tenant data access ───────────────────────────────────────────
        // C-073: Cross-tenant access violates tenant isolation — immediate DENY.
        // A compromised or misconfigured agent must not read/write across tenant boundaries.
        var crossTenant = ctx.GetParameter(ParamCrossTenantDataAccess);
        if (string.Equals(crossTenant, "true", StringComparison.OrdinalIgnoreCase))
        {
            activity?.SetTag("deny_reason", "cross_tenant_data_access");
            _logger.LogWarning(
                "C-062 DENY: Cross-tenant data access attempt. TenantId={TenantId} ActionType={ActionType}",
                ctx.TenantId, ctx.ActionType);
            return Deny(
                "C-062: Cross-tenant data access denied — tenant isolation boundary violated per AI security policy.");
        }

        // ── Signal 3: AI security risk level ─────────────────────────────────────────────
        // C-073: Risk level drives the final decision for tool/action classification.
        // PROHIBITED/HIGH → DENY. MEDIUM → ESCALATE (human review via C-049 path).
        // Missing/LOW/unrecognised → ALLOW (permissive for unclassified operational actions).
        var rawRiskLevel = ctx.GetParameter(ParamAiSecurityRiskLevel);

        if (rawRiskLevel is null)
        {
            // C-073: No risk level declared — action proceeds; absence is not a prohibition.
            // DESIGN_QUESTION: Should unclassified actions default to ESCALATE rather than ALLOW?
            //                  Flag for EA review — current spec does not mandate escalation for absent risk level.
            activity?.SetTag("ai_security_risk_level", "unclassified");
            return Allow("C-062: No AI security risk level specified — action permitted (unclassified).");
        }

        var normalisedRiskLevel = rawRiskLevel.ToUpperInvariant();
        activity?.SetTag("ai_security_risk_level", normalisedRiskLevel);

        return normalisedRiskLevel switch
        {
            RiskLevelProhibited => DenyRisk(rawRiskLevel, "prohibited"),
            RiskLevelHigh       => DenyRisk(rawRiskLevel, "high"),
            RiskLevelMedium     => EscalateRisk(rawRiskLevel),
            _                   => AllowRisk(rawRiskLevel)
        };
    }

    // ── Private result helpers ────────────────────────────────────────────────────────────

    private EvaluationResult DenyRisk(string level, string label)
    {
        _logger.LogWarning(
            "C-062 DENY: AI security risk level '{Level}' ({Label}) is not permitted.",
            level, label);
        return Deny(
            $"C-062: Action has {label} AI security risk level '{level}' — denied per AI security policy.");
    }

    private EvaluationResult EscalateRisk(string level)
    {
        _logger.LogInformation(
            "C-062 ESCALATE: AI security risk level '{Level}' requires human review.", level);
        return Escalate(
            $"C-062: Action has medium AI security risk level '{level}' — escalated to human review per C-049.");
    }

    private EvaluationResult AllowRisk(string level)
    {
        _logger.LogInformation(
            "C-062 ALLOW: AI security risk level '{Level}' within acceptable bounds.", level);
        return Allow(
            $"C-062: AI security risk level '{level}' is within acceptable bounds — action permitted.");
    }

    private EvaluationResult Allow(string reason)    => new(ClaimId, EvaluationVerdict.Allow,    reason);
    private EvaluationResult Deny(string reason)     => new(ClaimId, EvaluationVerdict.Deny,     reason);
    private EvaluationResult Escalate(string reason) => new(ClaimId, EvaluationVerdict.Escalate, reason);
}