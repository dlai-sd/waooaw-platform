// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R022, R028, R032
// Constitutional basis: C-023, C-059, C-063, C-088

using System.Security.Claims;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Services.AgentOperation;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.AgentOperation;

public sealed class AgentOperationAdminControllerTests
{
    private static readonly DateTimeOffset Now = new(2026, 12, 1, 9, 0, 0, TimeSpan.Zero);

    private static AgentOperationAdminController Controller(
        string? role,
        bool stepUp = false,
        Harness? harness = null
    )
    {
        var claims = new List<Claim> { new("sub", "founder-1") };
        if (role is not null)
            claims.Add(new Claim("role", role));
        if (stepUp)
        {
            claims.Add(new Claim("auth_time", Now.AddMinutes(-1).ToUnixTimeSeconds().ToString()));
            claims.Add(new Claim("acr", "2"));
            claims.Add(new Claim("amr", "otp"));
        }
        var controller = new AgentOperationAdminController((harness ?? new Harness()).Service, new FixedClock(Now))
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext
                {
                    User = new ClaimsPrincipal(new ClaimsIdentity(claims, "test")),
                },
            },
        };
        return controller;
    }

    private static AgentOperationSettingsBody Body(int allowance = 500) =>
        new(allowance, new Dictionary<string, int> { ["TYPE_A"] = 20 }, true, true, ["page-1"], false);

    [Fact]
    public async Task OnlyTheFounderReadsTheSettings_AndTheDefaultAllowanceIs1000()
    {
        var denied = Assert.IsType<ObjectResult>(await Controller("customer").GetSettingsAsync(default));
        Assert.Equal(403, denied.StatusCode);

        var read = Assert.IsType<OkObjectResult>(await Controller("founder").GetSettingsAsync(default));
        Assert.Equal(1000, Assert.IsType<AgentOperationSettings>(read.Value).ChatAllowanceDefault);
    }

    [Fact]
    public async Task AFounderWithoutAFreshStrongSignInCannotChangeTheSettings()
    {
        var harness = new Harness();

        var result = await Controller("founder", stepUp: false, harness).SaveSettingsAsync(Body(), default);

        Assert.Equal(403, Assert.IsType<ObjectResult>(result).StatusCode);
        Assert.Equal(1000, (await harness.Service.GetSettingsAsync(default)).ChatAllowanceDefault);
        var notFounder = await Controller("customer", stepUp: true).SaveSettingsAsync(Body(), default);
        Assert.Equal(403, Assert.IsType<ObjectResult>(notFounder).StatusCode);
    }

    [Fact]
    public async Task AFounderWithStepUpSavesTheSettings_AndAnInvalidAllowanceIsRefusedInPlainWords()
    {
        var harness = new Harness();
        var controller = Controller("founder", stepUp: true, harness);

        var saved = Assert.IsType<OkObjectResult>(await controller.SaveSettingsAsync(Body(), default));
        Assert.Equal(500, Assert.IsType<AgentOperationSettings>(saved.Value).ChatAllowanceDefault);
        Assert.Equal(500, (await harness.Service.GetSettingsAsync(default)).ChatAllowanceDefault);

        var refused = Assert.IsType<ObjectResult>(await controller.SaveSettingsAsync(Body(0), default));
        Assert.Equal(400, refused.StatusCode);
    }

    [Fact]
    public async Task ShareAndAttentionAreFounderOnlyAndReadWithoutCaching()
    {
        var founder = Controller("founder");

        Assert.IsType<OkObjectResult>(await founder.ShareAsync(null, null, default));
        Assert.IsType<OkObjectResult>(await founder.AttentionAsync(null, null, default));
        Assert.Equal("no-store", founder.Response.Headers.CacheControl.ToString());
        Assert.Equal(403, Assert.IsType<ObjectResult>(await Controller(null).ShareAsync(null, null, default)).StatusCode);
        Assert.Equal(403, Assert.IsType<ObjectResult>(await Controller(null).AttentionAsync(null, null, default)).StatusCode);
    }

    [Fact]
    public async Task AReversedRangeIsRefusedNotServed()
    {
        var founder = Controller("founder");

        var share = await founder.ShareAsync(new DateOnly(2026, 12, 10), new DateOnly(2026, 12, 1), default);

        Assert.Equal(400, Assert.IsType<ObjectResult>(share).StatusCode);
    }
}
