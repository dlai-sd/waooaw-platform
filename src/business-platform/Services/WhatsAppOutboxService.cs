// Implements: architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md §10.2, §13
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using System.Data;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record WhatsAppOutboundEligibility(
    bool OptedIn,
    bool OptedOut,
    bool RelationshipStopped,
    DateTimeOffset? LastInboundAt,
    string Purpose,
    string RecipientBindingDigest,
    string? TemplateName,
    string? TemplateVersion,
    string? TemplateLocale,
    string? TemplateCategory,
    bool TemplateApproved
);

public sealed record WhatsAppOutboxLease(
    Guid OutboxId,
    string Environment,
    Guid TenantId,
    Guid? RelationshipId,
    Guid? ConversationId,
    long Sequence,
    string PayloadReference,
    string PayloadDigest,
    int AttemptNumber,
    bool ReconciliationRequired,
    DateTimeOffset LeaseExpiresAt
);

public sealed record WhatsAppDispatchObservation(
    string State,
    string ProviderReferenceDigest,
    string ObservationDigest,
    DateTimeOffset ObservedAt
);

public sealed record WhatsAppProviderStatusEvent(
    string EventIdentity,
    string ProviderMessageId,
    string State,
    DateTimeOffset ObservedAt,
    string PayloadDigest
)
{
    public Guid? OutboxId { get; init; }
    public string? SenderBindingDigest { get; internal init; }
}

