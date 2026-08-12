// Implements: work-contracts/WC-060-goal005-ae01-continuity-evidence-stop.md WC060-05
// constitutional_basis: C-005, C-023, C-026, C-059, C-063

using Grpc.Core;
using Grpc.Net.Client;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Nodes;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.BusinessPlatform.Services;

public sealed record RelationshipEvidenceDetail(
    Guid EvidenceId,
    string Subject,
    string State,
    string PayloadState,
    Guid? PayloadReference,
    DateTimeOffset? ErasedAt,
    string EvidenceHash,
    DateTimeOffset RecordedAt);

public sealed record RelationshipEvidenceExportResult(
    Guid ExportId,
    string Status,
    DateTimeOffset AcceptedAt,
    DateTimeOffset ExpiresAt,
    string DownloadUrl,
    string DocumentSha256,
    string DocumentJson,
    bool Replayed);

public sealed class RelationshipEvidenceExportOptions
{
    public string DownloadBaseUrl { get; set; } = "https://api.waooaw.com";
    public string SigningKey { get; set; } = string.Empty;
}

public interface IRelationshipEvidenceGateway
{
    Task<IReadOnlyList<CustomerVisibleEvidenceRecord>> QueryAsync(
        Guid tenantId, IReadOnlyCollection<Guid> evidenceIds, CancellationToken cancellationToken);
}

public sealed class GrpcRelationshipEvidenceGateway(IConfiguration configuration) : IRelationshipEvidenceGateway
{
    public async Task<IReadOnlyList<CustomerVisibleEvidenceRecord>> QueryAsync(
        Guid tenantId, IReadOnlyCollection<Guid> evidenceIds, CancellationToken cancellationToken)
    {
        var endpoint = configuration["ConstitutionalEngine:GrpcUrl"]
            ?? throw new InvalidOperationException("ConstitutionalEngine:GrpcUrl is not configured.");
        using var channel = GrpcChannel.ForAddress(endpoint);
        var client = new ConstitutionalService.ConstitutionalServiceClient(channel);
        var request = new QueryEvidenceRecordsRequest { PageSize = 100 };
        request.EvidenceRecordIds.AddRange(evidenceIds.Select(value => value.ToString("D")));
        var response = await client.QueryEvidenceRecordsAsync(
            request,
            new Metadata { { "x-tenant-id", tenantId.ToString("D") } },
            cancellationToken: cancellationToken);
        return response.Records;
    }
}

public sealed class RelationshipEvidenceService
{
    private readonly IDbContextFactory<EmploymentRelationshipDbContext> _dbFactory;
    private readonly IRelationshipEvidenceGateway _gateway;
    private readonly IRelationshipConstitutionalGateway? _constitutionalGateway;
    private readonly RelationshipEvidenceExportOptions _options;

    public RelationshipEvidenceService(
        IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
        IRelationshipEvidenceGateway gateway,
        IRelationshipConstitutionalGateway? constitutionalGateway = null,
        IOptions<RelationshipEvidenceExportOptions>? options = null)
    {
        _dbFactory = dbFactory;
        _gateway = gateway;
        _constitutionalGateway = constitutionalGateway;
        _options = options?.Value ?? new RelationshipEvidenceExportOptions();
    }

