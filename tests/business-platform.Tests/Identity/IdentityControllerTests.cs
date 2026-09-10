// Implements: architecture/reference/components/identity-boundary.md §F2 Backend Tests
// constitutional_basis: C-023, C-026, C-059

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

// ── In-memory factory for IdentityDbContext (tests only) ─────────────────────

internal sealed class InMemoryIdentityDbContextFactory(string dbName, params IInterceptor[] interceptors)
    : IDbContextFactory<IdentityDbContext>
{
    public IdentityDbContext CreateDbContext() =>
        new(new DbContextOptionsBuilder<IdentityDbContext>()
            .UseInMemoryDatabase(dbName)
            .AddInterceptors(interceptors)
            .Options);
}

internal sealed class CapturingVerificationDispatcher : IIdentityVerificationDispatcher
{
    public string? LatestCode { get; private set; }

    public Task DispatchAsync(
        IdentityVerificationPurpose purpose,
        string destination,
        string code,
        CancellationToken ct)
    {
        LatestCode = code;
        return Task.CompletedTask;
    }
}

internal sealed class FailingVerificationDispatcher : IIdentityVerificationDispatcher
{
    public Task DispatchAsync(
        IdentityVerificationPurpose purpose,
        string destination,
        string code,
        CancellationToken ct) =>
        throw new InvalidOperationException("provider unavailable");
}

// ── Test helpers ─────────────────────────────────────────────────────────────

internal static class IdentityTestHelpers
{
    private const string TestHmacKey = "test-only-identity-hmac-key-32-bytes-minimum";

    private static readonly IdentityEnvironmentOptions TestEnvironment = new()
    {
        SchemaVersion = "1.0",
        Environment = "local",
        Providers =
        [
            new() { Id = "GOOGLE", DisplayName = "Google", AuthenticationPath = "GOOGLE", Enabled = true, BrokerAlias = "google", Scopes = ["openid", "profile", "email"], SecretReference = "kv://google-client", ReadinessEvidenceReference = "TEST-GOOGLE" },
            new() { Id = "FACEBOOK", DisplayName = "Facebook", AuthenticationPath = "META", Enabled = false, UnavailableReason = "NOT_CONFIGURED", BrokerAlias = "facebook", Scopes = ["email", "public_profile"] },
            new() { Id = "APPLE", DisplayName = "Apple", AuthenticationPath = "APPLE", Enabled = false, UnavailableReason = "NOT_CONFIGURED", BrokerAlias = "apple", Scopes = ["openid", "name", "email"] },
            new() { Id = "EMAIL", DisplayName = "Email", AuthenticationPath = "CREDENTIAL", Enabled = true, Scopes = [], ReadinessEvidenceReference = "TEST-EMAIL" },
        ],
    };

    public static IdentityController CreateController(
        IDbContextFactory<IdentityDbContext> factory,
        string subject = "test-subject",
        string? tenantId = null,
        string? identityProvider = null,
        string? providerIssuer = null,
        string? email = null,
        bool emailVerified = false,
        long? authTimestamp = null,
        string[]? customerRoles = null,
        CapturingVerificationDispatcher? dispatcher = null)
    {
        var service = CreateService(factory, dispatcher);

        var claims = new List<Claim>
        {
            new(ClaimTypes.NameIdentifier, subject),
        };
        if (email is not null) claims.Add(new Claim("email", email));
        if (emailVerified) claims.Add(new Claim("email_verified", "true"));
        if (identityProvider is not null) claims.Add(new Claim("identity_provider", identityProvider));
        if (providerIssuer is not null) claims.Add(new Claim("iss", providerIssuer));
        if (authTimestamp.HasValue) claims.Add(new Claim("auth_time", authTimestamp.Value.ToString()));
        if (tenantId is not null)
        {
            claims.Add(new Claim("exp", DateTimeOffset.UtcNow.AddMinutes(15).ToUnixTimeSeconds().ToString()));
            foreach (var role in customerRoles ?? ["OWNER"])
                claims.Add(new Claim("waooaw_roles", role));
        }

        var user = new ClaimsPrincipal(new ClaimsIdentity(claims, "Test"));

        var httpContext = new DefaultHttpContext { User = user };
        httpContext.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString();
        if (tenantId is not null)
            httpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId;

        return new IdentityController(
            service,
            new IdentityProviderProjectionService(Options.Create(TestEnvironment)),
            NullLogger<IdentityController>.Instance)
        {
            ControllerContext = new ControllerContext { HttpContext = httpContext },
        };
    }

    public static IdentityService CreateService(
        IDbContextFactory<IdentityDbContext> factory,
        CapturingVerificationDispatcher? dispatcher = null) =>
        new(
            factory,
            Options.Create(new IdentityHmacOptions { Key = TestHmacKey }),
            dispatcher ?? new CapturingVerificationDispatcher());

    // Sets a fresh idempotency key for each call
    public static void RefreshIdempotencyKey(ControllerBase controller) =>
        controller.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString();

    // Creates a controller with an arbitrary dispatcher (e.g. FailingVerificationDispatcher)
    public static IdentityController CreateControllerWithDispatcher(
        IDbContextFactory<IdentityDbContext> factory,
        IIdentityVerificationDispatcher dispatcher,
        string subject = "test-subject",
        string? tenantId = null,
        string? identityProvider = null,
        long? authTimestamp = null,
        string[]? customerRoles = null)
    {
        var service = new IdentityService(
            factory,
            Options.Create(new IdentityHmacOptions { Key = TestHmacKey }),
            dispatcher);

        var claims = new List<Claim> { new(ClaimTypes.NameIdentifier, subject) };
        if (identityProvider is not null) claims.Add(new Claim("identity_provider", identityProvider));
        if (authTimestamp.HasValue) claims.Add(new Claim("auth_time", authTimestamp.Value.ToString()));
        if (tenantId is not null)
        {
            claims.Add(new Claim("exp", DateTimeOffset.UtcNow.AddMinutes(15).ToUnixTimeSeconds().ToString()));
            foreach (var role in customerRoles ?? ["OWNER"])
                claims.Add(new Claim("waooaw_roles", role));
        }

        var user = new ClaimsPrincipal(new ClaimsIdentity(claims, "Test"));
        var httpContext = new DefaultHttpContext { User = user };
        httpContext.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString();
        if (tenantId is not null)
            httpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId;

        return new IdentityController(
            service,
            new IdentityProviderProjectionService(Options.Create(TestEnvironment)),
            NullLogger<IdentityController>.Instance)
        {
            ControllerContext = new ControllerContext { HttpContext = httpContext },
        };
    }
}

public sealed class IdentityProviderProjectionTests
{
    private static string EnvironmentManifestPath(string environment) =>
        Path.GetFullPath(Path.Combine(
            AppContext.BaseDirectory,
            "../../../../../infrastructure/identity-config/environments",
            $"{environment}.json"));

    [Fact]
    public void F2_GetProviders_ReturnsOrderedReadinessWithoutSecrets()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var controller = IdentityTestHelpers.CreateController(factory);

        var result = Assert.IsType<OkObjectResult>(controller.GetProviders());
        var json = JsonSerializer.Serialize(result.Value);
        var projection = JsonSerializer.SerializeToElement(result.Value);
        var providers = projection.GetProperty("Providers").EnumerateArray().ToArray();

