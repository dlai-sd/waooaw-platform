// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-001, C-003, C-023, C-041, C-059
using Grpc.Core;
using Microsoft.Extensions.Logging;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementation.
/// ValidateAction: WC012-02b (this sprint).
/// RecordEvidence / authority management: WC012-03.
/// TriggerEmergencyStop (Temporal integration): WC012-04b.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    // ValidateAction latency budget: target < 40ms (ADR-001, AD-005)
    private static readonly TimeSpan ValidateActionTimeout = TimeSpan.FromSeconds(5);

    private readonly EvaluatorRegistry _registry;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    public ConstitutionalEngineService(
        EvaluatorRegistry registry,
        ILogger<ConstitutionalEngineService> logger)
    {
        _registry = registry;
        _logger = logger;
    }

    // ─── RecordEvidence ──────────────────────────────────────────────────────
    // Stub — full implementation in WC012-03 (Evidence First Enforcer).
    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req, ServerCallContext ctx)
        => Task.FromResult(new RecordEvidenceResponse());

    // ─── ValidateAction ──────────────────────────────────────────────────────
    // C-041 default-deny: any action whose ContractId is absent, or any evaluator
    // that returns DENY, results in ValidationDecision.Deny before execution.
    // C-043: budget ceiling enforced by C043BudgetCeilingEvaluator.
    // C-048: exploitation guard enforced by C048NonExploitationEvaluator.
    // C-049: honest limitation enforced by C049HonestLimitationEvaluator.
    // C-062: AI security enforced by C062AiSecurityEvaluator.
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req, ServerCallContext ctx)
    {
        // Default deny: ContractId is mandatory (C-041 — unlisted contract = DENY)
        if (string.IsNullOrWhiteSpace(req.ContractId))
        {
            _logger.LogWarning(
                "ValidateAction default-deny: empty ContractId. ActionType={ActionType} (C-041)",
                req.ActionType);

            return new ValidateActionResponse
            {
                Decision = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason = "ContractId is required — default deny (C-041: unlisted tool/contract)."
            };
        }

        try
        {
            // Tenant isolation: read from gRPC metadata, never from request body.
            // Returns empty string when absent — downstream evaluators may deny on that basis.
            var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

            var evalCtx = EvaluationContext.FromRequest(req, tenantId);

            // Bounded timeout — ValidateAction must not block indefinitely (C-059, ERROR HANDLING RULE 4)
            using var cts = new CancellationTokenSource(ValidateActionTimeout);

            var results = await _registry.EvaluateAllAsync(evalCtx, cts.Token);

            // Short-circuit on first DENY or ESCALATE (architecture: ce-validate-action-evaluators.md)
            foreach (var result in results)
            {
                if (result.Verdict == EvaluationVerdict.Deny)
                {
                    _logger.LogInformation(
                        "ValidateAction DENY: ContractId={ContractId} ActionType={ActionType} " +
                        "ClaimId={ClaimId} Reason={Reason}",
                        req.ContractId, req.ActionType, result.ClaimId, result.Reason);

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
                        "ValidateAction ESCALATE: ContractId={ContractId} ActionType={ActionType} " +
                        "ClaimId={ClaimId} Reason={Reason}",
                        req.ContractId, req.ActionType, result.ClaimId, result.Reason);

                    return new ValidateActionResponse
                    {
                        Decision = ValidationDecision.Escalate,
                        ConstitutionalBasis = result.ClaimId,
                        Reason = result.Reason
                    };
                }
            }

            // All evaluators passed — action is within the Decision Space
            _logger.LogInformation(
                "ValidateAction ALLOW: ContractId={ContractId} ActionType={ActionType} " +
                "EvaluatorCount={Count}",
                req.ContractId, req.ActionType, results.Count);

            return new ValidateActionResponse
            {
                Decision = ValidationDecision.Allow,
                ConstitutionalBasis = "C-041; C-043; C-048; C-049; C-062",
                Reason = "All constitutional evaluators passed."
            };
        }
        catch (OperationCanceledException ex)
        {
            // Timeout is a hard failure — caller must not treat as success (C-023)
            _logger.LogError(
                ex,
                "ValidateAction timed out: ContractId={ContractId} ActionType={ActionType}",
                req.ContractId, req.ActionType);

            throw new RpcException(
                new Status(StatusCode.DeadlineExceeded,
                    $"ValidateAction timed out after {ValidateActionTimeout.TotalSeconds}s (AD-005)."));
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 3: map to gRPC status; never swallow (C-059, C-082)
            _logger.LogError(
                ex,
                "ValidateAction failed: ContractId={ContractId} ActionType={ActionType}",
                req.ContractId, req.ActionType);

            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
    }

    // ─── GrantAuthorityLicense ───────────────────────────────────────────────
    // Stub — full implementation in WC012-03 (Authority License Manager).
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req, ServerCallContext ctx)
        => Task.FromResult(new GrantAuthorityResponse());

    // ─── RevokeAuthorityLicense ──────────────────────────────────────────────
    // Stub — full implementation in WC012-03 (Authority License Manager).
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req, ServerCallContext ctx)
        => Task.FromResult(new RevokeAuthorityResponse());

    // ─── EvaluatePolicy ──────────────────────────────────────────────────────
    // Stub — full implementation in WC012-03.
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req, ServerCallContext ctx)
        => Task.FromResult(new EvaluatePolicyResponse());

    // ─── TriggerEmergencyStop ────────────────────────────────────────────────
    // Stub — Temporal integration is WC012-04b scope.
    // ⛔ Do NOT add Temporalio references here — that is WC012-04b.
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req, ServerCallContext ctx)
        => Task.FromResult(new EmergencyStopResponse());
}