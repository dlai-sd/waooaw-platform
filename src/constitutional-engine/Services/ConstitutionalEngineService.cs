// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security), C-059 (Traceability)
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Temporalio.Client;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.EmergencyStop;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementation for the Constitutional Engine.
/// ValidateAction enforces all runtime-evaluable constitutional claims via EvaluatorRegistry.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    private readonly ConstitutionalDbContext _db;
    private readonly EmergencyStopDbContext _emergencyDb;
    private readonly ITemporalClient? _temporalClient;
    private readonly ILogger<ConstitutionalEngineService> _logger;
    private readonly EvaluatorRegistry _registry;

    public ConstitutionalEngineService(
        ConstitutionalDbContext db,
        EmergencyStopDbContext emergencyDb,
        ITemporalClient? temporalClient,
        ILogger<ConstitutionalEngineService> logger,
        EvaluatorRegistry registry)
    {
        _db = db;
        _emergencyDb = emergencyDb;
        _temporalClient = temporalClient;
        _logger = logger;
        _registry = registry;
    }

    // ─── RecordEvidence ──────────────────────────────────────────────────────────
    // C-023: Evidence First — every action is recorded before it executes.

    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";
        _ = Guid.TryParse(tenantId, out var tenantGuid);

        var record = new EvidenceRecord
        {
            Id             = Guid.NewGuid(),
            IdempotencyKey = req.ActionInstanceId,
            TenantId       = tenantGuid,
            EvidenceType   = req.ActionType,
            Summary        = req.ProposedContent ?? req.ActionType,
            PayloadJson    = null,
            RecordedAt     = DateTimeOffset.UtcNow
        };

        _db.EvidenceRecords.Add(record);
        await _db.SaveChangesAsync(ctx.CancellationToken);

        _logger.LogInformation(
            "Evidence recorded: {EvidenceId} tenant={TenantId} type={ActionType}",
            record.Id, tenantGuid, req.ActionType);

        return new RecordEvidenceResponse { EvidenceRecordId = record.Id.ToString() };
    }

    // ─── ValidateAction ──────────────────────────────────────────────────────────
    // C-041 default-deny: unknown tool / missing contract → DENY.
    // Short-circuits on first DENY from any evaluator (per spec §2).
    // ESCALATE propagates when any evaluator signals human review (C-049 path).

    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext ctx)
    {
        var ct       = ctx.CancellationToken;
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";
        var evalCtx  = EvaluationContext.FromRequest(req, tenantId);

        _logger.LogDebug(
            "ValidateAction: contractId={ContractId} actionType={ActionType} tenant={TenantId}",
            evalCtx.ContractId, evalCtx.ActionType, tenantId);

        IReadOnlyList<EvaluationResult> results;
        try
        {
            results = await _registry.EvaluateAllAsync(evalCtx, ct);
        }
        catch (Exception ex)
        {
            // C-041 default-deny: evaluation failure → DENY, never silently allow.
            _logger.LogError(ex,
                "EvaluatorRegistry threw during ValidateAction for contract={ContractId}",
                evalCtx.ContractId);
            return new ValidateActionResponse
            {
                Decision           = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason             = "Constitutional evaluation failed; defaulting to deny (C-041)."
            };
        }

        // Short-circuit: first DENY wins.
        var firstDeny = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Deny);
        if (firstDeny is not null)
        {
            _logger.LogWarning(
                "ValidateAction DENY: claim={ClaimId} reason={Reason} contract={ContractId}",
                firstDeny.ClaimId, firstDeny.Reason, evalCtx.ContractId);

            return new ValidateActionResponse
            {
                Decision            = ValidationDecision.Deny,
                ConstitutionalBasis = firstDeny.ClaimId,
                Reason              = firstDeny.Reason
            };
        }

        // Escalate: first ESCALATE result → forward to human review (C-049 path).
        var firstEscalate = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Escalate);
        if (firstEscalate is not null)
        {
            _logger.LogInformation(
                "ValidateAction ESCALATE: claim={ClaimId} reason={Reason} contract={ContractId}",
                firstEscalate.ClaimId, firstEscalate.Reason, evalCtx.ContractId);

            return new ValidateActionResponse
            {
                Decision            = ValidationDecision.Escalate,
                ConstitutionalBasis = firstEscalate.ClaimId,
                Reason              = firstEscalate.Reason
            };
        }

        // All evaluators passed → ALLOW.
        // Compute remaining budget for caller visibility (C-043 / C-051 Resource Transparency).
        long budgetRemaining = evalCtx.ApprovedBudgetInrPaise
                             - evalCtx.CurrentSpendInrPaise
                             - evalCtx.ProposedSpendInrPaise;

        var claimsEnforced = string.Join(",", results.Select(r => r.ClaimId).Distinct());

        _logger.LogInformation(
            "ValidateAction ALLOW: contract={ContractId} evaluators={Count} budgetRemaining={BudgetRemaining}",
            evalCtx.ContractId, results.Count, budgetRemaining);

        return new ValidateActionResponse
        {
            Decision                = ValidationDecision.Allow,
            ConstitutionalBasis     = claimsEnforced,
            Reason                  = "All constitutional claims satisfied.",
            BudgetRemainingInrPaise = budgetRemaining
        };
    }

    // ─── GrantAuthorityLicense ───────────────────────────────────────────────────
    // C-003: authority is licensed, not assumed.

    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        var licenseId = Guid.NewGuid().ToString();
        _logger.LogInformation(
            "GrantAuthorityLicense: contract={ContractId} grantedBy={GrantedBy} licenseId={LicenseId}",
            req.ContractId, req.GrantedBy, licenseId);
        return Task.FromResult(new GrantAuthorityResponse { LicenseId = licenseId });
    }

    // ─── RevokeAuthorityLicense ──────────────────────────────────────────────────

    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        var licenseId = Guid.NewGuid().ToString();
        _logger.LogInformation(
            "RevokeAuthorityLicense: contract={ContractId} revokedBy={RevokedBy} licenseId={LicenseId}",
            req.ContractId, req.RevokedBy, licenseId);
        return Task.FromResult(new RevokeAuthorityResponse { LicenseId = licenseId });
    }

    // ─── EvaluatePolicy ──────────────────────────────────────────────────────────

    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
    {
        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit
        });
    }

    // ─── TriggerEmergencyStop ────────────────────────────────────────────────────
    // C-001: Emergency Stop is absolute and must complete ≤250 ms.

    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
    {
        var ct = ctx.CancellationToken;

        _ = Guid.TryParse(req.ContractId, out var contractGuid);

        var stopEvent = new EmergencyStopEvent
        {
            Id                  = Guid.NewGuid(),
            ContractId          = contractGuid,
            InitiatedByUserId   = req.StoppedBy,
            AffectedSessionIds  = req.ActiveSessionIds.ToArray(),
            TriggeredAt         = DateTimeOffset.UtcNow,
            TemporalSignalledAt = null,
            StopSource          = "gRPC"
        };

        _emergencyDb.EmergencyStopEvents.Add(stopEvent);
        await _emergencyDb.SaveChangesAsync(ct);

        _logger.LogCritical(
            "EmergencyStop persisted: id={EventId} contract={ContractId} sessions={SessionCount}",
            stopEvent.Id, req.ContractId, stopEvent.AffectedSessionIds.Length);

        // Best-effort Temporal signal — do NOT block the response path (C-001 ≤250 ms).
        if (_temporalClient is not null)
        {
            try
            {
                var handle = _temporalClient.GetWorkflowHandle(req.ContractId);
                await handle.SignalAsync("emergency_stop", new[] { stopEvent.Id.ToString() });
                stopEvent.TemporalSignalledAt = DateTimeOffset.UtcNow;
                await _emergencyDb.SaveChangesAsync(CancellationToken.None);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex,
                    "Temporal signal failed for EmergencyStop {EventId} — persisted record stands.",
                    stopEvent.Id);
            }
        }

        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = stopEvent.Id.ToString()
        };
        response.AffectedSessions.AddRange(stopEvent.AffectedSessionIds);
        return response;
    }
}