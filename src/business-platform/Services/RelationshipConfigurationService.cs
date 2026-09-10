// Implements: architecture/reference/product/ae01-relationship-data-contract.md § Migration 20
// constitutional_basis: C-023, C-026, C-059, C-063, C-078

using System.Security.Cryptography;
using System.Buffers.Binary;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record ContextValue(
    Guid PayloadReference,
    string FieldType,
    JsonElement Value,
    string Source,
    decimal? Confidence,
    string ConfirmationStatus);

public sealed record ContextQuestion(string FieldType, string Prompt);

public sealed record RelationshipConfigurationState(
    RelationshipOnboardPreference? Onboard,
    int ConfirmedContextCount,
    bool InductComplete,
    DateTimeOffset ProducedAt);

public sealed record RelationshipPortalGoal(
    RelationshipGoal Goal,
    string SkillId,
    string SkillLabel,
    RelationshipGoalDecision? CurrentDecision,
    bool HasPriorDecision);

public sealed record RelationshipGoalDecisionResult(
    RelationshipGoalDecision Decision,
    bool Replayed);

public sealed class RelationshipConfigurationConflictException : Exception;
public sealed class RelationshipGoalVersionConflictException : Exception;

public sealed class RelationshipConfigurationService(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    IRelationshipConstitutionalGateway constitutionalGateway)
{
    private static readonly ContextQuestion[] MinimumContextQuestions =
    [
        new("NAME", "What name should this professional use for your business?"),
        new("LOCATION", "Where does your business serve customers?"),
        new("BUSINESS_NATURE", "What does your business provide?"),
    ];

