// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-09
// constitutional_basis: C-002, C-023, C-026, C-059, C-076, C-083, C-084, C-085
using System.Diagnostics;
using System.Net;
using System.Reflection;
using System.Text;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Moq;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Spend;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class OwnerGatewayIdentityFixture : IDisposable
{
    private readonly string _credentials = Path.Combine(
        Path.GetTempPath(),
        $"waooaw-owner-gateways-{Guid.NewGuid():N}"
    );

    public OwnerGatewayIdentityFixture()
    {
        var process =
            Process.Start(
                new ProcessStartInfo
                {
                    FileName = "python3",
                    ArgumentList =
                    {
                        RepositoryPaths.Resolve("scripts/bootstrap_workload_identity.py"),
                        "--registry",
                        RepositoryPaths.Resolve("infrastructure/workload-identity/registry.yaml"),
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
        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException(process.StandardError.ReadToEnd());
        }
    }

    public WorkloadIdentityClient CreateIdentity() => WorkloadIdentityClient.Load(_credentials);

    public string CredentialsPath => _credentials;

    public void Dispose()
    {
        if (Directory.Exists(_credentials))
            Directory.Delete(_credentials, recursive: true);
    }
}

public sealed class OwnerGatewayCoverageTests(OwnerGatewayIdentityFixture fixture)
    : IClassFixture<OwnerGatewayIdentityFixture>
{
    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task ConfiguredApplication_ComposesConversationIdentityIndependentlyOfWorkspaceUrls(
        bool workspaceConfigured
    )
    {
        using var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            builder.UseSetting("WAOOAW_WORKLOAD_CREDENTIALS", fixture.CredentialsPath);
            builder.UseSetting(
                "ProfessionalRuntime:RelationshipWorkspaceBaseUrl",
                workspaceConfigured ? "https://runtime.test" : string.Empty
            );
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
                            ["WAOOAW_WORKLOAD_CREDENTIALS"] = fixture.CredentialsPath,
                            ["ProfessionalRuntime:RelationshipWorkspaceBaseUrl"] =
                                workspaceConfigured ? "https://runtime.test" : null,
                            ["BillingEngine:RelationshipWorkspaceBaseUrl"] = workspaceConfigured
                                ? "https://billing.test"
                                : null,
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
        using var runtimeClient = factory
            .Services.GetRequiredService<IHttpClientFactory>()
            .CreateClient("ConversationProfessionalRuntime");
        Assert.Equal(Uri.UriSchemeHttps, runtimeClient.BaseAddress!.Scheme);

        var response = await client.GetAsync("/health/live");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        if (workspaceConfigured)
        {
            Assert.IsType<AuthenticatedRelationshipWorkspaceOwnerGateway>(
                factory.Services.GetRequiredService<IRelationshipWorkspaceOwnerGateway>()
            );
            Assert.IsType<HttpRelationshipTrialOwnerGateway>(
                factory.Services.GetRequiredService<IRelationshipTrialOwnerGateway>()
            );
        }
        else
        {
            Assert.IsType<UnconfiguredRelationshipWorkspaceOwnerGateway>(
                factory.Services.GetRequiredService<IRelationshipWorkspaceOwnerGateway>()
            );
        }
        Assert.IsType<AuthenticatedOfferabilityOwnerGateway>(
            factory.Services.GetRequiredService<IOfferabilityOwnerGateway>()
        );
        Assert.IsType<AuthenticatedActivationBillingGateway>(
            factory.Services.GetRequiredService<IActivationBillingGateway>()
        );
    }

    [Fact]
    public async Task OfferabilityOwner_ReturnsCanonicalValidation()
    {
        var request = OfferabilityRequest();
        var producedAt = DateTimeOffset.UtcNow;
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedOfferabilityOwnerGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(
            gateway,
            "_billingEngine",
            Handler(
                (message, _) =>
                    Json(
                        HttpStatusCode.OK,
                        $$"""
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
                        """
                    )
            )
        );

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
        var price =
            mismatch == "proposedPricePaise"
                ? request.ProposedPricePaise + 1
                : request.ProposedPricePaise;
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedOfferabilityOwnerGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(
            gateway,
            "_billingEngine",
            Handler(
                (_, _) =>
                    Json(
                        HttpStatusCode.OK,
                        $$"""
                        {
                          "relationshipId": "{{relationshipId:D}}", "offeringId": "{{offeringId}}", "outcome": "APPROVED",
                          "costFloorPaise": 1, "minimumCompliantPricePaise": 1, "proposedPricePaise": {{price}},
                          "directContributionPaise": 1, "validationVersion": "v1", "producedAt": "{{DateTimeOffset.UtcNow:O}}"
                        }
                        """
                    )
            )
        );

        Assert.Null(await gateway.ValidateAsync(request, CancellationToken.None));
    }

    [Theory]
    [InlineData(HttpStatusCode.ServiceUnavailable, "{}")]
    [InlineData(HttpStatusCode.OK, "{invalid")]
    public async Task OfferabilityOwner_FailsClosedForUnusableResponse(
        HttpStatusCode status,
        string body
    )
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedOfferabilityOwnerGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(gateway, "_billingEngine", Handler((_, _) => Json(status, body)));

        Assert.Null(await gateway.ValidateAsync(OfferabilityRequest(), CancellationToken.None));
    }

    [Fact]
    public async Task WorkspaceOwners_ReturnCanonicalExecutionAndCommercialProjections()
    {
        var context = OwnerContext();
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedRelationshipWorkspaceOwnerGateway(
            identity,
            new Uri("https://runtime.test"),
            new Uri("https://billing.test")
        );
        ReplaceClient(
            gateway,
            "_professionalRuntime",
            Handler(
                (_, _) =>
                    Json(
                        HttpStatusCode.OK,
                        $$"""
                        {"schemaVersion":"1.0","relationshipId":"{{context.RelationshipId:D}}","projectionVersion":"execution-3","state":"ACTIVE","producedAt":"{{DateTimeOffset.UtcNow:O}}"}
                        """
                    )
            )
        );
        ReplaceClient(
            gateway,
            "_billingEngine",
            Handler(
                (_, _) =>
                    Json(
                        HttpStatusCode.OK,
                        $$"""
                        {"schemaVersion":"1.0","relationshipId":"{{context.RelationshipId:D}}","projectionVersion":"commercial-4","currencyState":"INR","actuals":"100","forecast":"200","thresholds":"300","producedAt":"{{DateTimeOffset.UtcNow:O}}"}
                        """
                    )
            )
        );

        var execution = await gateway.GetExecutionAsync(context, CancellationToken.None);
        var commercial = await gateway.GetCommercialAsync(context, CancellationToken.None);

        Assert.Equal("ACTIVE", execution?.State);
        Assert.Equal("INR", commercial?.CurrencyState);
    }

    [Theory]
    [InlineData(HttpStatusCode.BadGateway, "{}")]
    [InlineData(HttpStatusCode.OK, "{invalid")]
    [InlineData(HttpStatusCode.OK, "{\"schemaVersion\":\"2.0\"}")]
    public async Task WorkspaceOwners_FailClosedForUnusableResponses(
        HttpStatusCode status,
        string body
    )
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedRelationshipWorkspaceOwnerGateway(
            identity,
            new Uri("https://runtime.test"),
            new Uri("https://billing.test")
        );
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
            identity,
            new Uri("https://runtime.test"),
            new Uri("https://billing.test")
        );
        ReplaceClient(
            gateway,
            "_professionalRuntime",
            Handler((_, _) => throw new HttpRequestException("offline"))
        );
        ReplaceClient(
            gateway,
            "_billingEngine",
            Handler((_, _) => throw new TaskCanceledException("timeout"))
        );
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
        var factory = new StubClientFactory(
            Handler(
                (_, _) =>
                    Json(
                        HttpStatusCode.Created,
                        $$"""
                        {"trial_id":"{{trialId:D}}","started_at":"{{startsAt:O}}","expires_at":"{{startsAt.AddDays(
                            14
                        ):O}}"}
                        """
                    )
            )
        );
        using var gateway = new HttpRelationshipTrialOwnerGateway(
            factory,
            identity,
            new Uri("https://runtime.test")
        );
        ReplaceClient(
            gateway,
            "_professionalRuntime",
            Handler(
                (_, _) =>
                    Json(
                        HttpStatusCode.OK,
                        $$"""
                        {"trialId":"{{trialId:D}}","workflowState":"TRIAL_DEMONSTRATING","expiresAt":"{{startsAt.AddDays(
                            14
                        ):O}}"}
                        """
                    )
            )
        );

        var wbe = await gateway.StartWbeTrialAsync(
            Guid.NewGuid(),
            "DMA",
            "1.0.0",
            relationshipId,
            Guid.NewGuid(),
            CancellationToken.None
        );
        var runtime = await gateway.StartPrTrialAsync(
            Guid.NewGuid(),
            relationshipId,
            Guid.NewGuid(),
            Guid.NewGuid(),
            "DMA",
            "1.0.0",
            trialId,
            startsAt,
            startsAt.AddDays(14),
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.Equal(trialId, wbe?.TrialId);
        Assert.Equal("TRIAL_DEMONSTRATING", runtime?.WorkflowState);
    }

    [Fact]
    public async Task TrialOwner_SendsTenantRelationshipAndIdentityHashForTheWalletCredit()
    {
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var hash = new string('b', 64);
        var startsAt = DateTimeOffset.UtcNow;
        var sent = new List<string>();
        using var identity = fixture.CreateIdentity();
        var factory = new StubClientFactory(
            Handler(
                (request, _) =>
                {
                    sent.Add(request.Content!.ReadAsStringAsync().GetAwaiter().GetResult());
                    return Json(
                        HttpStatusCode.Created,
                        $$"""
                        {"trial_id":"{{Guid.NewGuid():D}}","started_at":"{{startsAt:O}}","expires_at":"{{startsAt.AddDays(
                            14
                        ):O}}"}
                        """
                    );
                }
            )
        );
        using var gateway = new HttpRelationshipTrialOwnerGateway(
            factory,
            identity,
            new Uri("https://runtime.test")
        );

        await gateway.StartWbeTrialAsync(
            Guid.NewGuid(),
            "DMA",
            "1.0.0",
            relationshipId,
            Guid.NewGuid(),
            CancellationToken.None,
            new TrialIdentityContext(tenantId, hash)
        );

        var body = Assert.Single(sent);
        Assert.Contains($"\"tenant_id\":\"{tenantId:D}\"", body);
        Assert.Contains($"\"relationship_id\":\"{relationshipId:D}\"", body);
        Assert.Contains($"\"identity_subject_hash\":\"{hash}\"", body);
    }

    [Fact]
    public async Task TrialOwner_RefusalIsLoggedWithItsStatusAndNoBody()
    {
        using var identity = fixture.CreateIdentity();
        var logger = new Mock<ILogger<HttpRelationshipTrialOwnerGateway>>();
        logger.Setup(value => value.IsEnabled(It.IsAny<LogLevel>())).Returns(true);
        using var gateway = new HttpRelationshipTrialOwnerGateway(
            new StubClientFactory(
                Handler(
                    (_, _) =>
                        Json(HttpStatusCode.InternalServerError, "{\"secret\":\"never logged\"}")
                )
            ),
            identity,
            new Uri("https://runtime.test"),
            logger.Object
        );

        var result = await gateway.StartWbeTrialAsync(
            Guid.NewGuid(),
            "DIGITAL_MARKETING_LOCAL_SERVICE",
            "1.0.0",
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.Null(result);
        logger.Verify(
            value =>
                value.Log(
                    LogLevel.Warning,
                    It.IsAny<EventId>(),
                    It.Is<It.IsAnyType>(
                        (state, _) =>
                            state.ToString()!.Contains("500")
                            && !state.ToString()!.Contains("never logged")
                    ),
                    null,
                    It.IsAny<Func<It.IsAnyType, Exception?, string>>()
                ),
            Times.Once
        );
    }

    [Fact]
    public async Task TrialOwner_ConflictLoadsMatchingActiveEntitlement()
    {
        var customerId = Guid.NewGuid();
        var trialId = Guid.NewGuid();
        var startsAt = DateTimeOffset.UtcNow;
        using var identity = fixture.CreateIdentity();
        var handler = new StubHandler(
            (request, _) =>
                request.Method == HttpMethod.Post
                    ? Json(HttpStatusCode.Conflict, "{}")
                    : Json(
                        HttpStatusCode.OK,
                        $$"""
                        {"trial_id":"{{trialId:D}}","agent_type":"DMA","agent_version":"1.0.0","status":"ACTIVE","started_at":"{{startsAt:O}}","expires_at":"{{startsAt.AddDays(
                            14
                        ):O}}"}
                        """
                    )
        );
        using var gateway = new HttpRelationshipTrialOwnerGateway(
            new StubClientFactory(handler),
            identity,
            new Uri("https://runtime.test")
        );

        var result = await gateway.StartWbeTrialAsync(
            customerId,
            "DMA",
            "1.0.0",
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.Equal(trialId, result?.TrialId);
    }

    [Theory]
    [InlineData("ACTIVE")]
    [InlineData("EXPIRED")]
    [InlineData("CONVERTED")]
    public async Task TrialOwner_ReturnsCanonicalWbeStatus(string status)
    {
        var trialId = Guid.NewGuid();
        HttpRequestMessage? capturedRequest = null;
        using var identity = fixture.CreateIdentity();
        using var gateway = new HttpRelationshipTrialOwnerGateway(
            new StubClientFactory(
                Handler(
                    (request, _) =>
                    {
                        capturedRequest = request;
                        return Json(
                            HttpStatusCode.OK,
                            $$"""
                            {"trial_id":"{{trialId:D}}","status":"{{status}}"}
                            """
                        );
                    }
                )
            ),
            identity,
            new Uri("https://runtime.test")
        );

        var result = await gateway.GetWbeTrialStatusAsync(
            Guid.NewGuid(),
            trialId,
            CancellationToken.None
        );

        Assert.Equal(status, result?.Status);
        Assert.Equal($"?trial_id={trialId}", capturedRequest?.RequestUri?.Query);
    }

    [Fact]
    public async Task TrialOwner_RejectsMismatchedOrUnsupportedWbeStatus()
    {
        var trialId = Guid.NewGuid();
        var response = Json(
            HttpStatusCode.OK,
            $$"""
            {"trial_id":"{{Guid.NewGuid():D}}","status":"ACTIVE"}
            """
        );
        using var identity = fixture.CreateIdentity();
        using var gateway = new HttpRelationshipTrialOwnerGateway(
            new StubClientFactory(Handler((_, _) => response)),
            identity,
            new Uri("https://runtime.test")
        );

        Assert.Null(
            await gateway.GetWbeTrialStatusAsync(Guid.NewGuid(), trialId, CancellationToken.None)
        );

        response = Json(
            HttpStatusCode.OK,
            $$"""
            {"trial_id":"{{trialId:D}}","status":"UNKNOWN"}
            """
        );
        Assert.Null(
            await gateway.GetWbeTrialStatusAsync(Guid.NewGuid(), trialId, CancellationToken.None)
        );
    }

    [Theory]
    [InlineData(HttpStatusCode.BadGateway, "{}")]
    [InlineData(HttpStatusCode.OK, "{invalid")]
    public async Task TrialOwner_FailsClosedForUnusableWbeStatus(HttpStatusCode status, string body)
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new HttpRelationshipTrialOwnerGateway(
            new StubClientFactory(Handler((_, _) => Json(status, body))),
            identity,
            new Uri("https://runtime.test")
        );

        Assert.Null(
            await gateway.GetWbeTrialStatusAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
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
            new Uri("https://runtime.test")
        );
        ReplaceClient(gateway, "_professionalRuntime", Handler((_, _) => Json(status, body)));

        Assert.Null(
            await gateway.StartWbeTrialAsync(
                Guid.NewGuid(),
                "DMA",
                "1.0.0",
                Guid.NewGuid(),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
        Assert.Null(
            await gateway.StartPrTrialAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                "DMA",
                "1.0.0",
                Guid.NewGuid(),
                DateTimeOffset.UtcNow,
                DateTimeOffset.UtcNow.AddDays(14),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task OfferingUsageOwner_SignsAndReturnsEveryCanonicalReceipt()
    {
        var reservationId = Guid.NewGuid();
        var identityValue = OfferingIdentity();
        var actions = new List<string>();
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedOfferingUsageGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(
            gateway,
            "_client",
            Handler(
                (request, _) =>
                {
                    actions.Add(request.RequestUri!.Segments[^1]);
                    Assert.StartsWith("Bearer ", request.Headers.Authorization?.ToString());
                    Assert.True(request.Headers.Contains("Idempotency-Key"));
                    return Json(
                        HttpStatusCode.OK,
                        $$"""
                        {
                          "reservationId": "{{reservationId:D}}",
                          "state": "RESERVED",
                          "maximumUnits": 8192,
                          "reservedRawPaise": 9,
                          "reservedMarkedUpPaise": 12,
                          "catalogueThreadId": "thread-1",
                          "providerAccountId": "{{Guid.NewGuid():D}}",
                          "rateVersion": "rate-1",
                          "replayed": false
                        }
                        """
                    );
                }
            )
        );

        Assert.Equal(
            reservationId,
            (await gateway.ReserveAsync(identityValue, 8192, CancellationToken.None)).ReservationId
        );
        await gateway.SettleAsync(
            identityValue,
            reservationId,
            4,
            Guid.NewGuid(),
            CancellationToken.None
        );
        await gateway.ReleaseAsync(
            identityValue,
            reservationId,
            Guid.NewGuid(),
            CancellationToken.None
        );
        Assert.NotNull(
            await gateway.ReconcileAsync(identityValue, reservationId, CancellationToken.None)
        );
        Assert.Equal(["reserve", "settle", "release", "reconcile"], actions);
    }

    [Theory]
    [InlineData(HttpStatusCode.NotFound, true)]
    [InlineData(HttpStatusCode.BadGateway, false)]
    [InlineData(HttpStatusCode.OK, false)]
    public async Task OfferingUsageOwner_FailsClosedForUnresolvedOutcomes(
        HttpStatusCode status,
        bool reconcileReturnsNull
    )
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedOfferingUsageGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(
            gateway,
            "_client",
            Handler((_, _) => Json(status, status == HttpStatusCode.OK ? "null" : "{}"))
        );

        if (reconcileReturnsNull)
        {
            Assert.Null(
                await gateway.ReconcileAsync(OfferingIdentity(), null, CancellationToken.None)
            );
        }
        else
        {
            await Assert.ThrowsAsync<OfferingUsageOwnerUnavailableException>(() =>
                gateway.ReserveAsync(OfferingIdentity(), 1, CancellationToken.None)
            );
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task OfferingUsageOwner_TranslatesTransportFailures(bool cancelled)
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedOfferingUsageGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(
            gateway,
            "_client",
            Handler(
                (_, _) =>
                {
                    if (cancelled)
                        throw new TaskCanceledException("timeout");
                    throw new HttpRequestException("offline");
                }
            )
        );

        await Assert.ThrowsAsync<OfferingUsageOwnerUnavailableException>(() =>
            gateway.ReserveAsync(OfferingIdentity(), 1, CancellationToken.None)
        );
    }

    [Fact]
    public async Task PlatformAccountGateway_ReservesWithASignedRouteAndOmitsAbsentFields()
    {
        var tenant = Guid.NewGuid();
        var key = Guid.NewGuid();
        var reservation = Guid.NewGuid();
        var captured = new List<(string Path, string Body, string? Idempotency)>();
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedOfferingUsageGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(
            gateway,
            "_client",
            Handler(
                (request, _) =>
                {
                    Assert.StartsWith("Bearer ", request.Headers.Authorization?.ToString());
                    captured.Add(
                        (
                            request.RequestUri!.AbsolutePath,
                            request.Content!.ReadAsStringAsync().GetAwaiter().GetResult(),
                            request.Headers.GetValues("Idempotency-Key").Single()
                        )
                    );
                    return Json(
                        HttpStatusCode.OK,
                        $$"""
                        {
                          "schemaVersion": "1.0",
                          "accountClass": "ACQUISITION",
                          "reservationId": "{{reservation:D}}",
                          "accountId": "{{Guid.NewGuid():D}}",
                          "state": "RESERVED",
                          "reservedPaise": 120,
                          "replayed": false
                        }
                        """
                    );
                }
            )
        );

        var receipt = await gateway.ReserveAccountAsync(
            new PlatformAccountReserveRequest(
                tenant,
                Guid.NewGuid(),
                SpendAccountClass.Acquisition,
                null,
                null,
                "lead-7",
                "llm_cloud",
                120,
                null,
                Guid.NewGuid(),
                key,
                Guid.NewGuid()
            ),
            CancellationToken.None
        );

        Assert.Equal(reservation, receipt.ReservationId);
        Assert.Equal(120, receipt.ReservedPaise);
        var sent = Assert.Single(captured);
        Assert.Equal("/internal/v1/wallet/accounts/reserve", sent.Path);
        Assert.Equal(key.ToString("D"), sent.Idempotency);
        Assert.Contains("\"accountClass\":\"ACQUISITION\"", sent.Body);
        Assert.Contains("\"leadRef\":\"lead-7\"", sent.Body);
        Assert.DoesNotContain("environment", sent.Body);
        Assert.DoesNotContain("campaignRef", sent.Body);
        Assert.DoesNotContain("purpose", sent.Body);
    }

    [Theory]
    [InlineData(SpendAccountClass.Subscription)]
    [InlineData(SpendAccountClass.Trial)]
    [InlineData(SpendAccountClass.SetupGrant)]
    public async Task PlatformAccountGateway_RefusesRelationshipScopedClasses(
        SpendAccountClass accountClass
    )
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedOfferingUsageGateway(
            identity,
            new Uri("https://billing.test")
        );

        await Assert.ThrowsAsync<ArgumentOutOfRangeException>(() =>
            gateway.ReserveAccountAsync(
                new PlatformAccountReserveRequest(
                    Guid.NewGuid(),
                    Guid.NewGuid(),
                    accountClass,
                    null,
                    null,
                    null,
                    "llm_cloud",
                    10,
                    null,
                    Guid.NewGuid(),
                    Guid.NewGuid(),
                    Guid.NewGuid()
                ),
                CancellationToken.None
            )
        );
    }

    [Theory]
    [InlineData(
        HttpStatusCode.Conflict,
        """{"detail":{"code":"ACQUISITION_BUDGET_EXHAUSTED","level":"CAMPAIGN"}}""",
        "ACQUISITION_BUDGET_EXHAUSTED",
        "CAMPAIGN"
    )]
    [InlineData(
        HttpStatusCode.Conflict,
        """{"detail":"WALLET_ACCOUNT_CLOSED"}""",
        "WALLET_ACCOUNT_CLOSED",
        null
    )]
    [InlineData(HttpStatusCode.UnprocessableEntity, "not json", "WALLET_REFUSED", null)]
    public async Task PlatformAccountGateway_SurfacesTheOwnerRefusalCodeAndLevel(
        HttpStatusCode status,
        string body,
        string code,
        string? level
    )
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedOfferingUsageGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(gateway, "_client", Handler((_, _) => Json(status, body)));

        var refused = await Assert.ThrowsAsync<PlatformAccountRefusedException>(() =>
            gateway.OpenSetupGrantAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                "DMA",
                "1.0.0",
                Guid.NewGuid(),
                CancellationToken.None
            )
        );

        Assert.Equal(code, refused.Code);
        Assert.Equal(level, refused.Level);
    }

    [Fact]
    public async Task PlatformAccountGateway_OpensTheSetupGrantOnTheRelationshipRoute()
    {
        var relationship = Guid.NewGuid();
        var paths = new List<string>();
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedOfferingUsageGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(
            gateway,
            "_client",
            Handler(
                (request, _) =>
                {
                    paths.Add(request.RequestUri!.AbsolutePath);
                    return Json(
                        HttpStatusCode.OK,
                        $$"""
                        {
                          "schemaVersion": "1.0",
                          "status": "GRANTED",
                          "accountId": "{{Guid.NewGuid():D}}",
                          "lotId": "{{Guid.NewGuid():D}}",
                          "creditedPaise": 5000,
                          "created": true
                        }
                        """
                    );
                }
            )
        );

        var receipt = await gateway.OpenSetupGrantAsync(
            Guid.NewGuid(),
            Guid.NewGuid(),
            relationship,
            "DMA",
            "1.0.0",
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.Equal([$"/internal/v1/relationships/{relationship:D}/setup-grant"], paths);
        Assert.Equal("GRANTED", receipt.Status);
        Assert.Equal(5000, receipt.CreditedPaise);
        Assert.True(receipt.Created);
    }

    [Theory]
    [InlineData(HttpStatusCode.BadGateway)]
    [InlineData(HttpStatusCode.ServiceUnavailable)]
    public async Task PlatformAccountGateway_FailsClosedWhenTheOwnerIsUnavailable(
        HttpStatusCode status
    )
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedOfferingUsageGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(gateway, "_client", Handler((_, _) => Json(status, "{}")));

        await Assert.ThrowsAsync<OfferingUsageOwnerUnavailableException>(() =>
            gateway.OpenSetupGrantAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                "DMA",
                "1.0.0",
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task PlatformAccountGateway_DrawsSettlesAndReleasesWithSignedRoutes()
    {
        var reservation = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var captured = new List<(string Path, string Body)>();
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedOfferingUsageGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(
            gateway,
            "_client",
            Handler(
                (request, _) =>
                {
                    Assert.StartsWith("Bearer ", request.Headers.Authorization?.ToString());
                    var body = request.Content!.ReadAsStringAsync().GetAwaiter().GetResult();
                    captured.Add((request.RequestUri!.AbsolutePath, body));
                    return request.RequestUri.AbsolutePath.EndsWith("/setup-grant/reserve")
                        ? Json(
                            HttpStatusCode.OK,
                            $$"""
                            {"schemaVersion":"1.0","status":"SETUP_GRANT_EXHAUSTED","accountId":"{{Guid.NewGuid():D}}","reservedPaise":0,"replayed":false}
                            """
                        )
                        : Json(
                            HttpStatusCode.OK,
                            $$"""
                            {"schemaVersion":"1.0","reservationId":"{{reservation:D}}","accountId":"{{Guid.NewGuid():D}}","state":"SETTLED","reservedPaise":200,"actualPaise":150,"overrunPaise":0,"fenced":false,"replayed":false}
                            """
                        );
                }
            )
        );

        var draw = await gateway.ReserveSetupGrantAsync(
            Guid.NewGuid(),
            Guid.NewGuid(),
            relationship,
            "DMA",
            "1.0.0",
            "llm_cloud",
            200,
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );
        var settled = await gateway.SettleAccountAsync(
            Guid.NewGuid(),
            Guid.NewGuid(),
            reservation,
            150,
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );
        var released = await gateway.ReleaseAccountAsync(
            Guid.NewGuid(),
            Guid.NewGuid(),
            reservation,
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.True(draw.IsExhausted);
        Assert.Null(draw.ReservationId);
        Assert.Equal(150, settled.ActualPaise);
        Assert.Equal(reservation, released.ReservationId);
        Assert.Equal(
            [
                $"/internal/v1/relationships/{relationship:D}/setup-grant/reserve",
                "/internal/v1/wallet/reservations/settle",
                "/internal/v1/wallet/reservations/release",
            ],
            captured.Select(item => item.Path).ToArray()
        );
        Assert.Contains("\"actualPaise\":150", captured[1].Body);
        Assert.Contains($"\"reservationId\":\"{reservation:D}\"", captured[2].Body);
    }

    [Fact]
    public async Task PlatformAccountGateway_SettleFailsClosedWhenTheOwnerIsUnavailable()
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedOfferingUsageGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(gateway, "_client", Handler((_, _) => Json(HttpStatusCode.BadGateway, "{}")));

        await Assert.ThrowsAsync<OfferingUsageOwnerUnavailableException>(() =>
            gateway.SettleAccountAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                10,
                Guid.NewGuid(),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task UnconfiguredPlatformAccountGateway_DeniesEveryOperation()
    {
        var gateway = new UnconfiguredOfferingUsageGateway();
        await Assert.ThrowsAsync<OfferingUsageOwnerUnavailableException>(() =>
            gateway.ReserveSetupGrantAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                "DMA",
                "1.0.0",
                "llm_cloud",
                10,
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<OfferingUsageOwnerUnavailableException>(() =>
            gateway.SettleAccountAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                10,
                Guid.NewGuid(),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<OfferingUsageOwnerUnavailableException>(() =>
            gateway.ReleaseAccountAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<OfferingUsageOwnerUnavailableException>(() =>
            gateway.ReserveAccountAsync(
                new PlatformAccountReserveRequest(
                    Guid.NewGuid(),
                    Guid.NewGuid(),
                    SpendAccountClass.Simulation,
                    "ci",
                    null,
                    null,
                    "llm_cloud",
                    10,
                    null,
                    Guid.NewGuid(),
                    Guid.NewGuid(),
                    Guid.NewGuid()
                ),
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<OfferingUsageOwnerUnavailableException>(() =>
            gateway.OpenSetupGrantAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                "DMA",
                "1.0.0",
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task UnconfiguredOfferingUsageOwner_DeniesEveryOperation()
    {
        var gateway = new UnconfiguredOfferingUsageGateway();
        var value = OfferingIdentity();
        await Assert.ThrowsAsync<OfferingUsageOwnerUnavailableException>(() =>
            gateway.ReserveAsync(value, 1, CancellationToken.None)
        );
        await Assert.ThrowsAsync<OfferingUsageOwnerUnavailableException>(() =>
            gateway.SettleAsync(value, Guid.NewGuid(), 1, Guid.NewGuid(), CancellationToken.None)
        );
        await Assert.ThrowsAsync<OfferingUsageOwnerUnavailableException>(() =>
            gateway.ReleaseAsync(value, Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None)
        );
        await Assert.ThrowsAsync<OfferingUsageOwnerUnavailableException>(() =>
            gateway.ReconcileAsync(value, null, CancellationToken.None)
        );
    }

    private static OfferingUsageIdentity OfferingIdentity() =>
        new(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            "DMA",
            "1.0.0",
            "content",
            "1.0.0",
            Guid.NewGuid(),
            Guid.NewGuid(),
            "inference",
            Guid.NewGuid(),
            new string('a', 64),
            Guid.NewGuid()
        );

    private static OfferabilityEvaluationRequest OfferabilityRequest() =>
        new(
            Guid.NewGuid(),
            Guid.NewGuid(),
            3,
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            "dma-starter-v1",
            "DMA",
            "STARTER",
            7_000
        );

    private static RelationshipOwnerContext OwnerContext() =>
        new(
            "actor",
            "EMPLOYER",
            Guid.NewGuid(),
            Guid.NewGuid(),
            3,
            Guid.NewGuid().ToString("D"),
            Guid.NewGuid()
        );

    private static HttpResponseMessage Json(HttpStatusCode status, string body) =>
        new(status) { Content = new StringContent(body, Encoding.UTF8, "application/json") };

    private static StubHandler Handler(
        Func<HttpRequestMessage, CancellationToken, HttpResponseMessage> send
    ) => new(send);

    private static void ReplaceClient(object target, string fieldName, StubHandler handler)
    {
        var field =
            target.GetType().GetField(fieldName, BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException($"Missing field {fieldName}");
        var original = Assert.IsType<HttpClient>(field.GetValue(target));
        field.SetValue(
            target,
            new HttpClient(handler) { BaseAddress = new Uri("https://owner.test") }
        );
        original.Dispose();
    }

    private sealed class StubClientFactory(StubHandler handler) : IHttpClientFactory
    {
        public HttpClient CreateClient(string name) =>
            new(handler, disposeHandler: false) { BaseAddress = new Uri("https://wbe.test") };
    }

    private sealed class StubHandler(
        Func<HttpRequestMessage, CancellationToken, HttpResponseMessage> send
    ) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) => Task.FromResult(send(request, cancellationToken));
    }
}
