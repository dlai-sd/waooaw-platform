// Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-4 Execution status and action timeline (WC170-R007, WC170-R010)
// Constitutional basis: C-001, C-005, C-023, C-049, C-059, C-063
// IB: IB-170

using System.Collections.Concurrent;
using System.Globalization;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Waooaw.BusinessPlatform.Services.RealWork;

public static class TimelineStates
{
    public const string Proposed = "PROPOSED";
    public const string Approved = "APPROVED";
    public const string Executing = "EXECUTING";
    public const string Completed = "COMPLETED";
    public const string Failed = "FAILED";
    public const string Halted = "HALTED";

    public static readonly IReadOnlySet<string> All = new HashSet<string>([
        Proposed,
        Approved,
        Executing,
        Completed,
        Failed,
        Halted,
    ]);

    /// <summary>Order of progress. A late lower-rank event is stored but never moves a work item back.</summary>
    public static int Rank(string state) =>
        state switch
        {
            Proposed => 0,
            Approved => 1,
            Executing => 2,
            _ => 3,
        };
}

public static class TimelineReasons
{
    public const string EmergencyStop = "EMERGENCY_STOP";
    public const string ProviderRejected = "PROVIDER_REJECTED";
    public const string UnknownOutcome = "UNKNOWN_OUTCOME";
    public const string Reconciled = "RECONCILED";
    public const string AwaitingProviderProof = "AWAITING_PROVIDER_PROOF";
    public const string PolicyBlocked = "POLICY_BLOCKED";
    public const string TimedOut = "TIMED_OUT";

    public static readonly IReadOnlySet<string> All = new HashSet<string>([
        EmergencyStop,
        ProviderRejected,
        UnknownOutcome,
        Reconciled,
        AwaitingProviderProof,
        PolicyBlocked,
        TimedOut,
    ]);
}

/// <summary>What the runtime reports. Free text from an agent never reaches the customer: the sentence is built here.</summary>
public sealed record TimelineEventInput(
    Guid EventId,
    Guid WorkItemId,
    string WorkItemType,
    string State,
    DateTimeOffset OccurredAt,
    Guid? ArtifactId = null,
    string? ArtifactDigest = null,
    bool ProducesArtifact = false,
    IReadOnlyList<string>? EvidenceRefs = null,
    string? ReasonCode = null,
    bool RequiresProviderProof = false,
    string? ProviderReference = null
);

public sealed record TimelineEventView(
    Guid EventId,
    Guid WorkItemId,
    string WorkItemType,
    string State,
    Guid? ArtifactId,
    string? ArtifactDigest,
    IReadOnlyList<string> EvidenceRefs,
    string? ReasonCode,
    string? ProviderReference,
    DateTimeOffset OccurredAt,
    long Sequence,
    string Sentence
);

public sealed record TimelineWorkItemView(
    Guid WorkItemId,
    string WorkItemType,
    string State,
    string? ReasonCode,
    string Sentence,
    IReadOnlyList<TimelineEventView> Events
);

public sealed record TimelineView(
    Guid RelationshipId,
    IReadOnlyList<TimelineEventView> Events,
    IReadOnlyList<TimelineWorkItemView> WorkItems,
    bool EmergencyStopActive
);

