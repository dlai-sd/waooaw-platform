// Implements: work-contracts/WC-096-conversational-customer-portal.md §5
// constitutional_basis: C-026, C-049, C-059, C-063

using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class PortalInteractionsControllerTests
{
    [Fact]
    public async Task MembershipAuthorityOwnsPersistentPortalTimeline()
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(factory, new ConversationCursorCodec(
            Options.Create(new ConversationCursorOptions { HmacKey = new string('c', 48) })));
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var context = new DefaultHttpContext();
        context.Items[CustomerMembershipMiddleware.MembershipItem] =
            new CustomerWorkspaceMembership(participantId, tenantId, Guid.NewGuid(), ["OWNER"]);
        context.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString();
        var controller = new PortalInteractionsController(service)
        {
            ControllerContext = new ControllerContext { HttpContext = context },
        };
        var request = new SendPortalInteractionMessageRequestV1(
            "1.0", Guid.NewGuid(), [new("1.0", "TEXT", "Show my agents", "en-IN")], "en-IN", "MY_AGENTS");

        Assert.IsType<AcceptedResult>(await controller.SendAsync(request, CancellationToken.None));
        var listed = Assert.IsType<OkObjectResult>(await controller.ListAsync(null, 40, CancellationToken.None));
        var timeline = Assert.IsType<PortalInteractionTimelinePageV1>(listed.Value);

        Assert.Equal("PORTAL", timeline.Scope);
        Assert.Equal(["CUSTOMER", "GUIDE"], timeline.Items.Select(item => item.Actor));
        Assert.All(timeline.Items, item => Assert.Equal("MY_AGENTS", item.CurrentSurface));
    }

    [Fact]
    public async Task MissingAuthorityAndInvalidIdempotencyFailClosed()
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(factory, new ConversationCursorCodec(
            Options.Create(new ConversationCursorOptions { HmacKey = new string('c', 48) })));
        var controller = new PortalInteractionsController(service)
        {
            ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() },
        };
        var request = new SendPortalInteractionMessageRequestV1(
            "1.0", Guid.NewGuid(), [new("1.0", "TEXT", "Show my agents", "en-IN")], "en-IN", "MY_AGENTS");

        Assert.Equal(401, Assert.IsType<ObjectResult>(
            await controller.ListAsync(null, 40, CancellationToken.None)).StatusCode);

        controller.HttpContext.Items[CustomerMembershipMiddleware.MembershipItem] =
            new CustomerWorkspaceMembership(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), ["OWNER"]);
        Assert.Equal(400, Assert.IsType<ObjectResult>(
            await controller.SendAsync(request, CancellationToken.None)).StatusCode);
    }
}