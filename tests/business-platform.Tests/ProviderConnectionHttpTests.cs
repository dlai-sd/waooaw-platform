// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R003, WC149-R008, WC149-R009
// constitutional_basis: C-023, C-059, C-063, C-083, C-084

using System.Net;
using System.Security.Claims;
using System.Text;
using System.Text.Json;
using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class MetaGraphClientTests
{
    private readonly List<(HttpMethod Method, Uri Uri, string? Auth, string Body)> _seen = [];
    private Func<HttpRequestMessage, HttpResponseMessage> _respond = _ => new(HttpStatusCode.OK);

    private MetaGraphClient Client() =>
        new(new HttpClient(new StandIn(this)), new MetaConnectionOptions { GraphVersion = "v21.0" });

    private sealed class StandIn(MetaGraphClientTests owner) : HttpMessageHandler
    {
        protected override async Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        )
        {
            owner._seen.Add(
                (
                    request.Method,
                    request.RequestUri!,
                    request.Headers.Authorization?.ToString(),
                    request.Content is null ? "" : await request.Content.ReadAsStringAsync(cancellationToken)
                )
            );
            return owner._respond(request);
        }
    }

    private static HttpResponseMessage Json(HttpStatusCode status, string json) =>
        new(status) { Content = new StringContent(json, Encoding.UTF8, "application/json") };

    [Fact]
    public async Task SecretsAndTokensTravelInTheBodyOrHeaderNeverTheUrl()
    {
        _respond = _ => Json(HttpStatusCode.OK, """{"access_token":"tok-1"}""");
        var client = Client();

        await client.ExchangeCodeAsync("111", "app-secret-x", "https://app.test/cb", "code-x", default);
        await client.ExtendUserTokenAsync("111", "app-secret-x", "user-token-x", default);

        _seen.Should().HaveCount(2);
        _seen.Should().OnlyContain(call => call.Uri.Host == "graph.facebook.com" && call.Uri.Scheme == "https");
        _seen.Select(call => call.Uri.ToString()).Should().OnlyContain(url =>
            !url.Contains("app-secret-x") && !url.Contains("user-token-x") && !url.Contains("code-x")
        );
        _seen[0].Uri.AbsolutePath.Should().Be("/v21.0/oauth/access_token");
        _seen[0].Body.Should().Contain("client_secret=app-secret-x");
    }

    [Fact]
    public async Task ListPagesKeepsOnlyUsablePagesInOrder()
    {
        _respond = _ =>
            Json(
                HttpStatusCode.OK,
                """{"data":[{"id":"abc","name":"Bad id","access_token":"t"},{"id":"42","name":"First","access_token":"page-1"},{"id":"43","name":"Second","access_token":"page-2"}]}"""
            );

        var pages = await Client().ListPagesAsync("user-token", default);

        pages.Select(p => p.Id).Should().Equal("42", "43");
        _seen[0].Auth.Should().Be("Bearer user-token");
        pages[0].ToString().Should().NotContain("page-1");
    }

    [Fact]
    public async Task PublishPostsToThePageFeedWithThePageToken()
    {
        _respond = _ => Json(HttpStatusCode.OK, """{"id":"42_9"}""");

        var id = await Client().PublishAsync("42", "page-token", "hello", default);

        id.Should().Be("42_9");
        _seen[0].Uri.AbsolutePath.Should().Be("/v21.0/42/feed");
        _seen[0].Auth.Should().Be("Bearer page-token");
        _seen[0].Body.Should().Be("message=hello");
    }

    [Fact]
    public async Task APageIdThatCouldRedirectTheRequestIsRefusedBeforeSending()
    {
        var failure = await Assert.ThrowsAsync<MetaGraphException>(() =>
            Client().PublishAsync("42/../../evil", "t", "m", default)
        );

        failure.Failure.Should().Be(MetaGraphFailure.Rejected);
        _seen.Should().BeEmpty();
    }

    [Theory]
    [InlineData(400, """{"error":{"type":"OAuthException","code":190,"message":"Invalid token abc-secret"}}""", MetaGraphFailure.AuthRejected)]
    [InlineData(400, """{"error":{"type":"GraphMethodException","code":190}}""", MetaGraphFailure.AuthRejected)]
    [InlineData(401, "not json", MetaGraphFailure.AuthRejected)]
    [InlineData(400, """{"error":{"type":"Other","code":100,"message":"abc-secret"}}""", MetaGraphFailure.Rejected)]
    [InlineData(500, """{"error":{"message":"abc-secret"}}""", MetaGraphFailure.Unavailable)]
    public async Task GraphErrorsAreClassifiedWithoutCopyingTheirText(
        int status,
        string body,
        MetaGraphFailure expected
    )
    {
        _respond = _ => Json((HttpStatusCode)status, body);

        var failure = await Assert.ThrowsAsync<MetaGraphException>(() =>
            Client().PublishAsync("42", "t", "m", default)
        );

        failure.Failure.Should().Be(expected);
        failure.Message.Should().NotContain("abc-secret");
    }

    [Fact]
    public async Task ANetworkFailureIsUnavailable()
    {
        _respond = _ => throw new HttpRequestException("connect failed for https://graph.facebook.com/?access_token=leak");

        var failure = await Assert.ThrowsAsync<MetaGraphException>(() =>
            Client().PublishAsync("42", "t", "m", default)
        );

        failure.Failure.Should().Be(MetaGraphFailure.Unavailable);
        failure.Message.Should().NotContain("leak");
    }

    [Theory]
    [InlineData("v21.0", "v21.0")]
    [InlineData("v9.1", "v9.1")]
    [InlineData("../evil", "v21.0")]
    [InlineData("", "v21.0")]
    public void OnlyWellFormedGraphVersionsAreAccepted(string configured, string expected)
    {
        var options = MetaConnectionOptions.From(
            new ConfigurationBuilder()
                .AddInMemoryCollection(
                    new Dictionary<string, string?>
                    {
                        ["ProviderConnections:Meta:GraphVersion"] = configured,
                    }
                )
                .Build()
        );

        options.GraphVersion.Should().Be(expected);
    }

    [Theory]
    [InlineData("https://app.waooaw.test/cb", true)]
    [InlineData("http://localhost:3000/cb", true)]
    [InlineData("http://app.waooaw.test/cb", false)]
    [InlineData("https://user:pw@app.waooaw.test/cb", false)]
    [InlineData("not a uri", false)]
    public void RedirectUrisMustBeHttpsOrLoopback(string redirect, bool valid) =>
        new MetaConnectionOptions { RedirectUri = redirect }.RedirectUriValue.Should().Match(
            uri => (uri != null) == valid
        );
}

