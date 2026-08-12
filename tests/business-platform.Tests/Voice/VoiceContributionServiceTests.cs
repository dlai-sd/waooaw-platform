// Implements: work-contracts/WC-062-wc034-f6-voice-interaction.md WC062-05
// constitutional_basis: C-001, C-005, C-023, C-026, C-042, C-049, C-059, C-063, C-076

using System.Text;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Voice;

internal sealed class InMemoryVoiceFactory(string databaseName) : IDbContextFactory<VoiceContributionDbContext>
{
    public VoiceContributionDbContext CreateDbContext() => new(
        new DbContextOptionsBuilder<VoiceContributionDbContext>().UseInMemoryDatabase(databaseName).Options);
}

internal sealed class VoiceMediaGatewayStub : IVoiceMediaGateway
{
    public int StoreCount { get; private set; }
    public int EraseCount { get; private set; }

    public Task<VoiceMediaInspection> ValidateScanAndStoreAsync(
        Stream audio,
        string declaredMediaType,
        Guid tenantId,
        Guid relationshipId,
        Guid sessionId,
        CancellationToken cancellationToken)
    {
        StoreCount += 1;
        return Task.FromResult(new VoiceMediaInspection(
            new string('a', 64), declaredMediaType, "audio/webm", audio.Length, 30_000, Guid.NewGuid().ToString()));
    }

    public Task EraseAsync(string payloadReference, CancellationToken cancellationToken)
    {
        EraseCount += 1;
        return Task.CompletedTask;
    }
}

internal sealed class VoiceTranscriptionGatewayStub(decimal confidence = 0.75m) : IVoiceTranscriptionGateway
{
    public int CallCount { get; private set; }

    public Task<VoiceTranscriptionResult> TranscribeAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid sessionId,
        VoiceMediaInspection inspection,
        string locale,
        CancellationToken cancellationToken)
    {
        CallCount += 1;
        return Task.FromResult(new VoiceTranscriptionResult("provider text", locale, confidence, "1.0.0"));
    }
}

internal sealed class TestVoiceContentProtector : IVoiceContentProtector
{
    public string Protect(string plaintext) => Convert.ToBase64String(Encoding.UTF8.GetBytes(plaintext));
    public string Unprotect(string ciphertext) => Encoding.UTF8.GetString(Convert.FromBase64String(ciphertext));
}

public sealed class VoiceContributionServiceTests
{
    [Fact]
    public async Task CctVoiceReplay01_FullLifecycleIsIdempotentAndEvidenceFirst()
    {
        var context = await CreateAsync();
        var createKey = Guid.NewGuid();
        var request = new CreateVoiceContributionSessionRequestV1("1.0.0", "mr-IN");
        var firstCreate = await context.Service.CreateAsync(
            context.TenantId, context.ParticipantId, context.RelationshipId, createKey, request, CancellationToken.None);
        var replayCreate = await context.Service.CreateAsync(
            context.TenantId, context.ParticipantId, context.RelationshipId, createKey, request, CancellationToken.None);
        Assert.False(firstCreate.Replayed);
        Assert.True(replayCreate.Replayed);
        Assert.Equal(firstCreate.Value.SessionId, replayCreate.Value.SessionId);

        var audio = Encoding.UTF8.GetBytes("bounded-webm-test-payload");
        var uploadKey = Guid.NewGuid();
        var firstUpload = await context.Service.UploadAsync(
            context.TenantId, context.ParticipantId, context.RelationshipId, firstCreate.Value.SessionId,
            uploadKey, new MemoryStream(audio), "audio/webm", CancellationToken.None);
        var replayUpload = await context.Service.UploadAsync(
            context.TenantId, context.ParticipantId, context.RelationshipId, firstCreate.Value.SessionId,
            uploadKey, new MemoryStream(audio), "audio/webm", CancellationToken.None);
        Assert.Equal("REVIEW_REQUIRED", firstUpload.Value.State);
        Assert.True(replayUpload.Replayed);
        Assert.Equal(1, context.Media.StoreCount);
        Assert.Equal(1, context.Transcription.CallCount);

        var correction = await context.Service.CorrectAsync(
            context.TenantId, context.ParticipantId, context.RelationshipId, firstCreate.Value.SessionId,
            Guid.NewGuid(), new VoiceCorrectionRequestV1("1.0.0", 1, "customer corrected text"), CancellationToken.None);
        Assert.Equal("READY_TO_SEND", correction.Value.State);
        Assert.Equal(2, correction.Value.Version);

        var sendKey = Guid.NewGuid();
        var firstSend = await context.Service.SendAsync(
            context.TenantId, context.ParticipantId, context.RelationshipId, firstCreate.Value.SessionId,
            sendKey, new SendVoiceContributionRequestV1("1.0.0", 2, true), CancellationToken.None);
        var replaySend = await context.Service.SendAsync(
            context.TenantId, context.ParticipantId, context.RelationshipId, firstCreate.Value.SessionId,
            sendKey, new SendVoiceContributionRequestV1("1.0.0", 2, true), CancellationToken.None);
        Assert.Equal("RECORDED", firstSend.Value.State);
        Assert.NotNull(firstSend.Value.EvidenceReference);
        Assert.True(replaySend.Replayed);
        Assert.Equal(1, context.Constitutional.CallCount);

        var erasure = await context.Service.EraseAsync(
            context.TenantId, context.ParticipantId, context.RelationshipId, firstSend.Value.ContributionId!.Value,
            Guid.NewGuid(), new VoicePayloadErasureRequestV1("1.0.0", "AUDIO_AND_TRANSCRIPT"), CancellationToken.None);
        Assert.Equal("COMPLETED", erasure.Value.Status);
        Assert.NotNull(erasure.Value.EvidenceReference);
        Assert.Equal(2, context.Constitutional.CallCount);
        Assert.Equal(1, context.Media.EraseCount);

        await using var db = context.VoiceFactory.CreateDbContext();
        Assert.Equal(2, await db.TranscriptVersions.CountAsync());
        Assert.All(await db.TranscriptVersions.ToListAsync(), value =>
        {
            Assert.Equal(string.Empty, value.TextCiphertext);
            Assert.NotNull(value.ErasedAt);
        });
        Assert.Single(await db.ErasureTombstones.ToListAsync());
        Assert.Equal(firstSend.Value.EvidenceReference, (await db.Sessions.SingleAsync()).EvidenceReference);
    }

