// Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R005, WC135-R006
// Constitutional basis: C-009, C-039, C-042, C-048, C-049, C-059, C-063

using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace Waooaw.BusinessPlatform.Services.Visitor;

public sealed record VisitorHoursContent(
    [property: JsonPropertyName("timeZone")] string TimeZone,
    [property: JsonPropertyName("opensAt")] string OpensAt,
    [property: JsonPropertyName("closesAt")] string ClosesAt
);

public sealed record VisitorConsentContent(
    [property: JsonPropertyName("noticeVersion")] string NoticeVersion,
    [property: JsonPropertyName("notice")] string Notice,
    [property: JsonPropertyName("accepted")] string Accepted,
    [property: JsonPropertyName("registeredNumberAccepted")] string RegisteredNumberAccepted,
    [property: JsonPropertyName("renewalUnavailable")] string RenewalUnavailable,
    [property: JsonPropertyName("yesLabel")] string YesLabel,
    [property: JsonPropertyName("stopLabel")] string StopLabel
);

public sealed record VisitorFixedContent(
    [property: JsonPropertyName("closedNotice")] string ClosedNotice,
    [property: JsonPropertyName("unsupportedContent")] string UnsupportedContent,
    [property: JsonPropertyName("stopAcknowledged")] string StopAcknowledged,
    [property: JsonPropertyName("resumeNotice")] string ResumeNotice
);

public sealed record VisitorDomain(
    [property: JsonPropertyName("code")] string Code,
    [property: JsonPropertyName("label")] string Label,
    [property: JsonPropertyName("family")] string Family,
    [property: JsonPropertyName("customerPlural")] string CustomerPlural,
    [property: JsonPropertyName("keywords")] IReadOnlyList<string> Keywords
);

public sealed record VisitorGoal(
    [property: JsonPropertyName("code")] string Code,
    [property: JsonPropertyName("label")] string Label,
    [property: JsonPropertyName("valueLine")] string ValueLine,
    [property: JsonPropertyName("keywords")] IReadOnlyList<string> Keywords,
    [property: JsonPropertyName("samplePlan")] string SamplePlan
);

public sealed record VisitorDiscoverContent(
    [property: JsonPropertyName("rephrase")] string Rephrase,
    [property: JsonPropertyName("askCity")] string AskCity,
    [property: JsonPropertyName("askDomain")] string AskDomain,
    [property: JsonPropertyName("domains")] IReadOnlyList<VisitorDomain> Domains,
    [property: JsonPropertyName("cities")] IReadOnlyList<string> Cities
);

public sealed record VisitorShowValueContent(
    [property: JsonPropertyName("qualifyAsk")] string QualifyAsk,
    [property: JsonPropertyName("intro")] string Intro,
    [property: JsonPropertyName("familyExamples")]
        IReadOnlyDictionary<string, string> FamilyExamples,
    [property: JsonPropertyName("skills")] string Skills,
    [property: JsonPropertyName("pricingPointer")] string PricingPointer,
    [property: JsonPropertyName("menuPrompt")] string MenuPrompt,
    [property: JsonPropertyName("samplePlanLabel")] string SamplePlanLabel,
    [property: JsonPropertyName("whatCanItDoLabel")] string WhatCanItDoLabel,
    [property: JsonPropertyName("startTrialLabel")] string StartTrialLabel,
    [property: JsonPropertyName("otherProfessionalsLabel")] string OtherProfessionalsLabel
);

public sealed record VisitorOtherProfessionalsContent(
    [property: JsonPropertyName("text")] string Text
);

public sealed record VisitorHandoffContent(
    [property: JsonPropertyName("text")] string Text,
    [property: JsonPropertyName("linkLabel")] string LinkLabel,
    [property: JsonPropertyName("contactThanks")] string ContactThanks,
    [property: JsonPropertyName("reminder")] string Reminder
);

public sealed record VisitorMiscContent(
    [property: JsonPropertyName("about")] string About,
    [property: JsonPropertyName("human")] string Human,
    [property: JsonPropertyName("offTopic")] string OffTopic
);

/// <summary>One versioned, per-tenant script (Conversation Policy layers, WC-135).</summary>
public sealed record VisitorContentSet
{
    [JsonPropertyName("contentId")]
    public string ContentId { get; init; } = string.Empty;

    [JsonPropertyName("version")]
    public string Version { get; init; } = string.Empty;

    [JsonPropertyName("locale")]
    public string Locale { get; init; } = "en-IN";

    [JsonPropertyName("hours")]
    public VisitorHoursContent Hours { get; init; } = new("Asia/Kolkata", "09:00", "21:00");

