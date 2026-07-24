// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-023 (Evidence First), C-027 (append-only ledger), C-003 (authority licensed),
//                       C-013 (Emergency Override), AD-001 (Emergency Stop ≤250ms), AD-002 (Evidence First enforcement),
//                       AD-005 (PAAS latency budget), AD-008 (every permission decision names constitutional basis)

using System.Diagnostics;
using Grpc.Core;
using Microsoft.Extensions.Logging;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Infrastructure;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementation for the Constitutional Engine.
/// This is the architectural implementation of Evidence First (C-023).
/// All governance events flow through this service before the calling service
/// may return success to its own client.
///
/// INTERNAL ONLY — never exposed to the internet (ADR-001).
/// Tenant isolation is enforced via gRPC metadata "x-tenant-id" on every call.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    private static readonly ActivitySource ActivitySource =
        new("Waooaw.ConstitutionalEngine", "1.0.0");

    private readonly ILogger<ConstitutionalEngineService> _logger;
    private readonly ITenantMetadataExtractor _tenantExtractor;

    public ConstitutionalEngineService(
        ILogger<ConstitutionalEngineService> logger,
        ITenantMetadataExtractor tenantExtractor)
    {
        _logger = logger;
        _tenantExtractor = tenantExtractor;
    }

    // ─── RecordEvidence ───────────────────────────────────────────────────────

    /// <summary>
    /// Evidence First Enforcer — writes an evidence record to the Constitutional Audit Ledger
    /// atomically before returning. If the write fails, returns gRPC INTERNAL so the caller
    /// does not return success to its own client.
    ///
    /// C-073: Implements C-023 (Evidence First), C-027 (append-only ledger), AD-002.
    /// Latency target: &lt;80ms (AD-005).
    /// </summary>
    public override async Task<RecordEvidenceResponse> RecordEvidence(
        RecordEvidenceRequest request,
        ServerCallContext context)
    {
        // C-073: Tenant extraction enforces C-029 (scope-boundary record) — every record is tenant-scoped.
        var tenantId = _tenantExtractor.ExtractTenantId(context);

        using var activity = ActivitySource.StartActivity("constitutional.evidence.record");
        activity?.SetTag("tenant.id", tenantId);
        activity?.SetTag("contract.id", request.ContractId);
        activity?.SetTag("evidence.type", request.EvidenceType.ToString());
        activity?.SetTag("constitutional.basis", "C-023;C-027;AD-002");

        _logger.LogInformation(
            "RecordEvidence called. TenantId={TenantId} ContractId={ContractId} EvidenceType={EvidenceType} IdempotencyKey={IdempotencyKey}",
            tenantId, request.ContractId, request.EvidenceType, request.IdempotencyKey);

        // DESIGN_QUESTION: Should the Evidence First Enforcer implementation be injected
        // as IEvidenceFirstEnforcer here, or should the DB write logic live directly in
        // this service class? Recommend injected handler for testability — awaiting EA confirmation.

        // Stub implementation — full implementation in WC012-02 (Evidence First Enforcer)
        await Task.CompletedTask;

        var evidenceId = Guid.NewGuid().ToString();
        var recordedAt = DateTimeOffset.UtcNow;

        _logger.LogInformation(
            "RecordEvidence stub returning. EvidenceId={EvidenceId} TenantId={TenantId}",
            evidenceId, tenantId);

        return new RecordEvidenceResponse
        {
            EvidenceId = evidenceId,
            RecordedAt = Google.Protobuf.WellKnownTypes.Timestamp.FromDateTimeOffset(recordedAt),
            WasDuplicate = false,
        };
    }

    // ─── ValidateAction ───────────────────────────────────────────────────────

    /// <summary>
    /// PAAS Boundary Validator — validates whether a proposed action falls within
    /// the current Decision Space. Returns ALLOW, DENY, or ESCALATE.
    /// Does NOT record evidence — caller must call RecordEvidence after this decision.
    ///
    /// C-073: Implements C-003 (authority licensed), AD-005 (PAAS latency budget &lt;40ms).
    /// On DENY: emits constitutional.authority.violated OTel span.
    /// </summary>
    public override async Task<ValidateActionResponse> ValidateAction(
        ValidateActionRequest request,
        ServerCallContext context)
    {
        var tenantId = _tenantExtractor.ExtractTenantId(context);

        using var activity = ActivitySource.StartActivity("constitutional.action.validate");
        activity?.SetTag("tenant.id", tenantId);
        activity?.SetTag("contract.id", request.ContractId);
        activity?.SetTag("action.type", request.ActionType);
        activity?.SetTag("constitutional.basis", "C-003;AD-005");

        _logger.LogInformation(
            "ValidateAction called. TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
            tenantId, request.ContractId, request.ActionType);

        // DESIGN_QUESTION: Decision Space cache warming strategy — should the cache be
        // warmed at session start via a Temporal signal, or lazily on first ValidateAction call?
        // AD-005 latency budget of 40ms may not tolerate a cold DB read. Awaiting EA decision.

        // Stub implementation — full implementation in WC012-03 (PAAS Boundary Validator)
        await Task.CompletedTask;

        return new ValidateActionResponse
        {
            Decision = ActionDecision.Allow,
            Reason = "Stub: Decision Space validation not yet implemented.",
            ConstitutionalBasis = "C-003 authority licensed; AD-005 PAAS latency budget",
            EscalationPrompt = string.Empty,
        };
    }

    // ─── GrantAuthorityLicense ────────────────────────────────────────────────

    /// <summary>
    /// Authority License Manager (expansion) — records an authority expansion event
    /// in the Constitutional Audit Ledger. Validates that justifying evidence IDs
    /// are provided and belong to the same contract.
    ///
    /// C-073: Implements C-003 (authority licensed), C-023 (Evidence First).
    /// </summary>
    public override async Task<GrantAuthorityResponse> GrantAuthorityLicense(
        GrantAuthorityRequest request,
        ServerCallContext context)
    {
        var tenantId = _tenantExtractor.ExtractTenantId(context);

        using var activity = ActivitySource.StartActivity("constitutional.authority.grant");
        activity?.SetTag("tenant.id", tenantId);
        activity?.SetTag("contract.id", request.ContractId);
        activity?.SetTag("constitutional.basis", "C-003;C-023");

        _logger.LogInformation(
            "GrantAuthorityLicense called. TenantId={TenantId} ContractId={ContractId} GrantedBy={GrantedBy} ActionTypesCount={Count}",
            tenantId, request.ContractId, request.GrantedBy, request.ActionTypesGranted.Count);

        // Stub implementation — full implementation in WC012-04 (Authority License Manager)
        await Task.CompletedTask;

        var evidenceId = Guid.NewGuid().ToString();
        var grantedAt = DateTimeOffset.UtcNow;

        return new GrantAuthorityResponse
        {
            EvidenceId = evidenceId,
            GrantedAt = Google.Protobuf.WellKnownTypes.Timestamp.FromDateTimeOffset(grantedAt),
        };
    }

    // ─── RevokeAuthorityLicense ───────────────────────────────────────────────

    /// <summary>
    /// Authority License Manager (restriction) — records an authority restriction
    /// or suspension event in the Constitutional Audit Ledger.
    ///
    /// C-073: Implements C-003 (authority licensed), C-023 (Evidence First).
    /// </summary>
    public override async Task<RevokeAuthorityResponse> RevokeAuthorityLicense(
        RevokeAuthorityRequest request,
        ServerCallContext context)
    {
        var tenantId = _tenantExtractor.ExtractTenantId(context);

        using var activity = ActivitySource.StartActivity("constitutional.authority.revoke");
        activity?.SetTag("tenant.id", tenantId);
        activity?.SetTag("contract.id", request.ContractId);
        activity?.SetTag("constitutional.basis", "C-003;C-023");

        _logger.LogInformation(
            "RevokeAuthorityLicense called. TenantId={TenantId} ContractId={ContractId} RevokedBy={RevokedBy}",
            tenantId, request.ContractId, request.RevokedBy);

        // Stub implementation — full implementation in WC012-04 (Authority License Manager)
        await Task.CompletedTask;

        var evidenceId = Guid.NewGuid().ToString();
        var revokedAt = DateTimeOffset.UtcNow;

        return new RevokeAuthorityResponse
        {
            EvidenceId = evidenceId,
            RevokedAt = Google.Protobuf.WellKnownTypes.Timestamp.FromDateTimeOffset(revokedAt),
        };
    }

    // ─── EvaluatePolicy ───────────────────────────────────────────────────────

    /// <summary>
    /// Policy Evaluator — general-purpose constitutional policy evaluation.
    /// Returns a decision with the constitutional basis string required for audit records.
    ///
    /// C-073: Implements AD-008 (every permission decision must name its constitutional basis).
    /// </summary>
    public override async Task<EvaluatePolicyResponse> EvaluatePolicy(
        EvaluatePolicyRequest request,
        ServerCallContext context)
    {
        var tenantId = _tenantExtractor.ExtractTenantId(context);

        using var activity = ActivitySource.StartActivity("constitutional.policy.evaluate");
        activity?.SetTag("tenant.id", tenantId);
        activity?.SetTag("contract.id", request.ContractId);
        activity?.SetTag("policy.id", request.PolicyId);
        activity?.SetTag("constitutional.basis", "AD-008");

        _logger.LogInformation(
            "EvaluatePolicy called. TenantId={TenantId} ContractId={ContractId} PolicyId={PolicyId} Actor={Actor}",
            tenantId, request.ContractId, request.PolicyId, request.Actor);

        // Stub implementation — full implementation in WC012-05 (Policy Evaluator)
        await Task.CompletedTask;

        return new EvaluatePolicyResponse
        {
            Decision = ActionDecision.Allow,
            Explanation = "Stub: Policy evaluation not yet implemented.",
            ConstitutionalBasis = "AD-008 every permission decision names constitutional basis",
            EvaluationOutputJson = "{}",
        };
    }

    // ─── TriggerEmergencyStop ─────────────────────────────────────────────────

    /// <summary>
    /// Emergency Stop Handler — records the stop event in the Constitutional Audit Ledger
    /// before returning confirmation, then signals the affected Professional Runtime to halt.
    ///
    /// C-073: Implements C-013 (Emergency Override — Constitutional Floor),
    ///        AD-001 (Emergency Stop ≤250ms end-to-end; this handler target ≤100ms).
    ///
    /// CRITICAL PATH: DB write must complete within 80ms (AD-005).
    /// Temporal signal is sent after the DB write — if signal fails, the stop is still
    /// recorded in the ledger and the response indicates runtime_signal_sent=false.
    /// </summary>
    public override async Task<EmergencyStopResponse> TriggerEmergencyStop(
        EmergencyStopRequest request,
        ServerCallContext context)
    {
        var tenantId = _tenantExtractor.ExtractTenantId(context);

        // C-073: Emergency Stop span — C-013 Constitutional Floor, AD-001 latency constraint.
        using var activity = ActivitySource.StartActivity("constitutional.emergency.stop");
        activity?.SetTag("tenant.id", tenantId);
        activity?.SetTag("contract.id", request.ContractId);
        activity?.SetTag("session.id", request.SessionId);
        activity?.SetTag("stop.reason", request.Reason.ToString());
        activity?.SetTag("constitutional.basis", "C-013;AD-001");

        _logger.LogWarning(
            "TriggerEmergencyStop called. TenantId={TenantId} ContractId={ContractId} SessionId={SessionId} Reason={Reason} TriggeredBy={TriggeredBy}",
            tenantId, request.ContractId, request.SessionId, request.Reason, request.TriggeredBy);

        // Stub implementation — full implementation in WC012-06 (Emergency Stop Handler)
        // CRITICAL: In production, DB write must complete within 80ms before this returns.
        await Task.CompletedTask;

        var evidenceId = Guid.NewGuid().ToString();
        var stoppedAt = DateTimeOffset.UtcNow;

        _logger.LogWarning(
            "EmergencyStop recorded. EvidenceId={EvidenceId} TenantId={TenantId} ContractId={ContractId} SessionId={SessionId}",
            evidenceId, tenantId, request.ContractId, request.SessionId);

        return new EmergencyStopResponse
        {
            EvidenceId = evidenceId,
            StoppedAt = Google.Protobuf.WellKnownTypes.Timestamp.FromDateTimeOffset(stoppedAt),
            RuntimeSignalSent = false, // Stub: Temporal signal not yet implemented
        };
    }
}