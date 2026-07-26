// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Evaluator for constitutional claim C-062 (AI Security).
/// Unconditionally denies actions bearing a prohibited security classification.
/// Escalates actions targeting protected platform systems to human review (Sujay, C-049 path).
/// All other actions are allowed — evaluator is not default-deny on its own; C-041 handles
/// the tool-authorization default-deny gate upstream.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-073: Prohibited security classifications — any action bearing one of these is unconditionally denied.
    // Classifications are vendor/agent-reported via the ActionParameters JSON field "security_classification".
    private static readonly HashSet<string> ProhibitedClassifications =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "OFFENSIVE_SECURITY",
            "MALWARE_GENERATION",
            "CREDENTIAL_HARVESTING",
            "VULNERABILITY_EXPLOITATION",
            "DATA_EXFILTRATION",
            "COVERT_CHANNEL",
            "PRIVILEGE_ESCALATION",
            "ROOTKIT",
            "RANSOMWARE",
            "SOCIAL_ENGINEERING",
            "PHISHING",
            "DENIAL_OF_SERVICE",
        };

    // C-073: Protected systems — direct automated access to these requires human authorisation.
    // System name is reported via ActionParameters JSON field "target_system".
    private static readonly HashSet<string> ProtectedSystems =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "keycloak",
            "constitutional-engine",
            "production-database",
            "temporal-server",
            "payment-gateway",
            "hr-database",
            "identity-provider",
            "secret-manager",
            "certificate-authority",
            "audit-ledger",
        };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>Constitutional claim ID this evaluator enforces.</summary>
    public string ClaimId => "C-062";

    // C-073: EvaluateAsync enforces C-062 (AI Security):
    //   1. Prohibited security_classification → DENY (unconditional, short-circuits registry)
    //   2. Protected target_system            → ESCALATE (human authorisation required)
    //   3. Neither                            → ALLOW (no AI security violation detected)
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("claim_id",    ClaimId);
        activity?.SetTag("tenant_id",   ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);

        // C-073: Extract security signals from JSON-encoded ActionParameters
        var securityClassification = ctx.GetParameter("security_classification");
        var targetSystem           = ctx.GetParameter("target_system");

        activity?.SetTag("security_classification", securityClassification ?? "(none)");
        activity?.SetTag("target_system",           targetSystem           ?? "(none)");

        // ── Gate 1: Prohibited classification — unconditional DENY ────────────────────────
        // C-073: An action self-reporting (or agent-annotated) with a prohibited classification
        // is denied regardless of tool authorisation state, budget, or any other claim.
        if (!string.IsNullOrWhiteSpace(securityClassification) &&
            ProhibitedClassifications.Contains(securityClassification))
        {
            _logger.LogWarning(
                "C-062 DENY: ProhibitedClassification={Classification} " +
                "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                securityClassification,
                ctx.TenantId,
                ctx.ActionType,
                ctx.ContractId);

            activity?.SetTag("decision",     "Deny");
            activity?.SetTag("deny_trigger", "prohibited_classification");

            return Task.FromResult(
                Deny($"C-062: Security classification '{securityClassification}' is prohibited " +
                     "under the AI Security policy — automated action denied."));
        }

        // ── Gate 2: Protected system — ESCALATE to human review ──────────────────────────
        // C-073: Actions targeting a protected platform system cannot be approved autonomously.
        // The agent must surface this to Sujay for explicit human authorisation (C-049 path).
        if (!string.IsNullOrWhiteSpace(targetSystem) &&
            ProtectedSystems.Contains(targetSystem))
        {
            _logger.LogWarning(
                "C-062 ESCALATE: ProtectedSystem={System} " +
                "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                targetSystem,
                ctx.TenantId,
                ctx.ActionType,
                ctx.ContractId);

            activity?.SetTag("decision",          "Escalate");
            activity?.SetTag("escalate_trigger",  "protected_system");

            return Task.FromResult(
                Escalate($"C-062: Target system '{targetSystem}' is a constitutionally protected " +
                         "system — human authorisation required before proceeding."));
        }

        // ── Gate 3: No AI security violation ─────────────────────────────────────────────
        _logger.LogDebug(
            "C-062 ALLOW: TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
            ctx.TenantId,
            ctx.ActionType,
            ctx.ContractId);

        activity?.SetTag("decision", "Allow");

        return Task.FromResult(Allow());
    }

    // ── Private result factories ──────────────────────────────────────────────────────────

    private EvaluationResult Deny(string reason) =>
        new(ClaimId, EvaluationVerdict.Deny, reason);

    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);

    private EvaluationResult Allow() =>
        new(ClaimId, EvaluationVerdict.Allow,
            "C-062: No prohibited security classification or protected system target detected.");
}