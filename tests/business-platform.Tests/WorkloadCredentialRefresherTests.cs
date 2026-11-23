// Implements: ADR-046 sections 5.1, 5.3 and 12.2 D4, D6, D9; workload-identity-cloud-issuance-contract.md section 8
// constitutional_basis: C-023, C-059, C-063, C-083, C-084, C-085

using System.Net;
using System.Text;
using FluentAssertions;
using Microsoft.Extensions.Logging;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class WorkloadCredentialRefresherTests : IDisposable
{
    private static readonly WorkloadCredentialSettings Settings = new(
        "business-platform",
        TestPki.TrustDomain
    );

    private readonly TestPki _pki = new();
    private readonly TestClock _clock;
    private readonly WorkloadIdentityClient _identity;
    private readonly OwnerLinkState _links = new();
    private readonly StubReader _reader = new();
    private readonly LogCapture _log = new();
    private readonly StubOwners _owners = new();

    public WorkloadCredentialRefresherTests()
    {
        _clock = new TestClock(_pki.Now);
        _identity = WorkloadIdentityClient.CreateReloadable(Settings, _clock);
    }

    [Fact]
    public async Task FirstReadLoadsTheCredentialAndProbesEveryOwner()
    {
        using var refresher = Create(out var prober);
        _reader.Set(_pki.Create(new CredentialOptions { Version = 10 }));

        await refresher.RefreshOnceAsync(CancellationToken.None);

        _identity.GetStatus().State.Should().Be("READY");
        _log.Text.Should().Contain("state=loaded").And.Contain("bundle_version=10");
        _links
            .Snapshot()
            .Should()
            .Equal(
                new Dictionary<string, string>
                {
                    ["billing"] = "READY",
                    ["professional-runtime"] = "UNCONFIGURED",
                }
            );
        _owners.Paths.Should().Equal(OwnerLinkProber.ProbeRoute);
        prober.Dispose();
    }

    [Fact]
    public async Task AnUnavailableOwnerLinkIsReprobedAtTheMinimumIntervalUntilItRecovers()
    {
        using var refresher = Create(out var prober, refreshSeconds: 300);
        _reader.Set(_pki.Create(new CredentialOptions { Version = 10 }));
        _owners.Throw = new HttpRequestException("owner is cold-starting");

        await refresher.RefreshOnceAsync(CancellationToken.None);

        _links.Snapshot()["billing"].Should().Be("UNAVAILABLE");
        refresher
            .NextDelaySeconds()
            .Should()
            .Be(WorkloadCredentialOptions.MinimumRefreshSeconds);

        _owners.Throw = null;
        await refresher.RefreshOnceAsync(CancellationToken.None);

        _links.Snapshot()["billing"].Should().Be("READY");
        refresher.NextDelaySeconds().Should().Be(300);
        prober.Dispose();
    }

    [Fact]
    public async Task VaultFailureKeepsTheLastCredentialAndNeverDowngradesTheVersion()
    {
        using var refresher = Create(out _);
        var current = _pki.Create(new CredentialOptions { Version = 20 });
        _reader.Set(current);
        await refresher.RefreshOnceAsync(CancellationToken.None);

        foreach (
            var failure in new Exception[]
            {
                new WorkloadCredentialReadException("VAULT_UNREACHABLE"),
                new InvalidOperationException("unexpected"),
            }
        )
        {
            _reader.Fail(failure);
            await refresher.RefreshOnceAsync(CancellationToken.None);
        }
        _reader.Set(_pki.Create(new CredentialOptions { Version = 19 }));
        await refresher.RefreshOnceAsync(CancellationToken.None);
        _reader.Set("UNISSUED", current.Trust);
        await refresher.RefreshOnceAsync(CancellationToken.None);

        _identity.IsAvailable.Should().BeTrue();
        _identity.GetStatus().BundleVersion.Should().Be(20);
        _log.Text.Should()
            .Contain("state=read_failed reason=VAULT_UNREACHABLE")
            .And.Contain("state=read_failed reason=InvalidOperationException")
            .And.Contain("state=rejected reason=ROLLBACK")
            .And.Contain("state=unissued reason=NO_CREDENTIAL");
    }

    [Fact]
    public async Task UnissuedVaultLeavesTheLinkUnavailableWithoutCrashing()
    {
        using var refresher = Create(out _);
        _reader.Set("UNISSUED", "UNISSUED");

        await refresher.RefreshOnceAsync(CancellationToken.None);

        _identity.IsAvailable.Should().BeFalse();
        _links.Snapshot()["billing"].Should().Be("UNAVAILABLE");
        _log.Text.Should().Contain("state=unissued");
    }

    [Fact]
    public async Task ExpiryAndRevocationAreLoggedOnceAndTheOwnersBecomeUnavailable()
    {
        using var refresher = Create(out _);
        _reader.Set(_pki.Create(new CredentialOptions { Version = 10 }));
        await refresher.RefreshOnceAsync(CancellationToken.None);
        _links.Snapshot()["billing"].Should().Be("READY");

        _clock.Advance(TimeSpan.FromHours(25));
        _reader.Fail(new WorkloadCredentialReadException("VAULT_UNREACHABLE"));
        await refresher.RefreshOnceAsync(CancellationToken.None);
        await refresher.RefreshOnceAsync(CancellationToken.None);

        _links.Snapshot()["billing"].Should().Be("UNAVAILABLE");
        _log.Count("state=unavailable reason=EXPIRED_OR_REVOKED").Should().Be(1);
    }

    [Fact]
    public async Task ProbeFailureDoesNotStopTheRefresh()
    {
        using var refresher = Create(out _);
        _reader.Set(_pki.Create(new CredentialOptions { Version = 10 }));
        _owners.Throw = new NotSupportedException("probe");

        await refresher.RefreshOnceAsync(CancellationToken.None);

        _identity.IsAvailable.Should().BeTrue();
        _log.Text.Should().Contain("owner_link_probe_failed reason=NotSupportedException");
    }

    [Fact]
    public async Task HostedLoopSurvivesVaultFailureAndStopsOnCancellation()
    {
        using var refresher = Create(out _);
        _reader.Fail(new WorkloadCredentialReadException("VAULT_UNREACHABLE"));

        await refresher.StartAsync(CancellationToken.None);
        await _reader.WaitForReadsAsync(1);
        await refresher.StopAsync(CancellationToken.None);

        _identity.IsAvailable.Should().BeFalse();
        _log.Text.Should().Contain("state=read_failed");
    }

    [Fact]
    public async Task LogsCarryOnlyStateReasonAndVersionAndNeverKeyMaterial()
    {
        using var refresher = Create(out _);
        var issued = _pki.Create(new CredentialOptions { Version = 10 });
        _reader.Set(issued);
        await refresher.RefreshOnceAsync(CancellationToken.None);
        _reader.Set(issued.Bundle.Replace("-----BEGIN", "BROKEN"), issued.Trust);
        await refresher.RefreshOnceAsync(CancellationToken.None);
        _reader.Fail(new WorkloadCredentialReadException("SECRET_READ_DENIED"));
        await refresher.RefreshOnceAsync(CancellationToken.None);

        _log.Text.Should()
            .NotContain("PRIVATE KEY")
            .And.NotContain("BEGIN")
            .And.NotContain(issued.TlsKeyPem);
        _log.Text.Should().NotContain(TestPki.Identity("business-platform"));
    }

    private static readonly OwnerLinkTarget[] Targets =
    [
        new("billing", "billing-engine", new Uri("https://billing.test")),
        new("professional-runtime", "professional-runtime", null),
    ];

    private WorkloadCredentialRefresher Create(out OwnerLinkProber prober, int refreshSeconds = 30)
    {
        prober = new OwnerLinkProber(
            _identity,
            _links,
            Targets,
            (uri, _) => new HttpClient(_owners.Handler(_identity)) { BaseAddress = uri }
        );
        return new WorkloadCredentialRefresher(
            _identity,
            _reader,
            prober,
            new WorkloadCredentialOptions { Source = "keyvault", RefreshSeconds = refreshSeconds },
            _log
        );
    }

    public void Dispose()
    {
        _identity.Dispose();
        _pki.Dispose();
    }

    private sealed class StubReader : IWorkloadCredentialReader
    {
        private Func<WorkloadCredentialDocuments> _next = () =>
            throw new WorkloadCredentialReadException("VAULT_UNREACHABLE");
        private int _reads;

        public void Set(IssuedCredentials issued) => Set(issued.Bundle, issued.Trust);

        public void Set(string bundle, string trust) =>
            _next = () => new WorkloadCredentialDocuments(bundle, trust);

        public void Fail(Exception exception) => _next = () => throw exception;

        public Task<WorkloadCredentialDocuments> ReadAsync(CancellationToken cancellationToken)
        {
            Interlocked.Increment(ref _reads);
            return Task.FromResult(_next());
        }

        public async Task WaitForReadsAsync(int count)
        {
            for (var attempt = 0; attempt < 200 && Volatile.Read(ref _reads) < count; attempt++)
                await Task.Delay(10);
            Volatile.Read(ref _reads).Should().BeGreaterThanOrEqualTo(count);
        }
    }

    private sealed class StubOwners
    {
        public List<string> Paths { get; } = [];
        public Exception? Throw { get; set; }

        public HttpMessageHandler Handler(WorkloadIdentityClient identity) =>
            new Responder(request =>
            {
                Paths.Add(request.RequestUri!.AbsolutePath);
                if (Throw is not null)
                    throw Throw;
                return Json(
                    HttpStatusCode.OK,
                    $$"""{"status":"ok","peer_identity_uri":"{{identity.GetOwnIdentityUri()}}"}"""
                );
            });
    }

    internal static HttpResponseMessage Json(HttpStatusCode status, string body) =>
        new(status) { Content = new StringContent(body, Encoding.UTF8, "application/json") };

    internal sealed class Responder(Func<HttpRequestMessage, HttpResponseMessage> respond)
        : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) => Task.FromResult(respond(request));
    }

    private sealed class LogCapture : ILogger<WorkloadCredentialRefresher>
    {
        private readonly List<string> _lines = [];

        public string Text
        {
            get
            {
                lock (_lines)
                    return string.Join('\n', _lines);
            }
        }

        public int Count(string fragment)
        {
            lock (_lines)
                return _lines.Count(line => line.Contains(fragment, StringComparison.Ordinal));
        }

        public IDisposable? BeginScope<TState>(TState state)
            where TState : notnull => null;

        public bool IsEnabled(LogLevel logLevel) => true;

        public void Log<TState>(
            LogLevel logLevel,
            EventId eventId,
            TState state,
            Exception? exception,
            Func<TState, Exception?, string> formatter
        )
        {
            lock (_lines)
                _lines.Add($"{formatter(state, exception)} {exception}");
        }
    }
}

