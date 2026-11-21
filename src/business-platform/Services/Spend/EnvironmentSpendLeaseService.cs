// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-06
// Constitutional basis: C-023, C-059, C-063

using System.Collections.Concurrent;

namespace Waooaw.BusinessPlatform.Services.Spend;

public sealed record EnvironmentSpendLeaseDraw(
    Guid LeaseId,
    long RemainingPaise,
    DateTimeOffset ExpiresAt
);

/// <summary>
/// Holds one budget lease per environment and draws per-call reservations from it in memory,
/// so the per-call path needs no environment-wide lock. Unused lease value returns on close or expiry.
/// </summary>
public sealed class EnvironmentSpendLeaseService(
    IEnvironmentSpendLeaseStore store,
    EnvironmentSpendOptions options
)
{
    private readonly string _holder = $"bp:{Guid.NewGuid():N}";
    private readonly ConcurrentDictionary<string, EnvironmentLease> _environments = new(
        StringComparer.Ordinal
    );

    public long LeaseSizePaise => options.LeaseSizePaise;

    public async Task<EnvironmentSpendLeaseDraw?> TryDrawAsync(
        string environment,
        long amountPaise,
        long maximumPaise,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        if (amountPaise <= 0 || amountPaise > LeaseSizePaise)
            throw new ArgumentOutOfRangeException(nameof(amountPaise));
        var held = _environments.GetOrAdd(environment, _ => new EnvironmentLease());
        await held.Mutex.WaitAsync(ct);
        try
        {
            if (held.Current is { } current)
            {
                if (current.ExpiresAt <= now)
                    held.Current = null;
                else if (current.RemainingPaise >= amountPaise)
                    return Draw(current, amountPaise);
                else
                {
                    held.Current = null;
                    await store.CloseAsync(current.LeaseId, ct);
                }
            }
            var granted = await store.GrantAsync(
                environment,
                _holder,
                LeaseSizePaise,
                maximumPaise,
                options.LeaseDuration,
                now,
                ct
            );
            if (granted is null)
                return null;
            if (granted.GrantedPaise < amountPaise)
            {
                await store.CloseAsync(granted.LeaseId, ct);
                return null;
            }
            held.Current = new HeldLease(granted.LeaseId, granted.GrantedPaise, granted.ExpiresAt);
            return Draw(held.Current, amountPaise);
        }
        finally
        {
            held.Mutex.Release();
        }
    }

    public async Task InvalidateAsync(string environment, Guid leaseId, CancellationToken ct)
    {
        if (!_environments.TryGetValue(environment, out var held))
            return;
        await held.Mutex.WaitAsync(ct);
        try
        {
            if (held.Current?.LeaseId == leaseId)
                held.Current = null;
        }
        finally
        {
            held.Mutex.Release();
        }
    }

    private static EnvironmentSpendLeaseDraw Draw(HeldLease lease, long amountPaise)
    {
        lease.RemainingPaise -= amountPaise;
        return new(lease.LeaseId, lease.RemainingPaise, lease.ExpiresAt);
    }

    private sealed class EnvironmentLease
    {
        public SemaphoreSlim Mutex { get; } = new(1, 1);
        public HeldLease? Current { get; set; }
    }

    private sealed class HeldLease(Guid leaseId, long remainingPaise, DateTimeOffset expiresAt)
    {
        public Guid LeaseId { get; } = leaseId;
        public long RemainingPaise { get; set; } = remainingPaise;
        public DateTimeOffset ExpiresAt { get; } = expiresAt;
    }
}