        Assert.Equal(["GOOGLE", "FACEBOOK", "APPLE", "EMAIL"],
            providers.Select(provider => provider.GetProperty("Id").GetString()!).ToArray());
        Assert.Equal("AVAILABLE", providers[0].GetProperty("Availability").GetString());
        Assert.Equal("UNAVAILABLE", providers[1].GetProperty("Availability").GetString());
        Assert.Equal("NOT_CONFIGURED", providers[1].GetProperty("UnavailableReason").GetString());
        Assert.DoesNotContain("SecretReference", json);
        Assert.DoesNotContain("ReadinessEvidenceReference", json);
        Assert.DoesNotContain("BrokerAlias", json);
    }

    [Fact]
    public void F2_GetProviders_UnconfiguredGoogleJourneyDoesNotDisableOtherProviders()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var projection = new IdentityProviderProjectionService(Options.Create(new IdentityEnvironmentOptions
        {
            Providers =
            [
                new() { Id = "GOOGLE", DisplayName = "Google", AuthenticationPath = "GOOGLE", Enabled = true },
                new() { Id = "EMAIL", DisplayName = "Email", AuthenticationPath = "CREDENTIAL", Enabled = true },
            ],
        }));
        var journey = new CustomerIdentityJourneyService(
            IdentityTestHelpers.CreateService(factory),
            factory,
            new GoogleWorkspaceProofAdapter(new HttpClient(), Options.Create(new IdentityBrokerReadOptions())),
            projection);
        var controller = new IdentityController(
            IdentityTestHelpers.CreateService(factory),
            projection,
            NullLogger<IdentityController>.Instance,
            journey)
        {
            ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() },
        };

        var result = Assert.IsType<OkObjectResult>(controller.GetProviders());
        var providers = Assert.IsType<IdentityProviderCollectionResponse>(result.Value).Providers;

        Assert.Equal("UNAVAILABLE", providers.Single(provider => provider.Id == "GOOGLE").Availability);
        Assert.Equal("AVAILABLE", providers.Single(provider => provider.Id == "EMAIL").Availability);
    }

    [Fact]
    public void F2_IdentityEnvironmentValidator_RejectsEnabledProviderWithoutReadinessEvidence()
    {
        var options = new IdentityEnvironmentOptions
        {
            SchemaVersion = "1.0",
            Environment = "demo",
            Providers =
            [
                new() { Id = "GOOGLE", DisplayName = "Google", AuthenticationPath = "GOOGLE", Enabled = true, BrokerAlias = "google", SecretReference = "kv://google-client" },
                new() { Id = "FACEBOOK", DisplayName = "Facebook", AuthenticationPath = "META", Enabled = false, UnavailableReason = "NOT_CONFIGURED" },
                new() { Id = "APPLE", DisplayName = "Apple", AuthenticationPath = "APPLE", Enabled = false, UnavailableReason = "NOT_CONFIGURED" },
                new() { Id = "EMAIL", DisplayName = "Email", AuthenticationPath = "CREDENTIAL", Enabled = true },
            ],
        };

        var result = new IdentityEnvironmentOptionsValidator().Validate(null, options);

        Assert.True(result.Failed);
        Assert.Contains(result.Failures, failure => failure.Contains("readiness evidence", StringComparison.Ordinal));
    }

    [Theory]
    [InlineData("demo")]
    [InlineData("uat")]
    [InlineData("prod")]
    public void F2_IdentityEnvironmentManifest_IsStrictAndValid(string environment)
    {
        var json = File.ReadAllText(EnvironmentManifestPath(environment));
        var options = JsonSerializer.Deserialize<IdentityEnvironmentOptions>(json,
            new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

        Assert.NotNull(options);
        var result = new IdentityEnvironmentOptionsValidator().Validate(null, options);
        Assert.True(result.Succeeded,
            result.Failed ? string.Join(Environment.NewLine, result.Failures) : string.Empty);
        Assert.All(options.Providers.Where(provider => provider.Enabled), provider =>
            Assert.False(string.IsNullOrWhiteSpace(provider.ReadinessEvidenceReference)));
        Assert.DoesNotContain("clientSecret", json, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void F2_IdentityEnvironmentValidator_RejectsWildcardProductionRedirect()
    {
        var json = File.ReadAllText(EnvironmentManifestPath("prod"));
        var options = JsonSerializer.Deserialize<IdentityEnvironmentOptions>(json,
            new JsonSerializerOptions { PropertyNameCaseInsensitive = true })!;
        options.Clients[0].RedirectUris = ["https://app.waooaw.com/*"];

        var result = new IdentityEnvironmentOptionsValidator().Validate(null, options);

        Assert.True(result.Failed);
        Assert.Contains(result.Failures, failure => failure.Contains("wildcard", StringComparison.Ordinal));
    }

    [Theory]
    [InlineData("ca-uat-web.wonderfulmoss-740b2b2d.centralindia.azurecontainerapps.io")]
    [InlineData("ca-demo-web.other.centralindia.azurecontainerapps.io")]
    [InlineData("ca-demo-web.wonderfulmoss-740b2b2d.centralindia.azurecontainerapps.io.example.com")]
    public void F2_IdentityEnvironmentValidator_RejectsUnapprovedDemoCloudHost(string host)
    {
        var options = ReadManifest("demo");
        options.Clients[0].RedirectUris = [$"https://{host}/api/auth/callback/keycloak-google"];

        var result = new IdentityEnvironmentOptionsValidator().Validate(null, options);

        Assert.True(result.Failed);
        Assert.Contains(result.Failures, failure => failure.Contains("does not belong to demo", StringComparison.Ordinal));
    }

    [Fact]
    public void F2_IdentityEnvironment_DemoOverlayClearsLocalProviderReadiness()
    {
        var manifestPath = Path.GetFullPath(EnvironmentManifestPath("demo"));
        var root = Path.GetFullPath("../../..", Path.GetDirectoryName(manifestPath)!);
        var configuration = new ConfigurationBuilder()
            .AddJsonFile(Path.GetFullPath("src/business-platform/appsettings.json", root))
            .Build();
        using var manifest = JsonDocument.Parse(File.ReadAllText(manifestPath));

        void Overlay(JsonElement element, string prefix)
        {
            if (element.ValueKind == JsonValueKind.Object)
                foreach (var property in element.EnumerateObject())
                    Overlay(property.Value, prefix + ":" + property.Name);
            else if (element.ValueKind == JsonValueKind.Array)
            {
                var index = 0;
                foreach (var child in element.EnumerateArray())
                    Overlay(child, prefix + ":" + index++);
            }
            else
                configuration[prefix] = element.ToString();
        }

        Overlay(manifest.RootElement, IdentityEnvironmentOptions.SectionName);
        for (var index = 0; index < 4; index++)
        {
            configuration[$"IdentityEnvironment:providers:{index}:enabled"] = "false";
            configuration[$"IdentityEnvironment:providers:{index}:unavailableReason"] = "NOT_CONFIGURED";
            configuration[$"IdentityEnvironment:providers:{index}:readinessEvidenceReference"] = "";
        }
        var options = configuration.GetSection(IdentityEnvironmentOptions.SectionName)
            .Get<IdentityEnvironmentOptions>()!;

        var result = new IdentityEnvironmentOptionsValidator().Validate(null, options);

        Assert.True(result.Succeeded, result.Failed ? string.Join("; ", result.Failures) : "");
        Assert.Equal("demo", options.Environment);
        Assert.All(new IdentityProviderProjectionService(Options.Create(options)).GetProviders(),
            provider => Assert.Equal("UNAVAILABLE", provider.Availability));
        Assert.Equal("", options.Providers[3].ReadinessEvidenceReference);
    }

    [Fact]
    public void F2_IdentityEnvironmentValidator_RejectsCrossEnvironmentRedirect()
    {
        var options = ReadManifest("prod");
        options.Clients[0].RedirectUris = ["https://app.uat.waooaw.com/api/auth/callback/keycloak"];

        var result = new IdentityEnvironmentOptionsValidator().Validate(null, options);

        Assert.True(result.Failed);
        Assert.Contains(result.Failures, failure => failure.Contains("does not belong to prod", StringComparison.Ordinal));
    }

    [Fact]
    public void F2_IdentityEnvironmentValidator_RejectsDuplicateBrokerAlias()
    {
        var options = ReadManifest("demo");
        options.Providers[1].BrokerAlias = options.Providers[0].BrokerAlias;

        var result = new IdentityEnvironmentOptionsValidator().Validate(null, options);

        Assert.True(result.Failed);
        Assert.Contains(result.Failures, failure => failure.Contains("broker aliases must be unique", StringComparison.Ordinal));
    }

    [Fact]
    public void F2_IdentityEnvironmentValidator_RejectsMetaBusinessScope()
    {
        var options = ReadManifest("uat");
        options.Providers[1].Scopes.Add("business_management");

        var result = new IdentityEnvironmentOptionsValidator().Validate(null, options);

        Assert.True(result.Failed);
        Assert.Contains(result.Failures, failure => failure.Contains("scopes must be exactly", StringComparison.Ordinal));
    }

    [Fact]
    public void F2_IdentityEnvironmentValidator_RejectsUnsafeConfigurationVariants()
    {
        Action<IdentityEnvironmentOptions>[] mutations =
        [
            options => options.SchemaVersion = "2.0",
            options => options.Environment = "unknown",
            options => options.Origins.Web = "relative",
            options => options.Origins.Api = "http://api.waooaw.com",
            options => options.Keycloak.Audience = "other",
            options => options.Keycloak.Realm = "other",
            options => options.Keycloak.AccessTokenMinutes = 16,
            options => options.Keycloak.RefreshSessionHours = 9,
            options => options.Keycloak.ClockSkewSeconds = -1,
            options => options.Keycloak.ClockSkewSeconds = 61,
            options => options.Keycloak.Issuer = "relative",
            options => options.Keycloak.JwksUri = "relative",
            options => options.Keycloak.JwksUri = "http://identity.waooaw.com/realms/waooaw/protocol/openid-connect/certs",
            options => options.Keycloak.JwksUri = "https://other.waooaw.com/realms/waooaw/protocol/openid-connect/certs",
            options => options.Keycloak.JwksUri = "https://identity.waooaw.com/not-the-issuer/certs",
            options => options.Clients.RemoveAt(0),
            options => options.Clients[0].Channel = "OTHER",
            options => options.Clients[0].Id = "",
            options => options.Clients[0].PkceRequired = false,
            options => options.Clients[0].Scopes.Remove("openid"),
            options => options.Clients[0].RedirectUris = [],
            options => options.Clients[0].PostLogoutRedirectUris = [],
            options => options.Clients[0].AllowedOrigins = ["relative"],
            options => options.Clients[0].AllowedOrigins = ["https://app.demo.waooaw.com"],
            options => options.Channels.Web = false,
            options => options.Channels.WhatsApp = false,
            options => options.Cookie.Name = "",
            options => options.Cookie.SameSite = "None",
            options => options.Cookie.Secure = false,
            options => options.IdentityEdge.Image = "",
            options => options.IdentityEdge.RoutePolicy = "",
            options => options.PhoneIdentity.InternalAudience = "",
            options => options.Providers.Reverse(),
            options => options.Providers[0].DisplayName = "",
            options => options.Providers[0].DisplayName = new string('x', 41),
            options => options.Providers[0].AuthenticationPath = "OTHER",
            options => options.Providers[0].Scopes.Add(options.Providers[0].Scopes[0]),
            options => options.Providers[3].UnavailableReason = "NOT_CONFIGURED",
            options => EnableGoogle(options, brokerAlias: ""),
            options => EnableGoogle(options, secretReference: ""),
            options => EnableGoogle(options, readinessEvidenceReference: ""),
            options => options.Providers[1].UnavailableReason = "",
            options => options.Providers[1].UnavailableReason = "INTERNAL_DETAIL",
            options => options.Providers[0].SecretReference = "secret-material",
            options => options.Providers[0].SecretReference = "kv://secret=value",
        ];

        for (var mutationIndex = 0; mutationIndex < mutations.Length; mutationIndex++)
        {
            var options = ReadManifest("prod");
            mutations[mutationIndex](options);

            Assert.True(new IdentityEnvironmentOptionsValidator().Validate(null, options).Failed,
                $"Mutation {mutationIndex} must fail validation.");
        }
    }

    private static IdentityEnvironmentOptions ReadManifest(string environment) =>
        JsonSerializer.Deserialize<IdentityEnvironmentOptions>(
            File.ReadAllText(EnvironmentManifestPath(environment)),
            new JsonSerializerOptions { PropertyNameCaseInsensitive = true })!;

    private static void EnableGoogle(
        IdentityEnvironmentOptions options,
        string brokerAlias = "google",
        string secretReference = "kv://google-client",
        string readinessEvidenceReference = "TEST-GOOGLE")
    {
        var provider = options.Providers[0];
        provider.Enabled = true;
        provider.UnavailableReason = null;
        provider.BrokerAlias = brokerAlias;
        provider.SecretReference = secretReference;
        provider.ReadinessEvidenceReference = readinessEvidenceReference;
    }
}

public sealed class IdentitySessionProjectionTests
{
    [Fact]
    public async Task F2_GetSession_ReturnsActorBoundAccountAndOwnerHints()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var controller = IdentityTestHelpers.CreateController(
            factory,
            subject: "session-owner",
            tenantId: Guid.NewGuid().ToString(),
            identityProvider: "google",
            email: "owner@example.com",
            emailVerified: true,
            authTimestamp: DateTimeOffset.UtcNow.ToUnixTimeSeconds());

        var created = Assert.IsType<ObjectResult>(await controller.StartRegistrationAsync(
            new StartRegistrationRequest("en"), CancellationToken.None));
        var registrationId = JsonSerializer.SerializeToElement(created.Value)
            .GetProperty("RegistrationId").GetGuid();
        IdentityTestHelpers.RefreshIdempotencyKey(controller);
        await controller.UpdateProfileAsync(registrationId,
            new UpdateRegistrationProfileRequest("Owner", "Acme", "Retail", "en"),
            CancellationToken.None);
        IdentityTestHelpers.RefreshIdempotencyKey(controller);
        await controller.CompleteRegistrationAsync(registrationId, CancellationToken.None);

        var result = Assert.IsType<OkObjectResult>(await controller.GetSessionAsync(CancellationToken.None));
        var json = JsonSerializer.SerializeToElement(result.Value);

        Assert.Equal("AAL2_ACCOUNT", json.GetProperty("AssuranceLevel").GetString());
        Assert.Contains("OWNER", json.GetProperty("Roles").EnumerateArray().Select(value => value.GetString()));
        Assert.Contains("LINK_WHATSAPP", json.GetProperty("Capabilities").EnumerateArray().Select(value => value.GetString()));
        Assert.False(json.TryGetProperty("TenantId", out _));
    }

    [Fact]
    public async Task F2_StartAccountLink_ViewerRoleIsDeniedBeforeMutation()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var controller = IdentityTestHelpers.CreateController(
            factory,
            tenantId: Guid.NewGuid().ToString(),
            authTimestamp: DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
            customerRoles: ["VIEWER"]);

        var result = Assert.IsType<ObjectResult>(await controller.StartAccountLinkAsync(
            new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));

        Assert.Equal(403, result.StatusCode);
        Assert.Empty(factory.CreateDbContext().AccountLinks);
    }
}

