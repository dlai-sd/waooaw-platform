// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// Implements: architecture/reference/ce-validate-action-evaluators.md §Evaluator Architecture
// Constitutional basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
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

    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req,
        ServerCallContext ctx)
    {
        var response = new RecordEvidenceResponse
        {
            EvidenceRecordId = Guid.NewGuid().ToString()
        };
        return Task.FromResult(response);
    }

    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req,
        ServerCallContext ctx)
    {
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";

        var evalCtx = EvaluationContext.FromRequest(req, tenantId);

        IReadOnlyList<EvaluationResult> results;
        try
        {
            results = await _registry.EvaluateAllAsync(evalCtx, ctx.CancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "EvaluatorRegistry threw during ValidateAction for ContractId={ContractId} ActionType={ActionType}",
                req.ContractId, req.ActionType);

            return new ValidateActionResponse
            {
                Decision            = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason              = "Internal evaluator error — default deny applied (C-041)"
            };
        }

        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction DENY: ContractId={ContractId} ActionType={ActionType} " +
                    "ClaimId={ClaimId} Reason={Reason}",
                    req.ContractId, req.ActionType, result.ClaimId, result.Reason);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = result.Reason ?? $"Denied by {result.ClaimId}"
                };
            }

            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                _logger.LogInformation(
                    "ValidateAction ESCALATE: ContractId={ContractId} ActionType={ActionType} " +
                    "ClaimId={ClaimId} Reason={Reason}",
                    req.ContractId, req.ActionType, result.ClaimId, result.Reason);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Escalate,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = result.Reason ?? $"Escalated by {result.ClaimId}"
                };
            }
        }

        _logger.LogInformation(
            "ValidateAction ALLOW: ContractId={ContractId} ActionType={ActionType}",
            req.ContractId, req.ActionType);

        long? budgetRemaining = null;
        if (req.BudgetContext is not null)
        {
            budgetRemaining = req.BudgetContext.ApprovedMonthlyBudgetInrPaise
                              - req.BudgetContext.CurrentMonthSpendInrPaise
                              - req.BudgetContext.ProposedSpendInrPaise;
        }

        var allowResponse = new ValidateActionResponse
        {
            Decision            = ValidationDecision.Allow,
            ConstitutionalBasis = "C-041",
            Reason              = "All constitutional evaluators passed"
        };

        if (budgetRemaining.HasValue)
        {
            allowResponse.BudgetRemainingInrPaise = budgetRemaining.Value;
        }

        return allowResponse;
    }

    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req,
        ServerCallContext ctx)
    {
        var response = new GrantAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        };
        return Task.FromResult(response);
    }

    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req,
        ServerCallContext ctx)
    {
        var response = new RevokeAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        };
        return Task.FromResult(response);
    }

    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req,
        ServerCallContext ctx)
    {
        var response = new EvaluatePolicyResponse
        {
            Decision            = PolicyDecision.Deny,
            ConstitutionalBasis = "C-041",
            Rationale           = "EvaluatePolicy not yet implemented — default deny (C-041)"
        };
        return Task.FromResult(response);
    }

    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req,
        ServerCallContext ctx)
    {
        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = Guid.NewGuid().ToString()
        };
        foreach (var sessionId in req.ActiveSessionIds)
        {
            response.AffectedSessions.Add(sessionId);
        }
        return Task.FromResult(response);
    }
}