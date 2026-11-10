// Implements: work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md §8
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using PostgresErrorCodes = Npgsql.PostgresErrorCodes;
using PostgresException = Npgsql.PostgresException;

namespace Waooaw.BusinessPlatform.Services;

internal static class WhatsAppRelationshipRoutePublication
{
    internal static async Task<WhatsAppRelationshipRoute> PublishAsync(
        EmploymentRelationshipDbContext db,
        Guid serviceTenantId,
        ChannelBinding binding,
        Guid identityLinkId,
        PortalPhoneAttachProof proof,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        if (
            serviceTenantId == Guid.Empty
            || binding.TenantId == Guid.Empty
            || binding.BindingId == Guid.Empty
            || identityLinkId == Guid.Empty
            || binding.Channel != "WHATSAPP"
            || binding.Status != "ACTIVE"
            || binding.BoundEvidenceId is not { } evidenceId
            || evidenceId == Guid.Empty
            || binding.BoundAt is null
            || binding.BoundAt > now
            || binding.ExternalSubjectHash.Length != 64
            || binding.ExternalSubjectHash.Any(value =>
                value is not (>= '0' and <= '9') and not (>= 'a' and <= 'f')
            )
            || proof.Actor is not { } actor
            || !Guid.TryParse(actor.Subject, out var actorId)
            || actorId != binding.ParticipantId
            || actorId != proof.ParticipantId
            || string.IsNullOrWhiteSpace(actor.Issuer)
            || actor.Issuer.Length > 2048
            || proof.Membership is not { } membership
            || membership.TenantId != binding.TenantId
            || membership.AccountId == Guid.Empty
            || membership.MembershipId == Guid.Empty
            || !membership.Roles.SequenceEqual(["OWNER"])
        )
            throw new ConstitutionalActionDeniedException(
                "WhatsApp relationship route authority is invalid."
            );
        if (db.Database.IsRelational() && db.Database.CurrentTransaction is null)
            throw new WhatsAppChannelBindingUnavailableException(
                "WhatsApp route publication requires the attachment transaction."
            );

        var candidate = new WhatsAppRelationshipRoute
        {
            ServiceTenantId = serviceTenantId,
            SenderHash = binding.ExternalSubjectHash,
            TenantId = binding.TenantId,
            BindingId = binding.BindingId,
            IdentityLinkId = identityLinkId,
            ActorIssuer = actor.Issuer,
            ActorId = actorId,
            AccountId = membership.AccountId,
            MembershipId = membership.MembershipId,
            BoundEvidenceId = evidenceId,
            PublishedAt = now,
        };
        var existing = await db.Set<WhatsAppRelationshipRoute>()
            .AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.ServiceTenantId == serviceTenantId
                    && value.SenderHash == candidate.SenderHash,
                ct
            );
        if (existing is not null)
        {
            if (!Matches(existing, candidate))
            {
                if (
                    !db.Database.IsNpgsql()
                    || existing.TenantId != candidate.TenantId
                    || existing.BindingId == candidate.BindingId
                    || existing.ActorId != candidate.ActorId
                    || existing.ActorIssuer != candidate.ActorIssuer
                    || existing.AccountId != candidate.AccountId
                    || existing.MembershipId != candidate.MembershipId
                )
                    throw new ConstitutionalActionDeniedException(
                        "WhatsApp relationship route is unavailable."
                    );
                bool renewed;
                try
                {
                    renewed = await db
                        .Database.SqlQuery<bool>(
                            $"""
                            SELECT business.renew_whatsapp_relationship_route(
                                {serviceTenantId}, {candidate.SenderHash}, {existing.BindingId}, {candidate.BindingId},
                                {candidate.IdentityLinkId}, {candidate.ActorIssuer}, {candidate.ActorId},
                                {candidate.AccountId}, {candidate.MembershipId}, {candidate.BoundEvidenceId},
                                {candidate.PublishedAt}) AS "Value"
                            """
                        )
                        .SingleAsync(ct);
                }
                catch (PostgresException failure)
                    when (failure.SqlState == PostgresErrorCodes.InsufficientPrivilege)
                {
                    throw new ConstitutionalActionDeniedException(
                        "WhatsApp relationship route renewal is unavailable."
                    );
                }
                if (!renewed)
                    throw new ConstitutionalActionDeniedException(
                        "WhatsApp relationship route is unavailable."
                    );
                return candidate;
            }
            return existing;
        }
        db.Set<WhatsAppRelationshipRoute>().Add(candidate);
        try
        {
            await db.SaveChangesAsync(ct);
        }
        catch (DbUpdateException failure)
            when (failure.InnerException
                    is PostgresException
                    {
                        SqlState: PostgresErrorCodes.UniqueViolation,
                        ConstraintName: "whatsapp_relationship_routes_pk"
                            or "whatsapp_relationship_routes_binding_unique",
                    }
            )
        {
            throw new ConstitutionalActionDeniedException(
                "WhatsApp relationship route is unavailable."
            );
        }
        return candidate;
    }

    private static bool Matches(
        WhatsAppRelationshipRoute existing,
        WhatsAppRelationshipRoute candidate
    ) =>
        existing.TenantId == candidate.TenantId
        && existing.BindingId == candidate.BindingId
        && existing.IdentityLinkId == candidate.IdentityLinkId
        && existing.ActorIssuer == candidate.ActorIssuer
        && existing.ActorId == candidate.ActorId
        && existing.AccountId == candidate.AccountId
        && existing.MembershipId == candidate.MembershipId
        && existing.BoundEvidenceId == candidate.BoundEvidenceId;
}
