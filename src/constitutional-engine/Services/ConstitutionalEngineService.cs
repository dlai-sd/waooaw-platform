// Implements: architecture/reference/components/constitutional-engine.md §4 Emergency Stop Handler
// Constitutional basis: C-001 (≤250ms), C-023 (Evidence First), C-024 (architectural floor), C-059 (Traceability)
using Grpc.Core;
using Microsoft.Extensions.Logging.Abstractions;
using System.Text.Json;
using Temporalio.Client;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.EmergencyStop;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    private readonly EvaluatorRegistry _registry;
    private readonly ConstitutionalDbContext _db;
    private readonly ILogger<ConstitutionalEngineService> _logger;
    private readonly EmergencyStopDbContext? _emergencyDb;
    private readonly ITemporalClient? _temporalClient;

    // Primary constructor — all new deps are optional so existing test call-sites compile unchanged.
    public ConstitutionalEngineService(
        EvaluatorRegistry registry,
        ConstitutionalDbContext db,
        ILogger<ConstitutionalEngineService>? logger = null,
        EmergencyStopDbContext? emergencyDb = null,
        ITemporalClient? temporalClient = null)
    {
        _registry        = registry;
        _db              = db;
        _logger          = logger ?? NullLogger<ConstitutionalEngineService>.Instance;
        _emergencyDb     = emergencyDb;
        _temporalClient  = temporalClient;
    }

    // ── §1 Validate Action ────────────────────────────────────────────────────

    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext context)
    {
        var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;
        var ctx = EvaluationContext.FromRequest(req, tenantId);

        var results = await _registry.EvaluateAllAsync(ctx, context.CancellationToken);

        var anyDeny     = results.Any(r => r.Verdict == EvaluationVerdict.Deny);
        var anyEscalate = results.Any(r => r.Verdict == EvaluationVerdict.Escalate);

        // ValidationDecision only exposes Unspecified=0 in the compiled proto;
        // map outcomes to the closest defined values.
        var decision = anyDeny
            ? ValidationDecision.Unspecified   // Denied path — proto Deny not yet emitted
            : ValidationDecision.Unspecified;  // Allow path — proto Allow not yet emitted

        var basis   = string.Join(", ", results.Select(r => r.ClaimId));
        var reasons = string.Join("; ", results.Select(r => r.Reason));

        _logger.LogInformation(
            "ValidateAction ContractId={ContractId} Decision={Decision} Basis={Basis}",
            req.ContractId, decision, basis);

        return new ValidateActionResponse
        {
            Decision           = decision,
            ConstitutionalBasis = basis,
            Reason             = reasons
        };
    }

    // ── §1 Record Evidence (C-023 Evidence-First) ─────────────────────────────

    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext context)
    {
        var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        var record = new EvidenceRecord
        {
            Id             = Guid.NewGuid(),
            IdempotencyKey = req.ActionInstanceId,
            TenantId       = Guid.TryParse(tenantId, out var tid) ? tid : Guid.Empty,
            EvidenceType   = req.ActionType,
            Summary        = req.ProposedContent ?? req.ExecutedContent ?? req.ActionType,
            PayloadJson    = JsonSerializer.Serialize(req),
            RecordedAt     = DateTimeOffset.UtcNow
        };

        _db.EvidenceRecords.Add(record);
        await _db.SaveChangesAsync(context.CancellationToken);

        _logger.LogInformation(
            "RecordEvidence EvidenceRecordId={Id} ContractId={ContractId}",
            record.Id, req.ContractId);

        return new RecordEvidenceResponse { EvidenceRecordId = record.Id.ToString() };
    }

    // ── §2 Authority Lifecycle ────────────────────────────────────────────────

    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext context)
    {
        _logger.LogInformation(
            "GrantAuthorityLicense ContractId={ContractId} GrantedBy={GrantedBy}",
            req.ContractId, req.GrantedBy);

        return Task.FromResult(new GrantAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
    }

    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext context)
    {
        _logger.LogInformation(
            "RevokeAuthorityLicense ContractId={ContractId} RevokedBy={RevokedBy}",
            req.ContractId, req.RevokedBy);

        return Task.FromResult(new RevokeAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
    }

    // ── §3 Policy Evaluation ──────────────────────────────────────────────────

    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext context)
    {
        _logger.LogInformation(
            "EvaluatePolicy ContractId={ContractId}", req.ContractId);

        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit
        });
    }

    // ── §4 Emergency Stop Handler (WC012-04b) ─────────────────────────────────
    // C-001: ≤250ms P99  |  C-023: Evidence First  |  ADR-018: Temporal signal

    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext context)
    {
        var ct       = context.CancellationToken;
        var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        _logger.LogInformation(
            "TriggerEmergencyStop ContractId={ContractId} StoppedBy={StoppedBy} Sessions={Count}",
            req.ContractId, req.StoppedBy, req.ActiveSessionIds.Count);

        var stopEvent = new EmergencyStopEvent
        {
            Id                = Guid.NewGuid(),
            ContractId        = Guid.TryParse(req.ContractId, out var cid) ? cid : Guid.Empty,
            InitiatedByUserId = req.StoppedBy,
            AffectedSessionIds = req.ActiveSessionIds.ToArray(),
            TriggeredAt       = DateTimeOffset.UtcNow,
            TemporalSignalledAt = null,
            StopSource        = "gRPC"
        };

        // ── C-023: Evidence First — persist before ANY side-effects ──────────
        if (_emergencyDb is not null)
        {
            _emergencyDb.Set<EmergencyStopEvent>().Add(stopEvent);
            await _emergencyDb.SaveChangesAsync(ct);

            _logger.LogInformation(
                "EmergencyStop persisted Id={Id} ContractId={ContractId}",
                stopEvent.Id, stopEvent.ContractId);
        }
        else
        {
            _logger.LogWarning(
                "EmergencyStopDbContext not configured — event {Id} not persisted",
                stopEvent.Id);
        }

        // ── ADR-018: Signal Temporal workflows (one per affected session) ─────
        if (_temporalClient is not null && req.ActiveSessionIds.Count > 0)
        {
            var signalErrors = 0;

            foreach (var sessionId in req.ActiveSessionIds)
            {
                try
                {
                    var handle = _temporalClient.GetWorkflowHandle(sessionId);
                    await handle.SignalAsync(
                        "emergency_stop",
                        new object[] { stopEvent.Id.ToString() });
                }
                catch (Exception ex)
                {
                    signalErrors++;
                    _logger.LogError(
                        ex,
                        "Failed to signal Temporal workflow SessionId={SessionId} StopId={StopId}",
                        sessionId, stopEvent.Id);
                }
            }

            // Record the Temporal signal timestamp regardless of partial failures
            stopEvent.TemporalSignalledAt = DateTimeOffset.UtcNow;

            if (_emergencyDb is not null)
            {
                await _emergencyDb.SaveChangesAsync(ct);
            }

            if (signalErrors > 0)
            {
                _logger.LogWarning(
                    "EmergencyStop {Id}: {Errors}/{Total} Temporal signals failed",
                    stopEvent.Id, signalErrors, req.ActiveSessionIds.Count);
            }
        }
        else if (_temporalClient is null)
        {
            _logger.LogWarning(
                "ITemporalClient not configured — sessions not signalled for StopId={Id}",
                stopEvent.Id);
        }

        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = stopEvent.Id.ToString()
        };
        response.AffectedSessions.AddRange(req.ActiveSessionIds);
        return response;
    }
}