// Implements: architecture/reference/components/wc062-voice-solution-contract.md § State And Sequence
// constitutional_basis: C-001, C-005, C-023, C-026, C-042, C-049, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record CreateVoiceContributionSessionRequestV1(string SchemaVersion, string Locale);
public sealed record VoiceContributionSessionV1(
    string SchemaVersion,
    Guid SessionId,
    Guid RelationshipId,
    string State,
    string Locale,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? ConfidenceBand,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] int? DurationSeconds,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] long? AudioSizeBytes,
    IReadOnlyList<string> AllowedCommands,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt);
public sealed record VoiceUploadReceiptV1(string SchemaVersion, Guid SessionId, string State, Guid ReceiptId, DateTimeOffset AcceptedAt);
public sealed record VoiceTranscriptV1(string SchemaVersion, Guid SessionId, string State, string Locale, string ConfidenceBand, string? Text, int Version);
public sealed record VoiceCorrectionRequestV1(string SchemaVersion, int ExpectedVersion, string CorrectedText);
public sealed record VoiceCorrectionReceiptV1(string SchemaVersion, Guid SessionId, string State, int Version, DateTimeOffset RecordedAt);
public sealed record SendVoiceContributionRequestV1(string SchemaVersion, int AcceptedTranscriptVersion, bool ExplicitSend);
public sealed record CancelVoiceContributionRequestV1(string SchemaVersion);
public sealed record VoiceContributionOutcomeV1(
    string SchemaVersion,
    Guid SessionId,
    Guid? ContributionId,
    string State,
    Guid? EvidenceReference,
    bool ReconciliationRequired,
    DateTimeOffset OutcomeAt);
public sealed record VoicePayloadErasureRequestV1(string SchemaVersion, string Scope);
public sealed record VoicePayloadErasureReceiptV1(
    string SchemaVersion,
    Guid ErasureId,
    Guid ContributionId,
    string Status,
    Guid? EvidenceReference,
    DateTimeOffset RecordedAt);

public sealed record VoiceMediaInspection(
    string ContentSha256,
    string DeclaredMediaType,
    string DetectedMediaType,
    long SizeBytes,
    int DurationMilliseconds,
    string PayloadReference);

public sealed record VoiceTranscriptionResult(string Text, string Locale, decimal Confidence, string ContractVersion);

public interface IVoiceMediaGateway
{
    Task<VoiceMediaInspection> ValidateScanAndStoreAsync(
        Stream audio,
        string declaredMediaType,
        Guid tenantId,
        Guid relationshipId,
        Guid sessionId,
        CancellationToken cancellationToken);

    Task EraseAsync(string payloadReference, CancellationToken cancellationToken);
}

public interface IVoiceTranscriptionGateway
{
    Task<VoiceTranscriptionResult> TranscribeAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid sessionId,
        VoiceMediaInspection inspection,
        string locale,
        CancellationToken cancellationToken);
}

public interface IVoiceContentProtector
{
    string Protect(string plaintext);
    string Unprotect(string ciphertext);
}

public sealed class UnconfiguredVoiceMediaGateway : IVoiceMediaGateway
{
    public Task<VoiceMediaInspection> ValidateScanAndStoreAsync(
        Stream audio,
        string declaredMediaType,
        Guid tenantId,
        Guid relationshipId,
        Guid sessionId,
        CancellationToken cancellationToken) =>
        throw new VoiceUnavailableException();

    public Task EraseAsync(string payloadReference, CancellationToken cancellationToken) =>
        throw new VoiceUnavailableException();
}

public sealed class UnconfiguredVoiceTranscriptionGateway : IVoiceTranscriptionGateway
{
    public Task<VoiceTranscriptionResult> TranscribeAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid sessionId,
        VoiceMediaInspection inspection,
        string locale,
        CancellationToken cancellationToken) =>
        throw new VoiceUnavailableException();
}

public sealed class AesVoiceContentProtector : IVoiceContentProtector
{
    private readonly byte[] _key;

