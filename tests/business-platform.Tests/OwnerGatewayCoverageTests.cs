// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// constitutional_basis: C-002, C-023, C-026, C-059, C-076, C-083, C-084, C-085
using System.Diagnostics;
using System.Net;
using System.Reflection;
using System.Text;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class OwnerGatewayIdentityFixture : IDisposable
{
    private readonly string _credentials = Path.Combine(
        Path.GetTempPath(), $"waooaw-owner-gateways-{Guid.NewGuid():N}");

    public OwnerGatewayIdentityFixture()
    {
        var process = Process.Start(new ProcessStartInfo
        {
            FileName = "python3",
            ArgumentList =
            {
                RepositoryPaths.Resolve("scripts/bootstrap_workload_identity.py"),
                "--registry", RepositoryPaths.Resolve("infrastructure/workload-identity/registry.yaml"),
                "--environment", "ci", "--output", _credentials,
            },
            RedirectStandardError = true,
            UseShellExecute = false,
        }) ?? throw new InvalidOperationException("Could not start credential bootstrap");
        process.WaitForExit();
        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException(process.StandardError.ReadToEnd());
        }
    }

    public WorkloadIdentityClient CreateIdentity() => WorkloadIdentityClient.Load(_credentials);

    public string CredentialsPath => _credentials;

    public void Dispose()
    {
        if (Directory.Exists(_credentials)) Directory.Delete(_credentials, recursive: true);
    }
}

