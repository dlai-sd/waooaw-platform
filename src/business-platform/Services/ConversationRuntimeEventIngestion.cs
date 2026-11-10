// Implements: WC-134 R006/R007; canonical runtime projection and restart checkpoints.
// constitutional_basis: C-001, C-005, C-023, C-059, C-063
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record ConversationRuntimeSource(
    Guid TenantId,
    Guid RelationshipId,
    Guid ExecutionId,
    Guid ConversationId,
    Guid MessageId,
    Guid IdempotencyKey,
    ConversationExecutionCallerV1 Caller,
    long AfterSequence,
    Guid? OriginChannelBindingId,
    string? OriginRecipientDigest
);

public sealed class ConversationRuntimeEventIngestion(
    IDbContextFactory<ConversationStoreDbContext> conversations,
    IDbContextFactory<EmploymentRelationshipDbContext> relationships,
    IOptions<Wc120ConversationOptions> options,
    TimeProvider clock,
    ConversationCursorCodec cursors,
    ConversationRuntimeIdentityAuthority? identity = null
)
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    public async Task<ConversationRuntimeSource> GetSourceAsync(
        Guid tenantId,
        Guid executionId,
        CancellationToken cancellationToken
    )
    {
        await using var db = await conversations.CreateDbContextAsync(cancellationToken);
        await using var authority = await relationships.CreateDbContextAsync(cancellationToken);
        return await GetSourceAsync(db, authority, tenantId, executionId, cancellationToken);
    }

    internal async Task<ConversationRuntimeSource> GetSourceAsync(
        ConversationStoreDbContext db,
        EmploymentRelationshipDbContext authority,
        Guid tenantId,
        Guid executionId,
        CancellationToken cancellationToken,
        ConversationReconciliationAuthority? permission = null
    )
    {
        var execution =
            await db
                .Executions.AsNoTracking()
                .SingleOrDefaultAsync(
                    value => value.TenantId == tenantId && value.ExecutionId == executionId,
                    cancellationToken
                )
            ?? throw new ConversationNotAccessibleException();
        if (permission is not null)
        {
            if (
                identity is null
                || permission.TenantId != tenantId
                || permission.ExecutionId != executionId
            )
                throw new ConversationNotAccessibleException();
            await ConversationReconciliationBinding.RequirePermissionAsync(
                db,
                authority,
                identity,
                permission,
                clock.GetUtcNow(),
                cancellationToken,
                clock
            );
            var bound = await ConversationReconciliationBinding.SourceAsync(
                db,
                authority,
                execution,
                options.Value.Environment,
                cancellationToken
            );
            if (ConversationReconciliationBinding.Digest(bound.Original) != permission.SourceDigest)
                throw new ConversationStateConflictException();
            return bound.Source;
        }
        var input =
            await db
                .Messages.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.MessageId == execution.MessageId
                        && value.RelationshipId == execution.RelationshipId
                        && value.ConversationId == execution.ConversationId
                        && value.Environment == options.Value.Environment
                        && value.Actor == "CUSTOMER"
                        && value.SchemaVersion == "1.0",
                    cancellationToken
                )
            ?? throw new ConversationStateConflictException();
        var origin =
            await db
                .IdempotencyOutcomes.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.RelationshipId == execution.RelationshipId
                        && value.ExecutionId == executionId
                        && value.MessageId == input.MessageId
                        && value.OperationFamily == "SEND",
                    cancellationToken
                )
            ?? throw new ConversationStateConflictException();
        if (db.Database.IsRelational())
        {
            if (identity is null)
                throw new ConversationExecutionUnavailableException();
            await identity.RequireCurrentAsync(
                db,
                execution,
                origin.ActorParticipantId,
                cancellationToken
            );
        }
        var participant =
            await authority
                .RelationshipParticipants.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.RelationshipId == execution.RelationshipId
                        && value.ParticipantId == origin.ActorParticipantId
                        && value.Status == "ACTIVE",
                    cancellationToken
                )
            ?? throw new ConversationNotAccessibleException();
        var relationship =
            await authority
                .EmploymentRelationships.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.RelationshipId == execution.RelationshipId,
                    cancellationToken
                )
            ?? throw new ConversationNotAccessibleException();
        if (
            relationship.State == EmploymentRelationshipState.StoppedEmergency
            || relationship.StoppedAt is not null
        )
            throw new ConversationStoppedException();
        if (
            await db.EmergencyStopLatches.AnyAsync(
                row =>
                    row.TenantId == tenantId
                    && row.RelationshipId == execution.RelationshipId
                    && row.Environment == options.Value.Environment
                    && (row.State == "LATCHED" || row.State == "EVIDENCE_CONFIRMED"),
                cancellationToken
            )
        )
            throw new ConversationStoppedException();
        if (input.EvidenceRecordId is not { } evidence || evidence == Guid.Empty)
            throw new ConversationStateConflictException();
        return new(
            tenantId,
            execution.RelationshipId,
            executionId,
            execution.ConversationId,
            input.MessageId,
            origin.IdempotencyKey,
            new(
                tenantId,
                execution.RelationshipId,
                origin.ActorParticipantId,
                RelationshipRoleCodec.ToDatabase(participant.Role),
                $"ce-decision:{evidence:D}",
                ConversationExecutionIdentity.Create(
                    tenantId,
                    execution.RelationshipId,
                    origin.ActorParticipantId,
                    execution.ConversationId,
                    origin.IdempotencyKey
                )
            ),
            execution.RuntimeSequence,
            execution.OriginChannelBindingId,
            execution.OriginRecipientDigest
        );
    }

    public async Task ApplyAsync(
        ConversationRuntimeSource source,
        RuntimeExecutionEventV1 value,
        CancellationToken cancellationToken
    )
    {
        await using var db = await conversations.CreateDbContextAsync(cancellationToken);
        await using var transaction = db.Database.IsRelational()
            ? await db.Database.BeginTransactionAsync(cancellationToken)
            : null;
        await ApplyEventAsync(db, transaction, source, value, null, cancellationToken);
        if (transaction is not null)
            await transaction.CommitAsync(cancellationToken);
    }

    public async Task<ConversationReconciliationOutcomeV1> ApplyReconciliationAsync(
        ConversationRuntimeSource source,
        Guid authorityId,
        RuntimeReconciliationResultV1 result,
        CancellationToken cancellationToken
    )
    {
        await using var db = await conversations.CreateDbContextAsync(cancellationToken);
        if (!db.Database.IsRelational() || identity is null)
            throw new ConversationExecutionUnavailableException();
        await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT ai_runtime.lock_employment_dispatch({source.TenantId}, {source.RelationshipId.ToString("D")})",
            cancellationToken
        );
        if (
            await db
                .Database.SqlQuery<int>(
                    $"SELECT 1 AS \"Value\" FROM constitutional.employment_dispatch_stops WHERE tenant_id = {source.TenantId} AND relationship_ref = {source.RelationshipId.ToString("D")}"
                )
                .AnyAsync(cancellationToken)
        )
            throw new ConversationStoppedException();
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT execution_id FROM business.conversation_executions WHERE tenant_id = {source.TenantId} AND execution_id = {source.ExecutionId} FOR UPDATE",
            cancellationToken
        );
        var permission =
            await db.ReconciliationAuthorities.SingleOrDefaultAsync(
                value =>
                    value.TenantId == source.TenantId
                    && value.AuthorityId == authorityId
                    && value.ExecutionId == source.ExecutionId,
                cancellationToken
            ) ?? throw new ConversationNotAccessibleException();
        await using var currentAuthority = new EmploymentRelationshipDbContext(
            new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                .UseNpgsql(db.Database.GetDbConnection())
                .Options
        );
        await currentAuthority.Database.UseTransactionAsync(
            transaction.GetDbTransaction(),
            cancellationToken
        );
        var currentSource = await GetSourceAsync(
            db,
            currentAuthority,
            source.TenantId,
            source.ExecutionId,
            cancellationToken,
            permission
        );
        if (
            currentSource.Caller != source.Caller
            || currentSource.IdempotencyKey != source.IdempotencyKey
            || currentSource.ConversationId != source.ConversationId
            || currentSource.MessageId != source.MessageId
            || currentSource.RelationshipId != source.RelationshipId
            || currentSource.OriginChannelBindingId != source.OriginChannelBindingId
            || currentSource.OriginRecipientDigest != source.OriginRecipientDigest
        )
            throw new ConversationStateConflictException();
        var execution = await db.Executions.SingleAsync(
            value => value.TenantId == source.TenantId && value.ExecutionId == source.ExecutionId,
            cancellationToken
        );
        var original = await ConversationReconciliationBinding.SourceAsync(
            db,
            currentAuthority,
            execution,
            options.Value.Environment,
            cancellationToken
        );
        HttpConversationExecutionGateway.ValidateReconciliationShape(
            result,
            original.Original,
            permission,
            source.AfterSequence
        );
        if (permission.ResponseJson is { } replay)
        {
            if (
                permission.ResultDigest != result.ResultDigest
                || permission.OriginalRequestDigest != result.OriginalRequestDigest
            )
                throw new ConversationIdempotencyConflictException();
            foreach (var value in result.Events)
            {
                var receipt = await db
                    .RuntimeEventReceipts.AsNoTracking()
                    .SingleOrDefaultAsync(
                        row =>
                            row.TenantId == source.TenantId
                            && row.ExecutionId == source.ExecutionId
                            && row.Sequence == value.Sequence,
                        cancellationToken
                    );
                var digest = AgentAdmissionCanonicalizer.Digest(
                    JsonSerializer.SerializeToElement(value, Json)
                )["sha256:".Length..];
                if (receipt is null || receipt.EventDigest != digest)
                    throw new ConversationIdempotencyConflictException();
            }
            if (!execution.RuntimeTerminal || execution.ProcessingState != result.State)
                throw new ConversationStateConflictException();
            await ConversationReconciliationBinding.RequirePermissionAsync(
                db,
                currentAuthority,
                identity,
                permission,
                clock.GetUtcNow(),
                cancellationToken,
                clock
            );
            return (
                JsonSerializer.Deserialize<ConversationReconciliationOutcomeV1>(replay, Json)
                ?? throw new ConversationStateConflictException()
            ) with
            {
                Replayed = true,
            };
        }
        if (
            execution.ProjectionVersion != permission.ExpectedProjectionVersion
            || execution.RuntimeSequence != source.AfterSequence
            || result.SchemaVersion != "1.0"
            || result.ReconciliationAuthorityId != authorityId
            || result.OriginalSourceDigest != permission.SourceDigest
            || result.ConversationId != source.ConversationId
            || result.ExecutionId != source.Caller.RuntimeExecutionId
            || result.OriginalMessageId != source.MessageId
            || result.State is not ("COMPLETED" or "FAILED" or "CANCELLED")
            || result.ResultDigest is null
            || result.OriginalRequestDigest is null
        )
            throw new ConversationStateConflictException();
        foreach (var value in result.Events)
            await ApplyEventAsync(db, transaction, source, value, permission, cancellationToken);
        if (!execution.RuntimeTerminal || execution.ProcessingState != result.State)
            throw new ConversationStateConflictException();
        var outcome = new ConversationReconciliationOutcomeV1(
            "1.0",
            source.ExecutionId,
            result.State,
            "RECONCILE_CANONICAL_PROJECTION",
            execution.ProjectionVersion,
            false
        );
        await ConversationReconciliationBinding.RequirePermissionAsync(
            db,
            currentAuthority,
            identity,
            permission,
            clock.GetUtcNow(),
            cancellationToken,
            clock
        );
        permission.OriginalRequestDigest = result.OriginalRequestDigest;
        permission.ResultDigest = result.ResultDigest;
        permission.ResponseJson = JsonSerializer.Serialize(outcome, Json);
        await db.SaveChangesAsync(cancellationToken);
        if (permission.ExpiresAt <= clock.GetUtcNow())
            throw new ConversationNotAccessibleException();
        await transaction.CommitAsync(cancellationToken);
        return outcome;
    }

    private async Task ApplyEventAsync(
        ConversationStoreDbContext db,
        IDbContextTransaction? transaction,
        ConversationRuntimeSource source,
        RuntimeExecutionEventV1 value,
        ConversationReconciliationAuthority? permission,
        CancellationToken cancellationToken
    )
    {
        if (
            source.TenantId != source.Caller.TenantId
            || source.RelationshipId != source.Caller.RelationshipId
        )
            throw new ConversationNotAccessibleException();
        if (
            source.TenantId == Guid.Empty
            || source.ExecutionId == Guid.Empty
            || value.SchemaVersion != "1.0"
            || value.ConversationId != source.ConversationId
            || value.ExecutionId != source.Caller.RuntimeExecutionId
            || value.MessageId != source.MessageId
            || value.Sequence < 1
            || value.EventId != $"{value.ExecutionId:D}:{value.Sequence}"
            || value.OccurredAt == default
            || value.Data.ValueKind != JsonValueKind.Object
        )
            throw new ConversationStateConflictException();
        RuntimeEventStreamReader.ValidatePayload(value);
        RuntimeEventStreamReader.ValidateUniqueProperties(value.Data);
        if (value.EventType == "heartbeat")
            throw new ConversationStateConflictException();
        var digest = AgentAdmissionCanonicalizer.Digest(
            JsonSerializer.SerializeToElement(value, Json)
        )["sha256:".Length..];
        if (transaction is not null)
        {
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT ai_runtime.lock_employment_dispatch({source.TenantId}, {source.RelationshipId.ToString("D")})",
                cancellationToken
            );
            if (
                await db
                    .Database.SqlQuery<int>(
                        $"SELECT 1 AS \"Value\" FROM constitutional.employment_dispatch_stops WHERE tenant_id = {source.TenantId} AND relationship_ref = {source.RelationshipId.ToString("D")}"
                    )
                    .AnyAsync(cancellationToken)
            )
                throw new ConversationStoppedException();
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT execution_id FROM business.conversation_executions WHERE tenant_id = {source.TenantId} AND execution_id = {source.ExecutionId} FOR UPDATE",
                cancellationToken
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT conversation_id FROM business.conversations WHERE tenant_id = {source.TenantId} AND conversation_id = {source.ConversationId} FOR UPDATE",
                cancellationToken
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT relationship_id FROM business.employment_relationships WHERE tenant_id = {source.TenantId} AND relationship_id = {source.RelationshipId} FOR SHARE",
                cancellationToken
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT binding_id FROM business.relationship_participants WHERE tenant_id = {source.TenantId} AND relationship_id = {source.RelationshipId} AND participant_id = {permission?.RequesterId ?? source.Caller.ActorId} FOR SHARE",
                cancellationToken
            );
        }
        await using var currentAuthority = transaction is null
            ? await relationships.CreateDbContextAsync(cancellationToken)
            : new EmploymentRelationshipDbContext(
                new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                    .UseNpgsql(db.Database.GetDbConnection())
                    .Options
            );
        if (transaction is not null)
            await currentAuthority.Database.UseTransactionAsync(
                transaction.GetDbTransaction(),
                cancellationToken
            );
        var current = await GetSourceAsync(
            db,
            currentAuthority,
            source.TenantId,
            source.ExecutionId,
            cancellationToken,
            permission
        );
        if (
            current.Caller != source.Caller
            || current.IdempotencyKey != source.IdempotencyKey
            || current.RelationshipId != source.RelationshipId
            || current.ConversationId != source.ConversationId
            || current.MessageId != source.MessageId
            || current.OriginChannelBindingId != source.OriginChannelBindingId
            || current.OriginRecipientDigest != source.OriginRecipientDigest
        )
            throw new ConversationNotAccessibleException();
        var prior = await db.RuntimeEventReceipts.SingleOrDefaultAsync(
            receipt =>
                receipt.TenantId == source.TenantId
                && receipt.ExecutionId == source.ExecutionId
                && receipt.Sequence == value.Sequence,
            cancellationToken
        );
        if (prior is not null)
        {
            if (
                !CryptographicOperations.FixedTimeEquals(
                    Encoding.ASCII.GetBytes(prior.EventDigest),
                    Encoding.ASCII.GetBytes(digest)
                )
            )
                throw new ConversationIdempotencyConflictException();
            return;
        }
        var execution = await db.Executions.SingleAsync(
            row => row.TenantId == source.TenantId && row.ExecutionId == source.ExecutionId,
            cancellationToken
        );
        if (execution.ProcessingState == "STOPPED")
            throw new ConversationStoppedException();
        if (
            execution.RuntimeTerminal
            || execution.ProcessingState == "CANCELLED"
            || value.Sequence != execution.RuntimeSequence + 1
        )
            throw new ConversationStateConflictException();
        var input = await db.Messages.SingleAsync(
            row => row.TenantId == source.TenantId && row.MessageId == source.MessageId,
            cancellationToken
        );
        if (transaction is not null)
        {
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT message_id FROM business.conversation_messages WHERE tenant_id = {source.TenantId} AND message_id = {source.MessageId} FOR UPDATE",
                cancellationToken
            );
            await db.Entry(input).ReloadAsync(cancellationToken);
        }
        var conversation = await db.Conversations.SingleAsync(
            row =>
                row.TenantId == source.TenantId
                && row.ConversationId == source.ConversationId
                && row.Environment == options.Value.Environment,
            cancellationToken
        );
        var now = clock.GetUtcNow();
        ConversationMessage? reply = execution.RuntimeReplyMessageId is { } replyId
            ? await db.Messages.SingleAsync(
                row => row.TenantId == source.TenantId && row.MessageId == replyId,
                cancellationToken
            )
            : null;
        var releasesReply =
            reply is not null && value.EventType is "execution.completed" or "execution.failed";
        if (
            permission is null
            && (
                value.EventType is "response.delta" or "response.system" or "card.proposed"
                || releasesReply
            )
        )
        {
            var mandate = await currentAuthority
                .OperationalMandateSnapshots.AsNoTracking()
                .SingleOrDefaultAsync(
                    row =>
                        row.TenantId == source.TenantId
                        && row.RelationshipId == source.RelationshipId
                        && row.ActorParticipantId == source.Caller.ActorId
                        && row.IdempotencyIdentity == source.IdempotencyKey,
                    cancellationToken
                );
            if (mandate is null || mandate.Deadline <= now)
                throw new ConversationNotAccessibleException();
            if (transaction is not null)
            {
                try
                {
                    await new OperationalMandateResolver(relationships).ValidateExistingAsync(
                        currentAuthority,
                        source.TenantId,
                        source.Caller.ActorId,
                        source.RelationshipId,
                        source.IdempotencyKey,
                        input.EvidenceRecordId ?? Guid.Empty,
                        input.SkillId,
                        JsonSerializer
                            .Deserialize<List<ConversationTextBlockV1>>(input.ContentJson, Json)
                            ?.FirstOrDefault()
                            ?.Text
                            ?? throw new ConversationStateConflictException(),
                        cancellationToken
                    );
                }
                catch (OperationalMandateUnavailableException)
                {
                    throw new ConversationNotAccessibleException();
                }
            }
        }
        if (
            value.EventType == "execution.completed"
            && (reply is null || reply.Actor != "PROFESSIONAL")
        )
            throw new ConversationStateConflictException();
        if (value.EventType is "response.delta" or "response.system" or "card.proposed")
        {
            if (value.EventType == "response.system" && reply is { Actor: "PROFESSIONAL" })
            {
                reply.ProcessingState = "FAILED";
                reply.Partial = true;
                reply.CompletionReason = "PARTIAL_FAILURE";
                reply.CompletedAt = now;
                reply = null;
            }
            if (reply is null)
            {
                reply = new ConversationMessage
                {
                    Environment = input.Environment,
                    TenantId = input.TenantId,
                    RelationshipId = input.RelationshipId,
                    ConversationId = input.ConversationId,
                    Sequence = conversation.NextMessageSequence++,
                    Channel = input.Channel,
                    Actor = value.EventType == "response.system" ? "SYSTEM" : "PROFESSIONAL",
                    SkillId = input.SkillId,
                    InteractionContextJson = input.InteractionContextJson,
                    ConversationPolicyJson = input.ConversationPolicyJson,
                    DeliveryState = "ACCEPTED",
                    ProcessingState = "RUNNING",
                    EvidenceState = "PENDING",
                    AcceptedAt = now,
                };
                execution.RuntimeReplyMessageId = reply.MessageId;
                db.Messages.Add(reply);
            }
            if ((value.EventType == "response.system") != (reply.Actor == "SYSTEM"))
                throw new ConversationStateConflictException();
            if (value.EventType == "card.proposed")
            {
                var cards = JsonSerializer.Deserialize<List<JsonElement>>(reply.CardsJson) ?? [];
                cards.Add(MapProposalCard(value.Data, source));
                reply.CardsJson = JsonSerializer.Serialize(cards);
                var prefix =
                    JsonSerializer
                        .Deserialize<List<ConversationTextBlockV1>>(reply.ContentJson, Json)
                        ?.Count > 0
                        ? "\n\n"
                        : "";
                SetText(
                    reply,
                    prefix + value.Data.GetProperty("effect").GetString()!,
                    input,
                    append: true
                );
            }
            else if (value.EventType == "response.system")
                SetText(reply, value.Data.GetProperty("text").GetString()!, input, append: false);
            else
            {
                if (value.Data.GetProperty("contentIndex").GetInt32() != 0)
                    throw new ConversationStateConflictException();
                SetText(
                    reply,
                    value.Data.GetProperty("appendText").GetString()!,
                    input,
                    append: true
                );
                reply.Partial = true;
            }
        }
        var publicType = value.EventType switch
        {
            "execution.accepted" or "processing.started" => "processing.started",
            "card.proposed" => "card.upserted",
            "execution.completed" => "message.completed",
            "execution.failed" => "message.failed",
            "execution.cancelled" => "stream.cancelled",
            "execution.stopped" => "stop.applied",
            "response.system" => "message.accepted",
            "evidence.pending" or "evidence.recorded" => "processing.started",
            _ => value.EventType,
        };
        if (
            value.EventType
            is "execution.completed"
                or "execution.failed"
                or "execution.cancelled"
                or "execution.stopped"
        )
        {
            if (
                execution.ProcessingState == "COMPLETED"
                && value.EventType != "execution.completed"
            )
                throw new ConversationStateConflictException();
            execution.RuntimeTerminal = true;
            execution.ProcessingState = value.Data.GetProperty("state").GetString()!;
            execution.Partial = value.Data.GetProperty("partial").GetBoolean();
            execution.CompletionReason = value.Data.GetProperty("completionReason").GetString();
            input.ProcessingState = execution.ProcessingState;
            input.Partial = execution.Partial;
            input.CompletionReason = execution.CompletionReason;
            input.CompletedAt = now;
            if (reply is not null)
            {
                reply.ProcessingState = execution.ProcessingState;
                reply.Partial = execution.Partial;
                reply.CompletionReason = execution.CompletionReason;
                reply.CompletedAt = now;
                if (execution.ProcessingState is not ("STOPPED" or "CANCELLED"))
                    await QueueReplyAsync(
                        db,
                        currentAuthority,
                        source,
                        reply,
                        conversation,
                        now,
                        cancellationToken,
                        permission
                    );
            }
        }
        else if (
            execution.ProcessingState != "COMPLETED"
            && value.EventType
                is "execution.accepted"
                    or "processing.started"
                    or "response.delta"
                    or "response.system"
                    or "card.proposed"
        )
            execution.ProcessingState = input.ProcessingState = "RUNNING";
        else if (value.EventType == "evidence.recorded")
        {
            // PR evidence is not CE confirmation; the customer projection remains pending.
            if (reply is not null)
                reply.EvidenceState = "PENDING";
        }
        conversation.UpdatedAt = now;
        execution.UpdatedAt = now;
        execution.RuntimeSequence = value.Sequence;
        execution.RuntimeNextAttemptAt = now.AddSeconds(45);
        db.RuntimeEventReceipts.Add(
            new()
            {
                TenantId = source.TenantId,
                ExecutionId = source.ExecutionId,
                Sequence = value.Sequence,
                EventDigest = digest,
                RecordedAt = now,
            }
        );
        db.Events.Add(
            new()
            {
                TenantId = source.TenantId,
                RelationshipId = source.RelationshipId,
                ConversationId = source.ConversationId,
                ExecutionId = source.ExecutionId,
                MessageId = reply?.MessageId ?? input.MessageId,
                Sequence = conversation.NextEventSequence++,
                EventType = publicType,
                OccurredAt = now,
                DataJson = PublicData(value, reply ?? input, conversation, source),
            }
        );
        await db.SaveChangesAsync(cancellationToken);
    }

    private string PublicData(
        RuntimeExecutionEventV1 value,
        ConversationMessage message,
        ConversationProjection conversation,
        ConversationRuntimeSource source
    )
    {
        object data = value.EventType switch
        {
            "response.delta" => new
            {
                contentIndex = value.Data.GetProperty("contentIndex").GetInt32(),
                appendText = value.Data.GetProperty("appendText").GetString(),
                partial = true,
            },
            "card.proposed" => new { card = MapProposalCard(value.Data, source) },
            "execution.failed" => new
            {
                code = value.Data.TryGetProperty("errorCode", out var code)
                && code.ValueKind == JsonValueKind.String
                    ? code.GetString()
                    : "PARTIAL_FAILURE",
                retryable = value.Data.TryGetProperty("errorCode", out var error)
                    && error.GetString() is "MODEL_UNAVAILABLE" or "INTERNAL_FAILURE",
                partial = message.Partial,
            },
            "reconciliation.required" => new
            {
                reason = value.Data.GetProperty("reason").GetString(),
                authoritativeCursor = cursors.Encode(
                    conversation.TenantId,
                    conversation.RelationshipId,
                    "timeline",
                    conversation.NextMessageSequence - 1
                ),
            },
            _ => new { message = ConversationService.ToContract(message) },
        };
        return JsonSerializer.Serialize(data, Json);
    }

    private static JsonElement MapProposalCard(JsonElement data, ConversationRuntimeSource source)
    {
        if (
            data.GetProperty("cardType").GetString() != "DECISION"
            || !data.GetProperty("data").TryGetProperty("employmentPatchProposal", out var proposal)
            || proposal.ValueKind != JsonValueKind.Object
            || !proposal.TryGetProperty("state", out var state)
            || state.ValueKind != JsonValueKind.String
            || state.GetString() != "PROPOSED"
            || !proposal.TryGetProperty("proposalId", out var id)
            || id.ValueKind != JsonValueKind.String
            || !id.TryGetGuid(out var proposalId)
            || proposalId != data.GetProperty("cardId").GetGuid()
            || !proposal.TryGetProperty("relationshipRef", out var relationship)
            || relationship.ValueKind != JsonValueKind.String
            || relationship.GetString() != source.RelationshipId.ToString("D")
            || !proposal.TryGetProperty("contributionRef", out var contribution)
            || contribution.ValueKind != JsonValueKind.String
            || contribution.GetString() != source.MessageId.ToString("D")
            || !proposal.TryGetProperty("operations", out var operations)
            || operations.ValueKind != JsonValueKind.Array
            || operations.GetArrayLength() is < 1 or > 100
        )
            throw new ConversationStateConflictException();
        return JsonSerializer.SerializeToElement(
            new
            {
                schemaVersion = "1.0",
                cardId = data.GetProperty("cardId").GetGuid(),
                cardType = "DECISION",
                owner = data.GetProperty("owner").GetString(),
                state = data.GetProperty("state").GetString(),
                effect = data.GetProperty("effect").GetString(),
                commands = Array.Empty<object>(),
                decisionState = "PROPOSED",
                authorityImpact = "No workspace change is applied until the customer confirms in the secure portal.",
                alternatives = new[]
                {
                    new
                    {
                        alternativeId = "REVIEW",
                        label = "Review proposal in portal",
                        effect = "Review the proposed update before deciding.",
                    },
                    new
                    {
                        alternativeId = "KEEP_CURRENT",
                        label = "Keep current workspace",
                        effect = "Do not apply the proposed update.",
                    },
                },
                data = data.GetProperty("data"),
            },
            Json
        );
    }

    private static void SetText(
        ConversationMessage reply,
        string text,
        ConversationMessage input,
        bool append
    )
    {
        var blocks =
            JsonSerializer.Deserialize<List<ConversationTextBlockV1>>(reply.ContentJson, Json)
            ?? [];
        var combined = append ? (blocks.SingleOrDefault()?.Text ?? "") + text : text;
        if (combined.Length > 32_000 || combined.Contains('\0'))
            throw new ConversationStateConflictException();
        reply.ContentJson = JsonSerializer.Serialize(
            new[]
            {
                new ConversationTextBlockV1(
                    "1.0",
                    "TEXT",
                    combined,
                    JsonSerializer
                        .Deserialize<List<ConversationTextBlockV1>>(input.ContentJson, Json)
                        ?.FirstOrDefault()
                        ?.Language
                ),
            },
            Json
        );
    }

    private async Task QueueReplyAsync(
        ConversationStoreDbContext db,
        EmploymentRelationshipDbContext authority,
        ConversationRuntimeSource source,
        ConversationMessage reply,
        ConversationProjection conversation,
        DateTimeOffset now,
        CancellationToken cancellationToken,
        ConversationReconciliationAuthority? permission = null
    )
    {
        if (reply.Channel != "WHATSAPP" || !options.Value.DispatchEnabled)
            return;
        if (db.Database.IsRelational())
        {
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT phone_hmac FROM business.whatsapp_journey_contacts WHERE tenant_id = {source.TenantId} AND phone_hmac = {source.OriginRecipientDigest} FOR SHARE",
                cancellationToken
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT binding_id FROM business.channel_bindings WHERE tenant_id = {source.TenantId} AND binding_id = {source.OriginChannelBindingId} FOR SHARE",
                cancellationToken
            );
        }
        var bindings = await authority
            .ChannelBindings.AsNoTracking()
            .Where(binding =>
                binding.TenantId == source.TenantId
                && binding.RelationshipId == source.RelationshipId
                && binding.BindingId == source.OriginChannelBindingId
                && binding.ExternalSubjectHash == source.OriginRecipientDigest
                && binding.ParticipantId == source.Caller.ActorId
                && binding.Status == "ACTIVE"
                && binding.Channel == "WHATSAPP"
                && binding.ConversationId == source.ConversationId.ToString("D")
            )
            .Take(2)
            .ToListAsync(cancellationToken);
        if (bindings.Count != 1)
        {
            DeliveryBlocked("RUNTIME_REPLY_BINDING_UNAVAILABLE");
            return;
        }
        var recipient = bindings[0].ExternalSubjectHash;
        var contacts = await authority
            .WhatsAppJourneyContacts.AsNoTracking()
            .Where(contact =>
                contact.TenantId == source.TenantId
                && contact.PhoneHmac == recipient
                && contact.OptedOutAt == null
                && contact.OptedInAt <= now
                && contact.LastInboundAt <= now
                && contact.LastInboundAt >= now.AddHours(-24)
            )
            .Take(2)
            .ToListAsync(cancellationToken);
        if (contacts.Count != 1)
        {
            DeliveryBlocked("RUNTIME_REPLY_CONSENT_OR_WINDOW_DENIED");
            return;
        }
        var blocks =
            JsonSerializer.Deserialize<List<ConversationTextBlockV1>>(reply.ContentJson, Json)
            ?? [];
        var text = blocks.SingleOrDefault()?.Text;
        if (string.IsNullOrWhiteSpace(text))
        {
            DeliveryBlocked("RUNTIME_REPLY_RENDERING_LIMIT");
            return;
        }
        if (text.Length > 4096)
        {
            var noticeText =
                reply.ProcessingState == "COMPLETED"
                    ? "Your response is available in the secure portal. It is too long for one WhatsApp message, so no content has been cut off. Open this relationship in the portal to read the full response and review any proposed changes."
                    : "Your request did not complete successfully. The available response is too long for one WhatsApp message. Open this relationship in the secure portal to read the full response and its limitations; no content has been cut off.";
            reply.DeliveryState = "UNRESOLVED";
            var notice = new ConversationMessage
            {
                Environment = reply.Environment,
                TenantId = reply.TenantId,
                RelationshipId = reply.RelationshipId,
                ConversationId = reply.ConversationId,
                Sequence = conversation.NextMessageSequence++,
                Actor = "SYSTEM",
                Channel = "WHATSAPP",
                SkillId = reply.SkillId,
                InteractionContextJson = reply.InteractionContextJson,
                ConversationPolicyJson = reply.ConversationPolicyJson,
                ContentJson = JsonSerializer.Serialize(
                    new[] { new ConversationTextBlockV1("1.0", "TEXT", noticeText, "en-IN") },
                    Json
                ),
                DeliveryState = "ACCEPTED",
                ProcessingState = "COMPLETED",
                CompletionReason = "COMPLETE",
                EvidenceState = "PENDING",
                AcceptedAt = now,
                CompletedAt = now,
            };
            db.Messages.Add(notice);
            db.Events.Add(
                new()
                {
                    TenantId = source.TenantId,
                    RelationshipId = source.RelationshipId,
                    ConversationId = source.ConversationId,
                    ExecutionId = source.ExecutionId,
                    MessageId = notice.MessageId,
                    Sequence = conversation.NextEventSequence++,
                    EventType = "message.completed",
                    OccurredAt = now,
                    DataJson = JsonSerializer.Serialize(
                        new { message = ConversationService.ToContract(notice) },
                        Json
                    ),
                }
            );
            reply = notice;
            text = noticeText;
        }
        db.ConversationOutbox.Add(
            new()
            {
                Environment = reply.Environment,
                TenantId = reply.TenantId,
                RelationshipId = reply.RelationshipId,
                ConversationId = reply.ConversationId,
                Sequence = reply.Sequence,
                AggregateId = reply.MessageId.ToString("D"),
                OperationFamily = "WHATSAPP_OUTBOUND",
                IdempotencyKey = reply.MessageId,
                PayloadReference = permission is null
                    ? $"runtime-reply:{source.ExecutionId:D}:{reply.MessageId:D}"
                    : $"runtime-recovery:{source.ExecutionId:D}:{reply.MessageId:D}:{permission.AuthorityId:D}",
                PayloadDigest = Convert.ToHexStringLower(
                    SHA256.HashData(Encoding.UTF8.GetBytes(text))
                ),
                Purpose = "CUSTOMER_REQUEST",
                RecipientBindingDigest = recipient,
                CreatedAt = now,
                UpdatedAt = now,
                NextAttemptAt = now,
            }
        );

        void DeliveryBlocked(string code)
        {
            reply.DeliveryState = "UNRESOLVED";
            db.OperationalSignals.Add(
                new()
                {
                    Environment = reply.Environment,
                    Category = "RUNTIME",
                    Code = code,
                    OccurredAt = now,
                }
            );
        }
    }
}
