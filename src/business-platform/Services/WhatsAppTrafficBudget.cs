// Implements: work-contracts/WC-121-demo-whatsapp-provider-enablement-work-component.md S11-S13
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using System.Data;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public interface IWhatsAppRegistrationVerificationBudget
{
    Task<WhatsAppActivationAuthority> ReserveAsync(Guid challengeId, CancellationToken ct);
}

public sealed class WhatsAppTrafficBudget(
    IDbContextFactory<ConversationStoreDbContext> conversations,
    IWhatsAppCapabilityGate gate,
    TimeProvider clock,
    WhatsAppTenantExecutionScope? execution = null,
    ConversationEnvironmentSpendOwner? environmentSpend = null
) : IWhatsAppRegistrationVerificationBudget
{
    private readonly ConversationEnvironmentSpendOwner _environmentSpend =
        environmentSpend ?? new ConversationEnvironmentSpendOwner();

    public Task<WhatsAppGuestTrafficNotice> ReserveRelationshipInboundAsync(
        Guid tenantId,
        string recipientBindingDigest,
        string providerMessageId,
        CancellationToken ct
    ) =>
        ReserveRelationshipInboundCoreAsync(
            tenantId,
            recipientBindingDigest,
            providerMessageId,
            null,
            ct
        );

    internal async Task<WhatsAppGuestTrafficNotice> ReserveRelationshipInboundAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid bindingId,
        string recipientBindingDigest,
        string providerMessageId,
        CancellationToken ct
    )
    {
        var authority = gate.RequireActive(clock.GetUtcNow());
        if (tenantId == authority.TenantId)
            return await ReserveRelationshipInboundAsync(
                tenantId,
                recipientBindingDigest,
                providerMessageId,
                ct
            );
        var scope =
            execution
            ?? throw new WhatsAppCapabilityUnavailableException(
                "INBOUND_BUDGET_ROUTING_OWNER_UNAVAILABLE"
            );
        void RequireRoute()
        {
            if (scope.ServiceTenantId != authority.TenantId || scope.CurrentTenantId != tenantId)
                throw new WhatsAppCapabilityUnavailableException("INBOUND_BUDGET_AUTHORITY_DENIED");
            scope.RequireRelationshipRecipient(
                tenantId,
                relationshipId,
                bindingId,
                recipientBindingDigest
            );
        }
        RequireRoute();
        using var serviceBudget = scope.BeginDatabaseTenantOverride(authority.TenantId);
        return await ReserveRelationshipInboundCoreAsync(
            authority.TenantId,
            recipientBindingDigest,
            providerMessageId,
            RequireRoute,
            ct
        );
    }

    private async Task<WhatsAppGuestTrafficNotice> ReserveRelationshipInboundCoreAsync(
        Guid tenantId,
        string recipientBindingDigest,
        string providerMessageId,
        Action? requireRoute,
        CancellationToken ct
    )
    {
        requireRoute?.Invoke();
        var now = clock.GetUtcNow();
        gate.RequireRecipient(tenantId, recipientBindingDigest, now);
        var authority = gate.RequireActive(now);
        if (authority.TenantId != tenantId || string.IsNullOrWhiteSpace(providerMessageId))
            throw new WhatsAppCapabilityUnavailableException("INBOUND_BUDGET_AUTHORITY_DENIED");
        var activationDigest = WhatsAppGuestTrafficEventIdentity.Activation(
            authority.ActivationReference
        );
        var authorityDigest = Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(authority)))
        );
        var eventId = WhatsAppGuestTrafficEventIdentity.Inbound(providerMessageId);
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.Serializable,
            ct
        );
        var lockKey = WhatsAppGuestTrafficEventIdentity.LockKey(tenantId);
        if (db.Database.IsRelational())
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT pg_advisory_xact_lock(hashtextextended({lockKey}, 0))",
                ct
            );
        now = clock.GetUtcNow();
        if (gate.RequireActive(now) != authority)
            throw new WhatsAppCapabilityUnavailableException("ACTIVATION_RECORD_CHANGED");
        requireRoute?.Invoke();
        await EnsureGuestAuthorityAsync(db, tenantId, activationDigest, authorityDigest, ct);
        if (
            await db.Set<WhatsAppTrafficReservation>()
                .AnyAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.ActivationDigest == activationDigest
                        && value.AuthorityDigest != authorityDigest,
                    ct
                )
        )
            throw new WhatsAppCapabilityUnavailableException("ACTIVATION_RECORD_CHANGED");
        var existing = await db
            .WhatsAppGuestTrafficEvents.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.ActivationDigest == activationDigest
                    && value.EventId == eventId,
                ct
            );
        if (existing is not null)
        {
            requireRoute?.Invoke();
            if (existing.EventType != "INBOUND" || existing.BindingDigest != recipientBindingDigest)
                throw new WhatsAppCapabilityUnavailableException("INBOUND_BUDGET_EVENT_CONFLICT");
            return existing.InboundNotice switch
            {
                "NONE" => WhatsAppGuestTrafficNotice.None,
                "GLOBAL_RATE_LIMIT" => WhatsAppGuestTrafficNotice.GlobalRateLimit,
                "ACTIVATION_LIMIT" => WhatsAppGuestTrafficNotice.ActivationLimit,
                _ => throw new WhatsAppCapabilityUnavailableException(
                    "INBOUND_BUDGET_REPLAY_UNRESOLVED"
                ),
            };
        }
        var count = await CountActivationMessagesAsync(db, tenantId, activationDigest, ct);
        var minuteCount = await CountGlobalMessagesAsync(db, tenantId, now.AddMinutes(-1), ct);
        if (count >= authority.MaximumMessages || minuteCount >= authority.MaximumMessagesPerMinute)
            throw new WhatsAppCapabilityUnavailableException("TRAFFIC_BUDGET_EXHAUSTED");
        var notice =
            count >= authority.MaximumMessages - 2 ? WhatsAppGuestTrafficNotice.ActivationLimit
            : minuteCount >= authority.MaximumMessagesPerMinute - 2
                ? WhatsAppGuestTrafficNotice.GlobalRateLimit
            : WhatsAppGuestTrafficNotice.None;
        db.WhatsAppGuestTrafficEvents.Add(
            new()
            {
                TenantId = tenantId,
                ActivationDigest = activationDigest,
                AuthorityDigest = authorityDigest,
                EventId = eventId,
                BindingDigest = recipientBindingDigest,
                EventType = "INBOUND",
                InboundNotice = notice switch
                {
                    WhatsAppGuestTrafficNotice.ActivationLimit => "ACTIVATION_LIMIT",
                    WhatsAppGuestTrafficNotice.GlobalRateLimit => "GLOBAL_RATE_LIMIT",
                    _ => "NONE",
                },
                ReservedAt = now,
            }
        );
        if (gate.RequireActive(clock.GetUtcNow()) != authority)
            throw new WhatsAppCapabilityUnavailableException("ACTIVATION_RECORD_CHANGED");
        requireRoute?.Invoke();
        await PersistReservationAsync(db, transaction, ct);
        return notice;
    }

    public async Task<WhatsAppActivationAuthority> ReserveAsync(
        Guid challengeId,
        CancellationToken ct
    )
    {
        var now = clock.GetUtcNow();
        var authority = gate.RequireActive(now);
        if (!authority.AllowRegistrationVerification || challengeId == Guid.Empty)
            throw new WhatsAppCapabilityUnavailableException("REGISTRATION_VERIFICATION_DENIED");
        var activationDigest = Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes(authority.ActivationReference))
        );
        var authorityDigest = Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(authority)))
        );
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.Serializable,
            ct
        );
        var reservations = db.Set<WhatsAppTrafficReservation>()
            .Where(value => value.TenantId == authority.TenantId);
        var activationReservations = reservations.Where(value =>
            value.ActivationDigest == activationDigest
        );
        await EnsureGuestAuthorityAsync(
            db,
            authority.TenantId,
            activationDigest,
            authorityDigest,
            ct
        );
        if (await reservations.AnyAsync(value => value.OutboxId == challengeId, ct))
            throw new WhatsAppCapabilityUnavailableException("VERIFICATION_ALREADY_RESERVED");
        if (
            await activationReservations.AnyAsync(
                value => value.AuthorityDigest != authorityDigest,
                ct
            )
        )
            throw new WhatsAppCapabilityUnavailableException("ACTIVATION_RECORD_CHANGED");
        var cost = authority.MaximumCostPerMessageInr;
        var costPaise = CheckedPaise(cost);
        await ReserveEnvironmentSpendAsync(() =>
            _environmentSpend.ReserveAsync(
                db,
                authority.Environment,
                "MESSAGING",
                challengeId,
                authority.TenantId,
                activationDigest,
                Convert.ToHexStringLower(
                    SHA256.HashData(Encoding.UTF8.GetBytes($"registration:{challengeId:D}"))
                ),
                challengeId,
                costPaise,
                CheckedPaise(Math.Min(500m, authority.MaximumSpendInr)),
                now,
                ct
            )
        );
        var lockKey = WhatsAppGuestTrafficEventIdentity.LockKey(authority.TenantId);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_advisory_xact_lock(hashtextextended({lockKey}, 0))",
            ct
        );
        var activationSpend =
            await activationReservations.SumAsync(value => (decimal?)value.ReservedCostInr, ct)
            ?? 0m;
        if (
            await CountActivationMessagesAsync(db, authority.TenantId, activationDigest, ct)
                >= authority.MaximumMessages
            || await CountGlobalMessagesAsync(db, authority.TenantId, now.AddMinutes(-1), ct)
                >= authority.MaximumMessagesPerMinute
            || activationSpend + cost > authority.MaximumSpendInr
        )
            throw new WhatsAppCapabilityUnavailableException("TRAFFIC_BUDGET_EXHAUSTED");
        db.Set<WhatsAppTrafficReservation>()
            .Add(
                new()
                {
                    TenantId = authority.TenantId,
                    ActivationDigest = activationDigest,
                    AuthorityDigest = authorityDigest,
                    OutboxId = challengeId,
                    AttemptNumber = 1,
                    ReservedCostInr = cost,
                    ReservedAt = now,
                }
            );
        await PersistReservationAsync(db, transaction, ct);
        return authority;
    }

    public Task<WhatsAppActivationAuthority> ReserveAsync(
        WhatsAppProviderDispatchRequest request,
        string recipientBindingDigest,
        CancellationToken cancellationToken
    ) => ReserveOutboundCoreAsync(request, recipientBindingDigest, null, cancellationToken);

    internal Task<WhatsAppActivationAuthority> ReserveRelationshipOutboundAsync(
        WhatsAppProviderDispatchRequest request,
        WhatsAppCurrentRelationshipRoute route,
        CancellationToken ct
    )
    {
        RequireOutboundRoute(request, route);
        return ReserveOutboundCoreAsync(request, route.SenderHash, route, ct);
    }

    private void RequireOutboundRoute(
        WhatsAppProviderDispatchRequest request,
        WhatsAppCurrentRelationshipRoute route
    )
    {
        var scope =
            execution
            ?? throw new WhatsAppCapabilityUnavailableException(
                "OUTBOUND_BUDGET_ROUTING_OWNER_UNAVAILABLE"
            );
        scope.RequireRelationshipRoute(route);
        if (
            request.TenantId != route.TenantId
            || request.Environment != route.Environment
            || request.RelationshipId != route.RelationshipId
            || request.ConversationId != route.ConversationId
        )
            throw new WhatsAppCapabilityUnavailableException("OUTBOUND_BUDGET_ROUTE_DENIED");
    }

    private async Task<WhatsAppActivationAuthority> ReserveOutboundCoreAsync(
        WhatsAppProviderDispatchRequest request,
        string recipientBindingDigest,
        WhatsAppCurrentRelationshipRoute? route,
        CancellationToken cancellationToken
    )
    {
        var now = clock.GetUtcNow();
        var budgetTenant = route?.ServiceTenantId ?? request.TenantId;
        if (route is not null)
            RequireOutboundRoute(request, route);
        gate.RequireRecipient(budgetTenant, recipientBindingDigest, now);
        var authority = gate.RequireActive(now);
        if (
            authority.TenantId != budgetTenant
            || authority.Environment != request.Environment
            || (
                !authority.AllowPublicAdmission
                && authority.RecipientBindingDigest != recipientBindingDigest
            )
        )
            throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DENIED");
        var digest = Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes(authority.ActivationReference))
        );
        var authorityDigest = Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(authority)))
        );
        await using var db = await conversations.CreateDbContextAsync(cancellationToken);
        if (route is not null && !db.Database.IsNpgsql())
            throw new WhatsAppChannelBindingUnavailableException(
                "Customer outbound accounting requires PostgreSQL."
            );
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.Serializable,
            cancellationToken
        );
        if (route is not null)
        {
            var locked = await db
                .Database.SqlQuery<Guid>(
                    $"""
                    SELECT outbox_id AS "Value" FROM business.conversation_outbox
                    WHERE outbox_id = {request.OutboxId} AND tenant_id = {route.TenantId}
                        AND environment = {route.Environment} AND relationship_id = {route.RelationshipId}
                        AND conversation_id = {route.ConversationId} AND portal_context_id IS NULL
                        AND recipient_binding_digest = {route.SenderHash}
                    FOR SHARE
                    """
                )
                .ToListAsync(cancellationToken);
            if (locked.Count != 1 || locked[0] != request.OutboxId)
                throw new WhatsAppCapabilityUnavailableException("CANONICAL_MESSAGE_REQUIRED");
            RequireOutboundRoute(request, route);
        }
        var dispatchOutbox = await db
            .ConversationOutbox.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.OutboxId == request.OutboxId
                    && value.TenantId == request.TenantId
                    && value.Environment == request.Environment
                    && value.RelationshipId == request.RelationshipId
                    && value.ConversationId == request.ConversationId
                    && value.Sequence == request.Sequence
                    && value.PayloadReference == request.PayloadReference
                    && value.PayloadDigest == request.PayloadDigest
                    && value.State == "DISPATCHING"
                    && value.AttemptNumber == request.AttemptNumber
                    && value.LeaseExpiresAt > now,
                cancellationToken
            );
        if (dispatchOutbox is null)
            throw new WhatsAppCapabilityUnavailableException("OUTBOUND_LEASE_EXPIRED");
        if (dispatchOutbox.RecipientBindingDigest != recipientBindingDigest)
            throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DENIED");
        if (
            dispatchOutbox.Purpose
                is not (
                    "CUSTOMER_REQUEST"
                    or "WHATSAPP_GUEST_DISCOVERY"
                    or "WHATSAPP_GUEST_SESSION_LIMIT_NOTICE"
                )
            || dispatchOutbox.TemplateName is not null
            || dispatchOutbox.TemplateVersion is not null
            || dispatchOutbox.TemplateLocale is not null
            || dispatchOutbox.TemplateCategory is not null
        )
            throw new WhatsAppCapabilityUnavailableException("PROACTIVE_MESSAGING_DISABLED");

        using var serviceBudget = route is null
            ? null
            : execution!.BeginDatabaseTenantOverride(budgetTenant);
        await ReserveEnvironmentSpendAsync(() =>
            _environmentSpend.ReserveAsync(
                db,
                authority.Environment,
                "MESSAGING",
                request.OutboxId,
                budgetTenant,
                digest,
                request.PayloadDigest,
                request.OutboxId,
                0,
                CheckedPaise(Math.Min(500m, authority.MaximumSpendInr)),
                now,
                cancellationToken
            )
        );
        if (db.Database.IsRelational())
        {
            var guestLockKey = WhatsAppGuestTrafficEventIdentity.LockKey(budgetTenant);
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT pg_advisory_xact_lock(hashtextextended({guestLockKey}, 0))",
                cancellationToken
            );
        }

        var reservations = db.Set<WhatsAppTrafficReservation>()
            .Where(value => value.TenantId == budgetTenant && value.ActivationDigest == digest);
        await EnsureGuestAuthorityAsync(
            db,
            budgetTenant,
            digest,
            authorityDigest,
            cancellationToken
        );
        if (
            await reservations.AnyAsync(
                value => value.AuthorityDigest != authorityDigest,
                cancellationToken
            )
        )
            throw new WhatsAppCapabilityUnavailableException("ACTIVATION_RECORD_CHANGED");
        if (
            await reservations.AnyAsync(
                value => value.OutboxId == request.OutboxId,
                cancellationToken
            )
        )
            throw new WhatsAppCapabilityUnavailableException("OUTBOUND_ALREADY_RESERVED");
        var globalMinuteCount = await CountGlobalMessagesAsync(
            db,
            budgetTenant,
            now.AddMinutes(-1),
            cancellationToken
        );
        if (
            dispatchOutbox.PortalContextId is not null
            && dispatchOutbox.Purpose
                is "WHATSAPP_GUEST_DISCOVERY"
                    or "WHATSAPP_GUEST_SESSION_LIMIT_NOTICE"
        )
        {
            var guestEvents = db.Set<WhatsAppGuestTrafficEvent>()
                .Where(value => value.TenantId == budgetTenant);
            if (globalMinuteCount >= authority.MaximumMessagesPerMinute)
                throw new WhatsAppCapabilityUnavailableException("GUEST_GLOBAL_RATE_LIMIT_REACHED");
            if (
                await guestEvents.AnyAsync(
                    value =>
                        value.EventId
                        == WhatsAppGuestTrafficEventIdentity.Outbound(request.OutboxId),
                    cancellationToken
                )
            )
                throw new WhatsAppCapabilityUnavailableException("OUTBOUND_ALREADY_RESERVED");
            if (
                await guestEvents.CountAsync(
                    value =>
                        value.BindingDigest == dispatchOutbox.RecipientBindingDigest
                        && value.EventType != "SESSION"
                        && value.ReservedAt > now.AddHours(-24),
                    cancellationToken
                ) >= 10
            )
                throw new WhatsAppCapabilityUnavailableException("GUEST_MESSAGE_LIMIT_REACHED");
            db.Set<WhatsAppGuestTrafficEvent>()
                .Add(
                    new()
                    {
                        TenantId = budgetTenant,
                        ActivationDigest = digest,
                        AuthorityDigest = authorityDigest,
                        EventId = WhatsAppGuestTrafficEventIdentity.Outbound(request.OutboxId),
                        BindingDigest = dispatchOutbox.RecipientBindingDigest,
                        EventType = "OUTBOUND",
                        ReservedAt = now,
                    }
                );
        }
        const decimal reservedCostInr = 0m;
        var count = await CountActivationMessagesAsync(db, budgetTenant, digest, cancellationToken);
        var reservedSpendInr =
            await reservations.SumAsync(value => (decimal?)value.ReservedCostInr, cancellationToken)
            ?? 0m;
        if (
            count >= authority.MaximumMessages
            || reservedSpendInr + reservedCostInr > authority.MaximumSpendInr
            || globalMinuteCount >= authority.MaximumMessagesPerMinute
        )
            throw new WhatsAppCapabilityUnavailableException("TRAFFIC_BUDGET_EXHAUSTED");

        db.Set<WhatsAppTrafficReservation>()
            .Add(
                new()
                {
                    TenantId = budgetTenant,
                    ActivationDigest = digest,
                    AuthorityDigest = authorityDigest,
                    OutboxId = request.OutboxId,
                    AttemptNumber = request.AttemptNumber,
                    ReservedCostInr = reservedCostInr,
                    ReservedAt = now,
                }
            );
        if (route is not null)
            RequireOutboundRoute(request, route);
        if (gate.RequireActive(clock.GetUtcNow()) != authority)
            throw new WhatsAppCapabilityUnavailableException("ACTIVATION_RECORD_CHANGED");
        await PersistReservationAsync(db, transaction, cancellationToken);
        return authority;
    }

    private static long CheckedPaise(decimal inr)
    {
        var paise = inr * 100m;
        if (paise != decimal.Truncate(paise) || paise < 0 || paise > long.MaxValue)
            throw new WhatsAppCapabilityUnavailableException("ENVIRONMENT_SPEND_COST_UNVERIFIABLE");
        return checked((long)paise);
    }

    private static async Task ReserveEnvironmentSpendAsync(
        Func<Task<EnvironmentSpendPermit>> reserve
    )
    {
        try
        {
            await reserve();
        }
        catch (Npgsql.PostgresException failure) when (failure.SqlState == "40001")
        {
            throw new WhatsAppCapabilityUnavailableException("TRAFFIC_BUDGET_CONCURRENT_CHANGE");
        }
    }

    internal static async Task<int> CountGlobalMessagesAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        DateTimeOffset since,
        CancellationToken ct
    )
    {
        var guestEvents = db.Set<WhatsAppGuestTrafficEvent>()
            .Where(value =>
                value.TenantId == tenantId
                && value.EventType != "SESSION"
                && value.ReservedAt > since
            );
        var guestCount = await guestEvents.CountAsync(ct);
        var reservations = db.Set<WhatsAppTrafficReservation>()
            .Where(value => value.TenantId == tenantId && value.ReservedAt > since);
        return checked(
            guestCount
            + await CountProviderReservationsWithoutGuestEventAsync(guestEvents, reservations, ct)
        );
    }

    internal static async Task<int> CountActivationMessagesAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        string activationDigest,
        CancellationToken ct
    )
    {
        var guestEvents = db.Set<WhatsAppGuestTrafficEvent>()
            .Where(value =>
                value.TenantId == tenantId
                && value.ActivationDigest == activationDigest
                && value.EventType != "SESSION"
            );
        var guestCount = await guestEvents.CountAsync(ct);
        var reservations = db.Set<WhatsAppTrafficReservation>()
            .Where(value =>
                value.TenantId == tenantId && value.ActivationDigest == activationDigest
            );
        return checked(
            guestCount
            + await CountProviderReservationsWithoutGuestEventAsync(guestEvents, reservations, ct)
        );
    }

    private static async Task<int> CountProviderReservationsWithoutGuestEventAsync(
        IQueryable<WhatsAppGuestTrafficEvent> guestEvents,
        IQueryable<WhatsAppTrafficReservation> reservations,
        CancellationToken ct
    )
    {
        var providerRows = await reservations
            .Select(value => new { value.ActivationDigest, value.OutboxId })
            .ToListAsync(ct);
        var eventIds = providerRows
            .Select(value => WhatsAppGuestTrafficEventIdentity.Outbound(value.OutboxId))
            .Distinct()
            .ToArray();
        if (eventIds.Length == 0)
            return 0;
        var guestRows = await guestEvents
            .Where(value => value.EventType == "OUTBOUND" && eventIds.Contains(value.EventId))
            .Select(value => new { value.ActivationDigest, value.EventId })
            .ToListAsync(ct);
        var guestKeys = guestRows
            .Select(value => (value.ActivationDigest, value.EventId))
            .ToHashSet();
        return providerRows.Count(value =>
            !guestKeys.Contains(
                (value.ActivationDigest, WhatsAppGuestTrafficEventIdentity.Outbound(value.OutboxId))
            )
        );
    }

    private static async Task EnsureGuestAuthorityAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        string activationDigest,
        string authorityDigest,
        CancellationToken ct
    )
    {
        if (
            await db.Set<WhatsAppGuestTrafficEvent>()
                .AnyAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.ActivationDigest == activationDigest
                        && value.AuthorityDigest != authorityDigest,
                    ct
                )
        )
            throw new WhatsAppCapabilityUnavailableException("ACTIVATION_RECORD_CHANGED");
    }

    private static async Task PersistReservationAsync(
        ConversationStoreDbContext db,
        IDbContextTransaction transaction,
        CancellationToken ct
    )
    {
        try
        {
            await db.SaveChangesAsync(ct);
            await transaction.CommitAsync(ct);
        }
        catch (InvalidOperationException failure)
            when (failure.InnerException
                    is DbUpdateException
                    {
                        InnerException: Npgsql.PostgresException { SqlState: "40001" }
                    }
            )
        {
            throw new WhatsAppCapabilityUnavailableException("TRAFFIC_BUDGET_CONCURRENT_CHANGE");
        }
        catch (DbUpdateException failure)
            when (failure.InnerException is Npgsql.PostgresException { SqlState: "40001" })
        {
            throw new WhatsAppCapabilityUnavailableException("TRAFFIC_BUDGET_CONCURRENT_CHANGE");
        }
        catch (Npgsql.PostgresException failure) when (failure.SqlState == "40001")
        {
            throw new WhatsAppCapabilityUnavailableException("TRAFFIC_BUDGET_CONCURRENT_CHANGE");
        }
    }
}
