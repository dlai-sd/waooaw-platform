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
    DateTimeOffset CreatedAt);

public sealed class PerformanceReviewInvalidException : Exception;

public sealed class PerformanceReviewService(
    IDbContextFactory<EmploymentRelationshipDbContext> relationshipFactory)
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
        await db.SaveChangesAsync(cancellationToken);
        return Project(window);
    }

    public async Task<IReadOnlyList<PerformanceReviewProjectionV1>> ListAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken)
    {
        await using var db = await relationshipFactory.CreateDbContextAsync(cancellationToken);
        return (await db.PerformanceReviewWindows.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .OrderByDescending(value => value.PeriodEnd).ThenByDescending(value => value.Revision)
            .ToListAsync(cancellationToken)).Select(Project).ToArray();
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

    private static PerformanceReviewProjectionV1 Project(PerformanceReviewWindow value) => new(
        value.ReviewId, value.AgentInstanceId, value.SkillId, value.SkillVersion, value.Revision,
        value.PolicyVersion, value.PeriodStart, value.PeriodEnd,
        JsonSerializer.Deserialize<Dictionary<string, string>>(value.SourceVersionsJson, JsonOptions)!,
        Deserialize(value.WorkDeliveryJson), Deserialize(value.AgentQualityJson),
        Deserialize(value.ConstitutionalPerformanceJson), Deserialize(value.CommercialUsageJson),
        Deserialize(value.CustomerBusinessOutcomeJson), Deserialize(value.CustomerAssessmentJson),
        Deserialize(value.TrustAutonomyJson), value.Recommendation, value.EvidenceId, value.CreatedAt);

    private static PerformanceReviewDimensionV1 Deserialize(string json) =>
        JsonSerializer.Deserialize<PerformanceReviewDimensionV1>(json, JsonOptions)
        ?? throw new PerformanceReviewInvalidException();
}
