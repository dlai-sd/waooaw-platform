using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppOutboxWorkerTests
{
    [Fact]
    public async Task CustomerWorkerRejectsPartialOwnerWiringBeforeLeasingOrProviderWork()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await SeedEligibilityAsync(context, now);
        var outbox = context.Outbox();
        await QueueAsync(outbox, context, Guid.NewGuid().ToString("D"), 1, Guid.NewGuid(), now);
        var gate = new OperationsGate(true);
        var directory = new WhatsAppOutboxWorkDirectory(
            context.Conversations, new WhatsAppTenantExecutionScope(gate, TimeProvider.System),
            gate, Options.Create(context.Options),
            new StaticOptionsMonitor<WhatsAppJourneyOptions>(new() { DispatchEnabled = true }), TimeProvider.System);
        var provider = new ProviderStub();
        var worker = new WhatsAppOutboxWorker(outbox, provider, TimeProvider.System, directory);
        var denied = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            worker.ProcessOneAsync("worker", CancellationToken.None, preferCustomer: true));
        Assert.Equal("CUSTOMER_WORKER_OWNER_UNAVAILABLE", denied.ReasonCode);
        Assert.Equal(0, provider.DispatchCount);
        Assert.Equal(0, provider.ReconcileCount);
        await using var db = context.Conversations.CreateDbContext();
        Assert.Equal("PENDING", (await db.ConversationOutbox.SingleAsync()).State);
        Assert.Empty(await db.DeliveryObservations.ToListAsync());
    }

    [Fact]
    public async Task ReplacedConversationBlocksQueuedRelationshipReplyBeforeDispatch()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await SeedEligibilityAsync(context, now);
        var outbox = context.Outbox();
        await QueueAsync(outbox, context, Guid.NewGuid().ToString("D"), 1, Guid.NewGuid(), now);
        var lease = await outbox.LeaseNextAsync("worker", now, CancellationToken.None);
        Assert.NotNull(lease);
        await using (var db = context.Relationships.CreateDbContext())
        {
            (await db.ChannelBindings.SingleAsync()).ConversationId = Guid.NewGuid().ToString("D");
            await db.SaveChangesAsync();
        }

        Assert.False(
            await outbox.BeginDispatchAsync(lease.OutboxId, "worker", now, CancellationToken.None)
        );
        await using var saved = context.Conversations.CreateDbContext();
        var record = await saved.ConversationOutbox.SingleAsync();
        Assert.Equal("BLOCKED", record.State);
        Assert.Equal("CURRENT_ELIGIBILITY_DENIED", record.BlockedReason);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task AmbiguousActiveBindingsBlockQueuedReplyBeforeDispatch(bool otherRelationship)
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await SeedEligibilityAsync(context, now);
        var outbox = context.Outbox();
        await QueueAsync(outbox, context, Guid.NewGuid().ToString("D"), 1, Guid.NewGuid(), now);
        var lease = await outbox.LeaseNextAsync("worker", now, CancellationToken.None);
        Assert.NotNull(lease);
        await using (var db = context.Relationships.CreateDbContext())
        {
            var relationshipId = otherRelationship ? Guid.NewGuid() : context.RelationshipId;
            if (otherRelationship)
                db.EmploymentRelationships.Add(
                    new EmploymentRelationship
                    {
                        TenantId = context.TenantId,
                        RelationshipId = relationshipId,
                        State = EmploymentRelationshipState.Active,
                    }
                );
            db.ChannelBindings.Add(
                new ChannelBinding
                {
                    TenantId = context.TenantId,
                    RelationshipId = relationshipId,
                    ParticipantId = Guid.NewGuid(),
                    ParticipantRole = "EMPLOYER",
                    Channel = "WHATSAPP",
                    ExternalSubjectHash = new string('c', 64),
                    ConversationId = context.WhatsAppConversationId.ToString("D"),
                    AssuranceLevel = "AAL1_CHANNEL",
                    Status = "ACTIVE",
                }
            );
            await db.SaveChangesAsync();
        }

        Assert.False(
            await outbox.BeginDispatchAsync(lease.OutboxId, "worker", now, CancellationToken.None)
        );
        await using var saved = context.Conversations.CreateDbContext();
        var record = await saved.ConversationOutbox.SingleAsync();
        Assert.Equal("BLOCKED", record.State);
        Assert.Equal("CURRENT_ELIGIBILITY_DENIED", record.BlockedReason);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task CapabilityDenialDistinguishesUnsentWorkFromUnknownPriorSubmission(
        bool reconciliation
    )
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await SeedEligibilityAsync(context, now);
        var outbox = context.Outbox();
        await QueueAsync(outbox, context, Guid.NewGuid().ToString("D"), 1, Guid.NewGuid(), now);
        var provider = new ProviderStub { DispatchState = "UNKNOWN" };
        var time = new MutableTimeProvider(now);
        var worker = new WhatsAppOutboxWorker(outbox, provider, time);
        if (reconciliation)
        {
            Assert.True(await worker.ProcessOneAsync("worker", CancellationToken.None));
            time.Advance(TimeSpan.FromMinutes(10));
        }
        provider.DenyCapability = true;

        Assert.True(await worker.ProcessOneAsync("worker", CancellationToken.None));

        await using var db = context.Conversations.CreateDbContext();
        var record = Assert.Single(db.ConversationOutbox);
        Assert.Equal(reconciliation ? "UNRESOLVED" : "BLOCKED", record.State);
        Assert.Equal(reconciliation ? null : "DISPATCH_AUTHORITY_DENIED", record.BlockedReason);
        Assert.Contains(
            db.DeliveryObservations,
            observation => observation.DeliveryState == (reconciliation ? "UNKNOWN" : "NOT_SENT")
        );
        Assert.DoesNotContain(
            db.DeliveryObservations,
            observation => observation.DeliveryState == "REJECTED"
        );
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task WorkerDispatchesEligibleWorkInOrderAndReconcilesUnknownWithoutBlindResend(bool preferCustomer)
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

        Assert.True(await worker.ProcessOneAsync("worker-1", CancellationToken.None, preferCustomer));
        Assert.True(await worker.ProcessOneAsync("worker-1", CancellationToken.None, !preferCustomer));
        Assert.Equal(2, provider.DispatchCount);
        Assert.Equal(0, provider.ReconcileCount);
        await using var db = context.Conversations.CreateDbContext();
        Assert.All(db.ConversationOutbox, value => Assert.Equal("DELIVERED", value.State));
    }

    [Fact]
    public async Task RelationshipClosureAndLegalHoldControlSevenYearDeliveryLifecycle()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var closedAt = DateTimeOffset.UtcNow;
        var observedAt = closedAt.AddYears(-8);
        var longerRetention = closedAt.AddYears(10);
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
            db.DeliveryObservations.Add(
                new ConversationDeliveryObservation
                {
                    Environment = context.Options.Environment,
                    TenantId = context.TenantId,
                    RelationshipId = context.RelationshipId,
                    MessageId = Guid.NewGuid(),
                    Provider = "WHATSAPP",
                    ProviderEventIdentity = "status-2",
                    ProviderReferenceDigest = new string('a', 64),
                    DeliveryState = "DELIVERED",
                    ObservationDigest = new string('b', 64),
                    ObservedAt = observedAt,
                    RetainUntil = longerRetention,
                }
            );
            await db.SaveChangesAsync();
        }
        var service = context.Outbox();
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
        await using var saved = context.Conversations.CreateDbContext();
        Assert.Equal(longerRetention, (await saved.DeliveryObservations.SingleAsync()).RetainUntil);
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
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            outbox.RecordProviderStatusAsync(
                new WhatsAppProviderStatusEvent(
                    "sender-bound-without-routing-owner", providerMessageId, "DELIVERED",
                    now.AddMinutes(20), new string('e', 64))
                {
                    SenderBindingDigest = new string('a', 64),
                },
                CancellationToken.None));
        await using (var db = context.Conversations.CreateDbContext())
            Assert.False(await db.ProviderEventClaims.AnyAsync(
                value => value.EventIdentity == "sender-bound-without-routing-owner"));
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
        Assert.Equal(
            now.AddMinutes(-1),
            Assert
                .Single(snapshot.Alerts, value => value.Code == "OUTBOUND_QUEUE_AGE_BREACH")
                .TriggeredAt
        );
        Assert.Equal(
            now.AddMinutes(-5),
            Assert
                .Single(snapshot.Alerts, value => value.Code == "OUTBOUND_RECONCILIATION_BREACH")
                .TriggeredAt
        );
        Assert.Equal(
            now.AddMinutes(-1),
            Assert
                .Single(snapshot.Alerts, value => value.Code == "DEAD_LETTER_AGE_BREACH")
                .TriggeredAt
        );
        var later = await operations.EvaluateAsync(now.AddMinutes(2), CancellationToken.None);
        Assert.Equal(
            snapshot.Alerts.ToDictionary(value => value.Code, value => value.TriggeredAt),
            later.Alerts.ToDictionary(value => value.Code, value => value.TriggeredAt)
        );
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task OperationsWorkerEmitsHeartbeatOnlyForActiveEvaluation(bool active)
    {
        var context = await Wc120FitnessContext.CreateAsync();
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.OperationalSignals.Add(
                new ConversationOperationalSignal
                {
                    Environment = context.Options.Environment,
                    Category = "SAFETY",
                    Code = "RESTORE_EGRESS_VIOLATION",
                    OccurredAt = DateTimeOffset.UtcNow,
                }
            );
            await db.SaveChangesAsync();
        }
        await using var services = new ServiceCollection()
            .AddSingleton(
                new ConversationOperationsService(
                    context.Conversations,
                    Options.Create(context.Options)
                )
            )
            .BuildServiceProvider();
        var gate = new OperationsGate(active);
        var logger = new OperationsLogger(
            active ? "WhatsApp operations alert:" : "evaluation inactive:"
        );
        var worker = new WhatsAppOperationsHostedService(
            services.GetRequiredService<IServiceScopeFactory>(),
            new WhatsAppTenantExecutionScope(gate, TimeProvider.System),
            gate,
            TimeProvider.System,
            logger
        );
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        await worker.StartAsync(timeout.Token);
        try
        {
            await logger.Expected.Task.WaitAsync(timeout.Token);
        }
        finally
        {
            await worker.StopAsync(timeout.Token);
            worker.Dispose();
        }
        var messages = logger.Messages.ToArray();
        Assert.Equal(active, messages.Any(value => value.Contains("evaluation heartbeat:")));
        Assert.Equal(active, messages.Any(value => value.Contains("IMMEDIATE_FENCE_REQUIRED")));
        Assert.Equal(!active, messages.Any(value => value.Contains("evaluation inactive:")));
        var observations = messages.Where(value => value.Contains("WC134_OBSERVATION=")).ToArray();
        Assert.Equal(active, observations.Length > 0);
        foreach (var message in observations)
        {
            using var json = JsonDocument.Parse(message.Split("WC134_OBSERVATION=", 2)[1]);
            var root = json.RootElement;
            Assert.Equal(8, root.EnumerateObject().Count());
            Assert.Equal("1.0", root.GetProperty("schemaVersion").GetString());
            Assert.Equal("test", root.GetProperty("environment").GetString());
            Assert.Equal(
                WhatsAppGuestTrafficEventIdentity.Activation("original"),
                root.GetProperty("activationDigest").GetString()
            );
            Assert.Equal("sha256:" + new string('a', 64), root.GetProperty("releaseDigest").GetString());
            Assert.Equal("sha256:" + new string('b', 64), root.GetProperty("configurationDigest").GetString());
            Assert.True(root.GetProperty("observedAt").GetDateTimeOffset() <= DateTimeOffset.UtcNow);
        }
    }

    [Fact]
    public async Task OperationsWorkerReportsDatabaseFailureWithoutSuccessHeartbeatOrDetails()
    {
        await using var services = new ServiceCollection()
            .AddSingleton(
                new ConversationOperationsService(
                    new FailingOperationsFactory(),
                    Options.Create(new Wc120ConversationOptions { Environment = "demo" })
                )
            )
            .BuildServiceProvider();
        var gate = new OperationsGate(true);
        var logger = new OperationsLogger("database unavailable;");
        var worker = new WhatsAppOperationsHostedService(
            services.GetRequiredService<IServiceScopeFactory>(),
            new WhatsAppTenantExecutionScope(gate, TimeProvider.System),
            gate,
            TimeProvider.System,
            logger
        );
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        await worker.StartAsync(timeout.Token);
        try
        {
            await logger.Expected.Task.WaitAsync(timeout.Token);
        }
        finally
        {
            await worker.StopAsync(timeout.Token);
            worker.Dispose();
        }
        Assert.DoesNotContain(logger.Messages, value => value.Contains("evaluation heartbeat:"));
        Assert.DoesNotContain(logger.Messages, value => value.Contains("private-database-detail"));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task OperationsWorkerDoesNotEmitHeartbeatAfterAuthorityChanges(bool wrongEnvironment)
    {
        var context = await Wc120FitnessContext.CreateAsync();
        await using var services = new ServiceCollection()
            .AddSingleton(
                new ConversationOperationsService(
                    context.Conversations,
                    Options.Create(context.Options)
                )
            )
            .BuildServiceProvider();
        var gate = new OperationsGate(
            true, changeAuthority: !wrongEnvironment, wrongEnvironment: wrongEnvironment
        );
        var logger = new OperationsLogger("OPERATIONS_AUTHORITY_CHANGED");
        var worker = new WhatsAppOperationsHostedService(
            services.GetRequiredService<IServiceScopeFactory>(),
            new WhatsAppTenantExecutionScope(gate, TimeProvider.System),
            gate,
            TimeProvider.System,
            logger
        );
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        await worker.StartAsync(timeout.Token);
        try
        {
            await logger.Expected.Task.WaitAsync(timeout.Token);
        }
        finally
        {
            await worker.StopAsync(timeout.Token);
            worker.Dispose();
        }
        Assert.DoesNotContain(logger.Messages, value => value.Contains("evaluation heartbeat:"));
    }

    private sealed class FailingOperationsFactory : IDbContextFactory<ConversationStoreDbContext>
    {
        public ConversationStoreDbContext CreateDbContext() =>
            throw new Npgsql.NpgsqlException("private-database-detail");

        public Task<ConversationStoreDbContext> CreateDbContextAsync(
            CancellationToken cancellationToken = default
        ) => throw new Npgsql.NpgsqlException("private-database-detail");
    }

    private sealed class OperationsGate(
        bool active, bool changeAuthority = false, bool wrongEnvironment = false
    )
        : IWhatsAppCapabilityGate
    {
        private readonly Guid _tenantId = Guid.NewGuid();
        private int _authorityReads;

        public WhatsAppCapabilityState Evaluate(DateTimeOffset now) =>
            active ? new("ACTIVE", "AUTHORIZED") : new("READY_INACTIVE", "ACTIVATION_REQUIRED");

        public WhatsAppActivationAuthority RequireActive(DateTimeOffset now) =>
            active
                ? new WhatsAppActivationAuthority
                {
                    TenantId = _tenantId,
                    Environment = wrongEnvironment ? "unrelated" : "test",
                    ReleaseDigest = "sha256:" + new string('a', 64),
                    ConfigurationDigest = "sha256:" + new string('b', 64),
                    ActivationReference =
                        changeAuthority && Interlocked.Increment(ref _authorityReads) >= 3
                            ? "changed"
                            : "original",
                }
                : throw new WhatsAppCapabilityUnavailableException("ACTIVATION_REQUIRED");

        public void RequireRecipient(
            Guid tenantId,
            string recipientBindingDigest,
            DateTimeOffset now
        ) => throw new NotSupportedException();
    }

    private sealed class OperationsLogger(string expected)
        : ILogger<WhatsAppOperationsHostedService>
    {
        public System.Collections.Concurrent.ConcurrentQueue<string> Messages { get; } = new();
        public TaskCompletionSource Expected { get; } =
            new(TaskCreationOptions.RunContinuationsAsynchronously);

        public IDisposable? BeginScope<TState>(TState state)
            where TState : notnull => null;

        public bool IsEnabled(LogLevel logLevel) => true;

        public void Log<TState>(
            LogLevel logLevel,
            EventId eventId,
            TState state,
            Exception? exception,
            Func<TState, Exception?, string> formatter
        )
        {
            var message = formatter(state, exception);
            Messages.Enqueue(message);
            if (message.Contains(expected, StringComparison.Ordinal))
                Expected.TrySetResult();
        }
    }

    [Theory]
    [InlineData("PRIVACY_BOUNDARY_BREACH")]
    [InlineData("ISOLATION_BOUNDARY_BREACH")]
    [InlineData("PRODUCTION_DARK_VIOLATION")]
    [InlineData("RESTORE_EGRESS_VIOLATION")]
    [InlineData("STOP_HARD_CEILING_BREACH")]
    public async Task OpenCriticalSignalRequiresImmediateFenceOnlyInItsEnvironment(string code)
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.OperationalSignals.AddRange(
                new ConversationOperationalSignal
                {
                    Environment = context.Options.Environment,
                    Category = "SAFETY",
                    Code = code,
                    OccurredAt = now.AddMinutes(-2),
                },
                new ConversationOperationalSignal
                {
                    Environment = "other-environment",
                    Category = "SAFETY",
                    Code = code,
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
        var alert = Assert.Single(snapshot.Alerts);
        Assert.Equal("IMMEDIATE_FENCE_REQUIRED", alert.Code);
        Assert.Equal("PAGE", alert.Severity);
        Assert.Equal(TimeSpan.FromMinutes(5), alert.ResponseDeadline);
        Assert.Equal(now.AddMinutes(-2), alert.TriggeredAt);
        Assert.Equal(1, snapshot.OpenSignalCount);

        await using (var db = context.Conversations.CreateDbContext())
        {
            var signal = await db.OperationalSignals.SingleAsync(value =>
                value.Environment == context.Options.Environment
            );
            signal.State = "RESOLVED";
            signal.ResolvedAt = now;
            await db.SaveChangesAsync();
        }
        snapshot = await operations.EvaluateAsync(now, CancellationToken.None);
        Assert.Empty(snapshot.Alerts);
        Assert.Equal(0, snapshot.OpenSignalCount);
    }

    [Theory]
    [InlineData("OPEN", "EMERGENCY_STOP", "EVIDENCE_RECONCILIATION_PENDING", true)]
    [InlineData("ACKNOWLEDGED", "EMERGENCY_STOP", "EVIDENCE_RECONCILIATION_PENDING", false)]
    [InlineData("RESOLVED", "EMERGENCY_STOP", "EVIDENCE_RECONCILIATION_PENDING", false)]
    [InlineData("OPEN", "OTHER", "EVIDENCE_RECONCILIATION_PENDING", false)]
    [InlineData("OPEN", "EMERGENCY_STOP", "OTHER", false)]
    public async Task StopEvidenceReconciliationAlertIsScopedAndDoesNotRestartDeadline(
        string state,
        string category,
        string code,
        bool expected
    )
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        var occurredAt = now.AddMinutes(-2);
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.OperationalSignals.AddRange(
                new ConversationOperationalSignal
                {
                    Environment = context.Options.Environment,
                    Category = category,
                    Code = code,
                    State = state,
                    OccurredAt = occurredAt,
                },
                new ConversationOperationalSignal
                {
                    Environment = "other-environment",
                    Category = "EMERGENCY_STOP",
                    Code = "EVIDENCE_RECONCILIATION_PENDING",
                    OccurredAt = now.AddMinutes(-10),
                }
            );
            await db.SaveChangesAsync();
        }
        var operations = new ConversationOperationsService(
            context.Conversations,
            Options.Create(context.Options)
        );
        var snapshot = await operations.EvaluateAsync(now, CancellationToken.None);
        var later = await operations.EvaluateAsync(now.AddMinutes(1), CancellationToken.None);
        if (expected)
        {
            var alert = Assert.Single(snapshot.Alerts);
            Assert.Equal("STOP_EVIDENCE_RECONCILIATION_REQUIRED", alert.Code);
            Assert.Equal("PAGE", alert.Severity);
            Assert.Equal(TimeSpan.FromMinutes(5), alert.ResponseDeadline);
            Assert.Equal(occurredAt, alert.TriggeredAt);
            Assert.Equal(alert, Assert.Single(later.Alerts));
        }
        else
        {
            Assert.Empty(snapshot.Alerts);
            Assert.Empty(later.Alerts);
        }
    }

    [Theory]
    [InlineData("PENDING", 120, null)]
    [InlineData("PENDING", 121, "OUTBOUND_QUEUE_AGE_BREACH")]
    [InlineData("LEASED", 120, null)]
    [InlineData("LEASED", 121, "OUTBOUND_QUEUE_AGE_BREACH")]
    [InlineData("UNRESOLVED", 900, null)]
    [InlineData("UNRESOLVED", 901, "OUTBOUND_RECONCILIATION_BREACH")]
    [InlineData("BLOCKED", 900, null)]
    [InlineData("BLOCKED", 901, "DEAD_LETTER_ACTION_REQUIRED")]
    [InlineData("BLOCKED", 1800, "DEAD_LETTER_ACTION_REQUIRED")]
    [InlineData("BLOCKED", 1801, "DEAD_LETTER_AGE_BREACH")]
    public async Task OperationsThresholdsMatchRunbook(
        string state,
        int elapsedSeconds,
        string? expectedCode
    )
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.ConversationOutbox.Add(
                OutboxRecord(context, state, now.AddSeconds(-elapsedSeconds))
            );
            await db.SaveChangesAsync();
        }
        var operations = new ConversationOperationsService(
            context.Conversations,
            Options.Create(context.Options)
        );
        var snapshot = await operations.EvaluateAsync(now, CancellationToken.None);
        if (expectedCode is null)
            Assert.Empty(snapshot.Alerts);
        else
            Assert.Equal(expectedCode, Assert.Single(snapshot.Alerts).Code);
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
    public async Task ExpiredDispatchingLeaseReconcilesInsteadOfRedispatching()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await SeedEligibilityAsync(context, now);
        var outbox = context.Outbox();
        await QueueAsync(outbox, context, Guid.NewGuid().ToString("D"), 1, Guid.NewGuid(), now);

        var lease = await outbox.LeaseNextAsync("crashed-worker", now, CancellationToken.None);
        Assert.NotNull(lease);
        Assert.True(
            await outbox.BeginDispatchAsync(
                lease.OutboxId,
                "crashed-worker",
                now,
                CancellationToken.None
            )
        );

        var provider = new ProviderStub();
        var time = new MutableTimeProvider(now.AddMinutes(2));
        var worker = new WhatsAppOutboxWorker(outbox, provider, time);

        Assert.True(await worker.ProcessOneAsync("recovery-worker", CancellationToken.None));

        Assert.Equal(0, provider.DispatchCount);
        Assert.Equal(1, provider.ReconcileCount);
        await using var db = context.Conversations.CreateDbContext();
        Assert.Equal("DELIVERED", Assert.Single(db.ConversationOutbox).State);
    }

    [Fact]
    public async Task LostDispatchResponseIsReconciledWithoutBlindRedispatch()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await SeedEligibilityAsync(context, now);
        var outbox = context.Outbox();
        await QueueAsync(outbox, context, Guid.NewGuid().ToString("D"), 1, Guid.NewGuid(), now);

        var provider = new ProviderStub { LoseDispatchResponse = true };
        var time = new MutableTimeProvider(now);
        var worker = new WhatsAppOutboxWorker(outbox, provider, time);

        Assert.True(await worker.ProcessOneAsync("worker", CancellationToken.None));
        time.Advance(TimeSpan.FromMinutes(10));
        Assert.True(await worker.ProcessOneAsync("worker", CancellationToken.None));

        Assert.Equal(1, provider.DispatchCount);
        Assert.Equal(1, provider.ReconcileCount);
        await using var db = context.Conversations.CreateDbContext();
        Assert.Equal("DELIVERED", Assert.Single(db.ConversationOutbox).State);
    }

    [Fact]
    public async Task EarlyProviderStatusCanBeReconciledAfterSubmissionEvidenceArrives()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await SeedEligibilityAsync(context, now);
        var outbox = context.Outbox();
        var queued = await QueueAsync(
            outbox,
            context,
            Guid.NewGuid().ToString("D"),
            1,
            Guid.NewGuid(),
            now
        );
        Assert.NotNull(queued);
        var providerMessageId = "provider-message-before-submission";
        var providerReferenceDigest = Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes(providerMessageId))
        );
        var earlyStatus = new WhatsAppProviderStatusEvent(
            "early-delivery-event",
            providerMessageId,
            "DELIVERED",
            now.AddSeconds(1),
            new string('a', 64)
        );

        Assert.False(await outbox.RecordProviderStatusAsync(earlyStatus, CancellationToken.None));

        var lease = await outbox.LeaseNextAsync(
            "worker",
            now.AddSeconds(2),
            CancellationToken.None
        );
        Assert.NotNull(lease);
        Assert.True(
            await outbox.BeginDispatchAsync(
                lease.OutboxId,
                "worker",
                now.AddSeconds(2),
                CancellationToken.None
            )
        );
        await outbox.RecordResultAsync(
            lease.OutboxId,
            "worker",
            new WhatsAppDispatchObservation(
                "PROVIDER_ACCEPTED",
                providerReferenceDigest,
                new string('b', 64),
                now.AddSeconds(3)
            ),
            CancellationToken.None
        );

        Assert.True(await outbox.RecordProviderStatusAsync(earlyStatus, CancellationToken.None));
        Assert.True(await outbox.RecordProviderStatusAsync(earlyStatus, CancellationToken.None));
        await using var db = context.Conversations.CreateDbContext();
        Assert.Contains(
            db.DeliveryObservations,
            observation =>
                observation.ProviderEventIdentity == earlyStatus.EventIdentity
                && observation.ProviderReferenceDigest == providerReferenceDigest
                && observation.DeliveryState == "DELIVERED"
        );
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
                    Purpose = "CUSTOMER_ALERT",
                },
                baseEligibility with
                {
                    TemplateName = "approved-template",
                    TemplateVersion = "1",
                    TemplateLocale = "en_IN",
                    TemplateCategory = "UTILITY",
                    TemplateApproved = true,
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

    private static Task SeedEligibilityAsync(Wc120FitnessContext context, DateTimeOffset now) =>
        context.SeedWhatsAppEligibilityAsync(new string('c', 64), now);

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
            context.WhatsAppConversationId,
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
        public bool DenyCapability { get; set; }
        public bool LoseDispatchResponse { get; init; }

        public Task<WhatsAppDispatchObservation> DispatchAsync(
            WhatsAppProviderDispatchRequest request,
            CancellationToken cancellationToken
        )
        {
            DispatchCount++;
            if (DenyCapability)
                throw new WhatsAppCapabilityUnavailableException("AUTHORITY_DENIED");
            if (LoseDispatchResponse)
                throw new HttpRequestException("Synthetic lost provider response");
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
            if (DenyCapability)
                throw new WhatsAppCapabilityUnavailableException("AUTHORITY_DENIED");
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
