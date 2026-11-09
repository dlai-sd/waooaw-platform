// Implements: WC-134 R005; identity-boundary.md Section 6.3.
// constitutional_basis: C-023, C-026, C-059, C-063

using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class WhatsAppAccountLinkConfirmationTests
{
    [Theory]
    [InlineData("LINK", true)]
    [InlineData(" LINK\nsynthetic-code", true)]
    [InlineData("link\tsynthetic-code", true)]
    [InlineData("LINK synthetic-code", true)]
    [InlineData("links", false)]
    [InlineData("show linked agents", false)]
    public void LinkControlTextIsRecognizedBeforeConversationArchiving(
        string text,
        bool expected
    ) => Assert.Equal(expected, WhatsAppAccountLinkInstruction.IsInstruction(text));

    [Theory]
    [InlineData("accepted")]
    [InlineData("accepted-key-rotation")]
    [InlineData("retired-key")]
    [InlineData("wrong-number")]
    [InlineData("tampered")]
    [InlineData("invalid-encoding")]
    [InlineData("oversized")]
    [InlineData("wrong-text")]
    [InlineData("invalid-subject-hash")]
    [InlineData("stale")]
    [InlineData("pre-approval")]
    [InlineData("expired")]
    [InlineData("cancelled")]
    [InlineData("proof-revoked")]
    [InlineData("proof-revoked-during-evidence")]
    [InlineData("proof-expired-during-evidence")]
    [InlineData("sent-stale-during-evidence")]
    [InlineData("evidence-outage")]
    public async Task FreshConfirmationIsDestinationBoundSingleUseAndEvidenceFirst(string scenario)
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var clock = new MutableClock { Now = DateTimeOffset.UtcNow };
        var gateway = new Gateway
        {
            FailConfirmation = scenario == "evidence-outage",
            ConfirmationEffect =
                scenario == "proof-revoked-during-evidence"
                    ? async () =>
                    {
                        await using var revoked = factory.CreateDbContext();
                        (await revoked.VerificationChallenges.SingleAsync()).State =
                            IdentityVerificationState.Expired;
                        await revoked.SaveChangesAsync();
                    }
                : scenario is "proof-expired-during-evidence" or "sent-stale-during-evidence"
                    ? () =>
                    {
                        clock.Now = clock.Now.AddMinutes(
                            scenario == "proof-expired-during-evidence" ? 5 : 2
                        );
                        return Task.CompletedTask;
                    }
                : null,
        };
        var controller = IdentityTestHelpers.CreateController(
            factory,
            tenantId: Guid.NewGuid().ToString(),
            authTimestamp: DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
            constitutionalGateway: gateway
        );
        var request = await IdentityTestHelpers.AccountLinkRequestAsync(factory, controller);
        var created = Assert.IsType<CreatedAtActionResult>(
            await controller.StartAccountLinkAsync(request, CancellationToken.None)
        );
        var linkId = JsonSerializer
            .SerializeToElement(created.Value)
            .GetProperty("LinkId")
            .GetGuid();
        IdentityTestHelpers.RefreshIdempotencyKey(controller);
        var approved = Assert.IsType<OkObjectResult>(
            await controller.ApproveAccountLinkAsync(linkId, CancellationToken.None)
        );
        var instruction = JsonSerializer
            .SerializeToElement(approved.Value)
            .GetProperty("WhatsAppConfirmation")
            .GetString()!;
        var token = instruction[5..];
        Assert.DoesNotContain("+14155550100", token);
        var now = DateTimeOffset.UtcNow;
        clock.Now = now;
        var proof = new VerifiedPhoneIdentityProof(
            "synthetic-confirmation",
            new string('b', 64),
            instruction,
            null,
            "synthetic-app",
            "AAL1_CHANNEL",
            now,
            now,
            now.AddMinutes(5),
            Guid.NewGuid()
        )
        {
            Environment = "demo",
        };
        var phone = "+14155550100";
        await using (var db = factory.CreateDbContext())
        {
            var link = (await db.AccountLinks.FindAsync(linkId))!;
            switch (scenario)
            {
                case "wrong-number":
                    phone = "+14155550101";
                    break;
                case "tampered":
                    var parts = token.Split('.');
                    parts[4] = (parts[4][0] == 'A' ? "B" : "A") + parts[4][1..];
                    token = string.Join('.', parts);
                    proof = proof with { Text = $"LINK {token}" };
                    break;
                case "invalid-encoding":
                    var malformed = token.Split('.');
                    malformed[2] = "?";
                    token = string.Join('.', malformed);
                    proof = proof with { Text = $"LINK {token}" };
                    break;
                case "oversized":
                    token = new string('x', 3073);
                    proof = proof with { Text = $"LINK {token}" };
                    break;
                case "wrong-text":
                    proof = proof with { Text = "ordinary signed message" };
                    break;
                case "invalid-subject-hash":
                    proof = proof with { PhoneSubjectHash = "not-a-digest" };
                    break;
                case "stale":
                    proof = proof with { SentAt = now.AddMinutes(-6) };
                    break;
                case "sent-stale-during-evidence":
                    proof = proof with { SentAt = now.AddMinutes(-4) };
                    link.UpdatedAt = proof.SentAt.AddSeconds(-1);
                    break;
                case "pre-approval":
                    proof = proof with { SentAt = link.UpdatedAt.AddSeconds(-1) };
                    break;
                case "expired":
                    db.Entry(link).Property(value => value.ExpiresAt).CurrentValue = now.AddSeconds(
                        -1
                    );
                    break;
                case "cancelled":
                    break;
                case "proof-revoked":
                    (
                        await db.VerificationChallenges.FindAsync(request.VerifiedMobileProofId)
                    )!.State = IdentityVerificationState.Expired;
                    break;
            }
            await db.SaveChangesAsync();
        }
        if (scenario == "cancelled")
        {
            IdentityTestHelpers.RefreshIdempotencyKey(controller);
            Assert.IsType<OkObjectResult>(
                await controller.CancelAccountLinkAsync(linkId, CancellationToken.None)
            );
        }
        var service =
            scenario is "proof-expired-during-evidence" or "sent-stale-during-evidence"
                ? new IdentityService(
                    factory,
                    Options.Create(
                        new IdentityHmacOptions { Key = IdentityTestHelpers.TestHmacKey }
                    ),
                    new CapturingVerificationDispatcher(),
                    gateway,
                    clock
                )
            : scenario is "accepted-key-rotation" or "retired-key"
                ? new IdentityService(
                    factory,
                    Options.Create(
                        new IdentityHmacOptions
                        {
                            Key = "synthetic-rotated-identity-hmac-key-32-bytes-minimum",
                            ActiveVersion = "v2",
                            ReadOnlyVersions =
                                scenario == "accepted-key-rotation"
                                    ? new Dictionary<string, string>
                                    {
                                        ["v1"] = IdentityTestHelpers.TestHmacKey,
                                    }
                                    : [],
                        }
                    ),
                    new CapturingVerificationDispatcher(),
                    gateway
                )
            : IdentityTestHelpers.CreateService(factory, constitutionalGateway: gateway);
        var acceptedScenario = scenario is "accepted" or "accepted-key-rotation";
        if (acceptedScenario)
        {
            Assert.False(await service.ConfirmAsync(token, phone, proof, CancellationToken.None));
            Assert.True(await service.ConfirmAsync(token, phone, proof, CancellationToken.None));
            await Assert.ThrowsAsync<IdentityActionDeniedException>(() =>
                service.ConfirmAsync(
                    token,
                    phone,
                    proof with
                    {
                        MessageId = "another-message",
                    },
                    CancellationToken.None
                )
            );
            IdentityTestHelpers.RefreshIdempotencyKey(controller);
            Assert.Equal(
                403,
                Assert
                    .IsType<ObjectResult>(
                        await controller.CancelAccountLinkAsync(linkId, CancellationToken.None)
                    )
                    .StatusCode
            );
        }
        else if (scenario == "evidence-outage")
            await Assert.ThrowsAsync<IdentityConstitutionalUnavailableException>(() =>
                service.ConfirmAsync(token, phone, proof, CancellationToken.None)
            );
        else if (scenario is "proof-revoked" or "proof-revoked-during-evidence")
            await Assert.ThrowsAsync<IdentityResourceNotFoundException>(() =>
                service.ConfirmAsync(token, phone, proof, CancellationToken.None)
            );
        else
            await Assert.ThrowsAsync<IdentityActionDeniedException>(() =>
                service.ConfirmAsync(token, phone, proof, CancellationToken.None)
            );

        await using var saved = factory.CreateDbContext();
        var persisted = (await saved.AccountLinks.FindAsync(linkId))!;
        Assert.Equal(acceptedScenario, persisted.State == IdentityAccountLinkState.Linked);
        Assert.Equal(acceptedScenario, persisted.ConfirmationEvidenceId.HasValue);
        Assert.Equal(acceptedScenario, persisted.ConfirmedAt.HasValue);
        if (scenario is "proof-expired-during-evidence" or "sent-stale-during-evidence")
            Assert.True(persisted.ExpiresAt > clock.Now);
        if (scenario == "sent-stale-during-evidence")
            Assert.True(proof.ExpiresAt > clock.Now);
        if (acceptedScenario)
        {
            Assert.Equal(64, persisted.ConfirmationMessageDigest!.Length);
            Assert.NotEqual(Guid.Empty, persisted.ConfirmationEvidenceId);
            Assert.Equal(proof.PhoneSubjectHash, persisted.ConfirmedPhoneSubjectHash);
        }
        Assert.Equal(
            acceptedScenario
            || scenario
                is "evidence-outage"
                    or "proof-revoked-during-evidence"
                    or "proof-expired-during-evidence"
                    or "sent-stale-during-evidence"
                ? 1
                : 0,
            gateway.ConfirmationCalls
        );
        Assert.Equal(scenario == "cancelled" ? 3 : 2, await saved.IdempotencyLedger.CountAsync());
    }

    [Theory]
    [InlineData(false, false)]
    [InlineData(true, false)]
    [InlineData(true, true)]
    public async Task PortalCancellationIsExplicitReplaySafeAndEvidenceFirst(
        bool approved,
        bool evidenceOutage
    )
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var gateway = new Gateway { FailCancellation = evidenceOutage };
        var controller = IdentityTestHelpers.CreateController(
            factory,
            tenantId: Guid.NewGuid().ToString(),
            authTimestamp: DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
            constitutionalGateway: gateway
        );
        var created = Assert.IsType<CreatedAtActionResult>(
            await controller.StartAccountLinkAsync(
                await IdentityTestHelpers.AccountLinkRequestAsync(factory, controller),
                CancellationToken.None
            )
        );
        var linkId = JsonSerializer
            .SerializeToElement(created.Value)
            .GetProperty("LinkId")
            .GetGuid();
        if (approved)
        {
            IdentityTestHelpers.RefreshIdempotencyKey(controller);
            Assert.IsType<OkObjectResult>(
                await controller.ApproveAccountLinkAsync(linkId, CancellationToken.None)
            );
        }
        IdentityTestHelpers.RefreshIdempotencyKey(controller);
        var result = Assert.IsAssignableFrom<ObjectResult>(
            await controller.CancelAccountLinkAsync(linkId, CancellationToken.None)
        );
        Assert.Equal(evidenceOutage ? 503 : 200, result.StatusCode);
        if (!evidenceOutage)
        {
            Assert.Equal(
                "CANCELLED",
                JsonSerializer.SerializeToElement(result.Value).GetProperty("State").GetString()
            );
            Assert.IsType<OkObjectResult>(
                await controller.CancelAccountLinkAsync(linkId, CancellationToken.None)
            );
        }
        await using var saved = factory.CreateDbContext();
        var link = (await saved.AccountLinks.FindAsync(linkId))!;
        Assert.Equal(!evidenceOutage, link.State == IdentityAccountLinkState.Cancelled);
        Assert.Equal(!evidenceOutage, link.CancellationEvidenceId.HasValue);
        Assert.Equal(1, gateway.CancellationCalls);
        Assert.Equal(
            (approved ? 2 : 1) + (evidenceOutage ? 0 : 1),
            await saved.IdempotencyLedger.CountAsync()
        );
    }

    [Theory]
    [InlineData("current")]
    [InlineData("cancelled")]
    [InlineData("foreign-actor")]
    [InlineData("foreign-tenant")]
    [InlineData("foreign-account")]
    [InlineData("manager")]
    [InlineData("changed-destination")]
    [InlineData("missing-evidence")]
    [InlineData("future-confirmation")]
    [InlineData("revoked-proof")]
    [InlineData("changed-registration-number")]
    [InlineData("cancelled-registration")]
    public async Task RelationshipCommitRereadsOwnerLinkAndRegistrationInsteadOfTrustingEarlierRead(
        string change
    )
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var actor = new VerifiedCustomerActor("https://identity.test", Guid.NewGuid().ToString("D"));
        var membership = new CustomerWorkspaceMembership(
            Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), ["OWNER"]);
        var digest = new string('b', 64);
        var registration = new IdentityRegistrationRecord
        {
            ActorIssuer = actor.Issuer, ActorSubject = actor.Subject,
            AccountId = membership.AccountId, State = IdentityRegistrationState.Completed,
            MobileVerified = true, MobileHmacDomain = "mobile",
            MobileHmacVersion = "v1", MobileHmacKey = new string('c', 64),
        };
        var proof = new IdentityVerificationChallengeRecord
        {
            RegistrationId = registration.RegistrationId, ActorSubject = actor.Subject,
            Purpose = IdentityVerificationPurpose.Mobile, State = IdentityVerificationState.Consumed,
            VerifiedAt = DateTimeOffset.UtcNow.AddMinutes(-1), DeliveryState = "SUBMITTED",
            DestinationHmacDomain = registration.MobileHmacDomain,
            DestinationHmacVersion = registration.MobileHmacVersion,
            DestinationHmacKey = registration.MobileHmacKey,
        };
        var link = new IdentityAccountLinkRecord
        {
            ActorSubject = actor.Subject, TenantId = membership.TenantId,
            VerifiedMobileProofId = proof.ChallengeId, State = IdentityAccountLinkState.Linked,
            ConfirmationEvidenceId = Guid.NewGuid(), ConfirmedAt = DateTimeOffset.UtcNow.AddSeconds(-1),
            ConfirmedPhoneSubjectHash = digest,
        };
        await using (var seed = factory.CreateDbContext())
        {
            seed.Add(registration);
            seed.Add(proof);
            seed.Add(link);
            await seed.SaveChangesAsync();
        }
        var identity = IdentityTestHelpers.CreateService(factory);
        Assert.Equal(digest, await identity.GetConfirmedPhoneSubjectHashAsync(
            link.LinkId, actor.Subject, membership.TenantId, CancellationToken.None, actor, membership));
        await using (var mutation = factory.CreateDbContext())
        {
            var currentLink = (await mutation.AccountLinks.FindAsync(link.LinkId))!;
            var currentRegistration = (await mutation.Registrations.FindAsync(registration.RegistrationId))!;
            switch (change)
            {
                case "cancelled": currentLink.State = IdentityAccountLinkState.Cancelled; break;
                case "changed-destination": currentLink.ConfirmedPhoneSubjectHash = new string('d', 64); break;
                case "missing-evidence": currentLink.ConfirmationEvidenceId = null; break;
                case "future-confirmation": currentLink.ConfirmedAt = DateTimeOffset.UtcNow.AddMinutes(1); break;
                case "revoked-proof":
                    (await mutation.VerificationChallenges.FindAsync(proof.ChallengeId))!.State = IdentityVerificationState.Expired;
                    break;
                case "changed-registration-number": currentRegistration.MobileHmacKey = new string('e', 64); break;
                case "cancelled-registration": currentRegistration.State = IdentityRegistrationState.Cancelled; break;
            }
            await mutation.SaveChangesAsync();
        }
        if (change == "foreign-actor")
            actor = new VerifiedCustomerActor(actor.Issuer, Guid.NewGuid().ToString("D"));
        if (change == "foreign-tenant")
            membership = membership with { TenantId = Guid.NewGuid() };
        if (change == "foreign-account")
            membership = membership with { AccountId = Guid.NewGuid() };
        if (change == "manager")
            membership = membership with { Roles = ["MANAGER"] };
        var relationships = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        await using var relationshipDb = relationships.CreateDbContext();
        if (change == "current")
            await identity.RequireRelationshipChannelLinkAsync(
                relationshipDb, link.LinkId, digest, actor, membership, CancellationToken.None);
        else
            await Assert.ThrowsAsync<IdentityResourceNotFoundException>(() =>
                identity.RequireRelationshipChannelLinkAsync(
                    relationshipDb, link.LinkId, digest, actor, membership, CancellationToken.None));
        await using var saved = factory.CreateDbContext();
        Assert.Single(await saved.AccountLinks.ToListAsync());
        Assert.Empty(await saved.IdempotencyLedger.ToListAsync());
    }

    private sealed class MutableClock : TimeProvider
    {
        public DateTimeOffset Now { get; set; }

        public override DateTimeOffset GetUtcNow() => Now;
    }

    private sealed class Gateway : IIdentityConstitutionalGateway
    {
        public bool FailConfirmation { get; init; }
        public Func<Task>? ConfirmationEffect { get; init; }
        public bool FailCancellation { get; init; }
        public int ConfirmationCalls { get; private set; }
        public int CancellationCalls { get; private set; }

        public async Task<Guid> AuthorizeAndRecordAsync(
            Guid tenantId,
            Guid actionInstanceId,
            string actionType,
            object actionParameters,
            CancellationToken cancellationToken
        )
        {
            if (actionType == "IDENTITY_ACCOUNT_LINK_CONFIRM")
            {
                ConfirmationCalls++;
                if (FailConfirmation)
                    throw new IdentityConstitutionalUnavailableException("synthetic outage");
                if (ConfirmationEffect is not null)
                    await ConfirmationEffect();
            }
            if (actionType == "IDENTITY_ACCOUNT_LINK_CANCEL")
            {
                CancellationCalls++;
                if (FailCancellation)
                    throw new IdentityConstitutionalUnavailableException("synthetic outage");
            }
            return Guid.NewGuid();
        }
    }
}
