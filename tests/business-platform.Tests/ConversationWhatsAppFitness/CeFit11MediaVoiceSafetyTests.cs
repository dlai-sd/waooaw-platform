using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class CeFit11MediaVoiceSafetyTests
{
    [Fact]
    public async Task MediaCorpus_ScansBeforeReasoning_AndRequiresCorrectedTranscriptConfirmationAndSendConsent()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var service = new WhatsAppMediaQuarantineService(
            context.Conversations,
            context.Payloads,
            Microsoft.Extensions.Options.Options.Create(context.Options),
            context.StopFence
        );
        var payloadReference = Guid.NewGuid();
        var media = await service.QuarantineAsync(
            context.TenantId,
            context.RelationshipId,
            Valid(payloadReference),
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );
        Assert.Equal("QUARANTINED", media.State);

        await Assert.ThrowsAsync<VoiceInvalidMediaException>(() =>
            service.QuarantineAsync(
                context.TenantId,
                context.RelationshipId,
                Valid(Guid.NewGuid()) with
                {
                    ArchiveEntries = 1,
                },
                DateTimeOffset.UtcNow,
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<VoiceInvalidMediaException>(() =>
            service.QuarantineAsync(
                context.TenantId,
                context.RelationshipId,
                Valid(Guid.NewGuid()) with
                {
                    ExpandedBytes = 50_000_001,
                },
                DateTimeOffset.UtcNow,
                CancellationToken.None
            )
        );

        var clean = await service.RecordScanVerdictAsync(
            context.TenantId,
            context.RelationshipId,
            media.MediaId,
            new(
                "CLEAN",
                "engine-1",
                "policy-1",
                "signatures-1",
                DateTimeOffset.UtcNow.AddMinutes(-1),
                new string('d', 64),
                DateTimeOffset.UtcNow
            ),
            CancellationToken.None
        );
        Assert.Equal("CLEAN", clean.State);
        await using var db = context.Conversations.CreateDbContext();
        Assert.Empty(db.Messages);
    }

    [Fact]
    public async Task MediaValidationAndLifecycleFailClosedAcrossEveryBound()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var service = new WhatsAppMediaQuarantineService(
            context.Conversations,
            context.Payloads,
            Microsoft.Extensions.Options.Options.Create(context.Options),
            context.StopFence
        );
        var payloadReference = Guid.NewGuid();
        var valid = Valid(payloadReference);
        var invalid = new[]
        {
            valid with
            {
                ProviderReferenceDigest = "bad",
            },
            valid with
            {
                DeclaredMediaType = "video/mp4",
            },
            valid with
            {
                DetectedMediaType = "audio/mpeg",
            },
            valid with
            {
                SignatureMediaType = "audio/mpeg",
            },
            valid with
            {
                SniffedMediaType = "audio/mpeg",
            },
            valid with
            {
                WireBytes = 0,
            },
            valid with
            {
                ExpandedBytes = 999_999,
            },
            valid with
            {
                ExpandedBytes = 100_000_001,
            },
            valid with
            {
                ExpandedBytes = 11_000_001,
            },
            valid with
            {
                DurationSeconds = 0,
            },
            valid with
            {
                CpuMilliseconds = 5_001,
            },
            valid with
            {
                WallTimeMilliseconds = 10_001,
            },
            valid with
            {
                PeakMemoryBytes = 268_435_457,
            },
            valid with
            {
                RecursionDepth = 17,
            },
            valid with
            {
                ArchiveEntries = 1,
            },
            valid with
            {
                PageCount = 1,
            },
            valid with
            {
                VideoFrames = 1,
            },
            valid with
            {
                AnimationFrames = 1,
            },
            valid with
            {
                ImageMegapixels = 41,
            },
            valid with
            {
                IsolationConfirmed = false,
            },
            valid with
            {
                Locale = "en-US",
            },
            valid with
            {
                PayloadReference = "",
            },
            valid with
            {
                PayloadReference = "not-a-guid",
            },
        };
        foreach (var inspection in invalid)
        {
            await Assert.ThrowsAsync<VoiceInvalidMediaException>(() =>
                service.QuarantineAsync(
                    context.TenantId,
                    context.RelationshipId,
                    inspection,
                    DateTimeOffset.UtcNow,
                    CancellationToken.None
                )
            );
        }

        await using (var payloadDb = context.Payloads.CreateDbContext())
        {
            payloadDb.OperationalPayloads.Add(
                new OperationalPayload
                {
                    PayloadRefId = payloadReference,
                    TenantId = context.TenantId,
                    AgentInstanceId = Guid.NewGuid().ToString("D"),
                    ActionType = "WHATSAPP_MEDIA",
                    PayloadJson = "{}",
                    PiiPresent = true,
                }
            );
            await payloadDb.SaveChangesAsync();
        }
        var clean = await service.QuarantineAsync(
            context.TenantId,
            context.RelationshipId,
            valid,
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );
        Assert.Equal(
            clean.MediaId,
            (
                await service.QuarantineAsync(
                    context.TenantId,
                    context.RelationshipId,
                    valid,
                    DateTimeOffset.UtcNow,
                    CancellationToken.None
                )
            ).MediaId
        );
        await service.RecordScanVerdictAsync(
            context.TenantId,
            context.RelationshipId,
            clean.MediaId,
            Verdict("CLEAN"),
            CancellationToken.None
        );
        var derivative = Guid.NewGuid();
        await service.RegisterDerivativesAsync(
            context.TenantId,
            context.RelationshipId,
            clean.MediaId,
            new[] { derivative, derivative },
            CancellationToken.None
        );
        await service.ApplyRelationshipClosureAsync(
            context.TenantId,
            context.RelationshipId,
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );
        await service.SetLegalHoldAsync(
            context.TenantId,
            context.RelationshipId,
            clean.MediaId,
            true,
            CancellationToken.None
        );
        await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
            service.EraseAsync(
                context.TenantId,
                context.RelationshipId,
                clean.MediaId,
                DateTimeOffset.UtcNow,
                CancellationToken.None
            )
        );
        await service.SetLegalHoldAsync(
            context.TenantId,
            context.RelationshipId,
            clean.MediaId,
            false,
            CancellationToken.None
        );
        await service.EraseAsync(
            context.TenantId,
            context.RelationshipId,
            clean.MediaId,
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );
        await using (var payloadDb = context.Payloads.CreateDbContext())
        {
            Assert.NotNull(payloadDb.OperationalPayloads.Single().ErasedAt);
        }

        var rejected = await service.QuarantineAsync(
            context.TenantId,
            context.RelationshipId,
            Valid(Guid.NewGuid()) with
            {
                ProviderReferenceDigest = new string('b', 64),
            },
            DateTimeOffset.UtcNow,
            CancellationToken.None
        );
        Assert.Equal(
            "REJECTED",
            (
                await service.RecordScanVerdictAsync(
                    context.TenantId,
                    context.RelationshipId,
                    rejected.MediaId,
                    Verdict("REJECTED"),
                    CancellationToken.None
                )
            ).State
        );
        await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
            service.RecordScanVerdictAsync(
                context.TenantId,
                context.RelationshipId,
                rejected.MediaId,
                Verdict("CLEAN"),
                CancellationToken.None
            )
        );
        Assert.Equal(
            1,
            await service.PurgeDueAsync(DateTimeOffset.UtcNow.AddDays(2), CancellationToken.None)
        );
    }

    private static WhatsAppMediaScanVerdictV1 Verdict(string verdict)
    {
        var observedAt = DateTimeOffset.UtcNow;
        return new(
            verdict,
            "engine-1",
            "policy-1",
            "signatures-1",
            observedAt.AddMinutes(-1),
            new string('d', 64),
            observedAt
        );
    }

    private static WhatsAppMediaInspectionV1 Valid(Guid payloadReference) =>
        new(
            new string('a', 64),
            "audio/ogg; codecs=opus",
            "audio/ogg; codecs=opus",
            1_000_000,
            1_000_000,
            60,
            "en-IN",
            payloadReference.ToString("D"),
            "audio/ogg; codecs=opus",
            "audio/ogg; codecs=opus",
            100,
            200,
            10_000_000,
            0,
            0,
            0,
            0,
            0,
            0,
            true
        );
}
