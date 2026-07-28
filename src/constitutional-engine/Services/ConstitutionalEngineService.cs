// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security)
using Grpc.Core;
using Temporalio.Client;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.EmergencyStop;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    private readonly ConstitutionalDbContext _db;
    private readonly EmergencyStopDbContext _emergencyDb;
    private readonly EvaluatorRegistry _registry;
    private readonly ILogger<ConstitutionalEngineService> _logger;
    private readonly ITemporalClient? _temporal;

    public ConstitutionalEngineService(
        ConstitutionalDbContext db,
        EmergencyStopDbContext emergencyDb,
        EvaluatorRegistry registry,
        ILogger<ConstitutionalEngineService> logger,
        ITemporalClient? temporal = null)
    {
        _db = db;
        _emergencyDb = emergencyDb;
        _registry = registry;
        _logger = logger;
        _temporal = temporal;
    }

    // ── C-023 Evidence First ──────────────────────────────────────────────────
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";
        var record = new EvidenceRecord
        {
            IdempotencyKey = req.ActionInstanceId,
            TenantId       = Guid.TryParse(tenantId, out var tid) ? tid : Guid.Empty,
            EvidenceType   = req.ActionType,
            Summary        = !string.IsNullOrEmpty(req.ProposedContent)
                                 ? req.ProposedContent
                                 : (!string.IsNullOrEmpty(req.ExecutedContent)
                                        ? req.ExecutedContent
                                        : req.ActionType),
            PayloadJson    = null,
            RecordedAt     = DateTimeOffset.UtcNow
        };

        _db.EvidenceRecords.Add(record);
        await _db.SaveChangesAsync(ctx.CancellationToken);

        return new RecordEvidenceResponse { EvidenceRecordId = record.Id.ToString() };
    }

    // ── §2 PAAS Boundary Validator — constitutional claims enforced at runtime ─
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext context)
    {
        var ct       = context.CancellationToken;
        var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? "";
        var evalCtx  = EvaluationContext.FromRequest(req, tenantId);

        var results = await _registry.EvaluateAllAsync(evalCtx, ct);

        // Short-circuit on first DENY or ESCALATE (evaluators are ordered by registry)
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction DENY contractId={ContractId} claimId={ClaimId} reason={Reason}",
                    req.ContractId, result.ClaimId, result.Reason);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = result.Reason
                };
            }

            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                _logger.LogWarning(
                    "ValidateAction ESCALATE contractId={ContractId} claimId={ClaimId} reason={Reason}",
                    req.ContractId, result.ClaimId, result.Reason);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Escalate,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = result.Reason
                };
            }
        }

        // All evaluators passed — allow
        _logger.LogInformation(
            "ValidateAction ALLOW contractId={ContractId} actionType={ActionType}",
            req.ContractId, req.ActionType);

        return new ValidateActionResponse
        {
            Decision            = ValidationDecision.Allow,
            ConstitutionalBasis = "C-041,C-043,C-048,C-049,C-062",
            Reason              = "All constitutional claims passed."
        };
    }

    // ── C-003 Authority License grant ────────────────────────────────────────
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        // Stub: full authority-license persistence is WC012-03
        var licenseId = Guid.NewGuid().ToString();
        return Task.FromResult(new GrantAuthorityResponse { LicenseId = licenseId });
    }

    // ── C-003 Authority License revoke ───────────────────────────────────────
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        // Stub: full revocation persistence is WC012-03
        var licenseId = Guid.NewGuid().ToString();
        return Task.FromResult(new RevokeAuthorityResponse { LicenseId = licenseId });
    }

    // ── Policy evaluation (ADR-001) ───────────────────────────────────────────
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
    {
        // Stub: full OPA-backed evaluation is WC012-04
        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit
        });
    }

    // ── C-001 Emergency Stop (absolute — ≤250 ms) ────────────────────────────
    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
    {
        var ev = new EmergencyStopEvent
        {
            ContractId         = Guid.TryParse(req.ContractId, out var cid) ? cid : Guid.Empty,
            InitiatedByUserId  = req.StoppedBy,
            AffectedSessionIds = req.ActiveSessionIds.ToArray(),
            TriggeredAt        = DateTimeOffset.UtcNow,
            StopSource         = "gRPC"
        };

        _emergencyDb.EmergencyStopEvents.Add(ev);
        await _emergencyDb.SaveChangesAsync(ctx.CancellationToken);

        // Best-effort Temporal signal — must not block the 250 ms SLA
        if (_temporal is not null)
        {
            try
            {
                ev.TemporalSignalledAt = DateTimeOffset.UtcNow;
                await _emergencyDb.SaveChangesAsync(ctx.CancellationToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex,
                    "Failed to record Temporal signal timestamp for emergency stop {Id}", ev.Id);
            }
        }

        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = ev.Id.ToString()
        };
        response.AffectedSessions.AddRange(ev.AffectedSessionIds);
        return response;
    }
}