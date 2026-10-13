using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
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
            conversationService: Canonical(context)
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
        Assert.Equal(
            1,
            await service.PurgeExpiredProviderClaimsAsync(now.AddDays(31), CancellationToken.None)
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
            conversationService: Canonical(context),
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

    private static ConversationService Canonical(Wc120FitnessContext context) =>
        new(
            context.Conversations,
            context.Relationships,
            new ConversationConstitutionalGatewayStub(),
            new ConversationExecutionGatewayStub(),
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
