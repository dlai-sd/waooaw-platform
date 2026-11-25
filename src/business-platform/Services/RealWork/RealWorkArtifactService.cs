// Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-2 Locked artifact projection (WC170-R005)
// Constitutional basis: C-005, C-023, C-049, C-059, C-063
// IB: IB-170

using System.Text.Json;
using System.Text.RegularExpressions;

namespace Waooaw.BusinessPlatform.Services.RealWork;

public static class ArtifactStatus
{
    public const string Draft = "DRAFT";
    public const string Proposed = "PROPOSED";
    public const string Locked = "LOCKED";
    public const string Superseded = "SUPERSEDED";
}

public sealed record ArtifactProposal(
    string ArtifactType,
    JsonElement Content,
    string PlainLanguageSummary,
    IReadOnlyList<string>? Limitations = null,
    string? AuthorityBoundary = null,
    Guid? SupersedesArtifactId = null,
    bool Draft = false,
    string? VocabularyVersion = null,
    string? VocabularyDigest = null
);

public sealed record ArtifactView(
    Guid ArtifactId,
    string ArtifactType,
    int Version,
    string Digest,
    string Status,
    DateTimeOffset? LockedAt,
    Guid? ApprovalEvidenceId,
    Guid? SupersedesArtifactId,
    string PlainLanguageSummary,
    IReadOnlyList<string> Limitations,
    string? AuthorityBoundary,
    string? VocabularyVersion,
    string? VocabularyDigest,
    JsonElement Content
);

internal sealed record ArtifactPayload(
    Guid ArtifactId,
    string ArtifactType,
    int Version,
    string Digest,
    JsonElement Content,
    string PlainLanguageSummary,
    IReadOnlyList<string> Limitations,
    string? AuthorityBoundary,
    Guid? SupersedesArtifactId,
    bool Draft,
    string? VocabularyVersion,
    string? VocabularyDigest
);

internal sealed record ArtifactLockPayload(
    Guid ArtifactId,
    string Digest,
    Guid ApprovalEvidenceId,
    DateTimeOffset LockedAt
);

internal sealed record ArtifactRefPayload(Guid ArtifactId, string Digest, Guid? SuccessorId = null);

/// <summary>
/// The owner-side version lifecycle beside the Intent Crystallizer's LockedArtifact (ADR-043). A locked artifact is
/// never edited: a change is a successor version, and a successor never inherits the approval of its predecessor.
/// The lock transition needs a genuine approval evidence id from the approval gate; an empty id is refused.
/// </summary>
public sealed partial class RealWorkArtifactService(IRealWorkLedger ledger, TimeProvider clock)
{
    [GeneratedRegex("^[A-Z][A-Z0-9_]{2,63}$")]
    private static partial Regex TypePattern();

