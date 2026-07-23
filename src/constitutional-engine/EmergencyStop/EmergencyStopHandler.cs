// Implements: architecture/reference/components/constitutional-engine.md §4 Emergency Stop Handler
// constitutional_basis: C-001 (Emergency Stop absolute), AD-002 (Evidence First),
//                       ADR-018 (Temporal workflow IDs), CCT-HO-01 (≤250ms P99)

using System;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.EmergencyStop;

/// <summary>
/// Orchestrates the Emergency Stop sequence:
///   1. Persist evidence record (AD-002 Evidence First — MUST complete before step 2)
///   2. Signal Temporal workflows to halt (within 100ms of step 1)
///   3. Update evidence record with signal confirmation timestamp
///
/// This handler is called by ConstitutionalEngineService.TriggerEmergencyStop (gRPC RPC).
/// CCT-HO-01: total end-to-end latency MUST be ≤250ms P99.
/// </summary>
public sealed class EmergencyStopHandler
{
    private static readonly ActivitySource _activitySource =
        new("Waooaw.ConstitutionalEngine.EmergencyStop");

    private readonly IEmergencyStopRepository _repository;
    private readonly ITemporalEmergencyStopSignaller _signaller;
    private readonly ILogger<EmergencyStopHandler> _logger;

    public EmergencyStopHandler(
        IEmergencyStopRepository repository,
        ITemporalEmergencyStopSignaller signaller,
        ILogger<EmergencyStopHandler> logger)
    {
        _repository = repository;
        _signaller = signaller;
        _logger = logger;
    }

    /// <summary>
    /// Executes the full Emergency Stop sequence for a contract.
    /// Returns the persisted evidence record on success.
    /// Throws on failure — caller must handle and surface appropriate gRPC status.
    /// </summary>
    // C-073: Constitutional obligation — implements C-001 Emergency Stop absolute guarantee
    public async Task<EmergencyStopResult> ExecuteAsync(
        EmergencyStopRequest request,
        CancellationToken cancellationToken = default)
    {
        using var activity = _activitySource.StartActivity(
            "EmergencyStop.Execute",
            ActivityKind.Internal);

        activity?.SetTag("contract.id", request.ContractId.ToString());
        activity?.SetTag("initiated_by", request.InitiatedByUserId);
        activity?.SetTag("stop.source", request.StopSource);

        var sw = Stopwatch.StartNew();

        _logger.LogInformation(
            "Emergency Stop initiated for contract {ContractId} by user {UserId} via {Source}",
            request.ContractId,
            request.InitiatedByUserId,
            request.StopSource);

        // Resolve session IDs: use provided list or look up all active sessions for contract
        var sessionIds = request.ActiveSessionIds is { Length: > 0 }
            ? request.ActiveSessionIds
            : await _repository.GetActiveSessionIdsForContractAsync(
                request.ContractId,
                cancellationToken);

        // ── STEP 1: Evidence First (AD-002) ──────────────────────────────────────────
        // C-073: Constitutional obligation — evidence record MUST be written before
        //        any downstream action. Do not reorder these steps.
        var stopEvent = new EmergencyStopEvent
        {
            Id = Guid.NewGuid(),
            ContractId = request.ContractId,
            InitiatedByUserId = request.InitiatedByUserId,
            AffectedSessionIds = sessionIds,
            TriggeredAt = DateTimeOffset.UtcNow,
            TraceId = activity?.TraceId.ToString(),
            StopSource = request.StopSource,
            Status = EmergencyStopStatus.Pending
        };

        EmergencyStopEvent persistedEvent;
        try
        {
            persistedEvent = await _repository.PersistEvidenceAsync(stopEvent, cancellationToken);
        }
        catch (Exception ex)
        {
            sw.Stop();
            _logger.LogCritical(
                ex,
                "CRITICAL: Emergency Stop evidence persistence FAILED for contract {ContractId} " +
                "after {ElapsedMs}ms — C-001 / AD-002 violation risk. " +
                "Stop NOT executed to avoid unrecorded action.",
                request.ContractId,
                sw.ElapsedMilliseconds);

            activity?.SetStatus(ActivityStatusCode.Error, "Evidence persistence failed");
            throw;
        }

        var evidenceElapsedMs = sw.ElapsedMilliseconds;
        _logger.LogInformation(
            "Emergency Stop evidence {EventId} persisted in {ElapsedMs}ms (AD-002 satisfied)",
            persistedEvent.Id,
            evidenceElapsedMs);

        // ── STEP 2: Signal Temporal workflows ────────────────────────────────────────
        // C-073: Constitutional obligation — signal within 100ms of evidence write
        try
        {
            await _signaller.SignalWorkflowsAsync(
                sessionIds,
                persistedEvent.Id,
                cancellationToken);
        }
        catch (Exception ex)
        {
            sw.Stop();
            _logger.LogCritical(
                ex,
                "CRITICAL: Emergency Stop Temporal signal FAILED for event {EventId}, " +
                "contract {ContractId} after {ElapsedMs}ms. " +
                "Evidence record exists but workflows may not have halted. " +
                "Manual intervention required.",
                persistedEvent.Id,
                request.ContractId,
                sw.ElapsedMilliseconds);

            // C-073: Constitutional obligation — mark evidence record as failed for audit
            await _repository.MarkFailedAsync(persistedEvent.Id, CancellationToken.None);

            activity?.SetStatus(ActivityStatusCode.Error, "Temporal signal failed");
            throw;
        }

        // ── STEP 3: Update evidence record with signal confirmation ───────────────────
        var signalledAt = DateTimeOffset.UtcNow;
        await _repository.MarkTemporalSignalledAsync(
            persistedEvent.Id,
            signalledAt,
            cancellationToken);

        sw.Stop();

        _logger.LogInformation(
            "Emergency Stop {EventId} completed successfully in {ElapsedMs}ms " +
            "(CCT-HO-01 budget: 250ms P99). Sessions halted: {SessionCount}",
            persistedEvent.Id,
            sw.ElapsedMilliseconds,
            sessionIds.Length);

        // C-073: Constitutional obligation — warn if approaching CCT-HO-01 budget
        if (sw.ElapsedMilliseconds > 200)
        {
            _logger.LogWarning(
                "Emergency Stop {EventId} took {ElapsedMs}ms — approaching CCT-HO-01 250ms P99 budget",
                persistedEvent.Id,
                sw.ElapsedMilliseconds);
        }

        activity?.SetTag("elapsed_ms", sw.ElapsedMilliseconds);
        activity?.SetTag("sessions_halted", sessionIds.Length);

        return new EmergencyStopResult(
            EmergencyStopRecordId: persistedEvent.Id,
            AffectedSessionIds: sessionIds,
            ConfirmedAt: signalledAt);
    }
}

/// <summary>Request model for EmergencyStopHandler.ExecuteAsync.</summary>
public sealed record EmergencyStopRequest(
    Guid ContractId,
    string InitiatedByUserId,
    string[] ActiveSessionIds,
    string StopSource = "gRPC");

/// <summary>Result returned to the gRPC caller after a successful Emergency Stop.</summary>
public sealed record EmergencyStopResult(
    Guid EmergencyStopRecordId,
    string[] AffectedSessionIds,
    DateTimeOffset ConfirmedAt);