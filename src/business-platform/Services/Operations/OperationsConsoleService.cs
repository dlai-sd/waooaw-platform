// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R008, WC171-R009, WC171-R010
// Constitutional basis: C-001, C-005, C-007, C-023, C-049, C-059, C-063
// IB: IB-171

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.Alerts;

namespace Waooaw.BusinessPlatform.Services.Operations;

public static class BlockedMessageActions
{
    public const string Retry = "RETRY";
    public const string CloseWithReason = "CLOSE_WITH_REASON";
    public const string MarkUndeliverable = "MARK_UNDELIVERABLE";

    public static readonly IReadOnlySet<string> All = new HashSet<string>(StringComparer.Ordinal)
    {
        Retry,
        CloseWithReason,
        MarkUndeliverable,
    };
}

/// <summary>A blocked outbound message with what an operator needs and nothing more: no recipient, no payload.</summary>
public sealed record BlockedMessageView(
    Guid OutboxId,
    Guid RelationshipId,
    string Purpose,
    string? TemplateCategory,
    string? BlockedReason,
    int AttemptNumber,
    DateTimeOffset BlockedSince,
    double AgeMinutes
);

public sealed record BlockedMessageResolutionView(
    Guid ResolutionId,
    Guid OutboxId,
    string Action,
    bool Replayed
);

public sealed record ServiceReadinessView(string Name, string State);

public sealed record DeliveryOutcomeCount(string Channel, string Outcome, int Count);

public sealed record OperationsOverview(
    string Environment,
    string WhatsApp,
    string? WhatsAppReason,
    int OpenSignals,
    int BlockedMessages,
    int UnresolvedMessages,
    double? OldestQueuedMinutes,
    double? OldestBlockedMinutes,
    IReadOnlyList<DeliveryOutcomeCount> Deliveries,
    IReadOnlyList<ServiceReadinessView> Services,
    DateTimeOffset ObservedAt
);

public sealed class BlockedMessageStateException : Exception;

public sealed class BlockedMessageConflictException : Exception;