public sealed class WhatsAppOutboxService(
    IDbContextFactory<ConversationStoreDbContext> dbFactory,
    IDbContextFactory<EmploymentRelationshipDbContext> relationshipDbFactory,
    IOptions<Wc120ConversationOptions> conversationOptions,
    IOptionsMonitor<WhatsAppJourneyOptions> whatsAppOptions,
    ConversationStopFence stopFence,
    ConversationRuntimeIdentityAuthority? runtimeIdentity = null,
    WhatsAppDeliveryObservationRouting? relationshipRouting = null,
    WhatsAppTenantExecutionScope? execution = null
)
{
    private static readonly TimeSpan ServiceWindow = TimeSpan.FromHours(24);
    private static readonly TimeSpan LeaseDuration = TimeSpan.FromSeconds(60);
    private readonly Wc120ConversationOptions _conversationOptions = conversationOptions.Value;
    private WhatsAppJourneyOptions WhatsAppOptions => whatsAppOptions.CurrentValue;

    public async Task QueueGuestDiscoveryAsync(
        WhatsAppGuestSession guestSession,
        PortalInteractionMessageV1 message,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        if (!_conversationOptions.Enabled || !WhatsAppOptions.DispatchEnabled)
            throw new WhatsAppCapabilityUnavailableException("DISPATCH_DISABLED");
        await using var db = await dbFactory.CreateDbContextAsync(ct);
        await using var transaction = db.Database.IsRelational()
            ? await db.Database.BeginTransactionAsync(ct)
            : null;
        if (transaction is not null)
        {
            var lockKey = WhatsAppGuestSession.LockKey(
                guestSession.TenantId,
                guestSession.BindingDigest
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT pg_advisory_xact_lock(hashtextextended({lockKey}, 0))",
                ct
            );
        }
        var current =
            await db.Set<WhatsAppGuestSession>()
                .AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == guestSession.TenantId
                        && value.BindingDigest == guestSession.BindingDigest
                        && value.ParticipantId == guestSession.ParticipantId,
                    ct
                )
            ?? throw new ConversationNotAccessibleException();
        if (current.StoppedAt is not null)
            throw new ConversationStoppedException();
        if (await IsRecipientOptedOutAsync(guestSession.TenantId, guestSession.BindingDigest, ct))
            throw new ConversationStoppedException();
        if (current.EvidenceId is null || current.AdmittedAt is null)
            throw new ConversationNotAccessibleException();
        var context = await db.PortalInteractionContexts.SingleAsync(
            value =>
                value.TenantId == guestSession.TenantId
                && value.ParticipantId == guestSession.ParticipantId,
            ct
        );
        var canonical = await db
            .PortalInteractionMessages.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == current.TenantId
                    && value.ParticipantId == current.ParticipantId
                    && value.ContextId == context.ContextId
                    && value.MessageId == message.MessageId,
                ct
            );
        if (
            canonical is null
            || canonical.Actor != "GUIDE"
            || message.Actor != "GUIDE"
            || canonical.Sequence != message.Sequence
            || canonical.ClientMessageId is not null
            || message.ClientMessageId is not null
            || !(
                JsonSerializer.Deserialize<List<ConversationTextBlockV1>>(
                    canonical.ContentJson,
                    new JsonSerializerOptions(JsonSerializerDefaults.Web)
                ) ?? throw new ConversationStateConflictException()
            ).SequenceEqual(message.Content)
        )
            throw new WhatsAppCapabilityUnavailableException("MESSAGE_PROJECTION_DENIED");
        if (
            !WhatsAppGuestConsent.IsCurrent(current)
            && (
                message.Content.Count != 1
                || !WhatsAppGuestConsent.IsPreConsentNotice(message.Content[0].Text)
            )
        )
            throw new ConversationNotAccessibleException();
        var payload = JsonSerializer.Serialize(
            message.Content,
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );
        var digest = Sha256(payload);
        var aggregate = message.MessageId.ToString("D");
        var reference = $"portal-message:{aggregate}";
        async Task<ConversationOutboxRecord?> ExistingAsync() =>
            await db
                .ConversationOutbox.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == guestSession.TenantId
                        && value.PortalContextId == context.ContextId
                        && value.IdempotencyKey == message.MessageId,
                    ct
                );
        void CheckExisting(ConversationOutboxRecord existing)
        {
            if (
                existing.Environment != _conversationOptions.Environment
                || existing.RelationshipId is not null
                || existing.ConversationId is not null
                || existing.Sequence != message.Sequence
                || existing.Owner != "BUSINESS_PLATFORM"
                || existing.AggregateId != aggregate
                || existing.OperationFamily != "WHATSAPP_OUTBOUND"
                || existing.Purpose != "WHATSAPP_GUEST_DISCOVERY"
                || existing.RecipientBindingDigest != guestSession.BindingDigest
                || existing.ProtectedRecipientDestination is not null
                || existing.PayloadDigest != digest
                || existing.PayloadReference != reference
                || existing.TemplateName is not null
                || existing.TemplateVersion is not null
                || existing.TemplateLocale is not null
                || existing.TemplateCategory is not null
            )
                throw new ConversationIdempotencyConflictException();
        }
        var existing = await ExistingAsync();
        if (existing is not null)
        {
            CheckExisting(existing);
            return;
        }
        if (db.Database.IsNpgsql())
        {
            var outboxId = Guid.NewGuid();
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                INSERT INTO business.conversation_outbox
                    (outbox_id, environment, tenant_id, portal_context_id, sequence, owner,
                     aggregate_id, operation_family, idempotency_key, payload_digest,
                     payload_reference, purpose, recipient_binding_digest, state,
                     attempt_number, next_attempt_at, created_at, updated_at)
                VALUES ({outboxId}, {_conversationOptions.Environment}, {guestSession.TenantId}, {context.ContextId},
                    {message.Sequence}, 'BUSINESS_PLATFORM', {aggregate}, 'WHATSAPP_OUTBOUND',
                    {message.MessageId}, {digest}, {reference}, 'WHATSAPP_GUEST_DISCOVERY',
                    {guestSession.BindingDigest}, 'PENDING', 0, {now}, {now}, {now})
                ON CONFLICT DO NOTHING
                """,
                ct
            );
            var inserted = await ExistingAsync();
            if (inserted is null)
                throw new ConversationIdempotencyConflictException();
            CheckExisting(inserted);
            await transaction!.CommitAsync(ct);
            return;
        }
        db.ConversationOutbox.Add(
            new()
            {
                Environment = _conversationOptions.Environment,
                TenantId = guestSession.TenantId,
                PortalContextId = context.ContextId,
                Sequence = message.Sequence,
                AggregateId = message.MessageId.ToString("D"),
                OperationFamily = "WHATSAPP_OUTBOUND",
                IdempotencyKey = message.MessageId,
                PayloadDigest = digest,
                PayloadReference = reference,
                Purpose = "WHATSAPP_GUEST_DISCOVERY",
                RecipientBindingDigest = guestSession.BindingDigest,
                CreatedAt = now,
                UpdatedAt = now,
                NextAttemptAt = now,
            }
        );
        await db.SaveChangesAsync(ct);
        if (transaction is not null)
            await transaction.CommitAsync(ct);
    }

    public async Task QueueGuestAdmissionNoticeAsync(
        Guid tenantId,
        Guid participantId,
        string bindingDigest,
        string protectedDestination,
        PortalInteractionMessageV1 message,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        if (!_conversationOptions.Enabled || !WhatsAppOptions.DispatchEnabled)
            throw new WhatsAppCapabilityUnavailableException("DISPATCH_DISABLED");
        if (!IsDigest(bindingDigest) || string.IsNullOrWhiteSpace(protectedDestination))
            throw new WhatsAppCapabilityUnavailableException("PHONE_DESTINATION_UNAVAILABLE");
        if (await IsRecipientOptedOutAsync(tenantId, bindingDigest, ct))
            throw new ConversationStoppedException();
        if (
            message.Actor != "GUIDE"
            || message.ClientMessageId is not null
            || message.Content.Count != 1
            || message.Content[0].Text != WhatsAppGuestTrafficBudget.SessionLimitNotice
        )
            throw new WhatsAppCapabilityUnavailableException("MESSAGE_PROJECTION_DENIED");
        await using var db = await dbFactory.CreateDbContextAsync(ct);
        var context = await db.PortalInteractionContexts.SingleAsync(
            value => value.TenantId == tenantId && value.ParticipantId == participantId,
            ct
        );
        var payload = JsonSerializer.Serialize(
            message.Content,
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );
        var digest = Sha256(payload);
        var reference = $"portal-message:{message.MessageId:D}";
        var existing = await db.ConversationOutbox.SingleOrDefaultAsync(
            value =>
                value.TenantId == tenantId
                && value.PortalContextId == context.ContextId
                && value.IdempotencyKey == message.MessageId,
            ct
        );
        if (existing is not null)
        {
            if (
                existing.Purpose != "WHATSAPP_GUEST_SESSION_LIMIT_NOTICE"
                || existing.RecipientBindingDigest != bindingDigest
                || existing.PayloadDigest != digest
            )
                throw new ConversationIdempotencyConflictException();
            return;
        }
        if (db.Database.IsNpgsql())
        {
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                INSERT INTO business.conversation_outbox
                    (outbox_id, environment, tenant_id, portal_context_id, sequence, owner,
                     aggregate_id, operation_family, idempotency_key, payload_digest,
                     payload_reference, purpose, recipient_binding_digest,
                     protected_recipient_destination, state, attempt_number,
                     next_attempt_at, created_at, updated_at)
                VALUES ({Guid.NewGuid()}, {_conversationOptions.Environment}, {tenantId}, {context.ContextId},
                    {message.Sequence}, 'BUSINESS_PLATFORM', {message.MessageId:D}, 'WHATSAPP_OUTBOUND',
                    {message.MessageId}, {digest}, {reference}, 'WHATSAPP_GUEST_SESSION_LIMIT_NOTICE',
                    {bindingDigest}, {protectedDestination}, 'PENDING', 0, {now}, {now}, {now})
                ON CONFLICT DO NOTHING
                """,
                ct
            );
            var inserted = await db.ConversationOutbox.SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.PortalContextId == context.ContextId
                    && value.IdempotencyKey == message.MessageId,
                ct
            );
            if (
                inserted is null
                || inserted.Purpose != "WHATSAPP_GUEST_SESSION_LIMIT_NOTICE"
                || inserted.RecipientBindingDigest != bindingDigest
                || inserted.PayloadDigest != digest
            )
                throw new ConversationIdempotencyConflictException();
            return;
        }
        db.ConversationOutbox.Add(
            new()
            {
                Environment = _conversationOptions.Environment,
                TenantId = tenantId,
                PortalContextId = context.ContextId,
                Sequence = message.Sequence,
                AggregateId = message.MessageId.ToString("D"),
                OperationFamily = "WHATSAPP_OUTBOUND",
                IdempotencyKey = message.MessageId,
                PayloadDigest = digest,
                PayloadReference = reference,
                Purpose = "WHATSAPP_GUEST_SESSION_LIMIT_NOTICE",
                RecipientBindingDigest = bindingDigest,
                ProtectedRecipientDestination = protectedDestination,
                CreatedAt = now,
                UpdatedAt = now,
                NextAttemptAt = now,
            }
        );
        await db.SaveChangesAsync(ct);
    }

    public async Task<ConversationOutboxRecord?> QueueAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid conversationId,
        long canonicalSequence,
        string aggregateId,
        Guid idempotencyKey,
        string payloadDigest,
        string payloadReference,
        WhatsAppOutboundEligibility eligibility,
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        if (!_conversationOptions.Enabled || !WhatsAppOptions.DispatchEnabled)
            return null;
        if (await stopFence.IsLatchedAsync(tenantId, relationshipId, cancellationToken))
            return null;
        if (
            !eligibility.OptedIn
            || eligibility.OptedOut
            || eligibility.RelationshipStopped
            || eligibility.Purpose != "CUSTOMER_REQUEST"
            || string.IsNullOrWhiteSpace(eligibility.RecipientBindingDigest)
        )
            return null;

        var insideServiceWindow =
            eligibility.LastInboundAt.HasValue
            && now - eligibility.LastInboundAt.Value <= ServiceWindow
            && now >= eligibility.LastInboundAt.Value;
        if (
            !insideServiceWindow
            || eligibility.TemplateName is not null
            || eligibility.TemplateVersion is not null
            || eligibility.TemplateLocale is not null
            || eligibility.TemplateCategory is not null
        )
            return null;
        if (!IsDigest(payloadDigest))
            throw new ArgumentException(
                "Payload digest must be lowercase SHA-256.",
                nameof(payloadDigest)
            );

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var existing = await db.ConversationOutbox.SingleOrDefaultAsync(
            value =>
                value.Environment == _conversationOptions.Environment
                && value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.OperationFamily == "WHATSAPP_OUTBOUND"
                && value.IdempotencyKey == idempotencyKey,
            cancellationToken
        );
        if (existing is not null)
        {
            if (!string.Equals(existing.PayloadDigest, payloadDigest, StringComparison.Ordinal))
                throw new ConversationIdempotencyConflictException();
            return existing;
        }

        var record = new ConversationOutboxRecord
        {
            Environment = _conversationOptions.Environment,
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ConversationId = conversationId,
            Sequence = canonicalSequence,
            AggregateId = aggregateId,
            OperationFamily = "WHATSAPP_OUTBOUND",
            IdempotencyKey = idempotencyKey,
            PayloadDigest = payloadDigest,
            PayloadReference = payloadReference,
            Purpose = eligibility.Purpose,
            RecipientBindingDigest = eligibility.RecipientBindingDigest,
            TemplateName = eligibility.TemplateName,
            TemplateVersion = eligibility.TemplateVersion,
            TemplateLocale = eligibility.TemplateLocale,
            TemplateCategory = eligibility.TemplateCategory,
            NextAttemptAt = now,
            CreatedAt = now,
            UpdatedAt = now,
        };
        db.ConversationOutbox.Add(record);
        await db.SaveChangesAsync(cancellationToken);
        return record;
    }

    public Task<WhatsAppOutboxLease?> LeaseNextAsync(
        string workerId,
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        if (execution?.CurrentTenantId is { } tenant && tenant != execution.ServiceTenantId)
            throw new WhatsAppCapabilityUnavailableException("EXACT_OUTBOX_ROUTE_REQUIRED");
        return LeaseNextCoreAsync(workerId, now, null, null, cancellationToken);
    }

    internal Task<WhatsAppOutboxLease?> LeaseRelationshipAsync(
        Guid outboxId,
        WhatsAppCurrentRelationshipRoute route,
        string workerId,
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        if (outboxId == Guid.Empty)
            throw new ArgumentException("Outbox identity is required.", nameof(outboxId));
        RequireLeaseRoute(route);
        return LeaseNextCoreAsync(workerId, now, outboxId, route, cancellationToken);
    }

    private void RequireLeaseRoute(WhatsAppCurrentRelationshipRoute route)
    {
        var scope =
            execution
            ?? throw new WhatsAppCapabilityUnavailableException("OUTBOX_ROUTING_OWNER_UNAVAILABLE");
        if (
            scope.ServiceTenantId != route.ServiceTenantId
            || scope.CurrentTenantId != route.TenantId
            || route.Environment != _conversationOptions.Environment
        )
            throw new WhatsAppCapabilityUnavailableException("OUTBOX_ROUTE_DENIED");
        scope.RequireRelationshipRoute(route);
    }

    private async Task<WhatsAppOutboxLease?> LeaseNextCoreAsync(
        string workerId,
        DateTimeOffset now,
        Guid? outboxId,
        WhatsAppCurrentRelationshipRoute? route,
        CancellationToken cancellationToken
    )
    {
        if (!_conversationOptions.Enabled || !WhatsAppOptions.DispatchEnabled)
            return null;
        if (string.IsNullOrWhiteSpace(workerId))
            throw new ArgumentException("Worker identity is required.", nameof(workerId));

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        if (route is not null && !db.Database.IsNpgsql())
            throw new WhatsAppChannelBindingUnavailableException(
                "Customer outbox leasing requires PostgreSQL."
            );
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.Serializable,
            cancellationToken
        );
        if (route is not null)
        {
            RequireLeaseRoute(route);
            var locked = await db
                .Database.SqlQuery<Guid>(
                    $"""
                    SELECT outbox_id AS "Value" FROM business.conversation_outbox
                    WHERE outbox_id = {outboxId} AND environment = {route.Environment}
                        AND tenant_id = {route.TenantId} AND relationship_id = {route.RelationshipId}
                        AND conversation_id = {route.ConversationId}
                        AND recipient_binding_digest = {route.SenderHash} AND portal_context_id IS NULL
                    FOR UPDATE SKIP LOCKED
                    """
                )
                .ToListAsync(cancellationToken);
            if (locked.Count == 0)
                return null;
            if (locked.Count != 1 || locked[0] != outboxId)
                throw new ConversationIdempotencyConflictException();
            var originalRouteMatches = await db
                .Database.SqlQuery<bool>(
                    $"""
                    SELECT business.matches_whatsapp_outbox_route(
                        {route.ServiceTenantId}, {route.TenantId}, {route.SenderHash}, {route.Environment},
                        {outboxId}, {route.BindingId}) AS "Value"
                    """
                )
                .SingleAsync(cancellationToken);
            if (!originalRouteMatches)
                throw new ConstitutionalActionDeniedException(
                    "The original outbox route has been retired."
                );
        }
        var eligible = db.ConversationOutbox.Where(value =>
            value.Environment == _conversationOptions.Environment
            && (
                value.State == "PENDING"
                || value.State == "UNRESOLVED"
                || (
                    (value.State == "LEASED" || value.State == "DISPATCHING")
                    && value.LeaseExpiresAt != null
                    && value.LeaseExpiresAt <= now
                )
            )
            && value.NextAttemptAt <= now
            && (
                value.AttemptNumber < 12
                || value.State == "UNRESOLVED"
                || value.State == "LEASED"
                || value.State == "DISPATCHING"
            )
            && !db.ConversationOutbox.Any(earlier =>
                earlier.Environment == value.Environment
                && earlier.TenantId == value.TenantId
                && earlier.RelationshipId == value.RelationshipId
                && earlier.ConversationId == value.ConversationId
                && earlier.PortalContextId == value.PortalContextId
                && earlier.Sequence < value.Sequence
                && earlier.State != "DELIVERED"
                && earlier.State != "BLOCKED"
            )
        );
        if (route is not null)
            eligible = eligible.Where(value =>
                value.OutboxId == outboxId
                && value.TenantId == route.TenantId
                && value.RelationshipId == route.RelationshipId
                && value.ConversationId == route.ConversationId
                && value.RecipientBindingDigest == route.SenderHash
                && value.PortalContextId == null
            );
        var record = await eligible
            .OrderBy(value => value.CreatedAt)
            .ThenBy(value => value.Sequence)
            .FirstOrDefaultAsync(cancellationToken);
        if (record is null)
            return null;

        var reconciliationRequired =
            record.State == "UNRESOLVED"
            || record.State == "DISPATCHING"
            || (record.State == "LEASED" && record.AttemptNumber >= 12);
        if (!reconciliationRequired)
            record.AttemptNumber++;
        record.State = "LEASED";
        record.LeaseOwner = workerId;
        record.HeartbeatAt = now;
        record.LeaseExpiresAt = now.Add(LeaseDuration);
        record.UpdatedAt = now;
        if (route is not null)
            RequireLeaseRoute(route);
        await db.SaveChangesAsync(cancellationToken);
        if (route is not null)
            RequireLeaseRoute(route);
        await transaction.CommitAsync(cancellationToken);
        return new(
            record.OutboxId,
            record.Environment,
            record.TenantId,
            record.RelationshipId,
            record.ConversationId,
            record.Sequence,
            record.PayloadReference,
            record.PayloadDigest,
            record.AttemptNumber,
            reconciliationRequired,
            record.LeaseExpiresAt.Value
        );
    }

    public async Task<bool> BeginDispatchAsync(
        Guid outboxId,
        string workerId,
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        if (!_conversationOptions.Enabled || !WhatsAppOptions.DispatchEnabled)
            return false;

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        await using var customerTransaction = await LockCustomerOwnedLeaseAsync(
            db,
            outboxId,
            workerId,
            now,
            cancellationToken
        );
        var record = await OwnedLeaseAsync(db, outboxId, workerId, cancellationToken);
        if (
            record.LeaseExpiresAt <= now
            || (
                record.RelationshipId is { } relationshipId
                && await stopFence.IsLatchedAsync(
                    record.TenantId,
                    relationshipId,
                    cancellationToken
                )
            )
            || !await IsCurrentlyEligibleAsync(record, now, cancellationToken)
        )
        {
            record.State = "BLOCKED";
            record.BlockedReason = "CURRENT_ELIGIBILITY_DENIED";
            record.LeaseOwner = null;
            record.LeaseExpiresAt = null;
            record.HeartbeatAt = null;
            record.UpdatedAt = now;
            db.OperationalSignals.Add(
                Signal(record.Environment, "OUTBOUND", "CURRENT_ELIGIBILITY_DENIED", now)
            );
            await db.SaveChangesAsync(cancellationToken);
            if (customerTransaction is not null)
                await customerTransaction.CommitAsync(cancellationToken);
            return false;
        }

        record.State = "DISPATCHING";
        record.UpdatedAt = now;
        await db.SaveChangesAsync(cancellationToken);
        if (customerTransaction is not null)
            await customerTransaction.CommitAsync(cancellationToken);
        return true;
    }

    public async Task HeartbeatAsync(
        Guid outboxId,
        string workerId,
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        await using var customerTransaction = await LockCustomerOwnedLeaseAsync(
            db,
            outboxId,
            workerId,
            now,
            cancellationToken
        );
        var record = await OwnedLeaseAsync(db, outboxId, workerId, cancellationToken);
        record.HeartbeatAt = now;
        record.LeaseExpiresAt = now.Add(LeaseDuration);
        record.UpdatedAt = now;
        await db.SaveChangesAsync(cancellationToken);
        if (customerTransaction is not null)
            await customerTransaction.CommitAsync(cancellationToken);
    }

    public async Task RecordResultAsync(
        Guid outboxId,
        string workerId,
        WhatsAppDispatchObservation observation,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        await using var customerTransaction = await LockCustomerOwnedLeaseAsync(
            db,
            outboxId,
            workerId,
            observation.ObservedAt,
            cancellationToken
        );
        var record = await OwnedLeaseAsync(db, outboxId, workerId, cancellationToken);
        if (!IsDigest(observation.ObservationDigest))
            throw new ArgumentException(
                "Observation digest must be lowercase SHA-256.",
                nameof(observation)
            );
        if (!IsDigest(observation.ProviderReferenceDigest))
            throw new ArgumentException(
                "Provider reference digest must be lowercase SHA-256.",
                nameof(observation)
            );

        record.State = observation.State switch
        {
            "DELIVERED" => "DELIVERED",
            "PROVIDER_ACCEPTED" => "UNRESOLVED",
            "UNKNOWN" => "UNRESOLVED",
            "REJECTED" or "NOT_SENT" => "BLOCKED",
            _ => throw new ArgumentException("Dispatch state is unsupported.", nameof(observation)),
        };
        record.BlockedReason = observation.State switch
        {
            "REJECTED" => "PROVIDER_REJECTED",
            "NOT_SENT" => "DISPATCH_AUTHORITY_DENIED",
            _ => null,
        };
        record.LeaseOwner = null;
        record.LeaseExpiresAt = null;
        record.HeartbeatAt = null;
        record.NextAttemptAt =
            record.State == "UNRESOLVED"
                ? observation.ObservedAt.Add(Backoff(record.AttemptNumber))
                : observation.ObservedAt;
        record.UpdatedAt = observation.ObservedAt;
        if (record.AttemptNumber >= 12 && observation.State == "REJECTED")
        {
            record.State = "BLOCKED";
            record.BlockedReason = "ATTEMPT_LIMIT_REACHED";
        }
        if (record.State == "UNRESOLVED")
        {
            db.OperationalSignals.Add(
                Signal(
                    record.Environment,
                    "OUTBOUND",
                    "PROVIDER_OUTCOME_UNKNOWN",
                    observation.ObservedAt
                )
            );
        }
        else if (record.State == "BLOCKED")
        {
            db.OperationalSignals.Add(
                Signal(
                    record.Environment,
                    "DEAD_LETTER",
                    record.BlockedReason ?? "OUTBOUND_BLOCKED",
                    observation.ObservedAt
                )
            );
        }
        if (Guid.TryParse(record.AggregateId, out var messageId))
        {
            db.DeliveryObservations.Add(
                new ConversationDeliveryObservation
                {
                    Environment = record.Environment,
                    TenantId = record.TenantId,
                    RelationshipId = record.RelationshipId,
                    PortalContextId = record.PortalContextId,
                    MessageId = record.PortalContextId is null ? messageId : null,
                    PortalMessageId = record.PortalContextId is not null ? messageId : null,
                    Provider = "WHATSAPP",
                    ProviderEventIdentity = observation.ObservationDigest,
                    ProviderReferenceDigest = observation.ProviderReferenceDigest,
                    DeliveryState = observation.State,
                    ObservationDigest = observation.ObservationDigest,
                    ObservedAt = observation.ObservedAt,
                    RetainUntil = observation.ObservedAt.AddYears(7),
                }
            );
        }
        await db.SaveChangesAsync(cancellationToken);
        if (customerTransaction is not null)
            await customerTransaction.CommitAsync(cancellationToken);
    }

    public async Task<bool> RecordProviderStatusAsync(
        WhatsAppProviderStatusEvent statusEvent,
        CancellationToken cancellationToken
    )
    {
        if (statusEvent.SenderBindingDigest is not null)
        {
            if (relationshipRouting is null)
                throw new WhatsAppCapabilityUnavailableException(
                    "DELIVERY_ROUTING_OWNER_UNAVAILABLE"
                );
            return await relationshipRouting.RecordDeliveryObservationAsync(
                statusEvent,
                (db, ct) => RecordProviderStatusCoreAsync(db, statusEvent, ct),
                cancellationToken
            );
        }
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        return await RecordProviderStatusCoreAsync(db, statusEvent, cancellationToken);
    }

    private async Task<bool> RecordProviderStatusCoreAsync(
        ConversationStoreDbContext db,
        WhatsAppProviderStatusEvent statusEvent,
        CancellationToken cancellationToken
    )
    {
        if (
            !IsDigest(statusEvent.PayloadDigest)
            || string.IsNullOrWhiteSpace(statusEvent.EventIdentity)
            || string.IsNullOrWhiteSpace(statusEvent.ProviderMessageId)
        )
            throw new ArgumentException(
                "Provider status identity is invalid.",
                nameof(statusEvent)
            );

        var deliveryState = statusEvent.State.Trim().ToUpperInvariant() switch
        {
            "SENT" => "PROVIDER_ACCEPTED",
            "DELIVERED" => "DELIVERED",
            "READ" => "READ",
            "FAILED" => "FAILED",
            _ => throw new ArgumentException(
                "Provider status is unsupported.",
                nameof(statusEvent)
            ),
        };
        var providerReferenceDigest = Sha256(statusEvent.ProviderMessageId);
        var observationDigest = Sha256(
            JsonSerializer.Serialize(
                new
                {
                    statusEvent.EventIdentity,
                    providerReferenceDigest,
                    deliveryState,
                    statusEvent.ObservedAt,
                }
            )
        );

        var claim = await db.ProviderEventClaims.SingleOrDefaultAsync(
            value =>
                value.Environment == _conversationOptions.Environment
                && value.Provider == "WHATSAPP_STATUS"
                && value.AppBindingDigest == _conversationOptions.AppBindingDigest
                && value.EventIdentity == statusEvent.EventIdentity,
            cancellationToken
        );
        if (claim is not null)
        {
            if (
                !string.Equals(
                    claim.PayloadDigest,
                    statusEvent.PayloadDigest,
                    StringComparison.Ordinal
                )
            )
                throw new ConversationIdempotencyConflictException();
            if (claim.State == "ACCEPTED")
                return true;
        }
        else
        {
            claim = new ProviderEventClaim
            {
                Environment = _conversationOptions.Environment,
                Provider = "WHATSAPP_STATUS",
                AppBindingDigest = _conversationOptions.AppBindingDigest,
                EventIdentity = statusEvent.EventIdentity,
                PayloadDigest = statusEvent.PayloadDigest,
                State = "CLAIMED",
                ReceivedAt = statusEvent.ObservedAt,
            };
            db.ProviderEventClaims.Add(claim);
            try
            {
                await db.SaveChangesAsync(cancellationToken);
            }
            catch (DbUpdateException exception)
                when (ProviderEventClaimConflict.IsIdentityCollision(exception))
            {
                db.ChangeTracker.Clear();
                claim = await db.ProviderEventClaims.SingleAsync(
                    value =>
                        value.Environment == _conversationOptions.Environment
                        && value.Provider == "WHATSAPP_STATUS"
                        && value.AppBindingDigest == _conversationOptions.AppBindingDigest
                        && value.EventIdentity == statusEvent.EventIdentity,
                    cancellationToken
                );
                if (
                    !string.Equals(
                        claim.PayloadDigest,
                        statusEvent.PayloadDigest,
                        StringComparison.Ordinal
                    )
                )
                    throw new ConversationIdempotencyConflictException();
                if (claim.State == "ACCEPTED")
                    return true;
            }
        }

        var source = await db
            .DeliveryObservations.AsNoTracking()
            .Where(value =>
                value.Environment == _conversationOptions.Environment
                && value.Provider == "WHATSAPP"
                && value.ProviderReferenceDigest == providerReferenceDigest
            )
            .OrderBy(value => value.ObservedAt)
            .FirstOrDefaultAsync(cancellationToken);
        if (
            statusEvent.SenderBindingDigest is { } sender
            && statusEvent.OutboxId is null
            && source is not null
        )
        {
            var messageId = (
                source.PortalContextId is null ? source.MessageId : source.PortalMessageId
            )?.ToString("D");
            if (
                messageId is null
                || !await db.ConversationOutbox.AnyAsync(
                    value =>
                        value.Environment == source.Environment
                        && value.TenantId == source.TenantId
                        && value.RelationshipId == source.RelationshipId
                        && value.PortalContextId == source.PortalContextId
                        && value.AggregateId == messageId
                        && value.RecipientBindingDigest == sender
                        && value.AttemptNumber > 0,
                    cancellationToken
                )
            )
                throw new ConversationIdempotencyConflictException();
        }
        if (statusEvent.OutboxId is { } correlatedId)
        {
            var correlated = await db
                .ConversationOutbox.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.OutboxId == correlatedId
                        && value.Environment == _conversationOptions.Environment
                        && value.AttemptNumber > 0
                        && (
                            value.State == "DISPATCHING"
                            || value.State == "UNRESOLVED"
                            || value.State == "LEASED"
                            || value.State == "DELIVERED"
                            || value.State == "BLOCKED"
                        ),
                    cancellationToken
                );
            if (
                correlated is null
                || (
                    statusEvent.SenderBindingDigest is { } bindingDigest
                    && correlated.RecipientBindingDigest != bindingDigest
                )
                || !Guid.TryParse(correlated.AggregateId, out var correlatedMessageId)
                || !await HasSubmissionReservationAsync(
                    db,
                    correlated,
                    statusEvent,
                    cancellationToken
                )
                || (
                    source is not null
                    && (
                        source.TenantId != correlated.TenantId
                        || source.RelationshipId != correlated.RelationshipId
                        || source.PortalContextId != correlated.PortalContextId
                        || (
                            source.PortalContextId is null
                                ? source.MessageId != correlatedMessageId
                                : source.PortalMessageId != correlatedMessageId
                        )
                    )
                )
            )
                throw new ConversationIdempotencyConflictException();
            source ??= new ConversationDeliveryObservation
            {
                Environment = correlated.Environment,
                TenantId = correlated.TenantId,
                RelationshipId = correlated.RelationshipId,
                PortalContextId = correlated.PortalContextId,
                MessageId = correlated.PortalContextId is null ? correlatedMessageId : null,
                PortalMessageId = correlated.PortalContextId is not null
                    ? correlatedMessageId
                    : null,
            };
        }
        if (source is null)
        {
            claim.State = "UNRESOLVED";
            db.OperationalSignals.Add(
                Signal(
                    _conversationOptions.Environment,
                    "DELIVERY",
                    "STATUS_BEFORE_SUBMISSION",
                    statusEvent.ObservedAt
                )
            );
            await db.SaveChangesAsync(cancellationToken);
            return false;
        }

        var alreadyRecorded = await db
            .DeliveryObservations.AsNoTracking()
            .AnyAsync(
                value =>
                    value.Environment == source.Environment
                    && value.TenantId == source.TenantId
                    && value.RelationshipId == source.RelationshipId
                    && value.MessageId == source.MessageId
                    && value.PortalMessageId == source.PortalMessageId
                    && value.Provider == "WHATSAPP"
                    && value.ProviderEventIdentity == statusEvent.EventIdentity,
                cancellationToken
            );
        if (!alreadyRecorded)
        {
            db.DeliveryObservations.Add(
                new ConversationDeliveryObservation
                {
                    Environment = source.Environment,
                    TenantId = source.TenantId,
                    RelationshipId = source.RelationshipId,
                    PortalContextId = source.PortalContextId,
                    MessageId = source.MessageId,
                    PortalMessageId = source.PortalMessageId,
                    Provider = "WHATSAPP",
                    ProviderEventIdentity = statusEvent.EventIdentity,
                    ProviderReferenceDigest = providerReferenceDigest,
                    DeliveryState = deliveryState,
                    ObservationDigest = observationDigest,
                    ObservedAt = statusEvent.ObservedAt,
                    RetainUntil = statusEvent.ObservedAt.AddYears(7),
                }
            );
        }
        claim.State = "ACCEPTED";
        claim.ResultJson = JsonSerializer.Serialize(new { deliveryState, observationDigest });
        claim.TerminalAt = DateTimeOffset.UtcNow;
        claim.ExpiresAt = claim.TerminalAt.Value.AddDays(30);
        await db.SaveChangesAsync(cancellationToken);
        return true;
    }

    internal async Task<bool> HasSubmissionReservationAsync(
        ConversationStoreDbContext db,
        ConversationOutboxRecord outbox,
        WhatsAppProviderStatusEvent status,
        CancellationToken ct
    )
    {
        var tenant = outbox.TenantId;
        if (
            status.SenderBindingDigest is not null
            && execution?.ServiceTenantId is { } serviceTenant
            && serviceTenant != tenant
        )
        {
            if (
                execution.CurrentTenantId != tenant
                || status.SenderBindingDigest != outbox.RecipientBindingDigest
            )
                throw new ConversationIdempotencyConflictException();
            using var serviceBudget = execution.BeginDatabaseTenantOverride(serviceTenant);
            return await db.Set<WhatsAppTrafficReservation>()
                .AnyAsync(
                    value =>
                        value.TenantId == serviceTenant
                        && value.OutboxId == outbox.OutboxId
                        && value.AttemptNumber == outbox.AttemptNumber,
                    ct
                );
        }
        return await db.Set<WhatsAppTrafficReservation>()
            .AnyAsync(value => value.TenantId == tenant && value.OutboxId == outbox.OutboxId, ct);
    }

    public async Task ApplyRelationshipClosureAsync(
        Guid tenantId,
        Guid relationshipId,
        DateTimeOffset closedAt,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var minimumRetention = closedAt.AddYears(7);
        var due = db.DeliveryObservations.Where(value =>
            value.Environment == _conversationOptions.Environment
            && value.TenantId == tenantId
            && value.RelationshipId == relationshipId
            && value.RetainUntil < minimumRetention
        );
        if (db.Database.IsRelational())
        {
            await due.ExecuteUpdateAsync(
                updates => updates.SetProperty(value => value.RetainUntil, minimumRetention),
                cancellationToken
            );
            return;
        }

        var observations = await due.ToListAsync(cancellationToken);
        foreach (var observation in observations)
            observation.RetainUntil = minimumRetention;
        await db.SaveChangesAsync(cancellationToken);
    }

    public async Task SetDeliveryLegalHoldAsync(
        Guid tenantId,
        Guid relationshipId,
        bool held,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var observations = await db
            .DeliveryObservations.Where(value =>
                value.Environment == _conversationOptions.Environment
                && value.TenantId == tenantId
                && value.RelationshipId == relationshipId
            )
            .ToListAsync(cancellationToken);
        foreach (var observation in observations)
            observation.LegalHold = held;
        await db.SaveChangesAsync(cancellationToken);
    }

    public async Task<int> PurgeDeliveryObservationsAsync(
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var due = db.DeliveryObservations.Where(value =>
            value.Environment == _conversationOptions.Environment
            && !value.LegalHold
            && value.RetainUntil <= now
        );
        if (db.Database.IsRelational())
            return await due.ExecuteDeleteAsync(cancellationToken);

        var observations = await due.ToListAsync(cancellationToken);
        db.DeliveryObservations.RemoveRange(observations);
        await db.SaveChangesAsync(cancellationToken);
        return observations.Count;
    }

    private async Task<IDbContextTransaction?> LockCustomerOwnedLeaseAsync(
        ConversationStoreDbContext db,
        Guid outboxId,
        string workerId,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        if (execution?.CurrentTenantId is not { } tenant || tenant == execution.ServiceTenantId)
            return null;
        var route = execution.RequireConfirmedRelationshipRoute();
        if (!db.Database.IsNpgsql())
            throw new WhatsAppChannelBindingUnavailableException(
                "Customer lease updates require PostgreSQL."
            );
        var transaction = await db.Database.BeginTransactionAsync(ct);
        try
        {
            var owned = await db
                .Database.SqlQuery<Guid>(
                    $"""
                    SELECT outbox_id AS "Value" FROM business.conversation_outbox
                    WHERE outbox_id = {outboxId} AND tenant_id = {route.TenantId}
                        AND environment = {route.Environment} AND relationship_id = {route.RelationshipId}
                        AND conversation_id = {route.ConversationId} AND recipient_binding_digest = {route.SenderHash}
                        AND portal_context_id IS NULL AND lease_owner = {workerId}
                        AND state IN ('LEASED', 'DISPATCHING') AND lease_expires_at > {now}
                    FOR UPDATE
                    """
                )
                .ToListAsync(ct);
            if (owned.Count != 1 || owned[0] != outboxId)
                throw new ConversationStateConflictException();
            execution.RequireRelationshipRoute(route);
            return transaction;
        }
        catch
        {
            await transaction.DisposeAsync();
            throw;
        }
    }

    private static async Task<ConversationOutboxRecord> OwnedLeaseAsync(
        ConversationStoreDbContext db,
        Guid outboxId,
        string workerId,
        CancellationToken cancellationToken
    )
    {
        var record = await db.ConversationOutbox.SingleOrDefaultAsync(
            value =>
                value.OutboxId == outboxId
                && (value.State == "LEASED" || value.State == "DISPATCHING")
                && value.LeaseOwner == workerId,
            cancellationToken
        );
        return record ?? throw new ConversationStateConflictException();
    }

    private static TimeSpan Backoff(int attemptNumber) =>
        TimeSpan.FromSeconds(Math.Min(300, Math.Pow(2, Math.Max(0, attemptNumber - 1))));

    internal async Task<bool> IsCurrentlyEligibleAsync(
        ConversationOutboxRecord record,
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        await using var db = await relationshipDbFactory.CreateDbContextAsync(cancellationToken);
        return await IsCurrentlyEligibleAsync(record, now, db, null, cancellationToken);
    }

    private async Task<bool> IsCurrentlyEligibleAsync(
        ConversationOutboxRecord record,
        DateTimeOffset now,
        EmploymentRelationshipDbContext db,
        ConversationStoreDbContext? runtimeContext,
        CancellationToken cancellationToken
    )
    {
        if (record.PortalContextId is { } contextId)
        {
            if (
                record.RelationshipId is not null
                || record.ConversationId is not null
                || record.Purpose
                    is not ("WHATSAPP_GUEST_DISCOVERY" or "WHATSAPP_GUEST_SESSION_LIMIT_NOTICE")
                || record.TemplateName is not null
            )
                return false;
            await using var interactions = await dbFactory.CreateDbContextAsync(cancellationToken);
            if (
                await db.WhatsAppJourneyContacts.AnyAsync(
                    contact =>
                        contact.TenantId == record.TenantId
                        && contact.PhoneHmac == record.RecipientBindingDigest
                        && contact.OptedOutAt != null,
                    cancellationToken
                )
            )
                return false;
            if (record.Purpose == "WHATSAPP_GUEST_SESSION_LIMIT_NOTICE")
            {
                if (
                    record.ProtectedRecipientDestination is null
                    || now < record.CreatedAt
                    || now - record.CreatedAt > ServiceWindow
                )
                    return false;
                var stoppedOrAdmitted = await interactions
                    .Set<WhatsAppGuestSession>()
                    .AnyAsync(
                        identity =>
                            identity.TenantId == record.TenantId
                            && identity.BindingDigest == record.RecipientBindingDigest,
                        cancellationToken
                    );
                return !stoppedOrAdmitted
                    && await interactions.PortalInteractionContexts.AnyAsync(
                        context =>
                            context.ContextId == contextId && context.TenantId == record.TenantId,
                        cancellationToken
                    );
            }
            var guest = await (
                from context in interactions.PortalInteractionContexts
                join identity in interactions.Set<WhatsAppGuestSession>()
                    on new { context.TenantId, context.ParticipantId } equals new
                    {
                        identity.TenantId,
                        identity.ParticipantId,
                    }
                where
                    context.ContextId == contextId
                    && identity.TenantId == record.TenantId
                    && identity.BindingDigest == record.RecipientBindingDigest
                    && identity.EvidenceId != null
                    && identity.AdmittedAt != null
                    && identity.StoppedAt == null
                    && identity.LastInboundAt <= now
                    && identity.LastInboundAt >= now.Subtract(ServiceWindow)
                select identity
            ).SingleOrDefaultAsync(cancellationToken);
            if (guest is null)
                return false;
            if (WhatsAppGuestConsent.IsCurrent(guest))
                return true;
            if (!Guid.TryParse(record.AggregateId, out var guestMessageId))
                return false;
            var contentJson = await interactions
                .PortalInteractionMessages.AsNoTracking()
                .Where(message =>
                    message.TenantId == record.TenantId
                    && message.ContextId == contextId
                    && message.ParticipantId == guest.ParticipantId
                    && message.MessageId == guestMessageId
                    && message.Sequence == record.Sequence
                    && message.Actor == "GUIDE"
                )
                .Select(message => message.ContentJson)
                .SingleOrDefaultAsync(cancellationToken);
            if (contentJson is null)
                return false;
            try
            {
                var content = JsonSerializer.Deserialize<List<ConversationTextBlockV1>>(
                    contentJson,
                    new JsonSerializerOptions(JsonSerializerDefaults.Web)
                );
                return content is { Count: 1 }
                    && content[0].BlockType == "TEXT"
                    && WhatsAppGuestConsent.IsPreConsentNotice(content[0].Text);
            }
            catch (JsonException)
            {
                return false;
            }
        }
        var relationship = await db
            .EmploymentRelationships.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == record.TenantId
                    && value.RelationshipId == record.RelationshipId,
                cancellationToken
            );
        if (
            relationship is null
            || relationship.State == EmploymentRelationshipState.StoppedEmergency
            || relationship.StoppedAt is not null
        )
            return false;

        var bindings = await db
            .ChannelBindings.AsNoTracking()
            .Where(value =>
                value.TenantId == record.TenantId
                && value.Channel == "WHATSAPP"
                && value.ExternalSubjectHash == record.RecipientBindingDigest
                && value.Status == "ACTIVE"
            )
            .Take(2)
            .ToListAsync(cancellationToken);
        if (
            bindings.Count != 1
            || bindings[0].RelationshipId != record.RelationshipId
            || record.ConversationId is null
            || !Guid.TryParse(bindings[0].ConversationId, out var boundConversationId)
            || boundConversationId != record.ConversationId
        )
            return false;
        var binding = bindings[0];
        var recoveryReply = record.PayloadReference.StartsWith(
            "runtime-recovery:",
            StringComparison.Ordinal
        );
        if (
            record.PayloadReference.StartsWith("runtime-reply:", StringComparison.Ordinal)
            || recoveryReply
        )
        {
            var parts = record.PayloadReference.Split(':');
            if (
                parts.Length != (recoveryReply ? 4 : 3)
                || !Guid.TryParse(parts[1], out var runtimeExecutionId)
                || !Guid.TryParse(parts[2], out var runtimeMessageId)
                || record.AggregateId != runtimeMessageId.ToString("D")
            )
                return false;
            await using var ownedRuntime = runtimeContext is null
                ? await dbFactory.CreateDbContextAsync(cancellationToken)
                : null;
            var runtime =
                runtimeContext
                ?? ownedRuntime
                ?? throw new ConversationExecutionUnavailableException();
            var execution = await runtime
                .Executions.AsNoTracking()
                .SingleOrDefaultAsync(
                    row =>
                        row.TenantId == record.TenantId
                        && row.ExecutionId == runtimeExecutionId
                        && row.RelationshipId == record.RelationshipId
                        && row.ConversationId == record.ConversationId,
                    cancellationToken
                );
            if (
                execution is null
                || !execution.RuntimeTerminal
                || execution.ProcessingState is not ("COMPLETED" or "FAILED")
                || execution.OriginChannelBindingId != binding.BindingId
                || execution.OriginRecipientDigest != record.RecipientBindingDigest
                || runtimeIdentity is null
            )
                return false;
            try
            {
                if (recoveryReply)
                {
                    if (!Guid.TryParse(parts[3], out var permissionId))
                        return false;
                    var permission = await runtime
                        .ReconciliationAuthorities.AsNoTracking()
                        .SingleOrDefaultAsync(
                            value =>
                                value.TenantId == record.TenantId
                                && value.ExecutionId == execution.ExecutionId
                                && value.AuthorityId == permissionId
                                && value.ResultDigest != null,
                            cancellationToken
                        );
                    if (permission is null)
                        return false;
                    await ConversationReconciliationBinding.RequirePermissionAsync(
                        runtime,
                        db,
                        runtimeIdentity,
                        permission,
                        now,
                        cancellationToken
                    );
                    var source = await ConversationReconciliationBinding.SourceAsync(
                        runtime,
                        db,
                        execution,
                        record.Environment,
                        cancellationToken
                    );
                    if (
                        source.Source.Caller.ActorId != binding.ParticipantId
                        || ConversationReconciliationBinding.Digest(source.Original)
                            != permission.SourceDigest
                    )
                        return false;
                }
                else
                    await runtimeIdentity.RequireCurrentAsync(
                        runtime,
                        execution,
                        binding.ParticipantId,
                        cancellationToken
                    );
            }
            catch (Exception failure)
                when (failure
                        is ConversationNotAccessibleException
                            or ConversationStoppedException
                            or ConversationStateConflictException
                            or ConversationExecutionUnavailableException
                )
            {
                return false;
            }
        }
        var boundRole = RelationshipRoleCodec.FromDatabase(binding.ParticipantRole);
        if (
            !await db
                .RelationshipParticipants.AsNoTracking()
                .AnyAsync(
                    value =>
                        value.TenantId == record.TenantId
                        && value.RelationshipId == record.RelationshipId
                        && value.ParticipantId == binding.ParticipantId
                        && value.Status == "ACTIVE"
                        && value.Role == boundRole,
                    cancellationToken
                )
        )
            return false;

        var contact = await db
            .WhatsAppJourneyContacts.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == record.TenantId
                    && value.PhoneHmac == record.RecipientBindingDigest,
                cancellationToken
            );
        if (contact is null || contact.OptedInAt > now || contact.OptedOutAt is not null)
            return false;

        return contact.LastInboundAt <= now && now - contact.LastInboundAt <= ServiceWindow;
    }

    internal async Task<bool> AuthorizeRuntimeEgressAsync(
        ConversationOutboxRecord record,
        TimeProvider clock,
        CancellationToken cancellationToken
    )
    {
        if (
            !record.PayloadReference.StartsWith("runtime-reply:", StringComparison.Ordinal)
            && !record.PayloadReference.StartsWith("runtime-recovery:", StringComparison.Ordinal)
        )
            return await IsCurrentlyEligibleAsync(record, clock.GetUtcNow(), cancellationToken);
        var parts = record.PayloadReference.Split(':');
        if (
            record.RelationshipId is not { } relationshipId
            || parts.Length < 3
            || !Guid.TryParse(parts[1], out var executionId)
            || runtimeIdentity is null
        )
            return false;
        await using var runtime = await dbFactory.CreateDbContextAsync(cancellationToken);
        if (!runtime.Database.IsRelational())
            throw new ConversationExecutionUnavailableException();
        await using var transaction = await runtime.Database.BeginTransactionAsync(
            cancellationToken
        );
        await runtime.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT ai_runtime.lock_employment_dispatch({record.TenantId}, {relationshipId.ToString("D")})",
            cancellationToken
        );
        await runtime.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT execution_id FROM business.conversation_executions WHERE tenant_id = {record.TenantId} AND execution_id = {executionId} FOR UPDATE",
            cancellationToken
        );
        await runtime.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT outbox_id FROM business.conversation_outbox WHERE tenant_id = {record.TenantId} AND outbox_id = {record.OutboxId} FOR UPDATE",
            cancellationToken
        );
        if (
            !await runtime
                .ConversationOutbox.AsNoTracking()
                .AnyAsync(
                    value =>
                        value.TenantId == record.TenantId
                        && value.OutboxId == record.OutboxId
                        && value.State == "DISPATCHING"
                        && value.PayloadReference == record.PayloadReference
                        && value.PayloadDigest == record.PayloadDigest
                        && value.RecipientBindingDigest == record.RecipientBindingDigest
                        && value.RelationshipId == record.RelationshipId
                        && value.ConversationId == record.ConversationId
                        && value.AttemptNumber == record.AttemptNumber
                        && value.LeaseOwner == record.LeaseOwner
                        && value.LeaseExpiresAt > clock.GetUtcNow(),
                    cancellationToken
                )
        )
            return false;
        if (!Guid.TryParse(record.AggregateId, out var messageId))
            return false;
        await runtime.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT message_id FROM business.conversation_messages WHERE tenant_id = {record.TenantId} AND message_id = {messageId} FOR SHARE",
            cancellationToken
        );
        var message = await runtime
            .Messages.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == record.TenantId
                    && value.MessageId == messageId
                    && value.RelationshipId == relationshipId
                    && value.ConversationId == record.ConversationId
                    && value.Environment == record.Environment
                    && value.Channel == "WHATSAPP",
                cancellationToken
            );
        if (
            message is null
            || message.Sequence != record.Sequence
            || message.Actor is not ("PROFESSIONAL" or "SYSTEM")
            || message.ProcessingState is not ("COMPLETED" or "FAILED")
        )
            return false;
        try
        {
            using var material = JsonDocument.Parse(message.ContentJson);
            RuntimeEventStreamReader.ValidateUniqueProperties(material.RootElement);
            var content = material.RootElement.Deserialize<List<ConversationTextBlockV1>>(
                new JsonSerializerOptions(JsonSerializerDefaults.Web)
                {
                    UnmappedMemberHandling = System
                        .Text
                        .Json
                        .Serialization
                        .JsonUnmappedMemberHandling
                        .Disallow,
                    RespectRequiredConstructorParameters = true,
                }
            );
            if (
                content is not { Count: 1 }
                || content[0].SchemaVersion != "1.0"
                || content[0].BlockType != "TEXT"
                || string.IsNullOrWhiteSpace(content[0].Text)
                || content[0].Text.Length > 4096
                || Convert.ToHexStringLower(
                    SHA256.HashData(Encoding.UTF8.GetBytes(content[0].Text))
                ) != record.PayloadDigest
            )
                return false;
        }
        catch (JsonException)
        {
            return false;
        }
        await using var authority = new EmploymentRelationshipDbContext(
            new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                .UseNpgsql(runtime.Database.GetDbConnection())
                .Options
        );
        await authority.Database.UseTransactionAsync(
            transaction.GetDbTransaction(),
            cancellationToken
        );
        var execution = await runtime
            .Executions.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == record.TenantId
                    && value.ExecutionId == executionId
                    && value.RelationshipId == relationshipId,
                cancellationToken
            );
        if (execution is null)
            return false;
        ConversationReconciliationAuthority? permission = null;
        try
        {
            if (parts[0] == "runtime-recovery")
            {
                if (parts.Length != 4 || !Guid.TryParse(parts[3], out var authorityId))
                    return false;
                permission = await runtime
                    .ReconciliationAuthorities.AsNoTracking()
                    .SingleOrDefaultAsync(
                        value =>
                            value.TenantId == record.TenantId
                            && value.ExecutionId == executionId
                            && value.AuthorityId == authorityId
                            && value.ResultDigest != null,
                        cancellationToken
                    );
                if (permission is null)
                    return false;
                await ConversationReconciliationBinding.RequirePermissionAsync(
                    runtime,
                    authority,
                    runtimeIdentity,
                    permission,
                    clock.GetUtcNow(),
                    cancellationToken,
                    clock
                );
            }
            else
            {
                if (execution.RuntimeActorId is not { } actorId)
                    return false;
                await runtimeIdentity.RequireCurrentAsync(
                    runtime,
                    execution,
                    actorId,
                    cancellationToken
                );
                await runtime.Database.ExecuteSqlInterpolatedAsync(
                    $"SELECT relationship_id FROM business.employment_relationships WHERE tenant_id = {record.TenantId} AND relationship_id = {relationshipId} FOR SHARE",
                    cancellationToken
                );
                await runtime.Database.ExecuteSqlInterpolatedAsync(
                    $"SELECT binding_id FROM business.relationship_participants WHERE tenant_id = {record.TenantId} AND relationship_id = {relationshipId} AND participant_id = {actorId} FOR SHARE",
                    cancellationToken
                );
            }
            await runtime.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT contact_id FROM business.whatsapp_journey_contacts WHERE tenant_id = {record.TenantId} AND phone_hmac = {record.RecipientBindingDigest} FOR SHARE",
                cancellationToken
            );
            await runtime.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT binding_id FROM business.channel_bindings WHERE tenant_id = {record.TenantId} AND binding_id = {execution.OriginChannelBindingId} FOR SHARE",
                cancellationToken
            );
            if (
                await runtime
                    .Database.SqlQuery<int>(
                        $"SELECT 1 AS \"Value\" FROM constitutional.employment_dispatch_stops WHERE tenant_id = {record.TenantId} AND relationship_ref = {relationshipId.ToString("D")}"
                    )
                    .AnyAsync(cancellationToken)
                || !await IsCurrentlyEligibleAsync(
                    record,
                    clock.GetUtcNow(),
                    authority,
                    runtime,
                    cancellationToken
                )
                || permission is not null && permission.ExpiresAt <= clock.GetUtcNow()
            )
                return false;
            await transaction.CommitAsync(cancellationToken);
            return true;
        }
        catch (Exception failure)
            when (failure
                    is ConversationNotAccessibleException
                        or ConversationStoppedException
                        or ConversationStateConflictException
            )
        {
            return false;
        }
    }

    private async Task<bool> IsRecipientOptedOutAsync(
        Guid tenantId,
        string recipientBindingDigest,
        CancellationToken cancellationToken
    )
    {
        await using var db = await relationshipDbFactory.CreateDbContextAsync(cancellationToken);
        return await db.WhatsAppJourneyContacts.AnyAsync(
            contact =>
                contact.TenantId == tenantId
                && contact.PhoneHmac == recipientBindingDigest
                && contact.OptedOutAt != null,
            cancellationToken
        );
    }

    internal async Task<string?> ResolveRelationshipDestinationAsync(
        ConversationOutboxRecord record,
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        if (record.RelationshipId is null || record.PortalContextId is not null)
            throw new ConversationStateConflictException();
        if (!await IsCurrentlyEligibleAsync(record, now, cancellationToken))
            throw new WhatsAppCapabilityUnavailableException("RECIPIENT_ELIGIBILITY_REVOKED");
        await using var db = await relationshipDbFactory.CreateDbContextAsync(cancellationToken);
        var contact = await db
            .WhatsAppJourneyContacts.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == record.TenantId
                    && value.PhoneHmac == record.RecipientBindingDigest,
                cancellationToken
            );
        if (contact?.ProtectedDestination is null)
            return null;
        if (
            contact.DestinationVerifiedAt is not { } verifiedAt
            || verifiedAt > now
            || now - verifiedAt > ServiceWindow
        )
            throw new WhatsAppCapabilityUnavailableException("PHONE_DESTINATION_UNAVAILABLE");
        return contact.ProtectedDestination;
    }

    private static bool IsDigest(string value) =>
        value.Length == 64
        && value.All(character => character is >= '0' and <= '9' or >= 'a' and <= 'f');

    private static string Sha256(string value) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));

    private static ConversationOperationalSignal Signal(
        string environment,
        string category,
        string code,
        DateTimeOffset occurredAt
    ) =>
        new()
        {
            Environment = environment,
            Category = category,
            Code = code,
            OccurredAt = occurredAt,
        };
}
