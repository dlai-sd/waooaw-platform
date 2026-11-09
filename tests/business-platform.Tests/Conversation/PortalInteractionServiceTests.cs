// Implements: work-contracts/WC-096-conversational-customer-portal.md §5
// constitutional_basis: C-026, C-049, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;
using Moq;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class PortalInteractionServiceTests
{
    public static TheoryData<string> GuestFixedNotices =>
        new()
        {
            WhatsAppGuestConsent.Notice,
            WhatsAppGuestConsent.Accepted,
            WhatsAppGuestConsent.RegisteredNumberAccepted,
            WhatsAppAccountLinkInstruction.ConfirmedNotice,
            WhatsAppAccountLinkInstruction.DeniedNotice,
            WhatsAppGuestTrafficBudget.UnsupportedContentNotice,
            WhatsAppGuestTrafficBudget.SessionLimitNotice,
            WhatsAppGuestTrafficBudget.MessageLimitNotice,
            WhatsAppGuestTrafficBudget.GlobalRateLimitNotice,
            WhatsAppGuestOperatingHours.ClosedNotice,
        };

    [Theory]
    [MemberData(nameof(GuestFixedNotices))]
    public async Task FixedGuestControlsAreGuideOnlyAndReplayWithoutCustomerText(string notice)
    {
        var service = CreateService(out var factory);
        var tenant = Guid.NewGuid();
        var participant = Guid.NewGuid();
        var key = Guid.NewGuid();
        var result = await service.SendGuestFixedNoticeAsync(
            tenant,
            participant,
            key,
            notice,
            CancellationToken.None
        );
        var replay = await service.SendGuestFixedNoticeAsync(
            tenant,
            participant,
            key,
            notice,
            CancellationToken.None
        );
        Assert.True(replay.Replayed);
        Assert.Equal(result.Value.MessageId, replay.Value.MessageId);
        Assert.Equal(notice, result.Value.Content.Single().Text);
        await using var db = factory.CreateDbContext();
        Assert.Equal("GUIDE", (await db.PortalInteractionMessages.SingleAsync()).Actor);
        Assert.Single(await db.PortalInteractionIdempotencyOutcomes.ToListAsync());
        await Assert.ThrowsAsync<ConversationRequestException>(() =>
            service.SendGuestFixedNoticeAsync(
                tenant,
                participant,
                Guid.NewGuid(),
                "arbitrary ungoverned reply",
                CancellationToken.None
            )
        );
    }

    [Theory]
    [InlineData("stopped")]
    [InlineData("missing-consent")]
    [InlineData("stale-version")]
    [InlineData("missing-evidence")]
    public async Task WhatsAppGuestCannotBypassStopOrConsentByCallingSharedOwnerDirectly(
        string state
    )
    {
        var service = CreateService(out var factory);
        var tenant = Guid.NewGuid();
        var participant = Guid.NewGuid();
        await using (var db = factory.CreateDbContext())
        {
            db.Add(
                new WhatsAppGuestSession
                {
                    TenantId = tenant,
                    ParticipantId = participant,
                    BindingDigest = new string('a', 64),
                    EvidenceId = Guid.NewGuid(),
                    AdmittedAt = DateTimeOffset.UtcNow,
                    StoppedAt = state == "stopped" ? DateTimeOffset.UtcNow : null,
                    ServiceConsentAt = state == "missing-consent" ? null : DateTimeOffset.UtcNow,
                    ServiceConsentEvidenceId = state == "missing-evidence" ? null : Guid.NewGuid(),
                    ServiceConsentNoticeVersion =
                        state == "stale-version" ? "retired" : WhatsAppGuestConsent.NoticeVersion,
                }
            );
            await db.SaveChangesAsync();
        }
        if (state == "stopped")
        {
            await Assert.ThrowsAsync<ConversationStoppedException>(() =>
                service.ListGuestDiscoveryAsync(
                    tenant,
                    participant,
                    null,
                    20,
                    CancellationToken.None
                )
            );
            await Assert.ThrowsAsync<ConversationStoppedException>(() =>
                service.SendGuestDiscoveryAsync(
                    tenant,
                    participant,
                    Guid.NewGuid(),
                    GuestRequest("do not persist"),
                    CancellationToken.None
                )
            );
            await Assert.ThrowsAsync<ConversationStoppedException>(() =>
                service.SendGuestFixedNoticeAsync(
                    tenant,
                    participant,
                    Guid.NewGuid(),
                    WhatsAppGuestConsent.Notice,
                    CancellationToken.None
                )
            );
        }
        else
        {
            await Assert.ThrowsAsync<ConversationNotAccessibleException>(() =>
                service.ListGuestDiscoveryAsync(
                    tenant,
                    participant,
                    null,
                    20,
                    CancellationToken.None
                )
            );
            await Assert.ThrowsAsync<ConversationNotAccessibleException>(() =>
                service.SendGuestDiscoveryAsync(
                    tenant,
                    participant,
                    Guid.NewGuid(),
                    GuestRequest("do not persist"),
                    CancellationToken.None
                )
            );
        }
        await using var check = factory.CreateDbContext();
        Assert.Empty(await check.PortalInteractionMessages.ToListAsync());
        Assert.Empty(await check.PortalInteractionIdempotencyOutcomes.ToListAsync());
    }

    [Fact]
    public async Task ConsentedWhatsAppGuestCanReadTimelineUntilStopped()
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(
            factory,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            ),
            new MatchingCatalog()
        );
        var guest = new WhatsAppGuestSession
        {
            TenantId = Guid.NewGuid(),
            BindingDigest = new string('a', 64),
            EvidenceId = Guid.NewGuid(),
            AdmittedAt = DateTimeOffset.UtcNow,
            ServiceConsentAt = DateTimeOffset.UtcNow,
            ServiceConsentEvidenceId = Guid.NewGuid(),
            ServiceConsentNoticeVersion = WhatsAppGuestConsent.NoticeVersion,
        };
        await using (var db = factory.CreateDbContext())
        {
            db.Add(guest);
            await db.SaveChangesAsync();
        }
        await service.SendGuestDiscoveryAsync(
            guest.TenantId,
            guest.ParticipantId,
            Guid.NewGuid(),
            GuestRequest("marketing"),
            CancellationToken.None
        );
        var page = await service.ListGuestDiscoveryAsync(
            guest.TenantId,
            guest.ParticipantId,
            null,
            20,
            CancellationToken.None
        );
        Assert.Equal(2, page.Items.Count);
        await using (var db = factory.CreateDbContext())
        {
            (await db.Set<WhatsAppGuestSession>().SingleAsync()).StoppedAt = DateTimeOffset.UtcNow;
            await db.SaveChangesAsync();
        }
        await Assert.ThrowsAsync<ConversationStoppedException>(() =>
            service.ListGuestDiscoveryAsync(
                guest.TenantId,
                guest.ParticipantId,
                null,
                20,
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task SendPersistsScopedGuideExchangeAndReplaysOneOutcome()
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(
            factory,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            )
        );
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var idempotencyKey = Guid.NewGuid();
        var request = new SendPortalInteractionMessageRequestV1(
            "1.0",
            Guid.NewGuid(),
            [new("1.0", "TEXT", "Show my billing", "en-IN")],
            "en-IN",
            "MY_AGENTS"
        );

        var accepted = await service.SendAsync(
            tenantId,
            participantId,
            idempotencyKey,
            request,
            CancellationToken.None
        );
        var replay = await service.SendAsync(
            tenantId,
            participantId,
            idempotencyKey,
            request,
            CancellationToken.None
        );
        var ownerTimeline = await service.ListAsync(
            tenantId,
            participantId,
            null,
            20,
            CancellationToken.None
        );
        var otherTimeline = await service.ListAsync(
            tenantId,
            Guid.NewGuid(),
            null,
            20,
            CancellationToken.None
        );

        Assert.False(accepted.Replayed);
        Assert.True(replay.Replayed);
        Assert.Equal(
            accepted.Value.CustomerMessage.MessageId,
            replay.Value.CustomerMessage.MessageId
        );
        Assert.Equal(["CUSTOMER", "GUIDE"], ownerTimeline.Items.Select(item => item.Actor));
        Assert.Equal(
            "/profile#billing",
            Assert.Single(ownerTimeline.Items[1].Capabilities).Destination
        );
        Assert.Empty(otherTimeline.Items);
        Assert.NotEqual(ownerTimeline.ContextId, otherTimeline.ContextId);
    }

    [Fact]
    public async Task IdempotencyRejectsChangedPayloadAndCursorIsContextBound()
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(
            factory,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            )
        );
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var idempotencyKey = Guid.NewGuid();
        var request = new SendPortalInteractionMessageRequestV1(
            "1.0",
            Guid.NewGuid(),
            [new("1.0", "TEXT", "Show alerts", "en-IN")],
            "en-IN",
            "ALERTS"
        );
        await service.SendAsync(
            tenantId,
            participantId,
            idempotencyKey,
            request,
            CancellationToken.None
        );

        await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() =>
            service.SendAsync(
                tenantId,
                participantId,
                idempotencyKey,
                request with
                {
                    CurrentSurface = "SETTINGS",
                },
                CancellationToken.None
            )
        );
        var owner = await service.ListAsync(
            tenantId,
            participantId,
            null,
            20,
            CancellationToken.None
        );
        await Assert.ThrowsAsync<ConversationCursorExpiredException>(() =>
            service.ListAsync(
                tenantId,
                Guid.NewGuid(),
                owner.AuthoritativeCursor,
                20,
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task RejectsEveryMalformedRequestShape()
    {
        var service = CreateService(out _);
        var valid = new SendPortalInteractionMessageRequestV1(
            "1.0",
            Guid.NewGuid(),
            [new("1.0", "TEXT", "Help me navigate", "en-IN")],
            "en-IN",
            "MY_AGENTS"
        );
        var malformed = new[]
        {
            valid with
            {
                SchemaVersion = "2.0",
            },
            valid with
            {
                ClientMessageId = Guid.Empty,
            },
            valid with
            {
                Content = [],
            },
            valid with
            {
                Content = [new("1.0", "IMAGE", "Help me navigate", "en-IN")],
            },
            valid with
            {
                Content = [new("1.0", "TEXT", " ", "en-IN")],
            },
            valid with
            {
                Content = [new("1.0", "TEXT", new string('x', 32001), "en-IN")],
            },
            valid with
            {
                Content = [new("1.0", "TEXT", "not\0persistable", "en-IN")],
            },
            valid with
            {
                Content = [new("1.0", "TEXT", "Help me navigate", "en\0IN")],
            },
            valid with
            {
                Locale = " ",
            },
            valid with
            {
                Locale = "not a language tag",
            },
            valid with
            {
                Locale = "AA-00000000-00000000-0000000-0000000",
            },
            valid with
            {
                CurrentSurface = "UNKNOWN",
            },
        };

        foreach (var request in malformed)
        {
            await Assert.ThrowsAsync<ConversationRequestException>(() =>
                service.SendAsync(
                    Guid.NewGuid(),
                    Guid.NewGuid(),
                    Guid.NewGuid(),
                    request,
                    CancellationToken.None
                )
            );
        }
    }

    [Fact]
    public async Task GuideRoutesEverySupportedFallbackWithoutCrossingAuthority()
    {
        var service = CreateService(out _);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var cases = new[]
        {
            (Text: "Show payment details", Surface: "BILLING", Destination: "/profile#billing"),
            (
                Text: "Show current work",
                Surface: "RELATIONSHIP",
                Destination: "/professionals/mine"
            ),
            (Text: "Where should I begin?", Surface: "MARKETPLACE", Destination: "/marketplace"),
            (
                Text: "Where should I continue?",
                Surface: "SETTINGS",
                Destination: "/professionals/mine"
            ),
        };

        foreach (var item in cases)
        {
            var request = new SendPortalInteractionMessageRequestV1(
                "1.0",
                Guid.NewGuid(),
                [new("1.0", "TEXT", item.Text, "en-IN")],
                "en-IN",
                item.Surface
            );
            var result = await service.SendAsync(
                tenantId,
                participantId,
                Guid.NewGuid(),
                request,
                CancellationToken.None
            );

            Assert.Equal(
                item.Destination,
                Assert.Single(result.Value.GuideMessage.Capabilities).Destination
            );
        }
    }

    [Fact]
    public async Task GuestDiscoveryUsesRecentTurnsForFollowUpsAndKeepsTheWelcomeOneTime()
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(
            factory,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            ),
            new MatchingCatalog()
        );
        IGuestConversation guestConversation = service;
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();

        var first = await guestConversation.SendGuestDiscoveryAsync(
            tenantId,
            participantId,
            Guid.NewGuid(),
            GuestRequest("I need marketing growth"),
            CancellationToken.None
        );
        var followUp = await guestConversation.SendGuestDiscoveryAsync(
            tenantId,
            participantId,
            Guid.NewGuid(),
            GuestRequest("Tell me more"),
            CancellationToken.None
        );
        var unrelatedParticipant = await guestConversation.SendGuestDiscoveryAsync(
            tenantId,
            Guid.NewGuid(),
            Guid.NewGuid(),
            GuestRequest("Tell me more"),
            CancellationToken.None
        );
        var browse = await guestConversation.SendGuestDiscoveryAsync(
            tenantId,
            Guid.NewGuid(),
            Guid.NewGuid(),
            GuestRequest("Browse professionals"),
            CancellationToken.None
        );

        Assert.Contains("Welcome to WAOOAW Demo", first.Value.GuideMessage.Content[0].Text);
        Assert.Contains("Fixture marketing professional", first.Value.GuideMessage.Content[0].Text);
        Assert.DoesNotContain(
            "Welcome to WAOOAW Demo",
            followUp.Value.GuideMessage.Content[0].Text
        );
        Assert.Contains(
            "Fixture marketing professional",
            followUp.Value.GuideMessage.Content[0].Text
        );
        Assert.Contains(
            "Tell me the outcome you need",
            unrelatedParticipant.Value.GuideMessage.Content[0].Text
        );
        Assert.Contains("You can explore", browse.Value.GuideMessage.Content[0].Text);
        Assert.Contains(
            "Fixture marketing professional",
            browse.Value.GuideMessage.Content[0].Text
        );
        var guestTimeline = await guestConversation.ListGuestDiscoveryAsync(
            tenantId,
            participantId,
            null,
            20,
            CancellationToken.None
        );
        Assert.Equal("GUEST_DISCOVERY", guestTimeline.Scope);
        Assert.Equal(
            ["CUSTOMER", "GUIDE", "CUSTOMER", "GUIDE"],
            guestTimeline.Items.Select(item => item.Actor)
        );
        await Assert.ThrowsAsync<ConversationRequestException>(() =>
            guestConversation.SendGuestDiscoveryAsync(
                tenantId,
                participantId,
                Guid.NewGuid(),
                GuestRequest("I need marketing growth") with
                {
                    CurrentSurface = "PROFILE",
                },
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task WebMarketplaceAndGuestUseTheSameCataloguePreviewWithoutSharingHistory()
    {
        var service = CreateService(out var factory);
        var tenant = Guid.NewGuid();
        var web = Guid.NewGuid();
        var guest = Guid.NewGuid();
        foreach (var text in new[] { "marketing growth", "What skills?", "What limitations?", "What trial?" })
        {
            var portalResult = await service.SendAsync(
                tenant, web, Guid.NewGuid(), GuestRequest(text), CancellationToken.None);
            var guestResult = await service.SendGuestDiscoveryAsync(
                tenant, guest, Guid.NewGuid(), GuestRequest(text), CancellationToken.None);
            Assert.Equal("PORTAL", portalResult.Value.Scope);
            Assert.Equal("GUEST_DISCOVERY", guestResult.Value.Scope);
            Assert.Equal(portalResult.Value.GuideMessage.Content.Single().Text,
                guestResult.Value.GuideMessage.Content.Single().Text);
            Assert.Equal(portalResult.Value.GuideMessage.Capabilities,
                guestResult.Value.GuideMessage.Capabilities);
            Assert.NotEqual(portalResult.Value.CustomerMessage.MessageId,
                guestResult.Value.CustomerMessage.MessageId);
        }
        await using var db = factory.CreateDbContext();
        Assert.Equal(8, await db.PortalInteractionMessages.CountAsync(value => value.ParticipantId == web));
        Assert.Equal(8, await db.PortalInteractionMessages.CountAsync(value => value.ParticipantId == guest));
        Assert.Empty(await db.ConversationOutbox.ToListAsync());
        Assert.Empty(await db.Executions.ToListAsync());
    }

    [Fact]
    public async Task MarketplaceFollowUpCannotUseAccountSurfaceTextOrEarlierInterruptedSelection()
    {
        var service = CreateService(out _);
        var tenant = Guid.NewGuid();
        var participant = Guid.NewGuid();
        await service.SendAsync(tenant, participant, Guid.NewGuid(),
            GuestRequest("marketing growth"), CancellationToken.None);
        await service.SendAsync(tenant, participant, Guid.NewGuid(),
            GuestRequest("private marketing account settings") with { CurrentSurface = "SETTINGS" },
            CancellationToken.None);
        var result = await service.SendAsync(tenant, participant, Guid.NewGuid(),
            GuestRequest("What skills?"), CancellationToken.None);
        Assert.DoesNotContain("Fixture campaign planning", result.Value.GuideMessage.Content.Single().Text);
        Assert.Contains("identify one professional", result.Value.GuideMessage.Content.Single().Text);
    }

    [Fact]
    public async Task MarketplaceReplayDoesNotBecomeANewGuestTranscriptOrCatalogueInvocation()
    {
        var service = CreateService(out var factory);
        var tenant = Guid.NewGuid();
        var participant = Guid.NewGuid();
        var key = Guid.NewGuid();
        var request = GuestRequest("marketing skills");
        var first = await service.SendAsync(tenant, participant, key, request, CancellationToken.None);
        var replay = await service.SendAsync(tenant, participant, key, request, CancellationToken.None);
        Assert.True(replay.Replayed);
        Assert.Equal("PORTAL", replay.Value.Scope);
        Assert.Equal(first.Value.GuideMessage.MessageId, replay.Value.GuideMessage.MessageId);
        await using var db = factory.CreateDbContext();
        Assert.Equal(2, await db.PortalInteractionMessages.CountAsync());
        Assert.Empty(await db.Set<WhatsAppGuestSession>().ToListAsync());
    }

    [Theory]
    [InlineData("What skills are available?", "Published skills: Fixture campaign planning")]
    [InlineData(
        "What are the limitations?",
        "Published limitations: Customer approval is required"
    )]
    [InlineData("What is the trial?", "The published trial lasts 7 days")]
    public async Task GuestPreviewUsesCurrentCatalogDisclosureWithoutImpersonatingProfessional(
        string question,
        string expected
    )
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(
            factory,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            ),
            new MatchingCatalog()
        );
        var tenant = Guid.NewGuid();
        var participant = Guid.NewGuid();
        await service.SendGuestDiscoveryAsync(
            tenant,
            participant,
            Guid.NewGuid(),
            GuestRequest("marketing growth"),
            CancellationToken.None
        );
        var result = await service.SendGuestDiscoveryAsync(
            tenant,
            participant,
            Guid.NewGuid(),
            GuestRequest(question),
            CancellationToken.None
        );
        var response = Assert.Single(result.Value.GuideMessage.Content).Text;
        Assert.Contains(expected, response);
        Assert.Contains("catalogue preview, not an employed professional", response);
        Assert.DoesNotContain("I will execute", response);
        Assert.Equal(
            "/marketplace",
            Assert.Single(result.Value.GuideMessage.Capabilities).Destination
        );
    }

    [Fact]
    public async Task GuestPreviewUsesReleasedDigitalMarketingCatalog()
    {
        var host = new Mock<IHostEnvironment>();
        host.SetupGet(value => value.ContentRootPath).Returns(AppContext.BaseDirectory);
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(
            factory,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            ),
            new ProfessionalCatalog(host.Object)
        );
        var tenant = Guid.NewGuid();
        var participant = Guid.NewGuid();
        await service.SendGuestDiscoveryAsync(
            tenant,
            participant,
            Guid.NewGuid(),
            GuestRequest("marketing"),
            CancellationToken.None
        );
        var result = await service.SendGuestDiscoveryAsync(
            tenant,
            participant,
            Guid.NewGuid(),
            GuestRequest("What skills?"),
            CancellationToken.None
        );
        var text = Assert.Single(result.Value.GuideMessage.Content).Text;
        Assert.Contains("Digital Marketing Professional", text);
        Assert.Contains("Customer Profiling", text);
        Assert.Contains("Content Strategy and Calendar", text);
        Assert.Contains("catalogue preview, not an employed professional", text);
    }

    [Fact]
    public async Task GuestPreviewRequiresOneCurrentDisclosureAndClarifiesMultipleTopics()
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(
            factory,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            ),
            new MatchingCatalog()
        );
        var tenant = Guid.NewGuid();
        var participant = Guid.NewGuid();
        var noSelection = await service.SendGuestDiscoveryAsync(
            tenant,
            participant,
            Guid.NewGuid(),
            GuestRequest("What skills?"),
            CancellationToken.None
        );
        Assert.Contains(
            "Please identify one professional",
            noSelection.Value.GuideMessage.Content[0].Text
        );
        var multipleTopics = await service.SendGuestDiscoveryAsync(
            tenant,
            participant,
            Guid.NewGuid(),
            GuestRequest("marketing skills and limitations"),
            CancellationToken.None
        );
        Assert.Contains("one at a time", multipleTopics.Value.GuideMessage.Content[0].Text);
    }

    [Theory]
    [InlineData(true, false)]
    [InlineData(false, true)]
    public async Task GuestPreviewFailsClosedForAmbiguousOrStaleCatalog(bool ambiguous, bool stale)
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(
            factory,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            ),
            new MatchingCatalog { Ambiguous = ambiguous, StaleDisclosure = stale }
        );
        var result = await service.SendGuestDiscoveryAsync(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            GuestRequest("marketing skills"),
            CancellationToken.None
        );
        Assert.Contains(
            ambiguous ? "Please identify one professional" : "disclosure is unavailable",
            result.Value.GuideMessage.Content[0].Text
        );
        Assert.DoesNotContain("Published skills:", result.Value.GuideMessage.Content[0].Text);
    }

    [Fact]
    public async Task GuestPreviewReplayKeepsOriginalCanonicalResponse()
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(
            factory,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            ),
            new MatchingCatalog()
        );
        var tenant = Guid.NewGuid();
        var participant = Guid.NewGuid();
        var key = Guid.NewGuid();
        var request = GuestRequest("marketing skills");
        var first = await service.SendGuestDiscoveryAsync(
            tenant,
            participant,
            key,
            request,
            CancellationToken.None
        );
        await service.SendGuestDiscoveryAsync(
            tenant,
            participant,
            Guid.NewGuid(),
            GuestRequest("start over"),
            CancellationToken.None
        );
        var replay = await service.SendGuestDiscoveryAsync(
            tenant,
            participant,
            key,
            request,
            CancellationToken.None
        );
        Assert.True(replay.Replayed);
        Assert.Equal(first.Value.GuideMessage.MessageId, replay.Value.GuideMessage.MessageId);
        Assert.Equal(first.Value.GuideMessage.Content, replay.Value.GuideMessage.Content);
        var timeline = await service.ListGuestDiscoveryAsync(
            tenant,
            participant,
            null,
            20,
            CancellationToken.None
        );
        Assert.Equal(4, timeline.Items.Count);
    }

    [Theory]
    [InlineData("Not marketing, something different")]
    [InlineData("I don't want marketing")]
    [InlineData("Please start over")]
    public async Task GuestCorrectionDoesNotReusePriorSelectionInLaterFollowUps(string correction)
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(
            factory,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            ),
            new MatchingCatalog()
        );
        var tenant = Guid.NewGuid();
        var participant = Guid.NewGuid();
        async Task<string> Send(string text) =>
            (
                await service.SendGuestDiscoveryAsync(
                    tenant,
                    participant,
                    Guid.NewGuid(),
                    GuestRequest(text),
                    CancellationToken.None
                )
            )
                .Value
                .GuideMessage
                .Content[0]
                .Text;

        Assert.Contains("Fixture marketing professional", await Send("marketing growth"));
        var corrected = await Send(correction);
        Assert.Contains("will not use the earlier selection", corrected);
        Assert.DoesNotContain("Fixture marketing professional", corrected);
        var followUp = await Send("Tell me more");
        Assert.DoesNotContain("Fixture marketing professional", followUp);
        Assert.Contains("Tell me the outcome you need", followUp);
        Assert.Contains("Fixture marketing professional", await Send("marketing growth"));
    }

    [Fact]
    public async Task GuestBrowseDoesNotInheritAnEarlierRecommendation()
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(
            factory,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            ),
            new MatchingCatalog()
        );
        var tenant = Guid.NewGuid();
        var participant = Guid.NewGuid();
        await service.SendGuestDiscoveryAsync(
            tenant,
            participant,
            Guid.NewGuid(),
            GuestRequest("marketing growth"),
            CancellationToken.None
        );
        var result = await service.SendGuestDiscoveryAsync(
            tenant,
            participant,
            Guid.NewGuid(),
            GuestRequest("Browse professionals"),
            CancellationToken.None
        );
        Assert.Contains("You can explore", result.Value.GuideMessage.Content[0].Text);
        Assert.DoesNotContain("catalogue suggests", result.Value.GuideMessage.Content[0].Text);
        var followUp = await service.SendGuestDiscoveryAsync(
            tenant,
            participant,
            Guid.NewGuid(),
            GuestRequest("What skills?"),
            CancellationToken.None
        );
        Assert.Contains(
            "Please identify one professional",
            followUp.Value.GuideMessage.Content[0].Text
        );
        Assert.DoesNotContain(
            "Fixture marketing professional",
            followUp.Value.GuideMessage.Content[0].Text
        );
    }

    [Theory]
    [InlineData("I need legal help, what skills are available?")]
    [InlineData("Help me with accounting")]
    public async Task GuestUnrelatedRequestInterruptsEarlierRecommendation(string unrelated)
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(
            factory,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            ),
            new MatchingCatalog()
        );
        var tenant = Guid.NewGuid();
        var participant = Guid.NewGuid();
        async Task<string> Send(string text) =>
            (
                await service.SendGuestDiscoveryAsync(
                    tenant,
                    participant,
                    Guid.NewGuid(),
                    GuestRequest(text),
                    CancellationToken.None
                )
            )
                .Value
                .GuideMessage
                .Content[0]
                .Text;

        Assert.Contains("Fixture marketing professional", await Send("marketing growth"));
        Assert.DoesNotContain("Fixture marketing professional", await Send(unrelated));
        Assert.DoesNotContain("Fixture marketing professional", await Send("What skills?"));
        Assert.Contains("Fixture marketing professional", await Send("marketing growth"));
        Assert.Contains("Fixture marketing professional", await Send("What skills?"));
    }

    [Fact]
    public async Task GuestNoticeUsesSharedConversationWithoutRunningCatalogueDiscovery()
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(
            factory,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            )
        );
        IGuestConversation guestConversation = service;
        const string notice = "Guest discovery is closed.";
        var result = await guestConversation.SendGuestNoticeAsync(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            GuestRequest("I need marketing growth"),
            notice,
            CancellationToken.None
        );

        Assert.Equal(notice, result.Value.GuideMessage.Content[0].Text);
        Assert.Equal(
            "/marketplace",
            Assert.Single(result.Value.GuideMessage.Capabilities).Destination
        );
    }

    [Fact]
    public async Task PaginationAndExpectedCursorUseAuthoritativeSequence()
    {
        var service = CreateService(out _);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var initial = await service.ListAsync(
            tenantId,
            participantId,
            null,
            1,
            CancellationToken.None
        );
        var first = new SendPortalInteractionMessageRequestV1(
            "1.0",
            Guid.NewGuid(),
            [new("1.0", "TEXT", "First question", "en-IN")],
            "en-IN",
            "MARKETPLACE",
            initial.AuthoritativeCursor
        );

        await service.SendAsync(
            tenantId,
            participantId,
            Guid.NewGuid(),
            first,
            CancellationToken.None
        );
        await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
            service.SendAsync(
                tenantId,
                participantId,
                Guid.NewGuid(),
                first with
                {
                    ClientMessageId = Guid.NewGuid(),
                },
                CancellationToken.None
            )
        );

        var latest = await service.ListAsync(
            tenantId,
            participantId,
            null,
            1,
            CancellationToken.None
        );
        Assert.True(latest.HasMore);
        Assert.NotNull(latest.NextCursor);

        var previous = await service.ListAsync(
            tenantId,
            participantId,
            latest.NextCursor,
            1,
            CancellationToken.None
        );
        Assert.Single(previous.Items);
    }

    [Fact]
    public async Task NullPersistedCollectionsProjectAsEmptyCollections()
    {
        var service = CreateService(out var factory);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var contextId = Guid.NewGuid();
        await using (var db = factory.CreateDbContext())
        {
            db.PortalInteractionContexts.Add(
                new PortalInteractionContext
                {
                    ContextId = contextId,
                    TenantId = tenantId,
                    ParticipantId = participantId,
                    NextMessageSequence = 2,
                }
            );
            db.PortalInteractionMessages.Add(
                new PortalInteractionMessage
                {
                    TenantId = tenantId,
                    ContextId = contextId,
                    ParticipantId = participantId,
                    Sequence = 1,
                    Actor = "GUIDE",
                    ContentJson = "null",
                    CapabilitiesJson = "null",
                    CurrentSurface = "MARKETPLACE",
                }
            );
            await db.SaveChangesAsync();
        }

        var timeline = await service.ListAsync(
            tenantId,
            participantId,
            null,
            20,
            CancellationToken.None
        );

        Assert.Empty(Assert.Single(timeline.Items).Content);
        Assert.Empty(timeline.Items[0].Capabilities);
    }

    private static PortalInteractionService CreateService(out InMemoryConversationFactory factory)
    {
        factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        return new PortalInteractionService(
            factory,
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            ),
            new MatchingCatalog()
        );
    }

    private static SendPortalInteractionMessageRequestV1 GuestRequest(string text) =>
        new("1.0", Guid.NewGuid(), [new("1.0", "TEXT", text, "en-IN")], "en-IN", "MARKETPLACE");

    private sealed class MatchingCatalog : IProfessionalCatalog
    {
        public bool Ambiguous { get; init; }
        public bool StaleDisclosure { get; init; }

        public IReadOnlyList<ProfessionalDiscoveryResult> Discover(string outcome) =>
            outcome.Contains("marketing", StringComparison.OrdinalIgnoreCase)
                ? Ambiguous
                    ?
                    [
                        new(
                            "DIGITAL_MARKETING",
                            "v1",
                            "Fixture marketing professional",
                            ["Supports marketing growth"],
                            new(true, "Fixture catalogue match")
                        ),
                        new(
                            "OTHER_MARKETING",
                            "v1",
                            "Other marketing professional",
                            ["Supports marketing growth"],
                            new(true, "Fixture catalogue match")
                        ),
                    ]
                    :
                    [
                        new(
                            "DIGITAL_MARKETING",
                            "v1",
                            "Fixture marketing professional",
                            ["Supports marketing growth"],
                            new(true, "Fixture catalogue match")
                        ),
                    ]
                : [];

        public ProfessionalDisclosure? GetDisclosure(string professionalType) =>
            Browse(professionalType, null).SingleOrDefault();

        public IReadOnlyList<ProfessionalDisclosure> Browse(
            string? professionalType,
            string? query
        ) =>
            [
                new(
                    "DIGITAL_MARKETING",
                    StaleDisclosure ? "v2" : "v1",
                    "digital-marketing",
                    "Fixture marketing professional",
                    ["Supports marketing growth"],
                    [new("fixture-skill", "Fixture campaign planning", true, null)],
                    ["Customer approval is required"],
                    [],
                    [],
                    new(true, 7, false, false),
                    "Fixture catalogue disclosure",
                    new("INR", 0, "MONTHLY", "Fixture"),
                    new(true, "Fixture catalogue match")
                ),
            ];
    }
}
