// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-03
// constitutional_basis: C-023, C-059, C-063, C-088, C-089
using System.Security.Claims;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class PricingAdminControllerCoverageTests
{
    private const string DraftId = "7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11";
    private static readonly string Draft = PricingAdminFixtures.Draft();

    private static PricingAdminController As(
        PricingAdminController controller,
        params Claim[] claims
    )
    {
        controller.ControllerContext.HttpContext.User = new ClaimsPrincipal(
            new ClaimsIdentity(claims, "Test")
        );
        return controller;
    }

    private static Claim[] StepUp(
        string acr = "2",
        string amr = "mfa",
        TimeSpan? age = null,
        string? authTime = null
    ) =>
        [
            new("amr", amr),
            new("acr", acr),
            new(
                "auth_time",
                authTime
                    ?? (DateTimeOffset.UtcNow - (age ?? TimeSpan.FromMinutes(1)))
                        .ToUnixTimeSeconds()
                        .ToString()
            ),
        ];

    private static async Task<string?> CodeAsync(Task<IActionResult> result)
    {
        var content = Assert.IsType<ContentResult>(await result);
        return content.StatusCode == 200
            ? null
            : PricingAdminFixtures.Content(content).GetProperty("code").GetString();
    }

    [Fact]
    public async Task A_body_over_the_size_limit_is_refused_before_the_owner_is_called()
    {
        var gateway = new RecordingPricingGateway();
        var controller = PricingAdminFixtures.Controller(
            PricingAdminFixtures.Service(gateway),
            ["pricing_admin"],
            false,
            "{\"schemaVersion\":\"1.0\",\"pad\":\"" + new string('a', 270_000) + "\"}"
        );

        var result = Assert.IsType<ContentResult>(
            await controller.CreatePricingDraftAsync(CancellationToken.None)
        );

        Assert.Equal(400, result.StatusCode);
        Assert.Equal(
            "The request body is too large.",
            PricingAdminFixtures.Content(result).GetProperty("detail").GetString()
        );
        Assert.Empty(gateway.Requests);
    }

    [Fact]
    public async Task A_body_just_under_the_limit_is_accepted()
    {
        var gateway = new RecordingPricingGateway();
        var controller = PricingAdminFixtures.Controller(
            PricingAdminFixtures.Service(gateway),
            ["pricing_admin"],
            false,
            "{\"schemaVersion\":\"1.0\",\"pad\":\"" + new string('a', 262_000) + "\"}"
        );

        var result = Assert.IsType<ContentResult>(
            await controller.CreatePricingDraftAsync(CancellationToken.None)
        );

        Assert.Equal(200, result.StatusCode);
        Assert.True(Assert.Single(gateway.Requests).Body.Length > 262_000);
    }

    [Fact]
    public async Task An_empty_write_body_is_a_published_request_problem()
    {
        var gateway = new RecordingPricingGateway();
        var controller = PricingAdminFixtures.Controller(
            PricingAdminFixtures.Service(gateway),
            ["pricing_admin"],
            false,
            ""
        );

        var code = await CodeAsync(controller.CreatePricingDraftAsync(CancellationToken.None));

        Assert.Equal("PRICING_REQUEST_INVALID", code);
        Assert.Empty(gateway.Requests);
    }

    [Fact]
    public async Task A_read_ignores_any_body_and_a_response_without_an_etag_sets_no_header()
    {
        var gateway = new RecordingPricingGateway
        {
            Respond = _ => new PricingGatewayResponse(200, null, null),
        };
        var controller = PricingAdminFixtures.Controller(
            PricingAdminFixtures.Service(gateway),
            ["pricing_admin"],
            false,
            "not json"
        );

        var result = Assert.IsType<ContentResult>(
            await controller.GetPricingDraftAsync(DraftId, CancellationToken.None)
        );

        Assert.Equal("{}", result.Content);
        Assert.False(controller.Response.Headers.ContainsKey("ETag"));
        Assert.Empty(Assert.Single(gateway.Requests).Body);
    }

    [Fact]
    public async Task Repeated_query_values_are_all_forwarded_in_order()
    {
        var gateway = new RecordingPricingGateway();
        var controller = PricingAdminFixtures.Controller(
            PricingAdminFixtures.Service(gateway),
            ["pricing_admin"],
            false,
            query: "?kind=RATE&kind=BUDGET&limit=5"
        );

        await controller.ListPricingDraftsAsync(CancellationToken.None);

        Assert.Equal("kind=RATE&kind=BUDGET&limit=5", Assert.Single(gateway.Requests).Query);
    }

    [Theory]
    [InlineData(ClaimTypes.NameIdentifier)]
    [InlineData("sub")]
    public async Task The_caller_is_identified_by_any_standard_subject_claim(string claimType)
    {
        var gateway = new RecordingPricingGateway();
        var controller = As(
            PricingAdminFixtures.Controller(PricingAdminFixtures.Service(gateway), [], false),
            new Claim(claimType, "subject-7"),
            new Claim(ClaimTypes.Role, "PRICING_ADMIN")
        );

        await controller.ListPricingDraftsAsync(CancellationToken.None);

        var request = Assert.Single(gateway.Requests);
        Assert.Equal(("subject-7", "PRICING_ADMIN"), (request.ActorSubject, request.EffectiveRole));
    }

    [Fact]
    public async Task A_signed_in_caller_without_any_subject_is_unauthorized()
    {
        var controller = As(
            PricingAdminFixtures.Controller(
                PricingAdminFixtures.Service(new RecordingPricingGateway()),
                [],
                false
            ),
            new Claim("role", "founder")
        );

        var result = Assert.IsType<ContentResult>(
            await controller.ListPricingDraftsAsync(CancellationToken.None)
        );

        Assert.Equal(401, result.StatusCode);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("not-a-guid")]
    [InlineData("00000000-0000-0000-0000-000000000000")]
    public async Task A_missing_or_unreadable_tenant_is_signed_as_the_nil_tenant(string? tenant)
    {
        var gateway = new RecordingPricingGateway();
        var controller = PricingAdminFixtures.Controller(
            PricingAdminFixtures.Service(gateway),
            ["pricing_admin"],
            false
        );
        var items = controller.ControllerContext.HttpContext.Items;
        if (tenant is null)
            items.Remove(TenantIsolationMiddleware.TenantIdItemKey);
        else
            items[TenantIsolationMiddleware.TenantIdItemKey] = tenant;

        await controller.ListPricingDraftsAsync(CancellationToken.None);

        Assert.Equal(Guid.Empty, Assert.Single(gateway.Requests).TenantId);
    }

    [Fact]
    public async Task A_tenant_stored_as_a_guid_object_instead_of_text_is_not_trusted()
    {
        var gateway = new RecordingPricingGateway();
        var controller = PricingAdminFixtures.Controller(
            PricingAdminFixtures.Service(gateway),
            ["pricing_admin"],
            false
        );
        controller.ControllerContext.HttpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] =
            Guid.NewGuid();

        await controller.ListPricingDraftsAsync(CancellationToken.None);

        Assert.Equal(Guid.Empty, Assert.Single(gateway.Requests).TenantId);
    }

    [Theory]
    [InlineData("2", "mfa", 60, null, true)]
    [InlineData("3", "pwd otp", 60, null, true)]
    [InlineData("urn:waooaw:aal2", "webauthn", 60, null, true)]
    [InlineData("urn:waooaw:aal3", "pwd webauthn", 60, null, true)]
    [InlineData("1", "mfa", 60, null, false)]
    [InlineData("2", "pwd", 60, null, false)]
    [InlineData("2", "", 60, null, false)]
    [InlineData("2", "mfa", 301, null, false)]
    [InlineData("2", "mfa", -10, null, true)]
    [InlineData("2", "mfa", -120, null, false)]
    [InlineData("2", "mfa", 0, "yesterday", false)]
    public async Task A_step_up_needs_a_recent_authentication_at_a_high_assurance_level_with_a_second_factor(
        string acr,
        string amr,
        int ageSeconds,
        string? authTime,
        bool accepted
    )
    {
        var controller = As(
            PricingAdminFixtures.Controller(
                PricingAdminFixtures.Service(new RecordingPricingGateway()),
                [],
                false,
                Draft
            ),
            [
                new Claim("participant_id", "founder-1"),
                new Claim("role", "founder"),
                .. StepUp(acr, amr, TimeSpan.FromSeconds(ageSeconds), authTime),
            ]
        );

        var code = await CodeAsync(
            controller.ActivatePackageForSaleAsync(DraftId, CancellationToken.None)
        );

        Assert.Equal(accepted ? null : "PRICING_STEP_UP_REQUIRED", code);
    }

    [Fact]
    public async Task A_step_up_may_be_spread_over_several_authentication_method_claims()
    {
        var controller = As(
            PricingAdminFixtures.Controller(
                PricingAdminFixtures.Service(new RecordingPricingGateway()),
                [],
                false,
                Draft
            ),
            new Claim("participant_id", "founder-1"),
            new Claim("participant_role", "FOUNDER"),
            new Claim("amr", "pwd"),
            new Claim("amr", "otp"),
            new Claim("acr", "2"),
            new Claim("auth_time", DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString())
        );

        var code = await CodeAsync(
            controller.ActivatePackageForSaleAsync(DraftId, CancellationToken.None)
        );

        Assert.Null(code);
    }

    [Fact]
    public async Task Header_values_must_be_single_non_empty_uuids()
    {
        var gateway = new RecordingPricingGateway();
        var service = PricingAdminFixtures.Service(gateway);

        foreach (
            var (header, value) in new[]
            {
                ("Idempotency-Key", Guid.Empty.ToString()),
                ("X-Correlation-ID", "not-a-guid"),
            }
        )
        {
            var controller = PricingAdminFixtures.Controller(
                service,
                ["pricing_admin"],
                false,
                Draft
            );
            controller.ControllerContext.HttpContext.Request.Headers[header] = value;
            Assert.Equal(
                "PRICING_REQUEST_INVALID",
                await CodeAsync(controller.CreatePricingDraftAsync(CancellationToken.None))
            );
        }

        var duplicated = PricingAdminFixtures.Controller(service, ["pricing_admin"], false, Draft);
        duplicated.ControllerContext.HttpContext.Request.Headers["Idempotency-Key"] =
            new Microsoft.Extensions.Primitives.StringValues([
                Guid.NewGuid().ToString(),
                Guid.NewGuid().ToString(),
            ]);
        Assert.Equal(
            "PRICING_REQUEST_INVALID",
            await CodeAsync(duplicated.CreatePricingDraftAsync(CancellationToken.None))
        );
        Assert.Empty(gateway.Requests);
    }

    [Fact]
    public async Task A_problem_carries_the_callers_correlation_id()
    {
        var correlation = Guid.NewGuid();
        var controller = PricingAdminFixtures.Controller(
            PricingAdminFixtures.Service(
                new RecordingPricingGateway
                {
                    Respond = _ => new PricingGatewayResponse(
                        404,
                        System
                            .Text.Json.JsonDocument.Parse("""{"code":"PRICING_NOT_FOUND"}""")
                            .RootElement.Clone(),
                        null
                    ),
                }
            ),
            ["pricing_admin"],
            false,
            correlation: correlation
        );

        var result = Assert.IsType<ContentResult>(
            await controller.GetPricingDraftAsync(DraftId, CancellationToken.None)
        );

        Assert.Equal(404, result.StatusCode);
        Assert.Equal(
            correlation.ToString("D"),
            PricingAdminFixtures.Content(result).GetProperty("correlationId").GetString()
        );
    }
}
