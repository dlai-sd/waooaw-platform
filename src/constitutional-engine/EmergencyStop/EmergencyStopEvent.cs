// Implements: architecture/reference/components/constitutional-engine.md §4 Emergency Stop Handler
// constitutional_basis: C-001 (Emergency Stop absolute), AD-002 (Evidence First)

using System;

namespace Waooaw.ConstitutionalEngine.EmergencyStop;

/// <summary>
/// Persistent evidence record for an Emergency Stop event.
/// Maps to constitutional.emergency_stop_events table.
/// </summary>
/// <remarks>
/// C-001: Every Emergency Stop MUST produce a durable evidence record before
/// any downstream action is taken (Evidence First — AD-002).
/// </remarks>
public sealed class EmergencyStopEvent
{
    // C-073: Constitutional obligation — primary key for evidence record
    public Guid Id { get; init; } = Guid.NewGuid();

    // C-073: Constitutional obligation — the employment contract being stopped
    public Guid ContractId { get; init; }

    // C-073: Constitutional obligation — customer who triggered the stop
    public string InitiatedByUserId { get; init; } = string.Empty;

    // C-073: Constitutional obligation — Temporal workflow IDs halted by this stop
    public string[] AffectedSessionIds { get; init; } = Array.Empty<string>();

    // C-073: Constitutional obligation — UTC timestamp of stop initiation (immutable)
    public DateTimeOffset TriggeredAt { get; init; } = DateTimeOffset.UtcNow;

    // C-073: Constitutional obligation — UTC timestamp when Temporal signal was confirmed
    public DateTimeOffset? TemporalSignalledAt { get; set; }

    // C-073: Constitutional obligation — gRPC trace context for audit correlation
    public string? TraceId { get; init; }

    // C-073: Constitutional obligation — raw source of stop (gRPC, WebSocket, REST-fallback)
    public string StopSource { get; init; } = "gRPC";

    // C-073: Constitutional obligation — final status of the stop operation
    public EmergencyStopStatus Status { get; set; } = EmergencyStopStatus.Pending;
}

public enum EmergencyStopStatus
{
    Pending = 0,
    TemporalSignalled = 1,
    Failed = 2
}