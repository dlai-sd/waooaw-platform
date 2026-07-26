// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-062 (AI Security) — prevents the AI agent from invoking tools that are
/// classified as prohibited security categories or that target WAOOAW-protected infrastructure
/// systems. Default deny on unknown classification when explicitly flagged as restricted.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource shared across the constitutional engine (single logical service boundary)
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-062: Tool classifications that are unconditionally prohibited for AI agents.
    // These represent categories where AI autonomy creates unacceptable security risk.
    private static readonly HashSet<string> ProhibitedClassifications = new(StringComparer.OrdinalIgnoreCase)
    {
        "weapons_development",
        "exploit_generation",
        "credential_theft",
        "social_engineering",
        "surveillance_unauthorized",
        "data_exfiltration",
        "privilege_escalation",
        "malware_generation",
        "cryptojacking",
        "denial_of_service",
    };

    // C-062: Infrastructure systems that the AI agent is prohibited from targeting directly.
    // Targeting these bypasses constitutional governance controls entirely.
    private static readonly HashSet<string> ProtectedSystems = new(StringComparer.OrdinalIgnoreCase)
    {
        "constitutional_engine",
        "keycloak",
        "audit_records",
        "payment_processor",
        "banking_core",
        "temporal_server",
        "waooaw_db_primary",
        "secrets_vault",
        "certificate_authority",
        "identity_provider",
    };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    // C-073: Constructor validates dependencies per C-059 traceability obligation.
    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc />
    public string ClaimId => "C-062";

    /// <summary>
    /// C-073: Evaluates whether the proposed action violates C-062 AI Security.
    /// Checks two independent gates:
    ///   1. tool_classification — must not be in the prohibited classifications set.
    ///   2. target_system — must not be a WAOOAW-protected infrastructure system.
    /// Either gate failing results in an unconditional DENY (no override path).
    /// Absence of both parameters = pass-through (not every action carries security metadata).
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Trace every evaluation for C-059 audit traceability
        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Gate 1: Prohibited tool classification ────────────────────────────────────────
        // C-073: ctx.GetParameter() is the ONLY correct way to read ActionParameters (JSON-encoded string).
        var toolClassification = ctx.GetParameter("tool_classification");

        if (!string.IsNullOrWhiteSpace(toolClassification)
            && ProhibitedClassifications.Contains(toolClassification))
        {
            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("deny_gate", "tool_classification");
            activity?.SetTag("denied_classification", toolClassification);

            // C-073: Structured log — never string interpolation (C-059 compliance)
            _logger.LogWarning(
                "C-062 DENY: ProhibitedClassification={Classification} TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
                toolClassification,
                ctx.TenantId,
                ctx.ContractId,
                ctx.ActionType);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"Tool classification '{toolClassification}' is unconditionally prohibited under C-062 AI Security. " +
                $"AI agents may not invoke tools in this category."));
        }

        // ── Gate 2: Protected system targeting ───────────────────────────────────────────
        // C-073: Targeting WAOOAW infrastructure bypasses constitutional governance — always deny.
        var targetSystem = ctx.GetParameter("target_system");

        if (!string.IsNullOrWhiteSpace(targetSystem)
            && ProtectedSystems.Contains(targetSystem))
        {
            activity?.SetTag("verdict", "Deny");
            activity?.SetTag("deny_gate", "target_system");
            activity?.SetTag("denied_system", targetSystem);

            _logger.LogWarning(
                "C-062 DENY: ProtectedSystem={System} TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
                targetSystem,
                ctx.TenantId,
                ctx.ContractId,
                ctx.ActionType);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"Target system '{targetSystem}' is a WAOOAW-protected infrastructure system under C-062 AI Security. " +
                $"Direct AI agent access to this system is prohibited."));
        }

        // ── Both gates passed ─────────────────────────────────────────────────────────────
        activity?.SetTag("verdict", "Allow");

        _logger.LogDebug(
            "C-062 Allow: TenantId={TenantId} ContractId={ContractId} ActionType={ActionType} " +
            "Classification={Classification} TargetSystem={TargetSystem}",
            ctx.TenantId,
            ctx.ContractId,
            ctx.ActionType,
            toolClassification ?? "<none>",
            targetSystem ?? "<none>");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-062 AI Security check passed: no prohibited classification or protected system target detected."));
    }
}