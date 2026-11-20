// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-06
// Constitutional basis: C-023, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services.Spend;

public sealed record EnvironmentSpendLease(
    Guid LeaseId,
    string Environment,
    long GrantedPaise,
    DateTimeOffset ExpiresAt
);

public interface IEnvironmentSpendLeaseStore
{
    Task<EnvironmentSpendLease?> GrantAsync(
        string environment,
        string holder,
        long leaseSizePaise,
        long maximumPaise,
        TimeSpan duration,
        DateTimeOffset now,
        CancellationToken ct
    );

    Task CloseAsync(Guid leaseId, CancellationToken ct);
}

/// <summary>Grants are serialized by the environment advisory lock; draws never take it.</summary>
public sealed class PostgresEnvironmentSpendLeaseStore(
    IDbContextFactory<ConversationStoreDbContext> conversations
) : IEnvironmentSpendLeaseStore
{
    public async Task<EnvironmentSpendLease?> GrantAsync(
        string environment,
        string holder,
        long leaseSizePaise,
        long maximumPaise,
        TimeSpan duration,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_advisory_xact_lock(hashtextextended({"environment-spend:" + environment},0))",
            ct
        );
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.environment_spend_leases AS lease
            SET state='EXPIRED',
                consumed_paise=COALESCE((
                    SELECT sum(attempt.reserved_paise)
                    FROM business.environment_spend_attempts attempt
                    WHERE attempt.lease_id=lease.lease_id),0)::BIGINT
            WHERE lease.environment={environment} AND lease.state='ACTIVE'
                AND lease.expires_at <= {now}
            """,
            ct
        );
        var exposure = await ConversationEnvironmentSpendOwner.ExposureAsync(
            db,
            environment,
            now,
            ct
        );
        var granted = Math.Min(leaseSizePaise, maximumPaise - exposure);
        if (granted <= 0)
        {
            await transaction.CommitAsync(ct);
            return null;
        }
        var leaseId = Guid.NewGuid();
        var expiresAt = now.Add(duration);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.environment_spend_leases
                (lease_id,environment,holder,granted_paise,consumed_paise,state,granted_at,expires_at)
            VALUES ({leaseId},{environment},{holder},{granted},0,'ACTIVE',{now},{expiresAt})
            """,
            ct
        );
        await transaction.CommitAsync(ct);
        return new(leaseId, environment, granted, expiresAt);
    }

    public async Task CloseAsync(Guid leaseId, CancellationToken ct)
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.environment_spend_leases AS lease
            SET state='RETURNED',
                consumed_paise=COALESCE((
                    SELECT sum(attempt.reserved_paise)
                    FROM business.environment_spend_attempts attempt
                    WHERE attempt.lease_id=lease.lease_id),0)::BIGINT
            WHERE lease.lease_id={leaseId} AND lease.state='ACTIVE'
            """,
            ct
        );
    }
}
