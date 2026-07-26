// Implements: architecture/reference/components/constitutional-engine.md §1 §2 §4
// constitutional_basis: C-023 (Evidence First), C-003 (Authority Licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-051 (Resource Transparency), C-062 (AI Security),
//                       C-059 (Traceability), C-073 (Annotation), C-076 (Test Coverage)

#nullable enable

using System.Diagnostics;
using System.Text.Json;
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.EmergencyStop;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementing the WAOOAW Constitutional Engine boundary validator.
/// All AI agent actions must pass through this service before execution.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    // C-059: Traceability — named ActivitySource for OpenTelemetry distributed tracing
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ConstitutionalDbContext _dbContext;
    private readonly EmergencyStopDbContext _emergencyStopDbContext;
    private readonly EvaluatorRegistry _registry;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    // C-073: Constructor annotation — all constitutional dependencies injected here
    public ConstitutionalEngineService(
        ConstitutionalDbContext dbContext,
        EmergencyStopDbContext emergencyStopDbContext,
        EvaluatorRegistry registry,
        ILogger<ConstitutionalEngineService> logger)
    {
        ArgumentNullException.ThrowIfNull(dbContext);
        ArgumentNullException.ThrowIfNull(emergencyStopDbContext);
        ArgumentNullException.ThrowIfNull(registry);
        ArgumentNullException.ThrowIfNull(logger);

        _dbContext = dbContext;
        _emergencyStopDbContext = emergencyStopDbContext;
        _registry = registry;
        _logger = logger;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // §1 — Evidence First Enforcer (C-023)
    // ─────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Implements C-023 (Evidence First) — persists an immutable audit record
    /// before returning. Idempotent on ActionInstanceId (C-085).
    /// </summary>
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req,
        ServerCallContext ctx)
    {
        var ct = ctx.CancellationToken;
        using var activity = _tracer.StartActivity("RecordEvidence", ActivityKind.Server);

        // Extract and validate tenant ID from gRPC metadata
        var tenantIdRaw = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;
        if (string.IsNullOrWhiteSpace(tenantIdRaw))
        {
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                "x-tenant-id metadata header is required"));
        }

        if (!Guid.TryParse(tenantIdRaw, out var tenantId))
        {
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                $"x-tenant-id is not a valid GUID: '{tenantIdRaw}'"));
        }

        // Validate required fields
        if (string.IsNullOrWhiteSpace(req.ActionInstanceId))
        {
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                "ActionInstanceId is required"));
        }

        activity?.SetTag("tenant.id", tenantIdRaw);
        activity?.SetTag("action.instance.id", req.ActionInstanceId);
        activity?.SetTag("action.type", req.ActionType);

        // C-085 Idempotency — check for existing record before inserting
        var existingRecord = await _dbContext.EvidenceRecords
            .AsNoTracking()
            .FirstOrDefaultAsync(r => r.IdempotencyKey == req.ActionInstanceId, ct)
            .ConfigureAwait(false);

        if (existingRecord is not null)
        {
            _logger.LogInformation(
                "RecordEvidence idempotent return for ActionInstanceId={ActionInstanceId}, RecordId={RecordId}",
                req.ActionInstanceId, existingRecord.Id);
            return new RecordEvidenceResponse { EvidenceRecordId = existingRecord.Id.ToString() };
        }

        // C-027 (Append-Only) — construct new immutable record
        var record = new EvidenceRecord
        {
            Id = Guid.NewGuid(),
            IdempotencyKey = req.ActionInstanceId,
            TenantId = tenantId,
            EvidenceType = string.IsNullOrWhiteSpace(req.ActionType)
                ? "UNSPECIFIED"
                : req.ActionType.ToUpperInvariant(),
            Summary = string.IsNullOrWhiteSpace(req.ProposedContent)
                ? $"Evidence recorded for action {req.ActionInstanceId}"
                : req.ProposedContent,
            PayloadJson = JsonSerializer.Serialize(new
            {
                req.ActionInstanceId,
                req.ContractId,
                req.ProfessionalId,
                req.ActionType,
                State = req.State.ToString(),
                req.ConstitutionalBasis,
                req.DecisionSpaceVersion
            }),
            RecordedAt = DateTimeOffset.UtcNow
        };

        // C-023: Persist to DB before returning response
        await _dbContext.EvidenceRecords.AddAsync(record, ct).ConfigureAwait(false);
        await _dbContext.SaveChangesAsync(ct).ConfigureAwait(false);

        _logger.LogInformation(
            "EvidenceRecord persisted: Id={Id}, TenantId={TenantId}, ActionInstanceId={ActionInstanceId}",
            record.Id, tenantId, req.ActionInstanceId);

        return new RecordEvidenceResponse { EvidenceRecordId = record.Id.ToString() };
    }

    // ─────────────────────────────────────────────────────────────────────────
    // §2 — PAAS Boundary Validator (ValidateAction)
    // ─────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Implements §2 PAAS Boundary Validator.
    /// Evaluates a proposed agent action against all registered constitutional claim evaluators.
    /// Short-circuits on first DENY. Default-deny for missing ContractId or empty tenant.
    /// Constitutional basis: C-041, C-043, C-048, C-049, C-051, C-062.
    /// </summary>
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req,
        ServerCallContext ctx)
    {
        var ct = ctx.CancellationToken;
        using var activity = _tracer.StartActivity("ValidateAction", ActivityKind.Server);

        // ── Input validation ──────────────────────────────────────────────────

        // C-073: Extract tenant ID — required for constitutional evaluation context
        var tenantIdRaw = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;
        if (string.IsNullOrWhiteSpace(tenantIdRaw))
        {
            _logger.LogWarning("ValidateAction rejected: x-tenant-id header missing");
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                "x-tenant-id metadata header is required"));
        }

        // C-073 / C-041: Default-deny when ContractId is absent — unknown contracts are not authorized
        if (string.IsNullOrWhiteSpace(req.ContractId))
        {
            _logger.LogWarning(
                "ValidateAction denied — ContractId is empty. TenantId={TenantId}",
                tenantIdRaw);

            activity?.SetTag("decision", "Deny");
            activity?.SetTag("denied_by", "C-041");
            activity?.SetTag("deny_reason", "ContractId is required — unknown contracts are denied by default");

            return new ValidateActionResponse
            {
                Decision = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason = "ContractId is required. Unknown contracts are denied by default (C-041 default-deny)."
            };
        }

        activity?.SetTag("tenant.id", tenantIdRaw);
        activity?.SetTag("contract.id", req.ContractId);
        activity?.SetTag("action.type", req.ActionType);
        activity?.SetTag("decision_space.version", req.DecisionSpaceVersion);

        _logger.LogInformation(
            "ValidateAction started: ContractId={ContractId}, ActionType={ActionType}, TenantId={TenantId}",
            req.ContractId, req.ActionType, tenantIdRaw);

        // ── Build evaluation context ──────────────────────────────────────────

        // C-073: EvaluationContext.FromRequest maps proto fields to evaluator-facing record
        var evalCtx = EvaluationContext.FromRequest(req, tenantIdRaw);

        // ── Run evaluator pipeline ────────────────────────────────────────────

        IReadOnlyList<EvaluationResult> results;
        try
        {
            // C-073: EvaluateAllAsync short-circuits on first DENY per evaluator registry contract
            results = await _registry
                .EvaluateAllAsync(evalCtx, ct)
                .ConfigureAwait(false);
        }
        catch (RpcException)
        {
            // Re-throw gRPC exceptions unmodified
            throw;
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning(
                "ValidateAction cancelled for ContractId={ContractId}", req.ContractId);
            throw new RpcException(new Status(StatusCode.Cancelled, "ValidateAction was cancelled"));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "EvaluatorRegistry threw an unexpected exception during ValidateAction. ContractId={ContractId}",
                req.ContractId);
            throw new RpcException(new Status(StatusCode.Internal,
                "Constitutional evaluation pipeline encountered an internal error"));
        }

        // ── Inspect results — short-circuit on first non-Allow verdict ────────

        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                // C-073 / C-041: Any DENY produces an immediate deny response
                _logger.LogWarning(
                    "ValidateAction DENIED by {ClaimId}: {Reason}. ContractId={ContractId}, TenantId={TenantId}",
                    result.ClaimId, result.Reason, req.ContractId, tenantIdRaw);

                activity?.SetTag("decision", "Deny");
                activity?.SetTag("denied_by", result.ClaimId);

                return new ValidateActionResponse
                {
                    Decision = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason = result.Reason
                };
            }

            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                // C-073 / C-049: Escalate → uncertain action requires human review
                _logger.LogWarning(
                    "ValidateAction ESCALATED by {ClaimId}: {Reason}. ContractId={ContractId}, TenantId={TenantId}",
                    result.ClaimId, result.Reason, req.ContractId, tenantIdRaw);

                activity?.SetTag("decision", "Escalate");
                activity?.SetTag("escalated_by", result.ClaimId);

                return new ValidateActionResponse
                {
                    Decision = ValidationDecision.Escalate,
                    ConstitutionalBasis = result.ClaimId,
                    Reason = result.Reason
                };
            }
        }

        // ── All evaluators passed — compute budget remainder and authorize ─────

        // C-051 (Resource Transparency): Report remaining budget in response.
        // BudgetRemainingInrPaise is derived — BudgetRemainingInrPaise does NOT exist on EvaluationContext.
        var budgetRemaining =
            evalCtx.ApprovedBudgetInrPaise
            - evalCtx.CurrentSpendInrPaise
            - evalCtx.ProposedSpendInrPaise;

        _logger.LogInformation(
            "ValidateAction AUTHORIZED. ContractId={ContractId}, ActionType={ActionType}, " +
            "EvaluatorsRun={Count}, BudgetRemainingInrPaise={BudgetRemaining}, TenantId={TenantId}",
            req.ContractId, req.ActionType, results.Count, budgetRemaining, tenantIdRaw);

        activity?.SetTag("decision", "Allow");
        activity?.SetTag("evaluators.run", results.Count);
        activity?.SetTag("budget.remaining_inr_paise", budgetRemaining);

        return new ValidateActionResponse
        {
            Decision = ValidationDecision.Allow,
            ConstitutionalBasis = "C-041,C-043,C-048,C-049,C-062",
            Reason = $"All {results.Count} constitutional evaluators authorized this action.",
            BudgetRemainingInrPaise = budgetRemaining
        };
    }

    // ─────────────────────────────────────────────────────────────────────────
    // §3 — Authority License Management (C-003)
    // ─────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Stub — authority license grant. Implementation deferred to WC012-04.
    /// </summary>
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req,
        ServerCallContext ctx)
    {
        // DESIGN_QUESTION: Does GrantAuthority require a Temporal workflow signal or direct DB write?
        _logger.LogWarning(
            "GrantAuthorityLicense called but not yet implemented. ContractId={ContractId}",
            req.ContractId);

        throw new RpcException(new Status(StatusCode.Unimplemented,
            "GrantAuthorityLicense is not yet implemented (planned: WC012-04)"));
    }

    /// <summary>
    /// C-073: Stub — authority license revocation. Implementation deferred to WC012-04.
    /// </summary>
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req,
        ServerCallContext ctx)
    {
        // DESIGN_QUESTION: Does RevokeAuthority broadcast to active sessions via WebSocket?
        _logger.LogWarning(
            "RevokeAuthorityLicense called but not yet implemented. ContractId={ContractId}",
            req.ContractId);

        throw new RpcException(new Status(StatusCode.Unimplemented,
            "RevokeAuthorityLicense is not yet implemented (planned: WC012-04)"));
    }

    /// <summary>
    /// C-073: Stub — policy evaluation. Implementation deferred to WC012-05.
    /// </summary>
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req,
        ServerCallContext ctx)
    {
        _logger.LogWarning("EvaluatePolicy called but not yet implemented.");

        throw new RpcException(new Status(StatusCode.Unimplemented,
            "EvaluatePolicy is not yet implemented (planned: WC012-05)"));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // §4 — Emergency Stop (C-001)
    // ─────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Implements C-001 (Emergency Stop — absolute). Records stop event and
    /// returns affected session IDs. Temporal signal integration deferred to WC012-06.
    /// </summary>
    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req,
        ServerCallContext ctx)
    {
        var ct = ctx.CancellationToken;
        using var activity = _tracer.StartActivity("TriggerEmergencyStop", ActivityKind.Server);

        if (!Guid.TryParse(req.ContractId, out var contractId))
        {
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                $"ContractId is not a valid GUID: '{req.ContractId}'"));
        }

        if (string.IsNullOrWhiteSpace(req.StoppedBy))
        {
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                "StoppedBy is required"));
        }

        activity?.SetTag("contract.id", req.ContractId);
        activity?.SetTag("stopped_by", req.StoppedBy);

        var stopEvent = new EmergencyStopEvent
        {
            Id = Guid.NewGuid(),
            ContractId = contractId,
            InitiatedByUserId = req.StoppedBy,
            AffectedSessionIds = req.ActiveSessionIds.ToArray(),
            TriggeredAt = DateTimeOffset.UtcNow,
            StopSource = "gRPC"
            // TemporalSignalledAt — set by WC012-06 Temporal integration task
        };

        await _emergencyStopDbContext.EmergencyStopEvents
            .AddAsync(stopEvent, ct)
            .ConfigureAwait(false);
        await _emergencyStopDbContext.SaveChangesAsync(ct).ConfigureAwait(false);

        _logger.LogCritical(
            "EmergencyStop recorded: RecordId={RecordId}, ContractId={ContractId}, " +
            "InitiatedBy={InitiatedBy}, AffectedSessions={SessionCount}",
            stopEvent.Id, req.ContractId, req.StoppedBy, stopEvent.AffectedSessionIds.Length);

        activity?.SetTag("emergency_stop.record_id", stopEvent.Id.ToString());

        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = stopEvent.Id.ToString()
        };
        response.AffectedSessions.AddRange(stopEvent.AffectedSessionIds);
        return response;
    }
}