public sealed partial class RealWorkTimelineService(
    IRealWorkLedger ledger,
    RealWorkDecisionService decisions,
    TimeProvider clock
)
{
    public const string StopWorkItemType = "EMERGENCY_STOP";
    public const string StopClearedWorkItemType = "EMERGENCY_STOP_CLEARED";
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    [GeneratedRegex(@"^[A-Z][A-Z0-9_]{2,63}$")]
    private static partial Regex TypePattern();

    // Tokens, secrets and credentials never enter the stream or any response (D3). References are reference-shaped
    // only: no whitespace, and no long unbroken opaque run that could be a credential.
    [GeneratedRegex(
        @"(?i)(bearer\s|access[_-]?token|secret|password|api[_-]?key|EAA[A-Za-z0-9]{20,})"
    )]
    private static partial Regex SecretPattern();

    [GeneratedRegex(@"^[A-Za-z0-9_.:/@=-]{1,200}$")]
    private static partial Regex ReferencePattern();

    [GeneratedRegex(@"[A-Za-z0-9+/_]{40,}")]
    private static partial Regex OpaqueRunPattern();

    private static readonly ConcurrentDictionary<(Guid, Guid), object> RelationshipLocks = new();

    /// <summary>One writer per relationship at a time, so a stop and a late result cannot interleave their check and append.</summary>
    public TimelineEventView Ingest(Guid tenantId, Guid relationshipId, TimelineEventInput input)
    {
        lock (RelationshipLocks.GetOrAdd((tenantId, relationshipId), _ => new object()))
            return IngestCore(tenantId, relationshipId, input);
    }

    private TimelineEventView IngestCore(
        Guid tenantId,
        Guid relationshipId,
        TimelineEventInput input
    )
    {
        Validate(input);
        var existing = Events(tenantId, relationshipId);
        var replay = existing.FirstOrDefault(item => item.EventId == input.EventId);
        if (replay is not null)
            return
                replay.WorkItemId == input.WorkItemId
                && replay.WorkItemType == input.WorkItemType
                && replay.ArtifactDigest == input.ArtifactDigest
                && (replay.State == input.State || replay.ReasonCode is not null)
                ? replay
                : throw new RealWorkConflictException("REAL_WORK_IDEMPOTENCY_CONFLICT");

        var state = input.State;
        var reason = input.ReasonCode;
        var isStopMarker = input.WorkItemType is StopWorkItemType or StopClearedWorkItemType;
        var stopActive = StopActive(existing);
        var latest = existing
            .Where(item => item.WorkItemId == input.WorkItemId)
            .OrderByDescending(item => TimelineStates.Rank(item.State))
            .ThenByDescending(item => item.Sequence)
            .FirstOrDefault();

        if (
            !isStopMarker
            && stopActive
            && state is not (TimelineStates.Halted or TimelineStates.Failed)
        )
        {
            // Emergency Stop fences the stream: a result that arrives later is evidence, never success (G1).
            state = TimelineStates.Halted;
            reason = TimelineReasons.EmergencyStop;
        }
        else if (
            !isStopMarker
            && latest?.ReasonCode == TimelineReasons.UnknownOutcome
            && latest.State is TimelineStates.Executing or TimelineStates.Failed
            && state == TimelineStates.Executing
            && reason is not (TimelineReasons.UnknownOutcome or TimelineReasons.Reconciled)
        )
            throw new RealWorkConflictException("REAL_WORK_BLIND_RETRY");
        else if (
            state == TimelineStates.Completed
            && input.RequiresProviderProof
            && string.IsNullOrWhiteSpace(input.ProviderReference)
        )
        {
            // Accepted or receipt-only is work in progress until the provider's own reference exists (D3).
            state = TimelineStates.Executing;
            reason = TimelineReasons.AwaitingProviderProof;
        }

        if (
            !isStopMarker
            && state
                is TimelineStates.Approved
                    or TimelineStates.Executing
                    or TimelineStates.Completed
            && !input.ProducesArtifact
        )
        {
            if (input.ArtifactId is null)
                throw new RealWorkConflictException("REAL_WORK_ARTIFACT_NOT_EXECUTABLE");
            var gate = decisions.Check(
                tenantId,
                relationshipId,
                input.ArtifactId.Value,
                input.ArtifactDigest
            );
            if (!gate.Executable)
                throw new RealWorkConflictException("REAL_WORK_ARTIFACT_NOT_EXECUTABLE");
        }
        if (state is TimelineStates.Failed or TimelineStates.Halted && reason is null)
            throw new RealWorkConflictException("REAL_WORK_INVALID_REQUEST");

        var view = new TimelineEventView(
            input.EventId,
            input.WorkItemId,
            input.WorkItemType,
            state,
            input.ArtifactId,
            input.ArtifactDigest,
            (input.EvidenceRefs ?? []).Distinct().ToArray(),
            reason,
            input.ProviderReference,
            input.OccurredAt.ToUniversalTime(),
            0,
            Sentence(input.WorkItemType, state, reason)
        );
        var record = ledger.Append(
            tenantId,
            relationshipId,
            RealWorkKinds.Timeline,
            input.EventId.ToString("N"),
            JsonSerializer.SerializeToElement(view, Json),
            clock.GetUtcNow()
        );
        return view with { Sequence = record.Sequence };
    }

    public TimelineView Read(Guid tenantId, Guid relationshipId)
    {
        var events = Events(tenantId, relationshipId);
        var items = events
            .Where(item => item.WorkItemType is not (StopWorkItemType or StopClearedWorkItemType))
            .GroupBy(item => item.WorkItemId)
            .Select(group =>
            {
                var ordered = group.OrderBy(item => item.Sequence).ToArray();
                var latest = ordered
                    .OrderByDescending(item => TimelineStates.Rank(item.State))
                    .ThenByDescending(item => item.Sequence)
                    .First();
                return new TimelineWorkItemView(
                    group.Key,
                    latest.WorkItemType,
                    latest.State,
                    latest.ReasonCode,
                    latest.Sentence,
                    ordered
                );
            })
            .OrderBy(item => item.Events[0].Sequence)
            .ToArray();
        return new TimelineView(relationshipId, events, items, StopActive(events));
    }

    internal IReadOnlyList<TimelineEventView> Events(Guid tenantId, Guid relationshipId) =>
        ledger
            .List(tenantId, relationshipId, RealWorkKinds.Timeline)
            .Select(record =>
                record.Payload.Deserialize<TimelineEventView>(Json)! with
                {
                    Sequence = record.Sequence,
                }
            )
            .ToArray();

    private static bool StopActive(IReadOnlyList<TimelineEventView> events)
    {
        var marker = events
            .Where(item => item.WorkItemType is StopWorkItemType or StopClearedWorkItemType)
            .MaxBy(item => item.Sequence);
        return marker?.WorkItemType == StopWorkItemType;
    }

    private static void Validate(TimelineEventInput input)
    {
        var refs = input.EvidenceRefs ?? [];
        if (
            input.EventId == Guid.Empty
            || input.WorkItemId == Guid.Empty
            || !TypePattern().IsMatch(input.WorkItemType)
            || !TimelineStates.All.Contains(input.State)
            || (input.ReasonCode is not null && !TimelineReasons.All.Contains(input.ReasonCode))
            || refs.Count > 20
            || refs.Any(item => string.IsNullOrWhiteSpace(item) || item.Length > 200)
            || (input.ArtifactDigest is not null && input.ArtifactDigest.Length != 64)
            || (input.ProviderReference?.Length ?? 0) > 200
            // The artifact-creating exemption is for non-consequential bootstrap steps only: it can never carry
            // provider proof or an artifact binding of its own.
            || (
                input.ProducesArtifact
                && (
                    input.RequiresProviderProof
                    || input.ProviderReference is not null
                    || input.ArtifactId is not null
                )
            )
        )
            throw new RealWorkConflictException("REAL_WORK_INVALID_REQUEST");
        if (
            refs.Any(IsCredentialLike)
            || (input.ProviderReference is not null && IsCredentialLike(input.ProviderReference))
        )
            throw new RealWorkConflictException("REAL_WORK_SECRET_REJECTED");
    }

    private static bool IsCredentialLike(string value) =>
        SecretPattern().IsMatch(value)
        || !ReferencePattern().IsMatch(value)
        || OpaqueRunPattern().IsMatch(value);

    private static string Sentence(string workItemType, string state, string? reason)
    {
        var what = Humanize(workItemType);
        return (state, reason) switch
        {
            (_, TimelineReasons.UnknownOutcome) =>
                $"We do not know yet how the {what} turned out. We are checking and will not repeat it blindly.",
            (_, TimelineReasons.AwaitingProviderProof) =>
                $"The {what} was accepted. It counts as done only when the provider confirms it.",
            (TimelineStates.Halted, TimelineReasons.EmergencyStop) =>
                $"The {what} was stopped by Emergency Stop. Any later result is kept as evidence only.",
            (TimelineStates.Completed, TimelineReasons.Reconciled) =>
                $"The {what} was checked afterwards and is confirmed done.",
            (TimelineStates.Failed, TimelineReasons.Reconciled) =>
                $"The {what} was checked afterwards and did not happen.",
            (TimelineStates.Proposed, _) => $"The agent proposed {what}.",
            (TimelineStates.Approved, _) => $"The {what} is approved and ready to run.",
            (TimelineStates.Executing, _) => $"The agent is working on the {what}.",
            (TimelineStates.Completed, _) => $"The {what} is done.",
            (TimelineStates.Failed, _) => $"The {what} did not complete.",
            _ => $"The {what} was halted.",
        };
    }

    public static string Humanize(string token) =>
        CultureInfo.InvariantCulture.TextInfo.ToLower(token.Replace('_', ' '));
}