/// <summary>
/// The Founder's and administrators' view of what needs attention, and the Founder's governed way to resolve a blocked
/// outbound message (WC171-R008, R009). Reads are minimized; a resolution is idempotent, audited by its own append-only
/// row, and never deletes or rewrites the blocked message.
/// </summary>
public sealed class OperationsConsoleService(
    IDbContextFactory<ConversationStoreDbContext> conversationFactory,
    IDbContextFactory<EmploymentRelationshipDbContext> relationshipFactory,
    ConversationOperationsService operations,
    WhatsAppTenantExecutionScope tenantExecution,
    HealthCheckService health,
    IOptions<Wc120ConversationOptions> options
)
{
    public async Task<OperationsOverview> OverviewAsync(
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        var environment = options.Value.Environment;
        var whatsapp = "ACTIVE";
        string? reason = null;
        ConversationOperationalSnapshot? snapshot = null;
        try
        {
            using var scope = tenantExecution.Begin();
            using var tenantOverride = tenantExecution.BeginDatabaseTenantOverride(
                tenantExecution.ServiceTenantId!.Value
            );
            snapshot = await operations.EvaluateAsync(now, cancellationToken);
        }
        catch (WhatsAppCapabilityUnavailableException unavailable)
        {
            whatsapp = "INACTIVE";
            reason = unavailable.ReasonCode;
        }
        await using var db = await relationshipFactory.CreateDbContextAsync(cancellationToken);
        var since = now.AddHours(-24);
        var deliveries = (
            await db
                .AlertDeliveries.AsNoTracking()
                .Where(value => value.RecordedAt >= since)
                .GroupBy(value => new { value.Channel, value.Outcome })
                .Select(group => new
                {
                    group.Key.Channel,
                    group.Key.Outcome,
                    Count = group.Count(),
                })
                .ToListAsync(cancellationToken)
        ).Select(value => new DeliveryOutcomeCount(value.Channel, value.Outcome, value.Count)).OrderBy(value => value.Channel).ThenBy(value => value.Outcome).ToArray();
        var report = await health.CheckHealthAsync(cancellationToken);
        var services = report
            .Entries.Select(entry => new ServiceReadinessView(
                entry.Key,
                entry.Value.Status.ToString().ToUpperInvariant()
            ))
            .OrderBy(value => value.Name)
            .ToArray();
        return new OperationsOverview(
            environment,
            whatsapp,
            reason,
            snapshot?.OpenSignalCount ?? 0,
            snapshot?.BlockedOutboxCount ?? 0,
            snapshot?.UnresolvedOutboxCount ?? 0,
            snapshot?.OldestQueuedAge?.TotalMinutes,
            snapshot?.OldestDeadLetterAge?.TotalMinutes,
            deliveries,
            services,
            now
        );
    }

    public async Task<IReadOnlyList<BlockedMessageView>> ListBlockedAsync(
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        using var scope = tenantExecution.Begin();
        using var tenantOverride = tenantExecution.BeginDatabaseTenantOverride(
            tenantExecution.ServiceTenantId!.Value
        );
        await using var db = await conversationFactory.CreateDbContextAsync(cancellationToken);
        var environment = options.Value.Environment;
        var rows = await db
            .ConversationOutbox.AsNoTracking()
            .Where(value => value.Environment == environment && value.State == "BLOCKED")
            .Where(value =>
                !db.OutboxResolutions.Any(resolution =>
                    resolution.OutboxId == value.OutboxId
                    && (
                        resolution.Action == BlockedMessageActions.CloseWithReason
                        || resolution.Action == BlockedMessageActions.MarkUndeliverable
                    )
                )
            )
            .OrderBy(value => value.UpdatedAt)
            .Take(100)
            .ToListAsync(cancellationToken);
        return rows.Select(value => new BlockedMessageView(
                value.OutboxId,
                value.RelationshipId ?? Guid.Empty,
                value.Purpose,
                value.TemplateCategory,
                value.BlockedReason,
                value.AttemptNumber,
                value.UpdatedAt,
                Math.Round((now - value.UpdatedAt).TotalMinutes, 1)
            ))
            .ToArray();
    }

    public async Task<BlockedMessageResolutionView> ResolveBlockedAsync(
        Guid outboxId,
        string action,
        string reason,
        string resolvedBy,
        Guid idempotencyKey,
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        if (!BlockedMessageActions.All.Contains(action) || reason.Trim().Length is < 5 or > 240)
            throw new ArgumentException("Action or reason is not valid.");
        using var scope = tenantExecution.Begin();
        using var tenantOverride = tenantExecution.BeginDatabaseTenantOverride(
            tenantExecution.ServiceTenantId!.Value
        );
        await using var db = await conversationFactory.CreateDbContextAsync(cancellationToken);
        var prior = await db
            .OutboxResolutions.AsNoTracking()
            .SingleOrDefaultAsync(
                value => value.IdempotencyKey == idempotencyKey,
                cancellationToken
            );
        if (prior is not null)
            return prior.OutboxId == outboxId && prior.Action == action
                ? new BlockedMessageResolutionView(
                    prior.ResolutionId,
                    prior.OutboxId,
                    prior.Action,
                    true
                )
                : throw new BlockedMessageConflictException();
        var environment = options.Value.Environment;
        var row =
            await db.ConversationOutbox.SingleOrDefaultAsync(
                value => value.OutboxId == outboxId && value.Environment == environment,
                cancellationToken
            ) ?? throw new KeyNotFoundException("Message not found.");
        if (row.State != "BLOCKED")
            throw new BlockedMessageStateException();
        if (action == BlockedMessageActions.Retry && row.AttemptNumber >= 12)
            throw new BlockedMessageStateException();
        var resolution = new ConversationOutboxResolution
        {
            OutboxId = row.OutboxId,
            TenantId = row.TenantId,
            Environment = environment,
            Action = action,
            Reason = reason.Trim(),
            ResolvedBy = resolvedBy.Length > 128 ? resolvedBy[..128] : resolvedBy,
            IdempotencyKey = idempotencyKey,
            ResolvedAt = now,
        };
        db.OutboxResolutions.Add(resolution);
        if (action == BlockedMessageActions.Retry)
        {
            // The same message goes back on the queue; the provider's answer decides what happens next.
            row.State = "PENDING";
            row.BlockedReason = null;
            row.NextAttemptAt = now;
            row.UpdatedAt = now;
        }
        await db.SaveChangesAsync(cancellationToken);
        return new BlockedMessageResolutionView(
            resolution.ResolutionId,
            row.OutboxId,
            action,
            false
        );
    }
}