public sealed class ProviderConnectionsControllerTests
{
    private readonly Mock<IProviderConnectionService> _service = new(MockBehavior.Strict);
    private readonly Guid _tenant = Guid.NewGuid();
    private readonly Guid _actor = Guid.NewGuid();

    private ProviderConnectionsController Controller(
        string? body = null,
        bool withTenant = true,
        bool withActor = true
    )
    {
        var http = new DefaultHttpContext();
        if (withTenant)
            http.Items[TenantIsolationMiddleware.TenantIdItemKey] = _tenant.ToString();
        if (withActor)
            http.User = new ClaimsPrincipal(
                new ClaimsIdentity([new Claim("participant_id", _actor.ToString())], "test")
            );
        if (body is not null)
            http.Request.Body = new MemoryStream(Encoding.UTF8.GetBytes(body));
        return new(_service.Object, NullLogger<ProviderConnectionsController>.Instance)
        {
            ControllerContext = new ControllerContext { HttpContext = http },
        };
    }

    private static string Problem(IActionResult result, out int status)
    {
        var content = Assert.IsType<ContentResult>(result);
        status = content.StatusCode!.Value;
        content.ContentType.Should().Be("application/problem+json");
        return content.Content!;
    }

    [Fact]
    public async Task ListUsesTheMembershipTenantAndIsNotCached()
    {
        _service.Setup(s => s.ListAsync(_tenant, default)).ReturnsAsync([]);
        var controller = Controller();

        Assert.IsType<OkObjectResult>(await controller.ListAsync(default));

        controller.Response.Headers.CacheControl.ToString().Should().Be("no-store");
    }

    [Fact]
    public async Task StartUsesTheTenantAndActorFromTheSession()
    {
        var start = new ProviderConnectionStart("https://www.facebook.com/v21.0/dialog/oauth?x=1", DateTimeOffset.UtcNow);
        _service.Setup(s => s.StartMetaAsync(_tenant, _actor, default)).ReturnsAsync(start);

        var result = Assert.IsType<OkObjectResult>(await Controller().StartAsync(default));

        result.Value.Should().Be(start);
    }

    [Theory]
    [InlineData(false, true)]
    [InlineData(true, false)]
    public async Task ARequestWithoutATenantOrActorIsForbiddenBeforeTheService(bool tenant, bool actor)
    {
        var body = Problem(await Controller(withTenant: tenant, withActor: actor).StartAsync(default), out var status);

        status.Should().Be(403);
        body.Should().Contain("CONNECTION_FORBIDDEN");
        _service.VerifyNoOtherCalls();
    }

    [Fact]
    public async Task CallbackPassesTheCodeAndStateAndNeverEchoesThem()
    {
        var summary = new ProviderConnectionSummary(Guid.NewGuid(), "meta", "CONNECTED", "Page", "42", [], null, DateTimeOffset.UtcNow);
        _service
            .Setup(s => s.CompleteMetaAsync(_tenant, _actor, It.Is<ProviderConnectionCallbackRequest>(r => r.Code == "the-code" && r.State == "the-state"), default))
            .ReturnsAsync(summary);

        var result = Assert.IsType<OkObjectResult>(
            await Controller("""{"code":"the-code","state":"the-state"}""").CallbackAsync(default)
        );

        JsonSerializer.Serialize(result.Value).Should().NotContain("the-code").And.NotContain("the-state");
    }

