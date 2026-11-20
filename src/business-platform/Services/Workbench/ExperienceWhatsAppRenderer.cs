// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-03
// Constitutional basis: C-001, C-009, C-023, C-059, C-063, ADR-051

using System.Text.Json;
using Waooaw.BusinessPlatform.Services.Visitor;

namespace Waooaw.BusinessPlatform.Services.Workbench;

/// <summary>
/// Renders the negotiated workbench blocks as the plain text of one WhatsApp reply. Blocks WhatsApp cannot show are
/// replaced by their declared fallback; consequential choices are named but never offered as buttons, because
/// WhatsApp phone identity cannot authorise them - the reply points to the workbench through a single-use link.
/// </summary>
public static class ExperienceWhatsAppRenderer
{
    public const string NoLinkLine = "Open the workbench in the secure portal to continue.";

    private static readonly HashSet<string> Native = new(StringComparer.Ordinal)
    {
        "TEXT",
        "CHOICES",
        "LIST",
        "LINK",
    };

    public static string Render(IReadOnlyList<ExperienceBlock> blocks, string? handoffUrl)
    {
        var parts = new List<string>();
        var optionsSeen = false;
        var linkLabel = ExperienceBlockBuilder.WorkbenchLinkLabel;
        foreach (var (type, data) in Flatten(blocks))
        {
            switch (type)
            {
                case "TEXT" when Text(data, "text") is { } text:
                    parts.Add(text);
                    break;
                case "CHOICES" when !optionsSeen && Labels(data) is { Count: > 0 } labels:
                    optionsSeen = true;
                    parts.Add($"Choices in the workbench: {string.Join(" · ", labels)}");
                    break;
                case "LIST" when Rows(data) is { Count: > 0 } rows:
                    parts.Add(string.Join("\n", rows));
                    break;
                case "LINK" when Text(data, "label") is { } label:
                    linkLabel = ExperienceBlockBuilder.Clip(
                        label,
                        VisitorWhatsAppRenderer.MaximumLabelLength
                    );
                    break;
            }
        }

        var link =
            Uri.TryCreate(handoffUrl, UriKind.Absolute, out var uri)
            && (uri.Scheme == Uri.UriSchemeHttps || uri.Scheme == Uri.UriSchemeHttp)
                ? VisitorReplyBlock.LinkBlock(linkLabel, uri.AbsoluteUri)
                : null;
        var tail = link is null ? NoLinkLine : $"{link.Label}: {link.Url}";
        var room = Math.Max(0, VisitorWhatsAppRenderer.MaximumBodyLength - tail.Length - 2);
        var body = ExperienceBlockBuilder.Clip(string.Join("\n\n", parts), room);
        var reply = new List<VisitorReplyBlock>();
        if (body.Length > 0)
            reply.Add(VisitorReplyBlock.TextBlock(body));
        reply.Add(link ?? VisitorReplyBlock.TextBlock(tail));
        return VisitorWhatsAppRenderer.CanonicalText(new VisitorReply { Blocks = reply });
    }

    private static IEnumerable<(string Type, JsonElement Data)> Flatten(
        IReadOnlyList<ExperienceBlock> blocks
    )
    {
        foreach (var block in blocks)
        {
            if (Native.Contains(block.Type))
            {
                yield return (block.Type, block.Data);
                continue;
            }
            foreach (var fallback in block.Fallback.Where(item => Native.Contains(item.Type)))
                yield return (fallback.Type, fallback.Data);
        }
    }

    private static string? Text(JsonElement data, string name) =>
        data.ValueKind == JsonValueKind.Object
        && data.TryGetProperty(name, out var value)
        && value.ValueKind == JsonValueKind.String
        && !string.IsNullOrWhiteSpace(value.GetString())
            ? value.GetString()!.Trim()
            : null;

    private static List<string> Labels(JsonElement data) =>
        Items(data, "choices")
            .Select(item => Text(item, "label"))
            .Where(label => label is not null)
            .Take(VisitorWhatsAppRenderer.MaximumButtons)
            .Select(label => label!)
            .ToList();

    private static List<string> Rows(JsonElement data) =>
        Items(data, "rows")
            .Select(item => (Title: Text(item, "title"), Description: Text(item, "description")))
            .Where(row => row.Title is not null)
            .Take(VisitorWhatsAppRenderer.MaximumRows)
            .Select(row =>
                row.Description is null ? $"- {row.Title}" : $"- {row.Title}: {row.Description}"
            )
            .ToList();

    private static List<JsonElement> Items(JsonElement data, string name) =>
        data.ValueKind == JsonValueKind.Object
        && data.TryGetProperty(name, out var array)
        && array.ValueKind == JsonValueKind.Array
            ? array.EnumerateArray().ToList()
            : new List<JsonElement>();
}