    public ArtifactView Propose(Guid tenantId, Guid relationshipId, ArtifactProposal proposal)
    {
        if (
            !TypePattern().IsMatch(proposal.ArtifactType)
            || proposal.Content.ValueKind != JsonValueKind.Object
            || string.IsNullOrWhiteSpace(proposal.PlainLanguageSummary)
            || proposal.PlainLanguageSummary.Length > 2000
            || (
                proposal.Limitations?.Any(item =>
                    string.IsNullOrWhiteSpace(item) || item.Length > 500
                )
                ?? false
            )
            || (proposal.AuthorityBoundary?.Length ?? 0) > 500
        )
            throw new RealWorkConflictException("REAL_WORK_INVALID_REQUEST");
        // An unresolved domain-vocabulary token must never reach a customer as text (DC-1).
        if (
            Mentions(proposal.PlainLanguageSummary)
            || Mentions(proposal.AuthorityBoundary)
            || (proposal.Limitations?.Any(Mentions) ?? false)
        )
            throw new RealWorkConflictException("REAL_WORK_UNRESOLVED_VOCABULARY");

        var digest = RealWorkDigest.Of(
            JsonSerializer.SerializeToElement(
                new { artifactType = proposal.ArtifactType, content = proposal.Content }
            )
        );
        var current = Fold(ledger.List(tenantId, relationshipId));
        var same = current.Where(item => item.ArtifactType == proposal.ArtifactType).ToArray();
        var repeated = same.FirstOrDefault(item =>
            item.Digest == digest && item.SupersedesArtifactId == proposal.SupersedesArtifactId
        );
        if (repeated is not null)
            return repeated;
        if (proposal.SupersedesArtifactId is { } predecessorId)
        {
            var predecessor =
                same.FirstOrDefault(item => item.ArtifactId == predecessorId)
                ?? throw new RealWorkConflictException("REAL_WORK_ARTIFACT_NOT_FOUND");
            if (predecessor.Status == ArtifactStatus.Superseded)
                throw new RealWorkConflictException("REAL_WORK_ARTIFACT_STATE_CONFLICT");
            if (predecessor.Digest == digest)
                throw new RealWorkConflictException("REAL_WORK_NO_CHANGE");
        }
        var payload = new ArtifactPayload(
            Guid.NewGuid(),
            proposal.ArtifactType,
            same.Length + 1,
            digest,
            proposal.Content,
            proposal.PlainLanguageSummary.Trim(),
            proposal.Limitations ?? [],
            proposal.AuthorityBoundary,
            proposal.SupersedesArtifactId,
            proposal.Draft,
            proposal.VocabularyVersion,
            proposal.VocabularyDigest
        );
        var record = ledger.Append(
            tenantId,
            relationshipId,
            RealWorkKinds.Artifact,
            $"{proposal.ArtifactType}:{digest}:{proposal.SupersedesArtifactId:N}",
            JsonSerializer.SerializeToElement(payload),
            clock.GetUtcNow()
        );
        var stored = record.Payload.Deserialize<ArtifactPayload>()!;
        return Get(tenantId, relationshipId, stored.ArtifactId)!;
    }

    /// <summary>Moves a DRAFT to PROPOSED: the agent is done and the customer may decide.</summary>
    public ArtifactView Submit(Guid tenantId, Guid relationshipId, Guid artifactId)
    {
        var artifact = Require(tenantId, relationshipId, artifactId);
        if (artifact.Status == ArtifactStatus.Draft)
            ledger.Append(
                tenantId,
                relationshipId,
                RealWorkKinds.ArtifactSubmitted,
                artifactId.ToString("N"),
                JsonSerializer.SerializeToElement(
                    new ArtifactRefPayload(artifactId, artifact.Digest)
                ),
                clock.GetUtcNow()
            );
        else if (artifact.Status != ArtifactStatus.Proposed)
            throw new RealWorkConflictException("REAL_WORK_ARTIFACT_STATE_CONFLICT");
        return Require(tenantId, relationshipId, artifactId);
    }

    public ArtifactView Lock(
        Guid tenantId,
        Guid relationshipId,
        Guid artifactId,
        string digest,
        Guid approvalEvidenceId
    )
    {
        if (approvalEvidenceId == Guid.Empty)
            throw new RealWorkConflictException("REAL_WORK_APPROVAL_EVIDENCE_REQUIRED");
        var artifact = Require(tenantId, relationshipId, artifactId);
        if (!string.Equals(artifact.Digest, digest, StringComparison.Ordinal))
            throw new RealWorkConflictException("REAL_WORK_DIGEST_MISMATCH");
        if (artifact.Status == ArtifactStatus.Locked)
            return artifact;
        if (artifact.Status != ArtifactStatus.Proposed)
            throw new RealWorkConflictException("REAL_WORK_ARTIFACT_STATE_CONFLICT");
        var now = clock.GetUtcNow();
        ledger.Append(
            tenantId,
            relationshipId,
            RealWorkKinds.ArtifactLocked,
            artifactId.ToString("N"),
            JsonSerializer.SerializeToElement(
                new ArtifactLockPayload(artifactId, artifact.Digest, approvalEvidenceId, now)
            ),
            now
        );
        if (artifact.SupersedesArtifactId is { } predecessorId)
        {
            var predecessor = Require(tenantId, relationshipId, predecessorId);
            ledger.Append(
                tenantId,
                relationshipId,
                RealWorkKinds.ArtifactSuperseded,
                predecessorId.ToString("N"),
                JsonSerializer.SerializeToElement(
                    new ArtifactRefPayload(predecessorId, predecessor.Digest, artifactId)
                ),
                now
            );
        }
        return Require(tenantId, relationshipId, artifactId);
    }

