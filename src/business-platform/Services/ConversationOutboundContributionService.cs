// Implements: WC120-R005, WC120-R010, WC120-R014
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using System.Collections.Concurrent;
using System.Data;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record ConversationConclusionV1(
    string Understanding,
    string Analysis,
    string Recommendation,
    string CustomerDecision,
    string NextAction,
    IReadOnlyList<string> OpenItems,
    string EvidenceState
);

public sealed record OutboundConversationContributionV1(
    string ActorKind,
    string ContributionKind,
    string DialogueAct,
    string Content,
    string ContextKey,
    string? ContextVersion,
    string Channel,
    Guid IdempotencyKey,
    string PayloadReference,
    string PayloadDigest,
    bool PublishToWhatsApp,
    WhatsAppOutboundEligibility? WhatsAppEligibility,
    ConversationConclusionV1? Conclusion = null,
    string? ContinuationReason = null,
    string? JourneyStatus = null,
    string? JourneyStage = null
);

public sealed record OutboundConversationReceiptV1(
    Guid MessageId,
    Guid ConversationId,
    long Sequence,
    bool Replayed,
    bool WhatsAppQueued,
    string? JourneyStatus = null,
    string? JourneyStage = null
);

public sealed class ConversationOutboundContributionService(
    IDbContextFactory<ConversationStoreDbContext> dbFactory,
    IConversationReferenceResolver references,
    ConversationStopFence stopFence,
    IOptions<Wc120ConversationOptions> options,
    WhatsAppTenantExecutionScope? whatsAppExecution = null,
    WhatsAppRelationshipRouting? whatsAppRouting = null
)
{
    private static readonly ConcurrentDictionary<string, SemaphoreSlim> CommitGates = new();
    private static readonly HashSet<string> ActorKinds = new(StringComparer.Ordinal)
    {
        "PROFESSIONAL",
        "SYSTEM",
    };
    private static readonly HashSet<string> ContributionKinds = new(StringComparer.Ordinal)
    {
        "TEXT",
        "TYPED_CARD",
        "TYPED_COMMAND_OUTCOME",
    };
    private static readonly HashSet<string> DialogueActs = new(StringComparer.Ordinal)
    {
        "ACKNOWLEDGE",
        "INFORM",
        "ASK",
        "CONFIRM_INFERENCE",
        "PRESENT_RESEARCH",
        "PRESENT_RECOMMENDATION",
        "PRESENT_OPTIONS",
        "REQUEST_DECISION",
        "WARN",
        "DISCLOSE_LIMITATION",
        "SUMMARIZE",
        "CONCLUDE",
        "ESCALATE",
        "HANDOFF",
    };
    private static readonly HashSet<string> ContinuationReasons = new(StringComparer.Ordinal)
    {
        "AWAITING_CUSTOMER_INPUT",
        "AWAITING_OWNER_RESULT",
        "BLOCKED_BY_POLICY",
        "ASSURANCE_REQUIRED",
        "MORE_RESEARCH_REQUIRED",
    };

    public async Task<OutboundConversationReceiptV1> CommitAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        OutboundConversationContributionV1 contribution,
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        return await CommitWithGateAsync(
            tenantId,
            participantId,
            relationshipId,
            contribution,
            null,
            null,
            null,
            now,
            cancellationToken
        );
    }

    internal async Task<OutboundConversationReceiptV1> CommitClarificationQuestionAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        OutboundConversationContributionV1 contribution,
        IReadOnlyList<Guid> sourceMessageIds,
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        var route =
            whatsAppExecution?.RequireConfirmedRelationshipRoute()
            ?? throw new WhatsAppCapabilityUnavailableException("CLARIFICATION_ROUTE_REQUIRED");
        if (
            contribution.ActorKind != "SYSTEM"
            || contribution.DialogueAct != "ASK"
            || contribution.Channel != "WHATSAPP"
            || contribution.Content != ConversationRequestClarification.Question
            || !contribution.PublishToWhatsApp
            || contribution.WhatsAppEligibility?.Purpose != "CUSTOMER_REQUEST"
            || route.Environment != options.Value.Environment
            || route.TenantId != tenantId
            || route.ParticipantId != participantId
            || route.RelationshipId != relationshipId
            || route.SenderHash != contribution.WhatsAppEligibility.RecipientBindingDigest
            || sourceMessageIds.Count is < 2 or > 3
            || sourceMessageIds.Any(value => value == Guid.Empty)
            || sourceMessageIds.Distinct().Count() != sourceMessageIds.Count
        )
            throw new ConversationRequestException("Clarification question is invalid.");

        return await CommitWithGateAsync(
            tenantId,
            participantId,
            relationshipId,
            contribution,
            sourceMessageIds,
            route.ParticipantRole,
            route.RelationshipVersion,
            now,
            cancellationToken
        );
    }

    private async Task<OutboundConversationReceiptV1> CommitWithGateAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        OutboundConversationContributionV1 contribution,
        IReadOnlyList<Guid>? clarificationSourceMessageIds,
        string? clarificationActorRole,
        int? clarificationRelationshipVersion,
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        var gateKey = $"{options.Value.Environment}:{tenantId:D}:{relationshipId:D}";
        var gate = CommitGates.GetOrAdd(gateKey, static _ => new SemaphoreSlim(1, 1));
        await gate.WaitAsync(cancellationToken);
        try
        {
            return await CommitCoreAsync(
                tenantId,
                participantId,
                relationshipId,
                contribution,
                clarificationSourceMessageIds,
                clarificationActorRole,
                clarificationRelationshipVersion,
                now,
                cancellationToken
            );
        }
        finally
        {
            gate.Release();
        }
    }

    public async Task<(
        OutboundConversationReceiptV1 Receipt,
        string Text
    )?> RecoverJourneyReplyAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid idempotencyKey,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        await using var routingRead = await WhatsAppRelationshipRouting.BeginIngressReadAsync(
            whatsAppExecution,
            whatsAppRouting,
            db,
            options.Value.Environment,
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        var outcome = await db
            .IdempotencyOutcomes.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.ActorParticipantId == participantId
                    && value.OperationFamily == "OUTBOUND_CONTRIBUTION"
                    && value.IdempotencyKey == idempotencyKey,
                cancellationToken
            );
        if (outcome is null)
        {
            WhatsAppRelationshipRouting.RequireIngressReadRelease(whatsAppExecution);
            return null;
        }
        var receipt =
            JsonSerializer.Deserialize<OutboundConversationReceiptV1>(
                outcome.ResponseJson,
                new JsonSerializerOptions(JsonSerializerDefaults.Web)
            ) ?? throw new ConversationStateConflictException();
        if (receipt.JourneyStatus is null || receipt.JourneyStage is null)
            throw new ConversationStateConflictException();
        var message = await db
            .Messages.AsNoTracking()
            .SingleAsync(
                value =>
                    value.Environment == options.Value.Environment
                    && value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.MessageId == receipt.MessageId,
                cancellationToken
            );
        WhatsAppRelationshipRouting.RequireIngressReadRelease(whatsAppExecution);
        return (receipt, ConversationService.ToContract(message).Content.Single().Text);
    }

    private async Task<OutboundConversationReceiptV1> CommitCoreAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        OutboundConversationContributionV1 contribution,
        IReadOnlyList<Guid>? clarificationSourceMessageIds,
        string? clarificationActorRole,
        int? clarificationRelationshipVersion,
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        Validate(contribution);
        if (!options.Value.Enabled)
            throw new ConversationExecutionUnavailableException();
        await stopFence.ThrowIfLatchedAsync(tenantId, relationshipId, cancellationToken);

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.Serializable,
            cancellationToken
        );
        var replay = await db.IdempotencyOutcomes.SingleOrDefaultAsync(
            value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ActorParticipantId == participantId
                && value.OperationFamily == "OUTBOUND_CONTRIBUTION"
                && value.IdempotencyKey == contribution.IdempotencyKey,
            cancellationToken
        );
        var requestDigest = clarificationSourceMessageIds is null
            ? Digest(contribution)
            : DigestClarificationQuestion(contribution, clarificationSourceMessageIds);
        if (replay is not null)
        {
            if (!string.Equals(replay.RequestHash, requestDigest, StringComparison.Ordinal))
                throw new ConversationIdempotencyConflictException();
            await WhatsAppRelationshipRouting.RequireIngressReadAsync(
                whatsAppExecution,
                whatsAppRouting,
                db,
                options.Value.Environment,
                tenantId,
                participantId,
                relationshipId,
                cancellationToken
            );
            var prior =
                JsonSerializer.Deserialize<OutboundConversationReceiptV1>(
                    replay.ResponseJson,
                    new JsonSerializerOptions(JsonSerializerDefaults.Web)
                ) ?? throw new ConversationStateConflictException();
            WhatsAppRelationshipRouting.RequireIngressReadRelease(whatsAppExecution);
            await transaction.CommitAsync(cancellationToken);
            return prior with { Replayed = true };
        }

        var conversation = await db.Conversations.SingleOrDefaultAsync(
            value =>
                value.Environment == options.Value.Environment
                && value.TenantId == tenantId
                && value.RelationshipId == relationshipId,
            cancellationToken
        );
        if (conversation is null)
        {
            conversation = new ConversationProjection
            {
                Environment = options.Value.Environment,
                TenantId = tenantId,
                RelationshipId = relationshipId,
            };
            db.Conversations.Add(conversation);
        }
        var resolved = await references.ResolveAsync(
            tenantId,
            participantId,
            relationshipId,
            conversation.ConversationId,
            contribution.ContextKey,
            contribution.ContextVersion,
            contribution.Channel,
            cancellationToken
        );
        await WhatsAppRelationshipRouting.RequireIngressCommitAsync(
            whatsAppExecution,
            whatsAppRouting,
            db,
            tenantId,
            participantId,
            relationshipId,
            conversation.ConversationId,
            contribution.Channel,
            null,
            contribution.WhatsAppEligibility?.RecipientBindingDigest,
            cancellationToken
        );
        await ConversationPendingStartAdmission.LockConversationAsync(
            db,
            options.Value.Environment,
            tenantId,
            relationshipId,
            cancellationToken
        );
        if (db.Entry(conversation).State != EntityState.Added)
            await db.Entry(conversation).ReloadAsync(cancellationToken);
        var sequence = conversation.NextMessageSequence++;
        conversation.UpdatedAt = now;
        var message = new ConversationMessage
        {
            Environment = options.Value.Environment,
            TenantId = tenantId,
            ConversationId = conversation.ConversationId,
            RelationshipId = relationshipId,
            Sequence = sequence,
            Actor = contribution.ActorKind,
            Channel = contribution.Channel,
            ContributionKind = contribution.ContributionKind,
            DialogueAct = contribution.DialogueAct,
            SkillId = contribution.ContextKey,
            ContentJson = JsonSerializer.Serialize(
                new[] { new ConversationTextBlockV1("1.0", "TEXT", contribution.Content, "en-IN") }
            ),
            ConclusionJson = contribution.Conclusion is null
                ? null
                : JsonSerializer.Serialize(contribution.Conclusion),
            InteractionContextJson = JsonSerializer.Serialize(resolved.Context),
            ConversationPolicyJson = JsonSerializer.Serialize(resolved.Policy),
            DeliveryState = contribution.PublishToWhatsApp ? "ACCEPTED" : "NOT_REQUIRED",
            ProcessingState = "COMPLETED",
            EvidenceState = "PENDING",
            AcceptedAt = now,
            CompletedAt = now,
        };
        db.Messages.Add(message);
        db.Events.Add(
            new ConversationEvent
            {
                TenantId = tenantId,
                ConversationId = conversation.ConversationId,
                RelationshipId = relationshipId,
                Sequence = conversation.NextEventSequence++,
                EventType = "message.completed",
                MessageId = message.MessageId,
                DataJson = JsonSerializer.Serialize(
                    new { message = ConversationService.ToContract(message) },
                    new JsonSerializerOptions(JsonSerializerDefaults.Web)
                ),
                OccurredAt = now,
            }
        );

        var queued = false;
        if (contribution.PublishToWhatsApp)
        {
            var eligibility =
                contribution.WhatsAppEligibility ?? throw new ConversationStateConflictException();
            if (!InitialEligibility(eligibility, now))
                throw new ConversationStateConflictException();
            db.ConversationOutbox.Add(
                new ConversationOutboxRecord
                {
                    Environment = options.Value.Environment,
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    ConversationId = conversation.ConversationId,
                    Sequence = sequence,
                    AggregateId = message.MessageId.ToString("D"),
                    OperationFamily = "WHATSAPP_OUTBOUND",
                    IdempotencyKey = contribution.IdempotencyKey,
                    PayloadDigest = contribution.PayloadDigest,
                    PayloadReference = contribution.PayloadReference,
                    Purpose = eligibility.Purpose,
                    RecipientBindingDigest = eligibility.RecipientBindingDigest,
                    TemplateName = eligibility.TemplateName,
                    TemplateVersion = eligibility.TemplateVersion,
                    TemplateLocale = eligibility.TemplateLocale,
                    TemplateCategory = eligibility.TemplateCategory,
                    NextAttemptAt = now,
                    CreatedAt = now,
                    UpdatedAt = now,
                }
            );
            queued = true;
        }

        var receipt = new OutboundConversationReceiptV1(
            message.MessageId,
            conversation.ConversationId,
            sequence,
            false,
            queued,
            contribution.JourneyStatus,
            contribution.JourneyStage
        );
        db.IdempotencyOutcomes.Add(
            new ConversationIdempotencyOutcome
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ActorParticipantId = participantId,
                OperationFamily = "OUTBOUND_CONTRIBUTION",
                IdempotencyKey = contribution.IdempotencyKey,
                RequestHash = requestDigest,
                MessageId = message.MessageId,
                Outcome = "ACCEPTED",
                ResponseJson = JsonSerializer.Serialize(receipt),
                CreatedAt = now,
                CompletedAt = now,
            }
        );
        await db.SaveChangesAsync(cancellationToken);
        if (clarificationSourceMessageIds is not null)
            await PersistClarificationQuestionAsync(
                db,
                tenantId,
                participantId,
                relationshipId,
                conversation.ConversationId,
                message.MessageId,
                options.Value.Environment,
                clarificationActorRole ?? throw new ConversationStateConflictException(),
                clarificationRelationshipVersion ?? throw new ConversationStateConflictException(),
                contribution.WhatsAppEligibility!.RecipientBindingDigest,
                clarificationSourceMessageIds,
                cancellationToken
            );
        if (whatsAppExecution?.ServiceTenantId is not null)
            whatsAppExecution.RequireUnchangedAuthority();
        await transaction.CommitAsync(cancellationToken);
        return receipt;
    }

    internal static async Task PersistClarificationQuestionAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid conversationId,
        Guid questionMessageId,
        string environment,
        string actorRole,
        int relationshipVersion,
        string recipientDigest,
        IReadOnlyList<Guid> sourceMessageIds,
        CancellationToken cancellationToken
    )
    {
        if (db.Database.CurrentTransaction is null)
            throw new InvalidOperationException(
                "Clarification questions require the canonical outbound transaction."
            );
        if (
            tenantId == Guid.Empty
            || participantId == Guid.Empty
            || relationshipId == Guid.Empty
            || conversationId == Guid.Empty
            || questionMessageId == Guid.Empty
            || string.IsNullOrWhiteSpace(actorRole)
            || relationshipVersion < 0
            || !IsDigest(recipientDigest)
            || sourceMessageIds.Count is < 2 or > 3
            || sourceMessageIds.Any(value => value == Guid.Empty)
            || sourceMessageIds.Distinct().Count() != sourceMessageIds.Count
        )
            throw new ConversationRequestException("Clarification source scope is invalid.");
        await ConversationPendingStartAdmission.LockConversationAsync(
            db,
            environment,
            tenantId,
            relationshipId,
            cancellationToken
        );
        var sourceIds = sourceMessageIds.ToArray();
        var questionId = Guid.NewGuid();
        var inserted = await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.conversation_request_questions
                (tenant_id, relationship_id, conversation_id, question_id, question_message_id,
                 environment, actor_id, actor_role, relationship_version, agent_instance_id,
                 channel_binding_id, recipient_digest)
            SELECT {tenantId}, {relationshipId}, {conversationId}, {questionId}, {questionMessageId},
                {environment}, {participantId}, {actorRole}, {relationshipVersion},
                (array_agg(mandate.agent_instance_id ORDER BY requested.ordinal))[1],
                (array_agg(execution.origin_channel_binding_id ORDER BY requested.ordinal))[1],
                (array_agg(execution.origin_recipient_digest ORDER BY requested.ordinal))[1]
            FROM unnest({sourceIds}) WITH ORDINALITY AS requested(message_id, ordinal)
            JOIN business.conversation_pending_starts AS pending
                ON pending.tenant_id = {tenantId} AND pending.message_id = requested.message_id
            JOIN business.conversation_messages AS source
                ON source.tenant_id = pending.tenant_id AND source.message_id = pending.message_id
            JOIN business.conversation_executions AS execution
                ON execution.tenant_id = pending.tenant_id AND execution.execution_id = pending.execution_id
            JOIN business.operational_mandate_snapshots AS mandate
                ON mandate.tenant_id = pending.tenant_id AND mandate.mandate_id = pending.mandate_id
            JOIN business.conversation_messages AS question
                ON question.tenant_id = {tenantId} AND question.relationship_id = {relationshipId}
                AND question.conversation_id = {conversationId} AND question.message_id = {questionMessageId}
            WHERE source.environment = {environment}
                AND source.relationship_id = {relationshipId}
                AND source.conversation_id = {conversationId}
                AND source.actor = 'CUSTOMER' AND source.channel = 'WHATSAPP'
                AND source.evidence_state = 'RECORDED'
                AND pending.actor_id = {participantId}
                AND mandate.actor_participant_id = {participantId}
                AND mandate.deadline > statement_timestamp()
                AND execution.origin_channel_binding_id IS NOT NULL
                AND execution.origin_recipient_digest = {recipientDigest}
                AND question.environment = {environment}
                AND question.actor = 'SYSTEM' AND question.channel = 'WHATSAPP'
                AND question.dialogue_act = 'ASK'
            HAVING count(*) = cardinality({sourceIds})
                AND count(DISTINCT requested.message_id) = cardinality({sourceIds})
                AND max(source.sequence) - min(source.sequence) + 1 = count(*)
                AND min(source.sequence) < max(source.sequence)
                AND count(DISTINCT pending.actor_id) = 1
                AND count(DISTINCT mandate.agent_instance_id) = 1
                AND count(DISTINCT execution.origin_channel_binding_id) = 1
                AND count(DISTINCT execution.origin_recipient_digest) = 1
                AND min(source.sequence - requested.ordinal) = max(source.sequence - requested.ordinal)
                AND bool_and(source.sequence < question.sequence)
            """,
            cancellationToken
        );
        if (inserted != 1)
            throw new ConversationStateConflictException();

        var membersInserted = await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.conversation_request_question_members
                (tenant_id, relationship_id, conversation_id, question_id, message_id, ordinal)
            SELECT {tenantId}, {relationshipId}, {conversationId}, {questionId},
                requested.message_id, requested.ordinal::INTEGER
            FROM unnest({sourceIds}) WITH ORDINALITY AS requested(message_id, ordinal)
            ORDER BY requested.ordinal
            """,
            cancellationToken
        );
        if (membersInserted != sourceIds.Length)
            throw new ConversationStateConflictException();

        var frozen = await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.conversation_request_questions
            SET frozen_at = statement_timestamp(), member_count = {sourceIds.Length}
            WHERE tenant_id = {tenantId} AND question_id = {questionId}
            """,
            cancellationToken
        );
        if (frozen != 1)
            throw new ConversationStateConflictException();
    }

    internal static void Validate(OutboundConversationContributionV1 value)
    {
        if (
            !ActorKinds.Contains(value.ActorKind)
            || !ContributionKinds.Contains(value.ContributionKind)
            || !DialogueActs.Contains(value.DialogueAct)
            || string.IsNullOrWhiteSpace(value.Content)
            || value.Content.Length > 32_000
            || string.IsNullOrWhiteSpace(value.ContextKey)
            || (value.ContextVersion is not null && string.IsNullOrWhiteSpace(value.ContextVersion))
            || string.IsNullOrWhiteSpace(value.PayloadReference)
            || !IsDigest(value.PayloadDigest)
        )
            throw new ConversationRequestException("Outbound contribution is invalid.");
        if (
            value.DialogueAct == "CONCLUDE"
            && !Complete(value.Conclusion)
            && (
                string.IsNullOrWhiteSpace(value.ContinuationReason)
                || !ContinuationReasons.Contains(value.ContinuationReason)
            )
        )
            throw new ConversationRequestException(
                "Material conclusion requires complete fields or a typed continuation reason."
            );
    }

    private static bool Complete(ConversationConclusionV1? value) =>
        value is not null
        && !string.IsNullOrWhiteSpace(value.Understanding)
        && !string.IsNullOrWhiteSpace(value.Analysis)
        && !string.IsNullOrWhiteSpace(value.Recommendation)
        && !string.IsNullOrWhiteSpace(value.CustomerDecision)
        && !string.IsNullOrWhiteSpace(value.NextAction)
        && value.OpenItems is not null
        && !string.IsNullOrWhiteSpace(value.EvidenceState);

    private static bool InitialEligibility(WhatsAppOutboundEligibility value, DateTimeOffset now) =>
        value.OptedIn
        && !value.OptedOut
        && !value.RelationshipStopped
        && value.Purpose == "CUSTOMER_REQUEST"
        && !string.IsNullOrWhiteSpace(value.RecipientBindingDigest)
        && value.TemplateName is null
        && value.TemplateVersion is null
        && value.TemplateLocale is null
        && value.TemplateCategory is null
        && value.LastInboundAt.HasValue
        && value.LastInboundAt <= now
        && now - value.LastInboundAt <= TimeSpan.FromHours(24);

    internal static string DigestClarificationQuestion(
        OutboundConversationContributionV1 contribution,
        IReadOnlyList<Guid> sourceMessageIds
    ) =>
        Convert.ToHexStringLower(
            SHA256.HashData(
                Encoding.UTF8.GetBytes(
                    JsonSerializer.Serialize(new { contribution, sourceMessageIds })
                )
            )
        );

    private static string Digest(OutboundConversationContributionV1 value) =>
        Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(value)))
        );

    private static bool IsDigest(string value) =>
        value.Length == 64
        && value.All(character => character is >= '0' and <= '9' or >= 'a' and <= 'f');
}
