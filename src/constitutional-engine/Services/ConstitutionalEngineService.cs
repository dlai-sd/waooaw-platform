// Implements: architecture/reference/components/constitutional-engine.md §1 Evidence First Enforcer
// Implements: architecture/reference/components/constitutional-engine.md §4 Emergency Stop Handler
// constitutional_basis: C-001, C-007, C-023, C-024, C-027, C-059, C-076, C-085
using System.Text.Json;
using Google.Protobuf.WellKnownTypes;
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
/// gRPC service implementation.
/// RecordEvidence:       WC012-03b — Evidence First Enforcer (C-023, C-007, C-027, C-085).
/// ValidateAction:       WC012-02b (prior sprint).
/// TriggerEmergencyStop: WC012-04b — Emergency Stop Handler (C-001, C-023, C-024).
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    // ─── Latency budgets ────────────────────────────────────────────────────
    // C-001 / AD-001: Emergency Stop ≤ 250 ms end-to-end.
    // 100 ms allocated to this service (header: "100ms here").
    private static readonly TimeSpan EmergencyStopTimeout  = TimeSpan.FromMilliseconds(100);

    // ValidateAction latency budget: target < 40 ms (ADR-001, AD-005)
    private static readonly TimeSpan ValidateActionTimeout = TimeSpan.FromSeconds(5);

    // RecordEvidence latency budget: target < 80 ms (AD-005)
    private static readonly TimeSpan RecordEvidenceTimeout = TimeSpan.FromSeconds(10);

    // ─── Dependencies ───────────────────────────────────────────────────────
    private readonly EvaluatorRegistry                          _registry;
    private readonly ILogger<ConstitutionalEngineService>       _logger;
    private readonly IDbContextFactory<ConstitutionalDbContext> _dbContextFactory;

    // Added in WC012-04b — optional so the 3-arg constructor used by existing
    // test helpers continues to compile unchanged (constructor compatibility rule).
    private readonly IDbContextFactory<EmergencyStopDbContext>? _emergencyStopDbContextFactory;
    private readonly ITemporalClient?                           _temporalClient;

    // ─── Primary constructor (5 args — DI registration) ────────────────────
    public ConstitutionalEngineService(
        EvaluatorRegistry registry,
        ILogger<ConstitutionalEngineService> logger,
        IDbContextFactory<ConstitutionalDbContext> dbContextFactory,
        IDbContextFactory<EmergencyStopDbContext> emergencyStopDbContextFactory,
        ITemporalClient temporalClient)
    {
        _registry                      = registry;
        _logger                        = logger;
        _dbContextFactory              = dbContextFactory;
        _emergencyStopDbContextFactory = emergencyStopDbContextFactory;
        _temporalClient                = temporalClient;
    }

    // ─── Compatibility overload — 3 args (preserves existing test call-sites) ─
    // WC012-03b tests inject only the first three dependencies; Emergency Stop
    // functionality simply requires the additional factories at runtime.
    public ConstitutionalEngineService(
        EvaluatorRegistry registry,
        ILogger<ConstitutionalEngineService> logger,
        IDbContextFactory<ConstitutionalDbContext> dbContextFactory)
        : this(registry, logger, dbContextFactory, null!, null!)
    {
    }

    // ═══════════════════════════════════════════════════════════════════════
    // §1  Evidence First Enforcer — RecordEvidence
    // C-023: Write to Constitutional Audit Ledger BEFORE returning OK.
    // C-007 / C-027: Append-only; no UPDATE or DELETE ever issued.
    // C-085: Idempotent on (IdempotencyKey, TenantId).
    // ═══════════════════════════════════════════════════════════════════════
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        var rawTenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        if (string.IsNullOrWhiteSpace(rawTenantId))
        {
            _logger.LogWarning(
                "RecordEvidence rejected: x-tenant-id metadata absent. " +
                "ActionInstanceId={ActionInstanceId} ActionType={ActionType}",
                req.ActionInstanceId, req.ActionType);

            throw new RpcException(
                new Status(StatusCode.Unauthenticated,
                    "x-tenant-id gRPC metadata is required (C-005: tenant isolation)."));
        }

        if (!Guid.TryParse(rawTenantId, out var tenantGuid))
        {
            _logger.LogWarning(
                "RecordEvidence rejected: x-tenant-id is not a valid UUID. " +
                "TenantIdRaw={TenantIdRaw} ActionInstanceId={ActionInstanceId}",
                rawTenantId, req.ActionInstanceId);

            throw new RpcException(
                new Status(StatusCode.Unauthenticated,
                    "x-tenant-id must be a valid UUID in canonical format (C-005)."));
        }

        if (string.IsNullOrWhiteSpace(req.ConstitutionalBasis))
        {
            _logger.LogWarning(
                "RecordEvidence rejected: constitutional_basis empty. " +
                "ActionInstanceId={ActionInstanceId} ActionType={ActionType}",
                req.ActionInstanceId, req.ActionType);

            throw new RpcException(
                new Status(StatusCode.InvalidArgument,
                    "constitutional_basis must not be empty (C-023; AD-008)."));
        }

        if (string.IsNullOrWhiteSpace(req.ActionInstanceId))
        {
            _logger.LogWarning(
                "RecordEvidence rejected: ActionInstanceId empty. ActionType={ActionType}",
                req.ActionType);

            throw new RpcException(
                new Status(StatusCode.InvalidArgument,
                    "action_instance_id must not be empty (C-023)."));
        }

        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ctx.CancellationToken);
        cts.CancelAfter(RecordEvidenceTimeout);

        try
        {
            await using var db = await _dbContextFactory.CreateDbContextAsync(cts.Token);

            // C-085: Idempotency — if record with same IdempotencyKey + TenantId already
            // exists, return the existing record without re-inserting (append-only, C-027).
            var existing = await db.Set<EvidenceRecord>()
                .FirstOrDefaultAsync(
                    e => e.IdempotencyKey == req.ActionInstanceId && e.TenantId == tenantGuid,
                    cts.Token);

            if (existing is not null)
            {
                _logger.LogInformation(
                    "RecordEvidence idempotent hit. IdempotencyKey={Key} TenantId={TenantId}",
                    req.ActionInstanceId, tenantGuid);

                return new RecordEvidenceResponse
                {
                    EvidenceRecordId = existing.Id.ToString(),
                    RecordedAt       = Timestamp.FromDateTimeOffset(existing.RecordedAt)
                };
            }

            var record = new EvidenceRecord
            {
                Id             = Guid.NewGuid(),
                IdempotencyKey = req.ActionInstanceId,
                TenantId       = tenantGuid,
                EvidenceType   = req.ActionType,
                Summary        = req.ConstitutionalBasis,
                PayloadJson    = req.HasProposedContent ? req.ProposedContent : null,
                RecordedAt     = DateTimeOffset.UtcNow
            };

            await db.Set<EvidenceRecord>().AddAsync(record, cts.Token);
            await db.SaveChangesAsync(cts.Token);

            _logger.LogInformation(
                "RecordEvidence persisted. RecordId={RecordId} TenantId={TenantId} ActionType={ActionType}",
                record.Id, tenantGuid, req.ActionType);

            return new RecordEvidenceResponse
            {
                EvidenceRecordId = record.Id.ToString(),
                RecordedAt       = Timestamp.FromDateTimeOffset(record.RecordedAt)
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (OperationCanceledException) when (
            cts.IsCancellationRequested && !ctx.CancellationToken.IsCancellationRequested)
        {
            _logger.LogError(
                "RecordEvidence exceeded latency budget {BudgetMs}ms. " +
                "ActionInstanceId={ActionInstanceId}",
                RecordEvidenceTimeout.TotalMilliseconds, req.ActionInstanceId);
            throw new RpcException(new Status(StatusCode.DeadlineExceeded,
                $"RecordEvidence exceeded {RecordEvidenceTimeout.TotalMilliseconds}ms latency budget."));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "RecordEvidence failed. ActionInstanceId={ActionInstanceId} TenantId={TenantId}",
                req.ActionInstanceId, tenantGuid);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // §2  PAAS Boundary Validator — ValidateAction
    // C-003: Authority licensed — validates action is within Decision Space.
    // AD-005: ValidateAction target < 40 ms.
    // ═══════════════════════════════════════════════════════════════════════
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext ctx)
    {
        var rawTenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        if (string.IsNullOrWhiteSpace(rawTenantId))
        {
            throw new RpcException(
                new Status(StatusCode.Unauthenticated,
                    "x-tenant-id gRPC metadata is required (C-005: tenant isolation)."));
        }

        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ctx.CancellationToken);
        cts.CancelAfter(ValidateActionTimeout);

        try
        {
            var evalCtx = EvaluationContext.FromRequest(req, rawTenantId);
            var results = await _registry.EvaluateAllAsync(evalCtx, cts.Token);

            // Any Deny verdict overrides; Escalate is returned if no Deny but escalation needed.
            var firstDeny     = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Deny);
            var firstEscalate = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Escalate);

            if (firstDeny is not null)
            {
                _logger.LogInformation(
                    "ValidateAction DENY. ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                    req.ContractId, firstDeny.ClaimId, firstDeny.Reason);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Deny,
                    ConstitutionalBasis = firstDeny.ClaimId,
                    Reason              = firstDeny.Reason
                };
            }

            if (firstEscalate is not null)
            {
                _logger.LogInformation(
                    "ValidateAction ESCALATE. ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                    req.ContractId, firstEscalate.ClaimId, firstEscalate.Reason);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Escalate,
                    ConstitutionalBasis = firstEscalate.ClaimId,
                    Reason              = firstEscalate.Reason
                };
            }

            _logger.LogInformation(
                "ValidateAction ALLOW. ContractId={ContractId} ActionType={ActionType}",
                req.ContractId, req.ActionType);

            return new ValidateActionResponse
            {
                Decision            = ValidationDecision.Allow,
                ConstitutionalBasis = "C-003; C-041",
                Reason              = "Action is within the approved Decision Space."
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (OperationCanceledException) when (
            cts.IsCancellationRequested && !ctx.CancellationToken.IsCancellationRequested)
        {
            _logger.LogError(
                "ValidateAction exceeded latency budget {BudgetMs}ms. ContractId={ContractId}",
                ValidateActionTimeout.TotalMilliseconds, req.ContractId);
            throw new RpcException(new Status(StatusCode.DeadlineExceeded,
                $"ValidateAction exceeded {ValidateActionTimeout.TotalMilliseconds}ms latency budget."));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "ValidateAction failed. ContractId={ContractId} ActionType={ActionType}",
                req.ContractId, req.ActionType);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // §3  Authority License Manager — GrantAuthorityLicense
    // C-003: Authority earned through evidence.
    // C-023: Write before returning.
    // ═══════════════════════════════════════════════════════════════════════
    public override async Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        var rawTenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        if (string.IsNullOrWhiteSpace(rawTenantId) || !Guid.TryParse(rawTenantId, out var tenantGuid))
        {
            throw new RpcException(
                new Status(StatusCode.Unauthenticated,
                    "x-tenant-id gRPC metadata is required and must be a valid UUID (C-005)."));
        }

        if (req.EvidenceIds.Count == 0)
        {
            throw new RpcException(
                new Status(StatusCode.InvalidArgument,
                    "At least one evidence_id is required for authority grant (C-003)."));
        }

        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ctx.CancellationToken);
        cts.CancelAfter(RecordEvidenceTimeout);

        try
        {
            var licenseId   = Guid.NewGuid();
            var recordedAt  = DateTimeOffset.UtcNow;

            await using var db = await _dbContextFactory.CreateDbContextAsync(cts.Token);

            var record = new EvidenceRecord
            {
                Id             = licenseId,
                IdempotencyKey = $"GRANT:{req.ContractId}:{licenseId}",
                TenantId       = tenantGuid,
                EvidenceType   = "AUTHORITY_GRANT",
                Summary        = $"Authority expanded to level {req.NewAuthorityLevel} by {req.GrantedBy}. Basis: {req.ConstitutionalBasis}",
                PayloadJson    = JsonSerializer.Serialize(new
                {
                    contractId        = req.ContractId,
                    newAuthorityLevel = req.NewAuthorityLevel,
                    grantedBy         = req.GrantedBy,
                    evidenceIds       = req.EvidenceIds.ToArray()
                }),
                RecordedAt = recordedAt
            };

            await db.Set<EvidenceRecord>().AddAsync(record, cts.Token);
            await db.SaveChangesAsync(cts.Token);

            _logger.LogInformation(
                "GrantAuthorityLicense persisted. LicenseId={LicenseId} ContractId={ContractId} Level={Level}",
                licenseId, req.ContractId, req.NewAuthorityLevel);

            return new GrantAuthorityResponse
            {
                LicenseId  = licenseId.ToString(),
                RecordedAt = Timestamp.FromDateTimeOffset(recordedAt)
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "GrantAuthorityLicense failed. ContractId={ContractId}", req.ContractId);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // §3  Authority License Manager — RevokeAuthorityLicense
    // C-003: Authority restriction recorded in Constitutional Audit Ledger.
    // C-023: Write before returning.
    // ═══════════════════════════════════════════════════════════════════════
    public override async Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        var rawTenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        if (string.IsNullOrWhiteSpace(rawTenantId) || !Guid.TryParse(rawTenantId, out var tenantGuid))
        {
            throw new RpcException(
                new Status(StatusCode.Unauthenticated,
                    "x-tenant-id gRPC metadata is required and must be a valid UUID (C-005)."));
        }

        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ctx.CancellationToken);
        cts.CancelAfter(RecordEvidenceTimeout);

        try
        {
            var licenseId  = Guid.NewGuid();
            var recordedAt = DateTimeOffset.UtcNow;

            await using var db = await _dbContextFactory.CreateDbContextAsync(cts.Token);

            var record = new EvidenceRecord
            {
                Id             = licenseId,
                IdempotencyKey = $"REVOKE:{req.ContractId}:{licenseId}",
                TenantId       = tenantGuid,
                EvidenceType   = "AUTHORITY_REVOKE",
                Summary        = $"Authority restricted to level {req.NewAuthorityLevel} by {req.RevokedBy}. Basis: {req.ConstitutionalBasis}",
                PayloadJson    = JsonSerializer.Serialize(new
                {
                    contractId        = req.ContractId,
                    newAuthorityLevel = req.NewAuthorityLevel,
                    revokedBy         = req.RevokedBy,
                    reason            = req.Reason
                }),
                RecordedAt = recordedAt
            };

            await db.Set<EvidenceRecord>().AddAsync(record, cts.Token);
            await db.SaveChangesAsync(cts.Token);

            _logger.LogInformation(
                "RevokeAuthorityLicense persisted. LicenseId={LicenseId} ContractId={ContractId} Level={Level}",
                licenseId, req.ContractId, req.NewAuthorityLevel);

            return new RevokeAuthorityResponse
            {
                LicenseId  = licenseId.ToString(),
                RecordedAt = Timestamp.FromDateTimeOffset(recordedAt)
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "RevokeAuthorityLicense failed. ContractId={ContractId}", req.ContractId);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // §  EvaluatePolicy
    // AD-008: Every permission decision must name its constitutional basis.
    // ═══════════════════════════════════════════════════════════════════════
    public override async Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
    {
        var rawTenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        if (string.IsNullOrWhiteSpace(rawTenantId))
        {
            throw new RpcException(
                new Status(StatusCode.Unauthenticated,
                    "x-tenant-id gRPC metadata is required (C-005)."));
        }

        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ctx.CancellationToken);
        cts.CancelAfter(ValidateActionTimeout);

        try
        {
            // Build a minimal EvaluationContext from the policy request fields.
            var evalCtx = new EvaluationContext(
                req.ContractId,
                req.ActionType,
                req.ActionContext,
                0,
                rawTenantId,
                null,
                0L,
                0L,
                0L,
                string.Empty);

            var results = await _registry.EvaluateAllAsync(evalCtx, cts.Token);

            var firstDeny     = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Deny);
            var firstEscalate = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Escalate);

            if (firstDeny is not null)
            {
                return new EvaluatePolicyResponse
                {
                    Decision            = PolicyDecision.Deny,
                    ConstitutionalBasis = firstDeny.ClaimId,
                    Rationale           = firstDeny.Reason
                };
            }

            if (firstEscalate is not null)
            {
                return new EvaluatePolicyResponse
                {
                    Decision            = PolicyDecision.Escalate,
                    ConstitutionalBasis = firstEscalate.ClaimId,
                    Rationale           = firstEscalate.Reason
                };
            }

            return new EvaluatePolicyResponse
            {
                Decision            = PolicyDecision.Permit,
                ConstitutionalBasis = "C-003; AD-008",
                Rationale           = "Action evaluated against all active claims — no violation found."
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "EvaluatePolicy failed. ContractId={ContractId} ActionType={ActionType}",
                req.ContractId, req.ActionType);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // §4  Emergency Stop Handler — TriggerEmergencyStop
    // C-001: ≤ 250 ms guaranteed — this service: 100 ms (AD-001 budget allocation).
    // C-024: Architectural floor — must always be honoured, no override.
    // C-023: Write EmergencyStopEvent to DB FIRST before signalling Temporal.
    //
    // Sequence (WC012-04b):
    //   1. Validate tenant metadata.
    //   2. Write EmergencyStopEvent to EmergencyStopDbContext (Evidence First, C-023).
    //   3. Signal Temporal workflow for each affected session (ADR-018).
    //   4. Return EmergencyStopResponse with persisted record ID + affected sessions.
    //
    // If Temporal signal fails for a session, the failure is logged (C-082 ERROR HANDLING
    // RULE 1) but does NOT abort the overall stop — the DB record is the constitutional
    // source of truth. Downstream workers poll for ABANDONED state.
    // ═══════════════════════════════════════════════════════════════════════
    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
    {
        var rawTenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        if (string.IsNullOrWhiteSpace(rawTenantId))
        {
            _logger.LogWarning(
                "TriggerEmergencyStop rejected: x-tenant-id metadata absent. ContractId={ContractId}",
                req.ContractId);
            throw new RpcException(
                new Status(StatusCode.Unauthenticated,
                    "x-tenant-id gRPC metadata is required (C-005: tenant isolation)."));
        }

        if (!Guid.TryParse(rawTenantId, out var tenantGuid))
        {
            _logger.LogWarning(
                "TriggerEmergencyStop rejected: x-tenant-id is not a valid UUID. " +
                "TenantIdRaw={TenantIdRaw} ContractId={ContractId}",
                rawTenantId, req.ContractId);
            throw new RpcException(
                new Status(StatusCode.Unauthenticated,
                    "x-tenant-id must be a valid UUID in canonical format (C-005)."));
        }

        if (!Guid.TryParse(req.ContractId, out var contractGuid))
        {
            throw new RpcException(
                new Status(StatusCode.InvalidArgument,
                    "contract_id must be a valid UUID in canonical format."));
        }

        if (string.IsNullOrWhiteSpace(req.StoppedBy))
        {
            throw new RpcException(
                new Status(StatusCode.InvalidArgument,
                    "stopped_by must not be empty (C-024: actor identity required for Emergency Stop)."));
        }

        // C-001: Emergency Stop MUST complete within 100 ms (this service's share of the
        // 250 ms end-to-end budget — see EmergencyStopTimeout constant above).
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ctx.CancellationToken);
        cts.CancelAfter(EmergencyStopTimeout);

        try
        {
            var triggeredAt      = DateTimeOffset.UtcNow;
            var stopEventId      = Guid.NewGuid();
            var affectedSessions = req.ActiveSessionIds.ToList();

            // ── Step 1: Write EmergencyStopEvent to DB FIRST (C-023 Evidence First) ──
            // The constitutional record must exist before any signal is issued.
            // If the DB write fails, the Emergency Stop is constitutionally unrecorded;
            // we surface that as gRPC INTERNAL so the caller does NOT confirm the stop.

            if (_emergencyStopDbContextFactory is null)
            {
                // Configuration error: factory not injected (only acceptable in narrow test
                // harnesses that do not exercise Emergency Stop). Fail loudly.
                _logger.LogError(
                    "TriggerEmergencyStop: EmergencyStopDbContextFactory is null. " +
                    "This is a DI misconfiguration. ContractId={ContractId}",
                    req.ContractId);
                throw new RpcException(
                    new Status(StatusCode.Internal,
                        "Emergency Stop DB context factory is not configured (DI misconfiguration)."));
            }

            var stopEvent = new EmergencyStopEvent
            {
                Id                  = stopEventId,
                ContractId          = contractGuid,
                InitiatedByUserId   = req.StoppedBy,
                AffectedSessionIds  = affectedSessions.ToArray(),
                TriggeredAt         = triggeredAt,
                TemporalSignalledAt = null,         // set after Temporal signal completes
                StopSource          = "CUSTOMER_INITIATED"
            };

            await using var emergencyDb =
                await _emergencyStopDbContextFactory.CreateDbContextAsync(cts.Token);

            await emergencyDb.Set<EmergencyStopEvent>().AddAsync(stopEvent, cts.Token);
            await emergencyDb.SaveChangesAsync(cts.Token);

            _logger.LogInformation(
                "TriggerEmergencyStop: EmergencyStopEvent persisted. " +
                "StopEventId={StopEventId} ContractId={ContractId} SessionCount={SessionCount}",
                stopEventId, req.ContractId, affectedSessions.Count);

            // ── Step 2: Signal Temporal to halt each affected session (ADR-018) ──
            // Temporal signal failures are tolerated — DB record is source of truth.
            // Each failure is logged (C-082: never swallow silently).
            var temporalSignalledAt = default(DateTimeOffset?);

            if (_temporalClient is not null && affectedSessions.Count > 0)
            {
                foreach (var sessionId in affectedSessions)
                {
                    try
                    {
                        var handle = _temporalClient.GetWorkflowHandle(sessionId);
                        await handle.SignalAsync(
                            "emergency-stop",
                            new object[] { stopEventId.ToString(), req.ContractId });
                    }
                    catch (Exception ex)
                    {
                        // C-082 ERROR HANDLING RULE 1: log; do not swallow silently.
                        // The DB record guarantees constitutional enforcement regardless
                        // of Temporal signal outcome.
                        _logger.LogError(ex,
                            "TriggerEmergencyStop: Temporal signal failed for session. " +
                            "SessionId={SessionId} StopEventId={StopEventId} ContractId={ContractId}",
                            sessionId, stopEventId, req.ContractId);
                    }
                }

                temporalSignalledAt = DateTimeOffset.UtcNow;
            }
            else if (_temporalClient is null)
            {
                _logger.LogWarning(
                    "TriggerEmergencyStop: ITemporalClient is null; Temporal signals skipped. " +
                    "StopEventId={StopEventId} ContractId={ContractId}",
                    stopEventId, req.ContractId);
            }

            // ── Step 3: Update TemporalSignalledAt on persisted record (best-effort) ──
            // This is NOT a constitutional obligation but aids audit observability.
            // Failure here must NOT abort the stop — we log and continue.
            if (temporalSignalledAt.HasValue)
            {
                try
                {
                    stopEvent.TemporalSignalledAt = temporalSignalledAt;
                    await emergencyDb.SaveChangesAsync(CancellationToken.None);
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex,
                        "TriggerEmergencyStop: failed to persist TemporalSignalledAt. " +
                        "StopEventId={StopEventId} ContractId={ContractId}",
                        stopEventId, req.ContractId);
                    // Non-fatal: constitutional record already written in Step 1.
                }
            }

            _logger.LogInformation(
                "TriggerEmergencyStop completed. StopEventId={StopEventId} ContractId={ContractId} " +
                "AffectedSessions={AffectedSessions} ElapsedMs={ElapsedMs}",
                stopEventId, req.ContractId,
                string.Join(",", affectedSessions),
                (DateTimeOffset.UtcNow - triggeredAt).TotalMilliseconds);

            // Format: "EMERGENCY_STOP:<uuid>" per evidence-schema.md specification.
            return new EmergencyStopResponse
            {
                EmergencyStopRecordId = $"EMERGENCY_STOP:{stopEventId}",
                AffectedSessions      = { affectedSessions },
                RecordedAt            = Timestamp.FromDateTimeOffset(triggeredAt)
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (OperationCanceledException) when (
            cts.IsCancellationRequested && !ctx.CancellationToken.IsCancellationRequested)
        {
            // C-001: exceeded Emergency Stop latency budget.
            _logger.LogError(
                "TriggerEmergencyStop exceeded latency budget {BudgetMs}ms. ContractId={ContractId}",
                EmergencyStopTimeout.TotalMilliseconds, req.ContractId);
            throw new RpcException(new Status(StatusCode.DeadlineExceeded,
                $"Emergency Stop exceeded {EmergencyStopTimeout.TotalMilliseconds}ms latency budget (C-001, AD-001)."));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "TriggerEmergencyStop failed. ContractId={ContractId} StoppedBy={StoppedBy}",
                req.ContractId, req.StoppedBy);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }
}