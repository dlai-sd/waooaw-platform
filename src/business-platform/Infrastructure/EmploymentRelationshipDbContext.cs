// Implements: architecture/reference/product/ae01-relationship-data-contract.md § Migration 19 and § Migration 22
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

using Microsoft.EntityFrameworkCore;

namespace Waooaw.BusinessPlatform.Infrastructure;

public enum EmploymentRelationshipState
{
    Discovered,
    Interviewing,
    TrialActive,
    Configuring,
    ContractPendingAcceptance,
    ContractAcceptedPendingPayment,
    ActivationPending,
    Active,
    Paused,
    StoppedEmergency,
    Terminated,
}

public enum RelationshipParticipantRole
{
    Evaluator,
    Employer,
    OutcomeOwner,
    RelationshipManager,
    ConstitutionalAuthority,
}

public sealed class EmploymentRelationship
{
    public Guid RelationshipId { get; set; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public string ProfessionalType { get; init; } = string.Empty;
    public Guid EvaluationIntentId { get; init; }
    public Guid InitiatingParticipantId { get; init; }
    public Guid? SourceRelationshipId { get; init; }
    public Guid? ForkEvidenceId { get; init; }
    public EmploymentRelationshipState State { get; set; } = EmploymentRelationshipState.Discovered;
    public int StateVersion { get; set; }
    public Guid? AuthoritySnapshotId { get; set; }
    public Guid? AcceptedContractId { get; set; }
    public Guid? ActivationId { get; set; }
    public DateTimeOffset? StoppedAt { get; set; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class RelationshipParticipant
{
    public Guid BindingId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid ParticipantId { get; init; }
    public RelationshipParticipantRole Role { get; init; }
    public string Status { get; set; } = "ACTIVE";
    public Guid BoundEvidenceId { get; init; }
    public DateTimeOffset BoundAt { get; init; } = DateTimeOffset.UtcNow;
    public Guid? RevokedEvidenceId { get; set; }
    public DateTimeOffset? RevokedAt { get; set; }
}

public sealed class RelationshipStateHistory
{
    public Guid HistoryId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public int StateVersion { get; init; }
    public EmploymentRelationshipState? FromState { get; init; }
    public EmploymentRelationshipState ToState { get; init; }
    public Guid ActorParticipantId { get; init; }
    public RelationshipParticipantRole ActorRole { get; init; }
    public Guid? AuthoritySnapshotId { get; init; }
    public Guid CorrelationId { get; init; }
    public Guid EvidenceId { get; init; }
    public DateTimeOffset OccurredAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class RelationshipIdempotency
{
    public Guid IdempotencyId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public string Purpose { get; init; } = string.Empty;
    public string IdempotencyKey { get; init; } = string.Empty;
    public string MaterialRequestHash { get; init; } = string.Empty;
    public Guid? OutcomeReference { get; set; }
    public string Status { get; set; } = "RECEIVED";
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? CompletedAt { get; set; }
}

public sealed class RelationshipContextPayload
{
    public Guid PayloadReference { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public string FieldType { get; init; } = string.Empty;
    public string? ValueJson { get; set; }
    public string Source { get; init; } = string.Empty;
    public decimal? Confidence { get; init; }
    public string ConfirmationStatus { get; set; } = "UNCONFIRMED";
    public DateTimeOffset? ConfirmedAt { get; set; }
    public DateTimeOffset? InvalidatedAt { get; set; }
    public string PayloadHash { get; init; } = string.Empty;
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? ErasedAt { get; set; }
}

public sealed class ContextConfirmationEvent
{
    public Guid EventId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid PayloadReference { get; init; }
    public string PayloadHash { get; init; } = string.Empty;
    public string FieldType { get; init; } = string.Empty;
    public string Action { get; init; } = string.Empty;
    public Guid ActorParticipantId { get; init; }
    public Guid CorrelationId { get; init; }
    public Guid EvidenceId { get; init; }
    public DateTimeOffset OccurredAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class RelationshipGoal
{
    public Guid GoalId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public string Goal { get; set; } = string.Empty;
    public string? Baseline { get; set; }
    public string Measure { get; set; } = string.Empty;
    public string? DecisionThreshold { get; set; }
    public string? EvidenceSource { get; set; }
    public int ReviewCadenceMonths { get; set; } = 2;
    public string Status { get; set; } = "PROPOSED";
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class RelationshipSkillConfiguration
{
    public Guid ConfigurationId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public string SkillId { get; init; } = string.Empty;
    public string SkillVersion { get; init; } = string.Empty;
    public Guid? GoalId { get; init; }
    public string AuthorityState { get; set; } = "NOT_GRANTED";
    public string Applicability { get; set; } = "APPLICABLE";
    public string? ApplicabilityReason { get; set; }
    public string Status { get; set; } = "PROPOSED";
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class DecisionSpaceSnapshot
{
    public Guid SnapshotId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public int Version { get; init; }
    public long BudgetCeilingInrPaise { get; init; }
    public string AuthorityBoundariesJson { get; init; } = "[]";
    public string StopConditionsJson { get; init; } = "[]";
    public int ReviewCadenceMonths { get; init; } = 2;
    public string AcceptedEvidenceJson { get; init; } = "[]";
    public Guid CreatedByParticipantId { get; init; }
    public Guid EvidenceId { get; init; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class EmploymentContractVersion
{
    public Guid ContractId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public int Version { get; init; }
    public string ContractHash { get; init; } = string.Empty;
    public string AeecVersion { get; init; } = string.Empty;
    public Guid? DomainSchedulePayloadReference { get; init; }
    public string DomainScheduleHash { get; init; } = string.Empty;
    public string ConfigurationSnapshotJson { get; init; } = "{}";
    public string PriceTaxSummaryJson { get; init; } = "{}";
    public string State { get; init; } = "PRESENTED";
    public Guid CreatedByParticipantId { get; init; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class ContractAcceptance
{
    public Guid AcceptanceId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid ContractId { get; init; }
    public int ContractVersion { get; init; }
    public string ContractHash { get; init; } = string.Empty;
    public Guid ParticipantId { get; init; }
    public RelationshipParticipantRole ParticipantRole { get; init; }
    public string AuthenticationAssurance { get; init; } = string.Empty;
    public Guid AuthoritySnapshotId { get; init; }
    public string ScopeConfirmationHash { get; init; } = string.Empty;
    public Guid AcceptanceEvidenceId { get; init; }
    public DateTimeOffset AcceptedAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class ActivationIntent
{
    public Guid ActivationIntentId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid AcceptedContractId { get; init; }
    public Guid ContractAcceptanceId { get; init; }
    public string PaymentReference { get; init; } = string.Empty;
    public Guid CorrelationId { get; init; }
    public string MaterialRequestHash { get; init; } = string.Empty;
    public string? ConflictingRequestHash { get; set; }
    public string Status { get; set; } = "PENDING";
    public Guid? OutcomeSubscriptionId { get; set; }
    public Guid? OutcomeEvidenceId { get; set; }
    public string? OutcomeJson { get; set; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? CompletedAt { get; set; }
}

public sealed class OfferabilityDecisionRecord
{
    public Guid DecisionId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public int RelationshipStateVersion { get; init; }
    public string PolicyVersion { get; init; } = string.Empty;
    public string Disposition { get; init; } = string.Empty;
    public decimal DirectContributionAmount { get; init; }
    public string OwnerVersionsJson { get; init; } = "{}";
    public string ReasonsJson { get; init; } = "[]";
    public Guid EvidenceId { get; init; }
    public DateTimeOffset ProducedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset ExpiresAt { get; init; }
}

public sealed class RelationshipTrialBinding
{
    public Guid BindingId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid CustomerId { get; init; }
    public Guid CorrelationId { get; init; }
    public Guid? TrialId { get; set; }
    public DateTimeOffset? StartsAt { get; set; }
    public DateTimeOffset? ExpiresAt { get; set; }
    public string Status { get; set; } = "PENDING";
    public string? UnresolvedOwner { get; set; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class WhatsAppJourneyContact
{
    public Guid ContactId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public string PhoneHmac { get; init; } = string.Empty;
    public DateTimeOffset OptedInAt { get; init; }
    public DateTimeOffset LastInboundAt { get; set; }
    public string JourneyStage { get; set; } = "DISCOVER";
    public bool PendingMediumRiskConfirmation { get; set; }
    public string? MpinHash { get; set; }
    public int MpinFailedAttempts { get; set; }
    public DateTimeOffset? MpinLockedUntil { get; set; }
}

public sealed class WhatsAppMessageReceipt
{
    public string MessageId { get; init; } = string.Empty;
    public Guid TenantId { get; init; }
    public string SessionTokenHash { get; init; } = string.Empty;
    public DateTimeOffset SessionExpiresAt { get; init; }
    public DateTimeOffset ReceivedAt { get; init; }
    public DateTimeOffset ExpiresAt { get; init; }
}

// ── Migration 22 — Continuity and Evidence Projection ────────────────────────

public sealed class ChannelBinding
{
    public Guid BindingId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid ParticipantId { get; init; }
    public string ParticipantRole { get; init; } = string.Empty;
    public string Channel { get; init; } = string.Empty;
    public string ExternalSubjectHash { get; init; } = string.Empty;
    public string ConversationId { get; init; } = string.Empty;
    public string AssuranceLevel { get; init; } = string.Empty;
    public string Status { get; set; } = "PREPARED";
    public Guid PreparedEvidenceId { get; init; }
    public Guid? BoundEvidenceId { get; set; }
    public Guid? RevokedEvidenceId { get; set; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? BoundAt { get; set; }
    public DateTimeOffset? RevokedAt { get; set; }
}

public sealed class ContinuityCheckpoint
{
    public Guid CheckpointId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid SourceBindingId { get; init; }
    public Guid TargetBindingId { get; init; }
    public string ContinuityEnvelopeHash { get; init; } = string.Empty;
    public string? ContinuityEnvelopeJson { get; init; }
    public string MaterialRequestHash { get; init; } = string.Empty;
    public Guid CausalMarker { get; init; }
    public long SequenceNumber { get; init; }
    public Guid IdempotencyKey { get; init; }
    public string Status { get; set; } = "PREPARED";
    public Guid PreparedEvidenceId { get; init; }
    public Guid? ResolutionEvidenceId { get; set; }
    public DateTimeOffset PreparedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset ExpiresAt { get; init; }
    public DateTimeOffset? ResolvedAt { get; set; }
}

public sealed class DeliveryAcknowledgement
{
    public Guid AcknowledgementId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid? CheckpointId { get; init; }
    public Guid BindingId { get; init; }
    public string MessageIdHash { get; init; } = string.Empty;
    public string AcknowledgementType { get; init; } = string.Empty;
    public DateTimeOffset AcknowledgedAt { get; init; }
    public Guid EvidenceId { get; init; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class ChannelMessageDeduplication
{
    public Guid DeduplicationId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid BindingId { get; init; }
    public string ProviderMessageIdHash { get; init; } = string.Empty;
    public string MaterialMessageHash { get; init; } = string.Empty;
    public DateTimeOffset ReceivedAt { get; init; } = DateTimeOffset.UtcNow;
    public Guid? OutcomeReference { get; set; }
    public string Status { get; set; } = "RECEIVED";
    public DateTimeOffset ExpiresAt { get; init; }
}

public sealed class RelationshipEvidenceExport
{
    public Guid ExportId { get; init; } = Guid.NewGuid();
    public Guid TenantId { get; init; }
    public Guid RelationshipId { get; init; }
    public Guid ParticipantId { get; init; }
    public string ParticipantRole { get; init; } = string.Empty;
    public Guid IdempotencyKey { get; init; }
    public string MaterialRequestHash { get; init; } = string.Empty;
    public string DocumentJson { get; init; } = string.Empty;
    public string DocumentSha256 { get; init; } = string.Empty;
    public Guid EvidenceId { get; init; }
    public DateTimeOffset CreatedAt { get; init; }
    public DateTimeOffset ExpiresAt { get; init; }
}

public sealed class EmploymentRelationshipDbContext : DbContext
{
    public EmploymentRelationshipDbContext(DbContextOptions<EmploymentRelationshipDbContext> options)
        : base(options) { }

    public DbSet<EmploymentRelationship> EmploymentRelationships => Set<EmploymentRelationship>();
    public DbSet<RelationshipParticipant> RelationshipParticipants => Set<RelationshipParticipant>();
    public DbSet<RelationshipStateHistory> RelationshipStateHistory => Set<RelationshipStateHistory>();
    public DbSet<RelationshipIdempotency> RelationshipIdempotency => Set<RelationshipIdempotency>();
    public DbSet<RelationshipContextPayload> RelationshipContextPayloads => Set<RelationshipContextPayload>();
    public DbSet<ContextConfirmationEvent> ContextConfirmationEvents => Set<ContextConfirmationEvent>();
    public DbSet<RelationshipGoal> RelationshipGoals => Set<RelationshipGoal>();
    public DbSet<RelationshipSkillConfiguration> RelationshipSkillConfigurations => Set<RelationshipSkillConfiguration>();
    public DbSet<DecisionSpaceSnapshot> DecisionSpaceSnapshots => Set<DecisionSpaceSnapshot>();
    public DbSet<EmploymentContractVersion> EmploymentContractVersions => Set<EmploymentContractVersion>();
    public DbSet<ContractAcceptance> ContractAcceptances => Set<ContractAcceptance>();
    public DbSet<ActivationIntent> ActivationIntents => Set<ActivationIntent>();
    public DbSet<OfferabilityDecisionRecord> OfferabilityDecisions => Set<OfferabilityDecisionRecord>();
    public DbSet<RelationshipTrialBinding> RelationshipTrialBindings => Set<RelationshipTrialBinding>();
    public DbSet<WhatsAppJourneyContact> WhatsAppJourneyContacts => Set<WhatsAppJourneyContact>();
    public DbSet<WhatsAppMessageReceipt> WhatsAppMessageReceipts => Set<WhatsAppMessageReceipt>();
    public DbSet<ChannelBinding> ChannelBindings => Set<ChannelBinding>();
    public DbSet<ContinuityCheckpoint> ContinuityCheckpoints => Set<ContinuityCheckpoint>();
    public DbSet<DeliveryAcknowledgement> DeliveryAcknowledgements => Set<DeliveryAcknowledgement>();
    public DbSet<ChannelMessageDeduplication> ChannelMessageDeduplications => Set<ChannelMessageDeduplication>();
    public DbSet<RelationshipEvidenceExport> RelationshipEvidenceExports => Set<RelationshipEvidenceExport>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<EmploymentRelationship>(entity =>
        {
            entity.ToTable("employment_relationships", "business");
            entity.HasKey(value => value.RelationshipId);
            entity.HasAlternateKey(value => new { value.TenantId, value.RelationshipId });
            entity.HasIndex(value => new
            {
                value.TenantId,
                value.InitiatingParticipantId,
                value.ProfessionalType,
                value.EvaluationIntentId,
            }).IsUnique();
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.ProfessionalType).HasColumnName("professional_type");
            entity.Property(value => value.EvaluationIntentId).HasColumnName("evaluation_intent_id");
            entity.Property(value => value.InitiatingParticipantId).HasColumnName("initiating_participant_id");
            entity.Property(value => value.SourceRelationshipId).HasColumnName("source_relationship_id");
            entity.Property(value => value.ForkEvidenceId).HasColumnName("fork_evidence_id");
            entity.Property(value => value.State).HasColumnName("state").HasConversion(
                value => RelationshipStateCodec.ToDatabase(value),
                value => RelationshipStateCodec.FromDatabase(value));
            entity.Property(value => value.StateVersion).HasColumnName("state_version").IsConcurrencyToken();
            entity.Property(value => value.AuthoritySnapshotId).HasColumnName("authority_snapshot_id");
            entity.Property(value => value.AcceptedContractId).HasColumnName("accepted_contract_id");
            entity.Property(value => value.ActivationId).HasColumnName("activation_id");
            entity.Property(value => value.StoppedAt).HasColumnName("stopped_at");
            entity.Property(value => value.CreatedAt).HasColumnName("created_at");
            entity.Property(value => value.UpdatedAt).HasColumnName("updated_at");
        });

        modelBuilder.Entity<RelationshipParticipant>(entity =>
        {
            entity.ToTable("relationship_participants", "business");
            entity.HasKey(value => value.BindingId);
            entity.Property(value => value.BindingId).HasColumnName("binding_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.ParticipantId).HasColumnName("participant_id");
            entity.Property(value => value.Role).HasColumnName("role").HasConversion(
                value => RelationshipRoleCodec.ToDatabase(value),
                value => RelationshipRoleCodec.FromDatabase(value));
            entity.Property(value => value.Status).HasColumnName("status");
            entity.Property(value => value.BoundEvidenceId).HasColumnName("bound_evidence_id");
            entity.Property(value => value.BoundAt).HasColumnName("bound_at");
            entity.Property(value => value.RevokedEvidenceId).HasColumnName("revoked_evidence_id");
            entity.Property(value => value.RevokedAt).HasColumnName("revoked_at");
            entity.HasOne<EmploymentRelationship>()
                .WithMany()
                .HasForeignKey(value => new { value.TenantId, value.RelationshipId })
                .HasPrincipalKey(value => new { value.TenantId, value.RelationshipId });
        });

        modelBuilder.Entity<RelationshipStateHistory>(entity =>
        {
            entity.ToTable("relationship_state_history", "business");
            entity.HasKey(value => value.HistoryId);
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.StateVersion }).IsUnique();
            entity.Property(value => value.HistoryId).HasColumnName("history_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.StateVersion).HasColumnName("state_version");
            entity.Property(value => value.FromState).HasColumnName("from_state").HasConversion(
                value => value.HasValue ? RelationshipStateCodec.ToDatabase(value.Value) : null,
                value => value == null ? null : RelationshipStateCodec.FromDatabase(value));
            entity.Property(value => value.ToState).HasColumnName("to_state").HasConversion(
                value => RelationshipStateCodec.ToDatabase(value),
                value => RelationshipStateCodec.FromDatabase(value));
            entity.Property(value => value.ActorParticipantId).HasColumnName("actor_participant_id");
            entity.Property(value => value.ActorRole).HasColumnName("actor_role").HasConversion(
                value => RelationshipRoleCodec.ToDatabase(value),
                value => RelationshipRoleCodec.FromDatabase(value));
            entity.Property(value => value.AuthoritySnapshotId).HasColumnName("authority_snapshot_id");
            entity.Property(value => value.CorrelationId).HasColumnName("correlation_id");
            entity.Property(value => value.EvidenceId).HasColumnName("evidence_id");
            entity.Property(value => value.OccurredAt).HasColumnName("occurred_at");
            entity.HasOne<EmploymentRelationship>()
                .WithMany()
                .HasForeignKey(value => new { value.TenantId, value.RelationshipId })
                .HasPrincipalKey(value => new { value.TenantId, value.RelationshipId });
        });

        modelBuilder.Entity<RelationshipIdempotency>(entity =>
        {
            entity.ToTable("relationship_idempotency", "business");
            entity.HasKey(value => value.IdempotencyId);
            entity.HasIndex(value => new { value.TenantId, value.Purpose, value.IdempotencyKey }).IsUnique();
            entity.Property(value => value.IdempotencyId).HasColumnName("idempotency_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.Purpose).HasColumnName("purpose");
            entity.Property(value => value.IdempotencyKey).HasColumnName("idempotency_key");
            entity.Property(value => value.MaterialRequestHash).HasColumnName("material_request_hash");
            entity.Property(value => value.OutcomeReference).HasColumnName("outcome_reference");
            entity.Property(value => value.Status).HasColumnName("status");
            entity.Property(value => value.CreatedAt).HasColumnName("created_at");
            entity.Property(value => value.CompletedAt).HasColumnName("completed_at");
            entity.HasOne<EmploymentRelationship>()
                .WithMany()
                .HasForeignKey(value => new { value.TenantId, value.RelationshipId })
                .HasPrincipalKey(value => new { value.TenantId, value.RelationshipId });
        });

        modelBuilder.Entity<OfferabilityDecisionRecord>(entity =>
        {
            entity.ToTable("offerability_decisions", "business");
            entity.HasKey(value => value.DecisionId);
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.ProducedAt });
            entity.Property(value => value.DecisionId).HasColumnName("decision_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.RelationshipStateVersion).HasColumnName("relationship_state_version");
            entity.Property(value => value.PolicyVersion).HasColumnName("policy_version");
            entity.Property(value => value.Disposition).HasColumnName("disposition");
            entity.Property(value => value.DirectContributionAmount).HasColumnName("direct_contribution_amount");
            entity.Property(value => value.OwnerVersionsJson).HasColumnName("owner_versions_json").HasColumnType("jsonb");
            entity.Property(value => value.ReasonsJson).HasColumnName("reasons_json").HasColumnType("jsonb");
            entity.Property(value => value.EvidenceId).HasColumnName("evidence_id");
            entity.Property(value => value.ProducedAt).HasColumnName("produced_at");
            entity.Property(value => value.ExpiresAt).HasColumnName("expires_at");
            entity.HasOne<EmploymentRelationship>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.RelationshipId })
                .HasPrincipalKey(value => new { value.TenantId, value.RelationshipId });
        });

        modelBuilder.Entity<RelationshipContextPayload>(entity =>
        {
            entity.ToTable("relationship_context_payloads", "payload_store");
            entity.HasKey(value => value.PayloadReference);
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.FieldType });
            entity.Property(value => value.PayloadReference).HasColumnName("payload_reference");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.FieldType).HasColumnName("field_type");
            entity.Property(value => value.ValueJson).HasColumnName("value_json").HasColumnType("jsonb");
            entity.Property(value => value.Source).HasColumnName("source");
            entity.Property(value => value.Confidence).HasColumnName("confidence");
            entity.Property(value => value.ConfirmationStatus).HasColumnName("confirmation_status");
            entity.Property(value => value.ConfirmedAt).HasColumnName("confirmed_at");
            entity.Property(value => value.InvalidatedAt).HasColumnName("invalidated_at");
            entity.Property(value => value.PayloadHash).HasColumnName("payload_hash");
            entity.Property(value => value.CreatedAt).HasColumnName("created_at");
            entity.Property(value => value.ErasedAt).HasColumnName("erased_at");
            entity.HasOne<EmploymentRelationship>()
                .WithMany()
                .HasForeignKey(value => new { value.TenantId, value.RelationshipId })
                .HasPrincipalKey(value => new { value.TenantId, value.RelationshipId });
        });

        modelBuilder.Entity<ContextConfirmationEvent>(entity =>
        {
            entity.ToTable("context_confirmation_events", "business");
            entity.HasKey(value => value.EventId);
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.OccurredAt });
            entity.Property(value => value.EventId).HasColumnName("event_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.PayloadReference).HasColumnName("payload_reference");
            entity.Property(value => value.PayloadHash).HasColumnName("payload_hash");
            entity.Property(value => value.FieldType).HasColumnName("field_type");
            entity.Property(value => value.Action).HasColumnName("action");
            entity.Property(value => value.ActorParticipantId).HasColumnName("actor_participant_id");
            entity.Property(value => value.CorrelationId).HasColumnName("correlation_id");
            entity.Property(value => value.EvidenceId).HasColumnName("evidence_id");
            entity.Property(value => value.OccurredAt).HasColumnName("occurred_at");
            entity.HasOne<EmploymentRelationship>()
                .WithMany()
                .HasForeignKey(value => new { value.TenantId, value.RelationshipId })
                .HasPrincipalKey(value => new { value.TenantId, value.RelationshipId });
        });

        modelBuilder.Entity<RelationshipGoal>(entity =>
        {
            entity.ToTable("relationship_goals", "business");
            entity.HasKey(value => value.GoalId);
            entity.Property(value => value.GoalId).HasColumnName("goal_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.Goal).HasColumnName("goal");
            entity.Property(value => value.Baseline).HasColumnName("baseline");
            entity.Property(value => value.Measure).HasColumnName("measure");
            entity.Property(value => value.DecisionThreshold).HasColumnName("decision_threshold");
            entity.Property(value => value.EvidenceSource).HasColumnName("evidence_source");
            entity.Property(value => value.ReviewCadenceMonths).HasColumnName("review_cadence_months");
            entity.Property(value => value.Status).HasColumnName("status");
            entity.Property(value => value.CreatedAt).HasColumnName("created_at");
            entity.Property(value => value.UpdatedAt).HasColumnName("updated_at");
            entity.HasOne<EmploymentRelationship>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.RelationshipId })
                .HasPrincipalKey(value => new { value.TenantId, value.RelationshipId });
        });

        modelBuilder.Entity<RelationshipSkillConfiguration>(entity =>
        {
            entity.ToTable("relationship_skill_configuration", "business");
            entity.HasKey(value => value.ConfigurationId);
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.SkillId, value.SkillVersion }).IsUnique();
            entity.Property(value => value.ConfigurationId).HasColumnName("configuration_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.SkillId).HasColumnName("skill_id");
            entity.Property(value => value.SkillVersion).HasColumnName("skill_version");
            entity.Property(value => value.GoalId).HasColumnName("goal_id");
            entity.Property(value => value.AuthorityState).HasColumnName("authority_state");
            entity.Property(value => value.Applicability).HasColumnName("applicability");
            entity.Property(value => value.ApplicabilityReason).HasColumnName("applicability_reason");
            entity.Property(value => value.Status).HasColumnName("status");
            entity.Property(value => value.CreatedAt).HasColumnName("created_at");
            entity.Property(value => value.UpdatedAt).HasColumnName("updated_at");
            entity.HasOne<EmploymentRelationship>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.RelationshipId })
                .HasPrincipalKey(value => new { value.TenantId, value.RelationshipId });
        });

        modelBuilder.Entity<DecisionSpaceSnapshot>(entity =>
        {
            entity.ToTable("decision_space_snapshots", "business");
            entity.HasKey(value => value.SnapshotId);
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.Version }).IsUnique();
            entity.Property(value => value.SnapshotId).HasColumnName("snapshot_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.Version).HasColumnName("version");
            entity.Property(value => value.BudgetCeilingInrPaise).HasColumnName("budget_ceiling_inr_paise");
            entity.Property(value => value.AuthorityBoundariesJson).HasColumnName("authority_boundaries_json").HasColumnType("jsonb");
            entity.Property(value => value.StopConditionsJson).HasColumnName("stop_conditions_json").HasColumnType("jsonb");
            entity.Property(value => value.ReviewCadenceMonths).HasColumnName("review_cadence_months");
            entity.Property(value => value.AcceptedEvidenceJson).HasColumnName("accepted_evidence_json").HasColumnType("jsonb");
            entity.Property(value => value.CreatedByParticipantId).HasColumnName("created_by_participant_id");
            entity.Property(value => value.EvidenceId).HasColumnName("evidence_id");
            entity.Property(value => value.CreatedAt).HasColumnName("created_at");
            entity.HasOne<EmploymentRelationship>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.RelationshipId })
                .HasPrincipalKey(value => new { value.TenantId, value.RelationshipId });
        });

            modelBuilder.Entity<EmploymentContractVersion>(entity =>
            {
                entity.ToTable("employment_contract_versions", "business");
                entity.HasKey(value => value.ContractId);
                entity.HasAlternateKey(value => new
                {
                    value.TenantId,
                    value.RelationshipId,
                    value.ContractId,
                    value.Version,
                    value.ContractHash,
                });
                entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.Version }).IsUnique();
                entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.ContractHash }).IsUnique();
                entity.Property(value => value.ContractId).HasColumnName("contract_id");
                entity.Property(value => value.TenantId).HasColumnName("tenant_id");
                entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
                entity.Property(value => value.Version).HasColumnName("version");
                entity.Property(value => value.ContractHash).HasColumnName("contract_hash").HasMaxLength(64).IsFixedLength();
                entity.Property(value => value.AeecVersion).HasColumnName("aeec_version").HasMaxLength(32);
                entity.Property(value => value.DomainSchedulePayloadReference).HasColumnName("domain_schedule_payload_reference");
                entity.Property(value => value.DomainScheduleHash).HasColumnName("domain_schedule_hash").HasMaxLength(64).IsFixedLength();
                entity.Property(value => value.ConfigurationSnapshotJson).HasColumnName("configuration_snapshot_json").HasColumnType("jsonb");
                entity.Property(value => value.PriceTaxSummaryJson).HasColumnName("price_tax_summary_json").HasColumnType("jsonb");
                entity.Property(value => value.State).HasColumnName("state").HasMaxLength(16);
                entity.Property(value => value.CreatedByParticipantId).HasColumnName("created_by_participant_id");
                entity.Property(value => value.CreatedAt).HasColumnName("created_at");
                entity.HasOne<EmploymentRelationship>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.RelationshipId })
                .HasPrincipalKey(value => new { value.TenantId, value.RelationshipId });
            });

        modelBuilder.Entity<ContractAcceptance>(entity =>
        {
            entity.ToTable("contract_acceptances", "business");
            entity.HasKey(value => value.AcceptanceId);
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.ContractId }).IsUnique();
            entity.Property(value => value.AcceptanceId).HasColumnName("acceptance_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.ContractId).HasColumnName("contract_id");
            entity.Property(value => value.ContractVersion).HasColumnName("contract_version");
            entity.Property(value => value.ContractHash).HasColumnName("contract_hash").HasMaxLength(64).IsFixedLength();
            entity.Property(value => value.ParticipantId).HasColumnName("participant_id");
            entity.Property(value => value.ParticipantRole).HasColumnName("participant_role").HasConversion(
                value => RelationshipRoleCodec.ToDatabase(value),
                value => RelationshipRoleCodec.FromDatabase(value));
            entity.Property(value => value.AuthenticationAssurance).HasColumnName("authentication_assurance").HasMaxLength(32);
            entity.Property(value => value.AuthoritySnapshotId).HasColumnName("authority_snapshot_id");
            entity.Property(value => value.ScopeConfirmationHash).HasColumnName("scope_confirmation_hash").HasMaxLength(64).IsFixedLength();
            entity.Property(value => value.AcceptanceEvidenceId).HasColumnName("acceptance_evidence_id");
            entity.Property(value => value.AcceptedAt).HasColumnName("accepted_at");
            entity.HasOne<EmploymentContractVersion>().WithMany()
                .HasForeignKey(value => new
                {
                    value.TenantId,
                    value.RelationshipId,
                    value.ContractId,
                    value.ContractVersion,
                    value.ContractHash,
                })
                .HasPrincipalKey(value => new
                {
                    value.TenantId,
                    value.RelationshipId,
                    value.ContractId,
                    value.Version,
                    value.ContractHash,
                });
        });

        modelBuilder.Entity<ActivationIntent>(entity =>
        {
            entity.ToTable("activation_intents", "business");
            entity.HasKey(value => value.ActivationIntentId);
            entity.HasIndex(value => new
            {
                value.TenantId,
                value.RelationshipId,
                value.AcceptedContractId,
                value.PaymentReference,
            }).IsUnique();
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.CorrelationId }).IsUnique();
            entity.Property(value => value.ActivationIntentId).HasColumnName("activation_intent_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.AcceptedContractId).HasColumnName("accepted_contract_id");
            entity.Property(value => value.ContractAcceptanceId).HasColumnName("contract_acceptance_id");
            entity.Property(value => value.PaymentReference).HasColumnName("payment_reference").HasMaxLength(128);
            entity.Property(value => value.CorrelationId).HasColumnName("correlation_id");
            entity.Property(value => value.MaterialRequestHash).HasColumnName("material_request_hash").HasMaxLength(64).IsFixedLength();
            entity.Property(value => value.ConflictingRequestHash).HasColumnName("conflicting_request_hash").HasMaxLength(64).IsFixedLength();
            entity.Property(value => value.Status).HasColumnName("status").HasMaxLength(24);
            entity.Property(value => value.OutcomeSubscriptionId).HasColumnName("outcome_subscription_id");
            entity.Property(value => value.OutcomeEvidenceId).HasColumnName("outcome_evidence_id");
            entity.Property(value => value.OutcomeJson).HasColumnName("outcome_json").HasColumnType("jsonb");
            entity.Property(value => value.CreatedAt).HasColumnName("created_at");
            entity.Property(value => value.UpdatedAt).HasColumnName("updated_at");
            entity.Property(value => value.CompletedAt).HasColumnName("completed_at");
        });

        modelBuilder.Entity<RelationshipTrialBinding>(entity =>
        {
            entity.ToTable("relationship_trial_bindings", "business");
            entity.HasKey(value => value.BindingId);
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId }).IsUnique();
            entity.Property(value => value.BindingId).HasColumnName("binding_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.CustomerId).HasColumnName("customer_id");
            entity.Property(value => value.CorrelationId).HasColumnName("correlation_id");
            entity.Property(value => value.TrialId).HasColumnName("trial_id");
            entity.Property(value => value.StartsAt).HasColumnName("starts_at");
            entity.Property(value => value.ExpiresAt).HasColumnName("expires_at");
            entity.Property(value => value.Status).HasColumnName("status");
            entity.Property(value => value.UnresolvedOwner).HasColumnName("unresolved_owner");
            entity.Property(value => value.CreatedAt).HasColumnName("created_at");
            entity.Property(value => value.UpdatedAt).HasColumnName("updated_at");
            entity.HasOne<EmploymentRelationship>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.RelationshipId })
                .HasPrincipalKey(value => new { value.TenantId, value.RelationshipId });
        });

        modelBuilder.Entity<WhatsAppJourneyContact>(entity =>
        {
            entity.ToTable("whatsapp_journey_contacts", "business");
            entity.HasKey(value => value.ContactId);
            entity.HasIndex(value => value.PhoneHmac).IsUnique();
            entity.Property(value => value.ContactId).HasColumnName("contact_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.PhoneHmac).HasColumnName("phone_hmac");
            entity.Property(value => value.OptedInAt).HasColumnName("opted_in_at");
            entity.Property(value => value.LastInboundAt).HasColumnName("last_inbound_at");
            entity.Property(value => value.JourneyStage).HasColumnName("journey_stage");
            entity.Property(value => value.PendingMediumRiskConfirmation).HasColumnName("pending_medium_risk_confirmation");
            entity.Property(value => value.MpinHash).HasColumnName("mpin_hash").HasMaxLength(64).IsFixedLength();
            entity.Property(value => value.MpinFailedAttempts).HasColumnName("mpin_failed_attempts");
            entity.Property(value => value.MpinLockedUntil).HasColumnName("mpin_locked_until");
        });

        modelBuilder.Entity<WhatsAppMessageReceipt>(entity =>
        {
            entity.ToTable("whatsapp_message_receipts", "business");
            entity.HasKey(value => value.MessageId);
            entity.Property(value => value.MessageId).HasColumnName("message_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.SessionTokenHash).HasColumnName("session_token_hash");
            entity.Property(value => value.SessionExpiresAt).HasColumnName("session_expires_at");
            entity.Property(value => value.ReceivedAt).HasColumnName("received_at");
            entity.Property(value => value.ExpiresAt).HasColumnName("expires_at");
        });

        modelBuilder.Entity<ChannelBinding>(entity =>
        {
            entity.ToTable("channel_bindings", "business");
            entity.HasKey(value => value.BindingId);
            entity.HasAlternateKey(value => new { value.TenantId, value.BindingId });
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.Status });
            entity.HasIndex(value => new { value.TenantId, value.ConversationId });
            entity.Property(value => value.BindingId).HasColumnName("binding_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.ParticipantId).HasColumnName("participant_id");
            entity.Property(value => value.ParticipantRole).HasColumnName("participant_role");
            entity.Property(value => value.Channel).HasColumnName("channel");
            entity.Property(value => value.ExternalSubjectHash).HasColumnName("external_subject_hash").HasMaxLength(64).IsFixedLength();
            entity.Property(value => value.ConversationId).HasColumnName("conversation_id");
            entity.Property(value => value.AssuranceLevel).HasColumnName("assurance_level");
            entity.Property(value => value.Status).HasColumnName("status");
            entity.Property(value => value.PreparedEvidenceId).HasColumnName("prepared_evidence_id");
            entity.Property(value => value.BoundEvidenceId).HasColumnName("bound_evidence_id");
            entity.Property(value => value.RevokedEvidenceId).HasColumnName("revoked_evidence_id");
            entity.Property(value => value.CreatedAt).HasColumnName("created_at");
            entity.Property(value => value.BoundAt).HasColumnName("bound_at");
            entity.Property(value => value.RevokedAt).HasColumnName("revoked_at");
            entity.HasOne<EmploymentRelationship>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.RelationshipId })
                .HasPrincipalKey(value => new { value.TenantId, value.RelationshipId });
        });

        modelBuilder.Entity<ContinuityCheckpoint>(entity =>
        {
            entity.ToTable("continuity_checkpoints", "business");
            entity.HasKey(value => value.CheckpointId);
            entity.HasAlternateKey(value => new { value.TenantId, value.CheckpointId });
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.IdempotencyKey }).IsUnique();
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.CausalMarker }).IsUnique();
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.SequenceNumber }).IsUnique();
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.Status });
            entity.HasIndex(value => new { value.TenantId, value.TargetBindingId, value.Status });
            entity.Property(value => value.CheckpointId).HasColumnName("checkpoint_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.SourceBindingId).HasColumnName("source_binding_id");
            entity.Property(value => value.TargetBindingId).HasColumnName("target_binding_id");
            entity.Property(value => value.ContinuityEnvelopeHash).HasColumnName("continuity_envelope_hash").HasMaxLength(64).IsFixedLength();
            entity.Property(value => value.ContinuityEnvelopeJson).HasColumnName("continuity_envelope").HasColumnType("jsonb");
            entity.Property(value => value.MaterialRequestHash).HasColumnName("material_request_hash").HasMaxLength(64).IsFixedLength();
            entity.Property(value => value.CausalMarker).HasColumnName("causal_marker");
            entity.Property(value => value.SequenceNumber).HasColumnName("sequence_number");
            entity.Property(value => value.IdempotencyKey).HasColumnName("idempotency_key");
            entity.Property(value => value.Status).HasColumnName("status");
            entity.Property(value => value.PreparedEvidenceId).HasColumnName("prepared_evidence_id");
            entity.Property(value => value.ResolutionEvidenceId).HasColumnName("resolution_evidence_id");
            entity.Property(value => value.PreparedAt).HasColumnName("prepared_at");
            entity.Property(value => value.ExpiresAt).HasColumnName("expires_at").ValueGeneratedOnAdd();
            entity.Property(value => value.ResolvedAt).HasColumnName("resolved_at");
            entity.HasOne<EmploymentRelationship>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.RelationshipId })
                .HasPrincipalKey(value => new { value.TenantId, value.RelationshipId });
            entity.HasOne<ChannelBinding>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.SourceBindingId })
                .HasPrincipalKey(value => new { value.TenantId, value.BindingId });
            entity.HasOne<ChannelBinding>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.TargetBindingId })
                .HasPrincipalKey(value => new { value.TenantId, value.BindingId });
        });

        modelBuilder.Entity<DeliveryAcknowledgement>(entity =>
        {
            entity.ToTable("delivery_acknowledgements", "business");
            entity.HasKey(value => value.AcknowledgementId);
            entity.HasIndex(value => new { value.TenantId, value.BindingId, value.MessageIdHash, value.AcknowledgementType }).IsUnique();
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.AcknowledgedAt });
            entity.HasIndex(value => new { value.TenantId, value.CheckpointId });
            entity.HasIndex(value => new { value.TenantId, value.BindingId, value.MessageIdHash });
            entity.Property(value => value.AcknowledgementId).HasColumnName("acknowledgement_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.CheckpointId).HasColumnName("checkpoint_id");
            entity.Property(value => value.BindingId).HasColumnName("binding_id");
            entity.Property(value => value.MessageIdHash).HasColumnName("message_id_hash").HasMaxLength(64).IsFixedLength();
            entity.Property(value => value.AcknowledgementType).HasColumnName("acknowledgement_type");
            entity.Property(value => value.AcknowledgedAt).HasColumnName("acknowledged_at");
            entity.Property(value => value.EvidenceId).HasColumnName("evidence_id");
            entity.Property(value => value.CreatedAt).HasColumnName("created_at");
            entity.HasOne<EmploymentRelationship>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.RelationshipId })
                .HasPrincipalKey(value => new { value.TenantId, value.RelationshipId });
            entity.HasOne<ContinuityCheckpoint>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.CheckpointId })
                .HasPrincipalKey(value => new { value.TenantId, value.CheckpointId })
                .IsRequired(false);
            entity.HasOne<ChannelBinding>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.BindingId })
                .HasPrincipalKey(value => new { value.TenantId, value.BindingId });
        });

        modelBuilder.Entity<ChannelMessageDeduplication>(entity =>
        {
            entity.ToTable("channel_message_deduplication", "business");
            entity.HasKey(value => value.DeduplicationId);
            entity.HasIndex(value => new { value.TenantId, value.BindingId, value.ProviderMessageIdHash }).IsUnique();
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.ReceivedAt });
            entity.HasIndex(value => value.ExpiresAt);
            entity.Property(value => value.DeduplicationId).HasColumnName("deduplication_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.BindingId).HasColumnName("binding_id");
            entity.Property(value => value.ProviderMessageIdHash).HasColumnName("provider_message_id_hash").HasMaxLength(64).IsFixedLength();
            entity.Property(value => value.MaterialMessageHash).HasColumnName("material_message_hash").HasMaxLength(64).IsFixedLength();
            entity.Property(value => value.ReceivedAt).HasColumnName("received_at");
            entity.Property(value => value.OutcomeReference).HasColumnName("outcome_reference");
            entity.Property(value => value.Status).HasColumnName("status");
            entity.Property(value => value.ExpiresAt).HasColumnName("expires_at").ValueGeneratedOnAdd();
            entity.HasOne<EmploymentRelationship>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.RelationshipId })
                .HasPrincipalKey(value => new { value.TenantId, value.RelationshipId });
            entity.HasOne<ChannelBinding>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.BindingId })
                .HasPrincipalKey(value => new { value.TenantId, value.BindingId });
        });

        modelBuilder.Entity<RelationshipEvidenceExport>(entity =>
        {
            entity.ToTable("relationship_evidence_exports", "business");
            entity.HasKey(value => value.ExportId);
            entity.HasIndex(value => new { value.TenantId, value.RelationshipId, value.IdempotencyKey }).IsUnique();
            entity.Property(value => value.ExportId).HasColumnName("export_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.RelationshipId).HasColumnName("relationship_id");
            entity.Property(value => value.ParticipantId).HasColumnName("participant_id");
            entity.Property(value => value.ParticipantRole).HasColumnName("participant_role");
            entity.Property(value => value.IdempotencyKey).HasColumnName("idempotency_key");
            entity.Property(value => value.MaterialRequestHash).HasColumnName("material_request_hash");
            entity.Property(value => value.DocumentJson).HasColumnName("document_json").HasColumnType("jsonb");
            entity.Property(value => value.DocumentSha256).HasColumnName("document_sha256");
            entity.Property(value => value.EvidenceId).HasColumnName("evidence_id");
            entity.Property(value => value.CreatedAt).HasColumnName("created_at");
            entity.Property(value => value.ExpiresAt).HasColumnName("expires_at");
            entity.HasOne<EmploymentRelationship>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.RelationshipId })
                .HasPrincipalKey(value => new { value.TenantId, value.RelationshipId });
        });
    }
}