public sealed class CustomerPortalIdentityTests
{
    private static async Task<IdentityController> CompletedControllerAsync(
        InMemoryIdentityDbContextFactory factory,
        string subject = "portal-owner",
        string? tenantId = null,
        string[]? roles = null)
    {
        var controller = IdentityTestHelpers.CreateController(factory, subject,
            tenantId ?? Guid.NewGuid().ToString(), "google", email: "owner@example.com",
            emailVerified: true, customerRoles: roles ?? ["OWNER"]);
        var created = Assert.IsType<ObjectResult>(await controller.StartRegistrationAsync(
            new StartRegistrationRequest("en"), CancellationToken.None));
        var registrationId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();
        IdentityTestHelpers.RefreshIdempotencyKey(controller);
        await controller.UpdateProfileAsync(registrationId,
            new UpdateRegistrationProfileRequest("Original", "Original Org", "Retail", "en"), CancellationToken.None);
        IdentityTestHelpers.RefreshIdempotencyKey(controller);
        await controller.CompleteRegistrationAsync(registrationId, CancellationToken.None);
        IdentityTestHelpers.RefreshIdempotencyKey(controller);
        return controller;
    }

    [Fact]
    public async Task Profile_UpdatePersistsAndSameKeyDifferentBodyConflicts()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var controller = await CompletedControllerAsync(factory);
        var request = new UpdateCustomerProfileRequest("1.0.0", "Ada", "Analytical Engines");

        var updated = Assert.IsType<OkObjectResult>(
            await controller.UpdateCustomerProfileAsync(request, CancellationToken.None));
        Assert.Equal("Ada", JsonSerializer.SerializeToElement(updated.Value).GetProperty("DisplayName").GetString());

        var replay = await controller.UpdateCustomerProfileAsync(request, CancellationToken.None);
        Assert.IsType<OkObjectResult>(replay);
        var conflict = Assert.IsType<ObjectResult>(await controller.UpdateCustomerProfileAsync(
            request with { DisplayName = "Grace" }, CancellationToken.None));
        Assert.Equal(409, conflict.StatusCode);
    }

    [Fact]
    public async Task Profile_IsTenantBoundAndViewerCannotMutate()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var tenantA = Guid.NewGuid().ToString();
        var controller = await CompletedControllerAsync(factory, tenantId: tenantA);
        await controller.UpdateCustomerProfileAsync(
            new UpdateCustomerProfileRequest("1.0.0", "Tenant A", "Org A"), CancellationToken.None);

        var tenantB = IdentityTestHelpers.CreateController(factory, "portal-owner", Guid.NewGuid().ToString(),
            "google", email: "owner@example.com", emailVerified: true, customerRoles: ["OWNER"]);
        var other = Assert.IsType<OkObjectResult>(await tenantB.GetCustomerProfileAsync(CancellationToken.None));
        Assert.Equal("Original", JsonSerializer.SerializeToElement(other.Value).GetProperty("DisplayName").GetString());

        var viewer = IdentityTestHelpers.CreateController(factory, "portal-owner", tenantA,
            "google", email: "owner@example.com", emailVerified: true, customerRoles: ["VIEWER"]);
        var denied = Assert.IsType<ObjectResult>(await viewer.UpdateCustomerProfileAsync(
            new UpdateCustomerProfileRequest("1.0.0", "No", "No"), CancellationToken.None));
        Assert.Equal(403, denied.StatusCode);
    }

    [Fact]
    public async Task Settings_UpdateRoundTripsValidatedPreferences()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var controller = await CompletedControllerAsync(factory);
        var request = new UpdateCustomerSettingsRequest("1.0.0", "fr-FR", "DARK", "ABSOLUTE",
            new NotificationPreferencesRequest(["IN_APP", "EMAIL"], ["EMAIL"], ["IN_APP"], ["WHATSAPP"]));

        var result = Assert.IsType<OkObjectResult>(
            await controller.UpdateCustomerSettingsAsync(request, CancellationToken.None));
        var json = JsonSerializer.SerializeToElement(result.Value);
        Assert.Equal("fr-FR", json.GetProperty("Locale").GetString());
        Assert.Equal("DARK", json.GetProperty("Theme").GetString());

        var read = Assert.IsType<OkObjectResult>(await controller.GetCustomerSettingsAsync(CancellationToken.None));
        Assert.Equal("ABSOLUTE", JsonSerializer.SerializeToElement(read.Value).GetProperty("TimestampVisibility").GetString());
    }

    [Fact]
    public async Task LoginMethods_ExposeOnlyAliasesStateAndMaskedIdentifier()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var controller = await CompletedControllerAsync(factory);

        var result = Assert.IsType<OkObjectResult>(controller.ListCustomerLoginMethods());
        var json = JsonSerializer.SerializeToElement(result.Value);
        var google = json.GetProperty("Items").EnumerateArray().Single(item => item.GetProperty("Provider").GetString() == "GOOGLE");
        Assert.Equal("ACTIVE", google.GetProperty("State").GetString());
        Assert.Equal("o***@example.com", google.GetProperty("MaskedIdentifier").GetString());
        Assert.DoesNotContain("subject", json.ToString(), StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("token", json.ToString(), StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task Profile_ReportsHighestAuthorityRole()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var controller = await CompletedControllerAsync(factory, roles: ["VIEWER", "OWNER", "MANAGER"]);

        var result = Assert.IsType<OkObjectResult>(await controller.GetCustomerProfileAsync(CancellationToken.None));

        Assert.Equal("OWNER", JsonSerializer.SerializeToElement(result.Value).GetProperty("ActiveRole").GetString());
    }

    [Fact]
    public async Task PortalEndpoints_RejectIncompleteSessions()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var missingTenant = IdentityTestHelpers.CreateController(factory, customerRoles: ["OWNER"]);
        var missingRoles = IdentityTestHelpers.CreateController(
            factory, tenantId: Guid.NewGuid().ToString("D"), customerRoles: []);
        var invalidExpiry = IdentityTestHelpers.CreateController(
            factory, tenantId: Guid.NewGuid().ToString("D"), customerRoles: ["OWNER"]);
        var expiryIdentity = (ClaimsIdentity)invalidExpiry.User.Identity!;
        expiryIdentity.RemoveClaim(expiryIdentity.FindFirst("exp")!);
        expiryIdentity.AddClaim(new Claim("exp", "invalid"));

        Assert.Equal(401, Assert.IsType<ObjectResult>(
            await missingTenant.GetSessionAsync(CancellationToken.None)).StatusCode);
        Assert.Equal(401, Assert.IsType<ObjectResult>(
            await missingRoles.GetSessionAsync(CancellationToken.None)).StatusCode);
        Assert.Equal(401, Assert.IsType<ObjectResult>(
            await invalidExpiry.GetSessionAsync(CancellationToken.None)).StatusCode);
        Assert.Equal(401, Assert.IsType<ObjectResult>(
            await missingTenant.GetCustomerProfileAsync(CancellationToken.None)).StatusCode);
        Assert.Equal(401, Assert.IsType<ObjectResult>(
            await missingRoles.GetCustomerSettingsAsync(CancellationToken.None)).StatusCode);
        Assert.Equal(401, Assert.IsType<ObjectResult>(missingTenant.ListCustomerLoginMethods()).StatusCode);
    }

    [Fact]
    public async Task ProfileAndSettings_RejectInvalidPortalPayloads()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var controller = await CompletedControllerAsync(factory);
        UpdateCustomerProfileRequest[] invalidProfiles =
        [
            new("2.0.0", "Ada", "Analytical Engines"),
            new("1.0.0", "", "Analytical Engines"),
            new("1.0.0", new string('x', 201), "Analytical Engines"),
            new("1.0.0", "Ada", ""),
            new("1.0.0", "Ada", new string('x', 201)),
        ];
        var validPreferences = new NotificationPreferencesRequest(
            ["IN_APP"], ["EMAIL"], ["IN_APP"], ["WHATSAPP"]);
        UpdateCustomerSettingsRequest[] invalidSettings =
        [
            new("2.0.0", "en", "SYSTEM", "RELATIVE", validPreferences),
            new("1.0.0", "invalid", "SYSTEM", "RELATIVE", validPreferences),
            new("1.0.0", "en", "OTHER", "RELATIVE", validPreferences),
            new("1.0.0", "en", "SYSTEM", "OTHER", validPreferences),
            new("1.0.0", "en", "SYSTEM", "RELATIVE", null!),
            new("1.0.0", "en", "SYSTEM", "RELATIVE", validPreferences with { ApprovalRequests = null! }),
            new("1.0.0", "en", "SYSTEM", "RELATIVE", validPreferences with { MaturityReports = ["SMS"] }),
            new("1.0.0", "en", "SYSTEM", "RELATIVE", validPreferences with { MonthlyNarratives = null! }),
            new("1.0.0", "en", "SYSTEM", "RELATIVE", validPreferences with { SelfGovernanceAlerts = ["SMS"] }),
        ];

        foreach (var request in invalidProfiles)
            Assert.Equal(400, Assert.IsType<ObjectResult>(
                await controller.UpdateCustomerProfileAsync(request, CancellationToken.None)).StatusCode);
        foreach (var request in invalidSettings)
            Assert.Equal(400, Assert.IsType<ObjectResult>(
                await controller.UpdateCustomerSettingsAsync(request, CancellationToken.None)).StatusCode);
    }

    [Fact]
    public async Task PortalProjectsFallbackRolesAndLoginProviders()
    {
        foreach (var (roles, expectedRole) in new[]
        {
            (new[] { "MANAGER" }, "MANAGER"),
            (new[] { "VIEWER" }, "VIEWER"),
        })
        {
            var controller = await CompletedControllerAsync(
                new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N")), roles: roles);
            var result = Assert.IsType<OkObjectResult>(
                await controller.GetCustomerProfileAsync(CancellationToken.None));
            Assert.Equal(expectedRole,
                JsonSerializer.SerializeToElement(result.Value).GetProperty("ActiveRole").GetString());
        }

        foreach (var provider in new[] { "meta", "apple", "credential" })
        {
            var controller = IdentityTestHelpers.CreateController(
                new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N")),
                tenantId: Guid.NewGuid().ToString("D"), identityProvider: provider,
                customerRoles: ["OWNER"]);
            Assert.IsType<OkObjectResult>(controller.ListCustomerLoginMethods());
        }
    }
}

// ── Registration Tests ────────────────────────────────────────────────────────

public sealed class IdentityRegistrationTests
{
    [Fact]
    public async Task F2_SubjectClaim_FallsBackToSubAndRejectsMissingSubject()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var controller = IdentityTestHelpers.CreateController(factory, identityProvider: "google");
        var identity = (ClaimsIdentity)controller.User.Identity!;
        identity.RemoveClaim(identity.FindFirst(ClaimTypes.NameIdentifier)!);
        identity.AddClaim(new Claim("sub", "fallback-subject"));

        Assert.IsType<ObjectResult>(await controller.StartRegistrationAsync(
            new StartRegistrationRequest("en"), CancellationToken.None));