    public ArtifactView? Get(Guid tenantId, Guid relationshipId, Guid artifactId) =>
        Fold(ledger.List(tenantId, relationshipId))
            .FirstOrDefault(item => item.ArtifactId == artifactId);

    public IReadOnlyList<ArtifactView> List(
        Guid tenantId,
        Guid relationshipId,
        string? artifactType = null
    ) =>
        Fold(ledger.List(tenantId, relationshipId))
            .Where(item => artifactType is null || item.ArtifactType == artifactType)
            .ToArray();

    private ArtifactView Require(Guid tenantId, Guid relationshipId, Guid artifactId) =>
        Get(tenantId, relationshipId, artifactId)
        ?? throw new RealWorkConflictException("REAL_WORK_ARTIFACT_NOT_FOUND");

    public static IReadOnlyList<ArtifactView> Fold(IReadOnlyList<RealWorkRecord> records)
    {
        var views = new Dictionary<Guid, ArtifactView>();
        var order = new List<Guid>();
        foreach (var record in records.OrderBy(item => item.Sequence))
        {
            switch (record.Kind)
            {
                case RealWorkKinds.Artifact:
                    var created = record.Payload.Deserialize<ArtifactPayload>()!;
                    order.Add(created.ArtifactId);
                    views[created.ArtifactId] = new ArtifactView(
                        created.ArtifactId,
                        created.ArtifactType,
                        created.Version,
                        created.Digest,
                        created.Draft ? ArtifactStatus.Draft : ArtifactStatus.Proposed,
                        null,
                        null,
                        created.SupersedesArtifactId,
                        created.PlainLanguageSummary,
                        created.Limitations,
                        created.AuthorityBoundary,
                        created.VocabularyVersion,
                        created.VocabularyDigest,
                        created.Content
                    );
                    break;
                case RealWorkKinds.ArtifactSubmitted:
                    var submitted = record.Payload.Deserialize<ArtifactRefPayload>()!;
                    if (views.TryGetValue(submitted.ArtifactId, out var draft))
                        views[submitted.ArtifactId] = draft with
                        {
                            Status = ArtifactStatus.Proposed,
                        };
                    break;
                case RealWorkKinds.ArtifactLocked:
                    var locked = record.Payload.Deserialize<ArtifactLockPayload>()!;
                    if (views.TryGetValue(locked.ArtifactId, out var proposed))
                        views[locked.ArtifactId] = proposed with
                        {
                            Status = ArtifactStatus.Locked,
                            LockedAt = locked.LockedAt,
                            ApprovalEvidenceId = locked.ApprovalEvidenceId,
                        };
                    break;
                case RealWorkKinds.ArtifactSuperseded:
                    var superseded = record.Payload.Deserialize<ArtifactRefPayload>()!;
                    if (views.TryGetValue(superseded.ArtifactId, out var previous))
                        views[superseded.ArtifactId] = previous with
                        {
                            Status = ArtifactStatus.Superseded,
                        };
                    break;
            }
        }
        // A predecessor is retired by the fact that its successor is locked, not by a second write that could be lost.
        foreach (
            var successor in views
                .Values.Where(item =>
                    item.Status == ArtifactStatus.Locked && item.SupersedesArtifactId is not null
                )
                .ToArray()
        )
            if (
                views.TryGetValue(successor.SupersedesArtifactId!.Value, out var retired)
                && retired.Status != ArtifactStatus.Superseded
            )
                views[retired.ArtifactId] = retired with { Status = ArtifactStatus.Superseded };
        return order.Select(id => views[id]).ToArray();
    }

    private static bool Mentions(string? text) =>
        text is not null && text.Contains("{DVE.", StringComparison.Ordinal);
}
