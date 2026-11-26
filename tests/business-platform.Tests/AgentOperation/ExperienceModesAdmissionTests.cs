// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R001, R004, R027
// Constitutional basis: C-001, C-059, C-063, ADR-049, ADR-051

using System.Text.Json;
using System.Text.Json.Nodes;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.AgentOperation;

public sealed class ExperienceModesAdmissionTests
{
    private static JsonNode Load(string path) =>
        JsonNode.Parse(File.ReadAllText(RepositoryPaths.Resolve(path)))!;

    private static JsonNode Dma() =>
        Load("src/digital-marketing-agent/contracts/employment-interface-manifest.v1.json");

    private static JsonNode Fixture() =>
        Load("src/agent-adapters/fixture_orchard/contracts/employment-interface-manifest.v1.json");

    private static ExperienceScanResult Scan(JsonNode manifest) =>
        ExperienceManifestScanner.Scan(JsonSerializer.SerializeToElement(manifest));

    private static JsonObject Experience(JsonNode manifest) => manifest["experience"]!.AsObject();

    [Fact]
    public void DmaDeclaresThreeModesThatAdmitWithTheirEntriesLayersLevelsAndPlatforms()
    {
        var scan = Scan(Dma());

        Assert.True(scan.ExperienceCapable);
        var declaration = scan.Declaration!;
        Assert.Equal(new[] { "INDUCT", "GOALS", "OPERATIONS" }, declaration.Modes.Select(mode => mode.ModeId));
        Assert.Equal(4, declaration.PlanLevels.Count);
        Assert.Equal("FACEBOOK", declaration.Platforms[0].PlatformId);
        Assert.Equal("INSTAGRAM", declaration.Platforms[1].PlatformId);
        Assert.All(
            declaration.EventLayers.Where(layer => layer.LayerId is "RELIGION" or "POLITICS"),
            layer =>
            {
                Assert.True(layer.Sensitive);
                Assert.False(layer.DefaultOn);
            }
        );
        Assert.Contains(declaration.Modes.Single(mode => mode.ModeId == "GOALS").Gates, gate => gate.Action == "PUBLISH");
    }

    [Fact]
    public void ADeclarationWithoutModesStillAdmitsAndKeepsTheWc171Menu()
    {
        var manifest = Dma();
        foreach (var name in new[] { "modes", "eventLayers", "planLevels", "platforms", "views" })
            Experience(manifest).Remove(name);

        var scan = Scan(manifest);

        Assert.True(scan.ExperienceCapable);
        Assert.Empty(scan.Declaration!.Modes);
        Assert.NotEmpty(scan.Declaration.Navigation);
    }

    [Fact]
    public void AnotherProfessionDeclaresItsOwnModesLayersAndLevelsThroughTheSameScanner()
    {
        var scan = Scan(Fixture());

        Assert.True(scan.ExperienceCapable);
        var declaration = scan.Declaration!;
        Assert.Equal(new[] { "SEASON", "MONTH", "TASK" }, declaration.PlanLevels.Select(level => level.LevelId));
        Assert.Equal("Know my orchard", declaration.Modes.Single(mode => mode.ModeId == "INDUCT").Label);
        Assert.DoesNotContain(declaration.EventLayers, layer => layer.LayerId == "RELIGION");
    }

    [Fact]
    public void AFourthModeIsRefused()
    {
        var manifest = Dma();
        var modes = Experience(manifest)["modes"]!.AsArray();
        modes.Add(JsonNode.Parse("""{"modeId":"EXTRA","labelKey":"MODE_EXTRA","label":"Extra","readinessSource":"GOAL_COVERAGE","entries":[]}"""));

        var scan = Scan(manifest);

        Assert.False(scan.ExperienceCapable);
        Assert.Contains("EXPERIENCE_MODES_INVALID", scan.ReasonCodes);
    }

