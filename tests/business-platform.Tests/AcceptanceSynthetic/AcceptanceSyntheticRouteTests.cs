// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §5 and adr/ADR-055-synthetic-acceptance-tenants-and-evidence.md decision 4
// Constitutional basis: C-059 (Implementation Traceability)

using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Net.Http.Headers;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Tokens;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.AcceptanceSynthetic;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.AcceptanceSynthetic;

/// <summary>
/// WC159-R001 (route off when the setting is off) and WC159-R002 (only the acceptance-provisioner realm role),
/// driven through a real JwtBearer pipeline with signed tokens and the production middleware order.
/// </summary>
public sealed class AcceptanceSyntheticRouteTests : IDisposable
{
    private const string Issuer = "https://identity.invalid/realms/waooaw";
    private const string RunId = "run-2026-11-23-001";
    private const string Subject = "0f9c1a52-7d2e-4c50-9b0b-6f3f5d0a1e11";
    private readonly RSA _signer = RSA.Create(2048);
    private readonly FakeSyntheticAcceptanceRegistry _registry = new();

    public void Dispose() => _signer.Dispose();

    private async Task<(WebApplication App, HttpClient Client)> HostAsync(bool enabled)
    {
        var builder = WebApplication.CreateBuilder();
        builder.WebHost.UseTestServer();
        builder.Logging.ClearProviders();
        builder.Services.AddControllers().AddApplicationPart(typeof(AcceptanceSyntheticController).Assembly);
        builder
            .Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
            .AddJwtBearer(options =>
            {
                options.MapInboundClaims = true;
                options.TokenValidationParameters = new TokenValidationParameters
                {
                    ValidIssuer = Issuer,
                    ValidAudience = "waooaw-platform",
                    IssuerSigningKey = new RsaSecurityKey(_signer),
                    ValidAlgorithms = [SecurityAlgorithms.RsaSha256],
                };
            });
        builder.Services.AddAuthorization();
        builder.Services.AddSingleton(Options.Create(new AcceptanceSyntheticOptions { Enabled = enabled }));
        builder.Services.AddSingleton<ISyntheticAcceptanceRegistry>(_registry);
        var app = builder.Build();
        app.UseRouting();
        app.UseAuthentication();
        app.UseAuthorization();
        app.UseMiddleware<CustomerMembershipMiddleware>();
        app.UseWhen(
            context =>
                !context.Items.ContainsKey(CustomerMembershipMiddleware.JourneyItem)
                && !context.Items.ContainsKey(CustomerMembershipMiddleware.StaffItem)
                && context.GetEndpoint()?.Metadata.GetMetadata<AcceptanceProvisionerRouteAttribute>() is null,
            branch => branch.UseTenantIsolation()
        );
        app.MapControllers();
        await app.StartAsync();
        return (app, app.GetTestClient());
    }

    private string Token(
        string client = AcceptanceProvisionerAuthority.ClientId,
        string? realmAccess = "{\"roles\":[\"acceptance-provisioner\"]}",
        RSA? signer = null,
        params Claim[] extra
    )
    {
        var claims = new List<Claim> { new("sub", "svc-acceptance-provisioner"), new("azp", client) };
        if (realmAccess is not null)
        {
            // A malformed claim can only travel as a string; a well-formed one travels as a JSON object like Keycloak's.
            var wellFormed = true;
            try { JsonDocument.Parse(realmAccess).Dispose(); } catch (JsonException) { wellFormed = false; }
            claims.Add(new Claim("realm_access", realmAccess, wellFormed ? JsonClaimValueTypes.Json : ClaimValueTypes.String));
        }
        claims.AddRange(extra);
        var now = DateTime.UtcNow;
        var token = new JwtSecurityToken(
            Issuer,
            "waooaw-platform",
            claims,
            now.AddSeconds(-1),
            now.AddMinutes(10),
            new SigningCredentials(new RsaSecurityKey(signer ?? _signer), SecurityAlgorithms.RsaSha256)
        );
        return new JwtSecurityTokenHandler().WriteToken(token);
    }

    private static async Task<HttpResponseMessage> SendAsync(
        HttpClient client,
        HttpMethod method,
        string path,
        string? token,
        string? body = null
    )
    {
        using var request = new HttpRequestMessage(method, path);
        if (token is not null)
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        if (body is not null)
            request.Content = new StringContent(body, Encoding.UTF8, "application/json");
        return await client.SendAsync(request);
    }

