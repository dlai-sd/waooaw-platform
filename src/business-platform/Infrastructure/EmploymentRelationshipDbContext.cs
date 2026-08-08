// Implements: architecture/reference/product/ae01-relationship-data-contract.md § Migration 19
// constitutional_basis: C-005, C-007, C-023, C-026, C-059

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

public sealed class EmploymentRelationshipDbContext : DbContext
{
    public EmploymentRelationshipDbContext(DbContextOptions<EmploymentRelationshipDbContext> options)
        : base(options) { }

    public DbSet<EmploymentRelationship> EmploymentRelationships => Set<EmploymentRelationship>();
    public DbSet<RelationshipParticipant> RelationshipParticipants => Set<RelationshipParticipant>();
    public DbSet<RelationshipStateHistory> RelationshipStateHistory => Set<RelationshipStateHistory>();
    public DbSet<RelationshipIdempotency> RelationshipIdempotency => Set<RelationshipIdempotency>();

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