    [JsonPropertyName("consent")]
    public VisitorConsentContent Consent { get; init; } = null!;

    [JsonPropertyName("fixed")]
    public VisitorFixedContent Fixed { get; init; } = null!;

    [JsonPropertyName("discover")]
    public VisitorDiscoverContent Discover { get; init; } = null!;

    [JsonPropertyName("goals")]
    public IReadOnlyList<VisitorGoal> Goals { get; init; } = [];

    [JsonPropertyName("showValue")]
    public VisitorShowValueContent ShowValue { get; init; } = null!;

    [JsonPropertyName("otherProfessionals")]
    public VisitorOtherProfessionalsContent OtherProfessionals { get; init; } = null!;

    [JsonPropertyName("handoff")]
    public VisitorHandoffContent Handoff { get; init; } = null!;

    [JsonPropertyName("misc")]
    public VisitorMiscContent Misc { get; init; } = null!;

    public string VersionLabel => $"{ContentId}@{Version}";

    public VisitorDomain DomainOrOther(string? code) =>
        Discover.Domains.FirstOrDefault(domain => domain.Code == code)
        ?? Discover.Domains.First(domain => domain.Code == "generic");

    public static VisitorContentSet Parse(string json) =>
        JsonSerializer.Deserialize<VisitorContentSet>(json, VisitorJson.Options)
        ?? throw new VisitorContentException("CONTENT_EMPTY");
}

public sealed class VisitorContentException(string reason) : Exception(reason)
{
    public string Reason { get; } = reason;
}

/// <summary>Content lint: fails closed on invalid, price-stating or over-promising scripts.</summary>
public static partial class VisitorContentValidator
{
    public static IReadOnlyList<string> Validate(
        VisitorContentSet content,
        VisitorConversationOptions limits
    )
    {
        var problems = new List<string>();
        void Require(string value, string name)
        {
            if (string.IsNullOrWhiteSpace(value))
                problems.Add($"{name}_MISSING");
        }

        if (
            string.IsNullOrWhiteSpace(content.ContentId)
            || string.IsNullOrWhiteSpace(content.Version)
        )
            problems.Add("IDENTITY_MISSING");
        if (content.Consent is null || content.Fixed is null || content.Discover is null)
            return [.. problems, "SECTION_MISSING"];
        if (content.ShowValue is null || content.OtherProfessionals is null)
            return [.. problems, "SECTION_MISSING"];
        if (content.Handoff is null || content.Misc is null)
            return [.. problems, "SECTION_MISSING"];

        Require(content.Consent.Notice, "CONSENT_NOTICE");
        Require(content.Consent.NoticeVersion, "CONSENT_NOTICE_VERSION");
        Require(content.Consent.Accepted, "CONSENT_ACCEPTED");
        if (!content.Consent.Notice.Contains("{retentionDays}", StringComparison.Ordinal))
            problems.Add("RETENTION_NOT_DISCLOSED");
        if (!content.Consent.Notice.Contains("STOP", StringComparison.Ordinal))
            problems.Add("CONSENT_STOP_MISSING");
        if (!content.Consent.Notice.Contains("privacy", StringComparison.OrdinalIgnoreCase))
            problems.Add("CONSENT_PRIVACY_LINK_MISSING");
        if (content.Consent.YesLabel.Length > limits.MaxChoiceLabelLength)
            problems.Add("YES_LABEL_TOO_LONG");
        if (content.Consent.StopLabel.Length > limits.MaxChoiceLabelLength)
            problems.Add("STOP_LABEL_TOO_LONG");

        if (!content.Discover.Domains.Any(domain => domain.Code == "generic"))
            problems.Add("DOMAIN_GENERIC_MISSING");
        var choiceGoals = content.Goals.Count(goal => goal.Code != "other");
        if (choiceGoals < 1 || choiceGoals > limits.MaxChoiceButtons)
            problems.Add("GOAL_COUNT");
        if (!content.Goals.Any(goal => goal.Code == "other"))
            problems.Add("GOAL_OTHER_MISSING");
        foreach (var goal in content.Goals.Where(goal => goal.Code != "other"))
            if (goal.Label.Length > limits.MaxChoiceLabelLength)
                problems.Add($"GOAL_LABEL_TOO_LONG:{goal.Code}");
        foreach (var domain in content.Discover.Domains)
            if (!content.ShowValue.FamilyExamples.ContainsKey(domain.Family))
                problems.Add($"FAMILY_EXAMPLE_MISSING:{domain.Family}");
        foreach (
            var label in new[]
            {
                content.ShowValue.SamplePlanLabel,
                content.ShowValue.WhatCanItDoLabel,
                content.ShowValue.StartTrialLabel,
                content.ShowValue.OtherProfessionalsLabel,
                content.Handoff.LinkLabel,
            }
        )
            if (label.Length > limits.MaxChoiceLabelLength)
                problems.Add($"LABEL_TOO_LONG:{label}");

        var trimmed = TrailingPunctuation()
            .Replace(content.OtherProfessionals.Text.Trim(), string.Empty);
        if (!trimmed.EndsWith("coming soon", StringComparison.OrdinalIgnoreCase))
            problems.Add("OTHER_PROFESSIONALS_NOT_COMING_SOON");

        foreach (var (name, text) in AllText(content))
        {
            if (PricePattern().IsMatch(text))
                problems.Add($"PRICE_STATED:{name}");
            if (GuaranteePattern().IsMatch(text))
                problems.Add($"OUTCOME_GUARANTEE:{name}");
            if (JargonPattern().IsMatch(text))
                problems.Add($"JARGON:{name}");
        }
        foreach (
            var (name, text) in AllText(content).Where(entry => entry.Name != "consent.notice")
        )
            if (text.Count(character => character == '?') > 1)
                problems.Add($"MORE_THAN_ONE_QUESTION:{name}");
        return problems;
    }

