// Implements: WC-134 R005; identity-boundary.md Section 6.3.
// constitutional_basis: C-023, C-026, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.WebUtilities;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public interface IWhatsAppAccountLinkConfirmation
{
    Task<bool> ConfirmAsync(
        string token,
        string phoneNumber,
        VerifiedPhoneIdentityProof proof,
        CancellationToken ct
    );
}

public static class WhatsAppAccountLinkInstruction
{
    public const string ConfirmedNotice =
        "Your WhatsApp number is linked to your WAOOAW account. "
        + "This does not sign you in, create an employment relationship, or move this guest chat. "
        + "Sign in at https://cp.demo.waooaw.com to choose a relationship and approve its channel access.";
    public const string DeniedNotice =
        "This account-link request could not be confirmed. "
        + "Sign in to WAOOAW and start a fresh WhatsApp link request. No account access was granted.";

    public static bool IsInstruction(string text)
    {
        var trimmed = text.TrimStart();
        return trimmed.Equals("LINK", StringComparison.OrdinalIgnoreCase)
            || (
                trimmed.Length > 4
                && trimmed.StartsWith("LINK", StringComparison.OrdinalIgnoreCase)
                && char.IsWhiteSpace(trimmed[4])
            );
    }
}

public sealed partial class IdentityService
{
    private const string AccountLinkTokenPurpose = "WAOOAW-WC134-ACCOUNT-LINK-V1";

    private sealed record AccountLinkToken(
        Guid LinkId,
        string ActorSubject,
        string? ActorIssuer,
        string? IdentitySubject,
        CustomerWorkspaceMembership? Membership,
        Guid TenantId
    )
    {
        [JsonIgnore]
        public VerifiedCustomerActor? Actor =>
            ActorIssuer is not null && IdentitySubject is not null
                ? new VerifiedCustomerActor(ActorIssuer, IdentitySubject)
                : null;
    }

    public string? CreateAccountLinkConfirmationToken(
        IdentityAccountLinkRecord link,
        VerifiedCustomerActor? actor,
        CustomerWorkspaceMembership? membership
    )
    {
        if (
            link.State != IdentityAccountLinkState.PendingWhatsAppConfirmation
            || link.ApprovalEvidenceId is null
            || link.ExpiresAt <= DateTimeOffset.UtcNow
        )
            return null;
        var plaintext = JsonSerializer.SerializeToUtf8Bytes(
            new AccountLinkToken(
                link.LinkId,
                link.ActorSubject,
                actor?.Issuer,
                actor?.Subject,
                membership,
                link.TenantId
            )
        );
        var key = AccountLinkTokenKey(_activeHmacVersion);
        var nonce = RandomNumberGenerator.GetBytes(12);
        var tag = new byte[16];
        var ciphertext = new byte[plaintext.Length];
        try
        {
            using var aes = new AesGcm(key, tag.Length);
            aes.Encrypt(
                nonce,
                plaintext,
                ciphertext,
                tag,
                Encoding.ASCII.GetBytes(AccountLinkTokenPurpose)
            );
            return string.Join(
                '.',
                "v1",
                _activeHmacVersion,
                WebEncoders.Base64UrlEncode(nonce),
                WebEncoders.Base64UrlEncode(tag),
                WebEncoders.Base64UrlEncode(ciphertext)
            );
        }
        finally
        {
            CryptographicOperations.ZeroMemory(key);
            CryptographicOperations.ZeroMemory(plaintext);
        }
    }

