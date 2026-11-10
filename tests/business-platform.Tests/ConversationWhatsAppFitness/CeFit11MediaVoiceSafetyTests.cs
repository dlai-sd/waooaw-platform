using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class CeFit11MediaVoiceSafetyTests
{
    [Fact]
    public async Task ConcurrentDerivativeRegistrationsPreserveBothBatches()
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var connectionString = postgres.GetConnectionString();
        var appConnection = new NpgsqlConnectionStringBuilder(connectionString)
        {
            ApplicationName = "wc134-media-registration",
        }.ConnectionString;
        var factory = new PostgresConversationFactory(
            new DbContextOptionsBuilder<ConversationStoreDbContext>()
                .UseNpgsql(appConnection)
                .Options
        );
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var media = new WhatsAppMediaRecord
        {
            Environment = "test",
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ProviderReferenceDigest = new string('a', 64),
            DeclaredMediaType = "audio/mpeg",
            DetectedMediaType = "audio/mpeg",
            Locale = "en-IN",
            State = "CLEAN",
        };
        await using (var db = factory.CreateDbContext())
        {
            await db.Database.EnsureCreatedAsync();
            db.WhatsAppMedia.Add(media);
            await db.SaveChangesAsync();
        }
        var options = Options.Create(new Wc120ConversationOptions { Environment = "test" });
        var service = new WhatsAppMediaQuarantineService(
            factory,
            new PayloadFitnessDbFactory(Guid.NewGuid().ToString("N")),
            options,
            new ConversationStopFence(factory, options)
        );
        await using var blocker = new NpgsqlConnection(connectionString);
        await blocker.OpenAsync();
        await using var transaction = await blocker.BeginTransactionAsync();
        await using (
            var takeLock = new NpgsqlCommand(
                "SELECT media_id FROM business.whatsapp_media WHERE media_id = @id FOR UPDATE",
                blocker,
                transaction
            )
        )
        {
            takeLock.Parameters.AddWithValue("id", media.MediaId);
            Assert.Equal(media.MediaId, await takeLock.ExecuteScalarAsync());
        }
        var first = Guid.NewGuid();
        var second = Guid.NewGuid();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        var registration1 = service.RegisterDerivativesAsync(
            tenantId,
            relationshipId,
            media.MediaId,
            [first],
            timeout.Token
        );
        var registration2 = service.RegisterDerivativesAsync(
            tenantId,
            relationshipId,
            media.MediaId,
            [second],
            timeout.Token
        );
        await using var observer = new NpgsqlConnection(connectionString);
        await observer.OpenAsync(timeout.Token);
        await using (
            var waiters = new NpgsqlCommand(
                "SELECT count(*) FROM pg_stat_activity WHERE application_name = 'wc134-media-registration' AND wait_event_type = 'Lock'",
                observer
            )
        )
        {
            while ((long)(await waiters.ExecuteScalarAsync(timeout.Token))! < 2)
                await Task.Delay(50, timeout.Token);
        }
        await transaction.CommitAsync(timeout.Token);
        await Task.WhenAll(registration1, registration2).WaitAsync(timeout.Token);
        await using var verify = factory.CreateDbContext();
        var saved = await verify.WhatsAppMedia.SingleAsync(timeout.Token);
        var references = JsonSerializer.Deserialize<Guid[]>(saved.DerivativePayloadReferencesJson);
        Assert.NotNull(references);
        Assert.Equal(new[] { first, second }.OrderBy(value => value), references);
    }

    private sealed class PostgresConversationFactory(
        DbContextOptions<ConversationStoreDbContext> options
    ) : IDbContextFactory<ConversationStoreDbContext>
    {
        public ConversationStoreDbContext CreateDbContext() => new(options);
    }

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
        var laterDerivative = Guid.NewGuid();
        await using (var payloadDb = context.Payloads.CreateDbContext())
        {
            foreach (var reference in new[] { derivative, laterDerivative })
                payloadDb.OperationalPayloads.Add(
                    new OperationalPayload
                    {
                        PayloadRefId = reference,
                        TenantId = context.TenantId,
                        AgentInstanceId = Guid.NewGuid().ToString("D"),
                        ActionType = "WHATSAPP_MEDIA",
                        PayloadJson = "{}",
                        PiiPresent = true,
                    }
                );
            await payloadDb.SaveChangesAsync();
        }
        await service.RegisterDerivativesAsync(
            context.TenantId,
            context.RelationshipId,
            clean.MediaId,
            new[] { derivative, derivative },
            CancellationToken.None
        );
        await service.RegisterDerivativesAsync(
            context.TenantId,
            context.RelationshipId,
            clean.MediaId,
            new[] { laterDerivative, derivative },
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
            Assert.Equal(3, payloadDb.OperationalPayloads.Count());
            Assert.All(payloadDb.OperationalPayloads, payload => Assert.NotNull(payload.ErasedAt));
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
