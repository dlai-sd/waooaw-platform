// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C7-02
// Constitutional basis: C-023, C-059, C-063

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Waooaw.BusinessPlatform.Services.Spend;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Spend;

public sealed class SimulatorHeaderTests
{
    private const string Header = SimulatorSpendHeader.HeaderName;

    private sealed record Outcome(string? Header, string Body);

    private static readonly SpendPurposeMap Purposes = SpendPurposeMap.Parse(
        File.ReadAllText(
            RepositoryPaths.Resolve("src/business-platform/Catalog/Spend/purpose-map.v1.json")
        )
    );

    private static ClaimsPrincipal Principal(
        string claimType,
        string role,
        bool authenticated = true
    ) => new(new ClaimsIdentity([new Claim(claimType, role)], authenticated ? "Test" : null));

    private static async Task<Outcome> CallAsync(
        bool enabled,
        ClaimsPrincipal? user,
        string path = "/trial",
        string? clientHeader = null
    )
    {
        var builder = WebApplication.CreateBuilder();
        builder.WebHost.UseTestServer();
        builder.Configuration.AddInMemoryCollection(
            new Dictionary<string, string?>
            {
                [$"{SimulatorHeaderOptions.SectionName}:Enabled"] = enabled ? "true" : "false",
            }
        );
        builder.Services.AddSimulatorSpendHeader(builder.Configuration);
        builder.Services.AddSingleton<ISpendAccountResolver>(
            new ObservingSpendAccountResolver(new SpendAccountResolver(Purposes))
        );
        await using var app = builder.Build();
        app.Use(
            async (context, next) =>
            {
                if (user is not null)
                    context.User = user;
                await next();
            }
        );
        app.UseSimulatorSpendHeader();
        app.Run(async context =>
        {
            var resolver = context.RequestServices.GetRequiredService<ISpendAccountResolver>();
            var body = "NO_SPEND_DECISION";
            if (context.Request.Path == "/trial")
                body = resolver
                    .Resolve(
                        new RelationshipSpendInput(
                            Guid.NewGuid(),
                            SpendAuthorityKinds.Trial,
                            SpendPurpose.AgentWork,
                            "WEB",
                            false
                        )
                    )
                    .AccountClass.ToStorage();
            else if (context.Request.Path == "/floor")
                body = resolver
                    .Resolve(
                        new RelationshipSpendInput(
                            Guid.NewGuid(),
                            SpendAuthorityKinds.None,
                            SpendPurpose.SafetyFloor,
                            "WEB",
                            false
                        )
                    )
                    .AccountClass.ToStorage();
            await context.Response.WriteAsync(body);
        });
        await app.StartAsync();
        using var client = app.GetTestClient();
        using var request = new HttpRequestMessage(HttpMethod.Get, path);
        if (clientHeader is not null)
            request.Headers.TryAddWithoutValidation(Header, clientHeader);
        using var response = await client.SendAsync(request);
        var seen = response.Headers.TryGetValues(Header, out var values)
            ? string.Join(",", values)
            : null;
        return new Outcome(seen, await response.Content.ReadAsStringAsync());
    }

    [Fact]
    public void The_header_flag_is_off_by_default_and_in_the_shipped_settings()
    {
        Assert.False(new SimulatorHeaderOptions().Enabled);
        using var settings = JsonDocument.Parse(
            File.ReadAllText(RepositoryPaths.Resolve("src/business-platform/appsettings.json"))
        );
        Assert.False(
            settings.RootElement.GetProperty("SimulatorHeaders").GetProperty("Enabled").GetBoolean()
        );
    }

    [Theory]
    [InlineData(ClaimTypes.Role, "visitor-simulator")]
    [InlineData("role", "visitor-simulator")]
    [InlineData("participant_role", "visitor-simulator")]
    [InlineData("role", "Visitor-Simulator")]
    public async Task The_header_is_emitted_for_the_simulator_role_when_the_flag_is_on(
        string claimType,
        string role
    )
    {
        var outcome = await CallAsync(true, Principal(claimType, role));
        Assert.Equal("SIMULATION", outcome.Header);
        Assert.Equal("SIMULATION", outcome.Body);
    }

    [Fact]
    public async Task The_header_reports_the_class_the_resolver_decided_for_the_request()
    {
        var outcome = await CallAsync(true, Principal("role", "visitor-simulator"), "/floor");
        Assert.Equal("PLATFORM_FLOOR", outcome.Header);
        Assert.Equal("PLATFORM_FLOOR", outcome.Body);
    }

    [Fact]
    public async Task The_header_is_absent_when_the_flag_is_off_but_simulator_spend_still_lands_on_simulation()
    {
        var outcome = await CallAsync(false, Principal("role", "visitor-simulator"));
        Assert.Null(outcome.Header);
        Assert.Equal("SIMULATION", outcome.Body);
    }

    [Theory]
    [InlineData("customer")]
    [InlineData("founder")]
    [InlineData("visitor-simulator-extra")]
    public async Task The_header_is_absent_for_other_roles_even_when_the_flag_is_on(string role)
    {
        var outcome = await CallAsync(true, Principal("role", role));
        Assert.Null(outcome.Header);
        Assert.Equal("TRIAL", outcome.Body);
    }

    [Fact]
    public async Task The_header_is_absent_for_anonymous_callers()
    {
        var outcome = await CallAsync(true, null);
        Assert.Null(outcome.Header);
        Assert.Equal("TRIAL", outcome.Body);
    }

    [Fact]
    public async Task A_role_claim_on_an_unauthenticated_identity_is_not_a_simulator()
    {
        var outcome = await CallAsync(
            true,
            Principal("role", "visitor-simulator", authenticated: false)
        );
        Assert.Null(outcome.Header);
        Assert.Equal("TRIAL", outcome.Body);
    }

    [Theory]
    [InlineData(false, "customer")]
    [InlineData(true, "customer")]
    [InlineData(false, "visitor-simulator")]
    public async Task A_client_supplied_header_is_never_echoed_or_trusted(bool enabled, string role)
    {
        var outcome = await CallAsync(enabled, Principal("role", role), clientHeader: "SIMULATION");
        Assert.Null(outcome.Header);
        Assert.Equal(role == "visitor-simulator" ? "SIMULATION" : "TRIAL", outcome.Body);
    }

    [Fact]
    public async Task The_header_is_omitted_when_the_request_made_no_spend_decision()
    {
        var outcome = await CallAsync(true, Principal("role", "visitor-simulator"), "/none");
        Assert.Null(outcome.Header);
        Assert.Equal("NO_SPEND_DECISION", outcome.Body);
    }

    [Fact]
    public void Outside_a_request_the_resolver_is_unchanged_and_records_nothing()
    {
        var resolver = new ObservingSpendAccountResolver(new SpendAccountResolver(Purposes));
        var decision = resolver.Resolve(
            new RelationshipSpendInput(
                Guid.NewGuid(),
                SpendAuthorityKinds.AcceptedOffering,
                SpendPurpose.AgentWork,
                "WEB",
                false
            )
        );
        Assert.Equal(SpendAccountClass.Subscription, decision.AccountClass);
        Assert.Null(SpendAccountObservationScope.Current);
    }
}
