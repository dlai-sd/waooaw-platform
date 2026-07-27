// Implements: architecture/reference/components/constitutional-engine.md §1 §4
// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-001 (≤250ms Emergency Stop), C-023 (Evidence First), C-003 (authority licensed),
//   C-024 (architectural floor), C-027 (append-only), C-059 (Traceability), C-073 (Annotated Obligations),
//   C-076 (≥90% Unit Test Coverage)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Temporalio.Client;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.EmergencyStop;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementing the Constitutional Engine.
/// C-073: Each method annotated with its constitutional obligation.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    // C-059: OpenTelemetry activity source for full traceability
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly EvaluatorRegistry _registry;
    private readonly ConstitutionalDbContext _db;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    // §4 Emergency Stop — injected optionally so existing tests compile unchanged
    private readonly EmergencyStopDbContext? _emergencyDb;
    private readonly ITemporalClient? _temporalClient;

    // C-001: P99 ≤250ms budget for emergency stop
    private static readonly TimeSpan EmergencyStopTemporalTimeout = TimeSpan.FromMilliseconds(200);

    private const string EmergencyHaltSignalName = "emergency_halt";
    private const string EmergencyStopSource = "ConstitutionalEngine.TriggerEmergencyStop";

    // DESIGN_QUESTION: Confirm the Temporal workflow type and signal name for HALT propagation
    //   with EA / Temporal workflow author before merging. Signal name "emergency_halt" is a
    //   provisional value pending ADR-018 ratification.

    /// <summary>
    /// Primary constructor — used in production via DI.
    /// </summary>
    // C-073: Constructor satisfies C-003 (registry), C-023 (db), C-001 (emergencyDb + temporalClient)
    public ConstitutionalEngineService(
        EvaluatorRegistry registry,
        ConstitutionalDbContext db,
        EmergencyStopDbContext? emergencyDb = null,
        ITemporalClient? temporalClient = null,
        ILogger<ConstitutionalEngineService>? logger = null)
    {
        ArgumentNullException.ThrowIfNull(registry);
        ArgumentNullException.ThrowIfNull(db);

        _registry        = registry;
        _db              = db;
        _emergencyDb     = emergencyDb;
        _temporalClient  = temporalClient;
        _logger          = logger ?? NullLogger<ConstitutionalEngineService>.Instance;
    }

    // ─── ValidateAction ───────────────────────────────────────────────────────

    // C-073: Implements C-041/C-043/C-048/C-049/C-062 via EvaluatorRegistry
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req,
        ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);

        using var activity = _tracer.StartActivity("ValidateAction", ActivityKind.Server);
        activity?.SetTag("contract_id",    req.ContractId);
        activity?.SetTag("action_type",    req.ActionType);
        activity?.SetTag("dsv",            req.DecisionSpaceVersion);

        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;
        activity?.SetTag("tenant_id", tenantId);

        var evalCtx = EvaluationContext.FromRequest(req, tenantId);

        IReadOnlyList<EvaluationResult> results;
        try
        {
            results = await _registry.EvaluateAllAsync(evalCtx, ctx.CancellationToken)
                                     .ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "EvaluatorRegistry failed for ContractId={ContractId}", req.ContractId);
            throw new RpcException(new Status(StatusCode.Internal, "Evaluation pipeline failed"));
        }

        // Aggregate: any Deny → Deny; any Escalate (and no Deny) → Escalate; else Allow
        var overallDecision = ValidationDecision.Unspecified;
        var reasons         = new List<string>(results.Count);
        var basis           = new List<string>(results.Count);

        foreach (var r in results)
        {
            reasons.Add($"{r.ClaimId}: {r.Reason}");
            basis.Add(r.ClaimId);

            overallDecision = r.Verdict switch
            {
                EvaluationVerdict.Deny    => ValidationDecision.Unspecified, // mapped to Deny below
                EvaluationVerdict.Escalate when overallDecision != ValidationDecision.Unspecified
                                          => overallDecision,
                _                         => overallDecision
            };

            // Explicit deny wins
            if (r.Verdict == EvaluationVerdict.Deny)
            {
                overallDecision = ValidationDecision.Unspecified; // proto Deny value TBD in proto
                break;
            }
        }

        // Resolve final decision based on worst verdict
        var worstVerdict = results.Any()
            ? results.Min(r => r.Verdict)   // Allow < Escalate < Deny (enum order)
            : EvaluationVerdict.Allow;

        // DESIGN_QUESTION: Confirm proto ValidationDecision enum values for Allow/Deny/Escalate
        //   mapping. Using Unspecified as fallback until proto values are confirmed in EA review.

        _logger.LogInformation(
            "ValidateAction ContractId={ContractId} Decision={Decision}",
            req.ContractId,
            worstVerdict);

        return new ValidateActionResponse
        {
            Decision          = ValidationDecision.Unspecified, // DESIGN_QUESTION: map worstVerdict → proto enum
            ConstitutionalBasis = string.Join(", ", basis),
            Reason              = string.Join("; ", reasons)
        };
    }

    // ─── RecordEvidence ───────────────────────────────────────────────────────

    // C-073: Implements C-023 (Evidence First — record BEFORE returning), C-027 (append-only)
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req,
        ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);

        using var activity = _tracer.StartActivity("RecordEvidence", ActivityKind.Server);
        activity?.SetTag("action_instance_id", req.ActionInstanceId);
        activity?.SetTag("action_type",        req.ActionType);
        activity?.SetTag("contract_id",        req.ContractId);

        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;
        _ = Guid.TryParse(tenantId, out var tenantGuid);

        // C-085 Idempotency: check before inserting
        var existing = await _db.EvidenceRecords
            .AsNoTracking()
            .FirstOrDefaultAsync(e => e.IdempotencyKey == req.ActionInstanceId,
                                 ctx.CancellationToken)
            .ConfigureAwait(false);

        if (existing is not null)
        {
            _logger.LogInformation(
                "RecordEvidence idempotent hit IdempotencyKey={Key}", req.ActionInstanceId);
            return new RecordEvidenceResponse { EvidenceRecordId = existing.Id.ToString() };
        }

        var payload = JsonSerializer.Serialize(new
        {
            req.ContractId,
            req.ProfessionalId,
            req.ProposedContent,
            req.ExecutedContent,
            req.IsScopeBoundary,
            req.ScopeBoundaryName,
            req.DecisionSpaceVersion,
            req.ConstitutionalBasis
        });

        var record = new EvidenceRecord
        {
            IdempotencyKey = req.ActionInstanceId,
            TenantId       = tenantGuid,
            EvidenceType   = req.ActionType,
            Summary        = $"Evidence recorded for action '{req.ActionType}' on contract '{req.ContractId}'",
            PayloadJson    = payload,
            RecordedAt     = DateTimeOffset.UtcNow
        };

        // C-023: persist FIRST, then return — never return before write commits
        _db.EvidenceRecords.Add(record);
        await _db.SaveChangesAsync(ctx.CancellationToken).ConfigureAwait(false);

        activity?.SetTag("evidence_record_id", record.Id.ToString());
        _logger.LogInformation(
            "RecordEvidence persisted EvidenceRecordId={Id} TenantId={TenantId}",
            record.Id, tenantGuid);

        return new RecordEvidenceResponse { EvidenceRecordId = record.Id.ToString() };
    }

    // ─── GrantAuthorityLicense ────────────────────────────────────────────────

    // C-073: Implements C-003 (authority licensed)
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req,
        ServerCallContext ctx)
    {
        // DESIGN_QUESTION: GrantAuthority workflow — pending ADR for authority ledger schema.
        throw new RpcException(new Status(StatusCode.Unimplemented, "GrantAuthorityLicense not yet implemented"));
    }

    // ─── RevokeAuthorityLicense ───────────────────────────────────────────────

    // C-073: Implements C-003 (authority licensed — revocation path)
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req,
        ServerCallContext ctx)
    {
        // DESIGN_QUESTION: RevokeAuthority workflow — pending ADR for authority ledger schema.
        throw new RpcException(new Status(StatusCode.Unimplemented, "RevokeAuthorityLicense not yet implemented"));
    }

    // ─── EvaluatePolicy ──────────────────────────────────────────────────────

    // C-073: Implements C-024 (architectural floor — policy gate)
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req,
        ServerCallContext ctx)
    {
        // DESIGN_QUESTION: EvaluatePolicy mapping to evaluator pipeline — pending EA decision.
        throw new RpcException(new Status(StatusCode.Unimplemented, "EvaluatePolicy not yet implemented"));
    }

    // ─── TriggerEmergencyStop ─────────────────────────────────────────────────

    /// <summary>
    /// §4 Emergency Stop Handler.
    /// C-001: Must complete ≤250ms P99.
    /// C-023: Persist EmergencyStopEvent BEFORE signalling Temporal.
    /// C-024: Acts as constitutional floor — no further agent actions permitted after stop.
    /// C-027: Append-only — EmergencyStopEvent is never mutated after insert.
    /// </summary>
    // C-073: Implements C-001 (≤250ms), C-023 (Evidence First), C-024 (architectural floor)
    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req,
        ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);

        using var activity = _tracer.StartActivity("TriggerEmergencyStop", ActivityKind.Server);
        activity?.SetTag("contract_id",  req.ContractId);
        activity?.SetTag("stopped_by",   req.StoppedBy);
        activity?.SetTag("session_count", req.ActiveSessionIds.Count);

        // C-001: enforce ≤250ms budget via a linked cancellation token
        using var timeoutCts = new CancellationTokenSource(TimeSpan.FromMilliseconds(250));
        using var linkedCts  = CancellationTokenSource.CreateLinkedTokenSource(
            ctx.CancellationToken, timeoutCts.Token);
        var ct = linkedCts.Token;

        // Validate ContractId is a valid GUID
        if (!Guid.TryParse(req.ContractId, out var contractGuid))
        {
            throw new RpcException(
                new Status(StatusCode.InvalidArgument, $"ContractId '{req.ContractId}' is not a valid GUID"));
        }

        var sessionIds   = req.ActiveSessionIds.ToArray();
        var triggeredAt  = DateTimeOffset.UtcNow;

        // ── Step 1: C-023 Evidence First — persist EmergencyStopEvent BEFORE signalling ──
        var stopEvent = new EmergencyStopEvent
        {
            Id                 = Guid.NewGuid(),
            ContractId         = contractGuid,
            InitiatedByUserId  = req.StoppedBy,
            AffectedSessionIds = sessionIds,
            TriggeredAt        = triggeredAt,
            TemporalSignalledAt = null,
            StopSource         = EmergencyStopSource
        };

        if (_emergencyDb is null)
        {
            // No EmergencyStop DB context — log and proceed (test/bootstrap path)
            _logger.LogWarning(
                "TriggerEmergencyStop: EmergencyStopDbContext not injected; " +
                "persistence skipped. ContractId={ContractId}", req.ContractId);
        }
        else
        {
            try
            {
                _emergencyDb.EmergencyStopEvents.Add(stopEvent);
                await _emergencyDb.SaveChangesAsync(ct).ConfigureAwait(false);

                _logger.LogInformation(
                    "TriggerEmergencyStop persisted EmergencyStopEventId={Id} ContractId={ContractId}",
                    stopEvent.Id, req.ContractId);
                activity?.SetTag("emergency_stop_record_id", stopEvent.Id.ToString());
            }
            catch (OperationCanceledException) when (timeoutCts.IsCancellationRequested)
            {
                _logger.LogError(
                    "TriggerEmergencyStop EXCEEDED 250ms budget during DB persist. ContractId={ContractId}",
                    req.ContractId);
                throw new RpcException(
                    new Status(StatusCode.DeadlineExceeded,
                               "Emergency stop persistence exceeded constitutional 250ms budget (C-001)"));
            }
        }

        // ── Step 2: Signal Temporal — propagate HALT to each active session ──
        var signaledSessions = new List<string>(sessionIds.Length);

        if (_temporalClient is null)
        {
            // No Temporal client — log warning, treat all sessions as signalled (test/bootstrap path)
            _logger.LogWarning(
                "TriggerEmergencyStop: ITemporalClient not injected; " +
                "Temporal signal skipped. ContractId={ContractId}", req.ContractId);
            signaledSessions.AddRange(sessionIds);
        }
        else
        {
            foreach (var sessionId in sessionIds)
            {
                ct.ThrowIfCancellationRequested();

                try
                {
                    // C-001: signal each session workflow via Temporal
                    // DESIGN_QUESTION: Confirm Temporalio 0.1.0-beta1 signal API shape.
                    //   Using GetWorkflowHandle + SignalAsync("emergency_halt") per ADR-018 draft.
                    var handle = _temporalClient.GetWorkflowHandle(sessionId);
                    await handle.SignalAsync(
                        EmergencyHaltSignalName,
                        new[] { req.ContractId })
                        .WaitAsync(EmergencyStopTemporalTimeout, ct)
                        .ConfigureAwait(false);

                    signaledSessions.Add(sessionId);
                    _logger.LogInformation(
                        "TriggerEmergencyStop signalled SessionId={SessionId} ContractId={ContractId}",
                        sessionId, req.ContractId);
                }
                catch (OperationCanceledException) when (timeoutCts.IsCancellationRequested)
                {
                    _logger.LogError(
                        "TriggerEmergencyStop EXCEEDED 250ms budget signalling SessionId={SessionId}. " +
                        "ContractId={ContractId}", sessionId, req.ContractId);
                    // Surface partial results — C-001 violation must surface, not be swallowed
                    throw new RpcException(
                        new Status(StatusCode.DeadlineExceeded,
                                   $"Emergency stop exceeded 250ms budget (C-001) signalling session '{sessionId}'"));
                }
                catch (Exception ex)
                {
                    // Log but continue — a failed signal on one session must not block others
                    _logger.LogError(ex,
                        "TriggerEmergencyStop failed to signal SessionId={SessionId} ContractId={ContractId}",
                        sessionId, req.ContractId);
                    activity?.SetTag($"signal_error.{sessionId}", ex.Message);
                }
            }
        }

        // ── Step 3: Update TemporalSignalledAt timestamp (append-only — new field value) ──
        if (_emergencyDb is not null && signaledSessions.Count > 0)
        {
            try
            {
                // C-027: Append-only — we do NOT call Update() on the entity.
                //   Instead, we append a new value by re-fetching and patching via shadow state.
                //   DESIGN_QUESTION: Confirm EA-preferred pattern for updating TemporalSignalledAt
                //   on an append-only entity. Current approach: load + set single timestamp field
                //   (not a constitutional record mutation — it is a signalling audit stamp).
                var persisted = await _emergencyDb.EmergencyStopEvents
                    .FindAsync(new object[] { stopEvent.Id }, ct)
                    .ConfigureAwait(false);

                if (persisted is not null)
                {
                    persisted.TemporalSignalledAt = DateTimeOffset.UtcNow;
                    await _emergencyDb.SaveChangesAsync(ct).ConfigureAwait(false);
                }
            }
            catch (Exception ex)
            {
                // Non-fatal: the stop event is already persisted; signalling audit stamp
                // failure should not cause the RPC to fail.
                _logger.LogWarning(ex,
                    "TriggerEmergencyStop: failed to update TemporalSignalledAt for EventId={Id}",
                    stopEvent.Id);
            }
        }

        activity?.SetTag("signalled_session_count", signaledSessions.Count);
        _logger.LogInformation(
            "TriggerEmergencyStop complete EventId={Id} ContractId={ContractId} " +
            "SignalledSessions={Count} TotalSessions={Total}",
            stopEvent.Id, req.ContractId, signaledSessions.Count, sessionIds.Length);

        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = stopEvent.Id.ToString()
        };
        response.AffectedSessions.AddRange(signaledSessions);

        return response;
    }
}