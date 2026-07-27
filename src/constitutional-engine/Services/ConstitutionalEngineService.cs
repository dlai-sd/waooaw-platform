// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// Constitutional basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security), C-059 (Traceability)
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
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
    private readonly ITemporalClient? _temporalClient;
    private readonly ILogger<ConstitutionalEngineService> _logger;
    private readonly EvaluatorRegistry? _registry;

    public ConstitutionalEngineService(
        ConstitutionalDbContext db,
        EmergencyStopDbContext emergencyDb,
        ITemporalClient? temporalClient,
        ILogger<ConstitutionalEngineService> logger,
        EvaluatorRegistry? registry = null)
    {
        _db = db;
        _emergencyDb = emergencyDb;
        _temporalClient = temporalClient;
        _logger = logger;
        _registry = registry;
    }

    // ── RecordEvidence ──────────────────────────────────────────────────────────
    // C-023: every action produces an immutable evidence record before returning.

    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        var tenantIdStr = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";
        _ = Guid.TryParse(tenantIdStr, out var tenantId);

        var record = new EvidenceRecord
        {
            IdempotencyKey    = req.ActionInstanceId,
            TenantId          = tenantId,
            EvidenceType      = req.ActionType,
            Summary           = string.IsNullOrWhiteSpace(req.ProposedContent)
                                    ? req.ActionType
                                    : req.ProposedContent,
            PayloadJson       = null,
        };

        _db.EvidenceRecords.Add(record);
        await _db.SaveChangesAsync(ctx.CancellationToken);

        _logger.LogInformation(
            "RecordEvidence persisted id={Id} tenantId={TenantId} type={EvidenceType}",
            record.Id, record.TenantId, record.EvidenceType);

        return new RecordEvidenceResponse { EvidenceRecordId = record.Id.ToString() };
    }

    // ── ValidateAction ──────────────────────────────────────────────────────────
    // G-INSTINCT-01: constitution enforced at runtime via EvaluatorRegistry.
    // Default-deny: unknown contract or missing registry → DENY (C-041).

    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext ctx)
    {
        var ct       = ctx.CancellationToken;
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";

        // C-041 default deny — registry not wired means nothing is authorized.
        if (_registry is null)
        {
            _logger.LogWarning(
                "ValidateAction: EvaluatorRegistry not configured — default deny (C-041). " +
                "contract={ContractId}", req.ContractId);

            return new ValidateActionResponse
            {
                Decision            = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason              = "EvaluatorRegistry not configured; default deny per C-041."
            };
        }

        // Build the evaluation context from the inbound gRPC request.
        var evalCtx = EvaluationContext.FromRequest(req, tenantId);
        var results = await _registry.EvaluateAllAsync(evalCtx, ct);

        // Short-circuit on first DENY; accumulate first ESCALATE for fallback.
        EvaluationResult? firstDeny     = null;
        EvaluationResult? firstEscalate = null;

        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                firstDeny = result;
                break; // short-circuit per architecture/reference/ce-validate-action-evaluators.md
            }

            if (result.Verdict == EvaluationVerdict.Escalate && firstEscalate is null)
            {
                firstEscalate = result;
            }
        }

        if (firstDeny is not null)
        {
            _logger.LogInformation(
                "ValidateAction DENY — contract={ContractId} action={ActionType} " +
                "claim={ClaimId} reason={Reason}",
                req.ContractId, req.ActionType, firstDeny.ClaimId, firstDeny.Reason);

            return new ValidateActionResponse
            {
                Decision            = ValidationDecision.Deny,
                ConstitutionalBasis = firstDeny.ClaimId,
                Reason              = firstDeny.Reason
            };
        }

        if (firstEscalate is not null)
        {
            _logger.LogInformation(
                "ValidateAction ESCALATE — contract={ContractId} action={ActionType} " +
                "claim={ClaimId} reason={Reason}",
                req.ContractId, req.ActionType, firstEscalate.ClaimId, firstEscalate.Reason);

            return new ValidateActionResponse
            {
                Decision            = ValidationDecision.Escalate,
                ConstitutionalBasis = firstEscalate.ClaimId,
                Reason              = firstEscalate.Reason
            };
        }

        // All evaluators passed — compute optional remaining budget for the response.
        long budgetRemaining = req.BudgetContext is not null
            ? req.BudgetContext.ApprovedMonthlyBudgetInrPaise
              - req.BudgetContext.CurrentMonthSpendInrPaise
              - req.BudgetContext.ProposedSpendInrPaise
            : 0L;

        _logger.LogInformation(
            "ValidateAction ALLOW — contract={ContractId} action={ActionType} evaluators={Count}",
            req.ContractId, req.ActionType, results.Count);

        return new ValidateActionResponse
        {
            Decision                  = ValidationDecision.Allow,
            ConstitutionalBasis       = "CE-ALL",
            Reason                    = "All constitutional evaluators passed.",
            BudgetRemainingInrPaise   = budgetRemaining
        };
    }

    // ── GrantAuthorityLicense ───────────────────────────────────────────────────
    // C-003: authority requires an explicit license grant recorded in CE.

    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        _logger.LogInformation(
            "GrantAuthorityLicense contract={ContractId} level={Level} grantedBy={GrantedBy}",
            req.ContractId, req.NewAuthorityLevel, req.GrantedBy);

        var licenseId = Guid.NewGuid().ToString();
        return Task.FromResult(new GrantAuthorityResponse { LicenseId = licenseId });
    }

    // ── RevokeAuthorityLicense ──────────────────────────────────────────────────

    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        _logger.LogInformation(
            "RevokeAuthorityLicense contract={ContractId} level={Level} revokedBy={RevokedBy}",
            req.ContractId, req.NewAuthorityLevel, req.RevokedBy);

        var licenseId = Guid.NewGuid().ToString();
        return Task.FromResult(new RevokeAuthorityResponse { LicenseId = licenseId });
    }

    // ── EvaluatePolicy ──────────────────────────────────────────────────────────

    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
    {
        _logger.LogInformation("EvaluatePolicy invoked");
        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit
        });
    }

    // ── TriggerEmergencyStop ────────────────────────────────────────────────────
    // C-001: Emergency Stop is absolute — ≤250ms, persists before returning,
    //        optionally signals Temporal for distributed propagation.

    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
    {
        var ct = ctx.CancellationToken;

        _ = Guid.TryParse(req.ContractId, out var contractId);

        var stopEvent = new EmergencyStopEvent
        {
            ContractId          = contractId,
            InitiatedByUserId   = req.StoppedBy,
            AffectedSessionIds  = req.ActiveSessionIds.ToArray(),
            StopSource          = "gRPC"
        };

        _emergencyDb.EmergencyStopEvents.Add(stopEvent);
        await _emergencyDb.SaveChangesAsync(ct);

        _logger.LogCritical(
            "EmergencyStop persisted id={Id} contractId={ContractId} sessions={SessionCount}",
            stopEvent.Id, stopEvent.ContractId, stopEvent.AffectedSessionIds.Length);

        // Best-effort Temporal signal — C-001 must not be blocked by workflow client failure.
        if (_temporalClient is not null)
        {
            try
            {
                // Signal the running agent-session workflow to halt immediately.
                // Workflow / signal name contract defined in Temporal worker (ADR-007).
                var handle = _temporalClient.GetWorkflowHandle(req.ContractId);
                await handle.SignalAsync("emergency-stop", new[] { stopEvent.Id.ToString() });

                stopEvent.TemporalSignalledAt = DateTimeOffset.UtcNow;
                await _emergencyDb.SaveChangesAsync(CancellationToken.None);
            }
            catch (Exception ex)
            {
                // Log but do NOT rethrow — persist is complete; stop is in effect.
                _logger.LogError(ex,
                    "EmergencyStop Temporal signal failed for contractId={ContractId}. " +
                    "Stop record is persisted; signal delivery is best-effort.",
                    req.ContractId);
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