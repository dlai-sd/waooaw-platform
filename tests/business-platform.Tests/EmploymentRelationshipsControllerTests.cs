// Implements: work-contracts/WC-057-goal005-ae01-employment-journey-foundation.md § WC057-04, WC057-07
// constitutional_basis: C-005, C-023, C-026, C-059

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class EmploymentRelationshipsControllerTests
{
    [Fact]
    public async Task LegacyHireReplaysCanonicalRelationshipWithDeprecationHeaders()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var service = new EmploymentRelationshipService(
            factory,
            gateway,
            NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var contractId = Guid.NewGuid();
        var controller = new AgentsController(service, NullLogger<AgentsController>.Instance)
        {
            ControllerContext = CreateControllerContext(tenantId, participantId),
        };
        var request = new HireAgentRequest(
            contractId.ToString(), "DMA", "content-publish", "1", 100_000, "1");

        var first = Assert.IsType<OkObjectResult>(
            await controller.HireAgentAsync(request, CancellationToken.None));
        var replay = Assert.IsType<OkObjectResult>(
            await controller.HireAgentAsync(request, CancellationToken.None));
        var firstJson = JsonSerializer.SerializeToElement(first.Value);
        var replayJson = JsonSerializer.SerializeToElement(replay.Value);
        var relationshipId = firstJson.GetProperty("relationship_id").GetGuid();

        Assert.Equal(relationshipId, replayJson.GetProperty("relationship_id").GetGuid());
        Assert.NotEqual(contractId, relationshipId);
        Assert.Equal(1, gateway.CallCount);
        Assert.Equal("true", controller.Response.Headers["Deprecation"]);
        Assert.Contains($"/api/v1/employment/relationships/{relationshipId}", controller.Response.Headers.Link.ToString());
    }

    [Fact]
    public async Task AdmissionDerivesTenantAndParticipantFromAuthenticatedContext()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var service = new EmploymentRelationshipService(
            factory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var controller = new EmploymentRelationshipsController(service)
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext
                {
                    User = new ClaimsPrincipal(new ClaimsIdentity(
                        [new Claim("participant_id", participantId.ToString())],
                        "Test")),
                },
            },
        };
        controller.HttpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString();

        var result = await controller.AdmitAsync(
            new AdmitEmploymentRelationshipRequest(Guid.NewGuid(), "DMA"),
            CancellationToken.None);

        var created = Assert.IsType<CreatedAtActionResult>(result);
        var response = Assert.IsType<EmploymentRelationshipResponse>(created.Value);
        await using var db = factory.CreateDbContext();
        var relationship = await db.EmploymentRelationships.FindAsync(response.RelationshipId);
        Assert.NotNull(relationship);
        Assert.Equal(tenantId, relationship.TenantId);
        Assert.Equal(participantId, relationship.InitiatingParticipantId);
    }

    [Fact]
    public void TransitionRequestAcceptsCanonicalNamedEnums()
    {
        const string json = """
            {
                            "targetState": "TRIAL_ACTIVE",
              "actorParticipantId": "5f33925b-fb0c-4366-8414-7f85309639b9",
                            "actorRole": "OUTCOME_OWNER",
              "correlationId": "85dbf23b-6892-47db-af07-21fa21d365f2"
            }
            """;

        var request = JsonSerializer.Deserialize<TransitionEmploymentRelationshipRequest>(
            json,
            new JsonSerializerOptions(JsonSerializerDefaults.Web));

        Assert.NotNull(request);
        Assert.Equal(EmploymentRelationshipState.TrialActive, request.TargetState);
        Assert.Equal(RelationshipParticipantRole.OutcomeOwner, request.ActorRole);
    }

    [Fact]
    public void TransitionEndpointRequiresInternalServicePolicy()
    {
        var method = typeof(EmploymentRelationshipsController).GetMethod(
            nameof(EmploymentRelationshipsController.TransitionAsync));
        Assert.NotNull(method);

        var authorization = Assert.Single(
            method.GetCustomAttributes(typeof(AuthorizeAttribute), true)
                .Cast<AuthorizeAttribute>());
        Assert.Equal("InternalService", authorization.Policy);
    }

    private static ControllerContext CreateControllerContext(Guid tenantId, Guid participantId)
    {
        var context = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity(
                [new Claim("participant_id", participantId.ToString())],
                "Test")),
        };
        context.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString();
        return new ControllerContext { HttpContext = context };
    }
}