    public async Task<bool> ConfirmAsync(
        string token,
        string phoneNumber,
        VerifiedPhoneIdentityProof proof,
        CancellationToken ct
    )
    {
        var context = ReadAccountLinkToken(token);
        var now = _clock.GetUtcNow();
        if (
            !Regex.IsMatch(phoneNumber, "\\A\\+[1-9][0-9]{7,14}\\z", RegexOptions.CultureInvariant)
            || proof.UnsupportedContent
            || proof.AuthenticationAssurance != "AAL1_CHANNEL"
            || string.IsNullOrWhiteSpace(proof.MessageId)
            || !IsLowerHexDigest(proof.PhoneSubjectHash)
            || !proof.Text.Trim().StartsWith("LINK ", StringComparison.OrdinalIgnoreCase)
            || proof.Text.Trim()[5..].Trim() != token
            || proof.VerifiedAt < proof.SentAt
            || proof.ExpiresAt <= proof.VerifiedAt
            || proof.ExpiresAt > proof.VerifiedAt.AddMinutes(5)
        )
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
        RequireCurrentWhatsAppConfirmationProof(proof, now);

        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        await using var transaction = await BeginAccountLinkContextAsync(
            db,
            context.Actor,
            context.Membership,
            context.TenantId,
            ct
        );
        var link = await FindAccountLinkForUpdateAsync(db, context.LinkId, ct);
        now = _clock.GetUtcNow();
        RequireCurrentWhatsAppConfirmationProof(proof, now);
        if (
            link is null
            || link.TenantId != context.TenantId
            || link.ActorSubject != context.ActorSubject
        )
            throw new IdentityResourceNotFoundException("Link not found or not accessible.");
        var mobileProof = await RequireAccountLinkProofAsync(
            db,
            link.VerifiedMobileProofId,
            context.ActorSubject,
            context.Actor,
            context.Membership,
            ct
        );
        var candidates = ComputeMatchCandidates("mobile", phoneNumber);
        if (
            !candidates.TryGetValue(mobileProof.DestinationHmacVersion!, out var candidate)
            || !CryptographicOperations.FixedTimeEquals(
                Encoding.ASCII.GetBytes(candidate),
                Encoding.ASCII.GetBytes(mobileProof.DestinationHmacKey!)
            )
        )
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");

        var messageDigest = Convert.ToHexStringLower(
            SHA256.HashData(
                Encoding.UTF8.GetBytes(
                    $"{proof.Environment}\n{proof.PhoneSubjectHash}\n{proof.MessageId}"
                )
            )
        );
        now = _clock.GetUtcNow();
        RequireCurrentWhatsAppConfirmationProof(proof, now);
        if (
            link.State == IdentityAccountLinkState.Linked
            && link.ConfirmationMessageDigest == messageDigest
            && link.ConfirmationEvidenceId.HasValue
        )
        {
            if (transaction is not null)
                await transaction.CommitAsync(ct);
            return true;
        }
        if (
            link.State != IdentityAccountLinkState.PendingWhatsAppConfirmation
            || link.ApprovalEvidenceId is null
            || link.ApprovalEvidenceId == Guid.Empty
            || link.ExpiresAt <= now
            || proof.SentAt < link.UpdatedAt
        )
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");

        var evidenceId = await RequireConstitutionalEvidenceAsync(
            context.TenantId,
            link.LinkId,
            "IDENTITY_ACCOUNT_LINK_CONFIRM",
            new { link.LinkId, messageDigest },
            ct
        );
        if (evidenceId == Guid.Empty)
            throw new IdentityConstitutionalUnavailableException(
                "Account-link evidence is unavailable."
            );
        await RequireAccountLinkProofAsync(
            db,
            link.VerifiedMobileProofId,
            context.ActorSubject,
            context.Actor,
            context.Membership,
            ct
        );
        now = _clock.GetUtcNow();
        RequireCurrentWhatsAppConfirmationProof(proof, now);
        if (link.ExpiresAt <= now)
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
        link.State = IdentityAccountLinkState.Linked;
        link.ConfirmationEvidenceId = evidenceId;
        link.ConfirmationMessageDigest = messageDigest;
        link.ConfirmedPhoneSubjectHash = proof.PhoneSubjectHash;
        link.ConfirmedAt = now;
        link.UpdatedAt = now;
        await db.SaveChangesAsync(ct);
        if (transaction is not null)
        {
            now = _clock.GetUtcNow();
            RequireCurrentWhatsAppConfirmationProof(proof, now);
            if (link.ExpiresAt <= now)
                throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            await transaction.CommitAsync(ct);
        }
        return false;
    }

