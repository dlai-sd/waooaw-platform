// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-023 (Evidence First), C-003 (Authority Licensed), C-001 (Emergency Stop),
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

    // ── RecordEvidence ──────────────────────────────────────────────────────────
    // WC012-03 scope — not implemented here.
    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req,
        ServerCallContext ctx)
    {
        return Task.FromResult(new RecordEvidenceResponse
        {
            EvidenceRecordId = string.Empty
        });
    }

    // ── ValidateAction ──────────────────────────────────────────────────────────
    // Enforces C-041 / C-043 / C-048 / C-049 / C-062 via EvaluatorRegistry.
    // Short-circuit on first DENY (handled inside EvaluatorRegistry.EvaluateAllAsync).
    // Default deny: any evaluator DENY → ValidationDecision.Deny returned to caller.
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req,
        ServerCallContext ctx)
    {
        var tenantId    = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;
        var evalContext = EvaluationContext.FromRequest(req, tenantId);

        _logger.LogInformation(
            "ValidateAction: ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
            evalContext.ContractId,
            evalContext.ActionType,
            evalContext.TenantId);

        IReadOnlyList<EvaluationResult> results;
        try
        {
            results = await _registry.EvaluateAllAsync(evalContext, ctx.CancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "EvaluatorRegistry threw during ValidateAction for ContractId={ContractId}",
                evalContext.ContractId);

            // Fail-closed: an unhandled evaluator exception is a constitutional DENY.
            return new ValidateActionResponse
            {
                Decision            = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason              = "Evaluator fault — default deny applied (fail-closed)."
            };
        }

        // ── Scan results: first Deny or Escalate wins ───────────────────────────
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction DENY: ClaimId={ClaimId} Reason={Reason} ContractId={ContractId}",
                    result.ClaimId, result.Reason, evalContext.ContractId);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = result.Reason ?? $"Denied by {result.ClaimId}."
                };
            }

            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                _logger.LogWarning(
                    "ValidateAction ESCALATE: ClaimId={ClaimId} Reason={Reason} ContractId={ContractId}",
                    result.ClaimId, result.Reason, evalContext.ContractId);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Escalate,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = result.Reason ?? $"Escalated by {result.ClaimId}."
                };
            }
        }

        // ── All evaluators passed → Allow ───────────────────────────────────────
        long budgetRemaining =
            evalContext.ApprovedBudgetInrPaise
            - evalContext.CurrentSpendInrPaise
            - evalContext.ProposedSpendInrPaise;

        _logger.LogInformation(
            "ValidateAction ALLOW: ContractId={ContractId} BudgetRemainingInrPaise={BudgetRemaining}",
            evalContext.ContractId,
            budgetRemaining);

        return new ValidateActionResponse
        {
            Decision                = ValidationDecision.Allow,
            ConstitutionalBasis     = "C-041,C-043,C-048,C-049,C-062",
            Reason                  = "All constitutional evaluators passed.",
            BudgetRemainingInrPaise = budgetRemaining
        };
    }

    // ── GrantAuthorityLicense ───────────────────────────────────────────────────
    // WC012-03 scope — stub.
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req,
        ServerCallContext ctx)
    {
        return Task.FromResult(new GrantAuthorityResponse
        {
            LicenseId = string.Empty
        });
    }

    // ── RevokeAuthorityLicense ──────────────────────────────────────────────────
    // WC012-03 scope — stub.
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req,
        ServerCallContext ctx)
    {
        return Task.FromResult(new RevokeAuthorityResponse
        {
            LicenseId = string.Empty
        });
    }

    // ── EvaluatePolicy ──────────────────────────────────────────────────────────
    // Future scope — stub.
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req,
        ServerCallContext ctx)
    {
        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Unspecified
        });
    }

    // ── TriggerEmergencyStop ────────────────────────────────────────────────────
    // WC012-04b scope (Temporal integration) — stub returns empty response.
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req,
        ServerCallContext ctx)
    {
        return Task.FromResult(new EmergencyStopResponse
        {
            EmergencyStopRecordId = string.Empty
        });
    }
}