// Implements: ADR-046 sections 5.1, 5.2 and 12.2 D4; workload-identity-cloud-issuance-contract.md section 8
// constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-083, C-084, C-085

using System.Collections.Concurrent;
using System.Net;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using FluentAssertions;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class WorkloadIdentityReloadTests
{
    private static readonly WorkloadCredentialSettings Settings = new(
        "business-platform",
        TestPki.TrustDomain
    );

    [Fact]
    public void ClientWithoutCredentialsIsUnavailableAndNeverSigns()
    {
        using var client = WorkloadIdentityClient.CreateReloadable(Settings);

        client.IsAvailable.Should().BeFalse();
        client
            .GetStatus()
            .Should()
            .Be(new WorkloadCredentialStatus("keyvault", "UNAVAILABLE", null, null));
        Sign(client, DateTimeOffset.UtcNow)
            .Should()
            .Throw<WorkloadCredentialsUnavailableException>();
        client
            .Invoking(value => value.GetAudience("billing-engine"))
            .Should()
            .Throw<WorkloadCredentialsUnavailableException>();
    }

    [Fact]
    public void ApplyLoadsRefreshesAndNeverDowngradesTheBundleVersion()
    {
        using var pki = new TestPki();
        var clock = new TestClock(pki.Now);
        using var client = WorkloadIdentityClient.CreateReloadable(Settings, clock);
        var first = pki.Create(new CredentialOptions { Version = 10 });
        var second = pki.Create(new CredentialOptions { Version = 11 });

        client.Apply(first.Bundle, first.Trust).Outcome.Should().Be("loaded");
        client.GetStatus().State.Should().Be("READY");
        client.GetStatus().BundleVersion.Should().Be(10);
        client.GetStatus().RemainingSeconds.Should().BeInRange(86_300, 86_400);
        client.Apply(first.Bundle, first.Trust).Outcome.Should().Be("unchanged");
        client.Apply(second.Bundle, second.Trust).Outcome.Should().Be("refreshed");
        client.GetStatus().BundleVersion.Should().Be(11);

        var downgrade = client.Apply(first.Bundle, first.Trust);

        downgrade.Should().Be(new WorkloadCredentialApplyResult("rejected", "ROLLBACK"));
        client.GetStatus().BundleVersion.Should().Be(11);
        client.IsAvailable.Should().BeTrue();
    }

    [Fact]
    public void RejectedBundlesKeepTheLastVerifiedCredential()
    {
        using var pki = new TestPki();
        using var client = WorkloadIdentityClient.CreateReloadable(
            Settings,
            new TestClock(pki.Now)
        );
        var good = pki.Create(new CredentialOptions { Version = 10 });
        client.Apply(good.Bundle, good.Trust);
        var tampered = pki.Create(
            new CredentialOptions
            {
                Version = 11,
                TrustAfterSigning = t => t["revoked_identity_uris"] = new JsonArray("x"),
            }
        );

        client.Apply(tampered.Bundle, tampered.Trust).Reason.Should().Be("TRUST_SIGNATURE");
        client.Apply("UNISSUED", good.Trust).Reason.Should().Be("NO_CREDENTIAL");
        client.Apply(good.Bundle, "{broken").Reason.Should().Be("NO_CREDENTIAL");

        client.IsAvailable.Should().BeTrue();
        client.GetStatus().BundleVersion.Should().Be(10);
    }

    [Fact]
    public void BundleRevokingTheLeafDropsTheCredentialImmediately()
    {
        using var pki = new TestPki();
        using var client = WorkloadIdentityClient.CreateReloadable(
            Settings,
            new TestClock(pki.Now)
        );
        var good = pki.Create(new CredentialOptions { Version = 10 });
        client.Apply(good.Bundle, good.Trust);
        var revoked = pki.Create(new CredentialOptions { Version = 11, RevokeLeafSerial = true });

        client.Apply(revoked.Bundle, revoked.Trust).Reason.Should().Be("REVOKED");

        client.IsAvailable.Should().BeFalse();
        client.GetStatus().State.Should().Be("UNAVAILABLE");
    }

    [Fact]
    public void CredentialExpiresWithTheLeafAndSigningStops()
    {
        using var pki = new TestPki();
        var clock = new TestClock(pki.Now);
        using var client = WorkloadIdentityClient.CreateReloadable(Settings, clock);
        var issued = pki.Create();
        client.Apply(issued.Bundle, issued.Trust);
        clock.Advance(TimeSpan.FromHours(23));
        client.IsAvailable.Should().BeTrue();

        clock.Advance(TimeSpan.FromHours(1));

        client.IsAvailable.Should().BeFalse();
        client.GetStatus().State.Should().Be("UNAVAILABLE");
        Sign(client, clock.GetUtcNow()).Should().Throw<WorkloadCredentialsUnavailableException>();
    }

    [Fact]
    public void DelegationSignerWaitsForItsActivationTime()
    {
        using var pki = new TestPki();
        var clock = new TestClock(pki.Now);
        using var client = WorkloadIdentityClient.CreateReloadable(Settings, clock);
        var issued = pki.Create(
            new CredentialOptions { DelegationActivateIn = TimeSpan.FromMinutes(10) }
        );

        client.Apply(issued.Bundle, issued.Trust).Outcome.Should().Be("loaded");

        client.IsAvailable.Should().BeFalse();
        clock.Advance(TimeSpan.FromMinutes(10));
        client.IsAvailable.Should().BeTrue();
    }

    [Fact]
    public void SignedEnvelopeVerifiesWithThePublishedDelegationCertificateAndRotatesOnActivation()
    {
        using var pki = new TestPki();
        var clock = new TestClock(pki.Now);
        using var client = WorkloadIdentityClient.CreateReloadable(Settings, clock);
        var first = pki.Create(new CredentialOptions { Version = 10 });
        var second = pki.Create(
            new CredentialOptions { Version = 11, DelegationActivateIn = TimeSpan.FromMinutes(10) }
        );
        client.Apply(first.Bundle, first.Trust);
        client.Apply(second.Bundle, second.Trust).Outcome.Should().Be("refreshed");

        var beforeActivation = Signed(client, clock);
        clock.Advance(TimeSpan.FromMinutes(10));
        var afterActivation = Signed(client, clock);

        beforeActivation
            .Payload.GetProperty("key_id")
            .GetString()
            .Should()
            .Be(first.DelegationKeyId);
        afterActivation
            .Payload.GetProperty("key_id")
            .GetString()
            .Should()
            .Be(second.DelegationKeyId);
        afterActivation
            .Payload.GetProperty("issuer_uri")
            .GetString()
            .Should()
            .Be(TestPki.Identity("business-platform"));
        Verifies(first.Delegation, beforeActivation).Should().BeTrue();
        Verifies(second.Delegation, afterActivation).Should().BeTrue();
        Verifies(first.Delegation, afterActivation).Should().BeFalse();
    }

    [Fact]
    public async Task ReloadingHandlerFailsClosedWithoutCredentialsAndRejectsPlaintextClients()
    {
        using var client = WorkloadIdentityClient.CreateReloadable(Settings);
        using var owner = client.CreateClient(new Uri("https://billing.test"), "billing-engine");

        var action = () => owner.GetAsync("/x");

        await action.Should().ThrowAsync<WorkloadCredentialsUnavailableException>();
        client
            .Invoking(value => value.CreateClient(new Uri("http://billing.test"), "billing-engine"))
            .Should()
            .Throw<InvalidOperationException>()
            .WithMessage("*HTTPS*");
        client
            .Invoking(value =>
                value.CreateClient(new Uri("https://x.test"), "constitutional-engine")
            )
            .Should()
            .Throw<InvalidOperationException>();
    }

    [Fact]
    public async Task ReloadedLeafIsPresentedOnNewConnectionsWithoutRestartingTheClient()
    {
        using var pki = new TestPki();
        using var client = WorkloadIdentityClient.CreateReloadable(
            Settings,
            new TestClock(pki.Now)
        );
        var first = pki.Create(new CredentialOptions { Version = 10 });
        var second = pki.Create(new CredentialOptions { Version = 11 });
        client.Apply(first.Bundle, first.Trust);
        await using var server = TlsOwnerServer.Start(pki, "billing-engine", expected: 2);
        using var owner = client.CreateClient(server.Url, "billing-engine");

        (await owner.GetAsync("/one")).EnsureSuccessStatusCode();
        client.Apply(second.Bundle, second.Trust).Outcome.Should().Be("refreshed");
        (await owner.GetAsync("/two")).EnsureSuccessStatusCode();

        server.ClientSerials.Should().Equal(first.Leaf.SerialNumber, second.Leaf.SerialNumber);
    }

    [Fact]
    public async Task PeerWithAnotherWorkloadIdentityOrARevokedIdentityIsRejected()
    {
        using var pki = new TestPki();
        using var client = WorkloadIdentityClient.CreateReloadable(
            Settings,
            new TestClock(pki.Now)
        );
        var first = pki.Create(new CredentialOptions { Version = 10 });
        client.Apply(first.Bundle, first.Trust);

        await using (var wrong = TlsOwnerServer.Start(pki, "professional-runtime", expected: 1))
        {
            using var owner = client.CreateClient(wrong.Url, "billing-engine");
            var call = () => owner.GetAsync("/x");
            await call.Should().ThrowAsync<HttpRequestException>();
        }

        await using var right = TlsOwnerServer.Start(pki, "billing-engine", expected: 2);
        using var billing = client.CreateClient(right.Url, "billing-engine");
        (await billing.GetAsync("/ok")).EnsureSuccessStatusCode();
        var revoked = pki.Create(
            new CredentialOptions
            {
                Version = 11,
                Trust = t =>
                    t["revoked_identity_uris"] = new JsonArray(TestPki.Identity("billing-engine")),
            }
        );
        client.Apply(revoked.Bundle, revoked.Trust).Outcome.Should().Be("refreshed");
        var afterRevocation = () => billing.GetAsync("/revoked");
        await afterRevocation.Should().ThrowAsync<HttpRequestException>();
    }

    private static Func<string> Sign(WorkloadIdentityClient client, DateTimeOffset now) =>
        () =>
            client.Sign(
                Context(),
                "urn:waooaw:service:billing-engine",
                "GET",
                "/r",
                "op",
                1,
                new string('a', 64),
                now
            );

    private static DelegatedRequestContext Context() =>
        new(
            "actor",
            "EMPLOYER",
            "tenant",
            Guid.NewGuid().ToString(),
            "PURPOSE",
            "subject",
            "command",
            null,
            new Dictionary<string, string>(),
            Guid.NewGuid().ToString()
        );

    private static SignedEnvelope Signed(WorkloadIdentityClient client, TestClock clock)
    {
        var token = client.Sign(
            Context(),
            "urn:waooaw:service:billing-engine",
            "GET",
            "/r",
            "op",
            1,
            new string('a', 64),
            clock.GetUtcNow()
        );
        var parts = token.Split('.');
        var payload = Decode(parts[0]);
        return new SignedEnvelope(
            payload,
            Decode(parts[1]),
            JsonDocument.Parse(payload).RootElement
        );
    }

    private static bool Verifies(X509Certificate2 delegation, SignedEnvelope envelope)
    {
        using var key = delegation.GetECDsaPublicKey()!;
        return key.VerifyData(
            envelope.PayloadBytes,
            envelope.Signature,
            HashAlgorithmName.SHA256,
            DSASignatureFormat.Rfc3279DerSequence
        );
    }

    private static byte[] Decode(string value)
    {
        var padded = value.Replace('-', '+').Replace('_', '/');
        return Convert.FromBase64String(padded + new string('=', (4 - padded.Length % 4) % 4));
    }

    private sealed record SignedEnvelope(
        byte[] PayloadBytes,
        byte[] Signature,
        JsonElement Payload
    );
}