    private static async Task<string> CodeAsync(HttpResponseMessage response) =>
        JsonDocument.Parse(await response.Content.ReadAsStringAsync()).RootElement.GetProperty("code").GetString()!;

    private static string SubjectPath(string runId = RunId) => $"/internal/v1/acceptance/runs/{runId}/synthetic-subjects";

    private static string SubjectBody(string subject = Subject) => $"{{\"subject\":\"{subject}\"}}";

    [Fact]
    public async Task WC159_R001_TheRouteIsOffByDefault_AndEveryCallerSeesTheSameDisabledNotFoundBeforeTheBodyIsRead()
    {
        Assert.False(new AcceptanceSyntheticOptions().Enabled);
        var (app, client) = await HostAsync(enabled: false);
        await using var _ = app;
        var provisioner = Token();
        var customer = Token(client: "waooaw-web");

        foreach (var token in new[] { provisioner, Token(realmAccess: null) })
        {
            foreach (var body in new[] { SubjectBody(), "not json", "{\"unknown\":1}" })
            {
                using var response = await SendAsync(client, HttpMethod.Post, SubjectPath(), token, body);
                Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
                Assert.Equal("ACCEPTANCE_SYNTHETIC_DISABLED", await CodeAsync(response));
            }
            using var recipient = await SendAsync(client, HttpMethod.Put, $"/internal/v1/acceptance/runs/{RunId}/sandbox-recipients", token, "{}");
            Assert.Equal(HttpStatusCode.NotFound, recipient.StatusCode);
            using var delete = await SendAsync(client, HttpMethod.Delete, $"/internal/v1/acceptance/runs/{RunId}", token);
            Assert.Equal(HttpStatusCode.NotFound, delete.StatusCode);
        }
        // A customer never reaches the route at all, and nothing was written.
        using var refused = await SendAsync(client, HttpMethod.Post, SubjectPath(), customer, SubjectBody());
        Assert.Equal(HttpStatusCode.Forbidden, refused.StatusCode);
        Assert.Equal(0, _registry.Calls);
    }

    [Fact]
    public async Task WC159_R002_OnlyAVerifiedProvisionerTokenWritesTheRegistry_WithTheIssuerTakenFromTheVerifiedToken()
    {
        var (app, client) = await HostAsync(enabled: true);
        await using var _ = app;

        using var created = await SendAsync(client, HttpMethod.Post, SubjectPath(), Token(), SubjectBody());
        Assert.Equal(HttpStatusCode.Created, created.StatusCode);
        Assert.Equal((Issuer, Subject, RunId, "svc-acceptance-provisioner"), _registry.Subjects.Single());

        // A body cannot name the issuer, a tenant or a marker.
        foreach (var body in new[]
        {
            $"{{\"subject\":\"{Subject}\",\"issuer\":\"https://attacker.invalid\"}}",
            $"{{\"subject\":\"{Subject}\",\"synthetic\":true,\"tenantId\":\"{Guid.NewGuid()}\"}}",
        })
        {
            using var forged = await SendAsync(client, HttpMethod.Post, SubjectPath(), Token(), body);
            Assert.Equal(HttpStatusCode.BadRequest, forged.StatusCode);
        }
        Assert.Single(_registry.Subjects);

        _registry.SubjectResult = SyntheticSubjectRegistration.AlreadyRegistered;
        using var repeated = await SendAsync(client, HttpMethod.Post, SubjectPath(), Token(), SubjectBody());
        Assert.Equal(HttpStatusCode.NoContent, repeated.StatusCode);
        _registry.SubjectResult = SyntheticSubjectRegistration.RunConflict;
        using var conflict = await SendAsync(client, HttpMethod.Post, SubjectPath(), Token(), SubjectBody());
        Assert.Equal(HttpStatusCode.Conflict, conflict.StatusCode);
        _registry.SubjectResult = SyntheticSubjectRegistration.LimitReached;
        using var limited = await SendAsync(client, HttpMethod.Post, SubjectPath(), Token(), SubjectBody());
        Assert.Equal(HttpStatusCode.TooManyRequests, limited.StatusCode);
    }

    [Theory]
    [InlineData("{\"subject\":\"short\"}")]
    [InlineData("{}")]
    [InlineData("{\"subject\":\"has space in the subject value\"}")]
    public async Task WC159_R002_AnInvalidSubjectIsRejectedBeforeTheRegistry(string body)
    {
        var (app, client) = await HostAsync(enabled: true);
        await using var _ = app;
        using var response = await SendAsync(client, HttpMethod.Post, SubjectPath(), Token(), body);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        using var badRun = await SendAsync(client, HttpMethod.Post, SubjectPath("bad"), Token(), SubjectBody());
        Assert.Equal(HttpStatusCode.BadRequest, badRun.StatusCode);
        Assert.Equal(0, _registry.Calls);
    }

