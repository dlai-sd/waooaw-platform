// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-03
// Constitutional basis: C-001, C-059, C-063, ADR-051

using System.Text.RegularExpressions;

namespace Waooaw.BusinessPlatform.Services.Workbench;

/// <summary>
/// What one client declares it can render, read from the `X-Experience-Capabilities` header. An absent header means
/// the v1 block set (TEXT, CHOICES, LIST, LINK); blocks above the stated version are replaced by their fallback.
/// </summary>
public sealed record ChannelCapabilities(
    string Channel,
    bool Voice,
    IReadOnlyDictionary<string, int> Blocks
)
{
    public const string HeaderName = "X-Experience-Capabilities";

    private static readonly Regex HeaderPattern = new(
        "^channel=(WEB|WHATSAPP|MOBILE|API|SIMULATION)(;modality=(text|voice)(,(text|voice))*)?(;blocks=[A-Z]+:[0-9]+(,[A-Z]+:[0-9]+)*)?$",
        RegexOptions.CultureInvariant | RegexOptions.Compiled,
        TimeSpan.FromMilliseconds(100)
    );

    private static readonly IReadOnlyDictionary<string, int> V1Set = new Dictionary<string, int>(
        StringComparer.Ordinal
    )
    {
        ["TEXT"] = 1,
        ["CHOICES"] = 1,
        ["LIST"] = 1,
        ["LINK"] = 1,
    };

    public static ChannelCapabilities Default { get; } = new("WEB", false, V1Set);

    /// <summary>Whether the client renders this block type at this version.</summary>
    public bool Supports(string type, int version) =>
        Blocks.TryGetValue(type, out var highest) && version <= highest;

    /// <summary>Parses the header; returns null when it does not follow the contract pattern.</summary>
    public static ChannelCapabilities? Parse(string? header)
    {
        if (string.IsNullOrEmpty(header))
            return Default;
        if (header.Length > 512 || !HeaderPattern.IsMatch(header))
            return null;
        var channel = "WEB";
        var voice = false;
        Dictionary<string, int>? blocks = null;
        foreach (var part in header.Split(';'))
        {
            var separator = part.IndexOf('=');
            var name = part[..separator];
            var value = part[(separator + 1)..];
            switch (name)
            {
                case "channel":
                    channel = value;
                    break;
                case "modality":
                    voice = value.Split(',').Contains("voice");
                    break;
                case "blocks":
                    blocks = new Dictionary<string, int>(StringComparer.Ordinal);
                    foreach (var entry in value.Split(','))
                    {
                        var pair = entry.Split(':');
                        if (!int.TryParse(pair[1], out var version) || version < 1)
                            return null;
                        blocks[pair[0]] = Math.Max(version, blocks.GetValueOrDefault(pair[0]));
                    }
                    break;
            }
        }
        return new ChannelCapabilities(
            channel,
            voice,
            blocks ?? new Dictionary<string, int>(V1Set, StringComparer.Ordinal)
        );
    }
}
