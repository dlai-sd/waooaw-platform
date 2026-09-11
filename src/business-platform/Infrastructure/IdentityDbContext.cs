// Implements: architecture/reference/components/identity-boundary.md §8 Canonical Data Contracts;
//             architecture/reference/components/environment-readiness-and-data-continuity.md §6
// constitutional_basis: C-005, C-007, C-026, C-059

using Microsoft.EntityFrameworkCore;

namespace Waooaw.BusinessPlatform.Infrastructure;

public enum IdentityRegistrationState
{
    Started,
    FederatedIdentityAccepted,
    CredentialIdentityAccepted,
    WhatsAppIdentityAccepted,
    EmailVerificationRequired,
    DuplicateResolutionRequired,
    ProfileCompletionRequired,
    ReadyToComplete,
    Completed,
    Expired,
    Cancelled,
}

public enum IdentityAuthenticationPath
{
    Google,
    Meta,
    Apple,
    Credential,
    WhatsApp,
}

public enum IdentityVerificationPurpose
{
    Email,
    Mobile,
}

public enum IdentityVerificationState
{
    Pending,
    Verified,
    Expired,
    Consumed,
}

public enum IdentityAccountLinkState
{
    PendingPortalApproval,
    PendingWhatsAppConfirmation,
    Linked,
    DuplicateResolutionRequired,
    Expired,
    Cancelled,
}

