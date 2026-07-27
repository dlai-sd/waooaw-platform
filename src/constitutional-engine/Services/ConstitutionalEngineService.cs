// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security)
using Grpc.Core;
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
        _logger = logger;
    }

    // ─── ValidateAction ──────────────────────────────────────────────────────────
    // C-041 default-deny: any unlisted tool or any DENY verdict → DENY.
    // C-043/C-048/C-049/C-062: evaluated in order by EvaluatorRegistry (short-circuit on first DENY).
    // WC012-03: RecordEvidence calls are deferred to the next sprint item.
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext ctx)
    {
        var ct = ctx.CancellationToken;

        // TenantId MUST come from gRPC metadata (not the request body).
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";

        var evalCtx = EvaluationContext.FromRequest(req, tenantId);

        IReadOnlyList<EvaluationResult> results = await _registry.EvaluateAllAsync(evalCtx, ct);

        // Pass 1 — first DENY short-circuits; registry may have already done this internally
        // but we enforce it here as well so the service layer is authoritative.
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction DENY — ContractId={ContractId} TenantId={TenantId} " +
                    "ActionType={ActionType} ClaimId={ClaimId} Reason={Reason}",
                    evalCtx.ContractId, tenantId, evalCtx.ActionType,
                    result.ClaimId, result.Reason);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = result.Reason ?? string.Empty
                };
            }
        }

        // Pass 2 — any ESCALATE surfaces after all DENYs are checked
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                _logger.LogInformation(
                    "ValidateAction ESCALATE — ContractId={ContractId} TenantId={TenantId} " +
                    "ActionType={ActionType} ClaimId={ClaimId} Reason={Reason}",
                    evalCtx.ContractId, tenantId, evalCtx.ActionType,
                    result.ClaimId, result.Reason);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Escalate,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = result.Reason ?? string.Empty
                };
            }
        }

        // All claims satisfied → ALLOW
        // Compute remaining budget from the three non-nullable long fields on EvaluationContext.
        // ⛔ BudgetRemainingInrPaise does NOT exist on EvaluationContext — compute explicitly.
        long budgetRemainingInrPaise =
            evalCtx.ApprovedBudgetInrPaise
            - evalCtx.CurrentSpendInrPaise
            - evalCtx.ProposedSpendInrPaise;

        _logger.LogInformation(
            "ValidateAction ALLOW — ContractId={ContractId} TenantId={TenantId} " +
            "ActionType={ActionType} BudgetRemainingInrPaise={BudgetRemainingInrPaise}",
            evalCtx.ContractId, tenantId, evalCtx.ActionType, budgetRemainingInrPaise);

        return new ValidateActionResponse
        {
            Decision                 = ValidationDecision.Allow,
            ConstitutionalBasis      = string.Join(", ", results.Select(r => r.ClaimId)),
            Reason                   = "All constitutional claims satisfied.",
            BudgetRemainingInrPaise  = budgetRemainingInrPaise
        };
    }

    // ─── RecordEvidence ──────────────────────────────────────────────────────────
    // Full implementation deferred to WC012-03 (Evidence pipeline sprint item).
    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        _logger.LogDebug(
            "RecordEvidence stub — ActionInstanceId={ActionInstanceId} ActionType={ActionType}",
            req.ActionInstanceId, req.ActionType);

        return Task.FromResult(new RecordEvidenceResponse
        {
            EvidenceRecordId = Guid.NewGuid().ToString()
        });
    }

    // ─── GrantAuthorityLicense ───────────────────────────────────────────────────
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        _logger.LogInformation(
            "GrantAuthorityLicense — ContractId={ContractId} GrantedBy={GrantedBy} Level={Level}",
            req.ContractId, req.GrantedBy, req.NewAuthorityLevel);

        return Task.FromResult(new GrantAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
    }

    // ─── RevokeAuthorityLicense ──────────────────────────────────────────────────
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        _logger.LogInformation(
            "RevokeAuthorityLicense — ContractId={ContractId} RevokedBy={RevokedBy} Reason={Reason}",
            req.ContractId, req.RevokedBy, req.Reason);

        return Task.FromResult(new RevokeAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
    }

    // ─── EvaluatePolicy ──────────────────────────────────────────────────────────
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
    {
        _logger.LogDebug("EvaluatePolicy stub invoked.");

        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit
        });
    }

    // ─── TriggerEmergencyStop ────────────────────────────────────────────────────
    // C-001 Human Override: emergency stop is the highest-priority safety mechanism.
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
    {
        _logger.LogCritical(
            "EMERGENCY STOP TRIGGERED — ContractId={ContractId} StoppedBy={StoppedBy} " +
            "AffectedSessions={AffectedSessionCount}",
            req.ContractId, req.StoppedBy, req.ActiveSessionIds.Count);

        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = Guid.NewGuid().ToString()
        };
        response.AffectedSessions.AddRange(req.ActiveSessionIds);

        return Task.FromResult(response);
    }
}