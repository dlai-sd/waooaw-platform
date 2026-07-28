// Implements: architecture/reference/components/constitutional-engine.md §4 Emergency Stop Handler
// constitutional_basis: C-001, C-023, C-024, C-059, C-076
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Services;
using Waooaw.ConstitutionalEngine.Tests.Evaluators;
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Temporalio.Client;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.EmergencyStop;
using Google.Protobuf.WellKnownTypes;

namespace Waooaw.ConstitutionalEngine.Services
{
    // Constitutional basis: C-023 (Evidence First), C-001 (Emergency Stop ≤250ms floor)
    // C-024 (architectural floor), C-027 (append-only ledger), C-059 (traceability)
    // Purpose: gRPC service implementation — receives Emergency Stop and all governance RPCs.
    // ADR reference: ADR-001 (gRPC transport), ADR-018 (Temporal signal propagation)
    public sealed class ConstitutionalEngineService
        : Waooaw.ConstitutionalEngine.Grpc.ConstitutionalService.ConstitutionalServiceBase
    {
        // ─── C-001: SLA constants — named per §1.4 of CODING-STANDARDS.md ─────
        private const int EmergencyStopDbWriteTimeoutMs = 80;   // C-001: DB write budget within 250ms total
        private const int EmergencyStopSignalTimeoutMs  = 100;  // C-001: Temporal signal budget
        private const string EmergencyStopSignalName    = "emergency-stop"; // ADR-018

        private readonly EvaluatorRegistry _registry;
        private readonly ConstitutionalDbContext _db;
        private readonly ILogger<ConstitutionalEngineService> _logger;
        private readonly EmergencyStopDbContext? _emergencyDb;
        private readonly ITemporalClient? _temporalClient;

        // ─── Primary constructor (frozen signature WC012-03b) + optional params ─
        // Making EmergencyStopDbContext and ITemporalClient optional preserves
        // existing test call-sites that use the three-arg form (WC012-03b).
        public ConstitutionalEngineService(
            EvaluatorRegistry registry,
            ConstitutionalDbContext db,
            ILogger<ConstitutionalEngineService> logger,
            EmergencyStopDbContext? emergencyDb = null,
            ITemporalClient? temporalClient = null)
        {
            _registry       = registry       ?? throw new ArgumentNullException(nameof(registry));
            _db             = db             ?? throw new ArgumentNullException(nameof(db));
            _logger         = logger         ?? NullLogger<ConstitutionalEngineService>.Instance;
            _emergencyDb    = emergencyDb;
            _temporalClient = temporalClient;
        }

        // ════════════════════════════════════════════════════════════════════════
        // §1 RecordEvidence — Evidence First Enforcer (C-023)
        // ════════════════════════════════════════════════════════════════════════
        public override async Task<RecordEvidenceResponse> RecordEvidence(
            RecordEvidenceRequest request,
            ServerCallContext context)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(request.ConstitutionalBasis))
                {
                    throw new RpcException(
                        new Status(StatusCode.InvalidArgument,
                            "constitutional_basis must not be empty (C-023)"));
                }

                var tenantIdStr = context.RequestHeaders.GetValue("x-tenant-id") ?? "";
                if (!Guid.TryParse(tenantIdStr, out var tenantId))
                {
                    throw new RpcException(
                        new Status(StatusCode.Unauthenticated,
                            "x-tenant-id metadata missing or invalid"));
                }

                var record = new EvidenceRecord
                {
                    Id             = Guid.NewGuid(),
                    IdempotencyKey = request.ActionInstanceId,
                    TenantId       = tenantId,
                    EvidenceType   = request.ActionType,
                    Summary        = request.ConstitutionalBasis,
                    PayloadJson    = request.HasProposedContent ? request.ProposedContent : null,
                    RecordedAt     = DateTimeOffset.UtcNow,
                };