    public async Task<IReadOnlyList<RelationshipEvidenceDetail>> ListAsync(
        Guid tenantId, Guid relationshipId, Guid participantId, CancellationToken cancellationToken)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var role = await ResolveRoleAsync(db, tenantId, relationshipId, participantId, cancellationToken);
        var ids = await LinkedEvidenceIdsAsync(db, tenantId, relationshipId, cancellationToken);
        if (ids.Count == 0) return [];
        var records = await _gateway.QueryAsync(tenantId, ids, cancellationToken);
        return records.Where(value => IsVisible(role, value.ActionType)).Select(ToDetail).ToList();
    }

    public async Task<RelationshipEvidenceDetail?> GetAsync(
        Guid tenantId, Guid relationshipId, Guid participantId, Guid evidenceId,
        CancellationToken cancellationToken)
    {
        var items = await ListAsync(tenantId, relationshipId, participantId, cancellationToken);
        return items.SingleOrDefault(value => value.EvidenceId == evidenceId);
    }

    public async Task<RelationshipEvidenceExportResult> CreateExportAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid participantId,
        Guid idempotencyKey,
        string purpose,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(purpose) || purpose.Length > 200)
            throw new ArgumentException("Export purpose must contain 1 to 200 characters.", nameof(purpose));
        if (_constitutionalGateway is null)
            throw new InvalidOperationException("Constitutional evidence gateway is unavailable.");
        var materialHash = Hash(purpose.Trim());
        await using var replayDb = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var replay = await replayDb.RelationshipEvidenceExports.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId
                && value.IdempotencyKey == idempotencyKey,
            cancellationToken);
        if (replay is not null)
        {
            if (!CryptographicOperations.FixedTimeEquals(
                Convert.FromHexString(replay.MaterialRequestHash), Convert.FromHexString(materialHash)))
                throw new ChannelContinuityConflictException("Evidence export idempotency key conflicts.");
            return ToExportResult(replay, true);
        }

        var evidence = await ListAsync(tenantId, relationshipId, participantId, cancellationToken);
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var role = await ResolveRoleAsync(db, tenantId, relationshipId, participantId, cancellationToken);
        var relationship = await db.EmploymentRelationships.AsNoTracking().SingleAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken);
        var exportId = Guid.NewGuid();
        var createdAt = DateTimeOffset.UtcNow;
        var document = new
        {
            evidence = evidence.Select(value => new
            {
                completeness = "CONSTITUTIONAL_PROOF_RETAINED",
                erasedAt = value.ErasedAt,
                evidenceId = value.EvidenceId,
                payloadReference = value.PayloadReference,
                payloadState = value.PayloadState,
                schemaVersion = "1.0",
                state = value.State,
                subject = value.Subject,
            }),
            exportId,
            generatedAt = createdAt,
            relationshipId,
            schemaVersion = "1.0",
        };
        var documentJson = CanonicalJson(document);
        var documentHash = Hash(documentJson);
        var exportEvidenceId = await _constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "EXPORT_RELATIONSHIP_EVIDENCE",
            exportId,
            new { participant_id = participantId, participant_role = RelationshipRoleCodec.ToDatabase(role), document_sha256 = documentHash },
            cancellationToken);
        var export = new RelationshipEvidenceExport
        {
            ExportId = exportId,
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ParticipantId = participantId,
            ParticipantRole = RelationshipRoleCodec.ToDatabase(role),
            IdempotencyKey = idempotencyKey,
            MaterialRequestHash = materialHash,
            DocumentJson = documentJson,
            DocumentSha256 = documentHash,
            EvidenceId = exportEvidenceId,
            CreatedAt = createdAt,
            ExpiresAt = createdAt.AddMinutes(15),
        };
        db.RelationshipEvidenceExports.Add(export);
        await db.SaveChangesAsync(cancellationToken);
        return ToExportResult(export, false);
    }

    public async Task<RelationshipEvidenceExportResult?> GetExportAsync(
        Guid tenantId, Guid relationshipId, Guid participantId, Guid exportId,
        CancellationToken cancellationToken)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var role = await ResolveRoleAsync(db, tenantId, relationshipId, participantId, cancellationToken);
        var export = await db.RelationshipEvidenceExports.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId
                && value.ExportId == exportId && value.ParticipantId == participantId
                && value.ParticipantRole == RelationshipRoleCodec.ToDatabase(role),
            cancellationToken);
        return export is null ? null : ToExportResult(export, true);
    }

    private RelationshipEvidenceExportResult ToExportResult(RelationshipEvidenceExport export, bool replayed)
    {
        var signingKey = Encoding.UTF8.GetBytes(_options.SigningKey);
        if (signingKey.Length < 32) throw new InvalidOperationException("Evidence export signing key must contain at least 32 characters.");
        var material = $"{export.TenantId:D}:{export.RelationshipId:D}:{export.ParticipantId:D}:{export.ParticipantRole}:{export.ExportId:D}:{export.ExpiresAt.ToUnixTimeSeconds()}";
        var signature = Convert.ToHexStringLower(HMACSHA256.HashData(signingKey, Encoding.UTF8.GetBytes(material)));
        var baseUrl = _options.DownloadBaseUrl.TrimEnd('/');
        if (!Uri.TryCreate(baseUrl, UriKind.Absolute, out var uri) || uri.Scheme != Uri.UriSchemeHttps)
            throw new InvalidOperationException("Evidence export download base URL must use HTTPS.");
        var url = $"{baseUrl}/api/v1/evidence-exports/{export.ExportId:D}/download?expires={export.ExpiresAt.ToUnixTimeSeconds()}&signature={signature}";
        return new(export.ExportId, "COMPLETED", export.CreatedAt, export.ExpiresAt, url,
            export.DocumentSha256, export.DocumentJson, replayed);
    }

    private static string CanonicalJson(object value)
    {
        var node = JsonSerializer.SerializeToNode(value, new JsonSerializerOptions(JsonSerializerDefaults.Web))!;
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream, new JsonWriterOptions { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping }))
            WriteCanonical(writer, node);
        return Encoding.UTF8.GetString(stream.ToArray());
    }

    private static void WriteCanonical(Utf8JsonWriter writer, JsonNode? node)
    {
        if (node is null)
        {
            writer.WriteNullValue();
        }
        else if (node is JsonObject obj)
        {
            writer.WriteStartObject();
            foreach (var property in obj.OrderBy(value => value.Key, StringComparer.Ordinal))
            {
                writer.WritePropertyName(property.Key);
                WriteCanonical(writer, property.Value);
            }
            writer.WriteEndObject();
        }
        else if (node is JsonArray array)
        {
            writer.WriteStartArray();
            foreach (var item in array) WriteCanonical(writer, item);
            writer.WriteEndArray();
        }
        else node.WriteTo(writer);
    }

    private static string Hash(string value) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));

    private static async Task<RelationshipParticipantRole> ResolveRoleAsync(
        EmploymentRelationshipDbContext db, Guid tenantId, Guid relationshipId, Guid participantId,
        CancellationToken cancellationToken)
    {
        var participant = await db.RelationshipParticipants.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId
                && value.ParticipantId == participantId && value.Status == "ACTIVE",
            cancellationToken);
        return participant?.Role ?? throw new KeyNotFoundException("Relationship evidence is not accessible.");
    }

    private static async Task<IReadOnlyCollection<Guid>> LinkedEvidenceIdsAsync(
        EmploymentRelationshipDbContext db, Guid tenantId, Guid relationshipId, CancellationToken cancellationToken)
    {
        var ids = new HashSet<Guid>();
        ids.UnionWith(await db.RelationshipStateHistory.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .Select(value => value.EvidenceId).ToListAsync(cancellationToken));
        var participantEvidence = await db.RelationshipParticipants.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .Select(value => new { value.BoundEvidenceId, value.RevokedEvidenceId }).ToListAsync(cancellationToken);
        ids.UnionWith(participantEvidence.Select(value => value.BoundEvidenceId));
        ids.UnionWith(participantEvidence.Where(value => value.RevokedEvidenceId.HasValue)
            .Select(value => value.RevokedEvidenceId!.Value));
        ids.UnionWith(await db.ContextConfirmationEvents.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .Select(value => value.EvidenceId).ToListAsync(cancellationToken));
        ids.UnionWith(await db.DecisionSpaceSnapshots.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .Select(value => value.EvidenceId).ToListAsync(cancellationToken));
        ids.UnionWith(await db.ContractAcceptances.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .Select(value => value.AcceptanceEvidenceId).ToListAsync(cancellationToken));
        ids.UnionWith(await db.ActivationIntents.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId
                && value.OutcomeEvidenceId.HasValue)
            .Select(value => value.OutcomeEvidenceId!.Value).ToListAsync(cancellationToken));
        var bindingEvidence = await db.ChannelBindings.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .Select(value => new { value.PreparedEvidenceId, value.BoundEvidenceId, value.RevokedEvidenceId })
            .ToListAsync(cancellationToken);
        ids.UnionWith(bindingEvidence.Select(value => value.PreparedEvidenceId));
        ids.UnionWith(bindingEvidence.Where(value => value.BoundEvidenceId.HasValue).Select(value => value.BoundEvidenceId!.Value));
        ids.UnionWith(bindingEvidence.Where(value => value.RevokedEvidenceId.HasValue).Select(value => value.RevokedEvidenceId!.Value));
        var checkpointEvidence = await db.ContinuityCheckpoints.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .Select(value => new { value.PreparedEvidenceId, value.ResolutionEvidenceId }).ToListAsync(cancellationToken);
        ids.UnionWith(checkpointEvidence.Select(value => value.PreparedEvidenceId));
        ids.UnionWith(checkpointEvidence.Where(value => value.ResolutionEvidenceId.HasValue)
            .Select(value => value.ResolutionEvidenceId!.Value));
        ids.UnionWith(await db.DeliveryAcknowledgements.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .Select(value => value.EvidenceId).ToListAsync(cancellationToken));
        return ids.Take(100).ToArray();
    }

    private static bool IsVisible(RelationshipParticipantRole role, string actionType) => role switch
    {
        RelationshipParticipantRole.Employer => true,
        RelationshipParticipantRole.Evaluator =>
            ContainsAny(actionType, "DISCLOS", "TRIAL", "CONFIG", "LIMIT", "STOP", "ADMIT", "INTERVIEW"),
        RelationshipParticipantRole.RelationshipManager =>
            !ContainsAny(actionType, "PAYMENT", "CHARGE", "PERSONAL", "CREDENTIAL"),
        _ => false,
    };

    private static bool ContainsAny(string value, params string[] fragments) =>
        fragments.Any(fragment => value.Contains(fragment, StringComparison.OrdinalIgnoreCase));

    private static RelationshipEvidenceDetail ToDetail(CustomerVisibleEvidenceRecord value)
    {
        var erased = !string.Equals(value.ErasureStatus, "NONE", StringComparison.OrdinalIgnoreCase);
        return new RelationshipEvidenceDetail(
            Guid.Parse(value.EvidenceRecordId),
            value.ActionType,
            "RECORDED",
            erased ? "ERASED" : value.HasPayloadRefId ? "AVAILABLE" : "NOT_RETAINED",
            !erased && value.HasPayloadRefId ? Guid.Parse(value.PayloadRefId) : null,
            value.ErasureTimestamp?.ToDateTimeOffset(),
            value.EvidenceHash,
            value.RecordedAt.ToDateTimeOffset());
    }
}