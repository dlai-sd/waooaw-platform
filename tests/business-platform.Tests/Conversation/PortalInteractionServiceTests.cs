// Implements: work-contracts/WC-096-conversational-customer-portal.md §5
// constitutional_basis: C-026, C-049, C-059, C-063

using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class PortalInteractionServiceTests
{
    [Fact]
    public async Task SendPersistsScopedGuideExchangeAndReplaysOneOutcome()
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(factory, new ConversationCursorCodec(
            Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })));
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var idempotencyKey = Guid.NewGuid();
        var request = new SendPortalInteractionMessageRequestV1(
            "1.0", Guid.NewGuid(), [new("1.0", "TEXT", "Show my billing", "en-IN")], "en-IN", "MY_AGENTS");

        var accepted = await service.SendAsync(tenantId, participantId, idempotencyKey, request, CancellationToken.None);
        var replay = await service.SendAsync(tenantId, participantId, idempotencyKey, request, CancellationToken.None);
        var ownerTimeline = await service.ListAsync(tenantId, participantId, null, 20, CancellationToken.None);
        var otherTimeline = await service.ListAsync(tenantId, Guid.NewGuid(), null, 20, CancellationToken.None);

        Assert.False(accepted.Replayed);
        Assert.True(replay.Replayed);
        Assert.Equal(accepted.Value.CustomerMessage.MessageId, replay.Value.CustomerMessage.MessageId);
        Assert.Equal(["CUSTOMER", "GUIDE"], ownerTimeline.Items.Select(item => item.Actor));
        Assert.Equal("/profile#billing", Assert.Single(ownerTimeline.Items[1].Capabilities).Destination);
        Assert.Empty(otherTimeline.Items);
        Assert.NotEqual(ownerTimeline.ContextId, otherTimeline.ContextId);
    }

    [Fact]
    public async Task IdempotencyRejectsChangedPayloadAndCursorIsContextBound()
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(factory, new ConversationCursorCodec(
            Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })));
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var idempotencyKey = Guid.NewGuid();
        var request = new SendPortalInteractionMessageRequestV1(
            "1.0", Guid.NewGuid(), [new("1.0", "TEXT", "Show alerts", "en-IN")], "en-IN", "ALERTS");
        await service.SendAsync(tenantId, participantId, idempotencyKey, request, CancellationToken.None);

        await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() => service.SendAsync(
            tenantId, participantId, idempotencyKey, request with { CurrentSurface = "SETTINGS" }, CancellationToken.None));
        var owner = await service.ListAsync(tenantId, participantId, null, 20, CancellationToken.None);
        await Assert.ThrowsAsync<ConversationCursorExpiredException>(() => service.ListAsync(
            tenantId, Guid.NewGuid(), owner.AuthoritativeCursor, 20, CancellationToken.None));
    }

    [Fact]
    public async Task RejectsEveryMalformedRequestShape()
    {
        var service = CreateService(out _);
        var valid = new SendPortalInteractionMessageRequestV1(
            "1.0", Guid.NewGuid(), [new("1.0", "TEXT", "Help me navigate", "en-IN")], "en-IN", "MY_AGENTS");
        var malformed = new[]
        {
            valid with { SchemaVersion = "2.0" },
            valid with { ClientMessageId = Guid.Empty },
            valid with { Content = [] },
            valid with { Content = [new("1.0", "IMAGE", "Help me navigate", "en-IN")] },
            valid with { Content = [new("1.0", "TEXT", " ", "en-IN")] },
            valid with { Content = [new("1.0", "TEXT", new string('x', 4001), "en-IN")] },
            valid with { Locale = " " },
            valid with { CurrentSurface = "UNKNOWN" },
        };

        foreach (var request in malformed)
        {
            await Assert.ThrowsAsync<ConversationRequestException>(() => service.SendAsync(
                Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), request, CancellationToken.None));
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
            (Text: "Show current work", Surface: "RELATIONSHIP", Destination: "/professionals/mine"),
            (Text: "Where should I begin?", Surface: "MARKETPLACE", Destination: "/marketplace"),
            (Text: "Where should I continue?", Surface: "SETTINGS", Destination: "/professionals/mine"),
        };

        foreach (var item in cases)
        {
            var request = new SendPortalInteractionMessageRequestV1(
                "1.0", Guid.NewGuid(), [new("1.0", "TEXT", item.Text, "en-IN")], "en-IN", item.Surface);
            var result = await service.SendAsync(
                tenantId, participantId, Guid.NewGuid(), request, CancellationToken.None);

            Assert.Equal(item.Destination, Assert.Single(result.Value.GuideMessage.Capabilities).Destination);
        }
    }

    [Fact]
    public async Task PaginationAndExpectedCursorUseAuthoritativeSequence()
    {
        var service = CreateService(out _);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var initial = await service.ListAsync(tenantId, participantId, null, 1, CancellationToken.None);
        var first = new SendPortalInteractionMessageRequestV1(
            "1.0", Guid.NewGuid(), [new("1.0", "TEXT", "First question", "en-IN")],
            "en-IN", "MARKETPLACE", initial.AuthoritativeCursor);

        await service.SendAsync(tenantId, participantId, Guid.NewGuid(), first, CancellationToken.None);
        await Assert.ThrowsAsync<ConversationStateConflictException>(() => service.SendAsync(
            tenantId,
            participantId,
            Guid.NewGuid(),
            first with { ClientMessageId = Guid.NewGuid() },
            CancellationToken.None));

        var latest = await service.ListAsync(tenantId, participantId, null, 1, CancellationToken.None);
        Assert.True(latest.HasMore);
        Assert.NotNull(latest.NextCursor);

        var previous = await service.ListAsync(
            tenantId, participantId, latest.NextCursor, 1, CancellationToken.None);
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
            db.PortalInteractionContexts.Add(new PortalInteractionContext
            {
                ContextId = contextId,
                TenantId = tenantId,
                ParticipantId = participantId,
                NextMessageSequence = 2,
            });
            db.PortalInteractionMessages.Add(new PortalInteractionMessage
            {
                TenantId = tenantId,
                ContextId = contextId,
                ParticipantId = participantId,
                Sequence = 1,
                Actor = "GUIDE",
                ContentJson = "null",
                CapabilitiesJson = "null",
                CurrentSurface = "MARKETPLACE",
            });
            await db.SaveChangesAsync();
        }

        var timeline = await service.ListAsync(tenantId, participantId, null, 20, CancellationToken.None);

        Assert.Empty(Assert.Single(timeline.Items).Content);
        Assert.Empty(timeline.Items[0].Capabilities);
    }

    private static PortalInteractionService CreateService(out InMemoryConversationFactory factory)
    {
        factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        return new PortalInteractionService(factory, new ConversationCursorCodec(
            Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })));
    }
}