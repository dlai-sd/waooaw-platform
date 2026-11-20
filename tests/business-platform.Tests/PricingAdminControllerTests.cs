// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-03
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-08
// constitutional_basis: C-023, C-059, C-063, C-088, C-089
using System.Reflection;
using System.Security.Claims;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Routing;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

internal sealed class RecordingPricingGateway : IPricingAdminGateway
{
    public List<PricingGatewayRequest> Requests { get; } = [];

    public Func<PricingGatewayRequest, PricingGatewayResponse> Respond { get; set; } =
        _ => new PricingGatewayResponse(
            200,
            JsonDocument.Parse("{}").RootElement.Clone(),
            "\"1:DRAFT:abc\""
        );

    public Task<PricingGatewayResponse> SendAsync(
        PricingGatewayRequest request,
        CancellationToken ct
    )
    {
        Requests.Add(request);
        return Task.FromResult(Respond(request));
    }
}

internal sealed class FakeCeilingStore : IEnvironmentSpendCeilingStore
{
    public List<(
        string Environment,
        long Maximum,
        long Hard,
        Guid Evidence,
        bool DryRun
    )> Calls { get; } = [];

    public Func<bool, EnvironmentCeilingOutcome> Respond { get; set; } =
        dryRun =>
            new(
                dryRun ? EnvironmentCeilingOutcomes.DryRunOk : EnvironmentCeilingOutcomes.Applied,
                50_000,
                60_000,
                null
            );

    public Task<EnvironmentCeilingOutcome> ApplyAsync(
        string environment,
        long maximumPaise,
        long hardMaximumPaise,
        Guid authorityEvidenceId,
        DateTimeOffset asOf,
        bool dryRun,
        CancellationToken ct
    )
    {
        Calls.Add((environment, maximumPaise, hardMaximumPaise, authorityEvidenceId, dryRun));
        return Task.FromResult(Respond(dryRun));
    }
}

internal sealed class FixedClock(DateTimeOffset now) : TimeProvider
{
    public DateTimeOffset Now { get; set; } = now;

    public override DateTimeOffset GetUtcNow() => Now;
}

internal static class PricingAdminFixtures
{
    public static readonly DateTimeOffset Now = new(2026, 11, 20, 9, 0, 0, TimeSpan.Zero);

    public static PricingAdminService Service(
        IPricingAdminGateway gateway,
        IEnvironmentSpendCeilingStore? ceilings = null,
        int writeLimit = 30,
        decimal hardMaximumInr = 500
    )
    {
        var clock = new FixedClock(Now);
        return new PricingAdminService(
            gateway,
            ceilings ?? new FakeCeilingStore(),
            new EnvironmentSpendOptions { HardMaximumInr = hardMaximumInr },
            new PricingAdminWriteLimiter(
                Options.Create(new PricingAdminOptions { WriteLimitPerMinute = writeLimit }),
                clock
            ),
            clock,
            NullLogger<PricingAdminService>.Instance
        );
    }

    public static PricingAdminController Controller(
        PricingAdminService service,
        string[] roles,
        bool stepUp,
        string? body = null,
        Guid? idempotencyKey = null,
        Guid? correlation = null,
        bool authenticated = true,
        string query = "",
        TimeSpan? authenticationAge = null
    )
    {
        var claims = new List<Claim> { new("participant_id", "admin-1") };
        claims.AddRange(roles.Select(role => new Claim("participant_role", role)));
        if (stepUp)
        {
            claims.Add(new Claim("amr", "mfa"));
            claims.Add(new Claim("acr", "2"));
            claims.Add(
                new Claim(
                    "auth_time",
                    (DateTimeOffset.UtcNow - (authenticationAge ?? TimeSpan.FromMinutes(1)))
                        .ToUnixTimeSeconds()
                        .ToString()
                )
            );
        }
        var http = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(
                authenticated ? new ClaimsIdentity(claims, "Test") : new ClaimsIdentity()
            ),
            TraceIdentifier = Guid.NewGuid().ToString(),
        };
        http.Items[TenantIsolationMiddleware.TenantIdItemKey] = Guid.NewGuid().ToString();
        http.Request.QueryString = new QueryString(query);
        http.Request.Headers["Idempotency-Key"] = (idempotencyKey ?? Guid.NewGuid()).ToString();
        http.Request.Headers["X-Correlation-ID"] = (correlation ?? Guid.NewGuid()).ToString();
        http.Request.Body = new MemoryStream(Encoding.UTF8.GetBytes(body ?? "{}"));
        return new PricingAdminController(service)
        {
            ControllerContext = new ControllerContext { HttpContext = http },
        };
    }

    public static string Draft(string kind = "RATE") =>
        $$$"""{"schemaVersion":"1.0","kind":"{{{kind}}}","body":{"x":1}}""";

    public static JsonElement Content(IActionResult result) =>
        JsonDocument.Parse(Assert.IsType<ContentResult>(result).Content!).RootElement.Clone();
}

