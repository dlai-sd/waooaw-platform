// Implements: work-contracts/WC-060-goal005-ae01-continuity-evidence-stop.md § WC060-07
// constitutional_basis: C-001, C-005, C-023, C-024, C-059

using Grpc.Core;
using Grpc.Net.Client;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.BusinessPlatform.Services;

public sealed record RelationshipEmergencyStopDispatch(Guid EvidenceId, DateTimeOffset ConfirmedAt);

public sealed class EmergencyStopReconciliationPendingException(Exception innerException)
    : Exception("Emergency Stop is latched locally; reconciliation is pending.", innerException);

public interface IRelationshipEmergencyStopGateway
{
    Task<RelationshipEmergencyStopDispatch> StopAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid participantId,
        IReadOnlyCollection<Guid> executionIds,
        CancellationToken cancellationToken
    );
}

public sealed class GrpcRelationshipEmergencyStopGateway(IConfiguration configuration)
    : IRelationshipEmergencyStopGateway
{
    public async Task<RelationshipEmergencyStopDispatch> StopAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid participantId,
        IReadOnlyCollection<Guid> executionIds,
        CancellationToken cancellationToken
    )
    {
        var endpoint =
            configuration["ConstitutionalEngine:GrpcUrl"]
            ?? throw new InvalidOperationException(
                "ConstitutionalEngine:GrpcUrl is not configured."
            );
        using var channel = GrpcChannel.ForAddress(endpoint);
        var client = new ConstitutionalService.ConstitutionalServiceClient(channel);
        var request = new EmergencyStopRequest
        {
            ContractId = relationshipId.ToString("D"),
            StoppedBy = participantId.ToString("D"),
        };
        request.ActiveSessionIds.Add(executionIds.Select(value => value.ToString("D")));
        var response = await client.TriggerEmergencyStopAsync(
            request,
            new Metadata { { "x-tenant-id", tenantId.ToString("D") } },
            deadline: DateTime.UtcNow.AddMilliseconds(200),
            cancellationToken: cancellationToken
        );
        var evidenceId = ParseEvidenceRecordId(response.EmergencyStopRecordId);
        if (response.PendingSessions.Count > 0)
            throw new RpcException(
                new Status(
                    StatusCode.Unavailable,
                    "Emergency Stop is recorded; runtime propagation remains pending."
                )
            );
        if (response.RecordedAt is null)
            throw new InvalidOperationException(
                "Constitutional Engine returned no Stop evidence timestamp."
            );
        return new RelationshipEmergencyStopDispatch(
            evidenceId,
            response.RecordedAt.ToDateTimeOffset()
        );
    }

    internal static Guid ParseEvidenceRecordId(string recordId)
    {
        const string prefix = "EMERGENCY_STOP:";
        if (
            !recordId.StartsWith(prefix, StringComparison.Ordinal)
            || !Guid.TryParseExact(recordId.AsSpan(prefix.Length), "D", out var evidenceId)
            || evidenceId == Guid.Empty
        )
            throw new InvalidOperationException(
                "Constitutional Engine returned an invalid Stop evidence identifier."
            );
        return evidenceId;
    }
}

