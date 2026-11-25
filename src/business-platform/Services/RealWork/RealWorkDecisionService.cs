// Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-3 Decision steps (WC170-R006)
// Constitutional basis: C-001, C-005, C-023, C-059, C-063
// IB: IB-170

using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services.RealWork;

public static class DecisionKinds
{
    public const string Approval = "APPROVAL";
    public const string ScopeConfirmation = "SCOPE_CONFIRMATION";
    public const string AcceptArtifactVersion = "ACCEPT_ARTIFACT_VERSION";
    public const string ConfirmScopeBoundary = "CONFIRM_SCOPE_BOUNDARY";

    public static bool IsDecisionCommand(string commandKind) =>
        commandKind is AcceptArtifactVersion or ConfirmScopeBoundary;
}

public sealed record DecisionView(
    string Kind,
    Guid ArtifactId,
    string ArtifactDigest,
    Guid EvidenceId,
    Guid ActorId,
    long? DecisionSpaceVersion,
    DateTimeOffset DecidedAt
);

/// <summary>
/// The two customer decisions as two steps, two labels and two evidence records. A consequential step is executable
/// only when the artifact is locked, not superseded, and BOTH records exist for its exact digest.
/// </summary>
public sealed record ArtifactDecisionState(
    Guid ArtifactId,
    string ArtifactDigest,
    string ArtifactStatus,
    DecisionView? Approval,
    DecisionView? ScopeConfirmation,
    bool Executable,
    string? BlockedReason
);

/// <summary>The Decision Space version a relationship is governed by now. A scope confirmation given under an older one is stale.</summary>
public interface IDecisionSpaceVersions
{
    long? Current(Guid tenantId, Guid relationshipId);
}

public sealed class WorkspaceDecisionSpaceVersions(ConversationalEmploymentService employment)
    : IDecisionSpaceVersions
{
    public long? Current(Guid tenantId, Guid relationshipId) =>
        employment.GetWorkspace(tenantId, relationshipId)?.DecisionSpaceVersion;
}

