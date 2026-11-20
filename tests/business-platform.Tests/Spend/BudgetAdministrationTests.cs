// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-04
// Constitutional basis: C-023, C-059, C-063, C-088
using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Spend;

public sealed class BudgetAdministrationTests
{
    private const string DraftId = "7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11";
    private static readonly Guid EvidenceId = Guid.NewGuid();

    private static string Version(
        string state,
        string scope = "ENVIRONMENT_CEILING",
        long maximum = 60_000
    ) =>
        $$$"""
            {"versionId":"{{{DraftId}}}","kind":"BUDGET","state":"{{{state}}}","evidenceId":"{{{EvidenceId}}}",
             "body":{"scope":"{{{scope}}}","ref":"demo","maximumPaise":{{{maximum}}}}}
            """;

    private static RecordingPricingGateway Owner(string draft, string? authorized = null)
    {
        var gateway = new RecordingPricingGateway();
        gateway.Respond = request => new PricingGatewayResponse(
            200,
            JsonDocument
                .Parse(request.WbeOperation == "wbeGetPricingDraft" ? draft : authorized ?? draft)
                .RootElement.Clone(),
            null
        );
        return gateway;
    }

    private static Task<IActionResult> Authorize(
        PricingAdminService service,
        string effectiveFrom = ""
    ) =>
        PricingAdminFixtures
            .Controller(
                service,
                ["founder"],
                true,
                $$"""{"schemaVersion":"1.0","expectedVersion":"\"1:SUBMITTED:abc\""{{effectiveFrom}}}"""
            )
            .AuthorizePricingDraftAsync(DraftId, CancellationToken.None);

    private static Task<IActionResult> Lower(
        PricingAdminService service,
        long paise,
        string scope = "ENVIRONMENT_CEILING"
    ) =>
        PricingAdminFixtures
            .Controller(
                service,
                ["pricing_admin"],
                false,
                $$"""{"schemaVersion":"1.0","scope":"{{scope}}","ref":"demo","newMaximumPaise":{{paise}},"reason":"safety"}"""
            )
            .LowerPricingCeilingAsync(CancellationToken.None);

    [Fact]
    public async Task A_founder_raise_within_the_maximum_checks_first_then_applies_after_the_owner_authorizes()
    {
        var gateway = Owner(Version("SUBMITTED"), Version("EFFECTIVE"));
        var store = new FakeCeilingStore();

        var result = await Authorize(
            PricingAdminFixtures.Service(gateway, store, hardMaximumInr: 1000)
        );

        Assert.Equal(200, Assert.IsType<ContentResult>(result).StatusCode);
        Assert.Equal(
            new[] { "wbeGetPricingDraft", "wbeAuthorizePricingDraft" },
            gateway.Requests.Select(request => request.WbeOperation).ToArray()
        );
        Assert.Equal(new[] { true, false }, store.Calls.Select(call => call.DryRun).ToArray());
        Assert.All(
            store.Calls,
            call =>
                Assert.Equal(
                    ("demo", 60_000L, 100_000L),
                    (call.Environment, call.Maximum, call.Hard)
                )
        );
        Assert.Equal(EvidenceId, store.Calls[1].Evidence);
    }

    [Fact]
    public async Task A_raise_above_the_deploy_time_maximum_is_refused_before_the_owner_authorizes()
    {
        var gateway = Owner(Version("SUBMITTED", maximum: 90_000));
        var store = new FakeCeilingStore
        {
            Respond = _ => new(EnvironmentCeilingOutcomes.AboveHardMaximum, 50_000, null, 50_000),
        };

        var result = await Authorize(PricingAdminFixtures.Service(gateway, store));

        Assert.Equal(422, Assert.IsType<ContentResult>(result).StatusCode);
        Assert.Equal(
            "PRICING_CEILING_ABOVE_MAXIMUM",
            PricingAdminFixtures.Content(result).GetProperty("code").GetString()
        );
        Assert.DoesNotContain(
            gateway.Requests,
            request => request.WbeOperation == "wbeAuthorizePricingDraft"
        );
        Assert.Single(store.Calls);
    }

    [Fact]
    public async Task Lowering_below_open_exposure_is_refused_with_the_blocking_amount()
    {
        var gateway = Owner(Version("SUBMITTED", maximum: 10_000));
        var store = new FakeCeilingStore
        {
            Respond = _ => new(EnvironmentCeilingOutcomes.BelowExposure, 50_000, null, 22_000),
        };

        var result = await Authorize(PricingAdminFixtures.Service(gateway, store));

        var problem = PricingAdminFixtures.Content(result);
        Assert.Equal(409, Assert.IsType<ContentResult>(result).StatusCode);
        Assert.Equal(
            "PRICING_CEILING_BELOW_OPEN_RESERVATIONS",
            problem.GetProperty("code").GetString()
        );
        Assert.Equal(22_000, problem.GetProperty("blockingPaise").GetInt64());
        Assert.DoesNotContain(
            gateway.Requests,
            request => request.WbeOperation == "wbeAuthorizePricingDraft"
        );
    }

