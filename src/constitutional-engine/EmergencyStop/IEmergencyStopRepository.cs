// Implements: architecture/reference/components/constitutional-engine.md §4 Emergency Stop Handler
// constitutional_basis: C-001 (Emergency Stop absolute), AD-002 (Evidence First)

using System;
using System.Threading;
using System.Threading.Tasks;

namespace Waooaw.ConstitutionalEngine.EmergencyStop;

/// <summary>
/// Repository abstraction for Emergency Stop evidence persistence.
/// Exists to allow unit testing without a live database (C-076).
/// </summary>
public interface IEmergencyStopRepository
{
    // C-073: Constitutional obligation — persist evidence record BEFORE signalling Temporal
    Task<EmergencyStopEvent> PersistEvidenceAsync(
        EmergencyStopEvent stopEvent,
        CancellationToken cancellationToken = default);

    // C-073: Constitutional obligation — update record after Temporal signal confirmed
    Task MarkTemporalSignalledAsync(
        Guid eventId,
        DateTimeOffset signalledAt,
        CancellationToken cancellationToken = default);

    // C-073: Constitutional obligation — mark record as failed for audit trail
    Task MarkFailedAsync(
        Guid eventId,
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Retrieves all known active session IDs for a contract.
    /// Used when the client omits activeSessionIds from the stop command.
    /// </summary>
    // DESIGN_QUESTION: Should active session lookup be owned by CE or by Professional Runtime?
    //                  Placeholder implementation returns empty — EA to confirm data ownership.
    Task<string[]> GetActiveSessionIdsForContractAsync(
        Guid contractId,
        CancellationToken cancellationToken = default);
}