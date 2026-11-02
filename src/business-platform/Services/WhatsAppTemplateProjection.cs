// Implements: architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md §10.2
// Constitutional basis: C-023, C-026, C-059, C-063

using System.Text;
using System.Text.RegularExpressions;

namespace Waooaw.BusinessPlatform.Services;

public sealed record WhatsAppTemplateProjection
{
    public string Name { get; init; } = string.Empty;
    public string Version { get; init; } = string.Empty;
    public string Locale { get; init; } = string.Empty;
    public string Category { get; init; } = string.Empty;
    public string Body { get; init; } = string.Empty;

    public string[] Project(string canonicalText)
    {
        if (string.IsNullOrEmpty(Body) || Body.Length > 4096 || canonicalText.Length > 4096)
            throw Denied();
        var matches = Regex.Matches(Body, @"\{\{([1-9][0-9]*)\}\}", RegexOptions.CultureInvariant);
        if (matches.Count > 10)
            throw Denied();
        var expression = new StringBuilder(@"\A");
        var end = 0;
        var index = 1;
        foreach (Match match in matches)
        {
            var literal = Body[end..match.Index];
            if (
                match.Groups[1].Value
                    != index.ToString(System.Globalization.CultureInfo.InvariantCulture)
                || (index > 1 && literal.Length == 0)
                || literal.Contains("{{", StringComparison.Ordinal)
                || literal.Contains("}}", StringComparison.Ordinal)
            )
                throw Denied();
            expression.Append(Regex.Escape(literal)).Append("(.+?)");
            end = match.Index + match.Length;
            index++;
        }
        var suffix = Body[end..];
        if (
            suffix.Contains("{{", StringComparison.Ordinal)
            || suffix.Contains("}}", StringComparison.Ordinal)
        )
            throw Denied();
        expression.Append(Regex.Escape(suffix)).Append(@"\z");
        Match projected;
        try
        {
            projected = Regex.Match(
                canonicalText,
                expression.ToString(),
                RegexOptions.CultureInvariant | RegexOptions.Singleline,
                TimeSpan.FromMilliseconds(50)
            );
        }
        catch (RegexMatchTimeoutException)
        {
            throw Denied();
        }
        if (!projected.Success)
            throw Denied();
        var parameters = projected
            .Groups.Cast<Group>()
            .Skip(1)
            .Select(value => value.Value)
            .ToArray();
        if (
            parameters.Any(value =>
                value.Length > 1024
                || value.Any(char.IsControl)
                || value.Contains("     ", StringComparison.Ordinal)
            )
        )
            throw Denied();
        return parameters;
    }

    private static WhatsAppCapabilityUnavailableException Denied() =>
        new("TEMPLATE_PROJECTION_DENIED");
}
