// Implements: architecture/reference/components/constitutional-engine.md §1 Evidence First Enforcer
// constitutional_basis: C-007, C-023, C-027, C-059, C-085
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Services;
using Waooaw.ConstitutionalEngine.Tests.Evaluators;
using Google.Protobuf.WellKnownTypes;
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using System;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;

namespace Waooaw.ConstitutionalEngine.Services;

// Constitutional basis: C-023 (Evidence First), C-007/C-027 (append-only ledger), C-085 (idempotency)
// Purpose: gRPC service implementation — RecordEvidence writes to constitutional.audit_records
//          before returning. Caller MUST NOT return success until this RPC returns OK.
// ADR reference: ADR-001 (gRPC transport), ADR-002 (Evidence First enforcement)
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    // C-001: Emergency Stop SLA — 250 ms end-to-end
    private const int EmergencyStopSlaMs = 250;

    // ADR-001: ValidateAction hot-path latency budget — 40 ms
    private const int ValidateActionSlaMs = 40;

    private readonly EvaluatorRegistry _evaluatorRegistry;
    private readonly ConstitutionalDbContext _db;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    // All-positional constructor — no named arguments (CS1744 prevention)
    public ConstitutionalEngineService(
        EvaluatorRegistry evaluatorRegistry,
        ConstitutionalDbContext db,
        ILogger<ConstitutionalEngineService> logger)
    {
        _evaluatorRegistry = evaluatorRegistry;
        _db = db;
        _logger = logger;
    }

    // ── RecordEvidence ─────────────────────────────────────────────────────────
    // C-023: write evidence BEFORE returning success.
    // C-027: INSERT only — no UPDATE or DELETE ever issued on this table.
    // C-085: idempotency — return existing record_id if ActionInstanceId already written.
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req,
        ServerCallContext context)
    {
        try
        {
            // Tenant isolation: x-tenant-id from gRPC metadata (never from request body)
            var tenantIdRaw = context.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;
            if (string.IsNullOrWhiteSpace(tenantIdRaw))
            {
                throw new RpcException(
                    new Status(StatusCode.Unauthenticated, "x-tenant-id metadata header is required"));
            }

            if (!Guid.TryParse(tenantIdRaw, out var tenantGuid))
            {
                throw new RpcException(
                    new Status(StatusCode.Unauthenticated,
                        "x-tenant-id must be a valid UUID in canonical format"));
            }

            if (string.IsNullOrWhiteSpace(req.ConstitutionalBasis))
            {
                throw new RpcException(
                    new Status(StatusCode.InvalidArgument,
                        "constitutional_basis must not be empty (AD-008)"));
            }

            // C-085: Idempotency — check for existing record by (IdempotencyKey, TenantId)
            var existing = await _db.Set<EvidenceRecord>()
                .AsNoTracking()
                .FirstOrDefaultAsync(
                    e => e.IdempotencyKey == req.ActionInstanceId && e.TenantId == tenantGuid,
                    context.CancellationToken);

            if (existing is not null)
            {
                _logger.LogInformation(
                    "RecordEvidence idempotent hit: returning existing record {RecordId} " +
                    "for key {IdempotencyKey} tenant {TenantId}",
                    existing.Id, req.ActionInstanceId, tenantGuid);

                return new RecordEvidenceResponse
                {
                    EvidenceRecordId = existing.Id.ToString(),
                    RecordedAt = Timestamp.FromDateTimeOffset(existing.RecordedAt)
                };
            }

            // C-023 / C-027: Append-only INSERT — no UPDATE or DELETE ever
            var record = new EvidenceRecord
            {
                Id = Guid.NewGuid(),
                IdempotencyKey = req.ActionInstanceId,
                TenantId = tenantGuid,
                EvidenceType = req.ActionType,
                Summary = BuildSummary(req),
                PayloadJson = JsonSerializer.Serialize(req),
                RecordedAt = DateTimeOffset.UtcNow
            };

            // C-023: write within a DB transaction — if this fails the caller must fail
            await using var tx = await _db.Database.BeginTransactionAsync(context.CancellationToken);
            try
            {
                await _db.Set<EvidenceRecord>().AddAsync(record, context.CancellationToken);
                await _db.SaveChangesAsync(context.CancellationToken);
                await tx.CommitAsync(context.CancellationToken);
            }
            catch (Exception dbEx)
            {
                await tx.RollbackAsync(context.CancellationToken);
                _logger.LogError(dbEx,
                    "RecordEvidence DB transaction failed for ActionInstanceId={ActionInstanceId} " +
                    "Tenant={TenantId}",
                    req.ActionInstanceId, tenantGuid);
                throw new RpcException(
                    new Status(StatusCode.Internal,
                        $"Constitutional Audit Ledger write failed: {dbEx.Message}"));
            }

            _logger.LogInformation(
                "RecordEvidence: wrote record {RecordId} ActionType={ActionType} " +
                "State={State} TenantId={TenantId}",
                record.Id, req.ActionType, req.State, tenantGuid);

            return new RecordEvidenceResponse
            {
                EvidenceRecordId = record.Id.ToString(),
                RecordedAt = Timestamp.FromDateTimeOffset(record.RecordedAt)
            };
        }
        catch (RpcException)
        {
            // Already an RpcException — rethrow without wrapping
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "RecordEvidence failed: ActionInstanceId={ActionInstanceId}",
                req.ActionInstanceId);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ── ValidateAction ─────────────────────────────────────────────────────────
    // C-003: validates proposed action is within Decision Space.
    // ADR-001: target latency < 40 ms (ValidateActionSlaMs).
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest request,
        ServerCallContext context)
    {
        try
        {
            var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;
            var ctx = EvaluationContext.FromRequest(request, tenantId);

            var results = await _evaluatorRegistry.EvaluateAllAsync(ctx, context.CancellationToken);

            // Aggregation: Deny takes precedence, then Escalate, then Allow
            var deny = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Deny);
            if (deny is not null)
            {
                _logger.LogWarning(
                    "ValidateAction DENY: ContractId={ContractId} ActionType={ActionType} " +
                    "ClaimId={ClaimId} Reason={Reason}",
                    request.ContractId, request.ActionType, deny.ClaimId, deny.Reason);

                return new ValidateActionResponse
                {
                    Decision = ValidationDecision.ValidationDecisionDeny,
                    ConstitutionalBasis = deny.ClaimId,
                    Reason = deny.Reason
                };
            }

            var escalate = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Escalate);
            if (escalate is not null)
            {
                _logger.LogInformation(
                    "ValidateAction ESCALATE: ContractId={ContractId} ActionType={ActionType} " +
                    "ClaimId={ClaimId} Reason={Reason}",
                    request.ContractId, request.ActionType, escalate.ClaimId, escalate.Reason);

                return new ValidateActionResponse
                {
                    Decision = ValidationDecision.ValidationDecisionEscalate,
                    ConstitutionalBasis = escalate.ClaimId,
                    Reason = escalate.Reason
                };
            }

            var allow = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Allow);
            return new ValidateActionResponse
            {
                Decision = ValidationDecision.ValidationDecisionAllow,
                ConstitutionalBasis = allow?.ClaimId ?? "C-003",
                Reason = allow?.Reason ?? "Action is within Decision Space"
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "ValidateAction failed: ContractId={ContractId} ActionType={ActionType}",
                request.ContractId, request.ActionType);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ── GrantAuthorityLicense ──────────────────────────────────────────────────
    // C-003: authority expansion — caller must supply evidence IDs.
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req,
        ServerCallContext ctx)
    {
        try
        {
            _logger.LogWarning(
                "GrantAuthorityLicense called for ContractId={ContractId} — not yet implemented",
                req.ContractId);
            throw new RpcException(
                new Status(StatusCode.Unimplemented, "GrantAuthorityLicense not yet implemented"));
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "GrantAuthorityLicense failed: ContractId={ContractId}", req.ContractId);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ── RevokeAuthorityLicense ─────────────────────────────────────────────────
    // C-003: authority restriction.
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req,
        ServerCallContext ctx)
    {
        try
        {
            _logger.LogWarning(
                "RevokeAuthorityLicense called for ContractId={ContractId} — not yet implemented",
                req.ContractId);
            throw new RpcException(
                new Status(StatusCode.Unimplemented, "RevokeAuthorityLicense not yet implemented"));
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "RevokeAuthorityLicense failed: ContractId={ContractId}", req.ContractId);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ── EvaluatePolicy ─────────────────────────────────────────────────────────
    // AD-008: every permission decision must name its constitutional basis.
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req,
        ServerCallContext ctx)
    {
        try
        {
            _logger.LogWarning(
                "EvaluatePolicy called for ContractId={ContractId} — not yet implemented",
                req.ContractId);
            throw new RpcException(
                new Status(StatusCode.Unimplemented, "EvaluatePolicy not yet implemented"));
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "EvaluatePolicy failed: ContractId={ContractId}", req.ContractId);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ── TriggerEmergencyStop ───────────────────────────────────────────────────
    // C-013: Emergency Override — constitutional floor. Target < 100 ms (AD-001).
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req,
        ServerCallContext ctx)
    {
        try
        {
            _logger.LogCritical(
                "TriggerEmergencyStop called for ContractId={ContractId} StoppedBy={StoppedBy} " +
                "— not yet implemented (SLA={SlaMs}ms)",
                req.ContractId, req.StoppedBy, EmergencyStopSlaMs);
            throw new RpcException(
                new Status(StatusCode.Unimplemented, "TriggerEmergencyStop not yet implemented"));
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "TriggerEmergencyStop failed: ContractId={ContractId}", req.ContractId);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ── Private helpers ────────────────────────────────────────────────────────

    private static string BuildSummary(RecordEvidenceRequest req) =>
        $"ActionType={req.ActionType} | State={req.State} | Contract={req.ContractId} " +
        $"| Professional={req.ProfessionalId} | Basis={req.ConstitutionalBasis}";
}