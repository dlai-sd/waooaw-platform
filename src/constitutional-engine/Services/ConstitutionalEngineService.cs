// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security)
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Temporalio.Client;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.EmergencyStop;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    private readonly ConstitutionalDbContext _db;
    private readonly EmergencyStopDbContext _emergencyDb;
    private readonly ITemporalClient? _temporalClient;
    private readonly EvaluatorRegistry? _registry;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    public ConstitutionalEngineService(
        ConstitutionalDbContext db,
        EmergencyStopDbContext emergencyDb,
        ILogger<ConstitutionalEngineService> logger,
        ITemporalClient? temporalClient = null,
        EvaluatorRegistry? registry = null)
    {
        _db = db;
        _emergencyDb = emergencyDb;
        _logger = logger;
        _temporalClient = temporalClient;
        _registry = registry;
    }

    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";

        var record = new EvidenceRecord
        {
            IdempotencyKey = req.ActionInstanceId,
            TenantId       = Guid.TryParse(tenantId, out var tid) ? tid : Guid.Empty,
            EvidenceType   = req.ActionType,
            Summary        = req.ProposedContent ?? req.ExecutedContent ?? req.ActionType,
            PayloadJson    = null
        };

        _db.EvidenceRecords.Add(record);
        await _db.SaveChangesAsync(ctx.CancellationToken);

        return new RecordEvidenceResponse { EvidenceRecordId = record.Id.ToString() };
    }

    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext ctx)
    {
        var ct       = ctx.CancellationToken;
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";

        // Default-deny: if no registry is wired (misconfiguration), deny all actions.
        if (_registry is null)
        {
            _logger.LogError(
                "EvaluatorRegistry is null — constitutional enforcement is unavailable. " +
                "Denying action {ActionType} for contract {ContractId}.",
                req.ActionType, req.ContractId);

            return new ValidateActionResponse
            {
                Decision           = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason             = "Constitutional registry unavailable — default deny (C-041)."
            };
        }

        // Default-deny: missing contract is constitutionally prohibited (C-041).
        if (string.IsNullOrWhiteSpace(req.ContractId))
        {
            _logger.LogWarning("ValidateAction called with empty ContractId — denying (C-041 default deny).");

            return new ValidateActionResponse
            {
                Decision            = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason              = "ContractId is required — default deny (C-041)."
            };
        }

        EvaluationContext evalCtx;
        try
        {
            evalCtx = EvaluationContext.FromRequest(req, tenantId);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "Failed to build EvaluationContext for contract {ContractId} action {ActionType}.",
                req.ContractId, req.ActionType);

            return new ValidateActionResponse
            {
                Decision            = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason              = "Malformed request — default deny (C-041)."
            };
        }

        IReadOnlyList<EvaluationResult> results;
        try
        {
            results = await _registry.EvaluateAllAsync(evalCtx, ct);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning(
                "ValidateAction evaluation cancelled for contract {ContractId}.", req.ContractId);
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "EvaluatorRegistry threw during ValidateAction for contract {ContractId}. " +
                "Applying default deny (C-041).", req.ContractId);

            return new ValidateActionResponse
            {
                Decision            = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason              = "Evaluation error — default deny (C-041)."
            };
        }

        // Short-circuit: first DENY wins.
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogInformation(
                    "ValidateAction DENY — claim {ClaimId} denied contract {ContractId} action {ActionType}: {Reason}",
                    result.ClaimId, req.ContractId, req.ActionType, result.Reason);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = result.Reason ?? $"Denied by {result.ClaimId}."
                };
            }
        }

        // Escalate: if any evaluator signalled Escalate (and no Deny), surface it.
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                _logger.LogInformation(
                    "ValidateAction ESCALATE — claim {ClaimId} escalated contract {ContractId} action {ActionType}: {Reason}",
                    result.ClaimId, req.ContractId, req.ActionType, result.Reason);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Escalate,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = result.Reason ?? $"Escalated by {result.ClaimId}."
                };
            }
        }

        // All evaluators passed — compute remaining budget for the response (informational).
        long budgetRemaining = 0L;
        if (req.BudgetContext is not null)
        {
            var bc = req.BudgetContext;
            budgetRemaining = bc.ApprovedMonthlyBudgetInrPaise
                              - bc.CurrentMonthSpendInrPaise
                              - bc.ProposedSpendInrPaise;
        }

        _logger.LogInformation(
            "ValidateAction ALLOW — contract {ContractId} action {ActionType} passed all evaluators.",
            req.ContractId, req.ActionType);

        return new ValidateActionResponse
        {
            Decision                = ValidationDecision.Allow,
            ConstitutionalBasis     = string.Join(",", results.Select(r => r.ClaimId)),
            Reason                  = "All constitutional claims satisfied.",
            BudgetRemainingInrPaise = budgetRemaining
        };
    }

    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        var response = new GrantAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        };
        return Task.FromResult(response);
    }

    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        var response = new RevokeAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        };
        return Task.FromResult(response);
    }

    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
    {
        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit
        });
    }

    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
    {
        var ct             = ctx.CancellationToken;
        var contractId     = Guid.TryParse(req.ContractId, out var cid) ? cid : Guid.Empty;
        var affectedIds    = req.ActiveSessionIds.ToArray();

        var stopEvent = new EmergencyStopEvent
        {
            ContractId         = contractId,
            InitiatedByUserId  = req.StoppedBy,
            AffectedSessionIds = affectedIds,
            StopSource         = "gRPC"
        };

        _emergencyDb.EmergencyStopEvents.Add(stopEvent);
        await _emergencyDb.SaveChangesAsync(ct);

        if (_temporalClient is not null)
        {
            try
            {
                var handle = _temporalClient.GetWorkflowHandle(req.ContractId);
                await handle.SignalAsync("emergency_stop", new[] { stopEvent.Id.ToString() });

                stopEvent.TemporalSignalledAt = DateTimeOffset.UtcNow;
                await _emergencyDb.SaveChangesAsync(ct);
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex,
                    "Temporal signal failed for EmergencyStop on contract {ContractId}. " +
                    "Stop is persisted; signal will be retried by reconciler.",
                    req.ContractId);
            }
        }

        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = stopEvent.Id.ToString()
        };
        response.AffectedSessions.AddRange(affectedIds);

        return response;
    }
}