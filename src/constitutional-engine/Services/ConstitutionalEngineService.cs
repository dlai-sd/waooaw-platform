// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-003 (Authority Licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security), C-059 (Traceability),
//                       C-073 (Annotation), ADR-001 (gRPC Constitutional Engine)

#nullable enable

using System.Diagnostics;
using Grpc.Core;
using Microsoft.Extensions.Logging;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementation for the Constitutional Engine.
/// Enforces constitutional claims at the PAAS boundary for every agent action.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    // C-059: Traceability via OpenTelemetry ActivitySource
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

    // ─── ValidateAction ──────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Constitutional obligation — ValidateAction enforces C-041, C-043, C-048, C-049, C-062.
    /// Short-circuits on first DENY. Default-deny for unknown or unconfigured contracts.
    /// </summary>
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest request,
        ServerCallContext context)
    {
        ArgumentNullException.ThrowIfNull(request);

        var ct = context.CancellationToken;

        // C-073: Extract tenant identity from gRPC metadata per stack rules
        var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? "";

        using var activity = _tracer.StartActivity("ValidateAction", ActivityKind.Server);
        activity?.SetTag("contract_id", request.ContractId);
        activity?.SetTag("action_type", request.ActionType);
        activity?.SetTag("tenant_id", tenantId);

        _logger.LogInformation(
            "ValidateAction called: ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
            request.ContractId, request.ActionType, tenantId);

        // C-073: Build evaluation context — BudgetContext is nullable on the proto message;
        // use ?? 0L to avoid CS0266 (long? → long implicit conversion is not permitted).
        var evalCtx = EvaluationContext.FromRequest(request, tenantId);

        // C-073: Run all registered evaluators; short-circuit on first DENY (registry contract)
        IReadOnlyList<EvaluationResult> results;
        try
        {
            results = await _registry.EvaluateAllAsync(evalCtx, ct).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            throw new RpcException(new Status(StatusCode.Cancelled, "ValidateAction cancelled by client."));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "EvaluatorRegistry fault for ContractId={ContractId}", request.ContractId);
            throw new RpcException(new Status(StatusCode.Internal, "Constitutional evaluation fault."));
        }

        // C-073: Compute budget remaining — BudgetContext is proto-optional (nullable C# reference).
        // Extract each field with null-coalescing to long (non-nullable) before arithmetic.
        // NEVER use BudgetRemainingInrPaise from EvaluationContext — it does not exist there.
        long approvedBudgetInrPaise  = request.BudgetContext?.ApprovedMonthlyBudgetInrPaise ?? 0L;
        long currentSpendInrPaise    = request.BudgetContext?.CurrentMonthSpendInrPaise     ?? 0L;
        long proposedSpendInrPaise   = request.BudgetContext?.ProposedSpendInrPaise         ?? 0L;
        long budgetRemainingInrPaise = approvedBudgetInrPaise - currentSpendInrPaise - proposedSpendInrPaise;

        // C-073: First DENY verdict → return DENY immediately (short-circuit on first failure)
        var denied = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Deny);
        if (denied is not null)
        {
            activity?.SetTag("decision", "DENY");
            activity?.SetTag("constitutional_basis", denied.ClaimId);

            _logger.LogWarning(
                "ValidateAction DENY: ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                request.ContractId, denied.ClaimId, denied.Reason);

            // BudgetRemainingInrPaise is long? on ValidateActionResponse — long is implicitly widened to long?
            return new ValidateActionResponse
            {
                Decision             = ValidationDecision.Deny,
                ConstitutionalBasis  = denied.ClaimId,
                Reason               = denied.Reason,
                BudgetRemainingInrPaise = budgetRemainingInrPaise
            };
        }

        // C-073: Check for Escalate — any evaluator requesting human review
        var escalated = results.FirstOrDefault(r => r.Verdict == EvaluationVerdict.Escalate);
        if (escalated is not null)
        {
            activity?.SetTag("decision", "ESCALATE");
            activity?.SetTag("constitutional_basis", escalated.ClaimId);

            _logger.LogWarning(
                "ValidateAction ESCALATE: ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                request.ContractId, escalated.ClaimId, escalated.Reason);

            // Escalate maps to Deny at the boundary until human approval is obtained (C-049)
            return new ValidateActionResponse
            {
                Decision            = ValidationDecision.Deny,
                ConstitutionalBasis = escalated.ClaimId,
                Reason              = $"[ESCALATE] {escalated.Reason}",
                BudgetRemainingInrPaise = budgetRemainingInrPaise
            };
        }

        // C-073: All evaluators passed → ALLOW
        const string AllBasisClaims = "C-041,C-043,C-048,C-049,C-062";
        activity?.SetTag("decision", "ALLOW");

        _logger.LogInformation(
            "ValidateAction ALLOW: ContractId={ContractId} EvaluatorCount={Count}",
            request.ContractId, results.Count);

        return new ValidateActionResponse
        {
            Decision            = ValidationDecision.Allow,
            ConstitutionalBasis = AllBasisClaims,
            Reason              = "All constitutional evaluators passed.",
            BudgetRemainingInrPaise = budgetRemainingInrPaise
        };
    }

    // ─── RecordEvidence ──────────────────────────────────────────────────────

    /// <summary>
    /// C-073: C-023 Evidence First — persists immutable audit records.
    /// Full implementation delivered in WC012-03.
    /// </summary>
    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest request,
        ServerCallContext context)
    {
        // DESIGN_QUESTION: WC012-03 owns persistence. Stub returns empty ID until that task lands.
        throw new RpcException(new Status(StatusCode.Unimplemented, "RecordEvidence implemented in WC012-03."));
    }

    // ─── GrantAuthorityLicense ───────────────────────────────────────────────

    /// <summary>
    /// C-073: C-003 Authority Licensed — grants authority level to a contract.
    /// </summary>
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest request,
        ServerCallContext context)
    {
        throw new RpcException(new Status(StatusCode.Unimplemented, "GrantAuthorityLicense not yet implemented."));
    }

    // ─── RevokeAuthorityLicense ──────────────────────────────────────────────

    /// <summary>
    /// C-073: C-003 Authority Licensed — revokes authority level from a contract.
    /// </summary>
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest request,
        ServerCallContext context)
    {
        throw new RpcException(new Status(StatusCode.Unimplemented, "RevokeAuthorityLicense not yet implemented."));
    }

    // ─── EvaluatePolicy ─────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Policy evaluation endpoint — evaluates multi-claim policy sets.
    /// </summary>
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest request,
        ServerCallContext context)
    {
        throw new RpcException(new Status(StatusCode.Unimplemented, "EvaluatePolicy not yet implemented."));
    }

    // ─── TriggerEmergencyStop ────────────────────────────────────────────────

    /// <summary>
    /// C-073: C-001 Human Override — triggers emergency stop across all active sessions.
    /// Full Temporal signal implementation delivered in WC012-04.
    /// </summary>
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest request,
        ServerCallContext context)
    {
        throw new RpcException(new Status(StatusCode.Unimplemented, "TriggerEmergencyStop implemented in WC012-04."));
    }
}