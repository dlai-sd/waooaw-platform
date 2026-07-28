// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-041, C-059
using Grpc.Core;
using Microsoft.Extensions.Logging;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// Constitutional Engine gRPC service implementation.
/// Purpose: Enforces constitutional boundaries at every PAAS action before execution.
/// Constitutional basis: C-023 (Evidence First), C-041 (Tool Authorization), C-059 (Traceability)
/// ADR reference: ADR-001 (gRPC Constitutional Engine), ADR-005 (ValidateAction 40ms budget)
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    private readonly EvaluatorRegistry _registry;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    // AD-005: ValidateAction must complete within 40ms (leaves 10ms for caller overhead in 50ms total budget)
    private const int ValidateActionTimeoutMs = 40;

    public ConstitutionalEngineService(
        EvaluatorRegistry registry,
        ILogger<ConstitutionalEngineService> logger)
    {
        _registry = registry ?? throw new ArgumentNullException(nameof(registry));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    /// <summary>
    /// RecordEvidence — Evidence First Enforcer.
    /// WC012-03 scope: stub only at this stage.
    /// Constitutional basis: C-023 (Evidence First), C-027 (append-only ledger)
    /// </summary>
    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
    {
        _logger.LogWarning(
            "RecordEvidence called but not yet implemented (WC012-03 scope): contractId={ContractId}",
            req.ContractId);
        throw new RpcException(new Status(StatusCode.Unimplemented, "RecordEvidence: WC012-03 scope"));
    }

    /// <summary>
    /// ValidateAction — PAAS Boundary Validator.
    /// Evaluates all registered claim evaluators against the proposed action.
    /// Short-circuits on the first DENY (C-041: default deny for unlisted tools).
    /// Constitutional basis: C-041 (Tool Authorization), C-043 (Budget Ceiling),
    ///                       C-048 (Non-Exploitation), C-049 (Honest Limitation), C-062 (AI Security)
    /// AD-005: target latency &lt; 40ms
    /// </summary>
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest request, ServerCallContext context)
    {
        try
        {
            // Tenant isolation: carried via gRPC metadata, never in request body (constitutional_service.proto)
            var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? "";

            if (string.IsNullOrWhiteSpace(tenantId))
            {
                _logger.LogWarning(
                    "ValidateAction rejected: missing x-tenant-id metadata. contractId={ContractId}",
                    request.ContractId);
                throw new RpcException(
                    new Status(StatusCode.Unauthenticated, "x-tenant-id metadata is required (constitutional_service.proto transport notes)"));
            }

            var ctx = EvaluationContext.FromRequest(request, tenantId);

            // AD-005: enforce 40ms constitutional budget — link to caller's cancellation token
            using var budgetCts = CancellationTokenSource.CreateLinkedTokenSource(context.CancellationToken);
            budgetCts.CancelAfter(TimeSpan.FromMilliseconds(ValidateActionTimeoutMs));

            IReadOnlyList<EvaluationResult> results;
            try
            {
                results = await _registry.EvaluateAllAsync(ctx, budgetCts.Token);
            }
            catch (OperationCanceledException oce) when (!context.CancellationToken.IsCancellationRequested)
            {
                // Budget exceeded — this is the internal timeout, not the caller cancelling
                _logger.LogError(
                    oce,
                    "ValidateAction exceeded {BudgetMs}ms constitutional budget (AD-005). contractId={ContractId} actionType={ActionType}",
                    ValidateActionTimeoutMs, request.ContractId, request.ActionType);
                throw new RpcException(
                    new Status(StatusCode.DeadlineExceeded,
                        $"ValidateAction exceeded {ValidateActionTimeoutMs}ms constitutional budget (AD-005)"));
            }

            // Short-circuit on first DENY — C-041: default deny for anything unlisted
            foreach (var result in results)
            {
                if (result.Verdict == EvaluationVerdict.Deny)
                {
                    _logger.LogInformation(
                        "ValidateAction DENY: claimId={ClaimId} reason={Reason} contractId={ContractId} actionType={ActionType}",
                        result.ClaimId, result.Reason, request.ContractId, request.ActionType);

                    return new ValidateActionResponse
                    {
                        Decision = ValidationDecision.Deny,
                        ConstitutionalBasis = result.ClaimId,
                        Reason = result.Reason
                    };
                }

                if (result.Verdict == EvaluationVerdict.Escalate)
                {
                    _logger.LogInformation(
                        "ValidateAction ESCALATE: claimId={ClaimId} reason={Reason} contractId={ContractId} actionType={ActionType}",
                        result.ClaimId, result.Reason, request.ContractId, request.ActionType);

                    return new ValidateActionResponse
                    {
                        Decision = ValidationDecision.Escalate,
                        ConstitutionalBasis = result.ClaimId,
                        Reason = result.Reason
                    };
                }
            }

            // All evaluators returned Allow → action is within Decision Space
            _logger.LogInformation(
                "ValidateAction ALLOW: contractId={ContractId} actionType={ActionType} evaluatorsRun={Count}",
                request.ContractId, request.ActionType, results.Count);

            return new ValidateActionResponse
            {
                Decision = ValidationDecision.Allow,
                ConstitutionalBasis = "C-041; C-043; C-048; C-049; C-062",
                Reason = "All constitutional evaluators passed"
            };
        }
        catch (RpcException)
        {
            // Propagate RpcExceptions without wrapping — they are already correctly typed
            throw;
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 3: map unexpected exceptions to StatusCode.Internal
            _logger.LogError(
                ex,
                "ValidateAction failed unexpectedly. contractId={ContractId} actionType={ActionType}",
                request.ContractId, request.ActionType);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    /// <summary>
    /// GrantAuthorityLicense — Authority License Manager (expansion).
    /// WC012-03 scope: stub only at this stage.
    /// Constitutional basis: C-003 (authority licensed), C-023 (Evidence First)
    /// </summary>
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
    {
        _logger.LogWarning(
            "GrantAuthorityLicense called but not yet implemented (WC012-03 scope): contractId={ContractId}",
            req.ContractId);
        throw new RpcException(new Status(StatusCode.Unimplemented, "GrantAuthorityLicense: WC012-03 scope"));
    }

    /// <summary>
    /// RevokeAuthorityLicense — Authority License Manager (restriction).
    /// WC012-03 scope: stub only at this stage.
    /// Constitutional basis: C-003 (authority licensed), C-023 (Evidence First)
    /// </summary>
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
    {
        _logger.LogWarning(
            "RevokeAuthorityLicense called but not yet implemented (WC012-03 scope): contractId={ContractId}",
            req.ContractId);
        throw new RpcException(new Status(StatusCode.Unimplemented, "RevokeAuthorityLicense: WC012-03 scope"));
    }

    /// <summary>
    /// EvaluatePolicy — general-purpose constitutional policy evaluation.
    /// WC012-03 scope: stub only at this stage.
    /// Constitutional basis: AD-008 (every permission decision must name its constitutional basis)
    /// </summary>
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
    {
        _logger.LogWarning(
            "EvaluatePolicy called but not yet implemented (WC012-03 scope): contractId={ContractId}",
            req.ContractId);
        throw new RpcException(new Status(StatusCode.Unimplemented, "EvaluatePolicy: WC012-03 scope"));
    }

    /// <summary>
    /// TriggerEmergencyStop — Emergency Stop Handler.
    /// Stub implementation: returns empty response.
    /// Full Temporal signal + session halt implementation is WC012-04b scope.
    /// Constitutional basis: C-013 (Emergency Override), AD-001 (≤250ms end-to-end)
    /// </summary>
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
    {
        // WC012-04b scope: Temporal signal integration is NOT part of this sprint
        _logger.LogWarning(
            "TriggerEmergencyStop invoked — stub only (WC012-04b scope): contractId={ContractId} stoppedBy={StoppedBy}",
            req.ContractId, req.StoppedBy);
        return Task.FromResult(new EmergencyStopResponse());
    }
}