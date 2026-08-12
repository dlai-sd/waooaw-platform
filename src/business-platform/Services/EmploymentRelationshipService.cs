// Implements: architecture/reference/product/ae01-solution-contract.md § Canonical API and Compatibility
// constitutional_basis: C-005, C-023, C-026, C-059

using Microsoft.EntityFrameworkCore;
using System.Security.Cryptography;
using System.Text;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record AdmitRelationshipResult(EmploymentRelationship Relationship, bool Created);

public sealed record EmergencyStopReleaseAuthorization(
    bool IsPortalContext,
    string AuthenticationAssurance,
    DateTimeOffset AuthenticatedAt,
    Guid OriginatingStopEvidenceId,
    Guid OriginatingStopCorrelationId,
    string Confirmation,
    string Justification);

public sealed class IllegalRelationshipTransitionException(
    EmploymentRelationshipState current,
    EmploymentRelationshipState target)
    : Exception($"Transition from {current} to {target} is not permitted.");

public sealed class EmploymentRelationshipService
{
    private static readonly IReadOnlyDictionary<EmploymentRelationshipState, ISet<EmploymentRelationshipState>> LegalTransitions =
        new Dictionary<EmploymentRelationshipState, ISet<EmploymentRelationshipState>>
        {
            [EmploymentRelationshipState.Discovered] = Set(EmploymentRelationshipState.Interviewing, EmploymentRelationshipState.StoppedEmergency),
            [EmploymentRelationshipState.Interviewing] = Set(EmploymentRelationshipState.TrialActive, EmploymentRelationshipState.Configuring, EmploymentRelationshipState.StoppedEmergency),
            [EmploymentRelationshipState.TrialActive] = Set(EmploymentRelationshipState.Configuring, EmploymentRelationshipState.StoppedEmergency),
            [EmploymentRelationshipState.Configuring] = Set(EmploymentRelationshipState.ContractPendingAcceptance, EmploymentRelationshipState.StoppedEmergency),
            [EmploymentRelationshipState.ContractPendingAcceptance] = Set(EmploymentRelationshipState.ContractAcceptedPendingPayment, EmploymentRelationshipState.StoppedEmergency),
            [EmploymentRelationshipState.ContractAcceptedPendingPayment] = Set(EmploymentRelationshipState.ActivationPending, EmploymentRelationshipState.StoppedEmergency),
            [EmploymentRelationshipState.ActivationPending] = Set(EmploymentRelationshipState.Active, EmploymentRelationshipState.StoppedEmergency),
            [EmploymentRelationshipState.Active] = Set(EmploymentRelationshipState.Paused, EmploymentRelationshipState.StoppedEmergency, EmploymentRelationshipState.Terminated),
            [EmploymentRelationshipState.Paused] = Set(EmploymentRelationshipState.Active, EmploymentRelationshipState.StoppedEmergency, EmploymentRelationshipState.Terminated),
            [EmploymentRelationshipState.StoppedEmergency] = Set(EmploymentRelationshipState.Paused, EmploymentRelationshipState.Active, EmploymentRelationshipState.Terminated),
            [EmploymentRelationshipState.Terminated] = Set(),
        };

    private readonly IDbContextFactory<EmploymentRelationshipDbContext> _dbFactory;
    private readonly IRelationshipConstitutionalGateway _constitutionalGateway;
    private readonly ILogger<EmploymentRelationshipService> _logger;

    public EmploymentRelationshipService(
        IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
        IRelationshipConstitutionalGateway constitutionalGateway,
        ILogger<EmploymentRelationshipService> logger)
    {
        _dbFactory = dbFactory;
        _constitutionalGateway = constitutionalGateway;
        _logger = logger;
    }

