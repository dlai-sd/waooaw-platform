// Implements: work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md WC134-R008
// Constitutional basis: C-023, C-026, C-059, C-063

using System.Data;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed class WhatsAppGuestTrafficEvent
{
    public Guid TenantId { get; init; }
    public string ActivationDigest { get; init; } = string.Empty;
    public string AuthorityDigest { get; init; } = string.Empty;
    public string EventId { get; init; } = string.Empty;
    public string BindingDigest { get; init; } = string.Empty;
    public string EventType { get; init; } = string.Empty;
    public string? InboundNotice { get; init; }
    public DateTimeOffset ReservedAt { get; init; }
}

public enum WhatsAppGuestTrafficNotice
{
    None,
    GuestMessageLimit,
    GlobalRateLimit,
    ActivationLimit,
    GuestSessionLimit,
}

public static class WhatsAppGuestTrafficEventIdentity
{
    public static string Inbound(string providerMessageId) => Create("inbound", providerMessageId);

    public static string Outbound(Guid outboxId) => Create("outbound", outboxId.ToString("D"));

    public static string Session(string bindingDigest, string businessDay) =>
        Create("session", $"{bindingDigest}:{businessDay}");

    public static string Activation(string activationReference) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(activationReference)));

    public static string LockKey(Guid tenantId) =>
        Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes($"guest-traffic:{tenantId:D}:daily"))
        );

    private static string Create(string purpose, string identity) =>
        Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes($"WC134:{purpose}:{identity}"))
        );
}

public sealed class WhatsAppGuestLimitOptions
{
    public const string SectionName = "WhatsAppGuestLimits";
    public const int DefaultMessagesPerGuestPer24Hours = 10;
    public const int DefaultNewSessionsPerDay = 100;

    // Inbound and outbound messages of one guest share this rolling 24-hour allowance.
    public int MessagesPerGuestPer24Hours { get; set; } = DefaultMessagesPerGuestPer24Hours;
    public int NewSessionsPerDay { get; set; } = DefaultNewSessionsPerDay;
}

