// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 (AI Security)
// constitutional_basis: C-062 (AI Security), C-059 (Traceability), C-073 (Annotated Obligations)

#nullable enable

using System.Diagnostics;
using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security): denies AI actions that match a prohibited security pattern,
/// carry a security risk score at or above the configured threshold, or require sandbox
/// isolation that was not declared by the caller.
///
/// Applies to ALL action types — AI security is a universal constraint.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // ── Parameter keys ────────────────────────────────────────────────────────────
    // C-073: each constant documents the JSON parameter name this evaluator reads
    private const string ParamProhibitedPatternMatched = "prohibited_pattern_matched";
    private const string ParamSecurityRiskScore        = "security_risk_score";
    private const string ParamRequiresSandbox          = "requires_sandbox";
    private const string ParamSandboxDeclared          = "sandbox_declared";

    // ── Threshold ─────────────────────────────────────────────────────────────────
    // C-062: actions with security_risk_score >= 0.80 are denied
    private const float SecurityRiskDenyThreshold = 0.80f;

    // ── Telemetry ─────────────────────────────────────────────────────────────────
    private static readonly ActivitySource _tracer =
        new("Waooaw.ConstitutionalEngine");

    // ── Dependencies ─────────────────────────────────────────────────────────────
    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    // C-073: constructor satisfies C-062 registration obligation via DI
    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // ── IClaimEvaluator ───────────────────────────────────────────────────────────

    /// <inheritdoc/>
    public string ClaimId => "C-062";

    /// <inheritdoc/>
    /// Empty set signals that this evaluator runs on every action type.
    /// C-062 (AI Security) is unconditional — no action type is exempt.
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    /// <inheritdoc/>
    // C-073: EvaluateAsync is the runtime enforcement point for C-062 (AI Security)
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.Evaluate", ActivityKind.Internal);
        activity?.SetTag("claim_id",    ClaimId);
        activity?.SetTag("tenant_id",   ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Gate 1: Prohibited pattern ────────────────────────────────────────────
        // C-062: any action matching a constitutionally prohibited AI security
        //        pattern is unconditionally denied — no threshold, no exception.
        var prohibitedRaw = ctx.GetParameter(ParamProhibitedPatternMatched);
        if (string.Equals(prohibitedRaw, "true", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogWarning(
                "C-062 DENY prohibited_pattern_matched=true. " +
                "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("deny_reason", "prohibited_pattern_matched");
            return Task.FromResult(
                Denied("C-062: action matches a constitutionally prohibited AI security pattern"));
        }

        // ── Gate 2: Security risk score ───────────────────────────────────────────
        // C-062: caller-supplied security_risk_score (0.0–1.0).
        //        Score >= 0.80 → DENY.  Missing score → pass (treat as 0.0).
        var riskRaw = ctx.GetParameter(ParamSecurityRiskScore);
        if (riskRaw is not null)
        {
            if (!float.TryParse(
                    riskRaw,
                    NumberStyles.Float,
                    CultureInfo.InvariantCulture,
                    out var riskScore))
            {
                // Malformed score is treated as a security violation — fail safe.
                _logger.LogWarning(
                    "C-062 DENY unparseable security_risk_score={Raw}. " +
                    "TenantId={TenantId} ActionType={ActionType}",
                    riskRaw, ctx.TenantId, ctx.ActionType);

                activity?.SetTag("deny_reason",       "unparseable_security_risk_score");
                activity?.SetTag("raw_risk_score",    riskRaw);
                return Task.FromResult(
                    Denied($"C-062: security_risk_score value '{riskRaw}' could not be parsed — " +
                           "fail-safe denial applied"));
            }

            activity?.SetTag("security_risk_score", riskScore);

            if (riskScore >= SecurityRiskDenyThreshold)
            {
                _logger.LogWarning(
                    "C-062 DENY security_risk_score={Score:F4} >= threshold={Threshold:F2}. " +
                    "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                    riskScore, SecurityRiskDenyThreshold, ctx.TenantId, ctx.ActionType, ctx.ContractId);

                activity?.SetTag("deny_reason", "security_risk_score_exceeded");
                return Task.FromResult(
                    Denied($"C-062: security risk score {riskScore:F4} meets or exceeds " +
                           $"the denial threshold of {SecurityRiskDenyThreshold:F2}"));
            }
        }

        // ── Gate 3: Sandbox isolation ─────────────────────────────────────────────
        // C-062: if an action declares that sandbox isolation is required, the caller
        //        must also set sandbox_declared=true.  Asymmetry is denied.
        var requiresSandboxRaw = ctx.GetParameter(ParamRequiresSandbox);
        if (string.Equals(requiresSandboxRaw, "true", StringComparison.OrdinalIgnoreCase))
        {
            var sandboxDeclaredRaw = ctx.GetParameter(ParamSandboxDeclared);
            if (!string.Equals(sandboxDeclaredRaw, "true", StringComparison.OrdinalIgnoreCase))
            {
                _logger.LogWarning(
                    "C-062 DENY requires_sandbox=true but sandbox_declared={Declared}. " +
                    "TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
                    sandboxDeclaredRaw ?? "<absent>",
                    ctx.TenantId, ctx.ActionType, ctx.ContractId);

                activity?.SetTag("deny_reason",     "sandbox_not_declared");
                activity?.SetTag("sandbox_declared", sandboxDeclaredRaw ?? "<absent>");
                return Task.FromResult(
                    Denied("C-062: action requires sandbox isolation " +
                           "but sandbox_declared was not set to true"));
            }
        }

        // ── All gates passed ──────────────────────────────────────────────────────
        _logger.LogDebug(
            "C-062 ALLOW. TenantId={TenantId} ActionType={ActionType} ContractId={ContractId}",
            ctx.TenantId, ctx.ActionType, ctx.ContractId);

        activity?.SetTag("verdict", "Allow");
        return Task.FromResult(Allow());
    }

    // ── Private result factories ──────────────────────────────────────────────────

    private EvaluationResult Allow() =>
        new(ClaimId, EvaluationVerdict.Allow, "C-062: AI security checks passed");

    private EvaluationResult Denied(string reason) =>
        new(ClaimId, EvaluationVerdict.Deny, reason);
}