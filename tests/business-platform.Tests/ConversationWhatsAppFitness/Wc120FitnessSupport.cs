using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

internal sealed class ConversationFitnessDbFactory(string databaseName)
    : IDbContextFactory<ConversationStoreDbContext>
{
    private readonly DbContextOptions<ConversationStoreDbContext> _options =
        new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseInMemoryDatabase(databaseName)
            .ConfigureWarnings(value => value.Ignore(InMemoryEventId.TransactionIgnoredWarning))
            .Options;

    public ConversationStoreDbContext CreateDbContext() => new(_options);
}

internal sealed class RelationshipFitnessDbFactory(string databaseName)
    : IDbContextFactory<EmploymentRelationshipDbContext>
{
    private readonly DbContextOptions<EmploymentRelationshipDbContext> _options =
        new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
            .UseInMemoryDatabase(databaseName)
            .Options;

    public EmploymentRelationshipDbContext CreateDbContext() => new(_options);
}

internal sealed class PayloadFitnessDbFactory(string databaseName)
    : IDbContextFactory<PayloadStoreDbContext>
{
    private readonly DbContextOptions<PayloadStoreDbContext> _options =
        new DbContextOptionsBuilder<PayloadStoreDbContext>()
            .UseInMemoryDatabase(databaseName)
            .Options;

    public PayloadStoreDbContext CreateDbContext() => new(_options);
}

internal sealed class StaticOptionsMonitor<T>(T value) : IOptionsMonitor<T>
{
    public T CurrentValue => value;

    public T Get(string? name) => value;

    public IDisposable? OnChange(Action<T, string?> listener) => null;
}

internal sealed class Wc120FitnessContext
{
    private Wc120FitnessContext(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        ConversationFitnessDbFactory conversations,
        RelationshipFitnessDbFactory relationships,
        PayloadFitnessDbFactory payloads,
        Wc120ConversationOptions options,
        ConversationalEmploymentService employment,
        ConversationContextProfileService profiles
    )
    {
        TenantId = tenantId;
        ParticipantId = participantId;
        RelationshipId = relationshipId;
        Conversations = conversations;
        Relationships = relationships;
        Payloads = payloads;
        Options = options;
        Employment = employment;
        Profiles = profiles;
        StopFence = new(conversations, Microsoft.Extensions.Options.Options.Create(options));
    }

    public Guid TenantId { get; }
    public Guid ParticipantId { get; }
    public Guid RelationshipId { get; }
    public ConversationFitnessDbFactory Conversations { get; }
    public RelationshipFitnessDbFactory Relationships { get; }
    public PayloadFitnessDbFactory Payloads { get; }
    public Wc120ConversationOptions Options { get; }
    public ConversationalEmploymentService Employment { get; }
    public ConversationContextProfileService Profiles { get; }
    public ConversationStopFence StopFence { get; }

    public static async Task<Wc120FitnessContext> CreateAsync(
        string workspaceVersion = "workspace-1"
    )
    {
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var suffix = Guid.NewGuid().ToString("N");
        var conversations = new ConversationFitnessDbFactory($"wc120-conversations-{suffix}");
        var relationships = new RelationshipFitnessDbFactory($"wc120-relationships-{suffix}");
        var payloads = new PayloadFitnessDbFactory($"wc120-payloads-{suffix}");
        var options = new Wc120ConversationOptions
        {
            Enabled = true,
            CallbackAcceptanceEnabled = true,
            DispatchEnabled = true,
            Environment = "test",
            AppBindingDigest = new string('a', 64),
            WabaBindingDigest = new string('b', 64),
            RecipientBindingDigest = new string('c', 64),
            PolicyVersion = "policy-1",
            InstitutionalPolicyVersion = "constitution-1",
            InteractionPolicyVersion = "interaction-1",
            ChannelRenderingPolicyVersion = "rendering-1",
            CustomerCommunicationProfileVersion = "communication-1",
            VocabularyPolicyVersion = "vocabulary-1",
            LocaleAccessibilityPolicyVersion = "accessibility-1",
        };
        await using (var db = relationships.CreateDbContext())
        {
            db.EmploymentRelationships.Add(
                new EmploymentRelationship
                {
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    AgentInstanceId = Guid.NewGuid(),
                    ProfessionalType = "neutral-professional",
                    ProfessionalVersion = "1.0.0",
                    State = EmploymentRelationshipState.Active,
                    AuthoritySnapshotId = Guid.NewGuid(),
                }
            );
            db.RelationshipParticipants.Add(
                new RelationshipParticipant
                {
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    ParticipantId = participantId,
                    Role = RelationshipParticipantRole.Employer,
                    BoundEvidenceId = Guid.NewGuid(),
                }
            );
            await db.SaveChangesAsync();
        }

        var employment = new ConversationalEmploymentService();
        employment.RegisterWorkspace(Workspace(tenantId, relationshipId, workspaceVersion));
        var profiles = new ConversationContextProfileService(
            conversations,
            relationships,
            employment,
            Microsoft.Extensions.Options.Options.Create(options)
        );
        return new(
            tenantId,
            participantId,
            relationshipId,
            conversations,
            relationships,
            payloads,
            options,
            employment,
            profiles
        );
    }

