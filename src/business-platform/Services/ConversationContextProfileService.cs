// Implements: architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md §25.2 WC120-P1
// Constitutional basis: C-005, C-023, C-026, C-059, C-062, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed class Wc120ConversationOptions
{
    public bool Enabled { get; set; }
    public bool CallbackAcceptanceEnabled { get; set; }
    public bool DispatchEnabled { get; set; }
    public string Environment { get; set; } = "local";
    public string AppBindingDigest { get; set; } = string.Empty;
    public string WabaBindingDigest { get; set; } = string.Empty;
    public string RecipientBindingDigest { get; set; } = string.Empty;
    public string PolicyVersion { get; set; } = string.Empty;
    public string InstitutionalPolicyVersion { get; set; } = string.Empty;
    public string InteractionPolicyVersion { get; set; } = string.Empty;
    public string ChannelRenderingPolicyVersion { get; set; } = string.Empty;
    public string? CustomerCommunicationProfileVersion { get; set; }
    public string? VocabularyPolicyVersion { get; set; }
    public string? LocaleAccessibilityPolicyVersion { get; set; }
}

public sealed record SourceVersionV1(string SourceType, string SourceReference, string Version);

public sealed record InteractionContextV1(
    Guid ContextId,
    string SchemaVersion,
    Guid RelationshipId,
    Guid ProfessionalInstanceId,
    Guid ConversationId,
    string Phase,
    string Purpose,
    string SubjectType,
    string SubjectReference,
    string? PendingIntentReference,
    long DecisionSpaceVersion,
    long? PlanVersion,
    long? ProfileVersion,
    string PolicyVersion,
    string Locale,
    string Channel,
    string AssuranceLevel,
    IReadOnlyList<SourceVersionV1> SourceVersions,
    string Freshness,
    DateTimeOffset ResolvedAt
);

public sealed record ConversationPolicyReferenceV1(
    string Version,
    string InstitutionalPolicyVersion,
    string ProfessionalPolicyVersion,
    string InteractionPolicyVersion,
    string? CustomerCommunicationProfileVersion,
    string? VocabularyPolicyVersion,
    string? LocaleAccessibilityPolicyVersion,
    string ChannelRenderingPolicyVersion
);

public sealed record CanonicalMessageV1(
    Guid MessageId,
    long Sequence,
    string ActorKind,
    string ContributionKind,
    string? Content,
    string? DialogueAct,
    DateTimeOffset AcceptedAt,
    InteractionContextV1 Context,
    ConversationPolicyReferenceV1 Policy,
    ConversationMessageStatesV1 States
);

public sealed record CanonicalConversationV1(
    Guid ConversationId,
    Guid RelationshipId,
    long CurrentSequence,
    InteractionContextV1 CurrentContext,
    ConversationPolicyReferenceV1 CurrentPolicy,
    IReadOnlyList<CanonicalMessageV1> Messages
);

public sealed record ResolvedConversationReferences(
    InteractionContextV1 Context,
    ConversationPolicyReferenceV1 Policy
);

public interface IConversationReferenceResolver
{
    Task<ResolvedConversationReferences> ResolveAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid conversationId,
        string requestedContext,
        string? expectedContextVersion,
        string channel,
        CancellationToken cancellationToken
    );
}

public sealed record ConversationCommandDescriptorV1(
    string Kind,
    string SubjectReference,
    string OperationId,
    string RequestSchema
);

public sealed record AvailableInteractionContextV1(
    string ContextKey,
    string Phase,
    string Purpose,
    string SubjectType,
    string RequiredAssurance,
    bool Available,
    string? UnavailableReason,
    IReadOnlyList<ConversationCommandDescriptorV1> AuthorizedCommands
);

public sealed record ContextProfileItemV1(
    Guid ObservationId,
    string SubjectType,
    string FactType,
    string Status,
    JsonElement Value,
    string SourceType,
    string SourceVersion,
    DateTimeOffset ObservedAt,
    DateTimeOffset? ValidUntil,
    Guid? PredecessorObservationId
);

