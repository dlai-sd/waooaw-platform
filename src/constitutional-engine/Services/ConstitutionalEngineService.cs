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

    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        // WC012-03 — stub pending evidence persistence sprint
        return Task.FromResult(new RecordEvidenceResponse
        {
            EvidenceRecordId = Guid.NewGuid().ToString()
        });
    }

    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest request, ServerCallContext context)
    {
        var ct = context.CancellationToken;

        // C-059: TenantId sourced from gRPC metadata
        var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? "";

        // Build evaluation context — FromRequest handles budget field mapping
        var ctx = EvaluationContext.FromRequest(request, tenantId);

        // C-043: compute remaining budget from non-nullable EvaluationContext fields
        long budgetRemaining =
            ctx.ApprovedBudgetInrPaise
            - ctx.CurrentSpendInrPaise
            - ctx.ProposedSpendInrPaise;

        IReadOnlyList<EvaluationResult> results;
        try
        {
            results = await _registry.EvaluateAllAsync(ctx, ct);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning(
                "ValidateAction cancelled for contract {ContractId} tenant {TenantId}",
                request.ContractId, tenantId);
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "EvaluatorRegistry threw for contract {ContractId} tenant {TenantId}",
                request.ContractId, tenantId);

            // C-041 default-deny: any evaluation failure is a deny to preserve safety
            return new ValidateActionResponse
            {
                Decision = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason = "Evaluator registry fault — defaulting to deny (C-041 default-deny).",
                BudgetRemainingInrPaise = budgetRemaining
            };
        }

        // Short-circuit on first DENY (spec: §Evaluator Architecture)
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogInformation(
                    "ValidateAction DENY contract={ContractId} claim={ClaimId} reason={Reason}",
                    request.ContractId, result.ClaimId, result.Reason);

                return new ValidateActionResponse
                {
                    Decision = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason = result.Reason,
                    BudgetRemainingInrPaise = budgetRemaining
                };
            }
        }

        // C-049: any Escalate triggers human review path
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                _logger.LogInformation(
                    "ValidateAction ESCALATE contract={ContractId} claim={ClaimId} reason={Reason}",
                    request.ContractId, result.ClaimId, result.Reason);

                return new ValidateActionResponse
                {
                    Decision = ValidationDecision.Escalate,
                    ConstitutionalBasis = result.ClaimId,
                    Reason = result.Reason,
                    BudgetRemainingInrPaise = budgetRemaining
                };
            }
        }

        // All evaluators passed — Allow
        _logger.LogInformation(
            "ValidateAction ALLOW contract={ContractId} tenant={TenantId} evaluators={Count}",
            request.ContractId, tenantId, results.Count);

        return new ValidateActionResponse
        {
            Decision = ValidationDecision.Allow,
            ConstitutionalBasis = "C-041,C-043,C-048,C-049,C-062",
            Reason = "All constitutional evaluators passed.",
            BudgetRemainingInrPaise = budgetRemaining
        };
    }

    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        // WC012-03 — stub pending authority licensing sprint
        return Task.FromResult(new GrantAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
    }

    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        // WC012-03 — stub pending authority licensing sprint
        return Task.FromResult(new RevokeAuthorityResponse
        {
            LicenseId = req.ContractId
        });
    }

    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
    {
        // WC012-03 — stub pending policy evaluation sprint
        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit
        });
    }

    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
    {
        // C-001: Emergency Stop — Temporal signal dispatch handled by WC012-04
        _logger.LogCritical(
            "EmergencyStop requested by {StoppedBy} for contract {ContractId}",
            req.StoppedBy, req.ContractId);

        return Task.FromResult(new EmergencyStopResponse
        {
            EmergencyStopRecordId = Guid.NewGuid().ToString()
        });
    }
}