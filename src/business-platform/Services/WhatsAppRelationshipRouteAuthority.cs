// Implements: work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md §8
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

internal sealed record WhatsAppCurrentRelationshipRoute(
    Guid ServiceTenantId,
    string Environment,
    string SenderHash,
    Guid TenantId,
    Guid BindingId,
    Guid RelationshipId,
    Guid ParticipantId,
    string ParticipantRole,
    Guid ConversationId,
    int RelationshipVersion
);

internal static class WhatsAppRelationshipRouteAuthority
{
    internal static async Task<WhatsAppRelationshipRoute?> FindDeliveryAsync(
        EmploymentRelationshipDbContext db,
        Guid serviceTenantId,
        string senderHash,
        string environment,
        Guid outboxId,
        CancellationToken ct
    )
    {
        if (!db.Database.IsNpgsql())
            throw new WhatsAppChannelBindingUnavailableException(
                "Delivery route lookup requires PostgreSQL."
            );
        return await db.Set<WhatsAppRelationshipRoute>()
            .FromSqlInterpolated(
                $"""SELECT * FROM business.find_whatsapp_delivery_route({serviceTenantId}, {senderHash}, {environment}, {outboxId})"""
            )
            .AsNoTracking()
            .SingleOrDefaultAsync(ct);
    }

    internal static async Task<WhatsAppRelationshipRoute?> FindAsync(
        EmploymentRelationshipDbContext db,
        Guid serviceTenantId,
        string senderHash,
        CancellationToken ct
    )
    {
        if (
            serviceTenantId == Guid.Empty
            || senderHash.Length != 64
            || senderHash.Any(value => value is not (>= '0' and <= '9') and not (>= 'a' and <= 'f'))
        )
            throw Denied();
        return await db.Set<WhatsAppRelationshipRoute>()
            .AsNoTracking()
            .SingleOrDefaultAsync(
                value => value.ServiceTenantId == serviceTenantId && value.SenderHash == senderHash,
                ct
            );
    }

