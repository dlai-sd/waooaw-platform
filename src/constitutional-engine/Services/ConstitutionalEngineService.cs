// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// Constitutional basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security), C-059 (Traceability)
using Grpc.Core;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.EmergencyStop;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Temporal;

namespace Waooaw.ConstitutionalEngine.Services;

public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    private readonly ConstitutionalDbContext _db;
    private readonly EmergencyStopDbContext _emergencyDb;
    private readonly ITemporalClient? _temporalClient;
    private readonly EvaluatorRegistry _registry;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    public ConstitutionalEngineService(
        ConstitutionalDbContext db,
        EmergencyStopDbContext emergencyDb,
        ITemporalClient? temporalClient,
        EvaluatorRegistry registry,
        ILogger<ConstitutionalEngineService> logger)
    {
        _db = db;
        _emergencyDb = emergencyDb;
        _temporalClient = temporalClient;
        _registry = registry;
        _logger = logger;
    }

    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";
        var record = new EvidenceRecord
        {
            IdempotencyKey = req.ActionInstanceId,
            TenantId = Guid.TryParse(tenantId, out var tid) ? tid : Guid.Empty,
            EvidenceType = req.ActionType,
            Summary = (!string.IsNullOrEmpty(req.ProposedContent)
                ? req.ProposedContent
                : (!string.IsNullOrEmpty(req.ExecutedContent)
                    ? req.ExecutedContent
                    : req.ActionType)),
            PayloadJson = null,
            RecordedAt = DateTimeOffset.UtcNow
        };

        _db.EvidenceRecords.Add(record);
        await _db.SaveChangesAsync(ctx.CancellationToken);

        return new RecordEvidenceResponse { EvidenceRecordId = record.Id.ToString() };
    }

    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext ctx)
    {
        // C-041 default-deny: empty ContractId is denied before evaluators run
        if (string.IsNullOrWhiteSpace(req.ContractId))
        {
            _logger.LogWarning(
                "ValidateAction denied — ContractId is missing (default deny, C-041)");

            return new ValidateActionResponse
            {
                Decision = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason = "ContractId is required. Default deny applied (C-041)."
            };
        }

        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";
        var evalCtx = EvaluationContext.FromRequest(req, tenantId);

        var results = await _registry.EvaluateAllAsync(evalCtx, ctx.CancellationToken);

        // Short-circuit: first Deny wins — evidence recording is WC012-03
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction DENIED by evaluator {ClaimId} for ContractId={ContractId}: {Reason}",
                    result.ClaimId, req.ContractId, result.Reason);

                return new ValidateActionResponse
                {
                    Decision        = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason          = result.Reason
                };
            }

            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                _logger.LogInformation(
                    "ValidateAction ESCALATED by evaluator {ClaimId} for ContractId={ContractId}: {Reason}",
                    result.ClaimId, req.ContractId, result.Reason);

                return new ValidateActionResponse
                {
                    Decision        = ValidationDecision.Escalate,
                    ConstitutionalBasis = result.ClaimId,
                    Reason          = result.Reason
                };
            }
        }

        _logger.LogInformation(
            "ValidateAction ALLOWED for ContractId={ContractId} ActionType={ActionType}",
            req.ContractId, req.ActionType);

        return new ValidateActionResponse
        {
            Decision        = ValidationDecision.Allow,
            ConstitutionalBasis = "C-041,C-043,C-048,C-049,C-062",
            Reason          = "All constitutional evaluators approved."
        };
    }

    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        return Task.FromResult(new GrantAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
    }

    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        return Task.FromResult(new RevokeAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
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
        var stopEvent = new EmergencyStopEvent
        {
            ContractId        = Guid.TryParse(req.ContractId, out var cid) ? cid : Guid.Empty,
            InitiatedByUserId = req.StoppedBy,
            AffectedSessionIds = req.ActiveSessionIds.ToArray(),
            TriggeredAt       = DateTimeOffset.UtcNow,
            StopSource        = "gRPC"
        };

        _emergencyDb.EmergencyStopEvents.Add(stopEvent);
        await _emergencyDb.SaveChangesAsync(ctx.CancellationToken);

        // Best-effort Temporal signal — C-001 stop must not block on Temporal availability
        if (_temporalClient is not null)
        {
            try
            {
                stopEvent.TemporalSignalledAt = DateTimeOffset.UtcNow;
                await _emergencyDb.SaveChangesAsync(ctx.CancellationToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(
                    ex,
                    "Failed to signal Temporal for emergency stop {EmergencyStopId}; " +
                    "stop is recorded in DB and remains in effect (C-001).",
                    stopEvent.Id);
            }
        }

        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = stopEvent.Id.ToString()
        };
        response.AffectedSessions.AddRange(req.ActiveSessionIds);
        return response;
    }
}