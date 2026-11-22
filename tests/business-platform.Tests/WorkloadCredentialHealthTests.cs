// Implements: ADR-046 sections 5.2, 5.3 and 12.2 D4, D6, D9; workload-identity-cloud-issuance-contract.md section 8
// constitutional_basis: C-023, C-059, C-063, C-083, C-084, C-085

using System.Net;
using System.Text.Json;
using FluentAssertions;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class WorkloadCredentialHealthTests : IDisposable
{
    private readonly TestPki _pki = new();
    private readonly WorkloadIdentityClient _identity;

    public WorkloadCredentialHealthTests() =>
        _identity = WorkloadIdentityClient.CreateReloadable(
            new WorkloadCredentialSettings("business-platform", TestPki.TrustDomain),
            new TestClock(_pki.Now)
        );

    [Fact]
    public async Task WithoutAnIdentityTheCheckIsHealthyAndEmpty()
    {
        var result = await new WorkloadCredentialHealthCheck().CheckHealthAsync(
            new HealthCheckContext()
        );

        result.Status.Should().Be(HealthStatus.Healthy);
        result.Data.Should().BeEmpty();
    }

    [Fact]
    public async Task UnavailableCredentialsNeverMakeThePlatformUnhealthy()
    {
        var links = new OwnerLinkState();
        links.Set("billing", OwnerLinkStatus.Unavailable);
        links.Set("professional-runtime", OwnerLinkStatus.Unconfigured);

        var result = await new WorkloadCredentialHealthCheck(_identity, links).CheckHealthAsync(
            new HealthCheckContext()
        );

        result.Status.Should().Be(HealthStatus.Healthy);
        result.Data["credential_source"].Should().Be("keyvault");
        result.Data["credential_state"].Should().Be("UNAVAILABLE");
        result.Data.Should().NotContainKey("credential_remaining_seconds");
        result.Data.Should().NotContainKey("credential_bundle_version");
        result
            .Data["owner_links"]
            .Should()
            .BeEquivalentTo(
                new Dictionary<string, string>
                {
                    ["billing"] = "UNAVAILABLE",
                    ["professional-runtime"] = "UNCONFIGURED",
                }
            );
    }

    [Fact]
    public async Task ReadyCredentialsExposeOnlyCoarseStateAndNoSecrets()
    {
        var issued = _pki.Create(new CredentialOptions { Version = 42 });
        _identity.Apply(issued.Bundle, issued.Trust);
        var links = new OwnerLinkState();
        links.Set("billing", OwnerLinkStatus.Ready);

        var result = await new WorkloadCredentialHealthCheck(_identity, links).CheckHealthAsync(
            new HealthCheckContext()
        );

        result.Status.Should().Be(HealthStatus.Healthy);
        result.Data["credential_state"].Should().Be("READY");
        result.Data["credential_bundle_version"].Should().Be(42L);
        ((long)result.Data["credential_remaining_seconds"]).Should().BeInRange(1, 86_400);
        var serialized = JsonSerializer.Serialize(result.Data);
        serialized
            .Should()
            .NotContain("PRIVATE")
            .And.NotContain("BEGIN")
            .And.NotContain("spiffe://");
        serialized.Should().NotContain(issued.TlsKeyPem).And.NotContain(issued.DelegationKeyId);
        result
            .Data.Keys.Should()
            .BeSubsetOf([
                "credential_source",
                "credential_state",
                "credential_remaining_seconds",
                "credential_bundle_version",
                "owner_links",
            ]);
    }

    [Fact]
    public async Task KeyVaultWithoutOwnerStateReportsAnEmptyLinkMap()
    {
        var result = await new WorkloadCredentialHealthCheck(_identity).CheckHealthAsync(
            new HealthCheckContext()
        );

        ((IReadOnlyDictionary<string, string>)result.Data["owner_links"]).Should().BeEmpty();
    }

    [Fact]
    public async Task KeyVaultApplicationStartsWithoutAVaultAndReportsDetailWithoutGatingReadiness()
    {
        using var baseFactory = new WebApplicationFactory<Program>();
        using var factory = baseFactory.WithWebHostBuilder(builder =>
        {
            builder.UseSetting("WAOOAW_WID_SOURCE", "keyvault");
            builder.UseSetting("WAOOAW_WID_VAULT_URL", "https://waooaw-demo.vault.azure.net/");
            builder.UseSetting("WAOOAW_WID_TRUST_DOMAIN", "waooaw.test");
            builder.UseSetting("WAOOAW_WID_REFRESH_SECONDS", "30");
            builder.UseSetting("ProfessionalRuntime:RelationshipWorkspaceBaseUrl", string.Empty);
            builder.UseSetting(
                "BillingEngine:RelationshipWorkspaceBaseUrl",
                "https://billing.test"
            );
            builder.ConfigureAppConfiguration(
                (_, configuration) =>
                    configuration.AddInMemoryCollection(
                        new Dictionary<string, string?>
                        {
                            ["Keycloak:Authority"] = "https://identity.test/realms/waooaw",
                            ["Keycloak:Audience"] = "bp-tests",
                            ["Keycloak:RequireHttpsMetadata"] = "false",
                            ["BillingEngine:BaseUrl"] = "https://billing-public.test",
                            ["BillingEngine:OpsAuthToken"] = "test-ops-token",
                            ["ProfessionalRuntime:VoiceBaseUrl"] = "https://runtime.test",
                            ["Voice:ProfessionalRuntimeJwtSecret"] = new string('v', 32),
                            ["Conversation:CursorHmacKey"] = new string('c', 32),
                            ["ConnectionStrings:DefaultConnection"] =
                                "Host=database;Database=bp;Username=bp",
                        }
                    )
            );
        });
        using var client = factory.CreateClient();

        var live = await client.GetAsync("/health/live");
        var detail = await client.GetAsync("/health/detail");

        live.StatusCode.Should().Be(HttpStatusCode.OK);
        detail.StatusCode.Should().Be(HttpStatusCode.OK);
        using var document = JsonDocument.Parse(await detail.Content.ReadAsStringAsync());
        document.RootElement.GetProperty("status").GetString().Should().Be("Healthy");
        var credentials = document.RootElement.GetProperty("workload_credentials");
        credentials.GetProperty("credential_source").GetString().Should().Be("keyvault");
        credentials.GetProperty("credential_state").GetString().Should().Be("UNAVAILABLE");
        var owners = credentials.GetProperty("owner_links");
        owners.GetProperty("billing").GetString().Should().Be("UNAVAILABLE");
        owners.GetProperty("professional-runtime").GetString().Should().Be("UNCONFIGURED");
        var pricing = factory.Services.GetRequiredService<IPricingAdminGateway>();
        await pricing
            .Invoking(value =>
                value.SendAsync(
                    new PricingGatewayRequest(
                        "list_prices",
                        "GET",
                        "/r",
                        "/r",
                        null,
                        [],
                        "actor",
                        "FOUNDER",
                        false,
                        Guid.NewGuid(),
                        "pricing",
                        Guid.NewGuid(),
                        null
                    ),
                    CancellationToken.None
                )
            )
            .Should()
            .ThrowAsync<PricingAdminOwnerUnavailableException>();
    }

    public void Dispose()
    {
        _identity.Dispose();
        _pki.Dispose();
    }
}
