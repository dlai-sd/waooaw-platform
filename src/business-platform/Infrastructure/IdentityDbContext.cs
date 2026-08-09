// Implements: architecture/reference/components/identity-boundary.md §8 Canonical Data Contracts
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
    public string? MobileHmacKey { get; set; }
    public string? MaskedEmail { get; set; }
    public string? MaskedMobile { get; set; }
    public string? DisplayName { get; set; }
    public string? BusinessName { get; set; }
    public string? BusinessDomain { get; set; }
    public string? LanguagePreference { get; set; }
    public Guid? AccountId { get; set; }
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
    public string ActorSubject { get; init; } = string.Empty;
    public string IdempotencyKey { get; init; } = string.Empty;
    public string OperationFamily { get; init; } = string.Empty;
    public string CanonicalHash { get; init; } = string.Empty;
    public int StatusCode { get; init; }
    public string? ResponseBody { get; init; }
    public DateTimeOffset ExpiresAt { get; init; } = DateTimeOffset.UtcNow.AddHours(25);
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
}

public sealed class IdentityDbContext : DbContext
{
    public DbSet<IdentityRegistrationRecord> Registrations => Set<IdentityRegistrationRecord>();
    public DbSet<IdentityVerificationChallengeRecord> VerificationChallenges => Set<IdentityVerificationChallengeRecord>();
    public DbSet<IdentityAccountLinkRecord> AccountLinks => Set<IdentityAccountLinkRecord>();
    public DbSet<IdentityIdempotencyEntry> IdempotencyLedger => Set<IdentityIdempotencyEntry>();

    public IdentityDbContext(DbContextOptions<IdentityDbContext> options) : base(options) { }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.HasDefaultSchema("identity");

        modelBuilder.Entity<IdentityRegistrationRecord>(e =>
        {
            e.ToTable("registrations");
            e.HasKey(r => r.RegistrationId);
            e.Property(r => r.RegistrationId).HasColumnName("registration_id");
            e.Property(r => r.ActorSubject).HasColumnName("actor_subject").HasMaxLength(256);
            e.Property(r => r.State).HasColumnName("state").HasConversion<string>();
            e.Property(r => r.AuthenticationPath).HasColumnName("authentication_path").HasConversion<string>();
            e.Property(r => r.ProviderLabel).HasColumnName("provider_label").HasMaxLength(40);
            e.Property(r => r.ProviderIssuer).HasColumnName("provider_issuer").HasMaxLength(256);
            e.Property(r => r.EmailVerified).HasColumnName("email_verified");
            e.Property(r => r.MobileVerified).HasColumnName("mobile_verified");
            e.Property(r => r.EmailHmacKey).HasColumnName("email_hmac_key").HasMaxLength(128);
            e.Property(r => r.MobileHmacKey).HasColumnName("mobile_hmac_key").HasMaxLength(128);
            e.Property(r => r.MaskedEmail).HasColumnName("masked_email").HasMaxLength(254);
            e.Property(r => r.MaskedMobile).HasColumnName("masked_mobile").HasMaxLength(32);
            e.Property(r => r.DisplayName).HasColumnName("display_name").HasMaxLength(120);
            e.Property(r => r.BusinessName).HasColumnName("business_name").HasMaxLength(160);
            e.Property(r => r.BusinessDomain).HasColumnName("business_domain").HasMaxLength(100);
            e.Property(r => r.LanguagePreference).HasColumnName("language_preference").HasMaxLength(5);
            e.Property(r => r.AccountId).HasColumnName("account_id");
            e.Property(r => r.ExpiresAt).HasColumnName("expires_at");
            e.Property(r => r.CreatedAt).HasColumnName("created_at");
            e.Property(r => r.UpdatedAt).HasColumnName("updated_at");
            e.HasIndex(r => r.ActorSubject);
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
            e.Property(i => i.ActorSubject).HasColumnName("actor_subject").HasMaxLength(256);
            e.Property(i => i.IdempotencyKey).HasColumnName("idempotency_key").HasMaxLength(36);
            e.Property(i => i.OperationFamily).HasColumnName("operation_family").HasMaxLength(64);
            e.Property(i => i.CanonicalHash).HasColumnName("canonical_hash").HasMaxLength(64);
            e.Property(i => i.StatusCode).HasColumnName("status_code");
            e.Property(i => i.ResponseBody).HasColumnName("response_body");
            e.Property(i => i.ExpiresAt).HasColumnName("expires_at");
            e.Property(i => i.CreatedAt).HasColumnName("created_at");
            e.HasIndex(i => new { i.ActorSubject, i.IdempotencyKey, i.OperationFamily }).IsUnique();
        });
    }
}
