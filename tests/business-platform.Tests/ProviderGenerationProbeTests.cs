// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R003, WC149-R005
// constitutional_basis: C-023, C-059, C-063, C-083, C-084

using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Services;
using Waooaw.WorkloadIdentity;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ProviderGenerationProbeTests
{
    private readonly Mock<IProviderProbeGateway> _gateway = new(MockBehavior.Strict);

    private static ProviderProbeResult Answered(string text) =>
        new(
            new("openai", "gpt", "gpt-x", text, 3, 5, 120),
            [new("openai", "ANSWERED", null)]
        );

    [Fact]
    public async Task ThePrimaryProviderIsFirstAndFallbacksFollowWithoutModels()
    {
        IReadOnlyList<ProviderProbeTarget>? sent = null;
        _gateway
            .Setup(g => g.ProbeAsync(It.IsAny<IReadOnlyList<ProviderProbeTarget>>(), "founder-1", default))
            .Callback<IReadOnlyList<ProviderProbeTarget>, string, CancellationToken>((p, _, _) => sent = p)
            .ReturnsAsync(Answered("hi"));

        var result = await new ProviderGenerationProbe(_gateway.Object).TestAnswerAsync(
            "openai",
            new("gpt-4o-mini", ["sarvam", "claude"]),
            "founder-1",
            default
        );

        sent.Should().Equal(
            new ProviderProbeTarget("openai", "gpt-4o-mini"),
            new ProviderProbeTarget("sarvam", null),
            new ProviderProbeTarget("claude", null)
        );
        result.Answered!.Text.Should().Be("hi");
    }

    [Theory]
    [InlineData("Bad Name", null, new string[0])]
    [InlineData("openai", "model with spaces", new string[0])]
    [InlineData("openai", null, new[] { "openai" })]
    [InlineData("openai", null, new[] { "a", "a" })]
    [InlineData("openai", null, new[] { "a", "b", "c", "d" })]
    [InlineData("openai", null, new[] { "Not Valid" })]
    public async Task InvalidRequestsNeverReachTheRuntime(
        string provider,
        string? model,
        string[] fallbacks
    )
    {
        var failure = await Assert.ThrowsAsync<ProviderAdminException>(() =>
            new ProviderGenerationProbe(_gateway.Object).TestAnswerAsync(
                provider,
                new(model, fallbacks),
                "founder-1",
                default
            )
        );

        failure.Status.Should().Be(400);
        _gateway.VerifyNoOtherCalls();
    }

    [Fact]
    public async Task TheAnswerTextIsTruncatedAndUnknownVocabularyIsReplaced()
    {
        _gateway
            .Setup(g => g.ProbeAsync(It.IsAny<IReadOnlyList<ProviderProbeTarget>>(), It.IsAny<string>(), default))
            .ReturnsAsync(
                new ProviderProbeResult(
                    Answered(new string('x', 5000)).Answered,
                    [
                        new("sarvam", "SKIPPED", "secret-token-leak"),
                        new("claude", "WHATEVER", null),
                        new("openai", "ANSWERED", "KEY_MISSING"),
                    ]
                )
            );

        var result = await new ProviderGenerationProbe(_gateway.Object).TestAnswerAsync(
            "sarvam",
            new(null, ["claude", "openai"]),
            "founder-1",
            default
        );

        result.Answered!.Text.Should().HaveLength(2000);
        result.Attempts.Select(a => (a.Outcome, a.Reason)).Should().Equal(
            ("SKIPPED", "PROVIDER_ERROR"),
            ("SKIPPED", "PROVIDER_ERROR"),
            ("ANSWERED", null)
        );
        JsonSerializer.Serialize(result).Should().NotContain("secret-token-leak");
    }

    [Fact]
    public async Task AnUnreachableRuntimeIsA503WithAClearCode()
    {
        _gateway
            .Setup(g => g.ProbeAsync(It.IsAny<IReadOnlyList<ProviderProbeTarget>>(), It.IsAny<string>(), default))
            .ThrowsAsync(new ProviderProbeUnavailableException("detail with https://internal.example"));

        var failure = await Assert.ThrowsAsync<ProviderAdminException>(() =>
            new ProviderGenerationProbe(_gateway.Object).TestAnswerAsync("openai", new(null, null), "founder-1", default)
        );

        failure.Status.Should().Be(503);
        failure.Code.Should().Be("PROVIDER_PROBE_UNAVAILABLE");
        failure.Message.Should().NotContain("internal.example");
    }

    [Fact]
    public async Task TheUnconfiguredGatewayAlwaysReportsUnavailable()
    {
        var failure = await Assert.ThrowsAsync<ProviderAdminException>(() =>
            new ProviderGenerationProbe(new UnconfiguredProviderProbeGateway()).TestAnswerAsync(
                "openai",
                new(null, null),
                "founder-1",
                default
            )
        );

        failure.Code.Should().Be("PROVIDER_PROBE_UNAVAILABLE");
    }
}

