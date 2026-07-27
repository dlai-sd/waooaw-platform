// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-023 (Evidence First), C-041 (Tool Authorization), C-043 (Budget Ceiling),
//                       C-048 (Non-Exploitation), C-049 (Honest Limitation), C-051 (Resource Transparency),
//                       C-062 (AI Security), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-073 (Constitutional Annotation), C-059 (Traceability)

#nullable enable

using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using System.Diagnostics;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.EmergencyStop;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementing all constitutional engine RPCs.
/// C-073: Every method that enforces a constitutional obligation is annotated below.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    // C-059: Tracer named for the service assembly — matches OTel registration in Program.cs
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ConstitutionalDbContext _db;
    private readonly EmergencyStopDbContext _emergencyStopDb;
    private readonly EvaluatorRegistry _registry;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    public ConstitutionalEngineService(
        ConstitutionalDbContext db,
        EmergencyStopDbContext emergencyStopDb,
        EvaluatorRegistry registry,
        ILogger<ConstitutionalEngineService> logger)
    {
        ArgumentNullException.ThrowIfNull(db);
        ArgumentNullException.ThrowIfNull(emergencyStopDb);
        ArgumentNullException.ThrowIfNull(registry);
        ArgumentNullException.ThrowIfNull(logger);
        _db = db;
        _emergencyStopDb = emergencyStopDb;
        _registry = registry;
        _logger = logger;
    }

    // ─────────────────────────────────────────────────────────────────────────────
    // C-073: RecordEvidence — implements C-023 (Evidence First).
    //        Every action touching constitutional state must produce an immutable
    //        audit record BEFORE any response is returned to the caller.
    // ─────────────────────────────────────────────────────────────────────────────
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req,
        ServerCallContext ctx)
    {
        using var activity = _tracer.StartActivity("RecordEvidence", ActivityKind.Server);

        // Extract and validate tenant ID from gRPC metadata (C-059: traceability)
        var tenantIdRaw = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;
        if (string.IsNullOrWhiteSpace(tenantIdRaw))
        {
            throw new RpcException(new Status(
                StatusCode.InvalidArgument,
                "x-tenant-id header is required"));
        }
        if (!Guid.TryParse(tenantIdRaw, out var tenantId))
        {
            throw new RpcException(new Status(
                StatusCode.InvalidArgument,
                $"x-tenant-id header is not a valid GUID: '{tenantIdRaw}'"));
        }

        // Validate ActionInstanceId — used as idempotency key
        if (string.IsNullOrWhiteSpace(req.ActionInstanceId))
        {
            throw new RpcException(new Status(
                StatusCode.InvalidArgument,
                "ActionInstanceId is required and must not be empty or whitespace"));
        }

        activity?.SetTag("tenant_id", tenantIdRaw);
        activity?.SetTag("action_instance_id", req.ActionInstanceId);
        activity?.SetTag("action_type", req.ActionType);

        // C-073: Idempotency guard — C-085 (Idempotency): prior persisted record is authoritative.
        //        Check by (IdempotencyKey, TenantId) to prevent cross-tenant idempotency collisions.
        var existing = await _db.EvidenceRecords
            .FirstOrDefaultAsync(
                e => e.IdempotencyKey == req.ActionInstanceId && e.TenantId == tenantId,
                ctx.CancellationToken);

        if (existing is not null)
        {
            _logger.LogInformation(
                "Idempotent RecordEvidence — returning existing record Id={Id} TenantId={TenantId}",
                existing.Id,
                tenantId);
            return new RecordEvidenceResponse { EvidenceRecordId = existing.Id.ToString() };
        }

        // C-073: Append-only write (C-027) — NEVER call Update() or Remove() on evidence records.
        var record = new EvidenceRecord
        {
            IdempotencyKey = req.ActionInstanceId,
            TenantId       = tenantId,
            EvidenceType   = req.ActionType,
            Summary        = BuildSummary(req),
            PayloadJson    = string.IsNullOrWhiteSpace(req.ProposedContent) ? null : req.ProposedContent,
            RecordedAt     = DateTimeOffset.UtcNow
        };

        _db.EvidenceRecords.Add(record);
        await _db.SaveChangesAsync(ctx.CancellationToken);

        _logger.LogInformation(
            "Evidence recorded Id={Id} TenantId={TenantId} ActionType={ActionType}",
            record.Id,
            tenantId,
            req.ActionType);

        return new RecordEvidenceResponse { EvidenceRecordId = record.Id.ToString() };
    }

    // ─────────────────────────────────────────────────────────────────────────────
    // C-073: ValidateAction — implements §2 PAAS Boundary Validator.
    //        Runs all registered IClaimEvaluator instances via EvaluatorRegistry.
    //        Default deny: any DENY verdict from any evaluator blocks the action.
    //        C-041: unlisted tool name = DENY.
    //        C-043: proposed spend exceeding budget ceiling = DENY.
    //        C-048: exploitation risk level HIGH/CRITICAL = DENY.
    //        C-049: confidence below threshold = ESCALATE.
    //        C-062: prohibited tool classification = DENY.
    // ─────────────────────────────────────────────────────────────────────────────
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req,
        ServerCallContext ctx)
    {
        using var activity = _tracer.StartActivity("ValidateAction", ActivityKind.Server);

        // Tenant ID comes from gRPC metadata — not from the request body
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        activity?.SetTag("contract_id", req.ContractId);
        activity?.SetTag("action_type", req.ActionType);
        activity?.SetTag("tenant_id", tenantId);
        activity?.SetTag("decision_space_version", req.DecisionSpaceVersion);

        // C-073: Default deny — C-041 requires an explicit ContractId to establish decision space.
        //        An absent or empty ContractId cannot be authorized.
        if (string.IsNullOrWhiteSpace(req.ContractId))
        {
            _logger.LogWarning(
                "ValidateAction DENY — ContractId is empty or missing (default deny, C-041)");
            activity?.SetTag("decision", "Deny");
            activity?.SetTag("claim_id", "C-041");
            return new ValidateActionResponse
            {
                Decision           = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason             = "ContractId is required — default deny (C-041)"
            };
        }

        // Build evaluation context from the gRPC request and tenant metadata header
        var evalCtx = EvaluationContext.FromRequest(req, tenantId);

        // C-073: Run all constitutional claim evaluators.
        //        EvaluatorRegistry.EvaluateAllAsync is the ONLY entry point — do not call
        //        individual evaluators directly from this service method.
        var results = await _registry.EvaluateAllAsync(evalCtx, ctx.CancellationToken);

        // C-073: Short-circuit on first DENY — do not evaluate remaining claims once one denies.
        //        C-049 Escalate verdict forwards to human review path (Sujay).
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction DENY ClaimId={ClaimId} ContractId={ContractId} ActionType={ActionType} Reason={Reason}",
                    result.ClaimId,
                    req.ContractId,
                    req.ActionType,
                    result.Reason);
                activity?.SetTag("decision", "Deny");
                activity?.SetTag("claim_id", result.ClaimId);
                return new ValidateActionResponse
                {
                    Decision           = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason             = result.Reason
                };
            }

            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                _logger.LogWarning(
                    "ValidateAction ESCALATE ClaimId={ClaimId} ContractId={ContractId} ActionType={ActionType} Reason={Reason}",
                    result.ClaimId,
                    req.ContractId,
                    req.ActionType,
                    result.Reason);
                activity?.SetTag("decision", "Escalate");
                activity?.SetTag("claim_id", result.ClaimId);
                return new ValidateActionResponse
                {
                    Decision           = ValidationDecision.Escalate,
                    ConstitutionalBasis = result.ClaimId,
                    Reason             = result.Reason
                };
            }
        }

        // All evaluators returned Allow — action is constitutionally authorized
        _logger.LogInformation(
            "ValidateAction ALLOW ContractId={ContractId} ActionType={ActionType} EvaluatorCount={Count}",
            req.ContractId,
            req.ActionType,
            results.Count);
        activity?.SetTag("decision", "Allow");
        activity?.SetTag("evaluator_count", results.Count);

        return new ValidateActionResponse
        {
            Decision           = ValidationDecision.Allow,
            ConstitutionalBasis = "C-041,C-043,C-048,C-049,C-062",
            Reason             = "All constitutional evaluators passed"
        };
    }

    // ─────────────────────────────────────────────────────────────────────────────
    // C-073: GrantAuthorityLicense — implements authority licensing per C-003.
    //        DESIGN_QUESTION: Is full GrantAuthorityLicense implementation in scope for WC012-02?
    //        Stub retained pending EA decision on sprint boundary.
    // ─────────────────────────────────────────────────────────────────────────────
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(new Status(
            StatusCode.Unimplemented,
            "GrantAuthorityLicense is not yet implemented — pending WC012-04"));
    }

    // ─────────────────────────────────────────────────────────────────────────────
    // C-073: RevokeAuthorityLicense — implements authority revocation per C-003.
    //        DESIGN_QUESTION: Is full RevokeAuthorityLicense implementation in scope for WC012-02?
    //        Stub retained pending EA decision on sprint boundary.
    // ─────────────────────────────────────────────────────────────────────────────
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(new Status(
            StatusCode.Unimplemented,
            "RevokeAuthorityLicense is not yet implemented — pending WC012-04"));
    }

    // ─────────────────────────────────────────────────────────────────────────────
    // C-073: EvaluatePolicy — implements policy evaluation gate.
    //        DESIGN_QUESTION: Is full EvaluatePolicy implementation in scope for WC012-02?
    //        Stub retained pending EA decision on sprint boundary.
    // ─────────────────────────────────────────────────────────────────────────────
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(new Status(
            StatusCode.Unimplemented,
            "EvaluatePolicy is not yet implemented — pending WC012-05"));
    }

    // ─────────────────────────────────────────────────────────────────────────────
    // C-073: TriggerEmergencyStop — implements C-001 absolute Emergency Stop.
    //        Writes to EmergencyStopDbContext (separate DB context per C-027).
    //        Append-only: never updates or deletes emergency stop events.
    // ─────────────────────────────────────────────────────────────────────────────
    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req,
        ServerCallContext ctx)
    {
        using var activity = _tracer.StartActivity("TriggerEmergencyStop", ActivityKind.Server);

        if (string.IsNullOrWhiteSpace(req.ContractId) || !Guid.TryParse(req.ContractId, out var contractId))
        {
            throw new RpcException(new Status(
                StatusCode.InvalidArgument,
                "ContractId is required and must be a valid GUID"));
        }

        activity?.SetTag("contract_id", req.ContractId);
        activity?.SetTag("stopped_by", req.StoppedBy);
        activity?.SetTag("session_count", req.ActiveSessionIds.Count);

        // C-073: Append-only emergency stop event (C-027) — immutable once written
        var stopEvent = new EmergencyStopEvent
        {
            ContractId         = contractId,
            InitiatedByUserId  = req.StoppedBy,
            AffectedSessionIds = req.ActiveSessionIds.ToArray(),
            TriggeredAt        = DateTimeOffset.UtcNow,
            StopSource         = "gRPC"
        };

        _emergencyStopDb.EmergencyStopEvents.Add(stopEvent);
        await _emergencyStopDb.SaveChangesAsync(ctx.CancellationToken);

        _logger.LogInformation(
            "EmergencyStop triggered Id={Id} ContractId={ContractId} StoppedBy={StoppedBy} Sessions={SessionCount}",
            stopEvent.Id,
            req.ContractId,
            req.StoppedBy,
            req.ActiveSessionIds.Count);

        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = stopEvent.Id.ToString()
        };
        response.AffectedSessions.AddRange(req.ActiveSessionIds);

        return response;
    }

    // ─────────────────────────────────────────────────────────────────────────────
    // Private helpers
    // ─────────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Builds a human-readable summary for an evidence record.
    ///        Summary must never be empty (tested by CCT-EF-01).
    /// </summary>
    private static string BuildSummary(RecordEvidenceRequest req)
    {
        var contractPart = string.IsNullOrWhiteSpace(req.ContractId)
            ? "unknown-contract"
            : req.ContractId;
        var actionPart = string.IsNullOrWhiteSpace(req.ActionType)
            ? "unknown-action"
            : req.ActionType;

        return $"Evidence recorded: action={actionPart} contract={contractPart} " +
               $"professional={req.ProfessionalId} state={req.State}";
    }
}