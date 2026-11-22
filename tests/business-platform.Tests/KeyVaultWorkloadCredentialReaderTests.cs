// Implements: ADR-046 sections 4.2, 5.1 and 12.2 D4; workload-identity-cloud-issuance-contract.md section 8
// constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-083, C-084, C-085

using System.Net;
using FluentAssertions;
using Microsoft.Extensions.Configuration;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class WorkloadCredentialOptionsTests
{
    [Theory]
    [InlineData("https://waooaw-demo.vault.azure.net/")]
    [InlineData("https://waooaw-demo.vault.azure.net")]
    [InlineData("HTTPS://WAOOAW-DEMO.VAULT.AZURE.NET/")]
    public void OnlyHttpsAzureVaultHostsAreAccepted(string url)
    {
        Options(url).VaultUri.Should().NotBeNull();
        Options(url).Validate().Should().BeNull();
    }

    [Theory]
    [InlineData("http://waooaw-demo.vault.azure.net/")]
    [InlineData("https://vault.azure.net/")]
    [InlineData("https://kv.vault.azure.net.evil.example/")]
    [InlineData("https://evilvault.azure.net/")]
    [InlineData("https://vault.azure.net.example/")]
    [InlineData("https://user:pw@waooaw-demo.vault.azure.net/")]
    [InlineData("https://waooaw-demo.vault.azure.net/secrets")]
    [InlineData("https://waooaw-demo.vault.azure.net/?x=1")]
    [InlineData("https://waooaw-demo.vault.azure.net/#x")]
    [InlineData("https://127.0.0.1/")]
    [InlineData("waooaw-demo.vault.azure.net")]
    [InlineData("")]
    public void OtherVaultUrlsAreRefused(string url)
    {
        Options(url).VaultUri.Should().BeNull();
        Options(url).Validate().Should().Be("CONFIG_VAULT_URL");
    }

    [Fact]
    public void ValidationOnlyAppliesToKeyVaultAndChecksWorkloadAndTrustDomain()
    {
        new WorkloadCredentialOptions().Validate().Should().BeNull();
        Options("https://x.vault.azure.net/", workload: "billing-engine")
            .Validate()
            .Should()
            .Be("CONFIG_WORKLOAD");
        Options("https://x.vault.azure.net/", trustDomain: " ")
            .Validate()
            .Should()
            .Be("CONFIG_TRUST_DOMAIN");
    }

    [Fact]
    public void ConfigurationDefaultsToDirectoryAndEnforcesTheMinimumRefresh()
    {
        WorkloadCredentialOptions
            .From(Config())
            .Should()
            .BeEquivalentTo(new WorkloadCredentialOptions());
        var options = WorkloadCredentialOptions.From(
            Config(
                ("WAOOAW_WID_SOURCE", " KeyVault "),
                ("WAOOAW_WID_REFRESH_SECONDS", "5"),
                ("WAOOAW_WID_TRUST_DOMAIN", " demo.waooaw.internal "),
                ("WAOOAW_WID_MANAGED_IDENTITY_CLIENT_ID", " client ")
            )
        );

        options.IsKeyVault.Should().BeTrue();
        options.RefreshSeconds.Should().Be(30);
        options.TrustDomain.Should().Be("demo.waooaw.internal");
        options.ManagedIdentityClientId.Should().Be("client");
        options.Workload.Should().Be("business-platform");
        WorkloadCredentialOptions
            .From(Config(("WAOOAW_WID_REFRESH_SECONDS", "900")))
            .RefreshSeconds.Should()
            .Be(900);
        WorkloadCredentialOptions
            .From(Config(("WAOOAW_WID_REFRESH_SECONDS", "soon")))
            .RefreshSeconds.Should()
            .Be(300);
    }

    internal static WorkloadCredentialOptions Options(
        string url,
        string workload = "business-platform",
        string trustDomain = "waooaw.test",
        string client = ""
    ) =>
        new()
        {
            Source = "keyvault",
            VaultUrl = url,
            Workload = workload,
            TrustDomain = trustDomain,
            ManagedIdentityClientId = client,
        };

    private static IConfiguration Config(params (string Key, string Value)[] values) =>
        new ConfigurationBuilder()
            .AddInMemoryCollection(values.ToDictionary(v => v.Key, v => (string?)v.Value))
            .Build();
}

public sealed class KeyVaultWorkloadCredentialReaderTests
{
    private const string Vault = "https://waooaw-demo.vault.azure.net/";

