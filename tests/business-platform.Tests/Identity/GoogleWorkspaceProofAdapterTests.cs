// Implements: adr/ADR-008-keycloak-identity-broker.md Amendment 3
// constitutional_basis: C-023, C-026, C-059

using System.Net;
using System.Security.Claims;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Abstractions;
using Microsoft.AspNetCore.Mvc.Filters;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class GoogleWorkspaceProofAdapterTests
{
    private sealed class RecordingLogger : ILogger<GoogleWorkspaceProofAdapter>
    {
        public List<string> Messages { get; } = [];

        public IDisposable? BeginScope<TState>(TState state)
            where TState : notnull => null;

        public bool IsEnabled(LogLevel logLevel) => true;

        public void Log<TState>(
            LogLevel logLevel,
            EventId eventId,
            TState state,
            Exception? exception,
            Func<TState, Exception?, string> formatter
        ) => Messages.Add(formatter(state, exception));
    }

    internal static IdentityBrokerReadOptions Configuration() =>
        new()
        {
            Enabled = true,
            ActorIssuer = "https://synthetic.invalid/realms/waooaw",
            PrivateOrigin = "https://keycloak.private.invalid",
            AllowedPrivateHosts = ["keycloak.private.invalid"],
            ClientId = "waooaw-bp-identity-reader",
            ClientSecret = "synthetic-reader-secret",
            AllowedAuthorizedParties = ["waooaw-web"],
            Providers = new()
            {
                ["google"] = new()
                {
                    ProviderNamespace = "urn:waooaw:identity:synthetic:google:customer-login:v1",
                    TrustConfigDigest = new string('a', 64),
                },
                ["facebook"] = new()
                {
                    ProviderNamespace = "urn:waooaw:identity:synthetic:facebook:customer-login:v1",
                    TrustConfigDigest = new string('b', 64),
                },
            },
        };

    internal static ClaimsPrincipal Principal(
        string subject = "synthetic-actor",
        string? issuer = null,
        string provider = "google",
        string authorizedParty = "waooaw-web",
        string providerClaim = "idp"
    )
    {
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        return new ClaimsPrincipal(
            new ClaimsIdentity(
                new[]
                {
                    new Claim("iss", issuer ?? Configuration().ActorIssuer),
                    new Claim("sub", subject),
                    new Claim("aud", "waooaw-platform"),
                    new Claim("azp", authorizedParty),
                    new Claim(providerClaim, provider),
                    new Claim("email_verified", "true"),
                    new Claim("email", "customer@example.com"),
                    new Claim("realm_access", "{\"roles\":[\"customer\"]}"),
                    new Claim("iat", now.ToString()),
                    new Claim("exp", (now + 600).ToString()),
                    new Claim("auth_time", now.ToString()),
                },
                "synthetic-validated-test-principal"
            )
        );
    }

    [Fact]
    public async Task Read_ExactStockRequests_PreservesOpaqueProviderSubject()
    {
        var handler = new SyntheticKeycloakHandler();
        using var client = new HttpClient(handler);
        var adapter = new GoogleWorkspaceProofAdapter(client, Options.Create(Configuration()));
        var proof = await adapter.ReadAsync(Principal(), default);
        Assert.Equal("Google-Opaque-synthetic-actor", proof.ProviderSubject);
        Assert.Equal(Configuration().Providers["google"].ProviderNamespace, proof.ProviderIssuer);
        Assert.Equal(
            new[]
            {
                "POST /realms/waooaw/protocol/openid-connect/token",
                "GET /admin/realms/waooaw/users/synthetic-actor",
                "GET /admin/realms/waooaw/users/synthetic-actor/federated-identity",
            },
            handler.Requests
        );
    }

    [Fact]
    public async Task Read_FacebookBinding_UsesFacebookTrustConfiguration()
    {
        var handler = new SyntheticKeycloakHandler { Provider = "facebook" };
        using var client = new HttpClient(handler);
        var adapter = new GoogleWorkspaceProofAdapter(client, Options.Create(Configuration()));

        var proof = await adapter.ReadAsync(Principal(provider: "facebook"), default);

        Assert.Equal("Facebook-Opaque-synthetic-actor", proof.ProviderSubject);
        Assert.Equal("facebook", proof.BrokerAlias);
        Assert.Equal(Configuration().Providers["facebook"].ProviderNamespace, proof.ProviderIssuer);
        Assert.Equal(
            Configuration().Providers["facebook"].TrustConfigDigest,
            proof.TrustConfigDigest
        );
    }

    [Fact]
    public void PreviewAuthorizedParty_RequiresExplicitConfiguration()
    {
        var configuration = Configuration();
        using var client = new HttpClient(new SyntheticKeycloakHandler());
        var previewPrincipal = Principal(authorizedParty: "waooaw-web-preview");

        var defaultAdapter = new GoogleWorkspaceProofAdapter(client, Options.Create(configuration));
        Assert.Throws<IdentityActionDeniedException>(() => defaultAdapter.ValidateActor(previewPrincipal));

        configuration.AllowedAuthorizedParties = ["waooaw-web", "waooaw-web-preview"];
        var previewAdapter = new GoogleWorkspaceProofAdapter(client, Options.Create(configuration));
        previewAdapter.ValidateActor(previewPrincipal);
    }

    [Fact]
    public async Task LocalClaimsProof_RequiresExplicitLocalPreviewConfiguration()
    {
        var handler = new SyntheticKeycloakHandler();
        using var client = new HttpClient(handler);
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["IdentityProviderPreview:ClaimsProofEnabled"] = "true",
            })
            .Build();
        var principal = Principal(
            issuer: "https://preview.invalid/realms/waooaw",
            authorizedParty: "waooaw-web-preview"
        );
        var adapter = new GoogleWorkspaceProofAdapter(
            client,
            Options.Create(new IdentityBrokerReadOptions()),
            environment: Options.Create(new IdentityEnvironmentOptions { Environment = "local" }),
            configuration: configuration
        );

        var proof = await adapter.ReadAsync(principal, default);

        Assert.True(adapter.IsConfigured);
        Assert.Equal("google", proof.BrokerAlias);
        Assert.Empty(handler.Requests);

        var nonLocal = new GoogleWorkspaceProofAdapter(
            client,
            Options.Create(new IdentityBrokerReadOptions()),
            environment: Options.Create(new IdentityEnvironmentOptions { Environment = "demo" }),
            configuration: configuration
        );
        Assert.False(nonLocal.IsConfigured);
        Assert.Throws<CustomerWorkspaceException>(() => nonLocal.ValidateActor(principal));
    }

    [Fact]
    public void LocalClaimsProof_AcceptsCanonicalIdentityProviderClaimAndRejectsConflict()
    {
        using var client = new HttpClient(new SyntheticKeycloakHandler());
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["IdentityProviderPreview:ClaimsProofEnabled"] = "true",
            })
            .Build();
        var adapter = new GoogleWorkspaceProofAdapter(
            client,
            Options.Create(new IdentityBrokerReadOptions()),
            environment: Options.Create(new IdentityEnvironmentOptions { Environment = "local" }),
            configuration: configuration
        );
        var principal = Principal(
            issuer: "https://preview.invalid/realms/waooaw",
            authorizedParty: "waooaw-web-preview",
            providerClaim: "identity_provider"
        );

        Assert.Equal(IdentityAuthenticationPath.Google, adapter.AuthenticationPath(principal));
        adapter.ValidateActor(principal);

        ((ClaimsIdentity)principal.Identity!).AddClaim(new Claim("idp", "facebook"));
        Assert.Throws<IdentityActionDeniedException>(() => adapter.ValidateActor(principal));
    }

    [Theory]
    [InlineData("authentication", "unauthenticated", false)]
    [InlineData("iss", "", false)]
    [InlineData("sub", "..", false)]
    [InlineData("sub", "service-account-synthetic", false)]
    [InlineData("azp", "other-client", false)]
    [InlineData("aud", "other-audience", false)]
    [InlineData("client_type", "service", false)]
    [InlineData("iat", "invalid", false)]
    [InlineData("iat", "future", false)]
    [InlineData("exp", "invalid", false)]
    [InlineData("exp", "expired", false)]
    [InlineData("exp", "long-lived", false)]
    [InlineData("auth_time", "invalid", false)]
    [InlineData("auth_time", "future", false)]
    [InlineData("auth_time", "stale", true)]
    public void LocalClaimsProof_InvalidSecurityBoundary_Denies(
        string claimType,
        string value,
        bool requiresFreshAuthentication
    )
    {
        using var client = new HttpClient(new SyntheticKeycloakHandler());
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["IdentityProviderPreview:ClaimsProofEnabled"] = "true",
            })
            .Build();
        var adapter = new GoogleWorkspaceProofAdapter(
            client,
            Options.Create(new IdentityBrokerReadOptions()),
            environment: Options.Create(new IdentityEnvironmentOptions { Environment = "local" }),
            configuration: configuration
        );
        var principal = Principal(
            issuer: "https://preview.invalid/realms/waooaw",
            authorizedParty: "waooaw-web-preview"
        );
        var identity = (ClaimsIdentity)principal.Identity!;
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        if (claimType == "authentication")
        {
            principal = new ClaimsPrincipal(new ClaimsIdentity(identity.Claims));
        }
        else
        {
            var existing = identity.FindFirst(claimType);
            if (existing is not null)
                identity.RemoveClaim(existing);
            var replacement = value switch
            {
                "future" => (now + 60).ToString(),
                "expired" => (now - 60).ToString(),
                "long-lived" => (now + 901).ToString(),
                "stale" => (now - 301).ToString(),
                _ => value,
            };
            identity.AddClaim(new Claim(claimType, replacement));
        }

        if (requiresFreshAuthentication)
        {
            var failure = Assert.Throws<CustomerWorkspaceException>(() =>
                adapter.ValidateActor(principal, requireFresh: true)
            );
            Assert.Equal(CustomerWorkspaceError.FreshAuthenticationRequired, failure.Error);
        }
        else
        {
            Assert.Throws<IdentityActionDeniedException>(() => adapter.ValidateActor(principal));
        }
    }

    [Fact]
    public async Task Read_ConfiguredAppleBinding_UsesSharedBrokerProof()
    {
        var configuration = Configuration();
        configuration.Providers["apple"] = new()
        {
            ProviderNamespace = "urn:waooaw:identity:synthetic:apple:customer-login:v1",
            TrustConfigDigest = new string('c', 64),
        };
        var handler = new SyntheticKeycloakHandler { Provider = "apple" };
        using var client = new HttpClient(handler);
        var adapter = new GoogleWorkspaceProofAdapter(client, Options.Create(configuration));

        var proof = await adapter.ReadAsync(Principal(provider: "apple"), default);

        Assert.Equal(Waooaw.BusinessPlatform.Infrastructure.IdentityAuthenticationPath.Apple,
            adapter.AuthenticationPath(Principal(provider: "apple")));
        Assert.Equal("apple", proof.BrokerAlias);
        Assert.Equal(configuration.Providers["apple"].ProviderNamespace, proof.ProviderIssuer);
    }

    [Fact]
    public async Task Read_UnsupportedProvider_DeniesBeforeNetwork()
    {
        var handler = new SyntheticKeycloakHandler();
        using var client = new HttpClient(handler);
        var adapter = new GoogleWorkspaceProofAdapter(client, Options.Create(Configuration()));

        await Assert.ThrowsAsync<IdentityActionDeniedException>(() =>
            adapter.ReadAsync(Principal(provider: "apple"), default)
        );

        Assert.Empty(handler.Requests);
    }

    [Fact]
    public async Task Read_PinnedStockKeycloakOverPrivateHttps_PreservesOpaqueProviderSubject()
    {
        if (Environment.GetEnvironmentVariable("WC085_STOCK_READER") != "true")
            return;

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
            Providers = new()
            {
                ["google"] = new()
                {
                    ProviderNamespace = "urn:waooaw:identity:demo:google:customer-login:v1",
                    TrustConfigDigest = new string('b', 64),
                },
            },
        };
        using var client = new HttpClient();
        var adapter = new GoogleWorkspaceProofAdapter(client, Options.Create(configuration));

        var proof = await adapter.ReadAsync(
            Principal(actorSubject, configuration.ActorIssuer),
            default
        );

        Assert.Equal(actorSubject, proof.Actor.Subject);
        Assert.Equal("Google-Opaque-" + actorSubject, proof.ProviderSubject);
        Assert.Equal(configuration.Providers["google"].ProviderNamespace, proof.ProviderIssuer);
    }

    [Theory]
    [InlineData("iss", "https://wrong.invalid/realms/waooaw")]
    [InlineData("azp", "waooaw-mobile")]
    [InlineData("aud", "other")]
    [InlineData("idp", "password")]
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
        using var client = new HttpClient(handler);
        var adapter = new GoogleWorkspaceProofAdapter(client, Options.Create(Configuration()));
        await Assert.ThrowsAnyAsync<Exception>(() => adapter.ReadAsync(principal, default));
        Assert.Empty(handler.Requests);
    }

    [Fact]
    public void ValidateActor_DenialLogsRuleWithoutClaimValue()
    {
        var principal = Principal();
        var identity = (ClaimsIdentity)principal.Identity!;
        identity.RemoveClaim(identity.FindFirst("aud"));
        identity.AddClaim(new Claim("aud", "private-audience-value"));
        var logger = new RecordingLogger();
        using var client = new HttpClient(new SyntheticKeycloakHandler());
        var adapter = new GoogleWorkspaceProofAdapter(
            client,
            Options.Create(Configuration()),
            logger
        );

        Assert.Throws<IdentityActionDeniedException>(() => adapter.ValidateActor(principal));

        var message = Assert.Single(logger.Messages);
        Assert.Contains("actor_audience", message, StringComparison.Ordinal);
        Assert.DoesNotContain("private-audience-value", message, StringComparison.Ordinal);
        Assert.DoesNotContain("synthetic-actor", message, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("client_type", "service")]
    [InlineData("sub", "service-account-synthetic")]
    [InlineData("iat", "invalid")]
    [InlineData("iat", "future")]
    [InlineData("exp", "invalid")]
    [InlineData("exp", "expired")]
    [InlineData("exp", "long-lived")]
    [InlineData("auth_time", "invalid")]
    [InlineData("auth_time", "future")]
    [InlineData("auth_time", "after-issued")]
    [InlineData("nbf", "invalid")]
    [InlineData("nbf", "future")]
    public void ValidateActor_InvalidSecurityBoundary_DeniesWithoutLogger(
        string claimType,
        string value
    )
    {
        var principal = Principal();
        var identity = (ClaimsIdentity)principal.Identity!;
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        var replacement = value switch
        {
            "future" => (now + 60).ToString(),
            "expired" => (now - 60).ToString(),
            "long-lived" => (now + 901).ToString(),
            "after-issued" => (now + 31).ToString(),
            _ => value,
        };
        var existing = identity.FindFirst(claimType);
        if (existing is not null)
            identity.RemoveClaim(existing);
        identity.AddClaim(new Claim(claimType, replacement));
        using var client = new HttpClient(new SyntheticKeycloakHandler());
        var adapter = new GoogleWorkspaceProofAdapter(client, Options.Create(Configuration()));

        Assert.Throws<IdentityActionDeniedException>(() => adapter.ValidateActor(principal));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("false")]
    public async Task Read_UnverifiedEmail_DeniesBeforeNetwork(string? emailVerified)
    {
        var principal = Principal();
        var identity = (ClaimsIdentity)principal.Identity!;
        identity.RemoveClaim(identity.FindFirst("email_verified"));
        if (emailVerified is not null) identity.AddClaim(new Claim("email_verified", emailVerified));
        var handler = new SyntheticKeycloakHandler();
        using var client = new HttpClient(handler);
        var adapter = new GoogleWorkspaceProofAdapter(client, Options.Create(Configuration()));

        Assert.False(adapter.HasVerifiedEmail(principal));
        adapter.ValidateActor(principal);
        await Assert.ThrowsAsync<IdentityActionDeniedException>(() => adapter.ReadAsync(principal, default));
        Assert.Empty(handler.Requests);
    }

    [Fact]
    public void VerifiedEmail_RequiresValidEmailClaim()
    {
        var principal = Principal();
        var adapter = new GoogleWorkspaceProofAdapter(
            new HttpClient(new SyntheticKeycloakHandler()), Options.Create(Configuration()));
        Assert.Equal("customer@example.com", adapter.VerifiedEmail(principal));

        var identity = (ClaimsIdentity)principal.Identity!;
        identity.RemoveClaim(identity.FindFirst("email"));
        identity.AddClaim(new Claim("email", "not-an-email"));
        Assert.Throws<IdentityActionDeniedException>(() => adapter.VerifiedEmail(principal));
    }

    [Theory]
    [InlineData(302)]
    [InlineData(401)]
    [InlineData(403)]
    [InlineData(500)]
    public async Task Read_DependencyFailure_IsUnavailableWithoutEscalation(int status)
    {
        var handler = new SyntheticKeycloakHandler { Status = (HttpStatusCode)status };
        using var client = new HttpClient(handler);
        var adapter = new GoogleWorkspaceProofAdapter(client, Options.Create(Configuration()));
        var failure = await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
            adapter.ReadAsync(Principal(), default)
        );
        Assert.Equal(503, failure.StatusCode);
        Assert.Single(handler.Requests);
    }

    [Fact]
    public void AbsentConfiguration_IsUnavailable()
    {
        using var client = new HttpClient(new SyntheticKeycloakHandler());
        var adapter = new GoogleWorkspaceProofAdapter(
            client,
            Options.Create(new IdentityBrokerReadOptions())
        );
        Assert.Equal(
            503,
            Assert
                .Throws<CustomerWorkspaceException>(() => adapter.ValidateActor(Principal()))
                .StatusCode
        );
    }

    [Theory]
    [InlineData("[]")]
    [InlineData("[{\"identityProvider\":\"google\",\"userId\":\"\"}]")]
    [InlineData("[{\"identityProvider\":\"apple\",\"userId\":\"subject\"}]")]
    [InlineData(
        "[{\"identityProvider\":\"google\",\"userId\":\"one\"},{\"identityProvider\":\"google\",\"userId\":\"two\"}]"
    )]
    [InlineData("[{\"identityProvider\":\"google\",\"userId\":\"one\",\"userId\":\"two\"}]")]
    [InlineData("not-json")]
    public async Task Read_MissingAmbiguousOrMalformedBinding_Denies(string body)
    {
        var handler = new SyntheticKeycloakHandler { BindingResponse = body };
        using var client = new HttpClient(handler);
        var adapter = new GoogleWorkspaceProofAdapter(client, Options.Create(Configuration()));
        var failure = await Record.ExceptionAsync(() => adapter.ReadAsync(Principal(), default));
        Assert.True(failure is IdentityActionDeniedException or CustomerWorkspaceException);
        Assert.Equal(3, handler.Requests.Count);
    }

    [Fact]
    public async Task Read_OversizedBody_IsBoundedUnavailable()
    {
        var handler = new SyntheticKeycloakHandler { BindingResponse = new string(' ', 16385) };
        using var client = new HttpClient(handler);
        var adapter = new GoogleWorkspaceProofAdapter(client, Options.Create(Configuration()));
        Assert.Equal(
            503,
            (
                await Assert.ThrowsAsync<CustomerWorkspaceException>(() =>
                    adapter.ReadAsync(Principal(), default)
                )
            ).StatusCode
        );
    }

    [Fact]
    public async Task Read_ConflictingDuplicateSubject_DeniesBeforeRead()
    {
        var principal = Principal();
        ((ClaimsIdentity)principal.Identity!).AddClaim(new Claim("sub", "other-actor"));
        var handler = new SyntheticKeycloakHandler();
        using var client = new HttpClient(handler);
        var adapter = new GoogleWorkspaceProofAdapter(client, Options.Create(Configuration()));
        await Assert.ThrowsAsync<IdentityActionDeniedException>(() =>
            adapter.ReadAsync(principal, default)
        );
        Assert.Empty(handler.Requests);
    }

    [Fact]
    public void CanonicalHash_UsesFullSha256AndBindsOperationRegistrationAndInput()
    {
        var registration = Guid.NewGuid();
        var hash = CustomerIdentityJourneyService.CanonicalHash(
            "CompleteRegistration",
            registration,
            new { }
        );
        Assert.Matches("^[0-9a-f]{64}$", hash);
        Assert.Equal(
            hash,
            CustomerIdentityJourneyService.CanonicalHash(
                "CompleteRegistration",
                registration,
                new { }
            )
        );
        Assert.NotEqual(
            hash,
            CustomerIdentityJourneyService.CanonicalHash(
                "CompleteRegistration",
                Guid.NewGuid(),
                new { }
            )
        );
        Assert.NotEqual(
            hash,
            CustomerIdentityJourneyService.CanonicalHash("UpdateProfile", registration, new { })
        );
        Assert.NotEqual(
            hash,
            CustomerIdentityJourneyService.CanonicalHash(
                "CompleteRegistration",
                registration,
                new { forged = true }
            )
        );
    }

    [Fact]
    public async Task MvcFilter_MissingJourneyDI_DeniesLegacyAction()
    {
        var controller = IdentityTestHelpers.CreateController(
            new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString())
        );
        var action = new ActionContext(
            controller.HttpContext,
            new RouteData(),
            new ActionDescriptor()
        );
        var context = new ActionExecutingContext(
            action,
            [],
            new Dictionary<string, object?>(),
            controller
        );
        var invoked = false;
        await controller.OnActionExecutionAsync(
            context,
            () =>
            {
                invoked = true;
                return Task.FromResult(new ActionExecutedContext(action, [], controller));
            }
        );
        Assert.False(invoked);
        Assert.Equal(503, Assert.IsType<ObjectResult>(context.Result).StatusCode);
    }

    [Theory]
    [InlineData("StartRegistrationAsync", "object", 201, "google", 0, false, "sid", "REGISTRATION_START", "SUCCEEDED")]
    [InlineData("StartRegistrationAsync", "status", 500, "facebook", 10, true, "jti", "REGISTRATION_FAILURE", "FAILED")]
    [InlineData("CompleteRegistrationAsync", "exception", 500, "apple", null, false, "none", "REGISTRATION_FAILURE", "FAILED")]
    [InlineData("CompleteRegistrationAsync", "default", 200, "email", 10, false, "sid", "REGISTRATION_COMPLETION", "SUCCEEDED")]
    [InlineData("GetSessionAsync", "object-default", 200, null, 0, false, "sid", "SESSION_ESTABLISHMENT", "SUCCEEDED")]
    [InlineData("GetSessionAsync", "status", 401, "google", 10, false, "sid", "AUTHORIZATION_DENIAL", "DENIED")]
    [InlineData("StartAccountLinkAsync", "status", 403, "facebook", 0, false, "sid", "AUTHORIZATION_DENIAL", "DENIED")]
    [InlineData("ApproveAccountLinkAsync", "status", 503, "apple", 0, false, "sid", "AUTHORIZATION_DENIAL", "FAILED")]
    public async Task MvcFilter_RecordsPrivacySafeObservedEvent(
        string actionName,
        string resultKind,
        int status,
        string? provider,
        int? authAgeMinutes,
        bool useSubClaim,
        string sessionClaim,
        string expectedEvent,
        string expectedOutcome)
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var identity = IdentityTestHelpers.CreateService(factory);
        var adapter = new GoogleWorkspaceProofAdapter(
            new HttpClient(),
            Options.Create(Configuration()));
        var providers = new IdentityProviderProjectionService(
            Options.Create(IdentityTestHelpers.TestEnvironment),
            IdentityTestHelpers.EmptyConfiguration);
        var journey = new CustomerIdentityJourneyService(identity, factory, adapter, providers);
        var securityEvents = new IdentitySecurityEventService(
            factory,
            Options.Create(new IdentityHmacOptions
            {
                Key = "test-only-identity-security-event-key-32-bytes",
            }),
            Options.Create(new IdentityEnvironmentOptions { Environment = "local" }));
        var claims = new List<Claim>
        {
            new(useSubClaim ? "sub" : ClaimTypes.NameIdentifier, "observed-actor"),
        };
        if (provider is not null)
            claims.Add(new Claim(provider == "facebook" ? "idp" : "identity_provider", provider));
        if (authAgeMinutes.HasValue)
            claims.Add(new Claim(
                "auth_time",
                DateTimeOffset.UtcNow.AddMinutes(-authAgeMinutes.Value).ToUnixTimeSeconds().ToString()));
        if (sessionClaim != "none")
            claims.Add(new Claim(sessionClaim, "observed-session"));
        var httpContext = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity(claims, "Test")),
        };
        httpContext.Items[CustomerMembershipMiddleware.JourneyItem] = true;
        var controller = new IdentityController(
            identity,
            providers,
            NullLogger<IdentityController>.Instance,
            journey,
            securityEvents)
        {
            ControllerContext = new ControllerContext { HttpContext = httpContext },
        };
        var action = new ActionContext(
            httpContext,
            new RouteData(),
            new ActionDescriptor { RouteValues = { ["action"] = actionName } });
        var context = new ActionExecutingContext(action, [], new Dictionary<string, object?>(), controller);

        await controller.OnActionExecutionAsync(context, () =>
        {
            var executed = new ActionExecutedContext(action, [], controller)
            {
                Result = resultKind switch
                {
                    "object" => new ObjectResult(new { }) { StatusCode = status },
                    "object-default" => new ObjectResult(new { }),
                    "status" => new StatusCodeResult(status),
                    _ => new EmptyResult(),
                },
            };
            if (resultKind == "exception")
                executed.Exception = new InvalidOperationException("synthetic action failure");
            return Task.FromResult(executed);
        });

        await using var db = factory.CreateDbContext();
        var record = Assert.Single(db.SecurityEvents);
        Assert.Equal(expectedEvent, record.EventType);
        Assert.Equal(expectedOutcome, record.Outcome);
        Assert.Equal(provider?.ToUpperInvariant() ?? "UNKNOWN", record.ProviderClass);
        Assert.NotNull(record.ActorRef);
    }

    [Fact]
    public async Task MvcFilter_IgnoresActionWithoutSecurityEventMapping()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var identity = IdentityTestHelpers.CreateService(factory);
        var adapter = new GoogleWorkspaceProofAdapter(new HttpClient(), Options.Create(Configuration()));
        var providers = new IdentityProviderProjectionService(
            Options.Create(IdentityTestHelpers.TestEnvironment),
            IdentityTestHelpers.EmptyConfiguration);
        var journey = new CustomerIdentityJourneyService(identity, factory, adapter, providers);
        var securityEvents = new IdentitySecurityEventService(
            factory,
            Options.Create(new IdentityHmacOptions { Key = "test-only-identity-security-event-key-32-bytes" }),
            Options.Create(new IdentityEnvironmentOptions { Environment = "local" }));
        var httpContext = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity([new Claim("sub", "observed-actor")], "Test")),
        };
        httpContext.Items[CustomerMembershipMiddleware.JourneyItem] = true;
        var controller = new IdentityController(
            identity, providers, NullLogger<IdentityController>.Instance, journey, securityEvents)
        {
            ControllerContext = new ControllerContext { HttpContext = httpContext },
        };
        var action = new ActionContext(
            httpContext,
            new RouteData(),
            new ActionDescriptor { RouteValues = { ["action"] = "GetProfileAsync" } });

        await controller.OnActionExecutionAsync(
            new ActionExecutingContext(action, [], new Dictionary<string, object?>(), controller),
            () => Task.FromResult(new ActionExecutedContext(action, [], controller) { Result = new OkResult() }));

        await using var db = factory.CreateDbContext();
        Assert.Empty(db.SecurityEvents);
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

    [Fact]
    public void SharedProviderNamespace_IsNotConfigured()
    {
        var configuration = Configuration();
        configuration.Providers["facebook"].ProviderNamespace = configuration
            .Providers["google"]
            .ProviderNamespace;

        Assert.False(configuration.IsConfigured);
    }

    [Fact]
    public void IndexedAuthorizedParties_BindWithoutDuplicatingDefaults()
    {
        var values = new Dictionary<string, string?>
        {
            ["IdentityBrokerRead:Enabled"] = "true",
            ["IdentityBrokerRead:ActorIssuer"] = "https://synthetic.invalid/realms/waooaw",
            ["IdentityBrokerRead:PrivateOrigin"] = "https://keycloak.private.invalid",
            ["IdentityBrokerRead:AllowedPrivateHosts:0"] = "keycloak.private.invalid",
            ["IdentityBrokerRead:ClientId"] = "waooaw-bp-identity-reader",
            ["IdentityBrokerRead:ClientSecret"] = "synthetic-reader-secret",
            ["IdentityBrokerRead:AllowedAuthorizedParties:0"] = "waooaw-web",
            ["IdentityBrokerRead:AllowedAuthorizedParties:1"] = "waooaw-web-preview",
            ["IdentityBrokerRead:Providers:google:ProviderNamespace"] =
                "urn:waooaw:identity:synthetic:google:customer-login:v1",
            ["IdentityBrokerRead:Providers:google:TrustConfigDigest"] = new string('a', 64),
            ["IdentityBrokerRead:Providers:facebook:ProviderNamespace"] =
                "urn:waooaw:identity:synthetic:facebook:customer-login:v1",
            ["IdentityBrokerRead:Providers:facebook:TrustConfigDigest"] = new string('b', 64),
        };
        var configuration = new ConfigurationBuilder().AddInMemoryCollection(values).Build();
        var options = new IdentityBrokerReadOptions();

        configuration.GetSection(IdentityBrokerReadOptions.SectionName).Bind(options);

        Assert.Equal(["waooaw-web", "waooaw-web-preview"], options.AllowedAuthorizedParties);
        Assert.True(options.IsConfigured);
    }

    internal sealed class SyntheticKeycloakHandler : HttpMessageHandler
    {
        public List<string> Requests { get; } = [];
        public HttpStatusCode Status { get; set; } = HttpStatusCode.OK;
        public string? BindingResponse { get; set; }
        public string Provider { get; set; } = "google";

        protected override async Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken ct
        )
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
                body =
                    "{\"access_token\":\"synthetic-machine-token\",\"token_type\":\"Bearer\",\"expires_in\":60}";
            }
            else
            {
                Assert.Equal(HttpMethod.Get, request.Method);
                Assert.Equal("synthetic-machine-token", request.Headers.Authorization!.Parameter);
                var subject = Uri.UnescapeDataString(path.Split('/')[5]);
                body = path.EndsWith("/federated-identity", StringComparison.Ordinal)
                    ? BindingResponse
                        ?? System.Text.Json.JsonSerializer.Serialize(
                            new[]
                            {
                                new
                                {
                                    identityProvider = Provider,
                                    userId = char.ToUpperInvariant(Provider[0])
                                        + Provider[1..]
                                        + "-Opaque-"
                                        + subject,
                                },
                            }
                        )
                    : System.Text.Json.JsonSerializer.Serialize(
                        new
                        {
                            id = subject,
                            enabled = true,
                            emailVerified = true,
                        }
                    );
            }
            return new HttpResponseMessage(Status) { Content = new StringContent(body) };
        }
    }
}
