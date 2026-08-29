using System.Security.Cryptography;
using System.Net;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace Waooaw.PhoneIdentity.Tests;

public sealed class PhoneIdentityVerifierTests
{
    private const string WebhookSecret = "wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww";
    private const string PhoneHashKey = "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh";
    private const string InternalSigningKey = "ssssssssssssssssssssssssssssssss";

    private static readonly PhoneIdentityVerifier Verifier = new(new PhoneIdentityOptions(
        WebhookSecret,
        "test-verification-token",
        PhoneHashKey,
        InternalSigningKey,
        "waooaw-phone-identity-test",
        "http://business-platform:5001"));

    [Fact]
    public void ValidMetaWebhookProducesShortLivedOpaqueProof()
    {
        var now = DateTimeOffset.UtcNow;
        var rawPhone = "+919876543210";
        var body = JsonSerializer.Serialize(new
        {
            messageId = "wamid-valid-1",
            timestamp = now.ToUnixTimeSeconds(),
            from = rawPhone,
            text = "status",
            riskTier = "TIER_1_LOW_RISK",
        }, PhoneIdentityJson.Options);

        var proof = Verifier.Verify(body, SignWebhook(body), now);
        var serialized = JsonSerializer.Serialize(proof, PhoneIdentityJson.Options);

        Assert.Equal("wamid-valid-1", proof.MessageId);
        Assert.Equal("waooaw-phone-identity-test", proof.Audience);
        Assert.Equal("AAL1_CHANNEL", proof.AuthenticationAssurance);
        Assert.Equal(TimeSpan.FromMinutes(5), proof.ExpiresAt - proof.VerifiedAt);
        Assert.DoesNotContain(rawPhone, serialized);
        Assert.Matches("^[0-9a-f]{64}$", proof.PhoneSubjectHash);
    }

    [Fact]
    public void InvalidSignatureFailsBeforeProofCreation()
    {
        var now = DateTimeOffset.UtcNow;
        var body = ValidBody(now, "wamid-invalid-signature");

        var exception = Assert.Throws<PhoneIdentityVerificationException>(() =>
            Verifier.Verify(body, "sha256=00", now));

        Assert.Equal(403, exception.StatusCode);
        Assert.Equal("WHATSAPP_SIGNATURE_INVALID", exception.Code);
    }

    [Fact]
    public void StaleTimestampIsRejected()
    {
        var now = DateTimeOffset.UtcNow;
        var body = ValidBody(now.AddMinutes(-6), "wamid-stale");

        var exception = Assert.Throws<PhoneIdentityVerificationException>(() =>
            Verifier.Verify(body, SignWebhook(body), now));

        Assert.Equal(409, exception.StatusCode);
        Assert.Equal("WHATSAPP_REPLAY_WINDOW_EXCEEDED", exception.Code);
    }

    [Fact]
    public void FutureTimestampOutsideClockSkewIsRejected()
    {
        var now = DateTimeOffset.UtcNow;
        var body = ValidBody(now.AddSeconds(31), "wamid-future");

        var exception = Assert.Throws<PhoneIdentityVerificationException>(() =>
            Verifier.Verify(body, SignWebhook(body), now));

        Assert.Equal(409, exception.StatusCode);
        Assert.Equal("WHATSAPP_REPLAY_WINDOW_EXCEEDED", exception.Code);
    }

    [Fact]
    public void InvalidPhoneIsRejected()
    {
        var now = DateTimeOffset.UtcNow;
        var body = JsonSerializer.Serialize(new
        {
            messageId = "wamid-invalid-phone",
            timestamp = now.ToUnixTimeSeconds(),
            from = "9876543210",
            text = "status",
        }, PhoneIdentityJson.Options);

        var exception = Assert.Throws<PhoneIdentityVerificationException>(() =>
            Verifier.Verify(body, SignWebhook(body), now));

        Assert.Equal(400, exception.StatusCode);
        Assert.Equal("WHATSAPP_PAYLOAD_INVALID", exception.Code);
    }