public sealed record ContextProfileV1(
    long ProfileVersion,
    Guid RelationshipId,
    IReadOnlyList<ContextProfileItemV1> Items,
    DateTimeOffset RebuiltAt
);

public sealed record ContextCorrectionRequestV1(
    Guid ObservationId,
    string CorrectionType,
    JsonElement? CorrectedValue,
    string? Reason,
    long ExpectedProfileVersion,
    string PayloadDigest
);

public sealed record ConversationMessageStatesV1(
    string Delivery,
    string Execution,
    string CustomerDecision,
    string ConstitutionalEvidence
);

public sealed record RequestConversationDataRightV1(
    string RightType,
    string Scope,
    string AssuranceReference,
    string? Reason,
    string PayloadDigest
);

public sealed record ConversationOperationReceiptV1(
    Guid OperationId,
    string OperationType,
    string State,
    DateTimeOffset AcceptedAt,
    Guid CorrelationId
);

public sealed class ConversationContextConflictException(string code)
    : InvalidOperationException(code)
{
    public string Code { get; } = code;
}

public sealed class ConversationContextProfileService(
    IDbContextFactory<ConversationStoreDbContext> conversationFactory,
    IDbContextFactory<EmploymentRelationshipDbContext> relationshipFactory,
    ConversationalEmploymentService employmentService,
    IOptions<Wc120ConversationOptions>? options = null
) : IConversationReferenceResolver
{
    private readonly Wc120ConversationOptions _options = options?.Value ?? new();
    private static readonly IReadOnlyDictionary<string, string> CommandSchemas = new Dictionary<
        string,
        string
    >(StringComparer.Ordinal)
    {
        ["CONFIRM_INDUCTION_ITEM"] = "ConfirmInductionItemCommandV1",
        ["DEFER_INDUCTION_ITEM"] = "DeferInductionItemCommandV1",
        ["APPLY_CANDIDATE_PATCH"] = "ApplyCandidatePatchCommandV1",
        ["SUBMIT_PLAN_FOR_REVIEW"] = "SubmitPlanForReviewCommandV1",
        ["ACCEPT_PLAN_VERSION"] = "AcceptPlanVersionCommandV1",
        ["ACKNOWLEDGE_MATERIAL_CHANGE"] = "AcknowledgeMaterialChangeCommandV1",
        ["RESCHEDULE_WITHIN_TOLERANCE"] = "RescheduleWithinToleranceCommandV1",
        ["REQUEST_REASSESSMENT"] = "RequestReassessmentCommandV1",
        ["ACKNOWLEDGE_CORRECTIVE_PROPOSAL"] = "AcknowledgeCorrectiveProposalCommandV1",
    };

    private static readonly HashSet<string> DataRightTypes = new(StringComparer.Ordinal)
    {
        "EXPORT",
        "CORRECT",
        "ERASE",
    };
    private static readonly HashSet<string> DataRightScopes = new(StringComparer.Ordinal)
    {
        "CONVERSATION",
        "CONTEXT_PROFILE",
        "MEDIA",
        "ALL_ELIGIBLE",
    };

    public async Task<ResolvedConversationReferences> ResolveAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid conversationId,
        string requestedContext,
        string? expectedContextVersion,
        string channel,
        CancellationToken cancellationToken
    )
    {
        await EnsureMembershipAsync(tenantId, participantId, relationshipId, cancellationToken);
        var workspace =
            employmentService.GetWorkspace(tenantId, relationshipId)
            ?? throw new ConversationContextConflictException("CONVERSATION_CONTEXT_UNAVAILABLE");
        if (
            !string.IsNullOrWhiteSpace(expectedContextVersion)
            && !string.Equals(
                expectedContextVersion,
                workspace.WorkspaceVersion,
                StringComparison.Ordinal
            )
        )
            throw new ConversationContextConflictException("CONVERSATION_CONTEXT_STALE");
        EnsurePolicyConfiguration();

        await using var relationshipDb = await relationshipFactory.CreateDbContextAsync(
            cancellationToken
        );
        var relationship =
            await relationshipDb
                .EmploymentRelationships.AsNoTracking()
                .SingleOrDefaultAsync(
                    value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
                    cancellationToken
                )
            ?? throw new ConversationContextConflictException("CONVERSATION_NOT_ACCESSIBLE");
        await using var conversationDb = await conversationFactory.CreateDbContextAsync(
            cancellationToken
        );
        var profileVersion = await conversationDb
            .ContextObservations.AsNoTracking()
            .Where(value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.Current
            )
            .MaxAsync(value => (long?)value.Revision, cancellationToken);
        var phase = workspace.Phases.ContainsKey(requestedContext)
            ? requestedContext
            : workspace.Phases.Keys.OrderBy(value => value, StringComparer.Ordinal).FirstOrDefault()
                ?? throw new ConversationContextConflictException(
                    "CONVERSATION_CONTEXT_UNAVAILABLE"
                );
        var resolvedAt = DateTimeOffset.UtcNow;
        var sourceVersions = new List<SourceVersionV1>
        {
            new("EMPLOYMENT_WORKSPACE", relationshipId.ToString("D"), workspace.WorkspaceVersion),
            new("WORKSPACE_MANIFEST", relationshipId.ToString("D"), workspace.ManifestVersion),
            new("WBE", relationshipId.ToString("D"), workspace.WbeSourceVersion),
        };
        if (!string.IsNullOrWhiteSpace(relationship.ProfessionalVersion))
        {
            sourceVersions.Add(
                new(
                    "PROFESSIONAL",
                    relationship.AgentInstanceId.ToString("D"),
                    relationship.ProfessionalVersion
                )
            );
        }
        var policyVersion = ConfiguredOrFallback(
            _options.PolicyVersion,
            workspace.WorkspaceVersion
        );
        var policy = new ConversationPolicyReferenceV1(
            policyVersion,
            ConfiguredOrFallback(_options.InstitutionalPolicyVersion, workspace.ManifestVersion),
            relationship.ProfessionalVersion ?? workspace.ManifestVersion,
            ConfiguredOrFallback(_options.InteractionPolicyVersion, workspace.WorkspaceVersion),
            _options.CustomerCommunicationProfileVersion,
            _options.VocabularyPolicyVersion,
            _options.LocaleAccessibilityPolicyVersion,
            ConfiguredOrFallback(
                _options.ChannelRenderingPolicyVersion,
                $"legacy-{channel.ToLowerInvariant()}"
            )
        );
        var context = new InteractionContextV1(
            DeterministicGuid(
                $"{tenantId:D}:{relationshipId:D}:{conversationId:D}:{workspace.WorkspaceVersion}:{phase}:{channel}"
            ),
            "1.0",
            relationshipId,
            relationship.AgentInstanceId,
            conversationId,
            phase,
            phase,
            "EMPLOYMENT_RELATIONSHIP",
            relationshipId.ToString("D"),
            null,
            Math.Max(1, workspace.DecisionSpaceVersion),
            long.TryParse(workspace.CurrentPlanVersion, out var planVersion) ? planVersion : null,
            profileVersion,
            policyVersion,
            "en-IN",
            channel.ToUpperInvariant(),
            "TIER_1",
            sourceVersions,
            "CURRENT",
            resolvedAt
        );
        return new(context, policy);
    }

    private void EnsurePolicyConfiguration()
    {
        if (!_options.Enabled)
            return;
        if (
            string.IsNullOrWhiteSpace(_options.PolicyVersion)
            || string.IsNullOrWhiteSpace(_options.InstitutionalPolicyVersion)
            || string.IsNullOrWhiteSpace(_options.InteractionPolicyVersion)
            || string.IsNullOrWhiteSpace(_options.ChannelRenderingPolicyVersion)
        )
            throw new ConversationContextConflictException("CONVERSATION_POLICY_UNAVAILABLE");
    }

    public async Task<CanonicalConversationV1> GetCanonicalAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        long afterSequence,
        int pageSize,
        CancellationToken cancellationToken
    )
    {
        if (afterSequence < 0 || pageSize is < 1 or > 100)
            throw new ConversationContextConflictException("CONVERSATION_REQUEST_INVALID");
        await EnsureMembershipAsync(tenantId, participantId, relationshipId, cancellationToken);
        await using var db = await conversationFactory.CreateDbContextAsync(cancellationToken);
        var conversation =
            await db
                .Conversations.AsNoTracking()
                .SingleOrDefaultAsync(
                    value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
                    cancellationToken
                )
            ?? throw new ConversationContextConflictException("CONVERSATION_NOT_ACCESSIBLE");
        var messages = await db
            .Messages.AsNoTracking()
            .Where(value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.Sequence > afterSequence
            )
            .OrderBy(value => value.Sequence)
            .Take(pageSize)
            .ToListAsync(cancellationToken);
        var currentReferences = await ResolveAsync(
            tenantId,
            participantId,
            relationshipId,
            conversation.ConversationId,
            messages.LastOrDefault()?.SkillId ?? string.Empty,
            null,
            messages.LastOrDefault()?.Channel ?? "WEB",
            cancellationToken
        );
        var canonicalMessages = messages
            .Select(value =>
            {
                var context = DeserializeReference(
                    value.InteractionContextJson,
                    currentReferences.Context
                );
                var policy = DeserializeReference(
                    value.ConversationPolicyJson,
                    currentReferences.Policy
                );
                var content = JsonSerializer
                    .Deserialize<ConversationTextBlockV1[]>(
                        value.ContentJson,
                        new JsonSerializerOptions(JsonSerializerDefaults.Web)
                    )
                    ?.FirstOrDefault()
                    ?.Text;
                return new CanonicalMessageV1(
                    value.MessageId,
                    value.Sequence,
                    value.Actor,
                    value.ContributionKind,
                    content,
                    value.DialogueAct,
                    value.AcceptedAt,
                    context,
                    policy,
                    new(
                        MapDeliveryState(value.DeliveryState),
                        MapExecutionState(value.ProcessingState),
                        "NOT_REQUIRED",
                        MapEvidenceState(value.EvidenceState)
                    )
                );
            })
            .ToList();
        return new(
            conversation.ConversationId,
            relationshipId,
            conversation.NextMessageSequence - 1,
            currentReferences.Context,
            currentReferences.Policy,
            canonicalMessages
        );
    }

    public async Task<IReadOnlyList<AvailableInteractionContextV1>> ListAvailableContextsAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        await EnsureMembershipAsync(tenantId, participantId, relationshipId, cancellationToken);
        var workspace =
            employmentService.GetWorkspace(tenantId, relationshipId)
            ?? throw new ConversationContextConflictException("CONVERSATION_CONTEXT_UNAVAILABLE");
        return workspace
            .Phases.OrderBy(value => value.Key, StringComparer.Ordinal)
            .Select(value => new AvailableInteractionContextV1(
                value.Key,
                value.Key,
                value.Key,
                "EMPLOYMENT_RELATIONSHIP",
                "TIER_1",
                true,
                null,
                ReadAuthorizedCommands(value.Value)
            ))
            .ToList();
    }

    public async Task<bool> IsCurrentContextVersionAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        string contextVersion,
        CancellationToken cancellationToken
    )
    {
        await EnsureMembershipAsync(tenantId, participantId, relationshipId, cancellationToken);
        var workspace = employmentService.GetWorkspace(tenantId, relationshipId);
        return workspace is not null
            && string.Equals(workspace.WorkspaceVersion, contextVersion, StringComparison.Ordinal);
    }

    public async Task<ContextProfileV1> GetProfileAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        await EnsureMembershipAsync(tenantId, participantId, relationshipId, cancellationToken);
        await using var db = await conversationFactory.CreateDbContextAsync(cancellationToken);
        var observations = await db
            .ContextObservations.AsNoTracking()
            .Where(value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.Current
            )
            .OrderBy(value => value.Owner)
            .ThenBy(value => value.ObservationType)
            .ThenBy(value => value.Revision)
            .ToListAsync(cancellationToken);
        var now = DateTimeOffset.UtcNow;
        return new ContextProfileV1(
            observations.Count == 0 ? 1 : observations.Max(value => value.Revision),
            relationshipId,
            observations
                .Select(value => new ContextProfileItemV1(
                    value.ObservationId,
                    value.SubjectType,
                    value.ObservationType,
                    value.ExpiresAt <= now ? "STALE" : value.Status,
                    JsonSerializer.Deserialize<JsonElement>(value.ValueJson),
                    value.SourceType,
                    value.SourceVersion,
                    value.RecordedAt,
                    value.ExpiresAt,
                    value.SupersedesObservationId
                ))
                .ToList(),
            now
        );
    }

    public async Task<ContextProfileItemV1> CorrectAsync(
        string environment,
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        ContextCorrectionRequestV1 request,
        CancellationToken cancellationToken
    )
    {
        await EnsureMembershipAsync(tenantId, participantId, relationshipId, cancellationToken);
        ValidateDigest(request.PayloadDigest, nameof(request.PayloadDigest));
        if (
            request.CorrectionType is not ("CORRECT" or "DISPUTE" or "ERASE")
            || (request.CorrectionType == "CORRECT" && request.CorrectedValue is null)
        )
            throw new ConversationContextConflictException("CONVERSATION_CONTEXT_INVALID");

        await using var db = await conversationFactory.CreateDbContextAsync(cancellationToken);
        await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);
        var current = await db.ContextObservations.SingleOrDefaultAsync(
            value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ObservationId == request.ObservationId
                && value.Current,
            cancellationToken
        );
        if (current is null)
            throw new ConversationContextConflictException("CONVERSATION_NOT_ACCESSIBLE");
        var profileVersion = await db
            .ContextObservations.Where(value =>
                value.TenantId == tenantId && value.RelationshipId == relationshipId
            )
            .MaxAsync(value => value.Revision, cancellationToken);
        if (profileVersion != request.ExpectedProfileVersion)
            throw new ConversationContextConflictException("CONVERSATION_CONTEXT_VERSION_CONFLICT");

        current.Current = false;
        var created = new ConversationContextObservation
        {
            Environment = environment,
            TenantId = tenantId,
            RelationshipId = relationshipId,
            Owner = current.Owner,
            SubjectType = current.SubjectType,
            ObservationType = current.ObservationType,
            Status = request.CorrectionType switch
            {
                "CORRECT" => "CONFIRMED",
                "DISPUTE" => "DISPUTED",
                _ => "ERASED",
            },
            ValueJson =
                request.CorrectionType == "ERASE"
                    ? "null"
                    : JsonSerializer.Serialize(
                        request.CorrectedValue
                            ?? JsonSerializer.Deserialize<JsonElement>(current.ValueJson)
                    ),
            SourceType = "CUSTOMER_CORRECTION",
            SourceVersion = $"profile:{profileVersion + 1}",
            SourceReference = current.SourceReference,
            SourceDigest = request.PayloadDigest,
            Revision = profileVersion + 1,
            SupersedesObservationId = current.ObservationId,
        };
        db.ContextObservations.Add(created);
        var summaries = await db
            .ContextSummaries.Where(value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.Current
            )
            .ToListAsync(cancellationToken);
        foreach (var summary in summaries)
        {
            summary.Current = false;
            summary.InvalidationReason = "SOURCE_CORRECTED";
            summary.InvalidatedAt = DateTimeOffset.UtcNow;
        }
        await db.SaveChangesAsync(cancellationToken);
        await transaction.CommitAsync(cancellationToken);
        return new ContextProfileItemV1(
            created.ObservationId,
            created.SubjectType,
            created.ObservationType,
            created.Status,
            JsonSerializer.Deserialize<JsonElement>(created.ValueJson),
            created.SourceType,
            created.SourceVersion,
            created.RecordedAt,
            created.ExpiresAt,
            created.SupersedesObservationId
        );
    }

    public async Task<ConversationMessageStatesV1> GetMessageStatesAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid messageId,
        CancellationToken cancellationToken
    )
    {
        await EnsureMembershipAsync(tenantId, participantId, relationshipId, cancellationToken);
        await using var db = await conversationFactory.CreateDbContextAsync(cancellationToken);
        var message =
            await db
                .Messages.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.RelationshipId == relationshipId
                        && value.MessageId == messageId,
                    cancellationToken
                )
            ?? throw new ConversationContextConflictException("CONVERSATION_MESSAGE_NOT_FOUND");
        return new ConversationMessageStatesV1(
            message.DeliveryState switch
            {
                "QUEUED" => "QUEUED",
                "SUBMITTED" => "SUBMITTED",
                "PROVIDER_ACCEPTED" => "PROVIDER_ACCEPTED",
                "DELIVERED" => "DELIVERED",
                "READ" => "READ",
                "FAILED" => "FAILED",
                "EXPIRED" => "EXPIRED",
                "UNRESOLVED" => "UNKNOWN",
                _ => "NOT_APPLICABLE",
            },
            message.ProcessingState switch
            {
                "QUEUED" => "QUEUED",
                "RUNNING" => "RUNNING",
                "COMPLETED" => "SUCCEEDED",
                "FAILED" => "FAILED",
                "CANCELLED" => "CANCELLED",
                "STOPPED" => "STOPPED",
                _ => "NOT_REQUESTED",
            },
            "NOT_REQUIRED",
            message.EvidenceState switch
            {
                "RECORDED" => "RECORDED",
                "BUFFERED_CE_UNAVAILABLE" => "BUFFERED_CE_UNAVAILABLE",
                "FAILED" => "FAILED",
                _ => "PENDING",
            }
        );
    }

    public async Task<ConversationOperationReceiptV1> RequestDataRightAsync(
        string environment,
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid idempotencyKey,
        RequestConversationDataRightV1 request,
        CancellationToken cancellationToken
    )
    {
        await EnsureMembershipAsync(tenantId, participantId, relationshipId, cancellationToken);
        if (
            !DataRightTypes.Contains(request.RightType)
            || !DataRightScopes.Contains(request.Scope)
            || string.IsNullOrWhiteSpace(request.AssuranceReference)
            || request.AssuranceReference.Length > 256
            || request.Reason is { Length: > 1000 }
        )
            throw new ConversationContextConflictException("CONVERSATION_DATA_RIGHT_INVALID");
        ValidateDigest(request.PayloadDigest, nameof(request.PayloadDigest));
        var scopeDigest = Sha256(request.Scope);
        var requestDigest = Sha256(JsonSerializer.Serialize(request));
        await using var db = await conversationFactory.CreateDbContextAsync(cancellationToken);
        var replay = await db.DataRightRequests.SingleOrDefaultAsync(
            value =>
                value.Environment == environment
                && value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == participantId
                && value.RequestType == request.RightType
                && value.IdempotencyKey == idempotencyKey,
            cancellationToken
        );
        if (replay is not null)
        {
            if (!FixedEquals(replay.RequestDigest, requestDigest))
                throw new ConversationContextConflictException(
                    "CONVERSATION_DATA_RIGHT_IDEMPOTENCY_CONFLICT"
                );
            return new(
                replay.RequestId,
                "DATA_RIGHT",
                "ACCEPTED",
                replay.CreatedAt,
                replay.RequestId
            );
        }

        var created = new ConversationDataRightRequest
        {
            Environment = environment,
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ParticipantId = participantId,
            RequestType = request.RightType,
            ScopeDigest = scopeDigest,
            IdempotencyKey = idempotencyKey,
            RequestDigest = requestDigest,
        };
        db.DataRightRequests.Add(created);
        await db.SaveChangesAsync(cancellationToken);
        return new(
            created.RequestId,
            "DATA_RIGHT",
            "ACCEPTED",
            created.CreatedAt,
            created.RequestId
        );
    }

    private async Task EnsureMembershipAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        await using var db = await relationshipFactory.CreateDbContextAsync(cancellationToken);
        var member = await db
            .RelationshipParticipants.AsNoTracking()
            .AnyAsync(
                value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.ParticipantId == participantId
                    && value.Status == "ACTIVE",
                cancellationToken
            );
        if (!member)
            throw new ConversationContextConflictException("CONVERSATION_NOT_ACCESSIBLE");
    }

    private static IReadOnlyList<ConversationCommandDescriptorV1> ReadAuthorizedCommands(
        JsonElement workspace
    )
    {
        if (
            workspace.ValueKind != JsonValueKind.Object
            || !workspace.TryGetProperty("availableCommands", out var commands)
            || commands.ValueKind != JsonValueKind.Array
        )
            return [];
        return commands
            .EnumerateArray()
            .Where(value => value.ValueKind == JsonValueKind.Object)
            .Select(value =>
            {
                var commandType =
                    value.TryGetProperty("kind", out var kind)
                    && kind.ValueKind == JsonValueKind.String
                        ? kind.GetString() ?? string.Empty
                        : string.Empty;
                var subjectReference =
                    value.TryGetProperty("subjectRef", out var subject)
                    && subject.ValueKind == JsonValueKind.String
                        ? subject.GetString() ?? string.Empty
                        : string.Empty;
                return new ConversationCommandDescriptorV1(
                    commandType,
                    subjectReference,
                    "submitEmploymentCommand",
                    "conversational-employment-business-platform.openapi.yaml#/components/schemas/EmploymentCommandRequestV1"
                );
            })
            .Where(value =>
                !string.IsNullOrWhiteSpace(value.Kind)
                && !string.IsNullOrWhiteSpace(value.SubjectReference)
                && CommandSchemas.ContainsKey(value.Kind)
            )
            .ToList();
    }

    private static void ValidateDigest(string value, string name)
    {
        if (
            value.Length != 64
            || value.Any(character => character is not (>= '0' and <= '9' or >= 'a' and <= 'f'))
        )
            throw new ConversationContextConflictException($"{name}_INVALID");
    }

    private static T DeserializeReference<T>(string json, T fallback)
    {
        if (string.IsNullOrWhiteSpace(json) || json == "{}")
            return fallback;
        return JsonSerializer.Deserialize<T>(
                json,
                new JsonSerializerOptions(JsonSerializerDefaults.Web)
            ) ?? fallback;
    }

    private static string MapDeliveryState(string state) =>
        state switch
        {
            "DELIVERED" => "DELIVERED",
            "READ" => "READ",
            "FAILED" or "REJECTED" => "FAILED",
            "EXPIRED" => "EXPIRED",
            "UNKNOWN" => "UNKNOWN",
            "SUBMITTED" => "SUBMITTED",
            "PROVIDER_ACCEPTED" => "PROVIDER_ACCEPTED",
            _ => "QUEUED",
        };

    private static string MapExecutionState(string state) =>
        state switch
        {
            "RUNNING" => "RUNNING",
            "COMPLETED" or "SUCCEEDED" => "SUCCEEDED",
            "FAILED" => "FAILED",
            "CANCELLED" => "CANCELLED",
            "STOPPED" => "STOPPED",
            "UNAVAILABLE" => "UNAVAILABLE",
            _ => "QUEUED",
        };

    private static string MapEvidenceState(string state) =>
        state switch
        {
            "RECORDED" => "RECORDED",
            "BUFFERED_CE_UNAVAILABLE" => "BUFFERED_CE_UNAVAILABLE",
            "FAILED" => "FAILED",
            _ => "PENDING",
        };

    private static string ConfiguredOrFallback(string configured, string fallback) =>
        string.IsNullOrWhiteSpace(configured) ? fallback : configured;

    private static Guid DeterministicGuid(string material)
    {
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(material));
        return new Guid(bytes.AsSpan(0, 16));
    }

    private static string Sha256(string value) =>
        Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value))).ToLowerInvariant();

    private static bool FixedEquals(string left, string right) =>
        left.Length == right.Length
        && CryptographicOperations.FixedTimeEquals(
            Encoding.ASCII.GetBytes(left),
            Encoding.ASCII.GetBytes(right)
        );
}
