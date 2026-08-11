// Implements: ADR-046 sections 3, 4.1, 5, 6, 7.2, and 10.1
// constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-076, C-080, C-083, C-084, C-085

using System.Diagnostics;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using FluentAssertions;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class WorkloadIdentityClientTests : IDisposable
{
    private readonly string _credentials = Path.Combine(Path.GetTempPath(), $"waooaw-identity-{Guid.NewGuid():N}");

    [Fact]
    public void FreshCiCredentialSignsCanonicalVerifiableEnvelope()
    {
        Bootstrap();
        using var client = WorkloadIdentityClient.Load(_credentials);
        var now = DateTimeOffset.FromUnixTimeSeconds(1_800_000_000);
        var token = client.Sign(
            new DelegatedRequestContext(
                "actor-opaque", "EMPLOYER", "tenant-a", Guid.NewGuid().ToString(),
                "RELATIONSHIP_EXECUTION_READ", "relationship-a", "read-a", null,
                new Dictionary<string, string> { ["relationship"] = "7", ["execution"] = "3" },
                Guid.NewGuid().ToString()),
            "urn:waooaw:service:professional-runtime", "GET",
            "/api/v1/internal/relationships/{relationshipId}/workspace-execution",
            "getRelationshipExecutionProjection", 1, new string('a', 64), now);

        var parts = token.Split('.');
        parts.Should().HaveCount(2);
        var payload = Decode(parts[0]);
        var signature = Decode(parts[1]);
        using var document = JsonDocument.Parse(payload);
        var properties = document.RootElement.EnumerateObject().Select(property => property.Name).ToArray();
        properties.Should().BeInAscendingOrder(StringComparer.Ordinal);
        document.RootElement.GetProperty("expires_at").GetInt64().Should().Be(
            document.RootElement.GetProperty("issued_at").GetInt64() + 60);
        document.RootElement.GetProperty("actor_source").GetString().Should().Be("BP_SESSION");

        var certificate = X509Certificate2.CreateFromPem(File.ReadAllText(
            Path.Combine(_credentials, "workloads", "business-platform", "delegation-cert.pem")));
        using var publicKey = certificate.GetECDsaPublicKey();
        publicKey.Should().NotBeNull();
        publicKey!.VerifyData(payload, signature, HashAlgorithmName.SHA256, DSASignatureFormat.Rfc3279DerSequence)
            .Should().BeTrue();
    }

    [Fact]
    public void PrivateOwnerClientRejectsPlaintextUrl()
    {
        Bootstrap();
        using var client = WorkloadIdentityClient.Load(_credentials);

        var action = () => client.CreateClient(
            new Uri("http://professional-runtime:5443"),
            "professional-runtime");

        action.Should().Throw<InvalidOperationException>().WithMessage("*HTTPS*");
    }

    private void Bootstrap()
    {
        var root = FindRepositoryRoot();
        var process = Process.Start(new ProcessStartInfo
        {
            FileName = "python3",
            ArgumentList =
            {
                Path.Combine(root, "scripts", "bootstrap_workload_identity.py"),
                "--registry", Path.Combine(root, "infrastructure", "workload-identity", "registry.yaml"),
                "--environment", "ci", "--output", _credentials,
            },
            RedirectStandardError = true,
            UseShellExecute = false,
        }) ?? throw new InvalidOperationException("Could not start credential bootstrap");
        process.WaitForExit();
        process.ExitCode.Should().Be(0, process.StandardError.ReadToEnd());
    }

    private static string FindRepositoryRoot()
    {
        var path = new DirectoryInfo(AppContext.BaseDirectory);
        while (path is not null && !Directory.Exists(Path.Combine(path.FullName, "constitution"))) path = path.Parent;
        return path?.FullName ?? throw new InvalidOperationException("Repository root not found");
    }

    private static byte[] Decode(string value) => Convert.FromBase64String(
        value.Replace('-', '+').Replace('_', '/') + new string('=', (4 - value.Length % 4) % 4));

    public void Dispose()
    {
        if (Directory.Exists(_credentials)) Directory.Delete(_credentials, recursive: true);
    }
}