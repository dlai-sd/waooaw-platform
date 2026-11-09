// Implements: work-contracts/WC-134-requirements.yaml WC134-R009
// Constitutional basis: C-001, C-005, C-023, C-024, C-059

using System.Data.Common;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class RelationshipEmergencyStopConcurrencyPostgresTests
{
    [Fact]
    public async Task StopCommitWaitsForConcurrentParticipantRevocationAndDeniesIt()
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var barrier = new ParticipantLockBarrier();
        var options = new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
            .UseNpgsql(postgres.GetConnectionString())
            .AddInterceptors(barrier)
            .Options;
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var participant = Guid.NewGuid();
        await using (var setup = new EmploymentRelationshipDbContext(options))
        {
            await setup.Database.EnsureCreatedAsync();
            setup.EmploymentRelationships.Add(
                new EmploymentRelationship
                {
                    TenantId = tenant,
                    RelationshipId = relationship,
                    InitiatingParticipantId = participant,
                    EvaluationIntentId = Guid.NewGuid(),
                    ProfessionalType = "DMA",
                    State = EmploymentRelationshipState.TrialActive,
                }
            );
            setup.RelationshipParticipants.Add(
                new RelationshipParticipant
                {
                    TenantId = tenant,
                    RelationshipId = relationship,
                    ParticipantId = participant,
                    Role = RelationshipParticipantRole.Evaluator,
                    BoundEvidenceId = Guid.NewGuid(),
                }
            );
            await setup.SaveChangesAsync();
        }
        await using var revoker = new NpgsqlConnection(postgres.GetConnectionString());
        await revoker.OpenAsync();
        await using var transaction = await revoker.BeginTransactionAsync();
        await using (
            var revoke = new NpgsqlCommand(
                """
                UPDATE business.relationship_participants
                SET status = 'REVOKED', revoked_evidence_id = @evidence, revoked_at = now()
                WHERE tenant_id = @tenant AND relationship_id = @relationship AND participant_id = @participant
                """,
                revoker,
                transaction
            )
        )
        {
            revoke.Parameters.AddWithValue("evidence", Guid.NewGuid());
            revoke.Parameters.AddWithValue("tenant", tenant);
            revoke.Parameters.AddWithValue("relationship", relationship);
            revoke.Parameters.AddWithValue("participant", participant);
            Assert.Equal(1, await revoke.ExecuteNonQueryAsync());
        }
        var service = new EmploymentRelationshipService(
            new RelationshipFactory(options),
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var stop = service.CommitEmergencyStopAsync(
            tenant,
            relationship,
            participant,
            RelationshipParticipantRole.Evaluator,
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );
        await barrier.Attempted.Task.WaitAsync(TimeSpan.FromSeconds(15));
        await transaction.CommitAsync();
        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() => stop);
        await using var verify = new EmploymentRelationshipDbContext(options);
        var current = await verify.EmploymentRelationships.SingleAsync();
        Assert.Equal(EmploymentRelationshipState.TrialActive, current.State);
        Assert.Empty(await verify.RelationshipStateHistory.ToListAsync());
    }

    [Fact]
    public async Task ConcurrentEvidenceConfirmationUsesOneDurableEvidenceForBothTransitions()
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var relationshipOptions = new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
            .UseNpgsql(postgres.GetConnectionString())
            .Options;
        var conversationOptions = new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseNpgsql(postgres.GetConnectionString())
            .Options;
        await using (var setup = new EmploymentRelationshipDbContext(relationshipOptions))
            await setup.Database.EnsureCreatedAsync();
        await using (var setup = new ConversationStoreDbContext(conversationOptions))
            await setup.Database.ExecuteSqlRawAsync(setup.Database.GenerateCreateScript());

        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var participant = Guid.NewGuid();
        var originalCorrelation = Guid.NewGuid();
        await using (var setup = new EmploymentRelationshipDbContext(relationshipOptions))
        {
            setup.EmploymentRelationships.Add(
                new EmploymentRelationship
                {
                    TenantId = tenant,
                    RelationshipId = relationship,
                    InitiatingParticipantId = participant,
                    EvaluationIntentId = Guid.NewGuid(),
                    ProfessionalType = "DMA",
                    State = EmploymentRelationshipState.TrialActive,
                }
            );
            setup.RelationshipParticipants.Add(
                new RelationshipParticipant
                {
                    TenantId = tenant,
                    RelationshipId = relationship,
                    ParticipantId = participant,
                    Role = RelationshipParticipantRole.Evaluator,
                    BoundEvidenceId = Guid.NewGuid(),
                }
            );
            await setup.SaveChangesAsync();
        }
        await using (var setup = new ConversationStoreDbContext(conversationOptions))
        {
            setup.EmergencyStopLatches.Add(
                new RelationshipEmergencyStopLatch
                {
                    Environment = "demo",
                    TenantId = tenant,
                    RelationshipId = relationship,
                    StoppedByParticipantId = participant,
                    CorrelationId = originalCorrelation,
                }
            );
            await setup.SaveChangesAsync();
        }

        var gateway = new ConcurrentGateway();
        var relationshipFactory = new RelationshipFactory(relationshipOptions);
        var service = new RelationshipEmergencyStopService(
            new ConversationFactory(conversationOptions),
            new EmploymentRelationshipService(
                relationshipFactory,
                new RecordingRelationshipConstitutionalGateway(),
                NullLogger<EmploymentRelationshipService>.Instance
            ),
            gateway,
            Options.Create(new Wc120ConversationOptions { Environment = "demo" }),
            NullLogger<RelationshipEmergencyStopService>.Instance
        );
        var first = service.StopAsync(
            tenant,
            relationship,
            participant,
            RelationshipParticipantRole.Evaluator,
            Guid.NewGuid(),
            CancellationToken.None
        );
        var second = service.StopAsync(
            tenant,
            relationship,
            participant,
            RelationshipParticipantRole.Evaluator,
            Guid.NewGuid(),
            CancellationToken.None
        );
        var results = await Task.WhenAll(first, second).WaitAsync(TimeSpan.FromSeconds(30));

        Assert.All(
            results,
            result => Assert.Equal(EmploymentRelationshipState.StoppedEmergency, result!.State)
        );
        Assert.Equal(2, gateway.Calls);
        await using var verifyConversation = new ConversationStoreDbContext(conversationOptions);
        var latch = await verifyConversation.EmergencyStopLatches.SingleAsync();
        await using var verifyRelationship = new EmploymentRelationshipDbContext(
            relationshipOptions
        );
        var transition = await verifyRelationship.RelationshipStateHistory.SingleAsync(value =>
            value.ToState == EmploymentRelationshipState.StoppedEmergency
        );
        Assert.Equal("EVIDENCE_CONFIRMED", latch.State);
        Assert.Contains(latch.EvidenceId!.Value, gateway.EvidenceIds);
        Assert.Equal(latch.EvidenceId, transition.EvidenceId);
        Assert.Equal(originalCorrelation, transition.CorrelationId);
    }

    private sealed class ConcurrentGateway : IRelationshipEmergencyStopGateway
    {
        private readonly TaskCompletionSource _bothCalled = new(
            TaskCreationOptions.RunContinuationsAsynchronously
        );
        private int _calls;
        public int Calls => _calls;
        public Guid[] EvidenceIds { get; } = [Guid.NewGuid(), Guid.NewGuid()];

        public async Task<RelationshipEmergencyStopDispatch> StopAsync(
            Guid tenantId,
            Guid relationshipId,
            Guid participantId,
            IReadOnlyCollection<Guid> executionIds,
            CancellationToken cancellationToken
        )
        {
            var call = Interlocked.Increment(ref _calls);
            if (call == 2)
                _bothCalled.TrySetResult();
            await _bothCalled.Task.WaitAsync(TimeSpan.FromSeconds(15), cancellationToken);
            return new RelationshipEmergencyStopDispatch(
                EvidenceIds[call - 1],
                DateTimeOffset.UtcNow
            );
        }
    }

    private sealed class ParticipantLockBarrier : DbCommandInterceptor
    {
        public TaskCompletionSource Attempted { get; } =
            new(TaskCreationOptions.RunContinuationsAsynchronously);

        public override ValueTask<InterceptionResult<int>> NonQueryExecutingAsync(
            DbCommand command,
            CommandEventData eventData,
            InterceptionResult<int> result,
            CancellationToken cancellationToken = default
        )
        {
            if (
                command.CommandText.Contains(
                    "business.relationship_participants",
                    StringComparison.Ordinal
                ) && command.CommandText.Contains("FOR UPDATE", StringComparison.Ordinal)
            )
                Attempted.TrySetResult();
            return ValueTask.FromResult(result);
        }
    }

    private sealed class RelationshipFactory(
        DbContextOptions<EmploymentRelationshipDbContext> options
    ) : IDbContextFactory<EmploymentRelationshipDbContext>
    {
        public EmploymentRelationshipDbContext CreateDbContext() => new(options);
    }

    private sealed class ConversationFactory(DbContextOptions<ConversationStoreDbContext> options)
        : IDbContextFactory<ConversationStoreDbContext>
    {
        public ConversationStoreDbContext CreateDbContext() => new(options);
    }
}
