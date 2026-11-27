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
    string ReasonText,
    bool CanUnblock,
    int AttemptNumber,
    DateTimeOffset BlockedSince,
    double AgeMinutes
);

/// <summary>An operator's resolution of a blocked message, as the audit trail shows it. No recipient, no payload.</summary>
public sealed record BlockedMessageHistoryView(
    Guid ResolutionId,
    Guid OutboxId,
    string Action,
    string Reason,
    string ResolvedBy,
    DateTimeOffset ResolvedAt
);

/// <summary>Plain-language reasons for the codes a blocked message can carry, so nobody has to read the database.</summary>
public static class BlockedReasonText
{
    public const int AttemptLimit = 12;

    public static string Describe(string? code) =>
        code switch
        {
            null or "" => "No reason was recorded.",
            "PROVIDER_REJECTED" => "WhatsApp refused the message.",
            "ATTEMPT_LIMIT_REACHED" => "Sending failed 12 times, so it stopped trying.",
            "CURRENT_ELIGIBILITY_DENIED" =>
                "The customer is no longer allowed to receive this message.",
            "RELATIONSHIP_ROUTE_RETIRED" =>
                "The agent relationship this message belonged to has ended.",
            "DISPATCH_AUTHORITY_DENIED" => "The platform was not allowed to send it just now.",
            _ => $"The sender stopped it ({code}).",
        };

    /// <summary>Unblocking puts the same message back on the queue; it is pointless for a relationship that has ended or after the attempt limit.</summary>
    public static bool CanUnblock(string? code, int attemptNumber) =>
        code is not "RELATIONSHIP_ROUTE_RETIRED" && attemptNumber < AttemptLimit;
}

public sealed record BlockedMessageResolutionView(
    Guid ResolutionId,
    Guid OutboxId,
    string Action,
    bool Replayed
);

public sealed record ServiceReadinessView(string Name, string State);

public sealed record DeliveryOutcomeCount(string Channel, string Outcome, int Count);

