// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062
//             architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-062 (AI Security), C-059 (Traceability), C-073 (Annotated Obligations)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security): blocks actions that violate the PAAS security boundary,
/// attempt prohibited tool categories, or request cross-tenant / unrestricted data scope.
/// Default-deny posture — any unrecognised security classification triggers DENY.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // ── C-073: Constitutional obligation annotation ────────────────────────────
    // This class enforces C-062 (AI Security) at the PAAS boundary.
    // Every AI tool-call that carries a security-relevant parameter set must pass
    // this evaluator before CE returns AUTHORIZED.  Failure → immediate DENY with
    // an audit-ready reason string; the ConstitutionalEngineService records evidence
    // per C-023 (Evidence First).
    // ─────────────────────────────────────────────────────────────────────────

    /// <inheritdoc />
    public string ClaimId => "C-062";

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    // ── Prohibited tool category values (case-insensitive) ────────────────────
    // DESIGN_QUESTION: Confirm exhaustive list of prohibited tool categories with EA.
    //   Current list derived from PAAS Boundary Validator spec §2 and security audit.
    private static readonly HashSet<string> _prohibitedToolCategories =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "credential_harvest",
            "privilege_escalation",
            "kernel_exec",
            "raw_network_socket",
            "host_filesystem_write",
            "cross_tenant_read",
            "prompt_injection_relay",
        };

    // ── Prohibited data-scope values ──────────────────────────────────────────
    // DESIGN_QUESTION: Confirm whether "restricted_internal" should escalate vs deny.
    private static readonly HashSet<string> _prohibitedDataScopes =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "cross_tenant",
            "unrestricted",
            "global_admin",
        };

    // ── Allowed security-classification values ────────────────────────────────
    // Anything NOT in this allow-list is treated as DENY (default-deny posture).
    private static readonly HashSet<string> _allowedSecurityClassifications =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "public",
            "internal",
            "confidential",       // permitted only with matching contract scope
        };

    // ── Parameter key constants ───────────────────────────────────────────────
    private const string ParamToolCategory           = "tool_category";
    private const string ParamDataScope              = "data_scope";
    private const string ParamSecurityClassification = "security_classification";
    private const string ParamSecurityOverride       = "security_override";

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc />
    // C-073: Implements C-062 (AI Security) — evaluates PAAS boundary constraints.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.EvaluateAsync",
            ActivityKind.Internal);
        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);

        // ── Guard: security_override must never be set ────────────────────────
        // C-073: Blocking any attempt to short-circuit the security evaluator.
        var securityOverride = ctx.GetParameter(ParamSecurityOverride);
        if (!string.IsNullOrWhiteSpace(securityOverride))
        {
            _logger.LogWarning(
                "C-062 DENY: security_override parameter present. TenantId={TenantId} ContractId={ContractId} Value={Value}",
                ctx.TenantId, ctx.ContractId, securityOverride);

            activity?.SetTag("deny_reason", "security_override_present");
            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-062: security_override parameter is prohibited. " +
                         $"AI agents may not bypass PAAS security boundaries. " +
                         $"Rejected value: '{securityOverride}'."));
        }

        // ── Check tool_category against prohibited list ────────────────────────
        // C-073: Default-deny for any tool category flagged as a PAAS boundary violation.
        var toolCategory = ctx.GetParameter(ParamToolCategory);
        if (!string.IsNullOrWhiteSpace(toolCategory) &&
            _prohibitedToolCategories.Contains(toolCategory))
        {
            _logger.LogWarning(
                "C-062 DENY: prohibited tool category. TenantId={TenantId} ContractId={ContractId} Category={Category}",
                ctx.TenantId, ctx.ContractId, toolCategory);

            activity?.SetTag("deny_reason", "prohibited_tool_category");
            activity?.SetTag("tool_category", toolCategory);
            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-062: Tool category '{toolCategory}' is prohibited by the AI Security policy. " +
                         "PAAS boundary violation. Default-deny applies."));
        }

        // ── Check data_scope against prohibited list ───────────────────────────
        // C-073: Cross-tenant and unrestricted data access violates the PAAS isolation guarantee.
        var dataScope = ctx.GetParameter(ParamDataScope);
        if (!string.IsNullOrWhiteSpace(dataScope) &&
            _prohibitedDataScopes.Contains(dataScope))
        {
            _logger.LogWarning(
                "C-062 DENY: prohibited data scope. TenantId={TenantId} ContractId={ContractId} Scope={Scope}",
                ctx.TenantId, ctx.ContractId, dataScope);

            activity?.SetTag("deny_reason", "prohibited_data_scope");
            activity?.SetTag("data_scope", dataScope);
            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-062: Data scope '{dataScope}' violates PAAS tenant-isolation boundary. " +
                         "Cross-tenant and unrestricted data access is prohibited."));
        }

        // ── Check security_classification — default-deny unknown values ────────
        // C-073: Any security classification outside the explicit allow-list is denied.
        //   An absent classification is permitted (not all actions carry one).
        var classification = ctx.GetParameter(ParamSecurityClassification);
        if (!string.IsNullOrWhiteSpace(classification) &&
            !_allowedSecurityClassifications.Contains(classification))
        {
            _logger.LogWarning(
                "C-062 DENY: unrecognised security classification. TenantId={TenantId} ContractId={ContractId} Classification={Classification}",
                ctx.TenantId, ctx.ContractId, classification);

            activity?.SetTag("deny_reason", "unrecognised_security_classification");
            activity?.SetTag("security_classification", classification);
            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-062: Security classification '{classification}' is not on the PAAS allow-list. " +
                         "Default-deny posture: only 'public', 'internal', or 'confidential' are permitted."));
        }

        // ── All C-062 checks passed ───────────────────────────────────────────
        _logger.LogInformation(
            "C-062 ALLOW. TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
            ctx.TenantId, ctx.ContractId, ctx.ActionType);

        activity?.SetTag("verdict", "Allow");
        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: "C-062: AI Security boundary constraints satisfied."));
    }
}