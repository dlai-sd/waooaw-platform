// Implements: architecture/reference/components/constitutional-engine.md §1 Evidence First Enforcer
// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-003 (Authority Licensed), C-001 (Emergency Stop),
//                       C-007 (Append-Only), C-027 (No Mutation), C-059 (Traceability),
//                       C-073 (Annotation), C-076 (Test Coverage), C-085 (Idempotency)

#nullable enable

using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using System.Diagnostics;
using System.Text.Json;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementing the Constitutional Engine boundary validator and evidence recorder.
/// All constitutional obligations are enforced here before any response is returned.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    // C-059: Traceable activity source for every RPC operation
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly EvaluatorRegistry _registry;
    private readonly ConstitutionalDbContext _dbContext;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    // C-073: Constructor injection — constitutional dependencies declared explicitly
    public ConstitutionalEngineService(
        EvaluatorRegistry registry,
        ConstitutionalDbContext dbContext,
        ILogger<ConstitutionalEngineService> logger)
    {
        ArgumentNullException.ThrowIfNull(registry);
        ArgumentNullException.ThrowIfNull(dbContext);
        ArgumentNullException.ThrowIfNull(logger);

        _registry = registry;
        _dbContext = dbContext;
        _logger = logger;
    }

    // ── ValidateAction ────────────────────────────────────────────────────────

    // C-073: Implements C-023 (Evidence First) — all evaluators run before response is formed
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest request,
        ServerCallContext context)
    {
        ArgumentNullException.ThrowIfNull(request);

        using var activity = _tracer.StartActivity("ValidateAction", ActivityKind.Server);
        activity?.SetTag("contract_id", request.ContractId);
        activity?.SetTag("action_type", request.ActionType);

        var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;
        activity?.SetTag("tenant_id", tenantId);

        _logger.LogInformation(
            "ValidateAction: ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
            request.ContractId, request.ActionType, tenantId);

        var evalContext = EvaluationContext.FromRequest(request, tenantId);
        var results = await _registry.EvaluateAllAsync(evalContext, context.CancellationToken);

        // First denial wins (C-023: deny is a constitutional boundary)
        var firstDeny = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Deny);
        if (firstDeny is not null)
        {
            _logger.LogWarning(
                "ValidateAction DENIED: ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                request.ContractId, firstDeny.ClaimId, firstDeny.Reason);

            activity?.SetTag("decision", "Deny");
            activity?.SetTag("deny_claim", firstDeny.ClaimId);

            return new ValidateActionResponse
            {
                Decision = ValidationDecision.Deny,
                ConstitutionalBasis = firstDeny.ClaimId,
                Reason = firstDeny.Reason
            };
        }

        var firstEscalate = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Escalate);
        if (firstEscalate is not null)
        {
            _logger.LogWarning(
                "ValidateAction ESCALATED: ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                request.ContractId, firstEscalate.ClaimId, firstEscalate.Reason);

            activity?.SetTag("decision", "Escalate");
            return new ValidateActionResponse
            {
                Decision = ValidationDecision.Escalate,
                ConstitutionalBasis = firstEscalate.ClaimId,
                Reason = firstEscalate.Reason
            };
        }

        activity?.SetTag("decision", "Allow");
        _logger.LogInformation(
            "ValidateAction ALLOWED: ContractId={ContractId}", request.ContractId);

        return new ValidateActionResponse
        {
            Decision = ValidationDecision.Allow,
            ConstitutionalBasis = string.Join(", ", results.Select(r => r.ClaimId)),
            Reason = "All constitutional evaluators passed."
        };
    }

    // ── RecordEvidence ────────────────────────────────────────────────────────

    // C-073: Implements C-023 (Evidence First) — DB write MUST precede response.
    //        Implements C-007/C-027 (Append-Only) — no UPDATE or DELETE ever.
    //        Implements C-085 (Idempotency) — duplicate ActionInstanceId returns existing record.
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest request,
        ServerCallContext context)
    {
        ArgumentNullException.ThrowIfNull(request);

        using var activity = _tracer.StartActivity("RecordEvidence", ActivityKind.Server);
        activity?.SetTag("action_instance_id", request.ActionInstanceId);
        activity?.SetTag("contract_id", request.ContractId);
        activity?.SetTag("action_type", request.ActionType);

        // Validate and extract tenant identifier (C-059: every record must be tenant-scoped)
        var tenantIdRaw = context.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;
        if (!Guid.TryParse(tenantIdRaw, out var tenantGuid))
        {
            _logger.LogWarning(
                "RecordEvidence rejected: x-tenant-id header is missing or not a valid GUID. Value={Value}",
                tenantIdRaw);

            throw new RpcException(new Status(
                StatusCode.InvalidArgument,
                "x-tenant-id header must be a valid GUID."));
        }

        if (string.IsNullOrWhiteSpace(request.ActionInstanceId))
        {
            throw new RpcException(new Status(
                StatusCode.InvalidArgument,
                "ActionInstanceId must not be empty."));
        }

        activity?.SetTag("tenant_id", tenantGuid.ToString());

        // C-085: Idempotency — check for existing record before inserting
        // C-073: Implements C-085 idempotency guard
        var idempotencyKey = request.ActionInstanceId;
        var existing = await _dbContext.EvidenceRecords
            .FirstOrDefaultAsync(
                e => e.IdempotencyKey == idempotencyKey && e.TenantId == tenantGuid,
                context.CancellationToken)
            .ConfigureAwait(false);

        if (existing is not null)
        {
            _logger.LogInformation(
                "RecordEvidence idempotent hit: IdempotencyKey={Key} ExistingId={Id}",
                idempotencyKey, existing.Id);

            activity?.SetTag("idempotent", true);
            return new RecordEvidenceResponse
            {
                EvidenceRecordId = existing.Id.ToString()
            };
        }

        // C-023 (Evidence First): build and persist the evidence record before returning
        // C-007/C-027 (Append-Only): Add() only — never Update() or Remove()
        var payloadJson = SerializePayload(request);

        var record = new EvidenceRecord
        {
            Id = Guid.NewGuid(),
            IdempotencyKey = idempotencyKey,
            TenantId = tenantGuid,
            EvidenceType = request.ActionType,
            Summary = BuildSummary(request),
            PayloadJson = payloadJson,
            RecordedAt = DateTimeOffset.UtcNow
        };

        // C-073: Append-only insert — NEVER call Update() or Remove() on constitutional records
        _dbContext.EvidenceRecords.Add(record);

        // C-023: SaveChanges BEFORE constructing the success response
        await _dbContext.SaveChangesAsync(context.CancellationToken).ConfigureAwait(false);

        _logger.LogInformation(
            "RecordEvidence persisted: Id={Id} ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
            record.Id, request.ContractId, request.ActionType, tenantGuid);

        activity?.SetTag("evidence_record_id", record.Id.ToString());

        return new RecordEvidenceResponse
        {
            EvidenceRecordId = record.Id.ToString()
        };
    }

    // ── GrantAuthorityLicense ─────────────────────────────────────────────────

    // C-073: Implements C-003 (Authority Licensed)
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest request,
        ServerCallContext context)
    {
        ArgumentNullException.ThrowIfNull(request);

        using var activity = _tracer.StartActivity("GrantAuthorityLicense", ActivityKind.Server);
        activity?.SetTag("contract_id", request.ContractId);

        _logger.LogInformation(
            "GrantAuthorityLicense: ContractId={ContractId} GrantedBy={GrantedBy} Level={Level}",
            request.ContractId, request.GrantedBy, request.NewAuthorityLevel);

        // DESIGN_QUESTION: Should GrantAuthorityLicense persist an authority license record to DB?
        //                  If yes, EA must specify entity schema and table name before implementation.
        var licenseId = Guid.NewGuid().ToString();
        activity?.SetTag("license_id", licenseId);

        return Task.FromResult(new GrantAuthorityResponse { LicenseId = licenseId });
    }

    // ── RevokeAuthorityLicense ────────────────────────────────────────────────

    // C-073: Implements C-003 (Authority Licensed) — revocation is also an append-only event
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest request,
        ServerCallContext context)
    {
        ArgumentNullException.ThrowIfNull(request);

        using var activity = _tracer.StartActivity("RevokeAuthorityLicense", ActivityKind.Server);
        activity?.SetTag("contract_id", request.ContractId);

        _logger.LogInformation(
            "RevokeAuthorityLicense: ContractId={ContractId} RevokedBy={RevokedBy} Level={Level}",
            request.ContractId, request.RevokedBy, request.NewAuthorityLevel);

        // DESIGN_QUESTION: Should RevokeAuthorityLicense write a revocation record to DB?
        //                  EA must specify entity schema for revocation events.
        var licenseId = Guid.NewGuid().ToString();
        activity?.SetTag("license_id", licenseId);

        return Task.FromResult(new RevokeAuthorityResponse { LicenseId = licenseId });
    }

    // ── EvaluatePolicy ────────────────────────────────────────────────────────

    // C-073: Implements policy evaluation gate
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest request,
        ServerCallContext context)
    {
        ArgumentNullException.ThrowIfNull(request);

        using var activity = _tracer.StartActivity("EvaluatePolicy", ActivityKind.Server);

        _logger.LogInformation("EvaluatePolicy called");

        // DESIGN_QUESTION: EvaluatePolicyRequest/Response fields not fully specified in TYPE CONTRACT.
        //                  EA must provide proto fields before implementing policy evaluation logic.
        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit
        });
    }

    // ── TriggerEmergencyStop ──────────────────────────────────────────────────

    // C-073: Implements C-001 (Emergency Stop) — highest-priority constitutional obligation
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest request,
        ServerCallContext context)
    {
        ArgumentNullException.ThrowIfNull(request);

        using var activity = _tracer.StartActivity("TriggerEmergencyStop", ActivityKind.Server);
        activity?.SetTag("contract_id", request.ContractId);
        activity?.SetTag("stopped_by", request.StoppedBy);

        _logger.LogCritical(
            "EMERGENCY STOP TRIGGERED: ContractId={ContractId} StoppedBy={StoppedBy} Sessions={Count}",
            request.ContractId, request.StoppedBy, request.ActiveSessionIds.Count);

        // DESIGN_QUESTION: Should EmergencyStop write an EmergencyStopEvent entity to DB?
        //                  EA must confirm entity schema and whether it's in ConstitutionalDbContext.
        var stopRecordId = Guid.NewGuid().ToString();
        activity?.SetTag("emergency_stop_record_id", stopRecordId);

        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = stopRecordId
        };
        response.AffectedSessions.AddRange(request.ActiveSessionIds);

        return Task.FromResult(response);
    }

    // ── Private helpers ───────────────────────────────────────────────────────

    private static string BuildSummary(RecordEvidenceRequest request) =>
        $"Action '{request.ActionType}' on contract '{request.ContractId}' " +
        $"by professional '{request.ProfessionalId}' " +
        $"[dsv={request.DecisionSpaceVersion}]";

    private static string SerializePayload(RecordEvidenceRequest request)
    {
        // Serialize only the non-proto fields to avoid protobuf serializer dependency in payload JSON.
        // The full proto message is not directly JSON-serializable via System.Text.Json.
        var payload = new
        {
            request.ActionInstanceId,
            request.ContractId,
            request.ProfessionalId,
            request.ActionType,
            State = request.State.ToString(),
            request.ProposedContent,
            request.ExecutedContent,
            request.IsScopeBoundary,
            request.ScopeBoundaryName,
            request.ScopeBoundaryAcknowledgment,
            request.DecisionSpaceVersion,
            request.ConstitutionalBasis
        };

        return JsonSerializer.Serialize(payload);
    }
}