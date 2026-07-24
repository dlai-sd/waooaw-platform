// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security)
// C-073: ValidateAction enforces the constitutional evaluator pipeline (WC012-02b).
// C-065: Author (AI Agent) does not merge this file. Requires human approval before merge.

#nullable enable

using System.Diagnostics;
using Grpc.Core;
using Microsoft.Extensions.Logging;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementation for the Constitutional Engine.
/// Enforces constitutional obligations at runtime via the evaluator pipeline.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
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

    // ── ValidateAction ────────────────────────────────────────────────────────────

    /// <summary>
    /// Evaluates a proposed action against all registered constitutional claim evaluators.
    /// Short-circuits on first DENY. Default deny for empty ContractId.
    /// RecordEvidence side-effect deferred to WC012-03.
    /// </summary>
    // C-073: Core constitutional enforcement gate — all five evaluators (C-041, C-043,
    // C-048, C-049, C-062) are invoked here via EvaluatorRegistry.EvaluateAllAsync.
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req,
        ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);

        using var activity = _tracer.StartActivity(
            "ConstitutionalEngineService.ValidateAction",
            ActivityKind.Server);

        activity?.SetTag("contract_id", req.ContractId);
        activity?.SetTag("action_type", req.ActionType);

        var ct = ctx.CancellationToken;

        // C-073: Default deny — empty ContractId has no valid constitutional basis.
        if (string.IsNullOrWhiteSpace(req.ContractId))
        {
            _logger.LogWarning(
                "ValidateAction DEFAULT DENY: ContractId is empty. ActionType={ActionType}",
                req.ActionType);

            activity?.SetTag("decision", "Deny");
            activity?.SetTag("deny_reason", "empty_contract_id");

            return new ValidateActionResponse
            {
                Decision = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason = "ContractId is required. Default deny — no valid employment contract context.",
            };
        }

        // Extract tenant from gRPC metadata (x-tenant-id header).
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        activity?.SetTag("tenant_id", tenantId);

        _logger.LogInformation(
            "ValidateAction: ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
            req.ContractId, req.ActionType, tenantId);

        // Build evaluation context from the incoming request.
        var evalCtx = EvaluationContext.FromRequest(req, tenantId);

        IReadOnlyList<EvaluationResult> results;
        try
        {
            // C-073: Invoke all applicable evaluators. Short-circuit on first DENY is
            // handled inside EvaluatorRegistry.EvaluateAllAsync.
            results = await _registry.EvaluateAllAsync(evalCtx, ct).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning(
                "ValidateAction cancelled. ContractId={ContractId}", req.ContractId);
            throw new RpcException(new Status(StatusCode.Cancelled, "ValidateAction was cancelled."));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "ValidateAction internal error. ContractId={ContractId} ActionType={ActionType}",
                req.ContractId, req.ActionType);
            throw new RpcException(
                new Status(StatusCode.Internal, "Constitutional evaluation failed — see service logs."));
        }

        // Inspect results for any DENY or ESCALATE verdict.
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction DENY: ClaimId={ClaimId} Reason={Reason} ContractId={ContractId}",
                    result.ClaimId, result.Reason, req.ContractId);

                activity?.SetTag("decision", "Deny");
                activity?.SetTag("deny_claim", result.ClaimId);

                return new ValidateActionResponse
                {
                    Decision = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason = result.Reason,
                };
            }

            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                _logger.LogWarning(
                    "ValidateAction ESCALATE: ClaimId={ClaimId} Reason={Reason} ContractId={ContractId}",
                    result.ClaimId, result.Reason, req.ContractId);

                activity?.SetTag("decision", "Escalate");
                activity?.SetTag("escalate_claim", result.ClaimId);

                return new ValidateActionResponse
                {
                    Decision = ValidationDecision.Escalate,
                    ConstitutionalBasis = result.ClaimId,
                    Reason = result.Reason,
                };
            }
        }

        // All evaluators passed → ALLOW.
        _logger.LogInformation(
            "ValidateAction ALLOW: ContractId={ContractId} ActionType={ActionType} EvaluatorCount={Count}",
            req.ContractId, req.ActionType, results.Count);

        activity?.SetTag("decision", "Allow");
        activity?.SetTag("evaluator_count", results.Count);

        return new ValidateActionResponse
        {
            Decision = ValidationDecision.Allow,
            ConstitutionalBasis = "C-041,C-043,C-048,C-049,C-062",
            Reason = $"All {results.Count} constitutional evaluators passed.",
        };
    }

    // ── RecordEvidence ────────────────────────────────────────────────────────────

    // C-073: Evidence recording — implementation completed in WC012-03.
    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req,
        ServerCallContext ctx)
    {
        // DESIGN_QUESTION: Full DB-backed implementation is in WC012-03a/03b.
        // This stub maintains compilability on the sprint branch until WC012-03 lands.
        throw new RpcException(
            new Status(StatusCode.Unimplemented, "RecordEvidence: implementation pending WC012-03."));
    }

    // ── GrantAuthorityLicense ─────────────────────────────────────────────────────

    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(
            new Status(StatusCode.Unimplemented, "GrantAuthorityLicense: implementation pending."));
    }

    // ── RevokeAuthorityLicense ────────────────────────────────────────────────────

    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(
            new Status(StatusCode.Unimplemented, "RevokeAuthorityLicense: implementation pending."));
    }

    // ── EvaluatePolicy ────────────────────────────────────────────────────────────

    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(
            new Status(StatusCode.Unimplemented, "EvaluatePolicy: implementation pending."));
    }

    // ── TriggerEmergencyStop ──────────────────────────────────────────────────────

    // C-073: Emergency Stop — C-001 hard override. Implementation in WC012-01.
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(
            new Status(StatusCode.Unimplemented, "TriggerEmergencyStop: implementation pending WC012-01."));
    }
}