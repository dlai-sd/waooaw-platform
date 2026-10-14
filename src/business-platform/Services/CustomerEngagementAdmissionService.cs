// Implements: architecture/reference/components/customer-engagement-workspace-solution-contract.md §7.2
// Constitutional basis: C-001, C-005, C-007, C-023, C-026, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record CustomerEngagementAdmissionOutcome(
    string SchemaVersion,
    Guid RelationshipId,
    Guid AgentInstanceId,
    Guid ConversationId,
    string LifecycleState,
    string EngagementIntent,
    bool Replayed,
    DateTimeOffset AdmittedAt,
    string EvidenceRef,
    WorkspaceFocusReference ResumeFocus
);

public sealed class CustomerEngagementAdmissionConflictException : Exception;

public sealed class CustomerEngagementAdmissionService(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    EmploymentRelationshipService relationshipService,
    ConversationService conversationService,
    CustomerEngagementWorkspaceService workspaceService
)
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    public async Task<CustomerEngagementAdmissionOutcome> AdmitAsync(
        Guid tenantId,
        Guid participantId,
        Guid clientIntentId,
        string idempotencyKey,
        string canonicalRequestHash,
        string engagementIntent,
        string professionalType,
        Guid professionalAdmissionId,
        string professionalVersion,
        string disclosureVersion,
        Guid correlationId,
        CancellationToken cancellationToken
    )
    {
        var operation = await ReserveAsync(
            tenantId,
            participantId,
            clientIntentId,
            idempotencyKey,
            canonicalRequestHash,
            engagementIntent,
            cancellationToken
        );
        if (operation.State == "SUCCEEDED" && operation.OutcomeJson is not null)
        {
            var replay =
                JsonSerializer.Deserialize<CustomerEngagementAdmissionOutcome>(
                    operation.OutcomeJson,
                    JsonOptions
                ) ?? throw new InvalidOperationException("Stored admission outcome is invalid.");
            return replay with { Replayed = true };
        }

        try
        {
            var acceptedAt = DateTimeOffset.UtcNow;
            var contractHash = Convert.ToHexStringLower(
                SHA256.HashData(
                    Encoding.UTF8.GetBytes(
                        $"{professionalAdmissionId:D}|{professionalVersion}|{engagementIntent}|{disclosureVersion}"
                    )
                )
            );
            var admitted = await relationshipService.AdmitPreparedFromAcquisitionAsync(
                tenantId,
                participantId,
                clientIntentId,
                professionalType,
                professionalAdmissionId,
                professionalVersion,
                operation.RelationshipId,
                operation.AgentInstanceId,
                correlationId,
                new RelationshipAcquisitionEvidence(
                    clientIntentId,
                    engagementIntent,
                    disclosureVersion,
                    disclosureVersion,
                    contractHash,
                    acceptedAt
                ),
                cancellationToken
            );
            var conversation = await conversationService.EnsureConversationAsync(
                tenantId,
                admitted.Relationship.RelationshipId,
                cancellationToken,
                operation.ConversationId
            );
            var progress = await workspaceService.GetProgressAsync(
                tenantId,
                participantId,
                admitted.Relationship.RelationshipId,
                cancellationToken
            );
            var focus =
                progress.AvailableFocuses.FirstOrDefault()
                ?? throw new InvalidOperationException("Initial workspace focus is unavailable.");

            await using var evidenceDb = await dbFactory.CreateDbContextAsync(cancellationToken);
            var evidenceId = await evidenceDb
                .RelationshipStateHistory.Where(value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == admitted.Relationship.RelationshipId
                    && value.StateVersion == 0
                )
                .Select(value => value.EvidenceId)
                .SingleAsync(cancellationToken);
            var outcome = new CustomerEngagementAdmissionOutcome(
                "1",
                admitted.Relationship.RelationshipId,
                admitted.Relationship.AgentInstanceId,
                conversation.ConversationId,
                "DISCOVERED",
                engagementIntent,
                false,
                admitted.Relationship.CreatedAt,
                evidenceId.ToString("D"),
                focus
            );
            await CompleteAsync(operation.OperationId, evidenceId, outcome, cancellationToken);
            return outcome;
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            await RecordFailureAsync(operation.OperationId, exception, cancellationToken);
            throw;
        }
    }

    private async Task<CustomerEngagementAdmissionOperation> ReserveAsync(
        Guid tenantId,
        Guid participantId,
        Guid clientIntentId,
        string idempotencyKey,
        string canonicalRequestHash,
        string engagementIntent,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var existing = await FindAsync(
            db,
            tenantId,
            participantId,
            clientIntentId,
            idempotencyKey,
            cancellationToken
        );
        if (existing is not null)
        {
            EnsureReplayMatches(existing, clientIntentId, idempotencyKey, canonicalRequestHash);
            return existing;
        }

        var operation = new CustomerEngagementAdmissionOperation
        {
            TenantId = tenantId,
            ParticipantId = participantId,
            IdempotencyKey = idempotencyKey,
            ClientIntentId = clientIntentId,
            MaterialRequestHash = canonicalRequestHash,
            RelationshipId = Guid.NewGuid(),
            AgentInstanceId = Guid.NewGuid(),
            ConversationId = Guid.NewGuid(),
            EngagementIntent = engagementIntent,
        };
        db.CustomerEngagementAdmissionOperations.Add(operation);
        try
        {
            await db.SaveChangesAsync(cancellationToken);
            return operation;
        }
        catch (DbUpdateException)
        {
            await using var replayDb = await dbFactory.CreateDbContextAsync(cancellationToken);
            var replay =
                await FindAsync(
                    replayDb,
                    tenantId,
                    participantId,
                    clientIntentId,
                    idempotencyKey,
                    cancellationToken
                )
                ?? throw new InvalidOperationException(
                    "Concurrent admission reservation could not be recovered."
                );
            EnsureReplayMatches(replay, clientIntentId, idempotencyKey, canonicalRequestHash);
            return replay;
        }
    }

    private static async Task<CustomerEngagementAdmissionOperation?> FindAsync(
        EmploymentRelationshipDbContext db,
        Guid tenantId,
        Guid participantId,
        Guid clientIntentId,
        string idempotencyKey,
        CancellationToken cancellationToken
    ) =>
        await db.CustomerEngagementAdmissionOperations.SingleOrDefaultAsync(
            value =>
                value.TenantId == tenantId
                && value.ParticipantId == participantId
                && (
                    value.IdempotencyKey == idempotencyKey || value.ClientIntentId == clientIntentId
                ),
            cancellationToken
        );

    private static void EnsureReplayMatches(
        CustomerEngagementAdmissionOperation operation,
        Guid clientIntentId,
        string idempotencyKey,
        string canonicalRequestHash
    )
    {
        if (
            operation.ClientIntentId != clientIntentId
            || operation.IdempotencyKey != idempotencyKey
            || operation.MaterialRequestHash != canonicalRequestHash
        )
            throw new CustomerEngagementAdmissionConflictException();
    }

    private async Task CompleteAsync(
        Guid operationId,
        Guid evidenceId,
        CustomerEngagementAdmissionOutcome outcome,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var operation = await db.CustomerEngagementAdmissionOperations.SingleAsync(
            value => value.OperationId == operationId,
            cancellationToken
        );
        operation.State = "SUCCEEDED";
        operation.EvidenceId = evidenceId;
        operation.OutcomeJson = JsonSerializer.Serialize(outcome, JsonOptions);
        operation.CompletedAt = DateTimeOffset.UtcNow;
        operation.UpdatedAt = DateTimeOffset.UtcNow;
        await db.SaveChangesAsync(cancellationToken);
    }

    private async Task RecordFailureAsync(
        Guid operationId,
        Exception exception,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var operation = await db.CustomerEngagementAdmissionOperations.SingleAsync(
            value => value.OperationId == operationId,
            cancellationToken
        );
        operation.State = "RECONCILE_REQUIRED";
        operation.UpdatedAt = DateTimeOffset.UtcNow;
        await db.SaveChangesAsync(cancellationToken);
    }
}
