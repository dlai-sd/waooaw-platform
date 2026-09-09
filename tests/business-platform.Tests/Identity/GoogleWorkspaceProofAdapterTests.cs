// Implements: adr/ADR-008-keycloak-identity-broker.md Amendment 3
// constitutional_basis: C-023, C-026, C-059

using System.Net;
using System.Security.Claims;
using Microsoft.Extensions.Options;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Abstractions;
using Microsoft.AspNetCore.Mvc.Filters;
using Microsoft.AspNetCore.Routing;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class GoogleWorkspaceProofAdapterTests
{
    internal static IdentityBrokerReadOptions Configuration() => new()
    {
        Enabled = true, ActorIssuer = "https://synthetic.invalid/realms/waooaw",
        PrivateOrigin = "https://keycloak.private.invalid", AllowedPrivateHosts = ["keycloak.private.invalid"],
        ClientId = "waooaw-bp-identity-reader", ClientSecret = "synthetic-reader-secret",
        ProviderNamespace = "urn:waooaw:identity:synthetic:google:customer-login:v1", TrustConfigDigest = new string('a', 64),
    };

    internal static ClaimsPrincipal Principal(string subject = "synthetic-actor", string? issuer = null)
    {
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        return new ClaimsPrincipal(new ClaimsIdentity(new[]
        {
            new Claim("iss", issuer ?? Configuration().ActorIssuer), new Claim("sub", subject),
            new Claim("aud", "waooaw-platform"), new Claim("azp", "waooaw-web"),
            new Claim("idp", "google"), new Claim("email_verified", "true"),
            new Claim("realm_access", "{\"roles\":[\"customer\"]}"),
            new Claim("iat", now.ToString()), new Claim("exp", (now + 600).ToString()),
            new Claim("auth_time", now.ToString()),
        }, "synthetic-validated-test-principal"));
    }

    [Fact]
    public async Task Read_ExactStockRequests_PreservesOpaqueProviderSubject()
    {
        var handler = new SyntheticKeycloakHandler();
        var adapter = new GoogleWorkspaceProofAdapter(new HttpClient(handler), Options.Create(Configuration()));
        var proof = await adapter.ReadAsync(Principal(), default);
        Assert.Equal("Google-Opaque-synthetic-actor", proof.ProviderSubject);
        Assert.Equal(Configuration().ProviderNamespace, proof.ProviderIssuer);
        Assert.Equal(new[] { "POST /realms/waooaw/protocol/openid-connect/token",
            "GET /admin/realms/waooaw/users/synthetic-actor",
            "GET /admin/realms/waooaw/users/synthetic-actor/federated-identity" }, handler.Requests);
    }

    [Fact]
    public async Task Read_PinnedStockKeycloakOverPrivateHttps_PreservesOpaqueProviderSubject()
    {
        if (Environment.GetEnvironmentVariable("WC085_STOCK_READER") != "true") return;

        var origin = Environment.GetEnvironmentVariable("WC085_READER_ORIGIN")!;
        var actorSubject = Environment.GetEnvironmentVariable("WC085_READER_ACTOR")!;
        var configuration = new IdentityBrokerReadOptions
        {
            Enabled = true,
            ActorIssuer = origin + "/realms/waooaw",
            PrivateOrigin = origin,
            AllowedPrivateHosts = [new Uri(origin).Host],
            ClientId = "waooaw-bp-identity-reader",
            ClientSecret = Environment.GetEnvironmentVariable("WC085_READER_SECRET")!,
            ProviderNamespace = "urn:waooaw:identity:demo:google:customer-login:v1",
            TrustConfigDigest = new string('b', 64),
        };
        var adapter = new GoogleWorkspaceProofAdapter(new HttpClient(), Options.Create(configuration));

        var proof = await adapter.ReadAsync(Principal(actorSubject, configuration.ActorIssuer), default);

        Assert.Equal(actorSubject, proof.Actor.Subject);
        Assert.Equal("Google-Opaque-" + actorSubject, proof.ProviderSubject);
        Assert.Equal(configuration.ProviderNamespace, proof.ProviderIssuer);
    }

    [Theory]
    [InlineData("iss", "https://wrong.invalid/realms/waooaw")]
    [InlineData("azp", "waooaw-mobile")]
    [InlineData("aud", "other")]
    [InlineData("idp", "password")]
    [InlineData("email_verified", "false")]
    [InlineData("auth_time", "1")]
    [InlineData("realm_access", "{\"roles\":[\"customer\",\"waooaw-operator\"]}")]
    [InlineData("sub", "..")]
    public async Task Read_InvalidPrincipal_DeniesBeforeNetwork(string claimType, string value)
    {
        var principal = Principal();
        var identity = (ClaimsIdentity)principal.Identity!;
        identity.RemoveClaim(identity.FindFirst(claimType));
        identity.AddClaim(new Claim(claimType, value));
        var handler = new SyntheticKeycloakHandler();
        var adapter = new GoogleWorkspaceProofAdapter(new HttpClient(handler), Options.Create(Configuration()));
        await Assert.ThrowsAnyAsync<Exception>(() => adapter.ReadAsync(principal, default));
        Assert.Empty(handler.Requests);
    }

    [Theory]
    [InlineData(302)]
    [InlineData(401)]
    [InlineData(403)]
    [InlineData(500)]
    public async Task Read_DependencyFailure_IsUnavailableWithoutEscalation(int status)
    {
        var handler = new SyntheticKeycloakHandler { Status = (HttpStatusCode)status };
        var adapter = new GoogleWorkspaceProofAdapter(new HttpClient(handler), Options.Create(Configuration()));
        var failure = await Assert.ThrowsAsync<CustomerWorkspaceException>(() => adapter.ReadAsync(Principal(), default));
        Assert.Equal(503, failure.StatusCode);
        Assert.Single(handler.Requests);
    }

    [Fact]
    public void AbsentConfiguration_IsUnavailable()
    {
        var adapter = new GoogleWorkspaceProofAdapter(new HttpClient(new SyntheticKeycloakHandler()),
            Options.Create(new IdentityBrokerReadOptions()));
        Assert.Equal(503, Assert.Throws<CustomerWorkspaceException>(() => adapter.ValidateActor(Principal())).StatusCode);
    }

    [Theory]
    [InlineData("[]")]
    [InlineData("[{\"identityProvider\":\"google\",\"userId\":\"\"}]")]
    [InlineData("[{\"identityProvider\":\"apple\",\"userId\":\"subject\"}]")]
    [InlineData("[{\"identityProvider\":\"google\",\"userId\":\"one\"},{\"identityProvider\":\"google\",\"userId\":\"two\"}]")]
    [InlineData("[{\"identityProvider\":\"google\",\"userId\":\"one\",\"userId\":\"two\"}]")]
    [InlineData("not-json")]
    public async Task Read_MissingAmbiguousOrMalformedBinding_Denies(string body)
    {
        var handler = new SyntheticKeycloakHandler { BindingResponse = body };
        var adapter = new GoogleWorkspaceProofAdapter(new HttpClient(handler), Options.Create(Configuration()));
        var failure = await Record.ExceptionAsync(() => adapter.ReadAsync(Principal(), default));
        Assert.True(failure is IdentityActionDeniedException or CustomerWorkspaceException);
        Assert.Equal(3, handler.Requests.Count);
    }

    [Fact]
    public async Task Read_OversizedBody_IsBoundedUnavailable()
    {
        var handler = new SyntheticKeycloakHandler { BindingResponse = new string(' ', 16385) };
        var adapter = new GoogleWorkspaceProofAdapter(new HttpClient(handler), Options.Create(Configuration()));
        Assert.Equal(503, (await Assert.ThrowsAsync<CustomerWorkspaceException>(() => adapter.ReadAsync(Principal(), default))).StatusCode);
    }

    [Fact]
    public async Task Read_ConflictingDuplicateSubject_DeniesBeforeRead()
    {
        var principal = Principal();
        ((ClaimsIdentity)principal.Identity!).AddClaim(new Claim("sub", "other-actor"));
        var handler = new SyntheticKeycloakHandler();
        var adapter = new GoogleWorkspaceProofAdapter(new HttpClient(handler), Options.Create(Configuration()));
        await Assert.ThrowsAsync<IdentityActionDeniedException>(() => adapter.ReadAsync(principal, default));
        Assert.Empty(handler.Requests);
    }

    [Fact]
    public void CanonicalHash_UsesFullSha256AndBindsOperationRegistrationAndInput()
    {
        var registration = Guid.NewGuid();
        var hash = CustomerIdentityJourneyService.CanonicalHash("CompleteRegistration", registration, new { });
        Assert.Matches("^[0-9a-f]{64}$", hash);
        Assert.Equal(hash, CustomerIdentityJourneyService.CanonicalHash("CompleteRegistration", registration, new { }));
        Assert.NotEqual(hash, CustomerIdentityJourneyService.CanonicalHash("CompleteRegistration", Guid.NewGuid(), new { }));
        Assert.NotEqual(hash, CustomerIdentityJourneyService.CanonicalHash("UpdateProfile", registration, new { }));
        Assert.NotEqual(hash, CustomerIdentityJourneyService.CanonicalHash("CompleteRegistration", registration, new { forged = true }));
    }

    [Fact]
    public async Task MvcFilter_MissingJourneyDI_DeniesLegacyAction()
    {
        var controller = IdentityTestHelpers.CreateController(new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString()));
        var action = new ActionContext(controller.HttpContext, new RouteData(), new ActionDescriptor());
        var context = new ActionExecutingContext(action, [], new Dictionary<string, object?>(), controller);
        var invoked = false;
        await controller.OnActionExecutionAsync(context, () =>
        {
            invoked = true;
            return Task.FromResult(new ActionExecutedContext(action, [], controller));
        });
        Assert.False(invoked);
        Assert.Equal(503, Assert.IsType<ObjectResult>(context.Result).StatusCode);
    }

    [Theory]
    [InlineData("http://keycloak.private.invalid")]
    [InlineData("https://public.invalid")]
    [InlineData("https://keycloak.private.invalid/other")]
    [InlineData("https://secret@keycloak.private.invalid")]
    public void UnapprovedTransport_IsNotConfigured(string origin)
    {
        var configuration = Configuration();
        configuration.PrivateOrigin = origin;
        Assert.False(configuration.IsConfigured);
    }

    internal sealed class SyntheticKeycloakHandler : HttpMessageHandler
    {
        public List<string> Requests { get; } = [];
        public HttpStatusCode Status { get; set; } = HttpStatusCode.OK;
        public string? BindingResponse { get; set; }
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        {
            var path = request.RequestUri!.AbsolutePath;
            Requests.Add(request.Method + " " + path);
            Assert.Equal("keycloak.private.invalid", request.RequestUri.Host);
            string body;
            if (request.Method == HttpMethod.Post)
            {
                var form = await request.Content!.ReadAsStringAsync(ct);
                Assert.Contains("grant_type=client_credentials", form);
                Assert.Contains("client_id=waooaw-bp-identity-reader", form);
                body = "{\"access_token\":\"synthetic-machine-token\",\"token_type\":\"Bearer\",\"expires_in\":60}";
            }
            else
            {
                Assert.Equal(HttpMethod.Get, request.Method);
                Assert.Equal("synthetic-machine-token", request.Headers.Authorization!.Parameter);
                var subject = Uri.UnescapeDataString(path.Split('/')[5]);
                body = path.EndsWith("/federated-identity", StringComparison.Ordinal)
                    ? BindingResponse ?? System.Text.Json.JsonSerializer.Serialize(new[] { new { identityProvider = "google", userId = "Google-Opaque-" + subject } })
                    : System.Text.Json.JsonSerializer.Serialize(new { id = subject, enabled = true, emailVerified = true });
            }
            return new HttpResponseMessage(Status) { Content = new StringContent(body) };
        }
    }
}