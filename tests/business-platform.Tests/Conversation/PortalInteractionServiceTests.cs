// Implements: work-contracts/WC-096-conversational-customer-portal.md §5
// constitutional_basis: C-026, C-049, C-059, C-063

using Microsoft.Extensions.Options;
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
}