    [Fact]
    public async Task Re_authorizing_an_effective_ceiling_completes_the_authority_update_idempotently()
    {
        var gateway = Owner(Version("EFFECTIVE"));
        var store = new FakeCeilingStore();

        var result = await Authorize(
            PricingAdminFixtures.Service(gateway, store, hardMaximumInr: 1000)
        );

        Assert.Equal(200, Assert.IsType<ContentResult>(result).StatusCode);
        Assert.Equal("wbeGetPricingDraft", Assert.Single(gateway.Requests).WbeOperation);
        var call = Assert.Single(store.Calls);
        Assert.False(call.DryRun);
        Assert.Equal(EvidenceId, call.Evidence);
    }

    [Fact]
    public async Task A_scheduled_ceiling_is_refused_because_nothing_would_apply_it_later()
    {
        var gateway = Owner(Version("SUBMITTED"));
        var store = new FakeCeilingStore();
        var future = PricingAdminFixtures.Now.AddDays(1).ToString("O");

        var result = await Authorize(
            PricingAdminFixtures.Service(gateway, store),
            $$""","effectiveFrom":"{{future}}" """
        );

        Assert.Equal(400, Assert.IsType<ContentResult>(result).StatusCode);
        Assert.Empty(store.Calls);
        Assert.DoesNotContain(
            gateway.Requests,
            request => request.WbeOperation == "wbeAuthorizePricingDraft"
        );
    }

    [Theory]
    [InlineData("TENANT")]
    [InlineData("ACQUISITION_CAMPAIGN")]
    [InlineData("SIMULATION")]
    public async Task Other_budget_scopes_never_touch_the_environment_spend_authority(string scope)
    {
        var gateway = Owner(Version("SUBMITTED", scope), Version("EFFECTIVE", scope));
        var store = new FakeCeilingStore();

        var authorized = await Authorize(PricingAdminFixtures.Service(gateway, store));
        var lowered = await Lower(PricingAdminFixtures.Service(gateway, store), 100, scope);

        Assert.Equal(200, Assert.IsType<ContentResult>(authorized).StatusCode);
        Assert.Equal(200, Assert.IsType<ContentResult>(lowered).StatusCode);
        Assert.Empty(store.Calls);
    }

    [Fact]
    public async Task An_admin_lowers_the_environment_ceiling_authority_first_without_a_founder()
    {
        var gateway = new RecordingPricingGateway();
        var store = new FakeCeilingStore
        {
            Respond = dryRun =>
                new(
                    dryRun
                        ? EnvironmentCeilingOutcomes.DryRunOk
                        : EnvironmentCeilingOutcomes.Applied,
                    50_000,
                    20_000,
                    null
                ),
        };

        var result = await Lower(PricingAdminFixtures.Service(gateway, store), 20_000);

        Assert.Equal(200, Assert.IsType<ContentResult>(result).StatusCode);
        Assert.Equal(new[] { true, false }, store.Calls.Select(call => call.DryRun).ToArray());
        Assert.Equal("wbeLowerPricingCeiling", Assert.Single(gateway.Requests).WbeOperation);
        Assert.False(Assert.Single(gateway.Requests).StepUp);
    }

    [Fact]
    public async Task A_safety_operation_that_would_raise_the_ceiling_is_refused()
    {
        var gateway = new RecordingPricingGateway();
        var store = new FakeCeilingStore
        {
            Respond = _ => new(EnvironmentCeilingOutcomes.DryRunOk, 20_000, 40_000, null),
        };

        var result = await Lower(PricingAdminFixtures.Service(gateway, store), 40_000);

        Assert.Equal(422, Assert.IsType<ContentResult>(result).StatusCode);
        Assert.Single(store.Calls);
        Assert.Empty(gateway.Requests);
    }

    [Fact]
    public async Task A_failing_authority_store_is_a_503_and_nothing_is_authorized()
    {
        var gateway = Owner(Version("SUBMITTED"));
        var store = new FakeCeilingStore
        {
            Respond = _ => throw new InvalidOperationException("db down"),
        };

        var result = await Authorize(PricingAdminFixtures.Service(gateway, store));

        Assert.Equal(503, Assert.IsType<ContentResult>(result).StatusCode);
        Assert.DoesNotContain(
            gateway.Requests,
            request => request.WbeOperation == "wbeAuthorizePricingDraft"
        );
    }
}
