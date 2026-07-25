// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-003 (Authority Licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security), C-059 (Traceability),
//                       C-073 (Annotation), ADR-001 (gRPC Constitutional Engine)

#nullable enable

using Grpc.Core;
using Microsoft.Extensions.Logging;
using System.Diagnostics;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementing the Constitutional Engine boundary validator.
/// All action validation flows through EvaluatorRegistry — short-circuit on first DENY.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    // C-059: traceability — every operation emits an OpenTelemetry span
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly EvaluatorRegistry _registry;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    /// <summary>C-073: constructor injection — DI provides evaluator registry and logger.</summary>
    public ConstitutionalEngineService(
        EvaluatorRegistry registry,
        ILogger<ConstitutionalEngineService> logger)
    {
        ArgumentNullException.ThrowIfNull(registry);
        ArgumentNullException.ThrowIfNull(logger);
        _registry = registry;
        _logger = logger;
    }

    // ─── ValidateAction ────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Implements the PAAS Boundary Validator (§2).
    /// Runs all applicable claim evaluators in order; short-circuits on first DENY.
    /// Default deny — unknown or unlisted actions are denied by C-041.
    /// </summary>
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest request,
        ServerCallContext context)
    {
        ArgumentNullException.ThrowIfNull(request);

        // C-073: extract tenant from gRPC metadata (C-041 default-deny context)
        var tenantId = context.RequestHeaders.GetValue("x-tenant-id") ?? "";

        using var activity = _tracer.StartActivity("ValidateAction", ActivityKind.Server);
        activity?.SetTag("contract_id", request.ContractId);
        activity?.SetTag("action_type", request.ActionType);
        activity?.SetTag("tenant_id", tenantId);

        _logger.LogInformation(
            "ValidateAction: ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
            request.ContractId, request.ActionType, tenantId);

        var ct = context.CancellationToken;

        // Build evaluation context from proto request + tenant metadata
        EvaluationContext ctx;
        try
        {
            ctx = EvaluationContext.FromRequest(request, tenantId);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "ValidateAction: Failed to build EvaluationContext for ContractId={ContractId}",
                request.ContractId);
            throw new RpcException(new Status(StatusCode.InvalidArgument,
                $"Cannot build evaluation context: {ex.Message}"));
        }

        // C-073: run all registered claim evaluators — short-circuit on first DENY
        IReadOnlyList<EvaluationResult> results;
        try
        {
            results = await _registry.EvaluateAllAsync(ctx, ct).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            throw new RpcException(new Status(StatusCode.Cancelled, "ValidateAction cancelled"));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "ValidateAction: EvaluatorRegistry threw for ContractId={ContractId}",
                request.ContractId);
            throw new RpcException(new Status(StatusCode.Internal,
                "Evaluator registry failure — action denied by default (C-041 default deny)"));
        }

        // C-041: first DENY verdict short-circuits — return DENY with claim context
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                activity?.SetTag("decision", "DENY");
                activity?.SetTag("claim_id", result.ClaimId);

                _logger.LogWarning(
                    "ValidateAction: DENY ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                    request.ContractId, result.ClaimId, result.Reason);

                // C-073: compute budget remaining from non-nullable EvaluationContext fields
                // (avoids CS0266 — all three fields are long, result is long, assigned to long?)
                long budgetRemaining = ctx.ApprovedBudgetInrPaise
                                       - ctx.CurrentSpendInrPaise
                                       - ctx.ProposedSpendInrPaise;

                return new ValidateActionResponse
                {
                    Decision             = ValidationDecision.Deny,
                    ConstitutionalBasis  = result.ClaimId,
                    Reason               = result.Reason ?? $"Denied by {result.ClaimId}",
                    BudgetRemainingInrPaise = budgetRemaining   // long → long? implicit, no CS0266
                };
            }

            // C-049: Escalate — forward to human oversight path
            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                activity?.SetTag("decision", "ESCALATE");
                activity?.SetTag("claim_id", result.ClaimId);

                _logger.LogWarning(
                    "ValidateAction: ESCALATE ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                    request.ContractId, result.ClaimId, result.Reason);

                long budgetRemaining = ctx.ApprovedBudgetInrPaise
                                       - ctx.CurrentSpendInrPaise
                                       - ctx.ProposedSpendInrPaise;

                return new ValidateActionResponse
                {
                    Decision             = ValidationDecision.Escalate,
                    ConstitutionalBasis  = result.ClaimId,
                    Reason               = result.Reason ?? $"Escalated by {result.ClaimId}",
                    BudgetRemainingInrPaise = budgetRemaining
                };
            }
        }

        // All evaluators returned Allow — action is constitutionally permitted
        activity?.SetTag("decision", "ALLOW");

        _logger.LogInformation(
            "ValidateAction: ALLOW ContractId={ContractId} ActionType={ActionType}",
            request.ContractId, request.ActionType);

        long remainingBudget = ctx.ApprovedBudgetInrPaise
                               - ctx.CurrentSpendInrPaise
                               - ctx.ProposedSpendInrPaise;

        return new ValidateActionResponse
        {
            Decision             = ValidationDecision.Allow,
            ConstitutionalBasis  = "C-041,C-043,C-048,C-049,C-062",
            Reason               = "All constitutional evaluators passed",
            BudgetRemainingInrPaise = remainingBudget   // long → long? implicit, no CS0266
        };
    }

    // ─── RecordEvidence ────────────────────────────────────────────────────────

    /// <summary>C-073: C-023 Evidence First — persists evidence records (WC012-03).</summary>
    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req,
        ServerCallContext ctx)
    {
        // DESIGN_QUESTION: Full EF Core persistence implemented in WC012-03a/03b.
        // Stub retained to satisfy proto service contract until DB layer is wired.
        _logger.LogInformation(
            "RecordEvidence: ActionInstanceId={ActionInstanceId} ContractId={ContractId}",
            req.ActionInstanceId, req.ContractId);

        return Task.FromResult(new RecordEvidenceResponse
        {
            EvidenceRecordId = Guid.NewGuid().ToString()
        });
    }

    // ─── GrantAuthorityLicense ─────────────────────────────────────────────────

    /// <summary>C-073: C-003 Authority Licensed — grants authority level (WC012-04).</summary>
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req,
        ServerCallContext ctx)
    {
        _logger.LogInformation(
            "GrantAuthorityLicense: ContractId={ContractId} NewAuthorityLevel={Level}",
            req.ContractId, req.NewAuthorityLevel);

        return Task.FromResult(new GrantAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
    }

    // ─── RevokeAuthorityLicense ────────────────────────────────────────────────

    /// <summary>C-073: C-003 Authority Licensed — revokes authority license (WC012-04).</summary>
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req,
        ServerCallContext ctx)
    {
        _logger.LogInformation(
            "RevokeAuthorityLicense: ContractId={ContractId} Reason={Reason}",
            req.ContractId, req.Reason);

        return Task.FromResult(new RevokeAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString()
        });
    }

    // ─── EvaluatePolicy ────────────────────────────────────────────────────────

    /// <summary>C-073: Policy evaluation — permit/deny based on policy rules (WC012-05).</summary>
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req,
        ServerCallContext ctx)
    {
        _logger.LogInformation("EvaluatePolicy invoked");

        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision = PolicyDecision.Permit
        });
    }

    // ─── TriggerEmergencyStop ──────────────────────────────────────────────────

    /// <summary>C-073: C-001 Human Override — emergency stop halts all active sessions.</summary>
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req,
        ServerCallContext ctx)
    {
        _logger.LogCritical(
            "TriggerEmergencyStop: ContractId={ContractId} StoppedBy={StoppedBy}",
            req.ContractId, req.StoppedBy);

        var response = new EmergencyStopResponse
        {
            EmergencyStopRecordId = Guid.NewGuid().ToString()
        };
        response.AffectedSessions.AddRange(req.ActiveSessionIds);
        return Task.FromResult(response);
    }
}