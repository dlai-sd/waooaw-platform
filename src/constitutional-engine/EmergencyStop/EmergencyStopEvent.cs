// Implements: architecture/reference/components/constitutional-engine.md §4
// constitutional_basis: C-001 (Emergency Stop absolute), C-023 (Evidence First), C-027 (append-only)

namespace Waooaw.ConstitutionalEngine.EmergencyStop;

/// <summary>Append-only evidence record for Emergency Stop events. C-001 + C-027.</summary>
public sealed class EmergencyStopEvent
{
    public Guid Id { get; init; } = Guid.NewGuid();
    public Guid ContractId { get; init; }
    public string InitiatedByUserId { get; init; } = string.Empty;
    public string[] AffectedSessionIds { get; init; } = Array.Empty<string>();
    public DateTimeOffset TriggeredAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? TemporalSignalledAt { get; set; }
    public string StopSource { get; init; } = "gRPC";
}
