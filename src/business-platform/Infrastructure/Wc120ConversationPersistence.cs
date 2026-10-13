// Implements: architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md §25.2 WC120-P1
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using System.Text;
using Microsoft.EntityFrameworkCore;

namespace Waooaw.BusinessPlatform.Infrastructure;

public sealed class ConversationOutboxRecord
{
    public Guid OutboxId { get; init; } = Guid.NewGuid();
    public string Environment { get; init; } = string.Empty;
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid ConversationId { get; init; }
    public long Sequence { get; init; }
    public string Owner { get; init; } = "BUSINESS_PLATFORM";
    public string AggregateId { get; init; } = string.Empty;
    public string OperationFamily { get; init; } = string.Empty;
    public Guid IdempotencyKey { get; init; }
    public string PayloadDigest { get; init; } = string.Empty;
    public string PayloadReference { get; init; } = string.Empty;
    public string Purpose { get; init; } = string.Empty;
    public string RecipientBindingDigest { get; init; } = string.Empty;
    public string? TemplateName { get; init; }
    public string? TemplateVersion { get; init; }
    public string? TemplateLocale { get; init; }
    public string? TemplateCategory { get; init; }
    public string State { get; set; } = "PENDING";
    public int AttemptNumber { get; set; }
    public string? LeaseOwner { get; set; }
    public DateTimeOffset? LeaseExpiresAt { get; set; }
    public DateTimeOffset? HeartbeatAt { get; set; }
    public DateTimeOffset NextAttemptAt { get; set; } = DateTimeOffset.UtcNow;
    public string? BlockedReason { get; set; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class ProviderEventClaim
{
    public Guid ClaimId { get; init; } = Guid.NewGuid();
    public string Environment { get; init; } = string.Empty;
    public string Provider { get; init; } = string.Empty;
    public string AppBindingDigest { get; init; } = string.Empty;
    public string EventIdentity { get; init; } = string.Empty;
    public string PayloadDigest { get; init; } = string.Empty;
    public string State { get; set; } = "CLAIMED";
    public string ResultJson { get; set; } = "{}";
    public Guid? LeaseOwner { get; set; }
    public DateTimeOffset? LeaseExpiresAt { get; set; }
    public DateTimeOffset ReceivedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? TerminalAt { get; set; }
    public DateTimeOffset? ExpiresAt { get; set; }
    public bool LegalHold { get; set; }
}

public sealed class ConversationContextObservation
{
    public Guid ObservationId { get; init; } = Guid.NewGuid();
    public string Environment { get; init; } = string.Empty;
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public string Owner { get; init; } = string.Empty;
    public string SubjectType { get; init; } = string.Empty;
    public string ObservationType { get; init; } = string.Empty;
    public string Status { get; init; } = "INFERRED";
    public string SourceType { get; init; } = string.Empty;
    public string SourceVersion { get; init; } = string.Empty;
    public string ValueJson { get; init; } = "{}";
    public string SourceReference { get; init; } = string.Empty;
    public string SourceDigest { get; init; } = string.Empty;
    public long Revision { get; init; }
    public Guid? SupersedesObservationId { get; init; }
    public bool Current { get; set; } = true;
    public DateTimeOffset RecordedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? ExpiresAt { get; init; }
}

public sealed class ConversationContextSummary
{
    public Guid SummaryId { get; init; } = Guid.NewGuid();
    public string Environment { get; init; } = string.Empty;
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public long SourceSequenceStart { get; init; }
    public long SourceSequenceEnd { get; init; }
    public string SourceDigestsJson { get; init; } = "[]";
    public string DerivationContractVersion { get; init; } = string.Empty;
    public string ModelPolicyVersion { get; init; } = string.Empty;
    public string ConversationPolicyVersion { get; init; } = string.Empty;
    public string PayloadReference { get; init; } = string.Empty;
    public bool Current { get; set; } = true;
    public string? InvalidationReason { get; set; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? InvalidatedAt { get; set; }
}

public sealed class ConversationDeliveryObservation
{
    public Guid ObservationId { get; init; } = Guid.NewGuid();
    public string Environment { get; init; } = string.Empty;
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid MessageId { get; init; }
    public string Provider { get; init; } = string.Empty;
    public string ProviderEventIdentity { get; init; } = string.Empty;
    public string ProviderReferenceDigest { get; init; } = string.Empty;
    public string DeliveryState { get; init; } = string.Empty;
    public string ObservationDigest { get; init; } = string.Empty;
    public DateTimeOffset ObservedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset RetainUntil { get; set; }
    public bool LegalHold { get; set; }
}

public sealed class ConversationDataRightRequest
{
    public Guid RequestId { get; init; } = Guid.NewGuid();
    public string Environment { get; init; } = string.Empty;
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid ParticipantId { get; init; }
    public string RequestType { get; init; } = string.Empty;
    public string ScopeDigest { get; init; } = string.Empty;
    public string State { get; set; } = "PENDING_OWNER_DECISION";
    public Guid IdempotencyKey { get; init; }
    public string RequestDigest { get; init; } = string.Empty;
    public string? OwnerDecisionReference { get; set; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class WhatsAppMediaRecord
{
    public Guid MediaId { get; init; } = Guid.NewGuid();
    public string Environment { get; init; } = string.Empty;
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public string ProviderReferenceDigest { get; init; } = string.Empty;
    public string DeclaredMediaType { get; init; } = string.Empty;
    public string DetectedMediaType { get; init; } = string.Empty;
    public long WireBytes { get; init; }
    public long ExpandedBytes { get; init; }
    public int DurationSeconds { get; init; }
    public int CpuMilliseconds { get; init; }
    public int WallTimeMilliseconds { get; init; }
    public long PeakMemoryBytes { get; init; }
    public int RecursionDepth { get; init; }
    public int ArchiveEntries { get; init; }
    public int PageCount { get; init; }
    public int VideoFrames { get; init; }
    public int AnimationFrames { get; init; }
    public int ImageMegapixels { get; init; }
    public bool IsolationConfirmed { get; init; }
    public string Locale { get; init; } = string.Empty;
    public string State { get; set; } = "QUARANTINED";
    public string? PayloadReference { get; set; }
    public string? ScannerEngineVersion { get; set; }
    public string? ScannerPolicyVersion { get; set; }
    public string? ScannerSignatureVersion { get; set; }
    public DateTimeOffset? ScannerSignaturePublishedAt { get; set; }
    public string? VerdictDigest { get; set; }
    public string DerivativePayloadReferencesJson { get; set; } = "[]";
    public bool LegalHold { get; set; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? TerminalAt { get; set; }
    public DateTimeOffset DeleteAfter { get; set; } = DateTimeOffset.UtcNow.AddHours(24);
}

public sealed class ConversationMigrationWatermark
{
    public string MigrationId { get; init; } = string.Empty;
    public string Environment { get; init; } = string.Empty;
    public string Owner { get; init; } = string.Empty;
    public string LastPrimaryKey { get; set; } = string.Empty;
    public int BatchSize { get; init; }
    public string State { get; set; } = "PENDING";
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class RelationshipEmergencyStopLatch
{
    public Guid LatchId { get; init; } = Guid.NewGuid();
    public string Environment { get; init; } = string.Empty;
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid StoppedByParticipantId { get; init; }
    public Guid CorrelationId { get; init; }
    public string State { get; set; } = "LATCHED";
    public Guid? EvidenceId { get; set; }
    public DateTimeOffset LatchedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? EvidenceConfirmedAt { get; set; }
}

public sealed class ConversationOperationalSignal
{
    public Guid SignalId { get; init; } = Guid.NewGuid();
    public string Environment { get; init; } = string.Empty;
    public string Category { get; init; } = string.Empty;
    public string Code { get; init; } = string.Empty;
    public string State { get; set; } = "OPEN";
    public DateTimeOffset OccurredAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? ResolvedAt { get; set; }
}

public static class Wc120ConversationModelConfiguration
{
    public static void ConfigureWc120Conversation(this ModelBuilder modelBuilder)
    {
        ConfigureOutbox(modelBuilder);
        ConfigureProviderClaim(modelBuilder);
        ConfigureObservation(modelBuilder);
        ConfigureSummary(modelBuilder);
        ConfigureDelivery(modelBuilder);
        ConfigureDataRight(modelBuilder);
        ConfigureMedia(modelBuilder);
        ConfigureMigration(modelBuilder);
        ConfigureEmergencyStopLatch(modelBuilder);
        ConfigureOperationalSignal(modelBuilder);
        MapColumns<ConversationOutboxRecord>(modelBuilder);
        MapColumns<ProviderEventClaim>(modelBuilder);
        MapColumns<ConversationContextObservation>(modelBuilder);
        MapColumns<ConversationContextSummary>(modelBuilder);
        MapColumns<ConversationDeliveryObservation>(modelBuilder);
        MapColumns<ConversationDataRightRequest>(modelBuilder);
        MapColumns<WhatsAppMediaRecord>(modelBuilder);
        MapColumns<ConversationMigrationWatermark>(modelBuilder);
        MapColumns<RelationshipEmergencyStopLatch>(modelBuilder);
        MapColumns<ConversationOperationalSignal>(modelBuilder);
    }

    private static void ConfigureOutbox(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<ConversationOutboxRecord>();
        entity.ToTable("conversation_outbox", "business");
        entity.HasKey(value => value.OutboxId);
        entity
            .HasIndex(value => new
            {
                value.Environment,
                value.TenantId,
                value.RelationshipId,
                value.Owner,
                value.AggregateId,
                value.Sequence,
            })
            .IsUnique();
        entity
            .HasIndex(value => new
            {
                value.Environment,
                value.TenantId,
                value.RelationshipId,
                value.OperationFamily,
                value.IdempotencyKey,
            })
            .IsUnique();
        entity.Property(value => value.PayloadDigest).HasMaxLength(64);
        entity.Property(value => value.PayloadReference).HasMaxLength(256);
        entity.Property(value => value.RecipientBindingDigest).HasMaxLength(64);
    }

    private static void ConfigureProviderClaim(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<ProviderEventClaim>();
        entity.ToTable("provider_event_claims", "business");
        entity.HasKey(value => value.ClaimId);
        entity
            .HasIndex(value => new
            {
                value.Environment,
                value.Provider,
                value.AppBindingDigest,
                value.EventIdentity,
            })
            .IsUnique();
        entity.Property(value => value.PayloadDigest).HasMaxLength(64);
        entity.Property(value => value.ResultJson).HasColumnType("jsonb");
    }

    private static void ConfigureObservation(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<ConversationContextObservation>();
        entity.ToTable("conversation_context_observations", "business");
        entity.HasKey(value => value.ObservationId);
        entity
            .HasIndex(value => new
            {
                value.Environment,
                value.TenantId,
                value.RelationshipId,
                value.Owner,
                value.ObservationType,
                value.Revision,
            })
            .IsUnique();
        entity.Property(value => value.ValueJson).HasColumnType("jsonb");
    }

    private static void ConfigureSummary(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<ConversationContextSummary>();
        entity.ToTable("conversation_context_summaries", "business");
        entity.HasKey(value => value.SummaryId);
        entity.HasIndex(value => new
        {
            value.Environment,
            value.TenantId,
            value.RelationshipId,
            value.SourceSequenceStart,
            value.SourceSequenceEnd,
        });
        entity.Property(value => value.SourceDigestsJson).HasColumnType("jsonb");
    }

    private static void ConfigureDelivery(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<ConversationDeliveryObservation>();
        entity.ToTable("conversation_delivery_observations", "business");
        entity.HasKey(value => value.ObservationId);
        entity
            .HasIndex(value => new
            {
                value.Environment,
                value.TenantId,
                value.RelationshipId,
                value.MessageId,
                value.Provider,
                value.ProviderEventIdentity,
            })
            .IsUnique();
    }

    private static void ConfigureDataRight(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<ConversationDataRightRequest>();
        entity.ToTable("conversation_data_right_requests", "business");
        entity.HasKey(value => value.RequestId);
        entity
            .HasIndex(value => new
            {
                value.Environment,
                value.TenantId,
                value.RelationshipId,
                value.ParticipantId,
                value.RequestType,
                value.IdempotencyKey,
            })
            .IsUnique();
    }

    private static void ConfigureMedia(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<WhatsAppMediaRecord>();
        entity.ToTable("whatsapp_media", "business");
        entity.HasKey(value => value.MediaId);
        entity
            .HasIndex(value => new
            {
                value.Environment,
                value.TenantId,
                value.RelationshipId,
                value.ProviderReferenceDigest,
            })
            .IsUnique();
        entity.Property(value => value.DerivativePayloadReferencesJson).HasColumnType("jsonb");
    }

    private static void ConfigureMigration(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<ConversationMigrationWatermark>();
        entity.ToTable("conversation_migration_watermarks", "business");
        entity.HasKey(value => new
        {
            value.MigrationId,
            value.Environment,
            value.Owner,
        });
    }

    private static void ConfigureEmergencyStopLatch(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<RelationshipEmergencyStopLatch>();
        entity.ToTable("relationship_emergency_stop_latches", "business");
        entity.HasKey(value => value.LatchId);
        entity
            .HasIndex(value => new
            {
                value.Environment,
                value.TenantId,
                value.RelationshipId,
            })
            .IsUnique();
    }

    private static void ConfigureOperationalSignal(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<ConversationOperationalSignal>();
        entity.ToTable("conversation_operational_signals", "business");
        entity.HasKey(value => value.SignalId);
        entity.HasIndex(value => new
        {
            value.Environment,
            value.Category,
            value.Code,
            value.State,
            value.OccurredAt,
        });
    }

    private static void MapColumns<TEntity>(ModelBuilder modelBuilder)
        where TEntity : class
    {
        var entity = modelBuilder.Entity<TEntity>();
        foreach (var property in entity.Metadata.GetProperties())
            property.SetColumnName(ToSnakeCase(property.Name));
    }

    private static string ToSnakeCase(string value)
    {
        var result = new StringBuilder(value.Length + 8);
        for (var index = 0; index < value.Length; index++)
        {
            var character = value[index];
            if (
                index > 0
                && char.IsUpper(character)
                && (
                    char.IsLower(value[index - 1])
                    || (index + 1 < value.Length && char.IsLower(value[index + 1]))
                )
            )
                result.Append('_');
            result.Append(char.ToLowerInvariant(character));
        }
        return result.ToString();
    }
}
