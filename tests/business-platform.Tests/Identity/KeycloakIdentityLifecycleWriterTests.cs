using System.Net;
using System.Reflection;
using System.Text;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class KeycloakIdentityLifecycleWriterTests
{
    [Fact]
    public async Task LifecycleService_RejectsInvalidAuthorityBeforePersistence()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var options = Options.Create(
            new IdentityHmacOptions
            {
                Key = new string('k', IdentityHmacOptions.MinKeyLength),
                ActiveVersion = "v1",
            }
        );
        var service = new IdentityLifecycleService(factory, options);
        var actor = Actor("issuer", "subject");

        Assert.Throws<InvalidOperationException>(() =>
            new IdentityLifecycleService(factory, Options.Create(new IdentityHmacOptions()))
        );
        Assert.Throws<InvalidOperationException>(() =>
            new IdentityLifecycleService(
                factory,
                Options.Create(new IdentityHmacOptions { ActiveVersion = "v1", Key = "" })
            )
        );
        Assert.Throws<InvalidOperationException>(() =>
            new IdentityLifecycleService(
                factory,
                Options.Create(
                    new IdentityHmacOptions
                    {
                        ActiveVersion = "v1",
                        Key = new string('k', IdentityHmacOptions.MinKeyLength - 1),
                    }
                )
            )
        );
        await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            service.BeginLinkAsync(
                actor,
                IdentityLifecycleProvider.Google,
                Guid.Empty,
                Guid.NewGuid(),
                Guid.NewGuid()
            )
        );
        await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            service.BeginUnlinkAsync(actor, Guid.Empty, Guid.NewGuid(), Guid.NewGuid())
        );
        await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            service.BeginLinkAsync(
                null!,
                IdentityLifecycleProvider.Google,
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid()
            )
        );
        await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            service.BeginLinkAsync(
                Actor("", "subject"),
                IdentityLifecycleProvider.Google,
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid()
            )
        );
        await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            service.BeginLinkAsync(
                Actor("issuer", ""),
                IdentityLifecycleProvider.Google,
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid()
            )
        );
        await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            service.BeginLinkAsync(
                actor,
                IdentityLifecycleProvider.Google,
                Guid.NewGuid(),
                Guid.Empty,
                Guid.NewGuid()
            )
        );
        await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            service.BeginLinkAsync(
                actor,
                IdentityLifecycleProvider.Google,
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.Empty
            )
        );
        await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            service.CompleteLinkAsync(
                actor,
                Guid.NewGuid(),
                "user",
                new KeycloakFederatedBinding("google", "id", "user")
            )
        );
        await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            service.CompleteUnlinkAsync(actor, Guid.NewGuid(), "user")
        );
    }

    [Fact]
    public async Task Writer_UsesOnlyAcceptedStockKeycloakRoutesAndSemantics()
    {
        var handler = new LifecycleHandler();
        using var client = new HttpClient(handler);
        var writer = new KeycloakIdentityLifecycleWriter(client, Options.Create(Configuration()));

        Assert.True(await writer.UserExistsAsync("customer-123", default));
        var bindings = await writer.ReadBindingsAsync("customer-123", default);
        Assert.Single(bindings);
        Assert.Equal("google", bindings[0].ProviderAlias);
        await writer.AddBindingAsync(
            "customer-123",
            new KeycloakFederatedBinding("apple", "opaque-provider-id", "opaque-user"),
            default
        );
        await writer.RemoveBindingAsync("customer-123", "apple", default);

        Assert.Equal(
            new[]
            {
                "POST /realms/waooaw/protocol/openid-connect/token",
                "GET /admin/realms/waooaw/users/customer-123",
                "POST /realms/waooaw/protocol/openid-connect/token",
                "GET /admin/realms/waooaw/users/customer-123/federated-identity",
                "POST /realms/waooaw/protocol/openid-connect/token",
                "POST /admin/realms/waooaw/users/customer-123/federated-identity/apple",
                "POST /realms/waooaw/protocol/openid-connect/token",
                "DELETE /admin/realms/waooaw/users/customer-123/federated-identity/apple",
            },
            handler.Requests
        );
        Assert.Contains("\"identityProvider\":\"apple\"", handler.AddBody);
        Assert.DoesNotContain("client-secret", handler.AddBody);
    }

    [Fact]
    public async Task Writer_AmbiguousMutationFailsAsUnknownOutcome()
    {
        using var client = new HttpClient(new UnknownOutcomeHandler());
        var writer = new KeycloakIdentityLifecycleWriter(client, Options.Create(Configuration()));
        await Assert.ThrowsAsync<KeycloakLifecycleUnknownOutcomeException>(() =>
            writer.AddBindingAsync(
                "customer-123",
                new KeycloakFederatedBinding("google", "opaque-provider-id", "opaque-user"),
                default
            )
        );
    }

    [Fact]
    public void Configuration_RejectsBroadenedWriterIdentityOrPublicHost()
    {
        var options = Configuration();
        options.ClientId = "waooaw-bp-identity-reader";
        Assert.False(options.IsConfigured);
        options = Configuration();
        options.AllowedPrivateHosts = ["other.invalid"];
        Assert.False(options.IsConfigured);
        options = Configuration();
        options.PrivateOrigin = "http://keycloak.private.invalid/";
        Assert.False(options.IsConfigured);
        options = Configuration();
        options.Enabled = false;
        Assert.False(options.IsConfigured);
        options = Configuration();
        options.PrivateOrigin = "not-a-uri";
        Assert.False(options.IsConfigured);
        options = Configuration();
        options.PrivateOrigin = "https://keycloak.private.invalid/admin";
        Assert.False(options.IsConfigured);
        options = Configuration();
        options.PrivateOrigin = "https://user@keycloak.private.invalid/";
        Assert.False(options.IsConfigured);
        options = Configuration();
        options.PrivateOrigin = "https://keycloak.private.invalid/?query=true";
        Assert.False(options.IsConfigured);
        options = Configuration();
        options.PrivateOrigin = "https://keycloak.private.invalid/#fragment";
        Assert.False(options.IsConfigured);
        options = Configuration();
        options.ClientSecret = " ";
        Assert.False(options.IsConfigured);
    }

    [Fact]
    public async Task Writer_RejectsInvalidInputsAndClosedRouteResponses()
    {
        var notFound = Writer(
            (request, _) =>
                request.RequestUri!.AbsolutePath.EndsWith("/token", StringComparison.Ordinal)
                    ? Json(HttpStatusCode.OK, """{"access_token":"token","expires_in":60}""")
                    : new HttpResponseMessage(HttpStatusCode.NotFound)
        );
        Assert.False(await notFound.UserExistsAsync("customer", default));

        var rejected = Writer(
            (request, _) =>
                request.RequestUri!.AbsolutePath.EndsWith("/token", StringComparison.Ordinal)
                    ? Json(HttpStatusCode.OK, """{"access_token":"token","expires_in":60}""")
                    : new HttpResponseMessage(HttpStatusCode.BadRequest)
        );
        await Assert.ThrowsAsync<KeycloakLifecycleRejectedException>(() =>
            rejected.UserExistsAsync("customer", default)
        );
        await Assert.ThrowsAsync<KeycloakLifecycleRejectedException>(() =>
            rejected.ReadBindingsAsync("customer", default)
        );
        await Assert.ThrowsAsync<KeycloakLifecycleRejectedException>(() =>
            rejected.AddBindingAsync(
                "customer",
                new KeycloakFederatedBinding("google", "provider-id", "provider-user"),
                default
            )
        );

        foreach (var userId in new[] { "", ".", "..", "invalid/id" })
            await Assert.ThrowsAsync<ArgumentException>(() =>
                rejected.UserExistsAsync(userId, default)
            );
        foreach (
            var binding in new[]
            {
                new KeycloakFederatedBinding("unsupported", "provider-id", "provider-user"),
                new KeycloakFederatedBinding("google", "invalid/id", "provider-user"),
                new KeycloakFederatedBinding("google", "provider-id", "invalid/user"),
            }
        )
            await Assert.ThrowsAsync<ArgumentException>(() =>
                rejected.AddBindingAsync("customer", binding, default)
            );
        await Assert.ThrowsAsync<ArgumentException>(() =>
            rejected.RemoveBindingAsync("customer", "unsupported", default)
        );
    }

    [Theory]
    [InlineData("""{}""")]
    [InlineData("""{"access_token":"","expires_in":60}""")]
    [InlineData("""{"access_token":"token"}""")]
    [InlineData("""{"access_token":"token","expires_in":"60"}""")]
    [InlineData("""{"access_token":"token","expires_in":0}""")]
    [InlineData("""{"access_token":"token","expires_in":61}""")]
    public async Task Writer_RejectsInvalidAccessTokenResponses(string payload)
    {
        var writer = Writer((_, _) => Json(HttpStatusCode.OK, payload));
        await Assert.ThrowsAsync<KeycloakLifecycleRejectedException>(() =>
            writer.UserExistsAsync("customer", default)
        );
    }

    [Theory]
    [InlineData("""{}""")]
    [InlineData("""{"identityProvider":"google"}""")]
    [InlineData("""{"identityProvider":"google","userId":"id"}""")]
    public async Task Writer_RejectsMalformedBindingPayloads(string item)
    {
        var writer = Writer(
            (request, _) =>
                request.RequestUri!.AbsolutePath.EndsWith("/token", StringComparison.Ordinal)
                    ? Json(HttpStatusCode.OK, """{"access_token":"token","expires_in":60}""")
                    : Json(HttpStatusCode.OK, $"[{item}]")
        );
        await Assert.ThrowsAsync<KeycloakLifecycleRejectedException>(() =>
            writer.ReadBindingsAsync("customer", default)
        );
    }

    [Fact]
    public async Task Writer_HandlesTimeoutCancellationAndRemainingClosedResponses()
    {
        var timeout = Writer(
            (request, _) =>
            {
                if (request.RequestUri!.AbsolutePath.EndsWith("/token", StringComparison.Ordinal))
                    return Json(HttpStatusCode.OK, """{"access_token":"token","expires_in":60}""");
                throw new OperationCanceledException();
            }
        );
        await Assert.ThrowsAsync<KeycloakLifecycleUnknownOutcomeException>(() =>
            timeout.AddBindingAsync(
                "customer",
                new KeycloakFederatedBinding("facebook", "provider-id", "provider-user"),
                default
            )
        );

        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            timeout.AddBindingAsync(
                "customer",
                new KeycloakFederatedBinding("apple", "provider-id", "provider-user"),
                cancellation.Token
            )
        );

        var tokenRejected = Writer((_, _) => new HttpResponseMessage(HttpStatusCode.Unauthorized));
        await Assert.ThrowsAsync<KeycloakLifecycleRejectedException>(() =>
            tokenRejected.UserExistsAsync("customer", default)
        );

        var nonArray = Writer(
            (request, _) =>
                request.RequestUri!.AbsolutePath.EndsWith("/token", StringComparison.Ordinal)
                    ? Json(HttpStatusCode.OK, """{"access_token":"token","expires_in":60}""")
                    : Json(HttpStatusCode.OK, """{"identityProvider":"google"}""")
        );
        await Assert.ThrowsAsync<KeycloakLifecycleRejectedException>(() =>
            nonArray.ReadBindingsAsync("customer", default)
        );

        var providers = Writer(
            (request, _) =>
                request.RequestUri!.AbsolutePath.EndsWith("/token", StringComparison.Ordinal)
                    ? Json(HttpStatusCode.OK, """{"access_token":"token","expires_in":60}""")
                    : Json(
                        HttpStatusCode.OK,
                        """[{"identityProvider":"facebook","userId":"facebook-id","userName":"facebook-user"},{"identityProvider":"apple","userId":"apple-id","userName":"apple-user"}]"""
                    )
        );
        Assert.Equal(2, (await providers.ReadBindingsAsync("customer", default)).Count);

        var deleteRejected = Writer(
            (request, _) =>
                request.RequestUri!.AbsolutePath.EndsWith("/token", StringComparison.Ordinal)
                    ? Json(HttpStatusCode.OK, """{"access_token":"token","expires_in":60}""")
                    : new HttpResponseMessage(HttpStatusCode.OK)
        );
        await Assert.ThrowsAsync<KeycloakLifecycleRejectedException>(() =>
            deleteRejected.RemoveBindingAsync("customer", "google", default)
        );
    }

    private static KeycloakIdentityLifecycleWriter Writer(
        Func<HttpRequestMessage, CancellationToken, HttpResponseMessage> response
    ) => new(new HttpClient(new DelegateHandler(response)), Options.Create(Configuration()));

    private static IdentityLifecycleWriterOptions Configuration() =>
        new()
        {
            Enabled = true,
            PrivateOrigin = "https://keycloak.private.invalid/",
            AllowedPrivateHosts = ["keycloak.private.invalid"],
            ClientId = "waooaw-bp-identity-lifecycle-writer",
            ClientSecret = "client-secret",
        };

    private static VerifiedCustomerActor Actor(string issuer, string subject) =>
        (VerifiedCustomerActor)
            Activator.CreateInstance(
                typeof(VerifiedCustomerActor),
                BindingFlags.Instance | BindingFlags.NonPublic,
                null,
                [issuer, subject],
                null
            )!;

    private sealed class LifecycleHandler : HttpMessageHandler
    {
        public List<string> Requests { get; } = [];
        public string AddBody { get; private set; } = "";

        protected override async Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        )
        {
            Requests.Add($"{request.Method} {request.RequestUri!.AbsolutePath}");
            if (request.RequestUri.AbsolutePath.EndsWith("/token", StringComparison.Ordinal))
                return Json(
                    HttpStatusCode.OK,
                    """{"access_token":"short-lived","expires_in":60}"""
                );
            if (
                request.Method == HttpMethod.Get
                && request.RequestUri.AbsolutePath.EndsWith(
                    "/federated-identity",
                    StringComparison.Ordinal
                )
            )
                return Json(
                    HttpStatusCode.OK,
                    """[{"identityProvider":"google","userId":"opaque","userName":"opaque-user"},{"identityProvider":"unsupported","userId":"ignored","userName":"ignored"}]"""
                );
            if (request.Method == HttpMethod.Get)
                return Json(HttpStatusCode.OK, """{"id":"customer-123"}""");
            if (request.Method == HttpMethod.Post)
            {
                AddBody = await request.Content!.ReadAsStringAsync(cancellationToken);
                return new HttpResponseMessage(HttpStatusCode.OK);
            }
            return new HttpResponseMessage(HttpStatusCode.NoContent);
        }
    }

    private sealed class UnknownOutcomeHandler : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        )
        {
            if (request.RequestUri!.AbsolutePath.EndsWith("/token", StringComparison.Ordinal))
                return Task.FromResult(
                    Json(HttpStatusCode.OK, """{"access_token":"short-lived","expires_in":60}""")
                );
            throw new HttpRequestException("synthetic disconnect");
        }
    }

    private sealed class DelegateHandler(
        Func<HttpRequestMessage, CancellationToken, HttpResponseMessage> response
    ) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) => Task.FromResult(response(request, cancellationToken));
    }

    private static HttpResponseMessage Json(HttpStatusCode status, string body) =>
        new(status) { Content = new StringContent(body, Encoding.UTF8, "application/json") };
}
