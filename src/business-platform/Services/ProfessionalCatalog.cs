// Implements: architecture/reference/product/ae01-solution-contract.md §Canonical API and Compatibility
// Constitutional basis: C-009, C-048, C-059, C-063

using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services;

public sealed record ProfessionalEligibility(bool Eligible, string Explanation);

public sealed record ProfessionalSkillDisclosure(
    string SkillId,
    string DisplayName,
    bool ApplicableInTrial,
    string? ActivationCondition);

public sealed record ProfessionalTrialDisclosure(
    bool Available,
    int DurationDays,
    bool PaidApiCallsAllowed,
    bool ExternalActionsAllowed);

public sealed record IndicativePriceDisclosure(
    string Currency,
    long AmountInrPaise,
    string Cadence,
    string Qualification);

public sealed record ProfessionalDisclosure(
    string ProfessionalType,
    string ProjectionVersion,
    string DisplayName,
    IReadOnlyList<string> Suitability,
    IReadOnlyList<ProfessionalSkillDisclosure> Skills,
    IReadOnlyList<string> Limitations,
    IReadOnlyList<string> AuthorityNeeds,
    IReadOnlyList<string> CustomerRights,
    ProfessionalTrialDisclosure Trial,
    string EvidencePosture,
    IndicativePriceDisclosure IndicativePrice,
    ProfessionalEligibility Eligibility);

public sealed record ProfessionalDiscoveryResult(
    string ProfessionalType,
    string ProjectionVersion,
    string DisplayName,
    IReadOnlyList<string> Suitability,
    ProfessionalEligibility Eligibility);

public interface IProfessionalCatalog
{
    IReadOnlyList<ProfessionalDiscoveryResult> Discover(string outcome);

    ProfessionalDisclosure? GetDisclosure(string professionalType);
}

public sealed class ProfessionalCatalog : IProfessionalCatalog
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    private readonly IReadOnlyList<ProfessionalCatalogManifest> _manifests;

    public ProfessionalCatalog(IHostEnvironment environment)
    {
        var catalogDirectory = Path.Combine(environment.ContentRootPath, "Catalog", "Professionals");
        _manifests = Directory.Exists(catalogDirectory)
            ? Directory.EnumerateFiles(catalogDirectory, "*.json", SearchOption.TopDirectoryOnly)
                .OrderBy(path => path, StringComparer.Ordinal)
                .Select(LoadManifest)
                .ToList()
            : [];
    }

    public IReadOnlyList<ProfessionalDiscoveryResult> Discover(string outcome)
    {
        var normalizedOutcome = Normalize(outcome);
        if (normalizedOutcome.Length < 3)
        {
            return [];
        }

        return _manifests
            .Where(manifest => manifest.Active)
            .Where(manifest => !manifest.ProhibitedOutcomeTerms.Any(term => ContainsTerm(normalizedOutcome, term)))
            .Where(manifest => manifest.SupportedOutcomeTerms.Any(term => ContainsTerm(normalizedOutcome, term)))
            .Select(manifest => new ProfessionalDiscoveryResult(
                manifest.ProfessionalType,
                manifest.ProjectionVersion,
                manifest.DisplayName,
                manifest.Suitability,
                new ProfessionalEligibility(true, manifest.EligibilityExplanation)))
            .ToList();
    }

    public ProfessionalDisclosure? GetDisclosure(string professionalType)
    {
        var manifest = _manifests.FirstOrDefault(candidate =>
            candidate.Active
            && string.Equals(candidate.ProfessionalType, professionalType, StringComparison.OrdinalIgnoreCase));

        return manifest is null
            ? null
            : new ProfessionalDisclosure(
                manifest.ProfessionalType,
                manifest.ProjectionVersion,
                manifest.DisplayName,
                manifest.Suitability,
                manifest.Skills,
                manifest.Limitations,
                manifest.AuthorityNeeds,
                manifest.CustomerRights,
                manifest.Trial,
                manifest.EvidencePosture,
                manifest.IndicativePrice,
                new ProfessionalEligibility(true, manifest.EligibilityExplanation));
    }

    private static ProfessionalCatalogManifest LoadManifest(string path)
    {
        using var stream = File.OpenRead(path);
        return JsonSerializer.Deserialize<ProfessionalCatalogManifest>(stream, JsonOptions)
            ?? throw new InvalidDataException($"Professional catalog manifest is empty: {Path.GetFileName(path)}");
    }

    private static string Normalize(string value) => value.Trim().ToLowerInvariant();

    private static bool ContainsTerm(string normalizedOutcome, string term) =>
        normalizedOutcome.Contains(Normalize(term), StringComparison.Ordinal);

    private sealed record ProfessionalCatalogManifest(
        string ProfessionalType,
        string ProjectionVersion,
        string DisplayName,
        bool Active,
        IReadOnlyList<string> SupportedOutcomeTerms,
        IReadOnlyList<string> ProhibitedOutcomeTerms,
        IReadOnlyList<string> Suitability,
        string EligibilityExplanation,
        IReadOnlyList<ProfessionalSkillDisclosure> Skills,
        IReadOnlyList<string> Limitations,
        IReadOnlyList<string> AuthorityNeeds,
        IReadOnlyList<string> CustomerRights,
        ProfessionalTrialDisclosure Trial,
        string EvidencePosture,
        IndicativePriceDisclosure IndicativePrice);
}