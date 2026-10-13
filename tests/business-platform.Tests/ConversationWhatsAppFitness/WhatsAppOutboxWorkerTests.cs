using System.Security.Cryptography;
using System.Text;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppOutboxWorkerTests
{
    [Fact]
    public async Task WorkerDispatchesEligibleWorkInOrderAndReconcilesUnknownWithoutBlindResend()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await SeedEligibilityAsync(context, now);
        var outbox = context.Outbox();
        var aggregate = Guid.NewGuid().ToString("D");
        await QueueAsync(outbox, context, aggregate, 1, Guid.NewGuid(), now);
        await QueueAsync(outbox, context, aggregate, 2, Guid.NewGuid(), now);
        var provider = new ProviderStub();
        var worker = new WhatsAppOutboxWorker(outbox, provider, TimeProvider.System);

        Assert.True(await worker.ProcessOneAsync("worker-1", CancellationToken.None));
        Assert.True(await worker.ProcessOneAsync("worker-1", CancellationToken.None));
        Assert.Equal(2, provider.DispatchCount);
        Assert.Equal(0, provider.ReconcileCount);
        await using var db = context.Conversations.CreateDbContext();
        Assert.All(db.ConversationOutbox, value => Assert.Equal("DELIVERED", value.State));
    }

    [Fact]
    public async Task RelationshipClosureAndLegalHoldControlSevenYearDeliveryLifecycle()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var observedAt = DateTimeOffset.UtcNow.AddYears(-8);
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.DeliveryObservations.Add(
                new ConversationDeliveryObservation
                {
                    Environment = context.Options.Environment,
                    TenantId = context.TenantId,
                    RelationshipId = context.RelationshipId,
                    MessageId = Guid.NewGuid(),
                    Provider = "WHATSAPP",
                    ProviderEventIdentity = "status-1",
                    ProviderReferenceDigest = new string('a', 64),
                    DeliveryState = "DELIVERED",
                    ObservationDigest = new string('b', 64),
                    ObservedAt = observedAt,
                    RetainUntil = observedAt.AddYears(7),
                }
            );
            await db.SaveChangesAsync();
        }
        var service = context.Outbox();
        var closedAt = DateTimeOffset.UtcNow;
        await service.ApplyRelationshipClosureAsync(
            context.TenantId,
            context.RelationshipId,
            closedAt,
            CancellationToken.None
        );
        await service.SetDeliveryLegalHoldAsync(
            context.TenantId,
            context.RelationshipId,
            true,
            CancellationToken.None
        );
        Assert.Equal(
            0,
            await service.PurgeDeliveryObservationsAsync(
                closedAt.AddYears(8),
                CancellationToken.None
            )
        );
        await service.SetDeliveryLegalHoldAsync(
            context.TenantId,
            context.RelationshipId,
            false,
            CancellationToken.None
        );
        Assert.Equal(
            1,
            await service.PurgeDeliveryObservationsAsync(
                closedAt.AddYears(8),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task OutboxRecordsUnknownRejectedAndProviderStatusOutcomes()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await SeedEligibilityAsync(context, now);
        var outbox = context.Outbox();
        var messageId = Guid.NewGuid();
        var queued = await QueueAsync(
            outbox,
            context,
            messageId.ToString("D"),
            1,
            Guid.NewGuid(),
            now
        );
        Assert.NotNull(queued);

        var lease = await outbox.LeaseNextAsync("worker", now, CancellationToken.None);
        Assert.NotNull(lease);
        Assert.True(
            await outbox.BeginDispatchAsync(lease.OutboxId, "worker", now, CancellationToken.None)
        );
        await outbox.HeartbeatAsync(
            lease.OutboxId,
            "worker",
            now.AddSeconds(1),
            CancellationToken.None
        );
        await outbox.RecordResultAsync(
            lease.OutboxId,
            "worker",
            new WhatsAppDispatchObservation(
                "UNKNOWN",
                new string('d', 64),
                new string('e', 64),
                now.AddSeconds(2)
            ),
            CancellationToken.None
        );

        lease = await outbox.LeaseNextAsync("worker", now.AddMinutes(10), CancellationToken.None);
        Assert.NotNull(lease);
        Assert.True(lease.ReconciliationRequired);
        Assert.True(
            await outbox.BeginDispatchAsync(
                lease.OutboxId,
                "worker",
                now.AddMinutes(10),
                CancellationToken.None
            )
        );
        await outbox.RecordResultAsync(
            lease.OutboxId,
            "worker",
            new WhatsAppDispatchObservation(
                "REJECTED",
                new string('f', 64),
                new string('a', 64),
                now.AddMinutes(10)
            ),
            CancellationToken.None
        );

        var providerMessageId = "provider-message";
        var providerReference = Convert
            .ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(providerMessageId)))
            .ToLowerInvariant();
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.DeliveryObservations.Add(
                new ConversationDeliveryObservation
                {
                    Environment = context.Options.Environment,
                    TenantId = context.TenantId,
                    RelationshipId = context.RelationshipId,
                    MessageId = messageId,
                    Provider = "WHATSAPP",
                    ProviderEventIdentity = "submission",
                    ProviderReferenceDigest = providerReference,
                    DeliveryState = "PROVIDER_ACCEPTED",
                    ObservationDigest = new string('b', 64),
                    ObservedAt = now,
                    RetainUntil = now.AddYears(7),
                }
            );
            await db.SaveChangesAsync();
        }
        foreach (var state in new[] { "SENT", "DELIVERED", "READ", "FAILED" })
        {
            var status = new WhatsAppProviderStatusEvent(
                $"event-{state}",
                providerMessageId,
                state,
                now.AddMinutes(20),
                new string('c', 64)
            );
            Assert.True(await outbox.RecordProviderStatusAsync(status, CancellationToken.None));
            Assert.True(await outbox.RecordProviderStatusAsync(status, CancellationToken.None));
        }
        await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() =>
            outbox.RecordProviderStatusAsync(
                new WhatsAppProviderStatusEvent(
                    "event-SENT",
                    providerMessageId,
                    "SENT",
                    now,
                    new string('f', 64)
                ),
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<ArgumentException>(() =>
            outbox.RecordProviderStatusAsync(
                new WhatsAppProviderStatusEvent("", "", "UNKNOWN", now, "bad"),
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<ArgumentException>(() =>
            outbox.RecordProviderStatusAsync(
                new WhatsAppProviderStatusEvent(
                    "unsupported-status",
                    providerMessageId,
                    "UNKNOWN",
                    now,
                    new string('a', 64)
                ),
                CancellationToken.None
            )
        );
        Assert.False(
            await outbox.RecordProviderStatusAsync(
                new WhatsAppProviderStatusEvent(
                    "before-submission",
                    "unknown-provider-message",
                    "DELIVERED",
                    now,
                    new string('d', 64)
                ),
                CancellationToken.None
            )
        );

        var invalidResult = await QueueAsync(
            outbox,
            context,
            Guid.NewGuid().ToString("D"),
            1,
            Guid.NewGuid(),
            now.AddMinutes(30)
        );
        var invalidLease = await outbox.LeaseNextAsync(
            "invalid-worker",
            now.AddMinutes(30),
            CancellationToken.None
        );
        Assert.NotNull(invalidResult);
        Assert.NotNull(invalidLease);
        await Assert.ThrowsAsync<ArgumentException>(() =>
            outbox.RecordResultAsync(
                invalidLease.OutboxId,
                "invalid-worker",
                new WhatsAppDispatchObservation("DELIVERED", new string('a', 64), "bad", now),
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<ArgumentException>(() =>
            outbox.RecordResultAsync(
                invalidLease.OutboxId,
                "invalid-worker",
                new WhatsAppDispatchObservation("DELIVERED", "bad", new string('a', 64), now),
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<ArgumentException>(() =>
            outbox.RecordResultAsync(
                invalidLease.OutboxId,
                "invalid-worker",
                new WhatsAppDispatchObservation(
                    "UNSUPPORTED",
                    new string('a', 64),
                    new string('b', 64),
                    now
                ),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task OperationsSnapshotRaisesEveryTimeBoundAlert()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.ConversationOutbox.AddRange(
                OutboxRecord(context, "PENDING", now.AddMinutes(-3)),
                OutboxRecord(context, "UNRESOLVED", now.AddMinutes(-20)),
                OutboxRecord(context, "BLOCKED", now.AddMinutes(-31))
            );
            db.OperationalSignals.Add(
                new ConversationOperationalSignal
                {
                    Environment = context.Options.Environment,
                    Category = "PRIVACY",
                    Code = "PRIVACY_BOUNDARY_BREACH",
                    OccurredAt = now,
                }
            );
            await db.SaveChangesAsync();
        }
        var operations = new ConversationOperationsService(
            context.Conversations,
            Options.Create(context.Options)
        );

        var snapshot = await operations.EvaluateAsync(now, CancellationToken.None);

        Assert.Equal(4, snapshot.Alerts.Count);
        Assert.Contains(snapshot.Alerts, value => value.Code == "IMMEDIATE_FENCE_REQUIRED");
        Assert.Equal(1, snapshot.BlockedOutboxCount);
        Assert.Equal(1, snapshot.UnresolvedOutboxCount);
    }

    [Fact]
    public async Task EmptyOperationsAndDisabledProviderRemainFailClosed()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var operations = new ConversationOperationsService(
            context.Conversations,
            Options.Create(context.Options)
        );
        var snapshot = await operations.EvaluateAsync(
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );
        Assert.Empty(snapshot.Alerts);
        Assert.Null(snapshot.OldestQueuedAge);

        var provider = new DisabledWhatsAppProviderAdapter();
        var request = new WhatsAppProviderDispatchRequest(
            Guid.NewGuid(),
            context.Options.Environment,
            context.TenantId,
            context.RelationshipId,
            Guid.NewGuid(),
            1,
            Guid.NewGuid().ToString("D"),
            new string('a', 64),
            1
        );
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            provider.DispatchAsync(request, CancellationToken.None)
        );
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            provider.ReconcileAsync(request, CancellationToken.None)
        );
    }

    [Fact]
    public async Task WorkerReconcilesUnknownOutcomeWithoutBlindRedispatch()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await SeedEligibilityAsync(context, now);
        var outbox = context.Outbox();
        await QueueAsync(outbox, context, Guid.NewGuid().ToString("D"), 1, Guid.NewGuid(), now);
        var provider = new ProviderStub { DispatchState = "UNKNOWN" };
        var time = new MutableTimeProvider(now);
        var worker = new WhatsAppOutboxWorker(outbox, provider, time);

        Assert.True(await worker.ProcessOneAsync("worker", CancellationToken.None));
        time.Advance(TimeSpan.FromMinutes(10));
        Assert.True(await worker.ProcessOneAsync("worker", CancellationToken.None));

        Assert.Equal(1, provider.DispatchCount);
        Assert.Equal(1, provider.ReconcileCount);
    }

    [Fact]
    public async Task OutboxRejectsDisabledInvalidAndExpiredEligibilityBeforeDispatch()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        context.Options.Enabled = false;
        var disabled = context.Outbox();
        Assert.Null(
            await QueueAsync(
                disabled,
                context,
                Guid.NewGuid().ToString("D"),
                1,
                Guid.NewGuid(),
                now
            )
        );
        Assert.Null(await disabled.LeaseNextAsync("worker", now, CancellationToken.None));

        context.Options.Enabled = true;
        var service = context.Outbox();
        var baseEligibility = new WhatsAppOutboundEligibility(
            true,
            false,
            false,
            now,
            "CUSTOMER_REQUEST",
            new string('a', 64),
            null,
            null,
            null,
            null,
            false
        );
        foreach (
            var eligibility in new[]
            {
                baseEligibility with
                {
                    OptedIn = false,
                },
                baseEligibility with
                {
                    OptedOut = true,
                },
                baseEligibility with
                {
                    RelationshipStopped = true,
                },
                baseEligibility with
                {
                    Purpose = "",
                },
                baseEligibility with
                {
                    RecipientBindingDigest = "",
                },
                baseEligibility with
                {
                    LastInboundAt = now.AddDays(-2),
                },
            }
        )
        {
            Assert.Null(
                await service.QueueAsync(
                    context.TenantId,
                    context.RelationshipId,
                    Guid.NewGuid(),
                    1,
                    Guid.NewGuid().ToString("D"),
                    Guid.NewGuid(),
                    new string('b', 64),
                    Guid.NewGuid().ToString("D"),
                    eligibility,
                    now,
                    CancellationToken.None
                )
            );
        }
        await Assert.ThrowsAsync<ArgumentException>(() =>
            service.QueueAsync(
                context.TenantId,
                context.RelationshipId,
                Guid.NewGuid(),
                1,
                Guid.NewGuid().ToString("D"),
                Guid.NewGuid(),
                "bad",
                Guid.NewGuid().ToString("D"),
                baseEligibility,
                now,
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<ArgumentException>(() =>
            service.LeaseNextAsync("", now, CancellationToken.None)
        );
        Assert.Null(await service.LeaseNextAsync("worker", now, CancellationToken.None));

        await SeedEligibilityAsync(context, now);
        var queued = await QueueAsync(
            service,
            context,
            Guid.NewGuid().ToString("D"),
            1,
            Guid.NewGuid(),
            now
        );
        var lease = await service.LeaseNextAsync("worker", now, CancellationToken.None);
        Assert.NotNull(queued);
        Assert.NotNull(lease);
        Assert.False(
            await service.BeginDispatchAsync(
                lease.OutboxId,
                "worker",
                now.AddMinutes(2),
                CancellationToken.None
            )
        );
    }

    private static ConversationOutboxRecord OutboxRecord(
        Wc120FitnessContext context,
        string state,
        DateTimeOffset occurredAt
    ) =>
        new()
        {
            Environment = context.Options.Environment,
            TenantId = context.TenantId,
            RelationshipId = context.RelationshipId,
            ConversationId = Guid.NewGuid(),
            AggregateId = Guid.NewGuid().ToString("D"),
            OperationFamily = "WHATSAPP_OUTBOUND",
            IdempotencyKey = Guid.NewGuid(),
            PayloadDigest = new string('a', 64),
            PayloadReference = Guid.NewGuid().ToString("D"),
            Purpose = "CUSTOMER_REQUEST",
            RecipientBindingDigest = new string('b', 64),
            State = state,
            NextAttemptAt = occurredAt,
            CreatedAt = occurredAt,
            UpdatedAt = occurredAt,
        };

    private static async Task SeedEligibilityAsync(Wc120FitnessContext context, DateTimeOffset now)
    {
        await using var db = context.Relationships.CreateDbContext();
        db.ChannelBindings.Add(
            new ChannelBinding
            {
                TenantId = context.TenantId,
                RelationshipId = context.RelationshipId,
                ParticipantId = context.ParticipantId,
                ParticipantRole = "EMPLOYER",
                Channel = "WHATSAPP",
                ExternalSubjectHash = new string('c', 64),
                ConversationId = Guid.NewGuid().ToString("D"),
                AssuranceLevel = "AAL1_CHANNEL",
                Status = "ACTIVE",
            }
        );
        db.WhatsAppJourneyContacts.Add(
            new WhatsAppJourneyContact
            {
                TenantId = context.TenantId,
                PhoneHmac = new string('c', 64),
                OptedInAt = now.AddDays(-1),
                LastInboundAt = now,
            }
        );
        await db.SaveChangesAsync();
    }

    private static Task<ConversationOutboxRecord?> QueueAsync(
        WhatsAppOutboxService outbox,
        Wc120FitnessContext context,
        string aggregate,
        long sequence,
        Guid idempotencyKey,
        DateTimeOffset now
    ) =>
        outbox.QueueAsync(
            context.TenantId,
            context.RelationshipId,
            Guid.NewGuid(),
            sequence,
            aggregate,
            idempotencyKey,
            new string((char)('a' + sequence), 64),
            Guid.NewGuid().ToString("D"),
            new(
                true,
                false,
                false,
                now,
                "CUSTOMER_REQUEST",
                new string('c', 64),
                null,
                null,
                null,
                null,
                false
            ),
            now,
            CancellationToken.None
        );

    private sealed class ProviderStub : IWhatsAppProviderAdapter
    {
        public int DispatchCount { get; private set; }
        public int ReconcileCount { get; private set; }
        public string DispatchState { get; init; } = "DELIVERED";

        public Task<WhatsAppDispatchObservation> DispatchAsync(
            WhatsAppProviderDispatchRequest request,
            CancellationToken cancellationToken
        )
        {
            DispatchCount++;
            return Task.FromResult(
                new WhatsAppDispatchObservation(
                    DispatchState,
                    new string('d', 64),
                    new string((char)('d' + request.Sequence), 64),
                    DateTimeOffset.UtcNow
                )
            );
        }

        public Task<WhatsAppDispatchObservation> ReconcileAsync(
            WhatsAppProviderDispatchRequest request,
            CancellationToken cancellationToken
        )
        {
            ReconcileCount++;
            return Task.FromResult(
                new WhatsAppDispatchObservation(
                    "DELIVERED",
                    new string('d', 64),
                    new string('f', 64),
                    DateTimeOffset.UtcNow
                )
            );
        }
    }

    private sealed class MutableTimeProvider(DateTimeOffset now) : TimeProvider
    {
        private DateTimeOffset _now = now;

        public override DateTimeOffset GetUtcNow() => _now;

        public void Advance(TimeSpan elapsed) => _now += elapsed;
    }
}