    private static void RequireCurrentWhatsAppConfirmationProof(
        VerifiedPhoneIdentityProof proof,
        DateTimeOffset now
    )
    {
        if (
            proof.SentAt > now.AddSeconds(30)
            || proof.SentAt < now.AddMinutes(-5)
            || proof.VerifiedAt > now.AddSeconds(30)
            || proof.ExpiresAt <= now
        )
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
    }

    public async Task<string> GetConfirmedPhoneSubjectHashAsync(
        Guid linkId,
        string actorSubject,
        Guid tenantId,
        CancellationToken ct,
        VerifiedCustomerActor actor,
        CustomerWorkspaceMembership membership
    )
    {
        var link = await GetAccountLinkAsync(linkId, actorSubject, tenantId, ct, actor, membership);
        if (
            link.State != IdentityAccountLinkState.Linked
            || link.ConfirmationEvidenceId is null
            || link.ConfirmationEvidenceId == Guid.Empty
            || link.ConfirmedAt is null
            || !IsLowerHexDigest(link.ConfirmedPhoneSubjectHash)
        )
            throw new IdentityResourceNotFoundException("Linked WhatsApp identity not accessible.");
        return link.ConfirmedPhoneSubjectHash!;
    }

    internal async Task RequireRelationshipChannelLinkAsync(
        EmploymentRelationshipDbContext relationshipDb,
        Guid linkId,
        string phoneSubjectHash,
        VerifiedCustomerActor actor,
        CustomerWorkspaceMembership membership,
        CancellationToken ct
    )
    {
        if (
            linkId == Guid.Empty
            || !IsLowerHexDigest(phoneSubjectHash)
            || membership.AccountId == Guid.Empty
            || membership.MembershipId == Guid.Empty
            || membership.TenantId == Guid.Empty
            || !membership.Roles.SequenceEqual(["OWNER"])
        )
            throw new IdentityResourceNotFoundException("Linked WhatsApp identity not accessible.");

        await using var db = relationshipDb.Database.IsNpgsql()
            ? new IdentityDbContext(
                new DbContextOptionsBuilder<IdentityDbContext>()
                    .UseNpgsql(relationshipDb.Database.GetDbConnection())
                    .Options
            )
            : await _dbFactory.CreateDbContextAsync(ct);
        if (relationshipDb.Database.IsRelational())
        {
            if (
                !relationshipDb.Database.IsNpgsql()
                || relationshipDb.Database.CurrentTransaction is not { } transaction
                || !Guid.TryParse(actor.Subject, out var actorId)
            )
                throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            await db.Database.UseTransactionAsync(transaction.GetDbTransaction(), ct);
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                SELECT pg_catalog.set_config('app.identity_issuer', {actor.Issuer}, true),
                       pg_catalog.set_config('app.identity_subject', {actor.Subject}, true),
                       pg_catalog.set_config('app.current_membership_id', {membership.MembershipId.ToString(
                    "D"
                )}, true),
                       pg_catalog.set_config('app.tenant_id', {membership.TenantId.ToString(
                    "D"
                )}, true),
                       pg_catalog.set_config('app.current_tenant_id', {membership.TenantId.ToString(
                    "D"
                )}, true)
                """,
                ct
            );
            var current = await db
                .Database.SqlQuery<ChannelLinkMembership>(
                    $"""
                    SELECT account_id AS "AccountId", membership_id AS "MembershipId", roles AS "Roles"
                    FROM identity.lock_conversation_runtime_membership(
                        {actor.Issuer}, {actorId}, {membership.TenantId}, {membership.MembershipId})
                    """
                )
                .ToListAsync(ct);
            if (
                current.Count != 1
                || current[0].AccountId != membership.AccountId
                || current[0].MembershipId != membership.MembershipId
                || !current[0].Roles.SequenceEqual(["OWNER"])
            )
                throw new IdentityResourceNotFoundException("Active account membership not found.");
        }
        var registration = await GetPortalRegistrationAsync(
            db,
            actor.Issuer,
            actor.Subject,
            membership,
            ct
        );
        if (db.Database.IsRelational())
        {
            await db
                .Registrations.FromSqlInterpolated(
                    $"SELECT * FROM identity.registrations WHERE registration_id = {registration.RegistrationId} FOR UPDATE"
                )
                .ToListAsync(ct);
            await db.Entry(registration).ReloadAsync(ct);
        }
        if (
            registration.State != IdentityRegistrationState.Completed
            || registration.AccountId != membership.AccountId
        )
            throw new IdentityResourceNotFoundException("Active account registration not found.");
        var link = await FindAccountLinkForUpdateAsync(db, linkId, ct);
        if (
            link is null
            || link.TenantId != membership.TenantId
            || !AccountLinkMatchesActor(link, actor.Subject, actor)
            || link.State != IdentityAccountLinkState.Linked
            || link.ConfirmationEvidenceId is null
            || link.ConfirmationEvidenceId == Guid.Empty
            || link.ConfirmedAt is null
            || link.ConfirmedAt > _clock.GetUtcNow()
            || link.ConfirmedPhoneSubjectHash != phoneSubjectHash
        )
            throw new IdentityResourceNotFoundException("Linked WhatsApp identity not accessible.");
        if (db.Database.IsRelational())
            await db
                .VerificationChallenges.FromSqlInterpolated(
                    $"SELECT * FROM identity.verification_challenges WHERE challenge_id = {link.VerifiedMobileProofId} FOR UPDATE"
                )
                .ToListAsync(ct);
        await RequireAccountLinkProofAsync(
            db,
            link.VerifiedMobileProofId,
            actor.Subject,
            actor,
            membership,
            ct
        );
    }

    private sealed class ChannelLinkMembership
    {
        public Guid AccountId { get; init; }
        public Guid MembershipId { get; init; }
        public string[] Roles { get; init; } = [];
    }

    private static bool IsLowerHexDigest(string? value) =>
        value is { Length: 64 }
        && value.All(character => character is (>= '0' and <= '9') or (>= 'a' and <= 'f'));

    private AccountLinkToken ReadAccountLinkToken(string token)
    {
        if (token.Length > 3072)
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
        var parts = token.Split('.');
        if (parts.Length != 5 || parts[0] != "v1" || !_hmacKeys.ContainsKey(parts[1]))
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
        byte[]? plaintext = null;
        var key = AccountLinkTokenKey(parts[1]);
        try
        {
            var nonce = WebEncoders.Base64UrlDecode(parts[2]);
            var tag = WebEncoders.Base64UrlDecode(parts[3]);
            var ciphertext = WebEncoders.Base64UrlDecode(parts[4]);
            if (nonce.Length != 12 || tag.Length != 16 || ciphertext.Length == 0)
                throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            plaintext = new byte[ciphertext.Length];
            using var aes = new AesGcm(key, tag.Length);
            aes.Decrypt(
                nonce,
                ciphertext,
                tag,
                plaintext,
                Encoding.ASCII.GetBytes(AccountLinkTokenPurpose)
            );
            return JsonSerializer.Deserialize<AccountLinkToken>(plaintext)
                ?? throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
        }
        catch (Exception exception)
            when (exception is FormatException or CryptographicException or JsonException)
        {
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
        }
        finally
        {
            CryptographicOperations.ZeroMemory(key);
            if (plaintext is not null)
                CryptographicOperations.ZeroMemory(plaintext);
        }
    }

    private byte[] AccountLinkTokenKey(string version) =>
        HMACSHA256.HashData(_hmacKeys[version], Encoding.ASCII.GetBytes(AccountLinkTokenPurpose));
}