    public async Task<ContextValue> ConfirmContextAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid actorParticipantId,
        string fieldType,
        JsonElement value,
        string source,
        decimal? confidence,
        Guid? correctsPayloadReference,
        Guid correlationId,
        CancellationToken cancellationToken)
    {
        var normalizedFieldType = fieldType.Trim().ToUpperInvariant();
        if (normalizedFieldType.Length == 0) throw new ArgumentException("Field type is required.", nameof(fieldType));
        if (confidence is < 0 or > 1) throw new ArgumentOutOfRangeException(nameof(confidence));

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId,
            cancellationToken) ?? throw new KeyNotFoundException("Relationship not found.");
        if (relationship.State == EmploymentRelationshipState.StoppedEmergency)
            throw new ConstitutionalActionDeniedException("Relationship configuration is blocked by Emergency Stop.");

        RelationshipContextPayload? corrected = null;
        if (correctsPayloadReference.HasValue)
        {
            corrected = await db.RelationshipContextPayloads.SingleOrDefaultAsync(
                item => item.TenantId == tenantId
                    && item.RelationshipId == relationshipId
                    && item.PayloadReference == correctsPayloadReference
                    && item.InvalidatedAt == null,
                cancellationToken) ?? throw new KeyNotFoundException("Context payload not found.");
            if (!string.Equals(corrected.FieldType, normalizedFieldType, StringComparison.Ordinal))
            {
                throw new InvalidOperationException("A correction must preserve the field type.");
            }
        }

        var valueJson = value.GetRawText();
        var payloadHash = Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(valueJson)));
        var payloadReference = Guid.NewGuid();
        var action = corrected is null ? "CONFIRMED" : "CORRECTED";
        var evidenceId = await constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            $"RELATIONSHIP_CONTEXT_{action}",
            correlationId,
            new { payloadReference, payloadHash, fieldType = normalizedFieldType, action },
            cancellationToken);

        var now = DateTimeOffset.UtcNow;
        if (corrected is not null)
        {
            corrected.InvalidatedAt = now;
            corrected.ConfirmationStatus = "CORRECTED";
        }

        var payload = new RelationshipContextPayload
        {
            PayloadReference = payloadReference,
            TenantId = tenantId,
            RelationshipId = relationshipId,
            FieldType = normalizedFieldType,
            ValueJson = valueJson,
            Source = source.Trim().ToUpperInvariant(),
            Confidence = confidence,
            ConfirmationStatus = "CONFIRMED",
            ConfirmedAt = now,
            PayloadHash = payloadHash,
            CreatedAt = now,
        };
        db.RelationshipContextPayloads.Add(payload);
        db.ContextConfirmationEvents.Add(new ContextConfirmationEvent
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            PayloadReference = payloadReference,
            PayloadHash = payloadHash,
            FieldType = normalizedFieldType,
            Action = action,
            ActorParticipantId = actorParticipantId,
            CorrelationId = correlationId,
            EvidenceId = evidenceId,
            OccurredAt = now,
        });
        await db.SaveChangesAsync(cancellationToken);
        return ToContextValue(payload);
    }

    public async Task<RelationshipConfigurationState> GetPortalConfigurationAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await EnsureRelationshipAsync(db, tenantId, relationshipId, cancellationToken);
        var onboard = await db.RelationshipOnboardPreferences.AsNoTracking().SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId, cancellationToken);
        var activeContext = await db.RelationshipContextPayloads.AsNoTracking()
            .Where(item => item.TenantId == tenantId && item.RelationshipId == relationshipId
                && item.InvalidatedAt == null && item.ErasedAt == null
                && item.ConfirmationStatus == "CONFIRMED")
            .Select(item => item.FieldType)
            .Distinct()
            .ToListAsync(cancellationToken);
        var inductComplete = MinimumContextQuestions.All(question => activeContext.Contains(question.FieldType));
        return new RelationshipConfigurationState(
            onboard, activeContext.Count, inductComplete,
            onboard?.UpdatedAt ?? relationship.UpdatedAt);
    }

    public async Task<RelationshipConfigurationState> UpdateOnboardAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid idempotencyKey,
        string requestHash,
        string? preferredAgentDisplayName,
        string? chatAppearance,
        string? timestampVisibility,
        string? themePreference,
        CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await EnsureRelationshipAsync(db, tenantId, relationshipId, cancellationToken);
        if (relationship.State == EmploymentRelationshipState.StoppedEmergency)
            throw new ConstitutionalActionDeniedException("Relationship configuration is blocked by Emergency Stop.");
        var key = idempotencyKey.ToString();
        const string purpose = "UPDATE_RELATIONSHIP_ONBOARD";
        var existing = await db.RelationshipIdempotency.SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId
                && item.Purpose == purpose && item.IdempotencyKey == key, cancellationToken);
        if (existing is not null && existing.MaterialRequestHash != requestHash)
            throw new RelationshipConfigurationConflictException();

        var preference = await db.RelationshipOnboardPreferences.SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId, cancellationToken);
        if (existing is null)
        {
            preference ??= new RelationshipOnboardPreference { TenantId = tenantId, RelationshipId = relationshipId };
            if (db.Entry(preference).State == EntityState.Detached) db.RelationshipOnboardPreferences.Add(preference);
            preference.PreferredAgentDisplayName = preferredAgentDisplayName;
            preference.ChatAppearance = chatAppearance;
            preference.TimestampVisibility = timestampVisibility;
            preference.ThemePreference = themePreference;
            preference.UpdatedAt = DateTimeOffset.UtcNow;
            db.RelationshipIdempotency.Add(new RelationshipIdempotency
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                Purpose = purpose,
                IdempotencyKey = key,
                MaterialRequestHash = requestHash,
                OutcomeReference = preference.PreferenceId,
                Status = "COMPLETED",
                CompletedAt = DateTimeOffset.UtcNow,
            });
            await db.SaveChangesAsync(cancellationToken);
        }

        var confirmedContextCount = await db.RelationshipContextPayloads.AsNoTracking().CountAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId
                && item.InvalidatedAt == null && item.ErasedAt == null
                && item.ConfirmationStatus == "CONFIRMED", cancellationToken);
        return new RelationshipConfigurationState(preference, confirmedContextCount,
            confirmedContextCount >= MinimumContextQuestions.Length, preference!.UpdatedAt);
    }

    public async Task<IReadOnlyList<RelationshipPortalGoal>> GetPortalGoalsAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        await EnsureRelationshipAsync(db, tenantId, relationshipId, cancellationToken);
        var goals = await db.RelationshipGoals.AsNoTracking()
            .Where(item => item.TenantId == tenantId && item.RelationshipId == relationshipId)
            .OrderBy(item => item.CreatedAt)
            .ToListAsync(cancellationToken);
        var skills = await db.RelationshipSkillConfigurations.AsNoTracking()
            .Where(item => item.TenantId == tenantId && item.RelationshipId == relationshipId)
            .OrderByDescending(item => item.UpdatedAt)
            .ToListAsync(cancellationToken);
        var decisions = await db.RelationshipGoalDecisions.AsNoTracking()
            .Where(item => item.TenantId == tenantId && item.RelationshipId == relationshipId)
            .OrderByDescending(item => item.OccurredAt)
            .ThenByDescending(item => item.DecisionId)
            .ToListAsync(cancellationToken);
        return goals.Select(goal =>
        {
            var skill = skills.FirstOrDefault(item => item.GoalId == goal.GoalId);
            var goalVersion = GetGoalVersion(goal);
            var decision = decisions.FirstOrDefault(item =>
                item.GoalId == goal.GoalId && item.GoalVersion == goalVersion);
            return new RelationshipPortalGoal(
                goal,
                skill?.SkillId ?? "UNASSIGNED",
                skill?.SkillId ?? "Unassigned skill",
                decision,
                decisions.Any(item => item.GoalId == goal.GoalId && item.GoalVersion != goalVersion));
        }).ToArray();
    }

    public async Task<RelationshipGoalDecision?> GetGoalDecisionAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid decisionId,
        CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        await EnsureRelationshipAsync(db, tenantId, relationshipId, cancellationToken);
        return await db.RelationshipGoalDecisions.AsNoTracking().SingleOrDefaultAsync(
            item => item.TenantId == tenantId
                && item.RelationshipId == relationshipId
                && item.DecisionId == decisionId,
            cancellationToken);
    }

    public async Task<RelationshipGoalDecisionResult> VerifyGoalAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid actorParticipantId,
        Guid idempotencyKey,
        string materialRequestHash,
        string expectedWorkspaceVersion,
        string expectedSubjectVersion,
        Guid goalId,
        string goalVersion,
        string decision,
        string? correctionReason,
        Guid correlationId,
        CancellationToken cancellationToken)
    {
        var normalizedDecision = Required(decision, nameof(decision)).ToUpperInvariant();
        var normalizedReason = correctionReason?.Trim();
        if (normalizedDecision is not ("VERIFIED" or "CHANGES_REQUESTED")
            || normalizedReason is { Length: > 500 }
            || (normalizedDecision == "VERIFIED" && normalizedReason is not null)
            || (normalizedDecision == "CHANGES_REQUESTED" && string.IsNullOrWhiteSpace(normalizedReason)))
            throw new ArgumentException("Goal verification decision is invalid.", nameof(decision));

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var purpose = $"VERIFY_GOAL:{actorParticipantId:N}";
        var key = idempotencyKey.ToString("D");
        long? lockKey = null;
        var connectionOpened = false;
        var lockAcquired = false;
        if (db.Database.ProviderName?.Contains("Npgsql", StringComparison.Ordinal) == true)
        {
            var lockMaterial = Encoding.UTF8.GetBytes($"{tenantId:D}:{purpose}:{key}");
            lockKey = BinaryPrimitives.ReadInt64BigEndian(SHA256.HashData(lockMaterial));
            await db.Database.OpenConnectionAsync(cancellationToken);
            connectionOpened = true;
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT pg_advisory_lock({lockKey.Value})", cancellationToken);
            lockAcquired = true;
        }
        try
        {
            var relationship = await EnsureRelationshipAsync(db, tenantId, relationshipId, cancellationToken);
            if (relationship.State == EmploymentRelationshipState.StoppedEmergency)
                throw new ConstitutionalActionDeniedException("Goal verification is blocked by Emergency Stop.");
            var reservation = await db.RelationshipIdempotency.AsNoTracking().SingleOrDefaultAsync(
                item => item.TenantId == tenantId
                    && item.Purpose == purpose
                    && item.IdempotencyKey == key,
                cancellationToken);
            if (reservation is not null)
            {
                if (reservation.RelationshipId != relationshipId
                    || reservation.MaterialRequestHash != materialRequestHash
                    || reservation.OutcomeReference is null)
                    throw new RelationshipConfigurationConflictException();
                var replay = await db.RelationshipGoalDecisions.AsNoTracking().SingleOrDefaultAsync(
                    item => item.TenantId == tenantId
                        && item.RelationshipId == relationshipId
                        && item.DecisionId == reservation.OutcomeReference,
                    cancellationToken) ?? throw new RelationshipConfigurationConflictException();
                return new RelationshipGoalDecisionResult(replay, true);
            }

            var currentWorkspaceVersion = $"relationship-{relationship.StateVersion}";
            var goal = await db.RelationshipGoals.SingleOrDefaultAsync(
                item => item.TenantId == tenantId
                    && item.RelationshipId == relationshipId
                    && item.GoalId == goalId,
                cancellationToken) ?? throw new KeyNotFoundException("Goal not found.");
            var currentGoalVersion = GetGoalVersion(goal);
            if (expectedWorkspaceVersion != currentWorkspaceVersion
                || expectedSubjectVersion != currentGoalVersion
                || goalVersion != currentGoalVersion)
                throw new RelationshipGoalVersionConflictException();

            var skill = await db.RelationshipSkillConfigurations.AsNoTracking()
                .Where(item => item.TenantId == tenantId
                    && item.RelationshipId == relationshipId
                    && item.GoalId == goalId)
                .OrderByDescending(item => item.UpdatedAt)
                .FirstOrDefaultAsync(cancellationToken);
            if (skill is null || string.IsNullOrWhiteSpace(skill.SkillId)
                || string.IsNullOrWhiteSpace(skill.SkillVersion)
                || string.IsNullOrWhiteSpace(goal.Measure)
                || goal.ReviewCadenceMonths <= 0)
                throw new ConstitutionalActionDeniedException("The goal is not eligible for verification.");

            var priorDecisionId = await db.RelationshipGoalDecisions.AsNoTracking()
                .Where(item => item.TenantId == tenantId
                    && item.RelationshipId == relationshipId
                    && item.GoalId == goalId)
                .OrderByDescending(item => item.OccurredAt)
                .ThenByDescending(item => item.DecisionId)
                .Select(item => (Guid?)item.DecisionId)
                .FirstOrDefaultAsync(cancellationToken);
            var evidenceId = await constitutionalGateway.AuthorizeAndRecordAsync(
                tenantId,
                relationshipId,
                relationship.ProfessionalType,
                "RELATIONSHIP_GOAL_VERIFICATION_DECIDED",
                correlationId,
                new { goalId, goalVersion, decision = normalizedDecision, priorDecisionId, materialRequestHash },
                cancellationToken);
            var occurredAt = DateTimeOffset.UtcNow;
            var goalDecision = new RelationshipGoalDecision
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                GoalId = goalId,
                GoalVersion = goalVersion,
                SkillId = skill.SkillId,
                SkillVersion = skill.SkillVersion,
                Measure = goal.Measure,
                ReviewCadenceMonths = goal.ReviewCadenceMonths,
                Decision = normalizedDecision,
                CorrectionReason = normalizedReason,
                PriorDecisionId = priorDecisionId,
                ActorParticipantId = actorParticipantId,
                ExpectedWorkspaceVersion = expectedWorkspaceVersion,
                ExpectedSubjectVersion = expectedSubjectVersion,
                IdempotencyKey = idempotencyKey,
                MaterialRequestHash = materialRequestHash,
                EvidenceId = evidenceId,
                OccurredAt = occurredAt,
            };
            db.RelationshipGoalDecisions.Add(goalDecision);
            db.RelationshipIdempotency.Add(new RelationshipIdempotency
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                Purpose = purpose,
                IdempotencyKey = key,
                MaterialRequestHash = materialRequestHash,
                OutcomeReference = goalDecision.DecisionId,
                Status = "SUCCEEDED",
                CompletedAt = occurredAt,
            });
            await db.SaveChangesAsync(cancellationToken);
            return new RelationshipGoalDecisionResult(goalDecision, false);
        }
        finally
        {
            if (lockAcquired)
                await db.Database.ExecuteSqlInterpolatedAsync(
                    $"SELECT pg_advisory_unlock({lockKey!.Value})", cancellationToken);
            if (connectionOpened) await db.Database.CloseConnectionAsync();
        }
    }

    public async Task<IReadOnlyList<ContextValue>> GetActiveContextAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var payloads = await db.RelationshipContextPayloads.AsNoTracking()
            .Where(item => item.TenantId == tenantId
                && item.RelationshipId == relationshipId
                && item.InvalidatedAt == null
                && item.ErasedAt == null
                && item.ValueJson != null)
            .OrderBy(item => item.CreatedAt)
            .ToListAsync(cancellationToken);
        return payloads.Select(ToContextValue).ToList();
    }

    public async Task<ContextQuestion?> GetNextContextQuestionAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken)
    {
        var context = await GetActiveContextAsync(tenantId, relationshipId, cancellationToken);
        var availableFields = context.Select(item => item.FieldType).ToHashSet(StringComparer.Ordinal);
        return MinimumContextQuestions.FirstOrDefault(question => !availableFields.Contains(question.FieldType));
    }

    public async Task<int> EraseContextPayloadsAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        await EnsureRelationshipAsync(db, tenantId, relationshipId, cancellationToken);
        var payloads = await db.RelationshipContextPayloads
            .Where(item => item.TenantId == tenantId
                && item.RelationshipId == relationshipId
                && item.ErasedAt == null)
            .ToListAsync(cancellationToken);
        var erasedAt = DateTimeOffset.UtcNow;
        foreach (var payload in payloads)
        {
            payload.ValueJson = null;
            payload.ErasedAt = erasedAt;
        }
        await db.SaveChangesAsync(cancellationToken);
        return payloads.Count;
    }

    public async Task<RelationshipGoal> SaveGoalAsync(
        Guid tenantId,
        Guid relationshipId,
        string goal,
        string? baseline,
        string measure,
        string? decisionThreshold,
        string? evidenceSource,
        string status,
        CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        await EnsureRelationshipAsync(db, tenantId, relationshipId, cancellationToken);
        var item = new RelationshipGoal
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            Goal = Required(goal, nameof(goal)),
            Baseline = baseline?.Trim(),
            Measure = Required(measure, nameof(measure)),
            DecisionThreshold = decisionThreshold?.Trim(),
            EvidenceSource = evidenceSource?.Trim(),
            ReviewCadenceMonths = 2,
            Status = Required(status, nameof(status)).ToUpperInvariant(),
        };
        db.RelationshipGoals.Add(item);
        await db.SaveChangesAsync(cancellationToken);
        return item;
    }

    public async Task<RelationshipSkillConfiguration> SaveSkillAsync(
        Guid tenantId,
        Guid relationshipId,
        string skillId,
        string skillVersion,
        Guid? goalId,
        string authorityState,
        string applicability,
        string? applicabilityReason,
        string status,
        CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        await EnsureRelationshipAsync(db, tenantId, relationshipId, cancellationToken);
        var item = new RelationshipSkillConfiguration
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            SkillId = Required(skillId, nameof(skillId)),
            SkillVersion = Required(skillVersion, nameof(skillVersion)),
            GoalId = goalId,
            AuthorityState = Required(authorityState, nameof(authorityState)).ToUpperInvariant(),
            Applicability = Required(applicability, nameof(applicability)).ToUpperInvariant(),
            ApplicabilityReason = applicabilityReason?.Trim(),
            Status = Required(status, nameof(status)).ToUpperInvariant(),
        };
        db.RelationshipSkillConfigurations.Add(item);
        await db.SaveChangesAsync(cancellationToken);
        return item;
    }

    public async Task<DecisionSpaceSnapshot> CreateDecisionSpaceAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid actorParticipantId,
        long budgetCeilingInrPaise,
        IReadOnlyList<string> authorityBoundaries,
        IReadOnlyList<string> stopConditions,
        int reviewCadenceMonths,
        IReadOnlyList<Guid> acceptedEvidence,
        Guid correlationId,
        CancellationToken cancellationToken)
    {
        if (budgetCeilingInrPaise < 0) throw new ArgumentOutOfRangeException(nameof(budgetCeilingInrPaise));
        if (reviewCadenceMonths != 2) throw new ArgumentOutOfRangeException(nameof(reviewCadenceMonths), "Review cadence must be two months.");
        if (authorityBoundaries.Count == 0) throw new ArgumentException("Authority boundaries are required.", nameof(authorityBoundaries));
        if (stopConditions.Count == 0) throw new ArgumentException("Stop conditions are required.", nameof(stopConditions));

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await EnsureRelationshipAsync(db, tenantId, relationshipId, cancellationToken);
        var version = (await db.DecisionSpaceSnapshots
            .Where(item => item.TenantId == tenantId && item.RelationshipId == relationshipId)
            .Select(item => (int?)item.Version)
            .MaxAsync(cancellationToken) ?? 0) + 1;
        var evidenceId = await constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "DECISION_SPACE_ACCEPTED",
            correlationId,
            new { version, budgetCeilingInrPaise, authorityBoundaries, stopConditions, reviewCadenceMonths, acceptedEvidence },
            cancellationToken);
        var snapshot = new DecisionSpaceSnapshot
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            Version = version,
            BudgetCeilingInrPaise = budgetCeilingInrPaise,
            AuthorityBoundariesJson = JsonSerializer.Serialize(authorityBoundaries),
            StopConditionsJson = JsonSerializer.Serialize(stopConditions),
            ReviewCadenceMonths = reviewCadenceMonths,
            AcceptedEvidenceJson = JsonSerializer.Serialize(acceptedEvidence),
            CreatedByParticipantId = actorParticipantId,
            EvidenceId = evidenceId,
        };
        db.DecisionSpaceSnapshots.Add(snapshot);
        await db.SaveChangesAsync(cancellationToken);
        return snapshot;
    }

    private static async Task<EmploymentRelationship> EnsureRelationshipAsync(
        EmploymentRelationshipDbContext db,
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken) =>
        await db.EmploymentRelationships.SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId,
            cancellationToken) ?? throw new KeyNotFoundException("Relationship not found.");

    private static string Required(string value, string parameterName) =>
        string.IsNullOrWhiteSpace(value)
            ? throw new ArgumentException("Value is required.", parameterName)
            : value.Trim();

    public static string GetGoalVersion(RelationshipGoal goal) =>
        $"goal-{goal.UpdatedAt.UtcTicks}";

    private static ContextValue ToContextValue(RelationshipContextPayload payload) => new(
        payload.PayloadReference,
        payload.FieldType,
        JsonSerializer.Deserialize<JsonElement>(payload.ValueJson!),
        payload.Source,
        payload.Confidence,
        payload.ConfirmationStatus);
}