public sealed class IdentityRegistrationRecord
{
    public Guid RegistrationId { get; init; } = Guid.NewGuid();
    public string? ActorIssuer { get; init; }
    public string ActorSubject { get; init; } = string.Empty;
    public IdentityRegistrationState State { get; set; } = IdentityRegistrationState.Started;
    public IdentityAuthenticationPath AuthenticationPath { get; set; }
    public string? ProviderLabel { get; set; }
    public bool EmailVerified { get; set; }
    public bool MobileVerified { get; set; }
    // Provider issuer + subject binding (issuer distinguishes Google from other OIDC providers)
    public string? ProviderIssuer { get; set; }
    // Match keys are keyed HMAC values — never returned to clients or exposed in logs
    public string? EmailHmacKey { get; set; }
    public string? EmailHmacVersion { get; set; }
    public string? EmailHmacDomain { get; set; }
    public string? MobileHmacKey { get; set; }
    public string? MobileHmacVersion { get; set; }
    public string? MobileHmacDomain { get; set; }
    public string? MaskedEmail { get; set; }
    public string? MaskedMobile { get; set; }
    public string? DisplayName { get; set; }
    public string? BusinessName { get; set; }
    public string? BusinessDomain { get; set; }
    public string? LanguagePreference { get; set; }
    public Guid? AccountId { get; set; }
    public Guid? ActorBindingId { get; set; }
    public Guid? OriginRegistrationId { get; set; }
    public DateTimeOffset? CompletedAt { get; set; }
    public string? CompletionOutcome { get; set; }
    public string? CompletionProfileSnapshot { get; set; }
    public int? CompletionStatusCode { get; set; }
    public string? CompletionResponseBody { get; set; }
    public DateTimeOffset ExpiresAt { get; init; } = DateTimeOffset.UtcNow.AddHours(2);
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class IdentityVerificationChallengeRecord
{
    public Guid ChallengeId { get; init; } = Guid.NewGuid();
    public Guid? RegistrationId { get; init; }
    public string ActorSubject { get; init; } = string.Empty;
    public IdentityVerificationPurpose Purpose { get; init; }
    public IdentityVerificationState State { get; set; } = IdentityVerificationState.Pending;
    // OTP code stored as HMAC — raw code never persisted
    public string CodeHmac { get; init; } = string.Empty;
    public string CodeHmacVersion { get; init; } = "v1";
    public string MaskedDestination { get; init; } = string.Empty;
    public DateTimeOffset? VerifiedAt { get; set; }
    public DateTimeOffset ExpiresAt { get; init; } = DateTimeOffset.UtcNow.AddMinutes(15);
    public DateTimeOffset ResendAfter { get; init; } = DateTimeOffset.UtcNow.AddMinutes(1);
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class IdentityAccountLinkRecord
{
    public Guid LinkId { get; init; } = Guid.NewGuid();
    public string ActorSubject { get; init; } = string.Empty;
    public Guid TenantId { get; init; }
    public IdentityAccountLinkState State { get; set; } = IdentityAccountLinkState.PendingPortalApproval;
    public string MaskedMobile { get; init; } = string.Empty;
    public Guid VerifiedMobileProofId { get; init; }
    public DateTimeOffset ExpiresAt { get; init; } = DateTimeOffset.UtcNow.AddMinutes(15);
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class IdentityIdempotencyEntry
{
    public Guid EntryId { get; init; } = Guid.NewGuid();
    public string? ActorIssuer { get; init; }
    public Guid? RegistrationId { get; init; }
    public string ActorSubject { get; init; } = string.Empty;
    public string IdempotencyKey { get; init; } = string.Empty;
    public string OperationFamily { get; init; } = string.Empty;
    public string CanonicalHash { get; init; } = string.Empty;
    public int StatusCode { get; init; }
    public string? ResponseBody { get; init; }
    public DateTimeOffset ExpiresAt { get; init; } = DateTimeOffset.UtcNow.AddHours(25);
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class CustomerPortalPreferenceRecord
{
    public Guid PreferenceId { get; init; } = Guid.NewGuid();
    public string ActorSubject { get; init; } = string.Empty;
    public Guid TenantId { get; init; }
    public string? DisplayName { get; set; }
    public string? OrganizationDisplayName { get; set; }
    public string Locale { get; set; } = "en";
    public string Theme { get; set; } = "SYSTEM";
    public string TimestampVisibility { get; set; } = "RELATIVE";
    public string ApprovalRequestChannels { get; set; } = "[\"IN_APP\"]";
    public string MaturityReportChannels { get; set; } = "[\"IN_APP\"]";
    public string MonthlyNarrativeChannels { get; set; } = "[\"IN_APP\"]";
    public string SelfGovernanceAlertChannels { get; set; } = "[\"IN_APP\"]";
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class IdentityAccountRecord
{
    public Guid AccountId { get; init; }
    public Guid InitialTenantId { get; init; }
    public Guid OriginRegistrationId { get; init; }
    public string Status { get; init; } = "ACTIVE";
    public DateTimeOffset CreatedAt { get; init; }
}

public sealed class IdentityLoginMethodRecord
{
    public Guid LoginMethodId { get; init; }
    public string ProviderIssuer { get; init; } = string.Empty;
    public string BrokerAlias { get; init; } = string.Empty;
    public string ProviderSubject { get; init; } = string.Empty;
    public Guid AccountId { get; init; }
    public string Status { get; init; } = "ACTIVE";
    public DateTimeOffset CreatedAt { get; init; }
}

public sealed class IdentityActorBindingRecord
{
    public Guid ActorBindingId { get; init; }
    public string ActorIssuer { get; init; } = string.Empty;
    public string ActorSubject { get; init; } = string.Empty;
    public Guid LoginMethodId { get; init; }
    public Guid AccountId { get; init; }
    public string Status { get; init; } = "ACTIVE";
    public string ProofSource { get; init; } = "KEYCLOAK_FEDERATED_IDENTITY";
    public DateTimeOffset VerifiedAt { get; init; }
    public DateTimeOffset AuthTime { get; init; }
    public string TrustConfigDigest { get; init; } = string.Empty;
    public Guid CorrelationId { get; init; }
    public DateTimeOffset CreatedAt { get; init; }
}

public sealed class IdentityMembershipRecord
{
    public Guid MembershipId { get; init; }
    public Guid AccountId { get; init; }
    public Guid TenantId { get; init; }
    public string[] Roles { get; init; } = ["OWNER"];
    public string Status { get; init; } = "ACTIVE";
    public DateTimeOffset CreatedAt { get; init; }
}

public sealed class IdentityRegistrationEventRecord
{
    public Guid EventId { get; init; } = Guid.NewGuid();
    public Guid RegistrationId { get; init; }
    public string? ActorIssuer { get; init; }
    public string ActorSubject { get; init; } = string.Empty;
    public string EventType { get; init; } = string.Empty;
    public string? FromState { get; init; }
    public string ToState { get; init; } = string.Empty;
    public Guid CorrelationId { get; init; }
    public DateTimeOffset OccurredAt { get; init; }
}

public sealed class IdentityOrganisationRecord
{
    public Guid Id { get; init; }
    public Guid TenantId { get; init; }
    public string Name { get; init; } = string.Empty;
    public string? BusinessDomain { get; init; }
    public bool IdentityManaged { get; init; }
    public string IdentityStatus { get; init; } = "ACTIVE";
    public DateTimeOffset CreatedAt { get; init; }
}

public sealed class IdentityDbContext : DbContext
{
    public DbSet<IdentityRegistrationRecord> Registrations => Set<IdentityRegistrationRecord>();
    public DbSet<IdentityVerificationChallengeRecord> VerificationChallenges => Set<IdentityVerificationChallengeRecord>();
    public DbSet<IdentityAccountLinkRecord> AccountLinks => Set<IdentityAccountLinkRecord>();
    public DbSet<IdentityIdempotencyEntry> IdempotencyLedger => Set<IdentityIdempotencyEntry>();
    public DbSet<CustomerPortalPreferenceRecord> CustomerPortalPreferences => Set<CustomerPortalPreferenceRecord>();
    public DbSet<IdentityAccountRecord> Accounts => Set<IdentityAccountRecord>();
    public DbSet<IdentityLoginMethodRecord> LoginMethods => Set<IdentityLoginMethodRecord>();
    public DbSet<IdentityActorBindingRecord> ActorBindings => Set<IdentityActorBindingRecord>();
    public DbSet<IdentityMembershipRecord> Memberships => Set<IdentityMembershipRecord>();
    public DbSet<IdentityRegistrationEventRecord> RegistrationEvents => Set<IdentityRegistrationEventRecord>();
    public DbSet<IdentityOrganisationRecord> Organisations => Set<IdentityOrganisationRecord>();

    public IdentityDbContext(DbContextOptions<IdentityDbContext> options) : base(options) { }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.HasDefaultSchema("identity");

        modelBuilder.Entity<IdentityRegistrationRecord>(e =>
        {
            e.ToTable("registrations");
            e.HasKey(r => r.RegistrationId);
            e.Property(r => r.RegistrationId).HasColumnName("registration_id");
            e.Property(r => r.ActorIssuer).HasColumnName("actor_issuer").HasMaxLength(256).UseCollation("C");
            e.Property(r => r.ActorSubject).HasColumnName("actor_subject").HasMaxLength(256).UseCollation("C");
            e.Property(r => r.State).HasColumnName("state").HasConversion<string>();
            e.Property(r => r.AuthenticationPath).HasColumnName("authentication_path").HasConversion<string>();
            e.Property(r => r.ProviderLabel).HasColumnName("provider_label").HasMaxLength(40);
            e.Property(r => r.ProviderIssuer).HasColumnName("provider_issuer").HasMaxLength(256);
            e.Property(r => r.EmailVerified).HasColumnName("email_verified");
            e.Property(r => r.MobileVerified).HasColumnName("mobile_verified");
            e.Property(r => r.EmailHmacKey).HasColumnName("email_hmac_key").HasMaxLength(128);
            e.Property(r => r.EmailHmacVersion).HasColumnName("email_hmac_version").HasMaxLength(32);
            e.Property(r => r.EmailHmacDomain).HasColumnName("email_hmac_domain").HasMaxLength(16);
            e.Property(r => r.MobileHmacKey).HasColumnName("mobile_hmac_key").HasMaxLength(128);
            e.Property(r => r.MobileHmacVersion).HasColumnName("mobile_hmac_version").HasMaxLength(32);
            e.Property(r => r.MobileHmacDomain).HasColumnName("mobile_hmac_domain").HasMaxLength(16);
            e.Property(r => r.MaskedEmail).HasColumnName("masked_email").HasMaxLength(254);
            e.Property(r => r.MaskedMobile).HasColumnName("masked_mobile").HasMaxLength(32);
            e.Property(r => r.DisplayName).HasColumnName("display_name").HasMaxLength(120);
            e.Property(r => r.BusinessName).HasColumnName("business_name").HasMaxLength(160);
            e.Property(r => r.BusinessDomain).HasColumnName("business_domain").HasMaxLength(100);
            e.Property(r => r.LanguagePreference).HasColumnName("language_preference").HasMaxLength(5);
            e.Property(r => r.AccountId).HasColumnName("account_id");
            e.Property(r => r.ActorBindingId).HasColumnName("actor_binding_id");
            e.Property(r => r.OriginRegistrationId).HasColumnName("origin_registration_id");
            e.Property(r => r.CompletedAt).HasColumnName("completed_at");
            e.Property(r => r.CompletionOutcome).HasColumnName("completion_outcome").HasMaxLength(24);
            e.Property(r => r.CompletionProfileSnapshot).HasColumnName("completion_profile_snapshot").HasColumnType("jsonb");
            e.Property(r => r.CompletionStatusCode).HasColumnName("completion_status_code");
            e.Property(r => r.CompletionResponseBody).HasColumnName("completion_response_body");
            e.Property(r => r.ExpiresAt).HasColumnName("expires_at");
            e.Property(r => r.CreatedAt).HasColumnName("created_at");
            e.Property(r => r.UpdatedAt).HasColumnName("updated_at");
            e.HasIndex(r => r.ActorSubject);
            e.HasIndex(r => new { r.ActorIssuer, r.ActorSubject });
        });

        modelBuilder.Entity<IdentityVerificationChallengeRecord>(e =>
        {
            e.ToTable("verification_challenges");
            e.HasKey(c => c.ChallengeId);
            e.Property(c => c.ChallengeId).HasColumnName("challenge_id");
            e.Property(c => c.RegistrationId).HasColumnName("registration_id");
            e.Property(c => c.ActorSubject).HasColumnName("actor_subject").HasMaxLength(256);
            e.Property(c => c.Purpose).HasColumnName("purpose").HasConversion<string>();
            e.Property(c => c.State).HasColumnName("state").HasConversion<string>();
            e.Property(c => c.CodeHmac).HasColumnName("code_hmac").HasMaxLength(128);
            e.Property(c => c.CodeHmacVersion).HasColumnName("code_hmac_version").HasMaxLength(32);
            e.Property(c => c.MaskedDestination).HasColumnName("masked_destination").HasMaxLength(254);
            e.Property(c => c.VerifiedAt).HasColumnName("verified_at");
            e.Property(c => c.ExpiresAt).HasColumnName("expires_at");
            e.Property(c => c.ResendAfter).HasColumnName("resend_after");
            e.Property(c => c.CreatedAt).HasColumnName("created_at");
        });

        modelBuilder.Entity<IdentityAccountLinkRecord>(e =>
        {
            e.ToTable("account_links");
            e.HasKey(l => l.LinkId);
            e.Property(l => l.LinkId).HasColumnName("link_id");
            e.Property(l => l.ActorSubject).HasColumnName("actor_subject").HasMaxLength(256);
            e.Property(l => l.TenantId).HasColumnName("tenant_id");
            e.Property(l => l.State).HasColumnName("state").HasConversion<string>();
            e.Property(l => l.MaskedMobile).HasColumnName("masked_mobile").HasMaxLength(32);
            e.Property(l => l.VerifiedMobileProofId).HasColumnName("verified_mobile_proof_id");
            e.Property(l => l.ExpiresAt).HasColumnName("expires_at");
            e.Property(l => l.CreatedAt).HasColumnName("created_at");
            e.Property(l => l.UpdatedAt).HasColumnName("updated_at");
            e.HasIndex(l => new { l.ActorSubject, l.TenantId });
        });

        modelBuilder.Entity<IdentityIdempotencyEntry>(e =>
        {
            e.ToTable("idempotency_ledger");
            e.HasKey(i => i.EntryId);
            e.Property(i => i.EntryId).HasColumnName("entry_id");
            e.Property(i => i.ActorIssuer).HasColumnName("actor_issuer").HasMaxLength(256).UseCollation("C");
            e.Property(i => i.RegistrationId).HasColumnName("registration_id");
            e.Property(i => i.ActorSubject).HasColumnName("actor_subject").HasMaxLength(256).UseCollation("C");
            e.Property(i => i.IdempotencyKey).HasColumnName("idempotency_key").HasMaxLength(36);
            e.Property(i => i.OperationFamily).HasColumnName("operation_family").HasMaxLength(64);
            e.Property(i => i.CanonicalHash).HasColumnName("canonical_hash").HasMaxLength(64);
            e.Property(i => i.StatusCode).HasColumnName("status_code");
            e.Property(i => i.ResponseBody).HasColumnName("response_body");
            e.Property(i => i.ExpiresAt).HasColumnName("expires_at");
            e.Property(i => i.CreatedAt).HasColumnName("created_at");
            e.HasIndex(i => new { i.ActorIssuer, i.ActorSubject, i.IdempotencyKey, i.OperationFamily }).IsUnique();
        });

        modelBuilder.Entity<CustomerPortalPreferenceRecord>(e =>
        {
            e.ToTable("customer_portal_preferences");
            e.HasKey(p => p.PreferenceId);
            e.Property(p => p.PreferenceId).HasColumnName("preference_id");
            e.Property(p => p.ActorSubject).HasColumnName("actor_subject").HasMaxLength(256);
            e.Property(p => p.TenantId).HasColumnName("tenant_id");
            e.Property(p => p.DisplayName).HasColumnName("display_name").HasMaxLength(200);
            e.Property(p => p.OrganizationDisplayName).HasColumnName("organization_display_name").HasMaxLength(200);
            e.Property(p => p.Locale).HasColumnName("locale").HasMaxLength(16);
            e.Property(p => p.Theme).HasColumnName("theme").HasMaxLength(16);
            e.Property(p => p.TimestampVisibility).HasColumnName("timestamp_visibility").HasMaxLength(16);
            e.Property(p => p.ApprovalRequestChannels).HasColumnName("approval_request_channels").HasColumnType("jsonb");
            e.Property(p => p.MaturityReportChannels).HasColumnName("maturity_report_channels").HasColumnType("jsonb");
            e.Property(p => p.MonthlyNarrativeChannels).HasColumnName("monthly_narrative_channels").HasColumnType("jsonb");
            e.Property(p => p.SelfGovernanceAlertChannels).HasColumnName("self_governance_alert_channels").HasColumnType("jsonb");
            e.Property(p => p.UpdatedAt).HasColumnName("updated_at");
            e.HasIndex(p => new { p.ActorSubject, p.TenantId }).IsUnique();
        });

        modelBuilder.Entity<IdentityAccountRecord>(entity =>
        {
            entity.ToTable("accounts");
            entity.HasKey(record => record.AccountId);
            entity.Property(record => record.AccountId).HasColumnName("account_id");
            entity.Property(record => record.InitialTenantId).HasColumnName("initial_tenant_id");
            entity.Property(record => record.OriginRegistrationId).HasColumnName("origin_registration_id");
            entity.Property(record => record.Status).HasColumnName("status").HasMaxLength(16);
            entity.Property(record => record.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
            entity.HasIndex(record => record.InitialTenantId).IsUnique();
            entity.HasIndex(record => record.OriginRegistrationId).IsUnique();
        });
        modelBuilder.Entity<IdentityLoginMethodRecord>(entity =>
        {
            entity.ToTable("login_methods");
            entity.HasKey(record => record.LoginMethodId);
            entity.Property(record => record.LoginMethodId).HasColumnName("login_method_id");
            entity.Property(record => record.ProviderIssuer).HasColumnName("provider_issuer").HasMaxLength(256).UseCollation("C");
            entity.Property(record => record.BrokerAlias).HasColumnName("broker_alias").HasMaxLength(40).UseCollation("C");
            entity.Property(record => record.ProviderSubject).HasColumnName("provider_subject").HasMaxLength(256).UseCollation("C");
            entity.Property(record => record.AccountId).HasColumnName("account_id");
            entity.Property(record => record.Status).HasColumnName("status").HasMaxLength(16);
            entity.Property(record => record.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
            entity.HasIndex(record => new { record.ProviderIssuer, record.BrokerAlias, record.ProviderSubject }).IsUnique();
        });
        modelBuilder.Entity<IdentityActorBindingRecord>(entity =>
        {
            entity.ToTable("actor_bindings");
            entity.HasKey(record => record.ActorBindingId);
            entity.Property(record => record.ActorBindingId).HasColumnName("actor_binding_id");
            entity.Property(record => record.ActorIssuer).HasColumnName("actor_issuer").HasMaxLength(256).UseCollation("C");
            entity.Property(record => record.ActorSubject).HasColumnName("actor_subject").HasMaxLength(256).UseCollation("C");
            entity.Property(record => record.LoginMethodId).HasColumnName("login_method_id");
            entity.Property(record => record.AccountId).HasColumnName("account_id");
            entity.Property(record => record.Status).HasColumnName("status").HasMaxLength(16);
            entity.Property(record => record.ProofSource).HasColumnName("proof_source").HasMaxLength(32);
            entity.Property(record => record.VerifiedAt).HasColumnName("verified_at");
            entity.Property(record => record.AuthTime).HasColumnName("auth_time");
            entity.Property(record => record.TrustConfigDigest).HasColumnName("trust_config_digest").HasMaxLength(64);
            entity.Property(record => record.CorrelationId).HasColumnName("correlation_id");
            entity.Property(record => record.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
            entity.HasIndex(record => new { record.ActorIssuer, record.ActorSubject }).IsUnique();
            entity.HasIndex(record => record.LoginMethodId).IsUnique().HasFilter("status = 'ACTIVE'");
        });
        modelBuilder.Entity<IdentityMembershipRecord>(entity =>
        {
            entity.ToTable("memberships");
            entity.HasKey(record => record.MembershipId);
            entity.Property(record => record.MembershipId).HasColumnName("membership_id");
            entity.Property(record => record.AccountId).HasColumnName("account_id");
            entity.Property(record => record.TenantId).HasColumnName("tenant_id");
            entity.Property(record => record.Roles).HasColumnName("roles").HasColumnType("text[]");
            entity.Property(record => record.Status).HasColumnName("status").HasMaxLength(16);
            entity.Property(record => record.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
            entity.HasIndex(record => record.AccountId).IsUnique();
        });
        modelBuilder.Entity<IdentityRegistrationEventRecord>(entity =>
        {
            entity.ToTable("registration_events");
            entity.HasKey(record => record.EventId);
            entity.Property(record => record.EventId).HasColumnName("event_id");
            entity.Property(record => record.RegistrationId).HasColumnName("registration_id");
            entity.Property(record => record.ActorIssuer).HasColumnName("actor_issuer").HasMaxLength(256).UseCollation("C");
            entity.Property(record => record.ActorSubject).HasColumnName("actor_subject").HasMaxLength(256).UseCollation("C");
            entity.Property(record => record.EventType).HasColumnName("event_type").HasMaxLength(64);
            entity.Property(record => record.FromState).HasColumnName("from_state").HasMaxLength(64);
            entity.Property(record => record.ToState).HasColumnName("to_state").HasMaxLength(64);
            entity.Property(record => record.CorrelationId).HasColumnName("correlation_id");
            entity.Property(record => record.OccurredAt).HasColumnName("occurred_at").HasDefaultValueSql("now()");
        });
        modelBuilder.Entity<IdentityOrganisationRecord>(entity =>
        {
            entity.ToTable("organisations", "business");
            entity.HasKey(record => record.Id);
            entity.Property(record => record.Id).HasColumnName("id");
            entity.Property(record => record.TenantId).HasColumnName("tenant_id");
            entity.Property(record => record.Name).HasColumnName("name").HasMaxLength(200);
            entity.Property(record => record.BusinessDomain).HasColumnName("business_domain").HasMaxLength(50);
            entity.Property(record => record.IdentityManaged).HasColumnName("identity_managed");
            entity.Property(record => record.IdentityStatus).HasColumnName("identity_status").HasMaxLength(24);
            entity.Property(record => record.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
            entity.HasIndex(record => record.TenantId).IsUnique();
        });
    }
}
