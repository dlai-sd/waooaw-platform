// Implements: work-contracts/WC-095-agent-employment-lifecycle-and-dma-customer-activation.md Section 10
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063, C-079

using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record PerformanceReviewDimensionV1(
    string State,
    string Summary,
    string EvidenceState,
    string? AttributionLimits = null,
    string? Uncertainty = null);

public sealed record PerformanceReviewDraftV1(
    string PolicyVersion,
    DateTimeOffset PeriodStart,
    DateTimeOffset PeriodEnd,
    IReadOnlyDictionary<string, string> SourceVersions,
    PerformanceReviewDimensionV1 WorkDelivery,
    PerformanceReviewDimensionV1 AgentQuality,
    PerformanceReviewDimensionV1 ConstitutionalPerformance,
    PerformanceReviewDimensionV1 CommercialUsage,
    PerformanceReviewDimensionV1 CustomerBusinessOutcome,
    PerformanceReviewDimensionV1 CustomerAssessment,
    PerformanceReviewDimensionV1 TrustAutonomy,
    string Recommendation,
    Guid EvidenceId);

public sealed record PerformanceReviewProjectionV1(
    Guid ReviewId,
    Guid AgentInstanceId,
    string SkillId,
    string SkillVersion,
    int Revision,
    string PolicyVersion,
    DateTimeOffset PeriodStart,
    DateTimeOffset PeriodEnd,
    IReadOnlyDictionary<string, string> SourceVersions,
    PerformanceReviewDimensionV1 WorkDelivery,
    PerformanceReviewDimensionV1 AgentQuality,
    PerformanceReviewDimensionV1 ConstitutionalPerformance,
    PerformanceReviewDimensionV1 CommercialUsage,
    PerformanceReviewDimensionV1 CustomerBusinessOutcome,
    PerformanceReviewDimensionV1 CustomerAssessment,
    PerformanceReviewDimensionV1 TrustAutonomy,
    string Recommendation,
    Guid EvidenceId,
    DateTimeOffset CreatedAt,
    PerformanceReviewResponseV1? CustomerResponse,
    bool ReassessmentRequired);

public sealed record PerformanceReviewResponseV1(
    Guid ResponseId,
    Guid ReviewId,
    int ReviewRevision,
    int ResponseRevision,
    string Decision,
    string? Reason,
    Guid EvidenceId,
    DateTimeOffset OccurredAt);

public sealed record PerformanceReviewResponseResult(
    PerformanceReviewResponseV1 Response,
    bool Replayed);

public sealed class PerformanceReviewInvalidException : Exception;

