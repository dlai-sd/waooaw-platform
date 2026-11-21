// Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R002, WC135-R004
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C2-03
// Constitutional basis: C-009, C-039, C-042, C-048, C-049, C-059, C-063

using System.Text.Json;
using System.Text.Json.Serialization;

namespace Waooaw.BusinessPlatform.Services.Visitor;

public static class VisitorStates
{
    public const string New = "NEW";
    public const string ConsentPending = "CONSENT_PENDING";
    public const string Discover = "DISCOVER";
    public const string Qualify = "QUALIFY";
    public const string ChooseProfessional = "CHOOSE_PROFESSIONAL";
    public const string ProfessionalCard = "PROFESSIONAL_CARD";
    public const string ShowValue = "SHOW_VALUE";
    public const string OtherProfessionals = "OTHER_PROFESSIONALS";
    public const string Handoff = "HANDOFF";
    public const string Stopped = "STOPPED";

    public static readonly IReadOnlySet<string> All = new HashSet<string>(StringComparer.Ordinal)
    {
        New,
        ConsentPending,
        Discover,
        Qualify,
        ChooseProfessional,
        ProfessionalCard,
        ShowValue,
        OtherProfessionals,
        Handoff,
        Stopped,
    };
}

public static class VisitorOutcomes
{
    public const string None = "NONE";
    public const string Lead = "LEAD";
    public const string Intent = "INTENT";
    public const string FullSuccess = "FULL_SUCCESS";
    public const string OptOut = "OPT_OUT";
}

public static class VisitorChannels
{
    public const string WhatsApp = "WHATSAPP";
    public const string Web = "WEB";
    public const string Mobile = "MOBILE";
    public const string Simulation = "SIMULATION";

    public static bool IsEndpointChannel(string channel) => channel is Web or Mobile or Simulation;
}

public sealed record VisitorChoice(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("label")] string Label
);

public sealed record VisitorListRow(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("title")] string Title,
    [property: JsonPropertyName("description")]
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? Description = null
);

/// <summary>One block of a structured reply: TEXT, CHOICES, LIST or LINK.</summary>
public sealed record VisitorReplyBlock
{
    [JsonPropertyName("type")]
    public string Type { get; init; } = "TEXT";

