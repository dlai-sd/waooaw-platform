// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-06
// Constitutional basis: C-001, C-059, C-063, ADR-051

using System.Text.Json;
using System.Text.Json.Nodes;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class ExperienceManifestScannerTests
{
    private static readonly OfferedEmploymentAgent Agent = new(
        "DIGITAL_MARKETING_LOCAL_SERVICE",
        "1.0.0",
        "OFFERED",
        "1.0-candidate",
        "1.1.0",
        new string('a', 64),
        "1.0.0",
        new string('b', 64)
    );

    private static JsonNode DmaManifest() =>
        JsonNode.Parse(
            File.ReadAllText(
                RepositoryPaths.Resolve(
                    "src/digital-marketing-agent/contracts/employment-interface-manifest.v1.json"
                )
            )
        )!;

    private static JsonElement Element(JsonNode node) => JsonSerializer.SerializeToElement(node);

    [Fact]
    public void DmaManifestV110_IsExperienceCompatibleAndYieldsADeclaration()
    {
        var scan = ExperienceManifestScanner.Scan(Element(DmaManifest()));

        Assert.Equal(ExperienceScanResult.Compatible, scan.State);
        Assert.True(scan.ExperienceCapable);
        Assert.Equal(new[] { "COMPATIBLE" }, scan.ReasonCodes);
        Assert.Contains(scan.Declaration!.Components, item => item.ComponentId == "CONTENT_PLAN");
        Assert.NotEmpty(scan.Declaration.GoalTypes);
        Assert.NotEmpty(scan.Declaration.Cadence);
        Assert.Contains("web", scan.Declaration.ChannelSupport.Keys);
    }

    [Fact]
    public void DmaManifestV110_PassesTheCompatibilityScanWithEvidence()
    {
        var outcome = EmploymentCompatibilityService.ScanExperience(Agent, Element(DmaManifest()));

        Assert.Equal("PASS", outcome.Result.State);
        Assert.Equal(new[] { "COMPATIBLE" }, outcome.Result.ReasonCodes);
        Assert.NotEmpty(outcome.Result.EvidenceRefs);
        Assert.Equal(ExperienceScanResult.Compatible, outcome.ExperienceState);
        Assert.Empty(outcome.Gaps);
    }

    [Fact]
    public void ManifestWithoutExperience_StaysCompatibleAsLegacyAndReportsTheGap()
    {
        var manifest = DmaManifest();
        manifest.AsObject().Remove("experience");

        var outcome = EmploymentCompatibilityService.ScanExperience(
            Agent with
            {
                ManifestVersion = "1.0.0",
            },
            Element(manifest)
        );

        Assert.Equal("PASS", outcome.Result.State);
        Assert.Equal(ExperienceScanResult.NotDeclared, outcome.ExperienceState);
        Assert.Equal(new[] { "EXPERIENCE_NOT_DECLARED" }, outcome.Gaps);
    }

    [Fact]
    public void ComponentWhoseSkillIsNotInTheCadence_FailsClosed()
    {
        var manifest = DmaManifest();
        manifest["experience"]!["components"]![0]!["skillId"] = "SKILL_THAT_DOES_NOT_EXIST";

        var outcome = EmploymentCompatibilityService.ScanExperience(Agent, Element(manifest));

        Assert.Equal("FAIL", outcome.Result.State);
        Assert.Contains("EXPERIENCE_COMPONENT_SKILL_UNRESOLVED", outcome.Result.ReasonCodes);
        Assert.Empty(outcome.Result.EvidenceRefs);
        Assert.Equal(ExperienceScanResult.Incompatible, outcome.ExperienceState);
    }

    [Fact]
    public void AvailableComponentWithoutASkillThread_FailsClosed()
    {
        var manifest = DmaManifest();
        var component = manifest["experience"]!["components"]![0]!;
        component.AsObject().Remove("skillId");
        component["availability"] = "AVAILABLE";

        var scan = ExperienceManifestScanner.Scan(Element(manifest));

        Assert.Equal(ExperienceScanResult.Incompatible, scan.State);
        Assert.Contains("EXPERIENCE_COMPONENT_THREAD_MISSING", scan.ReasonCodes);
    }

    [Fact]
    public void UnsupportedContractMajor_FailsClosed()
    {
        var manifest = DmaManifest();
        manifest["experience"]!["contractVersion"] = "2.0.0";

        var scan = ExperienceManifestScanner.Scan(Element(manifest));

        Assert.Equal(ExperienceScanResult.Incompatible, scan.State);
        Assert.Contains("EXPERIENCE_CONTRACT_VERSION_UNSUPPORTED", scan.ReasonCodes);
    }

    [Fact]
    public void DuplicateComponentIds_FailClosed()
    {
        var manifest = DmaManifest();
        manifest["experience"]!["components"]![1]!["componentId"] = "CONTENT_PLAN";

        var scan = ExperienceManifestScanner.Scan(Element(manifest));

        Assert.Contains("EXPERIENCE_COMPONENT_DUPLICATE", scan.ReasonCodes);
    }

    [Fact]
    public void ChannelWithoutTheV1BlockSet_FailsClosed()
    {
        var manifest = DmaManifest();
        manifest["experience"]!["channelSupport"]!["whatsapp"] = new JsonArray("TEXT");

        var scan = ExperienceManifestScanner.Scan(Element(manifest));

        Assert.Contains("EXPERIENCE_CHANNEL_SUPPORT_MISSING", scan.ReasonCodes);
    }

    [Theory]
    [InlineData("""{"experience": "yes"}""")]
    [InlineData("""{"experience": []}""")]
    public void NonObjectExperienceSection_FailsClosed(string json)
    {
        using var document = JsonDocument.Parse(json);

        var scan = ExperienceManifestScanner.Scan(document.RootElement.Clone());

        Assert.Equal(ExperienceScanResult.Incompatible, scan.State);
        Assert.Contains("EXPERIENCE_SECTION_INVALID", scan.ReasonCodes);
    }

    [Fact]
    public void ScanResult_PassesTheServiceCompletionRuleOnlyWhenCompatible()
    {
        var service = new EmploymentCompatibilityService();
        var agents = new[] { Agent with { ManifestVersion = "1.1.0" } };
        var request = new EmploymentCompatibilityRequest(
            "1.0",
            "1.0-candidate",
            "inventory-1",
            EmploymentCompatibilityService.InventoryDigest(agents),
            agents
        );
        var started = service.Start("caller", Guid.NewGuid(), request);
        var outcome = EmploymentCompatibilityService.ScanExperience(
            agents[0],
            Element(DmaManifest())
        );

        var completed = service.Complete(
            started.Result.ScanId,
            [outcome.Result],
            rollbackSafe: true
        );

        Assert.Equal("PASS", completed.State);
        Assert.True(completed.ActivationEligible);
    }
}
