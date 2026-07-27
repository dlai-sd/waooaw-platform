// Implements: architecture/reference/components/constitutional-engine.md
// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-007 (append-only audit), C-027 (immutable records), C-059 (traceability),
//                       C-073 (annotated obligations), C-085 (idempotency)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly EvaluatorRegistry _registry;
    private readonly ConstitutionalDbContext _db;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    // C-073: Constructor injection — all dependencies required at activation time
    public ConstitutionalEngineService(
        EvaluatorRegistry registry,
        ConstitutionalDbContext db,
        ILogger<ConstitutionalEngineService> logger)
    {
        ArgumentNullException.ThrowIfNull(registry);
        ArgumentNullException.ThrowIfNull(db);
        ArgumentNullException.ThrowIfNull(logger);
        _registry = registry;
        _db = db;
        _logger = logger;
    }

    // C-073: ValidateAction — runs all registered claim evaluators, returns constitutional decision
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest request,
        ServerCallContext context)
    {
        ArgumentNullException.ThrowIfNull(request);
        var ct = context.CancellationToken;

        using var activity = _tracer.StartActivity("ValidateAction", ActivityKind.Server);
        activity?.SetTag("contract_id", request.ContractId);
        activity?.SetTag("action_type", request.ActionType);

        var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? "";

        _logger.LogInformation(
            "ValidateAction: ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
            request.ContractId, request.ActionType, tenantId);

        var evalContext = EvaluationContext.FromRequest(request, tenantId);
        var results = await _registry.EvaluateAllAsync(evalContext, ct).ConfigureAwait(false);

        var denied = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Deny);
        if (denied is not null)
        {
            _logger.LogWarning(
                "ValidateAction DENY: ClaimId={ClaimId} Reason={Reason}",
                denied.ClaimId, denied.Reason);

            return new ValidateActionResponse
            {
                Decision        = ValidationDecision.Unspecified, // DESIGN_QUESTION: Proto should expose Deny variant — confirm with EA
                ConstitutionalBasis = denied.ClaimId,
                Reason          = denied.Reason
            };
        }

        var basis = string.Join(", ", results.Select(r => r.ClaimId));
        return new ValidateActionResponse
        {
            Decision            = ValidationDecision.Unspecified, // DESIGN_QUESTION: Proto should expose Allow variant
            ConstitutionalBasis = basis,
            Reason              = "All constitutional claims satisfied."
        };
    }

    // C-073: RecordEvidence — Evidence First enforcer (C-023). Writes EvidenceRecord to DB
    //        BEFORE returning response. Idempotent on ActionInstanceId (C-085). Append-only (C-007).
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest request,
        ServerCallContext context)
    {
        ArgumentNullException.ThrowIfNull(request);
        var ct = context.CancellationToken;

        using var activity = _tracer.StartActivity("RecordEvidence", ActivityKind.Server);
        activity?.SetTag("action_instance_id", request.ActionInstanceId);
        activity?.SetTag("contract_id", request.ContractId);
        activity?.SetTag("action_type", request.ActionType);

        var tenantIdHeader = context.RequestHeaders.GetValue("x-tenant-id") ?? "";

        _logger.LogInformation(
            "RecordEvidence: ActionInstanceId={ActionInstanceId} ContractId={ContractId} TenantId={TenantId}",
            request.ActionInstanceId, request.ContractId, tenantIdHeader);

        // C-085: Idempotency — return existing record if ActionInstanceId already recorded
        var existing = await _db.EvidenceRecords
            .AsNoTracking()
            .FirstOrDefaultAsync(r => r.IdempotencyKey == request.ActionInstanceId, ct)
            .ConfigureAwait(false);

        if (existing is not null)
        {
            _logger.LogInformation(
                "RecordEvidence idempotent hit: ActionInstanceId={ActionInstanceId} ExistingId={Id}",
                request.ActionInstanceId, existing.Id);

            activity?.SetTag("idempotent", true);
            return new RecordEvidenceResponse { EvidenceRecordId = existing.Id.ToString() };
        }

        // C-073: Resolve TenantId — parse header as Guid; fall back to empty Guid if absent/malformed
        var tenantGuid = Guid.TryParse(tenantIdHeader, out var parsedTenant)
            ? parsedTenant
            : Guid.Empty;

        // C-073: Build payload JSON from request fields for immutable audit trail (C-007)
        var payload = JsonSerializer.Serialize(new
        {
            request.ContractId,
            request.ProfessionalId,
            request.ActionType,
            State                      = request.State.ToString(),
            request.ProposedContent,
            request.ExecutedContent,
            request.IsScopeBoundary,
            request.ScopeBoundaryName,
            request.ScopeBoundaryAcknowledgment,
            request.DecisionSpaceVersion,
            request.ConstitutionalBasis
        });

        var record = new EvidenceRecord
        {
            Id             = Guid.NewGuid(),
            IdempotencyKey = request.ActionInstanceId,
            TenantId       = tenantGuid,
            EvidenceType   = request.ActionType,
            Summary        = $"Evidence recorded for action {request.ActionInstanceId} on contract {request.ContractId}",
            PayloadJson    = payload,
            RecordedAt     = DateTimeOffset.UtcNow
        };

        // C-023: Evidence FIRST — persist before returning any response.
        // C-007: Append-only — no Update() or Remove() ever called on EvidenceRecord.
        await _db.EvidenceRecords.AddAsync(record, ct).ConfigureAwait(false);
        await _db.SaveChangesAsync(ct).ConfigureAwait(false);

        _logger.LogInformation(
            "RecordEvidence committed: Id={Id} ActionInstanceId={ActionInstanceId}",
            record.Id, request.ActionInstanceId);

        activity?.SetTag("evidence_record_id", record.Id.ToString());

        return new RecordEvidenceResponse { EvidenceRecordId = record.Id.ToString() };
    }

    // C-073: GrantAuthorityLicense — authority licensing stub (C-003)
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest request,
        ServerCallContext context)
    {
        // DESIGN_QUESTION: Full authority licensing persistence is out of scope for WC012-03b.
        //                  EA to confirm target sprint.
        _logger.LogWarning("GrantAuthorityLicense called — stub implementation");
        return Task.FromResult(new GrantAuthorityResponse { LicenseId = Guid.NewGuid().ToString() });
    }

    // C-073: RevokeAuthorityLicense — authority revocation stub (C-003)
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest request,
        ServerCallContext context)
    {
        _logger.LogWarning("RevokeAuthorityLicense called — stub implementation");
        return Task.FromResult(new RevokeAuthorityResponse { LicenseId = Guid.NewGuid().ToString() });
    }

    // C-073: EvaluatePolicy — policy evaluation stub
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest request,
        ServerCallContext context)
    {
        _logger.LogWarning("EvaluatePolicy called — stub implementation");
        return Task.FromResult(new EvaluatePolicyResponse { Decision = PolicyDecision.Unspecified });
    }

    // C-073: TriggerEmergencyStop — emergency halt (C-001)
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest request,
        ServerCallContext context)
    {
        // DESIGN_QUESTION: EmergencyStopEvent persistence deferred — confirm target sprint with EA.
        _logger.LogCritical(
            "TriggerEmergencyStop: ContractId={ContractId} StoppedBy={StoppedBy}",
            request.ContractId, request.StoppedBy);

        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = Guid.NewGuid().ToString()
        };
        response.AffectedSessions.AddRange(request.ActiveSessionIds);
        return Task.FromResult(response);
    }
}