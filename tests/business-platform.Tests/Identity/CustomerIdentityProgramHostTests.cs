using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Tokens;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class CustomerIdentityProgramHostTests : IAsyncLifetime
{
    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("synthetic_program_journey").WithUsername("test_owner")
        .WithPassword("synthetic-owner-password").Build();
    private readonly RSA _signer = RSA.Create(2048);
    private readonly GoogleWorkspaceProofAdapterTests.SyntheticKeycloakHandler _broker = new();
    private readonly IdentityBrokerReadOptions _configuration = GoogleWorkspaceProofAdapterTests.Configuration();
    private WebApplicationFactory<Program>? _baseFactory;
    private WebApplicationFactory<Program>? _factory;
    private HttpClient _client = null!;
    private SyntheticOidcHandler _oidc = null!;

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
        await OwnerAsync(await File.ReadAllTextAsync(RepositoryPaths.Resolve("infrastructure/postgres/init/19-ae01-employment-relationship.sql")));
        await OwnerAsync(await File.ReadAllTextAsync(RepositoryPaths.Resolve("infrastructure/postgres/init/25-agent-admission.sql")));
        await OwnerAsync(await File.ReadAllTextAsync(RepositoryPaths.Resolve("infrastructure/postgres/init/31-agent-instance-binding.sql")));
        var contextConfiguration = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve("infrastructure/postgres/init/20b-ae01-context-configuration.sql"));
        var goalsStart = contextConfiguration.IndexOf(
            "CREATE TABLE IF NOT EXISTS business.relationship_goals (", StringComparison.Ordinal);
        var goalsEnd = contextConfiguration.IndexOf(");", goalsStart, StringComparison.Ordinal) + 2;
        await OwnerAsync(contextConfiguration[goalsStart..goalsEnd]);
        await OwnerAsync("""
            ALTER TABLE business.relationship_goals ENABLE ROW LEVEL SECURITY;
            ALTER TABLE business.relationship_goals FORCE ROW LEVEL SECURITY;
            CREATE POLICY relationship_goals_tenant_isolation ON business.relationship_goals
                USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
                WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
            GRANT SELECT, INSERT, UPDATE ON business.relationship_goals TO business_app;
            """);
    }

    public async Task DisposeAsync()
    {
        _client?.Dispose();
        if (_factory is not null) await _factory.DisposeAsync();
        if (_baseFactory is not null) await _baseFactory.DisposeAsync();
        _signer.Dispose();
        await _postgres.DisposeAsync();
    }

    private void StartHost(bool brokerEnabled = true, bool googleEnabled = true)
    {
        _oidc = new SyntheticOidcHandler(_configuration.ActorIssuer, _signer);
        var settings = new Dictionary<string, string?>
        {
            ["ConnectionStrings:Identity"] = AppConnection,
            ["ConnectionStrings:DefaultConnection"] = AppConnection,
            ["Temporal:Host"] = "",
            ["WAOOAW_WORKLOAD_CREDENTIALS"] = "",
            ["Keycloak:Authority"] = _configuration.ActorIssuer,
            ["Keycloak:RequireHttpsMetadata"] = "true",
            ["IdentityEnvironment:Keycloak:Issuer"] = _configuration.ActorIssuer,
            ["IdentityEnvironment:Keycloak:JwksUri"] = _configuration.ActorIssuer + "/protocol/openid-connect/certs",
            ["Identity:Hmac:Key"] = "synthetic-program-test-hmac-key-at-least-32-characters",
            ["ChannelContinuity:EnvelopeHmacKey"] = Convert.ToBase64String(new byte[32]),
        };
        if (brokerEnabled)
        {
            settings["IdentityBrokerRead:Enabled"] = "true";
            settings["IdentityBrokerRead:ActorIssuer"] = _configuration.ActorIssuer;
            settings["IdentityBrokerRead:PrivateOrigin"] = _configuration.PrivateOrigin;
            settings["IdentityBrokerRead:AllowedPrivateHosts:0"] = _configuration.AllowedPrivateHosts[0];
            settings["IdentityBrokerRead:ClientId"] = _configuration.ClientId;
            settings["IdentityBrokerRead:ClientSecret"] = _configuration.ClientSecret;
            settings["IdentityBrokerRead:Providers:google:ProviderNamespace"] =
                _configuration.Providers["google"].ProviderNamespace;
            settings["IdentityBrokerRead:Providers:google:TrustConfigDigest"] =
                _configuration.Providers["google"].TrustConfigDigest;
        }
        if (googleEnabled)
        {
            settings["IdentityEnvironment:Providers:0:Enabled"] = "true";
            settings["IdentityEnvironment:Providers:0:UnavailableReason"] = "";
            settings["IdentityEnvironment:Providers:0:SecretReference"] = "kv://synthetic/google";
            settings["IdentityEnvironment:Providers:0:ReadinessEvidenceReference"] = "SYNTHETIC-PROGRAM-HOST-ONLY";
        }
        _baseFactory = new WebApplicationFactory<Program>();
        _factory = _baseFactory.WithWebHostBuilder(builder =>
        {
            builder.UseEnvironment("Production");
            foreach (var setting in settings) builder.UseSetting(setting.Key, setting.Value);
            builder.ConfigureTestServices(services =>
            {
                services.Configure<JwtBearerOptions>(JwtBearerDefaults.AuthenticationScheme,
                    options => options.Backchannel = new HttpClient(_oidc));
                services.AddHttpClient<GoogleWorkspaceProofAdapter>()
                    .ConfigurePrimaryHttpMessageHandler(() => _broker);
            });
        });
        _client = _factory.CreateClient(new WebApplicationFactoryClientOptions { AllowAutoRedirect = false });
    }

    [Fact]
    public async Task Program_TenantlessGoogleSignup_ProfileCompleteSession_UsesRealRegistrationsAndJwtBearer()
    {
        StartHost();
        var schemes = await _factory!.Services.GetRequiredService<IAuthenticationSchemeProvider>().GetAllSchemesAsync();
        Assert.Equal(typeof(JwtBearerHandler), Assert.Single(schemes).HandlerType);
        var options = _factory.Services.GetRequiredService<IOptionsMonitor<JwtBearerOptions>>().Get(JwtBearerDefaults.AuthenticationScheme);
        Assert.True(options.TokenValidationParameters.ValidateIssuer);
        Assert.True(options.TokenValidationParameters.ValidateAudience);
        Assert.True(options.TokenValidationParameters.ValidateIssuerSigningKey);
        Assert.True(options.TokenValidationParameters.ValidateLifetime);
        Assert.Equal([SecurityAlgorithms.RsaSha256], options.TokenValidationParameters.ValidAlgorithms);
        await using (var database = await _factory.Services.GetRequiredService<IDbContextFactory<IdentityDbContext>>().CreateDbContextAsync())
            Assert.Equal(AppConnection, database.Database.GetConnectionString());

        var token = Token();
        Assert.DoesNotContain(new JwtSecurityTokenHandler().ReadJwtToken(token).Claims, claim => claim.Type == "tenant_id");
        using var started = await SendAsync(HttpMethod.Post, "/api/v1/identity/registrations", token, new { languagePreference = "en" });
        var registration = (await ExpectAsync(started, HttpStatusCode.Created)).GetProperty("registrationId").GetGuid();
        using var profile = await SendAsync(HttpMethod.Put, $"/api/v1/identity/registrations/{registration}/profile", token,
            new { displayName = "Synthetic Customer", businessName = "Synthetic Business", businessDomain = "Synthetic testing", languagePreference = "en" });
        Assert.Equal("READY_TO_COMPLETE", (await ExpectAsync(profile, HttpStatusCode.OK)).GetProperty("state").GetString());
        using var completed = await SendAsync(HttpMethod.Post, $"/api/v1/identity/registrations/{registration}/complete", token);
        var account = (await ExpectAsync(completed, HttpStatusCode.OK)).GetProperty("accountReference").GetGuid();
        using var response = await SendAsync(HttpMethod.Get, "/api/v1/identity/session", token);
        var session = await ExpectAsync(response, HttpStatusCode.OK);
        Assert.Equal(account, session.GetProperty("accountReference").GetGuid());
        Assert.Equal("OWNER", session.GetProperty("roles")[0].GetString());
        Assert.Equal("AAL2_ACCOUNT", session.GetProperty("assuranceLevel").GetString());
        Assert.Empty(session.GetProperty("capabilities").EnumerateArray());
        Assert.True(response.Headers.CacheControl!.NoStore);
        Assert.Equal(new[] { "/realms/waooaw/.well-known/openid-configuration", "/realms/waooaw/protocol/openid-connect/certs" }, _oidc.Requests);
        Assert.Equal(new[] { "POST /realms/waooaw/protocol/openid-connect/token",
            "GET /admin/realms/waooaw/users/synthetic-actor", "GET /admin/realms/waooaw/users/synthetic-actor/federated-identity" }, _broker.Requests);
        Assert.Equal(1L, await OwnerScalarAsync("SELECT count(*) FROM business.organisations WHERE identity_managed AND id = tenant_id"));
        Assert.Equal(1L, await OwnerScalarAsync("SELECT count(*) FROM identity.memberships WHERE roles = ARRAY['OWNER']::text[]"));
        await AssertRestrictedPoolAsync();
    }

    [Fact]
    public async Task Program_TwoMembershipResolvedActors_ListOnlyOwnRelationships()
    {
        StartHost();
        var firstToken = Token(subject: "synthetic-actor-one");
        var secondToken = Token(subject: "synthetic-actor-two");
        var firstAccount = await CompleteAsync(firstToken, "First");
        var secondAccount = await CompleteAsync(secondToken, "Second");
        var firstTenant = await OwnerGuidAsync(
            "SELECT initial_tenant_id FROM identity.accounts WHERE account_id = @id", firstAccount);
        var secondTenant = await OwnerGuidAsync(
            "SELECT initial_tenant_id FROM identity.accounts WHERE account_id = @id", secondAccount);
        var firstRelationship = await SeedRelationshipAsync(firstTenant, firstAccount, "DMA");
        var secondRelationship = await SeedRelationshipAsync(secondTenant, secondAccount, "SALES");

        using var firstResponse = await SendAsync(HttpMethod.Get, "/api/v1/employment/relationships", firstToken);
        using var secondResponse = await SendAsync(HttpMethod.Get, "/api/v1/employment/relationships", secondToken);
        var firstItems = (await ExpectAsync(firstResponse, HttpStatusCode.OK)).GetProperty("items");
        var secondItems = (await ExpectAsync(secondResponse, HttpStatusCode.OK)).GetProperty("items");

        Assert.Equal(firstRelationship, Assert.Single(firstItems.EnumerateArray()).GetProperty("relationshipId").GetGuid());
        Assert.Equal(secondRelationship, Assert.Single(secondItems.EnumerateArray()).GetProperty("relationshipId").GetGuid());
        Assert.True(firstResponse.Headers.CacheControl!.NoStore);
        Assert.True(secondResponse.Headers.CacheControl!.NoStore);

        using var forged = await SendAsync(
            HttpMethod.Get, "/api/v1/employment/relationships", firstToken, header: "x-tenant-id");
        Assert.Equal("IDENTITY_ACTION_DENIED",
            (await ExpectAsync(forged, HttpStatusCode.Forbidden)).GetProperty("code").GetString());
        await AssertRestrictedPoolAsync();
    }

    [Theory]
    [InlineData("issuer")]
    [InlineData("audience")]
    [InlineData("signature")]
    [InlineData("missing")]
    public async Task Program_InvalidBearer_DeniedBeforeJourney(string invalid)
    {
        StartHost();
        using var wrongSigner = RSA.Create(2048);
        var token = invalid == "missing" ? null : Token(
            issuer: invalid == "issuer" ? "https://wrong.invalid/realms/waooaw" : null,
            audience: invalid == "audience" ? "wrong-audience" : "waooaw-platform",
            signer: invalid == "signature" ? wrongSigner : null);
        using var response = await SendAsync(HttpMethod.Post, "/api/v1/identity/registrations", token, new { languagePreference = "en" });
        Assert.Equal("IDENTITY_SESSION_REQUIRED", (await ExpectAsync(response, HttpStatusCode.Unauthorized)).GetProperty("code").GetString());
        Assert.Empty(_broker.Requests);
        Assert.Equal(0L, await OwnerScalarAsync("SELECT count(*) FROM identity.registrations"));
    }

    [Theory]
    [InlineData("x-tenant-id")]
    [InlineData("x-account-id")]
    public async Task Program_CallerTenantInput_DeniedBeforeRegistration(string header)
    {
        StartHost();
        using var response = await SendAsync(HttpMethod.Post, "/api/v1/identity/registrations", Token(),
            new { languagePreference = "en" }, header);
        Assert.Equal("IDENTITY_ACTION_DENIED", (await ExpectAsync(response, HttpStatusCode.Forbidden)).GetProperty("code").GetString());
        Assert.Empty(_broker.Requests);
        Assert.Equal(0L, await OwnerScalarAsync("SELECT count(*) FROM identity.registrations"));
    }

    [Fact]
    public async Task Program_UnadaptedProtectedEndpoint_DeniedWithForgedTenantAndOwner()
    {
        StartHost();
        using var response = await SendAsync(HttpMethod.Get, "/api/v1/subscriptions", Token(extra:
            [new Claim("tenant_id", Guid.NewGuid().ToString()), new Claim("waooaw_roles", "OWNER")]));
        Assert.Equal("IDENTITY_ACTION_DENIED", (await ExpectAsync(response, HttpStatusCode.Forbidden)).GetProperty("code").GetString());
        Assert.Empty(_broker.Requests);
        Assert.Equal(0L, await OwnerScalarAsync("SELECT count(*) FROM identity.accounts"));
    }

    [Theory]
    [InlineData(false, false)]
    [InlineData(false, true)]
    [InlineData(true, false)]
    public async Task Program_MissingReadiness_HealthWorksAndJourneyFailsClosed(bool brokerEnabled, bool googleEnabled)
    {
        StartHost(brokerEnabled, googleEnabled);
        using var health = await _client.GetAsync("/health");
        Assert.Equal(HttpStatusCode.OK, health.StatusCode);
        using var providers = await _client.GetAsync("/api/v1/identity/providers");
        Assert.Equal("UNAVAILABLE", (await ExpectAsync(providers, HttpStatusCode.OK))
            .GetProperty("providers")[0].GetProperty("availability").GetString());
        foreach (var request in new[] { (HttpMethod.Post, "/api/v1/identity/registrations"),
            (HttpMethod.Post, $"/api/v1/identity/registrations/{Guid.NewGuid()}/complete"),
            (HttpMethod.Get, "/api/v1/identity/session") })
        {
            using var response = await SendAsync(request.Item1, request.Item2, Token(), new { languagePreference = "en" });
            Assert.Equal("IDENTITY_DEPENDENCY_UNAVAILABLE", (await ExpectAsync(response, HttpStatusCode.ServiceUnavailable)).GetProperty("code").GetString());
        }
        Assert.Empty(_broker.Requests);
        Assert.Equal(0L, await OwnerScalarAsync("SELECT count(*) FROM identity.registrations"));
        Assert.Equal(0L, await OwnerScalarAsync("SELECT count(*) FROM identity.accounts"));
    }

    private string Token(string? issuer = null, string audience = "waooaw-platform", RSA? signer = null,
        Claim[]? extra = null, string subject = "synthetic-actor")
    {
        var claims = GoogleWorkspaceProofAdapterTests.Principal(subject).Claims
            .Where(claim => claim.Type is not ("iss" or "aud" or "iat" or "exp")).Concat(extra ?? []);
        var now = DateTime.UtcNow;
        var token = new JwtSecurityToken(issuer ?? _configuration.ActorIssuer, audience, claims,
            now.AddSeconds(-1), now.AddMinutes(10), new SigningCredentials(
                new RsaSecurityKey(signer ?? _signer) { KeyId = "synthetic-program-key" }, SecurityAlgorithms.RsaSha256));
        token.Payload["iat"] = new DateTimeOffset(now).ToUnixTimeSeconds();
        return new JwtSecurityTokenHandler().WriteToken(token);
    }

    private async Task<HttpResponseMessage> SendAsync(HttpMethod method, string path, string? token, object? body = null, string? header = null)
    {
        using var request = new HttpRequestMessage(method, path);
        if (token is not null) request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        request.Headers.Add("Idempotency-Key", Guid.NewGuid().ToString());
        if (header is not null) request.Headers.Add(header, Guid.NewGuid().ToString());
        if (body is not null) request.Content = JsonContent.Create(body);
        return await _client.SendAsync(request);
    }

    private static async Task<JsonElement> ExpectAsync(HttpResponseMessage response, HttpStatusCode expected)
    {
        var body = await response.Content.ReadAsStringAsync();
        Assert.True(response.StatusCode == expected, $"Expected {expected}; received {response.StatusCode}: {body}");
        return JsonSerializer.Deserialize<JsonElement>(body);
    }

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

    private async Task<Guid> CompleteAsync(string token, string name)
    {
        using var started = await SendAsync(
            HttpMethod.Post, "/api/v1/identity/registrations", token, new { languagePreference = "en" });
        var registration = (await ExpectAsync(started, HttpStatusCode.Created)).GetProperty("registrationId").GetGuid();
        using var profile = await SendAsync(
            HttpMethod.Put, $"/api/v1/identity/registrations/{registration}/profile", token,
            new { displayName = name, businessName = name + " Business", businessDomain = "Synthetic testing", languagePreference = "en" });
        await ExpectAsync(profile, HttpStatusCode.OK);
        using var completed = await SendAsync(
            HttpMethod.Post, $"/api/v1/identity/registrations/{registration}/complete", token);
        return (await ExpectAsync(completed, HttpStatusCode.OK)).GetProperty("accountReference").GetGuid();
    }

    private async Task<Guid> OwnerGuidAsync(string sql, Guid id)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        command.Parameters.AddWithValue("id", id);
        return (Guid)(await command.ExecuteScalarAsync())!;
    }

    private async Task<Guid> SeedRelationshipAsync(Guid tenantId, Guid accountId, string professionalType)
    {
        var relationshipId = Guid.NewGuid();
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand("""
            INSERT INTO business.employment_relationships
                (relationship_id, tenant_id, professional_type, evaluation_intent_id, initiating_participant_id)
            VALUES (@relationship, @tenant, @professional, @evaluation, @account);
            INSERT INTO business.relationship_participants
                (tenant_id, relationship_id, participant_id, role, bound_evidence_id)
            VALUES (@tenant, @relationship, @account, 'EMPLOYER', @evidence);
            """, connection);
        command.Parameters.AddWithValue("relationship", relationshipId);
        command.Parameters.AddWithValue("tenant", tenantId);
        command.Parameters.AddWithValue("professional", professionalType);
        command.Parameters.AddWithValue("evaluation", Guid.NewGuid());
        command.Parameters.AddWithValue("account", accountId);
        command.Parameters.AddWithValue("evidence", Guid.NewGuid());
        await command.ExecuteNonQueryAsync();
        return relationshipId;
    }

    private async Task AssertRestrictedPoolAsync()
    {
        await using var connection = new NpgsqlConnection(AppConnection);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand("""
            SELECT current_user, rolsuper, rolbypassrls,
                COALESCE(NULLIF(current_setting('app.identity_issuer', true), ''), 'EMPTY'),
                COALESCE(NULLIF(current_setting('app.identity_subject', true), ''), 'EMPTY'),
                COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), 'EMPTY'),
                COALESCE(NULLIF(current_setting('app.current_tenant_id', true), ''), 'EMPTY')
            FROM pg_roles WHERE rolname = current_user
            """, connection);
        await using var reader = await command.ExecuteReaderAsync();
        Assert.True(await reader.ReadAsync());
        Assert.Equal("business_app", reader.GetString(0));
        Assert.False(reader.GetBoolean(1));
        Assert.False(reader.GetBoolean(2));
        for (var index = 3; index < 7; index++) Assert.Equal("EMPTY", reader.GetString(index));
    }

    private sealed class SyntheticOidcHandler(string issuer, RSA signer) : HttpMessageHandler
    {
        public List<string> Requests { get; } = [];

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            Assert.Equal(HttpMethod.Get, request.Method);
            Assert.Equal(new Uri(issuer).Host, request.RequestUri!.Host);
            Requests.Add(request.RequestUri.AbsolutePath);
            object body;
            if (request.RequestUri.AbsolutePath == "/realms/waooaw/.well-known/openid-configuration")
                body = new { issuer, jwks_uri = issuer + "/protocol/openid-connect/certs" };
            else
            {
                Assert.Equal("/realms/waooaw/protocol/openid-connect/certs", request.RequestUri.AbsolutePath);
                var key = signer.ExportParameters(false);
                body = new { keys = new[] { new { kty = "RSA", use = "sig", kid = "synthetic-program-key", alg = "RS256",
                    n = Base64UrlEncoder.Encode(key.Modulus!), e = Base64UrlEncoder.Encode(key.Exponent!) } } };
            }
            return Task.FromResult(CreateResponse(body));
        }

        private static HttpResponseMessage CreateResponse(object body) =>
            new(HttpStatusCode.OK) { Content = JsonContent.Create(body) };
    }
}