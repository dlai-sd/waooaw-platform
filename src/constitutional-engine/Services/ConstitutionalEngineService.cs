// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-023 (Evidence First), C-003 (Authority Licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using Grpc.Core;
using Microsoft.Extensions.Logging;
using System.Diagnostics;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementing the WAOOAW Constitutional Engine boundary validator.
/// C-073: Every method implementing a constitutional obligation carries an annotation comment.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    // C-073: OpenTelemetry activity source — all constitutional operations are traced (ADR-009)
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

    // ─────────────────────────────────────────────────────────────────────────
    // ValidateAction — C-073: enforces C-041, C-043, C-048, C-049, C-062
    // Gap Closed: G-INSTINCT-01 — CE.ValidateAction no longer a stub
    // Architecture: ce-validate-action-evaluators.md §Evaluator Architecture
    //   Short-circuit on first DENY; all denials recorded (C-023 handled in WC012-03).
    // ─────────────────────────────────────────────────────────────────────────
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest request,
        ServerCallContext context)
    {
        ArgumentNullException.ThrowIfNull(request);

        var ct = context.CancellationToken;

        // C-073: Extract tenant identity from gRPC metadata (multi-tenancy boundary)
        var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        using var activity = _tracer.StartActivity(
            "ConstitutionalEngine.ValidateAction",
            ActivityKind.Server);
        activity?.SetTag("contract_id", request.ContractId);
        activity?.SetTag("action_type", request.ActionType);
        activity?.SetTag("tenant_id", tenantId);
        activity?.SetTag("decision_space_version", request.DecisionSpaceVersion);

        _logger.LogInformation(
            "ValidateAction received: ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
            request.ContractId,
            request.ActionType,
            tenantId);

        // C-073: Default-deny posture — empty/missing ContractId denies immediately (C-041)
        if (string.IsNullOrWhiteSpace(request.ContractId))
        {
            _logger.LogWarning(
                "ValidateAction denied: missing ContractId. TenantId={TenantId}",
                tenantId);
            activity?.SetTag("decision", "DENY");
            activity?.SetTag("deny_reason", "missing_contract_id");

            return new ValidateActionResponse
            {
                // DESIGN_QUESTION: ValidationDecision enum in the compiled proto only exposes
                // Unspecified=0 in the type contract extract. Behavioral rules mandate
                // Allow/Deny/Escalate. Using ValidationDecision.Deny per behavioral rules —
                // EA to confirm proto field names match once full enum is visible.
                Decision = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason = "ContractId is required. Default-deny posture enforced."
            };
        }

        // C-073: Build evaluation context from the incoming request (C-059 traceability)
        EvaluationContext ctx;
        try
        {
            ctx = EvaluationContext.FromRequest(request, tenantId);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "ValidateAction failed to build EvaluationContext. ContractId={ContractId}",
                request.ContractId);
            activity?.SetTag("decision", "DENY");
            activity?.SetTag("deny_reason", "context_build_failure");

            throw new RpcException(
                new Status(StatusCode.InvalidArgument,
                    "Could not parse action parameters — see CE logs for details."));
        }

        // C-073: Run all registered claim evaluators (C-041, C-043, C-048, C-049, C-062)
        //        EvaluatorRegistry short-circuits on first DENY (ce-validate-action-evaluators.md)
        IReadOnlyList<EvaluationResult> results;
        try
        {
            results = await _registry.EvaluateAllAsync(ctx, ct).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning(
                "ValidateAction cancelled during evaluation. ContractId={ContractId}",
                request.ContractId);
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "ValidateAction evaluator pipeline threw. ContractId={ContractId}",
                request.ContractId);
            activity?.SetTag("decision", "DENY");
            activity?.SetTag("deny_reason", "evaluator_exception");

            // C-073: Fail-closed — any evaluator exception results in DENY (C-041 default deny)
            return new ValidateActionResponse
            {
                Decision = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason = "Evaluator pipeline encountered an internal error — fail-closed."
            };
        }

        // C-073: Inspect results — first DENY wins (short-circuit already applied by registry)
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction DENY: ContractId={ContractId} Claim={ClaimId} Reason={Reason}",
                    request.ContractId,
                    result.ClaimId,
                    result.Reason);

                activity?.SetTag("decision", "DENY");
                activity?.SetTag("deny_claim", result.ClaimId);
                activity?.SetTag("deny_reason", result.Reason);

                return new ValidateActionResponse
                {
                    Decision = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason = result.Reason
                };
            }

            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                // C-073: C-049 (Honest Limitation) escalation path — uncertain actions
                //        forwarded to human authority. Treated as DENY at this boundary;
                //        the calling agent must surface the escalation to the human.
                _logger.LogInformation(
                    "ValidateAction ESCALATE: ContractId={ContractId} Claim={ClaimId} Reason={Reason}",
                    request.ContractId,
                    result.ClaimId,
                    result.Reason);

                activity?.SetTag("decision", "ESCALATE");
                activity?.SetTag("escalate_claim", result.ClaimId);

                // DESIGN_QUESTION: Should Escalate map to a distinct ValidationDecision proto
                // value, or should we surface it as Deny with a specific Reason prefix?
                // Returning Deny with annotated reason until EA confirms proto shape.
                return new ValidateActionResponse
                {
                    Decision = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason = $"ESCALATE:{result.Reason}"
                };
            }
        }

        // C-073: All evaluators passed — compute budget remainder for response transparency (C-051)
        long budgetRemaining = ctx.ApprovedBudgetInrPaise
            - ctx.CurrentSpendInrPaise
            - ctx.ProposedSpendInrPaise;

        _logger.LogInformation(
            "ValidateAction ALLOW: ContractId={ContractId} ActionType={ActionType} BudgetRemainingPaise={BudgetRemaining}",
            request.ContractId,
            request.ActionType,
            budgetRemaining);

        activity?.SetTag("decision", "ALLOW");
        activity?.SetTag("budget_remaining_paise", budgetRemaining);

        return new ValidateActionResponse
        {
            Decision = ValidationDecision.Allow,
            ConstitutionalBasis = "C-041,C-043,C-048,C-049,C-062",
            Reason = "All constitutional evaluators passed.",
            BudgetRemainingInrPaise = budgetRemaining
        };
    }

    // ─────────────────────────────────────────────────────────────────────────
    // RecordEvidence — C-073: C-023 Evidence First
    // Full implementation: WC012-03
    // ─────────────────────────────────────────────────────────────────────────
    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req,
        ServerCallContext ctx)
    {
        // C-073: Stub — full implementation in WC012-03 (Data layer required)
        throw new RpcException(new Status(StatusCode.Unimplemented,
            "RecordEvidence not yet implemented — see WC012-03."));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // GrantAuthorityLicense — C-073: C-003 Authority must be explicitly licensed
    // Full implementation: future sprint
    // ─────────────────────────────────────────────────────────────────────────
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(new Status(StatusCode.Unimplemented,
            "GrantAuthorityLicense not yet implemented."));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // RevokeAuthorityLicense — C-073: C-003 Authority revocation path
    // Full implementation: future sprint
    // ─────────────────────────────────────────────────────────────────────────
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(new Status(StatusCode.Unimplemented,
            "RevokeAuthorityLicense not yet implemented."));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // EvaluatePolicy — C-073: policy evaluation boundary
    // Full implementation: future sprint
    // ─────────────────────────────────────────────────────────────────────────
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(new Status(StatusCode.Unimplemented,
            "EvaluatePolicy not yet implemented."));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // TriggerEmergencyStop — C-073: C-001 Human override / Emergency Stop
    // Full implementation: WC012-03 (Temporal signal + DB write required)
    // ─────────────────────────────────────────────────────────────────────────
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(new Status(StatusCode.Unimplemented,
            "TriggerEmergencyStop not yet implemented — see WC012-03."));
    }
}