        identity.RemoveClaim(identity.FindFirst("sub")!);
        IdentityTestHelpers.RefreshIdempotencyKey(controller);
        await Assert.ThrowsAsync<UnauthorizedAccessException>(() => controller.StartRegistrationAsync(
            new StartRegistrationRequest("en"), CancellationToken.None));
    }

    [Fact]
    public async Task F2_StartRegistration_Google_Returns201WithRegistrationId()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory,
            identityProvider: "google", email: "test@example.com", emailVerified: true);

        var result = await ctrl.StartRegistrationAsync(
            new StartRegistrationRequest("en"), CancellationToken.None);

        var created = Assert.IsType<ObjectResult>(result);
        Assert.Equal(201, created.StatusCode);
        var json = JsonSerializer.Serialize(created.Value);
        Assert.Contains("RegistrationId", json);
        Assert.DoesNotContain("TenantId", json);
        Assert.DoesNotContain("EmailHmacKey", json);
    }

    [Fact]
    public async Task F2_StartRegistration_SameIdempotencyKey_Replays()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, identityProvider: "google");

        var first = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var firstJson = JsonSerializer.SerializeToElement(first.Value);
        var regId = firstJson.GetProperty("RegistrationId").GetGuid();

        // Same Idempotency-Key → replay
        var replay = Assert.IsType<OkObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var replayJson = JsonSerializer.SerializeToElement(replay.Value);
        Assert.Equal(regId, replayJson.GetProperty("RegistrationId").GetGuid());
    }

    [Fact]
    public async Task F2_StartRegistration_Facebook_Returns403ActionDenied()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, identityProvider: "facebook");

        var result = await ctrl.StartRegistrationAsync(
            new StartRegistrationRequest("en"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(403, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_ACTION_DENIED", json.GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartRegistration_Apple_Returns403ActionDenied()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, identityProvider: "apple");

        var result = await ctrl.StartRegistrationAsync(
            new StartRegistrationRequest("en"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(403, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_ACTION_DENIED", json.GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_GetRegistration_CrossTenant_Returns404NotAccessible()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "subject-a", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var json = JsonSerializer.SerializeToElement(created.Value);
        var regId = json.GetProperty("RegistrationId").GetGuid();

        // Different subject tries to read the registration
        var ctrl2 = IdentityTestHelpers.CreateController(factory, subject: "subject-b", identityProvider: "google");
        IdentityTestHelpers.RefreshIdempotencyKey(ctrl2);

        var result = await ctrl2.GetRegistrationAsync(regId, CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        var errJson = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE", errJson.GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_GetRegistration_SameSubject_Returns200()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "same-sub", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var json = JsonSerializer.SerializeToElement(created.Value);
        var regId = json.GetProperty("RegistrationId").GetGuid();

        var result = await ctrl.GetRegistrationAsync(regId, CancellationToken.None);
        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public async Task F2_UpdateProfile_SetsMinimumFields_StateAdvances()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "profile-sub",
            identityProvider: "google", email: "p@example.com", emailVerified: true);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var update = await ctrl.UpdateProfileAsync(regId, new UpdateRegistrationProfileRequest(
            "Test User", "Acme", "Retail", "en"), CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(update);
        var updJson = JsonSerializer.SerializeToElement(ok.Value);
        Assert.Equal("READY_TO_COMPLETE", updJson.GetProperty("State").GetString());
    }

    [Fact]
    public async Task F2_CompleteRegistration_WithoutEmail_Returns422VerificationRequired()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        // emailVerified = false
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "incomplete-sub",
            identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.CompleteRegistrationAsync(regId, CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(422, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_VERIFICATION_REQUIRED", json.GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_CompleteRegistration_WithEmail_Returns200AccountCreated()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "complete-sub",
            identityProvider: "google", email: "c@example.com", emailVerified: true);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        await ctrl.UpdateProfileAsync(regId, new UpdateRegistrationProfileRequest(
            "Full Name", "Corp", "Consulting", "en"), CancellationToken.None);

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.CompleteRegistrationAsync(regId, CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var json = JsonSerializer.SerializeToElement(ok.Value);
        Assert.Equal("ACCOUNT_CREATED", json.GetProperty("Outcome").GetString());
        Assert.Equal("AAL2_ACCOUNT", json.GetProperty("AssuranceLevel").GetString());
    }

    [Fact]
    public async Task F2_CompleteRegistration_Replay_ReturnsSameOutcome()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "replay-comp",
            identityProvider: "google", email: "r@example.com", emailVerified: true);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        await ctrl.UpdateProfileAsync(regId, new UpdateRegistrationProfileRequest(
            "Name", "Co", "Domain", "en"), CancellationToken.None);

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var first = Assert.IsType<OkObjectResult>(
            await ctrl.CompleteRegistrationAsync(regId, CancellationToken.None));
        var firstRef = JsonSerializer.SerializeToElement(first.Value).GetProperty("AccountReference").GetGuid();

        // Same idempotency key → replay
        var replay = Assert.IsType<OkObjectResult>(
            await ctrl.CompleteRegistrationAsync(regId, CancellationToken.None));
        var replayRef = JsonSerializer.SerializeToElement(replay.Value).GetProperty("AccountReference").GetGuid();

        Assert.Equal(firstRef, replayRef);
    }

    [Fact]
    public async Task F2_CompleteRegistration_SaveFailure_PreservesIncompleteStateAndAllowsRetry()
    {
        var interceptor = new FailCompletionSaveOnceInterceptor();
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"), interceptor);
        var registration = new IdentityRegistrationRecord
        {
            ActorSubject = "completion-save-failure",
            State = IdentityRegistrationState.ReadyToComplete,
            EmailVerified = true,
            DisplayName = "Test Customer",
            BusinessName = "Test Business",
            BusinessDomain = "Consulting",
        };
        await using (var seed = factory.CreateDbContext())
        {
            seed.Registrations.Add(registration);
            await seed.SaveChangesAsync();
        }

        var service = IdentityTestHelpers.CreateService(factory);
        var idempotencyKey = Guid.NewGuid();
        const string canonicalHash = "completion-save-failure-hash";

        await Assert.ThrowsAsync<DbUpdateException>(() => service.CompleteRegistrationAsync(
            registration.RegistrationId, registration.ActorSubject, idempotencyKey,
            canonicalHash, CancellationToken.None));

        await using (var persisted = factory.CreateDbContext())
        {
            var unchanged = await persisted.Registrations.SingleAsync();
            Assert.Null(unchanged.AccountId);
            Assert.Equal(IdentityRegistrationState.ReadyToComplete, unchanged.State);
            Assert.Equal(registration.UpdatedAt, unchanged.UpdatedAt);
            Assert.Empty(await persisted.IdempotencyLedger.ToListAsync());
        }

        var (completed, isNew) = await service.CompleteRegistrationAsync(
            registration.RegistrationId, registration.ActorSubject, idempotencyKey,
            canonicalHash, CancellationToken.None);
        var (replayed, replayIsNew) = await service.CompleteRegistrationAsync(
            registration.RegistrationId, registration.ActorSubject, idempotencyKey,
            canonicalHash, CancellationToken.None);

        Assert.True(isNew);
        Assert.Equal("ACCOUNT_CREATED", completed.Outcome);
        Assert.NotEqual(Guid.Empty, completed.AccountReference);
        Assert.False(replayIsNew);
        Assert.Equal(completed, replayed);
        await using var saved = factory.CreateDbContext();
        var committed = await saved.Registrations.SingleAsync();
        Assert.Equal(completed.AccountReference, committed.AccountId);
        Assert.Equal(IdentityRegistrationState.Completed, committed.State);
        Assert.Single(await saved.IdempotencyLedger.ToListAsync());
    }

    private sealed class FailCompletionSaveOnceInterceptor : SaveChangesInterceptor
    {
        private bool _failed;

        public override ValueTask<InterceptionResult<int>> SavingChangesAsync(
            DbContextEventData eventData,
            InterceptionResult<int> result,
            CancellationToken cancellationToken = default)
        {
            if (!_failed && eventData.Context!.ChangeTracker.Entries<IdentityIdempotencyEntry>()
                .Any(entry => entry.State == EntityState.Added
                    && entry.Entity.OperationFamily == "CompleteRegistration"))
            {
                _failed = true;
                throw new DbUpdateException("Synthetic completion persistence failure.");
            }

            return ValueTask.FromResult(result);
        }
    }
}

// ── Email Verification Tests ──────────────────────────────────────────────────

public sealed class IdentityEmailVerificationTests
{
    [Fact]
    public async Task F2_StartEmailVerification_Returns202Challenge()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "ev-sub", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.StartEmailVerificationAsync(regId,
            new StartEmailVerificationRequest("test@example.com"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(202, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Contains("ChallengeId", json.ToString());
        // Must never return raw email or match keys
        Assert.DoesNotContain("test@example.com", json.ToString());
    }

    [Fact]
    public async Task F2_StartEmailVerification_AntiEnumeration_SameResponseShape()
    {
        // Both known and unknown emails must return the same 202 shape
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "ae-sub", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var r1 = Assert.IsType<ObjectResult>(
            await ctrl.StartEmailVerificationAsync(regId, new("known@example.com"), CancellationToken.None));

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var r2 = Assert.IsType<ObjectResult>(
            await ctrl.StartEmailVerificationAsync(regId, new("unknown@example.com"), CancellationToken.None));

        // Both must be 202
        Assert.Equal(202, r1.StatusCode);
        Assert.Equal(202, r2.StatusCode);
    }

    [Fact]
    public async Task F2_ConfirmEmailVerification_ExpiredChallenge_Returns410()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "exp-sub", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var chResp = Assert.IsType<ObjectResult>(
            await ctrl.StartEmailVerificationAsync(regId, new("test@example.com"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(chResp.Value).GetProperty("ChallengeId").GetGuid();

        // Manually expire the challenge
        await using var db = factory.CreateDbContext();
        var ch = await db.VerificationChallenges.FindAsync(challengeId);
        ch!.State = IdentityVerificationState.Expired;
        await db.SaveChangesAsync();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmEmailVerificationAsync(regId,
            new ConfirmVerificationRequest(challengeId, "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(410, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_CHALLENGE_EXPIRED", json.GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmEmailVerification_WrongCode_Returns403AndLeavesChallengePending()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "wrong-email-code", dispatcher: dispatcher);
        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var started = Assert.IsType<ObjectResult>(await ctrl.StartEmailVerificationAsync(
            regId, new("person@example.com"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var denied = Assert.IsType<ObjectResult>(await ctrl.ConfirmEmailVerificationAsync(
            regId, new(challengeId, "000000"), CancellationToken.None));
        Assert.Equal(403, denied.StatusCode);
        Assert.NotEqual("000000", dispatcher.LatestCode);

        await using var db = factory.CreateDbContext();
        var challenge = await db.VerificationChallenges.FindAsync(challengeId);
        Assert.Equal(IdentityVerificationState.Pending, challenge!.State);
        Assert.False((await db.Registrations.FindAsync(regId))!.EmailVerified);
    }

    [Fact]
    public async Task F2_ConfirmEmailVerification_ValidDispatchedCode_SucceedsWithoutPersistingRawCode()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "valid-email-code", dispatcher: dispatcher);
        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var started = Assert.IsType<ObjectResult>(await ctrl.StartEmailVerificationAsync(
            regId, new("person@example.com"), CancellationToken.None));
        var responseJson = JsonSerializer.Serialize(started.Value);
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();
        Assert.NotNull(dispatcher.LatestCode);
        Assert.DoesNotContain(dispatcher.LatestCode!, responseJson);

        await using (var db = factory.CreateDbContext())
        {
            var challenge = await db.VerificationChallenges.FindAsync(challengeId);
            Assert.NotEqual(dispatcher.LatestCode, challenge!.CodeHmac);
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var confirmed = Assert.IsType<OkObjectResult>(await ctrl.ConfirmEmailVerificationAsync(
            regId, new(challengeId, dispatcher.LatestCode!), CancellationToken.None));
        Assert.True(JsonSerializer.SerializeToElement(confirmed.Value).GetProperty("EmailVerified").GetBoolean());
    }
}

// ── Idempotency Conflict Tests ────────────────────────────────────────────────

public sealed class IdentityIdempotencyTests
{
    [Fact]
    public async Task F2_DivergentIdempotencyKey_Returns409Conflict()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "idem-sub", identityProvider: "google");

        // First call
        await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None);

        // Same Idempotency-Key but different body (different canonical hash)
        var result = await ctrl.StartRegistrationAsync(new StartRegistrationRequest("fr"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(409, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT", json.GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_SameKeyAndHash_Replays_WithoutDoubleWrite()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "replay-sub", identityProvider: "google");

        var r1 = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        Assert.Equal(201, r1.StatusCode);

        var r2 = Assert.IsType<OkObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        Assert.Equal(200, r2.StatusCode);

        // Registration count must stay at 1
        await using var db = factory.CreateDbContext();
        Assert.Equal(1, await db.Registrations.CountAsync());
    }
}

// ── Account Link / WhatsApp Boundary Tests ────────────────────────────────────

public sealed class IdentityAccountLinkTests
{
    [Fact]
    public async Task F2_StartAccountLink_WithFreshAal3_Returns201()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var authTs = DateTimeOffset.UtcNow.AddMinutes(-1);  // within 5-minute window
        var ctrl = IdentityTestHelpers.CreateController(factory,
            subject: "link-sub",
            tenantId: Guid.NewGuid().ToString(),
            authTimestamp: authTs.ToUnixTimeSeconds());

        var result = await ctrl.StartAccountLinkAsync(
            new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(201, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Contains("LinkId", json.ToString());
        Assert.Equal("AAL3_FRESH", json.GetProperty("RequiredAssurance").GetString());
        Assert.Equal("PENDING_PORTAL_APPROVAL", json.GetProperty("State").GetString());
    }

    [Fact]
    public async Task F2_StartAccountLink_StaleSession_Returns403StepUpRequired()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var authTs = DateTimeOffset.UtcNow.AddMinutes(-10);  // outside 5-minute window
        var ctrl = IdentityTestHelpers.CreateController(factory,
            subject: "stale-sub",
            tenantId: Guid.NewGuid().ToString(),
            authTimestamp: authTs.ToUnixTimeSeconds());

        var result = await ctrl.StartAccountLinkAsync(
            new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(403, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_STEP_UP_REQUIRED", json.GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_GetAccountLink_CrossTenant_Returns404NotAccessible()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var tenantA = Guid.NewGuid().ToString();
        var tenantB = Guid.NewGuid().ToString();
        var authTs = DateTimeOffset.UtcNow.AddMinutes(-1);

        var ctrlA = IdentityTestHelpers.CreateController(factory,
            subject: "ct-sub-a", tenantId: tenantA,
            authTimestamp: authTs.ToUnixTimeSeconds());

        var created = Assert.IsType<ObjectResult>(
            await ctrlA.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));
        var linkId = JsonSerializer.SerializeToElement(created.Value).GetProperty("LinkId").GetGuid();

        // Different tenant tries to read the link
        var ctrlB = IdentityTestHelpers.CreateController(factory,
            subject: "ct-sub-a", tenantId: tenantB);

        var result = await ctrlB.GetAccountLinkAsync(linkId, CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE", json.GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_GetAccountLink_WithoutTenant_Returns401SessionRequired()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        // No tenantId set in context
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "no-tenant-sub");

        var result = await ctrl.GetAccountLinkAsync(Guid.NewGuid(), CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(401, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_SESSION_REQUIRED", json.GetProperty("code").GetString());
    }
}

// ── Progressive Mobile Verification Tests ────────────────────────────────────

public sealed class IdentityProgressiveMobileTests
{
    [Fact]
    public async Task F2_StartAccountMobileVerification_Returns202Challenge()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "mob-sub",
            tenantId: Guid.NewGuid().ToString());

        var result = await ctrl.StartAccountMobileVerificationAsync(
            new StartMobileVerificationRequest("+911234567890"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(202, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Contains("ChallengeId", json.ToString());
        // Never reveal actual mobile number
        Assert.DoesNotContain("+911234567890", json.ToString());
    }

    [Fact]
    public async Task F2_ProgressiveMobile_AntiEnumeration_SameResponseShape()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl1 = IdentityTestHelpers.CreateController(factory, subject: "mob-ae-1");
        var ctrl2 = IdentityTestHelpers.CreateController(factory, subject: "mob-ae-2");

        // Both existing and non-existing mobiles must return the same 202 shape
        var r1 = Assert.IsType<ObjectResult>(
            await ctrl1.StartAccountMobileVerificationAsync(
                new StartMobileVerificationRequest("+919999999999"), CancellationToken.None));
        var r2 = Assert.IsType<ObjectResult>(
            await ctrl2.StartAccountMobileVerificationAsync(
                new StartMobileVerificationRequest("+911111111111"), CancellationToken.None));

        Assert.Equal(202, r1.StatusCode);
        Assert.Equal(202, r2.StatusCode);
    }

    [Fact]
    public async Task F2_ProgressiveMobile_ValidCode_ReplaysStableOutcome()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "progressive-mobile", dispatcher: dispatcher);

        var started = Assert.IsType<ObjectResult>(await ctrl.StartAccountMobileVerificationAsync(
            new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();
        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var key = ctrl.Request.Headers["Idempotency-Key"].ToString();

        var first = Assert.IsType<OkObjectResult>(await ctrl.ConfirmAccountMobileVerificationAsync(
            new(challengeId, dispatcher.LatestCode!), CancellationToken.None));
        var firstJson = JsonSerializer.SerializeToElement(first.Value);
        Assert.NotEqual("***", firstJson.GetProperty("MaskedMobile").GetString());

        ctrl.Request.Headers["Idempotency-Key"] = key;
        var replay = Assert.IsType<OkObjectResult>(await ctrl.ConfirmAccountMobileVerificationAsync(
            new(challengeId, dispatcher.LatestCode!), CancellationToken.None));
        var replayJson = JsonSerializer.SerializeToElement(replay.Value);
        Assert.Equal(firstJson.GetProperty("MaskedMobile").GetString(), replayJson.GetProperty("MaskedMobile").GetString());
        Assert.Equal(firstJson.GetProperty("VerifiedAt").GetDateTimeOffset(), replayJson.GetProperty("VerifiedAt").GetDateTimeOffset());
    }

    [Fact]
    public async Task F2_RegistrationMobile_StoresMatchKeyAndRejectsCrossRegistrationChallenge()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "mobile-registration", dispatcher: dispatcher);
        var first = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationAsync(new("en"), CancellationToken.None));
        var reg1 = JsonSerializer.SerializeToElement(first.Value).GetProperty("RegistrationId").GetGuid();
        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var second = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationAsync(new("fr"), CancellationToken.None));
        var reg2 = JsonSerializer.SerializeToElement(second.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var started = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            reg1, new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        await using (var db = factory.CreateDbContext())
        {
            var registration = await db.Registrations.FindAsync(reg1);
            Assert.NotNull(registration!.MobileHmacKey);
            Assert.DoesNotContain("+911234567890", registration.MobileHmacKey!);
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var inaccessible = Assert.IsType<ObjectResult>(await ctrl.ConfirmRegistrationMobileVerificationAsync(
            reg2, new(challengeId, dispatcher.LatestCode!), CancellationToken.None));
        Assert.Equal(404, inaccessible.StatusCode);
    }

    [Fact]
    public async Task F2_ProgressiveMobile_WrongCode_Returns403AndLeavesChallengePending()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "wrong-mobile-code", dispatcher: dispatcher);
        var started = Assert.IsType<ObjectResult>(await ctrl.StartAccountMobileVerificationAsync(
            new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var denied = Assert.IsType<ObjectResult>(await ctrl.ConfirmAccountMobileVerificationAsync(
            new(challengeId, "000000"), CancellationToken.None));
        Assert.Equal(403, denied.StatusCode);

        await using var db = factory.CreateDbContext();
        Assert.Equal(IdentityVerificationState.Pending,
            (await db.VerificationChallenges.FindAsync(challengeId))!.State);
    }
}

// ── Provider-Subject Binding Tests ────────────────────────────────────────────

public sealed class IdentityProviderSubjectBindingTests
{
    [Fact]
    public async Task F2_GoogleRegistration_BindsProviderLabel()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory,
            subject: "google-sub", identityProvider: "google",
            email: "g@example.com", emailVerified: true);

        var result = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var json = JsonSerializer.SerializeToElement(result.Value);

        Assert.Equal("GOOGLE", json.GetProperty("AuthenticationPath").GetString());
        Assert.True(json.GetProperty("EmailVerified").GetBoolean());
    }

    [Fact]
    public async Task F2_CredentialRegistration_NoProviderLabel()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        // No identity_provider claim → CREDENTIAL path
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "cred-sub");

        var result = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var json = JsonSerializer.SerializeToElement(result.Value);

        Assert.Equal("CREDENTIAL", json.GetProperty("AuthenticationPath").GetString());
    }

    [Fact]
    public async Task F2_TenantIdNeverAcceptedFromRequest_UsesJwtClaimOnly()
    {
        // The registration request body must not contain tenantId
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "tenant-sub", identityProvider: "google");

        var result = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var json = result.Value!.GetType().GetProperties();

        // Ensure no tenant_id property exists in the registration response
        Assert.DoesNotContain(json, p => p.Name.ToLowerInvariant().Contains("tenantid"));
    }

    [Fact]
    public async Task F2_SameSubjectFromDifferentIssuers_CreatesDistinctBindings()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var idempotencyKey = Guid.NewGuid().ToString();
        var first = IdentityTestHelpers.CreateController(factory, subject: "shared-subject", providerIssuer: "issuer-a");
        first.Request.Headers["Idempotency-Key"] = idempotencyKey;
        var second = IdentityTestHelpers.CreateController(factory, subject: "shared-subject", providerIssuer: "issuer-b");
        second.Request.Headers["Idempotency-Key"] = idempotencyKey;

        Assert.Equal(201, Assert.IsType<ObjectResult>(await first.StartRegistrationAsync(new("en"), CancellationToken.None)).StatusCode);
        Assert.Equal(201, Assert.IsType<ObjectResult>(await second.StartRegistrationAsync(new("en"), CancellationToken.None)).StatusCode);

        await using var db = factory.CreateDbContext();
        var registrations = await db.Registrations.OrderBy(value => value.ProviderIssuer).ToListAsync();
        Assert.Equal(["issuer-a", "issuer-b"], registrations.Select(value => value.ProviderIssuer));
        Assert.NotEqual(registrations[0].ActorSubject, registrations[1].ActorSubject);
    }

    [Fact]
    public async Task F2_GoogleVerifiedEmail_NextActionIsCompleteProfile()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, identityProvider: "google", emailVerified: true);
        var result = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationAsync(new("en"), CancellationToken.None));
        Assert.Equal("COMPLETE_PROFILE", JsonSerializer.SerializeToElement(result.Value).GetProperty("NextAction").GetString());
    }
}

// ── Email Masking / Privacy Tests ─────────────────────────────────────────────

public sealed class IdentityPrivacyTests
{
    [Theory]
    [InlineData("user@example.com", "u***@example.com")]
    [InlineData("ab@domain.org", "a***@domain.org")]
    public void F2_MaskEmail_MasksLocalPart(string email, string expected)
    {
        Assert.Equal(expected, IdentityService.MaskEmail(email));
    }

    [Fact]
    public void F2_MaskMobile_MasksMiddle()
    {
        var masked = IdentityService.MaskMobile("+911234567890");
        Assert.Contains("***", masked);
        Assert.DoesNotContain("12345678", masked);
    }

    [Fact]
    public async Task F2_StartEmailVerification_NeverExposesRawEmail()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "priv-sub", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.StartEmailVerificationAsync(regId,
            new StartEmailVerificationRequest("secret@example.com"), CancellationToken.None);

        var responseBody = JsonSerializer.Serialize(result);
        Assert.DoesNotContain("secret@example.com", responseBody);
        Assert.DoesNotContain("secret", responseBody.ToLowerInvariant().Replace("emailverified", ""));
    }

    [Fact]
    public async Task F2_Registration_ResponseNeverContainsHmacKeys()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "hmac-sub",
            identityProvider: "google", email: "h@example.com", emailVerified: true);

        var result = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var json = JsonSerializer.Serialize(result.Value);

        Assert.DoesNotContain("hmac", json.ToLowerInvariant());
        Assert.DoesNotContain("emailHmacKey", json);
        Assert.DoesNotContain("mobileHmacKey", json);
    }
}

