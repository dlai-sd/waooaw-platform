// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
//             architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-003 (Authority Licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-051 (Resource Transparency), C-062 (AI Security),
//                       C-059 (Traceability), C-073 (Annotated Obligations), C-076 (Test Coverage)

#nullable enable

using System.Diagnostics;
using System.Linq;
using Grpc.Core;
using Microsoft.Extensions.Logging;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementing the Constitutional Engine boundary validator.
/// Every ValidateAction call enforces constitution-as-code via the EvaluatorRegistry.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    // C-059: ActivitySource for distributed tracing — every constitutional operation is traceable.
    private static readonly ActivitySource _tracer =
        new("Waooaw.ConstitutionalEngine");

    private readonly EvaluatorRegistry _registry;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    /// <summary>
    /// Constructor injection (C-073: DI pattern enforced for constitutional services).
    /// </summary>
    public ConstitutionalEngineService(
        EvaluatorRegistry registry,
        ILogger<ConstitutionalEngineService> logger)
    {
        // C-073: Null-guard all injected dependencies.
        ArgumentNullException.ThrowIfNull(registry);
        ArgumentNullException.ThrowIfNull(logger);
        _registry = registry;
        _logger   = logger;
    }

    // ──────────────────────────────────────────────────────────────────────────
    // C-073: ValidateAction — enforces constitution at runtime via EvaluatorRegistry.
    //        This is the PAAS Boundary Validator (§2). Short-circuits on first DENY.
    //        Default deny: any action not explicitly authorised by an evaluator is denied.
    // ──────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// Validates a proposed agent action against all applicable constitutional claim evaluators.
    /// Short-circuits on first DENY. Returns AUTHORIZED only when all evaluators pass.
    /// Constitutional basis: C-041, C-043, C-048, C-049, C-051, C-062.
    /// </summary>
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest request,
        ServerCallContext context)
    {
        // C-073: All I/O is async; CancellationToken propagated from gRPC context.
        var ct = context.CancellationToken;

        // C-059: Emit a trace span for every ValidateAction call.
        using var activity = _tracer.StartActivity("ValidateAction", ActivityKind.Server);
        activity?.SetTag("contract_id",    request.ContractId);
        activity?.SetTag("action_type",    request.ActionType);
        activity?.SetTag("decision_space", request.DecisionSpaceVersion);

        // C-041: TenantId sourced from gRPC metadata header x-tenant-id.
        var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? "";
        activity?.SetTag("tenant_id", tenantId);

        _logger.LogInformation(
            "ValidateAction start ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
            request.ContractId, request.ActionType, tenantId);

        // C-073: Build the evaluation context from the inbound request.
        //        EvaluationContext.FromRequest maps proto fields → typed context record.
        EvaluationContext evalCtx = EvaluationContext.FromRequest(request, tenantId);

        IReadOnlyList<EvaluationResult> results;
        try
        {
            // C-073: Delegate to EvaluatorRegistry — single ordered evaluation pipeline.
            results = await _registry.EvaluateAllAsync(evalCtx, ct).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning(
                "ValidateAction cancelled ContractId={ContractId}", request.ContractId);
            throw new RpcException(new Status(StatusCode.Cancelled, "Request was cancelled."));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "EvaluatorRegistry pipeline fault ContractId={ContractId}", request.ContractId);
            throw new RpcException(
                new Status(StatusCode.Internal, "Constitutional evaluator pipeline failed."));
        }

        // ── Short-circuit: first DENY wins (C-041 default-deny principle) ──
        // C-073: Any DENY from any evaluator immediately blocks the action.
        var firstDeny = results.FirstOrDefault(
            r => r.Verdict == EvaluationVerdict.Deny);

        if (firstDeny is not null)
        {
            activity?.SetTag("decision",        "DENY");
            activity?.SetTag("denying_claim_id", firstDeny.ClaimId);

            _logger.LogWarning(
                "ValidateAction DENY ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                request.ContractId, firstDeny.ClaimId, firstDeny.Reason);

            return new ValidateActionResponse
            {
                Decision             = ValidationDecision.Deny,
                ConstitutionalBasis  = firstDeny.ClaimId,
                Reason               = firstDeny.Reason,
                // C-051: Return remaining budget even on DENY so caller can display transparency data.
                BudgetRemainingInrPaise = ComputeBudgetRemaining(request)
            };
        }

        // ── Escalate: first Escalate result triggers human review path (C-049) ──
        // C-073: Escalate routes to human override (C-001 / C-049). Treated as non-authorized.
        var firstEscalate = results.FirstOrDefault(
            r => r.Verdict == EvaluationVerdict.Escalate);

        if (firstEscalate is not null)
        {
            activity?.SetTag("decision",           "ESCALATE");
            activity?.SetTag("escalating_claim_id", firstEscalate.ClaimId);

            _logger.LogWarning(
                "ValidateAction ESCALATE ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                request.ContractId, firstEscalate.ClaimId, firstEscalate.Reason);

            return new ValidateActionResponse
            {
                Decision            = ValidationDecision.Escalate,
                ConstitutionalBasis = firstEscalate.ClaimId,
                Reason              = firstEscalate.Reason,
                BudgetRemainingInrPaise = ComputeBudgetRemaining(request)
            };
        }

        // ── All evaluators passed: ALLOW ──
        // C-073: All evaluators returned Allow — action is constitutionally authorised.
        var allClaims = string.Join(", ", results.Select(r => r.ClaimId));
        activity?.SetTag("decision",        "ALLOW");
        activity?.SetTag("evaluated_claims", allClaims);

        _logger.LogInformation(
            "ValidateAction ALLOW ContractId={ContractId} ActionType={ActionType} Claims=[{Claims}]",
            request.ContractId, request.ActionType, allClaims);

        return new ValidateActionResponse
        {
            Decision            = ValidationDecision.Allow,
            ConstitutionalBasis = allClaims,
            Reason              = "All constitutional evaluators passed.",
            BudgetRemainingInrPaise = ComputeBudgetRemaining(request)
        };
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Stub implementations preserved from prior task (WC012-02a).
    // These methods are implemented in later sprint tasks (WC012-03 / WC012-04).
    // EXTEND-NOT-REPLACE: do not alter logic already committed on the branch.
    // ──────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// Records constitutional evidence (C-023 Evidence First).
    /// Full implementation: WC012-03.
    /// </summary>
    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req,
        ServerCallContext ctx)
    {
        // DESIGN_QUESTION: WC012-03 will supply the full EF Core implementation.
        // Stub: return placeholder until WC012-03a ConstitutionalDbContext is on branch.
        throw new RpcException(
            new Status(StatusCode.Unimplemented, "RecordEvidence: implemented in WC012-03."));
    }

    /// <summary>
    /// Grants authority license to a contract (C-003 Authority Licensed).
    /// Full implementation: future sprint.
    /// </summary>
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(
            new Status(StatusCode.Unimplemented, "GrantAuthorityLicense: not yet implemented."));
    }

    /// <summary>
    /// Revokes authority license from a contract (C-003 Authority Licensed).
    /// Full implementation: future sprint.
    /// </summary>
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(
            new Status(StatusCode.Unimplemented, "RevokeAuthorityLicense: not yet implemented."));
    }

    /// <summary>
    /// Evaluates a policy set (Permit/Deny). Full implementation: future sprint.
    /// </summary>
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(
            new Status(StatusCode.Unimplemented, "EvaluatePolicy: not yet implemented."));
    }

    /// <summary>
    /// Triggers an Emergency Stop (C-001 Human Override).
    /// Full implementation: WC012-04 (Temporal signal).
    /// </summary>
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(
            new Status(StatusCode.Unimplemented, "TriggerEmergencyStop: implemented in WC012-04."));
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Private helpers
    // ──────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// Computes budget remaining from the optional BudgetContext on the request.
    /// C-051 (Resource Transparency): always return a value — never return null.
    /// </summary>
    private static long ComputeBudgetRemaining(ValidateActionRequest request)
    {
        if (request.BudgetContext is null)
        {
            // C-051: No budget context provided — return 0 (opaque, not null) per behavioral rules.
            return 0L;
        }

        var remaining =
              request.BudgetContext.ApprovedMonthlyBudgetInrPaise
            - request.BudgetContext.CurrentMonthSpendInrPaise
            - request.BudgetContext.ProposedSpendInrPaise;

        // C-051: BudgetRemainingInrPaise is long? — NEVER assign null. Clamp to 0 if negative.
        return remaining < 0L ? 0L : remaining;
    }
}