public sealed class RelationshipEmergencyStopService(
    IDbContextFactory<ConversationStoreDbContext> conversationFactory,
    EmploymentRelationshipService relationships,
    IRelationshipEmergencyStopGateway gateway,
    IOptions<Wc120ConversationOptions> conversationOptions,
    ILogger<RelationshipEmergencyStopService> logger
)
{
    public RelationshipEmergencyStopService(
        IDbContextFactory<ConversationStoreDbContext> conversationFactory,
        EmploymentRelationshipService relationships,
        IRelationshipEmergencyStopGateway gateway
    )
        : this(
            conversationFactory,
            relationships,
            gateway,
            Options.Create(new Wc120ConversationOptions { Environment = "legacy" }),
            NullLogger<RelationshipEmergencyStopService>.Instance
        ) { }

    public async Task<EmploymentRelationship?> StopAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid participantId,
        RelationshipParticipantRole participantRole,
        Guid correlationId,
        CancellationToken cancellationToken
    )
    {
        var existing = await relationships.GetAsync(tenantId, relationshipId, cancellationToken);
        if (existing is null || existing.State == EmploymentRelationshipState.StoppedEmergency)
            return existing;
        await using var conversations = await conversationFactory.CreateDbContextAsync(
            cancellationToken
        );
        var latch = await conversations.EmergencyStopLatches.SingleOrDefaultAsync(
            value =>
                value.Environment == conversationOptions.Value.Environment
                && value.TenantId == tenantId
                && value.RelationshipId == relationshipId,
            cancellationToken
        );
        if (latch is null)
        {
            latch = new RelationshipEmergencyStopLatch
            {
                Environment = conversationOptions.Value.Environment,
                TenantId = tenantId,
                RelationshipId = relationshipId,
                StoppedByParticipantId = participantId,
                CorrelationId = correlationId,
                LatchedAt = DateTimeOffset.UtcNow,
            };
            conversations.EmergencyStopLatches.Add(latch);
            try
            {
                await conversations.SaveChangesAsync(cancellationToken);
            }
            catch (DbUpdateException exception)
                when (exception.InnerException
                        is Npgsql.PostgresException
                        {
                            SqlState: Npgsql.PostgresErrorCodes.UniqueViolation,
                            ConstraintName: "relationship_emergency_stop_latch_unique",
                        }
                )
            {
                conversations.ChangeTracker.Clear();
                latch = await conversations.EmergencyStopLatches.SingleAsync(
                    value =>
                        value.Environment == conversationOptions.Value.Environment
                        && value.TenantId == tenantId
                        && value.RelationshipId == relationshipId,
                    cancellationToken
                );
            }
        }
        if (latch.StoppedByParticipantId != participantId)
            throw new ConstitutionalActionDeniedException(
                "Emergency Stop reconciliation requires the original participant."
            );
        if (latch.State == "EVIDENCE_CONFIRMED")
        {
            if (
                latch.EvidenceId is null
                || latch.EvidenceId == Guid.Empty
                || latch.EvidenceConfirmedAt is null
            )
                throw new ConstitutionalActionDeniedException(
                    "Emergency Stop evidence cannot be replayed for this participant."
                );
            return await relationships.CommitEmergencyStopAsync(
                tenantId,
                relationshipId,
                participantId,
                participantRole,
                latch.CorrelationId,
                latch.EvidenceId.Value,
                cancellationToken
            );
        }

        var terminalStates = new[] { "COMPLETED", "CANCELLED", "STOPPED" };
        var executions = await conversations
            .Executions.AsNoTracking()
            .Where(value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && !terminalStates.Contains(value.ProcessingState)
            )
            .ToListAsync(cancellationToken);
        var localExecutionIds = executions.Select(value => value.ExecutionId).ToArray();
        var origins = await conversations
            .IdempotencyOutcomes.AsNoTracking()
            .Where(value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.OperationFamily == "SEND"
                && value.ExecutionId != null
                && localExecutionIds.Contains(value.ExecutionId.Value)
            )
            .ToListAsync(cancellationToken);
        var executionIds = new HashSet<Guid>();
        foreach (var execution in executions)
        {
            var executionOrigins = origins
                .Where(value =>
                    value.ExecutionId == execution.ExecutionId
                    && value.MessageId == execution.MessageId
                )
                .ToList();
            if (executionOrigins.Count == 0)
                executionIds.Add(execution.ExecutionId);
            foreach (var origin in executionOrigins)
            {
                executionIds.Add(
                    ConversationExecutionIdentity.Create(
                        tenantId,
                        relationshipId,
                        origin.ActorParticipantId,
                        execution.ConversationId,
                        origin.IdempotencyKey
                    )
                );
            }
        }
        RelationshipEmergencyStopDispatch dispatch;
        try
        {
            dispatch = await gateway.StopAsync(
                tenantId,
                relationshipId,
                participantId,
                executionIds,
                cancellationToken
            );
        }
        catch (RpcException exception)
        {
            logger.LogWarning(
                "Emergency Stop latched locally; constitutional evidence reconciliation remains pending. Status: {StatusCode}",
                exception.StatusCode
            );
            await RecordPendingEvidenceSignalAsync(conversations, exception, cancellationToken);
            throw new EmergencyStopReconciliationPendingException(exception);
        }
        catch (TimeoutException exception)
        {
            logger.LogWarning(
                "Emergency Stop latched locally; constitutional evidence reconciliation timed out."
            );
            await RecordPendingEvidenceSignalAsync(conversations, exception, cancellationToken);
            throw new EmergencyStopReconciliationPendingException(exception);
        }
        if (dispatch.EvidenceId == Guid.Empty || dispatch.ConfirmedAt == default)
            throw new InvalidOperationException("Emergency Stop returned invalid evidence.");
        if (conversations.Database.IsRelational())
        {
            await conversations
                .EmergencyStopLatches.Where(value =>
                    value.LatchId == latch.LatchId
                    && value.Environment == latch.Environment
                    && value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.StoppedByParticipantId == participantId
                    && value.State == "LATCHED"
                )
                .ExecuteUpdateAsync(
                    updates =>
                        updates
                            .SetProperty(value => value.State, "EVIDENCE_CONFIRMED")
                            .SetProperty(value => value.EvidenceId, dispatch.EvidenceId)
                            .SetProperty(value => value.EvidenceConfirmedAt, dispatch.ConfirmedAt),
                    cancellationToken
                );
            await conversations.Entry(latch).ReloadAsync(cancellationToken);
            if (
                conversations.Entry(latch).State == EntityState.Detached
                || latch.State != "EVIDENCE_CONFIRMED"
                || latch.StoppedByParticipantId != participantId
                || latch.EvidenceId is null
                || latch.EvidenceId == Guid.Empty
                || latch.EvidenceConfirmedAt is null
            )
                throw new InvalidOperationException(
                    "Emergency Stop evidence reconciliation failed."
                );
        }
        else
        {
            latch.State = "EVIDENCE_CONFIRMED";
            latch.EvidenceId = dispatch.EvidenceId;
            latch.EvidenceConfirmedAt = dispatch.ConfirmedAt;
            await conversations.SaveChangesAsync(cancellationToken);
        }
        return await relationships.CommitEmergencyStopAsync(
            tenantId,
            relationshipId,
            participantId,
            participantRole,
            latch.CorrelationId,
            latch.EvidenceId!.Value,
            cancellationToken
        );
    }

    private async Task RecordPendingEvidenceSignalAsync(
        ConversationStoreDbContext conversations,
        Exception gatewayFailure,
        CancellationToken cancellationToken
    )
    {
        conversations.OperationalSignals.Add(
            PendingEvidenceSignal(conversationOptions.Value.Environment)
        );
        try
        {
            await conversations.SaveChangesAsync(cancellationToken);
        }
        catch (DbUpdateException signalFailure)
        {
            logger.LogError(
                "Emergency Stop reconciliation signal could not be persisted; the local latch remains active."
            );
            throw new EmergencyStopReconciliationPendingException(
                new AggregateException(gatewayFailure, signalFailure)
            );
        }
    }

    private static ConversationOperationalSignal PendingEvidenceSignal(string environment) =>
        new()
        {
            Environment = environment,
            Category = "EMERGENCY_STOP",
            Code = "EVIDENCE_RECONCILIATION_PENDING",
            OccurredAt = DateTimeOffset.UtcNow,
        };
}
