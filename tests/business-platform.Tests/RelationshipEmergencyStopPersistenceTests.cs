// Implements: work-contracts/WC-134-requirements.yaml WC134-R009
// Constitutional basis: C-001, C-005, C-023, C-024, C-059

using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Npgsql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class RelationshipEmergencyStopPersistenceTests
{
    [Fact]
    public void GatewayParsesDocumentedEmergencyStopEvidenceReference()
    {
        var id = Guid.NewGuid();
        Assert.Equal(
            id,
            GrpcRelationshipEmergencyStopGateway.ParseEvidenceRecordId($"EMERGENCY_STOP:{id:D}")
        );
    }

    [Theory]
    [InlineData("")]
    [InlineData("00000000-0000-0000-0000-000000000001")]
    [InlineData("emergency_stop:00000000-0000-0000-0000-000000000001")]
    [InlineData("EMERGENCY_STOP:00000000-0000-0000-0000-000000000000")]
    [InlineData("EMERGENCY_STOP:00000000000000000000000000000001")]
    [InlineData("EMERGENCY_STOP:not-a-uuid")]
    public void GatewayRejectsMalformedEmergencyStopEvidenceReference(string reference) =>
        Assert.Throws<InvalidOperationException>(() =>
            GrpcRelationshipEmergencyStopGateway.ParseEvidenceRecordId(reference)
        );

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task GatewayOutageLeavesLocalLatchButDoesNotReturnConfirmedStop(bool rpcFailure)
    {
        var relationshipFactory = new InMemoryEmploymentRelationshipFactory(
            Guid.NewGuid().ToString("N")
        );
        var relationships = new EmploymentRelationshipService(
            relationshipFactory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var tenant = Guid.NewGuid();
        var participant = Guid.NewGuid();
        var admitted = await relationships.AdmitAsync(
            tenant,
            participant,
            Guid.NewGuid(),
            "DMA",
            Guid.NewGuid(),
            CancellationToken.None
        );
        var conversationFactory = new InMemoryConversationStoreFactory(
            Guid.NewGuid().ToString("N")
        );
        var service = new RelationshipEmergencyStopService(
            conversationFactory,
            relationships,
            new UnavailableGateway(rpcFailure)
        );

        await Assert.ThrowsAsync<EmergencyStopReconciliationPendingException>(() =>
            service.StopAsync(
                tenant,
                admitted.Relationship.RelationshipId,
                participant,
                RelationshipParticipantRole.Evaluator,
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
        await using var verify = conversationFactory.CreateDbContext();
        Assert.Equal("LATCHED", (await verify.EmergencyStopLatches.SingleAsync()).State);
        Assert.Equal(
            "EVIDENCE_RECONCILIATION_PENDING",
            (await verify.OperationalSignals.SingleAsync()).Code
        );
        var current = await relationships.GetAsync(
            tenant,
            admitted.Relationship.RelationshipId,
            CancellationToken.None
        );
        Assert.NotEqual(EmploymentRelationshipState.StoppedEmergency, current!.State);
    }

    [Fact]
    public async Task PendingSignalWriteFailureStillLogsOutageAndPreservesLatch()
    {
        var relationshipFactory = new InMemoryEmploymentRelationshipFactory(
            Guid.NewGuid().ToString("N")
        );
        var relationships = new EmploymentRelationshipService(
            relationshipFactory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var tenant = Guid.NewGuid();
        var participant = Guid.NewGuid();
        var admitted = await relationships.AdmitAsync(
            tenant,
            participant,
            Guid.NewGuid(),
            "DMA",
            Guid.NewGuid(),
            CancellationToken.None
        );
        var name = Guid.NewGuid().ToString("N");
        var logger = new RecordingStopLogger();
        var service = new RelationshipEmergencyStopService(
            new InterceptedConversationFactory(name, new SignalSaveFailure()),
            relationships,
            new UnavailableGateway(true),
            Options.Create(new Wc120ConversationOptions { Environment = "legacy" }),
            logger
        );
        var exception = await Assert.ThrowsAsync<EmergencyStopReconciliationPendingException>(() =>
            service.StopAsync(
                tenant,
                admitted.Relationship.RelationshipId,
                participant,
                RelationshipParticipantRole.Evaluator,
                Guid.NewGuid(),
                CancellationToken.None
            )
        );

        Assert.Equal(1, logger.WarningCount);
        Assert.Equal(1, logger.ErrorCount);
        Assert.Contains("Unavailable", Assert.Single(logger.Messages));
        Assert.DoesNotContain("synthetic unavailable", Assert.Single(logger.Messages));
        var failures = Assert.IsType<AggregateException>(exception.InnerException);
        Assert.Contains(failures.InnerExceptions, failure => failure is RpcException);
        Assert.Contains(failures.InnerExceptions, failure => failure is DbUpdateException);
        await using var verify = new InMemoryConversationStoreFactory(name).CreateDbContext();
        Assert.Equal("LATCHED", (await verify.EmergencyStopLatches.SingleAsync()).State);
        Assert.Empty(await verify.OperationalSignals.ToListAsync());
    }

    [Fact]
    public async Task StopPropagatesUnrelatedLatchWriteFailure()
    {
        var relationshipFactory = new InMemoryEmploymentRelationshipFactory(
            Guid.NewGuid().ToString("N")
        );
        var relationships = new EmploymentRelationshipService(
            relationshipFactory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admitted = await relationships.AdmitAsync(
            tenantId,
            participantId,
            Guid.NewGuid(),
            "DMA",
            Guid.NewGuid(),
            CancellationToken.None
        );
        var failure = new DbUpdateException("Synthetic unrelated database failure");
        var factory = new InterceptedConversationFactory(
            Guid.NewGuid().ToString("N"),
            new SaveFailure(failure)
        );
        var service = new RelationshipEmergencyStopService(
            factory,
            relationships,
            new RecordingEmergencyStopGateway()
        );

        var actual = await Assert.ThrowsAsync<DbUpdateException>(() =>
            service.StopAsync(
                tenantId,
                admitted.Relationship.RelationshipId,
                participantId,
                RelationshipParticipantRole.Evaluator,
                Guid.NewGuid(),
                CancellationToken.None
            )
        );

        Assert.Same(failure, actual);
    }

    [Fact]
    public async Task StopRecoversOnlyFromLatchIdentityCollision()
    {
        var relationshipFactory = new InMemoryEmploymentRelationshipFactory(
            Guid.NewGuid().ToString("N")
        );
        var relationships = new EmploymentRelationshipService(
            relationshipFactory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admitted = await relationships.AdmitAsync(
            tenantId,
            participantId,
            Guid.NewGuid(),
            "DMA",
            Guid.NewGuid(),
            CancellationToken.None
        );
        var name = Guid.NewGuid().ToString("N");
        var interceptor = new LatchCollision(
            name,
            tenantId,
            admitted.Relationship.RelationshipId,
            participantId
        );
        var service = new RelationshipEmergencyStopService(
            new InterceptedConversationFactory(name, interceptor),
            relationships,
            new RecordingEmergencyStopGateway()
        );

        var result = await service.StopAsync(
            tenantId,
            admitted.Relationship.RelationshipId,
            participantId,
            RelationshipParticipantRole.Evaluator,
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.Equal(EmploymentRelationshipState.StoppedEmergency, result!.State);
        Assert.True(interceptor.CollisionInjected);
        await using var relationshipDb = relationshipFactory.CreateDbContext();
        var transition = await relationshipDb.RelationshipStateHistory.SingleAsync(value =>
            value.ToState == EmploymentRelationshipState.StoppedEmergency
        );
        Assert.Equal(interceptor.EvidenceId, transition.EvidenceId);
        Assert.Equal(interceptor.CorrelationId, transition.CorrelationId);
    }

    [Theory]
    [InlineData("different-actor")]
    [InlineData("latched-different-actor")]
    [InlineData("missing-evidence")]
    [InlineData("empty-evidence")]
    [InlineData("missing-time")]
    public async Task ConfirmedStopRejectsInvalidReplayAuthority(string scenario)
    {
        var relationshipFactory = new InMemoryEmploymentRelationshipFactory(
            Guid.NewGuid().ToString("N")
        );
        var relationships = new EmploymentRelationshipService(
            relationshipFactory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admitted = await relationships.AdmitAsync(
            tenantId,
            participantId,
            Guid.NewGuid(),
            "DMA",
            Guid.NewGuid(),
            CancellationToken.None
        );
        var conversationFactory = new InMemoryConversationStoreFactory(
            Guid.NewGuid().ToString("N")
        );
        await using (var db = conversationFactory.CreateDbContext())
        {
            db.EmergencyStopLatches.Add(
                new RelationshipEmergencyStopLatch
                {
                    Environment = "legacy",
                    TenantId = tenantId,
                    RelationshipId = admitted.Relationship.RelationshipId,
                    StoppedByParticipantId = scenario
                        is "different-actor"
                            or "latched-different-actor"
                        ? Guid.NewGuid()
                        : participantId,
                    CorrelationId = Guid.NewGuid(),
                    State =
                        scenario == "latched-different-actor" ? "LATCHED" : "EVIDENCE_CONFIRMED",
                    EvidenceId =
                        scenario == "missing-evidence" ? null
                        : scenario == "empty-evidence" ? Guid.Empty
                        : Guid.NewGuid(),
                    EvidenceConfirmedAt = scenario == "missing-time" ? null : DateTimeOffset.UtcNow,
                    LatchedAt = DateTimeOffset.UtcNow,
                }
            );
            await db.SaveChangesAsync();
        }
        var service = new RelationshipEmergencyStopService(
            conversationFactory,
            relationships,
            new RecordingEmergencyStopGateway()
        );

        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() =>
            service.StopAsync(
                tenantId,
                admitted.Relationship.RelationshipId,
                participantId,
                RelationshipParticipantRole.Evaluator,
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
        var current = await relationships.GetAsync(
            tenantId,
            admitted.Relationship.RelationshipId,
            CancellationToken.None
        );
        Assert.NotEqual(EmploymentRelationshipState.StoppedEmergency, current!.State);
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task StopLeavesLatchUnconfirmedWhenGatewayEvidenceIsInvalid(bool emptyId)
    {
        var relationshipFactory = new InMemoryEmploymentRelationshipFactory(
            Guid.NewGuid().ToString("N")
        );
        var relationships = new EmploymentRelationshipService(
            relationshipFactory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admitted = await relationships.AdmitAsync(
            tenantId,
            participantId,
            Guid.NewGuid(),
            "DMA",
            Guid.NewGuid(),
            CancellationToken.None
        );
        var conversationFactory = new InMemoryConversationStoreFactory(
            Guid.NewGuid().ToString("N")
        );
        var service = new RelationshipEmergencyStopService(
            conversationFactory,
            relationships,
            new InvalidEvidenceGateway(emptyId)
        );

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            service.StopAsync(
                tenantId,
                admitted.Relationship.RelationshipId,
                participantId,
                RelationshipParticipantRole.Evaluator,
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
        await using var db = conversationFactory.CreateDbContext();
        var latch = await db.EmergencyStopLatches.SingleAsync();
        Assert.Equal("LATCHED", latch.State);
        Assert.Null(latch.EvidenceId);
    }

    [Fact]
    public async Task ConfirmedStopEvidenceCannotBeReusedAfterRelationshipRelease()
    {
        var relationshipFactory = new InMemoryEmploymentRelationshipFactory(
            Guid.NewGuid().ToString("N")
        );
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var participant = Guid.NewGuid();
        var evidence = Guid.NewGuid();
        var correlation = Guid.NewGuid();
        await using (var db = relationshipFactory.CreateDbContext())
        {
            db.EmploymentRelationships.Add(
                new EmploymentRelationship
                {
                    TenantId = tenant,
                    RelationshipId = relationship,
                    InitiatingParticipantId = participant,
                    EvaluationIntentId = Guid.NewGuid(),
                    ProfessionalType = "DMA",
                    State = EmploymentRelationshipState.Active,
                    StateVersion = 2,
                }
            );
            db.RelationshipParticipants.Add(
                new RelationshipParticipant
                {
                    TenantId = tenant,
                    RelationshipId = relationship,
                    ParticipantId = participant,
                    Role = RelationshipParticipantRole.Evaluator,
                    BoundEvidenceId = Guid.NewGuid(),
                }
            );
            db.RelationshipStateHistory.Add(
                new RelationshipStateHistory
                {
                    TenantId = tenant,
                    RelationshipId = relationship,
                    StateVersion = 1,
                    FromState = EmploymentRelationshipState.Active,
                    ToState = EmploymentRelationshipState.StoppedEmergency,
                    ActorParticipantId = participant,
                    ActorRole = RelationshipParticipantRole.Evaluator,
                    CorrelationId = correlation,
                    EvidenceId = evidence,
                }
            );
            await db.SaveChangesAsync();
        }
        var relationships = new EmploymentRelationshipService(
            relationshipFactory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() =>
            relationships.CommitEmergencyStopAsync(
                tenant,
                relationship,
                participant,
                RelationshipParticipantRole.Evaluator,
                correlation,
                evidence,
                CancellationToken.None
            )
        );
        await using var verify = relationshipFactory.CreateDbContext();
        Assert.Equal(
            EmploymentRelationshipState.Active,
            (await verify.EmploymentRelationships.SingleAsync()).State
        );
        Assert.Single(await verify.RelationshipStateHistory.ToListAsync());
    }

    private sealed class InvalidEvidenceGateway(bool emptyId) : IRelationshipEmergencyStopGateway
    {
        public Task<RelationshipEmergencyStopDispatch> StopAsync(
            Guid tenantId,
            Guid relationshipId,
            Guid participantId,
            IReadOnlyCollection<Guid> executionIds,
            CancellationToken cancellationToken
        ) =>
            Task.FromResult(
                new RelationshipEmergencyStopDispatch(
                    emptyId ? Guid.Empty : Guid.NewGuid(),
                    emptyId ? DateTimeOffset.UtcNow : default
                )
            );
    }

    private sealed class UnavailableGateway(bool rpcFailure) : IRelationshipEmergencyStopGateway
    {
        public Task<RelationshipEmergencyStopDispatch> StopAsync(
            Guid tenantId,
            Guid relationshipId,
            Guid participantId,
            IReadOnlyCollection<Guid> executionIds,
            CancellationToken cancellationToken
        )
        {
            Exception failure = rpcFailure
                ? new RpcException(new Status(StatusCode.Unavailable, "synthetic unavailable"))
                : new TimeoutException("synthetic timeout");
            return Task.FromException<RelationshipEmergencyStopDispatch>(failure);
        }
    }

    private sealed class InterceptedConversationFactory(
        string name,
        SaveChangesInterceptor interceptor
    ) : IDbContextFactory<ConversationStoreDbContext>
    {
        public ConversationStoreDbContext CreateDbContext() =>
            new(
                new DbContextOptionsBuilder<ConversationStoreDbContext>()
                    .UseInMemoryDatabase(name)
                    .AddInterceptors(interceptor)
                    .Options
            );
    }

    private sealed class SaveFailure(DbUpdateException failure) : SaveChangesInterceptor
    {
        public override ValueTask<InterceptionResult<int>> SavingChangesAsync(
            DbContextEventData eventData,
            InterceptionResult<int> result,
            CancellationToken cancellationToken = default
        ) => ValueTask.FromException<InterceptionResult<int>>(failure);
    }

    private sealed class SignalSaveFailure : SaveChangesInterceptor
    {
        public override ValueTask<InterceptionResult<int>> SavingChangesAsync(
            DbContextEventData eventData,
            InterceptionResult<int> result,
            CancellationToken cancellationToken = default
        )
        {
            if (
                eventData
                    .Context!.ChangeTracker.Entries<ConversationOperationalSignal>()
                    .Any(value => value.State == EntityState.Added)
            )
                throw new DbUpdateException("Synthetic signal write failure");
            return ValueTask.FromResult(result);
        }
    }

    private sealed class RecordingStopLogger : ILogger<RelationshipEmergencyStopService>
    {
        public int WarningCount { get; private set; }
        public int ErrorCount { get; private set; }
        public List<string> Messages { get; } = [];

        public IDisposable? BeginScope<TState>(TState state)
            where TState : notnull => null;

        public bool IsEnabled(LogLevel logLevel) => true;

        public void Log<TState>(
            LogLevel logLevel,
            EventId eventId,
            TState state,
            Exception? exception,
            Func<TState, Exception?, string> formatter
        )
        {
            if (logLevel == LogLevel.Warning && exception is null)
            {
                WarningCount++;
                Messages.Add(formatter(state, exception));
            }
            if (logLevel == LogLevel.Error && exception is null)
                ErrorCount++;
        }
    }

    private sealed class LatchCollision(
        string name,
        Guid tenant,
        Guid relationship,
        Guid participant
    ) : SaveChangesInterceptor
    {
        public bool CollisionInjected { get; private set; }
        public Guid EvidenceId { get; } = Guid.NewGuid();
        public Guid CorrelationId { get; } = Guid.NewGuid();

        public override async ValueTask<InterceptionResult<int>> SavingChangesAsync(
            DbContextEventData eventData,
            InterceptionResult<int> result,
            CancellationToken cancellationToken = default
        )
        {
            await using var winner = new InMemoryConversationStoreFactory(name).CreateDbContext();
            winner.EmergencyStopLatches.Add(
                new RelationshipEmergencyStopLatch
                {
                    Environment = "legacy",
                    TenantId = tenant,
                    RelationshipId = relationship,
                    StoppedByParticipantId = participant,
                    CorrelationId = CorrelationId,
                    State = "EVIDENCE_CONFIRMED",
                    EvidenceId = EvidenceId,
                    EvidenceConfirmedAt = DateTimeOffset.UtcNow,
                    LatchedAt = DateTimeOffset.UtcNow,
                }
            );
            await winner.SaveChangesAsync(cancellationToken);
            CollisionInjected = true;
            throw new DbUpdateException(
                "Synthetic latch identity collision",
                new PostgresException(
                    "Synthetic unique violation",
                    "ERROR",
                    "ERROR",
                    PostgresErrorCodes.UniqueViolation,
                    constraintName: "relationship_emergency_stop_latch_unique"
                )
            );
        }
    }
}