    [Fact]
    public async Task ReadsBothDocumentsWithTheManagedIdentityTokenAndNothingElse()
    {
        var seen = new List<HttpRequestMessage>();
        var reader = Reader(
            request =>
            {
                seen.Add(request);
                return request.RequestUri!.AbsolutePath switch
                {
                    "/msi/token" => Json(
                        """{"access_token":"tok","resource":"https://vault.azure.net/"}"""
                    ),
                    "/secrets/wid-bundle-business-platform" => Json("""{"value":"BUNDLE"}"""),
                    "/secrets/wid-trust-bundle" => Json(
                        """{"value":"TRUST","attributes":{"enabled":true}}"""
                    ),
                    _ => new HttpResponseMessage(HttpStatusCode.NotFound),
                };
            },
            WorkloadCredentialOptionsTests.Options(Vault, client: "uami id")
        );

        var documents = await reader.ReadAsync(CancellationToken.None);

        documents.Should().Be(new WorkloadCredentialDocuments("BUNDLE", "TRUST"));
        seen.Select(r => r.RequestUri!.AbsoluteUri)
            .Should()
            .Equal(
                "http://127.0.0.1:42356/msi/token?api-version=2019-08-01&resource=https%3A%2F%2Fvault.azure.net&client_id=uami%20id",
                $"{Vault}secrets/wid-bundle-business-platform?api-version=7.4",
                $"{Vault}secrets/wid-trust-bundle?api-version=7.4"
            );
        seen[0].Headers.GetValues("X-IDENTITY-HEADER").Should().Equal("header-secret");
        seen[0].Headers.Authorization.Should().BeNull();
        seen.Skip(1).Should().OnlyContain(r => r.Headers.Authorization!.ToString() == "Bearer tok");
        seen.Skip(1).Should().OnlyContain(r => !r.Headers.Contains("X-IDENTITY-HEADER"));
    }

    [Theory]
    [InlineData(null, "header")]
    [InlineData("http://127.0.0.1:42356/msi/token", null)]
    [InlineData("http://127.0.0.1:42356/msi/token", " ")]
    [InlineData("https://127.0.0.1:42356/msi/token", "header")]
    [InlineData("http://169.254.169.254/msi/token", "header")]
    [InlineData("http://evil.example/msi/token", "header")]
    [InlineData("http://user:pw@127.0.0.1/msi/token", "header")]
    [InlineData("http://127.0.0.1/msi/token?x=1", "header")]
    [InlineData("not a url", "header")]
    public async Task TokenEndpointMustBeTheLoopbackManagedIdentityEndpoint(
        string? endpoint,
        string? header
    )
    {
        var called = false;
        var reader = Reader(
            _ =>
            {
                called = true;
                return Json("{}");
            },
            WorkloadCredentialOptionsTests.Options(Vault),
            endpoint,
            header
        );

        await Fails(reader, "IDENTITY_ENDPOINT_UNAVAILABLE");
        called.Should().BeFalse();
    }

    [Theory]
    [InlineData("""{"resource":"https://vault.azure.net"}""")]
    [InlineData("""{"access_token":" ","resource":"https://vault.azure.net"}""")]
    [InlineData("""{"access_token":"tok"}""")]
    [InlineData("""{"access_token":"tok","resource":"https://management.azure.com"}""")]
    [InlineData("""{"access_token":1,"resource":"https://vault.azure.net"}""")]
    [InlineData("[]")]
    public async Task TokenResponseMustCarryAVaultAudienceToken(string body)
    {
        var reader = Reader(_ => Json(body), WorkloadCredentialOptionsTests.Options(Vault));

        await Fails(reader, "IDENTITY_TOKEN_DENIED");
    }

    [Fact]
    public async Task TokenFailureIsDeniedAndNeverEchoesTheHeader()
    {
        var reader = Reader(
            _ => new HttpResponseMessage(HttpStatusCode.Unauthorized),
            WorkloadCredentialOptionsTests.Options(Vault)
        );

        var failure = await Fails(reader, "IDENTITY_TOKEN_DENIED");
        failure.ToString().Should().NotContain("header-secret");
    }

    [Theory]
    [InlineData("""{"value":"x","attributes":{"enabled":false}}""")]
    [InlineData("""{"value":""}""")]
    [InlineData("""{"value":null}""")]
    [InlineData("""{"other":"x"}""")]
    [InlineData("[]")]
    public async Task DisabledEmptyOrMalformedSecretsAreDenied(string secret)
    {
        var reader = Reader(
            request =>
                request.RequestUri!.AbsolutePath == "/msi/token"
                    ? Json("""{"access_token":"tok","resource":"https://vault.azure.net"}""")
                    : Json(secret),
            WorkloadCredentialOptionsTests.Options(Vault)
        );

        await Fails(reader, "SECRET_READ_DENIED");
    }

