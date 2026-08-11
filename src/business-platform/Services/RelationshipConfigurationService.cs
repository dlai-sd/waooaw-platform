// Implements: architecture/reference/product/ae01-relationship-data-contract.md § Migration 20
// constitutional_basis: C-023, C-026, C-059, C-063, C-078

using System.Security.Cryptography;
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

    private static ContextValue ToContextValue(RelationshipContextPayload payload) => new(
        payload.PayloadReference,
        payload.FieldType,
        JsonSerializer.Deserialize<JsonElement>(payload.ValueJson!),
        payload.Source,
        payload.Confidence,
        payload.ConfirmationStatus);
}