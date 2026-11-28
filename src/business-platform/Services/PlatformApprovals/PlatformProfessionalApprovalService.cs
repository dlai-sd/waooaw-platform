// Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R023, R024, R025
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services.PlatformApprovals;

public static class PlatformApprovalStates
{
    public const string NotApproved = "NOT_APPROVED";
    public const string Approved = "APPROVED";
    public const string Suspended = "SUSPENDED";
    public const string Retired = "RETIRED";
}

public static class PlatformApprovalActions
{
    public const string Approve = "approve";
    public const string Suspend = "suspend";
    public const string Retire = "retire";
}

/// <summary>The Founder's decision about one professional and version, for every customer.</summary>
public sealed record PlatformProfessionalApproval(
    string ProfessionalType,
    string ProfessionalVersion,
    string State,
    string ContentDigest,
    string ReleaseRevision,
    string DecidedBy,
    DateTimeOffset DecidedAt,
    string? Reason,
    int StateVersion
);

public sealed record PlatformProfessionalView(
    string ProfessionalType,
    string ProfessionalVersion,
    string DisplayName,
    string State,
    bool DefinitionChanged,
    string? DecidedBy,
    DateTimeOffset? DecidedAt,
    string? Reason,
    int StateVersion,
    IReadOnlyList<string> Actions
);

public sealed class PlatformApprovalException(int status, string code, string message)
    : Exception(message)
{
    public int Status { get; } = status;
    public string Code { get; } = code;
}

public interface IPlatformProfessionalApprovalStore
{
    Task<PlatformProfessionalApproval?> GetAsync(
        string professionalType,
        string professionalVersion,
        CancellationToken ct
    );

    /// <summary>Writes the decision and its history row; false when another decision won the race.</summary>
    Task<bool> SaveAsync(
        PlatformProfessionalApproval next,
        int expectedStateVersion,
        CancellationToken ct
    );
}

public sealed class InMemoryPlatformProfessionalApprovalStore : IPlatformProfessionalApprovalStore
{
    private readonly ConcurrentDictionary<(string, string), PlatformProfessionalApproval> rows = [];

    public List<PlatformProfessionalApproval> History { get; } = [];

    public Task<PlatformProfessionalApproval?> GetAsync(
        string professionalType,
        string professionalVersion,
        CancellationToken ct
    ) =>
        Task.FromResult(
            rows.TryGetValue((professionalType, professionalVersion), out var value) ? value : null
        );

    public Task<bool> SaveAsync(
        PlatformProfessionalApproval next,
        int expectedStateVersion,
        CancellationToken ct
    )
    {
        var key = (next.ProfessionalType, next.ProfessionalVersion);
        lock (History)
        {
            var current = rows.TryGetValue(key, out var existing) ? existing.StateVersion : 0;
            if (current != expectedStateVersion)
                return Task.FromResult(false);
            rows[key] = next;
            History.Add(next);
            return Task.FromResult(true);
        }
    }
}

