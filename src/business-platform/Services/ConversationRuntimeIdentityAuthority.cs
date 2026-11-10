// Implements: WC-134 R006/R008; current Identity, never stale JWT tenant/role authority.
// constitutional_basis: C-023, C-026, C-059, C-063
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record ConversationRuntimeMembership(
    string Issuer,
    Guid AccountId,
    Guid MembershipId,
    string Role
);

public sealed class ConversationRuntimeIdentityAuthority(IConfiguration configuration)
{
    public async Task<ConversationRuntimeMembership> ResolveAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        Guid actorId,
        CancellationToken cancellationToken
    )
    {
        var issuer =
            configuration["IdentityBrokerRead:ActorIssuer"]
            ?? configuration["IdentityEnvironment:Keycloak:Issuer"];
        if (
            string.IsNullOrWhiteSpace(issuer)
            || !Uri.TryCreate(issuer, UriKind.Absolute, out var uri)
            || uri.Scheme is not ("https" or "http")
        )
            throw new ConversationExecutionUnavailableException();
        return await LockAsync(db, tenantId, actorId, issuer, null, cancellationToken);
    }

    public async Task RequireCurrentAsync(
        ConversationStoreDbContext db,
        ConversationExecution execution,
        Guid actorId,
        CancellationToken cancellationToken
    )
    {
        if (
            execution.RuntimeActorIssuer is not { Length: > 0 } issuer
            || execution.RuntimeMembershipId is not { } membership
            || execution.RuntimeAccountId is not { } account
            || execution.RuntimeActorId != actorId
        )
            throw new ConversationNotAccessibleException();
        if (
            issuer
            != (
                configuration["IdentityBrokerRead:ActorIssuer"]
                ?? configuration["IdentityEnvironment:Keycloak:Issuer"]
            )
        )
            throw new ConversationNotAccessibleException();
        var current = await LockAsync(
            db,
            execution.TenantId,
            actorId,
            issuer,
            membership,
            cancellationToken
        );
        if (current.AccountId != account)
            throw new ConversationNotAccessibleException();
    }

    private static async Task<ConversationRuntimeMembership> LockAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        Guid actorId,
        string issuer,
        Guid? membershipId,
        CancellationToken cancellationToken
    )
    {
        if (!db.Database.IsRelational())
            throw new ConversationExecutionUnavailableException();
        var memberships = await db
            .Database.SqlQuery<MembershipRow>(
                $"""
                SELECT account_id AS "AccountId", membership_id AS "MembershipId", roles AS "Roles"
                FROM identity.lock_conversation_runtime_membership({issuer}, {actorId}, {tenantId}, {membershipId})
                """
            )
            .ToListAsync(cancellationToken);
        if (
            memberships.Count != 1
            || memberships[0].Roles.Length != 1
            || memberships[0].Roles[0] is not ("OWNER" or "MANAGER")
        )
            throw new ConversationNotAccessibleException();
        return new(
            issuer,
            memberships[0].AccountId,
            memberships[0].MembershipId,
            memberships[0].Roles[0]
        );
    }

    private sealed class MembershipRow
    {
        public Guid AccountId { get; init; }
        public Guid MembershipId { get; init; }
        public string[] Roles { get; init; } = [];
    }
}
