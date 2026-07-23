// Implements: architecture/reference/components/constitutional-engine.md §4 Emergency Stop Handler
// constitutional_basis: C-001 (Emergency Stop absolute), AD-002 (Evidence First), C-059 (Traceability)

using System;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.EmergencyStop;

/// <summary>
/// EF Core implementation of IEmergencyStopRepository.
/// Evidence First (AD-002): every write is durable before Temporal is signalled.
/// </summary>
public sealed class EmergencyStopRepository : IEmergencyStopRepository
{
    private static readonly ActivitySource _activitySource =
        new("Waooaw.ConstitutionalEngine.EmergencyStop");

    private readonly EmergencyStopDbContext _db;
    private readonly ILogger<EmergencyStopRepository> _logger;

    public EmergencyStopRepository(
        EmergencyStopDbContext db,
        ILogger<EmergencyStopRepository> logger)
    {
        _db = db;
        _logger = logger;
    }

    // C-073: Constitutional obligation — Evidence First: persist before any downstream action
    public async Task<EmergencyStopEvent> PersistEvidenceAsync(
        EmergencyStopEvent stopEvent,
        CancellationToken cancellationToken = default)
    {
        using var activity = _activitySource.StartActivity(
            "EmergencyStop.PersistEvidence",
            ActivityKind.Internal);

        activity?.SetTag("contract.id", stopEvent.ContractId.ToString());
        activity?.SetTag("stop.event.id", stopEvent.Id.ToString());
        activity?.SetTag("stop.source", stopEvent.StopSource);

        _logger.LogInformation(
            "Persisting Emergency Stop evidence record {EventId} for contract {ContractId} " +
            "initiated by {UserId}. Source: {Source}",
            stopEvent.Id,
            stopEvent.ContractId,
            stopEvent.InitiatedByUserId,
            stopEvent.StopSource);

        _db.EmergencyStopEvents.Add(stopEvent);
        await _db.SaveChangesAsync(cancellationToken);

        _logger.LogInformation(
            "Emergency Stop evidence record {EventId} persisted successfully (AD-002 Evidence First satisfied)",
            stopEvent.Id);

        return stopEvent;
    }

    // C-073: Constitutional obligation — update evidence record after Temporal signal
    public async Task MarkTemporalSignalledAsync(
        Guid eventId,
        DateTimeOffset signalledAt,
        CancellationToken cancellationToken = default)
    {
        using var activity = _activitySource.StartActivity(
            "EmergencyStop.MarkTemporalSignalled",
            ActivityKind.Internal);

        activity?.SetTag("stop.event.id", eventId.ToString());

        var rows = await _db.EmergencyStopEvents
            .Where(e => e.Id == eventId)
            .ExecuteUpdateAsync(
                setters => setters
                    .SetProperty(e => e.TemporalSignalledAt, signalledAt)
                    .SetProperty(e => e.Status, EmergencyStopStatus.TemporalSignalled),
                cancellationToken);

        if (rows == 0)
        {
            _logger.LogError(
                "Failed to mark Emergency Stop event {EventId} as TemporalSignalled — record not found",
                eventId);
        }
        else
        {
            _logger.LogInformation(
                "Emergency Stop event {EventId} marked as TemporalSignalled at {SignalledAt}",
                eventId,
                signalledAt);
        }
    }

    // C-073: Constitutional obligation — audit trail for failed stops
    public async Task MarkFailedAsync(
        Guid eventId,
        CancellationToken cancellationToken = default)
    {
        using var activity = _activitySource.StartActivity(
            "EmergencyStop.MarkFailed",
            ActivityKind.Internal);

        activity?.SetTag("stop.event.id", eventId.ToString());

        var rows = await _db.EmergencyStopEvents
            .Where(e => e.Id == eventId)
            .ExecuteUpdateAsync(
                setters => setters
                    .SetProperty(e => e.Status, EmergencyStopStatus.Failed),
                cancellationToken);

        _logger.LogError(
            "Emergency Stop event {EventId} marked as Failed (rows updated: {Rows})",
            eventId,
            rows);
    }

    // DESIGN_QUESTION: Active session lookup — see IEmergencyStopRepository for EA question.
    public Task<string[]> GetActiveSessionIdsForContractAsync(
        Guid contractId,
        CancellationToken cancellationToken = default)
    {
        // Placeholder: returns empty array — EA to confirm data ownership and source of truth
        _logger.LogWarning(
            "GetActiveSessionIdsForContractAsync called for contract {ContractId} — " +
            "returning empty (placeholder pending EA decision on data ownership)",
            contractId);

        return Task.FromResult(Array.Empty<string>());
    }
}