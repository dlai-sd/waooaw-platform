// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R010, R034
// Constitutional basis: C-023, C-059, C-063, C-083, C-084

using System.Reflection;
using Moq;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.AgentOperation;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.AgentOperation;

public sealed class CustomerConnectionInterfaceTests
{
    private static ProviderConnectionSummary Summary(string status, params string[] scopes) =>
        new(Guid.NewGuid(), ProviderConnectionService.MetaProvider, status, "Test page", "page-1", scopes, null, DateTimeOffset.UnixEpoch);

    [Fact]
    public async Task ACustodyConnectionIsListedAsFactsAndInstagramNeedsItsOwnPublishScope()
    {
        var custody = new Mock<IProviderConnectionService>();
        custody
            .SetupSequence(service => service.ListAsync(It.IsAny<Guid>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new List<ProviderConnectionSummary> { Summary("CONNECTED", "pages_manage_posts") })
            .ReturnsAsync(new List<ProviderConnectionSummary> { Summary("CONNECTED", "pages_manage_posts", ProviderCustodyConnectionInterface.InstagramPublishScope), Summary("REVOKED") });
        var connections = new ProviderCustodyConnectionInterface(custody.Object);

        var facebookOnly = await connections.ListAsync(Guid.NewGuid(), CancellationToken.None);
        var both = await connections.ListAsync(Guid.NewGuid(), CancellationToken.None);

        Assert.Equal(new[] { "META_FACEBOOK" }, facebookOnly.Select(fact => fact.Connector));
        Assert.Equal(new[] { "META_FACEBOOK", "META_INSTAGRAM" }, both.Select(fact => fact.Connector));
    }

    [Theory]
    [InlineData("CONNECTION_NEEDS_REPAIR")]
    [InlineData("CONNECTION_REVOKED")]
    public async Task AnExpiredOrWithdrawnConnectionSurfacesAsNeedsRepairWithoutAnyDetail(string code)
    {
        var custody = new Mock<IProviderConnectionService>();
        custody
            .Setup(service => service.PublishAsync(It.IsAny<Guid>(), It.IsAny<Guid>(), It.IsAny<Guid>(), It.IsAny<ProviderConnectionPublishRequest>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new ProviderConnectionException(409, code, "secret detail that must not travel"));
        var connections = new ProviderCustodyConnectionInterface(custody.Object);

        var failure = await Assert.ThrowsAsync<ConnectionNeedsRepairException>(() =>
            connections.PublishAsync(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), "Hello", "note", CancellationToken.None));

        Assert.DoesNotContain("secret", failure.Message);
    }

    [Fact]
    public async Task ThePublishRequestAlwaysCarriesTheApprovalAndNothingElse()
    {
        ProviderConnectionPublishRequest? seen = null;
        var custody = new Mock<IProviderConnectionService>();
        custody
            .Setup(service => service.PublishAsync(It.IsAny<Guid>(), It.IsAny<Guid>(), It.IsAny<Guid>(), It.IsAny<ProviderConnectionPublishRequest>(), It.IsAny<CancellationToken>()))
            .Callback<Guid, Guid, Guid, ProviderConnectionPublishRequest, CancellationToken>((_, _, _, request, _) => seen = request)
            .ReturnsAsync(new ProviderConnectionPublishResult("post-1", DateTimeOffset.UnixEpoch));
        var connections = new ProviderCustodyConnectionInterface(custody.Object);

        var post = await connections.PublishAsync(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), "Hello", "Approved version 2", CancellationToken.None);

        Assert.Equal("post-1", post.ProviderPostId);
        Assert.Equal(new ProviderConnectionPublishRequest("Hello", true, "Approved version 2"), seen);
    }

    [Fact]
    public void TheInterfaceAgentsAskThroughOffersOnlyFactsAndResultsNeverAKey()
    {
        var methods = typeof(ICustomerConnectionInterface).GetMethods().Select(method => method.Name).OrderBy(name => name);
        Assert.Equal(new[] { "ListAsync", "PublishAsync" }, methods);

        var secretWords = new[] { "token", "secret", "key", "password", "credential", "vault" };
        foreach (var type in new[] { typeof(ConnectionFacts), typeof(ConnectedPost) })
            foreach (var property in type.GetProperties(BindingFlags.Public | BindingFlags.Instance))
                Assert.DoesNotContain(secretWords, word => property.Name.Contains(word, StringComparison.OrdinalIgnoreCase));
        foreach (var method in typeof(ICustomerConnectionInterface).GetMethods())
            foreach (var parameter in method.GetParameters())
                Assert.DoesNotContain(secretWords, word => parameter.Name!.Contains(word, StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public async Task ASwappedCustodyLeavesTheInterfaceAndTheAgentFacingCallsUnchanged()
    {
        var fake = new FakeConnections();
        fake.Facts.Add(new ConnectionFacts(Guid.NewGuid(), "META_FACEBOOK", "CONNECTED", "page-9", "Other custody"));
        ICustomerConnectionInterface swapped = fake;

        var facts = await swapped.ListAsync(Guid.NewGuid(), CancellationToken.None);
        var post = await swapped.PublishAsync(Guid.NewGuid(), Guid.NewGuid(), facts[0].ConnectionId, "Hello", "note", CancellationToken.None);

        Assert.Equal("META_FACEBOOK", facts[0].Connector);
        Assert.Equal("post-1", post.ProviderPostId);
        Assert.Equal(typeof(ICustomerConnectionInterface), typeof(ProviderCustodyConnectionInterface).GetInterface(nameof(ICustomerConnectionInterface)));
        Assert.Equal(typeof(ICustomerConnectionInterface), typeof(FakeConnections).GetInterface(nameof(ICustomerConnectionInterface)));
    }
}
