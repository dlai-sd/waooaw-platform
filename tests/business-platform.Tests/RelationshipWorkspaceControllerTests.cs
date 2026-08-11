// Implements: ADR-046 section 10.1 end-to-end business-operation matrix
// constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-076, C-083, C-084, C-085

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

internal sealed class RelationshipOwnerGatewayStub : IRelationshipWorkspaceOwnerGateway
{
    public ExecutionOwnerProjection? Execution { get; set; }
    public CommercialOwnerProjection? Commercial { get; set; }
    public RelationshipOwnerContext? LastContext { get; private set; }

    public Task<ExecutionOwnerProjection?> GetExecutionAsync(
        RelationshipOwnerContext context, CancellationToken cancellationToken)
    {
        LastContext = context;
        return Task.FromResult(Execution);
    }

    public Task<CommercialOwnerProjection?> GetCommercialAsync(
        RelationshipOwnerContext context, CancellationToken cancellationToken)
    {
        LastContext = context;
        return Task.FromResult(Commercial);
    }
}

public sealed class RelationshipWorkspaceControllerTests
{
    [Fact]
    public async Task AuthenticatedOwnerTruthReplacesUnavailablePlaceholders()
    {
        var (controller, relationship, gateway) = await CreateControllerAsync();
        var producedAt = DateTimeOffset.UtcNow;
        gateway.Execution = new ExecutionOwnerProjection("execution-7", "CURRENT", producedAt);
        gateway.Commercial = new CommercialOwnerProjection(
            "commercial-9", "CURRENT", "INR 125", "INR 700 to INR 900", "BELOW_LIMIT", producedAt);

        var work = Json(await controller.GetWorkAsync(relationship.RelationshipId, CancellationToken.None));
        var usage = Json(await controller.GetUsageBudgetAsync(relationship.RelationshipId, CancellationToken.None));

        Assert.Equal("CURRENT", work.GetProperty("currencyState").GetString());
        Assert.Equal("execution-7", work.GetProperty("provenance").GetProperty("sourceProjectionVersion").GetString());
        Assert.Equal("CURRENT", usage.GetProperty("currencyState").GetString());
        Assert.Equal("INR 125", usage.GetProperty("actualAmount").GetString());
        Assert.Equal("commercial-9", usage.GetProperty("wbeProjectionVersion").GetString());
        Assert.Equal(relationship.TenantId, gateway.LastContext?.TenantId);
        Assert.Equal(relationship.RelationshipId, gateway.LastContext?.RelationshipId);
    }

    [Fact]
    public async Task MissingOwnerTruthRemainsExplicitlyUnavailable()
    {
        var (controller, relationship, _) = await CreateControllerAsync();

        var work = Json(await controller.GetWorkAsync(relationship.RelationshipId, CancellationToken.None));
        var usage = Json(await controller.GetUsageBudgetAsync(relationship.RelationshipId, CancellationToken.None));

        Assert.Equal("UNAVAILABLE", work.GetProperty("currencyState").GetString());
        Assert.Equal("unavailable-1", work.GetProperty("provenance").GetProperty("sourceProjectionVersion").GetString());
        Assert.Equal("UNAVAILABLE", usage.GetProperty("currencyState").GetString());
        Assert.Equal("Unavailable", usage.GetProperty("actualAmount").GetString());
    }

    [Fact]
    public async Task AggregatePreservesEachOwnerStateIndependently()
    {
        var (controller, relationship, gateway) = await CreateControllerAsync();
        gateway.Execution = new ExecutionOwnerProjection("execution-2", "STALE", DateTimeOffset.UtcNow);

        var workspace = Json(await controller.GetWorkspaceAsync(relationship.RelationshipId, CancellationToken.None));
        var sections = workspace.GetProperty("sections").EnumerateArray().ToDictionary(
            section => section.GetProperty("sectionType").GetString()!);

        Assert.Equal("STALE", sections["WORK"].GetProperty("currencyState").GetString());
        Assert.Equal("UNAVAILABLE", sections["USAGE_BUDGET"].GetProperty("currencyState").GetString());
        Assert.Equal("PARTIAL", workspace.GetProperty("snapshotState").GetString());
    }

    private static async Task<(RelationshipWorkspaceController Controller, EmploymentRelationship Relationship, RelationshipOwnerGatewayStub Gateway)> CreateControllerAsync()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var service = new EmploymentRelationshipService(
            factory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admitted = await service.AdmitAsync(
            tenantId, participantId, Guid.NewGuid(), "DMA", Guid.NewGuid(), CancellationToken.None);
        var gateway = new RelationshipOwnerGatewayStub();
        var httpContext = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity(
                [new Claim("participant_id", participantId.ToString()), new Claim("participant_role", "EMPLOYER")],
                "Test")),
            TraceIdentifier = Guid.NewGuid().ToString(),
        };
        httpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString();
        var controller = new RelationshipWorkspaceController(service, gateway)
        {
            ControllerContext = new ControllerContext { HttpContext = httpContext },
        };
        return (controller, admitted.Relationship, gateway);
    }

    private static JsonElement Json(IActionResult result)
    {
        var ok = Assert.IsType<OkObjectResult>(result);
        return JsonSerializer.SerializeToElement(ok.Value);
    }
}