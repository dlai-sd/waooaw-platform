// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R006
// Constitutional basis: C-023, C-026, C-059, C-063, C-078

using System.Security.Claims;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.CustomerDataRequests;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class CustomerDataRequestsControllerTests
{
    private static readonly Guid Tenant = Guid.NewGuid();
    private static readonly DateTimeOffset Now = new(2026, 12, 1, 9, 0, 0, TimeSpan.Zero);

    private static CustomerDataRequest Row(string kind = "EXPORT", string state = "RECEIVED") =>
        new(Guid.NewGuid(), Tenant, kind, state, Now, null, null);

    private static CustomerDataRequestsController Customer(
        Mock<ICustomerDataRequests> store,
        string[] roles,
        string? key,
        bool withTenant = true
    )
    {
        var context = new DefaultHttpContext();
        if (withTenant)
        {
            context.Items[TenantIsolationMiddleware.TenantIdItemKey] = Tenant.ToString("D");
            context.Items[CustomerMembershipMiddleware.MembershipItem] =
                new CustomerWorkspaceMembership(Guid.NewGuid(), Tenant, Guid.NewGuid(), roles);
        }
        if (key is not null)
            context.Request.Headers["Idempotency-Key"] = key;
        context.User = new ClaimsPrincipal(
            new ClaimsIdentity([new Claim("sub", "customer-1")], "test")
        );
        return new CustomerDataRequestsController(store.Object)
        {
            ControllerContext = new ControllerContext { HttpContext = context },
        };
    }

    [Fact]
    public async Task OnlyTheOwnerCanAskAndAHashedActorIsRecorded()
    {
        var store = new Mock<ICustomerDataRequests>();
        string? actorHash = null;
        store
            .Setup(value =>
                value.RequestAsync(Tenant, It.IsAny<string>(), "ERASURE", It.IsAny<Guid>(), default)
            )
            .Callback<Guid, string, string, Guid, CancellationToken>(
                (_, actor, _, _, _) => actorHash = actor
            )
            .ReturnsAsync((Row("ERASURE"), true));
        var body = new CustomerDataRequestBody("1.0.0", "ERASURE");

        var denied = await Customer(store, ["MANAGER"], Guid.NewGuid().ToString())
            .RequestAsync(body, default);
        var created = await Customer(store, ["OWNER"], Guid.NewGuid().ToString())
            .RequestAsync(body, default);

        Assert.Equal(403, Assert.IsType<ObjectResult>(denied).StatusCode);
        Assert.Equal(201, Assert.IsType<ObjectResult>(created).StatusCode);
        Assert.Matches("^[0-9a-f]{64}$", actorHash);
        Assert.DoesNotContain("customer-1", actorHash);
    }

    [Fact]
    public async Task AnAlreadyOpenRequestAnswersOkAndBadInputIsRefused()
    {
        var store = new Mock<ICustomerDataRequests>();
        store
            .Setup(value =>
                value.RequestAsync(Tenant, It.IsAny<string>(), "EXPORT", It.IsAny<Guid>(), default)
            )
            .ReturnsAsync((Row(), false));
        var key = Guid.NewGuid().ToString();

        var again = await Customer(store, ["OWNER"], key)
            .RequestAsync(new("1.0.0", "EXPORT"), default);
        var badKind = await Customer(store, ["OWNER"], key)
            .RequestAsync(new("1.0.0", "DELETE_EVERYTHING"), default);
        var noKey = await Customer(store, ["OWNER"], null)
            .RequestAsync(new("1.0.0", "EXPORT"), default);
        var badSchema = await Customer(store, ["OWNER"], key)
            .RequestAsync(new("9.9.9", "EXPORT"), default);

        Assert.IsType<OkObjectResult>(again);
        Assert.All(
            [badKind, noKey, badSchema],
            result => Assert.Equal(400, Assert.IsType<ObjectResult>(result).StatusCode)
        );
    }

    [Fact]
    public async Task WithoutATenantTheCustomerIsUnauthorizedAndTheListIsTheirOwn()
    {
        var store = new Mock<ICustomerDataRequests>();
        store.Setup(value => value.ListForCustomerAsync(Tenant, default)).ReturnsAsync([Row()]);

        Assert.IsType<UnauthorizedResult>(
            await Customer(store, ["OWNER"], null, withTenant: false).ListAsync(default)
        );
        Assert.IsType<UnauthorizedResult>(
            await Customer(store, ["OWNER"], Guid.NewGuid().ToString(), withTenant: false)
                .RequestAsync(new("1.0.0", "EXPORT"), default)
        );
        Assert.IsType<OkObjectResult>(await Customer(store, ["MANAGER"], null).ListAsync(default));
    }
}

