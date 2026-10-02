using System.Security.Claims;
using Microsoft.AspNetCore.Http;
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

    private static DefaultHttpContext CustomerContext(params Claim[] additionalClaims)
    {
        var claims = new[] { new Claim(ClaimTypes.Role, "customer") }.Concat(additionalClaims);
        return new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity(claims, "test")),
        };
    }
}
