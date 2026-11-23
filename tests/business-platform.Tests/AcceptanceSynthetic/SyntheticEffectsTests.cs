// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §5 and adr/ADR-055-synthetic-acceptance-tenants-and-evidence.md decision 4
// Constitutional basis: C-059 (Implementation Traceability)

using System.Diagnostics;
using System.Diagnostics.Metrics;
using System.Security.Claims;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc.Controllers;
using Microsoft.AspNetCore.Mvc.Routing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Middleware;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.AcceptanceSynthetic;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.AcceptanceSynthetic;

/// <summary>WC159-R004 (metrics label), R005 (delivery suppression) and R006 (the marker skips no control).</summary>
public sealed class SyntheticEffectsTests
{
    private const string Run = "run-2026-11-23-001";
    private const string Issuer = "https://identity.invalid/realms/waooaw";
    private static readonly Guid SyntheticTenant = Guid.Parse("a1a1a1a1-0000-4000-8000-000000000001");
    private static readonly Guid RealTenant = Guid.Parse("b2b2b2b2-0000-4000-8000-000000000002");

    private static WhatsAppProviderDispatchRequest Request(Guid tenant) =>
        new(Guid.NewGuid(), "demo", tenant, null, null, 1, "payload-ref", new string('a', 64), 3);

    private static SyntheticDeliveryGate Gate(FakeSyntheticAcceptanceRegistry registry, bool enabled = true) =>
        new(registry, Options.Create(new AcceptanceSyntheticOptions { Enabled = enabled }), NullLogger<SyntheticDeliveryGate>.Instance);

    private static FakeSyntheticAcceptanceRegistry Registry()
    {
        var registry = new FakeSyntheticAcceptanceRegistry();
        registry.TenantRuns[SyntheticTenant] = Run;
        registry.SandboxRecipients.Add((Run, SyntheticRecipient.Digest("+15550001234")));
        registry.SandboxRecipients.Add(("run-2026-11-23-002", SyntheticRecipient.Digest("+15550002222")));
        return registry;
    }

    [Fact]
    public async Task WC159_R005_ASyntheticTenantReachesOnlyItsRegisteredSandboxRecipient_AndEverythingElseIsSuppressedCountedAndRecorded()
    {
        var registry = Registry();
        var gate = Gate(registry);
        var counted = 0L;
        using var listener = new MeterListener();
        listener.InstrumentPublished = (instrument, meter) =>
        {
            if (instrument.Name == SyntheticAcceptanceTelemetry.SuppressedMetric)
                meter.EnableMeasurementEvents(instrument);
        };
        listener.SetMeasurementEventCallback<long>((_, value, _, _) => Interlocked.Add(ref counted, value));
        listener.Start();

        var sandbox = Request(SyntheticTenant);
        Assert.False(await gate.SuppressAsync(sandbox, "+1 555 000 1234", default));
        Assert.Empty(registry.Suppressions);

        var stranger = Request(SyntheticTenant);
        Assert.True(await gate.SuppressAsync(stranger, "+919876543210", default));
        // A sandbox recipient registered for another run is still a stranger to this run.
        Assert.True(await gate.SuppressAsync(Request(SyntheticTenant), "+15550002222", default));

        Assert.Equal(2, registry.Suppressions.Count);
        var recorded = registry.Suppressions[0];
        Assert.Equal((SyntheticTenant, Run, stranger.OutboxId, 3), (recorded.TenantId, recorded.RunId, recorded.OutboxId, recorded.Attempt));
        Assert.Equal(SyntheticRecipient.Digest("+919876543210"), recorded.Digest);
        Assert.DoesNotContain("919876543210", recorded.Digest);
        Assert.Equal(2, Interlocked.Read(ref counted));
    }

    [Fact]
    public async Task WC159_R005_ARealCustomerIsNeverSuppressed_AndTheGateDoesNothingWhenTheSettingIsOff()
    {
        var registry = Registry();
        Assert.False(await Gate(registry).SuppressAsync(Request(RealTenant), "+919876543210", default));
        Assert.False(await Gate(registry, enabled: false).SuppressAsync(Request(SyntheticTenant), "+919876543210", default));
        Assert.Empty(registry.Suppressions);
    }