/// <summary>
/// The Founder-approved WhatsApp limits for the running activation and what has been reserved against them so far.
/// Registration codes and guest messages share one window, one message count, one rate and one spend ceiling.
/// </summary>
public sealed record WhatsAppLimitsView(
    DateTimeOffset WindowStartsAt,
    DateTimeOffset WindowExpiresAt,
    int MaximumMessages,
    int MaximumMessagesPerMinute,
    decimal MaximumSpendInr,
    decimal MaximumCostPerMessageInr,
    bool GuestAdmission,
    bool RegistrationCodes,
    int? MessagesReserved,
    decimal? SpendReservedInr
);

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
    DateTimeOffset ObservedAt,
    WhatsAppLimitsView? Limits = null
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
    IOptions<Wc120ConversationOptions> options,
    IOptionsMonitor<WhatsAppCapabilityOptions>? capability = null,
    IOptions<WhatsAppAuthenticationTemplateOptions>? verification = null
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
        var authority = capability?.CurrentValue.Authority;
        int? reserved = null;
        decimal? reservedSpend = null;
        try
        {
            using var scope = tenantExecution.Begin();
            using var tenantOverride = tenantExecution.BeginDatabaseTenantOverride(
                tenantExecution.ServiceTenantId!.Value
            );
            snapshot = await operations.EvaluateAsync(now, cancellationToken);
            if (authority is not null && authority.ActivationReference.Length > 0)
            {
                // The same digest the traffic budget writes, so the count is exactly what the limits are checked against.
                var activationDigest = Convert.ToHexStringLower(
                    System.Security.Cryptography.SHA256.HashData(
                        System.Text.Encoding.UTF8.GetBytes(authority.ActivationReference)
                    )
                );
                await using var conversationDb = await conversationFactory.CreateDbContextAsync(
                    cancellationToken
                );
                var used = await conversationDb
                    .Set<WhatsAppTrafficReservation>()
                    .AsNoTracking()
                    .Where(value =>
                        value.TenantId == authority.TenantId
                        && value.ActivationDigest == activationDigest
                    )
                    .Select(value => value.ReservedCostInr)
                    .ToListAsync(cancellationToken);
                reserved = used.Count;
                reservedSpend = used.Sum();
            }
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
            now,
            authority is null || authority.MaximumMessages <= 0
                ? null
                : new WhatsAppLimitsView(
                    authority.StartsAt,
                    authority.ExpiresAt,
                    authority.MaximumMessages,
                    authority.MaximumMessagesPerMinute,
                    authority.MaximumSpendInr,
                    authority.MaximumCostPerMessageInr,
                    authority.AllowPublicAdmission,
                    authority.AllowRegistrationVerification && verification?.Value.Enabled == true,
                    reserved,
                    reservedSpend
                )
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
                BlockedReasonText.Describe(value.BlockedReason),
                BlockedReasonText.CanUnblock(value.BlockedReason, value.AttemptNumber),
                value.AttemptNumber,
                value.UpdatedAt,
                Math.Round((now - value.UpdatedAt).TotalMinutes, 1)
            ))
            .ToArray();
    }

    public async Task<IReadOnlyList<BlockedMessageHistoryView>> ListResolutionsAsync(
        int limit,
        CancellationToken cancellationToken
    )
    {
        using var scope = tenantExecution.Begin();
        using var tenantOverride = tenantExecution.BeginDatabaseTenantOverride(
            tenantExecution.ServiceTenantId!.Value
        );
        await using var db = await conversationFactory.CreateDbContextAsync(cancellationToken);
        var environment = options.Value.Environment;
        return (
            await db
                .OutboxResolutions.AsNoTracking()
                .Where(value => value.Environment == environment)
                .OrderByDescending(value => value.ResolvedAt)
                .Take(Math.Clamp(limit, 1, 100))
                .ToListAsync(cancellationToken)
        )
            .Select(value => new BlockedMessageHistoryView(
                value.ResolutionId,
                value.OutboxId,
                value.Action,
                value.Reason,
                value.ResolvedBy,
                value.ResolvedAt
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
        if (
            action == BlockedMessageActions.Retry
            && !BlockedReasonText.CanUnblock(row.BlockedReason, row.AttemptNumber)
        )
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

public sealed record PageGroup(
    string Signal,
    string Outcome,
    string? Reason,
    int Count,
    DateTimeOffset FirstRecordedAt,
    DateTimeOffset LastRecordedAt
);

/// <summary>
/// Records what became of a page (WC171-R008, O4). A page handed to the log pipeline is EMITTED: that proves the platform
/// raised it, not that a person received it. An acknowledgement stops the repeat paging, never the signal itself.
/// A standing alert is recorded once per <see cref="RepeatInterval"/>, not once per 30-second check, so the Pages list
/// stays readable; the alert itself keeps showing in the log pipeline every check.
/// </summary>
public sealed class OperatorPageService(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    TimeProvider clock
)
{
    public static readonly TimeSpan AcknowledgementWindow = TimeSpan.FromMinutes(30);
    public static readonly TimeSpan RepeatInterval = TimeSpan.FromMinutes(60);
    public static readonly TimeSpan GroupingHorizon = TimeSpan.FromDays(7);

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

    /// <summary>
    /// Records one page for a signal; when it is acknowledged the page is suppressed and the reason says so. A page of the
    /// same outcome already recorded inside <see cref="RepeatInterval"/> is not written again.
    /// </summary>
    public async Task<string> RecordAsync(
        string code,
        bool acknowledged,
        CancellationToken cancellationToken
    )
    {
        var outcome = acknowledged ? "SUPPRESSED" : "EMITTED";
        var now = clock.GetUtcNow();
        var since = now - RepeatInterval;
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var alreadyRecorded = await db
            .AlertDeliveries.AsNoTracking()
            .AnyAsync(
                value =>
                    value.Signal == code
                    && value.Channel == AlertChannels.OperatorPage
                    && value.Outcome == outcome
                    && value.RecordedAt >= since,
                cancellationToken
            );
        if (alreadyRecorded)
            return outcome;
        db.AlertDeliveries.Add(
            new AlertDelivery
            {
                Signal = code,
                AlertClass = AlertClasses.Operations,
                Channel = AlertChannels.OperatorPage,
                Outcome = outcome,
                Reason = acknowledged ? "ESCALATION_ACKNOWLEDGED" : "HANDED_TO_MONITORING",
                RecordedAt = now,
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

    /// <summary>Pages grouped by signal, outcome and reason over the last week, newest group first: a flood collapses into one line with a count.</summary>
    public async Task<IReadOnlyList<PageGroup>> RecentGroupedAsync(
        int limit,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var since = clock.GetUtcNow() - GroupingHorizon;
        var groups = await db
            .AlertDeliveries.AsNoTracking()
            .Where(value =>
                value.Channel == AlertChannels.OperatorPage && value.RecordedAt >= since
            )
            .GroupBy(value => new
            {
                value.Signal,
                value.Outcome,
                value.Reason,
            })
            .Select(group => new
            {
                group.Key.Signal,
                group.Key.Outcome,
                group.Key.Reason,
                Count = group.Count(),
                First = group.Min(value => value.RecordedAt),
                Last = group.Max(value => value.RecordedAt),
            })
            .OrderByDescending(value => value.Last)
            .Take(limit)
            .ToListAsync(cancellationToken);
        return groups
            .Select(value => new PageGroup(
                value.Signal,
                value.Outcome,
                value.Reason,
                value.Count,
                value.First,
                value.Last
            ))
            .ToArray();
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
