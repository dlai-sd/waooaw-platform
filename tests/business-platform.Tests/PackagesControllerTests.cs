// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-13
// constitutional_basis: C-005, C-023, C-026, C-059, C-063, ADR-051
using System.Net;
using System.Reflection;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class PackagesControllerTests
{
    private static readonly Guid Tenant = Guid.Parse("11111111-1111-4111-8111-111111111111");
    private static readonly Guid Account = Guid.Parse("22222222-2222-4222-8222-222222222222");

    private static readonly string[] CustomerSafePackageFields =
    [
        "packageId",
        "packageCode",
        "displayName",
        "agentType",
        "agentVersion",
        "billingPeriodDays",
        "priceInclGstPaise",
        "basePricePaise",
        "gstPaise",
        "gstRatePercent",
        "taxTreatment",
        "components",
    ];

    private sealed class FakeGateway(Func<OwnerPackagePage> answer) : IPackageCatalogGateway
    {
        public List<(
            Guid Tenant,
            string Actor,
            string Type,
            string Version,
            string? Cursor,
            int Limit,
            string Correlation
        )> Calls { get; } = [];

        public Task<OwnerPackagePage> ListAsync(
            Guid tenantId,
            string actorSubject,
            string agentType,
            string agentVersion,
            string? cursor,
            int limit,
            string correlationId,
            CancellationToken ct
        )
        {
            Calls.Add(
                (tenantId, actorSubject, agentType, agentVersion, cursor, limit, correlationId)
            );
            return Task.FromResult(answer());
        }
    }

    private static OwnerPackagePage Page(string? next = null) =>
        new(
            [
                new OwnerPackage(
                    Guid.Parse("33333333-3333-4333-8333-333333333333"),
                    "GROWTH",
                    "Growth",
                    "DIGITAL_MARKETING_LOCAL_SERVICE",
                    "1.0.0",
                    30,
                    236000,
                    200000,
                    36000,
                    18,
                    [
                        new OwnerPackageComponent("lead_batch", 30, "SPREAD", null),
                        new OwnerPackageComponent("PROACTIVE_MESSAGE", 30, "SPREAD", 40),
                    ]
                ),
            ],
            next
        );

    private static PackagesController Controller(
        IPackageCatalogGateway gateway,
        bool member = true,
        string? correlation = null
    )
    {
        var context = new DefaultHttpContext();
        if (member)
            context.Items[CustomerMembershipMiddleware.MembershipItem] =
                new CustomerWorkspaceMembership(
                    Account,
                    Tenant,
                    Guid.NewGuid(),
                    ["CUSTOMER_OWNER"]
                );
        if (correlation is not null)
            context.Request.Headers["X-Correlation-ID"] = correlation;
        return new PackagesController(
            new PackageCatalogService(gateway, new HumanizedComponentLabelSource()),
            NullLogger<PackagesController>.Instance
        )
        {
            ControllerContext = new ControllerContext { HttpContext = context },
        };
    }

    private static string Serialize(object? value) =>
        JsonSerializer.Serialize(value, new JsonSerializerOptions(JsonSerializerDefaults.Web));

    [Fact]
    public async Task ListsOnlyTheCustomerSafePackageShapeUnderTheMembershipTenant()
    {
        var gateway = new FakeGateway(() => Page("next-1"));
        var controller = Controller(gateway);

        var result = Assert.IsType<OkObjectResult>(
            await controller.ListAsync(
                "DIGITAL_MARKETING_LOCAL_SERVICE",
                "1.0.0",
                "c1",
                10,
                CancellationToken.None
            )
        );

        var call = Assert.Single(gateway.Calls);
        Assert.Equal(Tenant, call.Tenant);
        Assert.Equal(Account.ToString("D"), call.Actor);
        Assert.Equal("c1", call.Cursor);
        Assert.Equal(10, call.Limit);
        using var document = JsonDocument.Parse(Serialize(result.Value));
        var root = document.RootElement;
        Assert.Equal("1.0", root.GetProperty("schemaVersion").GetString());
        Assert.Equal("next-1", root.GetProperty("nextCursor").GetString());
        var item = root.GetProperty("items")[0];
        Assert.Equal(
            CustomerSafePackageFields.Order(StringComparer.Ordinal).ToArray(),
            item.EnumerateObject()
                .Select(property => property.Name)
                .Order(StringComparer.Ordinal)
                .ToArray()
        );
        Assert.Equal("GST_INCLUSIVE", item.GetProperty("taxTreatment").GetString());
        Assert.Equal(236000, item.GetProperty("priceInclGstPaise").GetInt64());
        var components = item.GetProperty("components");
        Assert.Equal("Lead batch", components[0].GetProperty("label").GetString());
        Assert.False(components[0].TryGetProperty("selectableMaximum", out _));
        Assert.Equal(40, components[1].GetProperty("selectableMaximum").GetInt32());
        Assert.Equal(
            new[] { "cadence", "componentId", "label", "quantity", "selectableMaximum" },
            components[1]
                .EnumerateObject()
                .Select(property => property.Name)
                .Order(StringComparer.Ordinal)
                .ToArray()
        );
    }

    [Fact]
    public async Task OmitsTheCursorOnTheLastPageAndUsesTheDefaultLimit()
    {
        var gateway = new FakeGateway(() => Page());
        var result = Assert.IsType<OkObjectResult>(
            await Controller(gateway)
                .ListAsync("AGENT", "1.0.0", null, null, CancellationToken.None)
        );

        Assert.Equal(PackageCatalogService.DefaultLimit, Assert.Single(gateway.Calls).Limit);
        using var document = JsonDocument.Parse(Serialize(result.Value));
        Assert.False(document.RootElement.TryGetProperty("nextCursor", out _));
    }

    [Fact]
    public async Task ARequestWithoutAMembershipIsRefusedBeforeTheOwnerIsAsked()
    {
        var gateway = new FakeGateway(() => Page());

        var result = await Controller(gateway, member: false)
            .ListAsync("AGENT", "1.0.0", null, null, CancellationToken.None);

        Assert.Equal(401, Assert.IsType<ObjectResult>(result).StatusCode);
        Assert.Empty(gateway.Calls);
    }

    [Theory]
    [InlineData("AGENT", "1.0.0", null, 0, null)]
    [InlineData("AGENT", "1.0.0", null, 101, null)]
    [InlineData("AGENT", "1.0.0", "", null, null)]
    [InlineData("bad type", "1.0.0", null, null, null)]
    [InlineData("AGENT", "1.0/../0", null, null, null)]
    [InlineData("AGENT", "1.0.0", null, null, "not-a-guid")]
    public async Task InvalidInputIsRefusedWithoutCallingTheOwner(
        string type,
        string version,
        string? cursor,
        int? limit,
        string? correlation
    )
    {
        var gateway = new FakeGateway(() => Page());

        var result = await Controller(gateway, correlation: correlation)
            .ListAsync(type, version, cursor, limit, CancellationToken.None);

        Assert.Equal(400, Assert.IsType<ObjectResult>(result).StatusCode);
        Assert.Empty(gateway.Calls);
    }

    [Fact]
    public async Task AnUnavailableOwnerIsAServiceUnavailableAndABadCursorIsABadRequest()
    {
        var down = Controller(new ThrowingGateway(new PackageCatalogUnavailableException("down")));
        var bad = Controller(new ThrowingGateway(new PackageCatalogCursorException()));

        Assert.Equal(
            503,
            Assert
                .IsType<ObjectResult>(
                    await down.ListAsync("AGENT", "1.0.0", null, null, CancellationToken.None)
                )
                .StatusCode
        );
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(
                    await bad.ListAsync("AGENT", "1.0.0", "x", null, CancellationToken.None)
                )
                .StatusCode
        );
    }

    [Fact]
    public void TheControllerRequiresAMembershipAndTheContractRoute()
    {
        var type = typeof(PackagesController);

        Assert.True(type.GetCustomAttribute<CustomerIdentityRouteAttribute>()!.RequiresMembership);
        Assert.NotNull(
            type.GetCustomAttribute<Microsoft.AspNetCore.Authorization.AuthorizeAttribute>()
        );
        Assert.Equal(
            "api/v1/marketplace/agents/{agentType}/versions/{agentVersion}/packages",
            type.GetCustomAttribute<RouteAttribute>()!.Template
        );
    }

    private sealed class ThrowingGateway(Exception error) : IPackageCatalogGateway
    {
        public Task<OwnerPackagePage> ListAsync(
            Guid tenantId,
            string actorSubject,
            string agentType,
            string agentVersion,
            string? cursor,
            int limit,
            string correlationId,
            CancellationToken ct
        ) => throw error;
    }
}

