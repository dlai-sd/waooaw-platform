// Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R006, WC135-R009
// Constitutional basis: C-009, C-023, C-026, C-048, C-049, C-059, C-063

using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services.Visitor;

/// <summary>
/// Projects a structured visitor reply onto WhatsApp: a canonical plain-text message that is always valid on its own,
/// plus an optional interactive payload (buttons, list or link button) built from the same reply.
/// </summary>
public static class VisitorWhatsAppRenderer
{
    public const int MaximumBodyLength = 1024;
    public const int MaximumButtons = 3;
    public const int MaximumRows = 10;
    public const int MaximumLabelLength = 20;
    public const int MaximumRowTitleLength = 24;
    public const int MaximumRowDescriptionLength = 72;

    /// <summary>The canonical text: every TEXT block, then a plain link line for each LINK block.</summary>
    public static string CanonicalText(VisitorReply reply)
    {
        var parts = new List<string>();
        foreach (var block in reply.Blocks)
        {
            if (block.Type == "TEXT" && !string.IsNullOrWhiteSpace(block.Text))
                parts.Add(block.Text);
            else if (block.Type == "LINK" && !string.IsNullOrWhiteSpace(block.Url))
                parts.Add($"{block.Label}: {block.Url}".Trim(' ', ':'));
        }
        return string.Join("\n\n", parts);
    }

    /// <summary>Builds the interactive part of a WhatsApp message, or null when plain text is the right rendering.</summary>
    public static object? Interactive(VisitorReply reply)
    {
        var body = string.Join(
            "\n\n",
            reply
                .Blocks.Where(block =>
                    block.Type == "TEXT" && !string.IsNullOrWhiteSpace(block.Text)
                )
                .Select(block => block.Text)
        );
        var choices = reply.Blocks.FirstOrDefault(block => block.Type == "CHOICES")?.Choices;
        var list = reply.Blocks.FirstOrDefault(block => block.Type == "LIST");
        var link = reply.Blocks.FirstOrDefault(block => block.Type == "LINK");
        var canonical = CanonicalText(reply);

        if (
            choices is { Count: > 0 and <= MaximumButtons }
            && Valid(choices.Select(c => c.Label), MaximumLabelLength)
        )
        {
            if (canonical.Length is 0 or > MaximumBodyLength)
                return null;
            return new
            {
                type = "interactive",
                interactive = new
                {
                    type = "button",
                    body = new { text = canonical },
                    action = new
                    {
                        buttons = choices
                            .Select(choice => new
                            {
                                type = "reply",
                                reply = new { id = choice.Id, title = choice.Label },
                            })
                            .ToArray(),
                    },
                },
            };
        }

        if (
            list?.Rows is { Count: > 0 and <= MaximumRows } rows
            && Valid(rows.Select(row => row.Title), MaximumRowTitleLength)
            && rows.All(row => (row.Description?.Length ?? 0) <= MaximumRowDescriptionLength)
            && !string.IsNullOrWhiteSpace(list.ListTitle)
            && list.ListTitle.Length <= MaximumLabelLength
        )
        {
            if (canonical.Length is 0 or > MaximumBodyLength)
                return null;
            return new
            {
                type = "interactive",
                interactive = new
                {
                    type = "list",
                    body = new { text = canonical },
                    action = new
                    {
                        button = list.ListTitle,
                        sections = new[]
                        {
                            new
                            {
                                title = "Options",
                                rows = rows.Select(row => new
                                    {
                                        id = row.Id,
                                        title = row.Title,
                                        description = row.Description,
                                    })
                                    .ToArray(),
                            },
                        },
                    },
                },
            };
        }

        if (
            link
                is {
                    Url: { Length: > 0 } url,
                    Label: { Length: > 0 and <= MaximumLabelLength } label
                }
            && Uri.TryCreate(url, UriKind.Absolute, out var uri)
            && uri.Scheme == Uri.UriSchemeHttps
            && body.Length is > 0 and <= MaximumBodyLength
        )
            return new
            {
                type = "interactive",
                interactive = new
                {
                    type = "cta_url",
                    body = new { text = body },
                    action = new
                    {
                        name = "cta_url",
                        parameters = new { display_text = label, url },
                    },
                },
            };
        return null;
    }

    private static bool Valid(IEnumerable<string> labels, int maximum)
    {
        var values = labels.ToList();
        return values.All(value => !string.IsNullOrWhiteSpace(value) && value.Length <= maximum)
            && values.Distinct(StringComparer.OrdinalIgnoreCase).Count() == values.Count;
    }

    public static VisitorReply? ParseReply(string json)
    {
        try
        {
            return JsonSerializer.Deserialize<VisitorReply>(json);
        }
        catch (JsonException)
        {
            return null;
        }
    }
}
