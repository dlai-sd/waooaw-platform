// Implements: WC-134 durable batch claim, freeze, dispatch and recovery.
// constitutional_basis: C-001, C-005, C-023, C-026, C-059, C-063
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record ConversationBatchWork(
    Guid ClaimId,
    Guid TenantId,
    Guid RelationshipId,
    Guid ConversationId,
    Guid FirstMessageId,
    long FencingToken,
    DateTimeOffset LeaseExpiresAt,
    Guid? BatchId = null,
    string DispatchState = "CLAIMED"
);

public sealed class ConversationBatchWorkScope
{
    private readonly AsyncLocal<ConversationBatchWork?> _current = new();
    public ConversationBatchWork? Current => _current.Value;

    internal IDisposable Begin(ConversationBatchWork work)
    {
        if (_current.Value is not null)
            throw new InvalidOperationException("Batch work scopes cannot be nested.");
        _current.Value = work;
        return new Scope(this);
    }

    private sealed class Scope(ConversationBatchWorkScope owner) : IDisposable
    {
        public void Dispose() => owner._current.Value = null;
    }
}

public sealed class ConversationBatchWorkDirectory(
    IDbContextFactory<ConversationStoreDbContext> conversations,
    IOptions<Wc120ConversationOptions> conversationOptions,
    IOptions<ConversationBatchingOptions> batchingOptions,
    ILogger<ConversationBatchWorkDirectory> logger
)
{
    private readonly Guid _workerId = Guid.NewGuid();

    public Guid WorkerId => _workerId;

    public async Task<ConversationBatchWork?> ClaimAsync(CancellationToken cancellationToken)
    {
        if (!conversationOptions.Value.Enabled)
            return null;
        await using var db = await conversations.CreateDbContextAsync(cancellationToken);
        var recovery = await db
            .Database.SqlQuery<RecoveryRow>(
                $"""
                SELECT batch_id AS "BatchId", tenant_id AS "TenantId",
                       relationship_id AS "RelationshipId", conversation_id AS "ConversationId",
                       first_message_id AS "FirstMessageId", dispatch_state AS "DispatchState",
                       fencing_token AS "FencingToken", lease_expires_at AS "LeaseExpiresAt",
                       authorized AS "Authorized"
                FROM business.claim_conversation_batch_recovery(
                    {conversationOptions.Value.Environment}, {_workerId},
                    {batchingOptions.Value.LeaseSeconds})
                """
            )
            .ToListAsync(cancellationToken);
        if (recovery.Count > 0)
        {
            if (recovery.Count != 1 || !recovery[0].Authorized)
                return null;
            var item = recovery[0];
            return new(
                item.BatchId,
                item.TenantId,
                item.RelationshipId,
                item.ConversationId,
                item.FirstMessageId,
                item.FencingToken,
                item.LeaseExpiresAt,
                item.BatchId,
                item.DispatchState
            );
        }
        var claims = await db
            .Database.SqlQuery<ClaimRow>(
                $"""
                SELECT claim_id AS "ClaimId", tenant_id AS "TenantId",
                       relationship_id AS "RelationshipId", conversation_id AS "ConversationId",
                       first_message_id AS "FirstMessageId", fencing_token AS "FencingToken",
                       lease_expires_at AS "LeaseExpiresAt", authorized AS "Authorized"
                FROM business.claim_conversation_batch(
                    {conversationOptions.Value.Environment}, {_workerId},
                    {batchingOptions.Value.LeaseSeconds})
                """
            )
            .ToListAsync(cancellationToken);
        if (claims.Count == 0)
            return null;
        if (claims.Count != 1 || !claims[0].Authorized)
        {
            logger.LogWarning("Conversation batch claim denied by current Identity authority.");
            return null;
        }
        var claim = claims[0];
        return new(
            claim.ClaimId,
            claim.TenantId,
            claim.RelationshipId,
            claim.ConversationId,
            claim.FirstMessageId,
            claim.FencingToken,
            claim.LeaseExpiresAt
        );
    }

    private sealed class ClaimRow
    {
        public Guid ClaimId { get; init; }
        public Guid TenantId { get; init; }
        public Guid RelationshipId { get; init; }
        public Guid ConversationId { get; init; }
        public Guid FirstMessageId { get; init; }
        public long FencingToken { get; init; }
        public DateTimeOffset LeaseExpiresAt { get; init; }
        public bool Authorized { get; init; }
    }

    private sealed class RecoveryRow
    {
        public Guid BatchId { get; init; }
        public Guid TenantId { get; init; }
        public Guid RelationshipId { get; init; }
        public Guid ConversationId { get; init; }
        public Guid FirstMessageId { get; init; }
        public string DispatchState { get; init; } = string.Empty;
        public long FencingToken { get; init; }
        public DateTimeOffset LeaseExpiresAt { get; init; }
        public bool Authorized { get; init; }
    }
}