    [Fact]
    public async Task WC159_R002_SandboxRecipientsAndRunDeactivationUseTheSameGuardAndValidation()
    {
        var (app, client) = await HostAsync(enabled: true);
        await using var _ = app;
        var recipientPath = $"/internal/v1/acceptance/runs/{RunId}/sandbox-recipients";

        using var accepted = await SendAsync(client, HttpMethod.Put, recipientPath, Token(), "{\"recipient\":\"+15550001234\"}");
        Assert.Equal(HttpStatusCode.NoContent, accepted.StatusCode);
        Assert.Equal((RunId, "+15550001234", "svc-acceptance-provisioner"), _registry.Recipients.Single());
        foreach (var body in new[] { "{\"recipient\":\"15550001234\"}", "{}", "{\"recipient\":\"+15550001234\",\"tenantId\":\"x\"}" })
        {
            using var invalid = await SendAsync(client, HttpMethod.Put, recipientPath, Token(), body);
            Assert.Equal(HttpStatusCode.BadRequest, invalid.StatusCode);
        }
        _registry.RecipientResult = SandboxRecipientRegistration.LimitReached;
        using var limited = await SendAsync(client, HttpMethod.Put, recipientPath, Token(), "{\"recipient\":\"+15550004321\"}");
        Assert.Equal(HttpStatusCode.TooManyRequests, limited.StatusCode);

        using var deactivated = await SendAsync(client, HttpMethod.Delete, $"/internal/v1/acceptance/runs/{RunId}", Token());
        Assert.Equal(HttpStatusCode.OK, deactivated.StatusCode);
        var counts = JsonDocument.Parse(await deactivated.Content.ReadAsStringAsync()).RootElement;
        Assert.Equal(2, counts.GetProperty("deactivatedSubjects").GetInt32());
        Assert.Equal(1, counts.GetProperty("deactivatedRecipients").GetInt32());
        using var badRun = await SendAsync(client, HttpMethod.Delete, "/internal/v1/acceptance/runs/bad", Token());
        Assert.Equal(HttpStatusCode.BadRequest, badRun.StatusCode);
        Assert.Equal([RunId], _registry.Deactivated);

        foreach (var (method, path, body) in new[]
        {
            (HttpMethod.Put, recipientPath, "{\"recipient\":\"+15550001234\"}"),
            (HttpMethod.Delete, $"/internal/v1/acceptance/runs/{RunId}", null),
        })
        {
            using var refused = await SendAsync(client, method, path, Token(client: "waooaw-web"), body);
            Assert.Equal(HttpStatusCode.Forbidden, refused.StatusCode);
        }
    }

    [Fact]
    public async Task WC159_R002_EveryOtherCallerIsRefused_IncludingACustomerAndATokenThatNamesItsOwnRoles()
    {
        var (app, client) = await HostAsync(enabled: true);
        await using var _ = app;
        using var otherSigner = RSA.Create(2048);
        const string Role = "{\"roles\":[\"acceptance-provisioner\"]}";
        var refused = new Dictionary<string, string?>
        {
            // A customer holds no such role, and a customer's own client is refused before the route runs.
            ["customer client"] = Token(client: "waooaw-web", realmAccess: Role),
            ["mobile client"] = Token(client: "waooaw-mobile", realmAccess: Role),
            ["customer, no role"] = Token(client: "waooaw-web", realmAccess: "{\"roles\":[\"customer\"]}"),
            ["other client holding the role"] = Token(client: "waooaw-admin-cli", realmAccess: Role),
            ["provisioner client without the role"] = Token(realmAccess: "{\"roles\":[\"customer\",\"pricing_admin\"]}"),
            ["provisioner client, no realm_access"] = Token(realmAccess: null),
            ["role outside realm_access"] = Token(realmAccess: null, extra: [new Claim("roles", "acceptance-provisioner"), new Claim("role", "acceptance-provisioner")]),
            ["self-claimed roles"] = Token(extra: new Claim("waooaw_roles", "acceptance-provisioner")),
            ["malformed realm_access"] = Token(realmAccess: "{\"roles\":"),
            ["non-array roles"] = Token(realmAccess: "{\"roles\":\"acceptance-provisioner\"}"),
            ["non-object realm_access"] = Token(realmAccess: "[\"acceptance-provisioner\"]"),
            ["similar role"] = Token(realmAccess: "{\"roles\":[\"Acceptance-Provisioner\",\"acceptance-provisioner-x\",1]}"),
            ["customer with a forged marker and tenant"] = Token(client: "waooaw-web", realmAccess: Role, extra: [new Claim("tenant_id", Guid.NewGuid().ToString()), new Claim("synthetic", "true")]),
        };
        foreach (var (name, token) in refused)
        {
            using var response = await SendAsync(client, HttpMethod.Post, SubjectPath(), token, SubjectBody());
            Assert.True(response.StatusCode == HttpStatusCode.Forbidden, $"{name}: {response.StatusCode}");
        }
        using var anonymous = await SendAsync(client, HttpMethod.Post, SubjectPath(), null, SubjectBody());
        Assert.Equal(HttpStatusCode.Unauthorized, anonymous.StatusCode);
        using var forgedSignature = await SendAsync(client, HttpMethod.Post, SubjectPath(), Token(signer: otherSigner), SubjectBody());
        Assert.Equal(HttpStatusCode.Unauthorized, forgedSignature.StatusCode);
        Assert.Equal(0, _registry.Calls);
    }

