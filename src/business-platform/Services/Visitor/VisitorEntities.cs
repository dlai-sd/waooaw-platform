// Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R007, WC135-R008
// Constitutional basis: C-009, C-023, C-026, C-048, C-059, C-063

using Microsoft.EntityFrameworkCore;

namespace Waooaw.BusinessPlatform.Services.Visitor;

public sealed class VisitorSession
{
    public Guid SessionId { get; init; }
    public Guid TenantId { get; init; }
    public string SubjectHash { get; init; } = string.Empty;
    public string Channel { get; init; } = string.Empty;
    public string State { get; set; } = VisitorStates.New;
    public string Outcome { get; set; } = VisitorOutcomes.None;
    public string ContentVersion { get; set; } = string.Empty;
    public DateTimeOffset? ConsentAt { get; set; }
    public string? ConsentNoticeVersion { get; set; }
    public Guid? ConsentEvidenceId { get; set; }
    public Guid? LeadId { get; set; }
    public int TurnCount { get; set; }
    public int? TurnsToFirstValue { get; set; }
    public int Nudges { get; set; }
    public DateTimeOffset CreatedAt { get; init; }
    public DateTimeOffset UpdatedAt { get; set; }
}

public sealed class VisitorTurn
{
    public Guid SessionId { get; init; }
    public long Sequence { get; init; }
    public Guid TenantId { get; init; }
    public Guid MessageId { get; init; }
    public Guid IdempotencyKey { get; init; }
    public string RequestHash { get; init; } = string.Empty;
    public string VisitorContentType { get; init; } = "TEXT";
    public string? VisitorTextProtected { get; init; }
    public string? VisitorChoiceId { get; init; }
    public string ReplyJson { get; init; } = "{}";
    public string StateAfter { get; init; } = VisitorStates.New;
    public string OutcomeAfter { get; init; } = VisitorOutcomes.None;
    public DateTimeOffset CreatedAt { get; init; }
}

public static class VisitorLeadStatus
{
    public const string Open = "OPEN";
    public const string Intent = "INTENT";
    public const string Converted = "CONVERTED";
}

public sealed class VisitorLead
{
    public Guid LeadId { get; init; }
    public Guid TenantId { get; init; }
    public string SubjectHash { get; init; } = string.Empty;
    public string? PhoneProtected { get; set; }
    public string? BusinessDomain { get; set; }
    public string? BusinessText { get; set; }
    public string? City { get; set; }
    public string? GoalCode { get; set; }
    public string? ContactNameProtected { get; set; }
    public string? ContactEmailProtected { get; set; }
    public string SourceChannel { get; init; } = string.Empty;
    public Guid ConsentReference { get; init; }
    public string Status { get; set; } = VisitorLeadStatus.Open;
    public Guid? AcquisitionIntentId { get; set; }
    public DateTimeOffset CreatedAt { get; init; }
    public DateTimeOffset UpdatedAt { get; set; }
}

public sealed class VisitorHandoffReference
{
    public string ReferenceHash { get; init; } = string.Empty;
    public Guid TenantId { get; init; }
    public Guid LeadId { get; init; }
    public DateTimeOffset CreatedAt { get; init; }
    public DateTimeOffset ExpiresAt { get; init; }
    public DateTimeOffset? TappedAt { get; set; }
    public DateTimeOffset? ConsumedAt { get; set; }
}

/// <summary>The structured reply behind a WhatsApp guest message, so the adapter can render buttons and links.</summary>
public sealed class VisitorRenderHint
{
    public Guid TenantId { get; init; }
    public Guid MessageId { get; init; }
    public string ReplyJson { get; init; } = "{}";
    public DateTimeOffset CreatedAt { get; init; }
}

