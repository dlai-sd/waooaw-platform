// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-03
// Constitutional basis: C-001, C-009, C-023, C-059, C-063, ADR-051

using System.Text.Json;
using Waooaw.BusinessPlatform.Services.Visitor;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class ExperienceWhatsAppRendererTests
{
    private static ExperienceBlock Block(
        string type,
        object data,
        params ExperienceFallbackBlock[] fallback
    ) =>
        new(
            $"{type.ToLowerInvariant()}-1",
            type,
            1,
            "CUSTOMER",
            JsonSerializer.SerializeToElement(
                data,
                new JsonSerializerOptions(JsonSerializerDefaults.Web)
            ),
            fallback
        );

    private static ExperienceFallbackBlock Fallback(string type, object data) =>
        new(
            type,
            JsonSerializer.SerializeToElement(
                data,
                new JsonSerializerOptions(JsonSerializerDefaults.Web)
            )
        );

    [Fact]
    public void Render_ShowsTextChoicesAndTheHandoffLinkInsteadOfTheWorkbenchReference()
    {
        var blocks = new[]
        {
            Block("TEXT", new { text = "Plan agreed." }),
            Block(
                "CHOICES",
                new
                {
                    choices = new[]
                    {
                        new { choiceId = "a", label = "Approve" },
                        new { choiceId = "b", label = "Not now" },
                    },
                }
            ),
            Block("LINK", new { label = "Open workbench", destinationRef = "workbench:abc" }),
        };

        var text = ExperienceWhatsAppRenderer.Render(
            blocks,
            "https://portal.example/relationships/1?handoff=t"
        );

        Assert.Contains("Plan agreed.", text);
        Assert.Contains("Choices in the workbench: Approve · Not now", text);
        Assert.EndsWith("Open workbench: https://portal.example/relationships/1?handoff=t", text);
        Assert.DoesNotContain("workbench:abc", text);
    }

    [Fact]
    public void Render_FlattensBlocksWhatsAppCannotShowToTheirFallback()
    {
        var blocks = new[]
        {
            Block(
                "DECISION",
                new { effect = "x" },
                Fallback("TEXT", new { text = "Start the plan. Authority: you." })
            ),
        };

        var text = ExperienceWhatsAppRenderer.Render(blocks, "https://portal.example/r?handoff=t");

        Assert.Contains("Start the plan. Authority: you.", text);
        Assert.DoesNotContain("DECISION", text);
    }

    [Fact]
    public void Render_ListsRowsAndSkipsEmptyOnes()
    {
        var blocks = new[]
        {
            Block(
                "LIST",
                new
                {
                    rows = new[]
                    {
                        new
                        {
                            rowId = "1",
                            title = "First",
                            description = "one",
                        },
                        new
                        {
                            rowId = "2",
                            title = "Second",
                            description = "",
                        },
                    },
                }
            ),
        };

        var text = ExperienceWhatsAppRenderer.Render(blocks, null);

        Assert.Contains("- First: one", text);
        Assert.Contains("- Second", text);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("javascript:alert(1)")]
    [InlineData("ftp://portal.example/x")]
    [InlineData("/relative/path")]
    public void Render_WithoutAUsableHandoffUrl_PointsToTheSecurePortalInstead(string? url)
    {
        var text = ExperienceWhatsAppRenderer.Render([Block("TEXT", new { text = "Hello." })], url);

        Assert.Contains(ExperienceWhatsAppRenderer.NoLinkLine, text);
        Assert.DoesNotContain("javascript", text);
        Assert.DoesNotContain("ftp://", text);
    }

    [Fact]
    public void Render_KeepsTheReplyWithinTheWhatsAppBodyLimitAndKeepsTheLink()
    {
        var long_ = new string('a', 4000);
        var text = ExperienceWhatsAppRenderer.Render(
            [Block("TEXT", new { text = long_ })],
            "https://portal.example/relationships/1?handoff=t"
        );

        Assert.True(text.Length <= VisitorWhatsAppRenderer.MaximumBodyLength);
        Assert.EndsWith("handoff=t", text);
    }
}
