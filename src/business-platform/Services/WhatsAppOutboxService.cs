// Implements: architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md §10.2, §13
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using System.Data;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
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
    Guid RelationshipId,
    Guid ConversationId,
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
);

public sealed class WhatsAppOutboxService(
    IDbContextFactory<ConversationStoreDbContext> dbFactory,
    IDbContextFactory<EmploymentRelationshipDbContext> relationshipDbFactory,
    IOptions<Wc120ConversationOptions> conversationOptions,
    IOptionsMonitor<WhatsAppJourneyOptions> whatsAppOptions,
    ConversationStopFence stopFence
)
{
    private static readonly TimeSpan ServiceWindow = TimeSpan.FromHours(24);
    private static readonly TimeSpan LeaseDuration = TimeSpan.FromSeconds(60);
    private readonly Wc120ConversationOptions _conversationOptions = conversationOptions.Value;
    private WhatsAppJourneyOptions WhatsAppOptions => whatsAppOptions.CurrentValue;

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
            || string.IsNullOrWhiteSpace(eligibility.Purpose)
            || string.IsNullOrWhiteSpace(eligibility.RecipientBindingDigest)
        )
            return null;

        var insideServiceWindow =
            eligibility.LastInboundAt.HasValue
            && now - eligibility.LastInboundAt.Value <= ServiceWindow
            && now >= eligibility.LastInboundAt.Value;
        var approvedTemplate =
            !string.IsNullOrWhiteSpace(eligibility.TemplateName)
            && !string.IsNullOrWhiteSpace(eligibility.TemplateVersion)
            && !string.IsNullOrWhiteSpace(eligibility.TemplateLocale)
            && !string.IsNullOrWhiteSpace(eligibility.TemplateCategory)
            && eligibility.TemplateApproved;
        if (!insideServiceWindow && !approvedTemplate)
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

    public async Task<WhatsAppOutboxLease?> LeaseNextAsync(
        string workerId,
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        if (!_conversationOptions.Enabled || !WhatsAppOptions.DispatchEnabled)
            return null;
        if (string.IsNullOrWhiteSpace(workerId))
            throw new ArgumentException("Worker identity is required.", nameof(workerId));

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.Serializable,
            cancellationToken
        );
        var record = await db
            .ConversationOutbox.Where(value =>
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
                    && earlier.AggregateId == value.AggregateId
                    && earlier.Sequence < value.Sequence
                    && earlier.State != "DELIVERED"
                    && earlier.State != "BLOCKED"
                )
            )
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
        await db.SaveChangesAsync(cancellationToken);
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
        var record = await OwnedLeaseAsync(db, outboxId, workerId, cancellationToken);
        if (
            record.LeaseExpiresAt <= now
            || await stopFence.IsLatchedAsync(
                record.TenantId,
                record.RelationshipId,
                cancellationToken
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
            return false;
        }

        record.State = "DISPATCHING";
        record.UpdatedAt = now;
        await db.SaveChangesAsync(cancellationToken);
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
        var record = await OwnedLeaseAsync(db, outboxId, workerId, cancellationToken);
        record.HeartbeatAt = now;
        record.LeaseExpiresAt = now.Add(LeaseDuration);
        record.UpdatedAt = now;
        await db.SaveChangesAsync(cancellationToken);
    }

    public async Task RecordResultAsync(
        Guid outboxId,
        string workerId,
        WhatsAppDispatchObservation observation,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
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
            "UNKNOWN" => "UNRESOLVED",
            "REJECTED" => "BLOCKED",
            _ => throw new ArgumentException("Dispatch state is unsupported.", nameof(observation)),
        };
        record.BlockedReason = observation.State == "REJECTED" ? "PROVIDER_REJECTED" : null;
        record.LeaseOwner = null;
        record.LeaseExpiresAt = null;
        record.HeartbeatAt = null;
        record.NextAttemptAt =
            record.State == "UNRESOLVED"
                ? observation.ObservedAt.Add(Backoff(record.AttemptNumber))
                : observation.ObservedAt;
        record.UpdatedAt = observation.ObservedAt;
        if (record.AttemptNumber >= 12 && record.State != "DELIVERED")
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
                    MessageId = messageId,
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
    }

    public async Task<bool> RecordProviderStatusAsync(
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

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
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
            catch (DbUpdateException)
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
                    MessageId = source.MessageId,
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

    public async Task ApplyRelationshipClosureAsync(
        Guid tenantId,
        Guid relationshipId,
        DateTimeOffset closedAt,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var minimumRetention = closedAt.AddYears(7);
        var observations = await db
            .DeliveryObservations.Where(value =>
                value.Environment == _conversationOptions.Environment
                && value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.RetainUntil < minimumRetention
            )
            .ToListAsync(cancellationToken);
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
        var due = await db
            .DeliveryObservations.Where(value =>
                value.Environment == _conversationOptions.Environment
                && !value.LegalHold
                && value.RetainUntil <= now
            )
            .ToListAsync(cancellationToken);
        db.DeliveryObservations.RemoveRange(due);
        await db.SaveChangesAsync(cancellationToken);
        return due.Count;
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

    private async Task<bool> IsCurrentlyEligibleAsync(
        ConversationOutboxRecord record,
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        await using var db = await relationshipDbFactory.CreateDbContextAsync(cancellationToken);
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
        )
            return false;

        var binding = await db
            .ChannelBindings.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == record.TenantId
                    && value.RelationshipId == record.RelationshipId
                    && value.Channel == "WHATSAPP"
                    && value.ExternalSubjectHash == record.RecipientBindingDigest
                    && value.Status == "ACTIVE",
                cancellationToken
            );
        if (binding is null)
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

        var insideServiceWindow =
            contact.LastInboundAt <= now && now - contact.LastInboundAt <= ServiceWindow;
        if (insideServiceWindow)
            return true;

        var templateIdentity = string.Join(
            ':',
            record.TemplateName,
            record.TemplateVersion,
            record.TemplateLocale,
            record.TemplateCategory
        );
        return WhatsAppOptions.ApprovedTemplates.Contains(templateIdentity, StringComparer.Ordinal);
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
