// Implements: WC-121 Component 01 direct evidence
// constitutional_basis: C-001, C-005, C-007, C-023, C-026, C-059, C-063

using System.Text.Json;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Tests.Conversation;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class CustomerEngagementWorkspaceServiceTests
{
    [Fact]
    public async Task PreferencesUseOptimisticVersionAndDoNotChangeRelationshipAuthority()
    {
        var fixture = await CreateAsync();

        var first = await fixture.Service.ReplacePreferencesAsync(
            fixture.TenantId,
            fixture.ParticipantId,
            fixture.RelationshipId,
            0,
            "OPERATIONS",
            false,
            CancellationToken.None
        );

        Assert.Equal(1, first.PreferenceVersion);
        Assert.Equal("OPERATIONS", first.DefaultFocus);
        await Assert.ThrowsAsync<CustomerEngagementVersionConflictException>(() =>
            fixture.Service.ReplacePreferencesAsync(
                fixture.TenantId,
                fixture.ParticipantId,
                fixture.RelationshipId,
                0,
                "RIGHTS",
                true,
                CancellationToken.None
            )
        );
        await using var db = fixture.Factory.CreateDbContext();
        var relationship = await db.EmploymentRelationships.SingleAsync();
        Assert.Equal(EmploymentRelationshipState.Active, relationship.State);
        Assert.Equal(3, relationship.StateVersion);
    }

    public sealed class CustomerEngagementAdmissionServiceTests
    {
        [Fact]
        public async Task CompleteOutcomeReplaysWithoutDuplicateRelationshipOrConversation()
        {
            var fixture = await CreateAsync();

            var first = await fixture.Service.AdmitAsync(
                fixture.TenantId,
                fixture.ParticipantId,
                fixture.ClientIntentId,
                fixture.IdempotencyKey,
                fixture.RequestHash,
                "TRIAL",
                "DMA",
                fixture.AdmissionId,
                "1.0.0",
                "disclosure-1",
                Guid.NewGuid(),
                CancellationToken.None
            );
            var replay = await fixture.Service.AdmitAsync(
                fixture.TenantId,
                fixture.ParticipantId,
                fixture.ClientIntentId,
                fixture.IdempotencyKey,
                fixture.RequestHash,
                "TRIAL",
                "DMA",
                fixture.AdmissionId,
                "1.0.0",
                "disclosure-1",
                Guid.NewGuid(),
                CancellationToken.None
            );

            Assert.False(first.Replayed);
            Assert.True(replay.Replayed);
            Assert.Equal(first.RelationshipId, replay.RelationshipId);
            Assert.Equal(first.AgentInstanceId, replay.AgentInstanceId);
            Assert.Equal(first.ConversationId, replay.ConversationId);
            Assert.Equal(first.EvidenceRef, replay.EvidenceRef);
            await using var relationshipDb = fixture.RelationshipFactory.CreateDbContext();
            Assert.Equal(1, await relationshipDb.EmploymentRelationships.CountAsync());
            Assert.Equal(
                "SUCCEEDED",
                (await relationshipDb.CustomerEngagementAdmissionOperations.SingleAsync()).State
            );
            await using var conversationDb = fixture.ConversationFactory.CreateDbContext();
            Assert.Equal(1, await conversationDb.Conversations.CountAsync());
        }

        [Fact]
        public async Task DivergentReplayIsRejectedBeforeAdditionalEffects()
        {
            var fixture = await CreateAsync();
            await fixture.Service.AdmitAsync(
                fixture.TenantId,
                fixture.ParticipantId,
                fixture.ClientIntentId,
                fixture.IdempotencyKey,
                fixture.RequestHash,
                "HIRE",
                "DMA",
                fixture.AdmissionId,
                "1.0.0",
                "disclosure-1",
                Guid.NewGuid(),
                CancellationToken.None
            );

            await Assert.ThrowsAsync<CustomerEngagementAdmissionConflictException>(() =>
                fixture.Service.AdmitAsync(
                    fixture.TenantId,
                    fixture.ParticipantId,
                    fixture.ClientIntentId,
                    fixture.IdempotencyKey,
                    "different-material-hash",
                    "HIRE",
                    "DMA",
                    fixture.AdmissionId,
                    "1.0.0",
                    "disclosure-2",
                    Guid.NewGuid(),
                    CancellationToken.None
                )
            );
            await using var relationshipDb = fixture.RelationshipFactory.CreateDbContext();
            Assert.Equal(1, await relationshipDb.EmploymentRelationships.CountAsync());
        }

        [Fact]
        public async Task InterruptedAdmissionRemainsExplicitAndRecoversWithReservedIdentity()
        {
            var fixture = await CreateAsync();
            fixture.Gateway.FailNext = true;

            await Assert.ThrowsAsync<InvalidOperationException>(() =>
                fixture.Service.AdmitAsync(
                    fixture.TenantId,
                    fixture.ParticipantId,
                    fixture.ClientIntentId,
                    fixture.IdempotencyKey,
                    fixture.RequestHash,
                    "TRIAL",
                    "DMA",
                    fixture.AdmissionId,
                    "1.0.0",
                    "disclosure-1",
                    Guid.NewGuid(),
                    CancellationToken.None
                )
            );
            Guid reservedRelationshipId;
            await using (var failedDb = fixture.RelationshipFactory.CreateDbContext())
            {
                var failed = await failedDb.CustomerEngagementAdmissionOperations.SingleAsync();
                Assert.Equal("RECONCILE_REQUIRED", failed.State);
                Assert.Empty(await failedDb.EmploymentRelationships.ToListAsync());
                reservedRelationshipId = failed.RelationshipId;
            }

            var recovered = await fixture.Service.AdmitAsync(
                fixture.TenantId,
                fixture.ParticipantId,
                fixture.ClientIntentId,
                fixture.IdempotencyKey,
                fixture.RequestHash,
                "TRIAL",
                "DMA",
                fixture.AdmissionId,
                "1.0.0",
                "disclosure-1",
                Guid.NewGuid(),
                CancellationToken.None
            );

            Assert.Equal(reservedRelationshipId, recovered.RelationshipId);
            await using var recoveredDb = fixture.RelationshipFactory.CreateDbContext();
            Assert.Equal(
                "SUCCEEDED",
                (await recoveredDb.CustomerEngagementAdmissionOperations.SingleAsync()).State
            );
            Assert.Single(await recoveredDb.EmploymentRelationships.ToListAsync());
        }

        private static async Task<AdmissionFixture> CreateAsync()
        {
            var suffix = Guid.NewGuid().ToString("N");
            var relationshipFactory = new InMemoryEmploymentRelationshipFactory(
                $"admission-{suffix}"
            );
            var conversationFactory = new InMemoryConversationFactory($"conversation-{suffix}");
            var relationshipGateway = new RecordingRelationshipConstitutionalGateway();
            var relationshipService = new EmploymentRelationshipService(
                relationshipFactory,
                relationshipGateway,
                NullLogger<EmploymentRelationshipService>.Instance
            );
            var conversationService = new ConversationService(
                conversationFactory,
                relationshipFactory,
                new ConversationConstitutionalGatewayStub(),
                new ConversationExecutionGatewayStub(),
                new OperationalMandateResolverStub(),
                new ConversationCursorCodec(
                    Options.Create(
                        new ConversationCursorOptions
                        {
                            HmacKey = "wc121-admission-test-key-at-least-32-characters", // gitleaks:allow
                        }
                    )
                )
            );
            var workspaceService = new CustomerEngagementWorkspaceService(
                relationshipFactory,
                new EphemeralDataProtectionProvider(),
                relationshipGateway
            );
            var service = new CustomerEngagementAdmissionService(
                relationshipFactory,
                relationshipService,
                conversationService,
                workspaceService
            );
            var tenantId = Guid.NewGuid();
            var participantId = Guid.NewGuid();
            var admissionId = Guid.NewGuid();
            await using (var db = relationshipFactory.CreateDbContext())
            {
                db.AgentAdmissions.Add(
                    new AgentAdmission
                    {
                        AdmissionId = admissionId,
                        TenantId = tenantId,
                        ProfessionalTypeId = "DMA",
                        ProfessionalVersion = "1.0.0",
                        OwnerSubjectId = Guid.NewGuid(),
                        State = AgentAdmissionState.Active,
                    }
                );
                await db.SaveChangesAsync();
            }
            return new(
                relationshipFactory,
                conversationFactory,
                relationshipGateway,
                service,
                tenantId,
                participantId,
                admissionId,
                Guid.NewGuid(),
                "customer-admission-idempotency-0001",
                "stable-material-request-hash"
            );
        }

        private sealed record AdmissionFixture(
            InMemoryEmploymentRelationshipFactory RelationshipFactory,
            InMemoryConversationFactory ConversationFactory,
            RecordingRelationshipConstitutionalGateway Gateway,
            CustomerEngagementAdmissionService Service,
            Guid TenantId,
            Guid ParticipantId,
            Guid AdmissionId,
            Guid ClientIntentId,
            string IdempotencyKey,
            string RequestHash
        );
    }

    [Fact]
    public async Task ProgressCarriesTruthAndProvenanceAndFocusReauthorizesCurrentState()
    {
        var fixture = await CreateAsync();

        var progress = await fixture.Service.GetProgressAsync(
            fixture.TenantId,
            fixture.ParticipantId,
            fixture.RelationshipId,
            CancellationToken.None
        );

        var item = Assert.Single(progress.Items);
        Assert.Equal("OPERATIONS", progress.LifecycleStage);
        Assert.Equal("WORKING", item.Truth.Processing);
        Assert.Equal("COMPLETED", item.Truth.Evidence);
        Assert.Equal("RECORDED", item.Provenance.EvidenceState);
        Assert.Equal("RELATIONSHIP", item.Provenance.SourceOwner);
        Assert.False(string.IsNullOrWhiteSpace(progress.ProjectionVersion));
        var focus = Assert.Single(progress.AvailableFocuses);
        var resolved = await fixture.Service.ResolveFocusAsync(
            fixture.TenantId,
            fixture.ParticipantId,
            fixture.RelationshipId,
            focus.FocusToken,
            CancellationToken.None
        );
        Assert.Equal("OPERATION", resolved.Destination);
        Assert.DoesNotContain(focus.FocusToken, resolved.CanonicalRoute);

        await using (var db = fixture.Factory.CreateDbContext())
        {
            var relationship = await db.EmploymentRelationships.SingleAsync();
            relationship.StateVersion += 1;
            await db.SaveChangesAsync();
        }
        await Assert.ThrowsAsync<CustomerEngagementFocusConflictException>(() =>
            fixture.Service.ResolveFocusAsync(
                fixture.TenantId,
                fixture.ParticipantId,
                fixture.RelationshipId,
                focus.FocusToken,
                CancellationToken.None
            )
        );
    }

    [Theory]
    [InlineData("CONVERSATION", "#conversation")]
    [InlineData("INDUCTION", "#induction")]
    [InlineData("SKILLS_GOALS", "#skills-and-goals")]
    [InlineData("PERFORMANCE", "#performance")]
    [InlineData("BUDGET", "#usage-and-budget")]
    [InlineData("RIGHTS", "#rights-and-control")]
    [InlineData("UNKNOWN", "#lifecycle")]
    public async Task FocusResolutionMapsCanonicalDestinationRoutes(
        string destination,
        string routeSuffix
    )
    {
        var fixture = await CreateAsync();
        var protector = fixture.DataProtectionProvider.CreateProtector(
            "WAOOAW.CustomerEngagementWorkspace.Focus.v1"
        );
        var token = protector.Protect(
            JsonSerializer.Serialize(
                new
                {
                    TokenId = Guid.NewGuid(),
                    fixture.TenantId,
                    fixture.ParticipantId,
                    fixture.RelationshipId,
                    AuthorityVersion = 3,
                    Destination = destination,
                    SubjectRef = $"relationship:{fixture.RelationshipId:D}",
                    SubjectVersion = "relationship-3",
                    IssuedAt = DateTimeOffset.UtcNow,
                    ExpiresAt = DateTimeOffset.UtcNow.AddMinutes(5),
                }
            )
        );

        var resolved = await fixture.Service.ResolveFocusAsync(
            fixture.TenantId,
            fixture.ParticipantId,
            fixture.RelationshipId,
            token,
            CancellationToken.None
        );

        Assert.Equal(destination, resolved.Destination);
        Assert.EndsWith(routeSuffix, resolved.CanonicalRoute, StringComparison.Ordinal);
    }

    [Fact]
    public async Task FocusResolutionRejectsCrossScopeAndExpiredPayloads()
    {
        var fixture = await CreateAsync();
        var protector = fixture.DataProtectionProvider.CreateProtector(
            "WAOOAW.CustomerEngagementWorkspace.Focus.v1"
        );
        string CreateToken(Guid tenantId, DateTimeOffset expiresAt)
        {
            return protector.Protect(
                JsonSerializer.Serialize(
                    new
                    {
                        TokenId = Guid.NewGuid(),
                        TenantId = tenantId,
                        fixture.ParticipantId,
                        fixture.RelationshipId,
                        AuthorityVersion = 3,
                        Destination = "OPERATION",
                        SubjectRef = $"relationship:{fixture.RelationshipId:D}",
                        SubjectVersion = "relationship-3",
                        IssuedAt = DateTimeOffset.UtcNow.AddMinutes(-20),
                        ExpiresAt = expiresAt,
                    }
                )
            );
        }

        await Assert.ThrowsAsync<CustomerEngagementNotAccessibleException>(() =>
            fixture.Service.ResolveFocusAsync(
                fixture.TenantId,
                fixture.ParticipantId,
                fixture.RelationshipId,
                CreateToken(Guid.NewGuid(), DateTimeOffset.UtcNow.AddMinutes(5)),
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<CustomerEngagementFocusExpiredException>(() =>
            fixture.Service.ResolveFocusAsync(
                fixture.TenantId,
                fixture.ParticipantId,
                fixture.RelationshipId,
                CreateToken(fixture.TenantId, DateTimeOffset.UtcNow.AddMinutes(-5)),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task EndingChannelSessionIsEvidenceBackedReplayableAndLeavesRelationshipActive()
    {
        var fixture = await CreateAsync(addChannelBinding: true);
        const string requestHash = "f7692f2f4af64da3b4be65c6431887f1";
        const string idempotencyKey = "customer-channel-end-0001";

        var ended = await fixture.Service.EndChannelSessionAsync(
            fixture.TenantId,
            fixture.ParticipantId,
            fixture.RelationshipId,
            fixture.ChannelSessionId,
            idempotencyKey,
            requestHash,
            0,
            Guid.NewGuid(),
            CancellationToken.None
        );
        var replay = await fixture.Service.EndChannelSessionAsync(
            fixture.TenantId,
            fixture.ParticipantId,
            fixture.RelationshipId,
            fixture.ChannelSessionId,
            idempotencyKey,
            requestHash,
            0,
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.False(ended.Replayed);
        Assert.True(replay.Replayed);
        Assert.Equal(ended.EvidenceId, replay.EvidenceId);
        Assert.Equal("END_CONVERSATION_CHANNEL_SESSION", fixture.Gateway.LastActionType);
        await using var db = fixture.Factory.CreateDbContext();
        Assert.Equal("ENDED", (await db.ChannelBindings.SingleAsync()).Status);
        Assert.Equal(
            EmploymentRelationshipState.Active,
            (await db.EmploymentRelationships.SingleAsync()).State
        );
    }

    [Fact]
    public async Task UnboundParticipantReceivesOnlyNotAccessible()
    {
        var fixture = await CreateAsync();

        await Assert.ThrowsAsync<CustomerEngagementNotAccessibleException>(() =>
            fixture.Service.GetProgressAsync(
                fixture.TenantId,
                Guid.NewGuid(),
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
    }

    private static async Task<Fixture> CreateAsync(bool addChannelBinding = false)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var dataProtectionProvider = new EphemeralDataProtectionProvider();
        var service = new CustomerEngagementWorkspaceService(
            factory,
            dataProtectionProvider,
            gateway
        );
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var channelSessionId = Guid.NewGuid();
        var evidenceId = Guid.NewGuid();
        await using var db = factory.CreateDbContext();
        db.EmploymentRelationships.Add(
            new EmploymentRelationship
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                AgentInstanceId = Guid.NewGuid(),
                ProfessionalType = "DMA",
                ProfessionalVersion = "1.0.0",
                EvaluationIntentId = Guid.NewGuid(),
                InitiatingParticipantId = participantId,
                State = EmploymentRelationshipState.Active,
                StateVersion = 3,
            }
        );
        db.RelationshipParticipants.Add(
            new RelationshipParticipant
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ParticipantId = participantId,
                Role = RelationshipParticipantRole.Employer,
                BoundEvidenceId = evidenceId,
            }
        );
        db.RelationshipStateHistory.Add(
            new RelationshipStateHistory
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                StateVersion = 3,
                ToState = EmploymentRelationshipState.Active,
                ActorParticipantId = participantId,
                ActorRole = RelationshipParticipantRole.Employer,
                CorrelationId = Guid.NewGuid(),
                EvidenceId = evidenceId,
            }
        );
        if (addChannelBinding)
        {
            db.ChannelBindings.Add(
                new ChannelBinding
                {
                    TenantId = tenantId,
                    BindingId = channelSessionId,
                    RelationshipId = relationshipId,
                    ParticipantId = participantId,
                    Channel = "WHATSAPP",
                    ConversationId = Guid.NewGuid().ToString("D"),
                    AssuranceLevel = "OTP",
                    Status = "ACTIVE",
                }
            );
        }
        await db.SaveChangesAsync();
        return new(
            factory,
            gateway,
            dataProtectionProvider,
            service,
            tenantId,
            participantId,
            relationshipId,
            channelSessionId
        );
    }

    private sealed record Fixture(
        InMemoryEmploymentRelationshipFactory Factory,
        RecordingRelationshipConstitutionalGateway Gateway,
        IDataProtectionProvider DataProtectionProvider,
        CustomerEngagementWorkspaceService Service,
        Guid TenantId,
        Guid ParticipantId,
        Guid RelationshipId,
        Guid ChannelSessionId
    );
}
