// Implements: architecture/reference/product/wc085-identity-architecture-decision.md First Discriminating Parent Check
// constitutional_basis: C-023, C-026, C-059

using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.TestHost;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Tokens;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class CustomerIdentityJourneyHttpPostgresTests : IAsyncLifetime
{
    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("synthetic_http_journey").WithUsername("test_owner")
        .WithPassword("synthetic-owner-password").Build();
    private readonly RSA _signer = RSA.Create(2048);
    private readonly GoogleWorkspaceProofAdapterTests.SyntheticKeycloakHandler _broker = new();
    private readonly IdentityBrokerReadOptions _configuration = GoogleWorkspaceProofAdapterTests.Configuration();
    private WebApplication _app = null!;
    private HttpClient _client = null!;
    private HttpClient _brokerClient = null!;
    private string AppConnection => new NpgsqlConnectionStringBuilder(_postgres.GetConnectionString())
    {
        Username = "business_app", Password = "synthetic-app-password", MaxPoolSize = 1,
    }.ConnectionString;

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        await OwnerAsync("""
            CREATE ROLE business_app LOGIN PASSWORD 'synthetic-app-password' NOSUPERUSER NOBYPASSRLS;
            CREATE ROLE constitutional_app LOGIN PASSWORD 'synthetic-app-password' NOSUPERUSER NOBYPASSRLS;
            CREATE ROLE runtime_app LOGIN PASSWORD 'synthetic-app-password' NOSUPERUSER NOBYPASSRLS;
            CREATE ROLE wbe_app LOGIN PASSWORD 'synthetic-app-password' NOSUPERUSER NOBYPASSRLS;
            CREATE SCHEMA business AUTHORIZATION business_app;
            """);
        var canonical = await File.ReadAllTextAsync(RepositoryPaths.Resolve("infrastructure/postgres/init/03-enums-and-tables.sql"));
        foreach (var table in new[] { "organisations", "business_domain_taxonomy" })
        {
            var start = canonical.IndexOf($"CREATE TABLE business.{table} (", StringComparison.Ordinal);
            var end = canonical.IndexOf(");", start, StringComparison.Ordinal) + 2;
            await OwnerAsync(canonical[start..end]);
        }
        await OwnerAsync(await File.ReadAllTextAsync(RepositoryPaths.Resolve("infrastructure/postgres/init/20-identity-boundary.sql")));
        await OwnerAsync("""
            GRANT ALL ON ALL TABLES IN SCHEMA business, identity TO business_app;
            GRANT SELECT ON ALL TABLES IN SCHEMA business TO constitutional_app, runtime_app, wbe_app;
            CREATE POLICY tenant_isolation ON business.organisations USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
            """);
        await OwnerAsync(await File.ReadAllTextAsync(RepositoryPaths.Resolve("infrastructure/postgres/init/29-customer-workspace-provisioning.sql")));

        var builder = WebApplication.CreateBuilder();
        builder.WebHost.UseTestServer();
        builder.Logging.ClearProviders();
        builder.Services.AddControllers().AddApplicationPart(typeof(IdentityController).Assembly);
        builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme).AddJwtBearer(options =>
        {
            options.MapInboundClaims = true;
            options.TokenValidationParameters = new TokenValidationParameters
            {
                ValidIssuer = _configuration.ActorIssuer, ValidAudience = "waooaw-platform",
                IssuerSigningKey = new RsaSecurityKey(_signer), ValidAlgorithms = [SecurityAlgorithms.RsaSha256],
                ValidateIssuer = true, ValidateAudience = true, ValidateLifetime = true,
                ValidateIssuerSigningKey = true, ClockSkew = TimeSpan.FromSeconds(30),
            };
        });
        builder.Services.AddAuthorization();
        builder.Services.AddDbContextFactory<IdentityDbContext>(options => options.UseNpgsql(AppConnection));
        builder.Services.Configure<IdentityHmacOptions>(options => options.Key = "synthetic-http-test-hmac-key-at-least-32-characters");
        builder.Services.AddSingleton<IIdentityVerificationDispatcher, UnconfiguredVerificationDispatcher>();
        builder.Services.AddScoped<IdentityService>();
        builder.Services.AddSingleton(Options.Create(new IdentityEnvironmentOptions
        {
            Providers = [
                new() { Id = "GOOGLE", DisplayName = "Google", AuthenticationPath = "GOOGLE",
                    Enabled = true, ReadinessEvidenceReference = "SYNTHETIC-TEST-ONLY" },
                new() { Id = "FACEBOOK", DisplayName = "Facebook", AuthenticationPath = "META",
                    Enabled = true, ReadinessEvidenceReference = "SYNTHETIC-TEST-ONLY" },
            ],
        }));
        builder.Services.AddSingleton<IdentityProviderProjectionService>();
        _brokerClient = new HttpClient(_broker);
        builder.Services.AddSingleton(new GoogleWorkspaceProofAdapter(_brokerClient, Options.Create(_configuration)));
        builder.Services.AddScoped<CustomerIdentityJourneyService>();
        _app = builder.Build();
        _app.UseRouting();
        _app.UseAuthentication();
        _app.UseAuthorization();
        _app.UseMiddleware<CustomerMembershipMiddleware>();
        _app.UseWhen(context => !context.Items.ContainsKey(CustomerMembershipMiddleware.JourneyItem),
            branch => branch.UseTenantIsolation());
        _app.MapControllers();
        await _app.StartAsync();
        _client = _app.GetTestClient();
    }

    public async Task DisposeAsync()
    {
        _client?.Dispose();
        if (_app is not null) await _app.DisposeAsync();
        _brokerClient?.Dispose();
        _signer.Dispose();
        await _postgres.DisposeAsync();
    }

    [Fact]
    public async Task Http_TwoTenantlessActors_CompleteDistinctWorkspaces_ThenOwnSessionAndCrossActorDenials()
    {
        var first = Token("actor-one");
        var second = Token("actor-two");
        var firstRegistration = await RegisterAsync(first);
        var secondRegistration = await RegisterAsync(second);
        var firstCompletion = await CompleteAsync(first, firstRegistration);
        var secondCompletion = await CompleteAsync(second, secondRegistration);
        var firstAccount = firstCompletion.GetProperty("accountReference").GetGuid();
        var secondAccount = secondCompletion.GetProperty("accountReference").GetGuid();
        Assert.NotEqual(firstAccount, secondAccount);
        foreach (var pair in new[] { (first, firstAccount), (second, secondAccount) })
        {
            var response = await SendAsync(HttpMethod.Get, "/api/v1/identity/session", pair.Item1);
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            var session = await JsonAsync(response);
            Assert.Equal(pair.Item2, session.GetProperty("accountReference").GetGuid());
            Assert.Equal("OWNER", session.GetProperty("roles")[0].GetString());
            Assert.Equal("AAL2_ACCOUNT", session.GetProperty("assuranceLevel").GetString());
            Assert.Empty(session.GetProperty("capabilities").EnumerateArray());
            Assert.True(response.Headers.CacheControl!.NoStore);
        }
        Assert.Equal(HttpStatusCode.NotFound, (await SendAsync(HttpMethod.Get,
            $"/api/v1/identity/registrations/{firstRegistration}", second)).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await SendAsync(HttpMethod.Put,
            $"/api/v1/identity/registrations/{firstRegistration}/profile", second, Profile())).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await SendAsync(HttpMethod.Post,
            $"/api/v1/identity/registrations/{firstRegistration}/complete", second)).StatusCode);
        Assert.Equal(2L, await OwnerScalarAsync("SELECT count(*) FROM business.organisations WHERE identity_managed AND id = tenant_id"));
        Assert.Equal(2L, await OwnerScalarAsync("SELECT count(DISTINCT tenant_id) FROM identity.memberships WHERE roles = ARRAY['OWNER']::text[]"));
        await AssertEmptyPoolAsync();
    }

    [Fact]
    public async Task Http_FacebookActor_CompletesRegistrationAndResolvesMembership()
    {
        _broker.Provider = "facebook";
        var token = Token("facebook-actor", provider: "facebook");

        var registration = await RegisterAsync(token);
        var completion = await CompleteAsync(token, registration);
        var session = await SendAsync(HttpMethod.Get, "/api/v1/identity/session", token);

        Assert.Equal(HttpStatusCode.OK, session.StatusCode);
        Assert.Equal(completion.GetProperty("accountReference").GetGuid(),
            (await JsonAsync(session)).GetProperty("accountReference").GetGuid());
        Assert.Equal(1L, await OwnerScalarAsync(
            "SELECT count(*) FROM identity.login_methods WHERE broker_alias = 'facebook'"));
        Assert.Equal(1L, await OwnerScalarAsync(
            "SELECT count(*) FROM identity.registrations WHERE provider_label = 'facebook'"));
        await AssertEmptyPoolAsync();
    }

    [Theory]
    [InlineData(null)]
    [InlineData("false")]
    public async Task Http_FacebookWithoutVerifiedEmail_DeniesBeforeRegistration(string? emailVerified)
    {
        _broker.Provider = "facebook";
        var token = Token("facebook-incomplete", provider: "facebook", emailVerified: emailVerified);

        var response = await SendAsync(HttpMethod.Post, "/api/v1/identity/registrations", token,
            new { languagePreference = "en" });

        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
        Assert.Empty(_broker.Requests);
        Assert.Equal(0L, await OwnerScalarAsync("SELECT count(*) FROM identity.registrations"));
        await AssertEmptyPoolAsync();
    }

    [Fact]
    public async Task Http_ForgedTenantClaimsNeverSelectMembership_AndForeignHeadersDeny()
    {
        var token = Token("actor-one");
        var registration = await RegisterAsync(token);
        var completed = await CompleteAsync(token, registration);
        var forged = Token("actor-one", extra: [new Claim("tenant_id", Guid.NewGuid().ToString()),
            new Claim("waooaw_roles", "[\"OWNER\",\"MANAGER\"]")]);
        var own = await SendAsync(HttpMethod.Get, "/api/v1/identity/session", forged);
        Assert.Equal(HttpStatusCode.OK, own.StatusCode);
        Assert.Equal(completed.GetProperty("accountReference").GetGuid(), (await JsonAsync(own)).GetProperty("accountReference").GetGuid());
        var foreign = await SendAsync(HttpMethod.Get, "/api/v1/identity/session", token,
            header: ("x-tenant-id", Guid.NewGuid().ToString()));
        Assert.Equal(HttpStatusCode.Forbidden, foreign.StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await SendAsync(HttpMethod.Get, "/api/v1/identity/session", token,
            header: ("x-account-id", Guid.NewGuid().ToString()))).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await SendAsync(HttpMethod.Post, "/api/v1/identity/registrations", token,
            new { languagePreference = "en" }, header: ("x-tenant-id", Guid.NewGuid().ToString()))).StatusCode);
        await AssertEmptyPoolAsync();
    }

    [Fact]
    public async Task Http_SameSubjectWrongIssuerAndForgedSignature_DenyAtBearerBoundary()
    {
        var registration = await RegisterAsync(Token("same-subject"));
        var wrongIssuer = Token("same-subject", issuer: "https://other.invalid/realms/waooaw");
        using var otherSigner = RSA.Create(2048);
        var forged = Token("same-subject", signer: otherSigner);
        foreach (var token in new[] { wrongIssuer, forged, "not-a-jwt" })
        {
            Assert.Equal(HttpStatusCode.Unauthorized, (await SendAsync(HttpMethod.Get,
                $"/api/v1/identity/registrations/{registration}", token)).StatusCode);
            Assert.Equal(HttpStatusCode.Unauthorized, (await SendAsync(HttpMethod.Post,
                $"/api/v1/identity/registrations/{registration}/complete", token)).StatusCode);
        }
        Assert.Empty(_broker.Requests);
        Assert.Equal(0L, await OwnerScalarAsync("SELECT count(*) FROM identity.accounts"));
    }

    [Fact]
    public async Task Http_AbsentConfiguration_DoesNotFallBackToLegacyCompletion()
    {
        _configuration.Enabled = false;
        var readiness = await SendAsync(HttpMethod.Get, "/api/v1/identity/providers", Token("actor"));
        Assert.Equal(HttpStatusCode.OK, readiness.StatusCode);
        Assert.Equal("UNAVAILABLE", (await JsonAsync(readiness)).GetProperty("providers")[0].GetProperty("availability").GetString());
        foreach (var request in new[] { (HttpMethod.Get, "/api/v1/identity/session"),
            (HttpMethod.Post, $"/api/v1/identity/registrations/{Guid.NewGuid()}/complete"),
            (HttpMethod.Post, "/api/v1/identity/registrations") })
        {
            var response = await SendAsync(request.Item1, request.Item2, Token("actor"), new { languagePreference = "en" });
            Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
            Assert.Equal("IDENTITY_DEPENDENCY_UNAVAILABLE", (await JsonAsync(response)).GetProperty("code").GetString());
        }
        Assert.Empty(_broker.Requests);
        Assert.Equal(0L, await OwnerScalarAsync("SELECT count(*) FROM identity.registrations"));
    }

    [Fact]
    public async Task Http_UnadaptedProtectedRoutes_DenyEvenWithForgedOwnerTenant()
    {
        var token = Token("actor", extra: [new Claim("tenant_id", Guid.NewGuid().ToString()), new Claim("waooaw_roles", "OWNER")]);
        foreach (var path in new[] { "/api/v1/identity/profile", "/api/v1/identity/settings",
            "/api/v1/identity/login-methods", "/api/v1/identity/mobile-verifications",
            "/api/v1/identity/account-links", "/api/v1/subscriptions", "/api/v1/identity/registrations/00000000-0000-0000-0000-000000000085/email-verifications" })
        {
            foreach (var method in new[] { HttpMethod.Get, HttpMethod.Put, HttpMethod.Post })
            {
                var response = await SendAsync(method, path, token, new { });
                Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
            }
        }
        Assert.Equal(0L, await OwnerScalarAsync("SELECT count(*) FROM identity.accounts"));
    }

    [Fact]
    public async Task Http_CompletionFailureRollsBack_ThenRetryAndParallelReplayKeepOneOutcome()
    {
        var token = Token("actor");
        var registration = await RegisterAsync(token);
        var key = Guid.NewGuid();
        var path = $"/api/v1/identity/registrations/{registration}/complete";
        await OwnerAsync("ALTER TABLE identity.idempotency_ledger ADD CONSTRAINT synthetic_commit_failure CHECK (operation_family <> 'CompleteRegistration')");
        Assert.Equal(HttpStatusCode.ServiceUnavailable, (await SendAsync(HttpMethod.Post, path, token, key: key)).StatusCode);
        Assert.Equal(0L, await OwnerScalarAsync("SELECT count(*) FROM identity.accounts"));
        Assert.Equal(0L, await OwnerScalarAsync("SELECT count(*) FROM identity.registration_events WHERE event_type = 'RegistrationCompleted'"));
        await AssertEmptyPoolAsync();
        await OwnerAsync("ALTER TABLE identity.idempotency_ledger DROP CONSTRAINT synthetic_commit_failure");
        var completed = await SendAsync(HttpMethod.Post, path, token, key: key);
        Assert.Equal(HttpStatusCode.OK, completed.StatusCode);
        var body = await completed.Content.ReadAsStringAsync();
        var retries = await Task.WhenAll(Enumerable.Range(0, 3).Select(_ => SendAsync(HttpMethod.Post, path, token, key: key)));
        foreach (var retry in retries)
        {
            Assert.Equal(HttpStatusCode.OK, retry.StatusCode);
            Assert.Equal(body, await retry.Content.ReadAsStringAsync());
        }
        var anotherRegistration = await RegisterAsync(token);
        var conflict = await SendAsync(HttpMethod.Post, $"/api/v1/identity/registrations/{anotherRegistration}/complete", token, key: key);
        Assert.Equal(HttpStatusCode.Conflict, conflict.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT", (await JsonAsync(conflict)).GetProperty("code").GetString());
        Assert.Equal(1L, await OwnerScalarAsync("SELECT count(*) FROM identity.accounts"));
        Assert.Equal(1L, await OwnerScalarAsync("SELECT count(*) FROM identity.idempotency_ledger WHERE operation_family = 'CompleteRegistration' AND length(canonical_hash) = 64"));
    }

    [Fact]
    public async Task Http_ReadPermissionFailureAndRevocation_FailClosed()
    {
        var token = Token("actor");
        var registration = await RegisterAsync(token);
        _broker.Status = HttpStatusCode.Forbidden;
        Assert.Equal(HttpStatusCode.ServiceUnavailable, (await SendAsync(HttpMethod.Post,
            $"/api/v1/identity/registrations/{registration}/complete", token)).StatusCode);
        Assert.Equal(0L, await OwnerScalarAsync("SELECT count(*) FROM identity.accounts"));
        _broker.Status = HttpStatusCode.OK;
        await CompleteAsync(token, registration);
        await OwnerAsync("UPDATE identity.memberships SET status = 'INACTIVE'");
        Assert.Equal(HttpStatusCode.Forbidden, (await SendAsync(HttpMethod.Get, "/api/v1/identity/session", token)).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await SendAsync(HttpMethod.Post,
            $"/api/v1/identity/registrations/{registration}/complete", token)).StatusCode);
        await AssertEmptyPoolAsync();
    }

    [Fact]
    public async Task Http_ProviderReadinessDisabled_DeniesDespiteConfiguredReader()
    {
        var environment = _app.Services.GetRequiredService<IOptions<IdentityEnvironmentOptions>>().Value;
        environment.Providers[0].Enabled = false;
        Assert.Equal(HttpStatusCode.ServiceUnavailable, (await SendAsync(HttpMethod.Post,
            "/api/v1/identity/registrations", Token("actor"), new { languagePreference = "en" })).StatusCode);
        Assert.Empty(_broker.Requests);
        Assert.Equal(0L, await OwnerScalarAsync("SELECT count(*) FROM identity.registrations"));
    }

    [Fact]
    public async Task Http_StartAndProfileIdempotency_BindRegistrationAndDoNotOverwrite()
    {
        var token = Token("actor");
        var key = Guid.NewGuid();
        var first = await SendAsync(HttpMethod.Post, "/api/v1/identity/registrations", token,
            new { languagePreference = "en" }, key);
        Assert.Equal(HttpStatusCode.Created, first.StatusCode);
        var registration = (await JsonAsync(first)).GetProperty("registrationId").GetGuid();
        var replay = await SendAsync(HttpMethod.Post, "/api/v1/identity/registrations", token,
            new { languagePreference = "en" }, key);
        Assert.Equal(HttpStatusCode.OK, replay.StatusCode);
        Assert.Equal(registration, (await JsonAsync(replay)).GetProperty("registrationId").GetGuid());
        Assert.Equal(HttpStatusCode.Conflict, (await SendAsync(HttpMethod.Post, "/api/v1/identity/registrations", token,
            new { languagePreference = "hi" }, key)).StatusCode);
        var profileKey = Guid.NewGuid();
        var path = $"/api/v1/identity/registrations/{registration}/profile";
        Assert.Equal(HttpStatusCode.OK, (await SendAsync(HttpMethod.Put, path, token, Profile(), profileKey)).StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await SendAsync(HttpMethod.Put, path, token, Profile(), profileKey)).StatusCode);
        var otherRegistration = await RegisterAsync(token);
        Assert.Equal(HttpStatusCode.Conflict, (await SendAsync(HttpMethod.Put,
            $"/api/v1/identity/registrations/{otherRegistration}/profile", token, Profile(), profileKey)).StatusCode);
        await CompleteAsync(token, registration);
        Assert.Equal(HttpStatusCode.Forbidden, (await SendAsync(HttpMethod.Put, path, token, Profile())).StatusCode);
        await AssertEmptyPoolAsync();
    }

    [Fact]
    public async Task Http_DatabaseResolverOutage_ReturnsUnavailableNotProtectedSession()
    {
        var token = Token("actor");
        await CompleteAsync(token, await RegisterAsync(token));
        await OwnerAsync("REVOKE EXECUTE ON FUNCTION identity.resolve_customer_membership() FROM business_app");
        Assert.Equal(HttpStatusCode.ServiceUnavailable, (await SendAsync(HttpMethod.Get, "/api/v1/identity/session", token)).StatusCode);
        await AssertEmptyPoolAsync();
    }

    private string Token(string subject, string? issuer = null, RSA? signer = null, Claim[]? extra = null,
        string provider = "google", string? emailVerified = "true")
    {
        var claims = GoogleWorkspaceProofAdapterTests.Principal(subject, provider: provider).Claims
            .Where(claim => claim.Type is not ("iss" or "aud" or "iat" or "exp" or "email_verified"))
            .Concat(emailVerified is null ? [] : [new Claim("email_verified", emailVerified)])
            .Concat(extra ?? []);
        var now = DateTime.UtcNow;
        var token = new JwtSecurityToken(issuer ?? _configuration.ActorIssuer, "waooaw-platform", claims,
            now.AddSeconds(-1), now.AddMinutes(10), new SigningCredentials(new RsaSecurityKey(signer ?? _signer), SecurityAlgorithms.RsaSha256));
        token.Payload["iat"] = new DateTimeOffset(now).ToUnixTimeSeconds();
        return new JwtSecurityTokenHandler().WriteToken(token);
    }

    private async Task<Guid> RegisterAsync(string token)
    {
        var started = await SendAsync(HttpMethod.Post, "/api/v1/identity/registrations", token, new { languagePreference = "en" });
        Assert.Equal(HttpStatusCode.Created, started.StatusCode);
        var registrationId = (await JsonAsync(started)).GetProperty("registrationId").GetGuid();
        var profile = await SendAsync(HttpMethod.Put, $"/api/v1/identity/registrations/{registrationId}/profile", token, Profile());
        Assert.Equal(HttpStatusCode.OK, profile.StatusCode);
        Assert.Equal("READY_TO_COMPLETE", (await JsonAsync(profile)).GetProperty("state").GetString());
        return registrationId;
    }

    private async Task<JsonElement> CompleteAsync(string token, Guid registrationId)
    {
        var response = await SendAsync(HttpMethod.Post, $"/api/v1/identity/registrations/{registrationId}/complete", token);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        return await JsonAsync(response);
    }

    private static object Profile() => new { displayName = "Synthetic Customer", businessName = "Synthetic Business",
        businessDomain = "Synthetic testing", languagePreference = "en" };

    private async Task<HttpResponseMessage> SendAsync(HttpMethod method, string path, string token,
        object? body = null, Guid? key = null, (string Name, string Value)? header = null)
    {
        using var request = new HttpRequestMessage(method, path);
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        request.Headers.Add("Idempotency-Key", (key ?? Guid.NewGuid()).ToString());
        if (header.HasValue) request.Headers.Add(header.Value.Name, header.Value.Value);
        if (body is not null) request.Content = JsonContent.Create(body);
        return await _client.SendAsync(request);
    }

    private static async Task<JsonElement> JsonAsync(HttpResponseMessage response) =>
        JsonSerializer.Deserialize<JsonElement>(await response.Content.ReadAsStringAsync());

    private async Task OwnerAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private async Task<long> OwnerScalarAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        return (long)(await command.ExecuteScalarAsync())!;
    }

    private async Task AssertEmptyPoolAsync()
    {
        await using var connection = new NpgsqlConnection(AppConnection);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand("""
            SELECT COALESCE(NULLIF(current_setting('app.identity_issuer', true), ''), 'EMPTY'),
                COALESCE(NULLIF(current_setting('app.identity_subject', true), ''), 'EMPTY'),
                COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), 'EMPTY'),
                COALESCE(NULLIF(current_setting('app.current_tenant_id', true), ''), 'EMPTY')
            """, connection);
        await using var reader = await command.ExecuteReaderAsync();
        Assert.True(await reader.ReadAsync());
        for (var index = 0; index < 4; index++) Assert.Equal("EMPTY", reader.GetString(index));
    }
}