// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-04
// Constitutional basis: C-023, C-059, C-063

using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services.Spend;

/// <summary>Versioned mapping from a registered interaction context to its spend purpose.</summary>
public sealed class SpendPurposeMap
{
    public const string WildcardPhase = "*";
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    private readonly Dictionary<(string ContextKey, string Phase), SpendPurpose> _entries;

    private SpendPurposeMap(Dictionary<(string, string), SpendPurpose> entries) =>
        _entries = entries;

    public int Count => _entries.Count;

    public static SpendPurposeMap LoadDefault() =>
        Parse(
            File.ReadAllText(
                Path.Combine(AppContext.BaseDirectory, "Catalog", "Spend", "purpose-map.v1.json")
            )
        );

    public static SpendPurposeMap Parse(string json)
    {
        var document =
            JsonSerializer.Deserialize<PurposeMapDocument>(json, Json)
            ?? throw new InvalidOperationException("Spend purpose map is empty.");
        if (document.SchemaVersion != "1.0" || document.Entries is not { Count: > 0 })
            throw new InvalidOperationException("Spend purpose map schema is invalid.");
        var entries = new Dictionary<(string, string), SpendPurpose>();
        foreach (var entry in document.Entries)
        {
            if (
                string.IsNullOrWhiteSpace(entry.ContextKey)
                || string.IsNullOrWhiteSpace(entry.Phase)
                || !Enum.TryParse<SpendPurpose>(entry.Purpose, false, out var purpose)
                || !Enum.IsDefined(purpose)
                || !entries.TryAdd((entry.ContextKey, entry.Phase), purpose)
            )
                throw new InvalidOperationException("Spend purpose map entry is invalid.");
        }
        return new(entries);
    }

    public SpendPurpose? Find(string? contextKey, string? phase)
    {
        if (string.IsNullOrWhiteSpace(contextKey))
            return null;
        if (
            !string.IsNullOrWhiteSpace(phase)
            && _entries.TryGetValue((contextKey, phase), out var exact)
        )
            return exact;
        return _entries.TryGetValue((contextKey, WildcardPhase), out var wildcard)
            ? wildcard
            : null;
    }

    private sealed record PurposeMapDocument(string? SchemaVersion, List<PurposeMapEntry>? Entries);

    private sealed record PurposeMapEntry(string? ContextKey, string? Phase, string? Purpose);
}