public sealed class PricingAdminControllerTests
{
    private static readonly string Draft = PricingAdminFixtures.Draft();
    private const string DraftId = "7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11";

    private static Task<IActionResult> Call(PricingAdminController controller, string operation)
    {
        var action = typeof(PricingAdminController)
            .GetMethods()
            .Single(method =>
                method.Name.Equals(operation + "Async", StringComparison.OrdinalIgnoreCase)
            );
        var arguments = action
            .GetParameters()
            .Select(parameter =>
                parameter.ParameterType == typeof(CancellationToken)
                    ? (object)CancellationToken.None
                    : DraftId
            )
            .ToArray();
        return (Task<IActionResult>)action.Invoke(controller, arguments)!;
    }

    private static string Pascal(string operation) =>
        char.ToUpperInvariant(operation[0]) + operation[1..];

    public static IEnumerable<object[]> AllOperations() =>
        PricingAdminService.Operations.Keys.Select(id => new object[] { id });

    [Theory]
    [MemberData(nameof(AllOperations))]
    public async Task Anonymous_and_customer_callers_are_refused_with_a_published_problem(
        string operation
    )
    {
        var service = PricingAdminFixtures.Service(new RecordingPricingGateway());

        var anonymous = await Call(
            PricingAdminFixtures.Controller(service, [], false, Draft, authenticated: false),
            Pascal(operation)
        );
        var customer = await Call(
            PricingAdminFixtures.Controller(service, ["EMPLOYER"], true, Draft),
            Pascal(operation)
        );

        Assert.Equal(401, Assert.IsType<ContentResult>(anonymous).StatusCode);
        Assert.Equal(403, Assert.IsType<ContentResult>(customer).StatusCode);
        Assert.Equal(
            "application/problem+json",
            Assert.IsType<ContentResult>(customer).ContentType
        );
        Assert.Equal(
            "PRICING_FORBIDDEN",
            PricingAdminFixtures.Content(customer).GetProperty("code").GetString()
        );
    }

    [Theory]
    [InlineData("authorizePricingDraft")]
    [InlineData("activatePackageForSale")]
    public async Task Only_the_founder_with_a_step_up_authorizes_or_activates(string operation)
    {
        var gateway = new RecordingPricingGateway();
        var service = PricingAdminFixtures.Service(gateway);

        var admin = await Call(
            PricingAdminFixtures.Controller(service, ["pricing_admin"], true, Draft),
            Pascal(operation)
        );
        var founderWithoutStepUp = await Call(
            PricingAdminFixtures.Controller(service, ["founder"], false, Draft),
            Pascal(operation)
        );
        var founderWithStaleStepUp = await Call(
            PricingAdminFixtures.Controller(
                service,
                ["founder"],
                true,
                Draft,
                authenticationAge: TimeSpan.FromMinutes(6)
            ),
            Pascal(operation)
        );

        Assert.Equal(
            "PRICING_FORBIDDEN",
            PricingAdminFixtures.Content(admin).GetProperty("code").GetString()
        );
        Assert.Equal(
            "PRICING_STEP_UP_REQUIRED",
            PricingAdminFixtures.Content(founderWithoutStepUp).GetProperty("code").GetString()
        );
        Assert.Equal(
            "PRICING_STEP_UP_REQUIRED",
            PricingAdminFixtures.Content(founderWithStaleStepUp).GetProperty("code").GetString()
        );
        Assert.Empty(gateway.Requests);
    }

