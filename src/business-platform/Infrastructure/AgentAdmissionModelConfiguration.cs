// Implements: WC-079 AA-03, AA-06, AA-08
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

using Microsoft.EntityFrameworkCore;

namespace Waooaw.BusinessPlatform.Infrastructure;

public static class AgentAdmissionModelConfiguration
{
    public static void Configure(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<AgentAdmission>(entity =>
        {
            entity.ToTable("agent_admissions", "business");
            entity.HasKey(value => value.AdmissionId);
            entity.HasAlternateKey(value => new { value.TenantId, value.AdmissionId });
            entity.HasIndex(value => new { value.TenantId, value.ProfessionalTypeId, value.ProfessionalVersion }).IsUnique();
            entity.Property(value => value.AdmissionId).HasColumnName("admission_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.ProfessionalTypeId).HasColumnName("professional_type_id");
            entity.Property(value => value.ProfessionalVersion).HasColumnName("professional_version");
            entity.Property(value => value.OwnerSubjectId).HasColumnName("owner_subject_id");
            entity.Property(value => value.SubmitterSubjectId).HasColumnName("submitter_subject_id");
            entity.Property(value => value.State).HasColumnName("state").HasConversion(
                state => AgentAdmissionStateCodec.ToDatabase(state),
                state => AgentAdmissionStateCodec.FromDatabase(state));
            entity.Property(value => value.StateVersion).HasColumnName("state_version").IsConcurrencyToken();
            entity.Property(value => value.CurrentRevision).HasColumnName("current_revision");
            entity.Property(value => value.AdmissionContentDigest).HasColumnName("admission_content_digest");
            entity.Property(value => value.EvidenceSetDigest).HasColumnName("evidence_set_digest");
            entity.Property(value => value.ArtifactDigest).HasColumnName("artifact_digest");
            entity.Property(value => value.PolicyVersion).HasColumnName("policy_version");
            entity.Property(value => value.SuccessorVersion).HasColumnName("successor_version");
            entity.Property(value => value.CreatedAt).HasColumnName("created_at");
            entity.Property(value => value.UpdatedAt).HasColumnName("updated_at");
        });

        modelBuilder.Entity<AgentAdmissionRevision>(entity =>
        {
            entity.ToTable("agent_admission_revisions", "business");
            entity.HasKey(value => value.RevisionId);
            entity.HasAlternateKey(value => new { value.TenantId, value.AdmissionId, value.RevisionId });
            entity.HasIndex(value => new { value.TenantId, value.AdmissionId, value.Revision }).IsUnique();
            entity.HasIndex(value => new { value.TenantId, value.AdmissionId, value.AdmissionContentDigest }).IsUnique();
            entity.Property(value => value.RevisionId).HasColumnName("revision_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.AdmissionId).HasColumnName("admission_id");
            entity.Property(value => value.Revision).HasColumnName("revision");
            entity.Property(value => value.ContractSchemaVersion).HasColumnName("contract_schema_version");
            entity.Property(value => value.AdmissionContentDigest).HasColumnName("admission_content_digest");
            entity.Property(value => value.AdmissionContentJson).HasColumnName("admission_content").HasColumnType("jsonb");
            entity.Property(value => value.ActorSubjectId).HasColumnName("actor_subject_id");
            entity.Property(value => value.PredecessorRevisionId).HasColumnName("predecessor_revision_id");
            entity.Property(value => value.CreatedAt).HasColumnName("created_at");
            Parent<AgentAdmissionRevision>(entity, value => new { value.TenantId, value.AdmissionId });
            entity.HasOne<AgentAdmissionRevision>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.AdmissionId, value.PredecessorRevisionId })
                .HasPrincipalKey(value => new { value.TenantId, value.AdmissionId, value.RevisionId });
        });

        modelBuilder.Entity<AgentAdmissionValidation>(entity =>
        {
            entity.ToTable("agent_admission_validations", "business");
            entity.HasKey(value => value.ValidationId);
            entity.HasAlternateKey(value => new { value.TenantId, value.ValidationId });
            entity.HasIndex(value => new { value.TenantId, value.AdmissionId, value.Revision, value.ValidatorProfile, value.IdempotencyKey }).IsUnique();
            entity.HasIndex(value => new { value.TenantId, value.IdempotencyKey }).IsUnique();
            entity.Property(value => value.ValidationId).HasColumnName("validation_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.AdmissionId).HasColumnName("admission_id");
            entity.Property(value => value.Revision).HasColumnName("revision");
            entity.Property(value => value.ValidatorProfile).HasColumnName("validator_profile");
            entity.Property(value => value.IdempotencyKey).HasColumnName("idempotency_key");
            entity.Property(value => value.RequestHash).HasColumnName("request_hash");
            entity.Property(value => value.Result).HasColumnName("result");
            entity.Property(value => value.FindingCount).HasColumnName("finding_count");
            entity.Property(value => value.ValidatedAt).HasColumnName("validated_at");
            Parent<AgentAdmissionValidation>(entity, value => new { value.TenantId, value.AdmissionId });
        });

        modelBuilder.Entity<AgentAdmissionFinding>(entity =>
        {
            entity.ToTable("agent_admission_findings", "business");
            entity.HasKey(value => value.FindingId);
            entity.HasIndex(value => new { value.TenantId, value.ValidationId, value.RuleId, value.ContractPath }).IsUnique();
            entity.Property(value => value.FindingId).HasColumnName("finding_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.ValidationId).HasColumnName("validation_id");
            entity.Property(value => value.RuleId).HasColumnName("rule_id");
            entity.Property(value => value.Severity).HasColumnName("severity");
            entity.Property(value => value.ContractPath).HasColumnName("contract_path");
            entity.Property(value => value.ConstitutionalBasis).HasColumnName("constitutional_basis");
            entity.Property(value => value.Expected).HasColumnName("expected");
            entity.Property(value => value.ObservedCategory).HasColumnName("observed_category");
            entity.Property(value => value.Remediation).HasColumnName("remediation");
            entity.Property(value => value.Blocking).HasColumnName("blocking");
            entity.Property(value => value.CreatedAt).HasColumnName("created_at");
            entity.HasOne<AgentAdmissionValidation>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.ValidationId })
                .HasPrincipalKey(value => new { value.TenantId, value.ValidationId });
        });

        modelBuilder.Entity<AgentAdmissionAssertion>(entity =>
        {
            entity.ToTable("agent_admission_assertions", "business");
            entity.HasKey(value => value.AssertionId);
            entity.HasIndex(value => new { value.TenantId, value.AdmissionId, value.AssertionType, value.Environment, value.SubjectDigest, value.PolicyVersion, value.ObservedAt }).IsUnique();
            entity.Property(value => value.AssertionId).HasColumnName("assertion_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.AdmissionId).HasColumnName("admission_id");
            entity.Property(value => value.AssertionType).HasColumnName("assertion_type");
            entity.Property(value => value.SubjectDigest).HasColumnName("subject_digest");
            entity.Property(value => value.Environment).HasColumnName("environment");
            entity.Property(value => value.Status).HasColumnName("status");
            entity.Property(value => value.SourceAuthority).HasColumnName("source_authority");
            entity.Property(value => value.ObservedAt).HasColumnName("observed_at");
            entity.Property(value => value.ValidUntil).HasColumnName("valid_until");
            entity.Property(value => value.PolicyVersion).HasColumnName("policy_version");
            entity.Property(value => value.EvidenceRef).HasColumnName("evidence_ref");
            Parent<AgentAdmissionAssertion>(entity, value => new { value.TenantId, value.AdmissionId });
        });

        modelBuilder.Entity<AgentAdmissionTransition>(entity =>
        {
            entity.ToTable("agent_admission_transitions", "business");
            entity.HasKey(value => value.TransitionId);
            entity.HasAlternateKey(value => new { value.TenantId, value.TransitionId });
            entity.HasIndex(value => new { value.TenantId, value.AdmissionId, value.FromState, value.ToState, value.CorrelationId }).IsUnique();
            entity.Property(value => value.TransitionId).HasColumnName("transition_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.AdmissionId).HasColumnName("admission_id");
            entity.Property(value => value.FromState).HasColumnName("from_state");
            entity.Property(value => value.ToState).HasColumnName("to_state");
            entity.Property(value => value.ActorSubjectId).HasColumnName("actor_subject_id");
            entity.Property(value => value.ActorAuthority).HasColumnName("actor_authority");
            entity.Property(value => value.CorrelationId).HasColumnName("correlation_id");
            entity.Property(value => value.AdmissionContentDigest).HasColumnName("admission_content_digest");
            entity.Property(value => value.EvidenceSetDigest).HasColumnName("evidence_set_digest");
            entity.Property(value => value.ArtifactDigest).HasColumnName("artifact_digest");
            entity.Property(value => value.PolicyVersion).HasColumnName("policy_version");
            entity.Property(value => value.CeEvidenceRef).HasColumnName("ce_evidence_ref");
            entity.Property(value => value.ReasonCategory).HasColumnName("reason_category");
            entity.Property(value => value.OccurredAt).HasColumnName("occurred_at");
            Parent<AgentAdmissionTransition>(entity, value => new { value.TenantId, value.AdmissionId });
        });

        modelBuilder.Entity<AgentAdmissionIdempotency>(entity =>
        {
            entity.ToTable("agent_admission_idempotency", "business");
            entity.HasKey(value => value.IdempotencyId);
            entity.HasIndex(value => new { value.TenantId, value.AdmissionId, value.Operation, value.IdempotencyKey }).IsUnique();
            entity.HasIndex(value => new { value.TenantId, value.Operation, value.IdempotencyKey }).IsUnique();
            entity.Property(value => value.IdempotencyId).HasColumnName("idempotency_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.AdmissionId).HasColumnName("admission_id");
            entity.Property(value => value.Operation).HasColumnName("operation");
            entity.Property(value => value.IdempotencyKey).HasColumnName("idempotency_key");
            entity.Property(value => value.ActorSubjectId).HasColumnName("actor_subject_id");
            entity.Property(value => value.SubjectDigest).HasColumnName("subject_digest");
            entity.Property(value => value.MaterialRequestHash).HasColumnName("material_request_hash");
            entity.Property(value => value.OutcomeReference).HasColumnName("outcome_reference");
            entity.Property(value => value.ResponseJson).HasColumnName("response_json").HasColumnType("jsonb");
            entity.Property(value => value.Status).HasColumnName("status");
            entity.Property(value => value.CreatedAt).HasColumnName("created_at");
            entity.Property(value => value.CompletedAt).HasColumnName("completed_at");
            Parent<AgentAdmissionIdempotency>(entity, value => new { value.TenantId, value.AdmissionId });
        });

        modelBuilder.Entity<AgentAdmissionOutbox>(entity =>
        {
            entity.ToTable("agent_admission_outbox", "business");
            entity.HasKey(value => value.OutboxId);
            entity.HasIndex(value => new { value.TenantId, value.TransitionId, value.ScopeHash }).IsUnique();
            entity.Property(value => value.OutboxId).HasColumnName("outbox_id");
            entity.Property(value => value.TenantId).HasColumnName("tenant_id");
            entity.Property(value => value.AdmissionId).HasColumnName("admission_id");
            entity.Property(value => value.TransitionId).HasColumnName("transition_id");
            entity.Property(value => value.EventType).HasColumnName("event_type");
            entity.Property(value => value.ScopeHash).HasColumnName("scope_hash");
            entity.Property(value => value.PayloadJson).HasColumnName("payload").HasColumnType("jsonb");
            entity.Property(value => value.OccurredAt).HasColumnName("occurred_at");
            entity.Property(value => value.PublishedAt).HasColumnName("published_at");
            entity.Property(value => value.PublishAttempts).HasColumnName("publish_attempts");
            Parent<AgentAdmissionOutbox>(entity, value => new { value.TenantId, value.AdmissionId });
            entity.HasOne<AgentAdmissionTransition>().WithMany()
                .HasForeignKey(value => new { value.TenantId, value.TransitionId })
                .HasPrincipalKey(value => new { value.TenantId, value.TransitionId });
        });
    }

    private static void Parent<TEntity>(
        Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<TEntity> entity,
        System.Linq.Expressions.Expression<Func<TEntity, object?>> foreignKey)
        where TEntity : class => entity.HasOne<AgentAdmission>().WithMany()
            .HasForeignKey(foreignKey)
            .HasPrincipalKey(value => new { value.TenantId, value.AdmissionId });
}