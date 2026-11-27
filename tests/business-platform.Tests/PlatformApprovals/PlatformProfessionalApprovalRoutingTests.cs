// Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R024
// Constitutional basis: C-023, C-059, C-063

using System.Net;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Text.Encodings.Web;
using System.Text.Json;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.TestHost;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.PlatformApprovals;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.PlatformApprovals;

/// <summary>
/// The decision route is exercised through the real ASP.NET router. Calling the controller method directly cannot catch a
/// route template that never matches (a parameter named {action} is reserved and made every approval answer 404 on Demo).
/// </summary>
public sealed class PlatformProfessionalApprovalRoutingTests
{
    private const string Type = "DIGITAL_MARKETING_LOCAL_SERVICE";

    private sealed class FounderAuthHandler(
        IOptionsMonitor<AuthenticationSchemeOptions> options,
        ILoggerFactory logger,
        UrlEncoder encoder,
        TimeProvider clock
    ) : AuthenticationHandler<AuthenticationSchemeOptions>(options, logger, encoder)
    {
        protected override Task<AuthenticateResult> HandleAuthenticateAsync()
        {
            var claims = new[]
            {
                new Claim("sub", "founder-1"),
                new Claim("role", "founder"),
                new Claim("auth_time", clock.GetUtcNow().ToUnixTimeSeconds().ToString()),
                new Claim("acr", "2"),
                new Claim("amr", "otp"),
            };
            var ticket = new AuthenticationTicket(
                new ClaimsPrincipal(new ClaimsIdentity(claims, "Test")),
                "Test"
            );
            return Task.FromResult(AuthenticateResult.Success(ticket));
        }
    }

    private static async Task<(WebApplication App, HttpClient Client)> HostAsync()
    {
        var root = Path.GetDirectoryName(
            RepositoryPaths.Resolve("src/business-platform/business-platform.csproj")
        )!;
        var builder = WebApplication.CreateBuilder(
            new WebApplicationOptions { ContentRootPath = root }
        );
        builder.WebHost.UseTestServer();
        builder.Logging.ClearProviders();
        builder
            .Services.AddControllers()
            .AddApplicationPart(typeof(PlatformProfessionalApprovalsController).Assembly);
        builder
            .Services.AddAuthentication("Test")
            .AddScheme<AuthenticationSchemeOptions, FounderAuthHandler>("Test", _ => { });
        builder.Services.AddAuthorization();
        builder.Services.AddSingleton(TimeProvider.System);
        builder.Services.AddSingleton<IProfessionalCatalog, ProfessionalCatalog>();
        builder.Services.AddSingleton<IPlatformProfessionalApprovalStore>(
            new InMemoryPlatformProfessionalApprovalStore()
        );
        builder.Services.AddSingleton<IDbContextFactory<EmploymentRelationshipDbContext>>(
            new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"))
        );
        builder.Services.AddScoped<PlatformProfessionalApprovalService>();
        var app = builder.Build();
        app.UseRouting();
        app.UseAuthentication();
        app.UseAuthorization();
        app.MapControllers();
        await app.StartAsync();
        return (app, app.GetTestClient());
    }

    [Fact]
    public async Task TheListAndEveryDecisionAreReachableThroughTheRealRouter()
    {
        var (app, client) = await HostAsync();
        await using var _ = app;

        var listed = await client.GetAsync("/api/v1/admin/professionals");
        Assert.Equal(HttpStatusCode.OK, listed.StatusCode);

        foreach (
            var (action, reason, expected) in new[]
            {
                ("approve", (string?)null, "APPROVED"),
                ("suspend", "Paused for a review", "SUSPENDED"),
                ("approve", null, "APPROVED"),
                ("retire", "Replaced by a new version", "RETIRED"),
            }
        )
        {
            var response = await client.PostAsJsonAsync(
                $"/api/v1/admin/professionals/{Type}/versions/1.0.0/{action}",
                new { reason }
            );

            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            using var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            Assert.Equal(expected, body.RootElement.GetProperty("state").GetString());
        }
    }

    [Fact]
    public async Task AnUnknownDecisionWordIsRefusedByTheService_NotLostInRouting()
    {
        var (app, client) = await HostAsync();
        await using var _ = app;

        var response = await client.PostAsJsonAsync(
            $"/api/v1/admin/professionals/{Type}/versions/1.0.0/delete",
            new { reason = (string?)null }
        );

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        using var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        Assert.Equal(
            "PROFESSIONAL_APPROVAL_UNKNOWN_ACTION",
            body.RootElement.GetProperty("code").GetString()
        );
    }
}