    [JsonPropertyName("text")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Text { get; init; }

    [JsonPropertyName("choices")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public IReadOnlyList<VisitorChoice>? Choices { get; init; }

    [JsonPropertyName("listTitle")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? ListTitle { get; init; }

    [JsonPropertyName("rows")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public IReadOnlyList<VisitorListRow>? Rows { get; init; }

    [JsonPropertyName("label")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Label { get; init; }

    [JsonPropertyName("url")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Url { get; init; }

    public static VisitorReplyBlock TextBlock(string text) => new() { Type = "TEXT", Text = text };

    public static VisitorReplyBlock ChoicesBlock(params VisitorChoice[] choices) =>
        new() { Type = "CHOICES", Choices = choices };

    public static VisitorReplyBlock LinkBlock(string label, string url) =>
        new()
        {
            Type = "LINK",
            Label = label,
            Url = url,
        };
}

/// <summary>The structured reply every channel renders (WC135-R004).</summary>
public sealed record VisitorReply
{
    public const string SchemaVersion = "1.0";
    public const string SchemaVersionV2 = "2.0";

    public static readonly IReadOnlySet<string> AcceptedSchemaVersions = new HashSet<string>(
        StringComparer.Ordinal
    )
    {
        SchemaVersion,
        SchemaVersionV2,
    };

    [JsonPropertyName("schemaVersion")]
    public string Schema { get; init; } = SchemaVersion;

    [JsonPropertyName("state")]
    public string State { get; init; } = VisitorStates.New;

    [JsonPropertyName("contentVersion")]
    public string ContentVersion { get; init; } = string.Empty;

    [JsonPropertyName("blocks")]
    public IReadOnlyList<VisitorReplyBlock> Blocks { get; init; } = [];

    public static VisitorReply Empty(string state, string contentVersion) =>
        new() { State = state, ContentVersion = contentVersion };

    /// <summary>Plain text of every TEXT block, for channels that cannot render structure.</summary>
    public string PlainText() =>
        string.Join(
            "\n\n",
            Blocks
                .Where(block => block.Type == "TEXT" && !string.IsNullOrWhiteSpace(block.Text))
                .Select(block => block.Text)
        );

    public string ToJson() => JsonSerializer.Serialize(this, VisitorJson.Options);

    public static VisitorReply FromJson(string json) =>
        JsonSerializer.Deserialize<VisitorReply>(json, VisitorJson.Options)
        ?? throw new JsonException("Visitor reply is empty.");
}

public static class VisitorJson
{
    public static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web)
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.Never,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
    };
}

/// <summary>Enforces the structural limits of the reply model before any renderer sees it.</summary>
public static class VisitorReplyValidator
{
    public static IReadOnlyList<string> Validate(
        VisitorReply reply,
        VisitorConversationOptions limits
    )
    {
        var problems = new List<string>();
        if (!VisitorReply.AcceptedSchemaVersions.Contains(reply.Schema))
            problems.Add("SCHEMA_VERSION_UNSUPPORTED");
        if (!VisitorStates.All.Contains(reply.State))
            problems.Add("STATE_UNKNOWN");
        if (reply.Blocks.Count > 6)
            problems.Add("TOO_MANY_BLOCKS");
        var choiceBlocks = 0;
        var listBlocks = 0;
        var linkBlocks = 0;
        foreach (var block in reply.Blocks)
        {
            switch (block.Type)
            {
                case "TEXT":
                    if (string.IsNullOrWhiteSpace(block.Text))
                        problems.Add("TEXT_EMPTY");
                    else if (block.Text.Length > limits.MaxTextBodyLength)
                        problems.Add("TEXT_TOO_LONG");
                    break;
                case "CHOICES":
                    choiceBlocks++;
                    ValidateChoices(block, limits, problems);
                    break;
                case "LIST":
                    listBlocks++;
                    ValidateList(block, limits, problems);
                    break;
                case "LINK":
                    linkBlocks++;
                    if (
                        string.IsNullOrWhiteSpace(block.Label)
                        || block.Label.Length > limits.MaxChoiceLabelLength
                        || !Uri.TryCreate(block.Url, UriKind.Absolute, out var url)
                        || url.Scheme != Uri.UriSchemeHttps
                    )
                        problems.Add("LINK_INVALID");
                    break;
                default:
                    problems.Add("BLOCK_TYPE_UNKNOWN");
                    break;
            }
        }
        if (choiceBlocks + listBlocks > 1)
            problems.Add("MULTIPLE_CHOICE_SETS");
        if (linkBlocks > 1)
            problems.Add("MULTIPLE_LINKS");
        var textBlocks = reply.Blocks.Where(block => block.Type == "TEXT").ToList();
        if (choiceBlocks + listBlocks + linkBlocks > 0 && textBlocks.Count == 0)
            problems.Add("INTERACTIVE_WITHOUT_BODY");
        if (
            choiceBlocks + listBlocks + linkBlocks > 0
            && textBlocks.Sum(block => block.Text?.Length ?? 0) > limits.MaxInteractiveBodyLength
        )
            problems.Add("INTERACTIVE_BODY_TOO_LONG");
        return problems;
    }

    private static void ValidateChoices(
        VisitorReplyBlock block,
        VisitorConversationOptions limits,
        List<string> problems
    )
    {
        var choices = block.Choices ?? [];
        if (choices.Count == 0 || choices.Count > limits.MaxChoiceButtons)
            problems.Add("CHOICE_COUNT");
        if (
            choices.Select(choice => choice.Label).Distinct(StringComparer.Ordinal).Count()
            != choices.Count
        )
            problems.Add("CHOICE_LABEL_DUPLICATE");
        if (
            choices.Select(choice => choice.Id).Distinct(StringComparer.Ordinal).Count()
            != choices.Count
        )
            problems.Add("CHOICE_ID_DUPLICATE");
        foreach (var choice in choices)
        {
            if (
                string.IsNullOrWhiteSpace(choice.Label)
                || choice.Label.Length > limits.MaxChoiceLabelLength
            )
                problems.Add("CHOICE_LABEL_LENGTH");
            if (string.IsNullOrWhiteSpace(choice.Id) || choice.Id.Length > 64)
                problems.Add("CHOICE_ID_LENGTH");
        }
    }

    private static void ValidateList(
        VisitorReplyBlock block,
        VisitorConversationOptions limits,
        List<string> problems
    )
    {
        var rows = block.Rows ?? [];
        if (rows.Count == 0 || rows.Count > limits.MaxListRows)
            problems.Add("LIST_ROW_COUNT");
        if (string.IsNullOrWhiteSpace(block.ListTitle) || block.ListTitle.Length > 24)
            problems.Add("LIST_TITLE");
        if (rows.Select(row => row.Id).Distinct(StringComparer.Ordinal).Count() != rows.Count)
            problems.Add("LIST_ROW_ID_DUPLICATE");
        foreach (var row in rows)
        {
            if (string.IsNullOrWhiteSpace(row.Title) || row.Title.Length > 24)
                problems.Add("LIST_ROW_TITLE");
            if (row.Description is { Length: > 72 })
                problems.Add("LIST_ROW_DESCRIPTION");
        }
    }
}
