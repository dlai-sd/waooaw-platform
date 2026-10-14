using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Xunit;

namespace BusinessPlatform.Tests;

public sealed class CustomerMembershipMiddlewareTests
{
    [Fact]
    public async Task UnmatchedRoutePreservesCustomerRoutingResult()
    {
        var context = CustomerContext();
        var journeyWasActive = false;
        var middleware = new CustomerMembershipMiddleware(nextContext =>
        {
            journeyWasActive = nextContext.Items.ContainsKey(
                CustomerMembershipMiddleware.JourneyItem
            );
            nextContext.Response.StatusCode = StatusCodes.Status404NotFound;
            return Task.CompletedTask;
        });

        await middleware.InvokeAsync(context);

        Assert.True(journeyWasActive);
        Assert.Equal(StatusCodes.Status404NotFound, context.Response.StatusCode);
        Assert.False(context.Items.ContainsKey(CustomerMembershipMiddleware.JourneyItem));
    }

    [Fact]
    public async Task UnmatchedRouteRejectsCustomerWithForgedTenantAuthority()
    {
        var context = CustomerContext(new Claim("tenant_id", Guid.NewGuid().ToString()));
        var nextWasCalled = false;
        var middleware = new CustomerMembershipMiddleware(_ =>
        {
            nextWasCalled = true;
            return Task.CompletedTask;
        });

        await middleware.InvokeAsync(context);

        Assert.False(nextWasCalled);
        Assert.Equal(StatusCodes.Status403Forbidden, context.Response.StatusCode);
    }

    [Fact]
    public async Task AnonymousEndpointBypassesCustomerJourney()
    {
        var context = CustomerContext();
        context.SetEndpoint(
            new Endpoint(
                _ => Task.CompletedTask,
                new EndpointMetadataCollection(new AllowAnonymousAttribute()),
                "anonymous"
            )
        );
        var nextWasCalled = false;
        var middleware = new CustomerMembershipMiddleware(_ =>
        {
            nextWasCalled = true;
            return Task.CompletedTask;
        });

        await middleware.InvokeAsync(context);

        Assert.True(nextWasCalled);
    }

    [Fact]
    public async Task NonCustomerInternalServiceEndpointBypassesCustomerJourney()
    {
        var context = new DefaultHttpContext { User = new ClaimsPrincipal(new ClaimsIdentity()) };
        context.SetEndpoint(
            new Endpoint(
                _ => Task.CompletedTask,
                new EndpointMetadataCollection(
                    new AuthorizeAttribute { Policy = "InternalService" },
                    new ControllerActionDescriptor()
                ),
                "internal"
            )
        );
        var nextWasCalled = false;
        var middleware = new CustomerMembershipMiddleware(_ =>
        {
            nextWasCalled = true;
            return Task.CompletedTask;
        });

        await middleware.InvokeAsync(context);

        Assert.True(nextWasCalled);
    }

    [Fact]
    public async Task CustomerControllerWithoutIdentityRouteFailsClosed()
    {
        var context = CustomerContext();
        context.SetEndpoint(
            new Endpoint(
                _ => Task.CompletedTask,
                new EndpointMetadataCollection(new ControllerActionDescriptor()),
                "controller"
            )
        );
        var middleware = new CustomerMembershipMiddleware(_ => Task.CompletedTask);

        await middleware.InvokeAsync(context);

        Assert.Equal(StatusCodes.Status403Forbidden, context.Response.StatusCode);
    }

    [Fact]
    public async Task MethodNotAllowedPreservesCustomerJourneyWithoutAuthority()
    {
        var context = CustomerContext();
        context.SetEndpoint(
            new Endpoint(
                _ => Task.CompletedTask,
                new EndpointMetadataCollection(),
                "405 HTTP Method Not Supported"
            )
        );
        var journeyWasActive = false;
        var middleware = new CustomerMembershipMiddleware(current =>
        {
            journeyWasActive = current.Items.ContainsKey(CustomerMembershipMiddleware.JourneyItem);
            current.Response.StatusCode = StatusCodes.Status405MethodNotAllowed;
            return Task.CompletedTask;
        });

        await middleware.InvokeAsync(context);

        Assert.True(journeyWasActive);
        Assert.Equal(StatusCodes.Status405MethodNotAllowed, context.Response.StatusCode);
    }

    [Fact]
    public async Task MethodNotAllowedRejectsForgedRoleAuthority()
    {
        var context = CustomerContext(new Claim("waooaw_roles", "OWNER"));
        context.SetEndpoint(
            new Endpoint(
                _ => Task.CompletedTask,
                new EndpointMetadataCollection(),
                "405 HTTP Method Not Supported"
            )
        );
        var middleware = new CustomerMembershipMiddleware(_ => Task.CompletedTask);

        await middleware.InvokeAsync(context);

        Assert.Equal(StatusCodes.Status403Forbidden, context.Response.StatusCode);
    }

    [Fact]
    public async Task UnmatchedNonCustomerBypassesCustomerJourney()
    {
        var context = new DefaultHttpContext { User = new ClaimsPrincipal(new ClaimsIdentity()) };
        var nextWasCalled = false;
        var middleware = new CustomerMembershipMiddleware(_ =>
        {
            nextWasCalled = true;
            return Task.CompletedTask;
        });

        await middleware.InvokeAsync(context);

        Assert.True(nextWasCalled);
    }

    [Fact]
    public async Task NonCustomerControllerBypassesCustomerJourney()
    {
        var context = new DefaultHttpContext { User = new ClaimsPrincipal(new ClaimsIdentity()) };
        context.SetEndpoint(
            new Endpoint(
                _ => Task.CompletedTask,
                new EndpointMetadataCollection(new ControllerActionDescriptor()),
                "controller"
            )
        );
        var nextWasCalled = false;
        var middleware = new CustomerMembershipMiddleware(_ =>
        {
            nextWasCalled = true;
            return Task.CompletedTask;
        });

        await middleware.InvokeAsync(context);

        Assert.True(nextWasCalled);
    }

    private static DefaultHttpContext CustomerContext(params Claim[] additionalClaims)
    {
        var claims = new[] { new Claim("azp", "waooaw-web") }.Concat(additionalClaims);
        return new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity(claims, "test")),
        };
    }
}
