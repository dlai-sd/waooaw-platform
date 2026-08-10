// Implements: architecture/reference/components/conversation-core.md § Durable Conversation Projection
// constitutional_basis: C-005, C-023, C-026, C-059, C-063

using Microsoft.EntityFrameworkCore;

namespace Waooaw.BusinessPlatform.Infrastructure;

public sealed class ConversationProjection
{
    public Guid ConversationId { get; init; } = Guid.NewGuid();
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
    public Guid TenantId { get; init; }
    public Guid ConversationId { get; init; }
    public Guid RelationshipId { get; init; }
    public long Sequence { get; init; }
    public string SchemaVersion { get; init; } = "1.0";
    public string Actor { get; init; } = "CUSTOMER";
    public string Channel { get; init; } = "WEB";
    public string ContentJson { get; set; } = "[]";
    public string CardsJson { get; set; } = "[]";
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

public sealed class ConversationStoreDbContext : DbContext
{
    public ConversationStoreDbContext(DbContextOptions<ConversationStoreDbContext> options)
        : base(options) { }

    public DbSet<ConversationProjection> Conversations => Set<ConversationProjection>();
    public DbSet<ConversationMessage> Messages => Set<ConversationMessage>();
    public DbSet<ConversationExecution> Executions => Set<ConversationExecution>();
    public DbSet<ConversationIdempotencyOutcome> IdempotencyOutcomes => Set<ConversationIdempotencyOutcome>();
    public DbSet<ConversationReadPosition> ReadPositions => Set<ConversationReadPosition>();
    public DbSet<ConversationEvent> Events => Set<ConversationEvent>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        ConfigureConversation(modelBuilder.Entity<ConversationProjection>());
        ConfigureMessage(modelBuilder.Entity<ConversationMessage>());
        ConfigureExecution(modelBuilder.Entity<ConversationExecution>());
        ConfigureIdempotency(modelBuilder.Entity<ConversationIdempotencyOutcome>());
        ConfigureReadPosition(modelBuilder.Entity<ConversationReadPosition>());
        ConfigureEvent(modelBuilder.Entity<ConversationEvent>());
    }

    private static void ConfigureConversation(Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<ConversationProjection> entity)
    {
        entity.ToTable("conversations", "business");
        entity.HasKey(value => value.ConversationId);
        entity.HasIndex(value => new { value.TenantId, value.RelationshipId }).IsUnique();
        entity.Property(value => value.ConversationId).HasColumnName("conversation_id");
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
        entity.Property(value => value.NextMessageSequence).HasColumnName("next_message_sequence").IsConcurrencyToken();
        entity.Property(value => value.NextEventSequence).HasColumnName("next_event_sequence").IsConcurrencyToken();
        entity.Property(value => value.CreatedAt).HasColumnName("created_at");
        entity.Property(value => value.UpdatedAt).HasColumnName("updated_at");
    }

    private static void ConfigureMessage(Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<ConversationMessage> entity)
    {
        entity.ToTable("conversation_messages", "business");
        entity.HasKey(value => value.MessageId);
        entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.Sequence }).IsUnique();
        entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.ClientMessageId }).IsUnique();
        entity.Property(value => value.MessageId).HasColumnName("message_id");
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.ConversationId).HasColumnName("conversation_id");
        entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
        entity.Property(value => value.Sequence).HasColumnName("sequence");
        entity.Property(value => value.SchemaVersion).HasColumnName("schema_version");
        entity.Property(value => value.Actor).HasColumnName("actor");
        entity.Property(value => value.Channel).HasColumnName("channel");
        entity.Property(value => value.ContentJson).HasColumnName("content_json").HasColumnType("jsonb");
        entity.Property(value => value.CardsJson).HasColumnName("cards_json").HasColumnType("jsonb");
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

    private static void ConfigureExecution(Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<ConversationExecution> entity)
    {
        entity.ToTable("conversation_executions", "business");
        entity.HasKey(value => value.ExecutionId);
        entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.MessageId }).IsUnique();
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
    }

    private static void ConfigureIdempotency(Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<ConversationIdempotencyOutcome> entity)
    {
        entity.ToTable("conversation_idempotency_outcomes", "business");
        entity.HasKey(value => value.IdempotencyId);
        entity.HasIndex(value => new
        {
            value.TenantId,
            value.RelationshipId,
            value.ActorParticipantId,
            value.OperationFamily,
            value.IdempotencyKey,
        }).IsUnique();
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
        entity.Property(value => value.ResponseJson).HasColumnName("response_json").HasColumnType("jsonb");
        entity.Property(value => value.CreatedAt).HasColumnName("created_at");
        entity.Property(value => value.CompletedAt).HasColumnName("completed_at");
    }

    private static void ConfigureReadPosition(Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<ConversationReadPosition> entity)
    {
        entity.ToTable("conversation_read_positions", "business");
        entity.HasKey(value => new { value.TenantId, value.RelationshipId, value.ParticipantId });
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
        entity.Property(value => value.ParticipantId).HasColumnName("participant_id");
        entity.Property(value => value.LastReadMessageId).HasColumnName("last_read_message_id");
        entity.Property(value => value.LastReadSequence).HasColumnName("last_read_sequence");
        entity.Property(value => value.UpdatedAt).HasColumnName("updated_at");
    }

    private static void ConfigureEvent(Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<ConversationEvent> entity)
    {
        entity.ToTable("conversation_events", "business");
        entity.HasKey(value => value.EventId);
        entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.Sequence }).IsUnique();
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
}