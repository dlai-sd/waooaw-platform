// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-02
// Constitutional basis: C-023, C-059, C-063, ADR-051

using System.Collections.Concurrent;
using Waooaw.BusinessPlatform.Services.Workbench;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

/// <summary>Mirrors the claim, replay, conflict and lease rules of the Postgres ledger.</summary>
internal sealed class InMemoryWorkbenchLedgerStore : IWorkbenchLedgerStore
{
    private readonly object _gate = new();
    private readonly Dictionary<
        (Guid Tenant, Guid Relationship, Guid Participant, Guid Key),
        Entry
    > _entries = [];

    public int Count
    {
        get
        {
            lock (_gate)
                return _entries.Count;
        }
    }

    public Task<WorkbenchLedgerClaim> ClaimAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        string digest,
        DateTimeOffset now,
        DateTimeOffset leaseUntil,
        CancellationToken ct
    )
    {
        lock (_gate)
        {
            var key = KeyOf(context, idempotencyKey);
            if (!_entries.TryGetValue(key, out var entry))
            {
                _entries[key] = new Entry(digest, null, leaseUntil);
                return Task.FromResult(new WorkbenchLedgerClaim(WorkbenchLedgerClaimKind.Claimed));
            }
            if (entry.Digest != digest)
                return Task.FromResult(new WorkbenchLedgerClaim(WorkbenchLedgerClaimKind.Conflict));
            if (entry.ResultJson is not null)
                return Task.FromResult(
                    new WorkbenchLedgerClaim(WorkbenchLedgerClaimKind.Replay, entry.ResultJson)
                );
            if (entry.LeaseUntil > now)
                return Task.FromResult(
                    new WorkbenchLedgerClaim(WorkbenchLedgerClaimKind.InProgress)
                );
            _entries[key] = entry with { LeaseUntil = leaseUntil };
            return Task.FromResult(new WorkbenchLedgerClaim(WorkbenchLedgerClaimKind.Claimed));
        }
    }

    public Task CompleteAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        string resultJson,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        lock (_gate)
        {
            var key = KeyOf(context, idempotencyKey);
            _entries[key] = _entries[key] with { ResultJson = resultJson };
        }
        return Task.CompletedTask;
    }

    public Task AbandonAsync(WorkbenchContext context, Guid idempotencyKey, CancellationToken ct)
    {
        lock (_gate)
        {
            var key = KeyOf(context, idempotencyKey);
            if (_entries.TryGetValue(key, out var entry) && entry.ResultJson is null)
                _entries.Remove(key);
        }
        return Task.CompletedTask;
    }

    private static (Guid, Guid, Guid, Guid) KeyOf(WorkbenchContext context, Guid key) =>
        (context.TenantId, context.RelationshipId, context.ParticipantId, key);

    private sealed record Entry(string Digest, string? ResultJson, DateTimeOffset LeaseUntil);
}

internal sealed class InMemoryWorkbenchHandoffStore : IWorkbenchHandoffStore
{
    private readonly object _gate = new();
    private readonly Dictionary<string, (WorkbenchHandoffRecord Record, bool Used)> _records = [];

    public int Count
    {
        get
        {
            lock (_gate)
                return _records.Count;
        }
    }

    public bool Contains(string tokenHash)
    {
        lock (_gate)
            return _records.ContainsKey(tokenHash);
    }

    public Task InsertAsync(WorkbenchHandoffRecord record, CancellationToken ct)
    {
        lock (_gate)
            _records[record.TokenHash] = (record, false);
        return Task.CompletedTask;
    }

    public Task<WorkbenchHandoffRedemption?> ConsumeAsync(
        string tokenHash,
        Guid tenantId,
        Guid relationshipId,
        Guid participantId,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        lock (_gate)
        {
            if (
                !_records.TryGetValue(tokenHash, out var entry)
                || entry.Used
                || entry.Record.ExpiresAt <= now
                || entry.Record.TenantId != tenantId
                || entry.Record.RelationshipId != relationshipId
                || entry.Record.ParticipantId != participantId
            )
                return Task.FromResult<WorkbenchHandoffRedemption?>(null);
            _records[tokenHash] = (entry.Record, true);
            return Task.FromResult<WorkbenchHandoffRedemption?>(
                new WorkbenchHandoffRedemption(entry.Record.Purpose, entry.Record.ContextRef)
            );
        }
    }
}

internal sealed class InMemoryWorkbenchGoalHistoryStore : IWorkbenchGoalHistoryStore
{
    private readonly ConcurrentDictionary<
        (Guid Tenant, Guid Relationship, Guid Goal),
        List<WorkbenchGoalVersionEntry>
    > _history = new();

    public Task AppendAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid goalId,
        WorkbenchGoalVersionEntry entry,
        CancellationToken ct
    )
    {
        var list = _history.GetOrAdd((tenantId, relationshipId, goalId), _ => []);
        lock (list)
            list.Add(entry with { VersionNo = list.Count + 1 });
        return Task.CompletedTask;
    }

    public Task<IReadOnlyList<WorkbenchGoalVersionEntry>> ListAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid goalId,
        CancellationToken ct
    )
    {
        if (!_history.TryGetValue((tenantId, relationshipId, goalId), out var list))
            return Task.FromResult<IReadOnlyList<WorkbenchGoalVersionEntry>>([]);
        lock (list)
            return Task.FromResult<IReadOnlyList<WorkbenchGoalVersionEntry>>(list.ToArray());
    }

    public Task<IReadOnlyDictionary<Guid, int>> LatestVersionsAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken ct
    ) =>
        Task.FromResult<IReadOnlyDictionary<Guid, int>>(
            _history
                .Where(item =>
                    item.Key.Tenant == tenantId && item.Key.Relationship == relationshipId
                )
                .ToDictionary(item => item.Key.Goal, item => item.Value.Count)
        );
}
