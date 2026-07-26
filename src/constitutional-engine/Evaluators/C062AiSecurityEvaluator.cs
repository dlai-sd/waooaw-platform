// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 AI Security at runtime by denying actions whose security
/// classification is prohibited, denying unattended access to protected systems,
/// and escalating actions that carry an explicit threat indicator for human review.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: Constitutional annotation — shared ActivitySource for OpenTelemetry tracing
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-073: Constitutional annotation — action classifications always prohibited under C-062.
    // Any action whose 'security_classification' parameter matches one of these values is DENIED.
    private static readonly HashSet<string> ProhibitedClassifications = new(StringComparer.OrdinalIgnoreCase)
    {
        "offensive_security",
        "credential_harvesting",
        "data_exfiltration",
        "privilege_escalation",
        "malware_execution",
        "social_engineering",
        "unauthorized_reconnaissance",
        "exploit_execution",
        "lateral_movement",
        "persistence_mechanism",
    };

    // C-073: Constitutional annotation — systems requiring an explicit 'system_authorization_token'
    // parameter before access is permitted under C-062.
    private static readonly HashSet<string> ProtectedSystems = new(StringComparer.OrdinalIgnoreCase)
    {
        "production_database",
        "payment_gateway",
        "identity_provider",
        "secrets_vault",
        "audit_ledger",
        "constitutional_engine",
        "hr_system",
        "financial_system",
        "certificate_authority",
        "key_management_service",
    };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Constitutional annotation — ClaimId ties this evaluator to the C-062 AI Security claim
    public string ClaimId => "C-062";

    /// <summary>
    /// C-073: Evaluates the incoming action against the C-062 AI Security policy.
    ///
    /// Evaluation order (short-circuits on first match):
    ///   1. DENY   — action_classification ∈ ProhibitedClassifications
    ///   2. DENY   — target_system ∈ ProtectedSystems AND system_authorization_token is absent/empty
    ///   3. ESCALATE — threat_indicator parameter is present and non-empty (forward to human review)
    ///   4. ALLOW  — no security violations detected
    ///
    /// MUST NOT perform network I/O — all evaluation is against parameters already present
    /// in the EvaluationContext (parsed from the JSON-encoded ActionParameters via GetParameter).
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Constitutional annotation — honour cancellation before any work begins
        ct.ThrowIfCancellationRequested();

        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("claim_id",    ClaimId);
        activity?.SetTag("tenant_id",   ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Check 1: Prohibited security classification ──────────────────────────
        // C-073: C-062 requires that any action whose classification matches a known
        // prohibited category is denied before any further evaluation.
        var classification = ctx.GetParameter("security_classification");
        if (!string.IsNullOrWhiteSpace(classification) &&
            ProhibitedClassifications.Contains(classification))
        {
            _logger.LogWarning(
                "C-062 DENY: prohibited security classification. " +
                "Classification={Classification} TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                classification, ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("deny_reason",             "prohibited_classification");
            activity?.SetTag("security_classification", classification);
            activity?.SetTag("verdict",                 "deny");

            return Task.FromResult(
                Deny($"Security classification '{classification}' is prohibited under C-062 AI Security policy."));
        }

        // ── Check 2: Protected system access without authorization token ──────────
        // C-073: Access to protected systems requires an explicit system_authorization_token.
        // Absence of the token when the target is a protected system is an automatic DENY.
        var targetSystem = ctx.GetParameter("target_system");
        if (!string.IsNullOrWhiteSpace(targetSystem) &&
            ProtectedSystems.Contains(targetSystem))
        {
            var authorizationToken = ctx.GetParameter("system_authorization_token");
            if (string.IsNullOrWhiteSpace(authorizationToken))
            {
                _logger.LogWarning(
                    "C-062 DENY: protected system access without authorization token. " +
                    "TargetSystem={TargetSystem} TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                    targetSystem, ctx.TenantId, ctx.ActionType, ctx.ContractId);

                activity?.SetTag("deny_reason",   "missing_system_authorization_token");
                activity?.SetTag("target_system", targetSystem);
                activity?.SetTag("verdict",       "deny");

                return Task.FromResult(
                    Deny($"Access to protected system '{targetSystem}' requires a " +
                         "'system_authorization_token' parameter under C-062 AI Security policy."));
            }

            _logger.LogDebug(
                "C-062: protected system access authorized by token. " +
                "TargetSystem={TargetSystem} TenantId={TenantId}",
                targetSystem, ctx.TenantId);

            activity?.SetTag("target_system",       targetSystem);
            activity?.SetTag("system_auth_present", true);
        }

        // ── Check 3: Explicit threat indicator — escalate for human review ────────
        // C-073: C-049 (Honest Limitation) intersects with C-062 here: if the agent has
        // detected an ambiguous threat indicator it cannot resolve, it must escalate rather
        // than self-approve (C-049) or silently deny (C-062).
        var threatIndicator = ctx.GetParameter("threat_indicator");
        if (!string.IsNullOrWhiteSpace(threatIndicator))
        {
            _logger.LogWarning(
                "C-062 ESCALATE: threat indicator detected — forwarding to human review. " +
                "ThreatIndicator={ThreatIndicator} TenantId={TenantId} ActionType={ActionType}",
                threatIndicator, ctx.TenantId, ctx.ActionType);

            activity?.SetTag("escalate_reason",  "threat_indicator_present");
            activity?.SetTag("threat_indicator", threatIndicator);
            activity?.SetTag("verdict",          "escalate");

            return Task.FromResult(
                Escalate($"Threat indicator '{threatIndicator}' detected — " +
                         "escalating to human review per C-062 AI Security / C-049 Honest Limitation."));
        }

        // ── All checks passed — ALLOW ─────────────────────────────────────────────
        _logger.LogDebug(
            "C-062 ALLOW: no AI security violations detected. " +
            "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
            ctx.TenantId, ctx.ActionType, ctx.ContractId);

        activity?.SetTag("verdict", "allow");

        return Task.FromResult(Allow());
    }

    // ── Private result helpers ────────────────────────────────────────────────────

    // C-073: Constitutional annotation — wraps a DENY verdict; reason is mandatory per C-023
    private EvaluationResult Deny(string reason) =>
        new(ClaimId, EvaluationVerdict.Deny, reason);

    // C-073: Constitutional annotation — wraps an ESCALATE verdict for human review paths
    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);

    // C-073: Constitutional annotation — wraps an ALLOW verdict when no violations detected
    private EvaluationResult Allow() =>
        new(ClaimId, EvaluationVerdict.Allow, "No C-062 AI Security violations detected.");
}