public sealed class PostgresPlatformProfessionalApprovalStore(
    IDbContextFactory<ConversationStoreDbContext> factory
) : IPlatformProfessionalApprovalStore
{
    private sealed record Row(
        string ProfessionalTypeId,
        string ProfessionalVersion,
        string State,
        string ContentDigest,
        string ReleaseRevision,
        string DecidedBySubject,
        DateTimeOffset DecidedAt,
        string? Reason,
        int StateVersion
    );

    public async Task<PlatformProfessionalApproval?> GetAsync(
        string professionalType,
        string professionalVersion,
        CancellationToken ct
    )
    {
        await using var db = await factory.CreateDbContextAsync(ct);
        var row = await db
            .Database.SqlQuery<Row>(
                $"""
                SELECT professional_type_id AS "ProfessionalTypeId", professional_version AS "ProfessionalVersion",
                       state AS "State", content_digest AS "ContentDigest", release_revision AS "ReleaseRevision",
                       decided_by_subject AS "DecidedBySubject", decided_at AS "DecidedAt", reason AS "Reason",
                       state_version AS "StateVersion"
                FROM business.platform_professional_approvals
                WHERE professional_type_id = {professionalType} AND professional_version = {professionalVersion}
                """
            )
            .FirstOrDefaultAsync(ct);
        return row is null
            ? null
            : new PlatformProfessionalApproval(
                row.ProfessionalTypeId,
                row.ProfessionalVersion,
                row.State,
                row.ContentDigest,
                row.ReleaseRevision,
                row.DecidedBySubject,
                row.DecidedAt,
                row.Reason,
                row.StateVersion
            );
    }

    public async Task<bool> SaveAsync(
        PlatformProfessionalApproval next,
        int expectedStateVersion,
        CancellationToken ct
    )
    {
        await using var db = await factory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        var written =
            expectedStateVersion == 0
                ? await db.Database.ExecuteSqlInterpolatedAsync(
                    $"""
                    INSERT INTO business.platform_professional_approvals
                        (professional_type_id, professional_version, state, content_digest, release_revision,
                         decided_by_subject, decided_at, reason, state_version)
                    VALUES ({next.ProfessionalType}, {next.ProfessionalVersion}, {next.State}, {next.ContentDigest},
                            {next.ReleaseRevision}, {next.DecidedBy}, {next.DecidedAt}, {next.Reason}, {next.StateVersion})
                    ON CONFLICT (professional_type_id, professional_version) DO NOTHING
                    """,
                    ct
                )
                : await db.Database.ExecuteSqlInterpolatedAsync(
                    $"""
                    UPDATE business.platform_professional_approvals
                    SET state = {next.State}, content_digest = {next.ContentDigest},
                        release_revision = {next.ReleaseRevision}, decided_by_subject = {next.DecidedBy},
                        decided_at = {next.DecidedAt}, reason = {next.Reason}, state_version = {next.StateVersion}
                    WHERE professional_type_id = {next.ProfessionalType}
                      AND professional_version = {next.ProfessionalVersion}
                      AND state_version = {expectedStateVersion}
                    """,
                    ct
                );
        if (written != 1)
            return false;
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.platform_professional_approval_events
                (professional_type_id, professional_version, state, content_digest, release_revision,
                 decided_by_subject, decided_at, reason, state_version)
            VALUES ({next.ProfessionalType}, {next.ProfessionalVersion}, {next.State}, {next.ContentDigest},
                    {next.ReleaseRevision}, {next.DecidedBy}, {next.DecidedAt}, {next.Reason}, {next.StateVersion})
            """,
            ct
        );
        await transaction.CommitAsync(ct);
        return true;
    }
}

/// <summary>
/// The Founder decides which professional versions customers may take on Trial or Hire. The decision is bound to the
/// exact definition shipped in this release (a digest of the catalogue entry); when the definition changes, the earlier
/// approval no longer applies until the Founder approves again. A customer's workspace receives its own admission record
/// from this decision when it first needs one, so the rest of the platform keeps reading workspace-scoped admissions.
/// </summary>
public sealed class PlatformProfessionalApprovalService(
    IProfessionalCatalog catalog,
    IPlatformProfessionalApprovalStore store,
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    TimeProvider clock,
    WorkspaceRuntimeBindingService? bindings = null
)
{
    public const string WorkspacePolicyVersion = "founder-platform-approval-v1";

    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    public static string ReleaseRevision =>
        Environment.GetEnvironmentVariable("CONTAINER_APP_REVISION") is { Length: > 0 } revision
            ? revision
            : "local";

    public async Task<IReadOnlyList<PlatformProfessionalView>> ListAsync(CancellationToken ct)
    {
        var views = new List<PlatformProfessionalView>();
        foreach (var disclosure in catalog.Browse(null, null))
        {
            var approval = await store.GetAsync(
                disclosure.ProfessionalType,
                disclosure.ProjectionVersion,
                ct
            );
            views.Add(ViewOf(disclosure, approval));
        }
        return views;
    }

    public async Task<PlatformProfessionalView> DecideAsync(
        string professionalType,
        string professionalVersion,
        string action,
        string actor,
        string? reason,
        CancellationToken ct
    )
    {
        var disclosure = FindDisclosure(professionalType, professionalVersion);
        if (
            action
            is not (
                PlatformApprovalActions.Approve
                or PlatformApprovalActions.Suspend
                or PlatformApprovalActions.Retire
            )
        )
            throw new PlatformApprovalException(
                404,
                "PROFESSIONAL_APPROVAL_UNKNOWN_ACTION",
                "That decision is not available."
            );
        var trimmed = reason?.Trim();
        if (action != PlatformApprovalActions.Approve && (trimmed is null || trimmed.Length < 5))
            throw new PlatformApprovalException(
                400,
                "PROFESSIONAL_APPROVAL_REASON_REQUIRED",
                "Give a short reason (at least 5 characters) for suspending or retiring."
            );
        if (trimmed is { Length: > 500 })
            throw new PlatformApprovalException(
                400,
                "PROFESSIONAL_APPROVAL_REASON_TOO_LONG",
                "The reason can be at most 500 characters."
            );

        var current = await store.GetAsync(professionalType, professionalVersion, ct);
        var currentState = current?.State ?? PlatformApprovalStates.NotApproved;
        var nextState = (currentState, action) switch
        {
            (PlatformApprovalStates.Retired, _) => throw new PlatformApprovalException(
                409,
                "PROFESSIONAL_APPROVAL_RETIRED",
                "A retired version cannot be approved again. Publish a new version instead."
            ),
            (_, PlatformApprovalActions.Approve) => PlatformApprovalStates.Approved,
            (PlatformApprovalStates.Approved, PlatformApprovalActions.Suspend) =>
                PlatformApprovalStates.Suspended,
            (
                PlatformApprovalStates.Approved
                    or PlatformApprovalStates.Suspended,
                PlatformApprovalActions.Retire
            ) => PlatformApprovalStates.Retired,
            _ => throw new PlatformApprovalException(
                409,
                "PROFESSIONAL_APPROVAL_NOT_ALLOWED",
                "That decision is not available for this version right now."
            ),
        };
        var next = new PlatformProfessionalApproval(
            professionalType,
            professionalVersion,
            nextState,
            DigestOf(disclosure),
            ReleaseRevision,
            actor,
            clock.GetUtcNow(),
            action == PlatformApprovalActions.Approve ? null : trimmed,
            (current?.StateVersion ?? 0) + 1
        );
        if (!await store.SaveAsync(next, current?.StateVersion ?? 0, ct))
            throw new PlatformApprovalException(
                409,
                "PROFESSIONAL_APPROVAL_CONFLICT",
                "Another decision was saved first. Reload and try again."
            );
        return ViewOf(disclosure, next);
    }

    /// <summary>The approval that applies to the exact definition in this release, or null when none does.</summary>
    public async Task<PlatformProfessionalApproval?> GetEffectiveAsync(
        string professionalType,
        string professionalVersion,
        CancellationToken ct
    )
    {
        var disclosure = catalog
            .Browse(professionalType, null)
            .FirstOrDefault(value => value.ProjectionVersion == professionalVersion);
        if (disclosure is null)
            return null;
        var approval = await store.GetAsync(professionalType, professionalVersion, ct);
        return
            approval is { State: PlatformApprovalStates.Approved }
            && approval.ContentDigest == DigestOf(disclosure)
            ? approval
            : null;
    }

    /// <summary>
    /// Gives the customer's workspace its own active admission for an approved professional version, or returns the one it
    /// already has. Returns null when the Founder has not approved this exact version.
    /// </summary>
    public async Task<Guid?> EnsureWorkspaceAdmissionAsync(
        Guid tenantId,
        Guid ownerSubjectId,
        string professionalType,
        string professionalVersion,
        CancellationToken ct
    )
    {
        var approval = await GetEffectiveAsync(professionalType, professionalVersion, ct);
        if (approval is null)
            return null;
        var contentDigest = approval.ContentDigest;
        var artifactDigest = Sha256($"{contentDigest}|{approval.ReleaseRevision}");
        var evidenceDigest = Sha256(
            $"{approval.ProfessionalType}|{approval.ProfessionalVersion}|{contentDigest}|{approval.DecidedBy}|{approval.DecidedAt:O}|{approval.StateVersion}"
        );
        for (var attempt = 0; attempt < 2; attempt++)
        {
            await using var db = await dbFactory.CreateDbContextAsync(ct);
            var admission = await db.AgentAdmissions.SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.ProfessionalTypeId == professionalType
                    && value.ProfessionalVersion == professionalVersion,
                ct
            );
            try
            {
                if (admission is null)
                {
                    admission = new AgentAdmission
                    {
                        TenantId = tenantId,
                        ProfessionalTypeId = professionalType,
                        ProfessionalVersion = professionalVersion,
                        OwnerSubjectId = ownerSubjectId,
                        State = AgentAdmissionState.Active,
                        StateVersion = 1,
                        AdmissionContentDigest = contentDigest,
                        EvidenceSetDigest = evidenceDigest,
                        ArtifactDigest = artifactDigest,
                        PolicyVersion = WorkspacePolicyVersion,
                    };
                    db.AgentAdmissions.Add(admission);
                    await db.SaveChangesAsync(ct);
                }
                else if (
                    admission.State != AgentAdmissionState.Active
                    || admission.AdmissionContentDigest != contentDigest
                    || admission.EvidenceSetDigest != evidenceDigest
                    || admission.ArtifactDigest != artifactDigest
                )
                {
                    admission.State = AgentAdmissionState.Active;
                    admission.StateVersion++;
                    admission.AdmissionContentDigest = contentDigest;
                    admission.EvidenceSetDigest = evidenceDigest;
                    admission.ArtifactDigest = artifactDigest;
                    admission.PolicyVersion = WorkspacePolicyVersion;
                    admission.UpdatedAt = clock.GetUtcNow();
                    await db.SaveChangesAsync(ct);
                }
                if (bindings is not null)
                    await bindings.EnsureAsync(
                        tenantId,
                        admission.AdmissionId,
                        ownerSubjectId,
                        professionalType,
                        professionalVersion,
                        ct
                    );
                return admission.AdmissionId;
            }
            catch (DbUpdateException) when (attempt == 0)
            {
                // A concurrent request created the same workspace admission; read it on the next pass.
            }
        }
        return null;
    }

    private ProfessionalDisclosure FindDisclosure(
        string professionalType,
        string professionalVersion
    ) =>
        catalog
            .Browse(professionalType, null)
            .FirstOrDefault(value => value.ProjectionVersion == professionalVersion)
        ?? throw new PlatformApprovalException(
            404,
            "PROFESSIONAL_APPROVAL_UNKNOWN",
            "That professional version is not in this release."
        );

    private static PlatformProfessionalView ViewOf(
        ProfessionalDisclosure disclosure,
        PlatformProfessionalApproval? approval
    )
    {
        var state = approval?.State ?? PlatformApprovalStates.NotApproved;
        var changed = approval is not null && approval.ContentDigest != DigestOf(disclosure);
        IReadOnlyList<string> actions = state switch
        {
            PlatformApprovalStates.NotApproved => [PlatformApprovalActions.Approve],
            PlatformApprovalStates.Approved when changed =>
            [
                PlatformApprovalActions.Approve,
                PlatformApprovalActions.Suspend,
                PlatformApprovalActions.Retire,
            ],
            PlatformApprovalStates.Approved =>
            [
                PlatformApprovalActions.Suspend,
                PlatformApprovalActions.Retire,
            ],
            PlatformApprovalStates.Suspended =>
            [
                PlatformApprovalActions.Approve,
                PlatformApprovalActions.Retire,
            ],
            _ => [],
        };
        return new PlatformProfessionalView(
            disclosure.ProfessionalType,
            disclosure.ProjectionVersion,
            disclosure.DisplayName,
            state,
            changed,
            approval?.DecidedBy,
            approval?.DecidedAt,
            approval?.Reason,
            approval?.StateVersion ?? 0,
            actions
        );
    }

    private static string DigestOf(ProfessionalDisclosure disclosure) =>
        Sha256(JsonSerializer.Serialize(disclosure, Json));

    private static string Sha256(string value) =>
        "sha256:"
        + Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value))).ToLowerInvariant();
}