    [Fact]
    public void InternalProofSignatureChangesWhenPayloadIsTampered()
    {
        var original = "{\"messageId\":\"one\"}";
        var tampered = "{\"messageId\":\"two\"}";

        Assert.NotEqual(Verifier.SignProof(original), Verifier.SignProof(tampered));
    }

    [Fact]
    public void DuplicateMetaMessageIsRejected()
    {
        var now = DateTimeOffset.UtcNow;
        var body = ValidBody(now, $"wamid-duplicate-{Guid.NewGuid():N}");

        Verifier.Verify(body, SignWebhook(body), now);
        var exception = Assert.Throws<PhoneIdentityVerificationException>(() =>
            Verifier.Verify(body, SignWebhook(body), now.AddSeconds(1)));

        Assert.Equal(409, exception.StatusCode);
        Assert.Equal("WHATSAPP_MESSAGE_REPLAYED", exception.Code);
    }

    private static string ValidBody(DateTimeOffset sentAt, string messageId) =>
        JsonSerializer.Serialize(new
        {
            messageId,
            timestamp = sentAt.ToUnixTimeSeconds(),
            from = "+919876543210",
            text = "status",
        }, PhoneIdentityJson.Options);

    private static string SignWebhook(string body)
    {
        var digest = HMACSHA256.HashData(
            Encoding.UTF8.GetBytes(WebhookSecret), Encoding.UTF8.GetBytes(body));
        return $"sha256={Convert.ToHexStringLower(digest)}";
    }
}

public sealed class PhoneIdentityHttpBoundaryTests
{
    private const string WebhookSecret = "test-meta-webhook-secret-at-least-32-bytes";

    [Fact]
    public async Task HealthReportsHealthy()
    {
        await using var application = new PhoneIdentityApplication();
        using var client = application.CreateClient();

        var response = await client.GetAsync("/health");

        Assert.True(response.IsSuccessStatusCode);
        Assert.Contains("healthy", await response.Content.ReadAsStringAsync());
    }

    [Fact]
    public async Task MetaVerificationAcceptsMatchingToken()
    {
        await using var application = new PhoneIdentityApplication();
        using var client = application.CreateClient();

        var response = await client.GetAsync(
            "/webhooks/meta?hub.mode=subscribe&hub.challenge=challenge-value&hub.verify_token=test-verification-token");

        Assert.True(response.IsSuccessStatusCode);
        Assert.Equal("challenge-value", await response.Content.ReadAsStringAsync());
    }

    [Fact]
    public async Task MetaVerificationRejectsWrongToken()
    {
        await using var application = new PhoneIdentityApplication();
        using var client = application.CreateClient();

        var response = await client.GetAsync(
            "/webhooks/meta?hub.mode=subscribe&hub.challenge=challenge-value&hub.verify_token=wrong-token-value");

        Assert.Equal(403, (int)response.StatusCode);
    }

    [Fact]
    public async Task MetaPostRejectsInvalidSignatureBeforeDependencyCall()
    {
        await using var application = new PhoneIdentityApplication();
        using var client = application.CreateClient();
        using var request = new HttpRequestMessage(HttpMethod.Post, "/webhooks/meta")
        {
            Content = new StringContent("{}", Encoding.UTF8, "application/json"),
        };
        request.Headers.Add("X-Hub-Signature-256", "sha256=00");

        var response = await client.SendAsync(request);

        Assert.Equal(403, (int)response.StatusCode);
    }

    [Fact]
    public async Task ValidMetaPostForwardsSignedProofToBusinessPlatform()
    {
        var downstream = new RecordingHandler(HttpStatusCode.OK, "{\"status\":\"ACCEPTED\"}");
        await using var application = new PhoneIdentityApplication(downstream);
        using var client = application.CreateClient();
        var body = ValidBody($"wamid-http-{Guid.NewGuid():N}");
        using var request = SignedRequest(body);

        var response = await client.SendAsync(request);

        Assert.True(response.IsSuccessStatusCode);
        Assert.Equal("/internal/identity/whatsapp-proofs", downstream.RequestUri?.AbsolutePath);
        Assert.StartsWith("sha256=", downstream.PhoneSignature);
        Assert.DoesNotContain("+919876543210", downstream.RequestBody);
    }

