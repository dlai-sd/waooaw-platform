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
    string ContextVersion,
    string Channel,
    Guid IdempotencyKey,
    string PayloadReference,
    string PayloadDigest,
    bool PublishToWhatsApp,
    WhatsAppOutboundEligibility? WhatsAppEligibility,
    ConversationConclusionV1? Conclusion = null,
    string? ContinuationReason = null
);

public sealed record OutboundConversationReceiptV1(
    Guid MessageId,
    Guid ConversationId,
    long Sequence,
    bool Replayed,
    bool WhatsAppQueued
);

public sealed class ConversationOutboundContributionService(
    IDbContextFactory<ConversationStoreDbContext> dbFactory,
    IConversationReferenceResolver references,
    ConversationStopFence stopFence,
    IOptions<Wc120ConversationOptions> options
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
                now,
                cancellationToken
            );
        }
        finally
        {
            gate.Release();
        }
    }

    private async Task<OutboundConversationReceiptV1> CommitCoreAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        OutboundConversationContributionV1 contribution,
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
        var requestDigest = Digest(contribution);
        if (replay is not null)
        {
            if (!string.Equals(replay.RequestHash, requestDigest, StringComparison.Ordinal))
                throw new ConversationIdempotencyConflictException();
            var prior =
                JsonSerializer.Deserialize<OutboundConversationReceiptV1>(
                    replay.ResponseJson,
                    new JsonSerializerOptions(JsonSerializerDefaults.Web)
                ) ?? throw new ConversationStateConflictException();
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
            queued
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
        await transaction.CommitAsync(cancellationToken);
        return receipt;
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
            || string.IsNullOrWhiteSpace(value.ContextVersion)
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
        && !string.IsNullOrWhiteSpace(value.Purpose)
        && !string.IsNullOrWhiteSpace(value.RecipientBindingDigest)
        && (
            (
                value.LastInboundAt.HasValue
                && value.LastInboundAt <= now
                && now - value.LastInboundAt <= TimeSpan.FromHours(24)
            )
            || (
                value.TemplateApproved
                && !string.IsNullOrWhiteSpace(value.TemplateName)
                && !string.IsNullOrWhiteSpace(value.TemplateVersion)
                && !string.IsNullOrWhiteSpace(value.TemplateLocale)
                && !string.IsNullOrWhiteSpace(value.TemplateCategory)
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
