// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
//             architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-051 (Resource Transparency), C-062 (AI Security),
//                       C-059 (Traceability), C-073 (Annotation), C-076 (≥90% unit test coverage)

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
/// gRPC service implementing the WAOOAW Constitutional Engine boundary validator.
/// All constitutional obligations are enforced here before any agent action is permitted.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    // C-059: OpenTelemetry tracer for distributed tracing of constitutional decisions
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ConstitutionalDbContext _dbContext;
    private readonly EvaluatorRegistry _registry;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    public ConstitutionalEngineService(
        ConstitutionalDbContext dbContext,
        EvaluatorRegistry registry,
        ILogger<ConstitutionalEngineService> logger)
    {
        ArgumentNullException.ThrowIfNull(dbContext);
        ArgumentNullException.ThrowIfNull(registry);
        ArgumentNullException.ThrowIfNull(logger);

        _dbContext = dbContext;
        _registry = registry;
        _logger = logger;
    }

    // ──────────────────────────────────────────────────────────────────────────
    // §1  Evidence First Enforcer — RecordEvidence
    // ──────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: RecordEvidence implements C-023 Evidence First — every agent action
    /// creates an immutable audit record before execution is permitted.
    /// </summary>
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        var ct = ctx.CancellationToken;

        using var activity = _tracer.StartActivity("RecordEvidence", ActivityKind.Server);

        // Extract and validate tenant ID from gRPC metadata (C-059 traceability)
        var tenantIdRaw = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;
        if (!Guid.TryParse(tenantIdRaw, out var tenantId))
        {
            _logger.LogWarning("RecordEvidence rejected — invalid x-tenant-id={TenantId}", tenantIdRaw);
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                $"x-tenant-id header must be a valid GUID, got: '{tenantIdRaw}'"));
        }

        // Validate action instance ID
        if (string.IsNullOrWhiteSpace(req.ActionInstanceId))
        {
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                "ActionInstanceId is required and must not be empty or whitespace."));
        }

        activity?.SetTag("tenant_id", tenantId.ToString());
        activity?.SetTag("action_instance_id", req.ActionInstanceId);
        activity?.SetTag("action_type", req.ActionType);

        // C-085 idempotency: return existing record if already written
        var existing = await _dbContext.EvidenceRecords
            .FirstOrDefaultAsync(r => r.IdempotencyKey == req.ActionInstanceId
                                   && r.TenantId == tenantId, ct);

        if (existing is not null)
        {
            _logger.LogInformation(
                "RecordEvidence idempotent hit — ActionInstanceId={ActionInstanceId} TenantId={TenantId}",
                req.ActionInstanceId, tenantId);
            return new RecordEvidenceResponse { EvidenceRecordId = existing.Id.ToString() };
        }

        // C-027 append-only: INSERT only, never UPDATE or DELETE
        var record = new EvidenceRecord
        {
            IdempotencyKey  = req.ActionInstanceId,
            TenantId        = tenantId,
            EvidenceType    = req.ActionType,
            Summary         = $"Evidence recorded for action '{req.ActionType}' on contract '{req.ContractId}'.",
            PayloadJson     = JsonSerializer.Serialize(new
            {
                req.ContractId,
                req.ActionType,
                req.ActionInstanceId,
                req.ProposedContent,
                req.ConstitutionalBasis,
                req.DecisionSpaceVersion
            }),
            RecordedAt = DateTimeOffset.UtcNow
        };

        _dbContext.EvidenceRecords.Add(record);
        await _dbContext.SaveChangesAsync(ct);

        _logger.LogInformation(
            "RecordEvidence persisted — Id={RecordId} ActionInstanceId={ActionInstanceId} TenantId={TenantId}",
            record.Id, req.ActionInstanceId, tenantId);

        return new RecordEvidenceResponse { EvidenceRecordId = record.Id.ToString() };
    }

    // ──────────────────────────────────────────────────────────────────────────
    // §2  PAAS Boundary Validator — ValidateAction
    // ──────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: ValidateAction implements the constitution-as-code principle.
    /// Every agent action must pass ALL registered claim evaluators before execution
    /// is permitted. Default deny — unlisted tool or empty ContractId → DENY.
    /// Short-circuits on the first DENY or Escalate result.
    /// Constitutional basis: C-041, C-043, C-048, C-049, C-051, C-062.
    /// </summary>
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext ctx)
    {
        var ct = ctx.CancellationToken;

        using var activity = _tracer.StartActivity("ValidateAction", ActivityKind.Server);
        activity?.SetTag("contract_id", req.ContractId);
        activity?.SetTag("action_type", req.ActionType);
        activity?.SetTag("decision_space_version", req.DecisionSpaceVersion);

        // C-041: Default deny — ContractId is required to identify the decision space boundary
        if (string.IsNullOrWhiteSpace(req.ContractId))
        {
            _logger.LogWarning(
                "ValidateAction DENY — ContractId missing. ActionType={ActionType}", req.ActionType);
            activity?.SetTag("decision", "DENY");
            activity?.SetTag("constitutional_basis", "C-041");
            return new ValidateActionResponse
            {
                Decision           = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason             = "ContractId is required. Default deny: no decision space boundary identified."
            };
        }

        // Extract tenant ID from gRPC metadata (C-059 traceability)
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        activity?.SetTag("tenant_id", tenantId);

        // Build evaluation context from the incoming request
        var evalCtx = EvaluationContext.FromRequest(req, tenantId);

        // Run all claim evaluators — any DENY or Escalate short-circuits (C-041 architecture)
        IReadOnlyList<EvaluationResult> results;
        try
        {
            results = await _registry.EvaluateAllAsync(evalCtx, ct);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning(
                "ValidateAction cancelled — ContractId={ContractId} TenantId={TenantId}",
                req.ContractId, tenantId);
            throw;
        }

        // Inspect evaluator results — short-circuit on first non-Allow verdict
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction DENY — ClaimId={ClaimId} ContractId={ContractId} "
                    + "TenantId={TenantId} Reason={Reason}",
                    result.ClaimId, req.ContractId, tenantId, result.Reason);

                activity?.SetTag("decision", "DENY");
                activity?.SetTag("constitutional_basis", result.ClaimId);
                activity?.SetTag("deny_reason", result.Reason);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = result.Reason
                };
            }

            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                // C-049: Honest limitation — uncertain action escalated to human (Sujay)
                // Conservative treatment: escalated actions are denied until human resolution
                _logger.LogWarning(
                    "ValidateAction ESCALATE→DENY — ClaimId={ClaimId} ContractId={ContractId} "
                    + "TenantId={TenantId} Reason={Reason}",
                    result.ClaimId, req.ContractId, tenantId, result.Reason);

                activity?.SetTag("decision", "ESCALATE");
                activity?.SetTag("constitutional_basis", result.ClaimId);
                activity?.SetTag("escalate_reason", result.Reason);

                // DESIGN_QUESTION: Should Escalate surface as a distinct ValidationDecision proto value,
                // or remain mapped to Deny until C-049 escalation workflow is wired? Flagged for EA review.
                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = $"Escalated to human review — action uncertain: {result.Reason}"
                };
            }
        }

        // All evaluators passed → AUTHORIZED
        // C-051: Compute remaining budget for transparency — uses three non-nullable longs
        var budgetRemaining = evalCtx.ApprovedBudgetInrPaise
                            - evalCtx.CurrentSpendInrPaise
                            - evalCtx.ProposedSpendInrPaise;

        _logger.LogInformation(
            "ValidateAction ALLOW — ContractId={ContractId} TenantId={TenantId} "
            + "ActionType={ActionType} BudgetRemainingPaise={BudgetRemaining}",
            req.ContractId, tenantId, req.ActionType, budgetRemaining);

        activity?.SetTag("decision", "ALLOW");
        activity?.SetTag("budget_remaining_paise", budgetRemaining);

        return new ValidateActionResponse
        {
            Decision            = ValidationDecision.Allow,
            ConstitutionalBasis = "C-041 C-043 C-048 C-049 C-062",
            Reason              = "All constitutional claim evaluators passed.",
            BudgetRemainingInrPaise = budgetRemaining
        };
    }

    // ──────────────────────────────────────────────────────────────────────────
    // §3  Authority License Manager — GrantAuthorityLicense / RevokeAuthorityLicense
    // ──────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: GrantAuthorityLicense — C-003 authority must be explicitly licensed.
    /// </summary>
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        // DESIGN_QUESTION: GrantAuthorityLicense full implementation is out of scope for WC012-02b.
        // Stub returns NotImplemented to prevent silent pass-through of unlicensed authority grants.
        throw new RpcException(new Status(StatusCode.Unimplemented,
            "GrantAuthorityLicense not yet implemented. See WC012 backlog for authority licensing sprint."));
    }

    /// <summary>
    /// C-073: RevokeAuthorityLicense — C-003 authority may be revoked at any time.
    /// </summary>
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        // DESIGN_QUESTION: RevokeAuthorityLicense full implementation is out of scope for WC012-02b.
        throw new RpcException(new Status(StatusCode.Unimplemented,
            "RevokeAuthorityLicense not yet implemented. See WC012 backlog for authority licensing sprint."));
    }

    // ──────────────────────────────────────────────────────────────────────────
    // §5  Policy Evaluator — EvaluatePolicy
    // ──────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: EvaluatePolicy — evaluates a free-form policy expression against context.
    /// </summary>
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
    {
        // DESIGN_QUESTION: EvaluatePolicy full implementation pending policy expression spec.
        throw new RpcException(new Status(StatusCode.Unimplemented,
            "EvaluatePolicy not yet implemented. See WC012 backlog for policy evaluation sprint."));
    }

    // ──────────────────────────────────────────────────────────────────────────
    // §4  Emergency Stop — TriggerEmergencyStop
    // ──────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: TriggerEmergencyStop implements C-001 Emergency Stop (absolute constitutional right).
    /// All active sessions for the contract are immediately halted. No override is possible.
    /// </summary>
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
    {
        // DESIGN_QUESTION: TriggerEmergencyStop full Temporal signal wiring is out of scope for WC012-02b.
        // Preserving stub from prior task — full implementation in WC012-04 (Emergency Stop sprint).
        throw new RpcException(new Status(StatusCode.Unimplemented,
            "TriggerEmergencyStop Temporal integration not yet wired. See WC012-04."));
    }
}