using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Tests.Conversation;
using Waooaw.BusinessPlatform.Tests.Identity;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppRelationshipRouteAuthorityTests
{
    [Theory]
    [InlineData("current")]
    [InlineData("cancelled-link")]
    [InlineData("issuer")]
    [InlineData("sender")]
    [InlineData("service-tenant")]
    [InlineData("revoked-binding")]
    [InlineData("binding-actor")]
    [InlineData("binding-evidence")]
    [InlineData("binding-destination")]
    [InlineData("binding-conversation")]
    [InlineData("binding-assurance")]
    [InlineData("stopped-relationship")]
    [InlineData("revoked-participant")]
    [InlineData("participant-role")]
    [InlineData("withdrawn-contact")]
    [InlineData("ambiguous-binding")]
    public async Task DirectoryCoordinatesRequireCurrentIdentityAndExactRelationshipAuthority(string change)
    {
        var identities = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var identity = IdentityTestHelpers.CreateService(identities);
        var actorId = Guid.NewGuid();
        var tenant = Guid.NewGuid();
        var serviceTenant = Guid.NewGuid();
        var account = Guid.NewGuid();
        var membership = Guid.NewGuid();
        const string issuer = "https://identity.test";
        var sender = new string('a', 64);
        var now = DateTimeOffset.UtcNow;
        var registration = new IdentityRegistrationRecord
        {
            ActorIssuer = issuer, ActorSubject = actorId.ToString("D"),
            State = IdentityRegistrationState.Completed, AccountId = account,
            MobileVerified = true, MobileHmacDomain = "mobile",
            MobileHmacVersion = "v1", MobileHmacKey = new string('b', 64),
        };
        var proof = new IdentityVerificationChallengeRecord
        {
            RegistrationId = registration.RegistrationId, ActorSubject = actorId.ToString("D"),
            Purpose = IdentityVerificationPurpose.Mobile, State = IdentityVerificationState.Consumed,
            VerifiedAt = now.AddMinutes(-1), DeliveryState = "SUBMITTED",
            DestinationHmacDomain = "mobile", DestinationHmacVersion = "v1",
            DestinationHmacKey = registration.MobileHmacKey,
        };
        var link = new IdentityAccountLinkRecord
        {
            ActorSubject = actorId.ToString("D"), TenantId = tenant,
            State = change == "cancelled-link" ? IdentityAccountLinkState.Cancelled : IdentityAccountLinkState.Linked,
            VerifiedMobileProofId = proof.ChallengeId, ConfirmationEvidenceId = Guid.NewGuid(),
            ConfirmedAt = now.AddSeconds(-1), ConfirmedPhoneSubjectHash = sender,
        };
        await using (var seed = identities.CreateDbContext())
        {
            seed.Add(registration);
            seed.Add(proof);
            seed.Add(link);
            await seed.SaveChangesAsync();
        }
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        await using var db = factory.CreateDbContext();
        var relationship = new EmploymentRelationship
        {
            TenantId = tenant, ProfessionalType = "DMA", StateVersion = 7,
            State = change == "stopped-relationship"
                ? EmploymentRelationshipState.StoppedEmergency : EmploymentRelationshipState.Active,
        };
        var participant = new RelationshipParticipant
        {
            TenantId = tenant, RelationshipId = relationship.RelationshipId, ParticipantId = actorId,
            Role = change == "participant-role" ? RelationshipParticipantRole.Evaluator : RelationshipParticipantRole.Employer,
            Status = change == "revoked-participant" ? "REVOKED" : "ACTIVE",
            BoundEvidenceId = Guid.NewGuid(), BoundAt = now.AddMinutes(-1),
        };
        var evidence = Guid.NewGuid();
        var conversation = Guid.NewGuid();
        var binding = new ChannelBinding
        {
            TenantId = tenant, RelationshipId = relationship.RelationshipId,
            ParticipantId = change == "binding-actor" ? Guid.NewGuid() : actorId,
            ParticipantRole = "EMPLOYER", Channel = "WHATSAPP",
            Status = change == "revoked-binding" ? "REVOKED" : "ACTIVE",
            ExternalSubjectHash = change == "binding-destination" ? new string('c', 64) : sender,
            ConversationId = change == "binding-conversation" ? "not-a-conversation" : conversation.ToString("D"),
            AssuranceLevel = change == "binding-assurance" ? "TIER_1_PHONE_IDENTITY" : "TIER_4_PORTAL_FRESH",
            BoundEvidenceId = change == "binding-evidence" ? Guid.NewGuid() : evidence,
            BoundAt = now.AddMinutes(-1),
        };
        db.Add(relationship);
        db.Add(participant);
        db.Add(binding);
        db.Add(new WhatsAppJourneyContact
        {
            TenantId = tenant, PhoneHmac = sender, OptedInAt = now.AddMinutes(-1),
            OptedOutAt = change == "withdrawn-contact" ? now.AddSeconds(-1) : null,
        });
        if (change == "ambiguous-binding")
            db.Add(new ChannelBinding
            {
                TenantId = tenant, RelationshipId = relationship.RelationshipId,
                ParticipantId = actorId, ParticipantRole = "EMPLOYER", Channel = "WHATSAPP",
                Status = "ACTIVE", ExternalSubjectHash = sender,
            });
        await db.SaveChangesAsync();
        var route = new WhatsAppRelationshipRoute
        {
            ServiceTenantId = serviceTenant, SenderHash = sender, TenantId = tenant,
            BindingId = binding.BindingId, IdentityLinkId = link.LinkId,
            ActorIssuer = issuer, ActorId = actorId, AccountId = account, MembershipId = membership,
            BoundEvidenceId = evidence, PublishedAt = now.AddSeconds(-1),
        };
        Task<WhatsAppCurrentRelationshipRoute> Resolve() =>
            WhatsAppRelationshipRouteAuthority.RequireCurrentAsync(
                db, identity, route, change == "service-tenant" ? Guid.NewGuid() : serviceTenant,
                change == "sender" ? new string('d', 64) : sender,
                change == "issuer" ? "https://other.identity.test" : issuer, "test", now, CancellationToken.None);
        if (change == "current")
        {
            var current = await Resolve();
            Assert.Equal(tenant, current.TenantId);
            Assert.Equal(serviceTenant, current.ServiceTenantId);
            Assert.Equal("test", current.Environment);
            Assert.Equal(relationship.RelationshipId, current.RelationshipId);
            Assert.Equal(actorId, current.ParticipantId);
            Assert.Equal("EMPLOYER", current.ParticipantRole);
            Assert.Equal(conversation, current.ConversationId);
            Assert.Equal(7, current.RelationshipVersion);
        }
        else if (change == "cancelled-link")
            await Assert.ThrowsAsync<IdentityResourceNotFoundException>(Resolve);
        else
            await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(Resolve);
        Assert.Empty(await db.Set<WhatsAppRelationshipRoute>().ToListAsync());
    }
}
