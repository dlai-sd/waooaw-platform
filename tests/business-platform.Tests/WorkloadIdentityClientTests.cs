// Implements: ADR-046 sections 3, 4.1, 5, 6, 7.2, and 10.1
// constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-076, C-080, C-083, C-084, C-085

using System.Diagnostics;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Configuration;
using Waooaw.WorkloadIdentity;
using FluentAssertions;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class WorkloadIdentityClientTests : IDisposable
{
    private readonly string _credentials = Path.Combine(
        Path.GetTempPath(),
        $"waooaw-identity-{Guid.NewGuid():N}"
    );

    [Fact]
    public void FreshCiCredentialSignsCanonicalVerifiableEnvelope()
    {
        Bootstrap();
        using var client = WorkloadIdentityClient.Load(_credentials);
        var now = DateTimeOffset.FromUnixTimeSeconds(1_800_000_000);
        var token = client.Sign(
            new DelegatedRequestContext(
                "actor-opaque",
                "EMPLOYER",
                "tenant-a",
                Guid.NewGuid().ToString(),
                "RELATIONSHIP_EXECUTION_READ",
                "relationship-a",
                "read-a",
                null,
                new Dictionary<string, string> { ["relationship"] = "7", ["execution"] = "3" },
                Guid.NewGuid().ToString()
            ),
            "urn:waooaw:service:professional-runtime",
            "GET",
            "/api/v1/internal/relationships/{relationshipId}/workspace-execution",
            "getRelationshipExecutionProjection",
            1,
            new string('a', 64),
            now
        );

        var parts = token.Split('.');
        parts.Should().HaveCount(2);
        var payload = Decode(parts[0]);
        var signature = Decode(parts[1]);
        using var document = JsonDocument.Parse(payload);
        var properties = document
            .RootElement.EnumerateObject()
            .Select(property => property.Name)
            .ToArray();
        properties.Should().BeInAscendingOrder(StringComparer.Ordinal);
        document
            .RootElement.GetProperty("expires_at")
            .GetInt64()
            .Should()
            .Be(document.RootElement.GetProperty("issued_at").GetInt64() + 60);
        document.RootElement.GetProperty("actor_source").GetString().Should().Be("BP_SESSION");

        var certificate = X509Certificate2.CreateFromPem(
            File.ReadAllText(
                Path.Combine(_credentials, "workloads", "business-platform", "delegation-cert.pem")
            )
        );
        using var publicKey = certificate.GetECDsaPublicKey();
        publicKey.Should().NotBeNull();
        publicKey!
            .VerifyData(
                payload,
                signature,
                HashAlgorithmName.SHA256,
                DSASignatureFormat.Rfc3279DerSequence
            )
            .Should()
            .BeTrue();
    }

    [Fact]
    public void PrivateOwnerClientRejectsPlaintextUrl()
    {
        Bootstrap();
        using var client = WorkloadIdentityClient.Load(_credentials);

        var action = () =>
            client.CreateClient(
                new Uri("http://professional-runtime:5443"),
                "professional-runtime"
            );

        action.Should().Throw<InvalidOperationException>().WithMessage("*HTTPS*");
    }

    [Fact]
    public void FactoryHandlerRetainsClientCertificateAndRejectsRedirects()
    {
        Bootstrap();
        using var client = WorkloadIdentityClient.Load(_credentials);
        using var handler = Assert.IsType<System.Net.Http.HttpClientHandler>(
            client.CreateHandler("professional-runtime")
        );
        Assert.Single(handler.ClientCertificates.Cast<X509Certificate2>());
        Assert.NotNull(handler.ServerCertificateCustomValidationCallback);
        Assert.False(handler.AllowAutoRedirect);
    }

    [Fact]
    public void GenericDomainAdapterIdentityIsAvailableToEmploymentOwners()
    {
        Bootstrap();
        using var client = WorkloadIdentityClient.Load(_credentials);

        client.GetAudience("domain-adapter").Should().Be("urn:waooaw:service:domain-adapter");
        using var domainClient = client.CreateClient(
            new Uri("https://domain-adapter:8443"),
            "domain-adapter"
        );

        domainClient.BaseAddress.Should().Be(new Uri("https://domain-adapter:8443"));
    }

    [Theory]
    [InlineData("none")]
    [InlineData("digest")]
    [InlineData("purpose")]
    [InlineData("route")]
    [InlineData("method")]
    [InlineData("operation")]
    [InlineData("audience")]
    public async Task InferenceEnvelopeBindsOriginalOwnerAndRejectsReplayWrongPeerOrRequestDrift(string mismatch)
    {
        Bootstrap();
        const string route = "/constitutional.v1.ConstitutionalService/ValidateAction";
        using var signer = WorkloadIdentityClient.Load(_credentials);
        var tenant = Guid.NewGuid();
        var actor = Guid.NewGuid();
        var delegated = new DelegatedRequestContext(actor.ToString("D"), "EMPLOYER", tenant.ToString("D"),
            Guid.NewGuid().ToString("D"), mismatch == "purpose" ? "FOREIGN_PURPOSE" : "CONVERSATION_INFERENCE_EVIDENCE", Guid.NewGuid().ToString("D"),
            Guid.NewGuid().ToString("D"), Guid.NewGuid().ToString("D"), new Dictionary<string, string>(), Guid.NewGuid().ToString("D"));
        var digest = new string('a', 64);
        var token = signer.Sign(delegated, mismatch == "audience" ? "urn:waooaw:service:ai-runtime" : "urn:waooaw:service:constitutional-engine", "POST", route,
            mismatch == "operation" ? "RecordEvidence" : "ValidateAction", 1,
            mismatch == "digest" ? new string('b', 64) : digest, DateTimeOffset.UtcNow);
        var config = new ConfigurationBuilder().AddInMemoryCollection(
            new Dictionary<string, string?> { ["WAOOAW_WORKLOAD_CREDENTIALS"] = _credentials }).Build();
        var validator = new InferenceWorkloadValidator(config, TimeProvider.System);
        using var peer = X509CertificateLoader.LoadCertificateFromFile(Path.Combine(_credentials, "workloads", "business-platform", "tls-cert.pem"));
        var http = new DefaultHttpContext();
        http.Connection.ClientCertificate = peer;
        http.Request.Method = mismatch == "method" ? "GET" : "POST";
        http.Request.Path = mismatch == "route" ? route + "-foreign" : route;
        http.Request.Headers.Authorization = $"Bearer {token}";
        if (mismatch != "none")
        {
            await Assert.ThrowsAsync<InferenceWorkloadRejectedException>(() => validator.RequireAsync(http,
                "business-platform", "constitutional-engine", "CONVERSATION_INFERENCE_EVIDENCE",
                route, "ValidateAction", digest, CancellationToken.None));
            return;
        }
        var caller = await validator.RequireAsync(http, "business-platform", "constitutional-engine",
            "CONVERSATION_INFERENCE_EVIDENCE", route, "ValidateAction", digest, CancellationToken.None);
        caller.ActorId.Should().Be(actor);
        caller.TenantId.Should().Be(tenant);
        await Assert.ThrowsAsync<InferenceWorkloadRejectedException>(() => validator.RequireAsync(http,
            "business-platform", "constitutional-engine", "CONVERSATION_INFERENCE_EVIDENCE",
            route, "ValidateAction", digest, CancellationToken.None));
        using var foreignPeer = X509CertificateLoader.LoadCertificateFromFile(Path.Combine(_credentials, "workloads", "ai-runtime", "tls-cert.pem"));
        http.Connection.ClientCertificate = foreignPeer;
        await Assert.ThrowsAsync<InferenceWorkloadRejectedException>(() => new InferenceWorkloadValidator(config, TimeProvider.System)
            .RequireAsync(http, "business-platform", "constitutional-engine", "CONVERSATION_INFERENCE_EVIDENCE",
                route, "ValidateAction", digest, CancellationToken.None));
    }

    [Theory]
    [InlineData("OWNER", "CONVERSATION_CONTENT_RECOVERY", true)]
    [InlineData("MANAGER", "CONVERSATION_CONTENT_RECOVERY", true)]
    [InlineData("EMPLOYER", "CONVERSATION_CONTENT_RECOVERY", false)]
    [InlineData("OWNER", "CONVERSATION_INFERENCE_EVIDENCE", false)]
    public async Task FreshReaderRolesAreAdmittedOnlyForSeparateContentRecovery(
        string role, string purpose, bool allowed)
    {
        Bootstrap();
        using var signer = WorkloadIdentityClient.Load(_credentials);
        const string route = "/constitutional.v1.ConstitutionalService/ValidateAction";
        var actor = Guid.NewGuid();
        var delegated = new DelegatedRequestContext(actor.ToString("D"), role, Guid.NewGuid().ToString("D"),
            Guid.NewGuid().ToString("D"), purpose, Guid.NewGuid().ToString("D"),
            Guid.NewGuid().ToString("D"), Guid.NewGuid().ToString("D"),
            new Dictionary<string, string>(), Guid.NewGuid().ToString("D"));
        var digest = new string('a', 64);
        var token = signer.Sign(delegated, "urn:waooaw:service:constitutional-engine",
            "POST", route, "ValidateAction", 1, digest, DateTimeOffset.UtcNow);
        var config = new ConfigurationBuilder().AddInMemoryCollection(
            new Dictionary<string, string?> { ["WAOOAW_WORKLOAD_CREDENTIALS"] = _credentials }).Build();
        var validator = new InferenceWorkloadValidator(config, TimeProvider.System);
        using var peer = X509CertificateLoader.LoadCertificateFromFile(
            Path.Combine(_credentials, "workloads", "business-platform", "tls-cert.pem"));
        var http = new DefaultHttpContext();
        http.Connection.ClientCertificate = peer;
        http.Request.Method = "POST";
        http.Request.Path = route;
        http.Request.Headers.Authorization = $"Bearer {token}";
        if (allowed)
        {
            var caller = await validator.RequireAsync(http, "business-platform", "constitutional-engine",
                purpose, route, "ValidateAction", digest, CancellationToken.None);
            Assert.Equal(actor, caller.ActorId);
            Assert.Equal(role, caller.Role);
        }
        else
            await Assert.ThrowsAsync<InferenceWorkloadRejectedException>(() => validator.RequireAsync(
                http, "business-platform", "constitutional-engine", purpose, route, "ValidateAction", digest, CancellationToken.None));
    }

    private void Bootstrap()
    {
        var root = FindRepositoryRoot();
        var process =
            Process.Start(
                new ProcessStartInfo
                {
                    FileName = "python3",
                    ArgumentList =
                    {
                        Path.Combine(root, "scripts", "bootstrap_workload_identity.py"),
                        "--registry",
                        Path.Combine(root, "infrastructure", "workload-identity", "registry.yaml"),
                        "--environment",
                        "ci",
                        "--output",
                        _credentials,
                    },
                    RedirectStandardError = true,
                    UseShellExecute = false,
                }
            ) ?? throw new InvalidOperationException("Could not start credential bootstrap");
        process.WaitForExit();
        process.ExitCode.Should().Be(0, process.StandardError.ReadToEnd());
    }

    private static string FindRepositoryRoot()
    {
        return RepositoryPaths.Root();
    }

    private static byte[] Decode(string value) =>
        Convert.FromBase64String(
            value.Replace('-', '+').Replace('_', '/') + new string('=', (4 - value.Length % 4) % 4)
        );

    public void Dispose()
    {
        if (Directory.Exists(_credentials))
            Directory.Delete(_credentials, recursive: true);
    }
}