public sealed class ConversationBatchDispatchWorker(
    IDbContextFactory<ConversationStoreDbContext> conversations,
    IDbContextFactory<EmploymentRelationshipDbContext> relationships,
    OperationalMandateResolver mandateResolver,
    IConversationBatchTaskResolver taskResolver,
    ConversationRuntimeIdentityAuthority runtimeIdentity,
    ConversationStopFence stopFence,
    IConversationExecutionGateway gateway,
    IConversationBatchExecutionGateway batchGateway,
    ConversationBatchWorkDirectory directory,
    ConversationBatchWorkScope workScope,
    IOptions<ConversationBatchingOptions> options,
    ILogger<ConversationBatchDispatchWorker> logger
)
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    public async Task<bool> ProcessOneAsync(CancellationToken cancellationToken)
    {
        var work = workScope.Current;
        if (work is null)
            throw new InvalidOperationException("A claimed batch work capability is required.");
        await stopFence.ThrowIfLatchedAsync(work.TenantId, work.RelationshipId, cancellationToken);
        await using var db = await conversations.CreateDbContextAsync(cancellationToken);
        await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);
        await ConversationPendingStartAdmission.LockConversationAsync(
            db,
            await db
                .Messages.Where(message =>
                    message.TenantId == work.TenantId && message.MessageId == work.FirstMessageId
                )
                .Select(message => message.Environment)
                .SingleAsync(cancellationToken),
            work.TenantId,
            work.RelationshipId,
            cancellationToken
        );
        var rows = work.BatchId is null
            ? await ReadSourcesAsync(db, work, options.Value.MaximumMessages + 1, cancellationToken)
            : await ReadFrozenSourcesAsync(db, work, cancellationToken);
        if (rows.Count == 0 || rows[0].MessageId != work.FirstMessageId)
            throw new ConversationStateConflictException();

        await using var relationshipDb = await relationships.CreateDbContextAsync(
            cancellationToken
        );
        var relationship = await relationshipDb.EmploymentRelationships.SingleAsync(
            value => value.TenantId == work.TenantId && value.RelationshipId == work.RelationshipId,
            cancellationToken
        );
        var candidates = new List<ConversationBatchCandidate>();
        var mandates = new Dictionary<Guid, OperationalMandateV1>();
        foreach (var row in rows)
        {
            if (
                row.ExecutionId is null
                || row.ActorId is null
                || row.IdempotencyKey is null
                || row.EvidenceId is null
                || row.WorkItemId is null
                || row.WorkItemRevision is null
                || row.WorkItemInvocationId is null
                || row.ChannelBindingId is null
                || string.IsNullOrWhiteSpace(row.RecipientDigest)
                || string.IsNullOrWhiteSpace(row.MandateJson)
            )
                throw new ConversationStateConflictException();
            var storedMandate =
                JsonSerializer.Deserialize<OperationalMandateV1>(row.MandateJson!, JsonOptions)
                ?? throw new ConversationStateConflictException();
            var currentMandate = await mandateResolver.ValidateExistingAsync(
                relationshipDb,
                work.TenantId,
                row.ActorId!.Value,
                work.RelationshipId,
                row.IdempotencyKey!.Value,
                row.EvidenceId!.Value,
                row.SkillId,
                row.Text,
                cancellationToken
            );
            if (
                currentMandate.MandateId != storedMandate.MandateId
                || !string.Equals(
                    currentMandate.MandateDigest,
                    storedMandate.MandateDigest,
                    StringComparison.Ordinal
                )
            )
                throw new ConversationNotAccessibleException();
            var claimedTask = new ConversationWorkItemReferenceV1(
                "professional-runtime",
                row.WorkItemId!.Value,
                row.WorkItemRevision!.Value,
                row.WorkItemInvocationId!.Value
            );
            var task = await taskResolver.ResolveFreshAsync(
                new(
                    work.TenantId,
                    work.RelationshipId,
                    row.ActorId.Value,
                    currentMandate.ActorRole,
                    relationship.StateVersion,
                    currentMandate.AgentInstanceId,
                    row.SkillId,
                    currentMandate.SkillVersion,
                    row.IdempotencyKey.Value,
                    claimedTask
                ),
                cancellationToken
            );
            if (task is null)
                throw new ConversationNotAccessibleException();
            var execution = await db.Executions.SingleAsync(
                value =>
                    value.TenantId == work.TenantId && value.ExecutionId == row.ExecutionId.Value,
                cancellationToken
            );
            await runtimeIdentity.RequireCurrentAsync(
                db,
                execution,
                row.ActorId.Value,
                cancellationToken
            );
            if (
                !await relationshipDb.ChannelBindings.AnyAsync(
                    binding =>
                        binding.BindingId == row.ChannelBindingId.Value
                        && binding.TenantId == work.TenantId
                        && binding.RelationshipId == work.RelationshipId
                        && binding.ParticipantId == row.ActorId.Value
                        && binding.Channel == "WHATSAPP"
                        && binding.Status == "ACTIVE"
                        && binding.ExternalSubjectHash == row.RecipientDigest,
                    cancellationToken
                )
            )
                throw new ConversationNotAccessibleException();
            var scope = new ConversationBatchScope(
                row.Environment,
                work.TenantId,
                work.RelationshipId,
                work.ConversationId,
                row.ActorId.Value,
                currentMandate.ActorRole,
                row.ChannelBindingId!.Value,
                row.RecipientDigest!,
                currentMandate.AgentInstanceId,
                row.SkillId,
                currentMandate.SkillVersion,
                row.Language,
                SharedAuthorityDigest(currentMandate),
                task
            );
            candidates.Add(
                new(
                    row.MessageId,
                    row.ExecutionId.Value,
                    row.Sequence,
                    row.AdmittedAt!.Value,
                    row.Text,
                    scope
                )
            );
            mandates[row.MessageId] = currentMandate;
        }

        var selection = ConversationBatchWindow.Select(candidates, options.Value.ToLimits());
        if (work.BatchId is not null)
        {
            var recoverySources = BuildSources(candidates, mandates);
            var preparedRecovery = HttpConversationExecutionGateway.PrepareBatchExecution(
                work.BatchId.Value,
                recoverySources
            );
            var persisted = await db
                .Database.SqlQuery<DispatchBindingRow>(
                    $"""
                    SELECT source_list_digest AS "SourceListDigest",
                           request_digest AS "RequestDigest",
                           runtime_execution_id AS "RuntimeExecutionId"
                    FROM business.conversation_batch_groups
                    WHERE tenant_id = {work.TenantId} AND batch_id = {work.BatchId.Value}
                    """
                )
                .SingleAsync(cancellationToken);
            if (
                persisted.SourceListDigest != preparedRecovery.SourceListDigest
                || persisted.RequestDigest != preparedRecovery.RequestDigest
                || persisted.RuntimeExecutionId == Guid.Empty
            )
                throw new ConversationStateConflictException();
            await transaction.CommitAsync(cancellationToken);
            try
            {
                await batchGateway.StartBatchAsync(
                    work.ConversationId,
                    work.BatchId.Value,
                    persisted.RuntimeExecutionId,
                    work.RelationshipId,
                    recoverySources,
                    cancellationToken
                );
                await TransitionAfterDispatchAsync(
                    work,
                    work.BatchId.Value,
                    work.DispatchState,
                    "STARTED",
                    null,
                    cancellationToken
                );
            }
            catch (Exception failure) when (failure is not OperationCanceledException)
            {
                logger.LogWarning(
                    "Conversation batch recovery remains unresolved. FailureType={FailureType}",
                    failure.GetType().Name
                );
                if (work.DispatchState == "DISPATCHING")
                    await TransitionAfterDispatchAsync(
                        work,
                        work.BatchId.Value,
                        "DISPATCHING",
                        "UNRESOLVED",
                        "RUNTIME_OUTCOME_UNKNOWN",
                        cancellationToken
                    );
            }
            return true;
        }
        if (selection.ReadyMembers.Count < 2)
        {
            var source = candidates[0];
            var mandate = mandates[source.MessageId];
            await transaction.CommitAsync(cancellationToken);
            await gateway.StartAsync(
                work.ConversationId,
                source.ExecutionId,
                source.MessageId,
                work.RelationshipId,
                source.Scope.Language,
                [new("1.0", "TEXT", source.Text, source.Scope.Language)],
                mandate,
                mandate.IdempotencyIdentity,
                cancellationToken
            );
            await CompleteIndividualAsync(work, cancellationToken);
            return true;
        }

        var members = selection.ReadyMembers;
        var batchId = work.ClaimId;
        var batchTask = members[0].Scope.Task ?? throw new ConversationStateConflictException();
        await ConversationPendingStartAdmission.FreezeAsync(
            db,
            members[0].Scope.Environment,
            work.TenantId,
            work.RelationshipId,
            work.ConversationId,
            batchId,
            selection,
            options.Value.ToLimits(),
            cancellationToken,
            new(
                directory.WorkerId,
                work.FencingToken,
                work.LeaseExpiresAt,
                batchTask.WorkItemId,
                batchTask.Revision,
                members[0].AcceptedAt.Add(options.Value.ToLimits().MaximumWait)
            )
        );
        var sources = BuildSources(members, mandates);
        var prepared = HttpConversationExecutionGateway.PrepareBatchExecution(batchId, sources);
        var runtimeExecutionId = ConversationExecutionIdentity.Create(
            work.TenantId,
            work.RelationshipId,
            members[0].Scope.ActorId,
            work.ConversationId,
            batchId
        );
        if (
            !await TransitionAsync(
                db,
                work,
                batchId,
                "CLAIMED",
                "DISPATCHING",
                prepared.SourceListDigest,
                prepared.RequestDigest,
                runtimeExecutionId,
                null,
                cancellationToken
            ) || !await FinishClaimAsync(db, work, "CONSUMED", null, cancellationToken)
        )
            throw new ConversationStateConflictException();
        await transaction.CommitAsync(cancellationToken);

        try
        {
            await stopFence.ThrowIfLatchedAsync(
                work.TenantId,
                work.RelationshipId,
                cancellationToken
            );
            await batchGateway.StartBatchAsync(
                work.ConversationId,
                batchId,
                runtimeExecutionId,
                work.RelationshipId,
                sources,
                cancellationToken
            );
            await TransitionAfterDispatchAsync(
                work,
                batchId,
                "DISPATCHING",
                "STARTED",
                null,
                cancellationToken
            );
        }
        catch (Exception failure) when (failure is not OperationCanceledException)
        {
            logger.LogWarning(
                "Conversation batch dispatch requires reconciliation. FailureType={FailureType}",
                failure.GetType().Name
            );
            await TransitionAfterDispatchAsync(
                work,
                batchId,
                "DISPATCHING",
                "UNRESOLVED",
                "RUNTIME_OUTCOME_UNKNOWN",
                cancellationToken
            );
        }
        return true;
    }

    private static async Task<IReadOnlyList<SourceRow>> ReadSourcesAsync(
        ConversationStoreDbContext db,
        ConversationBatchWork work,
        int limit,
        CancellationToken cancellationToken
    ) =>
        await db
            .Database.SqlQuery<SourceRow>(
                $"""
                SELECT message.message_id AS "MessageId", message.sequence AS "Sequence",
                       message.environment AS "Environment", message.skill_id AS "SkillId",
                       message.content_json -> 0 ->> 'text' AS "Text",
                       coalesce(message.content_json -> 0 ->> 'language', 'en') AS "Language",
                       pending.execution_id AS "ExecutionId", pending.actor_id AS "ActorId",
                       pending.idempotency_key AS "IdempotencyKey",
                       pending.evidence_id AS "EvidenceId", pending.admitted_at AS "AdmittedAt",
                       pending.work_item_id AS "WorkItemId",
                       pending.work_item_revision AS "WorkItemRevision",
                       pending.work_item_invocation_id AS "WorkItemInvocationId",
                       execution.origin_channel_binding_id AS "ChannelBindingId",
                       execution.origin_recipient_digest AS "RecipientDigest",
                       mandate.mandate_json::text AS "MandateJson"
                FROM business.conversation_messages AS first_message
                JOIN business.conversation_messages AS message
                  ON message.tenant_id = first_message.tenant_id
                 AND message.conversation_id = first_message.conversation_id
                 AND message.sequence >= first_message.sequence
                LEFT JOIN business.conversation_pending_starts AS pending
                  ON pending.tenant_id = message.tenant_id
                 AND pending.message_id = message.message_id
                LEFT JOIN business.conversation_executions AS execution
                  ON execution.tenant_id = pending.tenant_id
                 AND execution.execution_id = pending.execution_id
                LEFT JOIN business.operational_mandate_snapshots AS mandate
                  ON mandate.tenant_id = pending.tenant_id
                 AND mandate.mandate_id = pending.mandate_id
                WHERE first_message.tenant_id = {work.TenantId}
                  AND first_message.message_id = {work.FirstMessageId}
                ORDER BY message.sequence
                LIMIT {limit}
                """
            )
            .ToListAsync(cancellationToken);

    private static async Task<IReadOnlyList<SourceRow>> ReadFrozenSourcesAsync(
        ConversationStoreDbContext db,
        ConversationBatchWork work,
        CancellationToken cancellationToken
    ) =>
        await db
            .Database.SqlQuery<SourceRow>(
                $"""
                SELECT message.message_id AS "MessageId", message.sequence AS "Sequence",
                       message.environment AS "Environment", message.skill_id AS "SkillId",
                       message.content_json -> 0 ->> 'text' AS "Text",
                       coalesce(message.content_json -> 0 ->> 'language', 'en') AS "Language",
                       pending.execution_id AS "ExecutionId", pending.actor_id AS "ActorId",
                       pending.idempotency_key AS "IdempotencyKey",
                       pending.evidence_id AS "EvidenceId", pending.admitted_at AS "AdmittedAt",
                       pending.work_item_id AS "WorkItemId",
                       pending.work_item_revision AS "WorkItemRevision",
                       pending.work_item_invocation_id AS "WorkItemInvocationId",
                       execution.origin_channel_binding_id AS "ChannelBindingId",
                       execution.origin_recipient_digest AS "RecipientDigest",
                       mandate.mandate_json::text AS "MandateJson"
                FROM business.conversation_batch_members AS member
                JOIN business.conversation_messages AS message
                  ON message.tenant_id = member.tenant_id AND message.message_id = member.message_id
                JOIN business.conversation_pending_starts AS pending
                  ON pending.tenant_id = member.tenant_id AND pending.message_id = member.message_id
                JOIN business.conversation_executions AS execution
                  ON execution.tenant_id = pending.tenant_id AND execution.execution_id = pending.execution_id
                JOIN business.operational_mandate_snapshots AS mandate
                  ON mandate.tenant_id = pending.tenant_id AND mandate.mandate_id = pending.mandate_id
                WHERE member.tenant_id = {work.TenantId}
                  AND member.batch_id = {work.BatchId!.Value}
                ORDER BY member.ordinal
                """
            )
            .ToListAsync(cancellationToken);

    private static HttpConversationExecutionGateway.BatchExecutionSource[] BuildSources(
        IReadOnlyList<ConversationBatchCandidate> members,
        IReadOnlyDictionary<Guid, OperationalMandateV1> mandates
    ) =>
        members
            .Select(member =>
            {
                var mandate = mandates[member.MessageId];
                return new HttpConversationExecutionGateway.BatchExecutionSource(
                    "1.0",
                    member.MessageId,
                    member.ExecutionId,
                    member.Sequence,
                    member.Scope.Task!.WorkItemId,
                    member.Scope.Task.Revision,
                    member.Scope.Task.InvocationId,
                    mandate.IdempotencyIdentity,
                    Guid.Parse(mandate.ConstitutionalEvidenceRef["ce-evidence:".Length..]),
                    member.Text,
                    member.Scope.Language,
                    mandate
                );
            })
            .ToArray();

    private async Task CompleteIndividualAsync(
        ConversationBatchWork work,
        CancellationToken cancellationToken
    )
    {
        await using var db = await conversations.CreateDbContextAsync(cancellationToken);
        var completed = await db
            .Database.SqlQuery<bool>(
                $"SELECT business.complete_individual_pending_start({work.ClaimId}, {directory.WorkerId}, {work.FencingToken}) AS \"Value\""
            )
            .SingleAsync(cancellationToken);
        if (!completed)
            throw new ConversationStateConflictException();
    }

    private async Task TransitionAfterDispatchAsync(
        ConversationBatchWork work,
        Guid batchId,
        string expected,
        string next,
        string? failure,
        CancellationToken cancellationToken
    )
    {
        await using var db = await conversations.CreateDbContextAsync(cancellationToken);
        if (
            !await TransitionAsync(
                db,
                work,
                batchId,
                expected,
                next,
                null,
                null,
                null,
                failure,
                cancellationToken
            )
        )
            throw new ConversationStateConflictException();
    }

    private async Task<bool> TransitionAsync(
        ConversationStoreDbContext db,
        ConversationBatchWork work,
        Guid batchId,
        string expected,
        string next,
        string? sourceDigest,
        string? requestDigest,
        Guid? runtimeExecutionId,
        string? failure,
        CancellationToken cancellationToken
    ) =>
        await db
            .Database.SqlQuery<bool>(
                $"""
                SELECT business.transition_conversation_batch(
                    {work.TenantId}, {batchId}, {directory.WorkerId},
                    {work.FencingToken}, {expected}, {next}, {sourceDigest}, {requestDigest},
                    {runtimeExecutionId}, {failure}) AS "Value"
                """
            )
            .SingleAsync(cancellationToken);

    private async Task<bool> FinishClaimAsync(
        ConversationStoreDbContext db,
        ConversationBatchWork work,
        string state,
        string? failure,
        CancellationToken cancellationToken
    ) =>
        await db
            .Database.SqlQuery<bool>(
                $"SELECT business.finish_conversation_batch_claim({work.ClaimId}, {directory.WorkerId}, {work.FencingToken}, {state}, {failure}) AS \"Value\""
            )
            .SingleAsync(cancellationToken);

    private static string SharedAuthorityDigest(OperationalMandateV1 mandate)
    {
        var canonical = JsonSerializer.Serialize(
            new
            {
                mandate.TenantId,
                mandate.RelationshipId,
                mandate.AgentInstanceId,
                mandate.ActorId,
                mandate.ActorRole,
                mandate.RelationshipLifecycle,
                mandate.ProfessionalVersion,
                mandate.AdmissionRevision,
                mandate.SkillId,
                mandate.SkillVersion,
                mandate.ContextRevision,
                mandate.ConfigurationRevision,
                mandate.GoalRevision,
                mandate.DecisionSpaceRevision,
                mandate.CustomerContractDigest,
            },
            JsonOptions
        );
        return Convert
            .ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(canonical)))
            .ToLowerInvariant();
    }

    private sealed class SourceRow
    {
        public Guid MessageId { get; init; }
        public long Sequence { get; init; }
        public string Environment { get; init; } = string.Empty;
        public string SkillId { get; init; } = string.Empty;
        public string Text { get; init; } = string.Empty;
        public string Language { get; init; } = string.Empty;
        public Guid? ExecutionId { get; init; }
        public Guid? ActorId { get; init; }
        public Guid? IdempotencyKey { get; init; }
        public Guid? EvidenceId { get; init; }
        public DateTimeOffset? AdmittedAt { get; init; }
        public Guid? WorkItemId { get; init; }
        public int? WorkItemRevision { get; init; }
        public Guid? WorkItemInvocationId { get; init; }
        public Guid? ChannelBindingId { get; init; }
        public string? RecipientDigest { get; init; }
        public string? MandateJson { get; init; }
    }

    private sealed class DispatchBindingRow
    {
        public string SourceListDigest { get; init; } = string.Empty;
        public string RequestDigest { get; init; } = string.Empty;
        public Guid RuntimeExecutionId { get; init; }
    }
}

