// Implements: work-contracts/WC-033-goal005-bp-trial-lifecycle.md §WC033-03
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-03
// constitutional_basis: C-023 (phone gate), C-088 (trial billing mode), C-059, C-076 (≥90% coverage)
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using FluentAssertions;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

// ─── Stub HTTP infrastructure ─────────────────────────────────────────────────

/// <summary>
/// A reusable <see cref="HttpMessageHandler"/> stub that returns a fixed response.
/// Used to mock the WBE named HttpClient in integration tests.
/// </summary>
internal sealed class StubHttpMessageHandler : HttpMessageHandler
{
    private readonly Func<HttpRequestMessage, HttpResponseMessage> _factory;

    public StubHttpMessageHandler(HttpStatusCode status, string? body = null)
        : this(_ => new HttpResponseMessage(status)
        {
            Content = body is null
                ? null
                : new StringContent(body, Encoding.UTF8, "application/json"),
        }) { }

    public StubHttpMessageHandler(Func<HttpRequestMessage, HttpResponseMessage> factory)
    {
        _factory = factory;
    }

    public HttpRequestMessage? LastRequest { get; private set; }

    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken
    )
    {
        LastRequest = request;
        return Task.FromResult(_factory(request));
    }
}

// ─── Test auth handler (matches pattern in CCT_MT01) ─────────────────────────

file sealed class TestAuthHandlerOptions : AuthenticationSchemeOptions { }

file sealed class TestAuthHandler : AuthenticationHandler<TestAuthHandlerOptions>
{
    public TestAuthHandler(
        IOptionsMonitor<TestAuthHandlerOptions> options,
        ILoggerFactory logger,
        UrlEncoder encoder
    )
        : base(options, logger, encoder) { }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        if (!Request.Headers.TryGetValue("x-test-tenant-id", out var tenantValues))
            return Task.FromResult(AuthenticateResult.Fail("Missing x-test-tenant-id"));

        var claims = new List<Claim>
        {
            new("tenant_id", tenantValues.First()!),
            new(ClaimTypes.NameIdentifier, "test-user"),
        };
        if (Request.Headers.TryGetValue("x-test-channel", out var channelValues))
            claims.Add(new Claim("channel", channelValues.First()!));
        if (Request.Headers.TryGetValue("x-test-external-subject-hash", out var hashValues))
            claims.Add(new Claim("external_subject_hash", hashValues.First()!));
        var ticket = new AuthenticationTicket(
            new ClaimsPrincipal(new ClaimsIdentity(claims, Scheme.Name)),
            Scheme.Name
        );
        return Task.FromResult(AuthenticateResult.Success(ticket));
    }
}

// ─── WebApplicationFactory with WBE stub ──────────────────────────────────────

internal sealed class SubscriptionsTestFactory : WebApplicationFactory<Program>
{
    public StubHttpMessageHandler WbeStub { get; }

    public SubscriptionsTestFactory(StubHttpMessageHandler wbeStub)
    {
        WbeStub = wbeStub;
    }

    protected override void ConfigureWebHost(Microsoft.AspNetCore.Hosting.IWebHostBuilder builder)
    {
        builder.UseSetting("Conversation:CursorHmacKey", new string('c', 32));
        builder.ConfigureTestServices(services =>
        {
            // Replace JWT with test auth scheme
            services
                .AddAuthentication(options =>
                {
                    options.DefaultAuthenticateScheme = "Test";
                    options.DefaultChallengeScheme = "Test";
                })
                .AddScheme<TestAuthHandlerOptions, TestAuthHandler>("Test", _ => { });

            // Replace "WBE" named HttpClient with stub
            services.AddHttpClient("WBE").ConfigurePrimaryHttpMessageHandler(() => WbeStub);
        });
    }
}

// ─── SubscriptionsController Tests ───────────────────────────────────────────

public sealed class SubscriptionsControllerTests
{
    private static readonly string TenantId = Guid.NewGuid().ToString();