    [Fact]
    public async Task An_admin_drafts_and_the_call_is_signed_with_the_admin_role_and_the_idempotency_key()
    {
        var gateway = new RecordingPricingGateway();
        var key = Guid.NewGuid();
        var correlation = Guid.NewGuid();

        var result = await Call(
            PricingAdminFixtures.Controller(
                PricingAdminFixtures.Service(gateway),
                ["pricing_admin"],
                false,
                Draft,
                key,
                correlation
            ),
            "CreatePricingDraft"
        );

        var sent = Assert.Single(gateway.Requests);
        Assert.Equal(200, Assert.IsType<ContentResult>(result).StatusCode);
        Assert.Equal("wbeCreatePricingDraft", sent.WbeOperation);
        Assert.Equal("PRICING_ADMIN", sent.EffectiveRole);
        Assert.False(sent.StepUp);
        Assert.Equal(key, sent.IdempotencyKey);
        Assert.Equal(correlation, sent.CorrelationId);
        Assert.Equal("/internal/v1/pricing/drafts", sent.RouteTemplate);
        var forwarded = JsonDocument.Parse(sent.Body).RootElement;
        Assert.Equal(50_000, forwarded.GetProperty("deployTimeMaximumPaise").GetInt64());
    }

    [Fact]
    public async Task A_caller_cannot_supply_the_deploy_time_maximum()
    {
        var gateway = new RecordingPricingGateway();
        var body = """{"schemaVersion":"1.0","deployTimeMaximumPaise":99999999}""";

        var result = await Call(
            PricingAdminFixtures.Controller(
                PricingAdminFixtures.Service(gateway),
                ["founder"],
                true,
                body
            ),
            "CreatePricingDraft"
        );

        Assert.Equal(400, Assert.IsType<ContentResult>(result).StatusCode);
        Assert.Empty(gateway.Requests);
    }

    [Theory]
    [InlineData("not json")]
    [InlineData("[]")]
    [InlineData("""{"schemaVersion":"2.0"}""")]
    [InlineData("""{"kind":"RATE"}""")]
    public async Task Malformed_bodies_are_refused_before_the_owner_is_called(string body)
    {
        var gateway = new RecordingPricingGateway();

        var result = await Call(
            PricingAdminFixtures.Controller(
                PricingAdminFixtures.Service(gateway),
                ["founder"],
                true,
                body
            ),
            "CreatePricingDraft"
        );

        Assert.Equal(400, Assert.IsType<ContentResult>(result).StatusCode);
        Assert.Equal(
            "PRICING_REQUEST_INVALID",
            PricingAdminFixtures.Content(result).GetProperty("code").GetString()
        );
        Assert.Empty(gateway.Requests);
    }

    [Fact]
    public async Task A_state_changing_call_needs_a_uuid_idempotency_key()
    {
        var gateway = new RecordingPricingGateway();
        var controller = PricingAdminFixtures.Controller(
            PricingAdminFixtures.Service(gateway),
            ["founder"],
            true,
            Draft
        );
        controller.HttpContext.Request.Headers["Idempotency-Key"] = "not-a-uuid";

        var badKey = await Call(controller, "CreatePricingDraft");

        Assert.Equal(400, Assert.IsType<ContentResult>(badKey).StatusCode);
        Assert.Empty(gateway.Requests);
    }

