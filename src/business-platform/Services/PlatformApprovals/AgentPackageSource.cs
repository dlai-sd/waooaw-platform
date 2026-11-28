// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R007
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using System.Text.Json;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Services.PlatformApprovals;

/// <summary>One skill of an agent package with the identifiers a runtime binding records.</summary>
public sealed record AgentPackageSkill(
    string SkillId,
    string SkillVersion,
    string PromptVersion,
    string PromptDigest,
    string InputSchemaDigest,
    string OutputSchemaDigest
);

/// <summary>An agent package as shipped with the platform: its admission content and the skills it declares.</summary>
public sealed record AgentPackage(
    string ProfessionalType,
    string ProfessionalVersion,
    string ContractSchemaVersion,
    string ContentJson,
    string ContentDigest,
    string SpecificationRevision,
    string SpecificationDigest,
    IReadOnlyList<AgentPackageSkill> Skills
);

public interface IAgentPackageSource
{
    AgentPackage? Find(string professionalType, string professionalVersion);
}

/// <summary>
/// Reads the agent packages shipped in the image. The package carries skill ids, versions and schema digests but no
/// separate prompt digest, so a skill without a declared conversation operation takes its prompt version from the skill
/// version and its prompt digest from the canonical form of its own manifest entry. Input and output digests are the
/// configuration and compatibility schema digests the package declares. A skill with a conversation operation uses the
/// digests that operation declares, so the resolver's later match against the operation holds.
/// </summary>
public sealed class FileAgentPackageSource : IAgentPackageSource
{
    private readonly IReadOnlyList<AgentPackage> packages;

    public FileAgentPackageSource(string directory)
    {
        packages = Directory.Exists(directory)
            ? Directory
                .EnumerateFiles(directory, "*.json")
                .Order(StringComparer.Ordinal)
                .Select(Load)
                .OfType<AgentPackage>()
                .ToArray()
            : [];
    }

    public AgentPackage? Find(string professionalType, string professionalVersion) =>
        packages.FirstOrDefault(value =>
            value.ProfessionalType == professionalType
            && value.ProfessionalVersion == professionalVersion
        );

    private static AgentPackage? Load(string path)
    {
        using var document = JsonDocument.Parse(File.ReadAllBytes(path));
        var root = document.RootElement;
        if (
            !root.TryGetProperty("professionalIdentity", out var identity)
            || !root.TryGetProperty("skillManifest", out var manifest)
            || manifest.ValueKind != JsonValueKind.Array
        )
            return null;
        var specification = identity.GetProperty("agentSpecification");
        var skills = manifest.EnumerateArray().Select(skill => SkillOf(skill)).ToArray();
        return new AgentPackage(
            identity.GetProperty("professionalTypeId").GetString() ?? string.Empty,
            identity.GetProperty("professionalVersion").GetString() ?? string.Empty,
            root.TryGetProperty("contractSchemaVersion", out var schema)
                ? schema.GetString() ?? string.Empty
                : string.Empty,
            AgentAdmissionCanonicalizer.Canonicalize(root),
            AgentAdmissionCanonicalizer.Digest(root),
            specification.GetProperty("version").GetString() ?? string.Empty,
            specification.GetProperty("digest").GetString() ?? string.Empty,
            skills
        );
    }

    private static AgentPackageSkill SkillOf(JsonElement skill)
    {
        var id = skill.GetProperty("skillId").GetString() ?? string.Empty;
        var version = skill.GetProperty("skillVersion").GetString() ?? string.Empty;
        if (skill.TryGetProperty("conversationOperation", out var operationJson))
        {
            var operation = ConversationOperationBindingV1.Parse(operationJson);
            return new AgentPackageSkill(
                id,
                version,
                operation.PromptPolicy.Version,
                operation.PromptPolicy.Digest,
                operation.InputSchemaDigest,
                operation.OutputSchemaDigest
            );
        }
        return new AgentPackageSkill(
            id,
            version,
            version,
            AgentAdmissionCanonicalizer.Digest(skill),
            skill.GetProperty("configurationSchema").GetProperty("schemaDigest").GetString()
                ?? string.Empty,
            skill.GetProperty("compatibility").GetProperty("schemaDigest").GetString()
                ?? string.Empty
        );
    }
}
