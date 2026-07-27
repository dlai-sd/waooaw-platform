// Implements: architecture/reference/components/constitutional-engine.md
// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop),
//                       C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-062 (AI Security), C-059 (Traceability),
//                       C-073 (Annotated Obligations), C-076 (≥90% test coverage)

#nullable enable

using Grpc.Core;
using Microsoft.Extensions.Logging;
using System.Diagnostics;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementation for the Constitutional Engine.
/// C-073: All overrides annotated with their constitutional obligation.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    // C-073: ActivitySource for OpenTelemetry tracing per ADR-009
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

    // ─────────────────────────────────────────────────────────────────────────
    // C-073: ValidateAction — enforces all runtime-evaluable constitutional claims.
    // Short-circuit on first DENY per ce-validate-action-evaluators.md §Evaluator Architecture.
    // Default deny: unknown contract → DENY (C-041 default-deny principle).
    // ─────────────────────────────────────────────────────────────────────────
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest req,
        ServerCallContext ctx)
    {
        ArgumentNullException.ThrowIfNull(req);

        var ct = ctx.CancellationToken;

        // C-073: Extract tenant identity from gRPC metadata per STACK RULES
        var tenantId = ctx.RequestHeaders.GetValue("x-tenant-id") ?? string.Empty;

        using var activity = _tracer.StartActivity("ValidateAction", ActivityKind.Server);
        activity?.SetTag("contract_id", req.ContractId);
        activity?.SetTag("action_type", req.ActionType);
        activity?.SetTag("tenant_id", tenantId);

        _logger.LogInformation(
            "ValidateAction called ContractId={ContractId} ActionType={ActionType} TenantId={TenantId}",
            req.ContractId, req.ActionType, tenantId);

        // C-041: Default deny — empty contract ID cannot be authorized
        if (string.IsNullOrWhiteSpace(req.ContractId))
        {
            _logger.LogWarning("ValidateAction denied: missing ContractId TenantId={TenantId}", tenantId);
            activity?.SetTag("decision", "Deny");
            activity?.SetTag("deny_reason", "missing_contract_id");
            return new ValidateActionResponse
            {
                Decision           = ValidationDecision.Deny,
                ConstitutionalBasis = "C-041",
                Reason             = "ContractId is required — default deny applies (C-041)."
            };
        }

        // Build evaluation context from proto request + tenant metadata
        // C-073: EvaluationContext.FromRequest maps BudgetContext fields to non-nullable longs
        var evalCtx = EvaluationContext.FromRequest(req, tenantId);

        IReadOnlyList<EvaluationResult> results;
        try
        {
            results = await _registry.EvaluateAllAsync(evalCtx, ct).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("ValidateAction cancelled ContractId={ContractId}", req.ContractId);
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "EvaluatorRegistry fault ContractId={ContractId}", req.ContractId);
            throw new RpcException(new Status(StatusCode.Internal, "Constitutional evaluation fault."));
        }

        // C-073: Short-circuit on first DENY — do not evaluate remaining claims (spec §Evaluator Architecture)
        foreach (var result in results)
        {
            if (result.Verdict == EvaluationVerdict.Deny)
            {
                _logger.LogWarning(
                    "ValidateAction DENY ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                    req.ContractId, result.ClaimId, result.Reason);
                activity?.SetTag("decision", "Deny");
                activity?.SetTag("deny_claim", result.ClaimId);

                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = result.Reason ?? $"Denied by {result.ClaimId}."
                };
            }

            if (result.Verdict == EvaluationVerdict.Escalate)
            {
                _logger.LogWarning(
                    "ValidateAction ESCALATE ContractId={ContractId} ClaimId={ClaimId} Reason={Reason}",
                    req.ContractId, result.ClaimId, result.Reason);
                activity?.SetTag("decision", "Escalate");
                activity?.SetTag("escalate_claim", result.ClaimId);

                // C-049: Escalate maps to Deny at the gRPC boundary — human review required
                return new ValidateActionResponse
                {
                    Decision            = ValidationDecision.Deny,
                    ConstitutionalBasis = result.ClaimId,
                    Reason              = result.Reason ?? $"Escalated by {result.ClaimId} — human review required (C-049)."
                };
            }
        }

        // All evaluators passed — compute remaining budget for caller transparency (C-051)
        // C-073: Nullable rule — ApprovedBudgetInrPaise/CurrentSpendInrPaise/ProposedSpendInrPaise
        //        are non-nullable long on EvaluationContext. Arithmetic produces long.
        //        Assignment to BudgetRemainingInrPaise (long?) is implicit long→long? (no cast needed).
        long budgetRemaining =
            evalCtx.ApprovedBudgetInrPaise
            - evalCtx.CurrentSpendInrPaise
            - evalCtx.ProposedSpendInrPaise;

        _logger.LogInformation(
            "ValidateAction ALLOW ContractId={ContractId} ActionType={ActionType} BudgetRemainingInrPaise={BudgetRemaining}",
            req.ContractId, req.ActionType, budgetRemaining);
        activity?.SetTag("decision", "Allow");
        activity?.SetTag("budget_remaining_inr_paise", budgetRemaining);

        return new ValidateActionResponse
        {
            Decision              = ValidationDecision.Allow,
            ConstitutionalBasis   = "C-041,C-043,C-048,C-049,C-062",
            Reason                = "All constitutional evaluators passed.",
            BudgetRemainingInrPaise = budgetRemaining   // long → long? implicit: no CS0266
        };
    }

    // ─────────────────────────────────────────────────────────────────────────
    // C-073: RecordEvidence — C-023 Evidence First. Implemented in WC012-03.
    // ─────────────────────────────────────────────────────────────────────────
    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest req,
        ServerCallContext ctx)
    {
        // DESIGN_QUESTION: Full persistence wired in WC012-03a (DbContext not yet merged).
        throw new RpcException(new Status(StatusCode.Unimplemented, "RecordEvidence implemented in WC012-03."));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // C-073: GrantAuthorityLicense — C-003 authority licensed
    // ─────────────────────────────────────────────────────────────────────────
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(new Status(StatusCode.Unimplemented, "GrantAuthorityLicense not yet implemented."));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // C-073: RevokeAuthorityLicense — C-003 authority licensed
    // ─────────────────────────────────────────────────────────────────────────
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(new Status(StatusCode.Unimplemented, "RevokeAuthorityLicense not yet implemented."));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // C-073: EvaluatePolicy — policy evaluation boundary
    // ─────────────────────────────────────────────────────────────────────────
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(new Status(StatusCode.Unimplemented, "EvaluatePolicy not yet implemented."));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // C-073: TriggerEmergencyStop — C-001 Human Override (Emergency Stop)
    // ─────────────────────────────────────────────────────────────────────────
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest req,
        ServerCallContext ctx)
    {
        throw new RpcException(new Status(StatusCode.Unimplemented, "TriggerEmergencyStop implemented in WC012-03."));
    }
}