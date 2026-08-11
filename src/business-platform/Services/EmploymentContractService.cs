// Implements: work-contracts/WC-059-goal005-ae01-contract-payment-activation.md §WC059-02
// constitutional_basis: C-009, C-023, C-043, C-049, C-059

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record EmploymentContractCommercialTerms(
    string Currency,
    long GrossAmountInrPaise,
    long GstAmountInrPaise,
    string Cadence,
    string SubscriptionTerms,
    string AdSpendTreatment,
    string CancellationAndRefundTerms);

public sealed record EmploymentContractGoal(
    string Goal,
    string? Baseline,
    string Measure,
    string? DecisionThreshold,
    string? EvidenceSource);

public sealed record EmploymentContractSkill(
    string SkillId,
    string SkillVersion,
    string AuthorityState,
    string Applicability,
    string? ApplicabilityReason,
    string Status);

public sealed record EmploymentContractDocument(
    string AeecVersion,
    string ProfessionalType,
    string ProfessionalDisplayName,
    IReadOnlyList<string> Rights,
    IReadOnlyList<string> Obligations,
    IReadOnlyList<string> Limitations,
    IReadOnlyList<string> AuthorityTerms,
    IReadOnlyList<string> StopTerms,
    int ReviewCadenceMonths,
    long BudgetCeilingInrPaise,
    IReadOnlyList<EmploymentContractGoal> Goals,
    IReadOnlyList<EmploymentContractSkill> Skills,
    EmploymentContractCommercialTerms PriceTax,
    string EvidencePosture);

public sealed record EmploymentContractComposition(
    EmploymentContractVersion Contract,
    EmploymentContractDocument Document,
    bool Created);

