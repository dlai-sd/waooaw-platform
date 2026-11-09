// Implements: work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md WC134-R001-R006
// constitutional_basis: C-023, C-026, C-039, C-059, C-063

using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.TestHost;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Tests.Conversation;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppGuestSessionPostgresTests
{
    [Fact]
    public async Task ConsentHistoryMigrationIsReplaySafeAndTenantScoped()
    {
        await using var postgres = new PostgreSqlBuilder("postgres:16-alpine").Build();
        await postgres.StartAsync();
        await using var owner = new NpgsqlConnection(postgres.GetConnectionString());
        await owner.OpenAsync();
        await using (
            var setup = new NpgsqlCommand(
                """
                CREATE ROLE business_app LOGIN PASSWORD 'synthetic-app-password' NOBYPASSRLS;
                CREATE SCHEMA business;
                GRANT USAGE ON SCHEMA business TO business_app;
                CREATE TABLE business.whatsapp_guest_sessions (
                    tenant_id uuid NOT NULL,
                    binding_digest char(64) NOT NULL,
                    PRIMARY KEY (tenant_id, binding_digest)
                );
                """,
                owner
            )
        )
            await setup.ExecuteNonQueryAsync();
        var tenant = Guid.NewGuid();
        var otherTenant = Guid.NewGuid();
        var digest = new string('a', 64);
        await using (
            var seed = new NpgsqlCommand(
                """
                INSERT INTO business.whatsapp_guest_sessions VALUES (@tenant, @digest);
                """,
                owner
            )
        )
        {
            seed.Parameters.AddWithValue("tenant", tenant);
            seed.Parameters.AddWithValue("digest", digest);
            await seed.ExecuteNonQueryAsync();
        }
        var migration = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/80-wc134-guest-consent-history.sql"
            )
        );
        await using (var apply = new NpgsqlCommand(migration, owner))
            await apply.ExecuteNonQueryAsync();
        var appConnection = new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
        {
            Username = "business_app",
            Password = "synthetic-app-password",
            Options = $"-c app.current_tenant_id={tenant:D}",
        };
        await using (var app = new NpgsqlConnection(appConnection.ConnectionString))
        {
            await app.OpenAsync();
            await using var insert = new NpgsqlCommand(
                """
                INSERT INTO business.whatsapp_guest_consent_history
                    (tenant_id, binding_digest, evidence_id, notice_version, notice_message_id,
                     notice_queued_at, consent_message_id, consent_at)
                VALUES (@tenant, @digest, @evidence, 'previous', @notice, now(), 'yes', now())
                """,
                app
            );
            insert.Parameters.AddWithValue("tenant", tenant);
            insert.Parameters.AddWithValue("digest", digest);
            insert.Parameters.AddWithValue("evidence", Guid.NewGuid());
            insert.Parameters.AddWithValue("notice", Guid.NewGuid());
            await insert.ExecuteNonQueryAsync();
            await using var update = new NpgsqlCommand(
                "UPDATE business.whatsapp_guest_consent_history SET notice_version = 'altered'",
                app
            );
            var failure = await Assert.ThrowsAsync<PostgresException>(() =>
                update.ExecuteNonQueryAsync()
            );
            Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, failure.SqlState);
        }
        await using (var replay = new NpgsqlCommand(migration, owner))
            await replay.ExecuteNonQueryAsync();
        appConnection.Options = $"-c app.current_tenant_id={otherTenant:D}";
        await using (var other = new NpgsqlConnection(appConnection.ConnectionString))
        {
            await other.OpenAsync();
            await using var count = new NpgsqlCommand(
                "SELECT count(*) FROM business.whatsapp_guest_consent_history",
                other
            );
            Assert.Equal(0L, await count.ExecuteScalarAsync());
        }
        appConnection.Options = $"-c app.current_tenant_id={tenant:D}";
        await using (var original = new NpgsqlConnection(appConnection.ConnectionString))
        {
            await original.OpenAsync();
            await using var count = new NpgsqlCommand(
                "SELECT count(*) FROM business.whatsapp_guest_consent_history",
                original
            );
            Assert.Equal(1L, await count.ExecuteScalarAsync());
        }
    }

    [Theory]
    [InlineData(true, false)]
    [InlineData(false, false)]
    [InlineData(true, true)]
    [InlineData(false, true)]
    public async Task StaleConsentRequiresFreshNoticeAndAffirmationWithoutStoringText(
        bool previouslyConsented,
        bool stopDuringEvidence
    )
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var factory = new Factory(postgres.GetConnectionString());
        var now = new DateTimeOffset(2026, 11, 7, 9, 0, 0, TimeSpan.Zero);
        var clock = new Clock(now);
        var tenant = Guid.NewGuid();
        var digest = new string('a', 64);
        var oldEvidence = Guid.NewGuid();
        var oldNotice = Guid.NewGuid();
        await using (var db = factory.CreateDbContext())
        {
            await db.Database.EnsureCreatedAsync();
            await db.Database.ExecuteSqlRawAsync(
                """
                CREATE TABLE business.whatsapp_journey_contacts (
                    tenant_id uuid NOT NULL,
                    phone_hmac varchar(64) NOT NULL,
                    opted_out_at timestamptz NULL
                )
                """
            );
            db.Add(
                new WhatsAppGuestSession
                {
                    TenantId = tenant,
                    BindingDigest = digest,
                    EvidenceId = Guid.NewGuid(),
                    AdmittedAt = now.AddDays(-1),
                    FirstObservedAt = now.AddDays(-1),
                    LastInboundAt = now.AddDays(-1),
                    ServiceConsentNoticeQueuedAt = now.AddDays(-1),
                    ServiceConsentNoticeMessageId = oldNotice,
                    ServiceConsentNoticeVersion = "previous",
                    ServiceConsentAt = previouslyConsented ? now.AddHours(-23) : null,
                    ServiceConsentMessageId = previouslyConsented ? "old-consent" : null,
                    ServiceConsentEvidenceId = previouslyConsented ? oldEvidence : null,
                }
            );
            await db.SaveChangesAsync();
        }
        var gate = new Gate(tenant, digest) { Allowed = true };
        var settings = Options.Create(
            new Wc120ConversationOptions { Enabled = true, Environment = "demo" }
        );
        var interactions = new PortalInteractionService(
            factory,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            ),
            new Catalog()
        );
        var outbox = new WhatsAppOutboxService(
            factory,
            factory,
            settings,
            new StaticOptionsMonitor<WhatsAppJourneyOptions>(new() { DispatchEnabled = true }),
            new ConversationStopFence(factory, settings)
        );
        var evidence = new Evidence();
        var recognition = new RecognitionProbe();
        var service = new WhatsAppGuestSessionService(
            factory,
            evidence,
            gate,
            interactions,
            outbox,
            new WhatsAppGuestTrafficBudget(factory, gate, clock),
            clock,
            recognition
        );
        var proof = new VerifiedPhoneIdentityProof(
            previouslyConsented ? "old-consent" : "stale-consent",
            digest,
            "private customer question",
            null,
            "whatsapp-provider-callback",
            "AAL1_CHANNEL",
            now,
            now,
            now.AddMinutes(5),
            Guid.NewGuid()
        )
        {
            Environment = "demo",
        };
        var result = await service.ReceiveAsync(proof, CancellationToken.None, "+15555550123");
        Assert.Equal("CONSENT_REQUIRED", result.Status);
        Assert.Equal(WhatsAppGuestConsent.Notice, result.Reply);
        Assert.Equal(0, evidence.Consents);
        Assert.Equal(0, recognition.Calls);
        await using (var verify = factory.CreateDbContext())
        {
            var guest = await verify.Set<WhatsAppGuestSession>().SingleAsync();
            Assert.Null(guest.ServiceConsentEvidenceId);
            Assert.Equal(WhatsAppGuestConsent.NoticeVersion, guest.ServiceConsentNoticeVersion);
            Assert.NotEqual(oldNotice, guest.ServiceConsentNoticeMessageId);
            var history = await verify.Set<WhatsAppGuestConsentHistory>().ToListAsync();
            if (previouslyConsented)
            {
                var previous = Assert.Single(history);
                Assert.Equal(oldEvidence, previous.EvidenceId);
                Assert.Equal(oldNotice, previous.NoticeMessageId);
                Assert.Equal("previous", previous.NoticeVersion);
            }
            else
                Assert.Empty(history);
            var messages = await verify.PortalInteractionMessages.ToListAsync();
            Assert.Single(messages);
            Assert.DoesNotContain("private customer question", messages[0].ContentJson);
        }

        var sameSecond = proof with { MessageId = "same-second-yes", Text = "YES" };
        var premature = await service.ReceiveAsync(sameSecond, CancellationToken.None);
        Assert.Equal("CONSENT_REQUIRED", premature.Status);
        Assert.Equal(0, evidence.Consents);

        clock.Advance(TimeSpan.FromSeconds(2));
        var affirmative = proof with
        {
            MessageId = "new-consent",
            Text = "YES",
            SentAt = clock.GetUtcNow(),
            VerifiedAt = clock.GetUtcNow(),
            ExpiresAt = clock.GetUtcNow().AddMinutes(5),
        };
        if (stopDuringEvidence)
        {
            evidence.BeforeConsent = async () =>
            {
                var stop = affirmative with { MessageId = "renewal-stop", Text = "STOP" };
                var stopped = await service.ReceiveAsync(stop, CancellationToken.None);
                Assert.Equal("STOPPED", stopped.Status);
            };
        }
        var accepted = await service.ReceiveAsync(affirmative, CancellationToken.None);
        Assert.Equal(stopDuringEvidence ? "STOPPED" : "CONSENT_RECORDED", accepted.Status);
        Assert.Equal(1, evidence.Consents);
        await using var after = factory.CreateDbContext();
        var renewed = await after.Set<WhatsAppGuestSession>().SingleAsync();
        if (stopDuringEvidence)
        {
            Assert.NotNull(renewed.StoppedAt);
            Assert.False(WhatsAppGuestConsent.IsCurrent(renewed));
            Assert.Null(renewed.ServiceConsentEvidenceId);
            Assert.Equal(
                previouslyConsented ? 1 : 0,
                await after.Set<WhatsAppGuestConsentHistory>().CountAsync()
            );
            return;
        }
        Assert.True(WhatsAppGuestConsent.IsCurrent(renewed));
        Assert.NotEqual(oldEvidence, renewed.ServiceConsentEvidenceId);
        Assert.Equal("new-consent", renewed.ServiceConsentMessageId);
    }

    private sealed class RecognitionProbe : IWhatsAppRegistrationRecognition
    {
        public int Calls { get; private set; }

        public Task<bool> IsVerifiedRegistrationAsync(string phoneNumber, CancellationToken ct)
        {
            Calls++;
            return Task.FromResult(true);
        }
    }

    [Fact]
    public async Task ConcurrentNoticesPreserveTheirReferenceAndRejectAnEarlierAffirmation()
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var factory = new Factory(postgres.GetConnectionString());
        var now = new DateTimeOffset(2026, 11, 7, 9, 0, 0, TimeSpan.Zero);
        var clock = new Clock(now);
        var tenant = Guid.NewGuid();
        var digest = new string('a', 64);
        await using (var db = factory.CreateDbContext())
        {
            await db.Database.EnsureCreatedAsync();
            await db.Database.ExecuteSqlRawAsync(
                """
                CREATE TABLE business.whatsapp_journey_contacts (
                    tenant_id uuid NOT NULL,
                    phone_hmac varchar(64) NOT NULL,
                    opted_out_at timestamptz NULL
                )
                """
            );
            db.Add(
                new WhatsAppGuestSession
                {
                    TenantId = tenant,
                    BindingDigest = digest,
                    EvidenceId = Guid.NewGuid(),
                    AdmittedAt = now.AddMinutes(-1),
                    FirstObservedAt = now.AddMinutes(-1),
                    LastInboundAt = now.AddMinutes(-1),
                }
            );
            await db.SaveChangesAsync();
        }
        var interactions = new DelayedFirstGuestNotice(
            new PortalInteractionService(
                factory,
                new ConversationCursorCodec(
                    Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
                ),
                new Catalog()
            )
        );
        var gate = new Gate(tenant, digest) { Allowed = true };
        var settings = Options.Create(
            new Wc120ConversationOptions { Enabled = true, Environment = "demo" }
        );
        var outbox = new WhatsAppOutboxService(
            factory,
            factory,
            settings,
            new StaticOptionsMonitor<WhatsAppJourneyOptions>(new() { DispatchEnabled = true }),
            new ConversationStopFence(factory, settings)
        );
        var evidence = new Evidence();
        var service = new WhatsAppGuestSessionService(
            factory,
            evidence,
            gate,
            interactions,
            outbox,
            new WhatsAppGuestTrafficBudget(factory, gate, clock),
            clock
        );
        VerifiedPhoneIdentityProof Proof(string id) =>
            new(
                id,
                digest,
                "Hello",
                null,
                "whatsapp-provider-callback",
                "AAL1_CHANNEL",
                now,
                now,
                now.AddMinutes(5),
                Guid.NewGuid()
            )
            {
                Environment = "demo",
            };
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        var first = service.ReceiveAsync(Proof("first-notice"), deadline.Token);
        try
        {
            await interactions.FirstCreated.Task.WaitAsync(deadline.Token);
            Assert.Equal(
                "CONSENT_REQUIRED",
                (await service.ReceiveAsync(Proof("second-notice"), deadline.Token)).Status
            );
            Guid? secondNoticeId;
            await using (var db = factory.CreateDbContext())
            {
                var guest = await db.Set<WhatsAppGuestSession>().SingleAsync(deadline.Token);
                secondNoticeId = guest.ServiceConsentNoticeMessageId;
                Assert.NotNull(secondNoticeId);
            }
            interactions.ReleaseFirst.TrySetResult();
            Assert.Equal("CONSENT_REQUIRED", (await first).Status);
            await using var verify = factory.CreateDbContext();
            var saved = await verify.Set<WhatsAppGuestSession>().SingleAsync(deadline.Token);
            Assert.Equal(secondNoticeId, saved.ServiceConsentNoticeMessageId);
            Assert.Null(saved.ServiceConsentAt);
            Assert.Equal(2, await verify.ConversationOutbox.CountAsync(deadline.Token));
            var oldAffirmation = Proof("old-affirmation") with
            {
                Text = "YES",
                SentAt = now.AddSeconds(-1),
                VerifiedAt = now.AddSeconds(1),
            };
            Assert.Equal(
                "CONSENT_REQUIRED",
                (await service.ReceiveAsync(oldAffirmation, deadline.Token)).Status
            );
            Assert.Equal(0, evidence.Consents);
            clock.Advance(TimeSpan.FromSeconds(2));
            var newAffirmation = Proof("new-affirmation") with
            {
                Text = "YES",
                SentAt = clock.GetUtcNow(),
                VerifiedAt = clock.GetUtcNow(),
            };
            Assert.Equal(
                "CONSENT_RECORDED",
                (await service.ReceiveAsync(newAffirmation, deadline.Token)).Status
            );
            Assert.Equal(1, evidence.Consents);
        }
        finally
        {
            interactions.ReleaseFirst.TrySetResult();
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task GuestStopDoesNotWaitForEvidenceAndLateEvidenceCannotRestoreAdmissionOrConsent(
        bool consenting
    )
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var factory = new Factory(postgres.GetConnectionString());
        var now = DateTimeOffset.UtcNow;
        var clock = new Clock(now);
        var tenant = Guid.NewGuid();
        var digest = new string('a', 64);
        await using (var db = factory.CreateDbContext())
        {
            await db.Database.EnsureCreatedAsync();
            if (consenting)
                db.Add(
                    new WhatsAppGuestSession
                    {
                        TenantId = tenant,
                        BindingDigest = digest,
                        EvidenceId = Guid.NewGuid(),
                        AdmittedAt = now.AddSeconds(-1),
                        FirstObservedAt = now.AddSeconds(-1),
                        LastInboundAt = now.AddSeconds(-1),
                        ServiceConsentNoticeQueuedAt = now.AddSeconds(-1),
                        ServiceConsentNoticeMessageId = Guid.NewGuid(),
                        ServiceConsentNoticeVersion = WhatsAppGuestConsent.NoticeVersion,
                    }
                );
            await db.SaveChangesAsync();
        }
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        async Task PauseEvidence()
        {
            entered.TrySetResult();
            await release.Task.WaitAsync(deadline.Token);
        }
        var evidence = new Evidence
        {
            BeforeAdmission = consenting ? null : PauseEvidence,
            BeforeConsent = consenting ? PauseEvidence : null,
        };
        var gate = new Gate(tenant, digest) { Allowed = true };
        var settings = Options.Create(
            new Wc120ConversationOptions { Enabled = true, Environment = "demo" }
        );
        var outbox = new WhatsAppOutboxService(
            factory,
            factory,
            settings,
            new StaticOptionsMonitor<WhatsAppJourneyOptions>(new() { DispatchEnabled = true }),
            new ConversationStopFence(factory, settings)
        );
        var service = new WhatsAppGuestSessionService(
            factory,
            evidence,
            gate,
            new PortalInteractionService(
                factory,
                new ConversationCursorCodec(
                    Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
                ),
                new Catalog()
            ),
            outbox,
            new WhatsAppGuestTrafficBudget(factory, gate, clock),
            clock
        );
        VerifiedPhoneIdentityProof Proof(string id, string text) =>
            new(
                id,
                digest,
                text,
                null,
                "whatsapp-provider-callback",
                "AAL1_CHANNEL",
                now,
                now,
                now.AddMinutes(5),
                Guid.NewGuid()
            )
            {
                Environment = "demo",
            };
        var pending = service.ReceiveAsync(
            Proof("evidence-paused", consenting ? "YES" : "Hello"),
            deadline.Token
        );
        try
        {
            await entered.Task.WaitAsync(deadline.Token);
            var stopped = await service.ReceiveAsync(Proof("stop", "STOP"), deadline.Token);
            Assert.Equal("STOPPED", stopped.Status);
            Assert.False(pending.IsCompleted);
        }
        finally
        {
            release.TrySetResult();
        }
        Assert.Equal("STOPPED", (await pending).Status);
        await using var verify = factory.CreateDbContext();
        var guest = await verify.Set<WhatsAppGuestSession>().SingleAsync();
        Assert.NotNull(guest.StoppedAt);
        Assert.Null(guest.ServiceConsentAt);
        if (!consenting)
        {
            Assert.Null(guest.EvidenceId);
            Assert.Null(guest.AdmittedAt);
        }
        Assert.Empty(await verify.PortalInteractionMessages.ToListAsync());
        Assert.Empty(await verify.ConversationOutbox.ToListAsync());
    }

    [Theory]
    [InlineData("send")]
    [InlineData("queue")]
    [InlineData("list")]
    public async Task GuestOwnerAndQueueRecheckStopAfterWaitingForTheSenderLock(string operation)
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var factory = new Factory(postgres.GetConnectionString());
        var now = DateTimeOffset.UtcNow;
        var guest = new WhatsAppGuestSession
        {
            TenantId = Guid.NewGuid(),
            BindingDigest = new string('a', 64),
            EvidenceId = Guid.NewGuid(),
            AdmittedAt = now,
            ServiceConsentAt = now,
            ServiceConsentEvidenceId = Guid.NewGuid(),
            ServiceConsentNoticeVersion = WhatsAppGuestConsent.NoticeVersion,
        };
        var context = new PortalInteractionContext
        {
            TenantId = guest.TenantId,
            ParticipantId = guest.ParticipantId,
        };
        var guide = new PortalInteractionMessage
        {
            TenantId = guest.TenantId,
            ParticipantId = guest.ParticipantId,
            ContextId = context.ContextId,
            Actor = "GUIDE",
            Sequence = 1,
        };
        await using (var db = factory.CreateDbContext())
        {
            await db.Database.EnsureCreatedAsync();
            db.Add(guest);
            db.Add(context);
            db.Add(guide);
            await db.SaveChangesAsync();
        }
        var interactions = new PortalInteractionService(
            factory,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            ),
            new Catalog()
        );
        var settings = Options.Create(
            new Wc120ConversationOptions { Enabled = true, Environment = "demo" }
        );
        var outbox = new WhatsAppOutboxService(
            factory,
            factory,
            settings,
            new StaticOptionsMonitor<WhatsAppJourneyOptions>(new() { DispatchEnabled = true }),
            new ConversationStopFence(factory, settings)
        );
        await using var stopping = factory.CreateDbContext();
        await using var transaction = await stopping.Database.BeginTransactionAsync();
        var lockKey = WhatsAppGuestSession.LockKey(guest.TenantId, guest.BindingDigest);
        await stopping.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_advisory_xact_lock(hashtextextended({lockKey}, 0))"
        );
        (await stopping.Set<WhatsAppGuestSession>().SingleAsync()).StoppedAt = now;
        await stopping.SaveChangesAsync();
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        Task pending = operation switch
        {
            "queue" => outbox.QueueGuestDiscoveryAsync(
                guest,
                new PortalInteractionMessageV1(
                    "1.0",
                    guide.MessageId,
                    1,
                    "GUIDE",
                    [new("1.0", "TEXT", "stale reply", "en")],
                    [],
                    "MARKETPLACE",
                    null,
                    now
                ),
                now,
                deadline.Token
            ),
            "list" => interactions.ListGuestDiscoveryAsync(
                guest.TenantId,
                guest.ParticipantId,
                null,
                20,
                deadline.Token
            ),
            "send" => interactions.SendGuestDiscoveryAsync(
                guest.TenantId,
                guest.ParticipantId,
                Guid.NewGuid(),
                new SendPortalInteractionMessageRequestV1(
                    "1.0",
                    Guid.NewGuid(),
                    [new("1.0", "TEXT", "do not process", "en")],
                    "en",
                    "MARKETPLACE"
                ),
                deadline.Token
            ),
            _ => throw new ArgumentOutOfRangeException(nameof(operation)),
        };
        await Task.Delay(100, deadline.Token);
        Assert.False(pending.IsCompleted);
        await transaction.CommitAsync(deadline.Token);
        await Assert.ThrowsAsync<ConversationStoppedException>(() => pending);
        await using var verify = factory.CreateDbContext();
        Assert.Single(await verify.PortalInteractionMessages.ToListAsync());
        Assert.Empty(await verify.PortalInteractionIdempotencyOutcomes.ToListAsync());
        Assert.Empty(await verify.ConversationOutbox.ToListAsync());
    }

    [Fact]
    public async Task ConcurrentRelationshipDestinationRefreshCannotOverwriteNewerVerifiedRoute()
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var factory = new Factory(postgres.GetConnectionString());
        var relationships = (IDbContextFactory<EmploymentRelationshipDbContext>)factory;
        var tenant = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;
        var digest = new string('a', 64);
        var contact = new WhatsAppJourneyContact
        {
            TenantId = tenant,
            PhoneHmac = digest,
            OptedInAt = now,
            LastInboundAt = now,
        };
        await using (var owner = relationships.CreateDbContext())
        {
            await owner.Database.EnsureCreatedAsync();
            owner.WhatsAppJourneyContacts.Add(contact);
            await owner.SaveChangesAsync();
        }
        await using var first = relationships.CreateDbContext();
        await using var stale = relationships.CreateDbContext();
        var firstContact = await first.WhatsAppJourneyContacts.SingleAsync();
        var staleContact = await stale.WhatsAppJourneyContacts.SingleAsync();
        firstContact.ProtectedDestination = WhatsAppPhoneDestinationProtector.Protect(
            Credentials.PhoneSubjectKey,
            "+15550000001",
            digest
        );
        firstContact.DestinationVerifiedAt = now.AddSeconds(1);
        await first.SaveChangesAsync();
        staleContact.ProtectedDestination = WhatsAppPhoneDestinationProtector.Protect(
            Credentials.PhoneSubjectKey,
            "+15550000001",
            digest
        );
        staleContact.DestinationVerifiedAt = now;
        await Assert.ThrowsAsync<DbUpdateConcurrencyException>(() => stale.SaveChangesAsync());
        await using var verify = relationships.CreateDbContext();
        var current = await verify.WhatsAppJourneyContacts.SingleAsync();
        Assert.Equal(firstContact.ProtectedDestination, current.ProtectedDestination);
        Assert.Equal(
            firstContact.DestinationVerifiedAt!.Value.ToUnixTimeMilliseconds(),
            current.DestinationVerifiedAt!.Value.ToUnixTimeMilliseconds()
        );
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task SignedAccountLinkConfirmationRetriesWithoutPersistingCodeAndHonorsClosedHoursAndStop(
        bool relationshipBound
    )
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var factory = new Factory(postgres.GetConnectionString());
        await using (var db = factory.CreateDbContext())
        {
            await db.Database.EnsureCreatedAsync();
            await db.Database.ExecuteSqlRawAsync(
                """
                ALTER TABLE business.conversation_messages
                    ADD CONSTRAINT conversation_messages_delivery_check
                    CHECK (delivery_state IN ('ACCEPTED', 'FAILED', 'UNRESOLVED')),
                    ADD CONSTRAINT conversation_messages_completion_check
                    CHECK (completion_reason IS NULL OR completion_reason IN
                        ('COMPLETE', 'PARTIAL_FAILURE', 'CANCELLED', 'EMERGENCY_STOPPED'));
                ALTER TABLE business.conversation_executions
                    ADD CONSTRAINT conversation_executions_completion_check
                    CHECK (completion_reason IS NULL OR completion_reason IN
                        ('COMPLETE', 'PARTIAL_FAILURE', 'CANCELLED', 'EMERGENCY_STOPPED'));
                ALTER TABLE business.conversation_events
                    ADD CONSTRAINT conversation_events_type_check
                    CHECK (event_type IN ('message.accepted', 'processing.started', 'response.delta',
                        'card.upserted', 'message.completed', 'message.failed', 'stream.cancelled',
                        'stop.applied', 'reconciliation.required', 'heartbeat'));
                """
            );
        }
        await using (
            var db = ((IDbContextFactory<EmploymentRelationshipDbContext>)factory).CreateDbContext()
        )
        {
            await db.Database.ExecuteSqlRawAsync(db.Database.GenerateCreateScript());
            var destinationMigration = await File.ReadAllTextAsync(
                RepositoryPaths.Resolve(
                    "infrastructure/postgres/init/76-wc134-whatsapp-relationship-destinations.sql"
                )
            );
            await db.Database.ExecuteSqlRawAsync(destinationMigration);
            await db.Database.ExecuteSqlRawAsync(destinationMigration);
        }
        var clock = new Clock(new DateTimeOffset(2026, 11, 6, 15, 29, 0, TimeSpan.Zero));
        var tenant = Guid.NewGuid();
        var digest = Convert.ToHexStringLower(
            HMACSHA256.HashData(
                Encoding.UTF8.GetBytes(Credentials.PhoneSubjectKey),
                Encoding.UTF8.GetBytes("+15550000001")
            )
        );
        var gate = new Gate(tenant, digest)
        {
            Allowed = true,
            PublicAdmissionEnabled = relationshipBound,
        };
        var channel = new WhatsAppJourneyOptions
        {
            WebhookSecret = Credentials.Secret,
            TenantTokenKey = new string('k', 32),
            DispatchEnabled = true,
            CallbackAcceptanceEnabled = true,
        };
        static string Hash(string value) =>
            Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
        var settings = new Wc120ConversationOptions
        {
            Enabled = true,
            Environment = "demo",
            AppBindingDigest = Hash("1001"),
            WabaBindingDigest = Hash("1002"),
            RecipientBindingDigest = Hash("1003"),
            PolicyVersion = "synthetic-policy-1",
            InstitutionalPolicyVersion = "synthetic-institutional-1",
            InteractionPolicyVersion = "synthetic-interaction-1",
            ChannelRenderingPolicyVersion = "synthetic-rendering-1",
        };
        var outbox = new WhatsAppOutboxService(
            factory,
            factory,
            Options.Create(settings),
            new StaticOptionsMonitor<WhatsAppJourneyOptions>(channel),
            new ConversationStopFence(factory, Options.Create(settings))
        );
        var evidence = new Evidence();
        var employment = new ConversationalEmploymentService();
        var references = new RecoverableReferences(
            new ConversationContextProfileService(
                factory,
                factory,
                employment,
                Options.Create(settings)
            )
        );
        var outbound = new ConversationOutboundContributionService(
            factory,
            references,
            new ConversationStopFence(factory, Options.Create(settings)),
            Options.Create(settings)
        );
        var runtime = new ConversationExecutionGatewayStub();
        var canonical = new ConversationService(
            factory,
            factory,
            new ConversationConstitutionalGatewayStub(),
            runtime,
            new OperationalMandateResolverStub(),
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('k', 32) })
            ),
            conversationOptions: Options.Create(settings)
        );
        var confirmations = new Confirmations { Fail = true };
        var guests = new WhatsAppGuestSessionService(
            factory,
            evidence,
            gate,
            new PortalInteractionService(
                factory,
                new ConversationCursorCodec(
                    Options.Create(new ConversationCursorOptions { HmacKey = new string('k', 32) })
                ),
                new Catalog()
            ),
            outbox,
            new WhatsAppGuestTrafficBudget(factory, gate, clock),
            clock,
            accountLinkConfirmation: confirmations
        );
        var journey = new WhatsAppJourneyService(
            factory,
            evidence,
            Options.Create(channel),
            conversationDbFactory: factory,
            conversationOptions: Options.Create(settings),
            outboxService: outbox,
            capabilityGate: gate,
            webhookCredentials: new Credentials(digest, clock.GetUtcNow()),
            guestSessions: guests,
            conversationService: canonical,
            outboundContributions: outbound,
            engagementWorkspace: new CustomerEngagementWorkspaceService(
                factory,
                new EphemeralDataProtectionProvider(),
                new ConversationConstitutionalGatewayStub()
            ),
            clock: clock
        );
        string Envelope(string messageId, string text) =>
            JsonSerializer.Serialize(
                new
                {
                    @object = "whatsapp_business_account",
                    entry = new[]
                    {
                        new
                        {
                            id = "1002",
                            changes = new[]
                            {
                                new
                                {
                                    value = new
                                    {
                                        metadata = new { phone_number_id = "1003" },
                                        messages = new[]
                                        {
                                            new
                                            {
                                                id = messageId,
                                                from = "15550000001",
                                                type = "text",
                                                timestamp = clock
                                                    .GetUtcNow()
                                                    .ToUnixTimeSeconds()
                                                    .ToString(),
                                                text = new { body = text },
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                }
            );
        async Task<WhatsAppJourneyReceipt> Send(string body)
        {
            clock.Advance();
            return await journey.ReceiveAsync(
                Encoding.UTF8.GetBytes(body),
                "sha256="
                    + Convert.ToHexStringLower(
                        HMACSHA256.HashData(
                            Encoding.UTF8.GetBytes(Credentials.Secret),
                            Encoding.UTF8.GetBytes(body)
                        )
                    ),
                clock.GetUtcNow(),
                CancellationToken.None
            );
        }
        await Send(Envelope("hello", "Hello"));
        clock.Advance();
        await Send(Envelope("consent", "YES"));
        if (relationshipBound)
        {
            await using var db = (
                (IDbContextFactory<EmploymentRelationshipDbContext>)factory
            ).CreateDbContext();
            var relationship = new EmploymentRelationship { TenantId = tenant };
            var participant = Guid.NewGuid();
            db.EmploymentRelationships.Add(relationship);
            employment.RegisterWorkspace(
                Wc120FitnessContext.Workspace(
                    tenant,
                    relationship.RelationshipId,
                    "postgres-current-workspace-5"
                )
            );
            db.RelationshipParticipants.Add(
                new RelationshipParticipant
                {
                    TenantId = tenant,
                    RelationshipId = relationship.RelationshipId,
                    ParticipantId = participant,
                    Role = RelationshipParticipantRole.Employer,
                    BoundEvidenceId = Guid.NewGuid(),
                }
            );
            db.WhatsAppJourneyContacts.Add(
                new WhatsAppJourneyContact
                {
                    TenantId = tenant,
                    PhoneHmac = digest,
                    OptedInAt = clock.GetUtcNow(),
                    LastInboundAt = clock.GetUtcNow(),
                }
            );
            db.ChannelBindings.Add(
                new Waooaw.BusinessPlatform.Infrastructure.ChannelBinding
                {
                    TenantId = tenant,
                    RelationshipId = relationship.RelationshipId,
                    ParticipantId = participant,
                    ParticipantRole = "EMPLOYER",
                    Channel = "WHATSAPP",
                    ExternalSubjectHash = digest,
                    Status = "ACTIVE",
                }
            );
            await db.SaveChangesAsync();
        }
        var confirmation = Envelope("link", "LINK synthetic-private-code");
        await Assert.ThrowsAsync<IdentityConstitutionalUnavailableException>(() =>
            Send(confirmation)
        );
        confirmations.Fail = false;
        var accepted = await Send(confirmation);
        Assert.Equal("ACCOUNT_LINK", accepted.JourneyStage);
        Assert.Contains("does not sign you in", accepted.Reply);
        await Send(confirmation);
        Assert.Equal(2, confirmations.Calls);
        Assert.Equal("+15550000001", confirmations.LastNumber);
        await using (var db = factory.CreateDbContext())
        {
            var messages = await db.PortalInteractionMessages.ToListAsync();
            Assert.All(messages, value => Assert.Equal("GUIDE", value.Actor));
            Assert.DoesNotContain(
                messages,
                value => value.ContentJson.Contains("synthetic-private-code")
            );
            Assert.Equal(3, await db.ConversationOutbox.CountAsync());
        }
        if (relationshipBound)
        {
            var ordinary = Envelope("ordinary", "Please help with the current task.");
            references.Fail = true;
            await Assert.ThrowsAsync<ConversationContextConflictException>(() => Send(ordinary));
            await using (var pending = factory.CreateDbContext())
            {
                var failed = await pending.ProviderEventClaims.SingleAsync(value =>
                    value.EventIdentity == "ordinary"
                );
                Assert.Null(failed.LeaseOwner);
                Assert.Null(failed.LeaseExpiresAt);
                Assert.Null(failed.TerminalAt);
                Assert.Empty(await pending.Messages.ToListAsync());
                Assert.Empty(await pending.Executions.ToListAsync());
            }
            references.Fail = false;
            Assert.Equal("CONTEXT_SELECTION_REQUIRED", (await Send(ordinary)).Status);
            Assert.True((await Send(ordinary)).Replayed);
            Assert.Equal(0, runtime.StartCount);
            await using (var db = factory.CreateDbContext())
            {
                var claim = await db.ProviderEventClaims.SingleAsync(value =>
                    value.EventIdentity == "ordinary"
                );
                Assert.Null(claim.LeaseOwner);
                Assert.Null(claim.LeaseExpiresAt);
                Assert.Equal("ACCEPTED", claim.State);
                Assert.Equal("SYSTEM", (await db.Messages.SingleAsync()).Actor);
                Assert.Empty(await db.Executions.ToListAsync());
            }
            await using (
                var db = (
                    (IDbContextFactory<EmploymentRelationshipDbContext>)factory
                ).CreateDbContext()
            )
            {
                var relationship = await db.EmploymentRelationships.SingleAsync();
                db.RelationshipSkillConfigurations.Add(
                    new RelationshipSkillConfiguration
                    {
                        TenantId = tenant,
                        RelationshipId = relationship.RelationshipId,
                        SkillId = "INDUCTION",
                        SkillVersion = "1.0",
                        Status = "ACCEPTED",
                        AuthorityState = "GRANTED",
                    }
                );
                await db.SaveChangesAsync();
            }
            Assert.Equal("CONTEXT_SELECTION_REQUIRED", (await Send(ordinary)).Status);
            var runtimeBody = Envelope(
                "ordinary-after-selection",
                "Please help with the current task."
            );
            runtime.FailStart = true;
            await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
                Send(runtimeBody)
            );
            var originalExecution = runtime.LastExecutionId;
            var originalKey = runtime.LastMandate!.IdempotencyIdentity;
            Assert.Equal("RECONCILIATION_REQUIRED", (await Send(runtimeBody)).Status);
            Assert.Equal(originalExecution, runtime.LastExecutionId);
            Assert.Equal(originalKey, runtime.LastMandate!.IdempotencyIdentity);
            await using (var failed = factory.CreateDbContext())
            {
                var claim = await failed.ProviderEventClaims.SingleAsync(value =>
                    value.EventIdentity == "ordinary-after-selection"
                );
                Assert.Null(claim.LeaseOwner);
                Assert.NotNull(claim.TerminalAt);
                var current = await failed.Messages.SingleAsync(value => value.Actor == "CUSTOMER");
                Assert.Equal("FAILED", current.ProcessingState);
                Assert.Equal("UNRESOLVED", current.DeliveryState);
                Assert.Equal(1, await failed.Executions.CountAsync());
            }
            runtime.FailStart = false;
            Assert.Equal("RECONCILIATION_REQUIRED", (await Send(runtimeBody)).Status);
            Assert.True((await Send(runtimeBody)).Replayed);
            Assert.Equal(1, runtime.StartCount);
            await using var cancellationDb = factory.CreateDbContext();
            var execution = await cancellationDb.Executions.SingleAsync();
            var participant = await cancellationDb
                .IdempotencyOutcomes.Where(value => value.OperationFamily == "SEND")
                .Select(value => value.ActorParticipantId)
                .SingleAsync();
            var cancelKey = Guid.NewGuid();
            runtime.FailCancel = true;
            await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
                canonical.CancelAsync(
                    tenant,
                    participant,
                    execution.RelationshipId,
                    execution.ExecutionId,
                    cancelKey,
                    CancellationToken.None
                )
            );
            await using (var unchanged = factory.CreateDbContext())
            {
                Assert.Equal("FAILED", (await unchanged.Executions.SingleAsync()).ProcessingState);
                Assert.Empty(
                    await unchanged
                        .IdempotencyOutcomes.Where(value => value.OperationFamily == "CANCEL")
                        .ToListAsync()
                );
            }
            runtime.FailCancel = false;
            var cancelled = await canonical.CancelAsync(
                tenant,
                participant,
                execution.RelationshipId,
                execution.ExecutionId,
                cancelKey,
                CancellationToken.None
            );
            Assert.Equal("CANCELLED", cancelled.Value.State);
            Assert.False(cancelled.Value.Partial);
            Assert.True(
                (
                    await canonical.CancelAsync(
                        tenant,
                        participant,
                        execution.RelationshipId,
                        execution.ExecutionId,
                        cancelKey,
                        CancellationToken.None
                    )
                ).Replayed
            );
            Assert.Equal(2, runtime.CancelCount);
            await using var terminal = factory.CreateDbContext();
            Assert.Equal("CANCELLED", (await terminal.Executions.SingleAsync()).ProcessingState);
            Assert.Single(
                await terminal
                    .Events.Where(value => value.EventType == "stream.cancelled")
                    .ToListAsync()
            );
            Assert.Equal(originalExecution, runtime.LastExecutionId);
            Assert.Equal(originalKey, runtime.LastMandate!.IdempotencyIdentity);
            await using var messages = factory.CreateDbContext();
            var message = await messages.Messages.SingleAsync(value => value.Actor == "CUSTOMER");
            Assert.Equal("INDUCTION", message.SkillId);
            Assert.DoesNotContain("synthetic-private-code", message.ContentJson);
        }
        if (relationshipBound)
        {
            var progressBody = Envelope("progress-delivery", "Show my progress");
            var destinationVerifiedAt = clock.GetUtcNow();
            await Send(progressBody);
            await Send(progressBody);
            await using (var interrupted = factory.CreateDbContext())
            {
                var claim = await interrupted.ProviderEventClaims.SingleAsync(value =>
                    value.EventIdentity == "progress-delivery"
                );
                claim.State = "RECEIVED";
                claim.ResultJson = "{}";
                claim.TerminalAt = null;
                await interrupted.SaveChangesAsync();
            }
            Assert.True((await Send(progressBody)).Replayed);
            await using var db = factory.CreateDbContext();
            var system = await db
                .Messages.Where(value => value.Actor == "SYSTEM")
                .OrderByDescending(value => value.Sequence)
                .FirstAsync();
            var systemOutbox = await db.ConversationOutbox.SingleAsync(value =>
                value.AggregateId == system.MessageId.ToString()
            );
            Assert.Equal(system.Sequence, systemOutbox.Sequence);
            Assert.Equal(digest, systemOutbox.RecipientBindingDigest);
            var completed = await db.Events.SingleAsync(value =>
                value.EventType == "message.completed" && value.MessageId == system.MessageId
            );
            Assert.Equal(system.MessageId, completed.MessageId);
            Assert.Equal(3, await db.Messages.CountAsync(value => value.Actor == "SYSTEM"));
            Assert.Equal(
                3,
                await db.Events.CountAsync(value => value.EventType == "message.completed")
            );
            Assert.Equal(1, runtime.StartCount);
            await using var contacts = (
                (IDbContextFactory<EmploymentRelationshipDbContext>)factory
            ).CreateDbContext();
            var routedContact = await contacts.WhatsAppJourneyContacts.SingleAsync();
            Assert.NotNull(routedContact.ProtectedDestination);
            Assert.Equal(destinationVerifiedAt, routedContact.DestinationVerifiedAt);
            Assert.Equal(
                "+15550000001",
                WhatsAppPhoneDestinationProtector.Unprotect(
                    Credentials.PhoneSubjectKey,
                    routedContact.ProtectedDestination!,
                    digest
                )
            );
            Assert.DoesNotContain("15550000001", routedContact.ProtectedDestination!);
        }
        if (relationshipBound)
        {
            await using var db = factory.CreateDbContext();
            var origin = await db.IdempotencyOutcomes.SingleAsync(value =>
                value.OperationFamily == "SEND"
            );
            var originalExecution = await db.Executions.SingleAsync();
            runtime.StopStart = true;
            await Assert.ThrowsAsync<ConversationStoppedException>(() =>
                canonical.SendAsync(
                    tenant,
                    origin.ActorParticipantId,
                    originalExecution.RelationshipId,
                    Guid.NewGuid(),
                    new SendConversationMessageRequestV1(
                        "1.0",
                        Guid.NewGuid(),
                        "INDUCTION",
                        [
                            new ConversationTextBlockV1(
                                "1.0",
                                "TEXT",
                                "Stop before runtime acceptance",
                                "en"
                            ),
                        ],
                        "en"
                    ),
                    CancellationToken.None
                )
            );
            await using var stoppedDb = factory.CreateDbContext();
            var message = await stoppedDb.Messages.SingleAsync(value =>
                value.ProcessingState == "STOPPED"
            );
            Assert.Equal("FAILED", message.DeliveryState);
            Assert.Equal("EMERGENCY_STOPPED", message.CompletionReason);
            Assert.False(message.Partial);
            Assert.Single(
                await stoppedDb
                    .Events.Where(value => value.EventType == "stop.applied")
                    .ToListAsync()
            );
        }
        clock.Advance(TimeSpan.FromMinutes(1));
        var closed = await Send(Envelope("closed-link", "LINK synthetic-private-code"));
        Assert.Equal(WhatsAppGuestOperatingHours.ClosedNotice, closed.Reply);
        Assert.Equal(2, confirmations.Calls);
        if (relationshipBound)
        {
            await using var db = (
                (IDbContextFactory<EmploymentRelationshipDbContext>)factory
            ).CreateDbContext();
            (await db.WhatsAppJourneyContacts.SingleAsync()).OptedOutAt = clock.GetUtcNow();
            await db.SaveChangesAsync();
            var stoppedChannel = await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
                Send(Envelope("after-stop", "LINK synthetic-private-code"))
            );
            Assert.Equal(403, stoppedChannel.StatusCode);
            Assert.Equal(2, confirmations.Calls);
            await using var messages = factory.CreateDbContext();
            Assert.DoesNotContain(
                await messages.Messages.ToListAsync(),
                value => value.ContentJson.Contains("synthetic-private-code")
            );
            return;
        }
        await Send(Envelope("stop", "STOP"));
        var stopped = await Send(Envelope("after-stop", "LINK synthetic-private-code"));
        Assert.Equal("STOPPED", stopped.Status);
        Assert.Equal(2, confirmations.Calls);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task FirstContactConcurrencyReplayEvidenceFailureStopAndTenantIsolationUseRealPostgres(
        bool recognizedRegistration
    )
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var ownerOptions = new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseNpgsql(postgres.GetConnectionString())
            .Options;
        await using (var owner = new ConversationStoreDbContext(ownerOptions))
            await owner.Database.EnsureCreatedAsync();
        await using var connection = new NpgsqlConnection(postgres.GetConnectionString());
        await connection.OpenAsync();
        var identityOptions = new DbContextOptionsBuilder<IdentityDbContext>()
            .UseNpgsql(postgres.GetConnectionString())
            .Options;
        await using (var identity = new IdentityDbContext(identityOptions))
        {
            await using var schema = new NpgsqlCommand(
                identity.Database.GenerateCreateScript(),
                connection
            );
            await schema.ExecuteNonQueryAsync();
        }
        await using (
            var roles = new NpgsqlCommand(
                """
                CREATE ROLE business_app LOGIN PASSWORD 'synthetic-app-password' NOBYPASSRLS;
                CREATE ROLE bp_runtime NOLOGIN NOBYPASSRLS;
                GRANT USAGE ON SCHEMA identity, business TO business_app, bp_runtime;
                GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA business TO business_app;
                """,
                connection
            )
        )
            await roles.ExecuteNonQueryAsync();
        var legacyTenantId = Guid.NewGuid();
        var legacyContactId = Guid.NewGuid();
        await using (
            var legacySchema = new NpgsqlCommand(
                """
                CREATE TABLE business.whatsapp_journey_contacts (
                    contact_id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL UNIQUE,
                    phone_hmac CHAR(64) NOT NULL UNIQUE,
                    opted_in_at TIMESTAMPTZ NOT NULL,
                    opted_out_at TIMESTAMPTZ,
                    last_inbound_at TIMESTAMPTZ NOT NULL,
                    journey_stage VARCHAR(24) NOT NULL,
                    pending_medium_risk_confirmation BOOLEAN NOT NULL DEFAULT FALSE,
                    mpin_hash CHAR(64),
                    mpin_failed_attempts INTEGER NOT NULL DEFAULT 0,
                    mpin_locked_until TIMESTAMPTZ
                );
                CREATE TABLE business.whatsapp_message_receipts (
                    message_id VARCHAR(128) PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    session_token_hash CHAR(64) NOT NULL,
                    session_expires_at TIMESTAMPTZ NOT NULL,
                    received_at TIMESTAMPTZ NOT NULL,
                    expires_at TIMESTAMPTZ NOT NULL,
                    CONSTRAINT whatsapp_message_receipts_tenant_fk
                        FOREIGN KEY (tenant_id)
                        REFERENCES business.whatsapp_journey_contacts (tenant_id)
                );
                CREATE FUNCTION business.reject_ae01_append_only_mutation()
                RETURNS TRIGGER AS $$
                BEGIN
                    RAISE EXCEPTION 'append-only record';
                END;
                $$ LANGUAGE plpgsql;
                CREATE TRIGGER whatsapp_message_receipts_no_update
                    BEFORE UPDATE ON business.whatsapp_message_receipts
                    FOR EACH ROW EXECUTE FUNCTION business.reject_ae01_append_only_mutation();
                INSERT INTO business.whatsapp_journey_contacts
                    (contact_id, tenant_id, phone_hmac, opted_in_at, last_inbound_at,
                     journey_stage, pending_medium_risk_confirmation)
                VALUES (@contact_id, @tenant_id, @phone_hmac, now(), now(), 'DISCOVER', FALSE);
                INSERT INTO business.whatsapp_message_receipts
                    (message_id, tenant_id, session_token_hash, session_expires_at,
                     received_at, expires_at)
                VALUES ('legacy-receipt', @tenant_id, @phone_hmac,
                        now() + interval '30 minutes', now(), now() + interval '24 hours');
                """,
                connection
            )
        )
        {
            legacySchema.Parameters.AddWithValue("contact_id", legacyContactId);
            legacySchema.Parameters.AddWithValue("tenant_id", legacyTenantId);
            legacySchema.Parameters.AddWithValue("phone_hmac", new string('d', 64));
            await legacySchema.ExecuteNonQueryAsync();
        }
        foreach (
            var name in new[]
            {
                "35-wc096-portal-interactions.sql",
                "67-wc133-phone-onboarding.sql",
                "67-wc133-phone-onboarding.sql",
                "76-wc134-whatsapp-relationship-destinations.sql",
                "76-wc134-whatsapp-relationship-destinations.sql",
            }
        )
        {
            await using var migration = new NpgsqlCommand(
                await File.ReadAllTextAsync(
                    RepositoryPaths.Resolve($"infrastructure/postgres/init/{name}")
                ),
                connection
            );
            await migration.ExecuteNonQueryAsync();
        }
        var legacyGuestTenant = Guid.NewGuid();
        var legacyGuestParticipant = Guid.NewGuid();
        var legacyGuestDigest = new string('e', 64);
        await using (
            var legacyGuest = new NpgsqlCommand(
                """
                INSERT INTO identity.phone_onboarding
                    (tenant_id, binding_digest, participant_id, evidence_id, first_observed_at,
                     admitted_at, last_inbound_at, stopped_at)
                VALUES (@tenant_id, @digest, @participant_id, @evidence_id,
                        now() - interval '1 day', now() - interval '1 day',
                        now() - interval '1 hour', NULL)
                """,
                connection
            )
        )
        {
            legacyGuest.Parameters.AddWithValue("tenant_id", legacyGuestTenant);
            legacyGuest.Parameters.AddWithValue("digest", legacyGuestDigest);
            legacyGuest.Parameters.AddWithValue("participant_id", legacyGuestParticipant);
            legacyGuest.Parameters.AddWithValue("evidence_id", Guid.NewGuid());
            await legacyGuest.ExecuteNonQueryAsync();
        }
        foreach (var _ in Enumerable.Range(0, 2))
        {
            await using var migration = new NpgsqlCommand(
                await File.ReadAllTextAsync(
                    RepositoryPaths.Resolve(
                        "infrastructure/postgres/init/68-wc134-whatsapp-participant-isolation.sql"
                    )
                ),
                connection
            );
            await migration.ExecuteNonQueryAsync();
        }
        var guestBudgetMigrationSql = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/69-wc134-whatsapp-guest-traffic-budget.sql"
            )
        );
        for (var application = 0; application < 2; application++)
        {
            await using var guestBudgetMigration = new NpgsqlCommand(
                guestBudgetMigrationSql,
                connection
            );
            await guestBudgetMigration.ExecuteNonQueryAsync();
        }
        var sessionLimitNoticeMigrationSql = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/71-wc134-whatsapp-session-limit-notice.sql"
            )
        );
        for (var application = 0; application < 2; application++)
        {
            await using var sessionLimitNoticeMigration = new NpgsqlCommand(
                sessionLimitNoticeMigrationSql,
                connection
            );
            await sessionLimitNoticeMigration.ExecuteNonQueryAsync();
        }
        var guestReplayMigrationSql = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/78-wc134-guest-traffic-replay.sql"
            )
        );
        for (var application = 0; application < 2; application++)
        {
            await using var guestReplayMigration = new NpgsqlCommand(
                guestReplayMigrationSql,
                connection
            );
            await guestReplayMigration.ExecuteNonQueryAsync();
        }
        var activationNoticeMigrationSql = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/79-wc134-activation-traffic-notice.sql"
            )
        );
        for (var application = 0; application < 2; application++)
        {
            await using var activationNoticeMigration = new NpgsqlCommand(
                activationNoticeMigrationSql,
                connection
            );
            await activationNoticeMigration.ExecuteNonQueryAsync();
        }
        var guestConsentMigrationSql = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/72-wc134-whatsapp-guest-service-consent.sql"
            )
        );
        for (var application = 0; application < 2; application++)
        {
            await using var guestConsentMigration = new NpgsqlCommand(
                guestConsentMigrationSql,
                connection
            );
            await guestConsentMigration.ExecuteNonQueryAsync();
        }
        await using (
            var migratedReceipt = new NpgsqlCommand(
                """
                SELECT contact_id
                FROM business.whatsapp_message_receipts
                WHERE message_id = 'legacy-receipt'
                """,
                connection
            )
        )
            Assert.Equal(legacyContactId, await migratedReceipt.ExecuteScalarAsync());
        await using (
            var immutableReceipt = new NpgsqlCommand(
                """
                UPDATE business.whatsapp_message_receipts
                SET contact_id = @contact_id
                WHERE message_id = 'legacy-receipt'
                """,
                connection
            )
        )
        {
            immutableReceipt.Parameters.AddWithValue("contact_id", legacyContactId);
            await Assert.ThrowsAsync<PostgresException>(() =>
                immutableReceipt.ExecuteNonQueryAsync()
            );
        }
        await using (
            var migratedGuest = new NpgsqlCommand(
                """
                SELECT participant_id, evidence_id
                FROM business.whatsapp_guest_sessions
                WHERE tenant_id = @tenant_id AND binding_digest = @digest
                """,
                connection
            )
        )
        {
            migratedGuest.Parameters.AddWithValue("tenant_id", legacyGuestTenant);
            migratedGuest.Parameters.AddWithValue("digest", legacyGuestDigest);
            await using var reader = await migratedGuest.ExecuteReaderAsync();
            Assert.True(await reader.ReadAsync());
            Assert.Equal(legacyGuestParticipant, reader.GetGuid(0));
            Assert.False(reader.IsDBNull(1));
        }
        var conversationSchema = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/36-wc120-conversation-whatsapp.sql"
            )
        );
        await using (
            var policies = new NpgsqlCommand(
                conversationSchema[
                    conversationSchema.IndexOf(
                        "ALTER TABLE business.conversation_outbox ENABLE",
                        StringComparison.Ordinal
                    )..
                ],
                connection
            )
        )
            await policies.ExecuteNonQueryAsync();
        var tenant = Guid.NewGuid();
        var digest = new string('a', 64);
        var clock = new Clock(new DateTimeOffset(2026, 11, 6, 10, 0, 0, TimeSpan.Zero));
        var now = clock.GetUtcNow();
        var appConnection = new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
        {
            Username = "business_app",
            Password = "synthetic-app-password",
            Options = $"-c app.current_tenant_id={tenant:D}",
        };
        var factory = new Factory(appConnection.ConnectionString);
        var channel = new WhatsAppJourneyOptions
        {
            WebhookSecret = Credentials.Secret,
            TenantTokenKey = new string('k', 32),
            DispatchEnabled = true,
            CallbackAcceptanceEnabled = true,
            CallbackHost = "whatsapp-demo.example.test",
        };
        static string Hash(string value) =>
            Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
        var settings = new Wc120ConversationOptions
        {
            Enabled = true,
            Environment = "demo",
            AppBindingDigest = Hash("1001"),
            WabaBindingDigest = Hash("1002"),
            RecipientBindingDigest = Hash("1003"),
        };
        var fence = new ConversationStopFence(factory, Options.Create(settings));
        var outbox = new WhatsAppOutboxService(
            factory,
            factory,
            Options.Create(settings),
            new StaticOptionsMonitor<WhatsAppJourneyOptions>(channel),
            fence
        );
        async Task<bool> BeginDispatch(ConversationOutboxRecord queued, DateTimeOffset at)
        {
            await using var db = factory.CreateDbContext();
            var row = await db.ConversationOutbox.SingleAsync(value =>
                value.OutboxId == queued.OutboxId
            );
            row.State = "LEASED";
            row.LeaseOwner = "synthetic-worker";
            row.LeaseExpiresAt = at.AddSeconds(60);
            await db.SaveChangesAsync();
            return await outbox.BeginDispatchAsync(
                row.OutboxId,
                "synthetic-worker",
                at,
                CancellationToken.None
            );
        }
        var cursor = new ConversationCursorCodec(
            Options.Create(new ConversationCursorOptions { HmacKey = new string('k', 32) })
        );
        var evidence = new Evidence();
        var gate = new Gate(tenant, digest);
        var guestTrafficBudget = new WhatsAppGuestTrafficBudget(factory, gate, clock);
        var recognition = new Recognition(recognizedRegistration);
        var service = new WhatsAppGuestSessionService(
            factory,
            evidence,
            gate,
            new PortalInteractionService(factory, cursor, new Catalog()),
            outbox,
            guestTrafficBudget,
            clock,
            recognition
        );
        VerifiedPhoneIdentityProof Proof(
            string messageId,
            string text = "Hello",
            string? phoneSubjectHash = null,
            string phoneNumber = "+15550000001",
            string? payloadDigest = null
        )
        {
            clock.Advance();
            var proofTime = clock.GetUtcNow();
            return new(
                messageId,
                phoneSubjectHash ?? digest,
                text,
                null,
                "whatsapp",
                "PHONE_VERIFIED",
                proofTime,
                proofTime,
                proofTime.AddMinutes(5),
                Guid.NewGuid()
            )
            {
                Environment = "demo",
                AppBindingDigest = settings.AppBindingDigest,
                PayloadDigest =
                    payloadDigest
                    ?? Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(text))),
                ProtectedDestination = gate.PublicAdmissionEnabled
                    ? WhatsAppPhoneDestinationProtector.Protect(
                        Credentials.PhoneSubjectKey,
                        phoneNumber,
                        phoneSubjectHash ?? digest
                    )
                    : null,
            };
        }
        await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
            service.ReceiveAsync(Proof("disabled"), CancellationToken.None)
        );
        gate.Allowed = true;
        evidence.Fail = true;
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            service.ReceiveAsync(Proof("failed"), CancellationToken.None)
        );
        await using (var empty = factory.CreateDbContext())
        {
            var pending = Assert.Single(await empty.Set<WhatsAppGuestSession>().ToListAsync());
            Assert.Null(pending.EvidenceId);
            Assert.Null(pending.AdmittedAt);
            Assert.Empty(await empty.PortalInteractionMessages.ToListAsync());
            Assert.Empty(await empty.ConversationOutbox.ToListAsync());
        }
        evidence.Fail = false;
        await using (
            var contactGrants = new NpgsqlCommand(
                """
                GRANT SELECT, INSERT, UPDATE ON business.whatsapp_journey_contacts TO business_app;
                GRANT SELECT, INSERT ON business.whatsapp_message_receipts TO business_app;
                """,
                connection
            )
        )
        {
            await contactGrants.ExecuteNonQueryAsync();
        }
        var credentials = new Credentials(digest, now);
        var journey = new WhatsAppJourneyService(
            factory,
            evidence,
            Options.Create(channel),
            conversationDbFactory: factory,
            conversationOptions: Options.Create(settings),
            outboxService: outbox,
            capabilityGate: gate,
            webhookCredentials: credentials,
            guestSessions: service,
            clock: clock
        );
        var builder = WebApplication.CreateBuilder();
        builder.WebHost.UseTestServer();
        builder
            .Services.AddControllers()
            .AddApplicationPart(typeof(WhatsAppJourneyController).Assembly);
        builder.Services.AddSingleton(journey);
        builder.Services.AddSingleton<IWhatsAppWebhookCredentials>(credentials);
        builder.Services.AddSingleton<IWhatsAppCapabilityGate>(gate);
        builder.Services.AddSingleton(Options.Create(channel));
        builder.Services.AddSingleton(Options.Create(settings));
        builder.Services.AddSingleton<TimeProvider>(clock);
        await using var host = builder.Build();
        host.MapControllers();
        await host.StartAsync();
        using var client = host.GetTestClient();
        client.BaseAddress = new Uri("https://whatsapp-demo.example.test");
        var timestamp = now.ToUnixTimeSeconds().ToString();
        var maximumText = new string('é', 4094) + "🙂";
        var textMessage = new
        {
            id = "first",
            from = "15550000001",
            type = "text",
            timestamp,
            text = new { body = maximumText },
        };
        var imageMessage = new
        {
            id = "first-image",
            from = "15550000001",
            type = "image",
            timestamp,
            image = new { id = "provider-media-reference" },
        };
        var consentMessage = new
        {
            id = "first-consent",
            from = "15550000001",
            type = "text",
            timestamp = now.AddSeconds(2).ToUnixTimeSeconds().ToString(),
            text = new { body = "YES" },
        };
        var invalidConsentMessage = new
        {
            id = "first-invalid-consent",
            from = "15550000001",
            type = "text",
            timestamp,
            text = new { body = "yes please" },
        };
        var firstContactMessage = new
        {
            id = "first-contact",
            from = "15550000001",
            type = "text",
            timestamp,
            text = new { body = "YES" },
        };
        var status = new
        {
            id = "prior-outbound-message",
            status = "delivered",
            timestamp,
        };
        string Envelope(params object[] messages) =>
            JsonSerializer.Serialize(
                new
                {
                    @object = "whatsapp_business_account",
                    entry = new[]
                    {
                        new
                        {
                            id = "1002",
                            changes = new[]
                            {
                                new
                                {
                                    value = new
                                    {
                                        metadata = new { phone_number_id = "1003" },
                                        statuses = new[] { status },
                                        messages,
                                    },
                                },
                            },
                        },
                    },
                }
            );
        async Task SendWebhookAsync(string delivery)
        {
            clock.Advance();
            using var request = new HttpRequestMessage(
                HttpMethod.Post,
                "/api/v1/channels/whatsapp/webhook"
            );
            request.Content = new StringContent(delivery, Encoding.UTF8, "application/json");
            request.Headers.Add(
                "X-Hub-Signature-256",
                "sha256="
                    + Convert.ToHexStringLower(
                        HMACSHA256.HashData(
                            Encoding.UTF8.GetBytes(Credentials.Secret),
                            Encoding.UTF8.GetBytes(delivery)
                        )
                    )
            );
            using var response = await client.SendAsync(request);
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            Assert.Equal("{\"status\":\"ACCEPTED\"}", await response.Content.ReadAsStringAsync());
        }
        string Signature(string delivery) =>
            "sha256="
            + Convert.ToHexStringLower(
                HMACSHA256.HashData(
                    Encoding.UTF8.GetBytes(Credentials.Secret),
                    Encoding.UTF8.GetBytes(delivery)
                )
            );
        var oversizedEnvelope = Envelope(
            new
            {
                id = "oversized",
                from = "15550000001",
                type = "text",
                timestamp,
                text = new { body = new string('x', 4097) },
            }
        );
        using (
            var oversizedRequest = new HttpRequestMessage(
                HttpMethod.Post,
                "/api/v1/channels/whatsapp/webhook"
            )
        )
        {
            oversizedRequest.Content = new StringContent(
                oversizedEnvelope,
                Encoding.UTF8,
                "application/json"
            );
            oversizedRequest.Headers.Add(
                "X-Hub-Signature-256",
                "sha256="
                    + Convert.ToHexStringLower(
                        HMACSHA256.HashData(
                            Encoding.UTF8.GetBytes(Credentials.Secret),
                            Encoding.UTF8.GetBytes(oversizedEnvelope)
                        )
                    )
            );
            using var oversizedResponse = await client.SendAsync(oversizedRequest);
            Assert.Equal(HttpStatusCode.BadRequest, oversizedResponse.StatusCode);
        }
        await using (var db = factory.CreateDbContext())
        {
            Assert.Empty(await db.PortalInteractionMessages.ToListAsync());
            Assert.Empty(await db.ConversationOutbox.ToListAsync());
        }
        await SendWebhookAsync(Envelope(firstContactMessage));
        await using (var pendingDb = factory.CreateDbContext())
        {
            var pending = Assert.Single(await pendingDb.Set<WhatsAppGuestSession>().ToListAsync());
            Assert.NotNull(pending.ServiceConsentNoticeQueuedAt);
            Assert.Null(pending.ServiceConsentAt);
            Assert.Equal(0, evidence.Consents);
            var notice = Assert.Single(await pendingDb.PortalInteractionMessages.ToListAsync());
            Assert.Equal("GUIDE", notice.Actor);
            Assert.Contains(
                WhatsAppGuestConsent.Notice,
                notice.ContentJson,
                StringComparison.Ordinal
            );
            Assert.Empty(
                await pendingDb
                    .PortalInteractionMessages.Where(value => value.Actor == "CUSTOMER")
                    .ToListAsync()
            );
            Assert.Single(await pendingDb.ConversationOutbox.ToListAsync());
        }
        await SendWebhookAsync(Envelope(invalidConsentMessage));
        await using (var invalidConsentDb = factory.CreateDbContext())
        {
            var pending = Assert.Single(
                await invalidConsentDb.Set<WhatsAppGuestSession>().ToListAsync()
            );
            Assert.Null(pending.ServiceConsentAt);
            Assert.Equal(0, evidence.Consents);
            Assert.Empty(
                await invalidConsentDb
                    .PortalInteractionMessages.Where(value => value.Actor == "CUSTOMER")
                    .ToListAsync()
            );
        }
        evidence.Fail = true;
        clock.Advance();
        consentMessage = consentMessage with
        {
            timestamp = clock.GetUtcNow().ToUnixTimeSeconds().ToString(),
        };
        var consentDelivery = Envelope(consentMessage);
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            journey.ReceiveAsync(
                Encoding.UTF8.GetBytes(consentDelivery),
                Signature(consentDelivery),
                clock.GetUtcNow(),
                CancellationToken.None
            )
        );
        await using (var releasedClaimDb = factory.CreateDbContext())
        {
            var claim = await releasedClaimDb.ProviderEventClaims.SingleAsync(value =>
                value.EventIdentity == "first-consent"
            );
            Assert.Equal("CLAIMED", claim.State);
            Assert.Null(claim.LeaseOwner);
            Assert.Null(claim.LeaseExpiresAt);
        }
        await using (var failedConsentDb = factory.CreateDbContext())
        {
            var pending = Assert.Single(
                await failedConsentDb.Set<WhatsAppGuestSession>().ToListAsync()
            );
            Assert.Null(pending.ServiceConsentAt);
            Assert.Null(pending.ServiceConsentMessageId);
            Assert.Null(pending.ServiceConsentEvidenceId);
            Assert.Equal(0, evidence.Consents);
            Assert.Empty(
                await failedConsentDb
                    .PortalInteractionMessages.Where(value => value.Actor == "CUSTOMER")
                    .ToListAsync()
            );
        }
        evidence.Fail = false;
        recognition.Fail = true;
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            journey.ReceiveAsync(
                Encoding.UTF8.GetBytes(consentDelivery),
                Signature(consentDelivery),
                clock.GetUtcNow(),
                CancellationToken.None
            )
        );
        Assert.Equal(1, evidence.Consents);
        recognition.Fail = false;
        await SendWebhookAsync(consentDelivery);
        Assert.Equal(1, evidence.Consents);
        await SendWebhookAsync(consentDelivery);
        Assert.Equal(1, evidence.Consents);
        await using (var consentedDb = factory.CreateDbContext())
        {
            Assert.Empty(
                await consentedDb
                    .PortalInteractionMessages.Where(value => value.Actor == "CUSTOMER")
                    .ToListAsync()
            );
        }
        foreach (var delivery in new[] { Envelope(textMessage), Envelope(imageMessage) })
        {
            await SendWebhookAsync(delivery);
        }
        var receipts = await Task.WhenAll(
            Enumerable
                .Range(0, 8)
                .Select(_ =>
                    service.ReceiveAsync(
                        Proof(
                            "first",
                            maximumText,
                            payloadDigest: Convert.ToHexStringLower(
                                SHA256.HashData(
                                    Encoding.UTF8.GetBytes(
                                        JsonSerializer.Serialize(
                                            new
                                            {
                                                wabaId = "1002",
                                                recipientId = "1003",
                                                messageId = "first",
                                                from = "15550000001",
                                                timestampText = timestamp,
                                                messageType = "text",
                                                text = maximumText,
                                            }
                                        )
                                    )
                                )
                            )
                        ),
                        CancellationToken.None
                    )
                )
        );
        Assert.All(receipts, result => Assert.Equal("GUEST_DISCOVERY", result.JourneyStage));
        Assert.All(receipts, result => Assert.True(result.Replayed));
        Assert.Equal(1, evidence.Admissions);
        Assert.Equal(1, evidence.Consents);
        await using (var identity = new IdentityDbContext(identityOptions))
        {
            Assert.Empty(await identity.Accounts.ToListAsync());
            Assert.Empty(await identity.LoginMethods.ToListAsync());
            Assert.Empty(await identity.Memberships.ToListAsync());
        }
        await using (var db = factory.CreateDbContext())
        {
            var admittedSession = Assert.Single(await db.Set<WhatsAppGuestSession>().ToListAsync());
            Assert.NotNull(admittedSession.ServiceConsentAt);
            Assert.NotNull(admittedSession.ServiceConsentNoticeQueuedAt);
            Assert.NotNull(admittedSession.ServiceConsentNoticeMessageId);
            Assert.NotEqual(Guid.Empty, admittedSession.ServiceConsentNoticeMessageId.Value);
            Assert.Equal(
                WhatsAppGuestConsent.NoticeVersion,
                admittedSession.ServiceConsentNoticeVersion
            );
            Assert.Equal("first-consent", admittedSession.ServiceConsentMessageId);
            Assert.NotNull(admittedSession.ServiceConsentEvidenceId);
            Assert.Equal(
                new[]
                {
                    "first",
                    "first-consent",
                    "first-contact",
                    "first-image",
                    "first-invalid-consent",
                },
                await db
                    .ProviderEventClaims.Where(value => value.Provider == "WHATSAPP")
                    .OrderBy(value => value.EventIdentity)
                    .Select(value => value.EventIdentity)
                    .ToArrayAsync()
            );
            Assert.Single(
                await db
                    .ProviderEventClaims.Where(value => value.Provider == "WHATSAPP_STATUS")
                    .ToListAsync()
            );
            var messages = await db.PortalInteractionMessages.ToListAsync();
            Assert.Equal(6, messages.Count);
            var inbound = Assert.Single(messages, value => value.Actor == "CUSTOMER");
            var inboundContent =
                JsonSerializer.Deserialize<ConversationTextBlockV1[]>(
                    inbound.ContentJson,
                    new JsonSerializerOptions(JsonSerializerDefaults.Web)
                )
                ?? throw new InvalidOperationException("Inbound message content was unavailable.");
            Assert.Equal(maximumText, Assert.Single(inboundContent).Text);
            Assert.Contains(
                messages,
                value =>
                    value.ContentJson.Contains(
                        WhatsAppGuestConsent.Notice,
                        StringComparison.Ordinal
                    )
            );
            Assert.Contains(
                messages,
                value =>
                    value.ContentJson.Contains(
                        recognizedRegistration
                            ? WhatsAppGuestConsent.RegisteredNumberAccepted
                            : WhatsAppGuestConsent.Accepted,
                        StringComparison.Ordinal
                    )
            );
            Assert.NotEmpty(recognition.Numbers);
            Assert.All(recognition.Numbers, number => Assert.Equal("+15550000001", number));
            Assert.DoesNotContain(
                messages,
                value =>
                    value.ContentJson.Contains("provider-media-reference", StringComparison.Ordinal)
            );
            Assert.Contains(
                messages,
                value =>
                    value.ContentJson.Contains(
                        WhatsAppGuestTrafficBudget.UnsupportedContentNotice,
                        StringComparison.Ordinal
                    )
            );
            var queued = await db.ConversationOutbox.OrderBy(value => value.Sequence).ToListAsync();
            Assert.Equal(5, queued.Count);
            Assert.All(
                queued,
                value =>
                {
                    Assert.Null(value.RelationshipId);
                    Assert.Null(value.ConversationId);
                    Assert.NotNull(value.PortalContextId);
                    Assert.Null(value.TemplateName);
                }
            );
            Assert.True(await BeginDispatch(queued[0], clock.GetUtcNow()));
            Assert.False(await BeginDispatch(queued[0], clock.GetUtcNow().AddHours(25)));
        }
        await Task.WhenAll(
            Enumerable
                .Range(0, 3)
                .Select(i => service.ReceiveAsync(Proof($"turn-{i}"), CancellationToken.None))
        );
        var exhausted = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            service.ReceiveAsync(Proof("limit-exceeded"), CancellationToken.None)
        );
        Assert.Equal("GUEST_MESSAGE_LIMIT_REACHED", exhausted.ReasonCode);
        gate.ActivationChanged = true;
        var activationChangedLimit =
            await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                service.ReceiveAsync(
                    Proof("limit-exceeded-after-activation-change"),
                    CancellationToken.None
                )
            );
        Assert.Equal("GUEST_MESSAGE_LIMIT_REACHED", activationChangedLimit.ReasonCode);
        await using (var db = factory.CreateDbContext())
        {
            var timeline = await db
                .PortalInteractionMessages.OrderBy(value => value.Sequence)
                .ToListAsync();
            Assert.Equal(
                Enumerable.Range(1, 12).Select(value => (long)value),
                timeline.Select(value => value.Sequence)
            );
            Assert.Equal(8, await db.ConversationOutbox.CountAsync());
        }
        const string secondSender = "15550000002";
        var secondDigest = Convert.ToHexStringLower(
            HMACSHA256.HashData(
                Encoding.UTF8.GetBytes(Credentials.PhoneSubjectKey),
                Encoding.UTF8.GetBytes($"+{secondSender}")
            )
        );
        var publicEnvelope = JsonSerializer.Serialize(
            new
            {
                @object = "whatsapp_business_account",
                entry = new[]
                {
                    new
                    {
                        id = "1002",
                        changes = new[]
                        {
                            new
                            {
                                value = new
                                {
                                    metadata = new { phone_number_id = "1003" },
                                    messages = new[]
                                    {
                                        new
                                        {
                                            id = "second-user",
                                            from = secondSender,
                                            type = "text",
                                            timestamp = now.ToUnixTimeSeconds().ToString(),
                                            text = new { body = "Hello" },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            }
        );
        using (
            var request = new HttpRequestMessage(
                HttpMethod.Post,
                "/api/v1/channels/whatsapp/webhook"
            )
        )
        {
            request.Content = new StringContent(publicEnvelope, Encoding.UTF8, "application/json");
            request.Headers.Add(
                "X-Hub-Signature-256",
                "sha256="
                    + Convert.ToHexStringLower(
                        HMACSHA256.HashData(
                            Encoding.UTF8.GetBytes(Credentials.Secret),
                            Encoding.UTF8.GetBytes(publicEnvelope)
                        )
                    )
            );
            using var response = await client.SendAsync(request);
            Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
        }
        gate.PublicAdmissionEnabled = true;
        using (
            var request = new HttpRequestMessage(
                HttpMethod.Post,
                "/api/v1/channels/whatsapp/webhook"
            )
        )
        {
            request.Content = new StringContent(publicEnvelope, Encoding.UTF8, "application/json");
            request.Headers.Add(
                "X-Hub-Signature-256",
                "sha256="
                    + Convert.ToHexStringLower(
                        HMACSHA256.HashData(
                            Encoding.UTF8.GetBytes(Credentials.Secret),
                            Encoding.UTF8.GetBytes(publicEnvelope)
                        )
                    )
            );
            using var response = await client.SendAsync(request);
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            Assert.Equal("{\"status\":\"ACCEPTED\"}", await response.Content.ReadAsStringAsync());
        }
        var secondReplay = await service.ReceiveAsync(
            Proof("second-user", phoneSubjectHash: secondDigest, phoneNumber: $"+{secondSender}"),
            CancellationToken.None
        );
        Assert.Equal("GUEST_CONSENT", secondReplay.JourneyStage);
        Assert.True(secondReplay.Replayed);
        Assert.Equal(
            "GUEST_CONSENT",
            (
                await service.ReceiveAsync(
                    Proof("second-user-yes", "YES", secondDigest, $"+{secondSender}"),
                    CancellationToken.None
                )
            ).JourneyStage
        );
        Assert.Equal(
            "GUEST_DISCOVERY",
            (
                await service.ReceiveAsync(
                    Proof("second-user-question", "Hello", secondDigest, $"+{secondSender}"),
                    CancellationToken.None
                )
            ).JourneyStage
        );
        await using (var db = factory.CreateDbContext())
        {
            var identities = await db.Set<WhatsAppGuestSession>()
                .OrderBy(value => value.BindingDigest)
                .ToListAsync();
            Assert.Equal(2, identities.Count);
            Assert.NotEqual(identities[0].ParticipantId, identities[1].ParticipantId);
            Assert.Equal(
                $"+{secondSender}",
                WhatsAppPhoneDestinationProtector.Unprotect(
                    Credentials.PhoneSubjectKey,
                    identities
                        .Single(value => value.BindingDigest == secondDigest)
                        .ProtectedDestination!,
                    secondDigest
                )
            );
            Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
                WhatsAppPhoneDestinationProtector.Unprotect(
                    Credentials.PhoneSubjectKey,
                    identities
                        .Single(value => value.BindingDigest == secondDigest)
                        .ProtectedDestination!,
                    digest
                )
            );
            var contexts = await db
                .PortalInteractionContexts.OrderBy(value => value.ParticipantId)
                .ToListAsync();
            Assert.Equal(2, contexts.Count);
            Assert.NotEqual(contexts[0].ContextId, contexts[1].ContextId);
            Assert.Equal(
                8,
                await db.ConversationOutbox.CountAsync(value =>
                    value.RecipientBindingDigest == digest
                )
            );
            Assert.Equal(
                3,
                await db.ConversationOutbox.CountAsync(value =>
                    value.RecipientBindingDigest == secondDigest
                )
            );
            Assert.Equal(11, await db.ConversationOutbox.CountAsync());
        }
        var businessNow = clock.GetUtcNow();
        var businessLocalNow = TimeZoneInfo.ConvertTime(
            businessNow,
            TimeZoneInfo.FindSystemTimeZoneById("Asia/Kolkata")
        );
        var businessDayStart = new DateTimeOffset(
            businessLocalNow.Year,
            businessLocalNow.Month,
            businessLocalNow.Day,
            0,
            0,
            0,
            businessLocalNow.Offset
        ).ToUniversalTime();
        var activationDigest = WhatsAppGuestTrafficEventIdentity.Activation(
            "FA:previous-public-test"
        );
        var authorityDigest = Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes("previous activation authority"))
        );
        await using (var db = factory.CreateDbContext())
        {
            foreach (var index in Enumerable.Range(0, 99))
            {
                var binding = Convert.ToHexStringLower(
                    SHA256.HashData(Encoding.UTF8.GetBytes($"session-limit-{index}"))
                );
                db.WhatsAppGuestTrafficEvents.Add(
                    new()
                    {
                        TenantId = tenant,
                        ActivationDigest = activationDigest,
                        AuthorityDigest = authorityDigest,
                        EventId = WhatsAppGuestTrafficEventIdentity.Session(
                            binding,
                            businessLocalNow.ToString("yyyy-MM-dd")
                        ),
                        BindingDigest = binding,
                        EventType = "SESSION",
                        ReservedAt = businessNow,
                    }
                );
            }
            await db.SaveChangesAsync();
        }
        var thirdSender = "15550000003";
        var thirdDigest = Convert.ToHexStringLower(
            HMACSHA256.HashData(
                Encoding.UTF8.GetBytes(Credentials.PhoneSubjectKey),
                Encoding.UTF8.GetBytes($"+{thirdSender}")
            )
        );
        var thirdProof = Proof(
            "third-user",
            phoneSubjectHash: thirdDigest,
            phoneNumber: $"+{thirdSender}"
        );
        var sessionLimit = await service.ReceiveAsync(thirdProof, CancellationToken.None);
        Assert.Equal("LIMIT_REACHED", sessionLimit.Status);
        Assert.Equal("GUEST_SESSION_LIMIT", sessionLimit.JourneyStage);
        Assert.Equal(WhatsAppGuestTrafficBudget.SessionLimitNotice, sessionLimit.Reply);
        Assert.True((await service.ReceiveAsync(thirdProof, CancellationToken.None)).Replayed);
        await using (var db = factory.CreateDbContext())
        {
            Assert.DoesNotContain(
                await db.Set<WhatsAppGuestSession>().ToListAsync(),
                value => value.BindingDigest == thirdDigest
            );
            var limitedOutbox = await db.ConversationOutbox.SingleAsync(value =>
                value.RecipientBindingDigest == thirdDigest
                && value.Purpose == "WHATSAPP_GUEST_SESSION_LIMIT_NOTICE"
            );
            Assert.NotNull(limitedOutbox.ProtectedRecipientDestination);
            Assert.True(await BeginDispatch(limitedOutbox, clock.GetUtcNow()));
            var limitedContext = await db.PortalInteractionContexts.SingleAsync(value =>
                value.ContextId == limitedOutbox.PortalContextId
            );
            Assert.DoesNotContain(
                await db.PortalInteractionMessages.ToListAsync(),
                value =>
                    value.ParticipantId == limitedContext.ParticipantId && value.Actor == "CUSTOMER"
            );
            var limitedGuide = await db.PortalInteractionMessages.SingleAsync(value =>
                value.ParticipantId == limitedContext.ParticipantId && value.Actor == "GUIDE"
            );
            using var content = JsonDocument.Parse(limitedGuide.ContentJson);
            Assert.Equal(
                WhatsAppGuestTrafficBudget.SessionLimitNotice,
                content.RootElement[0].GetProperty("text").GetString()
            );
            Assert.Equal(
                "SESSION_LIMIT",
                (
                    await db.WhatsAppGuestTrafficEvents.SingleAsync(value =>
                        value.BindingDigest == thirdDigest
                    )
                ).EventType
            );
        }
        var fourthSender = "15550000004";
        var fourthDigest = Convert.ToHexStringLower(
            HMACSHA256.HashData(
                Encoding.UTF8.GetBytes(Credentials.PhoneSubjectKey),
                Encoding.UTF8.GetBytes($"+{fourthSender}")
            )
        );
        var fourthLimit = await service.ReceiveAsync(
            Proof("fourth-user", phoneSubjectHash: fourthDigest, phoneNumber: $"+{fourthSender}"),
            CancellationToken.None
        );
        Assert.Equal("GUEST_SESSION_LIMIT", fourthLimit.JourneyStage);
        Assert.Equal(
            "STOPPED",
            (
                await service.ReceiveAsync(
                    Proof("fourth-user-stop", "STOP", fourthDigest, $"+{fourthSender}"),
                    CancellationToken.None
                )
            ).Status
        );
        await using (var db = factory.CreateDbContext())
        {
            var limitedOutbox = await db.ConversationOutbox.SingleAsync(value =>
                value.RecipientBindingDigest == fourthDigest
                && value.Purpose == "WHATSAPP_GUEST_SESSION_LIMIT_NOTICE"
            );
            Assert.False(await BeginDispatch(limitedOutbox, clock.GetUtcNow()));
        }
        await using (var budgetDb = factory.CreateDbContext())
        {
            var secondSenderCount = await budgetDb.WhatsAppGuestTrafficEvents.CountAsync(value =>
                value.BindingDigest == secondDigest && value.EventType != "SESSION"
            );
            Assert.Equal(3, secondSenderCount);
        }
        var stopped = await service.ReceiveAsync(Proof("stop", "STOP"), CancellationToken.None);
        Assert.Equal("STOPPED", stopped.Status);
        Assert.Equal(
            "STOPPED",
            (
                await service.ReceiveAsync(Proof("repeat-stop", " stop "), CancellationToken.None)
            ).Status
        );
        Assert.Equal(
            "STOPPED",
            (await service.ReceiveAsync(Proof("after"), CancellationToken.None)).Status
        );
        Assert.Equal(
            "GUEST_DISCOVERY",
            (
                await service.ReceiveAsync(
                    Proof(
                        "second-user-after-stop",
                        phoneSubjectHash: secondDigest,
                        phoneNumber: $"+{secondSender}"
                    ),
                    CancellationToken.None
                )
            ).JourneyStage
        );
        await using (var db = factory.CreateDbContext())
        {
            Assert.Equal(20, await db.PortalInteractionMessages.CountAsync());
            var identities = await db.Set<WhatsAppGuestSession>()
                .ToDictionaryAsync(value => value.BindingDigest);
            Assert.NotNull(identities[digest].StoppedAt);
            Assert.Null(identities[secondDigest].StoppedAt);
            var firstUserOutbox = await db
                .ConversationOutbox.Where(value => value.RecipientBindingDigest == digest)
                .ToListAsync();
            Assert.Equal(8, firstUserOutbox.Count);
            foreach (var queued in firstUserOutbox)
                Assert.False(await BeginDispatch(queued, now));
        }
        recognition.Fail = true;
        var recognizedCallsBeforeStop = recognition.Numbers.Count;
        await SendWebhookAsync(
            Envelope(
                new
                {
                    id = "signed-stop-during-identity-outage",
                    from = "15550000001",
                    type = "text",
                    timestamp,
                    text = new { body = "STOP" },
                }
            )
        );
        Assert.Equal(recognizedCallsBeforeStop, recognition.Numbers.Count);
        appConnection.Options = $"-c app.current_tenant_id={Guid.NewGuid():D}";
        await using var denied = new Factory(appConnection.ConnectionString).CreateDbContext();
        Assert.Empty(await denied.Set<WhatsAppGuestSession>().ToListAsync());
        Assert.Empty(await denied.PortalInteractionMessages.ToListAsync());
        Assert.Empty(await denied.ConversationOutbox.ToListAsync());
    }

    private sealed class RecoverableReferences(IConversationReferenceResolver inner)
        : IConversationReferenceResolver
    {
        public bool Fail { get; set; }

        public Task<ResolvedConversationReferences> ResolveAsync(
            Guid tenantId,
            Guid participantId,
            Guid relationshipId,
            Guid conversationId,
            string requestedContext,
            string? expectedContextVersion,
            string channel,
            CancellationToken cancellationToken
        )
        {
            if (Fail)
                throw new ConversationContextConflictException("CONVERSATION_CONTEXT_UNAVAILABLE");
            return inner.ResolveAsync(
                tenantId,
                participantId,
                relationshipId,
                conversationId,
                requestedContext,
                expectedContextVersion,
                channel,
                cancellationToken
            );
        }
    }

    private sealed class Factory(string connectionString)
        : IDbContextFactory<ConversationStoreDbContext>,
            IDbContextFactory<EmploymentRelationshipDbContext>
    {
        public ConversationStoreDbContext CreateDbContext() =>
            new(
                new DbContextOptionsBuilder<ConversationStoreDbContext>()
                    .UseNpgsql(connectionString)
                    .Options
            );

        EmploymentRelationshipDbContext IDbContextFactory<EmploymentRelationshipDbContext>.CreateDbContext() =>
            new(
                new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                    .UseNpgsql(connectionString)
                    .Options
            );
    }

    private sealed class DelayedFirstGuestNotice(IGuestConversation inner) : IGuestConversation
    {
        private int _fixedNotices;
        public TaskCompletionSource FirstCreated { get; } =
            new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource ReleaseFirst { get; } =
            new(TaskCreationOptions.RunContinuationsAsynchronously);

        public Task<PortalInteractionTimelinePageV1> ListGuestDiscoveryAsync(
            Guid tenantId,
            Guid participantId,
            string? cursor,
            int limit,
            CancellationToken ct
        ) => inner.ListGuestDiscoveryAsync(tenantId, participantId, cursor, limit, ct);

        public Task<
            ConversationCommandResult<PortalInteractionSubmissionV1>
        > SendGuestDiscoveryAsync(
            Guid tenantId,
            Guid participantId,
            Guid key,
            SendPortalInteractionMessageRequestV1 request,
            CancellationToken ct
        ) => inner.SendGuestDiscoveryAsync(tenantId, participantId, key, request, ct);

        public Task<ConversationCommandResult<PortalInteractionSubmissionV1>> SendGuestNoticeAsync(
            Guid tenantId,
            Guid participantId,
            Guid key,
            SendPortalInteractionMessageRequestV1 request,
            string notice,
            CancellationToken ct
        ) => inner.SendGuestNoticeAsync(tenantId, participantId, key, request, notice, ct);

        public async Task<
            ConversationCommandResult<PortalInteractionMessageV1>
        > SendGuestFixedNoticeAsync(
            Guid tenantId,
            Guid participantId,
            Guid key,
            string notice,
            CancellationToken ct
        )
        {
            var result = await inner.SendGuestFixedNoticeAsync(
                tenantId,
                participantId,
                key,
                notice,
                ct
            );
            if (Interlocked.Increment(ref _fixedNotices) == 1)
            {
                FirstCreated.TrySetResult();
                await ReleaseFirst.Task.WaitAsync(ct);
            }
            return result;
        }
    }

    private sealed class Clock(DateTimeOffset now) : TimeProvider
    {
        private DateTimeOffset _now = now;

        public override DateTimeOffset GetUtcNow() => _now;

        public void Advance() => _now = _now.AddSeconds(1);

        public void Advance(TimeSpan amount) => _now += amount;
    }

    private sealed class Confirmations : IWhatsAppAccountLinkConfirmation
    {
        public bool Fail { get; set; }
        public int Calls { get; private set; }
        public string? LastNumber { get; private set; }

        public Task<bool> ConfirmAsync(
            string token,
            string phoneNumber,
            VerifiedPhoneIdentityProof proof,
            CancellationToken ct
        )
        {
            Calls++;
            LastNumber = phoneNumber;
            Assert.Equal("synthetic-private-code", token);
            Assert.Equal("LINK synthetic-private-code", proof.Text);
            if (Fail)
                throw new IdentityConstitutionalUnavailableException("synthetic outage");
            return Task.FromResult(false);
        }
    }

    private sealed class Recognition(bool recognized) : IWhatsAppRegistrationRecognition
    {
        public List<string> Numbers { get; } = [];
        public bool Fail { get; set; }

        public Task<bool> IsVerifiedRegistrationAsync(string phoneNumber, CancellationToken ct)
        {
            Numbers.Add(phoneNumber);
            if (Fail)
                throw new InvalidOperationException("Synthetic Identity recognition outage.");
            return Task.FromResult(recognized);
        }
    }

    private sealed class Evidence : IWhatsAppRegistrationEvidenceGateway
    {
        public bool Fail { get; set; }
        public Func<Task>? BeforeAdmission { get; set; }
        public Func<Task>? BeforeConsent { get; set; }
        public int Admissions { get; private set; }
        public int Consents { get; private set; }

        public async Task<Guid> RecordGuestAdmissionAsync(
            Guid tenantId,
            string admissionId,
            string bindingDigest,
            DateTimeOffset occurredAt,
            CancellationToken ct
        )
        {
            if (BeforeAdmission is not null)
                await BeforeAdmission();
            await RecordAsync(tenantId, admissionId, bindingDigest, occurredAt, ct);
            return Guid.NewGuid();
        }

        public async Task<Guid> RecordGuestConsentAsync(
            Guid tenantId,
            string messageId,
            string bindingDigest,
            string noticeVersion,
            DateTimeOffset occurredAt,
            CancellationToken ct
        )
        {
            if (BeforeConsent is not null)
                await BeforeConsent();
            if (Fail)
                throw new InvalidOperationException("Synthetic evidence outage");
            Consents++;
            return Guid.NewGuid();
        }

        public Task RecordAsync(
            Guid tenantId,
            string messageId,
            string phoneHmac,
            DateTimeOffset occurredAt,
            CancellationToken ct
        )
        {
            if (Fail)
                throw new InvalidOperationException("Synthetic evidence outage");
            Admissions++;
            return Task.CompletedTask;
        }
    }

    private sealed class Gate(Guid tenantId, string digest) : IWhatsAppCapabilityGate
    {
        public bool Allowed { get; set; }
        public bool PublicAdmissionEnabled { get; set; }
        public bool ActivationChanged { get; set; }
        public int MaximumMessagesPerMinute { get; set; } = int.MaxValue;

        public WhatsAppCapabilityState Evaluate(DateTimeOffset now) => new("ACTIVE", "AUTHORIZED");

        public WhatsAppActivationAuthority RequireActive(DateTimeOffset now) =>
            new()
            {
                ActivationReference =
                    PublicAdmissionEnabled ? "FA:public-test"
                    : ActivationChanged ? "FA:own-number-test-rotated"
                    : "FA:own-number-test",
                TenantId = tenantId,
                RecipientBindingDigest = digest,
                Environment = "demo",
                MaximumMessages = int.MaxValue,
                MaximumMessagesPerMinute = MaximumMessagesPerMinute,
                AllowProvisionalOnboarding = Allowed,
                AllowPublicAdmission = PublicAdmissionEnabled,
            };

        public void RequireRecipient(Guid tenant, string binding, DateTimeOffset now)
        {
            if (tenant != tenantId || binding != digest)
                throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DENIED");
        }
    }

    private sealed class Catalog : IProfessionalCatalog
    {
        public IReadOnlyList<ProfessionalDiscoveryResult> Discover(string outcome) =>
            [
                new(
                    "fixture",
                    "1",
                    "Fixture professional",
                    ["Synthetic business assistance"],
                    new(true, "Fixture")
                ),
            ];

        public ProfessionalDisclosure? GetDisclosure(string professionalType) => null;
    }

    private sealed class Credentials(string digest, DateTimeOffset now)
        : IWhatsAppWebhookCredentials
    {
        public const string Secret = "synthetic-webhook-secret-at-least-32";
        public const string PhoneSubjectKey = "synthetic-phone-subject-hmac-key-32";

        public Task<string> ReadVerifyTokenAsync(CancellationToken ct) =>
            Task.FromResult("synthetic-token");

        public Task<string> ReadAppSecretAsync(CancellationToken ct) => Task.FromResult(Secret);

        public Task<string> ReadPhoneSubjectKeyAsync(CancellationToken ct) =>
            Task.FromResult(PhoneSubjectKey);

        public Task<WhatsAppProviderBinding> ReadSenderBindingAsync(CancellationToken ct) =>
            Task.FromResult(
                new WhatsAppProviderBinding
                {
                    Environment = "demo",
                    BindingVersion = "fixture:binding",
                    AppId = "1001",
                    WabaId = "1002",
                    PhoneNumberId = "1003",
                    RecipientPhoneNumber = "+15550000001",
                    RecipientBindingDigest = digest,
                    ApiVersion = "v25.0",
                    AuthorityReference = "fixture:authority",
                    ValidFrom = now.AddMinutes(-1),
                    ExpiresAt = now.AddMinutes(10),
                }
            );
    }
}
