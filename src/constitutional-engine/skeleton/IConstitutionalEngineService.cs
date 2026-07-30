// Implements: architecture/reference/components/manifest/ce.yaml §surface.endpoints
// Constitutional basis: C-041 (Tool Authorization), C-023 (Evidence First), C-001 (Human Override)
// EA-PRODUCED SKELETON — implementation project fills logic. DO NOT change signatures.

#nullable enable
namespace Waooaw.ConstitutionalEngine.Skeleton;

using Waooaw.ConstitutionalEngine.Grpc;

/// <summary>
/// Constitutional Engine service contract.
/// All methods are gRPC RPCs — see constitutional_service.proto for wire format.
/// </summary>
public interface IConstitutionalEngineService
{
    /// <summary>
    /// Record evidence of an action BEFORE returning success to the caller.
    /// Constitutional: C-023 — Evidence First. MUST complete before caller returns.
    /// SLA: ≤100ms p99
    /// </summary>
    Task<RecordEvidenceResponse> RecordEvidenceAsync(
        RecordEvidenceRequest request,
        CancellationToken ct = default);

    /// <summary>
    /// Validate that a proposed action is within the agent's constitutional Decision Space.
    /// Constitutional: C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048, C-049.
    /// SLA: ≤40ms p99 (hot path — called before every agent action)
    /// </summary>
    Task<ValidateActionResponse> ValidateActionAsync(
        ValidateActionRequest request,
        CancellationToken ct = default);

    /// <summary>
    /// Trigger Emergency Stop for one or more active PAAS sessions.
    /// Constitutional: C-001 — Human Override. NEVER fails. NEVER blocks.
    /// SLA: ≤250ms p99
    /// </summary>
    Task<TriggerEmergencyStopResponse> TriggerEmergencyStopAsync(
        TriggerEmergencyStopRequest request,
        CancellationToken ct = default);

    /// <summary>
    /// Evaluate a policy claim against the current constitutional state.
    /// SLA: ≤40ms p99
    /// </summary>
    Task<EvaluatePolicyResponse> EvaluatePolicyAsync(
        EvaluatePolicyRequest request,
        CancellationToken ct = default);
}

/// <summary>
/// All evaluator results must use this type to indicate the constitutional decision.
/// Constitutional: C-023 — every ValidateAction call produces evidence of ALLOW or DENY.
/// </summary>
public enum ConstitutionalDecision { Allow, Deny, Escalate }

/// <summary>Thrown when CE is unavailable — triggers ADR-031 fail-safe protocol.</summary>
public sealed class CeUnavailableException(string message) : Exception(message);
