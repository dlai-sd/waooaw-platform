// Implements: architecture/reference/components/constitutional-engine.md §1 Evidence First Enforcer
// Constitutional basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//   C-007 (Append-only), C-027 (Append-only), C-085 (Idempotency), C-059 (Traceability)
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    private readonly EvaluatorRegistry _registry;
    private readonly ConstitutionalDbContext _db;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    public ConstitutionalEngineService(
        EvaluatorRegistry registry,
        ConstitutionalDbContext db,
        ILogger<ConstitutionalEngineService> logger)
    {
        _registry = registry;
        _db = db;
        _logger = logger;
    }

    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext context)
    {
        var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? "";
        var ctx = EvaluationContext.FromRequest(req, tenantId);
        var results = await _registry.EvaluateAllAsync(ctx, context.CancellationToken);

        var denied = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Deny);
        if (denied is not null)
        {
            _logger.LogWarning(
                "ValidateAction denied: ContractId={ContractId} Claim={ClaimId} Reason={Reason}",
                req.ContractId, denied.ClaimId, denied.Reason);

            return new ValidateActionResponse
            {
                Decision = ValidationDecision.Unspecified,
                Reason = denied.Reason,
                ConstitutionalBasis = denied.ClaimId
            };
        }

        var escalated = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Escalate);
        if (escalated is not null)
        {
            _logger.LogWarning(
                "ValidateAction escalated: ContractId={ContractId} Claim={ClaimId} Reason={Reason}",
                req.ContractId, escalated.ClaimId, escalated.Reason);

            return new ValidateActionResponse
            {
                Decision = ValidationDecision.Unspecified,
                Reason = escalated.Reason,
                ConstitutionalBasis = escalated.ClaimId
            };
        }

        _logger.LogInformation(
            "ValidateAction allowed: ContractId={ContractId} Claims={Claims}",
            req.ContractId, string.Join(",", results.Select(r => r.ClaimId)));

        return new ValidateActionResponse
        {
            Decision = ValidationDecision.Unspecified,
            Reason = "All constitutional claims passed.",
            ConstitutionalBasis = string.Join(",", results.Select(r => r.ClaimId))
        };
    }

    /// <summary>
    /// Records evidence into constitutional.audit_records.
    /// C-023: write to DB BEFORE returning success.
    /// C-085: idempotent — returns existing EvidenceRecordId if ActionInstanceId already written.
    /// C-007/C-027: append-only; no UPDATE or DELETE ever issued.
    /// </summary>
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext context)
    {
        var tenantIdStr = context.RequestHeaders.GetValue("x-tenant-id") ?? "";
        var tenantGuid = Guid.TryParse(tenantIdStr, out var tg) ? tg : Guid.Empty;

        // C-085: Idempotency — if this ActionInstanceId was already committed, return the
        // existing record id without inserting a duplicate row.
        var existing = await _db.Set<EvidenceRecord>()
            .FirstOrDefaultAsync(
                e => e.IdempotencyKey == req.ActionInstanceId && e.TenantId == tenantGuid,
                context.CancellationToken);

        if (existing is not null)
        {
            _logger.LogInformation(
                "RecordEvidence idempotency hit: ActionInstanceId={ActionInstanceId} ExistingId={ExistingId}",
                req.ActionInstanceId, existing.Id);

            return new RecordEvidenceResponse { EvidenceRecordId = existing.Id.ToString() };
        }

        // C-023: Evidence written BEFORE returning gRPC success response.
        // C-007/C-027: Only Add() is used — no Update(), Remove(), or raw SQL mutations.
        var payloadJson = System.Text.Json.JsonSerializer.Serialize(new
        {
            req.ContractId,
            req.ProfessionalId,
            req.ActionType,
            req.ProposedContent,
            req.ExecutedContent,
            req.IsScopeBoundary,
            req.ScopeBoundaryName,
            req.ScopeBoundaryAcknowledgment,
            req.DecisionSpaceVersion,
            req.ConstitutionalBasis
        });

        var record = new EvidenceRecord
        {
            Id                = Guid.NewGuid(),
            IdempotencyKey    = req.ActionInstanceId,
            TenantId          = tenantGuid,
            EvidenceType      = req.ActionType,
            Summary           = $"Contract={req.ContractId} ActionType={req.ActionType} Basis={req.ConstitutionalBasis}",
            PayloadJson       = payloadJson,
            RecordedAt        = DateTimeOffset.UtcNow
        };

        _db.Set<EvidenceRecord>().Add(record);
        await _db.SaveChangesAsync(context.CancellationToken);

        _logger.LogInformation(
            "Evidence recorded: Id={Id} ActionInstanceId={ActionInstanceId} TenantId={TenantId}",
            record.Id, req.ActionInstanceId, tenantGuid);

        return new RecordEvidenceResponse { EvidenceRecordId = record.Id.ToString() };
    }

    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext context)
    {
        _logger.LogInformation(
            "GrantAuthorityLicense: ContractId={ContractId} GrantedBy={GrantedBy}",
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
            "RevokeAuthorityLicense: ContractId={ContractId} RevokedBy={RevokedBy} Reason={Reason}",
            req.ContractId, req.RevokedBy, req.Reason);

        return Task.FromResult(new RevokeAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
    }

    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext context)
    {
        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit
        });
    }

    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext context)
    {
        _logger.LogCritical(
            "EMERGENCY STOP triggered: ContractId={ContractId} StoppedBy={StoppedBy} ActiveSessions={Count}",
            req.ContractId, req.StoppedBy, req.ActiveSessionIds.Count);

        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = Guid.NewGuid().ToString()
        };

        foreach (var sessionId in req.ActiveSessionIds)
        {
            response.AffectedSessions.Add(sessionId);
        }

        return Task.FromResult(response);
    }
}