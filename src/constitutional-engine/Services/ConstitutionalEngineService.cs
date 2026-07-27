// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-023 (Evidence First), C-003 (authority licensed), C-001 (Emergency Stop)

using Grpc.Core;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>gRPC service stub — full implementation in WC012-02/03/04.</summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    public override Task<RecordEvidenceResponse> RecordEvidence(RecordEvidenceRequest req, ServerCallContext ctx)
        => Task.FromResult(new RecordEvidenceResponse());
    public override Task<ValidateActionResponse> ValidateAction(ValidateActionRequest req, ServerCallContext ctx)
        => Task.FromResult(new ValidateActionResponse());
    public override Task<GrantAuthorityResponse> GrantAuthorityLicense(GrantAuthorityRequest req, ServerCallContext ctx)
        => Task.FromResult(new GrantAuthorityResponse());
    public override Task<RevokeAuthorityResponse> RevokeAuthorityLicense(RevokeAuthorityRequest req, ServerCallContext ctx)
        => Task.FromResult(new RevokeAuthorityResponse());
    public override Task<EvaluatePolicyResponse> EvaluatePolicy(EvaluatePolicyRequest req, ServerCallContext ctx)
        => Task.FromResult(new EvaluatePolicyResponse());
    public override Task<EmergencyStopResponse> TriggerEmergencyStop(EmergencyStopRequest req, ServerCallContext ctx)
        => Task.FromResult(new EmergencyStopResponse());
}
