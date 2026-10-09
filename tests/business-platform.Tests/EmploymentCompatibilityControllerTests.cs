// Implements: WC-115 R020-R022, R072-R075
// Constitutional basis: C-023, C-059, C-063, C-076, C-079, ADR-051
// IB: N/A - Founder-assigned WC-115

using System.Security.Claims;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class EmploymentCompatibilityControllerTests
{
    [Fact]
    public void StartValidatesHeadersInventoryAndReplayConflict()
    {
        var service = new EmploymentCompatibilityService();
        var controller = Controller(service);
        var agents = new[] { Agent("trading"), Agent("tutor") };
        var request = new EmploymentCompatibilityRequest(
            "1.0",
            "1.0-candidate",
            "inventory-1",
            EmploymentCompatibilityService.InventoryDigest(agents),
            agents
        );

        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(
                    controller.StartEmploymentCompatibilityScan(request, null, null)
                )
                .StatusCode
        );
        var correlationId = Guid.NewGuid();
        var key = Guid.NewGuid();
        var accepted = Assert.IsType<ObjectResult>(
            controller.StartEmploymentCompatibilityScan(request, key, correlationId)
        );
        Assert.Equal(202, accepted.StatusCode);
        var receipt = Assert.IsType<EmploymentCompatibilityReceipt>(accepted.Value);
        Assert.IsType<OkObjectResult>(
            controller.GetEmploymentCompatibilityScan(receipt.ScanId, correlationId)
        );
        Assert.Equal(
            404,
            Assert
                .IsType<ObjectResult>(
                    controller.GetEmploymentCompatibilityScan(Guid.NewGuid(), correlationId)
                )
                .StatusCode
        );
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(
                    controller.GetEmploymentCompatibilityScan(receipt.ScanId, null)
                )
                .StatusCode
        );

        var changedAgents = agents.Append(Agent("legal")).ToArray();
        var changed = request with
        {
            Agents = changedAgents,
            OfferedInventoryDigest = EmploymentCompatibilityService.InventoryDigest(changedAgents),
        };
        Assert.Equal(
            409,
            Assert
                .IsType<ObjectResult>(
                    controller.StartEmploymentCompatibilityScan(changed, key, correlationId)
                )
                .StatusCode
        );
    }

    [Fact]
    public void CompletedReplayReturnsTerminalResult()
    {
        var service = new EmploymentCompatibilityService();
        var controller = Controller(service);
        var agents = new[] { Agent("trading") };
        var request = new EmploymentCompatibilityRequest(
            "1.0",
            "1.0-candidate",
            "inventory-1",
            EmploymentCompatibilityService.InventoryDigest(agents),
            agents
        );
        var key = Guid.NewGuid();
        var correlationId = Guid.NewGuid();
        var accepted = Assert.IsType<ObjectResult>(
            controller.StartEmploymentCompatibilityScan(request, key, correlationId)
        );
        var receipt = Assert.IsType<EmploymentCompatibilityReceipt>(accepted.Value);
        service.Complete(
            receipt.ScanId,
            [
                new EmploymentAgentCompatibilityResult(
                    "trading",
                    "1.0.0",
                    "1.0.0",
                    "1.0.0",
                    "PASS",
                    ["COMPATIBLE"],
                    [],
                    ["evidence:trading"]
                ),
            ],
            true
        );

        var replay = Assert.IsType<OkObjectResult>(
            controller.StartEmploymentCompatibilityScan(request, key, correlationId)
        );

        Assert.Equal("PASS", Assert.IsType<EmploymentCompatibilityResult>(replay.Value).State);
    }

    private static EmploymentCompatibilityController Controller(
        EmploymentCompatibilityService service
    )
    {
        var context = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(
                new ClaimsIdentity([new Claim("client_id", "platform-admission")], "Test")
            ),
        };
        return new EmploymentCompatibilityController(service)
        {
            ControllerContext = new ControllerContext { HttpContext = context },
        };
    }

    private static OfferedEmploymentAgent Agent(string agentType) =>
        new(
            agentType,
            "1.0.0",
            "CANDIDATE",
            "1.0-candidate",
            "1.0.0",
            new string('a', 64),
            "1.0.0",
            new string('b', 64)
        );
}