/// <summary>A loopback mutual-TLS HTTP/1.1 owner that records the client certificate each connection presented.</summary>
internal sealed class TlsOwnerServer : IAsyncDisposable
{
    private readonly TcpListener _listener = new(IPAddress.Loopback, 0);
    private readonly CancellationTokenSource _stop = new();
    private readonly ConcurrentQueue<string> _serials = new();
    private readonly Task _loop;
    private readonly X509Certificate2 _certificate;
    private readonly SslStreamCertificateContext _context;
    private readonly TestPki _pki;

    private TlsOwnerServer(TestPki pki, string workload, int expected)
    {
        _pki = pki;
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var issued = pki.Issue(
            key,
            TestPki.Identity(workload),
            pki.Now.AddSeconds(-60),
            TimeSpan.FromHours(24),
            TestPki.ServerAuth
        );
        _certificate = issued.CopyWithPrivateKey(key);
        _context = SslStreamCertificateContext.Create(
            _certificate,
            [pki.Intermediate],
            offline: true
        );
        _listener.Start();
        _loop = Task.Run(() => ServeAsync(expected));
    }

    public Uri Url => new($"https://localhost:{((IPEndPoint)_listener.LocalEndpoint).Port}");

    public IReadOnlyList<string> ClientSerials => [.. _serials];