public sealed class PackageCatalogGatewayTests(OwnerGatewayIdentityFixture fixture)
    : IClassFixture<OwnerGatewayIdentityFixture>
{
    [Fact]
    public async Task ReadsTheOwnerCatalogueThroughASignedGetWithTheCursorAndCorrelation()
    {
        HttpRequestMessage? seen = null;
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedPackageCatalogGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(
            gateway,
            request =>
            {
                seen = request;
                return Json(
                    HttpStatusCode.OK,
                    """
                    {"schemaVersion":"1.0","items":[{"packageId":"33333333-3333-4333-8333-333333333333","packageCode":"GROWTH","displayName":"Growth","agentType":"AGENT","agentVersion":"1.0.0","billingPeriodDays":30,"priceInclGstPaise":236000,"basePricePaise":200000,"gstPaise":36000,"gstRatePercent":18,"components":[{"componentId":"lead_batch","quantity":30,"cadence":"SPREAD","selectableMaximum":null}]}],"nextCursor":"n1"}
                    """
                );
            }
        );
        var correlation = Guid.NewGuid().ToString("D");

        var page = await gateway.ListAsync(
            Guid.NewGuid(),
            Guid.NewGuid().ToString("D"),
            "AGENT",
            "1.0.0",
            "c 1",
            5,
            correlation,
            CancellationToken.None
        );

        Assert.Equal(HttpMethod.Get, seen!.Method);
        Assert.Equal(
            "/internal/v1/marketplace/agents/AGENT/versions/1.0.0/packages",
            seen.RequestUri!.AbsolutePath
        );
        Assert.Equal("?limit=5&after=c%201", seen.RequestUri.Query);
        Assert.StartsWith("Bearer ", seen.Headers.Authorization?.ToString());
        Assert.Equal(correlation, seen.Headers.GetValues("X-Correlation-ID").Single());
        Assert.Equal("n1", page.NextCursor);
        Assert.Equal(236000, Assert.Single(page.Items).PriceInclGstPaise);
        Assert.Null(page.Items[0].Components[0].SelectableMaximum);
    }

    [Theory]
    [InlineData(HttpStatusCode.UnprocessableEntity, typeof(PackageCatalogCursorException))]
    [InlineData(HttpStatusCode.BadGateway, typeof(PackageCatalogUnavailableException))]
    [InlineData(HttpStatusCode.Unauthorized, typeof(PackageCatalogUnavailableException))]
    public async Task OwnerFailuresMapToTheCatalogueExceptions(HttpStatusCode status, Type expected)
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedPackageCatalogGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(gateway, _ => Json(status, "{}"));

        var error = await Record.ExceptionAsync(() =>
            gateway.ListAsync(
                Guid.NewGuid(),
                "actor",
                "AGENT",
                "1.0.0",
                null,
                25,
                Guid.NewGuid().ToString("D"),
                CancellationToken.None
            )
        );

        Assert.IsType(expected, error);
    }

    private static HttpResponseMessage Json(HttpStatusCode status, string body) =>
        new(status) { Content = new StringContent(body, Encoding.UTF8, "application/json") };

    private static void ReplaceClient(
        object target,
        Func<HttpRequestMessage, HttpResponseMessage> send
    )
    {
        var field =
            target.GetType().GetField("_client", BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException("Missing field _client");
        var original = Assert.IsType<HttpClient>(field.GetValue(target));
        field.SetValue(
            target,
            new HttpClient(new StubHandler(send)) { BaseAddress = new Uri("https://owner.test") }
        );
        original.Dispose();
    }

    private sealed class StubHandler(Func<HttpRequestMessage, HttpResponseMessage> send)
        : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) => Task.FromResult(send(request));
    }
}
