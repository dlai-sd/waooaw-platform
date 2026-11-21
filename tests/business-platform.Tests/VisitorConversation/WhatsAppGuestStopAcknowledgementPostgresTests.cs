// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C1-02
// Constitutional basis: C-023, C-026, C-059, C-063

using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Visitor;
using Waooaw.BusinessPlatform.Tests.Conversation;
using Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.VisitorConversation;

[Collection("VisitorGuestCopy")]
public sealed class WhatsAppGuestStopAcknowledgementPostgresTests
{
    private const string Destination = "synthetic-protected-destination";

    private sealed class Factory(string connectionString)
        : IDbContextFactory<ConversationStoreDbContext>
    {
        public ConversationStoreDbContext CreateDbContext() =>
            new(
                new DbContextOptionsBuilder<ConversationStoreDbContext>()
                    .UseNpgsql(connectionString)
                    .Options
            );
    }

    private sealed class RelationshipFactory(string connectionString)
        : IDbContextFactory<EmploymentRelationshipDbContext>
    {
        public EmploymentRelationshipDbContext CreateDbContext() =>
            new(
                new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                    .UseNpgsql(connectionString)
                    .Options
            );
    }

    private sealed class Gate(Guid tenantId) : IWhatsAppCapabilityGate
    {
        public WhatsAppCapabilityState Evaluate(DateTimeOffset now) => new("ACTIVE", "AUTHORIZED");

        public WhatsAppActivationAuthority RequireActive(DateTimeOffset now) =>
            new()
            {
                ActivationReference = "FA:public-test",
                TenantId = tenantId,
                RecipientBindingDigest = new string('a', 64),
                Environment = "demo",
                MaximumMessages = int.MaxValue,
                MaximumMessagesPerMinute = int.MaxValue,
                AllowProvisionalOnboarding = true,
                AllowPublicAdmission = true,
            };

        public void RequireRecipient(Guid tenant, string binding, DateTimeOffset now) { }
    }

    private sealed class Catalog : IProfessionalCatalog
    {
        public IReadOnlyList<ProfessionalDiscoveryResult> Discover(string outcome) => [];

        public ProfessionalDisclosure? GetDisclosure(string professionalType) => null;
    }

    private sealed class Evidence : IWhatsAppRegistrationEvidenceGateway
    {
        public Task<Guid> RecordGuestAdmissionAsync(
            Guid t,
            string a,
            string b,
            DateTimeOffset o,
            CancellationToken c
        ) => Task.FromResult(Guid.NewGuid());

        public Task<Guid> RecordGuestConsentAsync(
            Guid t,
            string m,
            string b,
            string n,
            DateTimeOffset o,
            CancellationToken c
        ) => Task.FromResult(Guid.NewGuid());

        public Task RecordAsync(
            Guid t,
            string m,
            string p,
            DateTimeOffset o,
            CancellationToken c
        ) => Task.CompletedTask;
    }

    private sealed class Rig : IAsyncDisposable
    {
        private readonly PostgreSqlContainer _postgres;
        private int _counter;

        private Rig(PostgreSqlContainer postgres) => _postgres = postgres;

        public required Factory Db { get; init; }
        public required WhatsAppGuestSessionService Service { get; init; }
        public required WhatsAppOutboxService Outbox { get; init; }
        public required PortalInteractionService Interactions { get; init; }
        public required VisitorClock Clock { get; init; }
        public required RecordingLogger<WhatsAppGuestSessionService> Logger { get; init; }
        public required GuestCopy Copy { get; init; }
        public required Guid Tenant { get; init; }

        public string Digest { get; } = new('b', 64);

