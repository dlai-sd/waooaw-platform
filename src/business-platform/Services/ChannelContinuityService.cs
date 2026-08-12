// Implements: work-contracts/WC-060-goal005-ae01-continuity-evidence-stop.md WC060-03
// constitutional_basis: C-005, C-023, C-026, C-059

using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record ChannelContinuityIdentity(
    Guid ParticipantId,
    string Channel,
    string ConversationId,
    string ExternalSubjectHash,
    string AuthenticationAssurance,
    DateTimeOffset AuthenticatedAt);

public sealed record PrepareChannelHandoff(
    string TargetChannel,
    string TargetConversationId,
    string CommandPurpose,
    Guid CorrelationId,
    Guid IdempotencyKey);

public sealed record ActivateChannelHandoff(
    string TargetConversationId,
    Guid CorrelationId,
    Guid IdempotencyKey,
    NeutralContinuityEnvelope Envelope);

public sealed record NeutralContinuityEnvelope(
    string SchemaVersion,
    Guid TenantId,
    Guid RelationshipId,
    Guid ParticipantId,
    string ParticipantRole,
    string AuthenticationAssurance,
    Guid AuthoritySnapshotId,
    string SourceChannel,
    string SourceConversationId,
    string TargetChannel,
    string TargetConversationId,
    string CommandPurpose,
    Guid CorrelationId,
    Guid CausalMarker,
    long SequenceNumber,
    Guid IdempotencyKey,
    Guid EvidenceCommitmentId,
    Guid ContinuityCheckpointId,
    DateTimeOffset IssuedAt,
    string IntegritySignature);

public sealed record ChannelHandoffResult(
    Guid HandoffId,
    Guid RelationshipId,
    string Status,
    ChannelBinding SourceBinding,
    ChannelBinding TargetBinding,
    NeutralContinuityEnvelope ContinuityEnvelope,
    bool Replayed,
    Guid? ResolutionEvidenceId = null,
    DateTimeOffset? CommittedAt = null);

public sealed class ChannelContinuityConflictException(string message) : Exception(message);
public sealed class ChannelContinuityLockedException(string message) : Exception(message);

public sealed class ChannelContinuityOptions
{
    public string EnvelopeHmacKey { get; set; } = string.Empty;
}

public sealed class ChannelContinuityService
{
    private static readonly TimeSpan FreshAuthenticationWindow = TimeSpan.FromMinutes(5);
    private readonly IDbContextFactory<EmploymentRelationshipDbContext> _dbFactory;
    private readonly IRelationshipConstitutionalGateway _constitutionalGateway;
    private readonly byte[] _hmacKey;

    public ChannelContinuityService(
        IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
        IRelationshipConstitutionalGateway constitutionalGateway,
        Microsoft.Extensions.Options.IOptions<ChannelContinuityOptions> options)
    {
        _dbFactory = dbFactory;
        _constitutionalGateway = constitutionalGateway;
        _hmacKey = Convert.FromBase64String(options.Value.EnvelopeHmacKey);
        if (_hmacKey.Length < 32)
        {
            throw new InvalidOperationException("Continuity envelope HMAC key must contain at least 256 bits.");
        }
    }

    public async Task<ChannelHandoffResult> PrepareAsync(
        Guid tenantId,
        Guid relationshipId,
        ChannelContinuityIdentity sourceIdentity,
        PrepareChannelHandoff request,
        CancellationToken cancellationToken)
    {
        ValidateChannel(request.TargetChannel);
        ValidateText(request.TargetConversationId, 256, nameof(request.TargetConversationId));
        ValidateText(request.CommandPurpose, 64, nameof(request.CommandPurpose));

        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken) ?? throw new KeyNotFoundException("Employment relationship was not found.");
        EnsureNotStopped(relationship);

