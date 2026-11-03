// Implements: work-contracts/WC-133-whatsapp-first-registration-and-web-registration-repair.md R001-R004
// Constitutional basis: C-023, C-026, C-039, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed class PhoneOnboardingIdentity
{
    public Guid TenantId { get; init; }
    public string BindingDigest { get; init; } = string.Empty;
    public Guid ParticipantId { get; init; } = Guid.NewGuid();
    public Guid? EvidenceId { get; set; }
    public DateTimeOffset FirstObservedAt { get; init; }
    public DateTimeOffset? AdmittedAt { get; set; }
    public DateTimeOffset LastInboundAt { get; set; }
    public DateTimeOffset? StoppedAt { get; set; }
}

public sealed class PhoneOnboardingService(
    IDbContextFactory<ConversationStoreDbContext> factory,
    IWhatsAppRegistrationEvidenceGateway evidence,
    IWhatsAppCapabilityGate capability,
    PortalInteractionService interactions,
    WhatsAppOutboxService outbox,
    TimeProvider clock
)
{
    public async Task<WhatsAppJourneyReceipt> ReceiveAsync(
        VerifiedPhoneIdentityProof proof,
        CancellationToken ct
    )
    {
        var authority = capability.RequireActive(clock.GetUtcNow());
        if (!authority.AllowProvisionalOnboarding)
            throw new WhatsAppWebhookException(404, "WHATSAPP_IDENTITY_NOT_BOUND");
        capability.RequireRecipient(authority.TenantId, proof.PhoneSubjectHash, clock.GetUtcNow());
        await using var db = await factory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        var lockKey = Convert.ToHexStringLower(
            SHA256.HashData(
                Encoding.UTF8.GetBytes($"{authority.TenantId:D}:{proof.PhoneSubjectHash}")
            )
        );
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_advisory_xact_lock(hashtextextended({lockKey}, 0))",
            ct
        );
        var identity = await db.Set<PhoneOnboardingIdentity>()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == authority.TenantId
                    && value.BindingDigest == proof.PhoneSubjectHash,
                ct
            );
        if (identity is null)
        {
            identity = new PhoneOnboardingIdentity
            {
                TenantId = authority.TenantId,
                BindingDigest = proof.PhoneSubjectHash,
                FirstObservedAt = proof.VerifiedAt,
                LastInboundAt = proof.SentAt,
            };
            db.Add(identity);
        }
        var stop = proof.Text.Trim().Equals("STOP", StringComparison.OrdinalIgnoreCase);
        if (stop)
            identity.StoppedAt ??= clock.GetUtcNow();
        // A pending record preserves evidence inputs across uncertain CE responses; it grants no admission.
        await db.SaveChangesAsync(ct);
        await transaction.CommitAsync(ct);
        if (identity.StoppedAt is not null)
            return new(proof.MessageId, "STOPPED", "STOP", string.Empty, false, string.Empty);

        await using var admission = await db.Database.BeginTransactionAsync(ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_advisory_xact_lock(hashtextextended({lockKey}, 0))",
            ct
        );
        await db.Entry(identity).ReloadAsync(ct);
        if (identity.StoppedAt is not null)
        {
            await admission.CommitAsync(ct);
            return new(proof.MessageId, "STOPPED", "STOP", string.Empty, false, string.Empty);
        }
        if (identity.EvidenceId is null)
        {
            var evidenceId = await evidence.RecordProvisionalAsync(
                authority.TenantId,
                $"onboarding:{lockKey}",
                proof.PhoneSubjectHash,
                identity.FirstObservedAt,
                ct
            );
            if (evidenceId == Guid.Empty)
                throw new InvalidOperationException(
                    "Provisional admission requires a valid evidence identifier."
                );
            identity.EvidenceId = evidenceId;
            identity.AdmittedAt = clock.GetUtcNow();
        }
        if (capability.RequireActive(clock.GetUtcNow()) != authority)
            throw new WhatsAppCapabilityUnavailableException("ADMISSION_AUTHORITY_CHANGED");
        if (proof.SentAt > identity.LastInboundAt)
            identity.LastInboundAt = proof.SentAt;
        await db.SaveChangesAsync(ct);
        await admission.CommitAsync(ct);
        var messageKey = new Guid(
            SHA256
                .HashData(
                    Encoding.UTF8.GetBytes(
                        $"{proof.Environment}:{proof.AppBindingDigest}:{proof.MessageId}"
                    )
                )
                .AsSpan(0, 16)
        );
        var submitted = await interactions.SendPhoneOnboardingAsync(
            identity.TenantId,
            identity.ParticipantId,
            messageKey,
            new(
                "1.0",
                messageKey,
                [new("1.0", "TEXT", proof.Text, "en-IN")],
                "en-IN",
                "MARKETPLACE"
            ),
            ct
        );
        var reply = submitted.Value.GuideMessage;
        await outbox.QueueOnboardingAsync(identity, reply, proof.VerifiedAt, ct);
        return new(
            proof.MessageId,
            "ACCEPTED",
            "ONBOARDING",
            reply.Content.Single().Text,
            submitted.Replayed,
            string.Empty
        );
    }
}
