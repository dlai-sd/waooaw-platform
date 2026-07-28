// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// Constitutional basis: C-023 (Evidence First), C-003 (Authority Licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security), C-059 (Traceability)
using Grpc.Core;
using Microsoft.Extensions.Logging;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    private readonly EvaluatorRegistry _registry;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    public ConstitutionalEngineService(
        EvaluatorRegistry registry,
        ILogger<ConstitutionalEngineService> logger)
    {
        _registry = registry;
        _logger   = logger;
    }

    // ── RecordEvidence ────────────────────────────────────────────────────────
    // WC012-03 will replace this stub with full evidence persistence.
    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        return Task.FromResult(new RecordEvidenceResponse
        {
            EvidenceRecordId = Guid.NewGuid().ToString()
        });
    }

    // ── ValidateAction ────────────────────────────────────────────────────────
    // C-041 default-deny: unknown tool/contract → DENY.
    // C-043 budget ceiling, C-048 non-exploitation, C-049 honest limitation,
    // C-062 AI security: evaluated in order; first DENY or ESCALATE short-circuits.
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext ctx)
    {
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";
        var evalCtx  = EvaluationContext.FromRequest(req, tenantId);
        var ct       = ctx.CancellationToken;

        IReadOnlyList<EvaluationResult> results =
            await _registry.EvaluateAllAsync(evalCtx, ct);

        foreach (var result in results)
        {
            switch (result.Verdict)
            {
                case EvaluationVerdict.Deny:
                    _logger.LogWarning(
                        "ValidateAction DENY — ContractId={ContractId} ActionType={ActionType} " +
                        "ClaimId={ClaimId} Reason={Reason}",
                        req.ContractId, req.ActionType, result.ClaimId, result.Reason);

                    return new ValidateActionResponse
                    {
                        Decision            = ValidationDecision.Deny,
                        ConstitutionalBasis = result.ClaimId,
                        Reason              = result.Reason
                    };

                case EvaluationVerdict.Escalate:
                    _logger.LogWarning(
                        "ValidateAction ESCALATE — ContractId={ContractId} ActionType={ActionType} " +
                        "ClaimId={ClaimId} Reason={Reason}",
                        req.ContractId, req.ActionType, result.ClaimId, result.Reason);

                    return new ValidateActionResponse
                    {
                        Decision            = ValidationDecision.Escalate,
                        ConstitutionalBasis = result.ClaimId,
                        Reason              = result.Reason
                    };
            }
        }

        // All evaluators passed — action is constitutionally permitted.
        _logger.LogInformation(
            "ValidateAction ALLOW — ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
            req.ContractId, req.ActionType, tenantId);

        return new ValidateActionResponse
        {
            Decision            = ValidationDecision.Allow,
            ConstitutionalBasis = "C-041,C-043,C-048,C-049,C-062",
            Reason              = "All constitutional evaluators passed."
        };
    }

    // ── GrantAuthorityLicense ─────────────────────────────────────────────────
    // WC012-03 scope — stub returns a generated license ID.
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        return Task.FromResult(new GrantAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
    }

    // ── RevokeAuthorityLicense ────────────────────────────────────────────────
    // WC012-03 scope — stub returns a generated license ID.
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        return Task.FromResult(new RevokeAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
    }

    // ── EvaluatePolicy ────────────────────────────────────────────────────────
    // WC012-03 scope — stub.
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
    {
        return Task.FromResult(new EvaluatePolicyResponse());
    }

    // ── TriggerEmergencyStop ──────────────────────────────────────────────────
    // Temporal signal integration is WC012-04b scope — stub returns empty response.
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
    {
        return Task.FromResult(new EmergencyStopResponse());
    }
}