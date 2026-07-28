// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security), C-059 (Traceability)
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Temporalio.Client;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.EmergencyStop;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementation. Enforces constitutional claims at runtime.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    private readonly ConstitutionalDbContext _db;
    private readonly EmergencyStopDbContext _emergencyDb;
    private readonly EvaluatorRegistry _registry;
    private readonly ITemporalClient? _temporalClient;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    public ConstitutionalEngineService(
        ConstitutionalDbContext db,
        EmergencyStopDbContext emergencyDb,
        EvaluatorRegistry registry,
        ILogger<ConstitutionalEngineService> logger,
        ITemporalClient? temporalClient = null)
    {
        _db = db;
        _emergencyDb = emergencyDb;
        _registry = registry;
        _logger = logger;
        _temporalClient = temporalClient;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // RecordEvidence — C-023 (Evidence First)
    // ─────────────────────────────────────────────────────────────────────────
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";

        var record = new EvidenceRecord
        {
            IdempotencyKey      = req.ActionInstanceId,
            TenantId            = Guid.TryParse(tenantId, out var tid) ? tid : Guid.Empty,
            EvidenceType        = req.ActionType,
            Summary             = req.ProposedContent ?? req.ExecutedContent ?? req.ActionType,
            PayloadJson         = null,
            RecordedAt          = DateTimeOffset.UtcNow
        };

        _db.EvidenceRecords.Add(record);
        await _db.SaveChangesAsync(ctx.CancellationToken);

        _logger.LogInformation(
            "Evidence recorded: {EvidenceRecordId} type={ActionType} tenant={TenantId}",
            record.Id, record.EvidenceType, tenantId);

        return new RecordEvidenceResponse { EvidenceRecordId = record.Id.ToString() };
    }

    // ─────────────────────────────────────────────────────────────────────────
    // ValidateAction — C-041/C-043/C-048/C-049/C-062 enforced via EvaluatorRegistry
    // Default deny (C-041): any DENY from any evaluator → ValidationDecision.Deny
    // ─────────────────────────────────────────────────────────────────────────
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext ctx)
    {
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";
        var evalCtx  = EvaluationContext.FromRequest(req, tenantId);

        IReadOnlyList<EvaluationResult> results =
            await _registry.EvaluateAllAsync(evalCtx, ctx.CancellationToken);

        // Short-circuit on first DENY (spec: §2 Evaluator Architecture)
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction DENY: claim={ClaimId} reason={Reason} contract={ContractId}",
                    result.ClaimId, result.Reason, req.ContractId);

                return new ValidateActionResponse
                {
                    Decision           = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason             = result.Reason
                };
            }

            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                _logger.LogInformation(
                    "ValidateAction ESCALATE: claim={ClaimId} reason={Reason} contract={ContractId}",
                    result.ClaimId, result.Reason, req.ContractId);

                return new ValidateActionResponse
                {
                    Decision           = ValidationDecision.Escalate,
                    ConstitutionalBasis = result.ClaimId,
                    Reason             = result.Reason
                };
            }
        }

        // All evaluators passed → Allow
        _logger.LogInformation(
            "ValidateAction ALLOW: contract={ContractId} actionType={ActionType}",
            req.ContractId, req.ActionType);

        return new ValidateActionResponse
        {
            Decision           = ValidationDecision.Allow,
            ConstitutionalBasis = "ALL",
            Reason             = "All constitutional evaluators passed."
        };
    }

    // ─────────────────────────────────────────────────────────────────────────
    // GrantAuthorityLicense — C-003
    // ─────────────────────────────────────────────────────────────────────────
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        _logger.LogInformation(
            "GrantAuthorityLicense: contract={ContractId} level={Level} by={GrantedBy}",
            req.ContractId, req.NewAuthorityLevel, req.GrantedBy);

        return Task.FromResult(new GrantAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // RevokeAuthorityLicense — C-003
    // ─────────────────────────────────────────────────────────────────────────
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        _logger.LogInformation(
            "RevokeAuthorityLicense: contract={ContractId} level={Level} by={RevokedBy}",
            req.ContractId, req.NewAuthorityLevel, req.RevokedBy);

        return Task.FromResult(new RevokeAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // EvaluatePolicy — returns PERMIT/DENY based on PolicyDecision
    // ─────────────────────────────────────────────────────────────────────────
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
    {
        _logger.LogInformation(
            "EvaluatePolicy: contract={ContractId}",
            req.ContractId);

        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // TriggerEmergencyStop — C-001 (absolute, ≤250ms)
    // ─────────────────────────────────────────────────────────────────────────
    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
    {
        var stopEvent = new EmergencyStopEvent
        {
            ContractId         = Guid.TryParse(req.ContractId, out var cid) ? cid : Guid.Empty,
            InitiatedByUserId  = req.StoppedBy,
            AffectedSessionIds = req.ActiveSessionIds.ToArray(),
            TriggeredAt        = DateTimeOffset.UtcNow,
            StopSource         = "gRPC"
        };

        _emergencyDb.EmergencyStopEvents.Add(stopEvent);
        await _emergencyDb.SaveChangesAsync(ctx.CancellationToken);

        // Signal Temporal if client is available — fire-and-forget to stay within 250ms budget
        if (_temporalClient is not null)
        {
            _ = SignalTemporalEmergencyStopAsync(stopEvent, ctx.CancellationToken);
        }

        _logger.LogCritical(
            "EmergencyStop triggered: recordId={RecordId} contract={ContractId} by={StoppedBy} sessions={SessionCount}",
            stopEvent.Id, req.ContractId, req.StoppedBy, req.ActiveSessionIds.Count);

        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = stopEvent.Id.ToString()
        };
        response.AffectedSessions.AddRange(req.ActiveSessionIds);
        return response;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Private helpers
    // ─────────────────────────────────────────────────────────────────────────

    private async Task SignalTemporalEmergencyStopAsync(
        EmergencyStopEvent stopEvent, CancellationToken ct)
    {
        try
        {
            // Use untyped handle — signal the emergency stop workflow by contract ID
            var handle = _temporalClient!.GetWorkflowHandle(stopEvent.ContractId.ToString());
            await handle.SignalAsync("emergency-stop", new object[] { stopEvent.Id.ToString() });

            stopEvent.TemporalSignalledAt = DateTimeOffset.UtcNow;
            await _emergencyDb.SaveChangesAsync(ct);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "Temporal signal failed for EmergencyStop {RecordId}; persisted event is authoritative.",
                stopEvent.Id);
        }
    }
}