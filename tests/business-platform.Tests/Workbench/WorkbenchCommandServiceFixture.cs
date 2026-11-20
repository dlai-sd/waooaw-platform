// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-02
// Constitutional basis: C-023, C-059, C-063, ADR-051

using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Moq;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Workbench;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

/// <summary>Records what the command service logs, so a swallowed owner or history failure stays observable.</summary>
internal sealed class WorkbenchCapturedLogger<T> : ILogger<T>
{
    public List<(LogLevel Level, string Message, Exception? Exception)> Entries { get; } = [];

    public IDisposable? BeginScope<TState>(TState state)
        where TState : notnull => null;

    public bool IsEnabled(LogLevel logLevel) => true;

    public void Log<TState>(
        LogLevel logLevel,
        EventId eventId,
        TState state,
        Exception? exception,
        Func<TState, Exception?, string> formatter
    ) => Entries.Add((logLevel, formatter(state, exception), exception));
}

/// <summary>Goal history that can be made to fail on append or on read, to prove the owner's change is never undone by it.</summary>
internal sealed class WorkbenchFaultableGoalHistoryStore : IWorkbenchGoalHistoryStore
{
    private readonly InMemoryWorkbenchGoalHistoryStore _inner = new();

    public bool FailAppend { get; set; }
    public bool FailList { get; set; }

    public Task AppendAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid goalId,
        WorkbenchGoalVersionEntry entry,
        CancellationToken ct
    ) =>
        FailAppend
            ? Task.FromException(new InvalidOperationException("history store is down"))
            : _inner.AppendAsync(tenantId, relationshipId, goalId, entry, ct);

    public Task<IReadOnlyList<WorkbenchGoalVersionEntry>> ListAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid goalId,
        CancellationToken ct
    ) =>
        FailList
            ? Task.FromException<IReadOnlyList<WorkbenchGoalVersionEntry>>(
                new InvalidOperationException("history store is down")
            )
            : _inner.ListAsync(tenantId, relationshipId, goalId, ct);

    public Task<IReadOnlyDictionary<Guid, int>> LatestVersionsAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken ct
    ) => _inner.LatestVersionsAsync(tenantId, relationshipId, ct);
}

/// <summary>
/// An active employment relationship of the digital marketing agent, with its admitted experience declaration, an
/// employment workspace holding a plan draft, and real in-memory owners; only the remote owners are doubled.
/// </summary>
internal sealed class WorkbenchCommandServiceFixture
{
    public const string GoalTypeId = "UNDERSTAND_CURRENT_POSITION";
    public const string SkillId = "CONTENT_STRATEGY_AND_CALENDAR";
    public const string PlanVersion = "plan-1";

    private static readonly string ManifestText = File.ReadAllText(
        RepositoryPaths.Resolve(
            "src/digital-marketing-agent/contracts/employment-interface-manifest.v1.json"
        )
    );

    private WorkbenchCommandServiceFixture() { }

    public InMemoryEmploymentRelationshipFactory RelationshipFactory { get; private init; } = null!;
    public EmploymentRelationshipService Relationships { get; private init; } = null!;
    public ConversationalEmploymentService Employment { get; private init; } = null!;
    public RelationshipConfigurationService Configuration { get; private init; } = null!;
    public RecordingRelationshipConstitutionalGateway Constitutional { get; private init; } = null!;
    public WorkbenchCommandService Commands { get; private init; } = null!;
    public WorkbenchProjectionService Projection { get; private init; } = null!;
    public WorkbenchFaultableGoalHistoryStore GoalHistory { get; private init; } = null!;
    public WorkbenchCapturedLogger<WorkbenchCommandService> Logger { get; private init; } = null!;
    public InMemoryWorkbenchLedgerStore LedgerStore { get; private init; } = null!;
    public InMemoryWorkbenchHandoffStore HandoffStore { get; private init; } = null!;
    public Mock<IEmploymentCommandCoordinator> Coordinator { get; private init; } = null!;
    public Mock<IAdmittedExperienceManifestSource> Manifests { get; private init; } = null!;
    public Mock<IWorkbenchCommercialReader> Commercial { get; private init; } = null!;
    public Mock<IPackageCatalogGateway> Packages { get; private init; } = null!;
    public RecordingEmergencyStopGateway StopGateway { get; private init; } = null!;
    public Guid TenantId { get; private init; }
    public Guid RelationshipId { get; private init; }
    public Guid EmployerId { get; private init; }
    public Guid ManagerId { get; private init; }
    public Guid EvaluatorId { get; private init; }

