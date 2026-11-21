// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01, C6-02
// Constitutional basis: C-023, C-059, C-063, ADR-051

using System.Text.Json;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Moq;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Workbench;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

/// <summary>Real in-memory owner services behind the workbench services; only the remote owners are doubled.</summary>
internal sealed class WorkbenchHarness
{
    private WorkbenchHarness() { }

    public EmploymentRelationshipService Relationships { get; private init; } = null!;
    public WorkbenchProjectionService Projection { get; private init; } = null!;
    public WorkbenchCommandService Commands { get; private init; } = null!;
    public WorkbenchHandoffService Handoffs { get; private init; } = null!;
    public InMemoryWorkbenchHandoffStore HandoffStore { get; private init; } = null!;
    public InMemoryWorkbenchLedgerStore LedgerStore { get; private init; } = null!;
    public InMemoryWorkbenchGoalHistoryStore GoalHistory { get; private init; } = null!;
    public Mock<IPackageCatalogGateway> Packages { get; private init; } = null!;
    public Mock<IWorkbenchCommercialReader> Commercial { get; private init; } = null!;
    public Mock<IAdmittedExperienceManifestSource> Manifests { get; private init; } = null!;
    public RecordingEmergencyStopGateway StopGateway { get; private init; } = null!;
    public Guid TenantId { get; private init; }
    public Guid ParticipantId { get; private init; }
    public Guid RelationshipId { get; private init; }
    public RelationshipParticipantRole Role { get; private init; }

    public WorkbenchContext Context(string? audience = null, Guid? participant = null) =>
        new(
            TenantId,
            RelationshipId,
            "customer-subject",
            participant ?? ParticipantId,
            Role,
            audience ?? WorkbenchAudiences.FromRole(Role),
            Guid.NewGuid().ToString("D")
        );

    public static async Task<WorkbenchHarness> CreateAsync(bool enabledOptions = true)
    {
        var relationshipFactory = new InMemoryEmploymentRelationshipFactory(
            Guid.NewGuid().ToString("N")
        );
        var constitutional = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            relationshipFactory,
            constitutional,
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
        var role =
            await relationships.GetActiveRoleAsync(
                tenantId,
                admitted.Relationship.RelationshipId,
                participantId,
                CancellationToken.None
            ) ?? throw new InvalidOperationException("The admitted participant has no role.");

        var employment = new ConversationalEmploymentService();
        var configuration = new RelationshipConfigurationService(
            relationshipFactory,
            constitutional
        );
        var reviews = new PerformanceReviewService(relationshipFactory, constitutional);
        var evidenceGateway = new Mock<IRelationshipEvidenceGateway>();
        var evidence = new RelationshipEvidenceService(relationshipFactory, evidenceGateway.Object);
        var owners = new Mock<IRelationshipWorkspaceOwnerGateway>();
        var manifests = new Mock<IAdmittedExperienceManifestSource>();
        var commercial = new Mock<IWorkbenchCommercialReader>();
        commercial
            .Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ReturnsAsync(
                WorkbenchCommercialSnapshot.Unavailable(
                    "Billing is not reachable, so wallet figures are not shown."
                )
            );
        var stopGateway = new RecordingEmergencyStopGateway();
        var emergencyStops = new RelationshipEmergencyStopService(
            new InMemoryConversationStoreFactory(Guid.NewGuid().ToString("N")),
            relationships,
            stopGateway
        );
        var goalHistory = new InMemoryWorkbenchGoalHistoryStore();
        var packages = new Mock<IPackageCatalogGateway>();
        var projection = new WorkbenchProjectionService(
            relationships,
            employment,
            configuration,
            reviews,
            evidence,
            owners.Object,
            manifests.Object,
            commercial.Object,
            goalHistory,
            TimeProvider.System,
            NullLogger<WorkbenchProjectionService>.Instance
        );
        var handoffStore = new InMemoryWorkbenchHandoffStore();
        var handoffs = new WorkbenchHandoffService(
            handoffStore,
            Options.Create(
                new WorkbenchOptions
                {
                    Enabled = enabledOptions,
                    HandoffBaseUrl = "https://app.example.test",
                }
            ),
            TimeProvider.System
        );
        var ledgerStore = new InMemoryWorkbenchLedgerStore();
        var commands = new WorkbenchCommandService(
            relationships,
            employment,
            new Mock<IEmploymentCommandCoordinator>().Object,
            configuration,
            emergencyStops,
            evidence,
            projection,
            commercial.Object,
            packages.Object,
            goalHistory,
            new WorkbenchCommandLedger(ledgerStore, TimeProvider.System),
            handoffs,
            NullLogger<WorkbenchCommandService>.Instance
        );
        return new WorkbenchHarness
        {
            Relationships = relationships,
            Projection = projection,
            Commands = commands,
            Handoffs = handoffs,
            HandoffStore = handoffStore,
            LedgerStore = ledgerStore,
            GoalHistory = goalHistory,
            Packages = packages,
            Commercial = commercial,
            Manifests = manifests,
            StopGateway = stopGateway,
            TenantId = tenantId,
            ParticipantId = participantId,
            RelationshipId = admitted.Relationship.RelationshipId,
            Role = role,
        };
    }

    public static JsonDocument Manifest(string json) => JsonDocument.Parse(json);
}
