// Implements: work-contracts/WC-057-goal005-ae01-employment-journey-foundation.md § WC057-04, WC057-07
// constitutional_basis: C-005, C-023, C-026, C-059

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class EmploymentRelationshipsControllerTests
{
    [Fact]
    public async Task List_ReturnsOnlyParticipantAuthorizedRelationshipsWithServerResumeTarget()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var service = new EmploymentRelationshipService(
            factory, new RecordingRelationshipConstitutionalGateway(), NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var authorized = await service.AdmitAsync(
            tenantId, participantId, Guid.NewGuid(), "DMA", Guid.NewGuid(), CancellationToken.None);
        await service.AdmitAsync(
            tenantId, Guid.NewGuid(), Guid.NewGuid(), "SALES", Guid.NewGuid(), CancellationToken.None);
        await service.AdmitAsync(
            Guid.NewGuid(), participantId, Guid.NewGuid(), "HRA", Guid.NewGuid(), CancellationToken.None);
        await using (var seed = factory.CreateDbContext())
        {
            seed.RelationshipSkillConfigurations.AddRange(
                new RelationshipSkillConfiguration
                {
                    TenantId = tenantId, RelationshipId = authorized.Relationship.RelationshipId,
                    SkillId = "local-seo", SkillVersion = "1.0.0", Status = "ACTIVE",
                },
                new RelationshipSkillConfiguration
                {
                    TenantId = tenantId, RelationshipId = authorized.Relationship.RelationshipId,
                    SkillId = "campaign-planning", SkillVersion = "1.0.0", Status = "PROPOSED",
                });
            await seed.SaveChangesAsync();
        }
        var controller = new EmploymentRelationshipsController(service)
        {
            ControllerContext = CreateControllerContext(tenantId, participantId),
        };

        var result = Assert.IsType<OkObjectResult>(
            await controller.ListAsync(null, 20, CancellationToken.None));
        var json = JsonSerializer.SerializeToElement(result.Value);
        var item = Assert.Single(json.GetProperty("Items").EnumerateArray());

        Assert.Equal(authorized.Relationship.RelationshipId, item.GetProperty("RelationshipId").GetGuid());
        Assert.Equal("CONVERSATION", item.GetProperty("ResumeTarget").GetProperty("Surface").GetString());
        Assert.Equal("UNKNOWN", item.GetProperty("CurrencyState").GetString());
        Assert.Equal("NOT_STARTED", item.GetProperty("ConfigurationState").GetString());
        Assert.Equal(1, item.GetProperty("EnabledSkillCount").GetInt32());
        Assert.Equal(1, item.GetProperty("PendingSkillCount").GetInt32());
        Assert.Equal("Interview agent", item.GetProperty("NextActionLabel").GetString());
    }

    [Fact]
    public async Task List_MembershipContextOverridesForgedParticipantClaim()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var service = new EmploymentRelationshipService(
            factory, new RecordingRelationshipConstitutionalGateway(), NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var accountId = Guid.NewGuid();
        var otherAccountId = Guid.NewGuid();
        var authorized = await service.AdmitAsync(
            tenantId, accountId, Guid.NewGuid(), "DMA", Guid.NewGuid(), CancellationToken.None);
        await service.AdmitAsync(
            tenantId, otherAccountId, Guid.NewGuid(), "SALES", Guid.NewGuid(), CancellationToken.None);
        var context = CreateControllerContext(tenantId, otherAccountId);
        context.HttpContext.Items[CustomerMembershipMiddleware.MembershipItem] =
            new CustomerWorkspaceMembership(accountId, tenantId, Guid.NewGuid(), ["OWNER"]);
        var controller = new EmploymentRelationshipsController(service) { ControllerContext = context };

        var result = Assert.IsType<OkObjectResult>(
            await controller.ListAsync(null, 20, CancellationToken.None));
        var item = Assert.Single(JsonSerializer.SerializeToElement(result.Value)
            .GetProperty("Items").EnumerateArray());

        Assert.Equal(authorized.Relationship.RelationshipId, item.GetProperty("RelationshipId").GetGuid());
    }

    [Fact]
    public async Task List_ReturnsDistinctInstancesForSameCustomerAndProfessionalType()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var service = new EmploymentRelationshipService(
            factory, new RecordingRelationshipConstitutionalGateway(), NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admission = new AgentAdmission
        {
            TenantId = Guid.NewGuid(),
            ProfessionalTypeId = "DMA",
            ProfessionalVersion = "1.0.0",
            OwnerSubjectId = Guid.NewGuid(),
            State = AgentAdmissionState.Active,
        };
        await using (var seed = factory.CreateDbContext())
        {
            seed.AgentAdmissions.Add(admission);
            await seed.SaveChangesAsync();
        }
        await service.AdmitAsync(
            tenantId, participantId, Guid.NewGuid(), "DMA", admission.AdmissionId,
            admission.ProfessionalVersion, Guid.NewGuid(), CancellationToken.None);
        await service.AdmitAsync(
            tenantId, participantId, Guid.NewGuid(), "DMA", admission.AdmissionId,
            admission.ProfessionalVersion, Guid.NewGuid(), CancellationToken.None);
        var context = CreateControllerContext(tenantId, participantId);
        context.HttpContext.Items[CustomerMembershipMiddleware.MembershipItem] =
            new CustomerWorkspaceMembership(participantId, tenantId, Guid.NewGuid(), ["OWNER"]);
        var controller = new EmploymentRelationshipsController(service) { ControllerContext = context };

        var result = Assert.IsType<OkObjectResult>(
            await controller.ListAsync(null, 20, CancellationToken.None));
        var items = JsonSerializer.SerializeToElement(result.Value)
            .GetProperty("Items").EnumerateArray().ToArray();

        Assert.Equal(2, items.Length);
        Assert.All(items, item => Assert.Equal("DMA", item.GetProperty("ProfessionalType").GetString()));
        Assert.Equal(2, items.Select(item => item.GetProperty("AgentInstanceId").GetGuid()).Distinct().Count());
    }

    [Fact]
    public async Task List_ProjectsEveryLifecycleStateWithoutClientOwnedInterpretation()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var service = new EmploymentRelationshipService(
            factory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var states = Enum.GetValues<EmploymentRelationshipState>();
        var relationships = new List<EmploymentRelationship>();
        foreach (var (state, index) in states.Select((state, index) => (state, index)))
        {
            var admitted = await service.AdmitAsync(
                tenantId,
                participantId,
                Guid.NewGuid(),
                $"TYPE{index}",
                Guid.NewGuid(),
                CancellationToken.None
            );
            relationships.Add(admitted.Relationship);
            admitted.Relationship.State = state;
        }
        await using (var db = factory.CreateDbContext())
        {
            db.EmploymentRelationships.UpdateRange(relationships);
            await db.SaveChangesAsync();
        }
        var controller = new EmploymentRelationshipsController(service)
        {
            ControllerContext = CreateControllerContext(tenantId, participantId),
        };

        var result = Assert.IsType<OkObjectResult>(
            await controller.ListAsync(null, 100, CancellationToken.None)
        );
        var items = JsonSerializer.SerializeToElement(result.Value)
            .GetProperty("Items").EnumerateArray().ToArray();

        Assert.Equal(states.Length, items.Length);
        Assert.Contains(items, item => item.GetProperty("AvailabilityState").GetString() == "PAUSED");
        Assert.Contains(items, item => item.GetProperty("AvailabilityState").GetString() == "STOPPED");
        Assert.Contains(items, item => item.GetProperty("AvailabilityState").GetString() == "UNAVAILABLE");
        Assert.Contains(items, item => item.GetProperty("ResumeTarget").GetProperty("Surface").GetString() == "CONVERSATION");
        Assert.Contains(items, item => item.GetProperty("ResumeTarget").GetProperty("Surface").GetString() == "CONFIGURATION");
        Assert.Contains(items, item => item.GetProperty("ResumeTarget").GetProperty("Surface").GetString() == "WORK");
        Assert.Contains(items, item => item.GetProperty("UnreadState").GetString() == "ACTION_REQUIRED");
        Assert.Contains(items, item => item.GetProperty("ConfigurationState").GetString() == "BLOCKED");
        Assert.Contains(items, item => item.GetProperty("NextActionLabel").GetString() == "Review contract");
        Assert.Contains(items, item => item.GetProperty("NextActionLabel").GetString() == "Review stopped agent");
        Assert.Contains(items, item => item.GetProperty("CurrentWorkSummary").ValueKind == JsonValueKind.String);
    }

    [Fact]
    public async Task SelectionHandoff_ValidatesAuthorityAvailabilityAndHandleShape()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var service = new EmploymentRelationshipService(
            factory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var controller = new EmploymentRelationshipsController(service)
        {
            ControllerContext = CreateControllerContext(tenantId, participantId),
        };

        var unavailable = Assert.IsType<ObjectResult>(
            await controller.CreateSelectionFlashAsync(
                Guid.NewGuid(),
                new CreateMyAgentsSelectionRequest("HIRE_PAID"),
                CancellationToken.None
            )
        );
        Assert.Equal(StatusCodes.Status503ServiceUnavailable, unavailable.StatusCode);

        foreach (var handle in new[] { "short", new string('g', 64) })
        {
            var invalid = Assert.IsType<ObjectResult>(
                await controller.ConsumeSelectionFlashAsync(
                    new ConsumeMyAgentsSelectionRequest(handle),
                    CancellationToken.None
                )
            );
            Assert.Contains(
                "Selection handle is invalid.",
                JsonSerializer.Serialize(invalid.Value),
                StringComparison.Ordinal
            );
        }

        Assert.IsType<NoContentResult>(
            await controller.ConsumeSelectionFlashAsync(
                new ConsumeMyAgentsSelectionRequest(new string('a', 64)),
                CancellationToken.None
            )
        );

        controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext(),
        };
        Assert.IsType<UnauthorizedResult>(
            await controller.CreateSelectionFlashAsync(
                Guid.NewGuid(),
                new CreateMyAgentsSelectionRequest("HIRE_PAID"),
                CancellationToken.None
            )
        );
        Assert.IsType<UnauthorizedResult>(
            await controller.ConsumeSelectionFlashAsync(
                new ConsumeMyAgentsSelectionRequest(new string('a', 64)),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public void RelationshipCollectionAndAdmissionRequireCustomerMembership()
    {
        var adapted = typeof(EmploymentRelationshipsController).GetMethods()
            .Where(method => method.GetCustomAttributes(typeof(CustomerIdentityRouteAttribute), true).Length != 0)
            .Select(method => method.Name)
            .ToArray();

        Assert.Equal(
            [
                nameof(EmploymentRelationshipsController.ListAsync),
                nameof(EmploymentRelationshipsController.CreateSelectionFlashAsync),
                nameof(EmploymentRelationshipsController.ConsumeSelectionFlashAsync),
                nameof(EmploymentRelationshipsController.AdmitAsync),
            ],
            adapted);
    }

    [Fact]
    public async Task List_UsesOpaqueCursorAndRejectsUnknownCursor()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var service = new EmploymentRelationshipService(
            factory, new RecordingRelationshipConstitutionalGateway(), NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        await service.AdmitAsync(tenantId, participantId, Guid.NewGuid(), "DMA", Guid.NewGuid(), CancellationToken.None);
        await service.AdmitAsync(tenantId, participantId, Guid.NewGuid(), "SALES", Guid.NewGuid(), CancellationToken.None);
        var controller = new EmploymentRelationshipsController(service)
        {
            ControllerContext = CreateControllerContext(tenantId, participantId),
        };

        var first = Assert.IsType<OkObjectResult>(await controller.ListAsync(null, 1, CancellationToken.None));
        var firstJson = JsonSerializer.SerializeToElement(first.Value);
        var cursor = firstJson.GetProperty("NextCursor").GetString();
        Assert.NotNull(cursor);
        var second = Assert.IsType<OkObjectResult>(await controller.ListAsync(cursor, 1, CancellationToken.None));
        Assert.Single(JsonSerializer.SerializeToElement(second.Value).GetProperty("Items").EnumerateArray());

        var invalid = Assert.IsType<ObjectResult>(
            await controller.ListAsync(Convert.ToBase64String(Guid.NewGuid().ToByteArray()), 1, CancellationToken.None));
        Assert.Equal(404, invalid.StatusCode);
    }

    [Fact]
    public async Task List_RejectsEveryInvalidPaginationBoundary()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var service = new EmploymentRelationshipService(
            factory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var cases = new[]
        {
            (Query: "?limit=0", Cursor: (string?)null, Limit: 0),
            (Query: "?limit=101", Cursor: (string?)null, Limit: 101),
            (Query: "?unknown=value", Cursor: (string?)null, Limit: 20),
            (Query: "?cursor", Cursor: (string?)null, Limit: 20),
            (Query: "?cursor=", Cursor: "", Limit: 20),
            (Query: "?cursor=short", Cursor: "short", Limit: 20),
            (Query: "?cursor=" + new string('x', 2049), Cursor: new string('x', 2049), Limit: 20),
        };

        foreach (var testCase in cases)
        {
            var controller = new EmploymentRelationshipsController(service)
            {
                ControllerContext = CreateControllerContext(tenantId, participantId),
            };
            controller.Request.QueryString = new QueryString(testCase.Query);

            var result = Assert.IsType<ObjectResult>(
                await controller.ListAsync(
                    testCase.Cursor,
                    testCase.Limit,
                    CancellationToken.None
                )
            );

            Assert.Equal(StatusCodes.Status400BadRequest, result.StatusCode);
        }
    }

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
    public async Task AdmissionUsesResolvedMembershipWhenBrokerSubjectIsNotAGuid()
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
                        [new Claim("sub", "google-oauth2|customer-subject")],
                        "Test")),
                },
            },
        };
        controller.HttpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString();
        controller.HttpContext.Items[CustomerMembershipMiddleware.MembershipItem] =
            new CustomerWorkspaceMembership(participantId, tenantId, Guid.NewGuid(), ["OWNER"]);
        var admission = new AgentAdmission
        {
            TenantId = tenantId,
            ProfessionalTypeId = "DMA",
            ProfessionalVersion = "1.0.0",
            OwnerSubjectId = Guid.NewGuid(),
            State = AgentAdmissionState.Active,
        };
        await using (var seed = factory.CreateDbContext())
        {
            seed.AgentAdmissions.Add(admission);
            await seed.SaveChangesAsync();
        }

        var result = await controller.AdmitAsync(
            new AdmitEmploymentRelationshipRequest(
                Guid.NewGuid(), "DMA", admission.AdmissionId, admission.ProfessionalVersion),
            CancellationToken.None);

        var created = Assert.IsType<CreatedAtActionResult>(result);
        var response = Assert.IsType<EmploymentRelationshipResponse>(created.Value);
        await using var db = factory.CreateDbContext();
        var relationship = await db.EmploymentRelationships.FindAsync(response.RelationshipId);
        Assert.NotNull(relationship);
        Assert.Equal(tenantId, relationship.TenantId);
        Assert.Equal(admission.AdmissionId, relationship.ProfessionalAdmissionId);
        Assert.Equal(response.AgentInstanceId, relationship.AgentInstanceId);
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

    [Fact]
    public async Task TrialEndpointUsesAuthenticatedRelationshipParticipant()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var relationships = new EmploymentRelationshipService(
            factory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admission = new AgentAdmission
        {
            TenantId = tenantId,
            ProfessionalTypeId = "DMA",
            ProfessionalVersion = "1.0.0",
            OwnerSubjectId = Guid.NewGuid(),
            State = AgentAdmissionState.Active,
        };
        await using (var seed = factory.CreateDbContext())
        {
            seed.AgentAdmissions.Add(admission);
            await seed.SaveChangesAsync();
        }
        var admitted = await relationships.AdmitAsync(
            tenantId, participantId, Guid.NewGuid(), "DMA", admission.AdmissionId,
            admission.ProfessionalVersion, Guid.NewGuid(), CancellationToken.None);
        await relationships.TransitionAsync(
            tenantId, admitted.Relationship.RelationshipId, participantId, RelationshipParticipantRole.Evaluator,
            EmploymentRelationshipState.Interviewing, Guid.NewGuid(), false, CancellationToken.None);
        var startsAt = DateTimeOffset.UtcNow;
        var trialId = Guid.NewGuid();
        var gateway = new TrialOwnerGatewayStub
        {
            Wbe = new(trialId, startsAt, startsAt.AddDays(14)),
            Pr = new(trialId, "TRIAL_DEMONSTRATING", startsAt.AddDays(14)),
        };
        var controller = new EmploymentRelationshipsController(
            relationships, new RelationshipTrialService(factory, relationships, gateway))
        {
            ControllerContext = CreateControllerContext(tenantId, participantId),
        };

        var response = Assert.IsType<OkObjectResult>(await controller.StartTrialAsync(
            admitted.Relationship.RelationshipId, new StartRelationshipTrialRequest(), CancellationToken.None));
        var trial = Assert.IsType<RelationshipTrialResult>(response.Value);

        Assert.Equal(trialId, trial.TrialId);
        Assert.Equal("ACTIVE", trial.Status);
    }

    [Fact]
    public async Task HireSetupRejectsEachInvalidFieldBeforeMutation()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory, gateway, NullLogger<EmploymentRelationshipService>.Instance);
        var catalog = new HireTestCatalog();
        var controller = new EmploymentRelationshipsController(
            relationships,
            contracts: new EmploymentContractService(factory, catalog),
            configuration: new RelationshipConfigurationService(factory, gateway),
            professionalCatalog: catalog)
        {
            ControllerContext = CreateControllerContext(Guid.NewGuid(), Guid.NewGuid()),
        };
        var valid = ValidHireSetupRequest();
        PrepareRelationshipHireRequest[] invalidRequests =
        [
            valid with { AuthorityScopeConfirmation = "" },
            valid with { BusinessName = "" },
            valid with { BusinessName = new string('a', 161) },
            valid with { Location = "" },
            valid with { Location = new string('a', 201) },
            valid with { BusinessNature = "" },
            valid with { BusinessNature = new string('a', 1001) },
            valid with { Goal = "" },
            valid with { Goal = new string('a', 1001) },
            valid with { SuccessMeasure = "" },
            valid with { SuccessMeasure = new string('a', 501) },
            valid with { BudgetCeilingInrPaise = -1 },
            valid with { SelectedSkillIds = null! },
        ];

        foreach (var request in invalidRequests)
        {
            var response = Assert.IsType<ObjectResult>(await controller.PrepareHireAsync(
                Guid.NewGuid(), request, CancellationToken.None));
            Assert.IsType<ValidationProblemDetails>(response.Value);
        }
        await using var db = factory.CreateDbContext();
        Assert.Empty(await db.EmploymentRelationships.ToListAsync());
    }

    [Fact]
    public async Task HireSetupFailsClosedWhenAnyRequiredOwnerIsUnavailable()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory, gateway, NullLogger<EmploymentRelationshipService>.Instance);
        var catalog = new HireTestCatalog();
        var contracts = new EmploymentContractService(factory, catalog);
        var configuration = new RelationshipConfigurationService(factory, gateway);
        EmploymentRelationshipsController[] controllers =
        [
            new(relationships, contracts: contracts, professionalCatalog: catalog),
            new(relationships, configuration: configuration, professionalCatalog: catalog),
            new(relationships, contracts: contracts, configuration: configuration),
        ];

        foreach (var controller in controllers)
        {
            controller.ControllerContext = CreateControllerContext(Guid.NewGuid(), Guid.NewGuid());
            var response = Assert.IsType<ObjectResult>(await controller.PrepareHireAsync(
                Guid.NewGuid(), ValidHireSetupRequest(), CancellationToken.None));
            Assert.Equal(StatusCodes.Status503ServiceUnavailable, response.StatusCode);
        }
    }

    [Fact]
    public async Task HireSetupPersistsConfigurationAndPresentsExactContract()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory, gateway, NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        await using (var seed = factory.CreateDbContext())
        {
            seed.EmploymentRelationships.Add(new EmploymentRelationship
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                AgentInstanceId = Guid.NewGuid(),
                ProfessionalType = "DMA",
                ProfessionalVersion = "1.0.0",
                AcquisitionMode = "HIRE",
                EvaluationIntentId = Guid.NewGuid(),
                InitiatingParticipantId = participantId,
                State = EmploymentRelationshipState.Configuring,
            });
            seed.RelationshipParticipants.Add(new RelationshipParticipant
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ParticipantId = participantId,
                Role = RelationshipParticipantRole.Employer,
                BoundEvidenceId = Guid.NewGuid(),
            });
            await seed.SaveChangesAsync();
        }
        var catalog = new HireTestCatalog();
        var controller = new EmploymentRelationshipsController(
            relationships,
            contracts: new EmploymentContractService(factory, catalog),
            configuration: new RelationshipConfigurationService(factory, gateway),
            professionalCatalog: catalog)
        {
            ControllerContext = CreateControllerContext(tenantId, participantId),
        };

        var response = Assert.IsType<OkObjectResult>(await controller.PrepareHireAsync(
            relationshipId, ValidHireSetupRequest(), CancellationToken.None));

        Assert.IsType<EmploymentContractResponse>(response.Value);
        await using var db = factory.CreateDbContext();
        Assert.Equal(3, await db.RelationshipContextPayloads.CountAsync());
        Assert.Single(await db.RelationshipGoals.Where(value => value.Status == "ACCEPTED").ToListAsync());
        Assert.Single(await db.RelationshipSkillConfigurations.Where(value => value.Status == "ACCEPTED").ToListAsync());
        Assert.Single(await db.DecisionSpaceSnapshots.ToListAsync());
        Assert.Single(await db.EmploymentContractVersions.ToListAsync());
        Assert.Equal(
            EmploymentRelationshipState.ContractPendingAcceptance,
            (await db.EmploymentRelationships.SingleAsync()).State);
    }

    [Fact]
    public async Task CctAe01Stop01_AuthenticatedParticipantStopsPreActiveRelationship()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var relationships = new EmploymentRelationshipService(factory, new RecordingRelationshipConstitutionalGateway(), NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admitted = await relationships.AdmitAsync(tenantId, participantId, Guid.NewGuid(), "DMA", Guid.NewGuid(), CancellationToken.None);
        await using (var db = factory.CreateDbContext())
        {
            (await db.EmploymentRelationships.SingleAsync()).State = EmploymentRelationshipState.Configuring;
            await db.SaveChangesAsync();
        }
        var emergencyStops = new RelationshipEmergencyStopService(
            new InMemoryConversationStoreFactory(Guid.NewGuid().ToString("N")), relationships, new RecordingEmergencyStopGateway());
        var controller = new EmploymentRelationshipsController(relationships, emergencyStops: emergencyStops) { ControllerContext = CreateControllerContext(tenantId, participantId) };

        var result = await controller.StopAsync(admitted.Relationship.RelationshipId, new StopEmploymentRelationshipRequest(), CancellationToken.None);

        Assert.IsType<OkObjectResult>(result);
        Assert.Equal(EmploymentRelationshipState.StoppedEmergency,
            (await relationships.GetAsync(tenantId, admitted.Relationship.RelationshipId, CancellationToken.None))!.State);
    }

    [Fact]
    public async Task CctAe01StopRelease_StalePortalAuthenticationLeavesStopActive()
    {
        var fixture = await CreateStoppedEmployerAsync(DateTimeOffset.UtcNow.AddMinutes(-6));

        var result = await fixture.Controller.ReleaseStopAsync(
            fixture.RelationshipId,
            new ReleaseEmploymentRelationshipStopRequest(
                fixture.Stop.EvidenceId, fixture.Stop.CorrelationId, "RELEASE_EMERGENCY_STOP", "Customer confirmed recovery.", EmploymentRelationshipState.Active),
            CancellationToken.None);

        Assert.IsType<ObjectResult>(result);
        Assert.Equal(403, ((ObjectResult)result).StatusCode);
        Assert.Equal(EmploymentRelationshipState.StoppedEmergency,
            (await fixture.Service.GetAsync(fixture.TenantId, fixture.RelationshipId, CancellationToken.None))!.State);
    }

    [Fact]
    public async Task CctAe01StopRelease_FreshTierFourEmployerReleasesLinkedStop()
    {
        var fixture = await CreateStoppedEmployerAsync(DateTimeOffset.UtcNow);

        var result = await fixture.Controller.ReleaseStopAsync(
            fixture.RelationshipId,
            new ReleaseEmploymentRelationshipStopRequest(
                fixture.Stop.EvidenceId, fixture.Stop.CorrelationId, "RELEASE_EMERGENCY_STOP", "Customer confirmed recovery.", EmploymentRelationshipState.Active),
            CancellationToken.None);

        Assert.IsType<OkObjectResult>(result);
        Assert.Equal(EmploymentRelationshipState.Active,
            (await fixture.Service.GetAsync(fixture.TenantId, fixture.RelationshipId, CancellationToken.None))!.State);
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

    private static PrepareRelationshipHireRequest ValidHireSetupRequest() => new(
        "North Star Dental",
        "Pune",
        "Dental clinic",
        "Increase qualified appointments",
        "Monthly qualified bookings",
        250000,
        ["MARKET_RESEARCH_AND_MATURITY"],
        "CONFIRM_AUTHORITY_SCOPE");

    private sealed class HireTestCatalog : IProfessionalCatalog
    {
        public IReadOnlyList<ProfessionalDiscoveryResult> Discover(string outcome) => [];

        public ProfessionalDisclosure? GetDisclosure(string professionalType) =>
            professionalType == "DMA"
                ? new ProfessionalDisclosure(
                    "DMA",
                    "1.0.0",
                    "digital-marketing",
                    "Digital Marketing Professional",
                    ["Local service marketing"],
                    [new ProfessionalSkillDisclosure("MARKET_RESEARCH_AND_MATURITY", "Market Research", true, null)],
                    ["No guaranteed outcomes"],
                    ["Customer-approved budget ceiling"],
                    ["Emergency Stop"],
                    new ProfessionalTrialDisclosure(true, 14, false, false),
                    "Evidence-backed",
                    new IndicativePriceDisclosure("INR", 249900, "MONTHLY", "Includes GST"),
                    new ProfessionalEligibility(true, "Eligible"))
                : null;
    }

    private static async Task<(EmploymentRelationshipService Service, EmploymentRelationshipsController Controller,
        Guid TenantId, Guid RelationshipId, RelationshipStateHistory Stop)> CreateStoppedEmployerAsync(DateTimeOffset authenticatedAt)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var service = new EmploymentRelationshipService(factory, new RecordingRelationshipConstitutionalGateway(), NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admitted = await service.AdmitAsync(tenantId, participantId, Guid.NewGuid(), "DMA", Guid.NewGuid(), CancellationToken.None);
        await using (var db = factory.CreateDbContext())
        {
            (await db.EmploymentRelationships.SingleAsync()).State = EmploymentRelationshipState.Active;
            db.RelationshipParticipants.Add(new RelationshipParticipant
            {
                TenantId = tenantId,
                RelationshipId = admitted.Relationship.RelationshipId,
                ParticipantId = participantId,
                Role = RelationshipParticipantRole.Employer,
                BoundEvidenceId = Guid.NewGuid(),
            });
            await db.SaveChangesAsync();
        }
        await service.TransitionAsync(
            tenantId, admitted.Relationship.RelationshipId, participantId, RelationshipParticipantRole.Employer,
            EmploymentRelationshipState.StoppedEmergency, Guid.NewGuid(), false, CancellationToken.None);
        RelationshipStateHistory stop;
        await using (var db = factory.CreateDbContext())
            stop = await db.RelationshipStateHistory.SingleAsync(value => value.ToState == EmploymentRelationshipState.StoppedEmergency);
        var context = CreateControllerContext(tenantId, participantId);
        var identity = (ClaimsIdentity)context.HttpContext.User.Identity!;
        identity.AddClaim(new Claim("authentication_assurance", "TIER_4_PORTAL_FRESH"));
        identity.AddClaim(new Claim("auth_time", authenticatedAt.ToUnixTimeSeconds().ToString()));
        identity.AddClaim(new Claim("identity_provider", "keycloak"));
        var controller = new EmploymentRelationshipsController(service) { ControllerContext = context };
        return (service, controller, tenantId, admitted.Relationship.RelationshipId, stop);
    }
}