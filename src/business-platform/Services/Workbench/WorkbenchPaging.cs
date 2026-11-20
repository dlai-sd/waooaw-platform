// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01
// Constitutional basis: C-001, C-005, C-023, C-059, C-063, ADR-051

using System.Text;

namespace Waooaw.BusinessPlatform.Services.Workbench;

/// <summary>The window of a list read: where it starts and how many items it holds.</summary>
public sealed record WorkbenchPage(int Offset, int Limit)
{
    public static WorkbenchPage First { get; } = new(0, WorkbenchPaging.DefaultLimit);
}

/// <summary>
/// Opaque cursor paging of the workbench lists. A cursor names the position after the last item returned; a cursor
/// that this service did not issue is refused rather than guessed at.
/// </summary>
public static class WorkbenchPaging
{
    public const int DefaultLimit = 25;
    public const int MaximumLimit = 100;
    private const string Prefix = "o1.";

    /// <summary>Validates the query values; <paramref name="problem"/> names the first violation.</summary>
    public static WorkbenchPage Parse(string? cursor, int? limit, out string? problem)
    {
        problem = null;
        if (cursor is not null && cursor.Length is < 1 or > 256)
            problem = "cursor must be 1 to 256 characters.";
        else if (limit is not null && (limit < 1 || limit > MaximumLimit))
            problem = "limit must be 1 to 100.";
        else if (cursor is not null && !TryDecode(cursor, out _))
            problem = "cursor is not valid.";
        else
            return new WorkbenchPage(
                cursor is null || !TryDecode(cursor, out var offset) ? 0 : offset,
                limit ?? DefaultLimit
            );
        return WorkbenchPage.First;
    }

    /// <summary>The items of the page and the cursor of the next page, or null when the page is the last.</summary>
    public static (IReadOnlyList<T> Items, string? NextCursor) Slice<T>(
        IReadOnlyList<T> all,
        WorkbenchPage page
    )
    {
        var items = all.Skip(page.Offset).Take(page.Limit).ToArray();
        var end = page.Offset + items.Length;
        return (items, end < all.Count ? Encode(end) : null);
    }

    public static string Encode(int offset) =>
        Prefix
        + Convert
            .ToBase64String(
                Encoding.ASCII.GetBytes(
                    offset.ToString(System.Globalization.CultureInfo.InvariantCulture)
                )
            )
            .TrimEnd('=')
            .Replace('+', '-')
            .Replace('/', '_');

    private static bool TryDecode(string cursor, out int offset)
    {
        offset = 0;
        if (!cursor.StartsWith(Prefix, StringComparison.Ordinal))
            return false;
        var text = cursor[Prefix.Length..].Replace('-', '+').Replace('_', '/');
        text = text.PadRight(text.Length + ((4 - (text.Length % 4)) % 4), '=');
        try
        {
            return int.TryParse(
                    Encoding.ASCII.GetString(Convert.FromBase64String(text)),
                    System.Globalization.NumberStyles.None,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out offset
                )
                && offset >= 0;
        }
        catch (FormatException)
        {
            return false;
        }
    }
}