public sealed class OwnerGatewayCoverageTests(OwnerGatewayIdentityFixture fixture)
    : IClassFixture<OwnerGatewayIdentityFixture>
{
    [Fact]
    public async Task ConfiguredApplication_ComposesAuthenticatedOwnerGateways()
    {
        using var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            builder.UseSetting("WAOOAW_WORKLOAD_CREDENTIALS", fixture.CredentialsPath);
            builder.UseSetting("ProfessionalRuntime:RelationshipWorkspaceBaseUrl", "https://runtime.test");
            builder.UseSetting("BillingEngine:RelationshipWorkspaceBaseUrl", "https://billing.test");
            builder.ConfigureAppConfiguration((_, configuration) => configuration.AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    ["Keycloak:Authority"] = "https://identity.test/realms/waooaw",
                    ["Keycloak:Audience"] = "bp-tests",
                    ["Keycloak:RequireHttpsMetadata"] = "false",
                    ["WAOOAW_WORKLOAD_CREDENTIALS"] = fixture.CredentialsPath,
                    ["ProfessionalRuntime:RelationshipWorkspaceBaseUrl"] = "https://runtime.test",
                    ["BillingEngine:RelationshipWorkspaceBaseUrl"] = "https://billing.test",
                    ["BillingEngine:BaseUrl"] = "https://billing-public.test",
                    ["BillingEngine:OpsAuthToken"] = "test-ops-token",
                    ["ProfessionalRuntime:VoiceBaseUrl"] = "https://runtime.test",
                    ["Voice:ProfessionalRuntimeJwtSecret"] = new string('v', 32),
                    ["ConnectionStrings:DefaultConnection"] = "Host=database;Database=bp;Username=bp",
                }));
        });
        using var client = factory.CreateClient();

        var response = await client.GetAsync("/health");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.IsType<AuthenticatedRelationshipWorkspaceOwnerGateway>(
            factory.Services.GetRequiredService<IRelationshipWorkspaceOwnerGateway>());
        Assert.IsType<HttpRelationshipTrialOwnerGateway>(
            factory.Services.GetRequiredService<IRelationshipTrialOwnerGateway>());
        Assert.IsType<AuthenticatedOfferabilityOwnerGateway>(
            factory.Services.GetRequiredService<IOfferabilityOwnerGateway>());
        Assert.IsType<AuthenticatedActivationBillingGateway>(
            factory.Services.GetRequiredService<IActivationBillingGateway>());
    }

    [Fact]
    public async Task OfferabilityOwner_ReturnsCanonicalValidation()
    {
        var request = OfferabilityRequest();
        var producedAt = DateTimeOffset.UtcNow;
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedOfferabilityOwnerGateway(identity, new Uri("https://billing.test"));
        ReplaceClient(gateway, "_billingEngine", Handler((message, _) => Json(HttpStatusCode.OK, $$"""
            {
              "relationshipId": "{{request.RelationshipId:D}}",
              "offeringId": "{{request.OfferingId}}",
              "outcome": "APPROVED",
              "costFloorPaise": 5000,
              "minimumCompliantPricePaise": 6250,
              "proposedPricePaise": {{request.ProposedPricePaise}},
              "directContributionPaise": 2000,
              "validationVersion": "owner-7",
              "producedAt": "{{producedAt:O}}"
            }
            """)));

        var result = await gateway.ValidateAsync(request, CancellationToken.None);

        Assert.NotNull(result);
        Assert.Equal("APPROVED", result.Outcome);
        Assert.Equal(2_000, result.DirectContributionPaise);
    }

    [Theory]
    [InlineData("relationshipId")]
    [InlineData("offeringId")]
    [InlineData("proposedPricePaise")]
    public async Task OfferabilityOwner_RejectsMismatchedOwnerIdentity(string mismatch)
    {
        var request = OfferabilityRequest();
        var relationshipId = mismatch == "relationshipId" ? Guid.NewGuid() : request.RelationshipId;
        var offeringId = mismatch == "offeringId" ? "other" : request.OfferingId;
        var price = mismatch == "proposedPricePaise" ? request.ProposedPricePaise + 1 : request.ProposedPricePaise;
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedOfferabilityOwnerGateway(identity, new Uri("https://billing.test"));
        ReplaceClient(gateway, "_billingEngine", Handler((_, _) => Json(HttpStatusCode.OK, $$"""
            {
              "relationshipId": "{{relationshipId:D}}", "offeringId": "{{offeringId}}", "outcome": "APPROVED",
              "costFloorPaise": 1, "minimumCompliantPricePaise": 1, "proposedPricePaise": {{price}},
              "directContributionPaise": 1, "validationVersion": "v1", "producedAt": "{{DateTimeOffset.UtcNow:O}}"
            }
            """)));

        Assert.Null(await gateway.ValidateAsync(request, CancellationToken.None));
    }

    [Theory]
    [InlineData(HttpStatusCode.ServiceUnavailable, "{}")]
    [InlineData(HttpStatusCode.OK, "{invalid")]
    public async Task OfferabilityOwner_FailsClosedForUnusableResponse(HttpStatusCode status, string body)
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedOfferabilityOwnerGateway(identity, new Uri("https://billing.test"));
        ReplaceClient(gateway, "_billingEngine", Handler((_, _) => Json(status, body)));

        Assert.Null(await gateway.ValidateAsync(OfferabilityRequest(), CancellationToken.None));
    }

    [Fact]
    public async Task WorkspaceOwners_ReturnCanonicalExecutionAndCommercialProjections()
    {
        var context = OwnerContext();
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedRelationshipWorkspaceOwnerGateway(
            identity, new Uri("https://runtime.test"), new Uri("https://billing.test"));
        ReplaceClient(gateway, "_professionalRuntime", Handler((_, _) => Json(HttpStatusCode.OK, $$"""
            {"schemaVersion":"1.0","relationshipId":"{{context.RelationshipId:D}}","projectionVersion":"execution-3","state":"ACTIVE","producedAt":"{{DateTimeOffset.UtcNow:O}}"}
            """)));
        ReplaceClient(gateway, "_billingEngine", Handler((_, _) => Json(HttpStatusCode.OK, $$"""
            {"schemaVersion":"1.0","relationshipId":"{{context.RelationshipId:D}}","projectionVersion":"commercial-4","currencyState":"INR","actuals":"100","forecast":"200","thresholds":"300","producedAt":"{{DateTimeOffset.UtcNow:O}}"}
            """)));

        var execution = await gateway.GetExecutionAsync(context, CancellationToken.None);
        var commercial = await gateway.GetCommercialAsync(context, CancellationToken.None);

        Assert.Equal("ACTIVE", execution?.State);
        Assert.Equal("INR", commercial?.CurrencyState);
    }

    [Theory]
    [InlineData(HttpStatusCode.BadGateway, "{}")]
    [InlineData(HttpStatusCode.OK, "{invalid")]
    [InlineData(HttpStatusCode.OK, "{\"schemaVersion\":\"2.0\"}")]
    public async Task WorkspaceOwners_FailClosedForUnusableResponses(HttpStatusCode status, string body)
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedRelationshipWorkspaceOwnerGateway(
            identity, new Uri("https://runtime.test"), new Uri("https://billing.test"));
        ReplaceClient(gateway, "_professionalRuntime", Handler((_, _) => Json(status, body)));
        ReplaceClient(gateway, "_billingEngine", Handler((_, _) => Json(status, body)));
        var context = OwnerContext();

        Assert.Null(await gateway.GetExecutionAsync(context, CancellationToken.None));
        Assert.Null(await gateway.GetCommercialAsync(context, CancellationToken.None));
    }

    [Fact]
    public async Task WorkspaceOwners_FailClosedForTransportFailure()
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedRelationshipWorkspaceOwnerGateway(
            identity, new Uri("https://runtime.test"), new Uri("https://billing.test"));
        ReplaceClient(gateway, "_professionalRuntime", Handler((_, _) => throw new HttpRequestException("offline")));
        ReplaceClient(gateway, "_billingEngine", Handler((_, _) => throw new TaskCanceledException("timeout")));
        var context = OwnerContext();

        Assert.Null(await gateway.GetExecutionAsync(context, CancellationToken.None));
        Assert.Null(await gateway.GetCommercialAsync(context, CancellationToken.None));
    }

    [Fact]
    public async Task TrialOwners_ReturnCanonicalWbeAndProfessionalRuntimeResults()
    {
        var trialId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var startsAt = DateTimeOffset.UtcNow;
        using var identity = fixture.CreateIdentity();
        var factory = new StubClientFactory(Handler((_, _) => Json(HttpStatusCode.Created, $$"""
            {"trial_id":"{{trialId:D}}","started_at":"{{startsAt:O}}","expires_at":"{{startsAt.AddDays(14):O}}"}
            """)));
        using var gateway = new HttpRelationshipTrialOwnerGateway(
            factory, identity, new Uri("https://runtime.test"));
        ReplaceClient(gateway, "_professionalRuntime", Handler((_, _) => Json(HttpStatusCode.OK, $$"""
            {"trialId":"{{trialId:D}}","workflowState":"TRIAL_DEMONSTRATING","expiresAt":"{{startsAt.AddDays(14):O}}"}
            """)));

        var wbe = await gateway.StartWbeTrialAsync(
            Guid.NewGuid(), "DMA", relationshipId, Guid.NewGuid(), CancellationToken.None);
        var runtime = await gateway.StartPrTrialAsync(
            Guid.NewGuid(), relationshipId, trialId, startsAt, startsAt.AddDays(14),
            Guid.NewGuid(), CancellationToken.None);

        Assert.Equal(trialId, wbe?.TrialId);
        Assert.Equal("TRIAL_DEMONSTRATING", runtime?.WorkflowState);
    }

    [Fact]
    public async Task TrialOwner_ConflictLoadsMatchingActiveEntitlement()
    {
        var customerId = Guid.NewGuid();
        var trialId = Guid.NewGuid();
        var startsAt = DateTimeOffset.UtcNow;
        using var identity = fixture.CreateIdentity();
        var handler = new StubHandler((request, _) => request.Method == HttpMethod.Post
            ? Json(HttpStatusCode.Conflict, "{}")
            : Json(HttpStatusCode.OK, $$"""
                {"trial_id":"{{trialId:D}}","agent_type":"DMA","status":"ACTIVE","started_at":"{{startsAt:O}}","expires_at":"{{startsAt.AddDays(14):O}}"}
                """));
        using var gateway = new HttpRelationshipTrialOwnerGateway(
            new StubClientFactory(handler), identity, new Uri("https://runtime.test"));

        var result = await gateway.StartWbeTrialAsync(
            customerId, "DMA", Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None);

        Assert.Equal(trialId, result?.TrialId);
    }

    [Theory]
    [InlineData(HttpStatusCode.BadGateway, "{}")]
    [InlineData(HttpStatusCode.OK, "{invalid")]
    public async Task TrialOwners_FailClosedForUnusableResponses(HttpStatusCode status, string body)
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new HttpRelationshipTrialOwnerGateway(
            new StubClientFactory(Handler((_, _) => Json(status, body))),
            identity,
            new Uri("https://runtime.test"));
        ReplaceClient(gateway, "_professionalRuntime", Handler((_, _) => Json(status, body)));

        Assert.Null(await gateway.StartWbeTrialAsync(
            Guid.NewGuid(), "DMA", Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None));
        Assert.Null(await gateway.StartPrTrialAsync(
            Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), DateTimeOffset.UtcNow,
            DateTimeOffset.UtcNow.AddDays(14), Guid.NewGuid(), CancellationToken.None));
    }

    private static OfferabilityEvaluationRequest OfferabilityRequest() => new(
        Guid.NewGuid(), Guid.NewGuid(), 3, Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(),
        "dma-starter-v1", "DMA", "STARTER", 7_000);

    private static RelationshipOwnerContext OwnerContext() => new(
        "actor", "EMPLOYER", Guid.NewGuid(), Guid.NewGuid(), 3, Guid.NewGuid().ToString("D"));

    private static HttpResponseMessage Json(HttpStatusCode status, string body) => new(status)
    {
        Content = new StringContent(body, Encoding.UTF8, "application/json"),
    };

    private static StubHandler Handler(
        Func<HttpRequestMessage, CancellationToken, HttpResponseMessage> send) => new(send);

    private static void ReplaceClient(object target, string fieldName, StubHandler handler)
    {
        var field = target.GetType().GetField(fieldName, BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException($"Missing field {fieldName}");
        var original = Assert.IsType<HttpClient>(field.GetValue(target));
        field.SetValue(target, new HttpClient(handler) { BaseAddress = new Uri("https://owner.test") });
        original.Dispose();
    }

    private sealed class StubClientFactory(StubHandler handler) : IHttpClientFactory
    {
        public HttpClient CreateClient(string name) => new(handler, disposeHandler: false)
        {
            BaseAddress = new Uri("https://wbe.test"),
        };
    }

    private sealed class StubHandler(
        Func<HttpRequestMessage, CancellationToken, HttpResponseMessage> send) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken) => Task.FromResult(send(request, cancellationToken));
    }
}
