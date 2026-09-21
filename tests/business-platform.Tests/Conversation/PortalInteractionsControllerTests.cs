// Implements: work-contracts/WC-096-conversational-customer-portal.md §5
// constitutional_basis: C-026, C-049, C-059, C-063

using System.Security.Claims;
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
    [Theory]
    [InlineData(nameof(PortalInteractionsController.ListAsync))]
    [InlineData(nameof(PortalInteractionsController.SendAsync))]
    public void PortalRoutesRequireResolvedMembership(string methodName)
    {
        var method = typeof(PortalInteractionsController).GetMethod(methodName)!;
        var route = Assert.Single(
            method.GetCustomAttributes(typeof(CustomerIdentityRouteAttribute), true)
        );

        Assert.True(Assert.IsType<CustomerIdentityRouteAttribute>(route).RequiresMembership);
    }

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

        var unauthenticated = new PortalInteractionsController(service)
        {
            ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() },
        };
        Assert.Equal(401, Assert.IsType<ObjectResult>(
            await unauthenticated.SendAsync(request, CancellationToken.None)).StatusCode);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(101)]
    public async Task InvalidTimelineLimitsMapToBadRequest(int limit)
    {
        var controller = CreateController(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid());

        Assert.Equal(400, Assert.IsType<ObjectResult>(
            await controller.ListAsync(null, limit, CancellationToken.None)).StatusCode);
    }

    [Fact]
    public async Task ReplayAndServiceConflictsMapToStableHttpOutcomes()
    {
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var idempotencyKey = Guid.NewGuid();
        var controller = CreateController(tenantId, participantId, idempotencyKey);
        var request = new SendPortalInteractionMessageRequestV1(
            "1.0", Guid.NewGuid(), [new("1.0", "TEXT", "Show my agents", "en-IN")], "en-IN", "MY_AGENTS");

        Assert.IsType<AcceptedResult>(await controller.SendAsync(request, CancellationToken.None));
        Assert.IsType<OkObjectResult>(await controller.SendAsync(request, CancellationToken.None));

        var idempotencyConflict = Assert.IsType<ObjectResult>(await controller.SendAsync(
            request with { CurrentSurface = "SETTINGS" }, CancellationToken.None));
        Assert.Equal(409, idempotencyConflict.StatusCode);

        controller.HttpContext.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString();
        var malformed = Assert.IsType<ObjectResult>(await controller.SendAsync(
            request with { SchemaVersion = "2.0" }, CancellationToken.None));
        Assert.Equal(400, malformed.StatusCode);
    }

    [Fact]
    public async Task CursorConflictsMapToReconciliationAndExpiryOutcomes()
    {
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var controller = CreateController(tenantId, participantId, Guid.NewGuid());
        var initialResult = Assert.IsType<OkObjectResult>(
            await controller.ListAsync(null, 20, CancellationToken.None));
        var initial = Assert.IsType<PortalInteractionTimelinePageV1>(initialResult.Value);
        var request = new SendPortalInteractionMessageRequestV1(
            "1.0", Guid.NewGuid(), [new("1.0", "TEXT", "Show my agents", "en-IN")],
            "en-IN", "MY_AGENTS", initial.AuthoritativeCursor);
        Assert.IsType<AcceptedResult>(await controller.SendAsync(request, CancellationToken.None));

        controller.HttpContext.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString();
        var stateConflict = Assert.IsType<ObjectResult>(await controller.SendAsync(
            request with { ClientMessageId = Guid.NewGuid() }, CancellationToken.None));
        Assert.Equal(409, stateConflict.StatusCode);

        controller.HttpContext.Items[CustomerMembershipMiddleware.MembershipItem] =
            new CustomerWorkspaceMembership(Guid.NewGuid(), tenantId, Guid.NewGuid(), ["OWNER"]);
        var expired = Assert.IsType<ObjectResult>(
            await controller.ListAsync(initial.AuthoritativeCursor, 20, CancellationToken.None));
        Assert.Equal(410, expired.StatusCode);
    }

    [Theory]
    [InlineData("participant_id")]
    [InlineData(ClaimTypes.NameIdentifier)]
    [InlineData("sub")]
    public async Task ClaimAuthorityFallbacksOwnAStablePortalContext(string claimType)
    {
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var context = new DefaultHttpContext();
        context.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString();
        context.User = new ClaimsPrincipal(new ClaimsIdentity([new Claim(claimType, participantId.ToString())]));
        var controller = CreateController(context);

        var listed = Assert.IsType<OkObjectResult>(
            await controller.ListAsync(null, 20, CancellationToken.None));
        var repeated = Assert.IsType<OkObjectResult>(
            await controller.ListAsync(null, 20, CancellationToken.None));

        Assert.Equal(
            Assert.IsType<PortalInteractionTimelinePageV1>(listed.Value).ContextId,
            Assert.IsType<PortalInteractionTimelinePageV1>(repeated.Value).ContextId);
    }

    [Theory]
    [InlineData(42)]
    [InlineData("not-a-guid")]
    public async Task InvalidTenantFallbackFailsClosed(object tenantValue)
    {
        var context = new DefaultHttpContext();
        context.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantValue;
        context.User = new ClaimsPrincipal(new ClaimsIdentity([new Claim("sub", Guid.NewGuid().ToString())]));
        var controller = CreateController(context);

        Assert.Equal(401, Assert.IsType<ObjectResult>(
            await controller.ListAsync(null, 20, CancellationToken.None)).StatusCode);
    }

    [Fact]
    public async Task UnexpectedStoredPayloadMapsToServiceUnavailable()
    {
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        await using (var db = factory.CreateDbContext())
        {
            var portalContext = new PortalInteractionContext { TenantId = tenantId, ParticipantId = participantId };
            db.PortalInteractionContexts.Add(portalContext);
            db.PortalInteractionMessages.Add(new PortalInteractionMessage
            {
                TenantId = tenantId,
                ContextId = portalContext.ContextId,
                ParticipantId = participantId,
                Sequence = 1,
                Actor = "GUIDE",
                ContentJson = "not-json",
                CurrentSurface = "MARKETPLACE",
            });
            await db.SaveChangesAsync();
        }
        var httpContext = new DefaultHttpContext();
        httpContext.Items[CustomerMembershipMiddleware.MembershipItem] =
            new CustomerWorkspaceMembership(participantId, tenantId, Guid.NewGuid(), ["OWNER"]);
        var controller = new PortalInteractionsController(new PortalInteractionService(
            factory,
            new ConversationCursorCodec(Options.Create(new ConversationCursorOptions { HmacKey = new string('c', 48) }))))
        {
            ControllerContext = new ControllerContext { HttpContext = httpContext },
        };

        Assert.Equal(503, Assert.IsType<ObjectResult>(
            await controller.ListAsync(null, 20, CancellationToken.None)).StatusCode);
    }

    private static PortalInteractionsController CreateController(
        Guid tenantId,
        Guid participantId,
        Guid idempotencyKey)
    {
        var context = new DefaultHttpContext();
        context.Items[CustomerMembershipMiddleware.MembershipItem] =
            new CustomerWorkspaceMembership(participantId, tenantId, Guid.NewGuid(), ["OWNER"]);
        context.Request.Headers["Idempotency-Key"] = idempotencyKey.ToString();
        return CreateController(context);
    }

    private static PortalInteractionsController CreateController(DefaultHttpContext context)
    {
        var factory = new InMemoryConversationFactory(Guid.NewGuid().ToString("N"));
        var service = new PortalInteractionService(factory, new ConversationCursorCodec(
            Options.Create(new ConversationCursorOptions { HmacKey = new string('c', 48) })));
        return new PortalInteractionsController(service)
        {
            ControllerContext = new ControllerContext { HttpContext = context },
        };
    }
}