// Implements: work-contracts/WC-120-requirements.yaml WC120-R015 and PRODUCT-03
// Constitutional basis: C-005, C-007, C-023, C-026, C-059, C-063

using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record WhatsAppMediaInspectionV1(
    string ProviderReferenceDigest,
    string DeclaredMediaType,
    string DetectedMediaType,
    long WireBytes,
    long ExpandedBytes,
    int DurationSeconds,
    string Locale,
    string PayloadReference,
    string? SignatureMediaType = null,
    string? SniffedMediaType = null,
    int CpuMilliseconds = 0,
    int WallTimeMilliseconds = 0,
    long PeakMemoryBytes = 0,
    int RecursionDepth = 0,
    int ArchiveEntries = 0,
    int PageCount = 0,
    int VideoFrames = 0,
    int AnimationFrames = 0,
    int ImageMegapixels = 0,
    bool IsolationConfirmed = true
);

public sealed record WhatsAppMediaScanVerdictV1(
    string Verdict,
    string EngineVersion,
    string PolicyVersion,
    string SignatureVersion,
    DateTimeOffset SignaturePublishedAt,
    string VerdictDigest,
    DateTimeOffset ObservedAt
);

public sealed class WhatsAppMediaQuarantineService(
    IDbContextFactory<ConversationStoreDbContext> dbFactory,
    IDbContextFactory<PayloadStoreDbContext> payloadStoreFactory,
    IOptions<Wc120ConversationOptions> options,
    ConversationStopFence stopFence
)
{
    private static readonly HashSet<string> AllowedTypes = new(StringComparer.Ordinal)
    {
        "audio/ogg; codecs=opus",
        "audio/mpeg",
    };

    public async Task<WhatsAppMediaRecord> QuarantineAsync(
        Guid tenantId,
        Guid relationshipId,
        WhatsAppMediaInspectionV1 inspection,
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        if (!options.Value.Enabled)
            throw new ConversationExecutionUnavailableException();
        await stopFence.ThrowIfLatchedAsync(tenantId, relationshipId, cancellationToken);
        if (
            !IsDigest(inspection.ProviderReferenceDigest)
            || !AllowedTypes.Contains(inspection.DeclaredMediaType)
            || !string.Equals(
                inspection.DeclaredMediaType,
                inspection.DetectedMediaType,
                StringComparison.Ordinal
            )
            || !string.Equals(
                inspection.DeclaredMediaType,
                inspection.SignatureMediaType ?? inspection.DetectedMediaType,
                StringComparison.Ordinal
            )
            || !string.Equals(
                inspection.DeclaredMediaType,
                inspection.SniffedMediaType ?? inspection.DetectedMediaType,
                StringComparison.Ordinal
            )
            || inspection.WireBytes is < 1 or > 5_242_880
            || inspection.ExpandedBytes < inspection.WireBytes
            || inspection.ExpandedBytes > 104_857_600
            || inspection.ExpandedBytes > inspection.WireBytes * 10
            || inspection.DurationSeconds is < 1 or > 120
            || inspection.CpuMilliseconds is < 0 or > 5_000
            || inspection.WallTimeMilliseconds is < 0 or > 10_000
            || inspection.PeakMemoryBytes is < 0 or > 268_435_456
            || inspection.RecursionDepth is < 0 or > 16
            || inspection.ArchiveEntries != 0
            || inspection.PageCount != 0
            || inspection.VideoFrames != 0
            || inspection.AnimationFrames != 0
            || inspection.ImageMegapixels is < 0 or > 40
            || !inspection.IsolationConfirmed
            || inspection.Locale != "en-IN"
            || string.IsNullOrWhiteSpace(inspection.PayloadReference)
            || !Guid.TryParse(inspection.PayloadReference, out _)
        )
            throw new VoiceInvalidMediaException("invalid_media");

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var existing = await db.WhatsAppMedia.SingleOrDefaultAsync(
            value =>
                value.Environment == options.Value.Environment
                && value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ProviderReferenceDigest == inspection.ProviderReferenceDigest,
            cancellationToken
        );
        if (existing is not null)
            return existing;
        var record = new WhatsAppMediaRecord
        {
            Environment = options.Value.Environment,
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ProviderReferenceDigest = inspection.ProviderReferenceDigest,
            DeclaredMediaType = inspection.DeclaredMediaType,
            DetectedMediaType = inspection.DetectedMediaType,
            WireBytes = inspection.WireBytes,
            ExpandedBytes = inspection.ExpandedBytes,
            DurationSeconds = inspection.DurationSeconds,
            CpuMilliseconds = inspection.CpuMilliseconds,
            WallTimeMilliseconds = inspection.WallTimeMilliseconds,
            PeakMemoryBytes = inspection.PeakMemoryBytes,
            RecursionDepth = inspection.RecursionDepth,
            ArchiveEntries = inspection.ArchiveEntries,
            PageCount = inspection.PageCount,
            VideoFrames = inspection.VideoFrames,
            AnimationFrames = inspection.AnimationFrames,
            ImageMegapixels = inspection.ImageMegapixels,
            IsolationConfirmed = inspection.IsolationConfirmed,
            Locale = inspection.Locale,
            PayloadReference = inspection.PayloadReference,
            CreatedAt = now,
            DeleteAfter = now.AddHours(24),
        };
        db.WhatsAppMedia.Add(record);
        await db.SaveChangesAsync(cancellationToken);
        return record;
    }

    public async Task<WhatsAppMediaRecord> RecordScanVerdictAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid mediaId,
        WhatsAppMediaScanVerdictV1 verdict,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var record =
            await db.WhatsAppMedia.SingleOrDefaultAsync(
                value =>
                    value.MediaId == mediaId
                    && value.Environment == options.Value.Environment
                    && value.TenantId == tenantId
                    && value.RelationshipId == relationshipId,
                cancellationToken
            ) ?? throw new ConversationNotAccessibleException();
        if (
            record.State is "CLEAN" or "REJECTED" or "EXPIRED" or "ERASED"
            || verdict.Verdict is not ("CLEAN" or "REJECTED")
            || !IsDigest(verdict.VerdictDigest)
            || string.IsNullOrWhiteSpace(verdict.EngineVersion)
            || string.IsNullOrWhiteSpace(verdict.PolicyVersion)
            || string.IsNullOrWhiteSpace(verdict.SignatureVersion)
            || verdict.SignaturePublishedAt > verdict.ObservedAt
            || verdict.ObservedAt - verdict.SignaturePublishedAt > TimeSpan.FromHours(24)
        )
            throw new ConversationStateConflictException();

        record.ScannerEngineVersion = verdict.EngineVersion;
        record.ScannerPolicyVersion = verdict.PolicyVersion;
        record.ScannerSignatureVersion = verdict.SignatureVersion;
        record.ScannerSignaturePublishedAt = verdict.SignaturePublishedAt;
        record.VerdictDigest = verdict.VerdictDigest;
        record.TerminalAt = verdict.ObservedAt;
        record.State = verdict.Verdict;
        record.DeleteAfter =
            record.State == "REJECTED" ? verdict.ObservedAt.AddHours(24) : DateTimeOffset.MaxValue;
        if (record.State == "REJECTED")
        {
            db.OperationalSignals.Add(
                new ConversationOperationalSignal
                {
                    Environment = record.Environment,
                    Category = "MEDIA",
                    Code = "MEDIA_REJECTED",
                    OccurredAt = verdict.ObservedAt,
                }
            );
        }
        await db.SaveChangesAsync(cancellationToken);
        return record;
    }

    public async Task ApplyRelationshipClosureAsync(
        Guid tenantId,
        Guid relationshipId,
        DateTimeOffset closedAt,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var records = await db
            .WhatsAppMedia.Where(value =>
                value.Environment == options.Value.Environment
                && value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.State == "CLEAN"
            )
            .ToListAsync(cancellationToken);
        foreach (var record in records)
            record.DeleteAfter = closedAt.AddDays(90);
        await db.SaveChangesAsync(cancellationToken);
    }

    public async Task RegisterDerivativesAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid mediaId,
        IReadOnlyCollection<Guid> derivativePayloadReferences,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var record = await LoadAsync(db, tenantId, relationshipId, mediaId, cancellationToken);
        if (record.State != "CLEAN")
            throw new ConversationStateConflictException();
        record.DerivativePayloadReferencesJson = JsonSerializer.Serialize(
            derivativePayloadReferences.Distinct().OrderBy(value => value)
        );
        await db.SaveChangesAsync(cancellationToken);
    }

    public async Task SetLegalHoldAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid mediaId,
        bool held,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var record = await LoadAsync(db, tenantId, relationshipId, mediaId, cancellationToken);
        record.LegalHold = held;
        await db.SaveChangesAsync(cancellationToken);
    }

    public async Task EraseAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid mediaId,
        DateTimeOffset erasedAt,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var record = await LoadAsync(db, tenantId, relationshipId, mediaId, cancellationToken);
        if (record.LegalHold)
            throw new ConversationStateConflictException();
        await ErasePayloadsAsync(record, erasedAt, cancellationToken);
        record.PayloadReference = null;
        record.State = "ERASED";
        record.TerminalAt = erasedAt;
        record.DeleteAfter = erasedAt;
        await db.SaveChangesAsync(cancellationToken);
    }

    public async Task<int> PurgeDueAsync(DateTimeOffset now, CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var records = await db
            .WhatsAppMedia.Where(value =>
                value.Environment == options.Value.Environment
                && !value.LegalHold
                && value.PayloadReference != null
                && value.DeleteAfter <= now
            )
            .ToListAsync(cancellationToken);
        foreach (var record in records)
        {
            await ErasePayloadsAsync(record, now, cancellationToken);
            record.PayloadReference = null;
            if (record.State is "QUARANTINED" or "SCANNING")
            {
                record.State = "EXPIRED";
                record.TerminalAt = now;
            }
        }
        await db.SaveChangesAsync(cancellationToken);
        return records.Count;
    }

    private async Task ErasePayloadsAsync(
        WhatsAppMediaRecord record,
        DateTimeOffset erasedAt,
        CancellationToken cancellationToken
    )
    {
        var references =
            JsonSerializer.Deserialize<Guid[]>(record.DerivativePayloadReferencesJson) ?? [];
        if (record.PayloadReference is { } source && Guid.TryParse(source, out var sourceReference))
            references = [.. references, sourceReference];
        if (references.Length == 0)
            return;

        await using var payloadDb = await payloadStoreFactory.CreateDbContextAsync(
            cancellationToken
        );
        var payloads = await payloadDb
            .OperationalPayloads.Where(value =>
                value.TenantId == record.TenantId && references.Contains(value.PayloadRefId)
            )
            .ToListAsync(cancellationToken);
        foreach (var payload in payloads)
        {
            payload.PayloadJson = null;
            payload.PayloadBlobRef = null;
            payload.ErasedAt = erasedAt;
        }
        await payloadDb.SaveChangesAsync(cancellationToken);
    }

    private async Task<WhatsAppMediaRecord> LoadAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        Guid relationshipId,
        Guid mediaId,
        CancellationToken cancellationToken
    ) =>
        await db.WhatsAppMedia.SingleOrDefaultAsync(
            value =>
                value.MediaId == mediaId
                && value.Environment == options.Value.Environment
                && value.TenantId == tenantId
                && value.RelationshipId == relationshipId,
            cancellationToken
        ) ?? throw new ConversationNotAccessibleException();

    private static bool IsDigest(string value) =>
        value.Length == 64
        && value.All(character => character is >= '0' and <= '9' or >= 'a' and <= 'f');
}
