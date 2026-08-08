// Implements: architecture/reference/product/ae01-solution-contract.md § Canonical API and Compatibility
// constitutional_basis: C-005, C-023, C-026, C-059

using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record AdmitRelationshipResult(EmploymentRelationship Relationship, bool Created);

public sealed class IllegalRelationshipTransitionException(
    EmploymentRelationshipState current,
    EmploymentRelationshipState target)
    : Exception($"Transition from {current} to {target} is not permitted.");

public sealed class EmploymentRelationshipService
{
    private static readonly IReadOnlyDictionary<EmploymentRelationshipState, ISet<EmploymentRelationshipState>> LegalTransitions =
        new Dictionary<EmploymentRelationshipState, ISet<EmploymentRelationshipState>>
        {
            [EmploymentRelationshipState.Discovered] = Set(EmploymentRelationshipState.Interviewing),
            [EmploymentRelationshipState.Interviewing] = Set(EmploymentRelationshipState.TrialActive, EmploymentRelationshipState.Configuring),
            [EmploymentRelationshipState.TrialActive] = Set(EmploymentRelationshipState.Configuring),
            [EmploymentRelationshipState.Configuring] = Set(EmploymentRelationshipState.ContractPendingAcceptance),
            [EmploymentRelationshipState.ContractPendingAcceptance] = Set(EmploymentRelationshipState.ContractAcceptedPendingPayment),
            [EmploymentRelationshipState.ContractAcceptedPendingPayment] = Set(EmploymentRelationshipState.ActivationPending),
            [EmploymentRelationshipState.ActivationPending] = Set(EmploymentRelationshipState.Active),
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
        CancellationToken cancellationToken)
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

        if (relationship.State == EmploymentRelationshipState.StoppedEmergency
            && targetState is EmploymentRelationshipState.Active or EmploymentRelationshipState.Paused
            && (!explicitEmergencyRelease || actorRole != RelationshipParticipantRole.Employer))
        {
            throw new ConstitutionalActionDeniedException(
                "Emergency Stop release requires explicit same-tenant EMPLOYER authority.");
        }

        var evidenceId = await _constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "TRANSITION_EMPLOYMENT_RELATIONSHIP",
            correlationId,
            new
            {
                from_state = RelationshipStateCodec.ToDatabase(relationship.State),
                to_state = RelationshipStateCodec.ToDatabase(targetState),
                actor_participant_id = actorParticipantId,
                actor_role = RelationshipRoleCodec.ToDatabase(actorRole),
                explicit_emergency_release = explicitEmergencyRelease,
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
}