public static class VisitorModelConfiguration
{
    public static void ConfigureVisitorConversation(this ModelBuilder modelBuilder)
    {
        var session = modelBuilder.Entity<VisitorSession>();
        session.ToTable("visitor_sessions", "business");
        session.HasKey(value => value.SessionId);
        session.HasIndex(value => new { value.TenantId, value.SubjectHash }).IsUnique();
        session.Property(value => value.SessionId).HasColumnName("session_id");
        session.Property(value => value.TenantId).HasColumnName("tenant_id");
        session.Property(value => value.SubjectHash).HasColumnName("subject_hash").HasMaxLength(64);
        session.Property(value => value.Channel).HasColumnName("channel").HasMaxLength(12);
        session.Property(value => value.State).HasColumnName("state").HasMaxLength(24);
        session.Property(value => value.Outcome).HasColumnName("outcome").HasMaxLength(16);
        session
            .Property(value => value.ContentVersion)
            .HasColumnName("content_version")
            .HasMaxLength(64);
        session.Property(value => value.ConsentAt).HasColumnName("consent_at");
        session
            .Property(value => value.ConsentNoticeVersion)
            .HasColumnName("consent_notice_version")
            .HasMaxLength(32);
        session.Property(value => value.ConsentEvidenceId).HasColumnName("consent_evidence_id");
        session.Property(value => value.LeadId).HasColumnName("lead_id");
        session.Property(value => value.TurnCount).HasColumnName("turn_count");
        session.Property(value => value.TurnsToFirstValue).HasColumnName("turns_to_first_value");
        session.Property(value => value.Nudges).HasColumnName("nudges");
        session.Property(value => value.CreatedAt).HasColumnName("created_at");
        session.Property(value => value.UpdatedAt).HasColumnName("updated_at");

        var turn = modelBuilder.Entity<VisitorTurn>();
        turn.ToTable("visitor_turns", "business");
        turn.HasKey(value => new { value.SessionId, value.Sequence });
        turn.HasIndex(value => new { value.SessionId, value.IdempotencyKey }).IsUnique();
        turn.Property(value => value.SessionId).HasColumnName("session_id");
        turn.Property(value => value.Sequence).HasColumnName("sequence");
        turn.Property(value => value.TenantId).HasColumnName("tenant_id");
        turn.Property(value => value.MessageId).HasColumnName("message_id");
        turn.Property(value => value.IdempotencyKey).HasColumnName("idempotency_key");
        turn.Property(value => value.RequestHash).HasColumnName("request_hash").HasMaxLength(64);
        turn.Property(value => value.VisitorContentType)
            .HasColumnName("visitor_content_type")
            .HasMaxLength(8);
        turn.Property(value => value.VisitorTextProtected).HasColumnName("visitor_text_protected");
        turn.Property(value => value.VisitorChoiceId)
            .HasColumnName("visitor_choice_id")
            .HasMaxLength(64);
        turn.Property(value => value.ReplyJson).HasColumnName("reply_json").HasColumnType("jsonb");
        turn.Property(value => value.StateAfter).HasColumnName("state_after").HasMaxLength(24);
        turn.Property(value => value.OutcomeAfter).HasColumnName("outcome_after").HasMaxLength(16);
        turn.Property(value => value.CreatedAt).HasColumnName("created_at");

        var lead = modelBuilder.Entity<VisitorLead>();
        lead.ToTable("visitor_leads", "business");
        lead.HasKey(value => value.LeadId);
        lead.Property(value => value.LeadId).HasColumnName("lead_id");
        lead.Property(value => value.TenantId).HasColumnName("tenant_id");
        lead.Property(value => value.SubjectHash).HasColumnName("subject_hash").HasMaxLength(64);
        lead.Property(value => value.PhoneProtected).HasColumnName("phone_protected");
        lead.Property(value => value.BusinessDomain)
            .HasColumnName("business_domain")
            .HasMaxLength(64);
        lead.Property(value => value.BusinessText).HasColumnName("business_text").HasMaxLength(120);
        lead.Property(value => value.City).HasColumnName("city").HasMaxLength(80);
        lead.Property(value => value.GoalCode).HasColumnName("goal_code").HasMaxLength(48);
        lead.Property(value => value.ContactNameProtected).HasColumnName("contact_name_protected");
        lead.Property(value => value.ContactEmailProtected)
            .HasColumnName("contact_email_protected");
        lead.Property(value => value.SourceChannel)
            .HasColumnName("source_channel")
            .HasMaxLength(12);
        lead.Property(value => value.ConsentReference).HasColumnName("consent_reference");
        lead.Property(value => value.Status).HasColumnName("status").HasMaxLength(12);
        lead.Property(value => value.AcquisitionIntentId).HasColumnName("acquisition_intent_id");
        lead.Property(value => value.CreatedAt).HasColumnName("created_at");
        lead.Property(value => value.UpdatedAt).HasColumnName("updated_at");

        var reference = modelBuilder.Entity<VisitorHandoffReference>();
        reference.ToTable("visitor_handoff_references", "business");
        reference.HasKey(value => value.ReferenceHash);
        reference
            .Property(value => value.ReferenceHash)
            .HasColumnName("reference_hash")
            .HasMaxLength(64);
        reference.Property(value => value.TenantId).HasColumnName("tenant_id");
        reference.Property(value => value.LeadId).HasColumnName("lead_id");
        reference.Property(value => value.CreatedAt).HasColumnName("created_at");
        reference.Property(value => value.ExpiresAt).HasColumnName("expires_at");
        reference.Property(value => value.TappedAt).HasColumnName("tapped_at");
        reference.Property(value => value.ConsumedAt).HasColumnName("consumed_at");

        var hint = modelBuilder.Entity<VisitorRenderHint>();
        hint.ToTable("visitor_render_hints", "business");
        hint.HasKey(value => new { value.TenantId, value.MessageId });
        hint.Property(value => value.TenantId).HasColumnName("tenant_id");
        hint.Property(value => value.MessageId).HasColumnName("message_id");
        hint.Property(value => value.ReplyJson).HasColumnName("reply_json").HasColumnType("jsonb");
        hint.Property(value => value.CreatedAt).HasColumnName("created_at");
    }
}