    public AesVoiceContentProtector(IConfiguration configuration)
    {
        var configured = configuration["Voice:ContentEncryptionKey"];
        if (string.IsNullOrWhiteSpace(configured))
        {
            throw new InvalidOperationException("Voice:ContentEncryptionKey is required.");
        }

        _key = Convert.FromBase64String(configured);
        if (_key.Length != 32) throw new InvalidOperationException("Voice content key must be 256 bits.");
    }

    public string Protect(string plaintext)
    {
        var nonce = RandomNumberGenerator.GetBytes(12);
        var tag = new byte[16];
        var input = Encoding.UTF8.GetBytes(plaintext);
        var output = new byte[input.Length];
        using var aes = new AesGcm(_key, tag.Length);
        aes.Encrypt(nonce, input, output, tag);
        return Convert.ToBase64String(nonce.Concat(tag).Concat(output).ToArray());
    }

    public string Unprotect(string ciphertext)
    {
        var input = Convert.FromBase64String(ciphertext);
        if (input.Length < 29) throw new CryptographicException("Voice ciphertext is invalid.");
        var nonce = input[..12];
        var tag = input[12..28];
        var encrypted = input[28..];
        var output = new byte[encrypted.Length];
        using var aes = new AesGcm(_key, tag.Length);
        aes.Decrypt(nonce, encrypted, tag, output);
        return Encoding.UTF8.GetString(output);
    }
}

public sealed class VoiceRequestException(string message) : Exception(message);
public sealed class VoiceNotAccessibleException : Exception;
public sealed class VoiceConflictException(string message) : Exception(message);
public sealed class VoiceBlockedException(string message) : Exception(message);
public sealed class VoiceInvalidMediaException(string message) : Exception(message);
public sealed class VoiceLimitExceededException(string message) : Exception(message);
public sealed class VoiceUnavailableException : Exception;

public sealed class VoiceContributionService
{
    private const string SchemaVersion = "1.0.0";
    private static readonly HashSet<string> SupportedLocales = ["en-IN", "hi-IN", "mr-IN"];
    private static readonly HashSet<string> ErasureScopes = ["AUDIO", "TRANSCRIPT", "AUDIO_AND_TRANSCRIPT"];
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    private readonly IDbContextFactory<VoiceContributionDbContext> _voiceFactory;
    private readonly IDbContextFactory<EmploymentRelationshipDbContext> _relationshipFactory;
    private readonly IRelationshipConstitutionalGateway _constitutionalGateway;
    private readonly IVoiceMediaGateway _mediaGateway;
    private readonly IVoiceTranscriptionGateway _transcriptionGateway;
    private readonly IVoiceContentProtector _protector;

    public VoiceContributionService(
        IDbContextFactory<VoiceContributionDbContext> voiceFactory,
        IDbContextFactory<EmploymentRelationshipDbContext> relationshipFactory,
        IRelationshipConstitutionalGateway constitutionalGateway,
        IVoiceMediaGateway mediaGateway,
        IVoiceTranscriptionGateway transcriptionGateway,
        IVoiceContentProtector protector)
    {
        _voiceFactory = voiceFactory;
        _relationshipFactory = relationshipFactory;
        _constitutionalGateway = constitutionalGateway;
        _mediaGateway = mediaGateway;
        _transcriptionGateway = transcriptionGateway;
        _protector = protector;
    }