// ── WhatsApp Boundary Tests ───────────────────────────────────────────────────

public sealed class IdentityWhatsAppBoundaryTests
{
    [Fact]
    public async Task F2_StartRegistration_WhatsApp_Returns403ActionDenied()
    {
        // WhatsApp registration must only come through internal server-to-server adapter,
        // never through the browser endpoint.
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        // Simulate a WhatsApp "provider" claim (e.g. someone trying to inject it)
        // The service blocks it regardless of how authPath resolves in the controller.
        // Since the controller derives from identity_provider claim and none maps to WhatsApp,
        // we test the service directly with the WhatsApp path.
        var service = IdentityTestHelpers.CreateService(factory);
        var ex = await Assert.ThrowsAsync<IdentityActionDeniedException>(() =>
            service.StartRegistrationAsync(
                "wa-sub", Guid.NewGuid(), "hash", "en",
                IdentityAuthenticationPath.WhatsApp,
            null, null, false, null, null,
                CancellationToken.None));
        Assert.Contains("WhatsApp", ex.Message);
    }
}

public sealed class IdentityInputAndConfigurationTests
{
    [Fact]
    public async Task F2_InvalidLocaleEmailAndMobile_Return400()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory);
        Assert.Equal(400, Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new("english"), CancellationToken.None)).StatusCode);

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var created = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationAsync(new("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();
        Assert.Equal(400, Assert.IsType<ObjectResult>(await ctrl.StartEmailVerificationAsync(
            regId, new("not-an-email"), CancellationToken.None)).StatusCode);
        Assert.Equal(400, Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("12345"), CancellationToken.None)).StatusCode);
    }

    [Fact]
    public void F2_MissingOrShortHmacSecret_FailsClosed()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        Assert.Throws<InvalidOperationException>(() => new IdentityService(
            factory,
            Options.Create(new IdentityHmacOptions { Key = "short" }),
            new CapturingVerificationDispatcher()));
    }

    [Fact]
    public async Task F2_UnconfiguredDelivery_Returns503WithoutSuccessfulIdempotencyRecord()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateControllerWithDispatcher(
            factory, new FailingVerificationDispatcher(), subject: "delivery-failure");
        var created = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationAsync(new("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = Assert.IsType<ObjectResult>(await ctrl.StartEmailVerificationAsync(
            regId, new("person@example.com"), CancellationToken.None));
        Assert.Equal(503, result.StatusCode);

        await using var db = factory.CreateDbContext();
        Assert.Empty(await db.IdempotencyLedger.Where(value =>
            value.OperationFamily == "StartEmailVerification").ToListAsync());
        Assert.Equal(IdentityVerificationState.Expired,
            (await db.VerificationChallenges.SingleAsync()).State);
    }
}

