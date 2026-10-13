// Implements: work-contracts/WC-120-requirements.yaml WC120-R017 and WC120-R041
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record ConversationOperationalAlert(
    string Code,
    string Severity,
    DateTimeOffset TriggeredAt,
    TimeSpan ResponseDeadline
);

public sealed record ConversationOperationalSnapshot(
    string Environment,
    int OpenSignalCount,
    int BlockedOutboxCount,
    int UnresolvedOutboxCount,
    TimeSpan? OldestQueuedAge,
    TimeSpan? OldestUnknownAge,
    TimeSpan? OldestDeadLetterAge,
    IReadOnlyList<ConversationOperationalAlert> Alerts
);

public sealed class ConversationOperationsService(
    IDbContextFactory<ConversationStoreDbContext> dbFactory,
    IOptions<Wc120ConversationOptions> options
)
{
    public async Task<ConversationOperationalSnapshot> EvaluateAsync(
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var environment = options.Value.Environment;
        var queue = db
            .ConversationOutbox.AsNoTracking()
            .Where(value => value.Environment == environment);
        var oldestQueuedAt = await queue
            .Where(value => value.State == "PENDING" || value.State == "LEASED")
            .MinAsync(value => (DateTimeOffset?)value.CreatedAt, cancellationToken);
        var oldestUnknownAt = await queue
            .Where(value => value.State == "UNRESOLVED")
            .MinAsync(value => (DateTimeOffset?)value.UpdatedAt, cancellationToken);
        var oldestBlockedAt = await queue
            .Where(value => value.State == "BLOCKED")
            .MinAsync(value => (DateTimeOffset?)value.UpdatedAt, cancellationToken);
        var blockedCount = await queue.CountAsync(
            value => value.State == "BLOCKED",
            cancellationToken
        );
        var unresolvedCount = await queue.CountAsync(
            value => value.State == "UNRESOLVED",
            cancellationToken
        );
        var openSignals = await db
            .OperationalSignals.AsNoTracking()
            .CountAsync(
                value => value.Environment == environment && value.State == "OPEN",
                cancellationToken
            );
        var oldestQueuedAge = Age(now, oldestQueuedAt);
        var oldestUnknownAge = Age(now, oldestUnknownAt);
        var oldestDeadLetterAge = Age(now, oldestBlockedAt);
        var alerts = new List<ConversationOperationalAlert>();
        if (oldestQueuedAge > TimeSpan.FromSeconds(120))
        {
            alerts.Add(new("OUTBOUND_QUEUE_AGE_BREACH", "PAGE", now, TimeSpan.FromMinutes(5)));
        }
        if (oldestUnknownAge > TimeSpan.FromMinutes(15))
        {
            alerts.Add(new("OUTBOUND_RECONCILIATION_BREACH", "PAGE", now, TimeSpan.FromMinutes(5)));
        }
        if (oldestDeadLetterAge > TimeSpan.FromMinutes(30))
        {
            alerts.Add(new("DEAD_LETTER_AGE_BREACH", "PAGE", now, TimeSpan.FromMinutes(5)));
        }
        else if (oldestDeadLetterAge > TimeSpan.FromMinutes(15))
        {
            alerts.Add(new("DEAD_LETTER_ACTION_REQUIRED", "NOTIFY", now, TimeSpan.FromMinutes(5)));
        }
        if (
            await db
                .OperationalSignals.AsNoTracking()
                .AnyAsync(
                    value =>
                        value.Environment == environment
                        && value.State == "OPEN"
                        && (
                            value.Code.Contains("PRIVACY")
                            || value.Code.Contains("ISOLATION")
                            || value.Code.Contains("PRODUCTION_DARK")
                            || value.Code.Contains("STOP_HARD_CEILING")
                        ),
                    cancellationToken
                )
        )
        {
            alerts.Add(new("IMMEDIATE_FENCE_REQUIRED", "PAGE", now, TimeSpan.FromMinutes(5)));
        }
        return new(
            environment,
            openSignals,
            blockedCount,
            unresolvedCount,
            oldestQueuedAge,
            oldestUnknownAge,
            oldestDeadLetterAge,
            alerts
        );
    }

    private static TimeSpan? Age(DateTimeOffset now, DateTimeOffset? occurredAt) =>
        occurredAt.HasValue ? now - occurredAt.Value : null;
}
