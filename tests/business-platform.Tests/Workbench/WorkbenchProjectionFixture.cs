// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, ADR-051

using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Workbench;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

internal sealed class FixedClock(DateTimeOffset now) : TimeProvider
{
    public override DateTimeOffset GetUtcNow() => now;
}

/// <summary>Fails the selected database openings so owner reads can be made to fail one at a time.</summary>
internal sealed class FaultableFactory(IDbContextFactory<EmploymentRelationshipDbContext> inner)
    : IDbContextFactory<EmploymentRelationshipDbContext>
{
    private int _calls;

    private int[] _failing = [];

    /// <summary>Fails the given openings, counted from this call (1 is the next opening).</summary>
    public void FailNth(params int[] openings)
    {
        _calls = 0;
        _failing = openings;
    }

    public EmploymentRelationshipDbContext CreateDbContext()
    {
        _calls++;
        if (_failing.Contains(_calls))
            throw new InvalidOperationException("Owner store unavailable.");
        return inner.CreateDbContext();
    }
}

internal sealed class FaultableGoalHistory(IWorkbenchGoalHistoryStore inner)
    : IWorkbenchGoalHistoryStore
{
    public Exception? Failure { get; set; }

    public Task AppendAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid goalId,
        WorkbenchGoalVersionEntry entry,
        CancellationToken ct
    ) => inner.AppendAsync(tenantId, relationshipId, goalId, entry, ct);

    public Task<IReadOnlyList<WorkbenchGoalVersionEntry>> ListAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid goalId,
        CancellationToken ct
    ) =>
        Failure is null
            ? inner.ListAsync(tenantId, relationshipId, goalId, ct)
            : Task.FromException<IReadOnlyList<WorkbenchGoalVersionEntry>>(Failure);

    public Task<IReadOnlyDictionary<Guid, int>> LatestVersionsAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken ct
    ) =>
        Failure is null
            ? inner.LatestVersionsAsync(tenantId, relationshipId, ct)
            : Task.FromException<IReadOnlyDictionary<Guid, int>>(Failure);
}

/// <summary>
/// The projection service over real in-memory relationship, goal, skill and review owners; the remote owners, the
/// admitted manifest, the evidence ledger and the billing reader are doubled so each read can be shaped by a test.
/// </summary>
internal sealed class WorkbenchProjectionFixture
{
    public static readonly DateTimeOffset Now = new(2030, 6, 15, 12, 0, 0, TimeSpan.Zero);
    public const string AgentType = "DIGITAL_MARKETING_LOCAL_SERVICE";

    private WorkbenchProjectionFixture() { }

    public Guid TenantId { get; } = Guid.NewGuid();
    public Guid RelationshipId { get; } = Guid.NewGuid();
    public Guid ParticipantId { get; } = Guid.NewGuid();
    public Guid AgentInstanceId { get; } = Guid.NewGuid();
    public RelationshipParticipantRole Role { get; private set; }
    public WorkbenchProjectionService Service { get; private set; } = null!;
    public InMemoryEmploymentRelationshipFactory Store { get; private set; } = null!;
    public FaultableFactory ConfigurationStore { get; private set; } = null!;
    public FaultableFactory ReviewStore { get; private set; } = null!;
    public FaultableFactory EvidenceStore { get; private set; } = null!;
    public FaultableGoalHistory GoalHistory { get; private set; } = null!;
    public InMemoryWorkbenchGoalHistoryStore GoalHistoryRecords { get; private set; } = null!;
    public RelationshipConfigurationService Configuration { get; private set; } = null!;
    public Mock<IRelationshipWorkspaceOwnerGateway> Owners { get; } = new();
    public Mock<IAdmittedExperienceManifestSource> Manifests { get; } = new();
    public Mock<IWorkbenchCommercialReader> Commercial { get; } = new();
    public Mock<IRelationshipEvidenceGateway> EvidenceGateway { get; } = new();
    public Mock<IConversationalEmploymentPersistence> Persistence { get; } = new();