public sealed class OwnerLinkTests : IDisposable
{
    private static readonly WorkloadCredentialSettings Settings = new(
        "business-platform",
        TestPki.TrustDomain
    );

    private readonly TestPki _pki = new();
    private readonly TestClock _clock;
    private readonly WorkloadIdentityClient _identity;
    private readonly OwnerLinkTarget _billing = new(
        "billing",
        "billing-engine",
        new Uri("https://billing.test")
    );

    public OwnerLinkTests()
    {
        _clock = new TestClock(_pki.Now);
        _identity = WorkloadIdentityClient.CreateReloadable(Settings, _clock);
    }

    [Fact]
    public void StateReportsUpperCaseValuesSortedByOwner()
    {
        var state = new OwnerLinkState();
        state.Set("professional-runtime", OwnerLinkStatus.Unavailable);
        state.Set("billing", OwnerLinkStatus.Ready);
        state.Set("zeta", OwnerLinkStatus.Unconfigured);
        state.Set("zeta", OwnerLinkStatus.Unconfigured);

        state.Snapshot().Keys.Should().Equal("billing", "professional-runtime", "zeta");
        state.Snapshot().Values.Should().Equal("READY", "UNAVAILABLE", "UNCONFIGURED");
    }

    [Fact]
    public async Task OwnerWithoutABaseUrlIsUnconfiguredEvenWhenCredentialsAreMissing()
    {
        var state = new OwnerLinkState();
        using var prober = new OwnerLinkProber(
            _identity,
            state,
            [new OwnerLinkTarget("billing", "billing-engine", null)],
            (_, _) => throw new InvalidOperationException("must not be built")
        );

        await prober.ProbeAllAsync(CancellationToken.None);

        state.Snapshot()["billing"].Should().Be("UNCONFIGURED");
    }

