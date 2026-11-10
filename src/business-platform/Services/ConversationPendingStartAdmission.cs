// Implements: WC-134 canonical pending-start admission.
// constitutional_basis: C-023, C-026, C-059, C-063
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

internal sealed record ConversationPendingStartSource(
    string Environment,
    Guid TenantId,
    Guid RelationshipId,
    Guid ConversationId,
    Guid MessageId,
    Guid ExecutionId,
    Guid ActorId,
    Guid IdempotencyKey,
    Guid EvidenceId,
    Guid MandateId,
    ConversationBatchTaskIdentity Task
);

internal sealed class ConversationPendingStartCandidate
{
    public Guid MessageId { get; init; }
    public long Sequence { get; init; }
    public Guid? ExecutionId { get; init; }
    public DateTimeOffset? AdmittedAt { get; init; }
    public DateTimeOffset? DueAt { get; init; }
}

internal sealed record ConversationBatchFreezeLease(
    Guid WorkerId,
    long FencingToken,
    DateTimeOffset LeaseExpiresAt,
    Guid WorkItemId,
    int WorkItemRevision,
    DateTimeOffset DueAt
);

internal static class ConversationPendingStartAdmission
{
    internal static async Task LockConversationAsync(
        ConversationStoreDbContext db,
        string environment,
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        if (
            string.IsNullOrWhiteSpace(environment)
            || tenantId == Guid.Empty
            || relationshipId == Guid.Empty
        )
            throw new ArgumentException("A valid conversation scope is required.");
        if (!db.Database.IsRelational())
            return;
        RequireTransaction(db);
        var key = $"wc134:conversation-batch:{environment}:{tenantId:D}:{relationshipId:D}";
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_advisory_xact_lock(hashtextextended({key}, 0))",
            cancellationToken
        );
    }

    internal static async Task<IReadOnlyList<ConversationPendingStartCandidate>> ReadOrderedAsync(
        ConversationStoreDbContext db,
        string environment,
        Guid tenantId,
        Guid relationshipId,
        Guid conversationId,
        int maximumCandidates,
        CancellationToken cancellationToken
    )
    {
        if (conversationId == Guid.Empty)
            throw new ArgumentException(
                "A valid conversation is required.",
                nameof(conversationId)
            );
        if (maximumCandidates < 1)
            throw new ArgumentOutOfRangeException(nameof(maximumCandidates));
        await LockConversationAsync(db, environment, tenantId, relationshipId, cancellationToken);
        return await db
            .Database.SqlQuery<ConversationPendingStartCandidate>(
                $"""
                SELECT m.message_id AS "MessageId", m.sequence AS "Sequence",
                       p.execution_id AS "ExecutionId", p.admitted_at AS "AdmittedAt",
                       p.due_at AS "DueAt"
                FROM business.conversation_messages AS m
                LEFT JOIN business.conversation_pending_starts AS p
                    ON p.tenant_id = m.tenant_id AND p.message_id = m.message_id
                    AND NOT EXISTS (
                        SELECT 1 FROM business.conversation_batch_members AS assigned
                        JOIN business.conversation_batch_groups AS batch
                            ON batch.tenant_id = assigned.tenant_id AND batch.batch_id = assigned.batch_id
                        WHERE assigned.tenant_id = p.tenant_id AND assigned.message_id = p.message_id
                            AND batch.frozen_at IS NOT NULL
                    )
                WHERE m.tenant_id = {tenantId} AND m.relationship_id = {relationshipId}
                    AND m.conversation_id = {conversationId} AND m.environment = {environment}
                    AND m.sequence >= (
                        SELECT min(first_message.sequence)
                        FROM business.conversation_pending_starts AS first_pending
                        JOIN business.conversation_messages AS first_message
                            ON first_message.tenant_id = first_pending.tenant_id
                            AND first_message.message_id = first_pending.message_id
                        WHERE first_pending.tenant_id = {tenantId}
                            AND first_pending.relationship_id = {relationshipId}
                            AND first_pending.conversation_id = {conversationId}
                            AND first_message.environment = {environment}
                            AND NOT EXISTS (
                                SELECT 1 FROM business.conversation_batch_members AS assigned
                                JOIN business.conversation_batch_groups AS batch
                                    ON batch.tenant_id = assigned.tenant_id AND batch.batch_id = assigned.batch_id
                                WHERE assigned.tenant_id = first_pending.tenant_id
                                    AND assigned.message_id = first_pending.message_id
                                    AND batch.frozen_at IS NOT NULL
                            )
                    )
                ORDER BY m.sequence
                LIMIT {maximumCandidates}
                """
            )
            .ToListAsync(cancellationToken);
    }

    internal static async Task InsertAsync(
        ConversationStoreDbContext db,
        ConversationPendingStartSource source,
        TimeSpan wait,
        CancellationToken cancellationToken
    )
    {
        RequireTransaction(db);
        if (
            string.IsNullOrWhiteSpace(source.Environment)
            || source.TenantId == Guid.Empty
            || source.RelationshipId == Guid.Empty
            || source.ConversationId == Guid.Empty
            || source.MessageId == Guid.Empty
            || source.ExecutionId == Guid.Empty
            || source.ActorId == Guid.Empty
            || source.IdempotencyKey == Guid.Empty
            || source.EvidenceId == Guid.Empty
            || source.MandateId == Guid.Empty
            || source.Task.Owner != "professional-runtime"
            || source.Task.WorkItemId == Guid.Empty
            || source.Task.Revision < 1
            || source.Task.InvocationId == Guid.Empty
            || wait <= TimeSpan.Zero
            || wait.Ticks % TimeSpan.TicksPerMillisecond != 0
        )
            throw new ArgumentOutOfRangeException(nameof(source));

        await LockConversationAsync(
            db,
            source.Environment,
            source.TenantId,
            source.RelationshipId,
            cancellationToken
        );
        var milliseconds = wait.Ticks / TimeSpan.TicksPerMillisecond;
        var inserted = await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.conversation_pending_starts
                (tenant_id, relationship_id, conversation_id, message_id, execution_id, actor_id,
                 idempotency_key, evidence_id, mandate_id, admitted_at, due_at,
                 work_item_id, work_item_revision, work_item_owner, work_item_invocation_id)
            SELECT m.tenant_id, m.relationship_id, m.conversation_id, m.message_id, e.execution_id,
                   s.actor_participant_id, s.idempotency_identity, s.constitutional_evidence_id,
                   s.mandate_id, statement_timestamp(),
                   statement_timestamp() + {milliseconds} * interval '1 millisecond',
                   {source.Task.WorkItemId}, {source.Task.Revision}, {source.Task.Owner},
                   {source.Task.InvocationId}
            FROM business.conversation_messages AS m
            JOIN business.conversation_executions AS e
                ON (e.tenant_id, e.relationship_id, e.conversation_id, e.message_id)
                 = (m.tenant_id, m.relationship_id, m.conversation_id, m.message_id)
            JOIN business.operational_mandate_snapshots AS s
                ON (s.tenant_id, s.relationship_id, s.constitutional_evidence_id)
                 = (m.tenant_id, m.relationship_id, m.evidence_record_id)
            WHERE m.tenant_id = {source.TenantId}
                AND m.environment = {source.Environment}
                AND m.relationship_id = {source.RelationshipId}
                AND m.conversation_id = {source.ConversationId}
                AND m.message_id = {source.MessageId}
                AND m.actor = 'CUSTOMER' AND m.channel = 'WHATSAPP'
                AND m.evidence_state = 'RECORDED'
                AND e.execution_id = {source.ExecutionId}
                AND e.runtime_actor_id = {source.ActorId}
                AND e.origin_channel_binding_id IS NOT NULL
                AND s.actor_participant_id = {source.ActorId}
                AND s.idempotency_identity = {source.IdempotencyKey}
                AND s.constitutional_evidence_id = {source.EvidenceId}
                AND s.mandate_id = {source.MandateId}
                AND s.deadline > statement_timestamp() + {milliseconds} * interval '1 millisecond'
            """,
            cancellationToken
        );
        if (inserted != 1)
            throw new ConversationStateConflictException();
    }

    internal static async Task FreezeAsync(
        ConversationStoreDbContext db,
        string environment,
        Guid tenantId,
        Guid relationshipId,
        Guid conversationId,
        Guid batchId,
        ConversationBatchSelection selection,
        ConversationBatchLimits limits,
        CancellationToken cancellationToken,
        ConversationBatchFreezeLease? lease = null
    )
    {
        RequireTransaction(db);
        var members = selection.ReadyMembers;
        if (
            batchId == Guid.Empty
            || selection.IndividualMembers.Count != 0
            || members.Count == 0
            || members.Any(member =>
                member.MessageId == Guid.Empty
                || member.ExecutionId == Guid.Empty
                || member.Scope.Environment != environment
                || member.Scope.TenantId != tenantId
                || member.Scope.RelationshipId != relationshipId
                || member.Scope.ConversationId != conversationId
            )
            || selection.Boundary is { } nextBoundary
                && (
                    nextBoundary.Scope.Environment != environment
                    || nextBoundary.Scope.TenantId != tenantId
                    || nextBoundary.Scope.RelationshipId != relationshipId
                    || nextBoundary.Scope.ConversationId != conversationId
                )
            || members.Select(member => member.MessageId).Distinct().Count() != members.Count
            || lease is not null
                && (
                    lease.WorkerId == Guid.Empty
                    || lease.FencingToken < 1
                    || lease.LeaseExpiresAt <= DateTimeOffset.UtcNow
                    || lease.WorkItemId == Guid.Empty
                    || lease.WorkItemRevision < 1
                )
        )
            throw new ConversationStateConflictException();
        var proposed = selection.Boundary is null
            ? members
            : members.Concat([selection.Boundary]).ToArray();
        var verified = ConversationBatchWindow.Select(proposed, limits);
        if (verified.IndividualMembers.Count != 0 || verified.ReadyMembers.Count != members.Count)
            throw new ConversationStateConflictException();
        var candidates = await ReadOrderedAsync(
            db,
            environment,
            tenantId,
            relationshipId,
            conversationId,
            checked(members.Count + 1),
            cancellationToken
        );
        if (
            candidates.Count < members.Count
            || candidates
                .Take(members.Count)
                .Where(
                    (candidate, index) =>
                        candidate.ExecutionId != members[index].ExecutionId
                        || candidate.MessageId != members[index].MessageId
                        || candidate.Sequence != members[index].Sequence
                        || candidate.AdmittedAt != members[index].AcceptedAt
                )
                .Any()
        )
            throw new ConversationStateConflictException();
        var firstDueAt = candidates[0].DueAt;
        if (
            firstDueAt is null
            || candidates
                .Take(members.Count)
                .Any(candidate => candidate.AdmittedAt is null || candidate.AdmittedAt > firstDueAt)
        )
            throw new ConversationStateConflictException();
        var windowClosed = await db
            .Database.SqlQuery<bool>(
                $"SELECT {firstDueAt.Value} <= statement_timestamp() AS \"Value\""
            )
            .SingleAsync(cancellationToken);
        if (!windowClosed)
            throw new ConversationStateConflictException();

        var next = candidates.Count > members.Count ? candidates[members.Count] : null;
        if (
            members.Count < limits.MaximumMessages
            && next?.ExecutionId is not null
            && next.AdmittedAt <= firstDueAt
            && selection.Boundary is null
        )
            throw new ConversationStateConflictException();
        if (
            selection.Boundary is { } boundary
            && (
                next is null
                || next.MessageId != boundary.MessageId
                || next.ExecutionId != boundary.ExecutionId
                || next.Sequence != boundary.Sequence
                || next.AdmittedAt != boundary.AcceptedAt
            )
        )
            throw new ConversationStateConflictException();

        foreach (var member in proposed)
        {
            var matches = await db
                .Database.SqlQuery<long>(
                    $"""
                    SELECT count(*) AS "Value"
                    FROM business.conversation_pending_starts AS p
                    JOIN business.conversation_messages AS m
                        ON m.tenant_id = p.tenant_id AND m.message_id = p.message_id
                    JOIN business.conversation_executions AS e
                        ON e.tenant_id = p.tenant_id AND e.execution_id = p.execution_id
                    WHERE p.tenant_id = {tenantId} AND p.message_id = {member.MessageId}
                        AND p.actor_id = {member.Scope.ActorId}
                        AND m.skill_id = {member.Scope.SkillId}
                        AND e.origin_channel_binding_id = {member.Scope.ChannelBindingId}
                        AND e.origin_recipient_digest = {member.Scope.RecipientDigest}
                        AND CASE WHEN jsonb_typeof(m.content_json) = 'array'
                            THEN jsonb_array_length(m.content_json) = 1
                            ELSE false END
                        AND m.content_json -> 0 ->> 'schemaVersion' = '1.0'
                        AND m.content_json -> 0 ->> 'blockType' = 'TEXT'
                        AND jsonb_typeof(m.content_json -> 0 -> 'text') = 'string'
                        AND m.content_json -> 0 ->> 'text' = {member.Text}
                        AND m.content_json -> 0 ->> 'language' = {member.Scope.Language}
                    """
                )
                .SingleAsync(cancellationToken);
            if (matches != 1)
                throw new ConversationStateConflictException();
        }

        var dispatchState = lease is null ? null : "CLAIMED";
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.conversation_batch_groups
                (tenant_id, relationship_id, conversation_id, batch_id, dispatch_state, due_at,
                 work_item_id, work_item_revision, lease_owner, lease_token, lease_expires_at)
            VALUES ({tenantId}, {relationshipId}, {conversationId}, {batchId},
                {dispatchState}, {lease?.DueAt},
                {lease?.WorkItemId}, {lease?.WorkItemRevision}, {lease?.WorkerId},
                {lease?.FencingToken}, {lease?.LeaseExpiresAt})
            """,
            cancellationToken
        );
        for (var index = 0; index < members.Count; index++)
        {
            var messageId = members[index].MessageId;
            var ordinal = index + 1;
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                INSERT INTO business.conversation_batch_members
                    (tenant_id, relationship_id, conversation_id, batch_id, message_id, ordinal)
                VALUES ({tenantId}, {relationshipId}, {conversationId}, {batchId}, {messageId}, {ordinal})
                """,
                cancellationToken
            );
        }
        var count = members.Count;
        var updated = await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.conversation_batch_groups
            SET frozen_at = statement_timestamp(), member_count = {count}
            WHERE tenant_id = {tenantId} AND batch_id = {batchId}
            """,
            cancellationToken
        );
        if (updated != 1)
            throw new ConversationStateConflictException();
    }

    private static void RequireTransaction(ConversationStoreDbContext db)
    {
        if (db.Database.CurrentTransaction is null)
            throw new InvalidOperationException("Pending starts require an admission transaction.");
    }
}
