// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security)
// C-073: ValidateAction implements runtime constitutional enforcement across C-041/043/048/049/062

#nullable enable

using System.Diagnostics;
using Grpc.Core;
using Microsoft.Extensions.Logging;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementing all ConstitutionalService RPC methods.
/// ValidateAction now delegates to the EvaluatorRegistry for runtime constitutional enforcement.
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

    // -------------------------------------------------------------------------
    // C-073: Implements runtime constitutional enforcement across registered claims.
    // Short-circuits on first DENY; all results inspected for Deny/Escalate.
    // WC012-03 will add RecordEvidence calls here (audit trail per C-023).
    // -------------------------------------------------------------------------
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req,
        ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);

        using var activity = _tracer.StartActivity("ValidateAction", ActivityKind.Server);
        activity?.SetTag("contract_id", req.ContractId);
        activity?.SetTag("action_type", req.ActionType);

        var ct = ctx.CancellationToken;

        // Extract tenant from gRPC metadata (C-073: per-tenant constitutional enforcement)
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        if (string.IsNullOrWhiteSpace(req.ContractId))
        {
            _logger.LogWarning(
                "ValidateAction called with empty ContractId. TenantId={TenantId} ActionType={ActionType}",
                tenantId, req.ActionType);

            // Default deny — cannot evaluate without a contract reference (C-041 default deny)
            return new ValidateActionResponse
            {
                Decision = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason = "ValidateAction denied — ContractId is required for all constitutional validation."
            };
        }

        EvaluationContext evalCtx;
        try
        {
            evalCtx = EvaluationContext.FromRequest(req, tenantId);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "Failed to build EvaluationContext. ContractId={ContractId}", req.ContractId);
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                $"Invalid ValidateActionRequest: {ex.Message}"));
        }

        IReadOnlyList<EvaluationResult> results;
        try
        {
            results = await _registry.EvaluateAllAsync(evalCtx, ct).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning(
                "ValidateAction evaluation cancelled. ContractId={ContractId}", req.ContractId);
            throw new RpcException(new Status(StatusCode.Cancelled, "ValidateAction was cancelled."));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "Evaluator registry threw during ValidateAction. ContractId={ContractId}",
                req.ContractId);
            throw new RpcException(new Status(StatusCode.Internal,
                "Constitutional evaluation failed due to an internal error."));
        }

        // C-073: Inspect results — short-circuit on first Deny, then check Escalate
        foreach (var result in results)
        {
            activity?.SetTag($"evaluator.{result.ClaimId}.verdict", result.Verdict.ToString());

            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction DENY: ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                    req.ContractId, result.ClaimId, result.Reason);

                activity?.SetTag("ce.decision", "Deny");
                activity?.SetTag("ce.deny_claim", result.ClaimId);

                // TODO WC012-03: RecordEvidence(type=VALIDATION_DENY, basis=result.ClaimId, ...)
                return new ValidateActionResponse
                {
                    Decision = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason = result.Reason
                };
            }
        }

        // Check for escalation after confirming no denials
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                _logger.LogInformation(
                    "ValidateAction ESCALATE: ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                    req.ContractId, result.ClaimId, result.Reason);

                activity?.SetTag("ce.decision", "Escalate");
                activity?.SetTag("ce.escalate_claim", result.ClaimId);

                // Escalate is surfaced as Deny to callers pending human review (C-049 path)
                // TODO WC012-03: RecordEvidence(type=VALIDATION_ESCALATE, basis=result.ClaimId, ...)
                return new ValidateActionResponse
                {
                    Decision = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason = $"[ESCALATE] {result.Reason}"
                };
            }
        }

        // All evaluators passed — action is constitutionally authorized
        _logger.LogInformation(
            "ValidateAction ALLOW: ContractId={ContractId} ActionType={ActionType} EvaluatorCount={Count}",
            req.ContractId, req.ActionType, results.Count);

        activity?.SetTag("ce.decision", "Allow");

        // TODO WC012-03: RecordEvidence(type=VALIDATION_AUTHORIZED, basis="C-041,C-043,C-048,C-049,C-062", ...)
        return new ValidateActionResponse
        {
            Decision = ValidationDecision.Allow,
            ConstitutionalBasis = "C-041,C-043,C-048,C-049,C-062",
            Reason = "All constitutional evaluators passed."
        };
    }

    // -------------------------------------------------------------------------
    // Existing RPC stubs — preserved from WC012-01 (EXTEND-NOT-REPLACE)
    // -------------------------------------------------------------------------

    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req,
        ServerCallContext ctx)
    {
        // C-073: Full implementation owned by WC012-03 (Evidence Persistence)
        _logger.LogInformation(
            "RecordEvidence called. ContractId={ContractId} ActionType={ActionType}",
            req.ContractId, req.ActionType);

        return Task.FromResult(new RecordEvidenceResponse
        {
            EvidenceRecordId = Guid.NewGuid().ToString()
        });
    }

    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req,
        ServerCallContext ctx)
    {
        _logger.LogInformation(
            "GrantAuthorityLicense called. ContractId={ContractId}", req.ContractId);

        return Task.FromResult(new GrantAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
    }

    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req,
        ServerCallContext ctx)
    {
        _logger.LogInformation(
            "RevokeAuthorityLicense called. ContractId={ContractId}", req.ContractId);

        return Task.FromResult(new RevokeAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
    }

    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req,
        ServerCallContext ctx)
    {
        _logger.LogInformation(
            "EvaluatePolicy called. ContractId={ContractId} ActionType={ActionType}",
            req.ContractId, req.ActionType);

        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit,
            ConstitutionalBasis = "C-023",
            Rationale = "EvaluatePolicy stub — full implementation pending."
        });
    }

    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req,
        ServerCallContext ctx)
    {
        // C-073: Emergency Stop implementation owned by WC012-01 Temporal workflow task
        _logger.LogCritical(
            "TriggerEmergencyStop called. ContractId={ContractId} StoppedBy={StoppedBy}",
            req.ContractId, req.StoppedBy);

        return Task.FromResult(new EmergencyStopResponse
        {
            EmergencyStopRecordId = Guid.NewGuid().ToString()
        });
    }
}