        var participant = await db.RelationshipParticipants.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == sourceIdentity.ParticipantId
                && value.Status == "ACTIVE",
            cancellationToken) ?? throw new ConstitutionalActionDeniedException(
                "Handoff requires an active same-tenant participant binding.");
        var sourceBinding = await db.ChannelBindings.SingleOrDefaultAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == sourceIdentity.ParticipantId
                && value.Channel == sourceIdentity.Channel
                && value.ConversationId == sourceIdentity.ConversationId
                && value.Status == "ACTIVE",
            cancellationToken) ?? throw new ConstitutionalActionDeniedException(
                "Authenticated source channel is not actively bound to this relationship.");

        var materialHash = HashMaterial(request.TargetChannel, request.TargetConversationId, request.CommandPurpose);
        var replay = await db.ContinuityCheckpoints.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.IdempotencyKey == request.IdempotencyKey,
            cancellationToken);
        if (replay is not null)
        {
            if (!CryptographicOperations.FixedTimeEquals(
                    Convert.FromHexString(replay.MaterialRequestHash), Convert.FromHexString(materialHash)))
            {
                throw new ChannelContinuityConflictException("Idempotency key was reused with divergent handoff material.");
            }

            return await LoadResultAsync(db, replay, true, cancellationToken);
        }

        var authoritySnapshotId = relationship.AuthoritySnapshotId
            ?? throw new ConstitutionalActionDeniedException("Current relationship authority is unresolved.");
        var checkpointId = Guid.NewGuid();
        var targetBindingId = Guid.NewGuid();
        var causalMarker = Guid.NewGuid();
        var sequenceNumber = (await db.ContinuityCheckpoints
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .MaxAsync(value => (long?)value.SequenceNumber, cancellationToken) ?? 0) + 1;
        var preparedAt = DateTimeOffset.UtcNow;
        var evidenceId = await _constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "PREPARE_CHANNEL_HANDOFF",
            request.CorrelationId,
            new
            {
                participant_id = sourceIdentity.ParticipantId,
                participant_role = RelationshipRoleCodec.ToDatabase(participant.Role),
                source_binding_id = sourceBinding.BindingId,
                target_binding_id = targetBindingId,
                target_channel = request.TargetChannel,
                command_purpose = request.CommandPurpose,
                idempotency_key = request.IdempotencyKey,
            },
            cancellationToken);

        var unsignedEnvelope = new NeutralContinuityEnvelope(
            "1.0.0", tenantId, relationshipId, sourceIdentity.ParticipantId,
            RelationshipRoleCodec.ToDatabase(participant.Role), sourceIdentity.AuthenticationAssurance,
            authoritySnapshotId, sourceIdentity.Channel, sourceIdentity.ConversationId,
            request.TargetChannel, request.TargetConversationId, request.CommandPurpose,
            request.CorrelationId, causalMarker, sequenceNumber, request.IdempotencyKey,
            evidenceId, checkpointId, preparedAt, string.Empty);
        var envelope = unsignedEnvelope with { IntegritySignature = Sign(unsignedEnvelope) };
        var targetBinding = new ChannelBinding
        {
            BindingId = targetBindingId,
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ParticipantId = sourceIdentity.ParticipantId,
            ParticipantRole = RelationshipRoleCodec.ToDatabase(participant.Role),
            Channel = request.TargetChannel,
            ExternalSubjectHash = HashText(request.TargetConversationId),
            ConversationId = request.TargetConversationId,
            AssuranceLevel = sourceIdentity.AuthenticationAssurance,
            PreparedEvidenceId = evidenceId,
            CreatedAt = preparedAt,
        };
        var checkpoint = new ContinuityCheckpoint
        {
            CheckpointId = checkpointId,
            TenantId = tenantId,
            RelationshipId = relationshipId,
            SourceBindingId = sourceBinding.BindingId,
            TargetBindingId = targetBindingId,
            ContinuityEnvelopeHash = HashText(Canonicalize(unsignedEnvelope)),
            ContinuityEnvelopeJson = JsonSerializer.Serialize(envelope, new JsonSerializerOptions(JsonSerializerDefaults.Web)),
            MaterialRequestHash = materialHash,
            CausalMarker = causalMarker,
            SequenceNumber = sequenceNumber,
            IdempotencyKey = request.IdempotencyKey,
            PreparedEvidenceId = evidenceId,
            PreparedAt = preparedAt,
            ExpiresAt = preparedAt.AddMinutes(15),
        };
        db.ChannelBindings.Add(targetBinding);
        db.ContinuityCheckpoints.Add(checkpoint);
        await db.SaveChangesAsync(cancellationToken);
        return new ChannelHandoffResult(
            checkpointId, relationshipId, checkpoint.Status, sourceBinding, targetBinding, envelope, false);
    }

    public async Task<ChannelHandoffResult> ActivateAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid handoffId,
        ChannelContinuityIdentity targetIdentity,
        ActivateChannelHandoff request,
        CancellationToken cancellationToken)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken) ?? throw new KeyNotFoundException("Employment relationship was not found.");
        EnsureNotStopped(relationship);
        var checkpoint = await db.ContinuityCheckpoints.SingleOrDefaultAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.CheckpointId == handoffId,
            cancellationToken) ?? throw new KeyNotFoundException("Channel handoff was not found.");

        if (checkpoint.Status == "COMMITTED")
        {
            return await LoadResultAsync(db, checkpoint, true, cancellationToken);
        }
        if (checkpoint.Status != "PREPARED")
        {
            throw new ChannelContinuityConflictException("Channel handoff is already terminal.");
        }
        if (checkpoint.ExpiresAt <= DateTimeOffset.UtcNow)
        {
            throw new ChannelContinuityConflictException("Channel handoff has expired.");
        }
        if (!Verify(request.Envelope)
            || request.Envelope.ContinuityCheckpointId != handoffId
            || request.Envelope.TenantId != tenantId
            || request.Envelope.RelationshipId != relationshipId
            || request.Envelope.IdempotencyKey != request.IdempotencyKey
            || !CryptographicOperations.FixedTimeEquals(
                Convert.FromHexString(checkpoint.ContinuityEnvelopeHash),
                Convert.FromHexString(HashText(Canonicalize(request.Envelope with { IntegritySignature = string.Empty })))))
        {
            throw new ConstitutionalActionDeniedException("Continuity envelope verification failed.");
        }

        var targetBinding = await db.ChannelBindings.SingleAsync(
            value => value.TenantId == tenantId && value.BindingId == checkpoint.TargetBindingId,
            cancellationToken);
        var sourceBinding = await db.ChannelBindings.SingleAsync(
            value => value.TenantId == tenantId && value.BindingId == checkpoint.SourceBindingId,
            cancellationToken);
        if (targetIdentity.ParticipantId != request.Envelope.ParticipantId
            || targetIdentity.ConversationId != request.TargetConversationId
            || targetIdentity.ConversationId != targetBinding.ConversationId
            || targetIdentity.Channel != targetBinding.Channel
            || DateTimeOffset.UtcNow - targetIdentity.AuthenticatedAt > FreshAuthenticationWindow)
        {
            throw new ConstitutionalActionDeniedException("Fresh target-channel authentication does not match the prepared handoff.");
        }
        var hasCurrentRole = await db.RelationshipParticipants.AsNoTracking().AnyAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == targetIdentity.ParticipantId
                && value.Status == "ACTIVE"
                && RelationshipRoleCodec.ToDatabase(value.Role) == request.Envelope.ParticipantRole,
            cancellationToken);
        if (!hasCurrentRole || relationship.AuthoritySnapshotId != request.Envelope.AuthoritySnapshotId)
        {
            throw new ConstitutionalActionDeniedException("Participant role or relationship authority changed during handoff.");
        }

        var evidenceId = await _constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "ACTIVATE_CHANNEL_HANDOFF",
            request.CorrelationId,
            new
            {
                checkpoint_id = checkpoint.CheckpointId,
                source_binding_id = sourceBinding.BindingId,
                target_binding_id = targetBinding.BindingId,
                target_assurance = targetIdentity.AuthenticationAssurance,
            },
            cancellationToken);

        var committedAt = DateTimeOffset.UtcNow;
        targetBinding.Status = "ACTIVE";
        targetBinding.BoundEvidenceId = evidenceId;
        targetBinding.BoundAt = committedAt;
        checkpoint.Status = "COMMITTED";
        checkpoint.ResolutionEvidenceId = evidenceId;
        checkpoint.ResolvedAt = committedAt;
        await db.SaveChangesAsync(cancellationToken);
        return new ChannelHandoffResult(
            checkpoint.CheckpointId, relationshipId, checkpoint.Status, sourceBinding, targetBinding,
            request.Envelope, false, evidenceId, committedAt);
    }

    private async Task<ChannelHandoffResult> LoadResultAsync(
        EmploymentRelationshipDbContext db,
        ContinuityCheckpoint checkpoint,
        bool replayed,
        CancellationToken cancellationToken)
    {
        var source = await db.ChannelBindings.AsNoTracking().SingleAsync(
            value => value.TenantId == checkpoint.TenantId && value.BindingId == checkpoint.SourceBindingId,
            cancellationToken);
        var target = await db.ChannelBindings.AsNoTracking().SingleAsync(
            value => value.TenantId == checkpoint.TenantId && value.BindingId == checkpoint.TargetBindingId,
            cancellationToken);
        var envelope = checkpoint.ContinuityEnvelopeJson is null
            ? throw new InvalidOperationException("Persisted continuity envelope is unavailable.")
            : JsonSerializer.Deserialize<NeutralContinuityEnvelope>(
                checkpoint.ContinuityEnvelopeJson, new JsonSerializerOptions(JsonSerializerDefaults.Web))
                ?? throw new InvalidOperationException("Persisted continuity envelope is invalid.");
        return new ChannelHandoffResult(
            checkpoint.CheckpointId, checkpoint.RelationshipId, checkpoint.Status, source, target,
            envelope, replayed, checkpoint.ResolutionEvidenceId, checkpoint.ResolvedAt);
    }

    private string Sign(NeutralContinuityEnvelope envelope)
    {
        using var hmac = new HMACSHA256(_hmacKey);
        return Base64Url(hmac.ComputeHash(Encoding.UTF8.GetBytes(Canonicalize(envelope))));
    }

    private bool Verify(NeutralContinuityEnvelope envelope)
    {
        var supplied = Encoding.ASCII.GetBytes(envelope.IntegritySignature);
        var expected = Encoding.ASCII.GetBytes(Sign(envelope with { IntegritySignature = string.Empty }));
        return supplied.Length == expected.Length && CryptographicOperations.FixedTimeEquals(supplied, expected);
    }

    private static string Canonicalize(NeutralContinuityEnvelope envelope)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream, new JsonWriterOptions
        {
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
            Indented = false,
        }))
        {
            writer.WriteStartObject();
            writer.WriteString("authenticationAssurance", envelope.AuthenticationAssurance);
            writer.WriteString("authoritySnapshotId", envelope.AuthoritySnapshotId);
            writer.WriteString("causalMarker", envelope.CausalMarker);
            writer.WriteString("commandPurpose", envelope.CommandPurpose);
            writer.WriteString("continuityCheckpointId", envelope.ContinuityCheckpointId);
            writer.WriteString("correlationId", envelope.CorrelationId);
            writer.WriteString("evidenceCommitmentId", envelope.EvidenceCommitmentId);
            writer.WriteString("idempotencyKey", envelope.IdempotencyKey);
            writer.WriteString("issuedAt", envelope.IssuedAt.UtcDateTime.ToString("O"));
            writer.WriteString("participantId", envelope.ParticipantId);
            writer.WriteString("participantRole", envelope.ParticipantRole);
            writer.WriteString("relationshipId", envelope.RelationshipId);
            writer.WriteString("schemaVersion", envelope.SchemaVersion);
            writer.WriteNumber("sequenceNumber", envelope.SequenceNumber);
            writer.WriteString("sourceChannel", envelope.SourceChannel);
            writer.WriteString("sourceConversationId", envelope.SourceConversationId);
            writer.WriteString("targetChannel", envelope.TargetChannel);
            writer.WriteString("targetConversationId", envelope.TargetConversationId);
            writer.WriteString("tenantId", envelope.TenantId);
            writer.WriteEndObject();
        }
        return Encoding.UTF8.GetString(stream.ToArray());
    }

    private static string HashMaterial(params string[] values) => HashText(string.Join('\u001f', values));
    private static string HashText(string value) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
    private static string Base64Url(byte[] value) => Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');

    private static void ValidateChannel(string channel)
    {
        if (channel is not ("WHATSAPP" or "WEB")) throw new ArgumentException("Unsupported relationship channel.");
    }

    private static void ValidateText(string value, int maximumLength, string name)
    {
        if (string.IsNullOrWhiteSpace(value) || value.Length > maximumLength)
            throw new ArgumentException($"{name} must contain 1 to {maximumLength} characters.", name);
    }

    private static void EnsureNotStopped(EmploymentRelationship relationship)
    {
        if (relationship.State == EmploymentRelationshipState.StoppedEmergency)
            throw new ChannelContinuityLockedException("Relationship is stopped; channel handoff is locked.");
    }
}