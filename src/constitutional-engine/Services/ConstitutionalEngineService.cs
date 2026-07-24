// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-023 (Evidence First), C-027 (append-only ledger), C-003 (authority licensed),
//                       C-013 (Emergency Override), AD-001 (Emergency Stop ≤250ms), AD-002 (Evidence First enforcement),
//                       AD-005 (PAAS latency budget), AD-008 (constitutional basis on every permission decision)

using System.Diagnostics;
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.Grpc;
using Google.Protobuf.WellKnownTypes;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementation for the Constitutional Engine.
/// This is the only service that writes to the Constitutional Audit Ledger.
/// All governance events flow through this service before the calling service may return success.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    private static readonly ActivitySource ActivitySource =
        new("Waooaw.ConstitutionalEngine", "1.0.0");

    private readonly ConstitutionalDbContext _db;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    public ConstitutionalEngineService(
        ConstitutionalDbContext db,
        ILogger<ConstitutionalEngineService> logger)
    {
        _db = db;
        _logger = logger;
    }

    // ─── TENANT EXTRACTION ───────────────────────────────────────────────────

    /// <summary>
    /// Extracts and validates the tenant ID from gRPC metadata.
    /// C-023: tenant_id must be present on every RPC call.
    /// If absent or invalid → throws RpcException with UNAUTHENTICATED.
    /// </summary>
    // C-073: constitutional obligation — tenant isolation enforcement
    private static string ExtractTenantId(ServerCallContext context)
    {
        var tenantEntry = context.RequestHeaders.Get("x-tenant-id");
        if (tenantEntry is null || string.IsNullOrWhiteSpace(tenantEntry.Value))
        {
            throw new RpcException(new Status(
                StatusCode.Unauthenticated,
                "Missing required gRPC metadata: x-tenant-id (C-023, transport notes)"));
        }

        if (!Guid.TryParse(tenantEntry.Value, out _))
        {
            throw new RpcException(new Status(
                StatusCode.Unauthenticated,
                $"Invalid x-tenant-id format — must be a UUID: '{tenantEntry.Value}'"));
        }

        return tenantEntry.Value;
    }

    // ─── RecordEvidence ──────────────────────────────────────────────────────

    /// <summary>
    /// Evidence First Enforcer — writes an evidence record to the Constitutional Audit Ledger
    /// atomically before returning. If the write fails, returns gRPC INTERNAL error.
    /// The caller MUST NOT return success to its own client until this RPC returns OK.
    /// Latency target: &lt;80ms (AD-005).
    /// </summary>
    // C-073: constitutional obligation — Evidence First (C-023), append-only ledger (C-027)
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest request,
        ServerCallContext context)
    {
        // C-073: OTel span for Evidence First enforcement
        using var activity = ActivitySource.StartActivity("constitutional.evidence.record");
        activity?.SetTag("constitutional.basis", "C-023,C-027,AD-002");
        activity?.SetTag("evidence.type", request.EvidenceType.ToString());
        activity?.SetTag("idempotency.key", request.IdempotencyKey);

        var tenantId = ExtractTenantId(context);
        activity?.SetTag("tenant.id", tenantId);

        _logger.LogInformation(
            "RecordEvidence called. IdempotencyKey={IdempotencyKey} EvidenceType={EvidenceType} TenantId={TenantId}",
            request.IdempotencyKey, request.EvidenceType, tenantId);

        // Validate required fields
        if (string.IsNullOrWhiteSpace(request.IdempotencyKey))
        {
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                "idempotency_key is required"));
        }

        if (string.IsNullOrWhiteSpace(request.ConstitutionalBasis))
        {
            // AD-008: every evidence record must name its constitutional basis
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                "constitutional_basis is required (AD-008)"));
        }

        try
        {
            // C-027: Check idempotency — return existing record if key already used
            var existing = await _db.EvidenceRecords
                .AsNoTracking()
                .FirstOrDefaultAsync(
                    e => e.IdempotencyKey == request.IdempotencyKey && e.TenantId == tenantId,
                    context.CancellationToken);

            if (existing is not null)
            {
                _logger.LogInformation(
                    "RecordEvidence idempotent hit. EvidenceId={EvidenceId} IdempotencyKey={IdempotencyKey}",
                    existing.Id, request.IdempotencyKey);

                activity?.SetTag("idempotent.hit", true);

                return new RecordEvidenceResponse
                {
                    EvidenceId = existing.Id.ToString(),
                    LedgerTimestamp = Timestamp.FromDateTimeOffset(existing.LedgerTimestamp),
                    WasIdempotent = true,
                };
            }

            // C-027: Append-only INSERT within a transaction — no UPDATE or DELETE
            // C-073: constitutional obligation — atomic write before returning
            await using var transaction = await _db.Database.BeginTransactionAsync(
                context.CancellationToken);

            var record = new EvidenceRecord
            {
                Id = Guid.NewGuid(),
                IdempotencyKey = request.IdempotencyKey,
                TenantId = tenantId,
                EvidenceType = request.EvidenceType.ToString(),
                Description = request.Description,
                ConstitutionalBasis = request.ConstitutionalBasis,
                PayloadJson = string.IsNullOrWhiteSpace(request.PayloadJson)
                    ? null
                    : request.PayloadJson,
                ContractId = string.IsNullOrWhiteSpace(request.ContractId)
                    ? null
                    : request.ContractId,
                SessionId = string.IsNullOrWhiteSpace(request.SessionId)
                    ? null
                    : request.SessionId,
                RelatedEvidenceIds = request.RelatedEvidenceIds.Count > 0
                    ? request.RelatedEvidenceIds.ToArray()
                    : null,
                EventTimestamp = request.EventTimestamp is not null
                    ? request.EventTimestamp.ToDateTimeOffset()
                    : DateTimeOffset.UtcNow,
                LedgerTimestamp = DateTimeOffset.UtcNow,
            };

            _db.EvidenceRecords.Add(record);
            await _db.SaveChangesAsync(context.CancellationToken);
            await transaction.CommitAsync(context.CancellationToken);

            activity?.SetTag("evidence.id", record.Id.ToString());
            activity?.SetTag("idempotent.hit", false);

            _logger.LogInformation(
                "RecordEvidence committed. EvidenceId={EvidenceId} TenantId={TenantId} EvidenceType={EvidenceType}",
                record.Id, tenantId, record.EvidenceType);

            return new RecordEvidenceResponse
            {
                EvidenceId = record.Id.ToString(),
                LedgerTimestamp = Timestamp.FromDateTimeOffset(record.LedgerTimestamp),
                WasIdempotent = false,
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            // C-023: If write fails → INTERNAL error → caller must not return success
            _logger.LogError(ex,
                "RecordEvidence failed. IdempotencyKey={IdempotencyKey} TenantId={TenantId}",
                request.IdempotencyKey, tenantId);

            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);

            throw new RpcException(new Status(StatusCode.Internal,
                "Evidence write failed — caller must treat its own operation as failed (C-023)"));
        }
    }

    // ─── ValidateAction ──────────────────────────────────────────────────────

    /// <summary>
    /// PAAS Boundary Validator — validates whether a proposed action falls within the
    /// current Decision Space. Returns ALLOW, DENY, or ESCALATE.
    /// Latency target: &lt;40ms (AD-005 hot path).
    /// </summary>
    // C-073: constitutional obligation — Decision Space boundary enforcement (C-003)
    public override Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest request,
        ServerCallContext context)
    {
        using var activity = ActivitySource.StartActivity("constitutional.action.validate");
        activity?.SetTag("constitutional.basis", "C-003,AD-005");
        activity?.SetTag("action.type", request.ActionType);
        activity?.SetTag("session.id", request.SessionId);

        var tenantId = ExtractTenantId(context);
        activity?.SetTag("tenant.id", tenantId);

        _logger.LogInformation(
            "ValidateAction called. SessionId={SessionId} ActionType={ActionType} TenantId={TenantId}",
            request.SessionId, request.ActionType, tenantId);

        // DESIGN_QUESTION: Decision Space loading strategy — cache-first with DB fallback?
        // The spec says "Load Decision Space (from cache warmed at session start, or from DB on miss)".
        // Cache implementation (IMemoryCache vs IDistributedCache) needs EA decision before Sprint 005.

        // Stub: return ALLOW with constitutional basis for scaffold validation
        var response = new ValidateActionResponse
        {
            Decision = ActionDecision.Allow,
            Reason = "Stub implementation — Decision Space validation not yet implemented",
            ConstitutionalBasis = "C-003,AD-005",
            ViolatedConstraint = string.Empty,
            EscalationPrompt = string.Empty,
        };

        return Task.FromResult(response);
    }

    // ─── GrantAuthorityLicense ───────────────────────────────────────────────

    /// <summary>
    /// Authority License Manager (expansion) — records an authority expansion event.
    /// Validates that justifying evidence IDs are provided (C-023).
    /// </summary>
    // C-073: constitutional obligation — authority expansion must be evidence-justified (C-003, C-023)
    public override async Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest request,
        ServerCallContext context)
    {
        using var activity = ActivitySource.StartActivity("constitutional.authority.grant");
        activity?.SetTag("constitutional.basis", "C-003,C-023");
        activity?.SetTag("contract.id", request.ContractId);
        activity?.SetTag("professional.id", request.ProfessionalId);

        var tenantId = ExtractTenantId(context);
        activity?.SetTag("tenant.id", tenantId);

        _logger.LogInformation(
            "GrantAuthorityLicense called. ContractId={ContractId} ProfessionalId={ProfessionalId} TenantId={TenantId}",
            request.ContractId, request.ProfessionalId, tenantId);

        // C-023: Evidence IDs must be provided to justify expansion
        if (request.JustifyingEvidenceIds.Count == 0)
        {
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                "justifying_evidence_ids must be non-empty — authority expansion requires evidence (C-023)"));
        }

        if (string.IsNullOrWhiteSpace(request.IdempotencyKey))
        {
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                "idempotency_key is required"));
        }

        try
        {
            // Check idempotency
            var existing = await _db.EvidenceRecords
                .AsNoTracking()
                .FirstOrDefaultAsync(
                    e => e.IdempotencyKey == request.IdempotencyKey && e.TenantId == tenantId,
                    context.CancellationToken);

            if (existing is not null)
            {
                return new GrantAuthorityResponse
                {
                    EvidenceId = existing.Id.ToString(),
                    GrantedAt = Timestamp.FromDateTimeOffset(existing.LedgerTimestamp),
                };
            }

            await using var transaction = await _db.Database.BeginTransactionAsync(
                context.CancellationToken);

            var record = new EvidenceRecord
            {
                Id = Guid.NewGuid(),
                IdempotencyKey = request.IdempotencyKey,
                TenantId = tenantId,
                EvidenceType = EvidenceType.AuthorityGrant.ToString(),
                Description = request.Justification,
                ConstitutionalBasis = request.ConstitutionalBasis,
                ContractId = request.ContractId,
                RelatedEvidenceIds = request.JustifyingEvidenceIds.ToArray(),
                EventTimestamp = DateTimeOffset.UtcNow,
                LedgerTimestamp = DateTimeOffset.UtcNow,
            };

            _db.EvidenceRecords.Add(record);
            await _db.SaveChangesAsync(context.CancellationToken);
            await transaction.CommitAsync(context.CancellationToken);

            activity?.SetTag("evidence.id", record.Id.ToString());

            _logger.LogInformation(
                "GrantAuthorityLicense committed. EvidenceId={EvidenceId} ContractId={ContractId}",
                record.Id, request.ContractId);

            return new GrantAuthorityResponse
            {
                EvidenceId = record.Id.ToString(),
                GrantedAt = Timestamp.FromDateTimeOffset(record.LedgerTimestamp),
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "GrantAuthorityLicense failed. ContractId={ContractId} TenantId={TenantId}",
                request.ContractId, tenantId);

            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);

            throw new RpcException(new Status(StatusCode.Internal,
                "Authority grant write failed (C-023)"));
        }
    }

    // ─── RevokeAuthorityLicense ──────────────────────────────────────────────

    /// <summary>
    /// Authority License Manager (restriction) — records an authority restriction event.
    /// </summary>
    // C-073: constitutional obligation — authority restriction must be recorded (C-003, C-023)
    public override async Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest request,
        ServerCallContext context)
    {
        using var activity = ActivitySource.StartActivity("constitutional.authority.revoke");
        activity?.SetTag("constitutional.basis", "C-003,C-023");
        activity?.SetTag("contract.id", request.ContractId);
        activity?.SetTag("professional.id", request.ProfessionalId);

        var tenantId = ExtractTenantId(context);
        activity?.SetTag("tenant.id", tenantId);

        _logger.LogInformation(
            "RevokeAuthorityLicense called. ContractId={ContractId} ProfessionalId={ProfessionalId} TenantId={TenantId}",
            request.ContractId, request.ProfessionalId, tenantId);

        if (string.IsNullOrWhiteSpace(request.IdempotencyKey))
        {
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                "idempotency_key is required"));
        }

        try
        {
            var existing = await _db.EvidenceRecords
                .AsNoTracking()
                .FirstOrDefaultAsync(
                    e => e.IdempotencyKey == request.IdempotencyKey && e.TenantId == tenantId,
                    context.CancellationToken);

            if (existing is not null)
            {
                return new RevokeAuthorityResponse
                {
                    EvidenceId = existing.Id.ToString(),
                    RevokedAt = Timestamp.FromDateTimeOffset(existing.LedgerTimestamp),
                };
            }

            await using var transaction = await _db.Database.BeginTransactionAsync(
                context.CancellationToken);

            var record = new EvidenceRecord
            {
                Id = Guid.NewGuid(),
                IdempotencyKey = request.IdempotencyKey,
                TenantId = tenantId,
                EvidenceType = EvidenceType.AuthorityRevoke.ToString(),
                Description = request.Reason,
                ConstitutionalBasis = request.ConstitutionalBasis,
                ContractId = request.ContractId,
                EventTimestamp = DateTimeOffset.UtcNow,
                LedgerTimestamp = DateTimeOffset.UtcNow,
            };

            _db.EvidenceRecords.Add(record);
            await _db.SaveChangesAsync(context.CancellationToken);
            await transaction.CommitAsync(context.CancellationToken);

            activity?.SetTag("evidence.id", record.Id.ToString());

            _logger.LogInformation(
                "RevokeAuthorityLicense committed. EvidenceId={EvidenceId} ContractId={ContractId}",
                record.Id, request.ContractId);

            return new RevokeAuthorityResponse
            {
                EvidenceId = record.Id.ToString(),
                RevokedAt = Timestamp.FromDateTimeOffset(record.LedgerTimestamp),
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "RevokeAuthorityLicense failed. ContractId={ContractId} TenantId={TenantId}",
                request.ContractId, tenantId);

            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);

            throw new RpcException(new Status(StatusCode.Internal,
                "Authority revocation write failed (C-023)"));
        }
    }

    // ─── EvaluatePolicy ──────────────────────────────────────────────────────

    /// <summary>
    /// Policy Evaluator — general-purpose constitutional policy evaluation.
    /// Returns a decision with the constitutional basis string required for audit records (AD-008).
    /// </summary>
    // C-073: constitutional obligation — every permission decision must name its constitutional basis (AD-008)
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest request,
        ServerCallContext context)
    {
        using var activity = ActivitySource.StartActivity("constitutional.policy.evaluate");
        activity?.SetTag("constitutional.basis", "AD-008");
        activity?.SetTag("policy.set", request.PolicySet);
        activity?.SetTag("subject.id", request.SubjectId);
        activity?.SetTag("resource", request.Resource);
        activity?.SetTag("action", request.Action);

        var tenantId = ExtractTenantId(context);
        activity?.SetTag("tenant.id", tenantId);

        _logger.LogInformation(
            "EvaluatePolicy called. PolicySet={PolicySet} SubjectId={SubjectId} Action={Action} TenantId={TenantId}",
            request.PolicySet, request.SubjectId, request.Action, tenantId);

        // DESIGN_QUESTION: Policy rule storage — are rules stored in DB, config files, or a policy engine (OPA)?
        // EA decision needed before Sprint 005 policy implementation.

        // Stub: return PERMIT with constitutional basis for scaffold validation
        var response = new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit,
            ConstitutionalBasis = "AD-008",
            Explanation = "Stub implementation — policy rule evaluation not yet implemented",
        };

        return Task.FromResult(response);
    }

    // ─── TriggerEmergencyStop ────────────────────────────────────────────────

    /// <summary>
    /// Emergency Stop Handler — records the stop event in the Constitutional Audit Ledger
    /// and signals the affected Professional Runtime workflow to halt.
    /// Latency target: &lt;100ms (AD-001: 250ms total; 50ms network; 100ms here).
    /// </summary>
    // C-073: constitutional obligation — Emergency Stop is a Constitutional Floor (C-013, AD-001)
    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest request,
        ServerCallContext context)
    {
        // C-073: OTel span — Emergency Stop is on the critical latency budget
        using var activity = ActivitySource.StartActivity("constitutional.emergency.stop");
        activity?.SetTag("constitutional.basis", "C-013,AD-001");
        activity?.SetTag("session.id", request.SessionId);
        activity?.SetTag("contract.id", request.ContractId);
        activity?.SetTag("triggered.by", request.TriggeredBy);

        var tenantId = ExtractTenantId(context);
        activity?.SetTag("tenant.id", tenantId);

        _logger.LogWarning(
            "TriggerEmergencyStop called. SessionId={SessionId} ContractId={ContractId} TriggeredBy={TriggeredBy} TenantId={TenantId}",
            request.SessionId, request.ContractId, request.TriggeredBy, tenantId);

        if (string.IsNullOrWhiteSpace(request.IdempotencyKey))
        {
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                "idempotency_key is required"));
        }

        try
        {
            // Check idempotency
            var existing = await _db.EvidenceRecords
                .AsNoTracking()
                .FirstOrDefaultAsync(
                    e => e.IdempotencyKey == request.IdempotencyKey && e.TenantId == tenantId,
                    context.CancellationToken);

            if (existing is not null)
            {
                _logger.LogInformation(
                    "TriggerEmergencyStop idempotent hit. EvidenceId={EvidenceId}", existing.Id);

                return new EmergencyStopResponse
                {
                    EvidenceId = existing.Id.ToString(),
                    StoppedAt = Timestamp.FromDateTimeOffset(existing.LedgerTimestamp),
                    WorkflowSignalSent = false, // Cannot confirm signal on idempotent replay
                };
            }

            // C-013: DB write MUST complete before returning — within latency budget
            await using var transaction = await _db.Database.BeginTransactionAsync(
                context.CancellationToken);

            var record = new EvidenceRecord
            {
                Id = Guid.NewGuid(),
                IdempotencyKey = request.IdempotencyKey,
                TenantId = tenantId,
                EvidenceType = EvidenceType.EmergencyStop.ToString(),
                Description = request.Reason,
                ConstitutionalBasis = string.IsNullOrWhiteSpace(request.ConstitutionalBasis)
                    ? "C-013,AD-001"
                    : request.ConstitutionalBasis,
                ContractId = request.ContractId,
                SessionId = request.SessionId,
                EventTimestamp = DateTimeOffset.UtcNow,
                LedgerTimestamp = DateTimeOffset.UtcNow,
            };

            _db.EvidenceRecords.Add(record);
            await _db.SaveChangesAsync(context.CancellationToken);
            await transaction.CommitAsync(context.CancellationToken);

            activity?.SetTag("evidence.id", record.Id.ToString());

            _logger.LogWarning(
                "TriggerEmergencyStop committed. EvidenceId={EvidenceId} SessionId={SessionId}",
                record.Id, request.SessionId);

            // DESIGN_QUESTION: Temporal signal dispatch — should this use a fire-and-forget pattern
            // or await the signal acknowledgement? AD-001 requires ≤100ms for this RPC.
            // Temporal client integration is deferred to WC012-03 (Emergency Stop Handler implementation).
            var workflowSignalSent = false;

            _logger.LogWarning(
                "TriggerEmergencyStop: Temporal workflow signal NOT YET IMPLEMENTED. SessionId={SessionId}",
                request.SessionId);

            return new EmergencyStopResponse
            {
                EvidenceId = record.Id.ToString(),
                StoppedAt = Timestamp.FromDateTimeOffset(record.LedgerTimestamp),
                WorkflowSignalSent = workflowSignalSent,
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "TriggerEmergencyStop failed. SessionId={SessionId} TenantId={TenantId}",
                request.SessionId, tenantId);

            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);

            throw new RpcException(new Status(StatusCode.Internal,
                "Emergency stop write failed — session may not be halted (C-013)"));
        }
    }
}