    [Fact]
    public void WC159_R002_TheRoleIsNotRequestableAndTheProductionOptionsAreRefused()
    {
        Assert.DoesNotContain(
            Waooaw.BusinessPlatform.Services.PlatformAccess.PlatformRoles.AcceptanceProvisioner,
            Waooaw.BusinessPlatform.Services.PlatformAccess.PlatformRoles.Requestable
        );
        Assert.Equal("acceptance-provisioner", Waooaw.BusinessPlatform.Services.PlatformAccess.PlatformRoles.AcceptanceProvisioner);
    }

    [Theory]
    [InlineData(null, true, true)]
    [InlineData("demo", true, true)]
    [InlineData("uat", true, true)]
    [InlineData("local", true, true)]
    [InlineData("prod", true, false)]
    [InlineData("prod", false, true)]
    public void WC159_R001_ProductionRefusesToStartWithTheRegistryEnabled(string? environment, bool enabled, bool valid)
    {
        var configuration = new Microsoft.Extensions.Configuration.ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?> { ["IdentityEnvironment:Environment"] = environment })
            .Build();
        var result = new AcceptanceSyntheticOptionsValidator(configuration).Validate(null, new AcceptanceSyntheticOptions { Enabled = enabled });
        Assert.Equal(valid, result.Succeeded);
    }

    [Fact]
    public void WC159_R002_UnauthenticatedOrIncompletePrincipalsAreNeverProvisioners()
    {
        Assert.False(AcceptanceProvisionerAuthority.TryResolve(null, out _));
        Assert.False(AcceptanceProvisionerAuthority.TryResolve(new ClaimsPrincipal(new ClaimsIdentity()), out _));
        const string Role = "{\"roles\":[\"acceptance-provisioner\"]}";
        static ClaimsPrincipal Principal(params Claim[] claims) => new(new ClaimsIdentity(claims, "Test"));
        var good = new[]
        {
            new Claim("iss", Issuer),
            new Claim("azp", AcceptanceProvisionerAuthority.ClientId),
            new Claim("realm_access", Role),
        };
        Assert.True(AcceptanceProvisionerAuthority.TryResolve(Principal(good), out var withoutSubject));
        Assert.Equal(AcceptanceProvisionerAuthority.ClientId, withoutSubject!.Principal);
        Assert.True(AcceptanceProvisionerAuthority.TryResolve(Principal([.. good, new Claim(ClaimTypes.NameIdentifier, new string('s', 200))]), out var mapped));
        Assert.Equal(128, mapped!.Principal.Length);
        // Two different issuers or clients, an empty or oversized issuer: the token is ambiguous and refused.
        Assert.False(AcceptanceProvisionerAuthority.TryResolve(Principal([.. good, new Claim("iss", "https://other.invalid")]), out _));
        Assert.False(AcceptanceProvisionerAuthority.TryResolve(Principal([.. good, new Claim("azp", "waooaw-web")]), out _));
        Assert.False(AcceptanceProvisionerAuthority.TryResolve(Principal(good[1], good[2], new Claim("iss", " ")), out _));
        Assert.False(AcceptanceProvisionerAuthority.TryResolve(Principal(good[1], good[2], new Claim("iss", new string('i', 257))), out _));
        Assert.False(AcceptanceProvisionerAuthority.TryResolve(Principal(good[1], good[2]), out _));
    }
}
