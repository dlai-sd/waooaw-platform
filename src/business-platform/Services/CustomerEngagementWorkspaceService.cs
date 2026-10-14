// Implements: architecture/reference/components/customer-engagement-workspace-solution-contract.md §§6-10
// Constitutional basis: C-001, C-005, C-007, C-023, C-026, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record RelationshipWorkspacePreferenceState(
    int PreferenceVersion,
    string DefaultFocus,
    bool OpenProgressOnConversationFocus,
    DateTimeOffset UpdatedAt
);

public sealed record EngagementTruthDimensions(
    string Delivery,
    string Processing,
    string Evidence,
    string Commercial,
    string Outcome
);

public sealed record EngagementSourceProvenance(
    string SourceOwner,
    string SourceSubjectRef,
    string SourceVersion,
    string SourceContractVersion,
    DateTimeOffset ProducedAt,
    DateTimeOffset LastAuthoritativeConfirmationAt,
    string Freshness,
    string EvidenceState,
    string? EvidenceRef = null,
    DateTimeOffset? ObservedAt = null,
    DateTimeOffset? ValidUntil = null
);

public sealed record WorkspaceFocusReference(
    string SchemaVersion,
    string FocusToken,
    string Destination,
    string Label,
    string AccessibleLabel,
    DateTimeOffset IssuedAt,
    DateTimeOffset ExpiresAt
);

public sealed record EngagementNextAction(
    string ActionType,
    string Label,
    WorkspaceFocusReference Focus
);

public sealed record EngagementProgressItem(
    string ItemId,
    string Title,
    string State,
    string Owner,
    bool Required,
    EngagementTruthDimensions Truth,
    EngagementSourceProvenance Provenance,
    DateTimeOffset UpdatedAt,
    string? Summary = null,
    string? BlockedEffect = null,
    EngagementNextAction? NextAction = null
);

public sealed record CustomerEngagementProgress(
    string SchemaVersion,
    Guid RelationshipId,
    string ProjectionVersion,
    string ProjectionContractVersion,
    DateTimeOffset GeneratedAt,
    IReadOnlyList<EngagementSourceProvenance> ProjectionSources,
    string LifecycleStage,
    string Headline,
    string? Summary,
    WorkspaceFocusReference? SelectedFocus,
    IReadOnlyList<EngagementProgressItem> Items,
    IReadOnlyList<WorkspaceFocusReference> AvailableFocuses
);

public sealed record WorkspaceFocusResolution(
    string SchemaVersion,
    Guid RelationshipId,
    string Destination,
    string CanonicalRoute,
    DateTimeOffset ResolvedAt,
    string AuthorityVersion,
    string? SubjectRef,
    string? SubjectVersion
);

public sealed record ConversationChannelSessionResult(
    Guid ChannelSessionId,
    string Channel,
    int SessionVersion,
    DateTimeOffset EndedAt,
    bool Replayed,
    Guid EvidenceId
);

public sealed class CustomerEngagementNotAccessibleException : Exception;

public sealed class CustomerEngagementVersionConflictException : Exception;

public sealed class CustomerEngagementFocusExpiredException : Exception;

public sealed class CustomerEngagementFocusConflictException : Exception;

public sealed class CustomerEngagementIdempotencyConflictException : Exception;

public sealed class CustomerEngagementWorkspaceService
{
    private const string ProjectionContractVersion = "cew-progress-1";
    private static readonly TimeSpan FocusLifetime = TimeSpan.FromMinutes(15);
    private readonly IDbContextFactory<EmploymentRelationshipDbContext> _dbFactory;
    private readonly IDataProtector _focusProtector;
    private readonly IRelationshipConstitutionalGateway _constitutionalGateway;

    public CustomerEngagementWorkspaceService(
        IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
        IDataProtectionProvider dataProtectionProvider,
        IRelationshipConstitutionalGateway constitutionalGateway
    )
    {
        _dbFactory = dbFactory;
        _focusProtector = dataProtectionProvider.CreateProtector(
            "WAOOAW.CustomerEngagementWorkspace.Focus.v1"
        );
        _constitutionalGateway = constitutionalGateway;
    }

