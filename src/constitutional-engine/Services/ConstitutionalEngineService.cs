// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-023 (Evidence First), C-027 (append-only ledger), C-003 (authority licensed),
//                       C-013 (Emergency Override), AD-001 (Emergency Stop ≤250ms), AD-002 (Evidence First enforcement),
//                       AD-003 (Audit Ledger immutability), AD-005 (PAAS latency budget), AD-008 (constitutional basis on every decision)

using System.Diagnostics;
using Grpc.Core;
using Google.Protobuf.WellKnownTypes;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Interceptors;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementation for the Constitutional Engine.
///
/// All RPCs are stubbed at this scaffold stage and return NOT_IMPLEMENTED.
/// Each stub carries the constitutional annotation for the obligation it will fulfil.
/// Full implementations are delivered in subsequent tasks (WC012-02 through WC012-06).
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    private static readonly ActivitySource _activitySource =
        new("Waooaw.ConstitutionalEngine", "0.1.0");

    private readonly ILogger<ConstitutionalEngineService> _logger;

    public ConstitutionalEngineService(ILogger<ConstitutionalEngineService> logger)
    {
        _logger = logger;
    }

    // ── RecordEvidence ────────────────────────────────────────────────────────
    // C-023: Evidence First — write to Constitutional Audit Ledger atomically before returning.
    // C-027: append-only — INSERT only, never UPDATE or DELETE.
    // AD-002: Evidence First enforcement — caller must not return success until this returns OK.
    // AD-005: latency target < 80ms.
    /// <inheritdoc/>
    public override Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest request,
        ServerCallContext context)
    {
        // C-073: constitutional obligation annotation — Evidence First enforcer
        using var activity = _activitySource.StartActivity("constitutional.evidence.record");
        activity?.SetTag("tenant.id", TenantMetadataInterceptor.CurrentTenantId.ToString());
        activity?.SetTag("evidence.type", request.EvidenceType.ToString());
        activity?.SetTag("contract.id", request.ContractId);

        _logger.LogInformation(
            "RecordEvidence called: EvidenceType={EvidenceType} ContractId={ContractId} TenantId={TenantId}",
            request.EvidenceType, request.ContractId, TenantMetadataInterceptor.CurrentTenantId);

        // STUB: full implementation in WC012-02 (Evidence First Enforcer)
        throw new RpcException(new Status(StatusCode.Unimplemented, "RecordEvidence not yet implemented"));
    }

    // ── ValidateAction ────────────────────────────────────────────────────────
    // C-003: authority licensed — validate action against Decision Space boundary.
    // AD-005: PAAS hot path latency target < 40ms.
    /// <inheritdoc/>
    public override Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest request,
        ServerCallContext context)
    {
        // C-073: constitutional obligation annotation — PAAS Boundary Validator
        using var activity = _activitySource.StartActivity("constitutional.action.validate");
        activity?.SetTag("tenant.id", TenantMetadataInterceptor.CurrentTenantId.ToString());
        activity?.SetTag("action.type", request.ActionType);
        activity?.SetTag("contract.id", request.ContractId);
        activity?.SetTag("session.id", request.SessionId);

        _logger.LogInformation(
            "ValidateAction called: ActionType={ActionType} ContractId={ContractId} TenantId={TenantId}",
            request.ActionType, request.ContractId, TenantMetadataInterceptor.CurrentTenantId);

        // STUB: full implementation in WC012-03 (PAAS Boundary Validator)
        throw new RpcException(new Status(StatusCode.Unimplemented, "ValidateAction not yet implemented"));
    }

    // ── GrantAuthorityLicense ─────────────────────────────────────────────────
    // C-003: authority licensed — record authority expansion event.
    // C-023: Evidence First — justification evidence IDs must be supplied.
    /// <inheritdoc/>
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest request,
        ServerCallContext context)
    {
        // C-073: constitutional obligation annotation — Authority License Manager (grant)
        using var activity = _activitySource.StartActivity("constitutional.authority.grant");
        activity?.SetTag("tenant.id", TenantMetadataInterceptor.CurrentTenantId.ToString());
        activity?.SetTag("contract.id", request.ContractId);
        activity?.SetTag("authority.scope", request.AuthorityScope);

        _logger.LogInformation(
            "GrantAuthorityLicense called: ContractId={ContractId} Scope={Scope} TenantId={TenantId}",
            request.ContractId, request.AuthorityScope, TenantMetadataInterceptor.CurrentTenantId);

        // STUB: full implementation in WC012-04 (Authority License Manager)
        throw new RpcException(new Status(StatusCode.Unimplemented, "GrantAuthorityLicense not yet implemented"));
    }

    // ── RevokeAuthorityLicense ────────────────────────────────────────────────
    // C-003: authority licensed — record authority restriction event.
    // C-023: Evidence First — revocation is recorded in the ledger before returning.
    /// <inheritdoc/>
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest request,
        ServerCallContext context)
    {
        // C-073: constitutional obligation annotation — Authority License Manager (revoke)
        using var activity = _activitySource.StartActivity("constitutional.authority.revoke");
        activity?.SetTag("tenant.id", TenantMetadataInterceptor.CurrentTenantId.ToString());
        activity?.SetTag("license.id", request.LicenseId);
        activity?.SetTag("contract.id", request.ContractId);

        _logger.LogInformation(
            "RevokeAuthorityLicense called: LicenseId={LicenseId} ContractId={ContractId} TenantId={TenantId}",
            request.LicenseId, request.ContractId, TenantMetadataInterceptor.CurrentTenantId);

        // STUB: full implementation in WC012-04 (Authority License Manager)
        throw new RpcException(new Status(StatusCode.Unimplemented, "RevokeAuthorityLicense not yet implemented"));
    }

    // ── EvaluatePolicy ────────────────────────────────────────────────────────
    // AD-008: every permission decision must name its constitutional basis.
    /// <inheritdoc/>
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest request,
        ServerCallContext context)
    {
        // C-073: constitutional obligation annotation — Policy Evaluator
        using var activity = _activitySource.StartActivity("constitutional.policy.evaluate");
        activity?.SetTag("tenant.id", TenantMetadataInterceptor.CurrentTenantId.ToString());
        activity?.SetTag("policy.id", request.PolicyId);
        activity?.SetTag("subject.id", request.SubjectId);

        _logger.LogInformation(
            "EvaluatePolicy called: PolicyId={PolicyId} SubjectId={SubjectId} TenantId={TenantId}",
            request.PolicyId, request.SubjectId, TenantMetadataInterceptor.CurrentTenantId);

        // STUB: full implementation in WC012-05 (Policy Evaluator)
        throw new RpcException(new Status(StatusCode.Unimplemented, "EvaluatePolicy not yet implemented"));
    }

    // ── TriggerEmergencyStop ──────────────────────────────────────────────────
    // C-013: Emergency Override — Constitutional Floor, must always be honoured.
    // AD-001: Emergency Stop ≤250ms end-to-end; CE budget ≤100ms.
    // C-023: Evidence First — stop event recorded in ledger before returning.
    /// <inheritdoc/>
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest request,
        ServerCallContext context)
    {
        // C-073: constitutional obligation annotation — Emergency Stop Handler
        using var activity = _activitySource.StartActivity("constitutional.emergency.stop");
        activity?.SetTag("tenant.id", TenantMetadataInterceptor.CurrentTenantId.ToString());
        activity?.SetTag("session.id", request.SessionId);
        activity?.SetTag("contract.id", request.ContractId);
        activity?.SetTag("triggered.by", request.TriggeredBy);

        _logger.LogCritical(
            "TriggerEmergencyStop called: SessionId={SessionId} ContractId={ContractId} " +
            "TriggeredBy={TriggeredBy} TenantId={TenantId}",
            request.SessionId, request.ContractId,
            request.TriggeredBy, TenantMetadataInterceptor.CurrentTenantId);

        // STUB: full implementation in WC012-06 (Emergency Stop Handler)
        throw new RpcException(new Status(StatusCode.Unimplemented, "TriggerEmergencyStop not yet implemented"));
    }
}