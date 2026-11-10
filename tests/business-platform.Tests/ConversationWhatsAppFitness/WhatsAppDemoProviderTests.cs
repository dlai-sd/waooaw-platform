using System.Net;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Tests.Conversation;
using Waooaw.BusinessPlatform.Tests.Identity;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppDemoProviderTests
{
    [Theory]
    [InlineData("UNRESOLVED", true)]
    [InlineData("FAILED", true)]
    [InlineData("UNRESOLVED", false)]
    public async Task RelationshipWebhookReplayNeverRestartsFailedProfessionalWork(
        string deliveryState,
        bool contributionAvailable
    )
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await context.SeedWhatsAppEligibilityAsync(Recipient, now);
        await using (var relationships = context.Relationships.CreateDbContext())
        {
            relationships.RelationshipSkillConfigurations.Add(
                new RelationshipSkillConfiguration
                {
                    TenantId = context.TenantId,
                    RelationshipId = context.RelationshipId,
                    SkillId = "INDUCTION",
                    SkillVersion = "1.0",
                    Status = "ACCEPTED",
                    Applicability = "APPLICABLE",
                    AuthorityState = "GRANTED",
                }
            );
            await relationships.SaveChangesAsync();
        }
        var runtime = new ConversationExecutionGatewayStub { FailStart = true };
        var evidence = new ConversationConstitutionalGatewayStub();
        var mandate = new OperationalMandateResolverStub();
        var canonical = new ConversationService(
            context.Conversations,
            context.Relationships,
            evidence,
            runtime,
            mandate,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            ),
            conversationOptions: Options.Create(context.Options)
        );
        var journey = new WhatsAppJourneyService(
            context.Relationships,
            new ForbiddenEvidence(),
            Options.Create(new WhatsAppJourneyOptions()),
            conversationDbFactory: context.Conversations,
            conversationOptions: Options.Create(context.Options),
            conversationService: canonical,
            outboundContributions: contributionAvailable ? context.Outbound() : null
        );
        var proof = new VerifiedPhoneIdentityProof(
            "unknown-original",
            Recipient,
            "Please help with this task",
            null,
            "verified-test",
            "AAL1_CHANNEL",
            now,
            now,
            now.AddMinutes(5),
            Guid.NewGuid()
        );
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            journey.ReceiveVerifiedAsync(proof, CancellationToken.None)
        );
        var originalExecution = runtime.LastExecutionId;
        var originalMandate = runtime.LastMandate;
        if (deliveryState == "FAILED")
        {
            await using var db = context.Conversations.CreateDbContext();
            (await db.Messages.SingleAsync()).DeliveryState = "FAILED";
            (await db.IdempotencyOutcomes.SingleAsync()).Outcome = "FAILED";
            await db.SaveChangesAsync();
        }
        runtime.FailStart = false;
        for (var replay = 0; replay < 2; replay++)
        {
            if (!contributionAvailable)
                await Assert.ThrowsAsync<InvalidOperationException>(() =>
                    journey.ReceiveVerifiedAsync(proof, CancellationToken.None)
                );
            else
            {
                var receipt = await journey.ReceiveVerifiedAsync(proof, CancellationToken.None);
                Assert.Equal(
                    deliveryState == "UNRESOLVED"
                        ? "RECONCILIATION_REQUIRED"
                        : "SECURE_PORTAL_REQUIRED",
                    receipt.Status
                );
                Assert.Contains("No new professional work was started.", receipt.Reply);
                Assert.Equal(replay == 1, receipt.Replayed);
                Assert.Empty(receipt.InternalTenantToken);
            }
        }
        Assert.Equal(1, runtime.StartCount);
        Assert.Equal(1, evidence.CallCount);
        Assert.Equal(1, mandate.ResolveCount);
        Assert.Equal(originalExecution, runtime.LastExecutionId);
        Assert.Same(originalMandate, runtime.LastMandate);
        await using var verify = context.Conversations.CreateDbContext();
        var original = await verify.Messages.SingleAsync(value => value.Actor == "CUSTOMER");
        Assert.Equal(deliveryState, original.DeliveryState);
        Assert.Equal("FAILED", original.ProcessingState);
        Assert.Single(verify.Executions);
        Assert.Equal(contributionAvailable ? 1 : 0, verify.ConversationOutbox.Count());
        Assert.Equal(
            contributionAvailable ? 1 : 0,
            verify.Messages.Count(value => value.Actor == "SYSTEM")
        );
        Assert.Single(verify.IdempotencyOutcomes.Where(value => value.OperationFamily == "SEND"));
    }

    [Theory]
    [InlineData("STOP", false)]
    [InlineData("EMERGENCY STOP", false)]
    [InlineData("STOP", true)]
    [InlineData("EMERGENCY STOP", true)]
    public async Task SignedSafetyIngressRequiresRoutingOwnerAndNeverFallsIntoOrdinaryJourney(
        string text,
        bool ownerAvailable
    )
    {
        var fixture = await SeedAsync();
        var scope = new WhatsAppTenantExecutionScope(fixture.Gate, fixture.Clock);
        var secrets = new WebhookCredentials();
        var identity = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var routing = new WhatsAppRelationshipRouting(
            fixture.Context.Relationships,
            fixture.Context.Conversations,
            IdentityTestHelpers.CreateService(identity),
            scope,
            fixture.Gate,
            new ConfigurationBuilder().Build(),
            fixture.Clock
        );
        var journey = new WhatsAppJourneyService(
            fixture.Context.Relationships,
            new ForbiddenEvidence(),
            Options.Create(new WhatsAppJourneyOptions()),
            conversationOptions: Options.Create(fixture.Context.Options),
            webhookCredentials: secrets,
            capabilityGate: fixture.Gate,
            clock: fixture.Clock,
            tenantExecutionScope: scope,
            relationshipRouting: ownerAvailable ? routing : null
        );
        var body = Encoding.UTF8.GetBytes(
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
                                                id = "safety-owner",
                                                from = Binding()
                                                    .RecipientPhoneNumber.TrimStart('+'),
                                                timestamp = Now.ToUnixTimeSeconds().ToString(),
                                                type = "text",
                                                text = new { body = text },
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                }
            )
        );
        var signature =
            "sha256="
            + Convert.ToHexStringLower(
                HMACSHA256.HashData(Encoding.UTF8.GetBytes(secrets.AppSecret), body)
            );
        using (scope.Begin())
        {
            if (ownerAvailable)
            {
                var failure = await Assert.ThrowsAsync<WhatsAppChannelBindingUnavailableException>(
                    () =>
                        journey.ReceiveAsync(body, signature, Now, CancellationToken.None)
                );
                Assert.Equal("Safety routing requires PostgreSQL.", failure.Message);
            }
            else
            {
                var failure = await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
                    journey.ReceiveAsync(body, signature, Now, CancellationToken.None)
                );
                Assert.Equal("WHATSAPP_ROUTING_OWNER_UNAVAILABLE", failure.Code);
            }
            Assert.Equal(fixture.Request.TenantId, scope.CurrentTenantId);
        }
        await using var db = fixture.Context.Conversations.CreateDbContext();
        Assert.Empty(db.Set<WhatsAppGuestSession>());
        Assert.Empty(db.EmergencyStopLatches);
        await using var relationships = fixture.Context.Relationships.CreateDbContext();
        Assert.Empty(relationships.WhatsAppMessageReceipts);
    }

    [Fact]
    public async Task CustomerDispatchWithoutFreshRoutingOwnerCannotReadSecretsOrOpenProviderSocket()
    {
        var fixture = await SeedAsync();
        var reads = 0;
        var clients = new ClientFactory(
            (_, _) =>
            {
                reads++;
                throw new InvalidOperationException(
                    "Customer route denial must precede any provider socket."
                );
            }
        );
        var adapter = Adapter(fixture, clients);
        var denied = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            adapter.DispatchAsync(
                fixture.Request with
                {
                    TenantId = Guid.NewGuid(),
                },
                CancellationToken.None
            )
        );
        Assert.Equal("CUSTOMER_EGRESS_OWNER_UNAVAILABLE", denied.ReasonCode);
        Assert.Equal(0, reads);
        await using var db = fixture.Context.Conversations.CreateDbContext();
        Assert.Empty(await db.Set<WhatsAppTrafficReservation>().ToListAsync());
    }

    private static readonly DateTimeOffset Now = new(2026, 11, 2, 9, 0, 0, TimeSpan.Zero);
    private static readonly string Recipient = new('b', 64);
    private static readonly string TupleDigest = "sha256:" + new string('a', 64);

    [Theory]
    [InlineData("valid")]
    [InlineData("altered")]
    [InlineData("foreign")]
    [InlineData("customer")]
    [InlineData("collision")]
    [InlineData("stopped")]
    [InlineData("channel-stopped")]
    public async Task GuestQueueUsesCurrentAdmissionAndCanonicalGuideNotCallerSuppliedText(
        string scenario
    )
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var interactions = new PortalInteractionService(
            context.Conversations,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            )
        );
        var participant = Guid.NewGuid();
        var submitted = await interactions.SendGuestFixedNoticeAsync(
            context.TenantId,
            participant,
            Guid.NewGuid(),
            WhatsAppGuestConsent.Notice,
            CancellationToken.None
        );
        var guest = new WhatsAppGuestSession
        {
            TenantId = context.TenantId,
            ParticipantId = participant,
            BindingDigest = Recipient,
            EvidenceId = Guid.NewGuid(),
            AdmittedAt = Now,
        };
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.Add(guest);
            await db.SaveChangesAsync();
            if (scenario == "stopped")
            {
                guest.StoppedAt = Now;
                await db.SaveChangesAsync();
            }
        }
        if (scenario == "channel-stopped")
        {
            await using var relationshipDb = context.Relationships.CreateDbContext();
            relationshipDb.WhatsAppJourneyContacts.Add(
                new WhatsAppJourneyContact
                {
                    TenantId = context.TenantId,
                    PhoneHmac = Recipient,
                    OptedInAt = Now.AddDays(-1),
                    OptedOutAt = Now,
                    LastInboundAt = Now,
                }
            );
            await relationshipDb.SaveChangesAsync();
        }
        var reply = submitted.Value;
        reply = scenario switch
        {
            "altered" => reply with { Content = [new("1.0", "TEXT", "unowned text", "en")] },
            "foreign" => reply with { MessageId = Guid.NewGuid() },
            "customer" => reply with { Actor = "CUSTOMER" },
            _ => reply,
        };
        var outbox = context.Outbox(new WhatsAppJourneyOptions { DispatchEnabled = true });
        if (scenario == "collision")
        {
            await outbox.QueueGuestDiscoveryAsync(guest, reply, Now, CancellationToken.None);
            await using (var db = context.Conversations.CreateDbContext())
            {
                var existing = await db.ConversationOutbox.SingleAsync();
                db.Entry(existing).Property(value => value.RecipientBindingDigest).CurrentValue =
                    new string('c', 64);
                await db.SaveChangesAsync();
            }
            await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() =>
                outbox.QueueGuestDiscoveryAsync(guest, reply, Now, CancellationToken.None)
            );
            await using var saved = context.Conversations.CreateDbContext();
            Assert.Single(await saved.ConversationOutbox.ToListAsync());
        }
        else if (scenario == "valid")
        {
            await outbox.QueueGuestDiscoveryAsync(guest, reply, Now, CancellationToken.None);
            await outbox.QueueGuestDiscoveryAsync(guest, reply, Now, CancellationToken.None);
            await using var db = context.Conversations.CreateDbContext();
            var row = Assert.Single(await db.ConversationOutbox.ToListAsync());
            Assert.Equal(reply.MessageId.ToString("D"), row.AggregateId);
            Assert.Equal(reply.Sequence, row.Sequence);
        }
        else
        {
            if (scenario is "stopped" or "channel-stopped")
                await Assert.ThrowsAsync<ConversationStoppedException>(() =>
                    outbox.QueueGuestDiscoveryAsync(guest, reply, Now, CancellationToken.None)
                );
            else
                await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                    outbox.QueueGuestDiscoveryAsync(guest, reply, Now, CancellationToken.None)
                );
            await using var db = context.Conversations.CreateDbContext();
            Assert.Empty(await db.ConversationOutbox.ToListAsync());
        }
    }

    [Fact]
    public async Task GuestDiscoveryReplyRequiresCurrentConsentAtQueueAndDispatch()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var guest = new WhatsAppGuestSession
        {
            TenantId = context.TenantId,
            BindingDigest = Recipient,
            EvidenceId = Guid.NewGuid(),
            AdmittedAt = Now,
            LastInboundAt = Now,
            ServiceConsentAt = Now,
            ServiceConsentEvidenceId = Guid.NewGuid(),
            ServiceConsentNoticeVersion = WhatsAppGuestConsent.NoticeVersion,
        };
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.Add(guest);
            await db.SaveChangesAsync();
        }
        var interactions = new PortalInteractionService(
            context.Conversations,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            )
        );
        var messageId = Guid.NewGuid();
        var submission = await interactions.SendGuestNoticeAsync(
            guest.TenantId,
            guest.ParticipantId,
            messageId,
            new(
                "1.0",
                messageId,
                [new("1.0", "TEXT", "question", "en-IN")],
                "en-IN",
                "MARKETPLACE"
            ),
            "Private discovery response",
            CancellationToken.None
        );
        var outbox = context.Outbox(new WhatsAppJourneyOptions { DispatchEnabled = true });
        await using (var db = context.Conversations.CreateDbContext())
        {
            (await db.Set<WhatsAppGuestSession>().SingleAsync()).ServiceConsentNoticeVersion =
                "old";
            await db.SaveChangesAsync();
        }
        await Assert.ThrowsAsync<ConversationNotAccessibleException>(() =>
            outbox.QueueGuestDiscoveryAsync(
                guest,
                submission.Value.GuideMessage,
                Now,
                CancellationToken.None
            )
        );
        await using (var db = context.Conversations.CreateDbContext())
        {
            (await db.Set<WhatsAppGuestSession>().SingleAsync()).ServiceConsentNoticeVersion =
                WhatsAppGuestConsent.NoticeVersion;
            await db.SaveChangesAsync();
        }
        await outbox.QueueGuestDiscoveryAsync(
            guest,
            submission.Value.GuideMessage,
            Now,
            CancellationToken.None
        );
        await using (var db = context.Conversations.CreateDbContext())
        {
            (await db.Set<WhatsAppGuestSession>().SingleAsync()).ServiceConsentNoticeVersion =
                "old";
            await db.SaveChangesAsync();
        }
        var lease = Assert.IsType<WhatsAppOutboxLease>(
            await outbox.LeaseNextAsync("consent-check", Now, CancellationToken.None)
        );
        Assert.False(
            await outbox.BeginDispatchAsync(
                lease.OutboxId,
                "consent-check",
                Now,
                CancellationToken.None
            )
        );
    }

    [Theory]
    [InlineData(WhatsAppGuestConsent.Notice)]
    [InlineData(WhatsAppGuestTrafficBudget.UnsupportedContentNotice)]
    [InlineData(WhatsAppGuestTrafficBudget.MessageLimitNotice)]
    [InlineData(WhatsAppGuestTrafficBudget.GlobalRateLimitNotice)]
    [InlineData(WhatsAppGuestOperatingHours.ClosedNotice)]
    public async Task FixedServiceNoticesRemainAvailableBeforeConsent(string notice)
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var guest = new WhatsAppGuestSession
        {
            TenantId = context.TenantId,
            BindingDigest = Recipient,
            EvidenceId = Guid.NewGuid(),
            AdmittedAt = Now,
            LastInboundAt = Now,
        };
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.Add(guest);
            await db.SaveChangesAsync();
        }
        var interactions = new PortalInteractionService(
            context.Conversations,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            )
        );
        var reply = await interactions.SendGuestFixedNoticeAsync(
            guest.TenantId,
            guest.ParticipantId,
            Guid.NewGuid(),
            notice,
            CancellationToken.None
        );
        var outbox = context.Outbox(new WhatsAppJourneyOptions { DispatchEnabled = true });
        await outbox.QueueGuestDiscoveryAsync(guest, reply.Value, Now, CancellationToken.None);
        var lease = Assert.IsType<WhatsAppOutboxLease>(
            await outbox.LeaseNextAsync("pre-consent", Now, CancellationToken.None)
        );
        Assert.True(
            await outbox.BeginDispatchAsync(
                lease.OutboxId,
                "pre-consent",
                Now,
                CancellationToken.None
            )
        );
    }

    [Fact]
    public void GuestReplyDestinationIsEncryptedAndBoundToItsSenderDigest()
    {
        var protectedDestination = WhatsAppPhoneDestinationProtector.Protect(
            Credentials.SubjectKey,
            "+14155552671",
            Recipient
        );

        Assert.DoesNotContain("+14155552671", protectedDestination, StringComparison.Ordinal);
        Assert.Equal(
            "+14155552671",
            WhatsAppPhoneDestinationProtector.Unprotect(
                Credentials.SubjectKey,
                protectedDestination,
                Recipient
            )
        );
        Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
            WhatsAppPhoneDestinationProtector.Unprotect(
                Credentials.SubjectKey,
                protectedDestination,
                new string('c', 64)
            )
        );
        var tampered = protectedDestination.Split('.');
        var tag = Convert.FromBase64String(tampered[2]);
        tag[0] ^= 0x01;
        tampered[2] = Convert.ToBase64String(tag);
        Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
            WhatsAppPhoneDestinationProtector.Unprotect(
                Credentials.SubjectKey,
                string.Join('.', tampered),
                Recipient
            )
        );
    }

    [Theory]
    [InlineData(false, false, false, false, false, false, false)]
    [InlineData(true, false, false, false, false, false, false)]
    [InlineData(false, true, false, false, false, false, false)]
    [InlineData(false, false, true, false, false, false, false)]
    [InlineData(false, false, false, true, false, false, false)]
    [InlineData(false, false, false, false, true, false, false)]
    [InlineData(false, false, false, false, false, true, false)]
    [InlineData(false, false, false, false, false, false, true)]
    public async Task GuestGuideRepliesUseSenderRouteAndCurrentStop(
        bool stopped,
        bool missingDestination,
        bool relationshipContactOptedOut,
        bool staleConsent,
        bool changedDestination,
        bool renewedDestination,
        bool removedDestination
    )
    {
        var fixture = await SeedAsync();
        var guestSubject = new string('c', 64);
        fixture.Options.Authority = fixture.Options.Authority! with
        {
            AllowProvisionalOnboarding = true,
            RecipientBindingDigest = guestSubject,
            MaximumMessages = 20,
            MaximumMessagesPerMinute = 20,
        };
        var context = new PortalInteractionContext
        {
            TenantId = fixture.Request.TenantId,
            ParticipantId = Guid.NewGuid(),
        };
        var content = JsonSerializer.Serialize(
            new[]
            {
                new ConversationTextBlockV1("1.0", "TEXT", "Shared onboarding reply", "en-IN"),
            },
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );
        var guide = new PortalInteractionMessage
        {
            TenantId = context.TenantId,
            ParticipantId = context.ParticipantId,
            ContextId = context.ContextId,
            Sequence = 1,
            Actor = "GUIDE",
            ContentJson = content,
            CurrentSurface = "MARKETPLACE",
        };
        await using (var db = fixture.Context.Conversations.CreateDbContext())
        {
            db.ConversationOutbox.Remove(await db.ConversationOutbox.SingleAsync());
            await db.SaveChangesAsync();
            db.PortalInteractionContexts.Add(context);
            db.PortalInteractionMessages.Add(guide);
            db.Set<WhatsAppGuestSession>()
                .Add(
                    new()
                    {
                        TenantId = context.TenantId,
                        ParticipantId = context.ParticipantId,
                        BindingDigest = guestSubject,
                        ProtectedDestination = missingDestination
                            ? null
                            : WhatsAppPhoneDestinationProtector.Protect(
                                Credentials.SubjectKey,
                                "+14155552671",
                                guestSubject
                            ),
                        EvidenceId = Guid.NewGuid(),
                        AdmittedAt = Now,
                        ServiceConsentAt = Now,
                        ServiceConsentEvidenceId = Guid.NewGuid(),
                        ServiceConsentNoticeVersion = staleConsent
                            ? "retired"
                            : WhatsAppGuestConsent.NoticeVersion,
                        LastInboundAt = Now,
                        StoppedAt = stopped ? Now : null,
                    }
                );
            db.ConversationOutbox.Add(
                new()
                {
                    OutboxId = fixture.Request.OutboxId,
                    Environment = "demo",
                    TenantId = context.TenantId,
                    PortalContextId = context.ContextId,
                    Sequence = 1,
                    AggregateId = guide.MessageId.ToString("D"),
                    IdempotencyKey = guide.MessageId,
                    OperationFamily = "WHATSAPP_OUTBOUND",
                    PayloadReference = $"portal-message:{guide.MessageId:D}",
                    PayloadDigest = Hash(content),
                    Purpose = "WHATSAPP_GUEST_DISCOVERY",
                    RecipientBindingDigest = guestSubject,
                    CreatedAt = Now,
                    UpdatedAt = Now,
                    State = "DISPATCHING",
                    AttemptNumber = 1,
                    LeaseOwner = "fixture",
                    LeaseExpiresAt = Now.AddSeconds(60),
                }
            );
            await db.SaveChangesAsync();
        }
        if (relationshipContactOptedOut)
        {
            await using var relationshipDb = fixture.Context.Relationships.CreateDbContext();
            relationshipDb.WhatsAppJourneyContacts.Add(
                new WhatsAppJourneyContact
                {
                    TenantId = fixture.Request.TenantId,
                    PhoneHmac = guestSubject,
                    OptedInAt = Now.AddDays(-1),
                    OptedOutAt = Now,
                    LastInboundAt = Now,
                }
            );
            await relationshipDb.SaveChangesAsync();
        }
        fixture = fixture with
        {
            Request = fixture.Request with
            {
                RelationshipId = null,
                ConversationId = null,
                PayloadReference = $"portal-message:{guide.MessageId:D}",
                PayloadDigest = Hash(content),
            },
        };
        var calls = 0;
        using var factory = new ClientFactory(
            async (request, ct) =>
            {
                calls++;
                using var body = JsonDocument.Parse(await request.Content!.ReadAsStringAsync(ct));
                Assert.Equal("text", body.RootElement.GetProperty("type").GetString());
                Assert.Equal(
                    "Shared onboarding reply",
                    body.RootElement.GetProperty("text").GetProperty("body").GetString()
                );
                Assert.Equal("14155552671", body.RootElement.GetProperty("to").GetString());
                return Json(new { messages = new[] { new { id = "wamid.onboarding" } } });
            }
        );
        var credentials = new Credentials(async () =>
        {
            if (!changedDestination && !renewedDestination && !removedDestination)
                return;
            await using var db = fixture.Context.Conversations.CreateDbContext();
            var guest = await db.Set<WhatsAppGuestSession>().SingleAsync();
            guest.ProtectedDestination = removedDestination
                ? null
                : WhatsAppPhoneDestinationProtector.Protect(
                    Credentials.SubjectKey,
                    changedDestination ? "+14155552672" : "+14155552671",
                    guestSubject
                );
            await db.SaveChangesAsync();
        });
        if (
            stopped
            || missingDestination
            || relationshipContactOptedOut
            || staleConsent
            || changedDestination
            || removedDestination
        )
        {
            var failure = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                Adapter(fixture, factory, credentials: credentials)
                    .DispatchAsync(fixture.Request, CancellationToken.None)
            );
            Assert.Equal(
                missingDestination && !relationshipContactOptedOut ? "PHONE_DESTINATION_UNAVAILABLE"
                    : changedDestination || removedDestination ? "RECIPIENT_DESTINATION_CHANGED"
                    : "RECIPIENT_ELIGIBILITY_REVOKED",
                failure.ReasonCode
            );
        }
        else
        {
            var result = await Adapter(fixture, factory, credentials: credentials)
                .DispatchAsync(fixture.Request, CancellationToken.None);
            Assert.Equal("PROVIDER_ACCEPTED", result.State);
            await using (var budgetDb = fixture.Context.Conversations.CreateDbContext())
            {
                var reserved = Assert.Single(
                    await budgetDb.WhatsAppGuestTrafficEvents.ToListAsync()
                );
                Assert.Equal("OUTBOUND", reserved.EventType);
                Assert.Equal(guestSubject, reserved.BindingDigest);
            }
            var guestBudget = new WhatsAppGuestTrafficBudget(
                fixture.Context.Conversations,
                fixture.Gate,
                fixture.Clock
            );
            foreach (var index in Enumerable.Range(0, 8))
                Assert.Equal(
                    index == 7
                        ? WhatsAppGuestTrafficNotice.GuestMessageLimit
                        : WhatsAppGuestTrafficNotice.None,
                    await guestBudget.ReserveInboundAsync(
                        fixture.Request.TenantId,
                        guestSubject,
                        $"inbound-{index}",
                        false,
                        CancellationToken.None
                    )
                );
            var exhausted = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                guestBudget.ReserveInboundAsync(
                    fixture.Request.TenantId,
                    guestSubject,
                    "inbound-limit",
                    false,
                    CancellationToken.None
                )
            );
            Assert.Equal("GUEST_MESSAGE_LIMIT_REACHED", exhausted.ReasonCode);
            var replay = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                Adapter(fixture, factory).DispatchAsync(fixture.Request, CancellationToken.None)
            );
            Assert.Equal("OUTBOUND_ALREADY_RESERVED", replay.ReasonCode);
            await fixture
                .Context.Outbox()
                .RecordResultAsync(
                    fixture.Request.OutboxId,
                    "fixture",
                    result,
                    CancellationToken.None
                );
            await fixture
                .Context.Outbox()
                .RecordProviderStatusAsync(
                    new(
                        "event:onboarding",
                        "wamid.onboarding",
                        "DELIVERED",
                        Now,
                        Hash("status:onboarding")
                    ),
                    CancellationToken.None
                );
            var reconciled = await Adapter(fixture, factory)
                .ReconcileAsync(fixture.Request, CancellationToken.None);
            Assert.Equal("DELIVERED", reconciled.State);
            await using var deliveries = fixture.Context.Conversations.CreateDbContext();
            var observations = await deliveries.DeliveryObservations.ToListAsync();
            Assert.Equal(2, observations.Count);
            Assert.All(
                observations,
                value =>
                {
                    Assert.Null(value.RelationshipId);
                    Assert.Null(value.MessageId);
                    Assert.Equal(context.ContextId, value.PortalContextId);
                    Assert.Equal(guide.MessageId, value.PortalMessageId);
                }
            );
        }
        Assert.Equal(
            stopped
            || missingDestination
            || relationshipContactOptedOut
            || staleConsent
            || changedDestination
            || removedDestination
                ? 0
                : 1,
            calls
        );
        await using var saved = fixture.Context.Conversations.CreateDbContext();
        Assert.Equal(
            stopped || missingDestination || relationshipContactOptedOut || staleConsent ? 0 : 1,
            await saved.Set<WhatsAppTrafficReservation>().CountAsync()
        );
    }

    [Theory]
    [InlineData(
        """[{"SchemaVersion":"1.0","BlockType":"MEDIA","Text":"not an admitted text projection"}]"""
    )]
    [InlineData("""[{"SchemaVersion":"2.0","BlockType":"TEXT","Text":"unsupported version"}]""")]
    [InlineData("""[{"SchemaVersion":"1.0","Text":"missing block type"}]""")]
    [InlineData(
        """[{"SchemaVersion":"1.0","BlockType":"TEXT","Text":"first","Text":"overridden"}]"""
    )]
    [InlineData(
        """[{"SchemaVersion":"1.0","BlockType":"TEXT","Text":"body","MediaUrl":"https://example.test"}]"""
    )]
    [InlineData(
        """[{"schemaVersion":"1.0","blockType":"TEXT","text":"first","Text":"overridden"}]"""
    )]
    [InlineData("""[{"schemaVersion":"1.0","blockType":"TEXT","text":"body\u0000"}]""")]
    public async Task UnsupportedCanonicalBlocksCannotBecomeProviderText(string contentJson)
    {
        var fixture = await SeedAsync();
        await using (var db = fixture.Context.Conversations.CreateDbContext())
        {
            var message = await db.Messages.SingleAsync();
            message.ContentJson = contentJson;
            await db.SaveChangesAsync();
        }
        var calls = 0;
        using var factory = new ClientFactory(
            (_, _) =>
            {
                calls++;
                throw new InvalidOperationException(
                    "Unsupported canonical blocks must not leave the platform."
                );
            }
        );

        var failure = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Adapter(fixture, factory).DispatchAsync(fixture.Request, CancellationToken.None)
        );

        Assert.Equal("MESSAGE_PROJECTION_DENIED", failure.ReasonCode);
        Assert.Equal(0, calls);
        await using var saved = fixture.Context.Conversations.CreateDbContext();
        Assert.Empty(saved.Set<WhatsAppTrafficReservation>());
    }

    [Fact]
    public async Task SharedCamelCaseCanonicalTextReachesTheExistingProviderTransport()
    {
        var fixture = await SeedAsync();
        await using (var db = fixture.Context.Conversations.CreateDbContext())
        {
            var message = await db.Messages.SingleAsync();
            var content = JsonSerializer.Deserialize<ConversationTextBlockV1[]>(
                message.ContentJson
            )!;
            message.ContentJson = JsonSerializer.Serialize(
                content,
                new JsonSerializerOptions(JsonSerializerDefaults.Web)
            );
            await db.SaveChangesAsync();
        }
        var calls = 0;
        using var factory = new ClientFactory(
            (_, _) =>
            {
                calls++;
                return Task.FromResult(
                    new HttpResponseMessage(HttpStatusCode.OK)
                    {
                        Content = JsonContent.Create(
                            new { messages = new[] { new { id = "wamid.shared-text-contract" } } }
                        ),
                    }
                );
            }
        );
        var outcome = await Adapter(fixture, factory)
            .DispatchAsync(fixture.Request, CancellationToken.None);
        Assert.Equal("PROVIDER_ACCEPTED", outcome.State);
        Assert.Equal(1, calls);
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task ConsentAndServiceWindowAreRecheckedAfterProtectedReads(bool optOut)
    {
        var fixture = await SeedAsync();
        var calls = 0;
        using var factory = new ClientFactory(
            (_, _) =>
            {
                calls++;
                throw new InvalidOperationException(
                    "Ineligible recipient must not reach provider egress."
                );
            }
        );
        var credentials = new Credentials(async () =>
        {
            await using var db = fixture.Context.Relationships.CreateDbContext();
            var contact = await db.WhatsAppJourneyContacts.SingleAsync();
            if (optOut)
                contact.OptedOutAt = Now;
            else
                contact.LastInboundAt = Now.AddHours(-25);
            await db.SaveChangesAsync();
        });
        var failure = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Adapter(fixture, factory, credentials: credentials)
                .DispatchAsync(fixture.Request, CancellationToken.None)
        );
        Assert.Equal("RECIPIENT_ELIGIBILITY_REVOKED", failure.ReasonCode);
        Assert.Equal(0, calls);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task ChangedBoundConversationPreventsProviderDispatch(
        bool changeDuringProtectedRead
    )
    {
        var fixture = await SeedAsync();
        async Task ReplaceBindingConversation()
        {
            await using var db = fixture.Context.Relationships.CreateDbContext();
            var binding = await db.ChannelBindings.SingleAsync();
            binding.ConversationId = Guid.NewGuid().ToString("D");
            await db.SaveChangesAsync();
        }

        if (!changeDuringProtectedRead)
            await ReplaceBindingConversation();
        var calls = 0;
        using var factory = new ClientFactory(
            (_, _) =>
            {
                calls++;
                throw new InvalidOperationException(
                    "Stale conversation must not reach provider egress."
                );
            }
        );
        var credentials = new Credentials(
            changeDuringProtectedRead ? ReplaceBindingConversation : null
        );
        var failure = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Adapter(fixture, factory, credentials: credentials)
                .DispatchAsync(fixture.Request, CancellationToken.None)
        );
        Assert.Equal("RECIPIENT_ELIGIBILITY_REVOKED", failure.ReasonCode);
        Assert.Equal(0, calls);
    }

    [Theory]
    [InlineData("whatsapp-demo.example.com", "/", "GET", false)]
    [InlineData("whatsapp-demo.example.com", "/health/live", "GET", false)]
    [InlineData("whatsapp-demo.example.com", "/api/v1/channels/whatsapp/webhook", "PUT", false)]
    [InlineData("whatsapp-demo.example.com", "/api/v1/channels/whatsapp/webhook", "GET", true)]
    [InlineData("whatsapp-demo.example.com", "/api/v1/channels/whatsapp/webhook", "POST", true)]
    [InlineData("cp.demo.waooaw.com", "/api/v1/employment/relationships", "GET", true)]
    public async Task DedicatedCallbackHostExposesOnlyItsExactGetAndPostRoute(
        string host,
        string path,
        string method,
        bool expectedNext
    )
    {
        var invoked = false;
        var middleware = new WhatsAppCallbackHostMiddleware(_ =>
        {
            invoked = true;
            return Task.CompletedTask;
        });
        var context = new DefaultHttpContext();
        context.Request.Host = new HostString(host);
        context.Request.Path = path;
        context.Request.Method = method;
        await middleware.InvokeAsync(
            context,
            Options.Create(
                new WhatsAppJourneyOptions { CallbackHost = "whatsapp-demo.example.com" }
            )
        );
        Assert.Equal(expectedNext, invoked);
        if (!expectedNext)
            Assert.Equal(404, context.Response.StatusCode);
    }

    [Fact]
    public async Task KeyVaultReadsExactVersionsEveryTimeAndBoundsCredentialLifetime()
    {
        var calls = 0;
        using var factory = new ClientFactory(
            async (request, token) =>
            {
                calls++;
                await Task.CompletedTask;
                Assert.False(token.IsCancellationRequested);
                return SecretResponse(request);
            }
        );
        var reader = Reader(factory);
        var first = await reader.ReadAsync(CancellationToken.None);
        var second = await reader.ReadAsync(CancellationToken.None);
        Assert.Equal(6, calls);
        Assert.Equal(Now.AddMinutes(5), first.ValidUntil);
        Assert.Equal(first.ValidUntil, second.ValidUntil);
        Assert.Equal(nameof(WhatsAppProviderCredentials), first.ToString());
        Assert.Equal(nameof(WhatsAppProviderBinding), first.Binding.ToString());
    }

    [Fact]
    public async Task NonexpiringOutboundTokenRetainsFiveMinuteCredentialLease()
    {
        using var factory = new ClientFactory(
            (request, _) => Task.FromResult(SecretResponse(request, "outbound-no-expiry"))
        );
        var credentials = await Reader(factory).ReadAsync(CancellationToken.None);
        Assert.Equal(Now.AddMinutes(5), credentials.ValidUntil);
    }

    [Theory]
    [InlineData("no-expiry")]
    [InlineData("outbound-expired")]
    [InlineData("outbound-disabled")]
    [InlineData("outbound-future")]
    [InlineData("outbound-invalid-expiry")]
    public async Task NonexpiringExceptionDoesNotWeakenOtherSecretControls(string failure)
    {
        using var factory = new ClientFactory(
            (request, _) => Task.FromResult(SecretResponse(request, failure))
        );
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Reader(factory).ReadAsync(CancellationToken.None)
        );
    }

    [Theory]
    [InlineData("disabled")]
    [InlineData("expired")]
    [InlineData("wrong-version")]
    [InlineData("future")]
    [InlineData("wrong-resource")]
    [InlineData("oversized")]
    [InlineData("redirect")]
    [InlineData("wrong-shape")]
    public async Task SecretFailuresNeverReturnCredentialsOrFollowAnAlternateLocation(
        string failure
    )
    {
        var calls = 0;
        using var factory = new ClientFactory(
            (request, _) =>
            {
                calls++;
                return Task.FromResult(SecretResponse(request, failure));
            }
        );
        var error = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Reader(factory).ReadAsync(CancellationToken.None)
        );
        Assert.Matches("^[A-Z_]+$", error.ReasonCode);
        Assert.InRange(calls, 1, 2);
    }

    [Fact]
    public async Task InvalidVaultAndNonlocalIdentityEndpointAreDeniedBeforeAnyRequest()
    {
        var calls = 0;
        using var factory = new ClientFactory(
            (_, _) =>
            {
                calls++;
                throw new InvalidOperationException("Network must not be used.");
            }
        );
        var options = ProviderOptions();
        options.VaultHost = "kv-waooaw-uat.vault.azure.net";
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Reader(factory, options).ReadAsync(CancellationToken.None)
        );
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Reader(factory, endpoint: "https://example.invalid/token")
                .ReadAsync(CancellationToken.None)
        );
        Assert.Equal(0, calls);
    }

    [Fact]
    public async Task CallerCancellationIsNotConvertedToProviderSuccessOrDefaultCredentials()
    {
        using var cancellation = new CancellationTokenSource();
        using var factory = new ClientFactory(
            (_, token) =>
            {
                cancellation.Cancel();
                token.ThrowIfCancellationRequested();
                throw new InvalidOperationException("Cancellation was required.");
            }
        );
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            Reader(factory).ReadAsync(cancellation.Token)
        );
    }

    [Fact]
    public async Task EachWebhookPurposeReadsOnlyItsOwnPinnedSecretAndNoOutboundToken()
    {
        var paths = new List<string>();
        using var factory = new ClientFactory(
            (request, _) =>
            {
                paths.Add(request.RequestUri!.AbsolutePath);
                return Task.FromResult(SecretResponse(request));
            }
        );
        var reader = Reader(factory);
        await reader.ReadVerifyTokenAsync(CancellationToken.None);
        await reader.ReadAppSecretAsync(CancellationToken.None);
        await reader.ReadPhoneSubjectKeyAsync(CancellationToken.None);
        await reader.ReadSenderBindingAsync(CancellationToken.None);
        Assert.Equal(8, paths.Count);
        Assert.Single(
            paths,
            value => value.Contains("/whatsapp-verify-token/", StringComparison.Ordinal)
        );
        Assert.Single(
            paths,
            value => value.Contains("/whatsapp-app-secret/", StringComparison.Ordinal)
        );
        Assert.Single(
            paths,
            value => value.Contains("/whatsapp-provider-binding/", StringComparison.Ordinal)
        );
        Assert.Single(
            paths,
            value => value.Contains("/whatsapp-phone-subject-hmac/", StringComparison.Ordinal)
        );
        Assert.DoesNotContain(
            paths,
            value =>
                value.Contains("outbound", StringComparison.Ordinal)
                || value.Contains("media", StringComparison.Ordinal)
        );
    }

    [Fact]
    public async Task ProtectedVerificationDoesNotRequireBusinessActivationOrLegacyIdentityKeys()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var options = new WhatsAppJourneyOptions
        {
            VerificationEnabled = true,
            CallbackHost = "whatsapp.demo.example",
        };
        var protectedSecrets = new WebhookCredentials();
        var service = new WhatsAppJourneyService(
            context.Relationships,
            new ForbiddenEvidence(),
            Options.Create(options),
            webhookCredentials: protectedSecrets
        );
        var controller = new WhatsAppJourneyController(
            service,
            Options.Create(options),
            Options.Create(new Wc120ConversationOptions()),
            webhookCredentials: protectedSecrets
        )
        {
            ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() },
        };
        controller.Request.Host = new HostString(options.CallbackHost);
        controller.Request.QueryString = new QueryString(
            "?hub.mode=subscribe&hub.verify_token="
                + new string('v', 32)
                + "&hub.challenge=challenge"
        );
        var response = await controller.VerifyAsync(CancellationToken.None);
        Assert.Equal("challenge", Assert.IsType<ContentResult>(response).Content);
        Assert.Equal(1, protectedSecrets.VerifyReads);
        Assert.Equal(0, protectedSecrets.AppReads);
        var body = Encoding.UTF8.GetBytes("{}");
        controller.Request.ContentType = "application/json";
        controller.Request.Body = new MemoryStream(body);
        controller.Request.Headers["X-Hub-Signature-256"] =
            "sha256="
            + Convert.ToHexStringLower(
                HMACSHA256.HashData(Encoding.UTF8.GetBytes(protectedSecrets.AppSecret), body)
            );
        Assert.Equal(
            503,
            Assert
                .IsType<StatusCodeResult>(await controller.ReceiveAsync(CancellationToken.None))
                .StatusCode
        );
        Assert.Equal(1, protectedSecrets.AppReads);
        await using var db = context.Relationships.CreateDbContext();
        Assert.Empty(await db.WhatsAppJourneyContacts.ToListAsync());
    }

    [Fact]
    public async Task CanonicalProgressReachesProviderAsOneSystemReplyWithoutExecution()
    {
        var fixture = await SeedAsync();
        await using (var db = fixture.Context.Conversations.CreateDbContext())
        {
            db.Messages.RemoveRange(await db.Messages.ToListAsync());
            db.ConversationOutbox.RemoveRange(await db.ConversationOutbox.ToListAsync());
            await db.SaveChangesAsync();
        }
        var journey = new WhatsAppJourneyService(
            fixture.Context.Relationships,
            new ForbiddenEvidence(),
            Options.Create(new WhatsAppJourneyOptions()),
            conversationDbFactory: fixture.Context.Conversations,
            conversationOptions: Options.Create(fixture.Context.Options),
            stopFence: fixture.Context.StopFence,
            engagementWorkspace: new CustomerEngagementWorkspaceService(
                fixture.Context.Relationships,
                new EphemeralDataProtectionProvider(),
                new ConversationConstitutionalGatewayStub()
            ),
            outboundContributions: fixture.Context.Outbound(),
            clock: fixture.Clock
        );
        var proof = new VerifiedPhoneIdentityProof(
            "progress-provider",
            Recipient,
            "Show my progress",
            null,
            "signed-test",
            "AAL1_CHANNEL",
            Now,
            Now,
            Now.AddMinutes(1),
            Guid.NewGuid()
        )
        {
            Environment = "demo",
            AppBindingDigest = fixture.Context.Options.AppBindingDigest,
            PayloadDigest = Hash("progress-provider-payload"),
        };
        var receipt = await journey.ReceiveVerifiedAsync(proof, CancellationToken.None);
        Assert.True((await journey.ReceiveVerifiedAsync(proof, CancellationToken.None)).Replayed);
        var outbox = fixture.Context.Outbox();
        var lease = Assert.IsType<WhatsAppOutboxLease>(
            await outbox.LeaseNextAsync("guidance-worker", Now, CancellationToken.None)
        );
        Assert.True(
            await outbox.BeginDispatchAsync(
                lease.OutboxId,
                "guidance-worker",
                Now,
                CancellationToken.None
            )
        );
        var request = new WhatsAppProviderDispatchRequest(
            lease.OutboxId,
            lease.Environment,
            lease.TenantId,
            lease.RelationshipId,
            lease.ConversationId,
            lease.Sequence,
            lease.PayloadReference,
            lease.PayloadDigest,
            lease.AttemptNumber
        );
        var calls = 0;
        using var clients = new ClientFactory(
            async (submission, token) =>
            {
                calls++;
                using var body = JsonDocument.Parse(
                    await submission.Content!.ReadAsStringAsync(token)
                );
                Assert.Equal(
                    receipt.Reply,
                    body.RootElement.GetProperty("text").GetProperty("body").GetString()
                );
                Assert.Equal(
                    Binding().RecipientPhoneNumber.TrimStart('+'),
                    body.RootElement.GetProperty("to").GetString()
                );
                return Json(new { messages = new[] { new { id = "wamid.guidance" } } });
            }
        );
        var result = await Adapter(fixture, clients).DispatchAsync(request, CancellationToken.None);
        Assert.Equal("PROVIDER_ACCEPTED", result.State);
        await outbox.RecordResultAsync(
            lease.OutboxId,
            "guidance-worker",
            result,
            CancellationToken.None
        );
        Assert.Null(await outbox.LeaseNextAsync("another-worker", Now, CancellationToken.None));
        Assert.Equal(1, calls);
        await using var check = fixture.Context.Conversations.CreateDbContext();
        Assert.Equal("SYSTEM", (await check.Messages.SingleAsync()).Actor);
        Assert.Empty(await check.Executions.ToListAsync());
        Assert.Single(await check.Events.ToListAsync());
        Assert.Single(await check.ConversationOutbox.ToListAsync());
    }

    [Fact]
    public async Task RelationshipReplyCannotFallBackToAnotherRecipientsPilotDestination()
    {
        var fixture = await SeedAsync(recipient: new string('c', 64));
        using var clients = new ClientFactory(
            (_, _) => throw new InvalidOperationException("No provider request is permitted.")
        );
        var denied = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Adapter(fixture, clients).DispatchAsync(fixture.Request, CancellationToken.None)
        );
        Assert.Equal("RECIPIENT_DESTINATION_MISMATCH", denied.ReasonCode);
        await using var check = fixture.Context.Conversations.CreateDbContext();
        Assert.Empty(await check.Set<WhatsAppTrafficReservation>().ToListAsync());
    }

    [Theory]
    [InlineData("valid")]
    [InlineData("missing")]
    [InlineData("expired")]
    [InlineData("future")]
    [InlineData("tampered")]
    [InlineData("replaced")]
    [InlineData("revoked")]
    [InlineData("member-revoked")]
    [InlineData("pilot-only")]
    public async Task PublicRelationshipRepliesUseOnlyFreshVerifiedOwnedDestinations(
        string scenario
    )
    {
        var phone = "+14155552671";
        var recipient = Convert.ToHexStringLower(
            HMACSHA256.HashData(
                Encoding.UTF8.GetBytes(Credentials.SubjectKey),
                Encoding.UTF8.GetBytes(phone)
            )
        );
        var fixture = await SeedAsync(recipient: recipient);
        fixture.Options.PublicAdmissionIdentityKeyAvailable = true;
        fixture.Options.Authority = fixture.Options.Authority! with
        {
            AllowPublicAdmission = scenario != "pilot-only",
            AllowProvisionalOnboarding = true,
        };
        await using (var db = fixture.Context.Relationships.CreateDbContext())
        {
            var contact = await db.WhatsAppJourneyContacts.SingleAsync();
            if (scenario != "missing")
            {
                contact.ProtectedDestination = WhatsAppPhoneDestinationProtector.Protect(
                    Credentials.SubjectKey,
                    phone,
                    scenario == "tampered" ? Recipient : recipient
                );
                contact.DestinationVerifiedAt = scenario switch
                {
                    "expired" => Now.AddHours(-25),
                    "future" => Now.AddSeconds(1),
                    _ => Now,
                };
            }
            await db.SaveChangesAsync();
        }
        var calls = 0;
        using var clients = new ClientFactory(
            async (request, ct) =>
            {
                calls++;
                var body = await request.Content!.ReadAsStringAsync(ct);
                using var document = JsonDocument.Parse(body);
                Assert.Equal(
                    phone.TrimStart('+'),
                    document.RootElement.GetProperty("to").GetString()
                );
                Assert.Equal(
                    "Canonical shared-API reply",
                    document.RootElement.GetProperty("text").GetProperty("body").GetString()
                );
                return Json(new { messages = new[] { new { id = "synthetic-provider-reply" } } });
            }
        );
        var credentials = new Credentials(async () =>
        {
            if (scenario is not ("replaced" or "revoked" or "member-revoked"))
                return;
            await using var db = fixture.Context.Relationships.CreateDbContext();
            if (scenario == "replaced")
            {
                var contact = await db.WhatsAppJourneyContacts.SingleAsync();
                contact.ProtectedDestination = WhatsAppPhoneDestinationProtector.Protect(
                    Credentials.SubjectKey,
                    phone,
                    recipient
                );
            }
            else if (scenario == "member-revoked")
                (await db.RelationshipParticipants.SingleAsync()).Status = "REVOKED";
            else
                (await db.ChannelBindings.SingleAsync()).Status = "REVOKED";
            await db.SaveChangesAsync();
        });
        if (scenario == "valid")
        {
            var result = await Adapter(fixture, clients, credentials: credentials)
                .DispatchAsync(fixture.Request, CancellationToken.None);
            Assert.Equal("PROVIDER_ACCEPTED", result.State);
            Assert.Equal(1, calls);
            await using var db = fixture.Context.Conversations.CreateDbContext();
            Assert.Single(await db.Set<WhatsAppTrafficReservation>().ToListAsync());
        }
        else
        {
            await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                Adapter(fixture, clients, credentials: credentials)
                    .DispatchAsync(fixture.Request, CancellationToken.None)
            );
            Assert.Equal(0, calls);
        }
    }

    [Fact]
    public async Task PublicReservationCannotSubstituteAnotherSenderOrAnotherDispatchTuple()
    {
        var recipient = new string('c', 64);
        var fixture = await SeedAsync(recipient: recipient);
        fixture.Options.PublicAdmissionIdentityKeyAvailable = true;
        fixture.Options.Authority = fixture.Options.Authority! with
        {
            AllowPublicAdmission = true,
            AllowProvisionalOnboarding = true,
        };
        var budget = new WhatsAppTrafficBudget(
            fixture.Context.Conversations,
            fixture.Gate,
            fixture.Clock
        );
        var wrongSender = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveAsync(fixture.Request, Recipient, CancellationToken.None)
        );
        Assert.Equal("RECIPIENT_DENIED", wrongSender.ReasonCode);
        var wrongTuple = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveAsync(
                fixture.Request with
                {
                    RelationshipId = Guid.NewGuid(),
                },
                recipient,
                CancellationToken.None
            )
        );
        Assert.Equal("OUTBOUND_LEASE_EXPIRED", wrongTuple.ReasonCode);
        await using var check = fixture.Context.Conversations.CreateDbContext();
        Assert.Empty(await check.Set<WhatsAppTrafficReservation>().ToListAsync());
    }

    [Fact]
    public async Task RelationshipProgressIsCanonicalOutboundWithoutProfessionalExecution()
    {
        var context = await Wc120FitnessContext.CreateAsync(
            workspaceVersion: "current-workspace-42"
        );
        var now = DateTimeOffset.UtcNow;
        await context.SeedWhatsAppEligibilityAsync(Recipient, now);
        var service = new WhatsAppJourneyService(
            context.Relationships,
            new ForbiddenEvidence(),
            Options.Create(new WhatsAppJourneyOptions()),
            conversationDbFactory: context.Conversations,
            conversationOptions: Options.Create(context.Options),
            stopFence: context.StopFence,
            engagementWorkspace: new CustomerEngagementWorkspaceService(
                context.Relationships,
                new EphemeralDataProtectionProvider(),
                new ConversationConstitutionalGatewayStub()
            ),
            outboundContributions: context.Outbound()
        );
        var proof = new VerifiedPhoneIdentityProof(
            "progress-canonical",
            Recipient,
            "Show my progress",
            null,
            "signed-test",
            "AAL1_CHANNEL",
            now,
            now,
            now.AddMinutes(5),
            Guid.NewGuid()
        )
        {
            Environment = context.Options.Environment,
            AppBindingDigest = context.Options.AppBindingDigest,
            PayloadDigest = Hash("progress canonical signed payload"),
        };
        var first = await service.ReceiveVerifiedAsync(proof, CancellationToken.None);
        Assert.True((await service.ReceiveVerifiedAsync(proof, CancellationToken.None)).Replayed);
        await using var db = context.Conversations.CreateDbContext();
        var message = await db.Messages.SingleAsync();
        Assert.Equal("SYSTEM", message.Actor);
        Assert.Equal(
            first.Reply,
            Assert
                .Single(
                    Assert.IsType<ConversationTextBlockV1[]>(
                        JsonSerializer.Deserialize<ConversationTextBlockV1[]>(message.ContentJson)
                    )
                )
                .Text
        );
        Assert.Equal("INFORM", message.DialogueAct);
        Assert.Equal(context.WhatsAppConversationId, message.ConversationId);
        Assert.Empty(await db.Executions.ToListAsync());
        var queued = await db.ConversationOutbox.SingleAsync();
        Assert.Equal(message.MessageId.ToString("D"), queued.AggregateId);
        Assert.Equal(context.WhatsAppConversationId, queued.ConversationId);
        var completed = await db.Events.SingleAsync();
        Assert.Equal("message.completed", completed.EventType);
        Assert.Equal(message.MessageId, completed.MessageId);
        Assert.Equal(
            "WHATSAPP",
            JsonDocument
                .Parse(completed.DataJson)
                .RootElement.GetProperty("message")
                .GetProperty("channel")
                .GetString()
        );
    }

    [Theory]
    [InlineData("TIER_3_HIGH_RISK", "PORTAL_STEP_UP_REQUIRED")]
    [InlineData("TIER_4_CONSEQUENTIAL", "SECURE_PORTAL_REQUIRED")]
    [InlineData("TIER_2_MEDIUM_RISK", "CONFIRMATION_REQUIRED")]
    public async Task AssuranceGuidanceCommitsOnlyOneSystemReplyAndTimelineEvent(
        string risk,
        string expectedStatus
    )
    {
        var context = await Wc120FitnessContext.CreateAsync(workspaceVersion: "workspace-97");
        var now = DateTimeOffset.UtcNow;
        await context.SeedWhatsAppEligibilityAsync(Recipient, now);
        var service = new WhatsAppJourneyService(
            context.Relationships,
            new ForbiddenEvidence(),
            Options.Create(new WhatsAppJourneyOptions()),
            conversationDbFactory: context.Conversations,
            conversationOptions: Options.Create(context.Options),
            stopFence: context.StopFence,
            outboundContributions: context.Outbound()
        );
        var proof = new VerifiedPhoneIdentityProof(
            "assurance-canonical",
            Recipient,
            "A consequential request",
            risk,
            "signed-test",
            "AAL1_CHANNEL",
            now,
            now,
            now.AddMinutes(5),
            Guid.NewGuid()
        )
        {
            Environment = context.Options.Environment,
            AppBindingDigest = context.Options.AppBindingDigest,
            PayloadDigest = Hash("assurance signed payload"),
        };
        var first = await service.ReceiveVerifiedAsync(proof, CancellationToken.None);
        Assert.Equal(expectedStatus, first.Status);
        Assert.True((await service.ReceiveVerifiedAsync(proof, CancellationToken.None)).Replayed);
        await using var db = context.Conversations.CreateDbContext();
        var message = await db.Messages.SingleAsync();
        Assert.Equal("SYSTEM", message.Actor);
        Assert.Equal(
            first.Reply,
            Assert
                .Single(
                    Assert.IsType<ConversationTextBlockV1[]>(
                        JsonSerializer.Deserialize<ConversationTextBlockV1[]>(message.ContentJson)
                    )
                )
                .Text
        );
        Assert.Equal("PENDING", message.EvidenceState);
        Assert.Empty(await db.Executions.ToListAsync());
        Assert.Single(await db.ConversationOutbox.ToListAsync());
        Assert.Single(await db.Events.ToListAsync());
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task AmbiguousSenderBindingsDenyIngressWithoutProtectedMutation(
        bool securityEventsAvailable
    )
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await context.SeedWhatsAppEligibilityAsync(Recipient, now);
        await using (var db = context.Relationships.CreateDbContext())
        {
            var otherRelationshipId = Guid.NewGuid();
            db.EmploymentRelationships.Add(
                new EmploymentRelationship
                {
                    TenantId = context.TenantId,
                    RelationshipId = otherRelationshipId,
                    State = EmploymentRelationshipState.Active,
                }
            );
            db.ChannelBindings.Add(
                new ChannelBinding
                {
                    TenantId = context.TenantId,
                    RelationshipId = otherRelationshipId,
                    ParticipantId = Guid.NewGuid(),
                    ParticipantRole = "EMPLOYER",
                    Channel = "WHATSAPP",
                    ExternalSubjectHash = Recipient,
                    ConversationId = Guid.NewGuid().ToString("D"),
                    AssuranceLevel = "AAL1_CHANNEL",
                    Status = "ACTIVE",
                }
            );
            await db.SaveChangesAsync();
        }
        var proof = new VerifiedPhoneIdentityProof(
            "ambiguous-sender",
            Recipient,
            "Show my progress",
            null,
            "signed-test",
            "AAL1_CHANNEL",
            now.AddSeconds(1),
            now.AddSeconds(1),
            now.AddMinutes(5),
            Guid.NewGuid()
        )
        {
            Environment = context.Options.Environment,
            AppBindingDigest = context.Options.AppBindingDigest,
            PayloadDigest = Hash("ambiguous-sender"),
        };
        var identity = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var securityEvents = new IdentitySecurityEventService(
            identity,
            Options.Create(new IdentityHmacOptions { Key = new string('k', 32) }),
            Options.Create(new IdentityEnvironmentOptions { Environment = "local" })
        );
        var service = new WhatsAppJourneyService(
            context.Relationships,
            new ForbiddenEvidence(),
            Options.Create(new WhatsAppJourneyOptions()),
            conversationDbFactory: context.Conversations,
            conversationOptions: Options.Create(context.Options),
            stopFence: context.StopFence,
            outboundContributions: context.Outbound(),
            securityEvents: securityEventsAvailable ? securityEvents : null
        );

        if (securityEventsAvailable)
        {
            var failure = await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
                service.ReceiveVerifiedAsync(proof, CancellationToken.None)
            );
            Assert.Equal("WHATSAPP_IDENTITY_NOT_BOUND", failure.Code);
        }
        else
        {
            await Assert.ThrowsAsync<InvalidOperationException>(() =>
                service.ReceiveVerifiedAsync(proof, CancellationToken.None)
            );
        }
        await using (var identityDb = identity.CreateDbContext())
        {
            var events = await identityDb.SecurityEvents.ToListAsync();
            if (securityEventsAvailable)
            {
                var recorded = Assert.Single(events);
                Assert.Equal("AUTHORIZATION_DENIAL", recorded.EventType);
                Assert.Equal("WHATSAPP_BINDING_AMBIGUOUS", recorded.ReasonCode);
                Assert.Equal(proof.CorrelationId, recorded.CorrelationId);
                Assert.Null(recorded.ActorRef);
                Assert.Null(recorded.SessionRef);
                Assert.DoesNotContain(proof.MessageId, recorded.SourceEventId);
                Assert.DoesNotContain(proof.PhoneSubjectHash, recorded.SourceEventId);
            }
            else
                Assert.Empty(events);
        }
        await using (var saved = context.Relationships.CreateDbContext())
            Assert.Equal(now, (await saved.WhatsAppJourneyContacts.SingleAsync()).LastInboundAt);
        await using var conversations = context.Conversations.CreateDbContext();
        Assert.Empty(await conversations.Messages.ToListAsync());
        Assert.Empty(await conversations.ConversationOutbox.ToListAsync());
    }

    [Theory]
    [InlineData("revoked")]
    [InlineData("role-changed")]
    [InlineData("revoked-stop")]
    public async Task IngressRechecksParticipantButStillAcceptsRecipientStop(string scenario)
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await context.SeedWhatsAppEligibilityAsync(Recipient, now);
        await using (var db = context.Relationships.CreateDbContext())
        {
            var participant = await db.RelationshipParticipants.SingleAsync();
            if (scenario == "role-changed")
                db.Entry(participant).Property(value => value.Role).CurrentValue =
                    RelationshipParticipantRole.Evaluator;
            else
                participant.Status = "REVOKED";
            await db.SaveChangesAsync();
        }
        var proof = new VerifiedPhoneIdentityProof(
            $"participant-{scenario}",
            Recipient,
            scenario == "revoked-stop" ? "STOP" : "Show my progress",
            null,
            "signed-test",
            "AAL1_CHANNEL",
            now,
            now,
            now.AddMinutes(5),
            Guid.NewGuid()
        )
        {
            Environment = context.Options.Environment,
            AppBindingDigest = context.Options.AppBindingDigest,
            PayloadDigest = Hash($"signed-{scenario}"),
        };
        var service = new WhatsAppJourneyService(
            context.Relationships,
            new ForbiddenEvidence(),
            Options.Create(new WhatsAppJourneyOptions()),
            conversationDbFactory: context.Conversations,
            conversationOptions: Options.Create(context.Options),
            stopFence: context.StopFence,
            outboundContributions: context.Outbound()
        );
        if (scenario == "revoked-stop")
        {
            var receipt = await service.ReceiveVerifiedAsync(proof, CancellationToken.None);
            Assert.Equal("STOPPED", receipt.Status);
            await using var saved = context.Relationships.CreateDbContext();
            Assert.NotNull((await saved.WhatsAppJourneyContacts.SingleAsync()).OptedOutAt);
        }
        else
        {
            var failure = await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
                service.ReceiveVerifiedAsync(proof, CancellationToken.None)
            );
            Assert.Equal("WHATSAPP_IDENTITY_NOT_BOUND", failure.Code);
            await using var saved = context.Conversations.CreateDbContext();
            Assert.Empty(await saved.Messages.ToListAsync());
            Assert.Empty(await saved.ConversationOutbox.ToListAsync());
        }
    }

    [Fact]
    public async Task UnsupportedRelationshipContentCreatesOnlyAnIdempotentSystemReply()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        await context.SeedWhatsAppEligibilityAsync(Recipient, now);
        var proof = new VerifiedPhoneIdentityProof(
            "wamid-unsupported-relationship",
            Recipient,
            string.Empty,
            null,
            "whatsapp-provider-callback",
            "AAL1_CHANNEL",
            now,
            now,
            now.AddMinutes(5),
            Guid.NewGuid()
        )
        {
            Environment = context.Options.Environment,
            AppBindingDigest = context.Options.AppBindingDigest,
            PayloadDigest = Hash("signed unsupported relationship message"),
            UnsupportedContent = true,
        };
        var service = new WhatsAppJourneyService(
            context.Relationships,
            new ForbiddenEvidence(),
            Options.Create(new WhatsAppJourneyOptions()),
            conversationDbFactory: context.Conversations,
            conversationOptions: Options.Create(context.Options),
            stopFence: context.StopFence,
            outboundContributions: context.Outbound()
        );

        var first = await service.ReceiveVerifiedAsync(proof, CancellationToken.None);
        var replay = await service.ReceiveVerifiedAsync(proof, CancellationToken.None);

        Assert.Equal("UNSUPPORTED_CONTENT", first.Status);
        const string expectedReply =
            "I can't read attachments in WhatsApp. Please send your question as text.";
        Assert.Equal(expectedReply, first.Reply);
        Assert.True(replay.Replayed);
        await using var db = context.Conversations.CreateDbContext();
        var message = Assert.Single(await db.Messages.ToListAsync());
        Assert.Equal("SYSTEM", message.Actor);
        Assert.Equal("WHATSAPP", message.Channel);
        Assert.Equal(
            expectedReply,
            Assert
                .Single(
                    JsonSerializer.Deserialize<ConversationTextBlockV1[]>(
                        message.ContentJson,
                        new JsonSerializerOptions(JsonSerializerDefaults.Web)
                    )!
                )
                .Text
        );
        Assert.DoesNotContain("media-reference", message.ContentJson, StringComparison.Ordinal);
        var outbox = Assert.Single(await db.ConversationOutbox.ToListAsync());
        Assert.Equal(context.RelationshipId, outbox.RelationshipId);
        Assert.Equal("CUSTOMER_REQUEST", outbox.Purpose);
        Assert.Equal(Recipient, outbox.RecipientBindingDigest);
        Assert.Null(outbox.TemplateName);
        Assert.Single(await db.ProviderEventClaims.ToListAsync());
    }

    [Fact]
    public async Task AppSecretRotationUsesFreshSignatureAuthorityWithoutLegacyIdentityKey()
    {
        var fixture = await SeedAsync();
        var secrets = new WebhookCredentials();
        var service = new WhatsAppJourneyService(
            fixture.Context.Relationships,
            new ForbiddenEvidence(),
            Options.Create(new WhatsAppJourneyOptions()),
            conversationDbFactory: fixture.Context.Conversations,
            conversationOptions: Options.Create(fixture.Context.Options),
            outboxService: fixture.Context.Outbox(),
            webhookCredentials: secrets
        );
        var body = Encoding.UTF8.GetBytes(
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
                                        statuses = new[]
                                        {
                                            new
                                            {
                                                id = "wamid.synthetic",
                                                status = "delivered",
                                                timestamp = Now.ToUnixTimeSeconds().ToString(),
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                }
            )
        );
        static string Sign(byte[] bytes, string key) =>
            "sha256="
            + Convert.ToHexStringLower(HMACSHA256.HashData(Encoding.UTF8.GetBytes(key), bytes));
        var originalSignature = Sign(body, secrets.AppSecret);
        await service.ReceiveAsync(body, originalSignature, Now, CancellationToken.None);
        secrets.AppSecret = new string('r', 32);
        await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
            service.ReceiveAsync(body, originalSignature, Now, CancellationToken.None)
        );
        await service.ReceiveAsync(
            body,
            Sign(body, secrets.AppSecret),
            Now,
            CancellationToken.None
        );
        Assert.Equal(3, secrets.AppReads);
        foreach (var recipientJson in new[] { "null", "7", "true", "\"\"", "\"not-a-phone\"" })
        {
            var malformed = Encoding.UTF8.GetBytes(
                Encoding
                    .UTF8.GetString(body)
                    .Replace(
                        "\"status\":\"delivered\"",
                        "\"status\":\"delivered\",\"recipient_id\":" + recipientJson,
                        StringComparison.Ordinal
                    )
            );
            Assert.NotEqual(body, malformed);
            var rejected = await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
                service.ReceiveAsync(
                    malformed,
                    Sign(malformed, secrets.AppSecret),
                    Now,
                    CancellationToken.None
                )
            );
            Assert.Equal(400, rejected.StatusCode);
        }
        await using var db = fixture.Context.Relationships.CreateDbContext();
        var unchanged = Assert.Single(await db.WhatsAppJourneyContacts.ToListAsync());
        Assert.Equal(Recipient, unchanged.PhoneHmac);
        Assert.Equal(Now, unchanged.LastInboundAt);
        Assert.Null(unchanged.OptedOutAt);
    }

    [Theory]
    [InlineData("Approved static body", "Approved static body", 0)]
    [InlineData("Report: {{1}}", "Report: ready", 1)]
    [InlineData("Report {{1}} for {{2}}.", "Report ready for review.", 2)]
    public void ApprovedTemplateProjectionPreservesExactCanonicalContent(
        string body,
        string canonical,
        int expected
    )
    {
        var projection = new WhatsAppTemplateProjection { Body = body };
        var parameters = projection.Project(canonical);
        Assert.Equal(expected, parameters.Length);
        for (var index = 0; index < parameters.Length; index++)
            body = body.Replace(
                "{{" + (index + 1) + "}}",
                parameters[index],
                StringComparison.Ordinal
            );
        Assert.Equal(canonical, body);
    }

    [Theory]
    [InlineData("Approved static body", "Different body")]
    [InlineData("Report: {{2}}", "Report: ready")]
    [InlineData("{{1}}{{2}}", "ambiguous")]
    [InlineData("Report: {{x}}", "Report: ready")]
    [InlineData("Report: {{1}}", "Report: line\nbreak")]
    public void InvalidTemplateProjectionCannotSilentlyRewriteOrDiscardCanonicalContent(
        string body,
        string canonical
    )
    {
        Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
            new WhatsAppTemplateProjection { Body = body }.Project(canonical)
        );
    }

    [Fact]
    public async Task HttpAcceptanceIsNotDeliveryAndReservesBudgetDurably()
    {
        var fixture = await SeedAsync();
        var calls = 0;
        using var factory = new ClientFactory(
            async (request, token) =>
            {
                calls++;
                Assert.Equal("graph.facebook.com", request.RequestUri!.Host);
                Assert.Equal("Bearer", request.Headers.Authorization?.Scheme);
                using var body = JsonDocument.Parse(
                    await request.Content!.ReadAsStringAsync(token)
                );
                Assert.Equal(
                    "whatsapp",
                    body.RootElement.GetProperty("messaging_product").GetString()
                );
                Assert.Equal(
                    "Canonical shared-API reply",
                    body.RootElement.GetProperty("text").GetProperty("body").GetString()
                );
                Assert.Equal(
                    fixture.Request.OutboxId.ToString("D"),
                    body.RootElement.GetProperty("biz_opaque_callback_data").GetString()
                );
                return Json(new { messages = new[] { new { id = "wamid.synthetic" } } });
            }
        );
        var adapter = Adapter(fixture, factory);
        var result = await adapter.DispatchAsync(fixture.Request, CancellationToken.None);
        Assert.Equal("PROVIDER_ACCEPTED", result.State);
        Assert.Equal(Hash("wamid.synthetic"), result.ProviderReferenceDigest);
        Assert.Equal(1, calls);
        await using var db = fixture.Context.Conversations.CreateDbContext();
        Assert.Single(await db.Set<WhatsAppTrafficReservation>().ToListAsync());
        Assert.Equal("DISPATCHING", (await db.ConversationOutbox.SingleAsync()).State);
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            adapter.DispatchAsync(fixture.Request, CancellationToken.None)
        );
        Assert.Equal(1, calls);
    }

    [Fact]
    public async Task ProviderAcceptedOutboxWaitsForDeliveryAndNeverBecomesDeliveredFromHttpAlone()
    {
        var fixture = await SeedAsync();
        var outbox = fixture.Context.Outbox();
        await outbox.RecordResultAsync(
            fixture.Request.OutboxId,
            "fixture",
            new("PROVIDER_ACCEPTED", Hash("wamid.synthetic"), Hash("submission"), Now),
            CancellationToken.None
        );
        await using (var db = fixture.Context.Conversations.CreateDbContext())
        {
            Assert.Equal("UNRESOLVED", (await db.ConversationOutbox.SingleAsync()).State);
            Assert.Equal(
                "PROVIDER_ACCEPTED",
                (await db.DeliveryObservations.SingleAsync()).DeliveryState
            );
        }
        Assert.True(
            await outbox.RecordProviderStatusAsync(
                new(
                    "delivered-event",
                    "wamid.synthetic",
                    "delivered",
                    Now.AddSeconds(1),
                    Hash("callback")
                ),
                CancellationToken.None
            )
        );
        using var factory = new ClientFactory(
            (_, _) => throw new InvalidOperationException("Reconciliation must not send.")
        );
        Assert.Equal(
            "DELIVERED",
            (
                await Adapter(fixture, factory)
                    .ReconcileAsync(fixture.Request, CancellationToken.None)
            ).State
        );
    }

    [Fact]
    public async Task SignedOpaqueCorrelationRecoversLostSubmissionResponseWithoutResend()
    {
        var fixture = await SeedAsync();
        var budget = new WhatsAppTrafficBudget(
            fixture.Context.Conversations,
            fixture.Gate,
            fixture.Clock
        );
        await budget.ReserveAsync(fixture.Request, Recipient, CancellationToken.None);
        var outbox = fixture.Context.Outbox();
        await outbox.RecordResultAsync(
            fixture.Request.OutboxId,
            "fixture",
            new("UNKNOWN", Hash("unknown"), Hash("submission"), Now),
            CancellationToken.None
        );
        var status = new WhatsAppProviderStatusEvent(
            "delivered-event",
            "wamid.synthetic",
            "delivered",
            Now.AddSeconds(1),
            Hash("callback")
        )
        {
            OutboxId = fixture.Request.OutboxId,
        };
        Assert.True(await outbox.RecordProviderStatusAsync(status, CancellationToken.None));
        Assert.True(await outbox.RecordProviderStatusAsync(status, CancellationToken.None));
        await using var db = fixture.Context.Conversations.CreateDbContext();
        Assert.Single(
            await db
                .DeliveryObservations.Where(value => value.DeliveryState == "DELIVERED")
                .ToListAsync()
        );
        Assert.Equal("UNRESOLVED", (await db.ConversationOutbox.SingleAsync()).State);
        using var factory = new ClientFactory(
            (_, _) => throw new InvalidOperationException("Reconciliation must not send.")
        );
        Assert.Equal(
            "DELIVERED",
            (
                await Adapter(fixture, factory)
                    .ReconcileAsync(fixture.Request, CancellationToken.None)
            ).State
        );
    }

    [Fact]
    public async Task ApprovedTemplateCannotBeUsedForProactiveDeliveryInThisRelease()
    {
        var fixture = await SeedAsync("report");
        var channel = new WhatsAppJourneyOptions
        {
            DispatchEnabled = true,
            ApprovedTemplates = ["report:1:en_IN:UTILITY"],
            TemplateProjections =
            [
                new()
                {
                    Name = "report",
                    Version = "1",
                    Locale = "en_IN",
                    Category = "UTILITY",
                    Body = "{{1}}",
                },
            ],
        };
        var calls = 0;
        using var factory = new ClientFactory(
            async (request, token) =>
            {
                calls++;
                using var body = JsonDocument.Parse(
                    await request.Content!.ReadAsStringAsync(token)
                );
                Assert.Equal("template", body.RootElement.GetProperty("type").GetString());
                var template = body.RootElement.GetProperty("template");
                Assert.Equal("report", template.GetProperty("name").GetString());
                Assert.Equal(
                    "en_IN",
                    template.GetProperty("language").GetProperty("code").GetString()
                );
                Assert.Equal(
                    "Canonical shared-API reply",
                    template
                        .GetProperty("components")[0]
                        .GetProperty("parameters")[0]
                        .GetProperty("text")
                        .GetString()
                );
                return Json(new { messages = new[] { new { id = "wamid.synthetic" } } });
            }
        );
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Adapter(fixture, factory).DispatchAsync(fixture.Request, CancellationToken.None)
        );
        Assert.Equal(0, calls);
        var proactive = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Adapter(fixture, factory, channel)
                .DispatchAsync(fixture.Request, CancellationToken.None)
        );
        Assert.Equal("PROACTIVE_MESSAGING_DISABLED", proactive.ReasonCode);
        Assert.Equal(0, calls);
    }

    [Fact]
    public async Task AmbiguousHttpOutcomeIsUnknownAndCannotBlindlyResubmit()
    {
        var fixture = await SeedAsync();
        var calls = 0;
        using var factory = new ClientFactory(
            (_, _) =>
            {
                calls++;
                throw new HttpRequestException("Synthetic network loss.");
            }
        );
        var adapter = Adapter(fixture, factory);
        var observation = await adapter.DispatchAsync(fixture.Request, CancellationToken.None);
        Assert.Equal("UNKNOWN", observation.State);
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            adapter.DispatchAsync(fixture.Request, CancellationToken.None)
        );
        Assert.Equal(1, calls);
    }

    [Fact]
    public async Task BudgetAndRecipientBoundariesDenyBeforeProviderEgress()
    {
        var fixture = await SeedAsync();
        fixture.Options.Authority = fixture.Options.Authority! with
        {
            MaximumMessages = 1,
            MaximumMessagesPerMinute = 1,
        };
        var budget = new WhatsAppTrafficBudget(
            fixture.Context.Conversations,
            fixture.Gate,
            fixture.Clock
        );
        await budget.ReserveAsync(fixture.Request, Recipient, CancellationToken.None);
        await using (var db = fixture.Context.Conversations.CreateDbContext())
        {
            db.ConversationOutbox.Add(
                new()
                {
                    OutboxId = Guid.NewGuid(),
                    TenantId = fixture.Request.TenantId,
                    Environment = "demo",
                    RelationshipId = fixture.Request.RelationshipId,
                    ConversationId = fixture.Request.ConversationId,
                    Sequence = fixture.Request.Sequence,
                    PayloadReference = fixture.Request.PayloadReference,
                    PayloadDigest = fixture.Request.PayloadDigest,
                    RecipientBindingDigest = Recipient,
                    Purpose = "CUSTOMER_REQUEST",
                    State = "DISPATCHING",
                    AttemptNumber = 1,
                    LeaseExpiresAt = Now.AddMinutes(1),
                }
            );
            await db.SaveChangesAsync();
        }
        await using var check = fixture.Context.Conversations.CreateDbContext();
        var second = await check.ConversationOutbox.SingleAsync(value =>
            value.OutboxId != fixture.Request.OutboxId
        );
        var failure = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveAsync(
                fixture.Request with
                {
                    OutboxId = second.OutboxId,
                },
                Recipient,
                CancellationToken.None
            )
        );
        Assert.Equal("TRAFFIC_BUDGET_EXHAUSTED", failure.ReasonCode);
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveAsync(
                fixture.Request with
                {
                    TenantId = Guid.NewGuid(),
                },
                Recipient,
                CancellationToken.None
            )
        );
        Assert.Single(await check.Set<WhatsAppTrafficReservation>().ToListAsync());
    }

    [Fact]
    public async Task RelationshipInboundAndProviderReplyConsumeOneCombinedActivationAllowance()
    {
        var fixture = await SeedAsync();
        fixture.Options.Authority = fixture.Options.Authority! with
        {
            MaximumMessages = 2,
            MaximumMessagesPerMinute = 2,
        };
        var budget = new WhatsAppTrafficBudget(
            fixture.Context.Conversations,
            fixture.Gate,
            fixture.Clock
        );
        Assert.Equal(
            WhatsAppGuestTrafficNotice.ActivationLimit,
            await budget.ReserveRelationshipInboundAsync(
                fixture.Request.TenantId,
                Recipient,
                "original-inbound",
                CancellationToken.None
            )
        );
        await budget.ReserveAsync(fixture.Request, Recipient, CancellationToken.None);
        Assert.Equal(
            WhatsAppGuestTrafficNotice.ActivationLimit,
            await budget.ReserveRelationshipInboundAsync(
                fixture.Request.TenantId,
                Recipient,
                "original-inbound",
                CancellationToken.None
            )
        );
        var failure = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveRelationshipInboundAsync(
                fixture.Request.TenantId,
                Recipient,
                "next-inbound",
                CancellationToken.None
            )
        );
        Assert.Equal("TRAFFIC_BUDGET_EXHAUSTED", failure.ReasonCode);
        await using var db = fixture.Context.Conversations.CreateDbContext();
        Assert.Equal(
            2,
            await WhatsAppTrafficBudget.CountActivationMessagesAsync(
                db,
                fixture.Request.TenantId,
                WhatsAppGuestTrafficEventIdentity.Activation(
                    fixture.Options.Authority.ActivationReference
                ),
                CancellationToken.None
            )
        );
        Assert.Single(await db.WhatsAppGuestTrafficEvents.ToListAsync());
        Assert.Single(await db.Set<WhatsAppTrafficReservation>().ToListAsync());
    }

    [Fact]
    public async Task RelationshipInboundRateDecisionIsReplaySafeAndCannotBorrowAnotherSender()
    {
        var fixture = await SeedAsync(guest: true);
        fixture.Options.Authority = fixture.Options.Authority! with
        {
            MaximumMessagesPerMinute = 3,
        };
        var budget = new WhatsAppTrafficBudget(
            fixture.Context.Conversations,
            fixture.Gate,
            fixture.Clock
        );
        Assert.Equal(
            WhatsAppGuestTrafficNotice.None,
            await budget.ReserveRelationshipInboundAsync(
                fixture.Request.TenantId,
                Recipient,
                "first",
                CancellationToken.None
            )
        );
        Assert.Equal(
            WhatsAppGuestTrafficNotice.GlobalRateLimit,
            await budget.ReserveRelationshipInboundAsync(
                fixture.Request.TenantId,
                Recipient,
                "second",
                CancellationToken.None
            )
        );
        Assert.Equal(
            WhatsAppGuestTrafficNotice.None,
            await budget.ReserveRelationshipInboundAsync(
                fixture.Request.TenantId,
                Recipient,
                "first",
                CancellationToken.None
            )
        );
        var conflict = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveRelationshipInboundAsync(
                fixture.Request.TenantId,
                Hash("different-sender"),
                "first",
                CancellationToken.None
            )
        );
        Assert.Equal("RECIPIENT_DENIED", conflict.ReasonCode);
        await using var db = fixture.Context.Conversations.CreateDbContext();
        Assert.Equal(2, await db.WhatsAppGuestTrafficEvents.CountAsync());
    }

    [Fact]
    public async Task RelationshipInboundCannotResetExistingProviderAuthority()
    {
        var fixture = await SeedAsync();
        var budget = new WhatsAppTrafficBudget(
            fixture.Context.Conversations,
            fixture.Gate,
            fixture.Clock
        );
        await budget.ReserveAsync(fixture.Request, Recipient, CancellationToken.None);
        fixture.Options.Authority = fixture.Options.Authority! with { MaximumMessages = 20 };
        var failure = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveRelationshipInboundAsync(
                fixture.Request.TenantId,
                Recipient,
                "after-authority-change",
                CancellationToken.None
            )
        );
        Assert.Equal("ACTIVATION_RECORD_CHANGED", failure.ReasonCode);
        await using var db = fixture.Context.Conversations.CreateDbContext();
        Assert.Empty(await db.WhatsAppGuestTrafficEvents.ToListAsync());
    }

    [Fact]
    public async Task GuestOutboundSharesTheActivationConfiguredTenantWideRollingMinuteLimit()
    {
        var fixture = await SeedAsync(guest: true);
        fixture.Options.Authority = fixture.Options.Authority! with
        {
            MaximumMessagesPerMinute = 2,
            AllowProvisionalOnboarding = true,
        };
        var guestBudget = new WhatsAppGuestTrafficBudget(
            fixture.Context.Conversations,
            fixture.Gate,
            fixture.Clock
        );
        await guestBudget.ReserveInboundAsync(
            fixture.Request.TenantId,
            Hash("another-guest"),
            "prior-guest-message",
            false,
            CancellationToken.None
        );
        var budget = new WhatsAppTrafficBudget(
            fixture.Context.Conversations,
            fixture.Gate,
            fixture.Clock
        );

        await budget.ReserveAsync(fixture.Request, Recipient, CancellationToken.None);

        var limited = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            guestBudget.ReserveInboundAsync(
                fixture.Request.TenantId,
                Hash("third-guest"),
                "third-guest-message",
                false,
                CancellationToken.None
            )
        );
        Assert.Equal("GUEST_GLOBAL_RATE_LIMIT_REACHED", limited.ReasonCode);
    }

    [Fact]
    public async Task ExpiryAndStopFencePreventEgressWithoutDiscardingTheCanonicalMessage()
    {
        var fixture = await SeedAsync();
        var calls = 0;
        using var factory = new ClientFactory(
            (_, _) =>
            {
                calls++;
                throw new InvalidOperationException("Network must not be used.");
            }
        );
        fixture.Clock.Now = Now.AddMinutes(1);
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Adapter(fixture, factory).DispatchAsync(fixture.Request, CancellationToken.None)
        );
        fixture.Clock.Now = Now;
        await using (var db = fixture.Context.Conversations.CreateDbContext())
        {
            db.EmergencyStopLatches.Add(
                new()
                {
                    Environment = "demo",
                    TenantId = fixture.Request.TenantId,
                    RelationshipId = fixture.Request.RelationshipId!.Value,
                    State = "LATCHED",
                }
            );
            await db.SaveChangesAsync();
        }
        await Assert.ThrowsAsync<ConversationStoppedException>(() =>
            Adapter(fixture, factory).DispatchAsync(fixture.Request, CancellationToken.None)
        );
        await using var check = fixture.Context.Conversations.CreateDbContext();
        Assert.Single(await check.Messages.ToListAsync());
        Assert.Empty(await check.Set<WhatsAppTrafficReservation>().ToListAsync());
        Assert.Equal(0, calls);
    }

    [Theory]
    [InlineData("PROVIDER_ACCEPTED", "UNKNOWN")]
    [InlineData("DELIVERED", "DELIVERED")]
    [InlineData("READ", "DELIVERED")]
    [InlineData("FAILED", "REJECTED")]
    public async Task ReconciliationUsesSharedDeliveryEvidenceAndNeverSendsAgain(
        string state,
        string expected
    )
    {
        var fixture = await SeedAsync();
        await using (var db = fixture.Context.Conversations.CreateDbContext())
        {
            var message = await db.Messages.SingleAsync();
            db.DeliveryObservations.Add(
                new()
                {
                    Environment = "demo",
                    TenantId = fixture.Request.TenantId,
                    RelationshipId = fixture.Request.RelationshipId,
                    MessageId = message.MessageId,
                    Provider = "WHATSAPP",
                    ProviderEventIdentity = Hash("status"),
                    ProviderReferenceDigest = Hash("provider"),
                    DeliveryState = state,
                    ObservationDigest = Hash("observation"),
                    ObservedAt = Now,
                    RetainUntil = Now.AddYears(7),
                }
            );
            await db.SaveChangesAsync();
        }
        using var factory = new ClientFactory(
            (_, _) => throw new InvalidOperationException("Reconciliation must not send.")
        );
        var observation = await Adapter(fixture, factory)
            .ReconcileAsync(fixture.Request, CancellationToken.None);
        Assert.Equal(expected, observation.State);
    }

    [Fact]
    public async Task TenantExecutionScopeDoesNotLeakAcrossAsyncFlowsAndCanOnlyUseAuthorityTenant()
    {
        var fixture = await SeedAsync();
        var scope = new WhatsAppTenantExecutionScope(fixture.Gate, fixture.Clock);
        Assert.Null(scope.CurrentTenantId);
        await Task.Run(async () =>
        {
            using var tenant = scope.Begin();
            Assert.Equal(fixture.Request.TenantId, scope.CurrentTenantId);
            Assert.Throws<InvalidOperationException>(() => scope.Begin());
            await Task.Yield();
            Assert.Equal(fixture.Request.TenantId, scope.CurrentTenantId);
        });
        Assert.Null(scope.CurrentTenantId);
        fixture.Options.Revoked = true;
        Assert.Throws<WhatsAppCapabilityUnavailableException>(() => scope.Begin());
        Assert.Null(scope.CurrentTenantId);
    }

    private sealed record Fixture(
        Wc120FitnessContext Context,
        WhatsAppCapabilityOptions Options,
        WhatsAppCapabilityGate Gate,
        Clock Clock,
        WhatsAppProviderDispatchRequest Request
    );

    private static async Task<Fixture> SeedAsync(
        string? template = null,
        bool guest = false,
        string? recipient = null
    )
    {
        recipient ??= Recipient;
        var context = await Wc120FitnessContext.CreateAsync();
        context.Options.Environment = "demo";
        context.Options.AppBindingDigest = Hash("1001");
        context.Options.WabaBindingDigest = Hash("1002");
        context.Options.RecipientBindingDigest = Hash("1003");
        await context.SeedWhatsAppEligibilityAsync(recipient, Now);
        var options = new WhatsAppCapabilityOptions
        {
            Configured = true,
            ProviderAvailable = true,
            Environment = "demo",
            ReleaseDigest = TupleDigest,
            ConfigurationDigest = TupleDigest,
            CatalogDigest = TupleDigest,
            RollbackDigest = TupleDigest,
            Authority = new()
            {
                ActivationReference = "FA:demo",
                ExternalTrafficReference = "FA:traffic",
                ConsentReference = "consent:fixture",
                IncidentOwnerReference = "office:operations",
                AlertRouteReference = "alert:fixture",
                Environment = "demo",
                ReleaseDigest = TupleDigest,
                ConfigurationDigest = TupleDigest,
                CatalogDigest = TupleDigest,
                RollbackDigest = TupleDigest,
                TenantId = context.TenantId,
                RecipientBindingDigest = Recipient,
                StartsAt = Now,
                ExpiresAt = Now.AddMinutes(1),
                MaximumMessages = 10,
                MaximumMessagesPerMinute = 5,
                MaximumSpendInr = 100,
                MaximumCostPerMessageInr = 10,
            },
        };
        var gate = new WhatsAppCapabilityGate(
            new StaticOptionsMonitor<WhatsAppCapabilityOptions>(options)
        );
        var clock = new Clock { Now = Now };
        await using var db = context.Conversations.CreateDbContext();
        var message = new ConversationMessage
        {
            Environment = "demo",
            TenantId = context.TenantId,
            RelationshipId = context.RelationshipId,
            ConversationId = context.WhatsAppConversationId,
            Sequence = 1,
            ContentJson = JsonSerializer.Serialize(
                new[] { new ConversationTextBlockV1("1.0", "TEXT", "Canonical shared-API reply") }
            ),
        };
        var outbox = new ConversationOutboxRecord
        {
            Environment = "demo",
            TenantId = context.TenantId,
            RelationshipId = context.RelationshipId,
            ConversationId = message.ConversationId,
            PortalContextId = guest ? Guid.NewGuid() : null,
            Sequence = 1,
            AggregateId = message.MessageId.ToString("D"),
            Purpose = guest ? "WHATSAPP_GUEST_DISCOVERY" : "CUSTOMER_REQUEST",
            RecipientBindingDigest = recipient,
            TemplateName = template,
            TemplateVersion = template is null ? null : "1",
            TemplateLocale = template is null ? null : "en_IN",
            TemplateCategory = template is null ? null : "UTILITY",
            PayloadReference = "payload:fixture",
            PayloadDigest = Hash("payload"),
            CreatedAt = Now,
            UpdatedAt = Now,
            State = "DISPATCHING",
            AttemptNumber = 1,
            LeaseOwner = "fixture",
            LeaseExpiresAt = Now.AddSeconds(60),
        };
        db.Messages.Add(message);
        db.ConversationOutbox.Add(outbox);
        await db.SaveChangesAsync();
        return new(
            context,
            options,
            gate,
            clock,
            new(
                outbox.OutboxId,
                "demo",
                context.TenantId,
                context.RelationshipId,
                message.ConversationId,
                1,
                outbox.PayloadReference,
                outbox.PayloadDigest,
                1
            )
        );
    }

    private static WhatsAppCloudProviderAdapter Adapter(
        Fixture fixture,
        ClientFactory factory,
        WhatsAppJourneyOptions? channel = null,
        IWhatsAppProviderCredentials? credentials = null
    ) =>
        new(
            factory,
            credentials ?? new Credentials(),
            fixture.Gate,
            fixture.Context.Conversations,
            fixture.Context.StopFence,
            fixture.Context.Outbox(channel),
            new WhatsAppTrafficBudget(fixture.Context.Conversations, fixture.Gate, fixture.Clock),
            fixture.Clock,
            new StaticOptionsMonitor<WhatsAppJourneyOptions>(
                channel ?? new WhatsAppJourneyOptions { DispatchEnabled = true }
            ),
            Options.Create(fixture.Context.Options),
            credentials as IWhatsAppWebhookCredentials ?? new Credentials()
        );

    private static WhatsAppKeyVaultCredentials Reader(
        ClientFactory factory,
        WhatsAppProviderOptions? options = null,
        string endpoint = "http://127.0.0.1:8080/msi/token"
    ) =>
        new(
            factory,
            new StaticOptionsMonitor<WhatsAppProviderOptions>(options ?? ProviderOptions()),
            new ConfigurationBuilder()
                .AddInMemoryCollection(
                    new Dictionary<string, string?>
                    {
                        ["IDENTITY_ENDPOINT"] = endpoint,
                        ["IDENTITY_HEADER"] = "synthetic-identity-header",
                    }
                )
                .Build(),
            new Clock { Now = Now }
        );

    private static WhatsAppProviderOptions ProviderOptions() =>
        new()
        {
            Enabled = true,
            Environment = "demo",
            VaultHost = "kv-waooaw-demo.vault.azure.net",
            ManagedIdentityClientId = Guid.NewGuid().ToString("D"),
            BindingVersion = new string('a', 32),
            OutboundAuthorityVersion = new string('b', 32),
            VerifyTokenVersion = new string('c', 32),
            AppSecretVersion = new string('d', 32),
            PhoneSubjectKeyVersion = new string('e', 32),
        };

    private static HttpResponseMessage SecretResponse(
        HttpRequestMessage request,
        string? failure = null
    )
    {
        if (failure == "redirect")
        {
            var redirect = new HttpResponseMessage(HttpStatusCode.Redirect);
            redirect.Headers.Location = new Uri("https://example.invalid/denied");
            return redirect;
        }
        if (failure == "oversized")
            return new(HttpStatusCode.OK) { Content = new StringContent(new string('x', 65_537)) };
        if (failure == "wrong-shape")
            return Json(Array.Empty<string>());
        if (request.RequestUri!.IsLoopback)
            return Json(
                new
                {
                    access_token = new string('t', 40),
                    resource = failure == "wrong-resource"
                        ? "https://example.invalid"
                        : "https://vault.azure.net",
                }
            );
        var value = request.RequestUri.AbsolutePath.Contains(
            "whatsapp-provider-binding",
            StringComparison.Ordinal
        )
            ? JsonSerializer.Serialize(
                Binding(),
                new JsonSerializerOptions(JsonSerializerDefaults.Web)
            )
            : new string('p', 40);
        var outbound = request.RequestUri.AbsolutePath.Contains(
            "whatsapp-outbound-authority",
            StringComparison.Ordinal
        );
        var attributes = new Dictionary<string, object>
        {
            ["enabled"] = failure != "disabled" && !(outbound && failure == "outbound-disabled"),
            ["nbf"] = (
                failure == "future" || (outbound && failure == "outbound-future")
                    ? Now.AddMinutes(1)
                    : Now
            ).ToUnixTimeSeconds(),
        };
        if (failure != "no-expiry" && !(outbound && failure == "outbound-no-expiry"))
            attributes["exp"] =
                outbound && failure == "outbound-invalid-expiry"
                    ? "invalid"
                    : (
                        failure == "expired" || (outbound && failure == "outbound-expired")
                            ? Now
                            : Now.AddHours(1)
                    ).ToUnixTimeSeconds();
        return Json(
            new
            {
                id = failure == "wrong-version"
                    ? "https://example.invalid/denied"
                    : request.RequestUri.GetLeftPart(UriPartial.Path),
                value,
                attributes,
            }
        );
    }

    private static WhatsAppProviderBinding Binding() =>
        new()
        {
            Environment = "demo",
            BindingVersion = "fixture-1",
            AppId = "1001",
            WabaId = "1002",
            PhoneNumberId = "1003",
            RecipientPhoneNumber = string.Concat("+", "44", new string('7', 10)),
            RecipientBindingDigest = Recipient,
            ApiVersion = "v25.0",
            AuthorityReference = "FA:provider",
            ValidFrom = Now,
            ExpiresAt = Now.AddHours(1),
        };

    private sealed class Credentials(Func<Task>? beforeReturn = null)
        : IWhatsAppProviderCredentials,
            IWhatsAppWebhookCredentials
    {
        public static string SubjectKey { get; } = new('h', 40);

        public async Task<WhatsAppProviderCredentials> ReadAsync(
            CancellationToken cancellationToken
        )
        {
            if (beforeReturn is not null)
                await beforeReturn();
            return new WhatsAppProviderCredentials
            {
                Binding = Binding(),
                AccessToken = new string('p', 40),
                ValidUntil = Now.AddMinutes(5),
            };
        }

        public Task<string> ReadVerifyTokenAsync(CancellationToken cancellationToken) =>
            Task.FromResult(new string('v', 40));

        public Task<string> ReadAppSecretAsync(CancellationToken cancellationToken) =>
            Task.FromResult(new string('s', 40));

        public Task<string> ReadPhoneSubjectKeyAsync(CancellationToken cancellationToken) =>
            Task.FromResult(SubjectKey);

        public Task<WhatsAppProviderBinding> ReadSenderBindingAsync(
            CancellationToken cancellationToken
        ) => Task.FromResult(Binding());
    }

    private sealed class WebhookCredentials : IWhatsAppWebhookCredentials
    {
        public int VerifyReads { get; private set; }
        public int AppReads { get; private set; }
        public string AppSecret { get; set; } = new('s', 32);

        public Task<string> ReadVerifyTokenAsync(CancellationToken cancellationToken)
        {
            VerifyReads++;
            return Task.FromResult(new string('v', 32));
        }

        public Task<string> ReadAppSecretAsync(CancellationToken cancellationToken)
        {
            AppReads++;
            return Task.FromResult(AppSecret);
        }

        public Task<string> ReadPhoneSubjectKeyAsync(CancellationToken cancellationToken) =>
            Task.FromResult(new string('h', 40));

        public Task<WhatsAppProviderBinding> ReadSenderBindingAsync(
            CancellationToken cancellationToken
        ) => Task.FromResult(Binding());
    }

    private sealed class ForbiddenEvidence : IWhatsAppRegistrationEvidenceGateway
    {
        public Task RecordAsync(
            Guid tenantId,
            string messageId,
            string phoneHmac,
            DateTimeOffset occurredAt,
            CancellationToken cancellationToken
        ) => throw new InvalidOperationException("No registration evidence effect is permitted.");
    }

    private sealed class Clock : TimeProvider
    {
        public DateTimeOffset Now { get; set; }

        public override DateTimeOffset GetUtcNow() => Now;
    }

    private sealed class ClientFactory(
        Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> send
    ) : HttpMessageHandler, IHttpClientFactory
    {
        public HttpClient CreateClient(string name) =>
            new(this, disposeHandler: false) { Timeout = TimeSpan.FromSeconds(15) };

        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) => send(request, cancellationToken);
    }

    private static HttpResponseMessage Json<T>(T value) =>
        new(HttpStatusCode.OK)
        {
            Content = new StringContent(
                JsonSerializer.Serialize(value),
                Encoding.UTF8,
                "application/json"
            ),
        };

    private static string Hash(string value) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
}
