// Implements: work-contracts/WC-135-requirements.yaml WC135-R002, WC135-R005, WC135-R006, WC135-R009, WC135-R010
// Constitutional basis: C-009, C-023, C-026, C-048, C-059, C-063

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

/// <summary>The guest copy is process-wide, so tests that switch it must not overlap other tests.</summary>
[CollectionDefinition("VisitorGuestCopy", DisableParallelization = true)]
public sealed class VisitorGuestCopyCollection;

[Collection("VisitorGuestCopy")]
public sealed class WhatsAppVisitorV2PostgresTests
{
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

    [Fact]
    public async Task ScriptedConversationRunsThroughConsentStopStartAndStructuredReplies()
    {
        var content = VisitorTestContent.Shipped();
        var copy = GuestCopy.FromContent(content, 90);
        GuestCopyRegistry.Use(copy);
        try
        {
            await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
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
            var digest = new string('b', 64);
            var clock = new VisitorClock
            {
                Now = new DateTimeOffset(2026, 11, 19, 6, 0, 0, TimeSpan.Zero),
            };
            var gate = new Gate(tenant);
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
                new RelationshipDbFactory(postgres.GetConnectionString()),
                settings,
                new StaticOptionsMonitor<WhatsAppJourneyOptions>(new() { DispatchEnabled = true }),
                new ConversationStopFence(factory, settings)
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
            var service = new WhatsAppGuestSessionService(
                factory,
                new Evidence(),
                gate,
                interactions,
                outbox,
                new WhatsAppGuestTrafficBudget(factory, gate, clock),
                clock,
                visitor: visitor,
                visitorOptions: monitor
            );

            var counter = 0;
            async Task<WhatsAppJourneyReceipt> Say(string text, string? choice = null)
            {
                clock.Now = clock.Now.AddSeconds(3);
                var proof = new VerifiedPhoneIdentityProof(
                    $"wamid-{++counter}",
                    digest,
                    text,
                    null,
                    "whatsapp-provider-callback",
                    "AAL1_CHANNEL",
                    clock.Now,
                    clock.Now,
                    clock.Now.AddMinutes(5),
                    Guid.NewGuid()
                )
                {
                    Environment = "demo",
                    ProtectedDestination = "synthetic-protected-destination",
                    ChoiceId = choice,
                };
                return await service.ReceiveAsync(proof, CancellationToken.None, "+15555550123");
            }

            var welcome = await Say("Hi");
            Assert.Equal("CONSENT_REQUIRED", welcome.Status);
            Assert.Equal(copy.Notice, welcome.Reply);
            Assert.StartsWith("*Welcome to WAOOAW!*", welcome.Reply);
            Assert.Contains("https://cp.demo.waooaw.com/privacy", welcome.Reply);

            var consent = await Say("Yes", VisitorChoiceIds.ConsentYes);
            Assert.Equal("CONSENT_RECORDED", consent.Status);
            Assert.Equal(copy.Accepted, consent.Reply);
            Assert.Contains("Which professional would you like to explore?", consent.Reply);

            var card = await Say("1");
            Assert.Contains("Digital Marketing Professional", card.Reply);
            Assert.DoesNotContain("STOP", card.Reply);

            var stopped = await Say("stop");
            Assert.Equal("STOPPED", stopped.Status);
            Assert.Equal("STOPPED", (await Say("hello?")).Status);

            var resumed = await Say("Hi");
            Assert.Equal("CONSENT_REQUIRED", resumed.Status);
            Assert.Equal(copy.ResumeNotice, resumed.Reply);

            await using var verify = factory.CreateDbContext();
            var guest = await verify.Set<WhatsAppGuestSession>().SingleAsync();
            Assert.Null(guest.StoppedAt);
            Assert.Null(guest.ServiceConsentAt);
            Assert.Equal(1, guest.ResumeCount);
            Assert.Equal(1, await verify.Set<WhatsAppGuestConsentHistory>().CountAsync());
            var session = await verify.VisitorSessions.SingleAsync();
            Assert.Equal(digest, session.SubjectHash);
            Assert.Equal(VisitorOutcomes.OptOut, session.Outcome);

            // Both consent notices were stored with their Yes/STOP buttons.
            var hints = await verify.VisitorRenderHints.ToListAsync();
            Assert.True(hints.Count >= 2);
            Assert.All(
                hints,
                hint =>
                    Assert.NotNull(
                        VisitorWhatsAppRenderer.Interactive(
                            VisitorWhatsAppRenderer.ParseReply(hint.ReplyJson)!
                        )
                    )
            );
            Assert.Contains(
                hints,
                hint =>
                    hint.ReplyJson.Contains(VisitorChoiceIds.ConsentYes, StringComparison.Ordinal)
            );

            var again = await Say("YES", VisitorChoiceIds.ConsentYes);
            Assert.Equal("CONSENT_RECORDED", again.Status);
            Assert.Equal(copy.Accepted, again.Reply);
            var transcript = await verify
                .PortalInteractionMessages.Select(message => message.ContentJson)
                .ToListAsync();
            Assert.DoesNotContain(
                transcript,
                json => json.Contains("+15555550123", StringComparison.Ordinal)
            );
        }
        finally
        {
            GuestCopyRegistry.Reset();
        }
    }