// ── Update Profile Error Tests ────────────────────────────────────────────────

public sealed class IdentityUpdateProfileErrorTests
{
    [Theory]
    [InlineData("", "Business", "Retail", "en")]
    [InlineData("Name", "", "Retail", "en")]
    [InlineData("Name", "Business", "", "en")]
    [InlineData("Name", "Business", "Retail", "EN_us")]
    public async Task F2_UpdateProfile_InvalidFields_Return400(
        string displayName, string businessName, string businessDomain, string languagePreference)
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "upd-invalid");

        var result = await ctrl.UpdateProfileAsync(Guid.NewGuid(),
            new UpdateRegistrationProfileRequest(displayName, businessName, businessDomain, languagePreference),
            CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(400, obj.StatusCode);
        Assert.Equal("IDENTITY_REQUEST_INVALID",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_UpdateProfile_NotFound_Returns404()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "upd-notfound");

        var result = await ctrl.UpdateProfileAsync(Guid.NewGuid(),
            new UpdateRegistrationProfileRequest("N", "B", "D", "en"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_UpdateProfile_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "upd-idem", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        // First call with BodyA
        await ctrl.UpdateProfileAsync(regId,
            new UpdateRegistrationProfileRequest("Alice", "AcmeA", "RetailA", "en"), CancellationToken.None);

        // Same idempotency key, different body → conflict
        var conflict = await ctrl.UpdateProfileAsync(regId,
            new UpdateRegistrationProfileRequest("Bob", "AcmeB", "RetailB", "fr"), CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_UpdateProfile_BadIdempotencyKey_Returns400()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "upd-badkey", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        ctrl.Request.Headers["Idempotency-Key"] = "not-a-guid";
        var result = await ctrl.UpdateProfileAsync(regId,
            new UpdateRegistrationProfileRequest("N", "B", "D", "en"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(400, obj.StatusCode);
        Assert.Equal("IDENTITY_REQUEST_INVALID",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }
}

// ── Email Verification Additional Error Tests ─────────────────────────────────

public sealed class IdentityEmailVerificationAdditionalTests
{
    [Fact]
    public async Task F2_StartEmailVerification_UnknownRegistration_Returns404()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "ev-notfound");

        var result = await ctrl.StartEmailVerificationAsync(Guid.NewGuid(),
            new StartEmailVerificationRequest("test@example.com"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartEmailVerification_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "ev-idem", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        // First call with one email
        await ctrl.StartEmailVerificationAsync(regId, new("first@example.com"), CancellationToken.None);

        // Same key, different email → conflict
        var conflict = await ctrl.StartEmailVerificationAsync(regId, new("second@example.com"), CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartEmailVerification_Replay_ReturnsSameChallenge()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "ev-replay", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var first = Assert.IsType<ObjectResult>(
            await ctrl.StartEmailVerificationAsync(regId, new("replay@example.com"), CancellationToken.None));
        var firstId = JsonSerializer.SerializeToElement(first.Value).GetProperty("ChallengeId").GetGuid();

        // Same idempotency key + same email → replay (same challenge id)
        var replay = Assert.IsType<ObjectResult>(
            await ctrl.StartEmailVerificationAsync(regId, new("replay@example.com"), CancellationToken.None));
        var replayId = JsonSerializer.SerializeToElement(replay.Value).GetProperty("ChallengeId").GetGuid();

        Assert.Equal(firstId, replayId);
        Assert.Equal(202, replay.StatusCode);
    }

    [Fact]
    public async Task F2_StartEmailVerification_BadIdempotencyKey_Returns400()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "ev-badkey", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        ctrl.Request.Headers["Idempotency-Key"] = "not-a-guid";
        var result = await ctrl.StartEmailVerificationAsync(regId, new("t@example.com"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(400, obj.StatusCode);
        Assert.Equal("IDENTITY_REQUEST_INVALID",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmEmailVerification_InvalidCodeFormat_Returns400()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "cev-badcode", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        // 5-digit code fails the 6-digit regex check
        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmEmailVerificationAsync(regId,
            new ConfirmVerificationRequest(Guid.NewGuid(), "12345"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(400, obj.StatusCode);
        Assert.Equal("IDENTITY_REQUEST_INVALID",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmEmailVerification_UnknownChallenge_Returns404()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "cev-nochal", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        // Unknown challengeId (not in DB)
        var result = await ctrl.ConfirmEmailVerificationAsync(regId,
            new ConfirmVerificationRequest(Guid.NewGuid(), "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmEmailVerification_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "cev-idem", identityProvider: "google",
            dispatcher: dispatcher);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var started = Assert.IsType<ObjectResult>(
            await ctrl.StartEmailVerificationAsync(regId, new("cev@example.com"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        // First confirm succeeds
        await ctrl.ConfirmEmailVerificationAsync(regId, new(challengeId, dispatcher.LatestCode!), CancellationToken.None);

        // Same idempotency key, different code → conflict
        var conflict = await ctrl.ConfirmEmailVerificationAsync(regId,
            new(challengeId, "999999"), CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmEmailVerification_TimeBasedExpiry_Returns410()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "cev-texp", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var started = Assert.IsType<ObjectResult>(
            await ctrl.StartEmailVerificationAsync(regId, new("texp@example.com"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        // Set ExpiresAt to past while leaving State = Pending (different from the state-based expiry test)
        await using (var db = factory.CreateDbContext())
        {
            var ch = await db.VerificationChallenges.FindAsync(challengeId);
            db.Entry(ch!).Property(c => c.ExpiresAt).CurrentValue = DateTimeOffset.UtcNow.AddHours(-1);
            await db.SaveChangesAsync();
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmEmailVerificationAsync(regId,
            new ConfirmVerificationRequest(challengeId, "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(410, obj.StatusCode);
        Assert.Equal("IDENTITY_CHALLENGE_EXPIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());

        // Challenge state must have been set to Expired by the time-check branch
        await using var db2 = factory.CreateDbContext();
        Assert.Equal(IdentityVerificationState.Expired,
            (await db2.VerificationChallenges.FindAsync(challengeId))!.State);
    }
}

// ── Registration Mobile Verification Tests ────────────────────────────────────

public sealed class IdentityRegistrationMobileVerificationTests
{
    private static async Task<(IdentityController ctrl, Guid regId)> CreateRegistrationAsync(
        InMemoryIdentityDbContextFactory factory,
        string subject,
        CapturingVerificationDispatcher? dispatcher = null)
    {
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: subject,
            identityProvider: "google", dispatcher: dispatcher);
        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();
        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        return (ctrl, regId);
    }

    [Fact]
    public async Task F2_StartRegistrationMobileVerification_UnknownRegistration_Returns404()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "rmv-notfound");

        var result = await ctrl.StartRegistrationMobileVerificationAsync(Guid.NewGuid(),
            new StartMobileVerificationRequest("+911234567890"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartRegistrationMobileVerification_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "rmv-idem");

        // First call with +91 number
        await ctrl.StartRegistrationMobileVerificationAsync(regId,
            new StartMobileVerificationRequest("+911234567890"), CancellationToken.None);

        // Same key, different mobile → conflict
        var conflict = await ctrl.StartRegistrationMobileVerificationAsync(regId,
            new StartMobileVerificationRequest("+911234567891"), CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartRegistrationMobileVerification_Replay_ReturnsSameChallenge()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "rmv-replay");

        // First call
        var first = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("+911234567890"), CancellationToken.None));
        var firstId = JsonSerializer.SerializeToElement(first.Value).GetProperty("ChallengeId").GetGuid();

        // Same key + same mobile → replay
        var replay = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("+911234567890"), CancellationToken.None));
        Assert.Equal(firstId, JsonSerializer.SerializeToElement(replay.Value).GetProperty("ChallengeId").GetGuid());
        Assert.Equal(202, replay.StatusCode);
    }

    [Fact]
    public async Task F2_StartRegistrationMobileVerification_DeliveryFailure_Returns503()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        // Registration itself never dispatches, so FailingVerificationDispatcher is safe here
        var ctrl = IdentityTestHelpers.CreateControllerWithDispatcher(factory,
            new FailingVerificationDispatcher(), subject: "rmv-delivery", identityProvider: "google");
        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.StartRegistrationMobileVerificationAsync(regId,
            new StartMobileVerificationRequest("+911234567890"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(503, obj.StatusCode);
        Assert.Equal("IDENTITY_DEPENDENCY_UNAVAILABLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmRegistrationMobileVerification_InvalidCodeFormat_Returns400()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "crmv-badcode");

        // 5-digit code is invalid
        var result = await ctrl.ConfirmRegistrationMobileVerificationAsync(Guid.NewGuid(),
            new ConfirmVerificationRequest(Guid.NewGuid(), "12345"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(400, obj.StatusCode);
        Assert.Equal("IDENTITY_REQUEST_INVALID",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmRegistrationMobileVerification_ValidCode_ReturnsRegistrationResponse()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "crmv-success", dispatcher);

        var started = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var confirmed = Assert.IsType<OkObjectResult>(await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(challengeId, dispatcher.LatestCode!), CancellationToken.None));

        // The response must be IdentityRegistrationResponse shape (has RegistrationId, MobileVerified, etc.)
        var json = JsonSerializer.SerializeToElement(confirmed.Value);
        Assert.True(json.GetProperty("MobileVerified").GetBoolean());
        Assert.Equal(regId, json.GetProperty("RegistrationId").GetGuid());
        Assert.DoesNotContain("+911234567890", json.ToString());
    }

    [Fact]
    public async Task F2_ConfirmRegistrationMobileVerification_Replay_ReturnsSameRegistration()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "crmv-replay", dispatcher);

        var started = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var idemKey = ctrl.Request.Headers["Idempotency-Key"].ToString();

        // First confirm
        var first = Assert.IsType<OkObjectResult>(await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(challengeId, dispatcher.LatestCode!), CancellationToken.None));
        var firstReg = JsonSerializer.SerializeToElement(first.Value).GetProperty("RegistrationId").GetGuid();

        // Replay with same idempotency key
        ctrl.Request.Headers["Idempotency-Key"] = idemKey;
        var replay = Assert.IsType<OkObjectResult>(await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(challengeId, dispatcher.LatestCode!), CancellationToken.None));
        var replayReg = JsonSerializer.SerializeToElement(replay.Value).GetProperty("RegistrationId").GetGuid();

        Assert.Equal(firstReg, replayReg);
    }

    [Fact]
    public async Task F2_ConfirmRegistrationMobileVerification_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "crmv-idem", dispatcher);

        var started = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        // First confirm with correct code
        await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(challengeId, dispatcher.LatestCode!), CancellationToken.None);

        // Same key, different code → hash differs → conflict
        var conflict = await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(challengeId, "999999"), CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmRegistrationMobileVerification_ExpiredByState_Returns410()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "crmv-stateexp");

        var started = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        await using (var db = factory.CreateDbContext())
        {
            var ch = await db.VerificationChallenges.FindAsync(challengeId);
            ch!.State = IdentityVerificationState.Expired;
            await db.SaveChangesAsync();
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(challengeId, "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(410, obj.StatusCode);
        Assert.Equal("IDENTITY_CHALLENGE_EXPIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmRegistrationMobileVerification_TimeExpired_Returns410()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "crmv-timeexp");

        var started = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        // Keep State = Pending but put ExpiresAt in the past
        await using (var db = factory.CreateDbContext())
        {
            var ch = await db.VerificationChallenges.FindAsync(challengeId);
            db.Entry(ch!).Property(c => c.ExpiresAt).CurrentValue = DateTimeOffset.UtcNow.AddHours(-1);
            await db.SaveChangesAsync();
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(challengeId, "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(410, obj.StatusCode);
        Assert.Equal("IDENTITY_CHALLENGE_EXPIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmRegistrationMobileVerification_WrongCode_Returns403()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "crmv-wrongcode", dispatcher);

        var started = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var denied = Assert.IsType<ObjectResult>(await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(challengeId, "000000"), CancellationToken.None));

        Assert.Equal(403, denied.StatusCode);
        Assert.NotEqual("000000", dispatcher.LatestCode);
    }

    [Fact]
    public async Task F2_ConfirmRegistrationMobileVerification_UnknownChallenge_Returns404()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "crmv-nochal");

        // Unknown challengeId (not in DB)
        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(Guid.NewGuid(), "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }
}

// ── Account Mobile Error Tests ────────────────────────────────────────────────

public sealed class IdentityAccountMobileErrorTests
{
    [Fact]
    public async Task F2_StartAccountMobileVerification_InvalidMobileFormat_Returns400()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "amv-badmob");

        // Missing + prefix → invalid E.164
        var result = await ctrl.StartAccountMobileVerificationAsync(
            new StartMobileVerificationRequest("12345"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(400, obj.StatusCode);
        Assert.Equal("IDENTITY_REQUEST_INVALID",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartAccountMobileVerification_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "amv-idem");

        // First call
        await ctrl.StartAccountMobileVerificationAsync(
            new StartMobileVerificationRequest("+911234567890"), CancellationToken.None);

        // Same key, different mobile → conflict
        var conflict = await ctrl.StartAccountMobileVerificationAsync(
            new StartMobileVerificationRequest("+911234567891"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartAccountMobileVerification_DeliveryFailure_Returns503()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateControllerWithDispatcher(factory,
            new FailingVerificationDispatcher(), subject: "amv-delivery");

        var result = await ctrl.StartAccountMobileVerificationAsync(
            new StartMobileVerificationRequest("+911234567890"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(503, obj.StatusCode);
        Assert.Equal("IDENTITY_DEPENDENCY_UNAVAILABLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmAccountMobileVerification_InvalidCodeFormat_Returns400()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "camv-badcode");

        // 5-digit code is invalid format
        var result = await ctrl.ConfirmAccountMobileVerificationAsync(
            new ConfirmVerificationRequest(Guid.NewGuid(), "12345"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(400, obj.StatusCode);
        Assert.Equal("IDENTITY_REQUEST_INVALID",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmAccountMobileVerification_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "camv-idem", dispatcher: dispatcher);

        var started = Assert.IsType<ObjectResult>(await ctrl.StartAccountMobileVerificationAsync(
            new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        // First confirm succeeds
        await ctrl.ConfirmAccountMobileVerificationAsync(
            new(challengeId, dispatcher.LatestCode!), CancellationToken.None);

        // Same key, different code → conflict
        var conflict = await ctrl.ConfirmAccountMobileVerificationAsync(
            new(challengeId, "999999"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmAccountMobileVerification_ExpiredByState_Returns410()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "camv-stateexp");

        var started = Assert.IsType<ObjectResult>(await ctrl.StartAccountMobileVerificationAsync(
            new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        await using (var db = factory.CreateDbContext())
        {
            var ch = await db.VerificationChallenges.FindAsync(challengeId);
            ch!.State = IdentityVerificationState.Expired;
            await db.SaveChangesAsync();
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmAccountMobileVerificationAsync(
            new(challengeId, "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(410, obj.StatusCode);
        Assert.Equal("IDENTITY_CHALLENGE_EXPIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmAccountMobileVerification_TimeExpired_Returns410()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "camv-timeexp");

        var started = Assert.IsType<ObjectResult>(await ctrl.StartAccountMobileVerificationAsync(
            new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        // State stays Pending, ExpiresAt set to past
        await using (var db = factory.CreateDbContext())
        {
            var ch = await db.VerificationChallenges.FindAsync(challengeId);
            db.Entry(ch!).Property(c => c.ExpiresAt).CurrentValue = DateTimeOffset.UtcNow.AddHours(-1);
            await db.SaveChangesAsync();
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmAccountMobileVerificationAsync(
            new(challengeId, "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(410, obj.StatusCode);
        Assert.Equal("IDENTITY_CHALLENGE_EXPIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmAccountMobileVerification_UnknownChallenge_Returns404()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "camv-nochal");

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        // Unknown challengeId (not in DB)
        var result = await ctrl.ConfirmAccountMobileVerificationAsync(
            new(Guid.NewGuid(), "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }
}

// ── Complete Registration Error Tests ─────────────────────────────────────────

public sealed class IdentityCompleteRegistrationErrorTests
{
    [Fact]
    public async Task F2_CompleteRegistration_UnknownRegistration_Returns404()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "comp-notfound");

        var result = await ctrl.CompleteRegistrationAsync(Guid.NewGuid(), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_CompleteRegistration_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "comp-idem",
            identityProvider: "google", email: "comp@example.com", emailVerified: true);

        // Create two registrations for the same subject (different idempotency keys)
        var created1 = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var reg1Id = JsonSerializer.SerializeToElement(created1.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var created2 = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("fr"), CancellationToken.None));
        var reg2Id = JsonSerializer.SerializeToElement(created2.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        await ctrl.UpdateProfileAsync(reg1Id,
            new UpdateRegistrationProfileRequest("Name", "Co", "Domain", "en"), CancellationToken.None);

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        await ctrl.UpdateProfileAsync(reg2Id,
            new UpdateRegistrationProfileRequest("Name", "Co", "Domain", "en"), CancellationToken.None);

        // Complete reg1 with idempotency key K → records hash(reg1Id)
        var completeKey = Guid.NewGuid().ToString();
        ctrl.Request.Headers["Idempotency-Key"] = completeKey;
        await ctrl.CompleteRegistrationAsync(reg1Id, CancellationToken.None);

        // Same key K, different registrationId → hash(reg2Id) ≠ hash(reg1Id) → conflict
        ctrl.Request.Headers["Idempotency-Key"] = completeKey;
        var conflict = await ctrl.CompleteRegistrationAsync(reg2Id, CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_CompleteRegistration_WithEmailButMissingProfile_Returns422()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        // Email is verified by claim but profile fields (DisplayName etc.) not set
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "comp-noprofile",
            identityProvider: "google", email: "np@example.com", emailVerified: true);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        // Skip UpdateProfile — DisplayName/BusinessName/BusinessDomain are null
        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.CompleteRegistrationAsync(regId, CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(422, obj.StatusCode);
        Assert.Equal("IDENTITY_VERIFICATION_REQUIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }
}

// ── Account Link Full Flow Tests ──────────────────────────────────────────────

public sealed class IdentityAccountLinkFullFlowTests
{
    private static long FreshAuthTs => DateTimeOffset.UtcNow.AddMinutes(-1).ToUnixTimeSeconds();
    private static long StaleAuthTs => DateTimeOffset.UtcNow.AddMinutes(-10).ToUnixTimeSeconds();

    [Fact]
    public async Task F2_StartAccountLink_NoTenant_Returns401()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        // No tenantId in context
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "link-notenant",
            authTimestamp: FreshAuthTs);

        var result = await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(401, obj.StatusCode);
        Assert.Equal("IDENTITY_SESSION_REQUIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartAccountLink_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "link-idem",
            tenantId: Guid.NewGuid().ToString(), authTimestamp: FreshAuthTs);

        // First call with proofId A
        await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None);

        // Same key, different proofId → conflict
        var conflict = await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartAccountLink_Replay_ReturnsSameLink()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "link-replay",
            tenantId: Guid.NewGuid().ToString(), authTimestamp: FreshAuthTs);

        var proofId = Guid.NewGuid();
        var first = Assert.IsType<ObjectResult>(
            await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(proofId), CancellationToken.None));
        var firstLinkId = JsonSerializer.SerializeToElement(first.Value).GetProperty("LinkId").GetGuid();

        // Same key + same proofId → replay
        var replay = Assert.IsType<OkObjectResult>(
            await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(proofId), CancellationToken.None));
        var replayLinkId = JsonSerializer.SerializeToElement(replay.Value).GetProperty("LinkId").GetGuid();

        Assert.Equal(firstLinkId, replayLinkId);
    }

    [Fact]
    public async Task F2_ApproveAccountLink_NoTenant_Returns401()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        // No tenantId
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "approve-notenant",
            authTimestamp: FreshAuthTs);

        var result = await ctrl.ApproveAccountLinkAsync(Guid.NewGuid(), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(401, obj.StatusCode);
        Assert.Equal("IDENTITY_SESSION_REQUIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ApproveAccountLink_FreshSession_Returns200WithPendingState()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var tenantId = Guid.NewGuid().ToString();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "approve-ok",
            tenantId: tenantId, authTimestamp: FreshAuthTs);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));
        var linkId = JsonSerializer.SerializeToElement(created.Value).GetProperty("LinkId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var approved = Assert.IsType<OkObjectResult>(
            await ctrl.ApproveAccountLinkAsync(linkId, CancellationToken.None));

        var json = JsonSerializer.SerializeToElement(approved.Value);
        Assert.Equal("PENDING_WHATSAPP_CONFIRMATION", json.GetProperty("State").GetString());
        Assert.Equal(linkId, json.GetProperty("LinkId").GetGuid());
    }

    [Fact]
    public async Task F2_ApproveAccountLink_StaleSession_Returns403()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var tenantId = Guid.NewGuid().ToString();
        // Create link with fresh session
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "approve-stale",
            tenantId: tenantId, authTimestamp: FreshAuthTs);
        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));
        var linkId = JsonSerializer.SerializeToElement(created.Value).GetProperty("LinkId").GetGuid();

        // Approve with stale session (different controller, same subject/tenant but stale auth_time)
        var staleCtrl = IdentityTestHelpers.CreateController(factory, subject: "approve-stale",
            tenantId: tenantId, authTimestamp: StaleAuthTs);

        var result = await staleCtrl.ApproveAccountLinkAsync(linkId, CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(403, obj.StatusCode);
        Assert.Equal("IDENTITY_STEP_UP_REQUIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ApproveAccountLink_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var tenantId = Guid.NewGuid().ToString();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "approve-idem",
            tenantId: tenantId, authTimestamp: FreshAuthTs);

        // Create two links
        var link1 = Assert.IsType<ObjectResult>(
            await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));
        var link1Id = JsonSerializer.SerializeToElement(link1.Value).GetProperty("LinkId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var link2 = Assert.IsType<ObjectResult>(
            await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));
        var link2Id = JsonSerializer.SerializeToElement(link2.Value).GetProperty("LinkId").GetGuid();

        // Approve link1 with key K
        var approveKey = Guid.NewGuid().ToString();
        ctrl.Request.Headers["Idempotency-Key"] = approveKey;
        await ctrl.ApproveAccountLinkAsync(link1Id, CancellationToken.None);

        // Same key K, but different linkId → hash(link2Id) ≠ hash(link1Id) → conflict
        ctrl.Request.Headers["Idempotency-Key"] = approveKey;
        var conflict = await ctrl.ApproveAccountLinkAsync(link2Id, CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ApproveAccountLink_CrossTenant_Returns404()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var tenantA = Guid.NewGuid().ToString();
        var tenantB = Guid.NewGuid().ToString();

        var ctrlA = IdentityTestHelpers.CreateController(factory, subject: "approve-ct",
            tenantId: tenantA, authTimestamp: FreshAuthTs);
        var created = Assert.IsType<ObjectResult>(
            await ctrlA.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));
        var linkId = JsonSerializer.SerializeToElement(created.Value).GetProperty("LinkId").GetGuid();

        // Try to approve with tenantB context
        var ctrlB = IdentityTestHelpers.CreateController(factory, subject: "approve-ct",
            tenantId: tenantB, authTimestamp: FreshAuthTs);

        var result = await ctrlB.ApproveAccountLinkAsync(linkId, CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ApproveAccountLink_ExpiredLink_Returns410()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var tenantId = Guid.NewGuid().ToString();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "approve-exp",
            tenantId: tenantId, authTimestamp: FreshAuthTs);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));
        var linkId = JsonSerializer.SerializeToElement(created.Value).GetProperty("LinkId").GetGuid();

        // Expire the link directly
        await using (var db = factory.CreateDbContext())
        {
            var link = await db.AccountLinks.FindAsync(linkId);
            db.Entry(link!).Property(l => l.ExpiresAt).CurrentValue = DateTimeOffset.UtcNow.AddHours(-1);
            await db.SaveChangesAsync();
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ApproveAccountLinkAsync(linkId, CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(410, obj.StatusCode);
        Assert.Equal("IDENTITY_CHALLENGE_EXPIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());

        // State must have been set to Expired
        await using var db2 = factory.CreateDbContext();
        Assert.Equal(IdentityAccountLinkState.Expired, (await db2.AccountLinks.FindAsync(linkId))!.State);
    }

    [Fact]
    public async Task F2_GetAccountLink_ExistingLink_Returns200()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var tenantId = Guid.NewGuid().ToString();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "getlink-ok",
            tenantId: tenantId, authTimestamp: FreshAuthTs);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));
        var linkId = JsonSerializer.SerializeToElement(created.Value).GetProperty("LinkId").GetGuid();

        var result = await ctrl.GetAccountLinkAsync(linkId, CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var json = JsonSerializer.SerializeToElement(ok.Value);
        Assert.Equal(linkId, json.GetProperty("LinkId").GetGuid());
        Assert.Equal("PENDING_PORTAL_APPROVAL", json.GetProperty("State").GetString());
    }
}

// ── Registration State Machine Coverage ──────────────────────────────────────

public sealed class IdentityRegistrationStateAdditionalTests
{
    [Fact]
    public async Task F2_CompletedRegistration_GetRegistration_NextActionIsContinueToDefaultTarget()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "state-comp",
            identityProvider: "google", email: "sc@example.com", emailVerified: true);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        await ctrl.UpdateProfileAsync(regId,
            new UpdateRegistrationProfileRequest("Name", "Co", "Domain", "en"), CancellationToken.None);

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        await ctrl.CompleteRegistrationAsync(regId, CancellationToken.None);

        // GetRegistration should now show Completed state and CONTINUE_TO_DEFAULT_TARGET
        var reg = Assert.IsType<OkObjectResult>(await ctrl.GetRegistrationAsync(regId, CancellationToken.None));
        var json = JsonSerializer.SerializeToElement(reg.Value);
        Assert.Equal("COMPLETED", json.GetProperty("State").GetString());
        Assert.Equal("CONTINUE_TO_DEFAULT_TARGET", json.GetProperty("NextAction").GetString());
    }

    [Fact]
    public async Task F2_NonMappedRegistrationState_NextActionIsNone()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "state-none",
            identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        // Directly set state to a value not covered by ComputeNextAction (e.g. Cancelled)
        await using (var db = factory.CreateDbContext())
        {
            var reg = await db.Registrations.FindAsync(regId);
            reg!.State = IdentityRegistrationState.Cancelled;
            await db.SaveChangesAsync();
        }

        var result = Assert.IsType<OkObjectResult>(await ctrl.GetRegistrationAsync(regId, CancellationToken.None));
        Assert.Equal("NONE", JsonSerializer.SerializeToElement(result.Value).GetProperty("NextAction").GetString());
    }
}

// ── Dispatcher and HMAC Edge Case Tests ──────────────────────────────────────

public sealed class IdentityEdgeCaseTests
{
    [Fact]
    public async Task F2_UnconfiguredDispatcher_MobileVerification_Returns503()
    {
        // UnconfiguredVerificationDispatcher is the fail-closed stand-in shipped with the service
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateControllerWithDispatcher(factory,
            new UnconfiguredVerificationDispatcher(), subject: "unconf-mob");

        var result = await ctrl.StartAccountMobileVerificationAsync(
            new StartMobileVerificationRequest("+911234567890"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(503, obj.StatusCode);
        Assert.Equal("IDENTITY_DEPENDENCY_UNAVAILABLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_MalformedCodeHmac_TreatedAsWrongCode_Returns403()
    {
        // If the stored HMAC is not valid hex, VerifyCode must safely return false (no exception)
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "malformed-hmac");

        var started = Assert.IsType<ObjectResult>(await ctrl.StartAccountMobileVerificationAsync(
            new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        // Corrupt the stored HMAC to a non-hex string
        await using (var db = factory.CreateDbContext())
        {
            var ch = await db.VerificationChallenges.FindAsync(challengeId);
            db.Entry(ch!).Property(c => c.CodeHmac).CurrentValue = "not-valid-hex!@#";
            await db.SaveChangesAsync();
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmAccountMobileVerificationAsync(
            new(challengeId, "123456"), CancellationToken.None);

        // Must return 403, NOT an unhandled exception
        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(403, obj.StatusCode);
        Assert.Equal("IDENTITY_ACTION_DENIED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartRegistration_BadIdempotencyKey_Returns400()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "reg-badkey");

        ctrl.Request.Headers["Idempotency-Key"] = "not-a-guid";
        var result = await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(400, obj.StatusCode);
        Assert.Equal("IDENTITY_REQUEST_INVALID",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }
}
