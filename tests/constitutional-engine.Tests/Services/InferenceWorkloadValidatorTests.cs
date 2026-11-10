// Implements: WC-134 R006/R008; ADR-046 signed private inference boundaries.
// constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-076, C-080, C-083, C-084, C-085

using System.Diagnostics;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Configuration;
using Waooaw.BusinessPlatform.Services;
using Waooaw.WorkloadIdentity;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Services;

public sealed class InferenceWorkloadCredentialsFixture : IDisposable
{
    public string Path { get; } =
        System.IO.Path.Combine(
            System.IO.Path.GetTempPath(),
            $"waooaw-ce-identity-{Guid.NewGuid():N}"
        );

    public InferenceWorkloadCredentialsFixture()
    {
        var root = FindRepositoryRoot();
        using var process =
            Process.Start(
                new ProcessStartInfo
                {
                    FileName = "python3",
                    ArgumentList =
                    {
                        System.IO.Path.Combine(root, "scripts", "bootstrap_workload_identity.py"),
                        "--registry",
                        System.IO.Path.Combine(
                            root,
                            "infrastructure",
                            "workload-identity",
                            "registry.yaml"
                        ),
                        "--environment",
                        "ci",
                        "--output",
                        Path,
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
        var workspace = Environment.GetEnvironmentVariable("GITHUB_WORKSPACE");
        if (
            !string.IsNullOrWhiteSpace(workspace)
            && File.Exists(System.IO.Path.Combine(workspace, "docker-compose.yml"))
        )
            return workspace;
        var current = new DirectoryInfo(Directory.GetCurrentDirectory());
        while (current is not null)
        {
            if (File.Exists(System.IO.Path.Combine(current.FullName, "docker-compose.yml")))
                return current.FullName;
            current = current.Parent;
        }
        throw new InvalidOperationException("Repository root not found");
    }

    public void Dispose()
    {
        if (Directory.Exists(Path))
            Directory.Delete(Path, recursive: true);
    }

    public InferenceWorkloadValidator Validator() =>
        new(
            new ConfigurationBuilder()
                .AddInMemoryCollection(
                    new Dictionary<string, string?> { ["WAOOAW_WORKLOAD_CREDENTIALS"] = Path }
                )
                .Build(),
            TimeProvider.System
        );

    public X509Certificate2 Peer(string workload = "business-platform") =>
        X509CertificateLoader.LoadCertificateFromFile(
            System.IO.Path.Combine(Path, "workloads", workload, "tls-cert.pem")
        );

    public string IdentityUri(string workload)
    {
        using var manifest = JsonDocument.Parse(
            File.ReadAllText(System.IO.Path.Combine(Path, "manifest.json"))
        );
        return manifest
            .RootElement.GetProperty("workloads")
            .GetProperty(workload)
            .GetProperty("identity_uri")
            .GetString()!;
    }

    public string Sign(
        byte[] payload,
        Guid tenant,
        Guid relationship,
        int revision,
        string route,
        string operation,
        string? professional = null
    )
    {
        var versions = new Dictionary<string, string>
        {
            ["decisionSpaceRevision"] = revision.ToString(
                System.Globalization.CultureInfo.InvariantCulture
            ),
            ["mandateDigest"] = new string('a', 64),
        };
        if (professional is not null)
            versions["professionalType"] = professional;
        using var signer = WorkloadIdentityClient.Load(Path);
        return signer.Sign(
            new DelegatedRequestContext(
                Guid.NewGuid().ToString("D"),
                "EMPLOYER",
                tenant.ToString("D"),
                relationship.ToString("D"),
                "CONVERSATION_INFERENCE_EVIDENCE",
                Guid.NewGuid().ToString("D"),
                Guid.NewGuid().ToString("D"),
                Guid.NewGuid().ToString("D"),
                versions,
                Guid.NewGuid().ToString("D")
            ),
            "urn:waooaw:service:constitutional-engine",
            "POST",
            route,
            operation,
            1,
            Convert.ToHexStringLower(SHA256.HashData(payload)),
            DateTimeOffset.UtcNow
        );
    }
}

public sealed class InferenceWorkloadValidatorTests(InferenceWorkloadCredentialsFixture credentials)
    : IClassFixture<InferenceWorkloadCredentialsFixture>
{
    private const string Route = "/constitutional.v1.ConstitutionalService/ValidateAction";
    private const string Purpose = "CONVERSATION_INFERENCE_EVIDENCE";
    private const string Digest =
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

    [Theory]
    [InlineData("none")]
    [InlineData("digest")]
    [InlineData("purpose")]
    [InlineData("route")]
    [InlineData("method")]
    [InlineData("operation")]
    [InlineData("audience")]
    public async Task EnvelopeBindsOwnerAndRejectsReplayPeerOrRequestDrift(string mismatch)
    {
        using var signer = WorkloadIdentityClient.Load(credentials.Path);
        var tenant = Guid.NewGuid();
        var actor = Guid.NewGuid();
        var delegated = Context(
            actor,
            tenant,
            "EMPLOYER",
            mismatch == "purpose" ? "FOREIGN_PURPOSE" : Purpose
        );
        var token = signer.Sign(
            delegated,
            mismatch == "audience"
                ? "urn:waooaw:service:ai-runtime"
                : "urn:waooaw:service:constitutional-engine",
            "POST",
            Route,
            mismatch == "operation" ? "RecordEvidence" : "ValidateAction",
            1,
            mismatch == "digest" ? new string('b', 64) : Digest,
            DateTimeOffset.UtcNow
        );
        var validator = Validator();
        using var peer = Peer("business-platform");
        var http = Request(
            token,
            peer,
            mismatch == "method" ? "GET" : "POST",
            mismatch == "route" ? Route + "-foreign" : Route
        );

        if (mismatch != "none")
        {
            await Assert.ThrowsAsync<InferenceWorkloadRejectedException>(() =>
                RequireAsync(validator, http, Purpose, Digest)
            );
            return;
        }

        var caller = await RequireAsync(validator, http, Purpose, Digest);
        caller.ActorId.Should().Be(actor);
        caller.TenantId.Should().Be(tenant);
        await Assert.ThrowsAsync<InferenceWorkloadRejectedException>(() =>
            RequireAsync(validator, http, Purpose, Digest)
        );

        using var foreignPeer = Peer("ai-runtime");
        http.Connection.ClientCertificate = foreignPeer;
        await Assert.ThrowsAsync<InferenceWorkloadRejectedException>(() =>
            RequireAsync(Validator(), http, Purpose, Digest)
        );
    }

    [Theory]
    [InlineData("OWNER", "CONVERSATION_CONTENT_RECOVERY", true)]
    [InlineData("MANAGER", "CONVERSATION_CONTENT_RECOVERY", true)]
    [InlineData("EMPLOYER", "CONVERSATION_CONTENT_RECOVERY", false)]
    [InlineData("OWNER", Purpose, false)]
    public async Task ReaderRolesAreLimitedToContentRecovery(
        string role,
        string purpose,
        bool allowed
    )
    {
        using var signer = WorkloadIdentityClient.Load(credentials.Path);
        var actor = Guid.NewGuid();
        var token = signer.Sign(
            Context(actor, Guid.NewGuid(), role, purpose),
            "urn:waooaw:service:constitutional-engine",
            "POST",
            Route,
            "ValidateAction",
            1,
            Digest,
            DateTimeOffset.UtcNow
        );
        using var peer = Peer("business-platform");
        var http = Request(token, peer, "POST", Route);

        if (allowed)
        {
            var caller = await RequireAsync(Validator(), http, purpose, Digest);
            caller.ActorId.Should().Be(actor);
            caller.Role.Should().Be(role);
        }
        else
        {
            await Assert.ThrowsAsync<InferenceWorkloadRejectedException>(() =>
                RequireAsync(Validator(), http, purpose, Digest)
            );
        }
    }

    [Theory]
    [InlineData("missing-credentials")]
    [InlineData("missing-certificate")]
    [InlineData("missing-bearer")]
    [InlineData("malformed-bearer")]
    public async Task MissingTransportAuthorityIsRejected(string defect)
    {
        var configuration =
            defect == "missing-credentials" ? new ConfigurationBuilder().Build() : Configuration();
        using var peer = defect == "missing-certificate" ? null : Peer("business-platform");
        var http = Request(
            defect == "missing-bearer" ? ""
                : defect == "malformed-bearer" ? "not-a-token"
                : "payload.signature",
            peer,
            "POST",
            Route
        );

        await Assert.ThrowsAsync<InferenceWorkloadRejectedException>(() =>
            RequireAsync(
                new InferenceWorkloadValidator(configuration, TimeProvider.System),
                http,
                Purpose,
                Digest
            )
        );
    }

    [Fact]
    public void PeerUriSanMustMatchExactly()
    {
        using var peer = credentials.Peer();

        InferenceWorkloadValidator
            .HasExactUriSan(peer, credentials.IdentityUri("business-platform"))
            .Should()
            .BeTrue();
        InferenceWorkloadValidator
            .HasExactUriSan(peer, "urn:waooaw:service:ai-runtime")
            .Should()
            .BeFalse();
        InferenceWorkloadValidator
            .ValidatePeer(peer, credentials.Path, credentials.IdentityUri("business-platform"))
            .Should()
            .BeTrue();
        InferenceWorkloadValidator
            .ValidatePeer(peer, credentials.Path, "urn:waooaw:service:ai-runtime")
            .Should()
            .BeFalse();
    }

    private InferenceWorkloadValidator Validator() => new(Configuration(), TimeProvider.System);

    private IConfiguration Configuration() =>
        new ConfigurationBuilder()
            .AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    ["WAOOAW_WORKLOAD_CREDENTIALS"] = credentials.Path,
                }
            )
            .Build();

    private X509Certificate2 Peer(string workload) =>
        X509CertificateLoader.LoadCertificateFromFile(
            System.IO.Path.Combine(credentials.Path, "workloads", workload, "tls-cert.pem")
        );

    private static DefaultHttpContext Request(
        string token,
        X509Certificate2? peer,
        string method,
        string route
    )
    {
        var http = new DefaultHttpContext();
        http.Connection.ClientCertificate = peer;
        http.Request.Method = method;
        http.Request.Path = route;
        if (token.Length > 0)
            http.Request.Headers.Authorization = $"Bearer {token}";
        return http;
    }

    private static DelegatedRequestContext Context(
        Guid actor,
        Guid tenant,
        string role,
        string purpose
    ) =>
        new(
            actor.ToString("D"),
            role,
            tenant.ToString("D"),
            Guid.NewGuid().ToString("D"),
            purpose,
            Guid.NewGuid().ToString("D"),
            Guid.NewGuid().ToString("D"),
            Guid.NewGuid().ToString("D"),
            new Dictionary<string, string>(),
            Guid.NewGuid().ToString("D")
        );

    private static Task<InferenceWorkloadContext> RequireAsync(
        InferenceWorkloadValidator validator,
        HttpContext http,
        string purpose,
        string digest
    ) =>
        validator.RequireAsync(
            http,
            "business-platform",
            "constitutional-engine",
            purpose,
            Route,
            "ValidateAction",
            digest,
            CancellationToken.None
        );
}
