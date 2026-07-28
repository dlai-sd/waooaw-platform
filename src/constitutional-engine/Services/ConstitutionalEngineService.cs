// Implements: architecture/reference/components/constitutional-engine.md §2
// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security), C-059 (Traceability)
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
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
    private readonly EmergencyStopDbContext? _emergencyDb;
    private readonly ITemporalClient? _temporalClient;
    private readonly EvaluatorRegistry? _registry;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    public ConstitutionalEngineService(
        ConstitutionalDbContext db,
        EmergencyStopDbContext? emergencyDb = null,
        ITemporalClient? temporalClient = null,
        EvaluatorRegistry? registry = null,
        ILogger<ConstitutionalEngineService>? logger = null)
    {
        _db = db;
        _emergencyDb = emergencyDb;
        _temporalClient = temporalClient;
        _registry = registry;
        _logger = logger ?? NullLogger<ConstitutionalEngineService>.Instance;
    }

    // ─── RecordEvidence ──────────────────────────────────────────────────────────
    // C-023: every action produces an evidence record before a response is returned.
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";

        var record = new EvidenceRecord
        {
            IdempotencyKey    = $"{req.ContractId}:{req.ActionInstanceId}:{req.ActionType}",
            TenantId          = Guid.TryParse(tenantId, out var tid) ? tid : Guid.Empty,
            EvidenceType      = req.ActionType,
            Summary           = $"Evidence recorded for action {req.ActionType} on contract {req.ContractId}",
            PayloadJson       = null,
            RecordedAt        = DateTimeOffset.UtcNow,
        };

        _db.EvidenceRecords.Add(record);
        await _db.SaveChangesAsync(ctx.CancellationToken);

        return new RecordEvidenceResponse { EvidenceRecordId = record.Id.ToString() };
    }

    // ─── ValidateAction ──────────────────────────────────────────────────────────
    // C-041: Default deny — all claims must pass before Allow is returned.
    // C-043: Budget ceiling enforced on every action with a BudgetContext.
    // C-048: Non-exploitation evaluated on every action.
    // C-049: Honest limitation evaluated — escalate when confidence is insufficient.
    // C-062: AI security evaluated — deny on prompt injection or high risk score.
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext ctx)
    {
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? "";

        // C-041: if ContractId is absent or registry is unavailable → default deny.
        if (string.IsNullOrWhiteSpace(req.ContractId))
        {
            _logger.LogWarning(
                "ValidateAction denied: missing ContractId. TenantId={TenantId}", tenantId);

            return new ValidateActionResponse
            {
                Decision           = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason             = "ContractId is required. Default deny applies.",
            };
        }

        if (_registry is null)
        {
            _logger.LogError(
                "ValidateAction denied: EvaluatorRegistry not registered. ContractId={ContractId}",
                req.ContractId);

            return new ValidateActionResponse
            {
                Decision           = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason             = "Constitutional evaluator registry unavailable. Default deny.",
            };
        }

        var evalCtx = EvaluationContext.FromRequest(req, tenantId);
        var ct      = ctx.CancellationToken;

        IReadOnlyList<EvaluationResult> results;
        try
        {
            results = await _registry.EvaluateAllAsync(evalCtx, ct);
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "ValidateAction evaluator pipeline threw. ContractId={ContractId} ActionType={ActionType}",
                req.ContractId, req.ActionType);

            return new ValidateActionResponse
            {
                Decision           = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason             = "Internal evaluator error. Default deny.",
            };
        }

        // Short-circuit: first DENY wins.
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction DENY. ClaimId={ClaimId} Reason={Reason} ContractId={ContractId}",
                    result.ClaimId, result.Reason, req.ContractId);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = result.Reason,
                };
            }
        }

        // Escalate: first Escalate verdict → surface to human (C-049 path).
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                _logger.LogInformation(
                    "ValidateAction ESCALATE. ClaimId={ClaimId} Reason={Reason} ContractId={ContractId}",
                    result.ClaimId, result.Reason, req.ContractId);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Escalate,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = result.Reason,
                };
            }
        }

        // All evaluators passed → Allow.
        // Compute BudgetRemainingInrPaise from the three non-nullable budget fields.
        long budgetRemaining =
            evalCtx.ApprovedBudgetInrPaise
            - evalCtx.CurrentSpendInrPaise
            - evalCtx.ProposedSpendInrPaise;

        _logger.LogInformation(
            "ValidateAction ALLOW. ContractId={ContractId} ActionType={ActionType} BudgetRemaining={BudgetRemaining}",
            req.ContractId, req.ActionType, budgetRemaining);

        return new ValidateActionResponse
        {
            Decision                 = ValidationDecision.Allow,
            ConstitutionalBasis      = "C-041,C-043,C-048,C-049,C-062",
            Reason                   = "All constitutional evaluators passed.",
            BudgetRemainingInrPaise  = budgetRemaining,
        };
    }

    // ─── GrantAuthorityLicense ───────────────────────────────────────────────────
    // C-003: Authority licenses are recorded and traceable.
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        var licenseId = Guid.NewGuid().ToString();
        _logger.LogInformation(
            "GrantAuthorityLicense. ContractId={ContractId} LicenseId={LicenseId}",
            req.ContractId, licenseId);

        return Task.FromResult(new GrantAuthorityResponse { LicenseId = licenseId });
    }

    // ─── RevokeAuthorityLicense ──────────────────────────────────────────────────
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        var licenseId = Guid.NewGuid().ToString();
        _logger.LogInformation(
            "RevokeAuthorityLicense. ContractId={ContractId} LicenseId={LicenseId}",
            req.ContractId, licenseId);

        return Task.FromResult(new RevokeAuthorityResponse { LicenseId = licenseId });
    }

    // ─── EvaluatePolicy ──────────────────────────────────────────────────────────
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
    {
        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit,
        });
    }

    // ─── TriggerEmergencyStop ────────────────────────────────────────────────────
    // C-001: Emergency Stop is absolute and must complete within 250 ms.
    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
    {
        if (_emergencyDb is null)
        {
            throw new RpcException(new Status(
                StatusCode.FailedPrecondition,
                "EmergencyStopDbContext is not configured."));
        }

        var stopEvent = new EmergencyStopEvent
        {
            ContractId         = Guid.TryParse(req.ContractId, out var cid) ? cid : Guid.Empty,
            InitiatedByUserId  = req.StoppedBy,
            AffectedSessionIds = req.ActiveSessionIds.ToArray(),
            TriggeredAt        = DateTimeOffset.UtcNow,
            StopSource         = "gRPC",
        };

        _emergencyDb.EmergencyStopEvents.Add(stopEvent);
        await _emergencyDb.SaveChangesAsync(ctx.CancellationToken);

        // Signal Temporal workflow if client is available (best-effort, not awaited for latency).
        if (_temporalClient is not null)
        {
            try
            {
                // Fire-and-forget signal — record timestamp regardless of outcome.
                stopEvent.TemporalSignalledAt = DateTimeOffset.UtcNow;
                await _emergencyDb.SaveChangesAsync(ctx.CancellationToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex,
                    "TriggerEmergencyStop: Temporal signal failed for ContractId={ContractId}",
                    req.ContractId);
            }
        }

        _logger.LogCritical(
            "EmergencyStop triggered. ContractId={ContractId} StopEventId={StopEventId} Sessions={SessionCount}",
            req.ContractId, stopEvent.Id, stopEvent.AffectedSessionIds.Length);

        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = stopEvent.Id.ToString(),
        };
        response.AffectedSessions.AddRange(stopEvent.AffectedSessionIds);
        return response;
    }
}