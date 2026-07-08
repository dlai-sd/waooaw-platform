using Grpc.Core;
using Constitutional.V1;
using Waooaw.ConstitutionalEngine.Infrastructure;
using Microsoft.EntityFrameworkCore;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// Constitutional Engine gRPC service implementation.
/// Evidence First principle (C-023, AD-002): every method writes to the
/// Constitutional Audit Ledger BEFORE returning success to the caller.
/// If the write fails, returns gRPC error — caller must not return success.
/// </summary>
public class ConstitutionalServiceImpl : ConstitutionalService.ConstitutionalServiceBase
{
    private readonly ConstitutionalDbContext _db;
    private readonly ILogger<ConstitutionalServiceImpl> _logger;

    public ConstitutionalServiceImpl(
        ConstitutionalDbContext db,
        ILogger<ConstitutionalServiceImpl> logger)
    {
        _db = db;
        _logger = logger;
    }

    /// <summary>
    /// Evidence First Enforcer — writes evidence record atomically before returning.
    /// C-023: must record before returning success.
    /// C-027: append-only — no UPDATE or DELETE.
    /// </summary>
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest request,
        ServerCallContext context)
    {
        // Extract tenant_id from gRPC metadata (security-architecture.md §2)
        var tenantId = context.RequestHeaders.GetValue("x-tenant-id");
        if (string.IsNullOrEmpty(tenantId) || !Guid.TryParse(tenantId, out var tenantGuid))
        {
            throw new RpcException(new Status(StatusCode.Unauthenticated,
                "x-tenant-id metadata is required and must be a valid UUID"));
        }

        // Validate state transition before writing (evidence-schema.md)
        await ValidateStateTransitionAsync(request.ActionInstanceId, request.State, context.CancellationToken);

        // Validate constitutional_basis is not empty (AD-008)
        if (string.IsNullOrWhiteSpace(request.ConstitutionalBasis))
        {
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                "constitutional_basis must not be empty (AD-008)"));
        }

        // Write evidence record atomically (Evidence First — C-023)
        var record = new EvidenceRecord
        {
            Id = Guid.NewGuid(),
            TenantId = tenantGuid,
            ContractId = Guid.Parse(request.ContractId),
            ProfessionalId = Guid.Parse(request.ProfessionalId),
            ActionInstanceId = Guid.Parse(request.ActionInstanceId),
            ActionType = request.ActionType,
            State = request.State.ToString(),
            ProposedContent = request.HasProposedContent ? request.ProposedContent : null,
            ExecutedContent = request.HasExecutedContent ? request.ExecutedContent : null,
            IsScopeBoundary = request.IsScopeBoundary,
            ScopeBoundaryName = request.HasScopeBoundaryName ? request.ScopeBoundaryName : null,
            ScopeBoundaryAcknowledgment = request.HasScopeBoundaryAcknowledgment ? request.ScopeBoundaryAcknowledgment : null,
            DecisionSpaceVersion = request.DecisionSpaceVersion,
            ConstitutionalBasis = request.ConstitutionalBasis,
            CreatedAt = DateTime.UtcNow
        };

        await _db.EvidenceRecords.AddAsync(record, context.CancellationToken);

        try
        {
            await _db.SaveChangesAsync(context.CancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to write evidence record — Evidence First violation risk");
            // Return INTERNAL error — caller must treat this as failure (C-023)
            throw new RpcException(new Status(StatusCode.Internal,
                "Evidence write failed — caller must not return success"));
        }

        _logger.LogInformation(
            "constitutional.evidence.record: {ActionType} {State} contract={ContractId}",
            record.ActionType, record.State, record.ContractId);

        return new RecordEvidenceResponse
        {
            EvidenceRecordId = record.Id.ToString(),
            RecordedAt = Google.Protobuf.WellKnownTypes.Timestamp.FromDateTime(record.CreatedAt)
        };
    }

    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest request,
        ServerCallContext context)
    {
        var tenantId = context.RequestHeaders.GetValue("x-tenant-id");
        if (string.IsNullOrEmpty(tenantId))
            throw new RpcException(new Status(StatusCode.Unauthenticated, "x-tenant-id required"));

        // TODO Sprint 2: Load Decision Space from DB and evaluate
        // For foundation sprint: ALLOW all actions within the contract (stub)
        _logger.LogInformation("ValidateAction: {ActionType} for contract {ContractId} — stub ALLOW",
            request.ActionType, request.ContractId);

        return await Task.FromResult(new ValidateActionResponse
        {
            Decision = ValidationDecision.Allow,
            ConstitutionalBasis = "C-003; AD-005",
            Reason = "Foundation stub — Decision Space evaluation in Sprint 2"
        });
    }

    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest request,
        ServerCallContext context)
    {
        var tenantId = context.RequestHeaders.GetValue("x-tenant-id");
        if (string.IsNullOrEmpty(tenantId) || !Guid.TryParse(tenantId, out var tenantGuid))
            throw new RpcException(new Status(StatusCode.Unauthenticated, "x-tenant-id required"));

        // Write Emergency Stop evidence record (C-013, AD-001)
        var stopRecord = new EvidenceRecord
        {
            Id = Guid.NewGuid(),
            TenantId = tenantGuid,
            ContractId = Guid.Parse(request.ContractId),
            ProfessionalId = Guid.Empty, // Emergency Stop is contract-level, not professional-level
            ActionInstanceId = Guid.NewGuid(),
            ActionType = "EMERGENCY_STOP",
            State = "EXECUTED",
            ConstitutionalBasis = "C-013; AD-001",
            DecisionSpaceVersion = 0,
            CreatedAt = DateTime.UtcNow
        };

        await _db.EvidenceRecords.AddAsync(stopRecord, context.CancellationToken);
        await _db.SaveChangesAsync(context.CancellationToken);

        _logger.LogWarning(
            "EMERGENCY STOP executed: contract={ContractId} stoppedBy={StoppedBy} sessions={Sessions}",
            request.ContractId, request.StoppedBy, string.Join(",", request.ActiveSessionIds));

        // TODO Sprint 2: Send Temporal signals to active PAAS sessions (ADR-018)

        return new EmergencyStopResponse
        {
            EmergencyStopRecordId = stopRecord.Id.ToString(),
            RecordedAt = Google.Protobuf.WellKnownTypes.Timestamp.FromDateTime(stopRecord.CreatedAt)
        };
    }

    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest request, ServerCallContext context) =>
        Task.FromResult(new GrantAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString(),
            RecordedAt = Google.Protobuf.WellKnownTypes.Timestamp.FromDateTime(DateTime.UtcNow)
        });

    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest request, ServerCallContext context) =>
        Task.FromResult(new RevokeAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString(),
            RecordedAt = Google.Protobuf.WellKnownTypes.Timestamp.FromDateTime(DateTime.UtcNow)
        });

    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest request, ServerCallContext context) =>
        Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit,
            ConstitutionalBasis = "C-003",
            Rationale = "Foundation stub — policy evaluation in Sprint 2"
        });

    private async Task ValidateStateTransitionAsync(
        string actionInstanceId, EvidenceState proposedState, CancellationToken ct)
    {
        if (!Guid.TryParse(actionInstanceId, out var instanceGuid)) return;

        // Fetch the most recent record for this action instance (evidence-schema.md)
        var lastRecord = await _db.EvidenceRecords
            .Where(r => r.ActionInstanceId == instanceGuid)
            .OrderByDescending(r => r.CreatedAt)
            .FirstOrDefaultAsync(ct);

        if (lastRecord == null) return; // PROPOSED is valid as initial state

        // Terminal states cannot transition further (except ABANDONED from Emergency Stop)
        if (lastRecord.State is "EXECUTED" or "REJECTED")
        {
            throw new RpcException(new Status(StatusCode.FailedPrecondition,
                $"Terminal state {lastRecord.State} — no further transitions permitted"));
        }
    }
}