public sealed class WhatsAppGuestTrafficBudget(
    IDbContextFactory<ConversationStoreDbContext> conversations,
    IWhatsAppCapabilityGate gate,
    TimeProvider clock,
    IOptions<WhatsAppGuestLimitOptions>? limits = null
)
{
    // The notice thresholds need three messages of headroom; the upper bound only rejects typos.
    private const int MinimumMessagesPerGuest = 3;
    private const int MaximumConfiguredLimit = 100_000;
    public const string MessageLimitNotice =
        "You have reached the free guest-message limit for this 24-hour period. Please message us again after the limit resets. Reply STOP to stop messages.";
    public const string GlobalRateLimitNotice =
        "WAOOAW Demo is temporarily at its message capacity. Please try again in a minute. Reply STOP to stop messages.";
    public const string ActivationLimitNotice =
        "WAOOAW Demo has reached its current message capacity. Please try again later. Reply STOP to stop messages.";
    public const string SessionLimitNotice =
        "WAOOAW Demo is at its daily guest-session limit. Please try again tomorrow. Reply STOP to stop messages.";
    public const string UnsupportedContentNotice =
        "WAOOAW Demo currently supports text messages only. Please send your question as text. Reply STOP to stop messages.";
    private static readonly TimeZoneInfo BusinessTimeZone = TimeZoneInfo.FindSystemTimeZoneById(
        "Asia/Kolkata"
    );

    private (int MessagesPerGuest, int SessionsPerDay) ConfiguredLimits()
    {
        var configured = limits?.Value ?? new WhatsAppGuestLimitOptions();
        if (
            configured.MessagesPerGuestPer24Hours
                is < MinimumMessagesPerGuest
                    or > MaximumConfiguredLimit
            || configured.NewSessionsPerDay is < 1 or > MaximumConfiguredLimit
        )
            throw new WhatsAppCapabilityUnavailableException("GUEST_LIMIT_CONFIGURATION_INVALID");
        // The approved activation totals are checked before these limits, so a setting can only
        // tighten what the Founder approved, never widen it.
        return (configured.MessagesPerGuestPer24Hours, configured.NewSessionsPerDay);
    }

    public Task<WhatsAppGuestTrafficNotice> ReserveInboundAsync(
        Guid tenantId,
        string bindingDigest,
        string providerMessageId,
        bool newSession,
        CancellationToken cancellationToken
    ) =>
        ReserveAsync(
            tenantId,
            bindingDigest,
            WhatsAppGuestTrafficEventIdentity.Inbound(providerMessageId),
            "INBOUND",
            newSession,
            cancellationToken
        );

    public async Task ReserveOutboundAsync(
        Guid tenantId,
        string bindingDigest,
        Guid outboxId,
        CancellationToken cancellationToken
    )
    {
        await ReserveAsync(
            tenantId,
            bindingDigest,
            WhatsAppGuestTrafficEventIdentity.Outbound(outboxId),
            "OUTBOUND",
            false,
            cancellationToken
        );
    }

    private async Task<WhatsAppGuestTrafficNotice> ReserveAsync(
        Guid tenantId,
        string bindingDigest,
        string eventId,
        string eventType,
        bool newSession,
        CancellationToken cancellationToken
    )
    {
        var now = clock.GetUtcNow();
        var authority = gate.RequireActive(now);
        var (messagesPerGuest, sessionsPerDay) = ConfiguredLimits();
        if (
            !authority.AllowProvisionalOnboarding
            || authority.TenantId != tenantId
            || !IsDigest(bindingDigest)
        )
            throw new WhatsAppCapabilityUnavailableException("GUEST_BUDGET_AUTHORITY_DENIED");

        var activationDigest = WhatsAppGuestTrafficEventIdentity.Activation(
            authority.ActivationReference
        );
        var authorityDigest = Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(authority)))
        );
        await using var db = await conversations.CreateDbContextAsync(cancellationToken);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.Serializable,
            cancellationToken
        );
        var lockKey = WhatsAppGuestTrafficEventIdentity.LockKey(tenantId);
        if (db.Database.IsRelational())
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT pg_advisory_xact_lock(hashtextextended({lockKey}, 0))",
                cancellationToken
            );

        var events = db.Set<WhatsAppGuestTrafficEvent>()
            .Where(value =>
                value.TenantId == tenantId && value.ActivationDigest == activationDigest
            );
        var allTenantEvents = db.Set<WhatsAppGuestTrafficEvent>()
            .Where(value => value.TenantId == tenantId);
        if (
            await events.AnyAsync(
                value => value.AuthorityDigest != authorityDigest,
                cancellationToken
            )
        )
            throw new WhatsAppCapabilityUnavailableException("ACTIVATION_RECORD_CHANGED");
        var existingEvent = await events.SingleOrDefaultAsync(
            value => value.EventId == eventId,
            cancellationToken
        );
        if (existingEvent is not null)
        {
            if (
                existingEvent.BindingDigest != bindingDigest
                || (
                    existingEvent.EventType != eventType
                    && !(eventType == "INBOUND" && existingEvent.EventType == "SESSION_LIMIT")
                )
            )
                throw new WhatsAppCapabilityUnavailableException("GUEST_BUDGET_EVENT_CONFLICT");
            var replayNotice =
                eventType == "INBOUND"
                    ? existingEvent.InboundNotice switch
                    {
                        null when existingEvent.EventType == "SESSION_LIMIT" =>
                            WhatsAppGuestTrafficNotice.GuestSessionLimit,
                        "NONE" => WhatsAppGuestTrafficNotice.None,
                        "GUEST_MESSAGE_LIMIT" => WhatsAppGuestTrafficNotice.GuestMessageLimit,
                        "GLOBAL_RATE_LIMIT" => WhatsAppGuestTrafficNotice.GlobalRateLimit,
                        "ACTIVATION_LIMIT" => WhatsAppGuestTrafficNotice.ActivationLimit,
                        "GUEST_SESSION_LIMIT" => WhatsAppGuestTrafficNotice.GuestSessionLimit,
                        _ => throw new WhatsAppCapabilityUnavailableException(
                            "GUEST_BUDGET_REPLAY_UNRESOLVED"
                        ),
                    }
                    : WhatsAppGuestTrafficNotice.None;
            await transaction.CommitAsync(cancellationToken);
            return replayNotice;
        }

        if (
            await db.Set<WhatsAppTrafficReservation>()
                .AnyAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.ActivationDigest == activationDigest
                        && value.AuthorityDigest != authorityDigest,
                    cancellationToken
                )
        )
            throw new WhatsAppCapabilityUnavailableException("ACTIVATION_RECORD_CHANGED");

        var cutoff = now.AddHours(-24);
        var minuteStartsAt = now.AddMinutes(-1);
        var activationCount = await WhatsAppTrafficBudget.CountActivationMessagesAsync(
            db,
            tenantId,
            activationDigest,
            cancellationToken
        );
        var tenantMinuteCount = await WhatsAppTrafficBudget.CountGlobalMessagesAsync(
            db,
            tenantId,
            minuteStartsAt,
            cancellationToken
        );
        if (
            tenantMinuteCount >= authority.MaximumMessagesPerMinute
            || eventType == "INBOUND" && tenantMinuteCount >= authority.MaximumMessagesPerMinute - 1
        )
            throw new WhatsAppCapabilityUnavailableException("GUEST_GLOBAL_RATE_LIMIT_REACHED");
        if (
            activationCount >= authority.MaximumMessages
            || eventType == "INBOUND" && activationCount >= authority.MaximumMessages - 1
        )
            throw new WhatsAppCapabilityUnavailableException("TRAFFIC_BUDGET_EXHAUSTED");

        var guestMessageCount = await allTenantEvents.CountAsync(
            value =>
                value.BindingDigest == bindingDigest
                && value.EventType != "SESSION"
                && value.ReservedAt > cutoff,
            cancellationToken
        );
        if (
            guestMessageCount >= messagesPerGuest
            || eventType == "INBOUND" && guestMessageCount >= messagesPerGuest - 1
        )
            throw new WhatsAppCapabilityUnavailableException("GUEST_MESSAGE_LIMIT_REACHED");
        var notice =
            eventType == "INBOUND" && guestMessageCount == messagesPerGuest - 2
                ? WhatsAppGuestTrafficNotice.GuestMessageLimit
            : eventType == "INBOUND" && tenantMinuteCount == authority.MaximumMessagesPerMinute - 2
                ? WhatsAppGuestTrafficNotice.GlobalRateLimit
            : eventType == "INBOUND" && activationCount == authority.MaximumMessages - 2
                ? WhatsAppGuestTrafficNotice.ActivationLimit
            : WhatsAppGuestTrafficNotice.None;

        var sessionLimitReached = false;
        if (newSession && authority.AllowPublicAdmission)
        {
            var localNow = TimeZoneInfo.ConvertTime(now, BusinessTimeZone);
            var localDayStart = new DateTimeOffset(
                localNow.Year,
                localNow.Month,
                localNow.Day,
                0,
                0,
                0,
                localNow.Offset
            );
            var dayStart = localDayStart.ToUniversalTime();
            var sessionEventId = WhatsAppGuestTrafficEventIdentity.Session(
                bindingDigest,
                localDayStart.ToString("yyyy-MM-dd")
            );
            if (
                !await allTenantEvents.AnyAsync(
                    value =>
                        value.EventType == "SESSION"
                        && value.BindingDigest == bindingDigest
                        && value.ReservedAt >= dayStart,
                    cancellationToken
                )
            )
            {
                var sessionCount = await allTenantEvents
                    .Where(value => value.EventType == "SESSION" && value.ReservedAt >= dayStart)
                    .Select(value => value.BindingDigest)
                    .Distinct()
                    .CountAsync(cancellationToken);
                if (sessionCount >= sessionsPerDay)
                    sessionLimitReached = true;
                else
                    db.Set<WhatsAppGuestTrafficEvent>()
                        .Add(
                            new()
                            {
                                TenantId = tenantId,
                                ActivationDigest = activationDigest,
                                AuthorityDigest = authorityDigest,
                                EventId = sessionEventId,
                                BindingDigest = bindingDigest,
                                EventType = "SESSION",
                                ReservedAt = now,
                            }
                        );
            }
        }

        db.Set<WhatsAppGuestTrafficEvent>()
            .Add(
                new()
                {
                    TenantId = tenantId,
                    ActivationDigest = activationDigest,
                    AuthorityDigest = authorityDigest,
                    EventId = eventId,
                    BindingDigest = bindingDigest,
                    EventType = sessionLimitReached ? "SESSION_LIMIT" : eventType,
                    InboundNotice =
                        eventType == "INBOUND"
                            ? sessionLimitReached
                                ? "GUEST_SESSION_LIMIT"
                                : notice switch
                                {
                                    WhatsAppGuestTrafficNotice.None => "NONE",
                                    WhatsAppGuestTrafficNotice.GuestMessageLimit =>
                                        "GUEST_MESSAGE_LIMIT",
                                    WhatsAppGuestTrafficNotice.GlobalRateLimit =>
                                        "GLOBAL_RATE_LIMIT",
                                    WhatsAppGuestTrafficNotice.ActivationLimit =>
                                        "ACTIVATION_LIMIT",
                                    _ => throw new InvalidOperationException(
                                        "Unsupported guest traffic notice."
                                    ),
                                }
                            : null,
                    ReservedAt = now,
                }
            );
        try
        {
            await db.SaveChangesAsync(cancellationToken);
            await transaction.CommitAsync(cancellationToken);
            return sessionLimitReached ? WhatsAppGuestTrafficNotice.GuestSessionLimit : notice;
        }
        catch (InvalidOperationException failure)
            when (failure.InnerException
                    is DbUpdateException
                    {
                        InnerException: Npgsql.PostgresException { SqlState: "40001" }
                    }
            )
        {
            throw new WhatsAppCapabilityUnavailableException("GUEST_BUDGET_CONCURRENT_CHANGE");
        }
        catch (DbUpdateException failure)
            when (failure.InnerException is Npgsql.PostgresException { SqlState: "40001" })
        {
            throw new WhatsAppCapabilityUnavailableException("GUEST_BUDGET_CONCURRENT_CHANGE");
        }
        catch (Npgsql.PostgresException failure) when (failure.SqlState == "40001")
        {
            throw new WhatsAppCapabilityUnavailableException("GUEST_BUDGET_CONCURRENT_CHANGE");
        }
    }

    private static bool IsDigest(string value) =>
        value.Length == 64
        && value.All(character => character is (>= '0' and <= '9') or (>= 'a' and <= 'f'));
}