    public static async Task<WorkbenchCommandServiceFixture> CreateAsync(
        EmploymentRelationshipState state = EmploymentRelationshipState.Active,
        bool withDeclaration = true,
        bool withWorkspace = true,
        bool withPlan = true
    )
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
        var relationshipId = Guid.NewGuid();
        var employerId = Guid.NewGuid();
        var managerId = Guid.NewGuid();
        var evaluatorId = Guid.NewGuid();
        await using (var db = relationshipFactory.CreateDbContext())
        {
            db.EmploymentRelationships.Add(
                new EmploymentRelationship
                {
                    RelationshipId = relationshipId,
                    TenantId = tenantId,
                    ProfessionalType = "DIGITAL_MARKETING_LOCAL_SERVICE",
                    ProfessionalVersion = "1.0.0",
                    AcquisitionMode = "HIRE",
                    EvaluationIntentId = Guid.NewGuid(),
                    InitiatingParticipantId = employerId,
                    State = state,
                    StateVersion = 1,
                }
            );
            foreach (
                var (participant, role) in new[]
                {
                    (employerId, RelationshipParticipantRole.Employer),
                    (managerId, RelationshipParticipantRole.RelationshipManager),
                    (evaluatorId, RelationshipParticipantRole.Evaluator),
                }
            )
                db.RelationshipParticipants.Add(
                    new RelationshipParticipant
                    {
                        TenantId = tenantId,
                        RelationshipId = relationshipId,
                        ParticipantId = participant,
                        Role = role,
                        BoundEvidenceId = Guid.NewGuid(),
                    }
                );
            await db.SaveChangesAsync();
        }

        var employment = new ConversationalEmploymentService();
        if (withWorkspace)
            employment.RegisterWorkspace(Workspace(tenantId, relationshipId, withPlan));
        var configuration = new RelationshipConfigurationService(
            relationshipFactory,
            constitutional
        );
        var reviews = new PerformanceReviewService(relationshipFactory, constitutional);
        var evidenceGateway = new Mock<IRelationshipEvidenceGateway>();
        evidenceGateway
            .Setup(item =>
                item.QueryAsync(
                    It.IsAny<Guid>(),
                    It.IsAny<IReadOnlyCollection<Guid>>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync([]);
        var evidence = new RelationshipEvidenceService(
            relationshipFactory,
            evidenceGateway.Object,
            constitutional,
            Options.Create(
                new RelationshipEvidenceExportOptions
                {
                    DownloadBaseUrl = "https://api.example.test",
                    SigningKey = new string('k', 32),
                }
            )
        );
        var manifests = new Mock<IAdmittedExperienceManifestSource>();
        if (withDeclaration)
            manifests
                .Setup(item =>
                    item.GetAsync(
                        It.IsAny<AdmittedManifestRequest>(),
                        It.IsAny<CancellationToken>()
                    )
                )
                .ReturnsAsync(() => JsonDocument.Parse(ManifestText));
        var commercial = new Mock<IWorkbenchCommercialReader>();
        var stopGateway = new RecordingEmergencyStopGateway();
        var emergencyStops = new RelationshipEmergencyStopService(
            new InMemoryConversationStoreFactory(Guid.NewGuid().ToString("N")),
            relationships,
            stopGateway
        );
        var goalHistory = new WorkbenchFaultableGoalHistoryStore();
        var projection = new WorkbenchProjectionService(
            relationships,
            employment,
            configuration,
            reviews,
            evidence,
            new Mock<IRelationshipWorkspaceOwnerGateway>().Object,
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
                new WorkbenchOptions { Enabled = true, HandoffBaseUrl = "https://app.example.test" }
            ),
            TimeProvider.System
        );
        var ledgerStore = new InMemoryWorkbenchLedgerStore();
        var coordinator = new Mock<IEmploymentCommandCoordinator>();
        var packages = new Mock<IPackageCatalogGateway>();
        var logger = new WorkbenchCapturedLogger<WorkbenchCommandService>();
        var commands = new WorkbenchCommandService(
            relationships,
            employment,
            coordinator.Object,
            configuration,
            emergencyStops,
            evidence,
            projection,
            commercial.Object,
            packages.Object,
            goalHistory,
            new WorkbenchCommandLedger(ledgerStore, TimeProvider.System),
            handoffs,
            logger
        );
        return new WorkbenchCommandServiceFixture
        {
            RelationshipFactory = relationshipFactory,
            Relationships = relationships,
            Employment = employment,
            Configuration = configuration,
            Constitutional = constitutional,
            Commands = commands,
            Projection = projection,
            GoalHistory = goalHistory,
            Logger = logger,
            LedgerStore = ledgerStore,
            HandoffStore = handoffStore,
            Coordinator = coordinator,
            Manifests = manifests,
            Commercial = commercial,
            Packages = packages,
            StopGateway = stopGateway,
            TenantId = tenantId,
            RelationshipId = relationshipId,
            EmployerId = employerId,
            ManagerId = managerId,
            EvaluatorId = evaluatorId,
        };
    }