    private static DefaultHttpContext Context(string? subject, string? issuer, IServiceProvider services, ClaimsPrincipal? user = null)
    {
        var context = new DefaultHttpContext { RequestServices = services };
        context.User =
            user
            ?? new ClaimsPrincipal(new ClaimsIdentity(
                new[] { issuer is null ? null : new Claim("iss", issuer), subject is null ? null : new Claim("sub", subject) }.OfType<Claim>(),
                "Test"));
        context.SetEndpoint(new Endpoint(
            _ => Task.CompletedTask,
            new EndpointMetadataCollection(new ControllerActionDescriptor
            {
                AttributeRouteInfo = new AttributeRouteInfo { Template = "api/v1/identity/registrations/{registrationId:guid}/complete" },
            }),
            "complete"));
        return context;
    }

    private static async Task<IReadOnlyDictionary<string, object?>> JourneyTagsAsync(HttpContext context)
    {
        using var listener = new ActivityListener
        {
            ShouldListenTo = _ => true,
            Sample = (ref ActivityCreationOptions<ActivityContext> _) => ActivitySamplingResult.AllData,
        };
        ActivitySource.AddActivityListener(listener);
        using var source = new ActivitySource("wc159-test");
        using var activity = source.StartActivity("request");
        await new JourneyTelemetryMiddleware(_ => Task.CompletedTask).InvokeAsync(context);
        return activity!.TagObjects.ToDictionary(pair => pair.Key, pair => pair.Value);
    }

    private static IServiceProvider Services(FakeSyntheticAcceptanceRegistry registry, bool enabled = true) =>
        new ServiceCollection()
            .AddSingleton<ISyntheticAcceptanceRegistry>(registry)
            .AddSingleton(Options.Create(new AcceptanceSyntheticOptions { Enabled = enabled }))
            .BuildServiceProvider();

    [Fact]
    public async Task WC159_R004_JourneyTelemetryOfARegisteredSubjectIsLabelledSyntheticSoBusinessMetricsCanExcludeIt()
    {
        var registry = new FakeSyntheticAcceptanceRegistry();
        registry.Actors.Add((Issuer, "subject-synthetic-1"));
        var services = Services(registry);

        Assert.Equal(true, (await JourneyTagsAsync(Context("subject-synthetic-1", Issuer, services)))[JourneyTelemetryMiddleware.SyntheticTag]);
        Assert.DoesNotContain(JourneyTelemetryMiddleware.SyntheticTag, (await JourneyTagsAsync(Context("subject-real-0001", Issuer, services))).Keys);
        // The mapped NameIdentifier form of sub is honoured the same way as the raw one.
        var mapped = new ClaimsPrincipal(new ClaimsIdentity([new Claim("iss", Issuer), new Claim(ClaimTypes.NameIdentifier, "subject-synthetic-1")], "Test"));
        Assert.Equal(true, (await JourneyTagsAsync(Context(null, null, services, mapped)))[JourneyTelemetryMiddleware.SyntheticTag]);
    }

    [Fact]
    public async Task WC159_R004_TelemetryIsUnchangedWhenTheSettingIsOffOrTheRegistryCannotBeRead()
    {
        var registry = new FakeSyntheticAcceptanceRegistry();
        registry.Actors.Add((Issuer, "subject-synthetic-1"));
        Assert.DoesNotContain(JourneyTelemetryMiddleware.SyntheticTag, (await JourneyTagsAsync(Context("subject-synthetic-1", Issuer, Services(registry, enabled: false)))).Keys);
        Assert.DoesNotContain(JourneyTelemetryMiddleware.SyntheticTag, (await JourneyTagsAsync(Context("subject-synthetic-1", null, Services(registry)))).Keys);
        Assert.DoesNotContain(JourneyTelemetryMiddleware.SyntheticTag, (await JourneyTagsAsync(Context(null, Issuer, Services(registry)))).Keys);
        // No service container at all (as in a bare host) and a registry failure never fail the request.
        var bare = Context("subject-synthetic-1", Issuer, Services(registry));
        bare.RequestServices = null!;
        Assert.DoesNotContain(JourneyTelemetryMiddleware.SyntheticTag, (await JourneyTagsAsync(bare)).Keys);
        registry.Fail = true;
        Assert.DoesNotContain(JourneyTelemetryMiddleware.SyntheticTag, (await JourneyTagsAsync(Context("subject-synthetic-1", Issuer, Services(registry)))).Keys);
    }

