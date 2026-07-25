// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
//             architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-003 (Authority Licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security), C-059 (Traceability),
//                       C-073 (Constitutional Annotation), ADR-001 (gRPC Constitutional Engine)

#nullable enable

using Grpc.Core;
using Microsoft.Extensions.Logging;
using System.Diagnostics;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementing all constitutional engine operations.
/// ValidateAction enforces the full claim-evaluator pipeline (C-041, C-043, C-048, C-049, C-062).
/// RecordEvidence, GrantAuthority, RevokeAuthority, EvaluatePolicy, TriggerEmergencyStop are
/// implemented in subsequent sprint tasks (WC012-03 onward).
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    // C-073: ActivitySource annotates every constitutional operation for distributed tracing (ADR-009)
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly EvaluatorRegistry _registry;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    public ConstitutionalEngineService(
        EvaluatorRegistry registry,
        ILogger<ConstitutionalEngineService> logger)
    {
        ArgumentNullException.ThrowIfNull(registry);
        ArgumentNullException.ThrowIfNull(logger);
        _registry = registry;
        _logger = logger;
    }

    // ──────────────────────────────────────────────────────────────────────────
    // ValidateAction — constitutional evaluation pipeline (WC012-02b)
    // ──────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Enforces the ordered claim-evaluator pipeline.
    /// Short-circuits on first DENY. Returns ALLOW only when all evaluators pass.
    /// Default deny: unknown ContractId or missing authorization = DENY (C-041).
    /// </summary>
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest request,
        ServerCallContext context)
    {
        // C-073: ValidateAction is the runtime enforcement point for all constitutional claims
        var ct = context.CancellationToken;

        // TenantId sourced exclusively from gRPC metadata (C-062 boundary enforcement)
        var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? "";

        using var activity = _tracer.StartActivity("ValidateAction", ActivityKind.Server);
        activity?.SetTag("contract_id", request.ContractId);
        activity?.SetTag("action_type", request.ActionType);
        activity?.SetTag("tenant_id", tenantId);
        activity?.SetTag("decision_space_version", request.DecisionSpaceVersion);

        _logger.LogInformation(
            "ValidateAction started: ContractId={ContractId} ActionType={ActionType} TenantId={TenantId} DSV={DecisionSpaceVersion}",
            request.ContractId, request.ActionType, tenantId, request.DecisionSpaceVersion);

        // Build evaluation context from the incoming request (C-041 default deny baked in)
        var ctx = EvaluationContext.FromRequest(request, tenantId);

        IReadOnlyList<EvaluationResult> results;
        try
        {
            // C-073: Delegates to registered claim evaluators in priority order
            results = await _registry.EvaluateAllAsync(ctx, ct);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning(
                "ValidateAction cancelled: ContractId={ContractId}", request.ContractId);
            throw new RpcException(new Status(StatusCode.Cancelled, "Request was cancelled"));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "ValidateAction pipeline fault: ContractId={ContractId}", request.ContractId);
            throw new RpcException(
                new Status(StatusCode.Internal, "Constitutional evaluation pipeline encountered an error"));
        }

        // ── Short-circuit on first DENY (C-041 default-deny) ─────────────────
        var denial = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Deny);
        if (denial is not null)
        {
            activity?.SetTag("decision", "Deny");
            activity?.SetTag("denying_claim", denial.ClaimId);

            _logger.LogWarning(
                "ValidateAction DENY: ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                request.ContractId, denial.ClaimId, denial.Reason);

            return new ValidateActionResponse
            {
                Decision            = ValidationDecision.Deny,
                ConstitutionalBasis = denial.ClaimId,
                Reason              = denial.Reason,
            };
        }

        // ── Escalate path (C-049 Honest Limitation — uncertain action) ────────
        var escalation = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Escalate);
        if (escalation is not null)
        {
            activity?.SetTag("decision", "Escalate");
            activity?.SetTag("escalating_claim", escalation.ClaimId);

            _logger.LogInformation(
                "ValidateAction ESCALATE: ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                request.ContractId, escalation.ClaimId, escalation.Reason);

            return new ValidateActionResponse
            {
                Decision            = ValidationDecision.Escalate,
                ConstitutionalBasis = escalation.ClaimId,
                Reason              = escalation.Reason,
            };
        }

        // ── All evaluators passed → ALLOW ─────────────────────────────────────
        activity?.SetTag("decision", "Allow");

        _logger.LogInformation(
            "ValidateAction ALLOW: ContractId={ContractId} ActionType={ActionType} EvaluatorCount={Count}",
            request.ContractId, request.ActionType, results.Count);

        var allowResponse = new ValidateActionResponse
        {
            Decision            = ValidationDecision.Allow,
            ConstitutionalBasis = "C-041,C-043,C-048,C-049,C-062",
            Reason              = "All constitutional evaluators passed",
        };

        // Compute remaining budget from context (C-051 Resource Transparency)
        // BudgetRemainingInrPaise is nullable on the response — only set when BudgetContext present
        if (request.BudgetContext is not null)
        {
            // C-073: compute remainder from the three non-nullable budget fields on EvaluationContext
            long remaining = ctx.ApprovedBudgetInrPaise
                           - ctx.CurrentSpendInrPaise
                           - ctx.ProposedSpendInrPaise;
            allowResponse.BudgetRemainingInrPaise = remaining;
            activity?.SetTag("budget_remaining_inr_paise", remaining);
        }

        return allowResponse;
    }

    // ──────────────────────────────────────────────────────────────────────────
    // RecordEvidence — implemented in WC012-03
    // ──────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: RecordEvidence persists audit evidence (C-023). Full impl in WC012-03.
    /// </summary>
    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req,
        ServerCallContext ctx)
    {
        // DESIGN_QUESTION: Should stub return Unimplemented or an empty record? EA to confirm.
        throw new RpcException(new Status(StatusCode.Unimplemented,
            "RecordEvidence is implemented in WC012-03"));
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Authority licensing — implemented in WC012-04+
    // ──────────────────────────────────────────────────────────────────────────

    /// <summary>C-073: GrantAuthorityLicense enforces C-003 (Authority Licensed). Implemented in WC012-04.</summary>
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(new Status(StatusCode.Unimplemented,
            "GrantAuthorityLicense is implemented in WC012-04"));
    }

    /// <summary>C-073: RevokeAuthorityLicense enforces C-003 (Authority Licensed). Implemented in WC012-04.</summary>
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(new Status(StatusCode.Unimplemented,
            "RevokeAuthorityLicense is implemented in WC012-04"));
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Policy evaluation — implemented in WC012-05+
    // ──────────────────────────────────────────────────────────────────────────

    /// <summary>C-073: EvaluatePolicy enforces C-003 decision-space policy. Implemented in WC012-05.</summary>
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(new Status(StatusCode.Unimplemented,
            "EvaluatePolicy is implemented in WC012-05"));
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Emergency Stop — C-001 Human Override
    // ──────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: TriggerEmergencyStop enforces C-001 (Human Override — unconditional halt).
    /// Full impl via Temporal signal in WC012-06.
    /// </summary>
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(new Status(StatusCode.Unimplemented,
            "TriggerEmergencyStop is implemented in WC012-06"));
    }
}