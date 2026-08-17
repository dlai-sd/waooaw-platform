// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// constitutional_basis: C-005, C-023, C-049, C-059, C-076
using System.Net;
using System.Security.Claims;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Workflows;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class InfrastructureWorkflowCoverageTests
{
    [Theory]
    [InlineData("/health")]
    [InlineData("/health/ready")]
    [InlineData("/api/v1/payments/webhooks/razorpay")]
    [InlineData("/api/v1/whatsapp/webhook")]
    [InlineData("/api/v1/identity/registrations/start")]
    public async Task TenantMiddleware_BypassPaths_InvokeNext(string path)
    {
        var called = false;
        var middleware = new TenantIsolationMiddleware(
            _ =>
            {
                called = true;
                return Task.CompletedTask;
            },
            NullLogger<TenantIsolationMiddleware>.Instance);
        var context = new DefaultHttpContext();
        context.Request.Path = path;

        await middleware.InvokeAsync(context);

        Assert.True(called);
    }

    [Fact]
    public async Task TenantMiddleware_UnauthenticatedRequest_Returns401()
    {
        var middleware = MiddlewareThatMustNotContinue();
        var context = Context("/api/v1/providers");

        await middleware.InvokeAsync(context);

        Assert.Equal(401, context.Response.StatusCode);
    }

    [Fact]
    public async Task TenantMiddleware_AuthenticatedWithoutTenant_Returns403()
    {
        var middleware = MiddlewareThatMustNotContinue();
        var context = Context("/api/v1/providers", new Claim("sub", "customer"));

        await middleware.InvokeAsync(context);

        Assert.Equal(403, context.Response.StatusCode);
    }

    [Fact]
    public async Task TenantMiddleware_InvalidTenant_Returns403()
    {
        var middleware = MiddlewareThatMustNotContinue();
        var context = Context("/api/v1/providers", new Claim("tenant_id", "not-a-uuid"));

        await middleware.InvokeAsync(context);

        Assert.Equal(403, context.Response.StatusCode);
    }

    [Fact]
    public async Task TenantMiddleware_ValidTenantStoresCanonicalIdAndContinues()
    {
        var called = false;
        var middleware = new TenantIsolationMiddleware(
            _ =>
            {
                called = true;
                return Task.CompletedTask;
            },
            NullLogger<TenantIsolationMiddleware>.Instance);
        var tenantId = Guid.NewGuid();
        var context = Context("/api/v1/providers", new Claim("tenant_id", tenantId.ToString("B")));

        await middleware.InvokeAsync(context);

        Assert.True(called);
        Assert.Equal(tenantId.ToString("D"), context.Items[TenantIsolationMiddleware.TenantIdItemKey]);
    }

    [Fact]
    public async Task RenewalActivities_SendCanonicalProgressiveFailureRequests()
    {
        var handler = new RecordingHandler();
        var activities = new RenewalFailureActivities(new NamedClientFactory(handler));

        await activities.SendPaymentFailureAlertAsync("customer", "contract");
        await activities.SetDegradedModeAsync("customer", "contract", "DMA");
        await activities.PauseCampaignsAsync("customer", "DMA");
        await activities.SuspendContractAsync("customer", "contract");
        await activities.TerminateContractAsync("customer", "contract");

        Assert.Equal(6, handler.Requests.Count);
        Assert.Equal(2, handler.Requests.Count(value => value.Path == "/meter/alert"));
        Assert.Contains(handler.Requests, value => value.Path == "/api/v1/sessions/customer/mode" && value.Body.Contains("DEGRADED"));
        Assert.Contains(handler.Requests, value => value.Path == "/api/v1/campaigns/pause" && value.Body.Contains("RENEWAL_FAILURE_DAY7"));
        Assert.Contains(handler.Requests, value => value.Path == "/api/v1/contracts/contract/suspend");
        Assert.Contains(handler.Requests, value => value.Path == "/api/v1/contracts/contract/terminate");
    }

    [Fact]
    public async Task UnconfiguredWorkspaceOwners_ReturnUnavailableProjections()
    {
        var gateway = new UnconfiguredRelationshipWorkspaceOwnerGateway();
        var context = new RelationshipOwnerContext(
            "actor", "EMPLOYER", Guid.NewGuid(), Guid.NewGuid(), 1, Guid.NewGuid().ToString());

        Assert.Null(await gateway.GetExecutionAsync(context, CancellationToken.None));
        Assert.Null(await gateway.GetCommercialAsync(context, CancellationToken.None));
    }

    [Fact]
    public async Task EmploymentService_MissingCeConfigurationFailsClosed()
    {
        var service = new EmploymentService(
            new ConfigurationBuilder().Build(),
            NullLogger<EmploymentService>.Instance);

        await Assert.ThrowsAsync<InvalidOperationException>(() => service.RegisterCustomerAsync(
            new RegisterCustomerRequest("Name\nQuoted", "customer\\\"@example.com", Guid.NewGuid().ToString()),
            CancellationToken.None));
        await Assert.ThrowsAsync<InvalidOperationException>(() => service.HireAgentAsync(
            new HireAgentRequest("contract", "DMA", "skill", "1", 100, "1"),
            CancellationToken.None));
    }

    private static TenantIsolationMiddleware MiddlewareThatMustNotContinue() => new(
        _ => throw new InvalidOperationException("Request must not continue."),
        NullLogger<TenantIsolationMiddleware>.Instance);

    private static DefaultHttpContext Context(string path, params Claim[] claims)
    {
        var context = new DefaultHttpContext();
        context.Request.Path = path;
        if (claims.Length > 0)
        {
            context.User = new ClaimsPrincipal(new ClaimsIdentity(claims, "Test"));
        }
        context.Response.Body = new MemoryStream();
        return context;
    }

    private sealed class NamedClientFactory(RecordingHandler handler) : IHttpClientFactory
    {
        public HttpClient CreateClient(string name) => new(handler, disposeHandler: false)
        {
            BaseAddress = new Uri(name == "WBE" ? "https://wbe.test" : "https://paas.test"),
        };
    }

    private sealed class RecordingHandler : HttpMessageHandler
    {
        public List<(string Path, string Body)> Requests { get; } = [];

        protected override async Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            Requests.Add((
                request.RequestUri!.AbsolutePath,
                request.Content is null ? string.Empty : await request.Content.ReadAsStringAsync(cancellationToken)));
            return new HttpResponseMessage(HttpStatusCode.OK);
        }
    }
}