    private static readonly string WbeSuccessBody = JsonSerializer.Serialize(
        new
        {
            trial_id = Guid.NewGuid().ToString(),
            expires_at = DateTimeOffset.UtcNow.AddDays(14).ToString("O"),
            free_unit_caps = new { llm_cloud = 50, llm_local = 200 },
            wallet_bucket_ids = new[] { Guid.NewGuid().ToString() },
        }
    );

    private HttpClient CreateClient(StubHttpMessageHandler wbeStub)
    {
        var factory = new SubscriptionsTestFactory(wbeStub);
        var client = factory.CreateClient(
            new WebApplicationFactoryClientOptions { AllowAutoRedirect = false }
        );
        client.DefaultRequestHeaders.Add("x-test-tenant-id", TenantId);
        return client;
    }

    // ── CCT-PHONE-01: C-023 gate — phone not verified → 422 ──────────────────

    [Fact]
    public async Task TrialStart_PhoneNotVerified_Returns422()
    {
        // Arrange — WBE stub should NOT be called
        var wbeStub = new StubHttpMessageHandler(HttpStatusCode.OK, WbeSuccessBody);
        var client = CreateClient(wbeStub);
        var request = new TrialStartRequest(
            Guid.NewGuid(),
            "DMA",
            PhoneVerified: false,
            AgentVersion: "1.0.0"
        );

        // Act
        var response = await client.PostAsJsonAsync("/api/v1/subscriptions/trial-start", request);

        // Assert
        response
            .StatusCode.Should()
            .Be(
                HttpStatusCode.UnprocessableEntity,
                because: "C-023: phone verification is the evidence gate — must be 422 PHONE_NOT_VERIFIED"
            );

        var body = await response.Content.ReadAsStringAsync();
        body.Should().Contain("PHONE_NOT_VERIFIED");

        // WBE must NOT be called when phone gate fails
        wbeStub
            .LastRequest.Should()
            .BeNull(because: "WBE must not be called when phone gate fails");
    }

    // ── Happy path: phone verified, WBE returns 200 ──────────────────────────

    [Fact]
    public async Task TrialStart_PhoneVerified_WbeReturns200_Returns200WithTrialResponse()
    {
        // Arrange
        var wbeStub = new StubHttpMessageHandler(HttpStatusCode.OK, WbeSuccessBody);
        var client = CreateClient(wbeStub);
        var customerId = Guid.NewGuid();
        var request = new TrialStartRequest(
            customerId,
            "DMA",
            PhoneVerified: true,
            AgentVersion: "1.0.0"
        );

        // Act
        var response = await client.PostAsJsonAsync("/api/v1/subscriptions/trial-start", request);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.OK);

        var result = await response.Content.ReadFromJsonAsync<TrialStartResponse>(
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );
        result.Should().NotBeNull();
        result!.TrialId.Should().NotBe(Guid.Empty);
        result.ExpiresAt.Should().BeAfter(DateTimeOffset.UtcNow);