public sealed class ConversationBatchDispatchHostedService(
    IServiceScopeFactory scopes,
    ConversationBatchWorkScope workScope,
    TimeProvider clock,
    ILogger<ConversationBatchDispatchHostedService> logger
) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(1), clock);
        while (await timer.WaitForNextTickAsync(stoppingToken))
        {
            try
            {
                await using var scope = scopes.CreateAsyncScope();
                var directory =
                    scope.ServiceProvider.GetRequiredService<ConversationBatchWorkDirectory>();
                var work = await directory.ClaimAsync(stoppingToken);
                if (work is null)
                    continue;
                using var capability = workScope.Begin(work);
                await scope
                    .ServiceProvider.GetRequiredService<ConversationBatchDispatchWorker>()
                    .ProcessOneAsync(stoppingToken);
            }
            catch (Exception failure)
                when (failure
                        is ConversationExecutionUnavailableException
                            or ConversationStateConflictException
                            or ConversationNotAccessibleException
                            or OperationalMandateUnavailableException
                            or ConversationStoppedException
                            or DbUpdateException
                            or Npgsql.NpgsqlException
                )
            {
                logger.LogWarning(
                    "Conversation batch work deferred. FailureType={FailureType}",
                    failure.GetType().Name
                );
            }
        }
    }
}