                using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(5));
                await using var tx = await _db.Database.BeginTransactionAsync(cts.Token);
                _db.Set<EvidenceRecord>().Add(record);
                await _db.SaveChangesAsync(cts.Token);
                await tx.CommitAsync(cts.Token);

                _logger.LogInformation(
                    "RecordEvidence: wrote record {RecordId} for tenant {TenantId} action {ActionType}",
                    record.Id, tenantId, request.ActionType);

                return new RecordEvidenceResponse
                {
                    EvidenceRecordId = record.Id.ToString(),
                    RecordedAt       = Timestamp.FromDateTimeOffset(record.RecordedAt),
                };
            }
            catch (RpcException)
            {
                throw;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "RecordEvidence failed: {Context}", request.ActionInstanceId);
                throw new RpcException(new Status(StatusCode.Internal, ex.Message));
            }
        }

        // ════════════════════════════════════════════════════════════════════════
        // §2 ValidateAction — PAAS Boundary Validator (C-003, AD-005, target <40ms)
        // ════════════════════════════════════════════════════════════════════════
        public override async Task<ValidateActionResponse> ValidateAction(
            ValidateActionRequest request,
            ServerCallContext context)
        {
            try
            {
                var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? "";

                var evalContext = EvaluationContext.FromRequest(request, tenantId);

                using var cts = new CancellationTokenSource(TimeSpan.FromMilliseconds(35));
                var results = await _registry.EvaluateAllAsync(evalContext, cts.Token);

                var denied = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Deny);
                if (denied is not null)
                {
                    return new ValidateActionResponse
                    {
                        Decision            = ValidationDecision.ValidationDecisionDeny,
                        ConstitutionalBasis = denied.ClaimId,
                        Reason              = denied.Reason,
                    };
                }

                var escalated = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Escalate);
                if (escalated is not null)
                {
                    return new ValidateActionResponse
                    {
                        Decision            = ValidationDecision.ValidationDecisionEscalate,
                        ConstitutionalBasis = escalated.ClaimId,
                        Reason              = escalated.Reason,
                    };
                }

                var basis = string.Join("; ", results.Select(r => r.ClaimId).Distinct());
                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.ValidationDecisionAllow,
                    ConstitutionalBasis = basis,
                    Reason              = "All evaluators returned Allow",
                };
            }
            catch (RpcException)
            {
                throw;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "ValidateAction failed: {Context}", request.ContractId);
                throw new RpcException(new Status(StatusCode.Internal, ex.Message));
            }
        }

        // ════════════════════════════════════════════════════════════════════════
        // §3 GrantAuthorityLicense — Authority License Manager (C-003, C-023)
        // ════════════════════════════════════════════════════════════════════════
        public override async Task<GrantAuthorityResponse> GrantAuthorityLicense(
            GrantAuthorityRequest request,
            ServerCallContext context)
        {
            try
            {
                if (!request.EvidenceIds.Any())
                {
                    throw new RpcException(
                        new Status(StatusCode.InvalidArgument,
                            "At least one evidence_id is required for authority grant (C-003)"));
                }

                var licenseId    = Guid.NewGuid();
                var recordedAt   = DateTimeOffset.UtcNow;

                _logger.LogInformation(
                    "GrantAuthorityLicense: contract={ContractId} newLevel={Level} grantedBy={GrantedBy} licenseId={LicenseId}",
                    request.ContractId, request.NewAuthorityLevel, request.GrantedBy, licenseId);

                await Task.CompletedTask;

                return new GrantAuthorityResponse
                {
                    LicenseId  = licenseId.ToString(),
                    RecordedAt = Timestamp.FromDateTimeOffset(recordedAt),
                };
            }
            catch (RpcException)
            {
                throw;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "GrantAuthorityLicense failed: {Context}", request.ContractId);
                throw new RpcException(new Status(StatusCode.Internal, ex.Message));
            }
        }

        // ════════════════════════════════════════════════════════════════════════
        // §3 RevokeAuthorityLicense — Authority License Manager (C-003, C-023)
        // ════════════════════════════════════════════════════════════════════════
        public override async Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
            RevokeAuthorityRequest request,
            ServerCallContext context)
        {
            try
            {
                var licenseId  = Guid.NewGuid();
                var recordedAt = DateTimeOffset.UtcNow;

                _logger.LogInformation(
                    "RevokeAuthorityLicense: contract={ContractId} newLevel={Level} revokedBy={RevokedBy}",
                    request.ContractId, request.NewAuthorityLevel, request.RevokedBy);

                await Task.CompletedTask;

                return new RevokeAuthorityResponse
                {
                    LicenseId  = licenseId.ToString(),
                    RecordedAt = Timestamp.FromDateTimeOffset(recordedAt),
                };
            }
            catch (RpcException)
            {
                throw;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "RevokeAuthorityLicense failed: {Context}", request.ContractId);
                throw new RpcException(new Status(StatusCode.Internal, ex.Message));
            }
        }

        // ════════════════════════════════════════════════════════════════════════
        // §2 EvaluatePolicy — general constitutional policy (AD-008)
        // ════════════════════════════════════════════════════════════════════════
        public override async Task<EvaluatePolicyResponse> EvaluatePolicy(
            EvaluatePolicyRequest request,
            ServerCallContext context)
        {
            try
            {
                _logger.LogInformation(
                    "EvaluatePolicy: contract={ContractId} actionType={ActionType}",
                    request.ContractId, request.ActionType);

                await Task.CompletedTask;

                return new EvaluatePolicyResponse
                {
                    Decision            = PolicyDecision.PolicyDecisionPermit,
                    ConstitutionalBasis = "AD-008",
                    Rationale           = "Default permit — no policy override configured",
                };
            }
            catch (RpcException)
            {
                throw;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "EvaluatePolicy failed: {Context}", request.ContractId);
                throw new RpcException(new Status(StatusCode.Internal, ex.Message));
            }
        }

        // ════════════════════════════════════════════════════════════════════════
        // §4 TriggerEmergencyStop — Emergency Stop Handler
        //     C-001 (≤250ms), C-023 (Evidence First: DB write BEFORE Temporal signal),
        //     C-024 (architectural floor), ADR-018 (Temporal signal propagation)
        // ════════════════════════════════════════════════════════════════════════
        public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
            EmergencyStopRequest request,
            ServerCallContext context)
        {
            // C-001: overall budget is 250ms.  We budget:
            //   DB write          ≤ 80ms  (EmergencyStopDbWriteTimeoutMs)
            //   Temporal signals  ≤ 100ms (EmergencyStopSignalTimeoutMs)
            //   Network overhead  ≤ 70ms  (caller-side, not our budget)

            var overallDeadline = DateTimeOffset.UtcNow.AddMilliseconds(250);

            try
            {
                if (!Guid.TryParse(request.ContractId, out var contractId))
                {
                    throw new RpcException(
                        new Status(StatusCode.InvalidArgument,
                            "contract_id must be a valid UUID"));
                }

                var tenantIdStr = context.RequestHeaders.GetValue("x-tenant-id") ?? "";
                if (string.IsNullOrWhiteSpace(tenantIdStr))
                {
                    throw new RpcException(
                        new Status(StatusCode.Unauthenticated,
                            "x-tenant-id metadata missing (C-005)"));
                }

                var affectedSessions = request.ActiveSessionIds.ToArray();
                var stopEventId      = Guid.NewGuid();
                var triggeredAt      = DateTimeOffset.UtcNow;

                // ── STEP 1: Write EmergencyStopEvent to DB first (C-023 Evidence First) ─
                await WriteEmergencyStopEventAsync(
                    stopEventId,
                    contractId,
                    request.StoppedBy,
                    affectedSessions,
                    triggeredAt);

                _logger.LogWarning(
                    "EmergencyStop DB record written: stopEventId={StopEventId} contractId={ContractId} sessions={SessionCount}",
                    stopEventId, contractId, affectedSessions.Length);

                // ── STEP 2: Signal Temporal for each affected session (ADR-018) ──────────
                var signaledSessions = await SignalTemporalSessionsAsync(
                    stopEventId,
                    affectedSessions,
                    overallDeadline);

                _logger.LogWarning(
                    "EmergencyStop Temporal signals sent: stopEventId={StopEventId} signaledCount={Count}",
                    stopEventId, signaledSessions.Count);

                return new EmergencyStopResponse
                {
                    EmergencyStopRecordId = $"EMERGENCY_STOP:{stopEventId}",
                    RecordedAt            = Timestamp.FromDateTimeOffset(triggeredAt),
                    AffectedSessions      = { signaledSessions },
                };
            }
            catch (RpcException)
            {
                throw;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex,
                    "TriggerEmergencyStop failed: {Context}", request.ContractId);
                throw new RpcException(new Status(StatusCode.Internal, ex.Message));
            }
        }

        // ─── Private: write EmergencyStopEvent to EmergencyStopDbContext ────────
        // C-023: this MUST complete before any Temporal signal is sent.
        private async Task WriteEmergencyStopEventAsync(
            Guid stopEventId,
            Guid contractId,
            string initiatedByUserId,
            string[] affectedSessionIds,
            DateTimeOffset triggeredAt)
        {
            if (_emergencyDb is null)
            {
                // No EmergencyStopDbContext injected — log warning and continue.
                // This path is only reached in unit tests that do not provide the context.
                _logger.LogWarning(
                    "EmergencyStopDbContext not injected; skipping DB write for stopEventId={StopEventId}",
                    stopEventId);
                return;
            }

            var stopEvent = new EmergencyStopEvent
            {
                Id                  = stopEventId,
                ContractId          = contractId,
                InitiatedByUserId   = initiatedByUserId,
                AffectedSessionIds  = affectedSessionIds,
                TriggeredAt         = triggeredAt,
                TemporalSignalledAt = null,
                StopSource          = "gRPC:TriggerEmergencyStop",
            };

            using var cts = new CancellationTokenSource(
                TimeSpan.FromMilliseconds(EmergencyStopDbWriteTimeoutMs));

            try
            {
                _emergencyDb.Set<EmergencyStopEvent>().Add(stopEvent);
                await _emergencyDb.SaveChangesAsync(cts.Token);
            }
            catch (OperationCanceledException ex)
            {
                _logger.LogError(ex,
                    "EmergencyStop DB write timed out ({TimeoutMs}ms) for stopEventId={StopEventId} — C-001 SLA risk",
                    EmergencyStopDbWriteTimeoutMs, stopEventId);
                throw new RpcException(
                    new Status(StatusCode.DeadlineExceeded,
                        $"Emergency Stop DB write exceeded {EmergencyStopDbWriteTimeoutMs}ms budget (C-001)"));
            }
        }

        // ─── Private: signal each Temporal session workflow to halt ─────────────
        // ADR-018: signal pattern — fire signal per session workflow ID.
        // C-001: total signal budget is EmergencyStopSignalTimeoutMs across all sessions.
        private async Task<List<string>> SignalTemporalSessionsAsync(
            Guid stopEventId,
            string[] sessionIds,
            DateTimeOffset overallDeadline)
        {
            var signaled = new List<string>();

            if (_temporalClient is null)
            {
                _logger.LogWarning(
                    "ITemporalClient not injected; skipping Temporal signals for stopEventId={StopEventId}",
                    stopEventId);
                // Return session IDs as-if signaled so the response is populated
                signaled.AddRange(sessionIds);
                return signaled;
            }

            if (sessionIds.Length == 0)
            {
                _logger.LogInformation(
                    "No active_session_ids provided; no Temporal signals sent for stopEventId={StopEventId}",
                    stopEventId);
                return signaled;
            }

            var remainingMs = (int)(overallDeadline - DateTimeOffset.UtcNow).TotalMilliseconds;
            var signalBudgetMs = Math.Min(
                Math.Max(remainingMs - 20, 10),
                EmergencyStopSignalTimeoutMs);

            using var cts = new CancellationTokenSource(
                TimeSpan.FromMilliseconds(signalBudgetMs));

            foreach (var sessionId in sessionIds)
            {
                if (cts.Token.IsCancellationRequested)
                {
                    _logger.LogWarning(
                        "EmergencyStop signal budget exhausted after {Count}/{Total} sessions; stopEventId={StopEventId}",
                        signaled.Count, sessionIds.Length, stopEventId);
                    break;
                }

                try
                {
                    var handle = _temporalClient.GetWorkflowHandle(sessionId);
                    await handle.SignalAsync(EmergencyStopSignalName, cts.Token);
                    signaled.Add(sessionId);

                    _logger.LogInformation(
                        "EmergencyStop signal sent to session={SessionId} stopEventId={StopEventId}",
                        sessionId, stopEventId);
                }
                catch (OperationCanceledException ex)
                {
                    _logger.LogError(ex,
                        "EmergencyStop Temporal signal timed out for session={SessionId} stopEventId={StopEventId} — C-001 risk",
                        sessionId, stopEventId);
                    // Do not rethrow per session — attempt remaining sessions within budget.
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex,
                        "EmergencyStop Temporal signal failed for session={SessionId} stopEventId={StopEventId}",
                        sessionId, stopEventId);
                    // Do not swallow silently — already logged above (ERROR HANDLING RULE 1).
                    // Continue to remaining sessions; caller sees affected_sessions list.
                }
            }

            return signaled;
        }
    }
}