public sealed class OperationsDataRequestsControllerTests
{
    private static readonly DateTimeOffset Now = new(2026, 12, 1, 9, 0, 0, TimeSpan.Zero);

    private static OperationsDataRequestsController Operator(
        Mock<ICustomerDataRequests> store,
        bool founder,
        bool freshSignIn
    )
    {
        var claims = new List<Claim> { new("participant_id", "founder-1") };
        if (founder)
            claims.Add(new Claim("role", "founder"));
        if (freshSignIn)
        {
            claims.Add(new Claim("auth_time", Now.ToUnixTimeSeconds().ToString()));
            claims.Add(new Claim("acr", "2"));
            claims.Add(new Claim("amr", "otp"));
        }
        var clock = new Mock<TimeProvider>();
        clock.Setup(value => value.GetUtcNow()).Returns(Now);
        return new OperationsDataRequestsController(store.Object, clock.Object)
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext
                {
                    User = new ClaimsPrincipal(new ClaimsIdentity(claims, "test")),
                },
            },
        };
    }

    [Fact]
    public async Task OnlyTheFounderReadsTheOpenRequestsAndNothingPersonalIsReturned()
    {
        var store = new Mock<ICustomerDataRequests>();
        store
            .Setup(value => value.ListOpenForOperatorAsync(50, default))
            .ReturnsAsync([
                new CustomerDataRequest(
                    Guid.NewGuid(),
                    Guid.NewGuid(),
                    "ERASURE",
                    "RECEIVED",
                    Now,
                    null,
                    null
                ),
            ]);

        var denied = await Operator(store, founder: false, freshSignIn: true)
            .ListOpenAsync(default);
        var listed = await Operator(store, founder: true, freshSignIn: false)
            .ListOpenAsync(default);

        Assert.Equal(403, Assert.IsType<ObjectResult>(denied).StatusCode);
        var json = System.Text.Json.JsonSerializer.Serialize(
            Assert.IsType<OkObjectResult>(listed).Value
        );
        Assert.Contains("ERASURE", json);
        Assert.DoesNotContain("note", json, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task ClosingNeedsTheFounderAFreshSignInAndANote()
    {
        var store = new Mock<ICustomerDataRequests>();
        var id = Guid.NewGuid();
        store
            .Setup(value => value.ResolveAsync(id, true, "founder-1", "Exported and sent", default))
            .ReturnsAsync(
                new CustomerDataRequest(
                    id,
                    Guid.NewGuid(),
                    "EXPORT",
                    "COMPLETED",
                    Now,
                    Now,
                    "Exported and sent"
                )
            );
        store
            .Setup(value =>
                value.ResolveAsync(
                    It.Is<Guid>(v => v != id),
                    It.IsAny<bool>(),
                    It.IsAny<string>(),
                    It.IsAny<string>(),
                    default
                )
            )
            .ReturnsAsync((CustomerDataRequest?)null);
        var body = new ResolveDataRequestBody("1.0.0", true, "Exported and sent");

        var notFounder = await Operator(store, false, true).ResolveAsync(id, body, default);
        var stale = await Operator(store, true, false).ResolveAsync(id, body, default);
        var noNote = await Operator(store, true, true)
            .ResolveAsync(id, body with { Note = " " }, default);
        var closed = await Operator(store, true, true).ResolveAsync(id, body, default);
        var notOpen = await Operator(store, true, true).ResolveAsync(Guid.NewGuid(), body, default);

        Assert.Equal(403, Assert.IsType<ObjectResult>(notFounder).StatusCode);
        Assert.Equal(403, Assert.IsType<ObjectResult>(stale).StatusCode);
        Assert.Equal(400, Assert.IsType<ObjectResult>(noNote).StatusCode);
        Assert.IsType<OkObjectResult>(closed);
        Assert.Equal(409, Assert.IsType<ObjectResult>(notOpen).StatusCode);
    }
}
