// Implements: work-contracts/WC-062-wc034-f6-voice-interaction.md WC062-02, WC062-05
// constitutional_basis: C-005, C-026, C-042, C-049, C-059, C-063, C-076

using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Text;
using Microsoft.Extensions.Configuration;
using Moq;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Voice;

public sealed class HttpVoiceTranscriptionGatewayTests
{
    [Fact]
    public async Task SendsScopedServiceAssertionAndMapsProviderNeutralResult()
    {
        HttpRequestMessage? captured = null;
        string? capturedBody = null;
        var gateway = CreateGateway(request =>
        {
            captured = request;
            capturedBody = request.Content!.ReadAsStringAsync().GetAwaiter().GetResult();
            return Json(HttpStatusCode.Accepted, """
                {"contractVersion":"1.0.0","orchestrationId":"11111111-1111-4111-8111-111111111111","voiceSessionId":"22222222-2222-4222-8222-222222222222","state":"REVIEW_REQUIRED","locale":"hi-IN","transcript":"namaste","confidenceBand":"REVIEW","updatedAt":"2026-08-12T12:00:00Z"}
                """);
        });

        var result = await gateway.TranscribeAsync(
            Guid.NewGuid(), Guid.NewGuid(), Guid.Parse("22222222-2222-4222-8222-222222222222"),
            Inspection(), "hi-IN", CancellationToken.None);

        Assert.Equal("namaste", result.Text);
        Assert.Equal(0.80m, result.Confidence);
        Assert.NotNull(captured);
        Assert.Equal("voice:orchestrate", new JwtSecurityTokenHandler()
            .ReadJwtToken(captured!.Headers.Authorization!.Parameter).Claims.Single(value => value.Type == "scope").Value);
        Assert.Contains("\"mediaType\":\"audio/webm\"", capturedBody);
        Assert.DoesNotContain("tenant", capturedBody, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task RejectsNonOpaquePayloadReferenceBeforeNetwork()
    {
        var called = false;
        var gateway = CreateGateway(_ => { called = true; return Json(HttpStatusCode.OK, "{}"); });

        await Assert.ThrowsAsync<VoiceUnavailableException>(() => gateway.TranscribeAsync(
            Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), Inspection("storage/path"), "en-IN", CancellationToken.None));
        Assert.False(called);
    }

    [Theory]
    [InlineData(HttpStatusCode.Locked)]
    [InlineData(HttpStatusCode.ServiceUnavailable)]
    [InlineData(HttpStatusCode.BadRequest)]
    public async Task FailsClosedForStoppedUnavailableOrUnexpectedStatus(HttpStatusCode status)
    {
        var gateway = CreateGateway(_ => Json(status, "{}"));
        await Assert.ThrowsAsync<VoiceUnavailableException>(() => gateway.TranscribeAsync(
            Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), Inspection(), "en-IN", CancellationToken.None));
    }

    [Theory]
    [InlineData("UNAVAILABLE", "1.0.0")]
    [InlineData("COMPLETED", "2.0.0")]
    public async Task RejectsNonCompletedOrMismatchedResponse(string state, string version)
    {
        var gateway = CreateGateway(_ => Json(HttpStatusCode.OK, $$"""
            {"contractVersion":"{{version}}","orchestrationId":"11111111-1111-4111-8111-111111111111","voiceSessionId":"22222222-2222-4222-8222-222222222222","state":"{{state}}","locale":"en-IN","transcript":"text","confidenceBand":"HIGH","updatedAt":"2026-08-12T12:00:00Z"}
            """));
        await Assert.ThrowsAsync<VoiceUnavailableException>(() => gateway.TranscribeAsync(
            Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), Inspection(), "en-IN", CancellationToken.None));
    }

    private static VoiceMediaInspection Inspection(string? payloadReference = null) => new(
        new string('a', 64), "audio/webm", "audio/webm", 4096, 12_500, payloadReference ?? Guid.NewGuid().ToString());

    private static HttpResponseMessage Json(HttpStatusCode status, string value) => new(status)
    {
        Content = new StringContent(value, Encoding.UTF8, "application/json"),
    };

    private static HttpVoiceTranscriptionGateway CreateGateway(Func<HttpRequestMessage, HttpResponseMessage> response)
    {
        var client = new HttpClient(new StubHandler(response)) { BaseAddress = new Uri("http://professional-runtime/") };
        var factory = new Mock<IHttpClientFactory>();
        factory.Setup(value => value.CreateClient("VoiceProfessionalRuntime")).Returns(client);
        var configuration = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["Voice:ProfessionalRuntimeJwtSecret"] = "0123456789abcdef0123456789abcdef",
        }).Build();
        return new HttpVoiceTranscriptionGateway(factory.Object, configuration);
    }

    private sealed class StubHandler(Func<HttpRequestMessage, HttpResponseMessage> response) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) =>
            Task.FromResult(response(request));
    }
}