    public WorkbenchContext Employer(string? audience = null) =>
        ContextFor(EmployerId, RelationshipParticipantRole.Employer, audience);

    public WorkbenchContext Manager() =>
        ContextFor(ManagerId, RelationshipParticipantRole.RelationshipManager, null);

    public WorkbenchContext Evaluator() =>
        ContextFor(EvaluatorId, RelationshipParticipantRole.Evaluator, null);

    public WorkbenchContext ContextFor(
        Guid participant,
        RelationshipParticipantRole role,
        string? audience
    ) =>
        new(
            TenantId,
            RelationshipId,
            "customer-subject",
            participant,
            role,
            audience ?? WorkbenchAudiences.FromRole(role),
            Guid.NewGuid().ToString("D")
        );

    public async Task<EmploymentRelationship> RelationshipAsync()
    {
        var relationship = await Relationships.GetAsync(
            TenantId,
            RelationshipId,
            CancellationToken.None
        );
        return relationship ?? throw new InvalidOperationException("The relationship is missing.");
    }

    public async Task<string> VersionAsync() =>
        WorkbenchProjectionService.VersionOf(await RelationshipAsync());

    public async Task SetStateAsync(EmploymentRelationshipState state)
    {
        await using var db = RelationshipFactory.CreateDbContext();
        var relationship = db.EmploymentRelationships.Single(item =>
            item.RelationshipId == RelationshipId
        );
        relationship.State = state;
        relationship.StateVersion += 1;
        await db.SaveChangesAsync();
    }

    public async Task<RelationshipGoal> AddGoalAsync(
        string goalTypeId = GoalTypeId,
        string title = "Know where we stand",
        string status = "PROPOSED",
        string? skillId = SkillId
    )
    {
        var goal = await Configuration.SaveGoalAsync(
            TenantId,
            RelationshipId,
            title,
            """{"parameters":{"BUSINESS_DOMAIN":"bakery"}}""",
            goalTypeId,
            null,
            "workbench:v1",
            status,
            CancellationToken.None
        );
        if (skillId is not null)
            await AddSkillAsync(skillId, "PROPOSED", goal.GoalId);
        return goal;
    }

    public Task<RelationshipSkillConfiguration> AddSkillAsync(
        string skillId = SkillId,
        string status = "PROPOSED",
        Guid? goalId = null,
        string applicability = "APPLICABLE"
    ) =>
        Configuration.SaveSkillAsync(
            TenantId,
            RelationshipId,
            skillId,
            "1.0.0",
            goalId,
            "OWNER_APPROVAL",
            applicability,
            null,
            status,
            CancellationToken.None
        );

