// Implements: work-contracts/WC-095-agent-employment-lifecycle-and-dma-customer-activation.md §6.3
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063, C-076, C-079

using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Moq;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class OperationalMandateResolverTests(OwnerGatewayIdentityFixture identityFixture)
    : IClassFixture<OwnerGatewayIdentityFixture>
{
    [Fact]
    public async Task EmptyEvidenceCannotMintOrReplayAMandate()
    {
        var fixture = await CreateFixtureAsync();
        var resolver = new OperationalMandateResolver(fixture.Factory);
        var key = Guid.NewGuid();
        await Assert.ThrowsAsync<OperationalMandateUnavailableException>(() =>
            resolver.ResolveAsync(
                fixture.TenantId,
                fixture.ParticipantId,
                fixture.RelationshipId,
                key,
                Guid.Empty,
                "CUSTOMER_PROFILING",
                "Prepare the profile",
                CancellationToken.None
            )
        );
        await using (var db = fixture.Factory.CreateDbContext())
            Assert.Empty(await db.OperationalMandateSnapshots.ToListAsync());
        await resolver.ResolveAsync(
            fixture.TenantId,
            fixture.ParticipantId,
            fixture.RelationshipId,
            key,
            Guid.NewGuid(),
            "CUSTOMER_PROFILING",
            "Prepare the profile",
            CancellationToken.None
        );
        await Assert.ThrowsAsync<OperationalMandateUnavailableException>(() =>
            resolver.ResolveAsync(
                fixture.TenantId,
                fixture.ParticipantId,
                fixture.RelationshipId,
                key,
                Guid.Empty,
                "CUSTOMER_PROFILING",
                "Prepare the profile",
                CancellationToken.None
            )
        );
        await using var check = fixture.Factory.CreateDbContext();
        Assert.Single(await check.OperationalMandateSnapshots.ToListAsync());
    }

    [Fact]
    public async Task ReadinessRequiresExactPromotedBindingWithoutCreatingMandate()
    {
        var readyFixture = await CreateFixtureAsync();
        var readyResolver = new OperationalMandateResolver(readyFixture.Factory);
        var readiness = await readyResolver.GetReadinessAsync(
            readyFixture.TenantId,
            readyFixture.ParticipantId,
            readyFixture.RelationshipId,
            CancellationToken.None
        );

        Assert.True(readiness.Ready);
        Assert.Empty(readiness.BlockedReasons);
        await using (var db = readyFixture.Factory.CreateDbContext())
            Assert.Empty(await db.OperationalMandateSnapshots.ToListAsync());

        var blockedFixture = await CreateFixtureAsync(includeRuntimeBinding: false);
        var blockedResolver = new OperationalMandateResolver(blockedFixture.Factory);
        var blocked = await blockedResolver.GetReadinessAsync(
            blockedFixture.TenantId,
            blockedFixture.ParticipantId,
            blockedFixture.RelationshipId,
            CancellationToken.None
        );

        Assert.False(blocked.Ready);
        Assert.Contains(
            blocked.BlockedReasons,
            reason => reason.Contains("CUSTOMER_PROFILING", StringComparison.Ordinal)
        );
    }

    [Fact]
    public async Task ResolvesAndPersistsExactCurrentAuthorityOnce()
    {
        var fixture = await CreateFixtureAsync();
        var resolver = new OperationalMandateResolver(fixture.Factory);
        var key = Guid.NewGuid();
        var evidenceId = Guid.NewGuid();

        var first = await resolver.ResolveAsync(
            fixture.TenantId,
            fixture.ParticipantId,
            fixture.RelationshipId,
            key,
            evidenceId,
            "CUSTOMER_PROFILING",
            "Prepare the profile",
            CancellationToken.None
        );
        var replay = await resolver.ResolveAsync(
            fixture.TenantId,
            fixture.ParticipantId,
            fixture.RelationshipId,
            key,
            Guid.NewGuid(),
            "CUSTOMER_PROFILING",
            "Prepare the profile",
            CancellationToken.None
        );

        await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() =>
            resolver.ResolveAsync(
                fixture.TenantId,
                fixture.ParticipantId,
                fixture.RelationshipId,
                key,
                Guid.NewGuid(),
                "CUSTOMER_PROFILING",
                "A different purpose cannot widen replay",
                CancellationToken.None
            )
        );

        Assert.Equal(first.MandateId, replay.MandateId);
        Assert.Equal(first.MandateDigest, replay.MandateDigest);
        Assert.Equal(JsonSerializer.Serialize(first), JsonSerializer.Serialize(replay));
        Assert.Equal(first.PermittedActions, replay.PermittedActions);
        Assert.Equal(first.ApprovalRefs, replay.ApprovalRefs);
        Assert.Equal(fixture.AgentInstanceId, first.AgentInstanceId);
        Assert.Equal("CUSTOMER_PROFILING", first.SkillId);
        Assert.Equal("3.1", first.SpecificationRevision);
        Assert.Equal("sha256:" + new string('7', 64), first.PromptDigest);
        Assert.StartsWith("sha256:", first.MandateDigest);
        await using var db = fixture.Factory.CreateDbContext();
        var stored = await db.OperationalMandateSnapshots.SingleAsync();
        Assert.Equal(first.MandateId, stored.MandateId);
        Assert.Equal(first.MandateDigest, stored.MandateDigest);
        Assert.Equal(evidenceId, stored.ConstitutionalEvidenceId);
    }

    [Fact]
    public async Task LostRuntimeAcknowledgementReusesPersistedBodyAndRuntimeIdentity()
    {
        var fixture = await CreateFixtureAsync();
        var resolver = new OperationalMandateResolver(fixture.Factory);
        var key = Guid.NewGuid();
        var conversationId = Guid.NewGuid();
        var messageId = Guid.NewGuid();
        var executionId = ConversationExecutionIdentity.Create(
            fixture.TenantId,
            fixture.RelationshipId,
            fixture.ParticipantId,
            conversationId,
            key
        );
        string? originalBody = null;
        var attempts = 0;
        using var client = new HttpClient(
            new LostAcknowledgementHandler(
                async (request, token) =>
                {
                    var body = await request.Content!.ReadAsStringAsync(token);
                    attempts++;
                    if (attempts == 1)
                    {
                        originalBody = body;
                        throw new HttpRequestException(
                            "Synthetic acknowledgement lost after acceptance."
                        );
                    }
                    Assert.Equal(originalBody, body);
                    Assert.Equal(
                        key.ToString("D"),
                        request.Headers.GetValues("Idempotency-Key").Single()
                    );
                    return new HttpResponseMessage(HttpStatusCode.OK)
                    {
                        Content = JsonContent.Create(
                            new
                            {
                                schemaVersion = "1.0",
                                executionId,
                                conversationId,
                                messageId,
                                state = "ACCEPTED",
                                partial = false,
                                replayed = true,
                                acceptedAt = DateTimeOffset.UtcNow,
                            }
                        ),
                    };
                }
            )
        )
        {
            BaseAddress = new Uri("https://professional-runtime/"),
        };
        var clients = new Mock<IHttpClientFactory>();
        clients
            .Setup(value => value.CreateClient("ConversationProfessionalRuntime"))
            .Returns(client);
        using var identity = identityFixture.CreateIdentity();
        var gateway = new HttpConversationExecutionGateway(clients.Object, identity);
        var first = await resolver.ResolveAsync(
            fixture.TenantId,
            fixture.ParticipantId,
            fixture.RelationshipId,
            key,
            Guid.NewGuid(),
            "CUSTOMER_PROFILING",
            "Prepare the profile",
            CancellationToken.None
        );
        var content = new[]
        {
            new ConversationTextBlockV1("1.0", "TEXT", "Prepare the profile", "en-IN"),
        };
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            gateway.StartAsync(
                conversationId,
                executionId,
                messageId,
                fixture.RelationshipId,
                "en-IN",
                content,
                first,
                key,
                CancellationToken.None
            )
        );
        var replay = await resolver.ResolveAsync(
            fixture.TenantId,
            fixture.ParticipantId,
            fixture.RelationshipId,
            key,
            Guid.NewGuid(),
            "CUSTOMER_PROFILING",
            "Prepare the profile",
            CancellationToken.None
        );
        await gateway.StartAsync(
            conversationId,
            executionId,
            messageId,
            fixture.RelationshipId,
            "en-IN",
            content,
            replay,
            key,
            CancellationToken.None
        );
        Assert.Equal(2, attempts);
        await using var db = fixture.Factory.CreateDbContext();
        Assert.Single(await db.OperationalMandateSnapshots.ToListAsync());
    }

    private sealed class LostAcknowledgementHandler(
        Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> response
    ) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) => response(request, cancellationToken);
    }

    [Fact]
    public async Task ReplayDoesNotCreateOrRenewOriginalMandateAfterRuntimeResponseIsLost()
    {
        var fixture = await CreateFixtureAsync();
        var resolver = new OperationalMandateResolver(fixture.Factory);
        var key = Guid.NewGuid();
        var first = await resolver.ResolveAsync(
            fixture.TenantId,
            fixture.ParticipantId,
            fixture.RelationshipId,
            key,
            Guid.NewGuid(),
            "CUSTOMER_PROFILING",
            "Prepare the profile",
            CancellationToken.None
        );
        var originalBody = JsonSerializer.Serialize(first);
        for (var attempt = 0; attempt < 3; attempt++)
        {
            var replay = await resolver.ResolveAsync(
                fixture.TenantId,
                fixture.ParticipantId,
                fixture.RelationshipId,
                key,
                Guid.NewGuid(),
                "CUSTOMER_PROFILING",
                "Prepare the profile",
                CancellationToken.None
            );
            Assert.Equal(originalBody, JsonSerializer.Serialize(replay));
            Assert.Equal(first.Deadline, replay.Deadline);
        }
        await using var db = fixture.Factory.CreateDbContext();
        Assert.Single(await db.OperationalMandateSnapshots.ToListAsync());
    }

    [Theory]
    [InlineData("stop")]
    [InlineData("membership")]
    [InlineData("skill")]
    [InlineData("goal")]
    [InlineData("runtime")]
    [InlineData("decision-space")]
    [InlineData("digest")]
    [InlineData("expired")]
    [InlineData("role")]
    [InlineData("contract")]
    [InlineData("evidence")]
    [InlineData("applicability")]
    public async Task PersistedMandateReplayRechecksCurrentAuthorityWithoutRenewal(string change)
    {
        var fixture = await CreateFixtureAsync();
        var resolver = new OperationalMandateResolver(fixture.Factory);
        var key = Guid.NewGuid();
        await resolver.ResolveAsync(
            fixture.TenantId,
            fixture.ParticipantId,
            fixture.RelationshipId,
            key,
            Guid.NewGuid(),
            "CUSTOMER_PROFILING",
            "Prepare the profile",
            CancellationToken.None
        );
        await using (var db = fixture.Factory.CreateDbContext())
        {
            switch (change)
            {
                case "stop":
                    (await db.EmploymentRelationships.SingleAsync()).State =
                        EmploymentRelationshipState.StoppedEmergency;
                    break;
                case "membership":
                    (await db.RelationshipParticipants.SingleAsync()).Status = "REVOKED";
                    break;
                case "skill":
                    (await db.RelationshipSkillConfigurations.SingleAsync()).AuthorityState =
                        "DENIED";
                    break;
                case "applicability":
                    (await db.RelationshipSkillConfigurations.SingleAsync()).Applicability =
                        "NOT_APPLICABLE";
                    break;
                case "goal":
                    (await db.RelationshipGoals.SingleAsync()).Status = "INACTIVE";
                    break;
                case "runtime":
                    db.Entry(await db.AgentSkillRuntimeBindings.SingleAsync())
                        .Property(value => value.PromptDigest)
                        .CurrentValue = "sha256:" + new string('9', 64);
                    break;
                case "decision-space":
                    (await db.EmploymentRelationships.SingleAsync()).AuthoritySnapshotId =
                        Guid.NewGuid();
                    break;
                case "role":
                    db.Entry(await db.RelationshipParticipants.SingleAsync())
                        .Property(value => value.Role)
                        .CurrentValue = RelationshipParticipantRole.Evaluator;
                    break;
                case "contract":
                    (await db.EmploymentRelationships.SingleAsync()).AcceptedContractId =
                        Guid.NewGuid();
                    break;
                case "digest":
                    db.Entry(await db.OperationalMandateSnapshots.SingleAsync())
                        .Property(value => value.MandateDigest)
                        .CurrentValue = "sha256:" + new string('0', 64);
                    break;
                case "evidence":
                    db.Entry(await db.OperationalMandateSnapshots.SingleAsync())
                        .Property(value => value.ConstitutionalEvidenceId)
                        .CurrentValue = Guid.Empty;
                    break;
                case "expired":
                    var snapshot = await db.OperationalMandateSnapshots.SingleAsync();
                    var stored = JsonSerializer.Deserialize<OperationalMandateV1>(
                        snapshot.MandateJson,
                        new JsonSerializerOptions(JsonSerializerDefaults.Web)
                    )!;
                    var expired = stored with { Deadline = DateTimeOffset.UtcNow.AddMinutes(-1) };
                    db.Entry(snapshot).Property(value => value.Deadline).CurrentValue =
                        expired.Deadline;
                    db.Entry(snapshot).Property(value => value.MandateJson).CurrentValue =
                        JsonSerializer.Serialize(
                            expired,
                            new JsonSerializerOptions(JsonSerializerDefaults.Web)
                        );
                    break;
            }
            await db.SaveChangesAsync();
        }
        await Assert.ThrowsAsync<OperationalMandateUnavailableException>(() =>
            resolver.ResolveAsync(
                fixture.TenantId,
                fixture.ParticipantId,
                fixture.RelationshipId,
                key,
                Guid.NewGuid(),
                "CUSTOMER_PROFILING",
                "Prepare the profile",
                CancellationToken.None
            )
        );
        await using var check = fixture.Factory.CreateDbContext();
        Assert.Single(await check.OperationalMandateSnapshots.ToListAsync());
    }

    [Fact]
    public async Task RejectsUnpromotedSkillWithoutPersistingMandate()
    {
        var fixture = await CreateFixtureAsync(includeRuntimeBinding: false);
        var resolver = new OperationalMandateResolver(fixture.Factory);

        await Assert.ThrowsAsync<OperationalMandateUnavailableException>(() =>
            resolver.ResolveAsync(
                fixture.TenantId,
                fixture.ParticipantId,
                fixture.RelationshipId,
                Guid.NewGuid(),
                Guid.NewGuid(),
                "CUSTOMER_PROFILING",
                "Prepare the profile",
                CancellationToken.None
            )
        );

        await using var db = fixture.Factory.CreateDbContext();
        Assert.Empty(await db.OperationalMandateSnapshots.ToListAsync());
    }

    [Fact]
    public async Task DeclaredOperationIsBoundAndPersistedWithoutModelPolicyInference()
    {
        var operation = TestOperation();
        var fixture = await CreateFixtureAsync(operation: operation);
        var resolver = new OperationalMandateResolver(fixture.Factory);
        var key = Guid.NewGuid();
        var first = await resolver.ResolveAsync(
            fixture.TenantId,
            fixture.ParticipantId,
            fixture.RelationshipId,
            key,
            Guid.NewGuid(),
            "CUSTOMER_PROFILING",
            "Prepare the profile",
            CancellationToken.None
        );
        var replay = await resolver.ResolveAsync(
            fixture.TenantId,
            fixture.ParticipantId,
            fixture.RelationshipId,
            key,
            Guid.NewGuid(),
            "CUSTOMER_PROFILING",
            "Prepare the profile",
            CancellationToken.None
        );
        Assert.Equal(operation, first.ConversationOperation);
        Assert.Equal(first.MandateDigest, replay.MandateDigest);
        Assert.Equal(JsonSerializer.Serialize(first), JsonSerializer.Serialize(replay));
        Assert.NotEqual(first.SpecificationDigest, first.ConversationOperation!.ModelPolicy.Digest);
    }

    [Theory]
    [InlineData("action")]
    [InlineData("input")]
    [InlineData("output")]
    [InlineData("prompt")]
    public async Task OperationDriftCannotMintAMandate(string coordinate)
    {
        var operation = TestOperation();
        operation = coordinate switch
        {
            "action" => operation with { GovernedAction = "UNDECLARED_ACTION" },
            "input" => operation with { InputSchemaDigest = "sha256:" + new string('a', 64) },
            "output" => operation with { OutputSchemaDigest = "sha256:" + new string('a', 64) },
            _ => operation with
            {
                PromptPolicy = operation.PromptPolicy with { Version = "2.0.0" },
            },
        };
        var fixture = await CreateFixtureAsync(operation: operation);
        await Assert.ThrowsAsync<OperationalMandateUnavailableException>(() =>
            new OperationalMandateResolver(fixture.Factory).ResolveAsync(
                fixture.TenantId,
                fixture.ParticipantId,
                fixture.RelationshipId,
                Guid.NewGuid(),
                Guid.NewGuid(),
                "CUSTOMER_PROFILING",
                "Prepare the profile",
                CancellationToken.None
            )
        );
        await using var db = fixture.Factory.CreateDbContext();
        Assert.Empty(await db.OperationalMandateSnapshots.ToListAsync());
    }

    [Fact]
    public async Task LegacyMandateOmitsOperationInsteadOfInventingOne()
    {
        var fixture = await CreateFixtureAsync();
        var result = await new OperationalMandateResolver(fixture.Factory).ResolveAsync(
            fixture.TenantId,
            fixture.ParticipantId,
            fixture.RelationshipId,
            Guid.NewGuid(),
            Guid.NewGuid(),
            "CUSTOMER_PROFILING",
            "Prepare the profile",
            CancellationToken.None
        );
        Assert.Null(result.ConversationOperation);
        var json = JsonSerializer.Serialize(
            result,
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );
        Assert.DoesNotContain("conversationOperation", json, StringComparison.Ordinal);
    }

    private static ConversationOperationBindingV1 TestOperation() =>
        new(
            "PROFESSIONAL_RESPONSE",
            "PRESENT_PROFILE_PROPOSAL",
            "sha256:" + new string('5', 64),
            "sha256:" + new string('6', 64),
            new("prompt:synthetic", "1.0.0", "sha256:" + new string('7', 64)),
            new("model-policy:synthetic", "1.0.0", "sha256:" + new string('9', 64))
        );

    internal static async Task<Fixture> CreateFixtureAsync(
        bool includeRuntimeBinding = true,
        ConversationOperationBindingV1? operation = null,
        IDbContextFactory<EmploymentRelationshipDbContext>? database = null
    )
    {
        var factory =
            database ?? new InMemoryEmploymentRelationshipFactory($"mandate-{Guid.NewGuid():N}");
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var agentInstanceId = Guid.NewGuid();
        var admissionId = Guid.NewGuid();
        var goalId = Guid.NewGuid();
        var authorityId = Guid.NewGuid();
        var contractId = Guid.NewGuid();
        await using var db = factory.CreateDbContext();
        db.EmploymentRelationships.Add(
            new EmploymentRelationship
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                AgentInstanceId = agentInstanceId,
                ProfessionalAdmissionId = admissionId,
                ProfessionalType = "DIGITAL_MARKETING_LOCAL_SERVICE",
                ProfessionalVersion = "1.0.0",
                EvaluationIntentId = Guid.NewGuid(),
                InitiatingParticipantId = participantId,
                State = EmploymentRelationshipState.Active,
                AuthoritySnapshotId = authorityId,
                AcceptedContractId = contractId,
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
        db.AgentAdmissions.Add(
            new AgentAdmission
            {
                TenantId = tenantId,
                AdmissionId = admissionId,
                ProfessionalTypeId = "DIGITAL_MARKETING_LOCAL_SERVICE",
                ProfessionalVersion = "1.0.0",
                OwnerSubjectId = Guid.NewGuid(),
                State = AgentAdmissionState.Active,
                CurrentRevision = 1,
                AdmissionContentDigest = "sha256:" + new string('3', 64),
                ArtifactDigest = "sha256:" + new string('4', 64),
            }
        );
        var admissionJson = AdmissionJson();
        if (operation is not null)
        {
            var root = JsonNode.Parse(admissionJson)!;
            root["skillManifest"]![0]!["conversationOperation"] = JsonSerializer.SerializeToNode(
                operation,
                new JsonSerializerOptions(JsonSerializerDefaults.Web)
            );
            admissionJson = root.ToJsonString();
        }
        db.AgentAdmissionRevisions.Add(
            new AgentAdmissionRevision
            {
                TenantId = tenantId,
                AdmissionId = admissionId,
                Revision = 1,
                ContractSchemaVersion = "1.0.0",
                AdmissionContentDigest = "sha256:" + new string('3', 64),
                AdmissionContentJson = admissionJson,
                ActorSubjectId = Guid.NewGuid(),
            }
        );
        if (includeRuntimeBinding)
        {
            db.AgentSkillRuntimeBindings.Add(
                new AgentSkillRuntimeBinding
                {
                    TenantId = tenantId,
                    AdmissionId = admissionId,
                    SkillId = "CUSTOMER_PROFILING",
                    SkillVersion = "1.0.0",
                    ReleaseSequence = 1,
                    SpecificationRevision = "3.1",
                    SpecificationDigest = "sha256:" + new string('2', 64),
                    PromptVersion = "1.0.0",
                    PromptDigest = "sha256:" + new string('7', 64),
                    InputSchemaDigest = "sha256:" + new string('5', 64),
                    OutputSchemaDigest = "sha256:" + new string('6', 64),
                }
            );
        }
        db.RelationshipSkillConfigurations.Add(
            new RelationshipSkillConfiguration
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                SkillId = "CUSTOMER_PROFILING",
                SkillVersion = "1.0.0",
                GoalId = goalId,
                AuthorityState = "GRANTED",
                Status = "ACCEPTED",
            }
        );
        db.RelationshipSkillDecisions.Add(
            new RelationshipSkillDecision
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ConfigurationId = db.RelationshipSkillConfigurations.Local.Single().ConfigurationId,
                SkillId = "CUSTOMER_PROFILING",
                SkillVersion = "1.0.0",
                Decision = "ACCEPTED",
                ActorParticipantId = participantId,
                ExpectedWorkspaceVersion = "1",
                ExpectedSubjectVersion = "1",
                IdempotencyKey = Guid.NewGuid(),
                MaterialRequestHash = new string('a', 64),
                EvidenceId = Guid.NewGuid(),
            }
        );
        db.RelationshipGoals.Add(
            new RelationshipGoal
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                GoalId = goalId,
                Goal = "Confirm customer profile",
                Measure = "confirmed fields",
                Status = "ACTIVE",
            }
        );
        db.RelationshipGoalDecisions.Add(
            new RelationshipGoalDecision
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                GoalId = goalId,
                GoalVersion = "1",
                SkillId = "CUSTOMER_PROFILING",
                SkillVersion = "1.0.0",
                Measure = "confirmed fields",
                ReviewCadenceMonths = 1,
                Decision = "VERIFIED",
                ActorParticipantId = participantId,
                ExpectedWorkspaceVersion = "1",
                ExpectedSubjectVersion = "1",
                IdempotencyKey = Guid.NewGuid(),
                MaterialRequestHash = new string('b', 64),
                EvidenceId = Guid.NewGuid(),
            }
        );
        db.ContextConfirmationEvents.Add(
            new ContextConfirmationEvent
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                PayloadReference = Guid.NewGuid(),
                PayloadHash = new string('c', 64),
                FieldType = "BUSINESS_PROFILE",
                Action = "CONFIRMED",
                ActorParticipantId = participantId,
                CorrelationId = Guid.NewGuid(),
                EvidenceId = Guid.NewGuid(),
            }
        );
        db.DecisionSpaceSnapshots.Add(
            new DecisionSpaceSnapshot
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                SnapshotId = authorityId,
                Version = 1,
                BudgetCeilingInrPaise = 1000,
                CreatedByParticipantId = participantId,
                EvidenceId = Guid.NewGuid(),
            }
        );
        db.EmploymentContractVersions.Add(
            new EmploymentContractVersion
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ContractId = contractId,
                Version = 1,
                ContractHash = new string('d', 64),
                CreatedByParticipantId = participantId,
            }
        );
        db.ContractAcceptances.Add(
            new ContractAcceptance
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ContractId = contractId,
                ContractVersion = 1,
                ContractHash = new string('d', 64),
                ParticipantId = participantId,
                ParticipantRole = RelationshipParticipantRole.Employer,
                AuthenticationAssurance = "AAL2",
                AuthoritySnapshotId = authorityId,
                ScopeConfirmationHash = new string('e', 64),
                AcceptanceEvidenceId = Guid.NewGuid(),
            }
        );
        await db.SaveChangesAsync();
        return new Fixture(factory, tenantId, participantId, relationshipId, agentInstanceId);
    }

    private static string AdmissionJson() =>
        """
            {
              "professionalIdentity":{"professionalTypeId":"DIGITAL_MARKETING_LOCAL_SERVICE","professionalVersion":"1.0.0"},
              "complianceDeclaration":{
                "agentBaseSpec":{"version":"1.0"},
                "constitutionalDna":{"version":"2.0"},
                "platformAgentContract":{"schemaVersion":"1.0.0"}
              },
              "runtimeAdapter":{"protocolVersion":"1.0.0"},
              "skillManifest":[{"skillId":"CUSTOMER_PROFILING","skillVersion":"1.0.0","constitutionalActions":["PRESENT_PROFILE_PROPOSAL"]}]
            }
            """;

    internal sealed record Fixture(
        IDbContextFactory<EmploymentRelationshipDbContext> Factory,
        Guid TenantId,
        Guid ParticipantId,
        Guid RelationshipId,
        Guid AgentInstanceId
    );
}