    [Fact]
    public async Task Writes_without_an_idempotency_key_are_refused()
    {
        var gateway = new RecordingPricingGateway();
        var controller = PricingAdminFixtures.Controller(
            PricingAdminFixtures.Service(gateway),
            ["founder"],
            true,
            Draft
        );
        controller.HttpContext.Request.Headers.Remove("Idempotency-Key");

        var result = await Call(controller, "CreatePricingDraft");

        Assert.Equal(400, Assert.IsType<ContentResult>(result).StatusCode);
        Assert.Empty(gateway.Requests);
    }

    [Fact]
    public async Task Reads_forward_only_the_allowed_query_and_return_the_etag()
    {
        var gateway = new RecordingPricingGateway();
        var controller = PricingAdminFixtures.Controller(
            PricingAdminFixtures.Service(gateway),
            ["pricing_admin"],
            false,
            query: "?kind=RATE&state=EFFECTIVE"
        );

        var result = await Call(controller, "ListPricingDrafts");

        Assert.Equal(200, Assert.IsType<ContentResult>(result).StatusCode);
        Assert.Equal("kind=RATE&state=EFFECTIVE", Assert.Single(gateway.Requests).Query);
        Assert.Equal("\"1:DRAFT:abc\"", controller.Response.Headers.ETag.ToString());

        var bad = await Call(
            PricingAdminFixtures.Controller(
                PricingAdminFixtures.Service(gateway),
                ["pricing_admin"],
                false,
                query: "?admin=1"
            ),
            "ListPricingDrafts"
        );
        Assert.Equal(400, Assert.IsType<ContentResult>(bad).StatusCode);
    }

    [Fact]
    public async Task Path_identifiers_must_be_uuids()
    {
        var gateway = new RecordingPricingGateway();
        var controller = PricingAdminFixtures.Controller(
            PricingAdminFixtures.Service(gateway),
            ["pricing_admin"],
            false
        );

        var result = await controller.GetPricingDraftAsync("../../etc", CancellationToken.None);

        Assert.Equal(400, Assert.IsType<ContentResult>(result).StatusCode);
        Assert.Empty(gateway.Requests);
    }

    [Fact]
    public async Task Owner_failures_become_published_problems_with_only_the_published_members()
    {
        var gateway = new RecordingPricingGateway
        {
            Respond = _ => new PricingGatewayResponse(
                422,
                JsonDocument
                    .Parse(
                        """{"code":"PRICING_BELOW_FLOOR","minimumCompliantPricePaise":120000,"stack":"secret","violations":[{"rule":"R1"}]}"""
                    )
                    .RootElement.Clone(),
                null
            ),
        };

        var result = await Call(
            PricingAdminFixtures.Controller(
                PricingAdminFixtures.Service(gateway),
                ["pricing_admin"],
                false,
                Draft
            ),
            "SubmitPricingDraft"
        );

        var problem = PricingAdminFixtures.Content(result);
        Assert.Equal(422, Assert.IsType<ContentResult>(result).StatusCode);
        Assert.Equal("PRICING_BELOW_FLOOR", problem.GetProperty("code").GetString());
        Assert.Equal(120000, problem.GetProperty("minimumCompliantPricePaise").GetInt64());
        Assert.False(problem.TryGetProperty("stack", out _));
        Assert.Equal(1, problem.GetProperty("violations").GetArrayLength());
        Assert.True(Guid.TryParse(problem.GetProperty("correlationId").GetString(), out _));
    }

    [Theory]
    [InlineData(500, "PRICING_UNAVAILABLE")]
    [InlineData(418, "PRICING_UNAVAILABLE")]
    public async Task Unknown_owner_statuses_are_not_leaked(int status, string expected)
    {
        var gateway = new RecordingPricingGateway
        {
            Respond = _ => new PricingGatewayResponse(
                status,
                JsonDocument.Parse("""{"code":"INTERNAL_SQL_ERROR"}""").RootElement.Clone(),
                null
            ),
        };

        var result = await Call(
            PricingAdminFixtures.Controller(
                PricingAdminFixtures.Service(gateway),
                ["pricing_admin"],
                false
            ),
            "GetPricingLiveMargin"
        );

        Assert.Equal(503, Assert.IsType<ContentResult>(result).StatusCode);
        Assert.Equal(
            expected,
            PricingAdminFixtures.Content(result).GetProperty("code").GetString()
        );
    }

