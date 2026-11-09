// Implements: WC-134 R006; WC-120 CE-FIT-09.
// constitutional_basis: C-023, C-026, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Tests.Conversation;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class CeFit09WebhookIngressTests
{
    private const string Secret = "wc120-webhook-secret-at-least-32-characters";
    private const string TokenKey = "wc120-token-signing-key-at-least-32-chars";
    private const string Phone = "+919876543210";

    [Fact]
    public async Task ExhaustedRelationshipInboundBudgetStillAcceptsStopWithoutRuntimeOrReply()
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var conversationFactory = new ConversationFitnessDbFactory(
            new DbContextOptionsBuilder<ConversationStoreDbContext>()
                .UseNpgsql(postgres.GetConnectionString())
                .Options
        );
        await using (var db = conversationFactory.CreateDbContext())
            await db.Database.EnsureCreatedAsync();
        var context = await Wc120FitnessContext.CreateAsync(
            conversationFactory: conversationFactory
        );
        context.Options.AppBindingDigest = Sha256("app-test");
        context.Options.WabaBindingDigest = Sha256("waba-test");
        context.Options.RecipientBindingDigest = Sha256("recipient-test");
        var digest = Hmac(Secret, Phone);
        var now = DateTimeOffset.UtcNow;
        var gate = new InboundBudgetGate(context.TenantId, digest, now);
        var budget = new WhatsAppTrafficBudget(context.Conversations, gate, TimeProvider.System);
        await budget.ReserveRelationshipInboundAsync(
            context.TenantId,
            digest,
            "prior-message",
            CancellationToken.None
        );
        await using (var db = context.Relationships.CreateDbContext())
        {
            db.WhatsAppJourneyContacts.Add(
                new()
                {
                    TenantId = context.TenantId,
                    PhoneHmac = digest,
                    OptedInAt = now.AddMinutes(-1),
                    LastInboundAt = now.AddMinutes(-1),
                }
            );
            db.ChannelBindings.Add(
                new()
                {
                    TenantId = context.TenantId,
                    RelationshipId = context.RelationshipId,
                    ParticipantId = context.ParticipantId,
                    ParticipantRole = "EMPLOYER",
                    Channel = "WHATSAPP",
                    ExternalSubjectHash = digest,
                    ConversationId = Guid.NewGuid().ToString("D"),
                    AssuranceLevel = "AAL1_CHANNEL",
                    Status = "ACTIVE",
                }
            );
            await db.SaveChangesAsync();
        }
        var service = new WhatsAppJourneyService(
            context.Relationships,
            new EvidenceStub(),
            Microsoft.Extensions.Options.Options.Create(
                new WhatsAppJourneyOptions
                {
                    WebhookSecret = Secret,
                    TenantTokenKey = TokenKey,
                    CallbackAcceptanceEnabled = true,
                }
            ),
            conversationDbFactory: context.Conversations,
            conversationOptions: Microsoft.Extensions.Options.Options.Create(context.Options),
            stopFence: context.StopFence,
            conversationService: await CanonicalAsync(context),
            capabilityGate: gate,
            trafficBudget: budget
        );
        var ordinary = Body("over-budget", "hello", now);
        var denial = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            service.ReceiveAsync(ordinary, Sign(ordinary), now, CancellationToken.None)
        );
        Assert.Equal("TRAFFIC_BUDGET_EXHAUSTED", denial.ReasonCode);
        var stop = Body("stop-after-budget", "STOP", now);
        var receipt = await service.ReceiveAsync(stop, Sign(stop), now, CancellationToken.None);
        Assert.Equal("STOPPED", receipt.Status);
        Assert.Empty(receipt.Reply);
        await using var relationships = context.Relationships.CreateDbContext();
        Assert.NotNull((await relationships.WhatsAppJourneyContacts.SingleAsync()).OptedOutAt);
        await using var conversations = context.Conversations.CreateDbContext();
        Assert.Single(await conversations.WhatsAppGuestTrafficEvents.ToListAsync());
        Assert.Empty(await conversations.Set<ConversationExecution>().ToListAsync());
        Assert.Empty(await conversations.ConversationOutbox.ToListAsync());
    }

    private sealed class InboundBudgetGate(Guid tenantId, string digest, DateTimeOffset now)
        : IWhatsAppCapabilityGate
    {
        private readonly WhatsAppActivationAuthority _authority = new()
        {
            TenantId = tenantId,
            RecipientBindingDigest = digest,
            Environment = "test",
            ActivationReference = "FA:relationship-inbound-test",
            StartsAt = now.AddMinutes(-1),
            ExpiresAt = now.AddMinutes(5),
            MaximumMessages = 1,
            MaximumMessagesPerMinute = 1,
        };

        public WhatsAppCapabilityState Evaluate(DateTimeOffset time) => new("ACTIVE", "AUTHORIZED");

        public WhatsAppActivationAuthority RequireActive(DateTimeOffset time) => _authority;

        public void RequireRecipient(Guid tenant, string binding, DateTimeOffset time)
        {
            if (tenant != tenantId || binding != digest)
                throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DENIED");
        }
    }

    [Fact]
    public async Task ChallengeRawHmacLimitsBindingsAndAtomicClaim_FailClosed_AndCommitOneDurableOutcome()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        context.Options.AppBindingDigest = Sha256("app-test");
        context.Options.WabaBindingDigest = Sha256("waba-test");
        context.Options.RecipientBindingDigest = Sha256("recipient-test");
        var phoneDigest = Hmac(Secret, Phone);
        await using (var db = context.Relationships.CreateDbContext())
        {
            db.WhatsAppJourneyContacts.Add(
                new WhatsAppJourneyContact
                {
                    TenantId = context.TenantId,
                    PhoneHmac = phoneDigest,
                    OptedInAt = DateTimeOffset.UtcNow.AddDays(-1),
                    LastInboundAt = DateTimeOffset.UtcNow.AddMinutes(-1),
                }
            );
            db.ChannelBindings.Add(
                new ChannelBinding
                {
                    TenantId = context.TenantId,
                    RelationshipId = context.RelationshipId,
                    ParticipantId = context.ParticipantId,
                    ParticipantRole = "EMPLOYER",
                    Channel = "WHATSAPP",
                    ExternalSubjectHash = phoneDigest,
                    ConversationId = Guid.NewGuid().ToString("D"),
                    AssuranceLevel = "AAL1_CHANNEL",
                    Status = "ACTIVE",
                }
            );
            await db.SaveChangesAsync();
        }
        var service = new WhatsAppJourneyService(
            context.Relationships,
            new EvidenceStub(),
            Microsoft.Extensions.Options.Options.Create(
                new WhatsAppJourneyOptions
                {
                    WebhookSecret = Secret,
                    TenantTokenKey = TokenKey,
                    CallbackAcceptanceEnabled = true,
                }
            ),
            conversationDbFactory: context.Conversations,
            conversationOptions: Microsoft.Extensions.Options.Options.Create(context.Options),
            stopFence: context.StopFence,
            conversationService: await CanonicalAsync(context)
        );
        var now = DateTimeOffset.UtcNow;
        var body = Body("wamid-atomic-1", "hello", now);
        var first = await service.ReceiveAsync(body, Sign(body), now, CancellationToken.None);
        var replay = await service.ReceiveAsync(
            body,
            Sign(body),
            now.AddSeconds(1),
            CancellationToken.None
        );

        Assert.Equal("ACCEPTED", first.Status);
        Assert.True(replay.Replayed);
        await using (var db = context.Conversations.CreateDbContext())
        {
            Assert.Single(db.ProviderEventClaims);
            Assert.Equal("ACCEPTED", db.ProviderEventClaims.Single().State);
        }

        var modified = Body("wamid-atomic-1", "modified", now);
        await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() =>
            service.ReceiveAsync(
                modified,
                Sign(modified),
                now.AddSeconds(2),
                CancellationToken.None
            )
        );
        var invalid = await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
            service.ReceiveAsync(body, "sha256=" + new string('0', 64), now, CancellationToken.None)
        );
        Assert.Equal(403, invalid.StatusCode);
        await using (var db = context.Conversations.CreateDbContext())
        {
            foreach (
                var (environment, provider, appBinding) in new[]
                {
                    ("other", "WHATSAPP", context.Options.AppBindingDigest),
                    (context.Options.Environment, "OTHER", context.Options.AppBindingDigest),
                    (context.Options.Environment, "WHATSAPP", Sha256("other-app")),
                    (context.Options.Environment, "WHATSAPP_STATUS", Sha256("other-app")),
                }
            )
                db.ProviderEventClaims.Add(
                    new ProviderEventClaim
                    {
                        Environment = environment,
                        Provider = provider,
                        AppBindingDigest = appBinding,
                        EventIdentity = Guid.NewGuid().ToString("N"),
                        PayloadDigest = Sha256("synthetic"),
                        State = "ACCEPTED",
                        TerminalAt = now.AddDays(-2),
                        ExpiresAt = now.AddDays(-1),
                    }
                );
            await db.SaveChangesAsync();
        }
        await service.SetProviderClaimHoldAsync(
            "WHATSAPP",
            "wamid-atomic-1",
            true,
            CancellationToken.None
        );
        Assert.Equal(
            0,
            await service.PurgeExpiredProviderClaimsAsync(now.AddDays(31), CancellationToken.None)
        );
        await service.SetProviderClaimHoldAsync(
            "WHATSAPP",
            "wamid-atomic-1",
            false,
            CancellationToken.None
        );
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.ProviderEventClaims.Add(
                new ProviderEventClaim
                {
                    Environment = context.Options.Environment,
                    Provider = "WHATSAPP_STATUS",
                    AppBindingDigest = context.Options.AppBindingDigest,
                    EventIdentity = "status-expired",
                    PayloadDigest = Sha256("status"),
                    State = "ACCEPTED",
                    TerminalAt = now.AddDays(-2),
                    ExpiresAt = now.AddDays(-1),
                }
            );
            await db.SaveChangesAsync();
        }
        Assert.Equal(
            2,
            await service.PurgeExpiredProviderClaimsAsync(now.AddDays(31), CancellationToken.None)
        );
        await using var savedClaims = context.Conversations.CreateDbContext();
        Assert.Equal(4, await savedClaims.ProviderEventClaims.CountAsync());
        context.Options.AppBindingDigest = "invalid";
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            service.PurgeExpiredProviderClaimsAsync(now.AddDays(31), CancellationToken.None)
        );
    }

    [Fact]
    public async Task ProviderMessageAndStatusEnvelopesValidateBindingsAndTypedPayloads()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        context.Options.AppBindingDigest = Sha256("app-test");
        context.Options.WabaBindingDigest = Sha256("waba-test");
        context.Options.RecipientBindingDigest = Sha256("recipient-test");
        var phoneDigest = Hmac(Secret, Phone);
        await using (var db = context.Relationships.CreateDbContext())
        {
            db.WhatsAppJourneyContacts.Add(
                new WhatsAppJourneyContact
                {
                    TenantId = context.TenantId,
                    PhoneHmac = phoneDigest,
                    OptedInAt = DateTimeOffset.UtcNow.AddDays(-1),
                    LastInboundAt = DateTimeOffset.UtcNow,
                }
            );
            db.ChannelBindings.Add(
                new ChannelBinding
                {
                    TenantId = context.TenantId,
                    RelationshipId = context.RelationshipId,
                    ParticipantId = context.ParticipantId,
                    ParticipantRole = "EMPLOYER",
                    Channel = "WHATSAPP",
                    ExternalSubjectHash = phoneDigest,
                    ConversationId = Guid.NewGuid().ToString("D"),
                    AssuranceLevel = "AAL1_CHANNEL",
                    Status = "ACTIVE",
                }
            );
            await db.SaveChangesAsync();
        }
        var service = new WhatsAppJourneyService(
            context.Relationships,
            new EvidenceStub(),
            Microsoft.Extensions.Options.Options.Create(
                new WhatsAppJourneyOptions
                {
                    WebhookSecret = Secret,
                    TenantTokenKey = TokenKey,
                    CallbackAcceptanceEnabled = true,
                    DispatchEnabled = true,
                }
            ),
            conversationDbFactory: context.Conversations,
            conversationOptions: Microsoft.Extensions.Options.Options.Create(context.Options),
            stopFence: context.StopFence,
            conversationService: await CanonicalAsync(context),
            outboxService: context.Outbox()
        );
        var now = DateTimeOffset.UtcNow;
        var message = ProviderEnvelope(
            new
            {
                messages = new[]
                {
                    new
                    {
                        id = "wamid-provider",
                        from = Phone,
                        timestamp = now.ToUnixTimeSeconds().ToString(),
                        type = "text",
                        text = new { body = "hello" },
                    },
                },
            }
        );
        Assert.Equal(
            "ACCEPTED",
            (await service.ReceiveAsync(message, Sign(message), now, CancellationToken.None)).Status
        );

        var status = JsonSerializer.SerializeToUtf8Bytes(
            new
            {
                eventType = "status",
                statusEventId = "status-1",
                messageId = "provider-message",
                status = "delivered",
                wabaId = "waba-test",
                recipientId = "recipient-test",
                timestamp = now.ToUnixTimeSeconds(),
            }
        );
        Assert.Equal(
            "DELIVERY_STATUS",
            (
                await service.ReceiveAsync(status, Sign(status), now, CancellationToken.None)
            ).JourneyStage
        );
        var nestedStatus = JsonSerializer.SerializeToUtf8Bytes(
            new
            {
                entry = new[]
                {
                    new
                    {
                        id = "waba-test",
                        changes = new[]
                        {
                            new
                            {
                                value = new
                                {
                                    metadata = new { phone_number_id = "recipient-test" },
                                    statuses = new[]
                                    {
                                        new
                                        {
                                            id = "provider-message-2",
                                            status = "read",
                                            timestamp = now.ToUnixTimeSeconds().ToString(),
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            }
        );
        Assert.Equal(
            "DELIVERY_STATUS",
            (
                await service.ReceiveAsync(
                    nestedStatus,
                    Sign(nestedStatus),
                    now,
                    CancellationToken.None
                )
            ).JourneyStage
        );
        var malformedStatus = JsonSerializer.SerializeToUtf8Bytes(
            new
            {
                entry = new[]
                {
                    new
                    {
                        id = "waba-test",
                        changes = new[]
                        {
                            new
                            {
                                value = new
                                {
                                    metadata = new { phone_number_id = "recipient-test" },
                                    statuses = new[]
                                    {
                                        new
                                        {
                                            id = "",
                                            status = "read",
                                            timestamp = "invalid",
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            }
        );
        Assert.Equal(
            400,
            (
                await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
                    service.ReceiveAsync(
                        malformedStatus,
                        Sign(malformedStatus),
                        now,
                        CancellationToken.None
                    )
                )
            ).StatusCode
        );

        var wrongBinding = ProviderEnvelope(
            new
            {
                messages = new[]
                {
                    new
                    {
                        id = "wamid-wrong-binding",
                        from = Phone,
                        timestamp = now.ToUnixTimeSeconds().ToString(),
                        type = "text",
                        text = new { body = "hello" },
                    },
                },
            },
            recipientId: "wrong-recipient"
        );
        Assert.Equal(
            403,
            (
                await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
                    service.ReceiveAsync(
                        wrongBinding,
                        Sign(wrongBinding),
                        now,
                        CancellationToken.None
                    )
                )
            ).StatusCode
        );
        var malformed = ProviderEnvelope(
            new
            {
                messages = new[]
                {
                    new
                    {
                        id = "",
                        from = Phone,
                        timestamp = "invalid",
                        type = "image",
                    },
                },
            }
        );
        Assert.Equal(
            400,
            (
                await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
                    service.ReceiveAsync(malformed, Sign(malformed), now, CancellationToken.None)
                )
            ).StatusCode
        );
    }

    [Fact]
    public async Task SignedUnsupportedRelationshipMessageCreatesCanonicalSystemReply()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        context.Options.AppBindingDigest = Sha256("app-test");
        context.Options.WabaBindingDigest = Sha256("waba-test");
        context.Options.RecipientBindingDigest = Sha256("recipient-test");
        var phoneDigest = Hmac(Secret, Phone);
        await using (var db = context.Relationships.CreateDbContext())
        {
            db.WhatsAppJourneyContacts.Add(
                new WhatsAppJourneyContact
                {
                    TenantId = context.TenantId,
                    PhoneHmac = phoneDigest,
                    OptedInAt = DateTimeOffset.UtcNow.AddDays(-1),
                    LastInboundAt = DateTimeOffset.UtcNow,
                }
            );
            db.ChannelBindings.Add(
                new ChannelBinding
                {
                    TenantId = context.TenantId,
                    RelationshipId = context.RelationshipId,
                    ParticipantId = context.ParticipantId,
                    ParticipantRole = "EMPLOYER",
                    Channel = "WHATSAPP",
                    ExternalSubjectHash = phoneDigest,
                    ConversationId = Guid.NewGuid().ToString("D"),
                    AssuranceLevel = "AAL1_CHANNEL",
                    Status = "ACTIVE",
                }
            );
            await db.SaveChangesAsync();
        }
        var service = new WhatsAppJourneyService(
            context.Relationships,
            new EvidenceStub(),
            Microsoft.Extensions.Options.Options.Create(
                new WhatsAppJourneyOptions
                {
                    WebhookSecret = Secret,
                    TenantTokenKey = TokenKey,
                    CallbackAcceptanceEnabled = true,
                }
            ),
            conversationDbFactory: context.Conversations,
            conversationOptions: Microsoft.Extensions.Options.Options.Create(context.Options),
            stopFence: context.StopFence,
            outboundContributions: context.Outbound()
        );
        var now = DateTimeOffset.UtcNow;
        var body = ProviderEnvelope(
            new
            {
                messages = new[]
                {
                    new
                    {
                        id = "wamid-unsupported-relationship",
                        from = Phone,
                        timestamp = now.ToUnixTimeSeconds().ToString(),
                        type = "image",
                        image = new { id = "provider-media-reference" },
                    },
                },
            }
        );

        var first = await service.ReceiveAsync(body, Sign(body), now, CancellationToken.None);
        var replay = await service.ReceiveAsync(
            body,
            Sign(body),
            now.AddSeconds(1),
            CancellationToken.None
        );

        Assert.Equal("UNSUPPORTED_CONTENT", first.Status);
        Assert.True(replay.Replayed);
        await using var conversationDb = context.Conversations.CreateDbContext();
        var message = Assert.Single(await conversationDb.Messages.ToListAsync());
        Assert.Equal("SYSTEM", message.Actor);
        Assert.DoesNotContain(
            "provider-media-reference",
            message.ContentJson,
            StringComparison.Ordinal
        );
        var outbox = Assert.Single(await conversationDb.ConversationOutbox.ToListAsync());
        Assert.Equal(context.RelationshipId, outbox.RelationshipId);
        Assert.Equal("CUSTOMER_REQUEST", outbox.Purpose);
    }

    [Fact]
    public async Task SignedRelationshipTextEntersCanonicalConversationAndStartsRuntimeOnce()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        context.Options.AppBindingDigest = Sha256("app-test");
        context.Options.WabaBindingDigest = Sha256("waba-test");
        context.Options.RecipientBindingDigest = Sha256("recipient-test");
        var phoneDigest = Hmac(Secret, Phone);
        await using (var db = context.Relationships.CreateDbContext())
        {
            db.WhatsAppJourneyContacts.Add(
                new WhatsAppJourneyContact
                {
                    TenantId = context.TenantId,
                    PhoneHmac = phoneDigest,
                    OptedInAt = DateTimeOffset.UtcNow.AddDays(-1),
                    LastInboundAt = DateTimeOffset.UtcNow,
                }
            );
            db.ChannelBindings.Add(
                new ChannelBinding
                {
                    TenantId = context.TenantId,
                    RelationshipId = context.RelationshipId,
                    ParticipantId = context.ParticipantId,
                    ParticipantRole = "EMPLOYER",
                    Channel = "WHATSAPP",
                    ExternalSubjectHash = phoneDigest,
                    ConversationId = Guid.NewGuid().ToString("D"),
                    AssuranceLevel = "AAL1_CHANNEL",
                    Status = "ACTIVE",
                }
            );
            await db.SaveChangesAsync();
        }
        var runtime = new ConversationExecutionGatewayStub();
        var service = new WhatsAppJourneyService(
            context.Relationships,
            new EvidenceStub(),
            Microsoft.Extensions.Options.Options.Create(
                new WhatsAppJourneyOptions
                {
                    WebhookSecret = Secret,
                    TenantTokenKey = TokenKey,
                    CallbackAcceptanceEnabled = true,
                }
            ),
            conversationDbFactory: context.Conversations,
            conversationOptions: Microsoft.Extensions.Options.Options.Create(context.Options),
            stopFence: context.StopFence,
            conversationService: await CanonicalAsync(context, runtime)
        );
        var now = DateTimeOffset.UtcNow;
        var body = ProviderEnvelope(
            new
            {
                messages = new[]
                {
                    new
                    {
                        id = "wamid-relationship-text",
                        from = Phone,
                        timestamp = now.ToUnixTimeSeconds().ToString(),
                        type = "text",
                        text = new { body = "Please help me review my progress." },
                    },
                },
            }
        );

        var first = await service.ReceiveAsync(body, Sign(body), now, CancellationToken.None);
        var replay = await service.ReceiveAsync(
            body,
            Sign(body),
            now.AddSeconds(1),
            CancellationToken.None
        );

        Assert.Equal("ACCEPTED", first.Status);
        Assert.True(replay.Replayed);
        Assert.Equal(1, runtime.StartCount);
        await using var conversationDb = context.Conversations.CreateDbContext();
        var message = Assert.Single(await conversationDb.Messages.ToListAsync());
        Assert.Equal("WHATSAPP", message.Channel);
        Assert.Equal("INDUCTION", message.SkillId);
        Assert.Contains(
            "Please help me review my progress.",
            message.ContentJson,
            StringComparison.Ordinal
        );
        Assert.Single(await conversationDb.Executions.ToListAsync());
    }

    private static byte[] ProviderEnvelope(object value, string recipientId = "recipient-test") =>
        JsonSerializer.SerializeToUtf8Bytes(
            new
            {
                entry = new[]
                {
                    new
                    {
                        id = "waba-test",
                        changes = new[]
                        {
                            new
                            {
                                value = new
                                {
                                    metadata = new { phone_number_id = recipientId },
                                    messages = value
                                        .GetType()
                                        .GetProperty("messages")
                                        ?.GetValue(value),
                                },
                            },
                        },
                    },
                },
            }
        );

    private static byte[] Body(string messageId, string text, DateTimeOffset sentAt) =>
        JsonSerializer.SerializeToUtf8Bytes(
            new
            {
                messageId,
                from = Phone,
                text,
                timestamp = sentAt.ToUnixTimeSeconds(),
                riskTier = "TIER_1_LOW_RISK",
                appId = "app-test",
                wabaId = "waba-test",
                recipientId = "recipient-test",
            },
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );

    private static string Sign(byte[] body) => "sha256=" + Hmac(Secret, body);

    private static string Hmac(string key, string value) =>
        Hmac(key, Encoding.UTF8.GetBytes(value));

    private static string Hmac(string key, byte[] value) =>
        Convert.ToHexStringLower(HMACSHA256.HashData(Encoding.UTF8.GetBytes(key), value));

    private static string Sha256(string value) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));

    [Theory]
    [InlineData("single")]
    [InlineData("shared-web-context")]
    [InlineData("no-authority")]
    [InlineData("ambiguous")]
    [InlineData("retired-context")]
    public async Task ChannelSkillComesFromCurrentOwnerAuthorityAndSharedCanonicalContext(
        string scenario
    )
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var service = await CanonicalAsync(context);
        if (scenario is "shared-web-context" or "retired-context")
            await context.SeedConversationAsync(("WEB", "Continue this skill"));
        await using (var db = context.Relationships.CreateDbContext())
        {
            var induction = await db.RelationshipSkillConfigurations.SingleAsync();
            if (scenario == "no-authority")
                induction.AuthorityState = "NOT_GRANTED";
            if (scenario == "retired-context")
                induction.Status = "RETIRED";
            if (scenario is "shared-web-context" or "ambiguous" or "retired-context")
                db.RelationshipSkillConfigurations.Add(
                    new RelationshipSkillConfiguration
                    {
                        TenantId = context.TenantId,
                        RelationshipId = context.RelationshipId,
                        SkillId = "ANOTHER_SKILL",
                        SkillVersion = "1.0",
                        Status = "ACCEPTED",
                        AuthorityState = "GRANTED",
                    }
                );
            if (scenario == "retired-context")
                db.RelationshipSkillConfigurations.Add(
                    new RelationshipSkillConfiguration
                    {
                        TenantId = context.TenantId,
                        RelationshipId = context.RelationshipId,
                        SkillId = "THIRD_SKILL",
                        SkillVersion = "1.0",
                        Status = "ACCEPTED",
                        AuthorityState = "GRANTED",
                    }
                );
            await db.SaveChangesAsync();
        }
        if (scenario is "single" or "shared-web-context")
            Assert.Equal(
                "INDUCTION",
                await service.ResolveChannelSkillAsync(
                    context.TenantId,
                    context.ParticipantId,
                    context.RelationshipId,
                    CancellationToken.None
                )
            );
        else
            await Assert.ThrowsAsync<ConversationContextConflictException>(() =>
                service.ResolveChannelSkillAsync(
                    context.TenantId,
                    context.ParticipantId,
                    context.RelationshipId,
                    CancellationToken.None
                )
            );
    }

    [Fact]
    public async Task AcceptedMessageRetryKeepsOriginalSkillWithoutRestoringRevokedAuthority()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var service = await CanonicalAsync(context);
        var messageId = Guid.NewGuid();
        await service.SendAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            messageId,
            new SendConversationMessageRequestV1(
                "1.0",
                messageId,
                "INDUCTION",
                [new ConversationTextBlockV1("1.0", "TEXT", "Previously accepted")],
                "en-IN"
            ),
            CancellationToken.None
        );
        await using (var db = context.Relationships.CreateDbContext())
        {
            (await db.RelationshipSkillConfigurations.SingleAsync()).AuthorityState = "REVOKED";
            await db.SaveChangesAsync();
        }
        Assert.Equal(
            "INDUCTION",
            await service.ResolveChannelSkillAsync(
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                CancellationToken.None,
                messageId
            )
        );
        await Assert.ThrowsAsync<ConversationContextConflictException>(() =>
            service.ResolveChannelSkillAsync(
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<ConversationNotAccessibleException>(() =>
            service.ResolveChannelSkillAsync(
                context.TenantId,
                Guid.NewGuid(),
                context.RelationshipId,
                CancellationToken.None,
                messageId
            )
        );
    }

    private static async Task<ConversationService> CanonicalAsync(
        Wc120FitnessContext context,
        ConversationExecutionGatewayStub? runtime = null
    )
    {
        await using var db = context.Relationships.CreateDbContext();
        db.RelationshipSkillConfigurations.Add(
            new RelationshipSkillConfiguration
            {
                TenantId = context.TenantId,
                RelationshipId = context.RelationshipId,
                SkillId = "INDUCTION",
                SkillVersion = "1.0",
                Status = "ACCEPTED",
                AuthorityState = "GRANTED",
            }
        );
        await db.SaveChangesAsync();
        return new(
            context.Conversations,
            context.Relationships,
            new ConversationConstitutionalGatewayStub(),
            runtime ?? new ConversationExecutionGatewayStub(),
            new OperationalMandateResolverStub(),
            new ConversationCursorCodec(
                Microsoft.Extensions.Options.Options.Create(
                    new ConversationCursorOptions
                    {
                        HmacKey = "wc120-ingress-test-key-at-least-32-characters", // gitleaks:allow
                    }
                )
            ),
            context.StopFence,
            context.Profiles,
            Microsoft.Extensions.Options.Options.Create(context.Options)
        );
    }

    private sealed class EvidenceStub : IWhatsAppRegistrationEvidenceGateway
    {
        public Task RecordAsync(
            Guid tenantId,
            string messageId,
            string phoneHmac,
            DateTimeOffset occurredAt,
            CancellationToken cancellationToken
        ) => Task.CompletedTask;
    }
}
