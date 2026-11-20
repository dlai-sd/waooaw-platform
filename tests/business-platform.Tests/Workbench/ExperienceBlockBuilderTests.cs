// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-03
// Constitutional basis: C-001, C-059, C-063, ADR-051

using System.Text.Json;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class ExperienceBlockBuilderTests
{
    private static readonly Guid RelationshipId = Guid.Parse(
        "11111111-2222-3333-4444-555555555555"
    );

    private static ChannelCapabilities Capabilities(string header) =>
        ChannelCapabilities.Parse(header) ?? throw new InvalidOperationException("header rejected");

    private static WorkbenchDecision Decision(
        string confirm = "Approve plan",
        string cancel = "Not now"
    ) =>
        new(
            Guid.NewGuid(),
            "v1",
            "Start the agreed plan.",
            "Customer approval",
            "5 content drafts",
            confirm,
            cancel,
            null,
            null,
            "Platform",
            "CURRENT"
        );

    private static WorkbenchBlockInput Input(params WorkbenchDecision[] decisions) =>
        new(
            RelationshipId,
            WorkbenchAudiences.CustomerOwner,
            "OPERATIONS",
            new WorkbenchReadiness("READY", "AGREED", "ACTIVE", "NOT_STARTED"),
            decisions,
            [],
            null,
            ["Owner data is late."],
            new WorkbenchRecommendedAction(
                "resolve_decision",
                "Review the decision",
                "One item waits for you."
            )
        );

    [Fact]
    public void Parse_AbsentHeader_IsTheV1Set()
    {
        var parsed = ChannelCapabilities.Parse(null);

        Assert.NotNull(parsed);
        Assert.True(parsed!.Supports("TEXT", 1));
        Assert.False(parsed.Supports("DECISION", 1));
        Assert.False(parsed.Supports("TEXT", 2));
    }

    [Theory]
    [InlineData("channel=FAX")]
    [InlineData("channel=WEB;blocks=text:1")]
    [InlineData("channel=WEB;blocks=TEXT:0")]
    [InlineData("blocks=TEXT:1")]
    public void Parse_RejectsHeadersThatBreakTheContractPattern(string header) =>
        Assert.Null(ChannelCapabilities.Parse(header));

    [Fact]
    public void Parse_ReadsChannelModalityAndBlockVersions()
    {
        var parsed = Capabilities("channel=WHATSAPP;modality=text,voice;blocks=TEXT:1,DECISION:1");

        Assert.Equal("WHATSAPP", parsed.Channel);
        Assert.True(parsed.Voice);
        Assert.True(parsed.Supports("DECISION", 1));
        Assert.False(parsed.Supports("DECISION", 2));
        Assert.False(parsed.Supports("STATUS", 1));
    }

    [Fact]
    public void Build_ForV1Client_ReplacesRichBlocksWithFallbackAndKeepsTheLinkLast()
    {
        var blocks = ExperienceBlockBuilder.Build(Input(Decision()), ChannelCapabilities.Default);

        Assert.All(
            blocks,
            block => Assert.Contains(block.Type, new[] { "TEXT", "CHOICES", "LIST", "LINK" })
        );
        Assert.Equal("LINK", blocks[^1].Type);
        Assert.Single(blocks, block => block.Type == "LINK");
        Assert.Contains(blocks, block => block.Type == "CHOICES");
        Assert.True(blocks.Count <= ExperienceBlockBuilder.MaxBlocks);
    }

    [Fact]
    public void Build_ForClientThatRendersDecision_KeepsTheDecisionBlockWithItsFallback()
    {
        var blocks = ExperienceBlockBuilder.Build(
            Input(Decision()),
            Capabilities("channel=WEB;blocks=TEXT:1,CHOICES:1,LIST:1,LINK:1,STATUS:1,DECISION:1")
        );

        var decision = Assert.Single(blocks, block => block.Type == "DECISION");
        Assert.Equal(2, decision.Fallback.Count);
        Assert.Equal("TEXT", decision.Fallback[0].Type);
        Assert.Equal("CHOICES", decision.Fallback[1].Type);
    }

    [Fact]
    public void Negotiate_ReplacesABlockAboveTheClientMaximumVersionWithItsFallback()
    {
        var data = JsonSerializer.SerializeToElement(new { text = "Plan agreed." });
        var block = new ExperienceBlock(
            "status",
            "STATUS",
            2,
            "CUSTOMER",
            data,
            [new ExperienceFallbackBlock("TEXT", data)]
        );

        var result = ExperienceBlockBuilder.Negotiate(
            [block],
            Capabilities("channel=WEB;blocks=TEXT:1,STATUS:1")
        );

        var only = Assert.Single(result);
        Assert.Equal("TEXT", only.Type);
    }

    [Fact]
    public void Negotiate_KeepsOneLinkAndAtMostSixBlocks()
    {
        var data = JsonSerializer.SerializeToElement(new { text = "x" });
        var blocks = Enumerable
            .Range(0, 9)
            .Select(index => new ExperienceBlock($"text-{index}", "TEXT", 1, "PUBLIC", data, []))
            .Append(ExperienceBlockBuilder.LinkBlock(RelationshipId, ChannelCapabilities.Default))
            .Append(ExperienceBlockBuilder.LinkBlock(RelationshipId, ChannelCapabilities.Default))
            .ToArray();

        var result = ExperienceBlockBuilder.Negotiate(blocks, ChannelCapabilities.Default);

        Assert.Equal(ExperienceBlockBuilder.MaxBlocks, result.Count);
        Assert.Single(result, block => block.Type == "LINK");
        Assert.Equal("LINK", result[^1].Type);
    }

    [Fact]
    public void DecisionChoices_AreThreeUniqueLabelsWithinTheLimit()
    {
        var block = ExperienceBlockBuilder.DecisionBlock(
            Decision(
                "Approve the whole quarterly plan now",
                "Approve the whole quarterly plan now"
            ),
            ChannelCapabilities.Default
        );

        var choices = block.Fallback[1].Data.GetProperty("choices").EnumerateArray().ToArray();
        var labels = choices.Select(choice => choice.GetProperty("label").GetString()!).ToArray();
        Assert.Equal(3, choices.Length);
        Assert.All(
            labels,
            label => Assert.InRange(label.Length, 1, ExperienceBlockBuilder.MaxChoiceLabel)
        );
        Assert.Equal(3, labels.Distinct(StringComparer.OrdinalIgnoreCase).Count());
        Assert.StartsWith("approve:", choices[0].GetProperty("choiceId").GetString());
        Assert.StartsWith("decline:", choices[1].GetProperty("choiceId").GetString());
        Assert.StartsWith("defer:", choices[2].GetProperty("choiceId").GetString());
    }

    [Fact]
    public void DecisionMeaning_IsTheSameOnWebAndWhatsApp()
    {
        var web = ExperienceBlockBuilder.Build(Input(Decision()), ChannelCapabilities.Default);
        var whatsapp = ExperienceBlockBuilder.Build(
            Input(Decision()),
            Capabilities("channel=WHATSAPP;blocks=TEXT:1,CHOICES:1,LIST:1,LINK:1")
        );

        string[] Labels(IEnumerable<ExperienceBlock> blocks) =>
            blocks
                .Where(block => block.Type == "CHOICES")
                .SelectMany(block => block.Data.GetProperty("choices").EnumerateArray())
                .Select(choice => choice.GetProperty("label").GetString()!)
                .ToArray();

        Assert.Equal(Labels(web), Labels(whatsapp));
        Assert.Equal(3, Labels(web).Length);
    }

    [Fact]
    public void Spoken_IsPresentAndBoundedOnlyForVoiceClients()
    {
        var voice = ExperienceBlockBuilder.Build(
            Input(Decision()),
            new ChannelCapabilities("WEB", true, ChannelCapabilities.Default.Blocks)
        );
        var text = ExperienceBlockBuilder.Build(Input(Decision()), ChannelCapabilities.Default);

        Assert.Contains(voice, block => block.Spoken is not null);
        Assert.All(
            voice.Where(block => block.Spoken is not null),
            block => Assert.True(block.Spoken!.Length <= ExperienceBlockBuilder.MaxText)
        );
        Assert.All(text, block => Assert.Null(block.Spoken));
    }

    [Fact]
    public void Build_ForBeneficiary_OmitsDecisionsThatOnlyOwnersMayTake()
    {
        var input = Input(Decision()) with { Audience = WorkbenchAudiences.Beneficiary };

        var blocks = ExperienceBlockBuilder.Build(input, ChannelCapabilities.Default);

        Assert.DoesNotContain(blocks, block => block.Type == "CHOICES");
    }

    private static ExperienceGoalType GoalType(string id, params string[] parameters) =>
        new(id, parameters, [], [], ["Grow my reach"]);

    [Fact]
    public void Build_OffersADeclaredGoalAsAFormOnlyToAudiencesThatMayDecide()
    {
        var starters = new[] { GoalType("grow", "audience", "channel"), GoalType("no-parameters") };
        var web = Capabilities("channel=WEB;blocks=TEXT:1,CHOICES:1,LIST:1,LINK:1,FORM:1");

        var owner = ExperienceBlockBuilder.Build(Input() with { GoalStarters = starters }, web);
        var beneficiary = ExperienceBlockBuilder.Build(
            Input() with
            {
                Audience = WorkbenchAudiences.Beneficiary,
                GoalStarters = starters,
            },
            web
        );

        var form = Assert.Single(owner, block => block.Type == "FORM");
        Assert.Equal("goal-form-grow", form.Id);
        Assert.Equal("Grow my reach", form.Label);
        Assert.Equal("goal:grow", form.Data.GetProperty("formId").GetString());
        Assert.Equal(
            new[] { "audience", "channel" },
            form.Data.GetProperty("fields")
                .EnumerateArray()
                .Select(field => field.GetProperty("fieldId").GetString()!)
                .ToArray()
        );
        Assert.DoesNotContain(beneficiary, block => block.Type == "FORM");
        Assert.Equal("LINK", owner[^1].Type);
    }

    [Fact]
    public void GoalFormBlock_ForAClientWithoutForms_DegradesToTextThatPointsToTheWorkbench()
    {
        var blocks = ExperienceBlockBuilder.Build(
            Input() with
            {
                GoalStarters = [GoalType("grow", "audience")],
            },
            ChannelCapabilities.Default
        );

        Assert.DoesNotContain(blocks, block => block.Type == "FORM");
        Assert.Contains(
            blocks,
            block =>
                block.Type == "TEXT"
                && block.Data.GetProperty("text").GetString()!.Contains("Open the workbench")
        );
    }
}
