// Implements: WC-065 WC065-03, FA-047
// constitutional_basis: C-002, C-023, C-059, C-089, C-091

using Microsoft.EntityFrameworkCore;
using System.Text.Json;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public enum OfferabilityDisposition
{
    Allow,
    Revise,
    Escalate,
    Block,
}

public sealed record OfferabilityInput(
    string OfferingId,
    string PolicyVersion,
    decimal PriceAmount,
    decimal DirectCostAmount,
    bool OwnerEvidenceCurrent,
    bool OwnerEvidenceConflicting,
    bool CustomerProtectionSatisfied,
    bool ConstitutionalFloorSatisfied,
    bool RequestsCalculatedRisk,
    IReadOnlyDictionary<string, string> OwnerVersions);

public sealed record OfferabilityDecision(
    OfferabilityDisposition Disposition,
    decimal DirectContributionAmount,
    string PolicyVersion,
    IReadOnlyDictionary<string, string> OwnerVersions,
    IReadOnlyList<string> Reasons)
{
    public bool IsEligible => Disposition == OfferabilityDisposition.Allow;
}

public sealed class OfferabilityService
{
    public OfferabilityDecision Evaluate(OfferabilityInput input)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(input.OfferingId);
        ArgumentException.ThrowIfNullOrWhiteSpace(input.PolicyVersion);

        var directContribution = input.PriceAmount - input.DirectCostAmount;
        var reasons = new List<string>();

        if (!input.ConstitutionalFloorSatisfied)
            reasons.Add("CONSTITUTIONAL_FLOOR_FAILED");
        if (!input.CustomerProtectionSatisfied)
            reasons.Add("CUSTOMER_PROTECTION_FAILED");
        if (!input.OwnerEvidenceCurrent)
            reasons.Add("OWNER_EVIDENCE_UNAVAILABLE_OR_STALE");
        if (input.OwnerEvidenceConflicting)
            reasons.Add("OWNER_EVIDENCE_CONFLICTING");
        if (input.OwnerVersions.Count == 0 || input.OwnerVersions.Any(value => string.IsNullOrWhiteSpace(value.Value)))
            reasons.Add("OWNER_VERSION_MISSING");
        if (directContribution < 0)
            reasons.Add("NEGATIVE_DIRECT_CONTRIBUTION");
        if (input.RequestsCalculatedRisk)
            reasons.Add("CALCULATED_RISK_DISABLED");

        var disposition = reasons.Count == 0
            ? OfferabilityDisposition.Allow
            : reasons.Contains("CONSTITUTIONAL_FLOOR_FAILED") || reasons.Contains("CUSTOMER_PROTECTION_FAILED")
                ? OfferabilityDisposition.Block
                : reasons.Contains("CALCULATED_RISK_DISABLED") || reasons.Contains("OWNER_EVIDENCE_CONFLICTING")
                    ? OfferabilityDisposition.Escalate
                    : OfferabilityDisposition.Revise;

        return new OfferabilityDecision(
            disposition,
            directContribution,
            input.PolicyVersion,
            new Dictionary<string, string>(input.OwnerVersions, StringComparer.Ordinal),
            reasons);
    }
}

public interface IOfferabilityGuard
{
    Task RequireEligibleAsync(Guid tenantId, Guid relationshipId, CancellationToken cancellationToken);
}

public sealed class UnconfiguredOfferabilityGuard : IOfferabilityGuard
{
    public Task RequireEligibleAsync(Guid tenantId, Guid relationshipId, CancellationToken cancellationToken) =>
        throw new ActivationEligibilityException("Current offerability decision is unavailable.");
}

public sealed class PersistentOfferabilityGuard(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory) : IOfferabilityGuard
{
    public async Task RequireEligibleAsync(
        Guid tenantId, Guid relationshipId, CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var relationshipVersion = await db.EmploymentRelationships.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .Select(value => (int?)value.StateVersion)
            .SingleOrDefaultAsync(cancellationToken)
            ?? throw new ActivationEligibilityException("Relationship not found.");
        var decision = await db.OfferabilityDecisions.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .OrderByDescending(value => value.ProducedAt)
            .FirstOrDefaultAsync(cancellationToken);
        if (decision is null
            || decision.Disposition != "ALLOW"
            || decision.ExpiresAt <= DateTimeOffset.UtcNow
            || decision.RelationshipStateVersion != relationshipVersion)
            throw new ActivationEligibilityException("Current eligible offerability decision is required.");

        var professionalType = await db.EmploymentRelationships.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .Select(value => value.ProfessionalType)
            .SingleAsync(cancellationToken);
        var admitted = await db.AgentAdmissions.AsNoTracking()
            .Where(value => value.TenantId == tenantId
                && value.ProfessionalTypeId == professionalType
                && value.State == AgentAdmissionState.Active)
            .ToListAsync(cancellationToken);
        if (admitted.Count != 1)
            throw new ActivationEligibilityException("Exactly one active admitted professional version is required.");

        var admission = admitted[0];
        var revision = await db.AgentAdmissionRevisions.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId
                && value.AdmissionId == admission.AdmissionId
                && value.Revision == admission.CurrentRevision,
            cancellationToken) ?? throw new ActivationEligibilityException("Current admission revision is unavailable.");
        using var document = JsonDocument.Parse(revision.AdmissionContentJson);
        var exemptSkills = document.RootElement.GetProperty("skillManifest").EnumerateArray()
            .Where(value => value.TryGetProperty("nonGoalExemption", out _))
            .Select(value => value.GetProperty("skillId").GetString())
            .Where(value => value is not null)
            .ToHashSet(StringComparer.Ordinal);
        var configurations = await db.RelationshipSkillConfigurations.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .ToListAsync(cancellationToken);
        if (configurations.Count == 0
            || configurations.Any(value => value.GoalId is null && !exemptSkills.Contains(value.SkillId)))
            throw new ActivationEligibilityException("Every activated skill requires a goal or admitted non-goal exemption.");
    }
}