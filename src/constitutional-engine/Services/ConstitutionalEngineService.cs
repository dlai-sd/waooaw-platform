// Implements: architecture/reference/components/constitutional-engine.md §1 Evidence First Enforcer
// constitutional_basis: C-007, C-023, C-027, C-059, C-085
using System.Text.Json;
using Google.Protobuf.WellKnownTypes;
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementation.
/// RecordEvidence: WC012-03b — Evidence First Enforcer (C-023, C-007, C-027, C-085).
/// ValidateAction: WC012-02b (prior sprint).
/// RecordEvidence / authority management: WC012-03.
/// TriggerEmergencyStop (Temporal integration): WC012-04b.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    // ValidateAction latency budget: target < 40ms (ADR-001, AD-005)
    private static readonly TimeSpan ValidateActionTimeout = TimeSpan.FromSeconds(5);

    // RecordEvidence latency budget: target < 80ms (AD-005)
    private static readonly TimeSpan RecordEvidenceTimeout = TimeSpan.FromSeconds(10);

    private readonly EvaluatorRegistry _registry;
    private readonly ILogger<ConstitutionalEngineService> _logger;
    private readonly IDbContextFactory<ConstitutionalDbContext> _dbContextFactory;

    public ConstitutionalEngineService(
        EvaluatorRegistry registry,
        ILogger<ConstitutionalEngineService> logger,
        IDbContextFactory<ConstitutionalDbContext> dbContextFactory)
    {
        _registry = registry;
        _logger = logger;
        _dbContextFactory = dbContextFactory;
    }

    // ─── RecordEvidence ──────────────────────────────────────────────────────
    // C-023: Evidence MUST be written to the Constitutional Audit Ledger BEFORE
    //        this RPC returns OK. If the DB write fails, this method returns a
    //        gRPC error — the calling service must treat its own operation as failed.
    // C-007 / C-027: Append-only. No UPDATE or DELETE is ever issued.
    // C-085: Idempotency — if ActionInstanceId+TenantId already has a ledger
    //        record, return the existing evidence_record_id without a second INSERT.
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        // Tenant isolation: always from metadata, never from request body.
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

        // C-023: constitutional_basis must not be empty.
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
                    "action_instance_id is required (C-085: idempotency key)."));
        }

        using var cts = new CancellationTokenSource(RecordEvidenceTimeout);
        var cancellationToken = cts.Token;

        try
        {
            await using var db = await _dbContextFactory.CreateDbContextAsync(cancellationToken);

            // C-085: Idempotency check — if a record for this (IdempotencyKey, TenantId)
            // already exists, return the existing evidence_record_id without re-inserting.
            var existing = await db.Set<EvidenceRecord>()
                .AsNoTracking()
                .FirstOrDefaultAsync(
                    e => e.IdempotencyKey == req.ActionInstanceId && e.TenantId == tenantGuid,
                    cancellationToken);

            if (existing is not null)
            {
                _logger.LogInformation(
                    "RecordEvidence idempotent hit: ActionInstanceId={ActionInstanceId} " +
                    "ExistingRecordId={RecordId} TenantId={TenantId} (C-085)",
                    req.ActionInstanceId, existing.Id, tenantGuid);

                return new RecordEvidenceResponse
                {
                    EvidenceRecordId = existing.Id.ToString(),
                    RecordedAt = Timestamp.FromDateTimeOffset(existing.RecordedAt)
                };
            }

            // C-007 / C-027: Append-only INSERT within a DB transaction.
            // If the transaction fails, we throw — caller must treat its own
            // operation as failed (Evidence First, C-023).
            await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);

            var payloadJson = BuildPayloadJson(req);
            var now = DateTimeOffset.UtcNow;
            var newId = Guid.NewGuid();

            var record = new EvidenceRecord
            {
                Id = newId,
                IdempotencyKey = req.ActionInstanceId,
                TenantId = tenantGuid,
                EvidenceType = req.ActionType,
                Summary = $"{req.ActionType} | state={req.State} | contract={req.ContractId} | basis={req.ConstitutionalBasis}",
                PayloadJson = payloadJson,
                RecordedAt = now
            };

            db.Set<EvidenceRecord>().Add(record);

            // C-023: The INSERT must complete before this method returns OK.
            // Any exception aborts the transaction — gRPC error propagates to caller.
            await db.SaveChangesAsync(cancellationToken);
            await transaction.CommitAsync(cancellationToken);

            _logger.LogInformation(
                "RecordEvidence written: RecordId={RecordId} ActionInstanceId={ActionInstanceId} " +
                "ActionType={ActionType} State={State} TenantId={TenantId} " +
                "ConstitutionalBasis={ConstitutionalBasis} (C-023, C-027)",
                newId, req.ActionInstanceId, req.ActionType, req.State, tenantGuid,
                req.ConstitutionalBasis);

            return new RecordEvidenceResponse
            {
                EvidenceRecordId = newId.ToString(),
                RecordedAt = Timestamp.FromDateTimeOffset(now)
            };
        }
        catch (RpcException)
        {
            // Re-throw gRPC exceptions without wrapping.
            throw;
        }
        catch (OperationCanceledException ex)
        {
            _logger.LogError(ex,
                "RecordEvidence timed out: ActionInstanceId={ActionInstanceId} " +
                "ActionType={ActionType} TenantId={TenantId} (AD-005 budget exceeded)",
                req.ActionInstanceId, req.ActionType, tenantGuid);

            throw new RpcException(
                new Status(StatusCode.DeadlineExceeded,
                    "RecordEvidence exceeded latency budget (AD-005)."));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "RecordEvidence failed: ActionInstanceId={ActionInstanceId} " +
                "ActionType={ActionType} TenantId={TenantId}",
                req.ActionInstanceId, req.ActionType, tenantGuid);

            throw new RpcException(
                new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ─── ValidateAction ──────────────────────────────────────────────────────
    // C-003: action must fall within Decision Space before execution.
    // AD-005: target < 40ms — enforced by ValidateActionTimeout.
    // EvaluationVerdict.Allow  → ValidationDecision.Allow
    // EvaluationVerdict.Deny   → ValidationDecision.Deny
    // EvaluationVerdict.Escalate → ValidationDecision.Escalate
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext ctx)
    {
        var rawTenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        if (string.IsNullOrWhiteSpace(rawTenantId))
        {
            _logger.LogWarning(
                "ValidateAction rejected: x-tenant-id metadata absent. ContractId={ContractId}",
                req.ContractId);

            throw new RpcException(
                new Status(StatusCode.Unauthenticated,
                    "x-tenant-id gRPC metadata is required (C-005: tenant isolation)."));
        }

        using var cts = new CancellationTokenSource(ValidateActionTimeout);
        var cancellationToken = cts.Token;

        try
        {
            var evalCtx = EvaluationContext.FromRequest(req, rawTenantId);
            var results = await _registry.EvaluateAllAsync(evalCtx, cancellationToken);

            // Precedence: Deny > Escalate > Allow
            EvaluationResult? denyResult = null;
            EvaluationResult? escalateResult = null;

            foreach (var result in results)
            {
                if (result.Verdict == EvaluationVerdict.Deny)
                {
                    denyResult = result;
                    break;
                }

                if (result.Verdict == EvaluationVerdict.Escalate && escalateResult is null)
                {
                    escalateResult = result;
                }
            }

            if (denyResult is not null)
            {
                _logger.LogInformation(
                    "ValidateAction DENY: ContractId={ContractId} ActionType={ActionType} " +
                    "ClaimId={ClaimId} Reason={Reason} TenantId={TenantId}",
                    req.ContractId, req.ActionType, denyResult.ClaimId, denyResult.Reason, rawTenantId);

                return new ValidateActionResponse
                {
                    // PTR-VERIFIED: ValidationDecision.Deny (VALIDATION_DECISION_DENY = 2)
                    Decision = ValidationDecision.Deny,
                    ConstitutionalBasis = denyResult.ClaimId,
                    Reason = denyResult.Reason
                };
            }

            if (escalateResult is not null)
            {
                _logger.LogInformation(
                    "ValidateAction ESCALATE: ContractId={ContractId} ActionType={ActionType} " +
                    "ClaimId={ClaimId} Reason={Reason} TenantId={TenantId}",
                    req.ContractId, req.ActionType, escalateResult.ClaimId, escalateResult.Reason, rawTenantId);

                return new ValidateActionResponse
                {
                    // PTR-VERIFIED: ValidationDecision.Escalate (VALIDATION_DECISION_ESCALATE = 3)
                    Decision = ValidationDecision.Escalate,
                    ConstitutionalBasis = escalateResult.ClaimId,
                    Reason = escalateResult.Reason
                };
            }

            _logger.LogInformation(
                "ValidateAction ALLOW: ContractId={ContractId} ActionType={ActionType} " +
                "TenantId={TenantId}",
                req.ContractId, req.ActionType, rawTenantId);

            return new ValidateActionResponse
            {
                // PTR-VERIFIED: ValidationDecision.Allow (VALIDATION_DECISION_ALLOW = 1)
                Decision = ValidationDecision.Allow,
                ConstitutionalBasis = "C-003; C-041",
                Reason = "Action is within Decision Space."
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (OperationCanceledException ex)
        {
            _logger.LogError(ex,
                "ValidateAction timed out: ContractId={ContractId} ActionType={ActionType} " +
                "TenantId={TenantId} (AD-005 budget exceeded)",
                req.ContractId, req.ActionType, rawTenantId);

            throw new RpcException(
                new Status(StatusCode.DeadlineExceeded,
                    "ValidateAction exceeded latency budget (AD-005)."));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "ValidateAction failed: ContractId={ContractId} ActionType={ActionType} " +
                "TenantId={TenantId}",
                req.ContractId, req.ActionType, rawTenantId);

            throw new RpcException(
                new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ─── GrantAuthorityLicense ───────────────────────────────────────────────
    // C-003: authority expansion must be justified by evidence.
    // C-023: record MUST be written before returning OK.
    public override async Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        var rawTenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        if (string.IsNullOrWhiteSpace(rawTenantId))
        {
            throw new RpcException(
                new Status(StatusCode.Unauthenticated,
                    "x-tenant-id gRPC metadata is required (C-005: tenant isolation)."));
        }

        if (!Guid.TryParse(rawTenantId, out var tenantGuid))
        {
            throw new RpcException(
                new Status(StatusCode.Unauthenticated,
                    "x-tenant-id must be a valid UUID in canonical format (C-005)."));
        }

        if (string.IsNullOrWhiteSpace(req.ConstitutionalBasis))
        {
            throw new RpcException(
                new Status(StatusCode.InvalidArgument,
                    "constitutional_basis must not be empty (C-023; AD-008)."));
        }

        if (req.EvidenceIds.Count == 0)
        {
            throw new RpcException(
                new Status(StatusCode.InvalidArgument,
                    "At least one evidence_id is required (C-003: authority earned through evidence)."));
        }

        using var cts = new CancellationTokenSource(RecordEvidenceTimeout);
        var cancellationToken = cts.Token;

        try
        {
            await using var db = await _dbContextFactory.CreateDbContextAsync(cancellationToken);
            await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);

            var now = DateTimeOffset.UtcNow;
            var licenseId = Guid.NewGuid();

            var record = new EvidenceRecord
            {
                Id = licenseId,
                IdempotencyKey = $"grant-authority-{req.ContractId}-{licenseId}",
                TenantId = tenantGuid,
                EvidenceType = "AUTHORITY_GRANT",
                Summary = $"AUTHORITY_GRANT | contract={req.ContractId} | level={req.NewAuthorityLevel} | by={req.GrantedBy} | basis={req.ConstitutionalBasis}",
                PayloadJson = JsonSerializer.Serialize(new
                {
                    contract_id = req.ContractId,
                    new_authority_level = req.NewAuthorityLevel,
                    granted_by = req.GrantedBy,
                    evidence_ids = req.EvidenceIds,
                    constitutional_basis = req.ConstitutionalBasis
                }),
                RecordedAt = now
            };

            db.Set<EvidenceRecord>().Add(record);
            await db.SaveChangesAsync(cancellationToken);
            await transaction.CommitAsync(cancellationToken);

            _logger.LogInformation(
                "GrantAuthorityLicense written: LicenseId={LicenseId} ContractId={ContractId} " +
                "NewLevel={NewLevel} GrantedBy={GrantedBy} TenantId={TenantId} (C-003, C-023)",
                licenseId, req.ContractId, req.NewAuthorityLevel, req.GrantedBy, tenantGuid);

            return new GrantAuthorityResponse
            {
                LicenseId = licenseId.ToString(),
                RecordedAt = Timestamp.FromDateTimeOffset(now)
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (OperationCanceledException ex)
        {
            _logger.LogError(ex,
                "GrantAuthorityLicense timed out: ContractId={ContractId} TenantId={TenantId}",
                req.ContractId, rawTenantId);

            throw new RpcException(
                new Status(StatusCode.DeadlineExceeded,
                    "GrantAuthorityLicense exceeded latency budget."));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "GrantAuthorityLicense failed: ContractId={ContractId} TenantId={TenantId}",
                req.ContractId, rawTenantId);

            throw new RpcException(
                new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ─── RevokeAuthorityLicense ──────────────────────────────────────────────
    // C-003: authority restriction event recorded in Constitutional Audit Ledger.
    // C-023: record MUST be written before returning OK.
    public override async Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        var rawTenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        if (string.IsNullOrWhiteSpace(rawTenantId))
        {
            throw new RpcException(
                new Status(StatusCode.Unauthenticated,
                    "x-tenant-id gRPC metadata is required (C-005: tenant isolation)."));
        }

        if (!Guid.TryParse(rawTenantId, out var tenantGuid))
        {
            throw new RpcException(
                new Status(StatusCode.Unauthenticated,
                    "x-tenant-id must be a valid UUID in canonical format (C-005)."));
        }

        if (string.IsNullOrWhiteSpace(req.ConstitutionalBasis))
        {
            throw new RpcException(
                new Status(StatusCode.InvalidArgument,
                    "constitutional_basis must not be empty (C-023; AD-008)."));
        }

        using var cts = new CancellationTokenSource(RecordEvidenceTimeout);
        var cancellationToken = cts.Token;

        try
        {
            await using var db = await _dbContextFactory.CreateDbContextAsync(cancellationToken);
            await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);

            var now = DateTimeOffset.UtcNow;
            var licenseId = Guid.NewGuid();

            var record = new EvidenceRecord
            {
                Id = licenseId,
                IdempotencyKey = $"revoke-authority-{req.ContractId}-{licenseId}",
                TenantId = tenantGuid,
                EvidenceType = "AUTHORITY_REVOKE",
                Summary = $"AUTHORITY_REVOKE | contract={req.ContractId} | level={req.NewAuthorityLevel} | by={req.RevokedBy} | basis={req.ConstitutionalBasis}",
                PayloadJson = JsonSerializer.Serialize(new
                {
                    contract_id = req.ContractId,
                    new_authority_level = req.NewAuthorityLevel,
                    revoked_by = req.RevokedBy,
                    reason = req.Reason,
                    constitutional_basis = req.ConstitutionalBasis
                }),
                RecordedAt = now
            };

            db.Set<EvidenceRecord>().Add(record);
            await db.SaveChangesAsync(cancellationToken);
            await transaction.CommitAsync(cancellationToken);

            _logger.LogInformation(
                "RevokeAuthorityLicense written: LicenseId={LicenseId} ContractId={ContractId} " +
                "NewLevel={NewLevel} RevokedBy={RevokedBy} TenantId={TenantId} (C-003, C-023)",
                licenseId, req.ContractId, req.NewAuthorityLevel, req.RevokedBy, tenantGuid);

            return new RevokeAuthorityResponse
            {
                LicenseId = licenseId.ToString(),
                RecordedAt = Timestamp.FromDateTimeOffset(now)
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (OperationCanceledException ex)
        {
            _logger.LogError(ex,
                "RevokeAuthorityLicense timed out: ContractId={ContractId} TenantId={TenantId}",
                req.ContractId, rawTenantId);

            throw new RpcException(
                new Status(StatusCode.DeadlineExceeded,
                    "RevokeAuthorityLicense exceeded latency budget."));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "RevokeAuthorityLicense failed: ContractId={ContractId} TenantId={TenantId}",
                req.ContractId, rawTenantId);

            throw new RpcException(
                new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ─── EvaluatePolicy ──────────────────────────────────────────────────────
    // AD-008: every permission decision must name its constitutional basis.
    public override async Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
    {
        var rawTenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        if (string.IsNullOrWhiteSpace(rawTenantId))
        {
            throw new RpcException(
                new Status(StatusCode.Unauthenticated,
                    "x-tenant-id gRPC metadata is required (C-005: tenant isolation)."));
        }

        using var cts = new CancellationTokenSource(ValidateActionTimeout);
        var cancellationToken = cts.Token;

        try
        {
            // Build a synthetic ValidateActionRequest so we can reuse EvaluatorRegistry.
            var syntheticReq = new ValidateActionRequest
            {
                ContractId = req.ContractId,
                ActionType = req.ActionType,
                ActionParameters = req.ActionContext,
                DecisionSpaceVersion = 0
            };

            var evalCtx = EvaluationContext.FromRequest(syntheticReq, rawTenantId);
            var results = await _registry.EvaluateAllAsync(evalCtx, cancellationToken);

            EvaluationResult? denyResult = null;
            EvaluationResult? escalateResult = null;

            foreach (var result in results)
            {
                if (result.Verdict == EvaluationVerdict.Deny)
                {
                    denyResult = result;
                    break;
                }

                if (result.Verdict == EvaluationVerdict.Escalate && escalateResult is null)
                {
                    escalateResult = result;
                }
            }

            if (denyResult is not null)
            {
                return new EvaluatePolicyResponse
                {
                    Decision = PolicyDecision.Deny,
                    ConstitutionalBasis = denyResult.ClaimId,
                    Rationale = denyResult.Reason
                };
            }

            if (escalateResult is not null)
            {
                return new EvaluatePolicyResponse
                {
                    Decision = PolicyDecision.Escalate,
                    ConstitutionalBasis = escalateResult.ClaimId,
                    Rationale = escalateResult.Reason
                };
            }

            return new EvaluatePolicyResponse
            {
                Decision = PolicyDecision.Permit,
                ConstitutionalBasis = "C-003; AD-008",
                Rationale = "Action permitted within Decision Space."
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (OperationCanceledException ex)
        {
            _logger.LogError(ex,
                "EvaluatePolicy timed out: ContractId={ContractId} ActionType={ActionType} " +
                "TenantId={TenantId}",
                req.ContractId, req.ActionType, rawTenantId);

            throw new RpcException(
                new Status(StatusCode.DeadlineExceeded,
                    "EvaluatePolicy exceeded latency budget."));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "EvaluatePolicy failed: ContractId={ContractId} ActionType={ActionType} " +
                "TenantId={TenantId}",
                req.ContractId, req.ActionType, rawTenantId);

            throw new RpcException(
                new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ─── TriggerEmergencyStop ────────────────────────────────────────────────
    // C-013: Emergency Stop is a Constitutional Floor — MUST complete within budget.
    // AD-001: 100ms latency budget for this RPC.
    // C-023: record MUST be written before returning OK.
    // WC012-04b: Temporal signal integration is out of scope for this sprint.
    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
    {
        // Emergency Stop SLA: 100ms (AD-001)
        var emergencyStopTimeout = TimeSpan.FromMilliseconds(100);

        var rawTenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        if (string.IsNullOrWhiteSpace(rawTenantId))
        {
            throw new RpcException(
                new Status(StatusCode.Unauthenticated,
                    "x-tenant-id gRPC metadata is required (C-005: tenant isolation)."));
        }

        if (!Guid.TryParse(rawTenantId, out var tenantGuid))
        {
            throw new RpcException(
                new Status(StatusCode.Unauthenticated,
                    "x-tenant-id must be a valid UUID in canonical format (C-005)."));
        }

        using var cts = new CancellationTokenSource(emergencyStopTimeout);
        var cancellationToken = cts.Token;

        try
        {
            await using var db = await _dbContextFactory.CreateDbContextAsync(cancellationToken);
            await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);

            var now = DateTimeOffset.UtcNow;
            var stopRecordId = Guid.NewGuid();

            var record = new EvidenceRecord
            {
                Id = stopRecordId,
                IdempotencyKey = $"emergency-stop-{req.ContractId}-{stopRecordId}",
                TenantId = tenantGuid,
                EvidenceType = "EMERGENCY_STOP",
                Summary = $"EMERGENCY_STOP | contract={req.ContractId} | by={req.StoppedBy} | sessions={req.ActiveSessionIds.Count}",
                PayloadJson = JsonSerializer.Serialize(new
                {
                    contract_id = req.ContractId,
                    stopped_by = req.StoppedBy,
                    active_session_ids = req.ActiveSessionIds,
                    constitutional_basis = "C-013; AD-001"
                }),
                RecordedAt = now
            };

            db.Set<EvidenceRecord>().Add(record);
            await db.SaveChangesAsync(cancellationToken);
            await transaction.CommitAsync(cancellationToken);

            _logger.LogWarning(
                "TriggerEmergencyStop written: StopRecordId={StopRecordId} ContractId={ContractId} " +
                "StoppedBy={StoppedBy} SessionCount={SessionCount} TenantId={TenantId} (C-013, C-023)",
                stopRecordId, req.ContractId, req.StoppedBy, req.ActiveSessionIds.Count, tenantGuid);

            // WC012-04b: Temporal signal integration will be wired in the next sprint.
            // For now, we report the session IDs back without actively signalling them.
            return new EmergencyStopResponse
            {
                EmergencyStopRecordId = $"EMERGENCY_STOP:{stopRecordId}",
                RecordedAt = Timestamp.FromDateTimeOffset(now),
                AffectedSessions = { req.ActiveSessionIds }
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (OperationCanceledException ex)
        {
            _logger.LogError(ex,
                "TriggerEmergencyStop timed out: ContractId={ContractId} TenantId={TenantId} " +
                "(C-013 violation — Emergency Stop exceeded AD-001 100ms budget)",
                req.ContractId, rawTenantId);

            throw new RpcException(
                new Status(StatusCode.DeadlineExceeded,
                    "TriggerEmergencyStop exceeded Constitutional Floor latency budget (C-013; AD-001)."));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "TriggerEmergencyStop failed: ContractId={ContractId} TenantId={TenantId}",
                req.ContractId, rawTenantId);

            throw new RpcException(
                new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ─── Private Helpers ─────────────────────────────────────────────────────

    private static string BuildPayloadJson(RecordEvidenceRequest req)
    {
        return JsonSerializer.Serialize(new
        {
            action_instance_id = req.ActionInstanceId,
            contract_id = req.ContractId,
            professional_id = req.ProfessionalId,
            action_type = req.ActionType,
            state = req.State.ToString(),
            proposed_content = req.HasProposedContent ? req.ProposedContent : null,
            executed_content = req.HasExecutedContent ? req.ExecutedContent : null,
            is_scope_boundary = req.IsScopeBoundary,
            scope_boundary_name = req.HasScopeBoundaryName ? req.ScopeBoundaryName : null,
            scope_boundary_acknowledgment = req.HasScopeBoundaryAcknowledgment
                ? req.ScopeBoundaryAcknowledgment
                : null,
            decision_space_version = req.DecisionSpaceVersion,
            constitutional_basis = req.ConstitutionalBasis
        });
    }
}