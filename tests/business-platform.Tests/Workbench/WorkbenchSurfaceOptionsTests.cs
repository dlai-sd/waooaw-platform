// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01, C6-02
// Constitutional basis: C-023, C-059, C-063, ADR-051

using System.Net;
using System.Reflection;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class WorkbenchSurfaceOptionsTests(OwnerGatewayIdentityFixture fixture)
    : IClassFixture<OwnerGatewayIdentityFixture>
{
    private static readonly Guid Tenant = Guid.Parse("11111111-1111-4111-8111-111111111111");
    private static readonly Guid Relationship = Guid.Parse("22222222-2222-4222-8222-222222222222");

    private static AdmittedManifestRequest Request(
        string agentType = "lead_generation",
        string agentVersion = "1.0.0",
        string manifestVersion = "m-1"
    ) =>
        new(
            agentType,
            agentVersion,
            manifestVersion,
            "participant-1",
            "EMPLOYER",
            Tenant,
            Relationship,
            "corr-1"
        );

    private static void ReplaceClient(
        DomainAdapterExperienceManifestSource source,
        Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> send
    )
    {
        var field =
            typeof(DomainAdapterExperienceManifestSource).GetField(
                "_client",
                BindingFlags.Instance | BindingFlags.NonPublic
            ) ?? throw new InvalidOperationException("Missing field _client");
        var original = Assert.IsType<HttpClient>(field.GetValue(source));
        field.SetValue(
            source,
            new HttpClient(new StubHandler(send)) { BaseAddress = new Uri("https://adapter.test") }
        );
        original.Dispose();
    }

    private static HttpResponseMessage Json(HttpStatusCode status, string body) =>
        new(status) { Content = new StringContent(body, Encoding.UTF8, "application/json") };

    private DomainAdapterExperienceManifestSource Source(
        out Action<Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>>> replace
    )
    {
        var identity = fixture.CreateIdentity();
        var source = new DomainAdapterExperienceManifestSource(
            identity,
            new Uri("https://adapter.test")
        );
        replace = send => ReplaceClient(source, send);
        return source;
    }

    [Fact]
    public void OptionsDefaultToDisabledWithAFifteenMinuteHandoffAndBindFromTheSection()
    {
        var defaults = new WorkbenchOptions();
        Assert.False(defaults.Enabled);
        Assert.Equal(string.Empty, defaults.HandoffBaseUrl);
        Assert.Equal(900, defaults.HandoffTtlSeconds);
        Assert.Equal("Workbench", WorkbenchOptions.SectionName);

        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    ["Workbench:Enabled"] = "true",
                    ["Workbench:HandoffBaseUrl"] = "https://workbench.test",
                    ["Workbench:HandoffTtlSeconds"] = "120",
                }
            )
            .Build();
        var bound = configuration.GetSection(WorkbenchOptions.SectionName).Get<WorkbenchOptions>()!;

        Assert.True(bound.Enabled);
        Assert.Equal("https://workbench.test", bound.HandoffBaseUrl);
        Assert.Equal(120, bound.HandoffTtlSeconds);
    }

    [Fact]
    public async Task AnUnconfiguredSourceNeverSuppliesAManifest()
    {
        IAdmittedExperienceManifestSource source =
            new UnconfiguredAdmittedExperienceManifestSource();

        Assert.Null(await source.GetAsync(Request(), CancellationToken.None));
    }

    [Fact]
    public async Task ASuccessfulReadSendsASignedScopedRequestAndIsCachedForTheManifestVersion()
    {
        using var source = Source(out var replace);
        var calls = new List<HttpRequestMessage>();
        replace(
            (request, _) =>
            {
                calls.Add(request);
                return Task.FromResult(Json(HttpStatusCode.OK, """{"schemaVersion":"1.0"}"""));
            }
        );

        var first = await source.GetAsync(
            Request("lead generation", "1.0.0+b", "m-1"),
            CancellationToken.None
        );
        var second = await source.GetAsync(
            Request("lead generation", "1.0.0+b", "m-1"),
            CancellationToken.None
        );

        Assert.NotNull(first);
        Assert.Same(first, second);
        var sent = Assert.Single(calls);
        Assert.Equal(HttpMethod.Get, sent.Method);
        Assert.Equal("/internal/v1/employment-interface/manifest", sent.RequestUri!.AbsolutePath);
        Assert.Equal(
            "?agentType=lead%20generation&agentVersion=1.0.0%2Bb&manifestVersion=m-1",
            sent.RequestUri.Query
        );
        Assert.Equal("Bearer", sent.Headers.Authorization?.Scheme);
        Assert.False(string.IsNullOrWhiteSpace(sent.Headers.Authorization?.Parameter));
        Assert.Equal("corr-1", sent.Headers.GetValues("X-Correlation-ID").Single());
        Assert.Equal("1.0", first.RootElement.GetProperty("schemaVersion").GetString());
    }

    [Fact]
    public async Task EachManifestVersionIsReadAndCachedSeparately()
    {
        using var source = Source(out var replace);
        var seen = new List<string>();
        replace(
            (request, _) =>
            {
                seen.Add(request.RequestUri!.Query);
                return Task.FromResult(Json(HttpStatusCode.OK, $$"""{"n":{{seen.Count}}}"""));
            }
        );

        var one = await source.GetAsync(Request(manifestVersion: "m-1"), CancellationToken.None);
        var two = await source.GetAsync(Request(manifestVersion: "m-2"), CancellationToken.None);
        var otherAgent = await source.GetAsync(
            Request(agentType: "other", manifestVersion: "m-1"),
            CancellationToken.None
        );
        var oneAgain = await source.GetAsync(
            Request(manifestVersion: "m-1"),
            CancellationToken.None
        );

        Assert.Equal(3, seen.Count);
        Assert.Equal(1, one!.RootElement.GetProperty("n").GetInt32());
        Assert.Equal(2, two!.RootElement.GetProperty("n").GetInt32());
        Assert.Equal(3, otherAgent!.RootElement.GetProperty("n").GetInt32());
        Assert.Same(one, oneAgain);
    }

    [Theory]
    [InlineData(HttpStatusCode.NotFound)]
    [InlineData(HttpStatusCode.Forbidden)]
    [InlineData(HttpStatusCode.ServiceUnavailable)]
    public async Task ANon200AnswerIsNoManifestAndIsNotCached(HttpStatusCode status)
    {
        using var source = Source(out var replace);
        var answers = new Queue<HttpStatusCode>([status, HttpStatusCode.OK]);
        var calls = 0;
        replace(
            (_, _) =>
            {
                calls++;
                return Task.FromResult(Json(answers.Dequeue(), """{"ok":true}"""));
            }
        );

        Assert.Null(await source.GetAsync(Request(), CancellationToken.None));
        var recovered = await source.GetAsync(Request(), CancellationToken.None);

        Assert.True(recovered!.RootElement.GetProperty("ok").GetBoolean());
        Assert.Equal(2, calls);
    }

    [Fact]
    public async Task AMalformedBodyIsNoManifest()
    {
        using var source = Source(out var replace);
        replace((_, _) => Task.FromResult(Json(HttpStatusCode.OK, "{not json")));

        Assert.Null(await source.GetAsync(Request(), CancellationToken.None));
    }

    [Fact]
    public async Task ATransportFailureOrATimeoutIsNoManifest()
    {
        using var source = Source(out var replace);
        replace((_, _) => throw new HttpRequestException("connection refused"));
        Assert.Null(await source.GetAsync(Request(), CancellationToken.None));

        replace((_, _) => throw new TaskCanceledException("timed out"));
        Assert.Null(await source.GetAsync(Request(), CancellationToken.None));
    }

    [Fact]
    public async Task AnUnexpectedFailureIsNotSwallowed()
    {
        using var source = Source(out var replace);
        replace((_, _) => throw new InvalidOperationException("boom"));

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            source.GetAsync(Request(), CancellationToken.None)
        );
    }

    [Fact]
    public async Task DisposingReleasesTheCachedDocuments()
    {
        var source = Source(out var replace);
        replace((_, _) => Task.FromResult(Json(HttpStatusCode.OK, """{"ok":true}""")));
        var document = (await source.GetAsync(Request(), CancellationToken.None))!;

        source.Dispose();

        Assert.Throws<ObjectDisposedException>(() => document.RootElement.GetProperty("ok"));
    }

    private sealed class StubHandler(
        Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> send
    ) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) => send(request, cancellationToken);
    }
}