    [Fact]
    public void WC159_R006_TheMarkerIsReadOnlyByTheThreeEffectSites_AndNeverFromAClaimOrABody()
    {
        var root = RepositoryPaths.Root();
        var source = Directory.EnumerateFiles(Path.Combine(root, "src/business-platform"), "*.cs", SearchOption.AllDirectories)
            .Where(path => !path.Contains("/obj/") && !path.Contains("/Clients/Generated/"))
            .ToDictionary(path => Path.GetRelativePath(Path.Combine(root, "src/business-platform"), path).Replace('\\', '/'), File.ReadAllText);

        // The only code that reads the marker (as opposed to the provisioner route that writes it).
        var readers = new[] { "IsSyntheticActorAsync", "FindTenantRunAsync", "ISyntheticDeliveryGate", "SyntheticTenantInheritance" };
        var allowed = new HashSet<string>
        {
            "Services/AcceptanceSynthetic/SyntheticAcceptanceRegistry.cs",
            "Services/AcceptanceSynthetic/SyntheticDeliveryGate.cs",
            "Services/AcceptanceSynthetic/SyntheticTenantInheritance.cs",
            "Services/CustomerWorkspaceProvisioningService.cs", // (a) tenant creation inherits the label
            "Services/CustomerIdentityJourneyService.cs",
            "Services/WhatsAppCloudProviderAdapter.cs", // (b) delivery suppression
            "Middleware/JourneyTelemetryMiddleware.cs", // (a) metrics label
            "Program.cs",
        };
        var offenders = source
            .Where(file => readers.Any(reader => file.Value.Contains(reader, StringComparison.Ordinal)) && !allowed.Contains(file.Key))
            .Select(file => file.Key)
            .ToArray();
        Assert.Empty(offenders);

        // No authentication, authorization, entitlement, billing or evidence code mentions the marker at all.
        foreach (var guarded in new[]
        {
            "Services/EmploymentRelationshipService.cs", "Services/RelationshipPaymentService.cs", "Services/RelationshipTrialService.cs",
            "Services/RelationshipEvidenceService.cs", "Services/OfferabilityService.cs", "Services/EmploymentContractAcceptanceService.cs",
            "Services/Workbench/WorkbenchCommercialReader.cs", "Services/VerifiedIdentityProofAdapter.cs", "Infrastructure/CustomerMembershipMiddleware.cs",
            "Infrastructure/TenantIsolationMiddleware.cs", "Services/AuthenticatedActivationBillingGateway.cs",
        })
            Assert.DoesNotContain("synthetic", source[guarded], StringComparison.OrdinalIgnoreCase);

        // A claim is never the marker: nothing outside the provisioner authority reads a claim for it.
        Assert.DoesNotContain(source, file =>
            file.Key != "Services/AcceptanceSynthetic/AcceptanceProvisionerAuthority.cs"
            && (file.Value.Contains("FindFirst(\"synthetic", StringComparison.OrdinalIgnoreCase)
                || file.Value.Contains("HasClaim(\"synthetic", StringComparison.OrdinalIgnoreCase)
                || file.Value.Contains("\"waooaw_synthetic\"", StringComparison.OrdinalIgnoreCase)));
    }

    [Fact]
    public void WC159_R001_TheShippedSettingsAreOffAndTheWorkloadModuleRefusesProduction()
    {
        using var settings = System.Text.Json.JsonDocument.Parse(File.ReadAllText(RepositoryPaths.Resolve("src/business-platform/appsettings.json")));
        Assert.False(settings.RootElement.GetProperty("AcceptanceSyntheticTenants").GetProperty("Enabled").GetBoolean());

        var module = File.ReadAllText(RepositoryPaths.Resolve("infrastructure/terraform/phase2/modules/workload/feature-settings.tf"));
        Assert.Contains("acceptance_synthetic_tenants_enabled = optional(bool, false)", module);
        Assert.Contains("AcceptanceSyntheticTenants__Enabled", module);
        Assert.Contains("var.environment != \"prod\" || !var.feature_settings.acceptance_synthetic_tenants_enabled", module);
        foreach (var environment in new[] { "uat", "prod" })
            Assert.DoesNotContain(
                "acceptance_synthetic_tenants_enabled",
                File.ReadAllText(RepositoryPaths.Resolve($"infrastructure/platform-settings/{environment}.json"))
            );
        Assert.DoesNotContain(
            "acceptance_synthetic_tenants_enabled",
            File.ReadAllText(RepositoryPaths.Resolve("infrastructure/platform-settings/demo.json"))
        );
    }
}
