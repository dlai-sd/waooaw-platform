// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security)

#nullable enable

using System.Diagnostics;
using Grpc.Core;
using Microsoft.Extensions.Logging;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementing all constitutional engine operations.
/// WC012-02b extends ValidateAction with full evaluator-backed enforcement.
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
        _logger   = logger;
        _registry = registry;
    }

    // ─── ValidateAction ──────────────────────────────────────────────────────
    // C-073: Implements C-041, C-043, C-048, C-049, C-062 via EvaluatorRegistry

    /// <inheritdoc/>
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req,
        ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);

        var ct       = ctx.CancellationToken;
        // TenantId from gRPC metadata per stack rules
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        using var activity = _tracer.StartActivity("CE.ValidateAction", ActivityKind.Server);
        activity?.SetTag("contract.id", req.ContractId);
        activity?.SetTag("action.type", req.ActionType);
        activity?.SetTag("tenant.id", tenantId);

        _logger.LogInformation(
            "ValidateAction start. ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
            req.ContractId, req.ActionType, tenantId);

        // Default deny: ContractId must be present
        if (string.IsNullOrWhiteSpace(req.ContractId))
        {
            _logger.LogWarning("ValidateAction DENY: ContractId absent.");
            return new ValidateActionResponse
            {
                Decision            = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason              = "ContractId is required. Default deny.",
                BudgetRemainingInrPaise = 0L,
            };
        }

        // Build evaluation context
        var evalCtx = EvaluationContext.FromRequest(req, tenantId);

        IReadOnlyList<EvaluationResult> results;
        try
        {
            results = await _registry.EvaluateAllAsync(evalCtx, ct).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("ValidateAction cancelled. ContractId={ContractId}", req.ContractId);
            throw new RpcException(new Status(StatusCode.Cancelled, "ValidateAction cancelled."));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "ValidateAction evaluator error. ContractId={ContractId}", req.ContractId);
            throw new RpcException(new Status(StatusCode.Internal,
                "Constitutional evaluator error — action denied for safety."));
        }

        // Inspect results — short-circuit on first Deny or Escalate
        // C-073: Any DENY from any evaluator results in DENY response (C-041 default-deny principle)
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction DENY. ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                    req.ContractId, result.ClaimId, result.Reason);

                activity?.SetTag("ce.decision", "Deny");
                activity?.SetTag("ce.deny_claim", result.ClaimId);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = result.Reason,
                    // BudgetRemainingInrPaise is long? — use ?? 0L per stack rules
                    BudgetRemainingInrPaise =
                        (req.BudgetContext?.ApprovedMonthlyBudgetInrPaise ?? 0L)
                        - (req.BudgetContext?.CurrentMonthSpendInrPaise   ?? 0L),
                };
            }

            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                _logger.LogWarning(
                    "ValidateAction ESCALATE→DENY. ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                    req.ContractId, result.ClaimId, result.Reason);

                activity?.SetTag("ce.decision", "Escalate");
                activity?.SetTag("ce.escalate_claim", result.ClaimId);

                // DESIGN_QUESTION: Should Escalate map to ValidationDecision.Escalate once that
                // proto value exists, or route via a separate human-review endpoint? Currently
                // treated as Deny for safety; human-review routing is WC012-04 scope.
                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = $"[ESCALATE→DENY pending human review] {result.Reason}",
                    BudgetRemainingInrPaise =
                        (req.BudgetContext?.ApprovedMonthlyBudgetInrPaise ?? 0L)
                        - (req.BudgetContext?.CurrentMonthSpendInrPaise   ?? 0L),
                };
            }
        }

        // All evaluators passed → ALLOW
        var budgetRemaining =
            (req.BudgetContext?.ApprovedMonthlyBudgetInrPaise ?? 0L)
            - (req.BudgetContext?.CurrentMonthSpendInrPaise   ?? 0L)
            - (req.BudgetContext?.ProposedSpendInrPaise        ?? 0L);

        _logger.LogInformation(
            "ValidateAction ALLOW. ContractId={ContractId} ActionType={ActionType} " +
            "EvaluatorCount={Count} BudgetRemaining={BudgetRemaining}",
            req.ContractId, req.ActionType, results.Count, budgetRemaining);

        activity?.SetTag("ce.decision", "Allow");
        activity?.SetTag("ce.evaluator_count", results.Count);

        return new ValidateActionResponse
        {
            Decision            = ValidationDecision.Allow,
            ConstitutionalBasis = "C-041,C-043,C-048,C-049,C-062",
            Reason              = "All constitutional evaluators passed.",
            BudgetRemainingInrPaise = budgetRemaining,
        };
    }

    // ─── RecordEvidence ───────────────────────────────────────────────────────
    // C-073: Implements C-023 (Evidence First) — all actions must be evidenced

    /// <inheritdoc/>
    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req,
        ServerCallContext ctx)
    {
        // DESIGN_QUESTION: Full DB-backed implementation in WC012-03. Stub retained here.
        ArgumentNullException.ThrowIfNull(req);
        _logger.LogInformation(
            "RecordEvidence stub. ActionInstanceId={ActionInstanceId}", req.ActionInstanceId);
        return Task.FromResult(new RecordEvidenceResponse
        {
            EvidenceRecordId = Guid.NewGuid().ToString("D"),
        });
    }

    // ─── GrantAuthorityLicense ────────────────────────────────────────────────
    // C-073: Implements C-003 (Authority Licensed)

    /// <inheritdoc/>
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req,
        ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);
        _logger.LogInformation(
            "GrantAuthorityLicense stub. ContractId={ContractId}", req.ContractId);
        return Task.FromResult(new GrantAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString("D"),
        });
    }

    // ─── RevokeAuthorityLicense ───────────────────────────────────────────────
    // C-073: Implements C-003 (Authority Licensed)

    /// <inheritdoc/>
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req,
        ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);
        _logger.LogInformation(
            "RevokeAuthorityLicense stub. ContractId={ContractId}", req.ContractId);
        return Task.FromResult(new RevokeAuthorityResponse
        {
            LicenseId = Guid.NewGuid().ToString("D"),
        });
    }

    // ─── EvaluatePolicy ───────────────────────────────────────────────────────

    /// <inheritdoc/>
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req,
        ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);
        _logger.LogInformation(
            "EvaluatePolicy stub. ContractId={ContractId} ActionType={ActionType}",
            req.ContractId, req.ActionType);
        return Task.FromResult(new EvaluatePolicyResponse
        {
            Decision            = PolicyDecision.Permit,
            ConstitutionalBasis = string.Empty,
            Rationale           = "EvaluatePolicy stub — WC012-05 scope.",
        });
    }

    // ─── TriggerEmergencyStop ─────────────────────────────────────────────────
    // C-073: Implements C-001 (Human Override / Emergency Stop)

    /// <inheritdoc/>
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req,
        ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);
        _logger.LogCritical(
            "TriggerEmergencyStop stub. ContractId={ContractId} StoppedBy={StoppedBy}",
            req.ContractId, req.StoppedBy);
        return Task.FromResult(new EmergencyStopResponse
        {
            EmergencyStopRecordId = Guid.NewGuid().ToString("D"),
        });
    }
}