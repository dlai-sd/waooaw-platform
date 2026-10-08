// Implements: WC-115 R007-R010, R017-R018, R029-R038, CEW-FIT-04
// Constitutional basis: C-001, C-023, C-026, C-059, C-079, ADR-051
// IB: N/A - Founder-assigned WC-115

using System.Text.Json;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class EmploymentCommandCoordinatorTests
{
    [Fact]
    public async Task RequiredOwnersRunInClosedOrderAndPrIsNeverCalled()
    {
        var service = new ConversationalEmploymentService();
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var workspace = Workspace(tenantId, relationshipId);
        service.RegisterWorkspace(workspace);
        var command = Command();
        var submission = service.Submit(
            tenantId,
            relationshipId,
            Guid.NewGuid(),
            Guid.NewGuid(),
            command
        );
        var gateway = new RecordingGateway();
        var coordinator = new EmploymentCommandCoordinator(service, gateway);

        await coordinator.CoordinateAsync(
            new EmploymentCommandCoordinationContext(
                tenantId,
                relationshipId,
                Guid.NewGuid(),
                submission.Receipt.CommandId,
                "ACCEPT_PLAN_VERSION",
                command,
                workspace
            ),
            CancellationToken.None
        );

        Assert.Equal(["DOMAIN_ADAPTER", "WBE", "CE"], gateway.Owners);
        Assert.Equal(
            "COMPLETED",
            service.GetCommand(tenantId, relationshipId, submission.Receipt.CommandId)?.State
        );
        Assert.DoesNotContain("PR", gateway.Owners);
    }

    [Fact]
    public async Task UnknownOwnerStopsLaterDispatchAndEntersReconciliation()
    {
        var service = new ConversationalEmploymentService();
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var workspace = Workspace(tenantId, relationshipId);
        service.RegisterWorkspace(workspace);
        var command = Command();
        var submission = service.Submit(
            tenantId,
            relationshipId,
            Guid.NewGuid(),
            Guid.NewGuid(),
            command
        );
        var gateway = new RecordingGateway("DOMAIN_ADAPTER");
        var coordinator = new EmploymentCommandCoordinator(service, gateway);

        await coordinator.CoordinateAsync(
            new EmploymentCommandCoordinationContext(
                tenantId,
                relationshipId,
                Guid.NewGuid(),
                submission.Receipt.CommandId,
                "ACCEPT_PLAN_VERSION",
                command,
                workspace
            ),
            CancellationToken.None
        );

        Assert.Equal(["DOMAIN_ADAPTER"], gateway.Owners);
        Assert.Equal(
            "UNKNOWN",
            service.GetCommand(tenantId, relationshipId, submission.Receipt.CommandId)?.State
        );
    }

    private static EmploymentWorkspaceSnapshot Workspace(Guid tenantId, Guid relationshipId)
    {
        var source = Json(
            """
            {
              "owner": "BP",
              "contractVersion": "1.0.0-candidate.2",
              "sourceVersion": "workspace-1",
              "state": "CURRENT",
              "observedAt": "2026-10-08T00:00:00Z"
            }
            """
        );
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
        var plan = JsonSerializer.SerializeToElement(
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
        var aggregate = JsonSerializer.SerializeToElement(
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
                currentPlan = plan,
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
                producedAt = DateTimeOffset.Parse("2026-10-08T00:00:00Z"),
            }
        );
        return new EmploymentWorkspaceSnapshot(
            tenantId,
            relationshipId,
            "workspace-1",
            "manifest-1",
            aggregate,
            phases,
            readiness,
            new Dictionary<string, JsonElement> { ["plan-1"] = plan },
            "plan-1",
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
                sourceFreshness = DateTimeOffset.Parse("2026-10-08T00:00:00Z"),
                limitations = Array.Empty<string>(),
                availableCommands = Array.Empty<object>(),
                sources = new[] { source },
            }
        );

    private static JsonElement Command() =>
        Json(
            """
            {
              "schemaVersion": "1.0",
              "kind": "ACCEPT_PLAN_VERSION",
              "subjectRef": "plan-1",
              "expectedWorkspaceVersion": "workspace-1",
              "expectedManifestVersion": "manifest-1",
              "expectedPlanVersion": "plan-1",
              "expectedDecisionSpaceVersion": 1,
              "expectedWbeSourceVersion": "wbe-1",
              "acknowledgement": "I accept this exact plan."
            }
            """
        );

    private static JsonElement Json(string value)
    {
        using var document = JsonDocument.Parse(value);
        return document.RootElement.Clone();
    }

    private sealed class RecordingGateway(string? unknownOwner = null)
        : IEmploymentCommandOwnerGateway
    {
        public List<string> Owners { get; } = [];

        public Task<EmploymentOwnerValidation> ValidateAsync(
            string owner,
            EmploymentCommandCoordinationContext context,
            CancellationToken cancellationToken
        )
        {
            Owners.Add(owner);
            return Task.FromResult(
                new EmploymentOwnerValidation(
                    owner == unknownOwner ? "UNKNOWN" : "COMPLETED",
                    $"{owner.ToLowerInvariant()}:{context.CommandId}",
                    "source-1",
                    $"evidence:{owner}:{context.CommandId}"
                )
            );
        }
    }
}