        // WBE was called
        wbeStub.LastRequest.Should().NotBeNull();
        wbeStub.LastRequest!.RequestUri!.AbsolutePath.Should().Be("/trial/start");
    }

    // ── WBE returns 409 TRIAL_ALREADY_USED → BP propagates 409 ───────────────

    [Fact]
    public async Task TrialStart_WbeReturns409_Returns409Conflict()
    {
        // Arrange
        var wbeStub = new StubHttpMessageHandler(
            HttpStatusCode.Conflict,
            """{"detail":"TRIAL_ALREADY_USED"}"""
        );
        var client = CreateClient(wbeStub);
        var request = new TrialStartRequest(
            Guid.NewGuid(),
            "DMA",
            PhoneVerified: true,
            AgentVersion: "1.0.0"
        );

        // Act
        var response = await client.PostAsJsonAsync("/api/v1/subscriptions/trial-start", request);

        // Assert
        response
            .StatusCode.Should()
            .Be(
                HttpStatusCode.Conflict,
                because: "WBE 409 TRIAL_ALREADY_USED must be propagated to caller"
            );

        var body = await response.Content.ReadAsStringAsync();
        body.Should().Contain("TRIAL_ALREADY_USED");
    }

    // ── WBE unavailable → BP returns 503 ─────────────────────────────────────

    [Fact]
    public async Task TrialStart_WbeUnavailable_Returns503()
    {
        // Arrange — WBE throws a connection exception
        var wbeStub = new StubHttpMessageHandler(_ =>
            throw new HttpRequestException("Connection refused")
        );
        var client = CreateClient(wbeStub);
        var request = new TrialStartRequest(
            Guid.NewGuid(),
            "DMA",
            PhoneVerified: true,
            AgentVersion: "1.0.0"
        );

        // Act
        var response = await client.PostAsJsonAsync("/api/v1/subscriptions/trial-start", request);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.ServiceUnavailable);
    }

    // ── Null body → 400 ──────────────────────────────────────────────────────

    [Fact]
    public async Task TrialStart_NullBody_Returns400()
    {
        var wbeStub = new StubHttpMessageHandler(HttpStatusCode.OK, WbeSuccessBody);
        var client = CreateClient(wbeStub);

        var response = await client.PostAsync(
            "/api/v1/subscriptions/trial-start",
            new StringContent("{}", Encoding.UTF8, "application/json")
        );

        // A missing PhoneVerified defaults to false → 422
        response
            .StatusCode.Should()
            .Match(
                s => s == HttpStatusCode.BadRequest || s == HttpStatusCode.UnprocessableEntity,
                because: "invalid or incomplete body must be rejected"
            );
    }

    // ── WBE non-2xx (500) → BP returns 502 ───────────────────────────────────

    [Fact]
    public async Task TrialStart_WbeReturns500_Returns502()
    {
        var wbeStub = new StubHttpMessageHandler(HttpStatusCode.InternalServerError, "{}");
        var client = CreateClient(wbeStub);
        var request = new TrialStartRequest(
            Guid.NewGuid(),
            "DMA",
            PhoneVerified: true,
            AgentVersion: "1.0.0"
        );

        var response = await client.PostAsJsonAsync("/api/v1/subscriptions/trial-start", request);

        response.StatusCode.Should().Be(HttpStatusCode.BadGateway);
    }

    // ── Unauthenticated request → 401 (C-026) ────────────────────────────────

    [Fact]
    public async Task TrialStart_NoAuth_Returns401()
    {
        var wbeStub = new StubHttpMessageHandler(HttpStatusCode.OK, WbeSuccessBody);
        var factory = new SubscriptionsTestFactory(wbeStub);
        var client = factory.CreateClient(
            new WebApplicationFactoryClientOptions { AllowAutoRedirect = false }
        );
        // No auth headers

        var request = new TrialStartRequest(
            Guid.NewGuid(),
            "DMA",
            PhoneVerified: true,
            AgentVersion: "1.0.0"
        );
        var response = await client.PostAsJsonAsync("/api/v1/subscriptions/trial-start", request);

        response.StatusCode.Should().Be(HttpStatusCode.Unauthorized);
    }

    // ── C3-03: the exact agent version is forwarded; the verified identity hash comes from claims ──

    private static (StubHttpMessageHandler Stub, Func<string?> Body) CapturingStub(
        HttpStatusCode status,
        string responseBody
    )
    {
        string? captured = null;
        var stub = new StubHttpMessageHandler(request =>
        {
            captured = request.Content!.ReadAsStringAsync().GetAwaiter().GetResult();
            return new HttpResponseMessage(status)
            {
                Content = new StringContent(responseBody, Encoding.UTF8, "application/json"),
            };
        });
        return (stub, () => captured);
    }

    [Fact]
    public async Task TrialStart_ForwardsTheExactAgentVersionToWbe()
    {
        var (stub, body) = CapturingStub(HttpStatusCode.OK, WbeSuccessBody);
        var client = CreateClient(stub);
        var request = new TrialStartRequest(
            Guid.NewGuid(),
            "DMA",
            PhoneVerified: true,
            AgentVersion: "2.3.4"
        );

        var response = await client.PostAsJsonAsync("/api/v1/subscriptions/trial-start", request);

        response.StatusCode.Should().Be(HttpStatusCode.OK);
        using var sent = JsonDocument.Parse(body()!);
        sent.RootElement.GetProperty("agent_version").GetString().Should().Be("2.3.4");
        sent.RootElement.GetProperty("agent_type").GetString().Should().Be("DMA");
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("1.0")]
    [InlineData("v1.0.0")]
    [InlineData("1.0.0-beta")]
    [InlineData("1.0.0\n")]
    public async Task TrialStart_InvalidAgentVersion_Returns400WithoutCallingWbe(string? version)
    {
        var wbeStub = new StubHttpMessageHandler(HttpStatusCode.OK, WbeSuccessBody);
        var client = CreateClient(wbeStub);
        var request = new TrialStartRequest(
            Guid.NewGuid(),
            "DMA",
            PhoneVerified: true,
            AgentVersion: version
        );

        var response = await client.PostAsJsonAsync("/api/v1/subscriptions/trial-start", request);

        response.StatusCode.Should().Be(HttpStatusCode.BadRequest);
        (await response.Content.ReadAsStringAsync()).Should().Contain("AGENT_VERSION_INVALID");
        wbeStub.LastRequest.Should().BeNull(because: "an invalid version must never reach WBE");
    }

    [Fact]
    public async Task TrialStart_ForwardsTheVerifiedWhatsAppIdentityHashFromClaims()
    {
        var (stub, body) = CapturingStub(HttpStatusCode.OK, WbeSuccessBody);
        var client = CreateClient(stub);
        client.DefaultRequestHeaders.Add("x-test-channel", "WHATSAPP");
        client.DefaultRequestHeaders.Add("x-test-external-subject-hash", new string('A', 64));
        var request = new TrialStartRequest(
            Guid.NewGuid(),
            "DMA",
            PhoneVerified: true,
            AgentVersion: "1.0.0"
        );

        var response = await client.PostAsJsonAsync("/api/v1/subscriptions/trial-start", request);

        response.StatusCode.Should().Be(HttpStatusCode.OK);
        using var sent = JsonDocument.Parse(body()!);
        sent.RootElement.GetProperty("identity_subject_hash")
            .GetString()
            .Should()
            .Be(new string('a', 64));
    }

    [Theory]
    [InlineData(null, null)]
    [InlineData("WEB", "64")]
    [InlineData("WHATSAPP", "short")]
    public async Task TrialStart_WithoutAVerifiedIdentityClaimSendsNoHash(
        string? channel,
        string? hash
    )
    {
        var (stub, body) = CapturingStub(HttpStatusCode.OK, WbeSuccessBody);
        var client = CreateClient(stub);
        if (channel is not null)
            client.DefaultRequestHeaders.Add("x-test-channel", channel);
        if (hash is not null)
            client.DefaultRequestHeaders.Add(
                "x-test-external-subject-hash",
                hash == "64" ? new string('b', 64) : hash
            );
        var request = new TrialStartRequest(
            Guid.NewGuid(),
            "DMA",
            PhoneVerified: true,
            AgentVersion: "1.0.0"
        );

        var response = await client.PostAsJsonAsync("/api/v1/subscriptions/trial-start", request);

        response.StatusCode.Should().Be(HttpStatusCode.OK);
        using var sent = JsonDocument.Parse(body()!);
        sent.RootElement.GetProperty("identity_subject_hash")
            .ValueKind.Should()
            .Be(JsonValueKind.Null);
    }

    [Fact]
    public async Task TrialStart_WbeIdentityConflict_PropagatesTheIdentityCode()
    {
        var wbeStub = new StubHttpMessageHandler(
            HttpStatusCode.Conflict,
            """{"detail":{"code":"TRIAL_ALREADY_USED_BY_IDENTITY"}}"""
        );
        var client = CreateClient(wbeStub);
        var request = new TrialStartRequest(
            Guid.NewGuid(),
            "DMA",
            PhoneVerified: true,
            AgentVersion: "1.0.0"
        );

        var response = await client.PostAsJsonAsync("/api/v1/subscriptions/trial-start", request);

        response.StatusCode.Should().Be(HttpStatusCode.Conflict);
        (await response.Content.ReadAsStringAsync())
            .Should()
            .Contain("\"error\":\"TRIAL_ALREADY_USED_BY_IDENTITY\"");
    }
}