    public static async Task<WorkbenchProjectionFixture> CreateAsync(
        RelationshipParticipantRole role = RelationshipParticipantRole.Employer,
        string? professionalVersion = "1.0.0",
        EmploymentRelationshipState state = EmploymentRelationshipState.Active,
        bool withDeclaration = true,
        Action<JsonNode>? mutateManifest = null
    )
    {
        var fixture = new WorkbenchProjectionFixture { Role = role };
        fixture.Store = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        fixture.ConfigurationStore = new FaultableFactory(fixture.Store);
        fixture.ReviewStore = new FaultableFactory(fixture.Store);
        fixture.EvidenceStore = new FaultableFactory(fixture.Store);
        await using (var seed = fixture.Store.CreateDbContext())
        {
            seed.EmploymentRelationships.Add(
                new EmploymentRelationship
                {
                    RelationshipId = fixture.RelationshipId,
                    TenantId = fixture.TenantId,
                    AgentInstanceId = fixture.AgentInstanceId,
                    ProfessionalType = AgentType,
                    ProfessionalVersion = professionalVersion,
                    EvaluationIntentId = Guid.NewGuid(),
                    InitiatingParticipantId = fixture.ParticipantId,
                    State = state,
                    StateVersion = 7,
                }
            );
            seed.RelationshipParticipants.Add(
                new RelationshipParticipant
                {
                    TenantId = fixture.TenantId,
                    RelationshipId = fixture.RelationshipId,
                    ParticipantId = fixture.ParticipantId,
                    Role = role,
                    BoundEvidenceId = Guid.NewGuid(),
                }
            );
            await seed.SaveChangesAsync();
        }
        var constitutional = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            fixture.Store,
            constitutional,
            NullLogger<EmploymentRelationshipService>.Instance
        );
        fixture.Configuration = new RelationshipConfigurationService(
            fixture.ConfigurationStore,
            constitutional
        );
        fixture.GoalHistoryRecords = new InMemoryWorkbenchGoalHistoryStore();
        fixture.GoalHistory = new FaultableGoalHistory(fixture.GoalHistoryRecords);
        fixture
            .Commercial.Setup(item =>
                item.GetWalletAsync(It.IsAny<WorkbenchContext>(), It.IsAny<CancellationToken>())
            )
            .ReturnsAsync(WorkbenchCommercialSnapshot.Unavailable("Billing is not reachable."));
        fixture
            .EvidenceGateway.Setup(item =>
                item.QueryAsync(
                    It.IsAny<Guid>(),
                    It.IsAny<IReadOnlyCollection<Guid>>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync([]);
        if (withDeclaration)
            fixture
                .Manifests.Setup(item =>
                    item.GetAsync(
                        It.IsAny<AdmittedManifestRequest>(),
                        It.IsAny<CancellationToken>()
                    )
                )
                .ReturnsAsync(() => Manifest(mutateManifest));
        fixture.Service = new WorkbenchProjectionService(
            relationships,
            new ConversationalEmploymentService(fixture.Persistence.Object),
            fixture.Configuration,
            new PerformanceReviewService(fixture.ReviewStore, constitutional),
            new RelationshipEvidenceService(fixture.EvidenceStore, fixture.EvidenceGateway.Object),
            fixture.Owners.Object,
            fixture.Manifests.Object,
            fixture.Commercial.Object,
            fixture.GoalHistory,
            new FixedClock(Now),
            NullLogger<WorkbenchProjectionService>.Instance
        );
        return fixture;
    }

    public WorkbenchContext Context(string? audience = null) =>
        new(
            TenantId,
            RelationshipId,
            "customer-subject",
            ParticipantId,
            Role,
            audience ?? WorkbenchAudiences.FromRole(Role),
            Guid.NewGuid().ToString("D")
        );

    /// <summary>The real DMA manifest, which declares an experience, optionally reshaped by the test.</summary>
    public static JsonDocument Manifest(Action<JsonNode>? mutate = null)
    {
        var node = JsonNode.Parse(
            File.ReadAllText(
                RepositoryPaths.Resolve(
                    "src/digital-marketing-agent/contracts/employment-interface-manifest.v1.json"
                )
            )
        )!;
        mutate?.Invoke(node);
        return JsonDocument.Parse(node.ToJsonString());
    }

    /// <summary>Restricts every monitor tile to stewards, so the customer owner is shown none.</summary>
    public static void TilesForStewardsOnly(JsonNode manifest)
    {
        foreach (var tile in manifest["experience"]!["monitor"]!["tiles"]!.AsArray())
            tile!["audiences"] = new JsonArray("steward");
    }

    public static JsonElement Json(string json)
    {
        using var document = JsonDocument.Parse(json);
        return document.RootElement.Clone();
    }

    /// <summary>
    /// The workspace the employment owner holds. It must be set before the service first reads it, because the
    /// employment service keeps what it loaded.
    /// </summary>
    public void SetWorkspace(
        string readinessJson = "{}",
        IReadOnlyDictionary<string, string>? plans = null,
        string? currentPlanVersion = null
    )
    {
        var snapshot = new EmploymentWorkspaceSnapshot(
            TenantId,
            RelationshipId,
            "workspace-1",
            "1.1.0",
            Json("{}"),
            new Dictionary<string, JsonElement>(),
            Json(readinessJson),
            (plans ?? new Dictionary<string, string>()).ToDictionary(
                item => item.Key,
                item => Json(item.Value)
            ),
            currentPlanVersion,
            1,
            "wbe-1"
        );
        Persistence.Setup(item => item.LoadWorkspace(TenantId, RelationshipId)).Returns(snapshot);
    }

    public void SetExecution(ExecutionOwnerProjection? projection) =>
        Owners
            .Setup(item =>
                item.GetExecutionAsync(
                    It.IsAny<RelationshipOwnerContext>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync(projection);

    public async Task<RelationshipGoal> AddGoalAsync(
        string goal = "Grow weekly enquiries",
        string measure = "UNDERSTAND_CURRENT_POSITION",
        string status = "PROPOSED",
        string? baseline = null,
        string? threshold = null,
        DateTimeOffset? createdAt = null,
        DateTimeOffset? updatedAt = null
    )
    {
        await using var db = Store.CreateDbContext();
        var item = new RelationshipGoal
        {
            TenantId = TenantId,
            RelationshipId = RelationshipId,
            Goal = goal,
            Measure = measure,
            Status = status,
            Baseline = baseline,
            DecisionThreshold = threshold,
            CreatedAt = createdAt ?? DateTimeOffset.UtcNow,
            UpdatedAt = updatedAt ?? createdAt ?? DateTimeOffset.UtcNow,
        };
        db.RelationshipGoals.Add(item);
        await db.SaveChangesAsync();
        return item;
    }

    public async Task<RelationshipSkillConfiguration> AddSkillAsync(
        string skillId,
        string status = "PROPOSED",
        string applicability = "APPLICABLE",
        Guid? goalId = null,
        DateTimeOffset? updatedAt = null
    )
    {
        await using var db = Store.CreateDbContext();
        var item = new RelationshipSkillConfiguration
        {
            TenantId = TenantId,
            RelationshipId = RelationshipId,
            SkillId = skillId,
            SkillVersion = "1.0.0",
            GoalId = goalId,
            Status = status,
            Applicability = applicability,
            UpdatedAt = updatedAt ?? DateTimeOffset.UtcNow,
        };
        db.RelationshipSkillConfigurations.Add(item);
        await db.SaveChangesAsync();
        return item;
    }

    public async Task AddGoalDecisionAsync(
        RelationshipGoal goal,
        string decision,
        string? correctionReason = null,
        string? goalVersion = null
    )
    {
        await using var db = Store.CreateDbContext();
        db.RelationshipGoalDecisions.Add(
            new RelationshipGoalDecision
            {
                TenantId = TenantId,
                RelationshipId = RelationshipId,
                GoalId = goal.GoalId,
                GoalVersion = goalVersion ?? RelationshipConfigurationService.GetGoalVersion(goal),
                Decision = decision,
                CorrectionReason = correctionReason,
                ActorParticipantId = ParticipantId,
            }
        );
        await db.SaveChangesAsync();
    }

    public async Task AddReviewAsync(
        string recommendation,
        DateTimeOffset periodEnd,
        Func<string, PerformanceReviewDimensionV1>? dimension = null
    )
    {
        dimension ??= name => new PerformanceReviewDimensionV1("MET", name, "RECORDED");
        var skill = await Configuration.SaveSkillAsync(
            TenantId,
            RelationshipId,
            "REVIEWED_SKILL",
            "1.0.0",
            null,
            "GRANTED",
            "APPLICABLE",
            null,
            "ACCEPTED",
            CancellationToken.None
        );
        var service = new PerformanceReviewService(
            Store,
            new RecordingRelationshipConstitutionalGateway()
        );
        await service.AppendAsync(
            TenantId,
            RelationshipId,
            skill.SkillId,
            skill.SkillVersion,
            new PerformanceReviewDraftV1(
                "policy-1",
                periodEnd.AddDays(-30),
                periodEnd,
                new Dictionary<string, string> { ["execution"] = "1" },
                dimension("work"),
                dimension("quality"),
                dimension("constitutional"),
                dimension("commercial"),
                dimension("outcome"),
                dimension("assessment"),
                dimension("trust"),
                recommendation,
                Guid.NewGuid()
            ),
            CancellationToken.None
        );
    }
}
