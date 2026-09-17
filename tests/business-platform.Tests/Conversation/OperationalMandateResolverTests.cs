// Implements: work-contracts/WC-095-agent-employment-lifecycle-and-dma-customer-activation.md §6.3
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063, C-076, C-079

using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class OperationalMandateResolverTests
{
    [Fact]
    public async Task ReadinessRequiresExactPromotedBindingWithoutCreatingMandate()
    {
        var readyFixture = await CreateFixtureAsync();
        var readyResolver = new OperationalMandateResolver(readyFixture.Factory);
        var readiness = await readyResolver.GetReadinessAsync(
            readyFixture.TenantId, readyFixture.ParticipantId, readyFixture.RelationshipId,
            CancellationToken.None);

        Assert.True(readiness.Ready);
        Assert.Empty(readiness.BlockedReasons);
        await using (var db = readyFixture.Factory.CreateDbContext())
            Assert.Empty(await db.OperationalMandateSnapshots.ToListAsync());

        var blockedFixture = await CreateFixtureAsync(includeRuntimeBinding: false);
        var blockedResolver = new OperationalMandateResolver(blockedFixture.Factory);
        var blocked = await blockedResolver.GetReadinessAsync(
            blockedFixture.TenantId, blockedFixture.ParticipantId, blockedFixture.RelationshipId,
            CancellationToken.None);

        Assert.False(blocked.Ready);
        Assert.Contains(blocked.BlockedReasons,
            reason => reason.Contains("CUSTOMER_PROFILING", StringComparison.Ordinal));
    }

    [Fact]
    public async Task ResolvesAndPersistsExactCurrentAuthorityOnce()
    {
        var fixture = await CreateFixtureAsync();
        var resolver = new OperationalMandateResolver(fixture.Factory);
        var key = Guid.NewGuid();
        var evidenceId = Guid.NewGuid();

        var first = await resolver.ResolveAsync(
            fixture.TenantId, fixture.ParticipantId, fixture.RelationshipId, key, evidenceId,
            "CUSTOMER_PROFILING", "Prepare the profile", CancellationToken.None);
        var replay = await resolver.ResolveAsync(
            fixture.TenantId, fixture.ParticipantId, fixture.RelationshipId, key, Guid.NewGuid(),
            "CUSTOMER_PROFILING", "Prepare the profile", CancellationToken.None);

        await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() => resolver.ResolveAsync(
            fixture.TenantId, fixture.ParticipantId, fixture.RelationshipId, key, Guid.NewGuid(),
            "CUSTOMER_PROFILING", "A different purpose cannot widen replay", CancellationToken.None));

        Assert.Equal(first.MandateId, replay.MandateId);
        Assert.Equal(first.MandateDigest, replay.MandateDigest);
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
    public async Task RejectsUnpromotedSkillWithoutPersistingMandate()
    {
        var fixture = await CreateFixtureAsync(includeRuntimeBinding: false);
        var resolver = new OperationalMandateResolver(fixture.Factory);

        await Assert.ThrowsAsync<OperationalMandateUnavailableException>(() => resolver.ResolveAsync(
            fixture.TenantId, fixture.ParticipantId, fixture.RelationshipId, Guid.NewGuid(), Guid.NewGuid(),
            "CUSTOMER_PROFILING", "Prepare the profile", CancellationToken.None));

        await using var db = fixture.Factory.CreateDbContext();
        Assert.Empty(await db.OperationalMandateSnapshots.ToListAsync());
    }

    private static async Task<Fixture> CreateFixtureAsync(bool includeRuntimeBinding = true)
    {
        var factory = new InMemoryEmploymentRelationshipFactory($"mandate-{Guid.NewGuid():N}");
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var agentInstanceId = Guid.NewGuid();
        var admissionId = Guid.NewGuid();
        var goalId = Guid.NewGuid();
        var authorityId = Guid.NewGuid();
        var contractId = Guid.NewGuid();
        await using var db = factory.CreateDbContext();
        db.EmploymentRelationships.Add(new EmploymentRelationship
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
        });
        db.RelationshipParticipants.Add(new RelationshipParticipant
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ParticipantId = participantId,
            Role = RelationshipParticipantRole.Employer,
            BoundEvidenceId = Guid.NewGuid(),
        });
        db.AgentAdmissions.Add(new AgentAdmission
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
        });
        db.AgentAdmissionRevisions.Add(new AgentAdmissionRevision
        {
            TenantId = tenantId,
            AdmissionId = admissionId,
            Revision = 1,
            ContractSchemaVersion = "1.0.0",
            AdmissionContentDigest = "sha256:" + new string('3', 64),
            AdmissionContentJson = AdmissionJson(),
            ActorSubjectId = Guid.NewGuid(),
        });
        if (includeRuntimeBinding)
        {
            db.AgentSkillRuntimeBindings.Add(new AgentSkillRuntimeBinding
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
            });
        }
        db.RelationshipSkillConfigurations.Add(new RelationshipSkillConfiguration
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            SkillId = "CUSTOMER_PROFILING",
            SkillVersion = "1.0.0",
            GoalId = goalId,
            AuthorityState = "GRANTED",
            Status = "ACCEPTED",
        });
        db.RelationshipSkillDecisions.Add(new RelationshipSkillDecision
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
        });
        db.RelationshipGoals.Add(new RelationshipGoal
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            GoalId = goalId,
            Goal = "Confirm customer profile",
            Measure = "confirmed fields",
            Status = "ACTIVE",
        });
        db.RelationshipGoalDecisions.Add(new RelationshipGoalDecision
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
        });
        db.ContextConfirmationEvents.Add(new ContextConfirmationEvent
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
        });
        db.DecisionSpaceSnapshots.Add(new DecisionSpaceSnapshot
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            SnapshotId = authorityId,
            Version = 1,
            BudgetCeilingInrPaise = 1000,
            CreatedByParticipantId = participantId,
            EvidenceId = Guid.NewGuid(),
        });
        db.ContractAcceptances.Add(new ContractAcceptance
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
        });
        await db.SaveChangesAsync();
        return new Fixture(factory, tenantId, participantId, relationshipId, agentInstanceId);
    }

    private static string AdmissionJson() => """
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

    private sealed record Fixture(
        InMemoryEmploymentRelationshipFactory Factory,
        Guid TenantId,
        Guid ParticipantId,
        Guid RelationshipId,
        Guid AgentInstanceId);
}