    [Theory]
    [InlineData("""{"code":"c","state":"s","extra":1}""")]
    [InlineData("not json with secret-fragment")]
    [InlineData("null")]
    public async Task MalformedOrUnknownBodiesAre400WithoutQuotingTheBody(string body)
    {
        var problem = Problem(await Controller(body).CallbackAsync(default), out var status);

        status.Should().Be(400);
        problem.Should().Contain("CONNECTION_INVALID").And.NotContain("secret-fragment");
        _service.VerifyNoOtherCalls();
    }

    [Fact]
    public async Task AnOversizedBodyIsRefused()
    {
        var problem = Problem(
            await Controller("{\"code\":\"" + new string('a', 20_000) + "\"}").CallbackAsync(default),
            out var status
        );

        status.Should().Be(400);
        problem.Should().Contain("CONNECTION_INVALID");
    }

    [Fact]
    public async Task ServiceFailuresBecomeProblemJsonWithTheirStatusAndCode()
    {
        var id = Guid.NewGuid();
        _service
            .Setup(s => s.PublishAsync(_tenant, _actor, id, It.IsAny<ProviderConnectionPublishRequest>(), default))
            .ThrowsAsync(new ProviderConnectionException(409, "CONNECTION_NEEDS_REPAIR", "Reconnect this account."));

        var problem = Problem(
            await Controller("""{"message":"hi","approved":true}""").PublishAsync(id, default),
            out var status
        );

        status.Should().Be(409);
        using var document = JsonDocument.Parse(problem);
        document.RootElement.GetProperty("code").GetString().Should().Be("CONNECTION_NEEDS_REPAIR");
    }

    [Fact]
    public async Task RevokeReturns204()
    {
        var id = Guid.NewGuid();
        _service.Setup(s => s.RevokeAsync(_tenant, _actor, id, default)).Returns(Task.CompletedTask);

        Assert.IsType<NoContentResult>(await Controller().RevokeAsync(id, default));
    }
}

public sealed class ProviderCredentialResolverTests
{
    private static async Task<(ProviderRegistryDatabase Db, ProviderCredentialResolver Resolver)> CreateAsync()
    {
        var db = await ProviderRegistryDatabase.CreateAsync();
        return (db, new ProviderCredentialResolver(db.Factory()));
    }

    private static string Activate(string provider, string secret, string version) =>
        $"""
            WITH p AS (SELECT id FROM business.provider_configs WHERE provider_name = '{provider}' AND tenant_id IS NULL),
            v AS (
                INSERT INTO business.provider_credential_versions
                    (provider_config_id, version_no, vault_secret_name, vault_secret_version, status, test_outcome, created_by_subject)
                SELECT id, 1, '{secret}', '{version}', 'ACTIVE', 'PASSED', 'founder-1' FROM p RETURNING id, provider_config_id)
            UPDATE business.provider_configs c SET active_credential_version_id = v.id FROM v WHERE c.id = v.provider_config_id
            """;

    [Fact]
    public async Task OnlyAnActiveCredentialResolvesToItsKeyVaultReference()
    {
        var (db, resolver) = await CreateAsync();
        await using var _ = db;

        (await resolver.ResolveAsync("openai", default)).Should().BeNull();
        await db.ExecuteAsync(Activate("openai", "provider-openai", "a1b2c3d4e5f60718293a4b5c6d7e8f90"));
        (await resolver.ResolveAsync("openai", default))
            .Should()
            .Be(new ResolvedProviderCredential("openai", "provider-openai", "a1b2c3d4e5f60718293a4b5c6d7e8f90", "bearer"));
        (await resolver.ResolveAsync("not-a-provider", default)).Should().BeNull();
        (await resolver.ResolveAsync("Bad Name", default)).Should().BeNull();
    }

    [Fact]
    public async Task ADisabledProviderDoesNotResolveAndTheMetaAppRowDoes()
    {
        var (db, resolver) = await CreateAsync();
        await using var _ = db;
        await db.ExecuteAsync(Activate("openai", "provider-openai", "a1b2c3d4e5f60718293a4b5c6d7e8f90"));
        await db.ExecuteAsync(Activate("meta", "provider-meta", "b1b2c3d4e5f60718293a4b5c6d7e8f90"));

        (await resolver.ResolveAsync("meta", default))!.SecretName.Should().Be("provider-meta");
        await db.ExecuteAsync("UPDATE business.provider_configs SET active = false WHERE provider_name = 'openai'");

        (await resolver.ResolveAsync("openai", default)).Should().BeNull();
    }
}
