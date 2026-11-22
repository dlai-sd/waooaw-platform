// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R003
// constitutional_basis: C-023, C-059, C-063, C-083, C-084

using System.Net;
using System.Text.Json;
using FluentAssertions;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ProviderCredentialTesterTests
{
    private const string Secret = "sk-test-secret-value-0001";
    private const string BodySentinel = "provider-body-sentinel-7731";
    private static readonly IPAddress PublicAddress = IPAddress.Parse("93.184.216.34");

    private sealed class RecordingHandler(
        HttpStatusCode status,
        string body = "",
        string? location = null
    ) : HttpMessageHandler
    {
        public List<HttpRequestMessage> Requests { get; } = [];

        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        )
        {
            Requests.Add(request);
            var response = new HttpResponseMessage(status) { Content = new StringContent(body) };
            if (location is not null)
                response.Headers.Location = new Uri(location);
            return Task.FromResult(response);
        }
    }

    private static ProviderCredentialTester Tester(
        RecordingHandler handler,
        out List<IPAddress> pinned,
        params IPAddress[] resolved
    )
    {
        var pins = new List<IPAddress>();
        pinned = pins;
        return new ProviderCredentialTester(
            (_, _) => Task.FromResult(resolved.Length == 0 ? new[] { PublicAddress } : resolved),
            address =>
            {
                pins.Add(address);
                return handler;
            }
        );
    }

    private static ProviderTestTarget Target(
        string provider = "openai",
        string? url = "https://api.openai.com/v1/models",
        string? scheme = ProviderAuthSchemes.Bearer,
        string? header = null
    ) => new(provider, url, scheme, header);

    [Fact]
    public async Task NoTestUrlIsNotTestableAndSendsNothing()
    {
        var handler = new RecordingHandler(HttpStatusCode.OK);

        var result = await Tester(handler, out var pinned)
            .TestAsync(Target(url: null, scheme: null), Secret, default);

        result.Outcome.Should().Be(ProviderTestOutcomes.NotTestable);
        handler.Requests.Should().BeEmpty();
        pinned.Should().BeEmpty();
    }

    [Theory]
    [InlineData("127.0.0.1")]
    [InlineData("10.1.2.3")]
    [InlineData("172.16.5.5")]
    [InlineData("192.168.0.10")]
    [InlineData("169.254.169.254")]
    [InlineData("100.64.0.1")]
    [InlineData("0.0.0.0")]
    [InlineData("::1")]
    [InlineData("fe80::1")]
    [InlineData("fd00::1")]
    [InlineData("::ffff:10.0.0.1")]
    [InlineData("::ffff:169.254.169.254")]
    public async Task AnyNonPublicResolvedAddressIsRejectedBeforeAnythingIsSent(string address)
    {
        var handler = new RecordingHandler(HttpStatusCode.OK);

        var result = await Tester(handler, out var pinned, IPAddress.Parse(address))
            .TestAsync(Target(), Secret, default);

        result.Outcome.Should().Be(ProviderTestOutcomes.Failed);
        result.Detail.Should().Contain("blocked address");
        handler.Requests.Should().BeEmpty();
        pinned.Should().BeEmpty();
    }

    [Fact]
    public async Task OneBlockedAddressAmongPublicOnesRejectsTheHost()
    {
        var handler = new RecordingHandler(HttpStatusCode.OK);

        var result = await Tester(handler, out _, PublicAddress, IPAddress.Parse("10.0.0.9"))
            .TestAsync(Target(), Secret, default);

        result.Outcome.Should().Be(ProviderTestOutcomes.Failed);
        handler.Requests.Should().BeEmpty();
    }

    [Fact]
    public async Task LoopbackHostNameIsRejectedWithTheRealResolver()
    {
        var result = await new ProviderCredentialTester().TestAsync(
            Target(url: "https://localhost/v1/models"),
            Secret,
            default
        );

        result.Outcome.Should().Be(ProviderTestOutcomes.Failed);
        result.Detail.Should().NotContain(Secret);
    }

    [Theory]
    [InlineData("http://api.openai.com/v1/models")]
    [InlineData("https://user:pw@api.openai.com/v1/models")]
    [InlineData("https://api.openai.com:8443/v1/models")]
    [InlineData("https://api.openai.com/v1/models#fragment")]
    [InlineData("ftp://api.openai.com/v1/models")]
    [InlineData("not a url")]
    public async Task OnlyPlainHttpsUrlsAreSent(string url)
    {
        var handler = new RecordingHandler(HttpStatusCode.OK);

        var result = await Tester(handler, out _).TestAsync(Target(url: url), Secret, default);

        result.Outcome.Should().Be(ProviderTestOutcomes.Failed);
        handler.Requests.Should().BeEmpty();
    }

    [Fact]
    public async Task SuccessIsPassedAndTheConnectionIsPinnedToTheCheckedAddress()
    {
        var handler = new RecordingHandler(HttpStatusCode.OK, BodySentinel);

        var result = await Tester(handler, out var pinned).TestAsync(Target(), Secret, default);

        result
            .Should()
            .Be(new ProviderCredentialTestResult(ProviderTestOutcomes.Passed, "HTTP 200", 200));
        pinned.Should().Equal(PublicAddress);
        handler.Requests.Should().ContainSingle();
        handler.Requests[0].Method.Should().Be(HttpMethod.Get);
        handler.Requests[0].RequestUri!.ToString().Should().Be("https://api.openai.com/v1/models");
    }

    [Theory]
    [InlineData(HttpStatusCode.Unauthorized, "HTTP 401")]
    [InlineData(HttpStatusCode.Forbidden, "HTTP 403")]
    [InlineData(HttpStatusCode.InternalServerError, "HTTP 500")]
    public async Task NonSuccessIsFailedWithAShortReasonAndNoProviderBody(
        HttpStatusCode status,
        string detail
    )
    {
        var handler = new RecordingHandler(status, BodySentinel);

        var result = await Tester(handler, out _).TestAsync(Target(), Secret, default);

        result.Outcome.Should().Be(ProviderTestOutcomes.Failed);
        result.Detail.Should().Be(detail);
        JsonSerializer.Serialize(result).Should().NotContain(BodySentinel).And.NotContain(Secret);
    }

    [Fact]
    public async Task RedirectsAreNeverFollowed()
    {
        var handler = new RecordingHandler(
            HttpStatusCode.Redirect,
            BodySentinel,
            "http://169.254.169.254/latest/meta-data"
        );

        var result = await Tester(handler, out _).TestAsync(Target(), Secret, default);

        result.Outcome.Should().Be(ProviderTestOutcomes.Failed);
        result.Detail.Should().Be("HTTP 302");
        handler.Requests.Should().ContainSingle();
        JsonSerializer
            .Serialize(result)
            .Should()
            .NotContain("169.254")
            .And.NotContain(BodySentinel);
    }

    [Fact]
    public void TheRealHandlerDoesNotFollowRedirects()
    {
        var handler = (SocketsHttpHandler)ProviderCredentialTester.PinnedHandler(PublicAddress);

        handler.AllowAutoRedirect.Should().BeFalse();
        handler.UseProxy.Should().BeFalse();
        handler.ConnectCallback.Should().NotBeNull();
    }

    [Theory]
    [InlineData("openai", ProviderAuthSchemes.Bearer, null, "Authorization", "Bearer " + Secret)]
    [InlineData("anthropic", ProviderAuthSchemes.XApiKey, null, "x-api-key", Secret)]
    [InlineData("google", ProviderAuthSchemes.XGoogApiKey, null, "x-goog-api-key", Secret)]
    [InlineData("acme-sms", ProviderAuthSchemes.Header, "X-Acme-Token", "X-Acme-Token", Secret)]
    public async Task TheCredentialIsSentOnlyInTheConfiguredHeader(
        string provider,
        string scheme,
        string? customHeader,
        string expectedHeader,
        string expectedValue
    )
    {
        var handler = new RecordingHandler(HttpStatusCode.OK);

        await Tester(handler, out _)
            .TestAsync(
                Target(provider, "https://api.example.com/v1/ping", scheme, customHeader),
                Secret,
                default
            );

        var request = handler.Requests.Should().ContainSingle().Subject;
        request.Headers.GetValues(expectedHeader).Should().Equal(expectedValue);
        request.RequestUri!.Query.Should().BeEmpty();
        request.Headers.Contains("anthropic-version").Should().Be(provider == "anthropic");
        if (provider == "anthropic")
            request.Headers.GetValues("anthropic-version").Should().Equal("2023-06-01");
    }

    [Theory]
    [InlineData("abc\r\nX-Injected: 1")]
    [InlineData("abc\ndef")]
    public async Task ControlCharactersInTheValueAreNeverSent(string value)
    {
        var handler = new RecordingHandler(HttpStatusCode.OK);

        var result = await Tester(handler, out _).TestAsync(Target(), value, default);

        result.Outcome.Should().Be(ProviderTestOutcomes.Failed);
        handler.Requests.Should().BeEmpty();
    }

    [Fact]
    public async Task TransportFailureIsFailedWithoutDetailFromTheException()
    {
        var tester = new ProviderCredentialTester(
            (_, _) => Task.FromResult(new[] { PublicAddress }),
            _ => new ThrowingHandler()
        );

        var result = await tester.TestAsync(Target(), Secret, default);

        result.Outcome.Should().Be(ProviderTestOutcomes.Failed);
        result.Detail.Should().Be("The provider could not be reached.");
    }

    private sealed class ThrowingHandler : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) => throw new HttpRequestException($"connect failed carrying {Secret} {BodySentinel}");
    }
}