    public async Task<(VoiceContributionSessionV1 Value, bool Replayed)> CreateAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid idempotencyKey,
        CreateVoiceContributionSessionRequestV1 request,
        CancellationToken cancellationToken)
    {
        ValidateSchema(request.SchemaVersion);
        if (!SupportedLocales.Contains(request.Locale)) throw new VoiceRequestException("unsupported_language");
        await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        var hash = Hash(request);
        await using var db = await _voiceFactory.CreateDbContextAsync(cancellationToken);
        var replay = await FindReplayAsync(db, tenantId, relationshipId, participantId, null, "CREATE", idempotencyKey, hash, cancellationToken);
        if (replay is not null) return (Deserialize<VoiceContributionSessionV1>(replay.ResponseJson), true);

        var now = DateTimeOffset.UtcNow;
        var session = new VoiceContributionSession
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ActorParticipantId = participantId,
            SelectedLocale = request.Locale,
            ConsentVersion = "voice-consent-v1",
            CreatedAt = now,
            UpdatedAt = now,
            ExpiresAt = now.AddHours(24),
        };
        db.Sessions.Add(session);
        var response = ToSession(session, null, null);
        db.IdempotencyOutcomes.Add(NewOutcome(tenantId, relationshipId, participantId, session.SessionId, "CREATE", idempotencyKey, hash, response));
        await db.SaveChangesAsync(cancellationToken);
        return (response, false);
    }

    public async Task<VoiceContributionSessionV1> GetAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid sessionId,
        CancellationToken cancellationToken)
    {
        await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        await using var db = await _voiceFactory.CreateDbContextAsync(cancellationToken);
        var session = await GetSessionAsync(db, tenantId, participantId, relationshipId, sessionId, cancellationToken);
        var audio = await db.AudioPayloads.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.SessionId == sessionId, cancellationToken);
        var transcript = await CurrentTranscriptAsync(db, tenantId, sessionId, cancellationToken);
        return ToSession(session, audio, transcript);
    }

    public async Task<(VoiceUploadReceiptV1 Value, bool Replayed)> UploadAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid sessionId,
        Guid idempotencyKey,
        Stream audio,
        string declaredMediaType,
        CancellationToken cancellationToken)
    {
        await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        await using var db = await _voiceFactory.CreateDbContextAsync(cancellationToken);
        var session = await GetSessionAsync(db, tenantId, participantId, relationshipId, sessionId, cancellationToken);

        await using var boundedAudio = await ReadBoundedAsync(audio, cancellationToken);
        var requestHash = Convert.ToHexStringLower(SHA256.HashData(boundedAudio.ToArray()));
        var replay = await FindReplayAsync(
            db, tenantId, relationshipId, participantId, sessionId, "UPLOAD", idempotencyKey, requestHash, cancellationToken);
        if (replay is not null) return (Deserialize<VoiceUploadReceiptV1>(replay.ResponseJson), true);
        if (session.State != "CREATED") throw new VoiceConflictException("invalid_state");

        var inspection = await _mediaGateway.ValidateScanAndStoreAsync(
            boundedAudio, declaredMediaType, tenantId, relationshipId, sessionId, cancellationToken);
        if (inspection.SizeBytes > 15 * 1024 * 1024 || inspection.DurationMilliseconds > 180_000)
            throw new VoiceLimitExceededException("limit_exceeded");

        var now = DateTimeOffset.UtcNow;
        var payload = new VoiceAudioPayload
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            SessionId = sessionId,
            ContentSha256 = inspection.ContentSha256,
            DeclaredMediaType = inspection.DeclaredMediaType,
            DetectedMediaType = inspection.DetectedMediaType,
            SizeBytes = inspection.SizeBytes,
            DurationMilliseconds = inspection.DurationMilliseconds,
            ScanState = "CLEAN",
            PayloadReference = inspection.PayloadReference,
            CreatedAt = now,
            RetainUntil = now.AddHours(24),
        };
        db.AudioPayloads.Add(payload);
        session.State = "TRANSCRIBING";
        session.UpdatedAt = now;
        await db.SaveChangesAsync(cancellationToken);

        try
        {
            var result = await _transcriptionGateway.TranscribeAsync(
                tenantId, relationshipId, sessionId, inspection, session.SelectedLocale, cancellationToken);
            var band = ConfidenceBand(result.Confidence);
            var transcript = new VoiceTranscriptVersion
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                SessionId = sessionId,
                AudioPayloadId = payload.AudioPayloadId,
                Version = 1,
                Locale = result.Locale,
                LocaleSource = string.Equals(result.Locale, session.SelectedLocale, StringComparison.Ordinal) ? "DECLARED" : "DETECTED",
                Confidence = result.Confidence,
                ConfidenceBand = band,
                TextCiphertext = _protector.Protect(result.Text),
                TextSha256 = Sha256(result.Text),
                ContractVersion = result.ContractVersion,
            };
            db.TranscriptVersions.Add(transcript);
            session.CurrentTranscriptVersion = 1;
            session.AcceptedTranscriptId = band == "HIGH" ? transcript.TranscriptId : null;
            session.State = band == "HIGH" ? "READY_TO_SEND" : "REVIEW_REQUIRED";
        }
        catch (VoiceUnavailableException)
        {
            session.State = "UNAVAILABLE";
        }

        session.UpdatedAt = DateTimeOffset.UtcNow;
        var receipt = new VoiceUploadReceiptV1(SchemaVersion, sessionId, session.State, payload.AudioPayloadId, now);
        db.IdempotencyOutcomes.Add(NewOutcome(
            tenantId, relationshipId, participantId, sessionId, "UPLOAD", idempotencyKey, requestHash, receipt));
        await db.SaveChangesAsync(cancellationToken);
        return (receipt, false);
    }

    public async Task<VoiceTranscriptV1> GetTranscriptAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid sessionId,
        CancellationToken cancellationToken)
    {
        await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        await using var db = await _voiceFactory.CreateDbContextAsync(cancellationToken);
        var session = await GetSessionAsync(db, tenantId, participantId, relationshipId, sessionId, cancellationToken);
        var transcript = await CurrentTranscriptAsync(db, tenantId, sessionId, cancellationToken)
            ?? throw new VoiceConflictException("transcript_not_ready");
        return new VoiceTranscriptV1(
            SchemaVersion,
            sessionId,
            session.State,
            transcript.Locale,
            transcript.ConfidenceBand,
            transcript.ErasedAt is null ? _protector.Unprotect(transcript.TextCiphertext) : null,
            transcript.Version);
    }

    public async Task<(VoiceCorrectionReceiptV1 Value, bool Replayed)> CorrectAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid sessionId,
        Guid idempotencyKey,
        VoiceCorrectionRequestV1 request,
        CancellationToken cancellationToken)
    {
        ValidateSchema(request.SchemaVersion);
        if (string.IsNullOrWhiteSpace(request.CorrectedText) || request.CorrectedText.Length > 20_000)
            throw new VoiceRequestException("corrected_text_invalid");
        await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        await using var db = await _voiceFactory.CreateDbContextAsync(cancellationToken);
        var session = await GetSessionAsync(db, tenantId, participantId, relationshipId, sessionId, cancellationToken);
        if (session.State is not ("REVIEW_REQUIRED" or "READY_TO_SEND")) throw new VoiceConflictException("invalid_state");
        var hash = Hash(request);
        var replay = await FindReplayAsync(db, tenantId, relationshipId, participantId, sessionId, "CORRECT", idempotencyKey, hash, cancellationToken);
        if (replay is not null) return (Deserialize<VoiceCorrectionReceiptV1>(replay.ResponseJson), true);
        var current = await CurrentTranscriptAsync(db, tenantId, sessionId, cancellationToken)
            ?? throw new VoiceConflictException("transcript_not_ready");
        if (request.ExpectedVersion != current.Version) throw new VoiceConflictException("stale_version");

        var now = DateTimeOffset.UtcNow;
        var correction = new VoiceTranscriptVersion
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            SessionId = sessionId,
            AudioPayloadId = current.AudioPayloadId,
            Version = current.Version + 1,
            PredecessorTranscriptId = current.TranscriptId,
            Source = "CUSTOMER_CORRECTION",
            Locale = current.Locale,
            LocaleSource = current.LocaleSource,
            Confidence = current.Confidence,
            ConfidenceBand = "HIGH",
            TextCiphertext = _protector.Protect(request.CorrectedText.Trim()),
            TextSha256 = Sha256(request.CorrectedText.Trim()),
            ContractVersion = current.ContractVersion,
            CreatedAt = now,
        };
        db.TranscriptVersions.Add(correction);
        session.CurrentTranscriptVersion = correction.Version;
        session.AcceptedTranscriptId = correction.TranscriptId;
        session.State = "READY_TO_SEND";
        session.UpdatedAt = now;
        var receipt = new VoiceCorrectionReceiptV1(SchemaVersion, sessionId, session.State, correction.Version, now);
        db.IdempotencyOutcomes.Add(NewOutcome(tenantId, relationshipId, participantId, sessionId, "CORRECT", idempotencyKey, hash, receipt));
        await db.SaveChangesAsync(cancellationToken);
        return (receipt, false);
    }

    public async Task<(VoiceContributionOutcomeV1 Value, bool Replayed)> SendAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid sessionId,
        Guid idempotencyKey,
        SendVoiceContributionRequestV1 request,
        CancellationToken cancellationToken)
    {
        ValidateSchema(request.SchemaVersion);
        if (!request.ExplicitSend) throw new VoiceRequestException("consent_required");
        var relationship = await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        await using var db = await _voiceFactory.CreateDbContextAsync(cancellationToken);
        var session = await GetSessionAsync(db, tenantId, participantId, relationshipId, sessionId, cancellationToken);
        var hash = Hash(request);
        var replay = await FindReplayAsync(db, tenantId, relationshipId, participantId, sessionId, "SEND", idempotencyKey, hash, cancellationToken);
        if (replay is not null) return (Deserialize<VoiceContributionOutcomeV1>(replay.ResponseJson), true);
        if (session.State != "READY_TO_SEND" || request.AcceptedTranscriptVersion != session.CurrentTranscriptVersion)
            throw new VoiceConflictException("stale_version");
        var transcript = await CurrentTranscriptAsync(db, tenantId, sessionId, cancellationToken)
            ?? throw new VoiceConflictException("transcript_not_ready");
        var audio = await db.AudioPayloads.SingleAsync(
            value => value.TenantId == tenantId && value.SessionId == sessionId, cancellationToken);

        session.State = "SENDING";
        session.UpdatedAt = DateTimeOffset.UtcNow;
        var contributionId = Guid.NewGuid();
        var evidenceId = await _constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "VOICE_CONTRIBUTION_SEND",
            contributionId,
            new
            {
                sessionId,
                contributionId,
                transcript.Version,
                transcript.TextSha256,
                audio.ContentSha256,
                locale = transcript.Locale,
                explicitSend = true,
            },
            cancellationToken);
        var now = DateTimeOffset.UtcNow;
        session.ContributionId = contributionId;
        session.EvidenceReference = evidenceId;
        session.State = "RECORDED";
        session.UpdatedAt = now;
        audio.RetainUntil = now.AddDays(30);
        var outcome = new VoiceContributionOutcomeV1(SchemaVersion, sessionId, contributionId, "RECORDED", evidenceId, false, now);
        db.IdempotencyOutcomes.Add(NewOutcome(tenantId, relationshipId, participantId, sessionId, "SEND", idempotencyKey, hash, outcome));
        await db.SaveChangesAsync(cancellationToken);
        return (outcome, false);
    }

    public async Task<(VoiceContributionOutcomeV1 Value, bool Replayed)> CancelAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid sessionId,
        Guid idempotencyKey,
        CancelVoiceContributionRequestV1 request,
        CancellationToken cancellationToken)
    {
        ValidateSchema(request.SchemaVersion);
        await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        await using var db = await _voiceFactory.CreateDbContextAsync(cancellationToken);
        var session = await GetSessionAsync(db, tenantId, participantId, relationshipId, sessionId, cancellationToken);
        var hash = Hash(request);
        var replay = await FindReplayAsync(db, tenantId, relationshipId, participantId, sessionId, "CANCEL", idempotencyKey, hash, cancellationToken);
        if (replay is not null) return (Deserialize<VoiceContributionOutcomeV1>(replay.ResponseJson), true);
        if (session.State == "RECORDED") throw new VoiceConflictException("already_recorded");
        session.State = "CANCELLED";
        session.UpdatedAt = DateTimeOffset.UtcNow;
        var audio = await db.AudioPayloads.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.SessionId == sessionId, cancellationToken);
        if (audio?.PayloadReference is not null)
        {
            await _mediaGateway.EraseAsync(audio.PayloadReference, cancellationToken);
            audio.PayloadReference = null;
            audio.ErasedAt = session.UpdatedAt;
        }
        var outcome = new VoiceContributionOutcomeV1(SchemaVersion, sessionId, null, "CANCELLED", null, false, session.UpdatedAt);
        db.IdempotencyOutcomes.Add(NewOutcome(tenantId, relationshipId, participantId, sessionId, "CANCEL", idempotencyKey, hash, outcome));
        await db.SaveChangesAsync(cancellationToken);
        return (outcome, false);
    }

    public async Task<(VoicePayloadErasureReceiptV1 Value, bool Replayed)> EraseAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid contributionId,
        Guid idempotencyKey,
        VoicePayloadErasureRequestV1 request,
        CancellationToken cancellationToken)
    {
        ValidateSchema(request.SchemaVersion);
        if (!ErasureScopes.Contains(request.Scope)) throw new VoiceRequestException("scope_invalid");
        var relationship = await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        await using var db = await _voiceFactory.CreateDbContextAsync(cancellationToken);
        var session = await db.Sessions.SingleOrDefaultAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ActorParticipantId == participantId
                && value.ContributionId == contributionId,
            cancellationToken) ?? throw new VoiceNotAccessibleException();
        var hash = Hash(request);
        var replay = await FindReplayAsync(db, tenantId, relationshipId, participantId, session.SessionId, "ERASE", idempotencyKey, hash, cancellationToken);
        if (replay is not null) return (Deserialize<VoicePayloadErasureReceiptV1>(replay.ResponseJson), true);

        var erasureId = Guid.NewGuid();
        var evidenceId = await _constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "VOICE_PAYLOAD_ERASURE",
            erasureId,
            new { contributionId, request.Scope },
            cancellationToken);
        var now = DateTimeOffset.UtcNow;
        if (request.Scope is "AUDIO" or "AUDIO_AND_TRANSCRIPT")
        {
            var audio = await db.AudioPayloads.SingleOrDefaultAsync(
                value => value.TenantId == tenantId && value.SessionId == session.SessionId, cancellationToken);
            if (audio?.PayloadReference is not null) await _mediaGateway.EraseAsync(audio.PayloadReference, cancellationToken);
            if (audio is not null)
            {
                audio.PayloadReference = null;
                audio.ErasedAt = now;
            }
        }
        if (request.Scope is "TRANSCRIPT" or "AUDIO_AND_TRANSCRIPT")
        {
            var transcripts = await db.TranscriptVersions.Where(
                value => value.TenantId == tenantId && value.SessionId == session.SessionId).ToListAsync(cancellationToken);
            foreach (var transcript in transcripts)
            {
                transcript.TextCiphertext = string.Empty;
                transcript.ErasedAt = now;
            }
        }
        db.ErasureTombstones.Add(new VoiceErasureTombstone
        {
            TombstoneId = erasureId,
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ContributionId = contributionId,
            ActorParticipantId = participantId,
            Scope = request.Scope,
            ReasonClass = "CUSTOMER_REQUEST",
            EvidenceReference = evidenceId,
            ErasedAt = now,
        });
        var receipt = new VoicePayloadErasureReceiptV1(SchemaVersion, erasureId, contributionId, "COMPLETED", evidenceId, now);
        db.IdempotencyOutcomes.Add(NewOutcome(tenantId, relationshipId, participantId, session.SessionId, "ERASE", idempotencyKey, hash, receipt));
        await db.SaveChangesAsync(cancellationToken);
        return (receipt, false);
    }

    private async Task<EmploymentRelationship> EnsureAccessAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        CancellationToken cancellationToken)
    {
        await using var db = await _relationshipFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId, cancellationToken);
        if (relationship is null || relationship.State is EmploymentRelationshipState.StoppedEmergency or EmploymentRelationshipState.Terminated)
            throw new VoiceNotAccessibleException();
        var authorized = await db.RelationshipParticipants.AsNoTracking().AnyAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == participantId
                && value.Status == "ACTIVE",
            cancellationToken);
        if (!authorized) throw new VoiceNotAccessibleException();
        return relationship;
    }

    private static async Task<VoiceContributionSession> GetSessionAsync(
        VoiceContributionDbContext db,
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid sessionId,
        CancellationToken cancellationToken) =>
        await db.Sessions.SingleOrDefaultAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ActorParticipantId == participantId
                && value.SessionId == sessionId,
            cancellationToken) ?? throw new VoiceNotAccessibleException();

    private static Task<VoiceTranscriptVersion?> CurrentTranscriptAsync(
        VoiceContributionDbContext db,
        Guid tenantId,
        Guid sessionId,
        CancellationToken cancellationToken) =>
        db.TranscriptVersions.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.SessionId == sessionId)
            .OrderByDescending(value => value.Version)
            .FirstOrDefaultAsync(cancellationToken);

    private static async Task<VoiceIdempotencyOutcome?> FindReplayAsync(
        VoiceContributionDbContext db,
        Guid tenantId,
        Guid relationshipId,
        Guid participantId,
        Guid? sessionId,
        string operation,
        Guid idempotencyKey,
        string requestHash,
        CancellationToken cancellationToken)
    {
        var replay = await db.IdempotencyOutcomes.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ActorParticipantId == participantId
                && value.Operation == operation
                && value.IdempotencyKey == idempotencyKey,
            cancellationToken);
        if (replay is not null
            && ((sessionId is not null && replay.SessionId != sessionId) || replay.RequestSha256 != requestHash))
            throw new VoiceConflictException("idempotency_conflict");
        return replay;
    }

    private static VoiceIdempotencyOutcome NewOutcome<T>(
        Guid tenantId,
        Guid relationshipId,
        Guid participantId,
        Guid? sessionId,
        string operation,
        Guid idempotencyKey,
        string requestHash,
        T response) => new()
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ActorParticipantId = participantId,
            SessionId = sessionId,
            Operation = operation,
            IdempotencyKey = idempotencyKey,
            RequestSha256 = requestHash,
            ResponseJson = JsonSerializer.Serialize(response, JsonOptions),
        };

    private static VoiceContributionSessionV1 ToSession(
        VoiceContributionSession session,
        VoiceAudioPayload? audio,
        VoiceTranscriptVersion? transcript) => new(
        SchemaVersion,
        session.SessionId,
        session.RelationshipId,
        session.State,
        session.SelectedLocale,
        transcript?.ConfidenceBand,
        audio is null ? null : audio.DurationMilliseconds / 1000,
        audio?.SizeBytes,
        AllowedCommands(session.State),
        session.CreatedAt,
        session.UpdatedAt);

    private static IReadOnlyList<string> AllowedCommands(string state) => state switch
    {
        "CREATED" => ["UPLOAD", "CANCEL", "SWITCH_TO_TEXT"],
        "REVIEW_REQUIRED" => ["REVIEW_TRANSCRIPT", "SUBMIT_CORRECTION", "CANCEL", "SWITCH_TO_TEXT"],
        "READY_TO_SEND" => ["REVIEW_TRANSCRIPT", "SUBMIT_CORRECTION", "SEND", "CANCEL", "SWITCH_TO_TEXT"],
        "UNAVAILABLE" or "UNKNOWN" => ["RETRY", "CANCEL", "SWITCH_TO_TEXT"],
        "RECORDED" => ["REQUEST_ERASURE"],
        _ => [],
    };

    private static string ConfidenceBand(decimal confidence) => confidence >= 0.90m ? "HIGH" : confidence >= 0.70m ? "REVIEW" : "LOW";
    private static async Task<MemoryStream> ReadBoundedAsync(Stream source, CancellationToken cancellationToken)
    {
        const int maximumBytes = 15 * 1024 * 1024;
        var target = new MemoryStream();
        var buffer = new byte[81920];
        while (true)
        {
            var read = await source.ReadAsync(buffer, cancellationToken);
            if (read == 0) break;
            if (target.Length + read > maximumBytes) throw new VoiceLimitExceededException("limit_exceeded");
            await target.WriteAsync(buffer.AsMemory(0, read), cancellationToken);
        }
        target.Position = 0;
        return target;
    }

    private static string Hash<T>(T value) => Sha256(JsonSerializer.Serialize(value, JsonOptions));
    private static string Sha256(string value) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
    private static T Deserialize<T>(string value) => JsonSerializer.Deserialize<T>(value, JsonOptions)
        ?? throw new InvalidOperationException("Stored voice outcome is invalid.");
    private static void ValidateSchema(string schemaVersion)
    {
        if (schemaVersion != SchemaVersion) throw new VoiceRequestException("contract_mismatch");
    }
}