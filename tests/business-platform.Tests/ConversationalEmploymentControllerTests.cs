// Implements: WC-115 R055-R063, R067-R071
// Constitutional basis: C-001, C-023, C-026, C-059, C-076, C-079, ADR-051
// IB: N/A - Founder-assigned WC-115

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ConversationalEmploymentControllerTests
{
    [Fact(DisplayName = "CEW-POLICY-001 inaccessible relationships return 404")]
    public async Task ReadsReturnExplicitUnavailableAndNotAccessibleStates()
    {
        var fixture = await CreateAsync();

        Assert.Equal(
            503,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.GetEmploymentWorkspaceAsync(
                        fixture.RelationshipId,
                        CancellationToken.None
                    )
                )
                .StatusCode
        );
        Assert.Equal(
            503,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.GetEmploymentPhaseAsync(
                        fixture.RelationshipId,
                        "INDUCTION",
                        CancellationToken.None
                    )
                )
                .StatusCode
        );
        Assert.Equal(
            503,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.GetEmploymentReadinessAsync(
                        fixture.RelationshipId,
                        CancellationToken.None
                    )
                )
                .StatusCode
        );
        Assert.Equal(
            503,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.GetEmploymentPlanAsync(
                        fixture.RelationshipId,
                        CancellationToken.None
                    )
                )
                .StatusCode
        );
        Assert.Equal(
            503,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.GetEmploymentPlanVersionAsync(
                        fixture.RelationshipId,
                        "plan-1",
                        CancellationToken.None
                    )
                )
                .StatusCode
        );
        Assert.Equal(
            404,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.GetEmploymentCommandAsync(
                        fixture.RelationshipId,
                        Guid.NewGuid(),
                        CancellationToken.None
                    )
                )
                .StatusCode
        );

        fixture
            .Gate.Setup(item => item.Snapshot())
            .Returns(
                new EmploymentProtocolGateSnapshot(
                    EmploymentProtocolOptions.ExpectedGateId,
                    false,
                    0
                )
            );
        Assert.Equal(
            404,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.GetEmploymentWorkspaceAsync(
                        fixture.RelationshipId,
                        CancellationToken.None
                    )
                )
                .StatusCode
        );

        var noCurrentPlan = await CreateAsync();
        noCurrentPlan.Employment.RegisterWorkspace(
            Workspace(
                noCurrentPlan.TenantId,
                noCurrentPlan.RelationshipId,
                currentPlanVersion: null
            )
        );
        Assert.Equal(
            404,
            Assert
                .IsType<ObjectResult>(
                    await noCurrentPlan.Controller.GetEmploymentPlanAsync(
                        noCurrentPlan.RelationshipId,
                        CancellationToken.None
                    )
                )
                .StatusCode
        );
    }

    [Fact]
    public async Task WorkspaceAndCommandOperationsPreserveGateAssuranceAndReplay()
    {
        var fixture = await CreateAsync();
        fixture.Employment.RegisterWorkspace(Workspace(fixture.TenantId, fixture.RelationshipId));

        Assert.IsType<OkObjectResult>(
            await fixture.Controller.GetEmploymentWorkspaceAsync(
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
        Assert.IsType<OkObjectResult>(
            await fixture.Controller.GetEmploymentPhaseAsync(
                fixture.RelationshipId,
                "INDUCTION",
                CancellationToken.None
            )
        );
        Assert.Equal(
            404,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.GetEmploymentPhaseAsync(
                        fixture.RelationshipId,
                        "INVENTED",
                        CancellationToken.None
                    )
                )
                .StatusCode
        );
        Assert.IsType<OkObjectResult>(
            await fixture.Controller.GetEmploymentReadinessAsync(
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
        Assert.IsType<OkObjectResult>(
            await fixture.Controller.GetEmploymentPlanAsync(
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
        Assert.IsType<OkObjectResult>(
            await fixture.Controller.GetEmploymentPlanVersionAsync(
                fixture.RelationshipId,
                "plan-1",
                CancellationToken.None
            )
        );
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.SubmitEmploymentCommandAsync(
                        fixture.RelationshipId,
                        ValidCommand(),
                        null,
                        CancellationToken.None
                    )
                )
                .StatusCode
        );

        var key = Guid.NewGuid();
        var accepted = Assert.IsType<ObjectResult>(
            await fixture.Controller.SubmitEmploymentCommandAsync(
                fixture.RelationshipId,
                ValidCommand(),
                key,
                CancellationToken.None
            )
        );
        Assert.Equal(202, accepted.StatusCode);
        var receipt = Assert.IsType<EmploymentCommandReceipt>(accepted.Value);
        Assert.IsType<OkObjectResult>(
            await fixture.Controller.GetEmploymentCommandAsync(
                fixture.RelationshipId,
                receipt.CommandId,
                CancellationToken.None
            )
        );
        Assert.Equal(
            202,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.SubmitEmploymentCommandAsync(
                        fixture.RelationshipId,
                        ValidCommand(),
                        key,
                        CancellationToken.None
                    )
                )
                .StatusCode
        );

        fixture.Controller.ControllerContext = Context(
            fixture.TenantId,
            fixture.ParticipantId,
            "AAL2"
        );
        Assert.Equal(
            403,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.SubmitEmploymentCommandAsync(
                        fixture.RelationshipId,
                        ValidCommand(),
                        Guid.NewGuid(),
                        CancellationToken.None
                    )
                )
                .StatusCode
        );
    }

    [Fact(DisplayName = "CEW-FIT-18 authority is server-derived and non-enumerating")]
    public async Task MissingTenantParticipantAndFreshAssuranceFailClosed()
    {
        var fixture = await CreateAsync();
        fixture.Employment.RegisterWorkspace(Workspace(fixture.TenantId, fixture.RelationshipId));
        fixture.Controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext
            {
                User = new ClaimsPrincipal(new ClaimsIdentity([], "Test")),
            },
        };
        Assert.Equal(
            404,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.GetEmploymentWorkspaceAsync(
                        fixture.RelationshipId,
                        CancellationToken.None
                    )
                )
                .StatusCode
        );

        fixture.Controller.ControllerContext = Context(
            fixture.TenantId,
            Guid.NewGuid(),
            "AAL3_FRESH"
        );
        Assert.Equal(
            404,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.GetEmploymentWorkspaceAsync(
                        fixture.RelationshipId,
                        CancellationToken.None
                    )
                )
                .StatusCode
        );

        foreach (var participantClaimType in new[] { ClaimTypes.NameIdentifier, "sub" })
        {
            fixture.Controller.ControllerContext = Context(
                fixture.TenantId,
                fixture.ParticipantId,
                "AAL3_FRESH",
                participantClaimType: participantClaimType
            );
            Assert.IsType<OkObjectResult>(
                await fixture.Controller.GetEmploymentWorkspaceAsync(
                    fixture.RelationshipId,
                    CancellationToken.None
                )
            );
        }

        foreach (
            var context in new[]
            {
                Context(fixture.TenantId, fixture.ParticipantId, ""),
                Context(fixture.TenantId, fixture.ParticipantId, "AAL3_FRESH", "invalid"),
                Context(
                    fixture.TenantId,
                    fixture.ParticipantId,
                    "AAL3_FRESH",
                    DateTimeOffset.UtcNow.AddMinutes(-6).ToUnixTimeSeconds().ToString()
                ),
                Context(
                    fixture.TenantId,
                    fixture.ParticipantId,
                    "AAL3_FRESH",
                    DateTimeOffset.UtcNow.AddMinutes(2).ToUnixTimeSeconds().ToString()
                ),
            }
        )
        {
            fixture.Controller.ControllerContext = context;
            Assert.Equal(
                403,
                Assert
                    .IsType<ObjectResult>(
                        await fixture.Controller.SubmitEmploymentCommandAsync(
                            fixture.RelationshipId,
                            ValidCommand(),
                            Guid.NewGuid(),
                            CancellationToken.None
                        )
                    )
                    .StatusCode
            );
        }
    }

    [Fact]
    public async Task CommandValidationConflictAndTerminalReplayAreStable()
    {
        var fixture = await CreateAsync();
        fixture.Employment.RegisterWorkspace(Workspace(fixture.TenantId, fixture.RelationshipId));
        var malformed = Json(
            """
            {
              "schemaVersion": "1.0",
              "kind": "INVENTED",
              "subjectRef": "requirement-1",
              "expectedWorkspaceVersion": "workspace-1",
              "expectedManifestVersion": "manifest-1"
            }
            """
        );
        Assert.Equal(
            400,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.SubmitEmploymentCommandAsync(
                        fixture.RelationshipId,
                        malformed,
                        Guid.NewGuid(),
                        CancellationToken.None
                    )
                )
                .StatusCode
        );
        var stale = Json(
            """
            {
              "schemaVersion": "1.0",
              "kind": "CONFIRM_INDUCTION_ITEM",
              "subjectRef": "requirement-1",
              "expectedWorkspaceVersion": "workspace-stale",
              "expectedManifestVersion": "manifest-1"
            }
            """
        );
        Assert.Equal(
            409,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.SubmitEmploymentCommandAsync(
                        fixture.RelationshipId,
                        stale,
                        Guid.NewGuid(),
                        CancellationToken.None
                    )
                )
                .StatusCode
        );

        var key = Guid.NewGuid();
        var submission = fixture.Employment.Submit(
            fixture.TenantId,
            fixture.RelationshipId,
            fixture.ParticipantId,
            key,
            ValidCommand()
        );
        foreach (var owner in new[] { "CE", "DOMAIN_ADAPTER" })
        {
            fixture.Employment.UpdateOwnerStep(
                fixture.TenantId,
                fixture.RelationshipId,
                submission.Receipt.CommandId,
                owner,
                "COMPLETED",
                $"owner-command:{owner}",
                "source-1",
                $"evidence:{owner}"
            );
        }
        Assert.IsType<OkObjectResult>(
            await fixture.Controller.SubmitEmploymentCommandAsync(
                fixture.RelationshipId,
                ValidCommand(),
                key,
                CancellationToken.None
            )
        );
        var changed = Json(
            """
            {
              "schemaVersion": "1.0",
              "kind": "CONFIRM_INDUCTION_ITEM",
              "subjectRef": "requirement-2",
              "expectedWorkspaceVersion": "workspace-1",
              "expectedManifestVersion": "manifest-1"
            }
            """
        );
        Assert.Equal(
            409,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.SubmitEmploymentCommandAsync(
                        fixture.RelationshipId,
                        changed,
                        key,
                        CancellationToken.None
                    )
                )
                .StatusCode
        );
        Assert.Equal(
            404,
            Assert
                .IsType<ObjectResult>(
                    await fixture.Controller.GetEmploymentPlanVersionAsync(
                        fixture.RelationshipId,
                        "missing-plan",
                        CancellationToken.None
                    )
                )
                .StatusCode
        );
    }

    private static async Task<Fixture> CreateAsync()
    {
        var relationships = new EmploymentRelationshipService(
            new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N")),
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admitted = await relationships.AdmitAsync(
            tenantId,
            participantId,
            Guid.NewGuid(),
            "NEUTRAL",
            Guid.NewGuid(),
            CancellationToken.None
        );
        var gate = new Mock<IEmploymentProtocolGate>();
        gate.Setup(item => item.Snapshot())
            .Returns(
                new EmploymentProtocolGateSnapshot(
                    EmploymentProtocolOptions.ExpectedGateId,
                    true,
                    0
                )
            );
        var employment = new ConversationalEmploymentService();
        var coordinator = new Mock<IEmploymentCommandCoordinator>();
        coordinator
            .Setup(item =>
                item.CoordinateAsync(
                    It.IsAny<EmploymentCommandCoordinationContext>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .Returns(Task.CompletedTask);
        var controller = new ConversationalEmploymentController(
            relationships,
            gate.Object,
            employment,
            coordinator.Object
        )
        {
            ControllerContext = Context(tenantId, participantId, "AAL3_FRESH"),
        };
        return new Fixture(
            controller,
            gate,
            employment,
            tenantId,
            participantId,
            admitted.Relationship.RelationshipId
        );
    }

    private static ControllerContext Context(
        Guid tenantId,
        Guid participantId,
        string assurance,
        string? authenticationTime = null,
        string participantClaimType = "participant_id"
    )
    {
        var context = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(
                new ClaimsIdentity(
                    [
                        new Claim(participantClaimType, participantId.ToString()),
                        new Claim("authentication_assurance", assurance),
                        new Claim(
                            "auth_time",
                            authenticationTime
                                ?? DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString()
                        ),
                        new Claim("correlation_id", Guid.NewGuid().ToString()),
                    ],
                    "Test"
                )
            ),
        };
        context.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString();
        return new ControllerContext { HttpContext = context };
    }

    private static EmploymentWorkspaceSnapshot Workspace(
        Guid tenantId,
        Guid relationshipId,
        string? currentPlanVersion = "plan-1"
    )
    {
        var source = Source();
        var phases = new Dictionary<string, JsonElement>
        {
            ["INDUCTION"] = Phase("INDUCTION", source),
            ["PLANNING"] = Phase("PLANNING", source),
            ["OPERATIONS"] = Phase("OPERATIONS", source),
        };
        var readiness = JsonSerializer.SerializeToElement(
            new
            {
                induction = "READY",
                plan = "AGREED",
                operations = "ELIGIBLE",
                performance = "CURRENT",
                unmetConditions = Array.Empty<string>(),
                sources = new[] { source },
            }
        );
        var plan = Plan(source);
        var workspace = JsonSerializer.SerializeToElement(
            new
            {
                schemaVersion = "1.0",
                protocolVersion = "1.0-candidate",
                relationshipId,
                workspaceVersion = "workspace-1",
                agentType = "neutral-professional",
                agentVersion = "1.0.0",
                manifestVersion = "manifest-1",
                readiness,
                phases = phases.Values,
                currentPlan = currentPlanVersion is null ? (JsonElement?)null : plan,
                operations = new
                {
                    mode = "ACTIVE_BOUNDED",
                    eligibility = "ELIGIBLE",
                    eligibleSkillRefs = new[] { "skill-1" },
                    lockedSkillRefs = Array.Empty<string>(),
                    permittedOperationClasses = new[] { "READ_ONLY" },
                    stopReachable = true,
                    commercialSource = source,
                },
                sources = new[] { source },
                limitations = Array.Empty<string>(),
                availableCommands = Array.Empty<object>(),
                authoritativeCursor = "cursor-1",
                producedAt = DateTimeOffset.UtcNow,
            }
        );
        return new EmploymentWorkspaceSnapshot(
            tenantId,
            relationshipId,
            "workspace-1",
            "manifest-1",
            workspace,
            phases,
            readiness,
            new Dictionary<string, JsonElement> { ["plan-1"] = plan },
            currentPlanVersion,
            1,
            "wbe-1"
        );
    }

    private static JsonElement Phase(string phase, JsonElement source) =>
        JsonSerializer.SerializeToElement(
            new
            {
                phase,
                status = phase == "OPERATIONS" ? "ACTIVE" : "READY",
                progress = new
                {
                    mandatoryTotal = 1,
                    mandatoryCompleted = 1,
                    optionalTotal = 0,
                    optionalCompleted = 0,
                    blockedCount = 0,
                    deferredCount = 0,
                },
                completedItems = Array.Empty<object>(),
                inProgressItems = Array.Empty<object>(),
                pendingItems = Array.Empty<object>(),
                blockers = Array.Empty<object>(),
                assumptions = Array.Empty<string>(),
                dependencies = Array.Empty<object>(),
                milestones = Array.Empty<object>(),
                calendarCommitments = Array.Empty<object>(),
                evidenceState = "CURRENT",
                sourceFreshness = DateTimeOffset.UtcNow,
                limitations = Array.Empty<string>(),
                availableCommands = Array.Empty<object>(),
                sources = new[] { source },
            }
        );

    private static JsonElement Source() =>
        JsonSerializer.SerializeToElement(
            new
            {
                owner = "BP",
                contractVersion = "1.0.0-candidate.2",
                sourceVersion = "workspace-1",
                state = "CURRENT",
                observedAt = DateTimeOffset.UtcNow,
            }
        );

    private static JsonElement Plan(JsonElement source) =>
        JsonSerializer.SerializeToElement(
            new
            {
                planId = Guid.Parse("00000000-0000-0000-0000-000000000101"),
                planVersion = "plan-1",
                state = "AGREED",
                goalRef = "goal-1",
                outcomeLabel = "A bounded customer outcome",
                accountableOwner = "CUSTOMER",
                skillRefs = new[] { "skill-1" },
                milestones = Array.Empty<object>(),
                calendarCommitments = Array.Empty<object>(),
                source,
            }
        );

    private static JsonElement ValidCommand() =>
        Json(
            """
            {
              "schemaVersion": "1.0",
              "kind": "CONFIRM_INDUCTION_ITEM",
              "subjectRef": "requirement-1",
              "expectedWorkspaceVersion": "workspace-1",
              "expectedManifestVersion": "manifest-1"
            }
            """
        );

    private static JsonElement Json(string value)
    {
        using var document = JsonDocument.Parse(value);
        return document.RootElement.Clone();
    }

    private sealed record Fixture(
        ConversationalEmploymentController Controller,
        Mock<IEmploymentProtocolGate> Gate,
        ConversationalEmploymentService Employment,
        Guid TenantId,
        Guid ParticipantId,
        Guid RelationshipId
    );
}