        public static async Task<Rig> CreateAsync(bool switchOn, bool acknowledge, bool dispatch)
        {
            var content = VisitorTestContent.Shipped();
            if (!acknowledge)
                content = content with
                {
                    Protocol = content.Protocol with
                    {
                        Stop = content.Protocol.Stop with { Acknowledge = false },
                    },
                };
            var copy = GuestCopy.FromContent(content, 90);
            GuestCopyRegistry.Use(copy);
            var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
            await postgres.StartAsync();
            var factory = new Factory(postgres.GetConnectionString());
            await using (var setup = factory.CreateDbContext())
            {
                await setup.Database.EnsureCreatedAsync();
                await setup.Database.ExecuteSqlRawAsync(
                    "CREATE TABLE business.whatsapp_journey_contacts (tenant_id uuid NOT NULL, phone_hmac varchar(64) NOT NULL, opted_out_at timestamptz NULL)"
                );
            }
            var tenant = Guid.NewGuid();
            var clock = new VisitorClock
            {
                Now = new DateTimeOffset(2026, 11, 19, 6, 0, 0, TimeSpan.Zero),
            };
            var gate = new Gate(tenant);
            var settings = Options.Create(
                new Wc120ConversationOptions { Enabled = true, Environment = "demo" }
            );
            var protocol = new StaticOptionsMonitor<ProtocolOptions>(
                new() { WhatsAppStopAcknowledgementEnabled = switchOn }
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
                new RelationshipFactory(postgres.GetConnectionString()),
                settings,
                new StaticOptionsMonitor<WhatsAppJourneyOptions>(
                    new() { DispatchEnabled = dispatch }
                ),
                new ConversationStopFence(factory, settings),
                protocolOptions: protocol
            );
            var options = new VisitorConversationOptions
            {
                Mode = VisitorMode.V2,
                LocalKeys = new() { ["k1"] = new string('a', 40) },
                LocalCurrentKeyVersion = "k1",
            };
            var monitor = new StaticOptionsMonitor<VisitorConversationOptions>(options);
            var visitor = new VisitorConversationService(
                factory,
                new FixedContent(content),
                new VisitorFieldProtector(new ConfigurationVisitorKeyRing(monitor)),
                monitor,
                new StaticOptionsMonitor<VisitorLeadOptions>(new VisitorLeadOptions()),
                new CountingEvidence(),
                new VisitorTelemetry(NullLogger<VisitorTelemetry>.Instance),
                clock,
                NullLogger<VisitorConversationService>.Instance
            );
            var logger = new RecordingLogger<WhatsAppGuestSessionService>();
            var service = new WhatsAppGuestSessionService(
                factory,
                new Evidence(),
                gate,
                interactions,
                outbox,
                new WhatsAppGuestTrafficBudget(factory, gate, clock),
                clock,
                visitor: visitor,
                visitorOptions: monitor,
                protocolOptions: protocol,
                logger: logger
            );
            return new Rig(postgres)
            {
                Db = factory,
                Service = service,
                Outbox = outbox,
                Interactions = interactions,
                Clock = clock,
                Logger = logger,
                Copy = copy,
                Tenant = tenant,
            };
        }

        public async Task<WhatsAppJourneyReceipt> Say(
            string text,
            string? choice = null,
            string? messageId = null
        )
        {
            Clock.Now = Clock.Now.AddSeconds(3);
            var proof = new VerifiedPhoneIdentityProof(
                messageId ?? $"wamid-{++_counter}",
                Digest,
                text,
                null,
                "whatsapp-provider-callback",
                "AAL1_CHANNEL",
                Clock.Now,
                Clock.Now,
                Clock.Now.AddMinutes(5),
                Guid.NewGuid()
            )
            {
                Environment = "demo",
                ProtectedDestination = Destination,
                ChoiceId = choice,
            };
            return await Service.ReceiveAsync(proof, CancellationToken.None, "+15555550123");
        }

        public async Task<List<ConversationOutboxRecord>> OutboxRowsAsync()
        {
            await using var db = Db.CreateDbContext();
            return await db.ConversationOutbox.AsNoTracking().ToListAsync();
        }

        public async Task<List<ConversationOutboxRecord>> AcknowledgementRowsAsync() =>
            (await OutboxRowsAsync())
                .Where(row => row.Purpose == WhatsAppStopAcknowledgementPolicy.GuestPurpose)
                .ToList();

        public async ValueTask DisposeAsync()
        {
            GuestCopyRegistry.Reset();
            await _postgres.DisposeAsync();
        }
    }

    [Fact]
    public async Task StopIsAcknowledgedOnceThenSilentUntilStartAndConsentAgain()
    {
        await using var rig = await Rig.CreateAsync(
            switchOn: true,
            acknowledge: true,
            dispatch: true
        );
        Assert.Equal("CONSENT_REQUIRED", (await rig.Say("Hi")).Status);
        Assert.Equal(
            "CONSENT_RECORDED",
            (await rig.Say("YES", VisitorChoiceIds.ConsentYes)).Status
        );

        var stopped = await rig.Say("stop", messageId: "wamid-stop");
        Assert.Equal("STOPPED", stopped.Status);
        Assert.Equal(rig.Copy.StopAcknowledged, stopped.Reply);

        var row = Assert.Single(await rig.AcknowledgementRowsAsync());
        Assert.Equal(WhatsAppStopAcknowledgementPolicy.GuestPurpose, row.Purpose);
        Assert.Equal(rig.Digest, row.RecipientBindingDigest);
        Assert.Equal(Destination, row.ProtectedRecipientDestination);
        var ackMessageId = Guid.Parse(row.AggregateId);
        await using (var db = rig.Db.CreateDbContext())
        {
            var message = await db.PortalInteractionMessages.SingleAsync(value =>
                value.MessageId == ackMessageId
            );
            var block = Assert.Single(
                JsonSerializer.Deserialize<List<ConversationTextBlockV1>>(
                    message.ContentJson,
                    new JsonSerializerOptions(JsonSerializerDefaults.Web)
                )!
            );
            Assert.Equal(rig.Copy.StopAcknowledged, block.Text);
        }

        Assert.True(await rig.Outbox.IsCurrentlyEligibleAsync(row, rig.Clock.Now, default));
        Assert.True(
            await rig.Outbox.IsCurrentlyEligibleAsync(row, row.CreatedAt.AddHours(23), default)
        );
        Assert.False(
            await rig.Outbox.IsCurrentlyEligibleAsync(row, row.CreatedAt.AddHours(25), default)
        );

        Assert.Equal(string.Empty, (await rig.Say("stop", messageId: "wamid-stop")).Reply);
        Assert.Equal(string.Empty, (await rig.Say("STOP")).Reply);
        Assert.Equal(string.Empty, (await rig.Say("hello?")).Reply);
        Assert.Single(await rig.AcknowledgementRowsAsync());

        var resumed = await rig.Say("START");
        Assert.Equal("CONSENT_REQUIRED", resumed.Status);
        Assert.Equal(rig.Copy.ResumeNotice, resumed.Reply);
        Assert.False(await rig.Outbox.IsCurrentlyEligibleAsync(row, rig.Clock.Now, default));
        Assert.Equal(
            "CONSENT_RECORDED",
            (await rig.Say("YES", VisitorChoiceIds.ConsentYes)).Status
        );

        Assert.Contains("protocol_stop_acknowledged channel=WHATSAPP", rig.Logger.Lines);
        Assert.DoesNotContain(
            rig.Logger.Lines,
            line =>
                line.Contains(Destination, StringComparison.Ordinal)
                || line.Contains(rig.Digest, StringComparison.Ordinal)
                || line.Contains("15555550123", StringComparison.Ordinal)
        );
    }

