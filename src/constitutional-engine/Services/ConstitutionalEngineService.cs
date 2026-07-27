// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// Implements: architecture/reference/ce-validate-action-evaluators.md
// Constitutional basis: C-023 (Evidence First), C-003 (Authority Licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security), ADR-001 (gRPC)
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
        _logger = logger;
    }

    // ── RecordEvidence ─────────────────────────────────────────────────────────
    // Full persistence implementation deferred to WC012-03.
    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        _logger.LogInformation(
            "RecordEvidence stub: actionInstanceId={ActionInstanceId} contractId={ContractId}",
            req.ActionInstanceId, req.ContractId);

        return Task.FromResult(new RecordEvidenceResponse
        {
            EvidenceRecordId = Guid.NewGuid().ToString("D"),
        });
    }

    // ── ValidateAction ─────────────────────────────────────────────────────────
    // C-041: Default deny — unlisted tool / action must be denied.
    // C-043: Budget ceiling enforcement.
    // C-048: Non-exploitation guard.
    // C-049: Honest limitation / escalation path.
    // C-062: AI security boundary enforcement.
    // Short-circuits on first DENY; ESCALATE forwarded immediately to caller.
    // RecordEvidence audit write deferred to WC012-03.
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext ctx)
    {
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";
        var evalCtx = EvaluationContext.FromRequest(req, tenantId);
        var ct = ctx.CancellationToken;

        // Compute budget remaining for informational response field (non-null when context provided).
        long? budgetRemaining = req.BudgetContext is not null
            ? req.BudgetContext.ApprovedMonthlyBudgetInrPaise
              - req.BudgetContext.CurrentMonthSpendInrPaise
              - req.BudgetContext.ProposedSpendInrPaise
            : null;

        IReadOnlyList<EvaluationResult> results;
        try
        {
            results = await _registry.EvaluateAllAsync(evalCtx, ct);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning(
                "ValidateAction cancelled: contract={ContractId} action={ActionType}",
                evalCtx.ContractId, evalCtx.ActionType);

            return new ValidateActionResponse
            {
                Decision = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason = "Evaluation cancelled — default deny applies (C-041).",
                BudgetRemainingInrPaise = budgetRemaining ?? 0L,
            };
        }

        // Scan results. EvaluatorRegistry short-circuits on first DENY internally;
        // we re-scan here defensively to surface the first decisive verdict.
        foreach (var result in results)
        {
            switch (result.Verdict)
            {
                case EvaluationVerdict.Deny:
                    _logger.LogWarning(
                        "ValidateAction DENY: contract={ContractId} tenant={TenantId} " +
                        "action={ActionType} claim={ClaimId} reason={Reason}",
                        evalCtx.ContractId, evalCtx.TenantId,
                        evalCtx.ActionType, result.ClaimId, result.Reason);

                    return new ValidateActionResponse
                    {
                        Decision = ValidationDecision.Deny,
                        ConstitutionalBasis = result.ClaimId,
                        Reason = result.Reason,
                        BudgetRemainingInrPaise = budgetRemaining ?? 0L,
                    };

                case EvaluationVerdict.Escalate:
                    _logger.LogInformation(
                        "ValidateAction ESCALATE: contract={ContractId} tenant={TenantId} " +
                        "action={ActionType} claim={ClaimId} reason={Reason}",
                        evalCtx.ContractId, evalCtx.TenantId,
                        evalCtx.ActionType, result.ClaimId, result.Reason);

                    return new ValidateActionResponse
                    {
                        Decision = ValidationDecision.Escalate,
                        ConstitutionalBasis = result.ClaimId,
                        Reason = result.Reason,
                        BudgetRemainingInrPaise = budgetRemaining ?? 0L,
                    };
            }
        }

        // All evaluators returned Allow.
        _logger.LogInformation(
            "ValidateAction ALLOW: contract={ContractId} tenant={TenantId} action={ActionType} " +
            "evaluatorCount={Count}",
            evalCtx.ContractId, evalCtx.TenantId, evalCtx.ActionType, results.Count);

        return new ValidateActionResponse
        {
            Decision = ValidationDecision.Allow,
            ConstitutionalBasis = "C-041,C-043,C-048,C-049,C-062",
            Reason = "All constitutional evaluators passed.",
            BudgetRemainingInrPaise = budgetRemaining ?? 0L,
        };
    }

    // ── GrantAuthorityLicense ──────────────────────────────────────────────────
    // Full authority-ledger persistence deferred to WC012-03.
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        _logger.LogInformation(
            "GrantAuthorityLicense stub: contractId={ContractId} grantedBy={GrantedBy}",
            req.ContractId, req.GrantedBy);

        return Task.FromResult(new GrantAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString("D"),
        });
    }

    // ── RevokeAuthorityLicense ─────────────────────────────────────────────────
    // Full authority-ledger persistence deferred to WC012-03.
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        _logger.LogInformation(
            "RevokeAuthorityLicense stub: contractId={ContractId} revokedBy={RevokedBy}",
            req.ContractId, req.RevokedBy);

        return Task.FromResult(new RevokeAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString("D"),
        });
    }

    // ── EvaluatePolicy ─────────────────────────────────────────────────────────
    // OPA-backed policy evaluation deferred to WC012-03.
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
    {
        _logger.LogInformation("EvaluatePolicy stub invoked.");

        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit,
        });
    }

    // ── TriggerEmergencyStop ───────────────────────────────────────────────────
    // Temporal signal dispatch and session termination deferred to WC012-03.
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
    {
        _logger.LogCritical(
            "TriggerEmergencyStop stub: contractId={ContractId} stoppedBy={StoppedBy}",
            req.ContractId, req.StoppedBy);

        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = Guid.NewGuid().ToString("D"),
        };
        response.AffectedSessions.AddRange(req.ActiveSessionIds);
        return Task.FromResult(response);
    }
}