    public async Task<Guid> SeedConversationAsync(params (string Channel, string Text)[] messages)
    {
        var conversationId = Guid.NewGuid();
        await using var db = Conversations.CreateDbContext();
        db.Conversations.Add(
            new ConversationProjection
            {
                ConversationId = conversationId,
                Environment = Options.Environment,
                TenantId = TenantId,
                RelationshipId = RelationshipId,
                NextMessageSequence = messages.Length + 1,
            }
        );
        var sequence = 1L;
        foreach (var message in messages)
        {
            var references = await Profiles.ResolveAsync(
                TenantId,
                ParticipantId,
                RelationshipId,
                conversationId,
                "INDUCTION",
                "workspace-1",
                message.Channel,
                CancellationToken.None
            );
            db.Messages.Add(
                new ConversationMessage
                {
                    Environment = Options.Environment,
                    TenantId = TenantId,
                    RelationshipId = RelationshipId,
                    ConversationId = conversationId,
                    Sequence = sequence++,
                    Channel = message.Channel,
                    SkillId = "INDUCTION",
                    ContentJson = JsonSerializer.Serialize(
                        new[] { new ConversationTextBlockV1("1.0", "TEXT", message.Text, "en-IN") }
                    ),
                    InteractionContextJson = JsonSerializer.Serialize(references.Context),
                    ConversationPolicyJson = JsonSerializer.Serialize(references.Policy),
                }
            );
        }
        await db.SaveChangesAsync();
        return conversationId;
    }

    public ConversationOutboundContributionService Outbound() =>
        new(
            Conversations,
            Profiles,
            StopFence,
            Microsoft.Extensions.Options.Options.Create(Options)
        );

    public WhatsAppOutboxService Outbox(WhatsAppJourneyOptions? journey = null) =>
        new(
            Conversations,
            Relationships,
            Microsoft.Extensions.Options.Options.Create(Options),
            new StaticOptionsMonitor<WhatsAppJourneyOptions>(
                journey
                    ?? new WhatsAppJourneyOptions
                    {
                        CallbackAcceptanceEnabled = true,
                        DispatchEnabled = true,
                    }
            ),
            StopFence
        );

    private static EmploymentWorkspaceSnapshot Workspace(
        Guid tenantId,
        Guid relationshipId,
        string workspaceVersion
    )
    {
        var source = JsonSerializer.SerializeToElement(
            new
            {
                owner = "BP",
                contractVersion = "1.0.0-candidate.2",
                sourceVersion = workspaceVersion,
                state = "UNKNOWN",
                observedAt = DateTimeOffset.UtcNow,
                validUntil = DateTimeOffset.UtcNow.AddMinutes(5),
                limitation = "Owner validation remains pending.",
            }
        );
        static JsonElement Phase(string phase, JsonElement source) =>
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
        var workspace = JsonSerializer.SerializeToElement(
            new
            {
                schemaVersion = "1.0",
                protocolVersion = "1.0-candidate",
                relationshipId,
                workspaceVersion,
                agentType = "neutral-professional",
                agentVersion = "1.0.0",
                manifestVersion = "manifest-1",
                readiness,
                phases = phases.Values,
                currentPlan = (object?)null,
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
        return new(
            tenantId,
            relationshipId,
            workspaceVersion,
            "manifest-1",
            workspace,
            phases,
            readiness,
            new Dictionary<string, JsonElement>(),
            null,
            1,
            "wbe-1"
        );
    }
}
