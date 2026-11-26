// Implements: work-contracts/WC-172-safe-to-charge-real-customers.md (Demo defect repairs: Operations Customers tab)
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using System.Globalization;
using System.Text;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services.Operations;

public static class CustomerStatuses
{
    public const string LoggedInOnly = "LOGGED_IN_ONLY";
    public const string RegistrationStarted = "REGISTRATION_STARTED";
    public const string Registered = "REGISTERED";

    public static readonly IReadOnlySet<string> All = new HashSet<string>(StringComparer.Ordinal)
    {
        LoggedInOnly,
        RegistrationStarted,
        Registered,
    };
}

/// <summary>One signed-in person as the Founder sees them: masked contact details only, never a raw email, number or key.</summary>
public sealed record CustomerDirectoryEntry(
    Guid RegistrationId,
    string? DisplayName,
    string? MaskedEmail,
    string? MaskedMobile,
    string Status,
    string RegistrationState,
    DateTimeOffset FirstSeenAt,
    DateTimeOffset LastActiveAt,
    DateTimeOffset? RegisteredAt
);

public sealed record CustomerDirectoryPage(
    IReadOnlyList<CustomerDirectoryEntry> Items,
    string? NextCursor
);

public sealed class CustomerDirectoryFilterException : Exception;

public interface ICustomerDirectory
{
    Task<CustomerDirectoryPage> ListAsync(
        string? name,
        string? contact,
        string? status,
        string? cursor,
        int? pageSize,
        CancellationToken cancellationToken
    );
}

/// <summary>
/// Who has signed in and who has registered (Operations, Customers). Reads go through one narrow, read-only database
/// capability that returns the latest registration per person, newest activity first, one page at a time (keyset, no
/// OFFSET, no total count), so the cost of a page does not grow with the number of customers.
/// </summary>
public sealed class CustomerDirectoryService(
    IdentityService identity,
    IDbContextFactory<IdentityDbContext> factory
) : ICustomerDirectory
{
    public const int DefaultPageSize = 10;
    public const int MaximumPageSize = 50;

    public async Task<CustomerDirectoryPage> ListAsync(
        string? name,
        string? contact,
        string? status,
        string? cursor,
        int? pageSize,
        CancellationToken cancellationToken
    )
    {
        name = string.IsNullOrWhiteSpace(name) ? null : name.Trim();
        contact = string.IsNullOrWhiteSpace(contact) ? null : contact.Trim();
        status = string.IsNullOrWhiteSpace(status) ? null : status.Trim();
        if (
            name is { Length: > 120 }
            || contact is { Length: > 254 }
            || (status is not null && !CustomerStatuses.All.Contains(status))
        )
            throw new CustomerDirectoryFilterException();
        var size = Math.Clamp(pageSize ?? DefaultPageSize, 1, MaximumPageSize);
        (DateTimeOffset At, Guid Id)? after = null;
        if (cursor is not null)
            after = DecodeCursor(cursor) ?? throw new CustomerDirectoryFilterException();

        string[]? domains = null;
        string[]? versions = null;
        string[]? digests = null;
        if (contact is not null)
        {
            var candidates = ContactCandidates(contact);
            if (candidates.Count > 0)
            {
                domains = candidates.Select(value => value.Domain).ToArray();
                versions = candidates.Select(value => value.Version).ToArray();
                digests = candidates.Select(value => value.Digest).ToArray();
            }
            else
                return new CustomerDirectoryPage([], null);
        }

        var likeName = name is null ? null : EscapeLike(name);
        var afterAt = after?.At;
        var afterId = after?.Id;
        var limit = size + 1;
        await using var db = await factory.CreateDbContextAsync(cancellationToken);
        var rows = await db
            .Database.SqlQuery<DirectoryRow>(
                $@"SELECT registration_id AS ""RegistrationId"", display_name AS ""DisplayName"",
                          masked_email AS ""MaskedEmail"", masked_mobile AS ""MaskedMobile"",
                          status AS ""Status"", registration_state AS ""RegistrationState"",
                          first_seen_at AS ""FirstSeenAt"", last_active_at AS ""LastActiveAt"",
                          registered_at AS ""RegisteredAt""
                   FROM identity.operator_customer_directory({likeName}, {domains}, {versions}, {digests},
                                                             {status}, {afterAt}, {afterId}, {limit})"
            )
            .ToListAsync(cancellationToken);
        var items = rows.Take(size)
            .Select(row => new CustomerDirectoryEntry(
                row.RegistrationId,
                row.DisplayName,
                row.MaskedEmail,
                row.MaskedMobile,
                row.Status,
                row.RegistrationState,
                row.FirstSeenAt,
                row.LastActiveAt,
                row.RegisteredAt
            ))
            .ToArray();
        var next =
            rows.Count > size
                ? EncodeCursor(items[^1].LastActiveAt, items[^1].RegistrationId)
                : null;
        return new CustomerDirectoryPage(items, next);
    }

    // An email has an at-sign; a number is typed with or without the leading plus and is stored in international form.
    private List<(string Domain, string Version, string Digest)> ContactCandidates(string contact)
    {
        var result = new List<(string, string, string)>();
        if (contact.Contains('@'))
        {
            foreach (var (version, digest) in identity.ComputeMatchCandidates("email", contact))
                result.Add(("email", version, digest));
            return result;
        }
        var digits = new string(contact.Where(char.IsAsciiDigit).ToArray());
        if (digits.Length is < 8 or > 15)
            return result;
        foreach (var (version, digest) in identity.ComputeMatchCandidates("mobile", "+" + digits))
            result.Add(("mobile", version, digest));
        return result;
    }

    private static string EscapeLike(string value) =>
        value.Replace("\\", "\\\\").Replace("%", "\\%").Replace("_", "\\_");

    public static string EncodeCursor(DateTimeOffset at, Guid id) =>
        Convert
            .ToBase64String(
                Encoding.UTF8.GetBytes(
                    at.UtcTicks.ToString(CultureInfo.InvariantCulture) + "|" + id.ToString("N")
                )
            )
            .TrimEnd('=')
            .Replace('+', '-')
            .Replace('/', '_');

    public static (DateTimeOffset At, Guid Id)? DecodeCursor(string cursor)
    {
        try
        {
            var padded = cursor.Replace('-', '+').Replace('_', '/');
            padded = padded.PadRight(padded.Length + ((4 - (padded.Length % 4)) % 4), '=');
            var parts = Encoding.UTF8.GetString(Convert.FromBase64String(padded)).Split('|');
            return
                parts.Length == 2
                && long.TryParse(
                    parts[0],
                    NumberStyles.None,
                    CultureInfo.InvariantCulture,
                    out var ticks
                )
                && ticks > 0
                && ticks <= DateTimeOffset.MaxValue.Ticks
                && Guid.TryParseExact(parts[1], "N", out var id)
                ? (new DateTimeOffset(ticks, TimeSpan.Zero), id)
                : null;
        }
        catch (FormatException)
        {
            return null;
        }
    }

    private sealed class DirectoryRow
    {
        public Guid RegistrationId { get; set; }
        public string? DisplayName { get; set; }
        public string? MaskedEmail { get; set; }
        public string? MaskedMobile { get; set; }
        public string Status { get; set; } = string.Empty;
        public string RegistrationState { get; set; } = string.Empty;
        public DateTimeOffset FirstSeenAt { get; set; }
        public DateTimeOffset LastActiveAt { get; set; }
        public DateTimeOffset? RegisteredAt { get; set; }
    }
}