public sealed class EmploymentContractService(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    IProfessionalCatalog professionalCatalog)
{
    private const string AeecVersion = "1.0";
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    };

    public async Task<EmploymentContractComposition> ComposeAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid actorParticipantId,
        EmploymentContractCommercialTerms commercialTerms,
        CancellationToken cancellationToken)
    {
        ValidateCommercialTerms(commercialTerms);
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.AsNoTracking().SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId,
            cancellationToken) ?? throw new KeyNotFoundException("Relationship not found.");
        var decisionSpace = await db.DecisionSpaceSnapshots.AsNoTracking()
            .Where(item => item.TenantId == tenantId && item.RelationshipId == relationshipId)
            .OrderByDescending(item => item.Version)
            .FirstOrDefaultAsync(cancellationToken)
            ?? throw new InvalidOperationException("An accepted Decision Space snapshot is required before contract composition.");
        var disclosure = professionalCatalog.GetDisclosure(relationship.ProfessionalType)
            ?? throw new InvalidOperationException("The professional disclosure required for contract composition is unavailable.");
        var goals = await db.RelationshipGoals.AsNoTracking()
            .Where(item => item.TenantId == tenantId
                && item.RelationshipId == relationshipId
                && item.Status == "ACCEPTED")
            .OrderBy(item => item.Goal)
            .ThenBy(item => item.GoalId)
            .Select(item => new EmploymentContractGoal(
                item.Goal, item.Baseline, item.Measure, item.DecisionThreshold, item.EvidenceSource))
            .ToListAsync(cancellationToken);
        var skills = await db.RelationshipSkillConfigurations.AsNoTracking()
            .Where(item => item.TenantId == tenantId
                && item.RelationshipId == relationshipId
                && (item.Status == "ACCEPTED" || item.Status == "DEFERRED"))
            .OrderBy(item => item.SkillId)
            .ThenBy(item => item.SkillVersion)
            .Select(item => new EmploymentContractSkill(
                item.SkillId,
                item.SkillVersion,
                item.AuthorityState,
                item.Applicability,
                item.ApplicabilityReason,
                item.Status))
            .ToListAsync(cancellationToken);

        var authorityBoundaries = DeserializeSortedStrings(decisionSpace.AuthorityBoundariesJson);
        var stopConditions = DeserializeSortedStrings(decisionSpace.StopConditionsJson);
        var document = new EmploymentContractDocument(
            AeecVersion,
            relationship.ProfessionalType,
            disclosure.DisplayName,
            Sort(disclosure.CustomerRights.Concat([
                "Inspect and export the governing contract and material evidence.",
                "Decline, choose not now, cancel, or exit without concealed consequences.",
            ])),
            [
                "Provide accurate business context and identify corrections promptly.",
                "Keep credentials and delegated access within the accepted authority scope.",
                "Review consequential proposals and payment consequences before approval.",
            ],
            Sort(disclosure.Limitations),
            Sort(disclosure.AuthorityNeeds.Concat(authorityBoundaries)),
            Sort(stopConditions.Concat([
                "Emergency Stop remains available and halts consequential progression until authorized release or termination.",
            ])),
            decisionSpace.ReviewCadenceMonths,
            decisionSpace.BudgetCeilingInrPaise,
            goals,
            skills,
            commercialTerms with
            {
                Currency = commercialTerms.Currency.Trim().ToUpperInvariant(),
                Cadence = commercialTerms.Cadence.Trim().ToUpperInvariant(),
                SubscriptionTerms = commercialTerms.SubscriptionTerms.Trim(),
                AdSpendTreatment = commercialTerms.AdSpendTreatment.Trim(),
                CancellationAndRefundTerms = commercialTerms.CancellationAndRefundTerms.Trim(),
            },
            disclosure.EvidencePosture);
        var documentJson = JsonSerializer.Serialize(document, JsonOptions);
        var contractHash = Hash(documentJson);
        var existing = await db.EmploymentContractVersions.AsNoTracking().SingleOrDefaultAsync(
            item => item.TenantId == tenantId
                && item.RelationshipId == relationshipId
                && item.ContractHash == contractHash,
            cancellationToken);
        if (existing is not null)
        {
            return new EmploymentContractComposition(existing, DeserializeDocument(existing.ConfigurationSnapshotJson), false);
        }

        var domainScheduleJson = JsonSerializer.Serialize(new
        {
            professionalType = relationship.ProfessionalType,
            goals,
            skills,
        }, JsonOptions);
        var version = (await db.EmploymentContractVersions
            .Where(item => item.TenantId == tenantId && item.RelationshipId == relationshipId)
            .Select(item => (int?)item.Version)
            .MaxAsync(cancellationToken) ?? 0) + 1;
        var contract = new EmploymentContractVersion
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            Version = version,
            ContractHash = contractHash,
            AeecVersion = AeecVersion,
            DomainScheduleHash = Hash(domainScheduleJson),
            ConfigurationSnapshotJson = documentJson,
            PriceTaxSummaryJson = JsonSerializer.Serialize(document.PriceTax, JsonOptions),
            CreatedByParticipantId = actorParticipantId,
        };
        db.EmploymentContractVersions.Add(contract);
        await db.SaveChangesAsync(cancellationToken);
        return new EmploymentContractComposition(contract, document, true);
    }

    public async Task<EmploymentContractVersion?> GetByVersionAsync(
        Guid tenantId,
        Guid relationshipId,
        int version,
        CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        return await db.EmploymentContractVersions.AsNoTracking().SingleOrDefaultAsync(
            item => item.TenantId == tenantId
                && item.RelationshipId == relationshipId
                && item.Version == version,
            cancellationToken);
    }

    public async Task<EmploymentContractComposition?> GetLatestAsync(
        Guid tenantId, Guid relationshipId, CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var contract = await db.EmploymentContractVersions.AsNoTracking()
            .Where(item => item.TenantId == tenantId && item.RelationshipId == relationshipId)
            .OrderByDescending(item => item.Version)
            .FirstOrDefaultAsync(cancellationToken);
        return contract is null
            ? null
            : new EmploymentContractComposition(contract, DeserializeDocument(contract.ConfigurationSnapshotJson), false);
    }

    private static EmploymentContractDocument DeserializeDocument(string json) =>
        JsonSerializer.Deserialize<EmploymentContractDocument>(json, JsonOptions)
        ?? throw new InvalidOperationException("Stored employment contract material is invalid.");

    private static IReadOnlyList<string> DeserializeSortedStrings(string json) =>
        Sort(JsonSerializer.Deserialize<IReadOnlyList<string>>(json, JsonOptions) ?? []);

    private static IReadOnlyList<string> Sort(IEnumerable<string> values) =>
        values.Select(value => value.Trim())
            .Where(value => value.Length > 0)
            .Distinct(StringComparer.Ordinal)
            .OrderBy(value => value, StringComparer.Ordinal)
            .ToList();

    private static string Hash(string value) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));

    private static void ValidateCommercialTerms(EmploymentContractCommercialTerms terms)
    {
        if (!string.Equals(terms.Currency.Trim(), "INR", StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("Contract currency must be INR.", nameof(terms));
        if (terms.GrossAmountInrPaise <= 0)
            throw new ArgumentOutOfRangeException(nameof(terms), "Gross amount must be positive.");
        if (terms.GstAmountInrPaise < 0 || terms.GstAmountInrPaise > terms.GrossAmountInrPaise)
            throw new ArgumentOutOfRangeException(nameof(terms), "GST must be between zero and the gross amount.");
        if (string.IsNullOrWhiteSpace(terms.Cadence)
            || string.IsNullOrWhiteSpace(terms.SubscriptionTerms)
            || string.IsNullOrWhiteSpace(terms.AdSpendTreatment)
            || string.IsNullOrWhiteSpace(terms.CancellationAndRefundTerms))
            throw new ArgumentException("Complete subscription, ad-spend, and cancellation terms are required.", nameof(terms));
    }
}