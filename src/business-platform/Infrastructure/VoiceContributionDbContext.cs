// Implements: architecture/reference/data/wc062-voice-data-contract.md § State And Lineage
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

using Microsoft.EntityFrameworkCore;

namespace Waooaw.BusinessPlatform.Infrastructure;

public sealed class VoiceContributionSession
{
    public Guid SessionId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid ActorParticipantId { get; init; }
    public Guid? ContributionId { get; set; }
    public string SchemaVersion { get; init; } = "1.0";
    public string State { get; set; } = "CREATED";
    public string SelectedLocale { get; init; } = string.Empty;
    public string ConsentVersion { get; init; } = string.Empty;
    public int CurrentTranscriptVersion { get; set; }
    public Guid? AcceptedTranscriptId { get; set; }
    public Guid? EvidenceReference { get; set; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset ExpiresAt { get; init; }
}

public sealed class VoiceAudioPayload
{
    public Guid AudioPayloadId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid SessionId { get; init; }
    public string ContentSha256 { get; init; } = string.Empty;
    public string DeclaredMediaType { get; init; } = string.Empty;
    public string DetectedMediaType { get; init; } = string.Empty;
    public long SizeBytes { get; init; }
    public int DurationMilliseconds { get; init; }
    public string ScanState { get; set; } = "PENDING";
    public string? PayloadReference { get; set; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset RetainUntil { get; set; }
    public DateTimeOffset? ErasedAt { get; set; }
}

public sealed class VoiceTranscriptVersion
{
    public Guid TranscriptId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid SessionId { get; init; }
    public Guid AudioPayloadId { get; init; }
    public int Version { get; init; }
    public Guid? PredecessorTranscriptId { get; init; }
    public string Source { get; init; } = "PROVIDER";
    public string Locale { get; init; } = string.Empty;
    public string LocaleSource { get; init; } = "DECLARED";
    public decimal? Confidence { get; init; }
    public string ConfidenceBand { get; init; } = "UNKNOWN";
    public string TextCiphertext { get; set; } = string.Empty;
    public string TextSha256 { get; init; } = string.Empty;
    public string ContractVersion { get; init; } = "1.0.0";
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? ErasedAt { get; set; }
}

public sealed class VoiceIdempotencyOutcome
{
    public Guid OutcomeId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid ActorParticipantId { get; init; }
    public Guid? SessionId { get; init; }
    public string Operation { get; init; } = string.Empty;
    public Guid IdempotencyKey { get; init; }
    public string RequestSha256 { get; init; } = string.Empty;
    public string ResponseJson { get; set; } = "{}";
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class VoiceErasureTombstone
{
    public Guid TombstoneId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid ContributionId { get; init; }
    public Guid ActorParticipantId { get; init; }
    public string Scope { get; init; } = string.Empty;
    public string ReasonClass { get; init; } = string.Empty;
    public Guid EvidenceReference { get; init; }
    public DateTimeOffset ErasedAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class VoiceContributionDbContext : DbContext
{
    public VoiceContributionDbContext(DbContextOptions<VoiceContributionDbContext> options)
        : base(options) { }

    public DbSet<VoiceContributionSession> Sessions => Set<VoiceContributionSession>();
    public DbSet<VoiceAudioPayload> AudioPayloads => Set<VoiceAudioPayload>();
    public DbSet<VoiceTranscriptVersion> TranscriptVersions => Set<VoiceTranscriptVersion>();
    public DbSet<VoiceIdempotencyOutcome> IdempotencyOutcomes => Set<VoiceIdempotencyOutcome>();
    public DbSet<VoiceErasureTombstone> ErasureTombstones => Set<VoiceErasureTombstone>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        ConfigureSession(modelBuilder.Entity<VoiceContributionSession>());
        ConfigureAudio(modelBuilder.Entity<VoiceAudioPayload>());
        ConfigureTranscript(modelBuilder.Entity<VoiceTranscriptVersion>());
        ConfigureIdempotency(modelBuilder.Entity<VoiceIdempotencyOutcome>());
        ConfigureTombstone(modelBuilder.Entity<VoiceErasureTombstone>());
    }

    private static void ConfigureSession(Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<VoiceContributionSession> entity)
    {
        entity.ToTable("voice_contribution_sessions", "business");
        entity.HasKey(value => value.SessionId);
        entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.SessionId }).IsUnique();
        entity.HasIndex(value => new { value.TenantId, value.ContributionId }).IsUnique();
        entity.Property(value => value.SessionId).HasColumnName("session_id");
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
        entity.Property(value => value.ActorParticipantId).HasColumnName("actor_participant_id");
        entity.Property(value => value.ContributionId).HasColumnName("contribution_id");
        entity.Property(value => value.SchemaVersion).HasColumnName("schema_version");
        entity.Property(value => value.State).HasColumnName("state").IsConcurrencyToken();
        entity.Property(value => value.SelectedLocale).HasColumnName("selected_locale");
        entity.Property(value => value.ConsentVersion).HasColumnName("consent_version");
        entity.Property(value => value.CurrentTranscriptVersion).HasColumnName("current_transcript_version");
        entity.Property(value => value.AcceptedTranscriptId).HasColumnName("accepted_transcript_id");
        entity.Property(value => value.EvidenceReference).HasColumnName("evidence_reference");
        entity.Property(value => value.CreatedAt).HasColumnName("created_at");
        entity.Property(value => value.UpdatedAt).HasColumnName("updated_at");
        entity.Property(value => value.ExpiresAt).HasColumnName("expires_at");
    }