    [Fact]
    public void ADuplicateModeIsRefused()
    {
        var manifest = Dma();
        var modes = Experience(manifest)["modes"]!.AsArray();
        modes[2] = JsonNode.Parse(modes[0]!.ToJsonString());

        Assert.Contains("EXPERIENCE_MODES_DUPLICATE", Scan(manifest).ReasonCodes);
    }

    [Theory]
    [InlineData("<b>Bold</b>")]
    [InlineData("Menu {{token}}")]
    [InlineData("Back`tick")]
    public void MarkupInAModeLabelIsRefused(string label)
    {
        var manifest = Dma();
        Experience(manifest)["modes"]![0]!["label"] = label;

        Assert.Contains("EXPERIENCE_MODES_INVALID", Scan(manifest).ReasonCodes);
    }

    [Fact]
    public void AnEntryThatOpensNothingIsRefused()
    {
        var manifest = Dma();
        Experience(manifest)["modes"]![0]!["entries"]![0]!["surface"] = JsonNode.Parse("""{"kind":"KERNEL_VIEW","target":"not_a_view"}""");

        Assert.Contains("EXPERIENCE_NAVIGATION_TARGET_UNRESOLVED", Scan(manifest).ReasonCodes);
    }

    [Fact]
    public void AnEmbeddedSurfaceInAModeEntryIsRefused()
    {
        var manifest = Dma();
        Experience(manifest)["modes"]![0]!["entries"]![0]!["surface"] = JsonNode.Parse("""{"kind":"EMBEDDED","target":"x"}""");

        Assert.Contains("EXPERIENCE_NAVIGATION_SURFACE_UNSUPPORTED", Scan(manifest).ReasonCodes);
    }

    [Fact]
    public void ASensitiveLayerThatStartsOnIsRefused()
    {
        var manifest = Dma();
        var layers = Experience(manifest)["eventLayers"]!.AsArray();
        layers.Single(layer => layer!["layerId"]!.GetValue<string>() == "RELIGION")!["defaultOn"] = true;

        Assert.Contains("EXPERIENCE_EVENT_LAYERS_INVALID", Scan(manifest).ReasonCodes);
    }

    [Theory]
    [InlineData("readinessSource", "SOMETHING_ELSE")]
    [InlineData("modeId", "OPERATIONS_AND_MORE")]
    public void AnUnknownReadinessSourceOrModeIdIsRefused(string field, string value)
    {
        var manifest = Dma();
        Experience(manifest)["modes"]![2]![field] = value;

        Assert.Contains("EXPERIENCE_MODES_INVALID", Scan(manifest).ReasonCodes);
    }

    [Fact]
    public void AToolThatNamesAnUndeclaredPlanLevelOrAnUnknownCommandIsRefused()
    {
        var level = Dma();
        Experience(level)["modes"]![1]!["toolGroups"]![1]!["tools"]![0]!["planLevel"] = "NOT_A_LEVEL";
        var command = Dma();
        Experience(command)["modes"]![1]!["toolGroups"]![0]!["tools"]![0]!["command"] = "DELETE_EVERYTHING";

        Assert.Contains("EXPERIENCE_MODES_INVALID", Scan(level).ReasonCodes);
        Assert.Contains("EXPERIENCE_MODES_INVALID", Scan(command).ReasonCodes);
    }

    [Fact]
    public void ADuplicatePlatformOrAnUnknownConnectorOrViewIsRefused()
    {
        var duplicate = Dma();
        var platforms = Experience(duplicate)["platforms"]!.AsArray();
        platforms.Add(JsonNode.Parse(platforms[0]!.ToJsonString()));
        var connector = Dma();
        Experience(connector)["platforms"]![0]!["connector"] = "CUSTOM_KEYS";
        var view = Dma();
        Experience(view)["views"]!.AsArray().Add("TIMELINE");

        Assert.Contains("EXPERIENCE_PLATFORMS_INVALID", Scan(duplicate).ReasonCodes);
        Assert.Contains("EXPERIENCE_PLATFORMS_INVALID", Scan(connector).ReasonCodes);
        Assert.Contains("EXPERIENCE_VIEWS_INVALID", Scan(view).ReasonCodes);
    }
}
