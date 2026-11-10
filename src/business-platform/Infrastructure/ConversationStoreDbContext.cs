// Implements: architecture/reference/components/conversation-core.md § Durable Conversation Projection
// constitutional_basis: C-005, C-023, C-026, C-059, C-063

using Microsoft.EntityFrameworkCore;

namespace Waooaw.BusinessPlatform.Infrastructure;

public sealed class ConversationProjection
{
    public Guid ConversationId { get; init; } = Guid.NewGuid();
    public string Environment { get; init; } = "legacy";
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public long NextMessageSequence { get; set; } = 1;
    public long NextEventSequence { get; set; } = 1;
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class ConversationMessage
{
    public Guid MessageId { get; init; } = Guid.NewGuid();
    public string Environment { get; init; } = "legacy";
    public Guid TenantId { get; init; }
    public Guid ConversationId { get; init; }
    public Guid RelationshipId { get; init; }
    public long Sequence { get; init; }
    public string SchemaVersion { get; init; } = "1.0";
    public string Actor { get; init; } = "CUSTOMER";
    public string Channel { get; init; } = "WEB";
    public string ContributionKind { get; init; } = "TEXT";
    public string? DialogueAct { get; init; }
    public string SkillId { get; init; } = string.Empty;
    public string ContentJson { get; set; } = "[]";
    public string CardsJson { get; set; } = "[]";
    public string? ConclusionJson { get; init; }
    public string InteractionContextJson { get; init; } = "{}";
    public string ConversationPolicyJson { get; init; } = "{}";
    public string DeliveryState { get; set; } = "ACCEPTED";
    public string ProcessingState { get; set; } = "QUEUED";
    public string EvidenceState { get; set; } = "PENDING";
    public Guid? EvidenceRecordId { get; set; }
    public bool Partial { get; set; }
    public string? CompletionReason { get; set; }
    public Guid? RetryOfMessageId { get; init; }
    public Guid? ClientMessageId { get; init; }
    public DateTimeOffset AcceptedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? CompletedAt { get; set; }
}

public sealed class ConversationExecution
{
    public Guid ExecutionId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid ConversationId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid MessageId { get; init; }
    public string ProcessingState { get; set; } = "QUEUED";
    public bool Partial { get; set; }
    public string? CompletionReason { get; set; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
    public long RuntimeSequence { get; set; }
    public Guid? RuntimeReplyMessageId { get; set; }
    public DateTimeOffset? RuntimeNextAttemptAt { get; set; }
    public bool RuntimeTerminal { get; set; }
    public Guid? OriginChannelBindingId { get; init; }
    public string? OriginRecipientDigest { get; init; }
    public string? RuntimeActorIssuer { get; init; }
    public Guid? RuntimeMembershipId { get; init; }
    public Guid? RuntimeAccountId { get; init; }
    public Guid? RuntimeActorId { get; init; }
    public long ProjectionVersion { get; set; }
}

internal sealed class ConversationPendingStartReference
{
    public Guid TenantId { get; init; }
    public Guid MessageId { get; init; }
    public Guid ExecutionId { get; init; }
}

public sealed class ConversationReconciliationAuthority
{
    public Guid AuthorityId { get; init; }
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid ExecutionId { get; init; }
    public Guid RequesterId { get; init; }
    public string Issuer { get; init; } = string.Empty;
    public Guid AccountId { get; init; }
    public Guid MembershipId { get; init; }
    public string Role { get; init; } = string.Empty;
    public Guid DecisionSpaceSnapshotId { get; init; }
    public int DecisionSpaceVersion { get; init; }
    public Guid EvidenceId { get; init; }
    public string SourceDigest { get; init; } = string.Empty;
    public Guid IdempotencyKey { get; init; }
    public string RequestDigest { get; init; } = string.Empty;
    public long ExpectedProjectionVersion { get; init; }
    public DateTimeOffset CreatedAt { get; init; }
    public DateTimeOffset ExpiresAt { get; init; }
    public string? OriginalRequestDigest { get; set; }
    public string? ResultDigest { get; set; }
    public string? ResponseJson { get; set; }
}

public sealed class ConversationRuntimeEventReceipt
{
    public Guid TenantId { get; init; }
    public Guid ExecutionId { get; init; }
    public long Sequence { get; init; }
    public string EventDigest { get; init; } = string.Empty;
    public DateTimeOffset RecordedAt { get; init; }
}

public sealed class ConversationIdempotencyOutcome
{
    public Guid IdempotencyId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid ActorParticipantId { get; init; }
    public string OperationFamily { get; init; } = string.Empty;
    public Guid IdempotencyKey { get; init; }
    public string RequestHash { get; init; } = string.Empty;
    public Guid? MessageId { get; set; }
    public Guid? ExecutionId { get; set; }
    public string Outcome { get; set; } = "ACCEPTED";
    public string ResponseJson { get; set; } = "{}";
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset CompletedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class ConversationReadPosition
{
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid ParticipantId { get; init; }
    public Guid LastReadMessageId { get; set; }
    public long LastReadSequence { get; set; }
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class ConversationEvent
{
    public Guid EventId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid ConversationId { get; init; }
    public Guid RelationshipId { get; init; }
    public long Sequence { get; init; }
    public string EventType { get; init; } = string.Empty;
    public Guid? MessageId { get; init; }
    public Guid? ExecutionId { get; init; }
    public string DataJson { get; init; } = "{}";
    public DateTimeOffset OccurredAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class PortalInteractionContext
{
    public Guid ContextId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid ParticipantId { get; init; }
    public long NextMessageSequence { get; set; } = 1;
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class PortalInteractionMessage
{
    public Guid MessageId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid ContextId { get; init; }
    public Guid ParticipantId { get; init; }
    public long Sequence { get; init; }
    public string Actor { get; init; } = string.Empty;
    public string ContentJson { get; init; } = "[]";
    public string CapabilitiesJson { get; init; } = "[]";
    public string CurrentSurface { get; init; } = string.Empty;
    public Guid? ClientMessageId { get; init; }
    public DateTimeOffset AcceptedAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class PortalInteractionIdempotencyOutcome
{
    public Guid IdempotencyId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid ParticipantId { get; init; }
    public Guid IdempotencyKey { get; init; }
    public string RequestHash { get; init; } = string.Empty;
    public string ResponseJson { get; init; } = "{}";
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class ConversationStoreDbContext : DbContext
{
    public ConversationStoreDbContext(DbContextOptions<ConversationStoreDbContext> options)
        : base(options) { }

    public DbSet<ConversationProjection> Conversations => Set<ConversationProjection>();
    public DbSet<ConversationMessage> Messages => Set<ConversationMessage>();
    public DbSet<ConversationExecution> Executions => Set<ConversationExecution>();
    internal DbSet<ConversationPendingStartReference> PendingStarts =>
        Set<ConversationPendingStartReference>();
    public DbSet<ConversationReconciliationAuthority> ReconciliationAuthorities =>
        Set<ConversationReconciliationAuthority>();
    public DbSet<ConversationRuntimeEventReceipt> RuntimeEventReceipts =>
        Set<ConversationRuntimeEventReceipt>();
    public DbSet<ConversationIdempotencyOutcome> IdempotencyOutcomes =>
        Set<ConversationIdempotencyOutcome>();
    public DbSet<ConversationReadPosition> ReadPositions => Set<ConversationReadPosition>();
    public DbSet<ConversationEvent> Events => Set<ConversationEvent>();
    public DbSet<PortalInteractionContext> PortalInteractionContexts =>
        Set<PortalInteractionContext>();
    public DbSet<PortalInteractionMessage> PortalInteractionMessages =>
        Set<PortalInteractionMessage>();
    public DbSet<PortalInteractionIdempotencyOutcome> PortalInteractionIdempotencyOutcomes =>
        Set<PortalInteractionIdempotencyOutcome>();
    public DbSet<ConversationOutboxRecord> ConversationOutbox => Set<ConversationOutboxRecord>();
    public DbSet<ProviderEventClaim> ProviderEventClaims => Set<ProviderEventClaim>();
    public DbSet<ConversationContextObservation> ContextObservations =>
        Set<ConversationContextObservation>();
    public DbSet<ConversationContextSummary> ContextSummaries => Set<ConversationContextSummary>();
    public DbSet<ConversationDeliveryObservation> DeliveryObservations =>
        Set<ConversationDeliveryObservation>();
    public DbSet<ConversationDataRightRequest> DataRightRequests =>
        Set<ConversationDataRightRequest>();
    public DbSet<WhatsAppMediaRecord> WhatsAppMedia => Set<WhatsAppMediaRecord>();
    public DbSet<ConversationMigrationWatermark> MigrationWatermarks =>
        Set<ConversationMigrationWatermark>();
    public DbSet<RelationshipEmergencyStopLatch> EmergencyStopLatches =>
        Set<RelationshipEmergencyStopLatch>();
    public DbSet<ConversationOperationalSignal> OperationalSignals =>
        Set<ConversationOperationalSignal>();
    public DbSet<Services.WhatsAppGuestTrafficEvent> WhatsAppGuestTrafficEvents =>
        Set<Services.WhatsAppGuestTrafficEvent>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        var receipt = modelBuilder.Entity<ConversationRuntimeEventReceipt>();
        receipt.ToTable("conversation_runtime_event_receipts", "business");
        receipt.HasKey(value => new
        {
            value.TenantId,
            value.ExecutionId,
            value.Sequence,
        });
        receipt.Property(value => value.TenantId).HasColumnName("tenant_id");
        receipt.Property(value => value.ExecutionId).HasColumnName("execution_id");
        receipt.Property(value => value.Sequence).HasColumnName("sequence");
        receipt.Property(value => value.EventDigest).HasColumnName("event_digest");
        receipt.Property(value => value.RecordedAt).HasColumnName("recorded_at");
        ConfigureConversation(modelBuilder.Entity<ConversationProjection>());
        ConfigureMessage(modelBuilder.Entity<ConversationMessage>());
        ConfigureExecution(modelBuilder.Entity<ConversationExecution>());
        var pendingStart = modelBuilder.Entity<ConversationPendingStartReference>();
        pendingStart.ToTable("conversation_pending_starts", "business");
        pendingStart.HasKey(value => new { value.TenantId, value.MessageId });
        pendingStart.Property(value => value.TenantId).HasColumnName("tenant_id");
        pendingStart.Property(value => value.MessageId).HasColumnName("message_id");
        pendingStart.Property(value => value.ExecutionId).HasColumnName("execution_id");
        var reconciliation = modelBuilder.Entity<ConversationReconciliationAuthority>();
        reconciliation.ToTable("conversation_reconciliation_authorities", "business");
        reconciliation.HasKey(value => value.AuthorityId);
        reconciliation
            .HasIndex(value => new
            {
                value.TenantId,
                value.ExecutionId,
                value.RequesterId,
                value.IdempotencyKey,
            })
            .IsUnique();
        foreach (var property in reconciliation.Metadata.GetProperties())
            property.SetColumnName(
                System
                    .Text.RegularExpressions.Regex.Replace(property.Name, "(?<!^)([A-Z])", "_$1")
                    .ToLowerInvariant()
            );
        reconciliation.Property(value => value.ResponseJson).HasColumnType("jsonb");
        ConfigureIdempotency(modelBuilder.Entity<ConversationIdempotencyOutcome>());
        ConfigureReadPosition(modelBuilder.Entity<ConversationReadPosition>());
        ConfigureEvent(modelBuilder.Entity<ConversationEvent>());
        ConfigurePortalContext(modelBuilder.Entity<PortalInteractionContext>());
        ConfigurePortalMessage(modelBuilder.Entity<PortalInteractionMessage>());
        ConfigurePortalIdempotency(modelBuilder.Entity<PortalInteractionIdempotencyOutcome>());
        modelBuilder.ConfigureWc120Conversation();
        var guestSession = modelBuilder.Entity<Services.WhatsAppGuestSession>();
        guestSession.ToTable("whatsapp_guest_sessions", "business");
        guestSession.HasKey(value => new { value.TenantId, value.BindingDigest });
        guestSession.HasIndex(value => new { value.TenantId, value.ParticipantId }).IsUnique();
        guestSession.Property(value => value.TenantId).HasColumnName("tenant_id");
        guestSession.Property(value => value.BindingDigest).HasColumnName("binding_digest");
        guestSession.Property(value => value.ParticipantId).HasColumnName("participant_id");
        guestSession.Property(value => value.EvidenceId).HasColumnName("evidence_id");
        guestSession
            .Property(value => value.ProtectedDestination)
            .HasColumnName("protected_destination")
            .HasMaxLength(512);
        guestSession.Property(value => value.FirstObservedAt).HasColumnName("first_observed_at");
        guestSession.Property(value => value.AdmittedAt).HasColumnName("admitted_at");
        guestSession.Property(value => value.LastInboundAt).HasColumnName("last_inbound_at");
        guestSession.Property(value => value.StoppedAt).HasColumnName("stopped_at");
        guestSession
            .Property(value => value.ServiceConsentNoticeQueuedAt)
            .HasColumnName("service_consent_notice_queued_at");
        guestSession
            .Property(value => value.ServiceConsentNoticeMessageId)
            .HasColumnName("service_consent_notice_message_id");
        guestSession
            .Property(value => value.ServiceConsentNoticeVersion)
            .HasColumnName("service_consent_notice_version")
            .HasMaxLength(32);
        guestSession.Property(value => value.ServiceConsentAt).HasColumnName("service_consent_at");
        guestSession
            .Property(value => value.ServiceConsentMessageId)
            .HasColumnName("service_consent_message_id")
            .HasMaxLength(128);
        guestSession
            .Property(value => value.ServiceConsentEvidenceId)
            .HasColumnName("service_consent_evidence_id");

        var consentHistory = modelBuilder.Entity<Services.WhatsAppGuestConsentHistory>();
        consentHistory.ToTable("whatsapp_guest_consent_history", "business");
        consentHistory.HasKey(value => new
        {
            value.TenantId,
            value.BindingDigest,
            value.EvidenceId,
        });
        consentHistory.Property(value => value.TenantId).HasColumnName("tenant_id");
        consentHistory.Property(value => value.BindingDigest).HasColumnName("binding_digest");
        consentHistory.Property(value => value.EvidenceId).HasColumnName("evidence_id");
        consentHistory
            .Property(value => value.NoticeVersion)
            .HasColumnName("notice_version")
            .HasMaxLength(32);
        consentHistory.Property(value => value.NoticeMessageId).HasColumnName("notice_message_id");
        consentHistory.Property(value => value.NoticeQueuedAt).HasColumnName("notice_queued_at");
        consentHistory
            .Property(value => value.ConsentMessageId)
            .HasColumnName("consent_message_id")
            .HasMaxLength(128);
        consentHistory.Property(value => value.ConsentAt).HasColumnName("consent_at");

        var guestTrafficEvent = modelBuilder.Entity<Services.WhatsAppGuestTrafficEvent>();
        guestTrafficEvent.ToTable("whatsapp_guest_traffic_events", "business");
        guestTrafficEvent.HasKey(value => new
        {
            value.TenantId,
            value.ActivationDigest,
            value.EventId,
        });
        guestTrafficEvent.Property(value => value.TenantId).HasColumnName("tenant_id");
        guestTrafficEvent
            .Property(value => value.ActivationDigest)
            .HasColumnName("activation_digest");
        guestTrafficEvent
            .Property(value => value.AuthorityDigest)
            .HasColumnName("authority_digest");
        guestTrafficEvent.Property(value => value.EventId).HasColumnName("event_id");
        guestTrafficEvent.Property(value => value.BindingDigest).HasColumnName("binding_digest");
        guestTrafficEvent.Property(value => value.EventType).HasColumnName("event_type");
        guestTrafficEvent
            .Property(value => value.InboundNotice)
            .HasColumnName("inbound_notice")
            .HasMaxLength(32);
        guestTrafficEvent.Property(value => value.ReservedAt).HasColumnName("reserved_at");
        guestTrafficEvent.HasIndex(value => new
        {
            value.TenantId,
            value.ActivationDigest,
            value.BindingDigest,
            value.ReservedAt,
        });
    }

    private static void ConfigureConversation(
        Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<ConversationProjection> entity
    )
    {
        entity.ToTable("conversations", "business");
        entity.HasKey(value => value.ConversationId);
        entity
            .HasIndex(value => new
            {
                value.Environment,
                value.TenantId,
                value.RelationshipId,
            })
            .IsUnique();
        entity.Property(value => value.ConversationId).HasColumnName("conversation_id");
        entity.Property(value => value.Environment).HasColumnName("environment");
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
        entity
            .Property(value => value.NextMessageSequence)
            .HasColumnName("next_message_sequence")
            .IsConcurrencyToken();
        entity
            .Property(value => value.NextEventSequence)
            .HasColumnName("next_event_sequence")
            .IsConcurrencyToken();
        entity.Property(value => value.CreatedAt).HasColumnName("created_at");
        entity.Property(value => value.UpdatedAt).HasColumnName("updated_at");
    }

    private static void ConfigureMessage(
        Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<ConversationMessage> entity
    )
    {
        entity.ToTable("conversation_messages", "business");
        entity.HasKey(value => value.MessageId);
        entity
            .HasIndex(value => new
            {
                value.Environment,
                value.TenantId,
                value.RelationshipId,
                value.Sequence,
            })
            .IsUnique();
        entity
            .HasIndex(value => new
            {
                value.TenantId,
                value.RelationshipId,
                value.ClientMessageId,
            })
            .IsUnique();
        entity.Property(value => value.MessageId).HasColumnName("message_id");
        entity.Property(value => value.Environment).HasColumnName("environment");
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.ConversationId).HasColumnName("conversation_id");
        entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
        entity.Property(value => value.Sequence).HasColumnName("sequence");
        entity.Property(value => value.SchemaVersion).HasColumnName("schema_version");
        entity.Property(value => value.Actor).HasColumnName("actor");
        entity.Property(value => value.Channel).HasColumnName("channel");
        entity.Property(value => value.ContributionKind).HasColumnName("contribution_kind");
        entity.Property(value => value.DialogueAct).HasColumnName("dialogue_act");
        entity.Property(value => value.SkillId).HasColumnName("skill_id");
        entity
            .Property(value => value.ContentJson)
            .HasColumnName("content_json")
            .HasColumnType("jsonb");
        entity
            .Property(value => value.CardsJson)
            .HasColumnName("cards_json")
            .HasColumnType("jsonb");
        entity
            .Property(value => value.ConclusionJson)
            .HasColumnName("conclusion_json")
            .HasColumnType("jsonb");
        entity
            .Property(value => value.InteractionContextJson)
            .HasColumnName("interaction_context_json")
            .HasColumnType("jsonb");
        entity
            .Property(value => value.ConversationPolicyJson)
            .HasColumnName("conversation_policy_json")
            .HasColumnType("jsonb");
        entity.Property(value => value.DeliveryState).HasColumnName("delivery_state");
        entity.Property(value => value.ProcessingState).HasColumnName("processing_state");
        entity.Property(value => value.EvidenceState).HasColumnName("evidence_state");
        entity.Property(value => value.EvidenceRecordId).HasColumnName("evidence_record_id");
        entity.Property(value => value.Partial).HasColumnName("partial");
        entity.Property(value => value.CompletionReason).HasColumnName("completion_reason");
        entity.Property(value => value.RetryOfMessageId).HasColumnName("retry_of_message_id");
        entity.Property(value => value.ClientMessageId).HasColumnName("client_message_id");
        entity.Property(value => value.AcceptedAt).HasColumnName("accepted_at");
        entity.Property(value => value.CompletedAt).HasColumnName("completed_at");
    }

    private static void ConfigureExecution(
        Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<ConversationExecution> entity
    )
    {
        entity.ToTable("conversation_executions", "business");
        entity.HasKey(value => value.ExecutionId);
        entity
            .HasOne<ConversationMessage>()
            .WithMany()
            .HasForeignKey(value => value.MessageId)
            .OnDelete(DeleteBehavior.Restrict);
        entity
            .HasIndex(value => new
            {
                value.TenantId,
                value.RelationshipId,
                value.MessageId,
            })
            .IsUnique();
        entity.Property(value => value.ExecutionId).HasColumnName("execution_id");
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.ConversationId).HasColumnName("conversation_id");
        entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
        entity.Property(value => value.MessageId).HasColumnName("message_id");
        entity.Property(value => value.ProcessingState).HasColumnName("processing_state");
        entity.Property(value => value.Partial).HasColumnName("partial");
        entity.Property(value => value.CompletionReason).HasColumnName("completion_reason");
        entity.Property(value => value.CreatedAt).HasColumnName("created_at");
        entity.Property(value => value.UpdatedAt).HasColumnName("updated_at");
        entity
            .Property(value => value.RuntimeSequence)
            .HasColumnName("runtime_sequence")
            .IsConcurrencyToken();
        entity
            .Property(value => value.RuntimeReplyMessageId)
            .HasColumnName("runtime_reply_message_id");
        entity
            .Property(value => value.RuntimeNextAttemptAt)
            .HasColumnName("runtime_next_attempt_at");
        entity.Property(value => value.RuntimeTerminal).HasColumnName("runtime_terminal");
        entity
            .Property(value => value.OriginChannelBindingId)
            .HasColumnName("origin_channel_binding_id");
        entity
            .Property(value => value.OriginRecipientDigest)
            .HasColumnName("origin_recipient_digest");
        entity.Property(value => value.RuntimeActorIssuer).HasColumnName("runtime_actor_issuer");
        entity.Property(value => value.RuntimeMembershipId).HasColumnName("runtime_membership_id");
        entity.Property(value => value.RuntimeAccountId).HasColumnName("runtime_account_id");
        entity.Property(value => value.RuntimeActorId).HasColumnName("runtime_actor_id");
        entity
            .Property(value => value.ProjectionVersion)
            .HasColumnName("projection_version")
            .IsConcurrencyToken();
    }

    public override int SaveChanges(bool acceptAllChangesOnSuccess)
    {
        AdvanceProjectionVersions();
        return base.SaveChanges(acceptAllChangesOnSuccess);
    }

    public override Task<int> SaveChangesAsync(
        bool acceptAllChangesOnSuccess,
        CancellationToken cancellationToken = default
    )
    {
        AdvanceProjectionVersions();
        return base.SaveChangesAsync(acceptAllChangesOnSuccess, cancellationToken);
    }

    internal void AdvanceProjectionVersions()
    {
        ChangeTracker.DetectChanges();
        foreach (
            var entry in ChangeTracker
                .Entries<ConversationExecution>()
                .Where(value => value.State == EntityState.Modified)
        )
            entry.Entity.ProjectionVersion = checked(
                entry.Property(value => value.ProjectionVersion).OriginalValue + 1
            );
    }

    private static void ConfigureIdempotency(
        Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<ConversationIdempotencyOutcome> entity
    )
    {
        entity.ToTable("conversation_idempotency_outcomes", "business");
        entity.HasKey(value => value.IdempotencyId);
        entity
            .HasIndex(value => new
            {
                value.TenantId,
                value.RelationshipId,
                value.ActorParticipantId,
                value.OperationFamily,
                value.IdempotencyKey,
            })
            .IsUnique();
        entity.Property(value => value.IdempotencyId).HasColumnName("idempotency_id");
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
        entity.Property(value => value.ActorParticipantId).HasColumnName("actor_participant_id");
        entity.Property(value => value.OperationFamily).HasColumnName("operation_family");
        entity.Property(value => value.IdempotencyKey).HasColumnName("idempotency_key");
        entity.Property(value => value.RequestHash).HasColumnName("request_hash");
        entity.Property(value => value.MessageId).HasColumnName("message_id");
        entity.Property(value => value.ExecutionId).HasColumnName("execution_id");
        entity.Property(value => value.Outcome).HasColumnName("outcome");
        entity
            .Property(value => value.ResponseJson)
            .HasColumnName("response_json")
            .HasColumnType("jsonb");
        entity.Property(value => value.CreatedAt).HasColumnName("created_at");
        entity.Property(value => value.CompletedAt).HasColumnName("completed_at");
    }

    private static void ConfigureReadPosition(
        Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<ConversationReadPosition> entity
    )
    {
        entity.ToTable("conversation_read_positions", "business");
        entity.HasKey(value => new
        {
            value.TenantId,
            value.RelationshipId,
            value.ParticipantId,
        });
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
        entity.Property(value => value.ParticipantId).HasColumnName("participant_id");
        entity.Property(value => value.LastReadMessageId).HasColumnName("last_read_message_id");
        entity.Property(value => value.LastReadSequence).HasColumnName("last_read_sequence");
        entity.Property(value => value.UpdatedAt).HasColumnName("updated_at");
    }

    private static void ConfigureEvent(
        Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<ConversationEvent> entity
    )
    {
        entity.ToTable("conversation_events", "business");
        entity.HasKey(value => value.EventId);
        entity
            .HasIndex(value => new
            {
                value.TenantId,
                value.RelationshipId,
                value.Sequence,
            })
            .IsUnique();
        entity.Property(value => value.EventId).HasColumnName("event_id");
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.ConversationId).HasColumnName("conversation_id");
        entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
        entity.Property(value => value.Sequence).HasColumnName("sequence");
        entity.Property(value => value.EventType).HasColumnName("event_type");
        entity.Property(value => value.MessageId).HasColumnName("message_id");
        entity.Property(value => value.ExecutionId).HasColumnName("execution_id");
        entity.Property(value => value.DataJson).HasColumnName("data_json").HasColumnType("jsonb");
        entity.Property(value => value.OccurredAt).HasColumnName("occurred_at");
    }

    private static void ConfigurePortalContext(
        Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<PortalInteractionContext> entity
    )
    {
        entity.ToTable("portal_interaction_contexts", "business");
        entity.HasKey(value => value.ContextId);
        entity.HasIndex(value => new { value.TenantId, value.ParticipantId }).IsUnique();
        entity.Property(value => value.ContextId).HasColumnName("context_id");
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.ParticipantId).HasColumnName("participant_id");
        entity
            .Property(value => value.NextMessageSequence)
            .HasColumnName("next_message_sequence")
            .IsConcurrencyToken();
        entity.Property(value => value.CreatedAt).HasColumnName("created_at");
        entity.Property(value => value.UpdatedAt).HasColumnName("updated_at");
    }

    private static void ConfigurePortalMessage(
        Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<PortalInteractionMessage> entity
    )
    {
        entity.ToTable("portal_interaction_messages", "business");
        entity.HasKey(value => value.MessageId);
        entity
            .HasIndex(value => new
            {
                value.TenantId,
                value.ParticipantId,
                value.Sequence,
            })
            .IsUnique();
        entity
            .HasIndex(value => new
            {
                value.TenantId,
                value.ParticipantId,
                value.ClientMessageId,
            })
            .IsUnique();
        entity.Property(value => value.MessageId).HasColumnName("message_id");
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.ContextId).HasColumnName("context_id");
        entity.Property(value => value.ParticipantId).HasColumnName("participant_id");
        entity.Property(value => value.Sequence).HasColumnName("sequence");
        entity.Property(value => value.Actor).HasColumnName("actor");
        entity
            .Property(value => value.ContentJson)
            .HasColumnName("content_json")
            .HasColumnType("jsonb");
        entity
            .Property(value => value.CapabilitiesJson)
            .HasColumnName("capabilities_json")
            .HasColumnType("jsonb");
        entity.Property(value => value.CurrentSurface).HasColumnName("current_surface");
        entity.Property(value => value.ClientMessageId).HasColumnName("client_message_id");
        entity.Property(value => value.AcceptedAt).HasColumnName("accepted_at");
    }

    private static void ConfigurePortalIdempotency(
        Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<PortalInteractionIdempotencyOutcome> entity
    )
    {
        entity.ToTable("portal_interaction_idempotency_outcomes", "business");
        entity.HasKey(value => value.IdempotencyId);
        entity
            .HasIndex(value => new
            {
                value.TenantId,
                value.ParticipantId,
                value.IdempotencyKey,
            })
            .IsUnique();
        entity.Property(value => value.IdempotencyId).HasColumnName("idempotency_id");
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.ParticipantId).HasColumnName("participant_id");
        entity.Property(value => value.IdempotencyKey).HasColumnName("idempotency_key");
        entity.Property(value => value.RequestHash).HasColumnName("request_hash");
        entity
            .Property(value => value.ResponseJson)
            .HasColumnName("response_json")
            .HasColumnType("jsonb");
        entity.Property(value => value.CreatedAt).HasColumnName("created_at");
    }
}