    private static void ConfigureAudio(Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<VoiceAudioPayload> entity)
    {
        entity.ToTable("voice_audio_payloads", "business");
        entity.HasKey(value => value.AudioPayloadId);
        entity.HasIndex(value => new { value.TenantId, value.SessionId }).IsUnique();
        entity.Property(value => value.AudioPayloadId).HasColumnName("audio_payload_id");
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
        entity.Property(value => value.SessionId).HasColumnName("session_id");
        entity.Property(value => value.ContentSha256).HasColumnName("content_sha256");
        entity.Property(value => value.DeclaredMediaType).HasColumnName("declared_media_type");
        entity.Property(value => value.DetectedMediaType).HasColumnName("detected_media_type");
        entity.Property(value => value.SizeBytes).HasColumnName("size_bytes");
        entity.Property(value => value.DurationMilliseconds).HasColumnName("duration_milliseconds");
        entity.Property(value => value.ScanState).HasColumnName("scan_state");
        entity.Property(value => value.PayloadReference).HasColumnName("payload_reference");
        entity.Property(value => value.CreatedAt).HasColumnName("created_at");
        entity.Property(value => value.RetainUntil).HasColumnName("retain_until");
        entity.Property(value => value.ErasedAt).HasColumnName("erased_at");
    }

    private static void ConfigureTranscript(Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<VoiceTranscriptVersion> entity)
    {
        entity.ToTable("voice_transcript_versions", "business");
        entity.HasKey(value => value.TranscriptId);
        entity.HasIndex(value => new { value.TenantId, value.SessionId, value.Version }).IsUnique();
        entity.Property(value => value.TranscriptId).HasColumnName("transcript_id");
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
        entity.Property(value => value.SessionId).HasColumnName("session_id");
        entity.Property(value => value.AudioPayloadId).HasColumnName("audio_payload_id");
        entity.Property(value => value.Version).HasColumnName("version");
        entity.Property(value => value.PredecessorTranscriptId).HasColumnName("predecessor_transcript_id");
        entity.Property(value => value.Source).HasColumnName("source");
        entity.Property(value => value.Locale).HasColumnName("locale");
        entity.Property(value => value.LocaleSource).HasColumnName("locale_source");
        entity.Property(value => value.Confidence).HasColumnName("confidence").HasPrecision(5, 4);
        entity.Property(value => value.ConfidenceBand).HasColumnName("confidence_band");
        entity.Property(value => value.TextCiphertext).HasColumnName("text_ciphertext");
        entity.Property(value => value.TextSha256).HasColumnName("text_sha256");
        entity.Property(value => value.ContractVersion).HasColumnName("contract_version");
        entity.Property(value => value.CreatedAt).HasColumnName("created_at");
        entity.Property(value => value.ErasedAt).HasColumnName("erased_at");
    }

    private static void ConfigureIdempotency(Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<VoiceIdempotencyOutcome> entity)
    {
        entity.ToTable("voice_idempotency_outcomes", "business");
        entity.HasKey(value => value.OutcomeId);
        entity.HasIndex(value => new
        {
            value.TenantId,
            value.RelationshipId,
            value.ActorParticipantId,
            value.Operation,
            value.IdempotencyKey,
        }).IsUnique();
        entity.Property(value => value.OutcomeId).HasColumnName("outcome_id");
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
        entity.Property(value => value.ActorParticipantId).HasColumnName("actor_participant_id");
        entity.Property(value => value.SessionId).HasColumnName("session_id");
        entity.Property(value => value.Operation).HasColumnName("operation");
        entity.Property(value => value.IdempotencyKey).HasColumnName("idempotency_key");
        entity.Property(value => value.RequestSha256).HasColumnName("request_sha256");
        entity.Property(value => value.ResponseJson).HasColumnName("response_json").HasColumnType("jsonb");
        entity.Property(value => value.CreatedAt).HasColumnName("created_at");
    }

    private static void ConfigureTombstone(Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<VoiceErasureTombstone> entity)
    {
        entity.ToTable("voice_erasure_tombstones", "business");
        entity.HasKey(value => value.TombstoneId);
        entity.HasIndex(value => new { value.TenantId, value.ContributionId, value.Scope }).IsUnique();
        entity.Property(value => value.TombstoneId).HasColumnName("tombstone_id");
        entity.Property(value => value.TenantId).HasColumnName("tenant_id");
        entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
        entity.Property(value => value.ContributionId).HasColumnName("contribution_id");
        entity.Property(value => value.ActorParticipantId).HasColumnName("actor_participant_id");
        entity.Property(value => value.Scope).HasColumnName("scope");
        entity.Property(value => value.ReasonClass).HasColumnName("reason_class");
        entity.Property(value => value.EvidenceReference).HasColumnName("evidence_reference");
        entity.Property(value => value.ErasedAt).HasColumnName("erased_at");
    }
}