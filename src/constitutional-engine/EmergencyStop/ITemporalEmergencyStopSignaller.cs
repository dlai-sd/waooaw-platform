// Implements: architecture/reference/components/constitutional-engine.md §4 Emergency Stop Handler
// constitutional_basis: C-001 (Emergency Stop absolute), ADR-018 (Temporal workflow IDs)

using System;
using System.Threading;
using System.Threading.Tasks;

namespace Waooaw.ConstitutionalEngine.EmergencyStop;

/// <summary>
/// Abstraction for signalling Temporal workflows to halt on Emergency Stop.
/// Decoupled from the Temporal SDK to allow unit testing (C-076).
/// </summary>
public interface ITemporalEmergencyStopSignaller
{
    // C-073: Constitutional obligation — signal Temporal within 100ms of evidence write
    Task SignalWorkflowsAsync(
        string[] workflowIds,
        Guid emergencyStopEventId,
        CancellationToken cancellationToken = default);
}