    public static TlsOwnerServer Start(TestPki pki, string workload, int expected) =>
        new(pki, workload, expected);

    private async Task ServeAsync(int expected)
    {
        for (var served = 0; served < expected && !_stop.IsCancellationRequested; served++)
        {
            try
            {
                using var tcp = await _listener.AcceptTcpClientAsync(_stop.Token);
                await using var ssl = new SslStream(tcp.GetStream(), false);
                await ssl.AuthenticateAsServerAsync(
                    new SslServerAuthenticationOptions
                    {
                        ServerCertificateContext = _context,
                        ClientCertificateRequired = true,
                        RemoteCertificateValidationCallback = (_, certificate, _, _) =>
                            certificate is not null
                            && ValidClientCertificate(certificate),
                    },
                    _stop.Token
                );
                using (var remote = new X509Certificate2(ssl.RemoteCertificate!))
                    _serials.Enqueue(remote.SerialNumber);
                var buffer = new byte[4096];
                var seen = new StringBuilder();
                while (!seen.ToString().Contains("\r\n\r\n", StringComparison.Ordinal))
                {
                    var read = await ssl.ReadAsync(buffer, _stop.Token);
                    if (read == 0)
                        break;
                    seen.Append(Encoding.ASCII.GetString(buffer, 0, read));
                }
                await ssl.WriteAsync(
                    Encoding.ASCII.GetBytes(
                        "HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok"
                    ),
                    _stop.Token
                );
                await ssl.FlushAsync(_stop.Token);
            }
            catch (Exception exception)
                when (exception
                        is IOException
                            or System.Security.Authentication.AuthenticationException
                )
            {
                // A client that rejects this peer aborts the handshake; the next connection is served.
            }
            catch (OperationCanceledException)
            {
                return;
            }
        }
    }

    private bool ValidClientCertificate(X509Certificate certificate)
    {
        using var typed = new X509Certificate2(certificate);
        return ValidClient(typed);
    }

    private bool ValidClient(X509Certificate2 certificate)
    {
        using var chain = new X509Chain();
        chain.ChainPolicy.TrustMode = X509ChainTrustMode.CustomRootTrust;
        chain.ChainPolicy.CustomTrustStore.Add(_pki.Root);
        chain.ChainPolicy.ExtraStore.Add(_pki.Intermediate);
        chain.ChainPolicy.RevocationMode = X509RevocationMode.NoCheck;
        return chain.Build(certificate)
            && WorkloadIdentityClient.HasExactUriSan(
                certificate,
                TestPki.Identity("business-platform")
            );
    }

    public async ValueTask DisposeAsync()
    {
        await _stop.CancelAsync();
        _listener.Stop();
        try
        {
            await _loop;
        }
        catch (Exception exception) when (exception is ObjectDisposedException or SocketException)
        {
            // The listener was stopped while the loop was waiting for a connection.
        }
        _certificate.Dispose();
        _stop.Dispose();
    }
}