/// <summary>
/// Records what became of a page (WC171-R008, O4). A page handed to the log pipeline is EMITTED: that proves the platform
/// raised it, not that a person received it. An acknowledgement stops the repeat paging, never the signal itself.
/// </summary>
public sealed class OperatorPageService(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    TimeProvider clock
)
{
    public static readonly TimeSpan AcknowledgementWindow = TimeSpan.FromMinutes(30);

    public async Task<bool> IsAcknowledgedAsync(string code, CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var since = clock.GetUtcNow() - AcknowledgementWindow;
        return await db
            .AlertDeliveries.AsNoTracking()
            .AnyAsync(
                value =>
                    value.Signal == code
                    && value.Channel == AlertChannels.OperatorPage
                    && value.Outcome == "ACKNOWLEDGED"
                    && value.RecordedAt >= since,
                cancellationToken
            );
    }

    /// <summary>Records one page for a signal; when it is acknowledged the page is suppressed and the reason says so.</summary>
    public async Task<string> RecordAsync(
        string code,
        bool acknowledged,
        CancellationToken cancellationToken
    )
    {
        var outcome = acknowledged ? "SUPPRESSED" : "EMITTED";
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        db.AlertDeliveries.Add(
            new AlertDelivery
            {
                Signal = code,
                AlertClass = AlertClasses.Operations,
                Channel = AlertChannels.OperatorPage,
                Outcome = outcome,
                Reason = acknowledged ? "ESCALATION_ACKNOWLEDGED" : "HANDED_TO_MONITORING",
                RecordedAt = clock.GetUtcNow(),
            }
        );
        await db.SaveChangesAsync(cancellationToken);
        return outcome;
    }

    public async Task AcknowledgeAsync(
        string code,
        string actor,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        db.AlertDeliveries.Add(
            new AlertDelivery
            {
                Signal = code,
                AlertClass = AlertClasses.Operations,
                Channel = AlertChannels.OperatorPage,
                Outcome = "ACKNOWLEDGED",
                Reason = actor.Length > 120 ? actor[..120] : actor,
                RecordedAt = clock.GetUtcNow(),
            }
        );
        await db.SaveChangesAsync(cancellationToken);
    }

    public async Task<IReadOnlyList<AlertDelivery>> RecentAsync(
        int limit,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        return await db
            .AlertDeliveries.AsNoTracking()
            .Where(value => value.Channel == AlertChannels.OperatorPage)
            .OrderByDescending(value => value.RecordedAt)
            .Take(limit)
            .ToListAsync(cancellationToken);
    }
}

public sealed record SpendChainView(
    IReadOnlyList<object> Authorizations,
    IReadOnlyList<object> Items,
    IReadOnlyList<object> Reconciliations
);

public sealed class SpendChainUnavailableException : Exception;

/// <summary>The spend chain and its discrepancies live in the billing engine; BP reads them over a signed route that needs a route grant.</summary>
public interface ISpendChainReader
{
    Task<SpendChainView> ReadAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken
    );

    Task<bool> ResolveDiscrepancyAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid resultId,
        Guid evidenceId,
        CancellationToken cancellationToken
    );
}

/// <summary>Honest default: until the route grant exists the console says the spend chain cannot be read, it never invents it.</summary>
public sealed class UnavailableSpendChainReader : ISpendChainReader
{
    public Task<SpendChainView> ReadAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken
    ) => throw new SpendChainUnavailableException();

    public Task<bool> ResolveDiscrepancyAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid resultId,
        Guid evidenceId,
        CancellationToken cancellationToken
    ) => throw new SpendChainUnavailableException();
}