    [Fact]
    public void InteractiveRepliesRenderOnlyWhatWhatsAppAcceptsAndAlwaysKeepPlainText()
    {
        var reply = new VisitorReply
        {
            Blocks =
            [
                VisitorReplyBlock.TextBlock("Which one?"),
                VisitorReplyBlock.ChoicesBlock(new("a", "Option A"), new("b", "Option B")),
            ],
        };
        var buttons = JsonSerializer.SerializeToNode(VisitorWhatsAppRenderer.Interactive(reply))!;
        Assert.Equal("button", buttons["interactive"]!["type"]!.GetValue<string>());
        Assert.Equal("Which one?", VisitorWhatsAppRenderer.CanonicalText(reply));

        var tooMany = reply with
        {
            Blocks =
            [
                VisitorReplyBlock.TextBlock("Pick"),
                VisitorReplyBlock.ChoicesBlock(
                    new("a", "A"),
                    new("b", "B"),
                    new("c", "C"),
                    new("d", "D")
                ),
            ],
        };
        Assert.Null(VisitorWhatsAppRenderer.Interactive(tooMany));

        var tooLong = reply with
        {
            Blocks =
            [
                VisitorReplyBlock.TextBlock("Pick"),
                VisitorReplyBlock.ChoicesBlock(
                    new VisitorChoice("a", "This label is far too long for a button")
                ),
            ],
        };
        Assert.Null(VisitorWhatsAppRenderer.Interactive(tooLong));

        var link = new VisitorReply
        {
            Blocks =
            [
                VisitorReplyBlock.TextBlock("Ready?"),
                new VisitorReplyBlock
                {
                    Type = "LINK",
                    Label = "Start free trial",
                    Url = "https://cp.demo.waooaw.com/start",
                },
            ],
        };
        Assert.Equal(
            "Ready?\n\nStart free trial: https://cp.demo.waooaw.com/start",
            VisitorWhatsAppRenderer.CanonicalText(link)
        );
        var cta = JsonSerializer.SerializeToNode(VisitorWhatsAppRenderer.Interactive(link))!;
        Assert.Equal("cta_url", cta["interactive"]!["type"]!.GetValue<string>());
    }

    private sealed class RelationshipDbFactory(string connectionString)
        : IDbContextFactory<EmploymentRelationshipDbContext>
    {
        public EmploymentRelationshipDbContext CreateDbContext() =>
            new(
                new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                    .UseNpgsql(connectionString)
                    .Options
            );
    }
}