    /// <summary>Makes the coordinator answer every submitted command the way the owners would.</summary>
    public void CoordinatorAnswers(string ownerState)
    {
        Coordinator
            .Setup(item =>
                item.CoordinateAsync(
                    It.IsAny<EmploymentCommandCoordinationContext>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .Callback<EmploymentCommandCoordinationContext, CancellationToken>(
                (context, _) =>
                {
                    var step = ownerState == "PARTIAL" ? "COMPLETED" : ownerState;
                    var owners =
                        ownerState == "COMPLETED"
                            ? context.CommandKind == "ACCEPT_PLAN_VERSION"
                                ? new[] { "DOMAIN_ADAPTER", "WBE", "CE" }
                                : ["DOMAIN_ADAPTER", "CE"]
                            : ["DOMAIN_ADAPTER"];
                    foreach (var owner in owners)
                        Employment.UpdateOwnerStep(
                            context.TenantId,
                            context.RelationshipId,
                            context.CommandId,
                            owner,
                            step,
                            "owner-ref",
                            "owner-version",
                            $"evidence-{owner}"
                        );
                }
            )
            .Returns(Task.CompletedTask);
    }

    public void CoordinatorFails(Exception failure) =>
        Coordinator
            .Setup(item =>
                item.CoordinateAsync(
                    It.IsAny<EmploymentCommandCoordinationContext>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ThrowsAsync(failure);

    private static JsonElement Source() =>
        JsonSerializer.SerializeToElement(
            new
            {
                owner = "BP",
                contractVersion = "1.0.0-candidate.2",
                sourceVersion = "workspace-1",
                state = "UNKNOWN",
                observedAt = DateTimeOffset.UtcNow,
                validUntil = DateTimeOffset.UtcNow.AddMinutes(5),
                limitation = "Owner validation remains pending.",
            }
        );

    private static JsonElement Phase(string phase, JsonElement source) =>
        JsonSerializer.SerializeToElement(
            new
            {
                phase,
                status = "DEGRADED",
                progress = new
                {
                    mandatoryTotal = 0,
                    mandatoryCompleted = 0,
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
                evidenceState = "UNKNOWN",
                sourceFreshness = DateTimeOffset.UtcNow,
                limitations = new[] { "Owner checks are pending." },
                availableCommands = Array.Empty<object>(),
                sources = new[] { source },
            }
        );

    private static EmploymentWorkspaceSnapshot Workspace(
        Guid tenantId,
        Guid relationshipId,
        bool withPlan
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
                induction = "NOT_STARTED",
                plan = "NO_PLAN",
                operations = "LOCKED",
                performance = "NOT_ESTABLISHED",
                unmetConditions = new[] { "Owner checks are pending." },
                sources = new[] { source },
            }
        );
        var plan = JsonSerializer.SerializeToElement(
            new
            {
                planId = Guid.NewGuid(),
                planVersion = PlanVersion,
                state = "DRAFT",
                goalRef = "goal-1",
                outcomeLabel = "Governed outcome",
                accountableOwner = "DOMAIN_ADAPTER",
                skillRefs = new[] { "skill-1" },
                milestones = new[]
                {
                    new
                    {
                        itemId = Guid.NewGuid(),
                        itemVersion = "item-1",
                        phase = "PLANNING",
                        label = "Validate plan",
                        mandatory = true,
                        state = "PROPOSED",
                        reason = "Owner validation is required.",
                        accountableOwner = "DOMAIN_ADAPTER",
                        blockedEffects = Array.Empty<string>(),
                        source,
                        availableCommands = Array.Empty<object>(),
                    },
                },
                calendarCommitments = Array.Empty<object>(),
                source,
            }
        );
        var workspaceNode = JsonSerializer.SerializeToNode(
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
                currentPlan = JsonNode.Parse(plan.GetRawText()),
                operations = new
                {
                    mode = "TRIAL_ADVISORY",
                    eligibility = "LOCKED",
                    eligibleSkillRefs = Array.Empty<string>(),
                    lockedSkillRefs = new[] { "skill-1" },
                    permittedOperationClasses = Array.Empty<string>(),
                    stopReachable = true,
                    commercialSource = source,
                },
                sources = new[] { source },
                limitations = new[] { "Owner checks are pending." },
                availableCommands = Array.Empty<object>(),
                authoritativeCursor = "cursor-1",
                producedAt = DateTimeOffset.UtcNow,
            }
        );
        if (!withPlan)
            workspaceNode!.AsObject().Remove("currentPlan");
        var workspace = JsonSerializer.SerializeToElement(workspaceNode);
        return new EmploymentWorkspaceSnapshot(
            tenantId,
            relationshipId,
            "workspace-1",
            "manifest-1",
            workspace,
            phases,
            readiness,
            withPlan
                ? new Dictionary<string, JsonElement> { [PlanVersion] = plan }
                : new Dictionary<string, JsonElement>(),
            withPlan ? PlanVersion : null,
            1,
            "wbe-1"
        );
    }
}