    public async Task<RelationshipWorkspacePreferenceState> GetPreferencesAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        await RequireRelationshipAsync(
            db,
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        var preference = await db.RelationshipOnboardPreferences.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken
        );
        return preference is null
            ? new(0, "LIFECYCLE", true, DateTimeOffset.UnixEpoch)
            : ToPreference(preference);
    }

    public async Task<RelationshipWorkspacePreferenceState> ReplacePreferencesAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        int expectedVersion,
        string defaultFocus,
        bool openProgressOnConversationFocus,
        CancellationToken cancellationToken
    )
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        await RequireRelationshipAsync(
            db,
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        var preference = await db.RelationshipOnboardPreferences.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken
        );
        var currentVersion = preference?.WorkspacePreferenceVersion ?? 0;
        if (currentVersion != expectedVersion)
            throw new CustomerEngagementVersionConflictException();
        if (preference is null)
        {
            preference = new RelationshipOnboardPreference
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
            };
            db.RelationshipOnboardPreferences.Add(preference);
        }
        preference.DefaultFocus = defaultFocus;
        preference.OpenProgressOnConversationFocus = openProgressOnConversationFocus;
        preference.WorkspacePreferenceVersion = currentVersion + 1;
        preference.UpdatedAt = DateTimeOffset.UtcNow;
        await db.SaveChangesAsync(cancellationToken);
        return ToPreference(preference);
    }

    public async Task<CustomerEngagementProgress> GetProgressAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await RequireRelationshipAsync(
            db,
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        var history = await db
            .RelationshipStateHistory.Where(value =>
                value.TenantId == tenantId && value.RelationshipId == relationshipId
            )
            .OrderByDescending(value => value.StateVersion)
            .FirstOrDefaultAsync(cancellationToken);
        var now = DateTimeOffset.UtcNow;
        var state = RelationshipStateCodec.ToDatabase(relationship.State);
        var sourceVersion = $"relationship-{relationship.StateVersion}";
        var provenance = new EngagementSourceProvenance(
            "RELATIONSHIP",
            relationshipId.ToString("D"),
            sourceVersion,
            "ae01-relationship-1",
            relationship.UpdatedAt,
            history?.OccurredAt ?? relationship.UpdatedAt,
            "CURRENT",
            history is null ? "PENDING" : "RECORDED",
            history?.EvidenceId.ToString("D")
        );
        var lifecycleStage = StageFor(relationship.State);
        var focus = CreateFocus(
            tenantId,
            participantId,
            relationship,
            DestinationFor(lifecycleStage),
            relationshipId.ToString("D"),
            sourceVersion,
            now
        );
        var progressState = relationship.State switch
        {
            EmploymentRelationshipState.Active => "WORKING",
            EmploymentRelationshipState.StoppedEmergency => "BLOCKED",
            EmploymentRelationshipState.Terminated => "COMPLETED",
            _ => "IN_PROGRESS",
        };
        var truth = new EngagementTruthDimensions(
            "UNKNOWN",
            progressState,
            history is null ? "UNKNOWN" : "COMPLETED",
            "UNKNOWN",
            "UNKNOWN"
        );
        var item = new EngagementProgressItem(
            $"lifecycle:{relationshipId:D}",
            "Employment journey",
            progressState,
            progressState == "BLOCKED" ? "WAOOAW" : "CUSTOMER",
            true,
            truth,
            provenance,
            relationship.UpdatedAt,
            $"Your professional relationship is {state.ToLowerInvariant().Replace('_', ' ')}.",
            progressState == "BLOCKED"
                ? "Emergency Stop is active. Ordinary work cannot continue."
                : null,
            new EngagementNextAction("OPEN", NextActionLabel(lifecycleStage), focus)
        );
        return new CustomerEngagementProgress(
            "1",
            relationshipId,
            ComputeProjectionVersion(relationship, provenance),
            ProjectionContractVersion,
            now,
            [provenance],
            lifecycleStage,
            HeadlineFor(lifecycleStage),
            "Progress is composed from current owner-confirmed relationship truth.",
            null,
            [item],
            [focus]
        );
    }

    public async Task<WorkspaceFocusResolution> ResolveFocusAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        string token,
        CancellationToken cancellationToken
    )
    {
        FocusPayload payload;
        try
        {
            payload =
                JsonSerializer.Deserialize<FocusPayload>(_focusProtector.Unprotect(token))
                ?? throw new CryptographicException();
        }
        catch (Exception exception) when (exception is CryptographicException or JsonException)
        {
            throw new CustomerEngagementNotAccessibleException();
        }
        if (
            payload.TenantId != tenantId
            || payload.ParticipantId != participantId
            || payload.RelationshipId != relationshipId
        )
            throw new CustomerEngagementNotAccessibleException();
        if (payload.ExpiresAt <= DateTimeOffset.UtcNow)
            throw new CustomerEngagementFocusExpiredException();

        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await RequireRelationshipAsync(
            db,
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        if (
            relationship.State == EmploymentRelationshipState.StoppedEmergency
            || payload.AuthorityVersion != relationship.StateVersion
            || payload.SubjectVersion != $"relationship-{relationship.StateVersion}"
        )
            throw new CustomerEngagementFocusConflictException();
        return new WorkspaceFocusResolution(
            "1",
            relationshipId,
            payload.Destination,
            RouteFor(payload.Destination, relationshipId),
            DateTimeOffset.UtcNow,
            relationship.StateVersion.ToString(),
            payload.SubjectRef,
            payload.SubjectVersion
        );
    }

    public async Task<ConversationChannelSessionResult> EndChannelSessionAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid channelSessionId,
        string idempotencyKey,
        string materialRequestHash,
        int expectedVersion,
        Guid correlationId,
        CancellationToken cancellationToken
    )
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await RequireRelationshipAsync(
            db,
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        var purpose = $"END_CHANNEL_SESSION:{channelSessionId:D}";
        var existing = await db.RelationshipIdempotency.SingleOrDefaultAsync(
            value =>
                value.TenantId == tenantId
                && value.Purpose == purpose
                && value.IdempotencyKey == idempotencyKey,
            cancellationToken
        );
        if (existing is not null && existing.MaterialRequestHash != materialRequestHash)
            throw new CustomerEngagementIdempotencyConflictException();
        var binding = await db.ChannelBindings.SingleOrDefaultAsync(
            value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == participantId
                && value.BindingId == channelSessionId,
            cancellationToken
        );
        if (binding is null)
            throw new CustomerEngagementNotAccessibleException();
        if (existing is not null || binding.Status == "ENDED")
            return new(
                channelSessionId,
                binding.Channel,
                1,
                binding.RevokedAt ?? binding.BoundAt ?? binding.CreatedAt,
                true,
                binding.RevokedEvidenceId ?? Guid.Empty
            );
        ValidateChannelSessionVersion(expectedVersion);

        var evidenceId = await _constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "END_CONVERSATION_CHANNEL_SESSION",
            correlationId,
            new
            {
                channel_session_id = channelSessionId,
                channel = binding.Channel,
                relationship_remains_active = true,
            },
            cancellationToken
        );
        var endedAt = DateTimeOffset.UtcNow;
        binding.Status = "ENDED";
        binding.RevokedAt = endedAt;
        binding.RevokedEvidenceId = evidenceId;
        db.RelationshipIdempotency.Add(
            new RelationshipIdempotency
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                Purpose = purpose,
                IdempotencyKey = idempotencyKey,
                MaterialRequestHash = materialRequestHash,
                OutcomeReference = channelSessionId,
                Status = "SUCCEEDED",
                CompletedAt = endedAt,
            }
        );
        await db.SaveChangesAsync(cancellationToken);
        return new(channelSessionId, binding.Channel, 1, endedAt, false, evidenceId);
    }

    private WorkspaceFocusReference CreateFocus(
        Guid tenantId,
        Guid participantId,
        EmploymentRelationship relationship,
        string destination,
        string subjectRef,
        string subjectVersion,
        DateTimeOffset now
    )
    {
        var expiresAt = now.Add(FocusLifetime);
        var payload = new FocusPayload(
            Guid.NewGuid(),
            tenantId,
            participantId,
            relationship.RelationshipId,
            relationship.StateVersion,
            destination,
            subjectRef,
            subjectVersion,
            now,
            expiresAt
        );
        return new WorkspaceFocusReference(
            "1",
            _focusProtector.Protect(JsonSerializer.Serialize(payload)),
            destination,
            LabelFor(destination),
            $"Open {LabelFor(destination).ToLowerInvariant()} for this professional relationship",
            now,
            expiresAt
        );
    }

    private static async Task<EmploymentRelationship> RequireRelationshipAsync(
        EmploymentRelationshipDbContext db,
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        var authorized = await db.RelationshipParticipants.AnyAsync(
            value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == participantId
                && value.Status == "ACTIVE",
            cancellationToken
        );
        if (!authorized)
            throw new CustomerEngagementNotAccessibleException();
        return await db.EmploymentRelationships.SingleOrDefaultAsync(
                value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
                cancellationToken
            ) ?? throw new CustomerEngagementNotAccessibleException();
    }

    private static RelationshipWorkspacePreferenceState ToPreference(
        RelationshipOnboardPreference preference
    ) =>
        new(
            preference.WorkspacePreferenceVersion,
            preference.DefaultFocus,
            preference.OpenProgressOnConversationFocus,
            preference.UpdatedAt
        );

    private static string ComputeProjectionVersion(
        EmploymentRelationship relationship,
        EngagementSourceProvenance provenance
    )
    {
        var bytes = SHA256.HashData(
            Encoding.UTF8.GetBytes(
                $"{relationship.RelationshipId:D}|{relationship.StateVersion}|{provenance.SourceVersion}|{ProjectionContractVersion}"
            )
        );
        return Convert.ToHexStringLower(bytes);
    }

    private static string StageFor(EmploymentRelationshipState state) =>
        state switch
        {
            EmploymentRelationshipState.Discovered
            or EmploymentRelationshipState.Interviewing
            or EmploymentRelationshipState.TrialActive => "TRIAL_OR_HIRE",
            EmploymentRelationshipState.Configuring
            or EmploymentRelationshipState.ContractPendingAcceptance
            or EmploymentRelationshipState.ContractAcceptedPendingPayment
            or EmploymentRelationshipState.ActivationPending => "INDUCTION",
            EmploymentRelationshipState.Active => "OPERATIONS",
            EmploymentRelationshipState.Paused
            or EmploymentRelationshipState.StoppedEmergency
            or EmploymentRelationshipState.Terminated => "PAUSED_RENEWAL_OR_EXIT",
            _ => "DISCOVERED",
        };

    private static string DestinationFor(string stage) =>
        stage switch
        {
            "INDUCTION" => "INDUCTION",
            "SKILLS_AND_GOALS" => "SKILLS_GOALS",
            "OPERATIONS" => "OPERATION",
            "PERFORMANCE" => "PERFORMANCE",
            "PAUSED_RENEWAL_OR_EXIT" => "RIGHTS",
            _ => "LIFECYCLE",
        };

    private static string RouteFor(string destination, Guid relationshipId) =>
        destination switch
        {
            "CONVERSATION" => $"/relationships/{relationshipId:D}#conversation",
            "INDUCTION" => $"/relationships/{relationshipId:D}#induction",
            "SKILLS_GOALS" => $"/relationships/{relationshipId:D}#skills-and-goals",
            "OPERATION" => $"/relationships/{relationshipId:D}#operations",
            "PERFORMANCE" => $"/relationships/{relationshipId:D}#performance",
            "BUDGET" => $"/relationships/{relationshipId:D}#usage-and-budget",
            "RIGHTS" => $"/relationships/{relationshipId:D}#rights-and-control",
            _ => $"/relationships/{relationshipId:D}#lifecycle",
        };

    private static string LabelFor(string destination) =>
        destination switch
        {
            "SKILLS_GOALS" => "skills and goals",
            "OPERATION" => "operations",
            _ => destination.ToLowerInvariant().Replace('_', ' '),
        };

    private static string HeadlineFor(string stage) =>
        stage switch
        {
            "TRIAL_OR_HIRE" => "Choose the right next step",
            "INDUCTION" => "Prepare your professional to deliver",
            "SKILLS_AND_GOALS" => "Agree goals and a practical plan",
            "OPERATIONS" => "Track work and customer outcomes",
            "PERFORMANCE" => "Review outcomes and improve",
            "PAUSED_RENEWAL_OR_EXIT" => "Review rights and next steps",
            _ => "Discover the right professional",
        };

    private static string NextActionLabel(string stage) =>
        stage switch
        {
            "TRIAL_OR_HIRE" => "Continue Trial or Hire",
            "INDUCTION" => "Continue induction",
            "OPERATIONS" => "Review current work",
            "PAUSED_RENEWAL_OR_EXIT" => "Review rights and controls",
            _ => "Continue",
        };

    private static void ValidateChannelSessionVersion(int expectedVersion)
    {
        if (expectedVersion != 0)
            throw new CustomerEngagementVersionConflictException();
    }

    private sealed record FocusPayload(
        Guid TokenId,
        Guid TenantId,
        Guid ParticipantId,
        Guid RelationshipId,
        int AuthorityVersion,
        string Destination,
        string SubjectRef,
        string SubjectVersion,
        DateTimeOffset IssuedAt,
        DateTimeOffset ExpiresAt
    );
}