    [Theory]
    [InlineData(false, true)]
    [InlineData(true, false)]
    public async Task StopStaysSilentWhenTheRolloutSwitchOrThePolicyIsOff(
        bool switchOn,
        bool acknowledge
    )
    {
        await using var rig = await Rig.CreateAsync(switchOn, acknowledge, dispatch: true);
        await rig.Say("Hi");
        await rig.Say("YES", VisitorChoiceIds.ConsentYes);
        var outboxBefore = (await rig.OutboxRowsAsync()).Count;

        var stopped = await rig.Say("stop");

        Assert.Equal("STOPPED", stopped.Status);
        Assert.Equal(string.Empty, stopped.Reply);
        Assert.Equal(outboxBefore, (await rig.OutboxRowsAsync()).Count);
        Assert.DoesNotContain(
            rig.Logger.Lines,
            line => line.Contains("protocol_stop_acknowledged", StringComparison.Ordinal)
        );
    }

    [Fact]
    public async Task AFailedAcknowledgementNeverUndoesOrHidesTheStop()
    {
        await using var rig = await Rig.CreateAsync(
            switchOn: true,
            acknowledge: true,
            dispatch: false
        );

        var stopped = await rig.Say("STOP");

        Assert.Equal("STOPPED", stopped.Status);
        Assert.Equal(string.Empty, stopped.Reply);
        await using var db = rig.Db.CreateDbContext();
        Assert.NotNull((await db.Set<WhatsAppGuestSession>().SingleAsync()).StoppedAt);
        Assert.Empty(await rig.OutboxRowsAsync());
        Assert.Contains(
            "protocol_stop_acknowledgement_failed channel=WHATSAPP reason=WhatsAppCapabilityUnavailableException",
            rig.Logger.Lines
        );
    }

    [Fact]
    public async Task OnlyTheFixedAcknowledgementTextCanBeQueuedAndOnlyForAStoppedGuest()
    {
        await using var rig = await Rig.CreateAsync(
            switchOn: true,
            acknowledge: true,
            dispatch: true
        );
        await rig.Say("Hi");
        await rig.Say("YES", VisitorChoiceIds.ConsentYes);

        var early = await rig.Interactions.SendGuestFixedNoticeAsync(
            rig.Tenant,
            Guid.NewGuid(),
            Guid.NewGuid(),
            rig.Copy.StopAcknowledged,
            default
        );
        var notStopped = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            rig.Outbox.QueueGuestStopAcknowledgementAsync(
                rig.Tenant,
                Guid.NewGuid(),
                rig.Digest,
                Destination,
                early.Value,
                rig.Clock.Now,
                default
            )
        );
        Assert.Equal("RECIPIENT_ELIGIBILITY_REVOKED", notStopped.ReasonCode);

        await rig.Say("stop");
        var other = await rig.Interactions.SendGuestFixedNoticeAsync(
            rig.Tenant,
            Guid.NewGuid(),
            Guid.NewGuid(),
            rig.Copy.Notice,
            default
        );
        var wrongText = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            rig.Outbox.QueueGuestStopAcknowledgementAsync(
                rig.Tenant,
                Guid.NewGuid(),
                rig.Digest,
                Destination,
                other.Value,
                rig.Clock.Now,
                default
            )
        );
        Assert.Equal("MESSAGE_PROJECTION_DENIED", wrongText.ReasonCode);
    }
}
