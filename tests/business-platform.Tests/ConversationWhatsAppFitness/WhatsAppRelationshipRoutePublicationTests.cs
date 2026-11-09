using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Tests.Conversation;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppRelationshipRoutePublicationTests
{
    [Fact]
    public async Task PublicationRetainsExactCustomerOwnerCoordinatesAndReplayDoesNotRenew()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        await using var db = factory.CreateDbContext();
        var binding = Binding();
        var proof = Proof(binding);
        var serviceTenant = Guid.NewGuid();
        var link = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;
        db.ChannelBindings.Add(binding);
        await db.SaveChangesAsync();
        await WhatsAppRelationshipRoutePublication.PublishAsync(
            db, serviceTenant, binding, link, proof, now, CancellationToken.None);
        await WhatsAppRelationshipRoutePublication.PublishAsync(
            db, serviceTenant, binding, link, proof, now.AddMinutes(1), CancellationToken.None);
        var route = await db.Set<WhatsAppRelationshipRoute>().SingleAsync();
        Assert.Equal(serviceTenant, route.ServiceTenantId);
        Assert.NotEqual(serviceTenant, route.TenantId);
        Assert.Equal(binding.TenantId, route.TenantId);
        Assert.Equal(binding.BindingId, route.BindingId);
        Assert.Equal(binding.ExternalSubjectHash, route.SenderHash);
        Assert.Equal(binding.BoundEvidenceId, route.BoundEvidenceId);
        Assert.Equal(link, route.IdentityLinkId);
        Assert.Equal(proof.Actor!.Issuer, route.ActorIssuer);
        Assert.Equal(binding.ParticipantId, route.ActorId);
        Assert.Equal(proof.Membership!.AccountId, route.AccountId);
        Assert.Equal(proof.Membership.MembershipId, route.MembershipId);
        Assert.Equal(now, route.PublishedAt);
        var candidate = await WhatsAppRelationshipRouteAuthority.FindAsync(
            db, serviceTenant, binding.ExternalSubjectHash, CancellationToken.None);
        Assert.NotNull(candidate);
        Assert.Equal(binding.TenantId, candidate.TenantId);
        Assert.Null(await WhatsAppRelationshipRouteAuthority.FindAsync(
            db, Guid.NewGuid(), binding.ExternalSubjectHash, CancellationToken.None));
        Assert.Null(await WhatsAppRelationshipRouteAuthority.FindAsync(
            db, serviceTenant, new string('b', 64), CancellationToken.None));
    }

    [Theory]
    [InlineData("binding")]
    [InlineData("link")]
    [InlineData("issuer")]
    [InlineData("account")]
    [InlineData("membership")]
    [InlineData("evidence")]
    public async Task DivergentPublicationCannotReplaceOriginalRoute(string change)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        await using var db = factory.CreateDbContext();
        var binding = Binding();
        var proof = Proof(binding);
        var serviceTenant = Guid.NewGuid();
        var link = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;
        await WhatsAppRelationshipRoutePublication.PublishAsync(
            db, serviceTenant, binding, link, proof, now, CancellationToken.None);
        var changedBinding = change is "binding" or "evidence" ? Binding(
            binding.TenantId, binding.ParticipantId,
            change == "binding" ? Guid.NewGuid() : binding.BindingId,
            change == "evidence" ? Guid.NewGuid() : binding.BoundEvidenceId
        ) : binding;
        var changedProof = proof with
        {
            Actor = change == "issuer"
                ? new VerifiedCustomerActor("https://other.identity.test", binding.ParticipantId.ToString("D"))
                : proof.Actor,
            Membership = proof.Membership! with
            {
                AccountId = change == "account" ? Guid.NewGuid() : proof.Membership!.AccountId,
                MembershipId = change == "membership" ? Guid.NewGuid() : proof.Membership!.MembershipId,
            },
        };
        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() =>
            WhatsAppRelationshipRoutePublication.PublishAsync(
                db, serviceTenant, changedBinding, change == "link" ? Guid.NewGuid() : link,
                changedProof, now, CancellationToken.None));
        var route = await db.Set<WhatsAppRelationshipRoute>().SingleAsync();
        Assert.Equal(binding.BindingId, route.BindingId);
        Assert.Equal(link, route.IdentityLinkId);
        Assert.Equal(proof.Membership!.MembershipId, route.MembershipId);
    }

    [Theory]
    [InlineData("actor")]
    [InlineData("membership")]
    [InlineData("tenant")]
    [InlineData("role")]
    [InlineData("subject")]
    public async Task UnverifiedOrMismatchedPublicationHasNoEffect(string change)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        await using var db = factory.CreateDbContext();
        var binding = Binding();
        var original = Proof(binding);
        var proof = original with
        {
            Actor = change == "actor" ? null : change == "subject"
                ? new VerifiedCustomerActor(original.Actor!.Issuer, Guid.NewGuid().ToString("D"))
                : original.Actor,
            Membership = change == "membership" ? null : original.Membership! with
            {
                TenantId = change == "tenant" ? Guid.NewGuid() : binding.TenantId,
                Roles = change == "role" ? ["MANAGER"] : ["OWNER"],
            },
        };
        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() =>
            WhatsAppRelationshipRoutePublication.PublishAsync(
                db, Guid.NewGuid(), binding, Guid.NewGuid(), proof,
                DateTimeOffset.UtcNow, CancellationToken.None));
        Assert.Empty(await db.Set<WhatsAppRelationshipRoute>().ToListAsync());
    }

    private static ChannelBinding Binding(
        Guid? tenant = null, Guid? actor = null, Guid? binding = null, Guid? evidence = null
    ) => new()
    {
        TenantId = tenant ?? Guid.NewGuid(),
        BindingId = binding ?? Guid.NewGuid(),
        ParticipantId = actor ?? Guid.NewGuid(),
        RelationshipId = Guid.NewGuid(),
        ParticipantRole = "EMPLOYER",
        Channel = "WHATSAPP",
        Status = "ACTIVE",
        ExternalSubjectHash = new string('a', 64),
        BoundEvidenceId = evidence ?? Guid.NewGuid(),
        BoundAt = DateTimeOffset.UtcNow.AddMinutes(-1),
    };

    private static PortalPhoneAttachProof Proof(ChannelBinding binding) => new(
        binding.ParticipantId, "TIER_4_PORTAL_FRESH", DateTimeOffset.UtcNow, Guid.NewGuid(),
        new VerifiedCustomerActor("https://identity.test", binding.ParticipantId.ToString("D")),
        new CustomerWorkspaceMembership(
            AccountId: Guid.NewGuid(), TenantId: binding.TenantId,
            MembershipId: Guid.NewGuid(), Roles: ["OWNER"])
    );
}