    [Fact]
    public async Task BusinessPlatformOutageReturnsServiceUnavailable()
    {
        await using var application = new PhoneIdentityApplication(new RecordingHandler(throws: true));
        using var client = application.CreateClient();
        var body = ValidBody($"wamid-outage-{Guid.NewGuid():N}");
        using var request = SignedRequest(body);

        var response = await client.SendAsync(request);

        Assert.Equal(503, (int)response.StatusCode);
    }

    [Fact]
    public async Task SignedMalformedPayloadReturnsBadRequest()
    {
        await using var application = new PhoneIdentityApplication();
        using var client = application.CreateClient();
        const string body = "not-json";
        using var request = SignedRequest(body);

        var response = await client.SendAsync(request);

        Assert.Equal(400, (int)response.StatusCode);
    }

    [Fact]
    public void ConfigurationRejectsMissingSecrets()
    {
        var configuration = new ConfigurationBuilder().AddInMemoryCollection().Build();

        Assert.Throws<InvalidOperationException>(() => PhoneIdentityOptions.FromConfiguration(configuration));
    }

    private static string ValidBody(string messageId) => JsonSerializer.Serialize(new
    {
        messageId,
        timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
        from = "+919876543210",
        text = "status",
        riskTier = "TIER_1_LOW_RISK",
    }, PhoneIdentityJson.Options);

    private static HttpRequestMessage SignedRequest(string body)
    {
        var digest = HMACSHA256.HashData(Encoding.UTF8.GetBytes(WebhookSecret), Encoding.UTF8.GetBytes(body));
        var request = new HttpRequestMessage(HttpMethod.Post, "/webhooks/meta")
        {
            Content = new StringContent(body, Encoding.UTF8, "application/json"),
        };
        request.Headers.Add("X-Hub-Signature-256", $"sha256={Convert.ToHexStringLower(digest)}");
        return request;
    }

    private sealed class PhoneIdentityApplication(HttpMessageHandler? downstream = null)
        : WebApplicationFactory<Program>
    {
        protected override void ConfigureWebHost(IWebHostBuilder builder)
        {
            builder
                .UseSetting("PhoneIdentity:WebhookSecret", WebhookSecret)
                .UseSetting("PhoneIdentity:VerifyToken", "test-verification-token")
                .UseSetting("PhoneIdentity:PhoneHashKey", "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh")
                .UseSetting("PhoneIdentity:InternalSigningKey", "ssssssssssssssssssssssssssssssss")
                .UseSetting("PhoneIdentity:InternalAudience", "waooaw-phone-identity-test")
                .UseSetting("PhoneIdentity:BusinessPlatformBaseUrl", "http://business-platform:5001");
            if (downstream is not null)
                builder.ConfigureServices(services => services.AddSingleton<IHttpClientFactory>(
                    new StubHttpClientFactory(downstream)));
        }
    }

    private sealed class StubHttpClientFactory(HttpMessageHandler handler) : IHttpClientFactory
    {
        public HttpClient CreateClient(string name) => new(handler, disposeHandler: false)
        {
            BaseAddress = new Uri("http://business-platform:5001"),
        };
    }

    private sealed class RecordingHandler(
        HttpStatusCode statusCode = HttpStatusCode.OK,
        string responseBody = "{}",
        bool throws = false) : HttpMessageHandler
    {
        public Uri? RequestUri { get; private set; }
        public string? PhoneSignature { get; private set; }
        public string RequestBody { get; private set; } = string.Empty;

        protected override async Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            if (throws)
                throw new HttpRequestException("downstream unavailable");
            RequestUri = request.RequestUri;
            PhoneSignature = request.Headers.GetValues("X-WAOOAW-Phone-Signature").Single();
            RequestBody = await request.Content!.ReadAsStringAsync(cancellationToken);
            return new HttpResponseMessage(statusCode)
            {
                Content = new StringContent(responseBody, Encoding.UTF8, "application/json"),
            };
        }
    }
}