    [Fact]
    public async Task An_unreachable_owner_is_a_503_problem()
    {
        var gateway = new ThrowingGateway();

        var result = await Call(
            PricingAdminFixtures.Controller(
                PricingAdminFixtures.Service(gateway),
                ["pricing_admin"],
                false
            ),
            "GetPricingLiveMargin"
        );

        Assert.Equal(503, Assert.IsType<ContentResult>(result).StatusCode);
    }

    [Fact]
    public async Task State_changing_calls_are_rate_limited_per_subject()
    {
        var gateway = new RecordingPricingGateway();
        var service = PricingAdminFixtures.Service(gateway, writeLimit: 2);

        var results = new List<IActionResult>();
        for (var attempt = 0; attempt < 3; attempt++)
            results.Add(
                await Call(
                    PricingAdminFixtures.Controller(service, ["pricing_admin"], false, Draft),
                    "CreatePricingDraft"
                )
            );

        Assert.Equal(
            new[] { 200, 200, 429 },
            results.Select(result => Assert.IsType<ContentResult>(result).StatusCode ?? 0).ToArray()
        );
        Assert.Equal(
            "PRICING_RATE_LIMITED",
            PricingAdminFixtures.Content(results[2]).GetProperty("code").GetString()
        );
    }

    [Fact]
    public void The_controller_is_authorized_and_is_not_a_customer_identity_route()
    {
        var type = typeof(PricingAdminController);

        Assert.NotNull(type.GetCustomAttribute<AuthorizeAttribute>());
        Assert.Null(type.GetCustomAttribute<CustomerIdentityRouteAttribute>());
        Assert.Equal(
            PricingAdminService.PublicRoutePrefix,
            type.GetCustomAttribute<RouteAttribute>()!.Template
        );
    }

    [Fact]
    public void The_controller_routes_equal_the_service_operations_and_the_published_spec()
    {
        var actions = typeof(PricingAdminController)
            .GetMethods(BindingFlags.Instance | BindingFlags.Public | BindingFlags.DeclaredOnly)
            .Select(method => new
            {
                Name = method.Name,
                Http = method.GetCustomAttributes().OfType<HttpMethodAttribute>().Single(),
            })
            .ToDictionary(
                action => char.ToLowerInvariant(action.Name[0]) + action.Name[1..^"Async".Length],
                action =>
                    (
                        Method: action.Http.HttpMethods.Single(),
                        Route: $"{PricingAdminService.PublicRoutePrefix}/{action.Http.Template}"
                    ),
                StringComparer.Ordinal
            );
        var declared = PricingAdminService.Operations.ToDictionary(
            pair => pair.Key,
            pair => (pair.Value.Method, Route: pair.Value.PublicRoute)
        );

        Assert.Equal(declared.OrderBy(pair => pair.Key), actions.OrderBy(pair => pair.Key));

        var spec = File.ReadAllText(
            RepositoryPaths.Resolve(
                "architecture/reference/api-specs/pricing-admin-business-platform.openapi.yaml"
            )
        );
        foreach (var (id, (method, route)) in declared)
        {
            var start = spec.IndexOf($"\n  /{route}:\n", StringComparison.Ordinal);
            Assert.True(start >= 0, $"{route} is not in the published spec");
            var end = spec.IndexOf("\n  /", start + 1, StringComparison.Ordinal);
            var block = end < 0 ? spec[start..] : spec[start..end];
            Assert.Contains($"\n    {method.ToLowerInvariant()}:", block);
            Assert.Contains($"operationId: {id}", block);
        }
    }

    private sealed class ThrowingGateway : IPricingAdminGateway
    {
        public Task<PricingGatewayResponse> SendAsync(
            PricingGatewayRequest request,
            CancellationToken ct
        ) => throw new PricingAdminOwnerUnavailableException("down");
    }
}