    [Fact]
    public async Task OwnerIsUnavailableWithoutACredentialAndNoRequestIsSent()
    {
        var state = new OwnerLinkState();
        var requests = 0;
        using var prober = Prober(
            state,
            _ =>
            {
                requests++;
                return WorkloadCredentialRefresherTests.Json(HttpStatusCode.OK, "{}");
            }
        );

        await prober.ProbeAllAsync(CancellationToken.None);

        state.Snapshot()["billing"].Should().Be("UNAVAILABLE");
        requests.Should().Be(0);
    }

    [Fact]
    public async Task LinkFollowsTheOwnerThroughReadyUnavailableAndReady()
    {
        Load(10);
        var state = new OwnerLinkState();
        var mode = "ok";
        var builds = 0;
        using var prober = new OwnerLinkProber(
            _identity,
            state,
            [_billing],
            (uri, _) =>
            {
                builds++;
                return new HttpClient(
                    new WorkloadCredentialRefresherTests.Responder(_ => Respond(mode))
                )
                {
                    BaseAddress = uri,
                };
            }
        );

        await prober.ProbeAllAsync(CancellationToken.None);
        var first = state.Snapshot()["billing"];
        mode = "down";
        await prober.ProbeAllAsync(CancellationToken.None);
        var second = state.Snapshot()["billing"];
        mode = "ok";
        await prober.ProbeAllAsync(CancellationToken.None);

        (first, second, state.Snapshot()["billing"]).Should().Be(("READY", "UNAVAILABLE", "READY"));
        builds.Should().Be(1);
    }