    /// <summary>Every visitor-facing string with a stable name, for lint and tests.</summary>
    public static IEnumerable<(string Name, string Text)> AllText(VisitorContentSet content)
    {
        yield return ("consent.notice", content.Consent.Notice);
        yield return ("consent.accepted", content.Consent.Accepted);
        yield return ("consent.registeredNumberAccepted", content.Consent.RegisteredNumberAccepted);
        yield return ("consent.renewalUnavailable", content.Consent.RenewalUnavailable);
        yield return ("fixed.closedNotice", content.Fixed.ClosedNotice);
        yield return ("fixed.unsupportedContent", content.Fixed.UnsupportedContent);
        yield return ("fixed.stopAcknowledged", content.Fixed.StopAcknowledged);
        yield return ("fixed.resumeNotice", content.Fixed.ResumeNotice);
        yield return ("discover.rephrase", content.Discover.Rephrase);
        yield return ("discover.askCity", content.Discover.AskCity);
        yield return ("discover.askDomain", content.Discover.AskDomain);
        foreach (var goal in content.Goals)
        {
            yield return ($"goal.{goal.Code}.valueLine", goal.ValueLine);
            yield return ($"goal.{goal.Code}.samplePlan", goal.SamplePlan);
        }
        yield return ("showValue.qualifyAsk", content.ShowValue.QualifyAsk);
        yield return ("showValue.intro", content.ShowValue.Intro);
        foreach (var (family, example) in content.ShowValue.FamilyExamples)
            yield return ($"showValue.example.{family}", example);
        yield return ("showValue.skills", content.ShowValue.Skills);
        yield return ("showValue.pricingPointer", content.ShowValue.PricingPointer);
        yield return ("showValue.menuPrompt", content.ShowValue.MenuPrompt);
        yield return ("otherProfessionals.text", content.OtherProfessionals.Text);
        yield return ("handoff.text", content.Handoff.Text);
        yield return ("handoff.contactThanks", content.Handoff.ContactThanks);
        yield return ("handoff.reminder", content.Handoff.Reminder);
        yield return ("misc.about", content.Misc.About);
        yield return ("misc.human", content.Misc.Human);
        yield return ("misc.offTopic", content.Misc.OffTopic);
    }

    [GeneratedRegex(
        @"[\u20B9$]|\bRs\.?\s*\d|\bINR\b|per\s+month|/\s*month|/\s*mo\b|\bper\s+year\b",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant
    )]
    private static partial Regex PricePattern();

    [GeneratedRegex(
        @"guarantee|will\s+(increase|double|triple)|100\s*%|assured\s+result",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant
    )]
    private static partial Regex GuaranteePattern();

    [GeneratedRegex(
        @"catalogue\s+preview|listed\s+for\s+trial|decision\s+space|constitutional|employment\s+relationship",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant
    )]
    private static partial Regex JargonPattern();

    [GeneratedRegex(@"[\s\p{P}\p{S}]+$", RegexOptions.CultureInvariant)]
    private static partial Regex TrailingPunctuation();
}

public interface IVisitorContentProvider
{
    /// <summary>Resolves the content set for a tenant; throws <see cref="VisitorContentException"/> when unavailable or invalid.</summary>
    VisitorContentSet Get(Guid tenantId);
}