public sealed class PerformanceReviewService(
    IDbContextFactory<EmploymentRelationshipDbContext> relationshipFactory,
    IRelationshipConstitutionalGateway constitutionalGateway)
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);
    private static readonly HashSet<string> Recommendations =
    [
        "CONTINUE_CURRENT_MANDATE",
        "TUNE_NON_MATERIAL_PRESENTATION",
        "PROPOSE_GOAL_OR_CONFIGURATION_CHANGE",
        "REASSESSMENT_REQUIRED",
        "PAUSE_AFFECTED_WORK",
        "ESCALATE_LIMITATION_OR_BLOCKER",
        "OFFER_TERMINATION_OR_APPROVED_MIGRATION",
    ];
    private static readonly HashSet<string> CustomerDecisions =
    [
        "CONTINUE_CURRENT_MANDATE",
        "REQUEST_REASSESSMENT",
        "DISPUTE_ASSESSMENT",
        "PAUSE_AFFECTED_WORK",
        "REQUEST_TERMINATION_OR_MIGRATION",
    ];

    public async Task<PerformanceReviewProjectionV1> AppendAsync(
        Guid tenantId,
        Guid relationshipId,
        string skillId,
        string skillVersion,
        PerformanceReviewDraftV1 draft,
        CancellationToken cancellationToken)
    {
        Validate(skillId, skillVersion, draft);
        await using var db = await relationshipFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken) ?? throw new PerformanceReviewInvalidException();
        var skillExists = await db.RelationshipSkillConfigurations.AsNoTracking().AnyAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId
                && value.SkillId == skillId && value.SkillVersion == skillVersion
                && value.Status == "ACCEPTED",
            cancellationToken);
        if (!skillExists) throw new PerformanceReviewInvalidException();
        var revision = await db.PerformanceReviewWindows
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId
                && value.SkillId == skillId)
            .Select(value => (int?)value.Revision).MaxAsync(cancellationToken) ?? 0;
        var window = new PerformanceReviewWindow
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            AgentInstanceId = relationship.AgentInstanceId,
            SkillId = skillId,
            SkillVersion = skillVersion,
            Revision = revision + 1,
            PolicyVersion = draft.PolicyVersion,
            PeriodStart = draft.PeriodStart,
            PeriodEnd = draft.PeriodEnd,
            SourceVersionsJson = JsonSerializer.Serialize(draft.SourceVersions, JsonOptions),
            WorkDeliveryJson = Serialize(draft.WorkDelivery),
            AgentQualityJson = Serialize(draft.AgentQuality),
            ConstitutionalPerformanceJson = Serialize(draft.ConstitutionalPerformance),
            CommercialUsageJson = Serialize(draft.CommercialUsage),
            CustomerBusinessOutcomeJson = Serialize(draft.CustomerBusinessOutcome),
            CustomerAssessmentJson = Serialize(draft.CustomerAssessment),
            TrustAutonomyJson = Serialize(draft.TrustAutonomy),
            Recommendation = draft.Recommendation,
            EvidenceId = draft.EvidenceId,
        };
        db.PerformanceReviewWindows.Add(window);
        if (draft.Recommendation is not ("CONTINUE_CURRENT_MANDATE" or "TUNE_NON_MATERIAL_PRESENTATION"))
        {
            db.CustomerAlerts.Add(new CustomerAlert
            {
                TenantId = tenantId,
                AlertType = "PERFORMANCE_REVIEW",
                Severity = draft.Recommendation is "PAUSE_AFFECTED_WORK" or "ESCALATE_LIMITATION_OR_BLOCKER"
                    ? "HIGH" : "MEDIUM",
                Source = "BUSINESS_PLATFORM",
                RelationshipId = relationshipId,
                DueMeaning = "A performance review requires your decision.",
                DestinationSurface = "RELATIONSHIP",
                DestinationSubjectId = window.ReviewId.ToString("D"),
                AvailableAction = "REVIEW",
            });
        }
        await db.SaveChangesAsync(cancellationToken);
        return Project(window, null);
    }

    public async Task<PerformanceReviewResponseResult> RespondAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid actorParticipantId,
        Guid reviewId,
        int expectedReviewRevision,
        string decision,
        string? reason,
        Guid idempotencyKey,
        string materialRequestHash,
        Guid correlationId,
        CancellationToken cancellationToken)
    {
        if (!CustomerDecisions.Contains(decision) || expectedReviewRevision < 1
            || idempotencyKey == Guid.Empty || correlationId == Guid.Empty
            || materialRequestHash.Length != 64 || reason is { Length: > 500 }
            || (decision == "CONTINUE_CURRENT_MANDATE" && reason is not null)
            || (decision != "CONTINUE_CURRENT_MANDATE" && string.IsNullOrWhiteSpace(reason)))
            throw new PerformanceReviewInvalidException();
        await using var db = await relationshipFactory.CreateDbContextAsync(cancellationToken);
        var replay = await db.PerformanceReviewResponses.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId
                && value.IdempotencyKey == idempotencyKey, cancellationToken);
        if (replay is not null)
        {
            if (replay.ReviewId != reviewId || replay.ReviewRevision != expectedReviewRevision
                || replay.ActorParticipantId != actorParticipantId
                || replay.MaterialRequestHash != materialRequestHash)
                throw new PerformanceReviewConflictException();
            return new PerformanceReviewResponseResult(Project(replay), true);
        }
        var review = await db.PerformanceReviewWindows.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId
                && value.ReviewId == reviewId, cancellationToken)
            ?? throw new KeyNotFoundException("Performance review not found.");
        if (review.Revision != expectedReviewRevision) throw new PerformanceReviewConflictException();
        var relationship = await db.EmploymentRelationships.AsNoTracking().SingleAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken);
        if (relationship.State == EmploymentRelationshipState.StoppedEmergency)
            throw new ConstitutionalActionDeniedException("Performance review response is blocked by Emergency Stop.");
        var normalizedReason = reason?.Trim();
        var reasonHash = normalizedReason is null ? null : Convert.ToHexStringLower(
            System.Security.Cryptography.SHA256.HashData(
                System.Text.Encoding.UTF8.GetBytes(normalizedReason)));
        var evidenceId = await constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId, relationshipId, relationship.ProfessionalType,
            "RELATIONSHIP_PERFORMANCE_REVIEW_RESPONSE", correlationId,
            new { actorParticipantId, reviewId, reviewRevision = expectedReviewRevision, decision, reasonHash },
            cancellationToken);
        var responseRevision = await db.PerformanceReviewResponses
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId
                && value.ReviewId == reviewId)
            .Select(value => (int?)value.ResponseRevision).MaxAsync(cancellationToken) ?? 0;
        var response = new PerformanceReviewResponse
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ReviewId = reviewId,
            ReviewRevision = expectedReviewRevision,
            ResponseRevision = responseRevision + 1,
            ActorParticipantId = actorParticipantId,
            Decision = decision,
            Reason = normalizedReason,
            IdempotencyKey = idempotencyKey,
            MaterialRequestHash = materialRequestHash,
            EvidenceId = evidenceId,
        };
        db.PerformanceReviewResponses.Add(response);
        await db.SaveChangesAsync(cancellationToken);
        return new PerformanceReviewResponseResult(Project(response), false);
    }

    public async Task<IReadOnlyList<PerformanceReviewProjectionV1>> ListAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken)
    {
        await using var db = await relationshipFactory.CreateDbContextAsync(cancellationToken);
        var reviews = await db.PerformanceReviewWindows.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .OrderByDescending(value => value.PeriodEnd).ThenByDescending(value => value.Revision)
            .ToListAsync(cancellationToken);
        var responses = await db.PerformanceReviewResponses.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .OrderByDescending(value => value.ResponseRevision)
            .ToListAsync(cancellationToken);
        return reviews.Select(review => Project(
            review, responses.FirstOrDefault(response => response.ReviewId == review.ReviewId))).ToArray();
    }

    public async Task<PerformanceReviewResponseV1?> GetResponseAsync(
        Guid tenantId, Guid relationshipId, Guid responseId, CancellationToken cancellationToken)
    {
        await using var db = await relationshipFactory.CreateDbContextAsync(cancellationToken);
        var response = await db.PerformanceReviewResponses.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId
                && value.ResponseId == responseId, cancellationToken);
        return response is null ? null : Project(response);
    }

    private static void Validate(string skillId, string skillVersion, PerformanceReviewDraftV1 draft)
    {
        if (string.IsNullOrWhiteSpace(skillId) || string.IsNullOrWhiteSpace(skillVersion)
            || string.IsNullOrWhiteSpace(draft.PolicyVersion) || draft.PeriodStart >= draft.PeriodEnd
            || draft.SourceVersions.Count == 0 || !Recommendations.Contains(draft.Recommendation)
            || draft.EvidenceId == Guid.Empty)
            throw new PerformanceReviewInvalidException();
        foreach (var dimension in new[]
        {
            draft.WorkDelivery, draft.AgentQuality, draft.ConstitutionalPerformance,
            draft.CommercialUsage, draft.CustomerBusinessOutcome, draft.CustomerAssessment,
            draft.TrustAutonomy,
        })
            if (string.IsNullOrWhiteSpace(dimension.State) || string.IsNullOrWhiteSpace(dimension.Summary)
                || string.IsNullOrWhiteSpace(dimension.EvidenceState))
                throw new PerformanceReviewInvalidException();
    }

    private static string Serialize(PerformanceReviewDimensionV1 dimension) =>
        JsonSerializer.Serialize(dimension, JsonOptions);

    private static PerformanceReviewProjectionV1 Project(
        PerformanceReviewWindow value, PerformanceReviewResponse? response) => new(
        value.ReviewId, value.AgentInstanceId, value.SkillId, value.SkillVersion, value.Revision,
        value.PolicyVersion, value.PeriodStart, value.PeriodEnd,
        JsonSerializer.Deserialize<Dictionary<string, string>>(value.SourceVersionsJson, JsonOptions)!,
        Deserialize(value.WorkDeliveryJson), Deserialize(value.AgentQualityJson),
        Deserialize(value.ConstitutionalPerformanceJson), Deserialize(value.CommercialUsageJson),
        Deserialize(value.CustomerBusinessOutcomeJson), Deserialize(value.CustomerAssessmentJson),
        Deserialize(value.TrustAutonomyJson), value.Recommendation, value.EvidenceId, value.CreatedAt,
        response is null ? null : Project(response),
        value.Recommendation is "REASSESSMENT_REQUIRED" or "PAUSE_AFFECTED_WORK"
            || response?.Decision is "REQUEST_REASSESSMENT" or "DISPUTE_ASSESSMENT" or "PAUSE_AFFECTED_WORK");

    private static PerformanceReviewResponseV1 Project(PerformanceReviewResponse value) => new(
        value.ResponseId, value.ReviewId, value.ReviewRevision, value.ResponseRevision,
        value.Decision, value.Reason, value.EvidenceId, value.OccurredAt);

    private static PerformanceReviewDimensionV1 Deserialize(string json) =>
        JsonSerializer.Deserialize<PerformanceReviewDimensionV1>(json, JsonOptions)
        ?? throw new PerformanceReviewInvalidException();
}

public sealed class PerformanceReviewConflictException : Exception;
