// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C1-03
// Constitutional basis: C-023, C-026, C-059, C-063

using Microsoft.EntityFrameworkCore;
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
public sealed class WhatsAppRelationshipStopAcknowledgementTests
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

    private sealed class Rig : IAsyncDisposable
    {
        private readonly PostgreSqlContainer _postgres;
        private int _counter;

        private Rig(PostgreSqlContainer postgres) => _postgres = postgres;

        public required Factory Db { get; init; }
        public required WhatsAppRelationshipStopAcknowledgementService Service { get; init; }
        public required WhatsAppOutboxService Outbox { get; init; }
        public required PortalInteractionService Interactions { get; init; }
        public required VisitorClock Clock { get; init; }
        public required RecordingLogger<WhatsAppRelationshipStopAcknowledgementService> Logger { get; init; }
        public required GuestCopy Copy { get; init; }
        public required Guid Tenant { get; init; }

        public Guid RelationshipTenant { get; } = Guid.NewGuid();
        public Guid RelationshipId { get; } = Guid.NewGuid();
        public string Digest { get; } = new('b', 64);

        public static async Task<Rig> CreateAsync(bool switchOn, bool dispatch)
        {
            var copy = GuestCopy.FromContent(VisitorTestContent.Shipped(), 90);
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
            var logger = new RecordingLogger<WhatsAppRelationshipStopAcknowledgementService>();
            return new Rig(postgres)
            {
                Db = factory,
                Service = new WhatsAppRelationshipStopAcknowledgementService(
                    interactions,
                    outbox,
                    gate,
                    settings,
                    protocol,
                    clock,
                    logger
                ),
                Outbox = outbox,
                Interactions = interactions,
                Clock = clock,
                Logger = logger,
                Copy = copy,
                Tenant = tenant,
            };
        }

        public VerifiedPhoneIdentityProof Proof(string text, string? messageId = null) =>
            new(
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
            };

        public WhatsAppSafetyAcknowledgementTarget Target(
            bool emergency,
            string? contactDestination = Destination
        ) => new(RelationshipTenant, RelationshipId, emergency, contactDestination);

        public async Task MarkStoppedAsync()
        {
            await using var db = Db.CreateDbContext();
            db.Set<WhatsAppGuestSession>()
                .Add(
                    new WhatsAppGuestSession
                    {
                        TenantId = Tenant,
                        BindingDigest = Digest,
                        FirstObservedAt = Clock.Now,
                        LastInboundAt = Clock.Now,
                        StoppedAt = Clock.Now,
                    }
                );
            await db.SaveChangesAsync();
        }

        public async Task LatchEmergencyStopAsync()
        {
            await using var db = Db.CreateDbContext();
            db.EmergencyStopLatches.Add(
                new RelationshipEmergencyStopLatch
                {
                    Environment = "demo",
                    TenantId = RelationshipTenant,
                    RelationshipId = RelationshipId,
                    StoppedByParticipantId = Guid.NewGuid(),
                    CorrelationId = Guid.NewGuid(),
                    LatchedAt = Clock.Now,
                }
            );
            await db.SaveChangesAsync();
        }

        public async Task<List<ConversationOutboxRecord>> RowsAsync()
        {
            await using var db = Db.CreateDbContext();
            return await db.ConversationOutbox.AsNoTracking().ToListAsync();
        }

        public async ValueTask DisposeAsync()
        {
            GuestCopyRegistry.Reset();
            await _postgres.DisposeAsync();
        }
    }

    [Fact]
    public void RelationshipReferencesCarryOnlyIdentifiersAndRejectForeignShapes()
    {
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var key = Guid.NewGuid();

        foreach (var emergency in new[] { false, true })
        {
            var reference = WhatsAppStopAcknowledgementPolicy.RelationshipReference(
                emergency,
                tenant,
                relationship,
                key
            );
            Assert.True(
                WhatsAppStopAcknowledgementPolicy.TryParseRelationshipReference(
                    reference,
                    out var parsedEmergency,
                    out var parsedTenant,
                    out var parsedRelationship
                )
            );
            Assert.Equal(emergency, parsedEmergency);
            Assert.Equal(tenant, parsedTenant);
            Assert.Equal(relationship, parsedRelationship);
        }

        foreach (
            var foreign in new[]
            {
                null,
                string.Empty,
                $"portal-message:{key:D}",
                $"relationship-stop:{tenant:D}:{relationship:D}",
                $"relationship-stop:{tenant:D}:{relationship:D}:{key:D}:extra",
                $"relationship-stop:not-a-guid:{relationship:D}:{key:D}",
                $"relationship-emergency-stop:{Guid.Empty:D}:{relationship:D}:{key:D}",
                $"relationship-emergency-stop:{tenant:D}:{relationship:D}:{Guid.Empty:D}",
            }
        )
            Assert.False(
                WhatsAppStopAcknowledgementPolicy.TryParseRelationshipReference(
                    foreign,
                    out _,
                    out _,
                    out _
                ),
                foreign
            );
    }

    [Fact]
    public async Task StopIsAcknowledgedOnceAfterItsEvidenceAndAReplayQueuesNothingNew()
    {
        await using var rig = await Rig.CreateAsync(switchOn: true, dispatch: true);
        await rig.MarkStoppedAsync();

        var text = await rig.Service.TryAcknowledgeAsync(
            rig.Target(emergency: false),
            rig.Proof("STOP", "wamid-stop"),
            default
        );
        var replay = await rig.Service.TryAcknowledgeAsync(
            rig.Target(emergency: false),
            rig.Proof("STOP", "wamid-stop"),
            default
        );

        Assert.Equal(rig.Copy.StopAcknowledged, text);
        Assert.Equal(rig.Copy.StopAcknowledged, replay);
        var row = Assert.Single(await rig.RowsAsync());
        Assert.Equal(WhatsAppStopAcknowledgementPolicy.RelationshipPurpose, row.Purpose);
        Assert.Equal(rig.Digest, row.RecipientBindingDigest);
        Assert.Equal(Destination, row.ProtectedRecipientDestination);
        Assert.True(
            WhatsAppStopAcknowledgementPolicy.TryParseRelationshipReference(
                row.PayloadReference,
                out var emergency,
                out var relationshipTenant,
                out var relationshipId
            )
        );
        Assert.False(emergency);
        Assert.Equal(rig.RelationshipTenant, relationshipTenant);
        Assert.Equal(rig.RelationshipId, relationshipId);

        Assert.True(await rig.Outbox.IsCurrentlyEligibleAsync(row, rig.Clock.Now, default));
        Assert.False(
            await rig.Outbox.IsCurrentlyEligibleAsync(row, row.CreatedAt.AddHours(25), default)
        );
        Assert.Contains("protocol_stop_acknowledged channel=WHATSAPP kind=STOP", rig.Logger.Lines);
        Assert.DoesNotContain(
            rig.Logger.Lines,
            line =>
                line.Contains(Destination, StringComparison.Ordinal)
                || line.Contains(rig.Digest, StringComparison.Ordinal)
        );
    }

    [Fact]
    public async Task EmergencyStopSendsTheFixedSentenceOnlyOnceItsFenceLatchExists()
    {
        await using var rig = await Rig.CreateAsync(switchOn: true, dispatch: true);

        Assert.Null(
            await rig.Service.TryAcknowledgeAsync(
                rig.Target(emergency: true),
                rig.Proof("EMERGENCY STOP", "wamid-emergency"),
                default
            )
        );
        Assert.Empty(await rig.RowsAsync());

        await rig.LatchEmergencyStopAsync();
        var text = await rig.Service.TryAcknowledgeAsync(
            rig.Target(emergency: true),
            rig.Proof("EMERGENCY STOP", "wamid-emergency"),
            default
        );

        Assert.Equal(WhatsAppStopAcknowledgementPolicy.EmergencyStopConfirmation, text);
        var row = Assert.Single(await rig.RowsAsync());
        Assert.Equal(WhatsAppStopAcknowledgementPolicy.RelationshipPurpose, row.Purpose);
        Assert.True(await rig.Outbox.IsCurrentlyEligibleAsync(row, rig.Clock.Now, default));
        Assert.Contains(
            "protocol_stop_acknowledgement_failed channel=WHATSAPP kind=EMERGENCY_STOP reason=RECIPIENT_ELIGIBILITY_REVOKED",
            rig.Logger.Lines
        );
        Assert.Contains(
            "protocol_stop_acknowledged channel=WHATSAPP kind=EMERGENCY_STOP",
            rig.Logger.Lines
        );
    }

    [Theory]
    [InlineData(false, true)]
    [InlineData(true, false)]
    public async Task ADisabledOrFailedAcknowledgementReturnsNothingAndNeverThrows(
        bool switchOn,
        bool dispatch
    )
    {
        await using var rig = await Rig.CreateAsync(switchOn, dispatch);
        await rig.MarkStoppedAsync();

        var text = await rig.Service.TryAcknowledgeAsync(
            rig.Target(emergency: false),
            rig.Proof("STOP"),
            default
        );

        Assert.Null(text);
        Assert.Empty(await rig.RowsAsync());
        Assert.DoesNotContain(
            rig.Logger.Lines,
            line => line.Contains("protocol_stop_acknowledged ", StringComparison.Ordinal)
        );
        if (switchOn)
            Assert.Contains(
                "protocol_stop_acknowledgement_failed channel=WHATSAPP kind=STOP reason=DISPATCH_DISABLED",
                rig.Logger.Lines
            );
    }

    [Fact]
    public async Task OnlyTheFixedTextForAStoppedRecipientCanBeQueuedThroughTheRelationshipRoute()
    {
        await using var rig = await Rig.CreateAsync(switchOn: true, dispatch: true);
        var participant = Guid.NewGuid();
        var fixedNotice = await rig.Interactions.SendGuestFixedNoticeAsync(
            rig.Tenant,
            participant,
            Guid.NewGuid(),
            rig.Copy.StopAcknowledged,
            default
        );

        var notStopped = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            rig.Outbox.QueueRelationshipStopAcknowledgementAsync(
                rig.Tenant,
                rig.RelationshipTenant,
                rig.RelationshipId,
                participant,
                rig.Digest,
                Destination,
                emergency: false,
                fixedNotice.Value,
                rig.Clock.Now,
                default
            )
        );
        Assert.Equal("RECIPIENT_ELIGIBILITY_REVOKED", notStopped.ReasonCode);

        await rig.MarkStoppedAsync();
        var wrongKind = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            rig.Outbox.QueueRelationshipStopAcknowledgementAsync(
                rig.Tenant,
                rig.RelationshipTenant,
                rig.RelationshipId,
                participant,
                rig.Digest,
                Destination,
                emergency: true,
                fixedNotice.Value,
                rig.Clock.Now,
                default
            )
        );
        Assert.Equal("MESSAGE_PROJECTION_DENIED", wrongKind.ReasonCode);

        await rig.Outbox.QueueRelationshipStopAcknowledgementAsync(
            rig.Tenant,
            rig.RelationshipTenant,
            rig.RelationshipId,
            participant,
            rig.Digest,
            Destination,
            emergency: false,
            fixedNotice.Value,
            rig.Clock.Now,
            default
        );
        Assert.Single(await rig.RowsAsync());
    }
}
