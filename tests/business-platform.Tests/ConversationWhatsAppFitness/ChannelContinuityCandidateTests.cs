using System.Security.Cryptography;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Tests.Conversation;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class ChannelContinuityCandidateTests
{
    [Fact]
    public async Task CandidatePrepareAndRevertPreserveSourceAndReplayExactIdentityDuringStop()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var sourceBinding = new ChannelBinding
        {
            TenantId = context.TenantId,
            RelationshipId = context.RelationshipId,
            ParticipantId = context.ParticipantId,
            ParticipantRole = "EMPLOYER",
            Channel = "WEB",
            ExternalSubjectHash = new string('a', 64),
            ConversationId = Guid.NewGuid().ToString("D"),
            AssuranceLevel = "AAL2",
            Status = "ACTIVE",
        };
        await using (var db = context.Relationships.CreateDbContext())
        {
            db.ChannelBindings.Add(sourceBinding);
            await db.SaveChangesAsync();
        }
        var service = new ChannelContinuityService(
            context.Relationships,
            new ConversationConstitutionalGatewayStub(),
            Options.Create(
                new ChannelContinuityOptions
                {
                    EnvelopeHmacKey = Convert.ToBase64String(RandomNumberGenerator.GetBytes(32)),
                }
            )
        );
        var idempotencyKey = Guid.NewGuid();
        var identity = new ChannelContinuityIdentity(
            context.ParticipantId,
            "WEB",
            sourceBinding.ConversationId,
            sourceBinding.ExternalSubjectHash,
            "AAL2",
            DateTimeOffset.UtcNow
        );
        var prepared = await service.PrepareAsync(
            context.TenantId,
            context.RelationshipId,
            identity,
            new(
                "WHATSAPP",
                $"pending:{idempotencyKey:D}",
                "CONTINUE_CONVERSATION",
                Guid.NewGuid(),
                idempotencyKey,
                new string('b', 64),
                "workspace-1",
                7
            ),
            CancellationToken.None
        );
        Assert.Equal("PREPARED", prepared.Status);
        Assert.Equal("ACTIVE", prepared.SourceBinding.Status);
        Assert.Equal("PREPARED", prepared.TargetBinding.Status);

        string checkpointDigest;
        await using (var db = context.Relationships.CreateDbContext())
        {
            db.EmploymentRelationships.Single().State =
                EmploymentRelationshipState.StoppedEmergency;
            checkpointDigest = db
                .ContinuityCheckpoints.Single(value => value.CheckpointId == prepared.HandoffId)
                .ContinuityEnvelopeHash;
            await db.SaveChangesAsync();
        }
        var revert = new RevertChannelHandoff(
            sourceBinding.BindingId,
            Guid.NewGuid(),
            Guid.NewGuid(),
            checkpointDigest,
            "PREPARED",
            "CUSTOMER_CANCELLED",
            new string('c', 64)
        );
        var reverted = await service.RevertAsync(
            context.TenantId,
            context.RelationshipId,
            prepared.HandoffId,
            context.ParticipantId,
            revert,
            CancellationToken.None
        );
        var replay = await service.RevertAsync(
            context.TenantId,
            context.RelationshipId,
            prepared.HandoffId,
            context.ParticipantId,
            revert,
            CancellationToken.None
        );
        Assert.Equal("REVERTED", reverted.Status);
        Assert.Equal("ACTIVE", reverted.SourceBinding.Status);
        Assert.Equal("REVOKED", reverted.TargetBinding.Status);
        Assert.True(replay.Replayed);
    }
}
