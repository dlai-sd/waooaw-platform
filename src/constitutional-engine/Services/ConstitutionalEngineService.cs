// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security)

using Grpc.Core;
using Microsoft.Extensions.Logging;
using System.Diagnostics;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementing all constitutional engine endpoints.
/// ValidateAction enforces the five runtime-evaluatable claims via EvaluatorRegistry.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<ConstitutionalEngineService> _logger;
    private readonly EvaluatorRegistry _registry;

    public ConstitutionalEngineService(
        ILogger<ConstitutionalEngineService> logger,
        EvaluatorRegistry registry)
    {
        ArgumentNullException.ThrowIfNull(logger);
        ArgumentNullException.ThrowIfNull(registry);
        _logger = logger;
        _registry = registry;
    }

    // C-073: Implements C-023 (Evidence First) — every action produces an audit record
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);

        using var activity = _tracer.StartActivity("RecordEvidence", ActivityKind.Server);
        activity?.SetTag("contract_id", req.ContractId);
        activity?.SetTag("action_type", req.ActionType);

        // DESIGN_QUESTION: EF Core persistence via ConstitutionalDbContext is WC012-03a.
        // Until that task lands, evidence is logged structurally and a synthetic ID returned.
        var evidenceRecordId = Guid.NewGuid().ToString("N");

        _logger.LogInformation(
            "RecordEvidence ContractId={ContractId} ActionType={ActionType} State={State} " +
            "EvidenceRecordId={EvidenceRecordId}",
            req.ContractId, req.ActionType, req.State, evidenceRecordId);

        activity?.SetTag("evidence_record_id", evidenceRecordId);

        return new RecordEvidenceResponse { EvidenceRecordId = evidenceRecordId };
    }

    // C-073: Implements C-041, C-043, C-048, C-049, C-062 — constitutional claim evaluation
    //        at the PAAS Decision Space boundary. Short-circuits on first DENY.
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);

        using var activity = _tracer.StartActivity("ValidateAction", ActivityKind.Server);
        activity?.SetTag("contract_id", req.ContractId);
        activity?.SetTag("action_type", req.ActionType);

        var ct = ctx.CancellationToken;

        // C-073: Extract TenantId from gRPC metadata per C-059 traceability contract
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;
        activity?.SetTag("tenant_id", tenantId);

        _logger.LogInformation(
            "ValidateAction BEGIN ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
            req.ContractId, req.ActionType, tenantId);

        // Default deny: ContractId must be present before evaluators run
        if (string.IsNullOrWhiteSpace(req.ContractId))
        {
            _logger.LogWarning(
                "ValidateAction DEFAULT DENY: ContractId absent. TenantId={TenantId}", tenantId);
            activity?.SetTag("validate_action.verdict", "Deny");
            activity?.SetTag("validate_action.basis", "DEFAULT_DENY");
            return new ValidateActionResponse
            {
                Decision = ValidationDecision.Deny,
                ConstitutionalBasis = "DEFAULT_DENY",
                Reason = "ContractId is required — all actions require an active contract."
            };
        }

        // Build evaluation context from the incoming request
        var evalCtx = EvaluationContext.FromRequest(req, tenantId);

        // Run all applicable evaluators via registry; short-circuit on first DENY or ESCALATE
        IReadOnlyList<EvaluationResult> results;
        try
        {
            results = await _registry.EvaluateAllAsync(evalCtx, ct).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning(
                "ValidateAction CANCELLED. ContractId={ContractId} TenantId={TenantId}",
                req.ContractId, tenantId);
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "ValidateAction EVALUATOR FAULT. ContractId={ContractId} TenantId={TenantId}",
                req.ContractId, tenantId);
            // Fail-closed: evaluator fault → deny
            activity?.SetTag("validate_action.verdict", "Deny");
            return new ValidateActionResponse
            {
                Decision = ValidationDecision.Deny,
                ConstitutionalBasis = "EVALUATOR_FAULT",
                Reason = "Constitutional evaluator encountered an unexpected error — action denied (fail-closed)."
            };
        }

        // Inspect results — EvaluatorRegistry short-circuits on first non-Allow internally,
        // but we also check here for transparency and to build the response.
        foreach (var result in results)
        {
            activity?.SetTag($"evaluator.{result.ClaimId}.verdict", result.Verdict.ToString());

            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction DENY ClaimId={ClaimId} Reason={Reason} " +
                    "ContractId={ContractId} TenantId={TenantId}",
                    result.ClaimId, result.Reason, req.ContractId, tenantId);
                activity?.SetTag("validate_action.verdict", "Deny");
                activity?.SetTag("validate_action.deny_claim", result.ClaimId);

                // Budget remaining is informational on budget-related denials
                long? budgetRemaining = result.ClaimId == "C-043" && req.BudgetContext is not null
                    ? req.BudgetContext.ApprovedMonthlyBudgetInrPaise - req.BudgetContext.CurrentMonthSpendInrPaise
                    : null;

                var denyResponse = new ValidateActionResponse
                {
                    Decision = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason = result.Reason
                };
                if (budgetRemaining.HasValue)
                    denyResponse.BudgetRemainingInrPaise = budgetRemaining.Value;

                return denyResponse;
            }

            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                _logger.LogInformation(
                    "ValidateAction ESCALATE ClaimId={ClaimId} Reason={Reason} " +
                    "ContractId={ContractId} TenantId={TenantId}",
                    result.ClaimId, result.Reason, req.ContractId, tenantId);
                activity?.SetTag("validate_action.verdict", "Escalate");
                activity?.SetTag("validate_action.escalate_claim", result.ClaimId);

                return new ValidateActionResponse
                {
                    Decision = ValidationDecision.Escalate,
                    ConstitutionalBasis = result.ClaimId,
                    Reason = result.Reason
                };
            }
        }

        // All evaluators passed → ALLOW
        _logger.LogInformation(
            "ValidateAction ALLOW ContractId={ContractId} TenantId={TenantId} EvaluatorCount={Count}",
            req.ContractId, tenantId, results.Count);
        activity?.SetTag("validate_action.verdict", "Allow");
        activity?.SetTag("validate_action.evaluator_count", results.Count);

        var budgetRemainingOnAllow = req.BudgetContext is not null
            ? req.BudgetContext.ApprovedMonthlyBudgetInrPaise
              - req.BudgetContext.CurrentMonthSpendInrPaise
              - req.BudgetContext.ProposedSpendInrPaise
            : (long?)null;

        var allowResponse = new ValidateActionResponse
        {
            Decision = ValidationDecision.Allow,
            ConstitutionalBasis = "C-041,C-043,C-048,C-049,C-062",
            Reason = "All constitutional claim evaluators passed."
        };
        if (budgetRemainingOnAllow.HasValue)
            allowResponse.BudgetRemainingInrPaise = budgetRemainingOnAllow.Value;

        return allowResponse;
    }

    // C-073: Implements C-003 (authority licensed) — authority grant requires evidence chain
    public override async Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);

        using var activity = _tracer.StartActivity("GrantAuthorityLicense", ActivityKind.Server);
        activity?.SetTag("contract_id", req.ContractId);

        _logger.LogInformation(
            "GrantAuthorityLicense ContractId={ContractId} GrantedBy={GrantedBy} " +
            "NewAuthorityLevel={Level}",
            req.ContractId, req.GrantedBy, req.NewAuthorityLevel);

        // DESIGN_QUESTION: EF Core persistence is WC012-03a. Returning synthetic ID until then.
        var licenseId = Guid.NewGuid().ToString("N");
        activity?.SetTag("license_id", licenseId);
        return new GrantAuthorityResponse { LicenseId = licenseId };
    }

    // C-073: Implements C-003 (authority licensed) — authority revocation is append-only
    public override async Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);

        using var activity = _tracer.StartActivity("RevokeAuthorityLicense", ActivityKind.Server);
        activity?.SetTag("contract_id", req.ContractId);

        _logger.LogInformation(
            "RevokeAuthorityLicense ContractId={ContractId} RevokedBy={RevokedBy} Reason={Reason}",
            req.ContractId, req.RevokedBy, req.Reason);

        // DESIGN_QUESTION: EF Core persistence is WC012-03a.
        var licenseId = Guid.NewGuid().ToString("N");
        activity?.SetTag("license_id", licenseId);
        return new RevokeAuthorityResponse { LicenseId = licenseId };
    }

    // C-073: Implements policy evaluation — returns PolicyDecision for caller
    public override async Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);

        using var activity = _tracer.StartActivity("EvaluatePolicy", ActivityKind.Server);
        activity?.SetTag("contract_id", req.ContractId);
        activity?.SetTag("action_type", req.ActionType);

        _logger.LogInformation(
            "EvaluatePolicy ContractId={ContractId} ActionType={ActionType}",
            req.ContractId, req.ActionType);

        // DESIGN_QUESTION: EvaluatePolicy is a separate policy path from ValidateAction.
        // EA to confirm whether this should delegate to EvaluatorRegistry or maintain
        // a separate policy rule store. Returning PERMIT stub until spec lands.
        return new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit,
            ConstitutionalBasis = "STUB",
            Rationale = "EvaluatePolicy stub — pending EA policy store specification."
        };
    }

    // C-073: Implements C-001 (Emergency Stop) — all sessions halted immediately
    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);

        using var activity = _tracer.StartActivity("TriggerEmergencyStop", ActivityKind.Server);
        activity?.SetTag("contract_id", req.ContractId);

        _logger.LogCritical(
            "TriggerEmergencyStop ContractId={ContractId} StoppedBy={StoppedBy} SessionCount={Count}",
            req.ContractId, req.StoppedBy, req.ActiveSessionIds.Count);

        // DESIGN_QUESTION: EF Core persistence + Temporal signal dispatch is WC012-03a.
        var stopRecordId = Guid.NewGuid().ToString("N");
        activity?.SetTag("emergency_stop_record_id", stopRecordId);

        var response = new EmergencyStopResponse { EmergencyStopRecordId = stopRecordId };
        response.AffectedSessions.AddRange(req.ActiveSessionIds);
        return response;
    }
}