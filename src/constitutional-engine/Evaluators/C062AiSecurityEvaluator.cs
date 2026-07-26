// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security) by denying requests whose tool classification is
/// prohibited or whose target system is a protected WAOOAW platform component.
/// No network I/O — decision is pure in-memory set membership.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: Activity source shared across all CE evaluators (one logical service boundary)
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-073: C-062 AI Security — tool classifications the constitution prohibits outright.
    // Any tool_classification parameter matching this set receives an immediate DENY.
    private static readonly HashSet<string> ProhibitedClassifications =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "weapons",
            "surveillance_unlicensed",
            "biometric_exploitation",
            "adversarial_ml",
            "deepfake_generation",
            "social_engineering",
            "credential_harvesting",
            "data_exfiltration",
            "ransom_encryption",
            "covert_persistence",
        };

    // C-073: C-062 AI Security — WAOOAW platform systems agents must NOT directly manipulate.
    // Any target_system parameter matching this set receives an immediate DENY.
    private static readonly HashSet<string> ProtectedSystems =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "constitutional_engine",
            "keycloak",
            "temporal",
            "postgres",
            "audit_ledger",
            "waooaw_platform",
            "emergency_stop",
            "evidence_store",
        };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>Constitutional claim enforced by this evaluator.</summary>
    public string ClaimId => "C-062";

    // C-073: Enforces C-062 (AI Security) — evaluates tool_classification and target_system
    // parameters against constitutional prohibited/protected sets. Short-circuits on first violation.
    // Must complete synchronously (no I/O) to stay within the 40 ms ValidateAction budget.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.EvaluateAsync", ActivityKind.Internal);

        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Check 1: prohibited tool classification (C-062 AI Security boundary) ───────────────
        // C-073: tool_classification is extracted from JSON-encoded ActionParameters via GetParameter.
        var toolClassification = ctx.GetParameter("tool_classification");

        if (!string.IsNullOrWhiteSpace(toolClassification) &&
            ProhibitedClassifications.Contains(toolClassification))
        {
            _logger.LogWarning(
                "C-062 DENY prohibited tool classification: Classification={Classification} " +
                "TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
                toolClassification, ctx.TenantId, ctx.ContractId, ctx.ActionType);

            activity?.SetTag("deny_reason", "prohibited_classification");
            activity?.SetTag("tool_classification", toolClassification);
            activity?.SetTag("verdict", "deny");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-062: Tool classification '{toolClassification}' is prohibited " +
                        "under the AI Security constitutional boundary."));
        }

        // ── Check 2: direct manipulation of a protected WAOOAW platform system ────────────────
        // C-073: target_system identifies the downstream system the agent intends to call.
        // Agents must route through sanctioned MCP tools — never bypass via direct system access.
        var targetSystem = ctx.GetParameter("target_system");

        if (!string.IsNullOrWhiteSpace(targetSystem) &&
            ProtectedSystems.Contains(targetSystem))
        {
            _logger.LogWarning(
                "C-062 DENY protected system targeted: TargetSystem={TargetSystem} " +
                "TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
                targetSystem, ctx.TenantId, ctx.ContractId, ctx.ActionType);

            activity?.SetTag("deny_reason", "protected_system");
            activity?.SetTag("target_system", targetSystem);
            activity?.SetTag("verdict", "deny");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-062: Direct manipulation of protected platform system '{targetSystem}' " +
                        "is prohibited. Route through authorised MCP tools."));
        }

        // ── No C-062 violation detected ──────────────────────────────────────────────────────
        _logger.LogDebug(
            "C-062 ALLOW: no AI security violation detected " +
            "TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
            ctx.TenantId, ctx.ContractId, ctx.ActionType);

        activity?.SetTag("verdict", "allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: "C-062: No AI security boundary violation detected."));
    }
}