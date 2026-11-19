// Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R005
// Constitutional basis: C-039, C-042, C-048, C-049, C-059, C-063

using System.Collections.Concurrent;
using System.Text.RegularExpressions;
using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services.Visitor;

/// <summary>
/// Reads scripted content sets from <c>Catalog/Visitor/{contentId}.v1.json</c>. Every set is linted at load;
/// an invalid or missing set fails closed so the conversation never falls back to hardcoded text.
/// </summary>
public sealed partial class FileVisitorContentProvider(
    IOptionsMonitor<VisitorConversationOptions> options,
    ILogger<FileVisitorContentProvider> logger
) : IVisitorContentProvider
{
    private readonly ConcurrentDictionary<string, VisitorContentSet> _cache = new();

    public VisitorContentSet Get(Guid tenantId)
    {
        var current = options.CurrentValue;
        var id = current.TenantContentIds.TryGetValue(tenantId, out var mapped)
            ? mapped
            : current.DefaultContentId;
        if (!ContentIdPattern().IsMatch(id))
            throw new VisitorContentException("CONTENT_ID_INVALID");
        if (_cache.TryGetValue(id, out var cached))
            return cached;
        var path = Path.Combine(AppContext.BaseDirectory, "Catalog", "Visitor", $"{id}.v1.json");
        if (!File.Exists(path))
            throw new VisitorContentException("CONTENT_NOT_FOUND");
        VisitorContentSet content;
        try
        {
            content = VisitorContentSet.Parse(File.ReadAllText(path));
        }
        catch (System.Text.Json.JsonException)
        {
            throw new VisitorContentException("CONTENT_INVALID_JSON");
        }
        var problems = VisitorContentValidator.Validate(content, current);
        if (problems.Count > 0)
        {
            logger.LogError(
                "visitor.content.invalid contentId={ContentId} problems={Problems}",
                id,
                string.Join(",", problems.Take(10))
            );
            throw new VisitorContentException("CONTENT_INVALID");
        }
        if (!string.Equals(content.ContentId, id, StringComparison.Ordinal))
            throw new VisitorContentException("CONTENT_ID_MISMATCH");
        _cache[id] = content;
        return content;
    }

    [GeneratedRegex(@"^[a-z0-9][a-z0-9-]{0,47}$", RegexOptions.CultureInvariant)]
    private static partial Regex ContentIdPattern();
}