    internal static async Task<WhatsAppCurrentRelationshipRoute> RequireCurrentAsync(
        EmploymentRelationshipDbContext db,
        IdentityService identity,
        WhatsAppRelationshipRoute route,
        Guid serviceTenantId,
        string senderHash,
        string expectedIssuer,
        string expectedEnvironment,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        if (
            route.ServiceTenantId != serviceTenantId
            || route.SenderHash != senderHash
            || serviceTenantId == Guid.Empty
            || route.TenantId == Guid.Empty
            || route.BindingId == Guid.Empty
            || route.IdentityLinkId == Guid.Empty
            || route.ActorId == Guid.Empty
            || route.AccountId == Guid.Empty
            || route.MembershipId == Guid.Empty
            || route.BoundEvidenceId == Guid.Empty
            || route.PublishedAt > now
            || route.ActorIssuer != expectedIssuer
            || string.IsNullOrWhiteSpace(expectedIssuer)
            || string.IsNullOrWhiteSpace(expectedEnvironment)
            || senderHash.Length != 64
            || senderHash.Any(value => value is not (>= '0' and <= '9') and not (>= 'a' and <= 'f'))
        )
            throw Denied();
        if (db.Database.IsRelational() && db.Database.CurrentTransaction is null)
            throw new WhatsAppChannelBindingUnavailableException(
                "Current WhatsApp route validation requires the owning transaction."
            );

        await identity.RequireRelationshipChannelLinkAsync(
            db,
            route.IdentityLinkId,
            senderHash,
            new VerifiedCustomerActor(route.ActorIssuer, route.ActorId.ToString("D")),
            new CustomerWorkspaceMembership(
                AccountId: route.AccountId,
                TenantId: route.TenantId,
                MembershipId: route.MembershipId,
                Roles: ["OWNER"]
            ),
            ct
        );
        var binding = await db
            .ChannelBindings.AsNoTracking()
            .SingleOrDefaultAsync(
                value => value.TenantId == route.TenantId && value.BindingId == route.BindingId,
                ct
            );
        if (binding is null)
            throw Denied();
        var relationshipId = binding.RelationshipId;
        if (db.Database.IsNpgsql())
        {
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT relationship_id FROM business.employment_relationships WHERE tenant_id = {route.TenantId} AND relationship_id = {binding.RelationshipId} FOR SHARE",
                ct
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT binding_id FROM business.relationship_participants WHERE tenant_id = {route.TenantId} AND relationship_id = {binding.RelationshipId} AND participant_id = {route.ActorId} FOR SHARE",
                ct
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT contact_id FROM business.whatsapp_journey_contacts WHERE tenant_id = {route.TenantId} AND phone_hmac = {senderHash} FOR SHARE",
                ct
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT binding_id FROM business.channel_bindings WHERE tenant_id = {route.TenantId} AND binding_id = {route.BindingId} FOR SHARE",
                ct
            );
            binding = await db
                .ChannelBindings.AsNoTracking()
                .SingleOrDefaultAsync(
                    value => value.TenantId == route.TenantId && value.BindingId == route.BindingId,
                    ct
                );
        }
        if (
            binding is null
            || binding.RelationshipId != relationshipId
            || binding.Channel != "WHATSAPP"
            || binding.Status != "ACTIVE"
            || binding.ExternalSubjectHash != senderHash
            || binding.ParticipantId != route.ActorId
            || binding.BoundEvidenceId != route.BoundEvidenceId
            || binding.BoundAt is null
            || binding.BoundAt > now
            || binding.RevokedAt is not null
            || binding.AssuranceLevel != "TIER_4_PORTAL_FRESH"
            || !Guid.TryParseExact(binding.ConversationId, "D", out var conversationId)
            || conversationId == Guid.Empty
        )
            throw Denied();
        var relationship = await db
            .EmploymentRelationships.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == route.TenantId
                    && value.RelationshipId == binding.RelationshipId,
                ct
            );
        var participants = await db
            .RelationshipParticipants.AsNoTracking()
            .Where(value =>
                value.TenantId == route.TenantId
                && value.RelationshipId == binding.RelationshipId
                && value.ParticipantId == route.ActorId
                && value.Status == "ACTIVE"
            )
            .Take(2)
            .ToListAsync(ct);
        var contacts = await db
            .WhatsAppJourneyContacts.AsNoTracking()
            .Where(value => value.TenantId == route.TenantId && value.PhoneHmac == senderHash)
            .Take(2)
            .ToListAsync(ct);
        if (
            relationship is null
            || relationship.State
                is not (
                    EmploymentRelationshipState.TrialActive
                    or EmploymentRelationshipState.Active
                )
            || participants.Count != 1
            || participants[0].RevokedAt is not null
            || participants[0].BoundAt > now
            || participants[0].BoundEvidenceId == Guid.Empty
            || RelationshipRoleCodec.ToDatabase(participants[0].Role) != binding.ParticipantRole
            || contacts.Count != 1
            || contacts[0].OptedOutAt is not null
            || contacts[0].OptedInAt > now
        )
            throw Denied();
        var activeBindings = await db
            .ChannelBindings.AsNoTracking()
            .Where(value =>
                value.TenantId == route.TenantId
                && value.Channel == "WHATSAPP"
                && value.Status == "ACTIVE"
                && (
                    value.ExternalSubjectHash == senderHash
                    || value.RelationshipId == binding.RelationshipId
                )
            )
            .Select(value => value.BindingId)
            .Take(2)
            .ToListAsync(ct);
        if (activeBindings.Count != 1 || activeBindings[0] != route.BindingId)
            throw Denied();
        if (db.Database.IsNpgsql())
            await RequireCanonicalConversationAsync(
                db,
                route.TenantId,
                binding.RelationshipId,
                conversationId,
                expectedEnvironment,
                ct
            );
        return new(
            serviceTenantId,
            expectedEnvironment,
            senderHash,
            route.TenantId,
            binding.BindingId,
            binding.RelationshipId,
            binding.ParticipantId,
            binding.ParticipantRole,
            conversationId,
            relationship.StateVersion
        );
    }

    internal static async Task RequireCanonicalConversationAsync(
        EmploymentRelationshipDbContext db,
        Guid tenantId,
        Guid relationshipId,
        Guid conversationId,
        string environment,
        CancellationToken ct
    )
    {
        if (!db.Database.IsNpgsql() || db.Database.CurrentTransaction is null)
            throw new WhatsAppChannelBindingUnavailableException(
                "Canonical WhatsApp route validation requires the owning PostgreSQL transaction."
            );
        if (
            tenantId == Guid.Empty
            || relationshipId == Guid.Empty
            || conversationId == Guid.Empty
            || string.IsNullOrWhiteSpace(environment)
        )
            throw Denied();
        var conversations = await db
            .Database.SqlQuery<Guid>(
                $"""
                SELECT conversation_id AS "Value" FROM business.conversations
                WHERE environment = {environment} AND tenant_id = {tenantId}
                    AND relationship_id = {relationshipId} AND conversation_id = {conversationId}
                FOR SHARE
                """
            )
            .ToListAsync(ct);
        if (conversations.Count != 1 || conversations[0] != conversationId)
            throw Denied();
    }

    private static ConstitutionalActionDeniedException Denied() =>
        new("WhatsApp relationship route is unavailable.");
}