public sealed class ProviderCredentialResolveTests(OwnerGatewayIdentityFixture fixture)
    : IClassFixture<OwnerGatewayIdentityFixture>,
        IDisposable
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    private readonly X509Certificate2 _peer = X509Certificate2.CreateFromPem(
        File.ReadAllText(
            Path.Combine(fixture.CredentialsPath, "workloads", "ai-runtime", "tls-cert.pem")
        )
    );
    private readonly Mock<IProviderCredentialResolver> _resolver = new(MockBehavior.Strict);

    public void Dispose() => _peer.Dispose();

    private static JsonElement Body(string name) =>
        JsonSerializer.SerializeToElement(new { providerName = name });

    private ProviderCredentialResolveController Controller() =>
        new(
            new ProviderCredentialWorkloadAuthority(
                new InferenceWorkloadValidator(
                    new ConfigurationBuilder()
                        .AddInMemoryCollection(
                            new Dictionary<string, string?>
                            {
                                ["WAOOAW_WORKLOAD_CREDENTIALS"] = fixture.CredentialsPath,
                            }
                        )
                        .Build(),
                    TimeProvider.System
                )
            ),
            _resolver.Object,
            NullLogger<ProviderCredentialResolveController>.Instance
        )
        {
            ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() },
        };

    private void Sign(
        HttpContext http,
        JsonElement body,
        string purpose = "PROVIDER_CREDENTIAL_RESOLVE",
        string actorSource = "WORKLOAD"
    )
    {
        using var manifest = JsonDocument.Parse(
            File.ReadAllText(Path.Combine(fixture.CredentialsPath, "manifest.json"))
        );
        var workloads = manifest.RootElement.GetProperty("workloads");
        var source = workloads.GetProperty("ai-runtime");
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        const string route = "/internal/v1/provider-credentials/resolve";
        var payload = JsonSerializer.SerializeToUtf8Bytes(
            new Dictionary<string, object>
            {
                ["issuer_uri"] = source.GetProperty("identity_uri").GetString()!,
                ["key_id"] = source.GetProperty("delegation_key_id").GetString()!,
                ["target_audience"] = workloads
                    .GetProperty("business-platform")
                    .GetProperty("audience")
                    .GetString()!,
                ["method"] = "POST",
                ["route"] = route,
                ["operation"] = "resolveProviderCredential",
                ["schema_version"] = "1.0",
                ["contract_major"] = 1,
                ["purpose"] = purpose,
                ["actor_source"] = actorSource,
                ["request_digest"] = Convert.ToHexStringLower(
                    SHA256.HashData(
                        Encoding.UTF8.GetBytes(AgentAdmissionCanonicalizer.Canonicalize(body))
                    )
                ),
                ["issued_at"] = now,
                ["not_before"] = now,
                ["expires_at"] = now + 60,
                ["tenant_id"] = "platform",
                ["relationship_id"] = "provider-credential",
                ["actor_subject"] = source.GetProperty("identity_uri").GetString()!,
                ["effective_role"] = "WORKLOAD",
                ["subject_reference"] = "openai",
                ["command_id"] = Guid.NewGuid().ToString("D"),
                ["idempotency_key"] = (object?)null!,
                ["expected_versions"] = new Dictionary<string, string>(),
                ["envelope_id"] = Guid.NewGuid().ToString("D"),
            }
        );
        using var signing = ECDsa.Create();
        signing.ImportFromPem(
            File.ReadAllText(
                Path.Combine(fixture.CredentialsPath, "workloads", "ai-runtime", "delegation-key.pem")
            )
        );
        static string Encode(byte[] value) =>
            Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');
        http.Request.Method = "POST";
        http.Request.Path = route;
        http.Connection.ClientCertificate = _peer;
        http.Request.Headers.Authorization =
            "Bearer "
            + Encode(payload)
            + "."
            + Encode(
                signing.SignData(payload, HashAlgorithmName.SHA256, DSASignatureFormat.Rfc3279DerSequence)
            );
    }

    [Fact]
    public async Task ASignedAiRuntimeCallReceivesTheReferenceWithNoStore()
    {
        var reference = new ResolvedProviderCredential("openai", "provider-openai", "abc123", "bearer");
        _resolver.Setup(r => r.ResolveAsync("openai", default)).ReturnsAsync(reference);
        var controller = Controller();
        var body = Body("openai");
        Sign(controller.HttpContext, body);

        var result = Assert.IsType<OkObjectResult>(await controller.ResolveAsync(body, default));

        result.Value.Should().Be(reference);
        controller.Response.Headers.CacheControl.ToString().Should().Be("no-store");
        JsonSerializer.Serialize(result.Value, Json).Should().Contain("\"secretName\":\"provider-openai\"");
    }

    [Fact]
    public async Task AProviderWithoutAnActiveCredentialIs404()
    {
        _resolver.Setup(r => r.ResolveAsync("sarvam", default)).ReturnsAsync((ResolvedProviderCredential?)null);
        var controller = Controller();
        var body = Body("sarvam");
        Sign(controller.HttpContext, body);

        var result = Assert.IsType<NotFoundObjectResult>(await controller.ResolveAsync(body, default));

        JsonSerializer.Serialize(result.Value).Should().Contain("PROVIDER_CREDENTIAL_NOT_FOUND");
    }

    [Theory]
    [InlineData("certificate")]
    [InlineData("header")]
    [InlineData("digest")]
    [InlineData("purpose")]
    [InlineData("actorSource")]
    [InlineData("replay")]
    public async Task AnInvalidWorkloadCallCannotReachTheResolver(string defect)
    {
        _resolver
            .Setup(r => r.ResolveAsync("openai", default))
            .ReturnsAsync(new ResolvedProviderCredential("openai", "provider-openai", "abc123", "bearer"));
        var controller = Controller();
        var body = Body("openai");
        Sign(
            controller.HttpContext,
            defect == "digest" ? Body("other") : body,
            defect == "purpose" ? "CONVERSATION_INFERENCE_OWNER" : "PROVIDER_CREDENTIAL_RESOLVE",
            defect == "actorSource" ? "BP_SESSION" : "WORKLOAD"
        );
        if (defect == "certificate")
            controller.HttpContext.Connection.ClientCertificate = null;
        if (defect == "header")
            controller.Request.Headers.Authorization = "Bearer malformed";
        if (defect == "replay")
            Assert.IsType<OkObjectResult>(await controller.ResolveAsync(body, default));

        var result = Assert.IsType<ObjectResult>(await controller.ResolveAsync(body, default));

        result.StatusCode.Should().Be(403);
        _resolver.Invocations.Count.Should().Be(defect == "replay" ? 1 : 0);
    }

    [Theory]
    [InlineData("Not Valid")]
    [InlineData("")]
    public async Task AnInvalidProviderNameIsRefusedAfterAuthentication(string name)
    {
        var controller = Controller();
        var body = Body(name);
        Sign(controller.HttpContext, body);

        var result = Assert.IsType<BadRequestObjectResult>(await controller.ResolveAsync(body, default));

        JsonSerializer.Serialize(result.Value).Should().Contain("PROVIDER_INVALID");
    }
}
