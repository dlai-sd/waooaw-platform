// Implements: architecture/reference/components/constitutional-engine.md §1 Evidence First Enforcer
// constitutional_basis: C-007, C-023, C-027, C-059, C-085
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Services;
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Google.Protobuf.WellKnownTypes;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;

// Constitutional basis: C-023 (Evidence First), C-027 (append-only ledger),
// C-007 (no UPDATE/DELETE), C-059 (error handling), C-085 (idempotency)
// Purpose: gRPC service implementation — Evidence First Enforcer and PAAS Boundary Validator
// ADR reference: ADR-001 (gRPC), ADR-002 (Evidence First enforcement)

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// ConstitutionalEngineService — the constitutional backbone.
/// Implements all six RPCs defined in constitutional_service.proto.
/// C-023: evidence MUST be written before success is returned to any caller.
/// C-027: append-only ledger — no UPDATE or DELETE is ever issued on audit records.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    // C-001: Constitutional floor — Emergency Stop SLA
    private const int EmergencyStopSlaMs = 250;

    // ADR-001: ValidateAction latency budget
    private const int ValidateActionTargetMs = 40;

    private readonly EvaluatorRegistry _registry;
    private readonly ConstitutionalDbContext _db;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    // ⛔ CONSTRUCTOR RULE: all-positional args, no named args after positional (CS1744)
    public ConstitutionalEngineService(
        EvaluatorRegistry registry,
        ConstitutionalDbContext db,
        ILogger<ConstitutionalEngineService> logger)
    {
        _registry = registry ?? throw new ArgumentNullException(nameof(registry));
        _db = db ?? throw new ArgumentNullException(nameof(db));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    // ─── RecordEvidence ─────────────────────────────────────────────────────
    // C-023: write to constitutional.audit_records BEFORE returning OK.
    // C-085: check ActionInstanceId idempotency — return existing record_id if already written.
    // C-027: INSERT only — no UPDATE or DELETE ever issued.
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest request,
        ServerCallContext context)
    {
        var tenantId = ExtractTenantId(context);

        _logger.LogInformation(
            "RecordEvidence — contract={ContractId} action={ActionType} state={State} tenant={TenantId}",
            request.ContractId, request.ActionType, request.State, tenantId);

        // Validate required fields — C-023: constitutional_basis must not be empty
        if (string.IsNullOrWhiteSpace(request.ConstitutionalBasis))
        {
            throw new RpcException(new Status(
                StatusCode.InvalidArgument,
                "constitutional_basis must not be empty (C-023, AD-008)"));
        }

        if (string.IsNullOrWhiteSpace(request.ActionInstanceId))
        {
            throw new RpcException(new Status(
                StatusCode.InvalidArgument,
                "action_instance_id is required"));
        }

        try
        {
            // C-085: idempotency check — if already written, return existing record_id
            var idempotencyKey = BuildIdempotencyKey(request.ActionInstanceId, request.State, tenantId);
            var existing = await _db.Set<EvidenceRecord>()
                .AsNoTracking()
                .FirstOrDefaultAsync(
                    e => e.IdempotencyKey == idempotencyKey,
                    context.CancellationToken);

            if (existing is not null)
            {
                _logger.LogInformation(
                    "RecordEvidence — idempotent replay: existing record {RecordId} for key={IdempotencyKey}",
                    existing.Id, idempotencyKey);

                return new RecordEvidenceResponse
                {
                    EvidenceRecordId = existing.Id.ToString(),
                    RecordedAt = Timestamp.FromDateTimeOffset(existing.RecordedAt)
                };
            }

            // C-023: write atomically inside a transaction BEFORE returning
            // C-027: INSERT only — EF Core Add() never issues UPDATE/DELETE on this entity
            await using var tx = await _db.Database.BeginTransactionAsync(context.CancellationToken);

            try
            {
                var now = DateTimeOffset.UtcNow;
                var recordId = Guid.NewGuid();

                var payloadJson = BuildPayloadJson(request);

                var record = new EvidenceRecord
                {
                    Id = recordId,
                    IdempotencyKey = idempotencyKey,
                    TenantId = ParseTenantGuid(tenantId),
                    EvidenceType = $"{request.ActionType}:{request.State}",
                    Summary = BuildSummary(request),
                    PayloadJson = payloadJson,
                    RecordedAt = now
                };

                // C-007 / C-027: Add() is an INSERT; no SaveChanges() with tracking that could UPDATE
                await _db.Set<EvidenceRecord>().AddAsync(record, context.CancellationToken);
                await _db.SaveChangesAsync(context.CancellationToken);
                await tx.CommitAsync(context.CancellationToken);

                _logger.LogInformation(
                    "RecordEvidence — committed record {RecordId} for contract={ContractId} state={State}",
                    recordId, request.ContractId, request.State);

                return new RecordEvidenceResponse
                {
                    EvidenceRecordId = recordId.ToString(),
                    RecordedAt = Timestamp.FromDateTimeOffset(now)
                };
            }
            catch (Exception txEx)
            {
                await tx.RollbackAsync(CancellationToken.None);
                _logger.LogError(txEx,
                    "RecordEvidence — transaction rolled back for contract={ContractId} state={State}",
                    request.ContractId, request.State);
                throw new RpcException(new Status(StatusCode.Internal,
                    $"Evidence write failed — transaction rolled back: {txEx.Message}"));
            }
        }
        catch (RpcException)
        {
            throw; // propagate gRPC status codes unchanged
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "RecordEvidence — unhandled failure for contract={ContractId} action={ActionType}",
                request.ContractId, request.ActionType);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ─── ValidateAction ──────────────────────────────────────────────────────
    // C-003: validates proposed action against current Decision Space.
    // Uses EvaluationContext.FromRequest() — frozen API; never construct directly.
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest request,
        ServerCallContext context)
    {
        var tenantId = ExtractTenantId(context);

        _logger.LogInformation(
            "ValidateAction — contract={ContractId} action={ActionType} tenant={TenantId}",
            request.ContractId, request.ActionType, tenantId);

        try
        {
            // C-041: use EvaluationContext.FromRequest — frozen API; all parameters required
            var ctx = EvaluationContext.FromRequest(request, tenantId);

            var results = await _registry.EvaluateAllAsync(ctx, context.CancellationToken);

            // Aggregate: any Deny → Deny, any Escalate → Escalate, else Allow
            var decision = ValidationDecision.Allow;
            var reason = "All evaluators passed — action is within Decision Space";
            var constitutionalBasis = "C-003; C-041";

            foreach (var result in results)
            {
                if (result.Verdict == EvaluationVerdict.Deny)
                {
                    decision = ValidationDecision.Deny;
                    reason = result.Reason;
                    constitutionalBasis = result.ClaimId;
                    break; // first Deny wins
                }

                if (result.Verdict == EvaluationVerdict.Escalate && decision != ValidationDecision.Deny)
                {
                    decision = ValidationDecision.Escalate;
                    reason = result.Reason;
                    constitutionalBasis = result.ClaimId;
                }
            }

            if (decision == ValidationDecision.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction — DENY contract={ContractId} action={ActionType} reason={Reason}",
                    request.ContractId, request.ActionType, reason);
            }

            var response = new ValidateActionResponse
            {
                Decision = decision,
                ConstitutionalBasis = constitutionalBasis,
                Reason = reason
            };

            // Budget remaining — set if BudgetContext present and action was budget-evaluated
            if (request.BudgetContext is not null)
            {
                var remaining = request.BudgetContext.ApprovedMonthlyBudgetInrPaise
                    - request.BudgetContext.CurrentMonthSpendInrPaise
                    - (decision == ValidationDecision.Allow ? request.BudgetContext.ProposedSpendInrPaise : 0);
                response.BudgetRemainingInrPaise = remaining;
            }

            return response;
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "ValidateAction — unhandled failure for contract={ContractId} action={ActionType}",
                request.ContractId, request.ActionType);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ─── GrantAuthorityLicense ───────────────────────────────────────────────
    // C-003: authority expansion must be evidenced and recorded.
    public override async Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest request,
        ServerCallContext context)
    {
        var tenantId = ExtractTenantId(context);

        _logger.LogInformation(
            "GrantAuthorityLicense — contract={ContractId} newLevel={NewLevel} grantedBy={GrantedBy}",
            request.ContractId, request.NewAuthorityLevel, request.GrantedBy);

        if (request.EvidenceIds.Count == 0)
        {
            throw new RpcException(new Status(
                StatusCode.InvalidArgument,
                "At least one evidence_id is required to grant authority (C-003: authority earned through evidence)"));
        }

        if (string.IsNullOrWhiteSpace(request.ConstitutionalBasis))
        {
            throw new RpcException(new Status(
                StatusCode.InvalidArgument,
                "constitutional_basis must not be empty (AD-008)"));
        }

        try
        {
            await using var tx = await _db.Database.BeginTransactionAsync(context.CancellationToken);
            try
            {
                var now = DateTimeOffset.UtcNow;
                var licenseId = Guid.NewGuid();

                var payloadJson = System.Text.Json.JsonSerializer.Serialize(new
                {
                    contract_id = request.ContractId,
                    new_authority_level = request.NewAuthorityLevel,
                    granted_by = request.GrantedBy,
                    evidence_ids = request.EvidenceIds,
                    constitutional_basis = request.ConstitutionalBasis
                });

                var record = new EvidenceRecord
                {
                    Id = licenseId,
                    IdempotencyKey = $"GRANT:{request.ContractId}:{request.NewAuthorityLevel}:{request.GrantedBy}:{now.Ticks}",
                    TenantId = ParseTenantGuid(tenantId),
                    EvidenceType = "AUTHORITY_GRANT",
                    Summary = $"Authority expanded to level {request.NewAuthorityLevel} for contract {request.ContractId}",
                    PayloadJson = payloadJson,
                    RecordedAt = now
                };

                await _db.Set<EvidenceRecord>().AddAsync(record, context.CancellationToken);
                await _db.SaveChangesAsync(context.CancellationToken);
                await tx.CommitAsync(context.CancellationToken);

                _logger.LogInformation(
                    "GrantAuthorityLicense — committed license {LicenseId} for contract={ContractId}",
                    licenseId, request.ContractId);

                return new GrantAuthorityResponse
                {
                    LicenseId = licenseId.ToString(),
                    RecordedAt = Timestamp.FromDateTimeOffset(now)
                };
            }
            catch (Exception txEx)
            {
                await tx.RollbackAsync(CancellationToken.None);
                _logger.LogError(txEx,
                    "GrantAuthorityLicense — transaction rolled back for contract={ContractId}",
                    request.ContractId);
                throw new RpcException(new Status(StatusCode.Internal,
                    $"Authority grant write failed: {txEx.Message}"));
            }
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "GrantAuthorityLicense — unhandled failure for contract={ContractId}",
                request.ContractId);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ─── RevokeAuthorityLicense ──────────────────────────────────────────────
    // C-003: authority restriction must be recorded in the Constitutional Audit Ledger.
    public override async Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest request,
        ServerCallContext context)
    {
        var tenantId = ExtractTenantId(context);

        _logger.LogInformation(
            "RevokeAuthorityLicense — contract={ContractId} newLevel={NewLevel} revokedBy={RevokedBy}",
            request.ContractId, request.NewAuthorityLevel, request.RevokedBy);

        if (string.IsNullOrWhiteSpace(request.ConstitutionalBasis))
        {
            throw new RpcException(new Status(
                StatusCode.InvalidArgument,
                "constitutional_basis must not be empty (AD-008)"));
        }

        try
        {
            await using var tx = await _db.Database.BeginTransactionAsync(context.CancellationToken);
            try
            {
                var now = DateTimeOffset.UtcNow;
                var licenseId = Guid.NewGuid();

                var payloadJson = System.Text.Json.JsonSerializer.Serialize(new
                {
                    contract_id = request.ContractId,
                    new_authority_level = request.NewAuthorityLevel,
                    revoked_by = request.RevokedBy,
                    reason = request.Reason,
                    constitutional_basis = request.ConstitutionalBasis
                });

                var record = new EvidenceRecord
                {
                    Id = licenseId,
                    IdempotencyKey = $"REVOKE:{request.ContractId}:{request.NewAuthorityLevel}:{request.RevokedBy}:{now.Ticks}",
                    TenantId = ParseTenantGuid(tenantId),
                    EvidenceType = "AUTHORITY_REVOKE",
                    Summary = $"Authority restricted to level {request.NewAuthorityLevel} for contract {request.ContractId}: {request.Reason}",
                    PayloadJson = payloadJson,
                    RecordedAt = now
                };

                await _db.Set<EvidenceRecord>().AddAsync(record, context.CancellationToken);
                await _db.SaveChangesAsync(context.CancellationToken);
                await tx.CommitAsync(context.CancellationToken);

                _logger.LogInformation(
                    "RevokeAuthorityLicense — committed license {LicenseId} for contract={ContractId}",
                    licenseId, request.ContractId);

                return new RevokeAuthorityResponse
                {
                    LicenseId = licenseId.ToString(),
                    RecordedAt = Timestamp.FromDateTimeOffset(now)
                };
            }
            catch (Exception txEx)
            {
                await tx.RollbackAsync(CancellationToken.None);
                _logger.LogError(txEx,
                    "RevokeAuthorityLicense — transaction rolled back for contract={ContractId}",
                    request.ContractId);
                throw new RpcException(new Status(StatusCode.Internal,
                    $"Authority revoke write failed: {txEx.Message}"));
            }
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "RevokeAuthorityLicense — unhandled failure for contract={ContractId}",
                request.ContractId);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ─── EvaluatePolicy ──────────────────────────────────────────────────────
    // AD-008: every permission decision must name its constitutional basis.
    public override async Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest request,
        ServerCallContext context)
    {
        var tenantId = ExtractTenantId(context);

        _logger.LogInformation(
            "EvaluatePolicy — contract={ContractId} action={ActionType} tenant={TenantId}",
            request.ContractId, request.ActionType, tenantId);

        try
        {
            // Build EvaluationContext for policy evaluation.
            // EvaluationContext.FromRequest requires a ValidateActionRequest — build a synthetic one.
            var syntheticRequest = new ValidateActionRequest
            {
                ContractId = request.ContractId,
                ActionType = request.ActionType,
                ActionParameters = request.ActionContext,
                DecisionSpaceVersion = 0  // policy evaluation — no specific version required
            };

            var ctx = EvaluationContext.FromRequest(syntheticRequest, tenantId);
            var results = await _registry.EvaluateAllAsync(ctx, context.CancellationToken);

            var policyDecision = PolicyDecision.Permit;
            var constitutionalBasis = "C-003; AD-008";
            var rationale = "All constitutional evaluators permitted this action";

            foreach (var result in results)
            {
                if (result.Verdict == EvaluationVerdict.Deny)
                {
                    policyDecision = PolicyDecision.Deny;
                    constitutionalBasis = result.ClaimId;
                    rationale = result.Reason;
                    break;
                }

                if (result.Verdict == EvaluationVerdict.Escalate && policyDecision != PolicyDecision.Deny)
                {
                    policyDecision = PolicyDecision.Escalate;
                    constitutionalBasis = result.ClaimId;
                    rationale = result.Reason;
                }
            }

            _logger.LogInformation(
                "EvaluatePolicy — decision={Decision} contract={ContractId} action={ActionType}",
                policyDecision, request.ContractId, request.ActionType);

            return new EvaluatePolicyResponse
            {
                Decision = policyDecision,
                ConstitutionalBasis = constitutionalBasis,
                Rationale = rationale
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "EvaluatePolicy — unhandled failure for contract={ContractId} action={ActionType}",
                request.ContractId, request.ActionType);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ─── TriggerEmergencyStop ────────────────────────────────────────────────
    // C-013: Emergency Stop is a Constitutional Floor — must complete within latency budget.
    // AD-001: 250ms total; 50ms network; 100ms here.
    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest request,
        ServerCallContext context)
    {
        var tenantId = ExtractTenantId(context);

        _logger.LogWarning(
            "TriggerEmergencyStop — contract={ContractId} stoppedBy={StoppedBy} sessions={SessionCount} tenant={TenantId}",
            request.ContractId, request.StoppedBy, request.ActiveSessionIds.Count, tenantId);

        // C-013: Emergency Stop latency budget — use timeout to honour AD-001
        using var timeoutCts = new CancellationTokenSource(TimeSpan.FromMilliseconds(EmergencyStopSlaMs));
        using var combinedCts = CancellationTokenSource.CreateLinkedTokenSource(
            context.CancellationToken, timeoutCts.Token);

        try
        {
            await using var tx = await _db.Database.BeginTransactionAsync(combinedCts.Token);
            try
            {
                var now = DateTimeOffset.UtcNow;
                var stopRecordId = Guid.NewGuid();
                var affectedSessions = request.ActiveSessionIds.ToList();

                var payloadJson = System.Text.Json.JsonSerializer.Serialize(new
                {
                    contract_id = request.ContractId,
                    stopped_by = request.StoppedBy,
                    active_session_ids = affectedSessions,
                    triggered_at = now
                });

                var record = new EvidenceRecord
                {
                    Id = stopRecordId,
                    IdempotencyKey = $"EMERGENCY_STOP:{request.ContractId}:{request.StoppedBy}:{now.Ticks}",
                    TenantId = ParseTenantGuid(tenantId),
                    EvidenceType = "EMERGENCY_STOP",
                    Summary = $"Emergency Stop triggered by {request.StoppedBy} for contract {request.ContractId} — {affectedSessions.Count} session(s) halted",
                    PayloadJson = payloadJson,
                    RecordedAt = now
                };

                // C-023: write BEFORE returning — caller must not confirm halt until this returns OK
                await _db.Set<EvidenceRecord>().AddAsync(record, combinedCts.Token);
                await _db.SaveChangesAsync(combinedCts.Token);
                await tx.CommitAsync(combinedCts.Token);

                _logger.LogWarning(
                    "TriggerEmergencyStop — COMMITTED stop record {StopRecordId} for contract={ContractId} sessions={Sessions}",
                    stopRecordId, request.ContractId, string.Join(",", affectedSessions));

                var response = new EmergencyStopResponse
                {
                    EmergencyStopRecordId = $"EMERGENCY_STOP:{stopRecordId}",
                    RecordedAt = Timestamp.FromDateTimeOffset(now)
                };

                foreach (var sessionId in affectedSessions)
                {
                    response.AffectedSessions.Add(sessionId);
                }

                return response;
            }
            catch (Exception txEx)
            {
                await tx.RollbackAsync(CancellationToken.None);
                _logger.LogError(txEx,
                    "TriggerEmergencyStop — CRITICAL: transaction rolled back for contract={ContractId}. Emergency Stop NOT confirmed.",
                    request.ContractId);
                throw new RpcException(new Status(StatusCode.Internal,
                    $"Emergency Stop write failed — HALT NOT CONFIRMED: {txEx.Message}"));
            }
        }
        catch (OperationCanceledException) when (timeoutCts.IsCancellationRequested)
        {
            _logger.LogError(
                "TriggerEmergencyStop — TIMEOUT exceeded {SlaMs}ms for contract={ContractId}. SLA VIOLATION C-013/AD-001.",
                EmergencyStopSlaMs, request.ContractId);
            throw new RpcException(new Status(StatusCode.DeadlineExceeded,
                $"Emergency Stop exceeded {EmergencyStopSlaMs}ms SLA (C-013, AD-001)"));
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "TriggerEmergencyStop — unhandled failure for contract={ContractId}",
                request.ContractId);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ─── Private helpers ─────────────────────────────────────────────────────

    /// <summary>
    /// Extracts the tenant ID from gRPC metadata.
    /// Returns UNAUTHENTICATED if the header is absent or empty.
    /// </summary>
    private string ExtractTenantId(ServerCallContext context)
    {
        var tenantId = context.RequestHeaders.GetValue("x-tenant-id");
        if (string.IsNullOrWhiteSpace(tenantId))
        {
            throw new RpcException(new Status(
                StatusCode.Unauthenticated,
                "x-tenant-id metadata header is required (C-005: tenant isolation)"));
        }
        return tenantId;
    }

    /// <summary>
    /// Builds an idempotency key that is unique per action-instance + state + tenant.
    /// C-085: same key → same record returned; INSERT is never duplicated.
    /// </summary>
    private static string BuildIdempotencyKey(string actionInstanceId, EvidenceState state, string tenantId)
        => $"{tenantId}:{actionInstanceId}:{(int)state}";

    /// <summary>
    /// Serialises the full RecordEvidenceRequest as JSON for the PayloadJson column.
    /// C-027: the payload is immutable once stored.
    /// </summary>
    private static string BuildPayloadJson(RecordEvidenceRequest request)
        => System.Text.Json.JsonSerializer.Serialize(new
        {
            action_instance_id = request.ActionInstanceId,
            contract_id = request.ContractId,
            professional_id = request.ProfessionalId,
            action_type = request.ActionType,
            state = request.State.ToString(),
            proposed_content = request.HasProposedContent ? request.ProposedContent : null,
            executed_content = request.HasExecutedContent ? request.ExecutedContent : null,
            is_scope_boundary = request.IsScopeBoundary,
            scope_boundary_name = request.HasScopeBoundaryName ? request.ScopeBoundaryName : null,
            decision_space_version = request.DecisionSpaceVersion,
            constitutional_basis = request.ConstitutionalBasis
        });

    /// <summary>
    /// Builds a human-readable summary for the evidence record.
    /// </summary>
    private static string BuildSummary(RecordEvidenceRequest request)
        => $"{request.ActionType} [{request.State}] for contract {request.ContractId} — basis: {request.ConstitutionalBasis}";

    /// <summary>
    /// Parses the tenant ID string into a Guid, returning Guid.Empty if parsing fails.
    /// Logs a warning on failure — Guid.Empty is detectable in audit queries.
    /// </summary>
    private Guid ParseTenantGuid(string tenantId)
    {
        if (Guid.TryParse(tenantId, out var parsed))
        {
            return parsed;
        }

        _logger.LogWarning(
            "ParseTenantGuid — tenant ID '{TenantId}' is not a valid UUID; using Guid.Empty for storage",
            tenantId);
        return Guid.Empty;
    }
}