    [Fact]
    public async Task CctVoiceTenant01_CrossTenantAndCrossParticipantRevealNothing()
    {
        var context = await CreateAsync();
        var created = await context.Service.CreateAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            Guid.NewGuid(),
            new CreateVoiceContributionSessionRequestV1("1.0.0", "en-IN"),
            CancellationToken.None);

        await Assert.ThrowsAsync<VoiceNotAccessibleException>(() => context.Service.GetAsync(
            Guid.NewGuid(), context.ParticipantId, context.RelationshipId, created.Value.SessionId, CancellationToken.None));
        await Assert.ThrowsAsync<VoiceNotAccessibleException>(() => context.Service.GetAsync(
            context.TenantId, Guid.NewGuid(), context.RelationshipId, created.Value.SessionId, CancellationToken.None));
    }

    [Fact]
    public async Task CctVoiceEf01_ExplicitSendAndCurrentVersionAreMandatory()
    {
        var context = await CreateAsync(confidence: 0.95m);
        var session = await CreateAndUploadAsync(context);
        await Assert.ThrowsAsync<VoiceRequestException>(() => context.Service.SendAsync(
            context.TenantId, context.ParticipantId, context.RelationshipId, session,
            Guid.NewGuid(), new SendVoiceContributionRequestV1("1.0.0", 1, false), CancellationToken.None));
        await Assert.ThrowsAsync<VoiceConflictException>(() => context.Service.SendAsync(
            context.TenantId, context.ParticipantId, context.RelationshipId, session,
            Guid.NewGuid(), new SendVoiceContributionRequestV1("1.0.0", 2, true), CancellationToken.None));
        Assert.Equal(0, context.Constitutional.CallCount);
    }

    [Fact]
    public async Task CancelErasesUnsentPayloadWithoutCreatingSendEvidence()
    {
        var context = await CreateAsync();
        var session = await CreateAndUploadAsync(context);
        var cancelled = await context.Service.CancelAsync(
            context.TenantId, context.ParticipantId, context.RelationshipId, session,
            Guid.NewGuid(), new CancelVoiceContributionRequestV1("1.0.0"), CancellationToken.None);
        Assert.Equal("CANCELLED", cancelled.Value.State);
        Assert.Equal(1, context.Media.EraseCount);
        Assert.Equal(0, context.Constitutional.CallCount);
    }

    private static async Task<Guid> CreateAndUploadAsync(TestContext context)
    {
        var created = await context.Service.CreateAsync(
            context.TenantId, context.ParticipantId, context.RelationshipId, Guid.NewGuid(),
            new CreateVoiceContributionSessionRequestV1("1.0.0", "en-IN"), CancellationToken.None);
        await context.Service.UploadAsync(
            context.TenantId, context.ParticipantId, context.RelationshipId, created.Value.SessionId,
            Guid.NewGuid(), new MemoryStream(Encoding.UTF8.GetBytes("audio")), "audio/webm", CancellationToken.None);
        return created.Value.SessionId;
    }

    private static async Task<TestContext> CreateAsync(decimal confidence = 0.75m)
    {
        var voiceFactory = new InMemoryVoiceFactory(Guid.NewGuid().ToString("N"));
        var relationshipFactory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var constitutional = new RecordingRelationshipConstitutionalGateway();
        var media = new VoiceMediaGatewayStub();
        var transcription = new VoiceTranscriptionGatewayStub(confidence);
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        await using (var db = relationshipFactory.CreateDbContext())
        {
            db.EmploymentRelationships.Add(new EmploymentRelationship
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ProfessionalType = "DMA",
                EvaluationIntentId = Guid.NewGuid(),
                InitiatingParticipantId = participantId,
                State = EmploymentRelationshipState.Active,
            });
            db.RelationshipParticipants.Add(new RelationshipParticipant
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ParticipantId = participantId,
                Role = RelationshipParticipantRole.Employer,
                BoundEvidenceId = Guid.NewGuid(),
            });
            await db.SaveChangesAsync();
        }
        var service = new VoiceContributionService(
            voiceFactory, relationshipFactory, constitutional, media, transcription, new TestVoiceContentProtector());
        return new(service, voiceFactory, constitutional, media, transcription, tenantId, relationshipId, participantId);
    }

    private sealed record TestContext(
        VoiceContributionService Service,
        InMemoryVoiceFactory VoiceFactory,
        RecordingRelationshipConstitutionalGateway Constitutional,
        VoiceMediaGatewayStub Media,
        VoiceTranscriptionGatewayStub Transcription,
        Guid TenantId,
        Guid RelationshipId,
        Guid ParticipantId);
}