public sealed class RealWorkDecisionService(
    IRealWorkLedger ledger,
    RealWorkArtifactService artifacts,
    IRelationshipConstitutionalGateway constitutional,
    TimeProvider clock,
    IDecisionSpaceVersions? versions = null
)
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    /// <summary>"Do you approve this exact version?" The caller's participant check has already run; CE re-checks.</summary>
    public async Task<DecisionView> ApproveAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid actorId,
        string professionalType,
        Guid artifactId,
        string artifactDigest,
        Guid commandId,
        long decisionSpaceVersion,
        CancellationToken cancellationToken
    )
    {
        var artifact = BindExactVersion(tenantId, relationshipId, artifactId, artifactDigest);
        if (artifact.Status is not (ArtifactStatus.Proposed or ArtifactStatus.Locked))
            throw new RealWorkConflictException("REAL_WORK_ARTIFACT_STATE_CONFLICT");
        var existing = Find(tenantId, relationshipId, DecisionKinds.Approval, artifactId);
        if (existing is not null)
        {
            artifacts.Lock(
                tenantId,
                relationshipId,
                artifactId,
                artifactDigest,
                existing.EvidenceId
            );
            return existing;
        }
        var evidenceId = await constitutional.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            professionalType,
            $"EMPLOYMENT_{DecisionKinds.AcceptArtifactVersion}",
            commandId,
            new
            {
                relationshipId,
                artifactId,
                artifactDigest,
                artifactType = artifact.ArtifactType,
                artifactVersion = artifact.Version,
                actorId,
            },
            checked((int)decisionSpaceVersion),
            cancellationToken
        );
        var decision = Record(
            tenantId,
            relationshipId,
            DecisionKinds.Approval,
            artifactId,
            artifactDigest,
            evidenceId,
            actorId,
            null
        );
        artifacts.Lock(tenantId, relationshipId, artifactId, artifactDigest, evidenceId);
        return decision;
    }

    /// <summary>"Is it within what this agent may do for you, and who may do it?" Needs the approved exact version first.</summary>
    public async Task<DecisionView> ConfirmScopeAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid actorId,
        string professionalType,
        Guid artifactId,
        string artifactDigest,
        Guid commandId,
        long decisionSpaceVersion,
        CancellationToken cancellationToken
    )
    {
        var artifact = BindExactVersion(tenantId, relationshipId, artifactId, artifactDigest);
        if (
            artifact.Status != ArtifactStatus.Locked
            || Find(tenantId, relationshipId, DecisionKinds.Approval, artifactId) is null
        )
            throw new RealWorkConflictException("REAL_WORK_APPROVAL_REQUIRED_FIRST");
        var existing = Find(tenantId, relationshipId, DecisionKinds.ScopeConfirmation, artifactId);
        if (existing is not null)
            return existing;
        var evidenceId = await constitutional.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            professionalType,
            $"EMPLOYMENT_{DecisionKinds.ConfirmScopeBoundary}",
            commandId,
            new
            {
                relationshipId,
                artifactId,
                artifactDigest,
                artifactType = artifact.ArtifactType,
                decisionSpaceVersion,
                actorId,
            },
            checked((int)decisionSpaceVersion),
            cancellationToken
        );
        return Record(
            tenantId,
            relationshipId,
            DecisionKinds.ScopeConfirmation,
            artifactId,
            artifactDigest,
            evidenceId,
            actorId,
            decisionSpaceVersion
        );
    }

    public ArtifactDecisionState Check(
        Guid tenantId,
        Guid relationshipId,
        Guid artifactId,
        string? artifactDigest
    )
    {
        var artifact = artifacts.Get(tenantId, relationshipId, artifactId);
        if (artifact is null)
            return new(
                artifactId,
                artifactDigest ?? "",
                "UNKNOWN",
                null,
                null,
                false,
                "ARTIFACT_NOT_FOUND"
            );
        var approval = Find(tenantId, relationshipId, DecisionKinds.Approval, artifactId);
        var scope = Find(tenantId, relationshipId, DecisionKinds.ScopeConfirmation, artifactId);
        var current = versions?.Current(tenantId, relationshipId);
        var reason =
            artifact.Status != ArtifactStatus.Locked ? $"ARTIFACT_{artifact.Status}"
            : !string.Equals(artifact.Digest, artifactDigest, StringComparison.Ordinal)
                ? "DIGEST_MISMATCH"
            : approval is null || approval.ArtifactDigest != artifact.Digest ? "APPROVAL_MISSING"
            : scope is null || scope.ArtifactDigest != artifact.Digest
                ? "SCOPE_CONFIRMATION_MISSING"
            : current is not null && scope.DecisionSpaceVersion != current
                ? "SCOPE_CONFIRMATION_STALE"
            : null;
        return new(
            artifactId,
            artifact.Digest,
            artifact.Status,
            approval,
            scope,
            reason is null,
            reason
        );
    }

    private ArtifactView BindExactVersion(
        Guid tenantId,
        Guid relationshipId,
        Guid artifactId,
        string artifactDigest
    )
    {
        var artifact =
            artifacts.Get(tenantId, relationshipId, artifactId)
            ?? throw new RealWorkConflictException("REAL_WORK_ARTIFACT_NOT_FOUND");
        if (!string.Equals(artifact.Digest, artifactDigest, StringComparison.Ordinal))
            throw new RealWorkConflictException("REAL_WORK_DIGEST_MISMATCH");
        return artifact;
    }

    private DecisionView Record(
        Guid tenantId,
        Guid relationshipId,
        string kind,
        Guid artifactId,
        string digest,
        Guid evidenceId,
        Guid actorId,
        long? decisionSpaceVersion
    )
    {
        var now = clock.GetUtcNow();
        var view = new DecisionView(
            kind,
            artifactId,
            digest,
            evidenceId,
            actorId,
            decisionSpaceVersion,
            now
        );
        var record = ledger.Append(
            tenantId,
            relationshipId,
            RealWorkKinds.Decision,
            $"{kind}:{artifactId:N}",
            JsonSerializer.SerializeToElement(view, Json),
            now
        );
        return record.Payload.Deserialize<DecisionView>(Json)!;
    }

    private DecisionView? Find(Guid tenantId, Guid relationshipId, string kind, Guid artifactId) =>
        ledger
            .List(tenantId, relationshipId, RealWorkKinds.Decision)
            .Select(record => record.Payload.Deserialize<DecisionView>(Json)!)
            .FirstOrDefault(item => item.Kind == kind && item.ArtifactId == artifactId);
}