    [Theory]
    [InlineData("status-503")]
    [InlineData("wrong-peer")]
    [InlineData("target-peer")]
    [InlineData("not-ok")]
    [InlineData("no-peer")]
    [InlineData("array")]
    [InlineData("bad-json")]
    [InlineData("http-error")]
    [InlineData("canceled")]
    public async Task AnythingOtherThanAnOkResponseFromTheExpectedPeerIsUnavailable(string mode)
    {
        Load(10);
        var state = new OwnerLinkState();
        using var prober = Prober(state, _ => Respond(mode));

        await prober.ProbeAllAsync(CancellationToken.None);

        state.Snapshot()["billing"].Should().Be("UNAVAILABLE");
    }

    [Fact]
    public async Task ExpiredCredentialTurnsAReadyLinkUnavailableWithoutAnotherRequest()
    {
        Load(10);
        var state = new OwnerLinkState();
        var requests = 0;
        using var prober = Prober(
            state,
            _ =>
            {
                requests++;
                return Respond("ok");
            }
        );
        await prober.ProbeAllAsync(CancellationToken.None);

        _clock.Advance(TimeSpan.FromHours(25));
        await prober.ProbeAllAsync(CancellationToken.None);

        state.Snapshot()["billing"].Should().Be("UNAVAILABLE");
        requests.Should().Be(1);
    }

    private OwnerLinkProber Prober(
        OwnerLinkState state,
        Func<HttpRequestMessage, HttpResponseMessage> respond
    ) =>
        new(
            _identity,
            state,
            [_billing],
            (uri, _) =>
                new HttpClient(new WorkloadCredentialRefresherTests.Responder(respond))
                {
                    BaseAddress = uri,
                }
        );

    private HttpResponseMessage Respond(string mode)
    {
        var peer = _identity.GetOwnIdentityUri();
        return mode switch
        {
            "ok" => WorkloadCredentialRefresherTests.Json(
                HttpStatusCode.OK,
                $$"""{"status":"ok","peer_identity_uri":"{{peer}}"}"""
            ),
            "status-503" => WorkloadCredentialRefresherTests.Json(
                HttpStatusCode.ServiceUnavailable,
                $$"""{"status":"ok","peer_identity_uri":"{{peer}}"}"""
            ),
            "wrong-peer" => WorkloadCredentialRefresherTests.Json(
                HttpStatusCode.OK,
                """{"status":"ok","peer_identity_uri":"spiffe://waooaw.test/workload/other"}"""
            ),
            "target-peer" => WorkloadCredentialRefresherTests.Json(
                HttpStatusCode.OK,
                $$"""{"status":"ok","peer_identity_uri":"{{_identity.GetIdentityUri("billing-engine")}}"}"""
            ),
            "not-ok" => WorkloadCredentialRefresherTests.Json(
                HttpStatusCode.OK,
                $$"""{"status":"degraded","peer_identity_uri":"{{peer}}"}"""
            ),
            "no-peer" => WorkloadCredentialRefresherTests.Json(
                HttpStatusCode.OK,
                """{"status":"ok"}"""
            ),
            "array" => WorkloadCredentialRefresherTests.Json(HttpStatusCode.OK, "[]"),
            "bad-json" => WorkloadCredentialRefresherTests.Json(HttpStatusCode.OK, "{nope"),
            "http-error" => throw new HttpRequestException("refused"),
            "canceled" => throw new TaskCanceledException("timeout"),
            _ => WorkloadCredentialRefresherTests.Json(HttpStatusCode.ServiceUnavailable, "{}"),
        };
    }

    private void Load(long version)
    {
        var issued = _pki.Create(new CredentialOptions { Version = version });
        _identity.Apply(issued.Bundle, issued.Trust).Outcome.Should().Be("loaded");
    }

    public void Dispose()
    {
        _identity.Dispose();
        _pki.Dispose();
    }
}