    [Fact]
    public async Task ForbiddenSecretIsDeniedAndTransportFailuresAreUnreachable()
    {
        var forbidden = Reader(
            request =>
                request.RequestUri!.AbsolutePath == "/msi/token"
                    ? Json("""{"access_token":"tok","resource":"https://vault.azure.net"}""")
                    : new HttpResponseMessage(HttpStatusCode.Forbidden),
            WorkloadCredentialOptionsTests.Options(Vault)
        );
        var down = Reader(
            _ => throw new HttpRequestException("refused"),
            WorkloadCredentialOptionsTests.Options(Vault)
        );
        var timeout = Reader(
            _ => throw new TaskCanceledException("timeout"),
            WorkloadCredentialOptionsTests.Options(Vault)
        );
        var garbage = Reader(_ => Json("<html>"), WorkloadCredentialOptionsTests.Options(Vault));

        await Fails(forbidden, "SECRET_READ_DENIED");
        await Fails(down, "VAULT_UNREACHABLE");
        await Fails(timeout, "VAULT_UNREACHABLE");
        await Fails(garbage, "VAULT_UNREACHABLE");
    }

    [Fact]
    public async Task CallerCancellationIsNotReportedAsAVaultFailure()
    {
        using var cancel = new CancellationTokenSource();
        var reader = Reader(
            _ =>
            {
                cancel.Cancel();
                throw new TaskCanceledException();
            },
            WorkloadCredentialOptionsTests.Options(Vault)
        );

        var read = () => reader.ReadAsync(cancel.Token);

        await read.Should().ThrowAsync<OperationCanceledException>();
    }

    [Theory]
    [InlineData("http://waooaw-demo.vault.azure.net/", "workload", "td", "CONFIG_VAULT_URL")]
    [InlineData("", "workload", "td", "CONFIG_VAULT_URL")]
    public async Task InvalidConfigurationNeverContactsTheNetwork(
        string url,
        string workload,
        string trustDomain,
        string code
    )
    {
        var called = false;
        var reader = Reader(
            _ =>
            {
                called = true;
                return Json("{}");
            },
            WorkloadCredentialOptionsTests.Options(url, workload, trustDomain)
        );

        await Fails(reader, code);
        called.Should().BeFalse();
    }

    [Fact]
    public async Task WorkloadAndTrustDomainConfigurationErrorsAreReportedBeforeAnyRequest()
    {
        var called = false;
        HttpResponseMessage Respond(HttpRequestMessage _)
        {
            called = true;
            return Json("{}");
        }

        await Fails(
            Reader(
                Respond,
                WorkloadCredentialOptionsTests.Options(Vault, workload: "billing-engine")
            ),
            "CONFIG_WORKLOAD"
        );
        await Fails(
            Reader(Respond, WorkloadCredentialOptionsTests.Options(Vault, trustDomain: "")),
            "CONFIG_TRUST_DOMAIN"
        );
        called.Should().BeFalse();
    }

    private static async Task<WorkloadCredentialReadException> Fails(
        KeyVaultWorkloadCredentialReader reader,
        string code
    )
    {
        var failure = await reader
            .Invoking(value => value.ReadAsync(CancellationToken.None))
            .Should()
            .ThrowAsync<WorkloadCredentialReadException>();
        failure.Which.Code.Should().Be(code);
        return failure.Which;
    }

    private static KeyVaultWorkloadCredentialReader Reader(
        Func<HttpRequestMessage, HttpResponseMessage> respond,
        WorkloadCredentialOptions options,
        string? endpoint = "http://127.0.0.1:42356/msi/token",
        string? header = "header-secret"
    ) =>
        new(
            new HttpClient(new WorkloadCredentialRefresherTests.Responder(respond)),
            new ConfigurationBuilder()
                .AddInMemoryCollection(
                    new Dictionary<string, string?>
                    {
                        ["IDENTITY_ENDPOINT"] = endpoint,
                        ["IDENTITY_HEADER"] = header,
                    }
                )
                .Build(),
            options
        );

    private static HttpResponseMessage Json(string body) =>
        WorkloadCredentialRefresherTests.Json(HttpStatusCode.OK, body);
}
