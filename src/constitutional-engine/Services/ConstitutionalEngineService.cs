// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security)
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

    // ─── RecordEvidence ───────────────────────────────────────────────────────
    // WC012-03 implements the full body; stub retained here per EXTEND-NOT-REPLACE.
    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        return Task.FromResult(new RecordEvidenceResponse
        {
            EvidenceRecordId = Guid.NewGuid().ToString()
        });
    }

    // ─── ValidateAction ───────────────────────────────────────────────────────
    // C-041: default deny — unlisted tool / missing ContractId → DENY immediately.
    // C-043: budget ceiling enforced by C043BudgetCeilingEvaluator.
    // C-048: non-exploitation enforced by C048NonExploitationEvaluator.
    // C-049: honest limitation enforced by C049HonestLimitationEvaluator.
    // C-062: AI security enforced by C062AiSecurityEvaluator.
    // Short-circuit: first DENY terminates evaluation; first ESCALATE triggers escalation path.
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest request, ServerCallContext context)
    {
        var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? "";

        // Default deny: missing ContractId is a C-041 violation.
        if (string.IsNullOrWhiteSpace(request.ContractId))
        {
            _logger.LogWarning(
                "ValidateAction: missing ContractId — default deny (C-041). TenantId={TenantId}",
                tenantId);

            return new ValidateActionResponse
            {
                Decision           = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason             = "ContractId is required; default deny."
            };
        }

        var evalCtx = EvaluationContext.FromRequest(request, tenantId);
        var ct      = context.CancellationToken;

        IReadOnlyList<EvaluationResult> results =
            await _registry.EvaluateAllAsync(evalCtx, ct);

        // First pass: short-circuit on DENY.
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction: DENY — claimId={ClaimId} reason={Reason} " +
                    "contractId={ContractId} tenantId={TenantId}",
                    result.ClaimId, result.Reason,
                    evalCtx.ContractId, evalCtx.TenantId);

                return new ValidateActionResponse
                {
                    Decision           = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason             = result.Reason
                };
            }
        }

        // Second pass: escalate if any evaluator requested human review (C-049 path).
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                _logger.LogInformation(
                    "ValidateAction: ESCALATE — claimId={ClaimId} reason={Reason} " +
                    "contractId={ContractId} tenantId={TenantId}",
                    result.ClaimId, result.Reason,
                    evalCtx.ContractId, evalCtx.TenantId);

                return new ValidateActionResponse
                {
                    Decision           = ValidationDecision.Escalate,
                    ConstitutionalBasis = result.ClaimId,
                    Reason             = result.Reason
                };
            }
        }

        // All evaluators passed → ALLOW.
        long budgetRemaining =
            evalCtx.ApprovedBudgetInrPaise
            - evalCtx.CurrentSpendInrPaise
            - evalCtx.ProposedSpendInrPaise;

        _logger.LogInformation(
            "ValidateAction: ALLOW — contractId={ContractId} tenantId={TenantId} " +
            "evaluatorCount={Count} budgetRemainingInrPaise={Remaining}",
            evalCtx.ContractId, evalCtx.TenantId,
            results.Count, budgetRemaining);

        return new ValidateActionResponse
        {
            Decision                = ValidationDecision.Allow,
            ConstitutionalBasis     = "C-041,C-043,C-048,C-049,C-062",
            Reason                  = "All constitutional evaluators passed.",
            BudgetRemainingInrPaise = budgetRemaining
        };
    }

    // ─── GrantAuthorityLicense ────────────────────────────────────────────────
    // Full authority-licensing body is outside WC012-02 scope; stub retained.
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        return Task.FromResult(new GrantAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
    }

    // ─── RevokeAuthorityLicense ───────────────────────────────────────────────
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        return Task.FromResult(new RevokeAuthorityResponse
        {
            LicenseId = req.ContractId
        });
    }

    // ─── EvaluatePolicy ───────────────────────────────────────────────────────
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
    {
        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Deny
        });
    }

    // ─── TriggerEmergencyStop ─────────────────────────────────────────────────
    // C-001: Emergency Stop — full Temporal signal implementation is outside scope.
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
    {
        _logger.LogCritical(
            "EmergencyStop triggered — contractId={ContractId} stoppedBy={StoppedBy}",
            req.ContractId, req.StoppedBy);

        return Task.FromResult(new EmergencyStopResponse
        {
            EmergencyStopRecordId = Guid.NewGuid().ToString()
        });
    }
}