public static class RelationshipStateCodec
{
    public static string ToDatabase(EmploymentRelationshipState value) => value switch
    {
        EmploymentRelationshipState.Discovered => "DISCOVERED",
        EmploymentRelationshipState.Interviewing => "INTERVIEWING",
        EmploymentRelationshipState.TrialActive => "TRIAL_ACTIVE",
        EmploymentRelationshipState.Configuring => "CONFIGURING",
        EmploymentRelationshipState.ContractPendingAcceptance => "CONTRACT_PENDING_ACCEPTANCE",
        EmploymentRelationshipState.ContractAcceptedPendingPayment => "CONTRACT_ACCEPTED_PENDING_PAYMENT",
        EmploymentRelationshipState.ActivationPending => "ACTIVATION_PENDING",
        EmploymentRelationshipState.Active => "ACTIVE",
        EmploymentRelationshipState.Paused => "PAUSED",
        EmploymentRelationshipState.StoppedEmergency => "STOPPED_EMERGENCY",
        EmploymentRelationshipState.Terminated => "TERMINATED",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, "Unknown relationship state"),
    };

    public static EmploymentRelationshipState FromDatabase(string value) => value switch
    {
        "DISCOVERED" => EmploymentRelationshipState.Discovered,
        "INTERVIEWING" => EmploymentRelationshipState.Interviewing,
        "TRIAL_ACTIVE" => EmploymentRelationshipState.TrialActive,
        "CONFIGURING" => EmploymentRelationshipState.Configuring,
        "CONTRACT_PENDING_ACCEPTANCE" => EmploymentRelationshipState.ContractPendingAcceptance,
        "CONTRACT_ACCEPTED_PENDING_PAYMENT" => EmploymentRelationshipState.ContractAcceptedPendingPayment,
        "ACTIVATION_PENDING" => EmploymentRelationshipState.ActivationPending,
        "ACTIVE" => EmploymentRelationshipState.Active,
        "PAUSED" => EmploymentRelationshipState.Paused,
        "STOPPED_EMERGENCY" => EmploymentRelationshipState.StoppedEmergency,
        "TERMINATED" => EmploymentRelationshipState.Terminated,
        _ => throw new InvalidOperationException($"Unknown relationship state '{value}'"),
    };
}

public static class RelationshipRoleCodec
{
    public static string ToDatabase(RelationshipParticipantRole value) => value switch
    {
        RelationshipParticipantRole.Evaluator => "EVALUATOR",
        RelationshipParticipantRole.Employer => "EMPLOYER",
        RelationshipParticipantRole.OutcomeOwner => "OUTCOME_OWNER",
        RelationshipParticipantRole.RelationshipManager => "RELATIONSHIP_MANAGER",
        RelationshipParticipantRole.ConstitutionalAuthority => "CONSTITUTIONAL_AUTHORITY",
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, "Unknown participant role"),
    };

    public static RelationshipParticipantRole FromDatabase(string value) => value switch
    {
        "EVALUATOR" => RelationshipParticipantRole.Evaluator,
        "EMPLOYER" => RelationshipParticipantRole.Employer,
        "OUTCOME_OWNER" => RelationshipParticipantRole.OutcomeOwner,
        "RELATIONSHIP_MANAGER" => RelationshipParticipantRole.RelationshipManager,
        "CONSTITUTIONAL_AUTHORITY" => RelationshipParticipantRole.ConstitutionalAuthority,
        _ => throw new InvalidOperationException($"Unknown participant role '{value}'"),
    };
}