    public async Task<AdmitRelationshipResult> AdmitAsync(
        Guid tenantId,
        Guid participantId,
        Guid evaluationIntentId,
        string professionalType,
        Guid correlationId,
        CancellationToken cancellationToken)
    {
        var normalizedProfessionalType = professionalType.Trim().ToUpperInvariant();
        if (normalizedProfessionalType.Length is 0 or > 64)
        {
            throw new ArgumentException("Professional type must contain 1 to 64 characters.", nameof(professionalType));
        }

        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var existing = await FindByAdmissionKeyAsync(
            db,
            tenantId,
            participantId,
            evaluationIntentId,
            normalizedProfessionalType,
            cancellationToken);
        if (existing is not null)
        {
            return new AdmitRelationshipResult(existing, false);
        }

        var relationshipId = Guid.NewGuid();
        var evidenceId = await _constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            normalizedProfessionalType,
            "ADMIT_EMPLOYMENT_RELATIONSHIP",
            correlationId,
            new
            {
                evaluation_intent_id = evaluationIntentId,
                initiating_participant_id = participantId,
                professional_type = normalizedProfessionalType,
                target_state = "DISCOVERED",
            },
            cancellationToken);

        var relationship = new EmploymentRelationship
        {
            RelationshipId = relationshipId,
            TenantId = tenantId,
            ProfessionalType = normalizedProfessionalType,
            EvaluationIntentId = evaluationIntentId,
            InitiatingParticipantId = participantId,
        };
        db.EmploymentRelationships.Add(relationship);
        db.RelationshipParticipants.Add(new RelationshipParticipant
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ParticipantId = participantId,
            Role = RelationshipParticipantRole.Evaluator,
            BoundEvidenceId = evidenceId,
        });
        db.RelationshipStateHistory.Add(new RelationshipStateHistory
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            StateVersion = 0,
            ToState = EmploymentRelationshipState.Discovered,
            ActorParticipantId = participantId,
            ActorRole = RelationshipParticipantRole.Evaluator,
            CorrelationId = correlationId,
            EvidenceId = evidenceId,
        });

        try
        {
            await db.SaveChangesAsync(cancellationToken);
            return new AdmitRelationshipResult(relationship, true);
        }
        catch (DbUpdateException exception)
        {
            _logger.LogInformation(
                exception,
                "Concurrent first admission detected for tenant {TenantId}, participant {ParticipantId}, intent {EvaluationIntentId}",
                tenantId,
                participantId,
                evaluationIntentId);

            await using var replayDb = await _dbFactory.CreateDbContextAsync(cancellationToken);
            var replay = await FindByAdmissionKeyAsync(
                replayDb,
                tenantId,
                participantId,
                evaluationIntentId,
                normalizedProfessionalType,
                cancellationToken);
            if (replay is null)
            {
                throw;
            }

            return new AdmitRelationshipResult(replay, false);
        }
    }

    public Task<AdmitRelationshipResult> AdmitLegacyAsync(
        Guid tenantId,
        Guid participantId,
        string legacyIdentity,
        string professionalType,
        Guid correlationId,
        CancellationToken cancellationToken) =>
        AdmitAsync(
            tenantId,
            participantId,
            DeriveLegacyEvaluationIntent(legacyIdentity),
            professionalType,
            correlationId,
            cancellationToken);

    public async Task<EmploymentRelationship?> GetAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        return await db.EmploymentRelationships
            .AsNoTracking()
            .SingleOrDefaultAsync(
                value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
                cancellationToken);
    }

    public async Task<bool> IsActiveParticipantAsync(
        Guid tenantId, Guid relationshipId, Guid participantId, CancellationToken cancellationToken)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        return await db.RelationshipParticipants.AsNoTracking().AnyAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == participantId
                && value.Status == "ACTIVE",
            cancellationToken);
    }

    public async Task<RelationshipParticipantRole?> GetActiveRoleAsync(
        Guid tenantId, Guid relationshipId, Guid participantId, CancellationToken cancellationToken)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        return await db.RelationshipParticipants.AsNoTracking()
            .Where(value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == participantId
                && value.Status == "ACTIVE")
            .OrderBy(value => value.Role == RelationshipParticipantRole.Employer ? 0 : 1)
            .Select(value => (RelationshipParticipantRole?)value.Role)
            .FirstOrDefaultAsync(cancellationToken);
    }

    public async Task<IReadOnlyList<RelationshipStateHistory>> GetTimelineAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        return await db.RelationshipStateHistory
            .AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .OrderBy(value => value.StateVersion)
            .ToListAsync(cancellationToken);
    }

    public async Task<EmploymentRelationship?> TransitionAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid actorParticipantId,
        RelationshipParticipantRole actorRole,
        EmploymentRelationshipState targetState,
        Guid correlationId,
        bool explicitEmergencyRelease,
        CancellationToken cancellationToken,
        EmergencyStopReleaseAuthorization? emergencyReleaseAuthorization = null)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken);
        if (relationship is null)
        {
            return null;
        }

        if (!LegalTransitions[relationship.State].Contains(targetState))
        {
            throw new IllegalRelationshipTransitionException(relationship.State, targetState);
        }

        var hasActiveRoleBinding = await db.RelationshipParticipants.AnyAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == actorParticipantId
                && value.Role == actorRole
                && value.Status == "ACTIVE",
            cancellationToken);
        if (!hasActiveRoleBinding)
        {
            throw new ConstitutionalActionDeniedException(
                "Transition authority requires an active same-tenant participant-role binding.");
        }

        RelationshipStateHistory? originatingStop = null;
        if (relationship.State == EmploymentRelationshipState.StoppedEmergency
            && targetState is EmploymentRelationshipState.Active or EmploymentRelationshipState.Paused)
        {
            originatingStop = await db.RelationshipStateHistory.AsNoTracking()
                .Where(value => value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.ToState == EmploymentRelationshipState.StoppedEmergency)
                .OrderByDescending(value => value.StateVersion)
                .FirstOrDefaultAsync(cancellationToken);
            ValidateEmergencyRelease(actorRole, explicitEmergencyRelease, emergencyReleaseAuthorization, originatingStop);
        }

        var actionType = originatingStop is null ? "TRANSITION_EMPLOYMENT_RELATIONSHIP" : "RELEASE_EMERGENCY_STOP";
        var evidenceId = await _constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            actionType,
            correlationId,
            new
            {
                from_state = RelationshipStateCodec.ToDatabase(relationship.State),
                to_state = RelationshipStateCodec.ToDatabase(targetState),
                actor_participant_id = actorParticipantId,
                actor_role = RelationshipRoleCodec.ToDatabase(actorRole),
                explicit_emergency_release = explicitEmergencyRelease,
                originating_stop_evidence_id = originatingStop?.EvidenceId,
                originating_stop_correlation_id = originatingStop?.CorrelationId,
                constitutional_basis = originatingStop is null ? null : $"EMERGENCY_STOP_RELEASE:{originatingStop.EvidenceId:D}",
                release_justification = emergencyReleaseAuthorization?.Justification.Trim(),
            },
            cancellationToken);

        var previousState = relationship.State;
        relationship.State = targetState;
        relationship.StateVersion += 1;
        relationship.UpdatedAt = DateTimeOffset.UtcNow;
        relationship.StoppedAt = targetState == EmploymentRelationshipState.StoppedEmergency
            ? DateTimeOffset.UtcNow
            : relationship.StoppedAt;
        db.RelationshipStateHistory.Add(new RelationshipStateHistory
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            StateVersion = relationship.StateVersion,
            FromState = previousState,
            ToState = targetState,
            ActorParticipantId = actorParticipantId,
            ActorRole = actorRole,
            AuthoritySnapshotId = relationship.AuthoritySnapshotId,
            CorrelationId = correlationId,
            EvidenceId = evidenceId,
        });

        await db.SaveChangesAsync(cancellationToken);
        return relationship;
    }

    public async Task<EmploymentRelationship?> CommitEmergencyStopAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid actorParticipantId,
        RelationshipParticipantRole actorRole,
        Guid correlationId,
        Guid stopEvidenceId,
        CancellationToken cancellationToken)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken);
        if (relationship is null) return null;
        if (relationship.State == EmploymentRelationshipState.StoppedEmergency) return relationship;
        if (!LegalTransitions[relationship.State].Contains(EmploymentRelationshipState.StoppedEmergency))
            throw new IllegalRelationshipTransitionException(relationship.State, EmploymentRelationshipState.StoppedEmergency);
        var bound = await db.RelationshipParticipants.AnyAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == actorParticipantId
                && value.Role == actorRole
                && value.Status == "ACTIVE",
            cancellationToken);
        if (!bound) throw new ConstitutionalActionDeniedException("Emergency Stop requires an active same-tenant participant binding.");

        var previousState = relationship.State;
        relationship.State = EmploymentRelationshipState.StoppedEmergency;
        relationship.StateVersion += 1;
        relationship.StoppedAt = DateTimeOffset.UtcNow;
        relationship.UpdatedAt = relationship.StoppedAt.Value;
        db.RelationshipStateHistory.Add(new RelationshipStateHistory
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            StateVersion = relationship.StateVersion,
            FromState = previousState,
            ToState = EmploymentRelationshipState.StoppedEmergency,
            ActorParticipantId = actorParticipantId,
            ActorRole = actorRole,
            AuthoritySnapshotId = relationship.AuthoritySnapshotId,
            CorrelationId = correlationId,
            EvidenceId = stopEvidenceId,
        });
        await db.SaveChangesAsync(cancellationToken);
        return relationship;
    }

    private static void ValidateEmergencyRelease(
        RelationshipParticipantRole actorRole,
        bool explicitEmergencyRelease,
        EmergencyStopReleaseAuthorization? authorization,
        RelationshipStateHistory? originatingStop)
    {
        var freshAuthentication = authorization is not null
            && authorization.AuthenticatedAt <= DateTimeOffset.UtcNow
            && DateTimeOffset.UtcNow - authorization.AuthenticatedAt <= TimeSpan.FromMinutes(5);
        if (!explicitEmergencyRelease
            || actorRole != RelationshipParticipantRole.Employer
            || authorization is null
            || !authorization.IsPortalContext
            || authorization.AuthenticationAssurance != "TIER_4_PORTAL_FRESH"
            || !freshAuthentication
            || authorization.Confirmation != "RELEASE_EMERGENCY_STOP"
            || string.IsNullOrWhiteSpace(authorization.Justification)
            || authorization.Justification.Trim().Length > 500
            || originatingStop is null
            || authorization.OriginatingStopEvidenceId != originatingStop.EvidenceId
            || authorization.OriginatingStopCorrelationId != originatingStop.CorrelationId)
        {
            throw new ConstitutionalActionDeniedException(
                "Emergency Stop release requires fresh Tier-4 portal EMPLOYER authorization linked to the active Stop.");
        }
    }

    private static Task<EmploymentRelationship?> FindByAdmissionKeyAsync(
        EmploymentRelationshipDbContext db,
        Guid tenantId,
        Guid participantId,
        Guid evaluationIntentId,
        string professionalType,
        CancellationToken cancellationToken) =>
        db.EmploymentRelationships
            .AsNoTracking()
            .SingleOrDefaultAsync(
                value => value.TenantId == tenantId
                    && value.InitiatingParticipantId == participantId
                    && value.EvaluationIntentId == evaluationIntentId
                    && value.ProfessionalType == professionalType,
                cancellationToken);

    private static ISet<EmploymentRelationshipState> Set(params EmploymentRelationshipState[] states) =>
        new HashSet<EmploymentRelationshipState>(states);

    private static Guid DeriveLegacyEvaluationIntent(string legacyIdentity)
    {
        var digest = SHA256.HashData(Encoding.UTF8.GetBytes($"WC057:LEGACY:{legacyIdentity}"));
        return new Guid(digest.AsSpan(0, 16));
    }
}