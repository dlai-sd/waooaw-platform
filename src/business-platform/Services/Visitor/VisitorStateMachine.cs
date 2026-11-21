// Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R001, WC135-R002, WC135-R005, WC135-R009
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C1-01
// Constitutional basis: C-009, C-039, C-042, C-048, C-049, C-059, C-063

using System.Text.RegularExpressions;

namespace Waooaw.BusinessPlatform.Services.Visitor;

public sealed record VisitorSnapshot
{
    public string State { get; init; } = VisitorStates.New;
    public string? Domain { get; init; }
    public string? BusinessText { get; init; }
    public string? City { get; init; }
    public string? Goal { get; init; }
    public bool HasName { get; init; }
    public bool HasEmail { get; init; }
    public bool ConsentGiven { get; init; }
    public bool Tapped { get; init; }
    public int Turns { get; init; }
    public int? TurnsToFirstValue { get; init; }
    public int Nudges { get; init; }

    public bool HasBusinessDetails => !string.IsNullOrWhiteSpace(Domain);

    public string Outcome =>
        State == VisitorStates.Stopped ? VisitorOutcomes.OptOut
        : HasBusinessDetails && Tapped ? VisitorOutcomes.FullSuccess
        : HasBusinessDetails ? VisitorOutcomes.Lead
        : Tapped ? VisitorOutcomes.Intent
        : VisitorOutcomes.None;
}

public sealed record VisitorInput(string Kind, string? Text = null, string? ChoiceId = null)
{
    public const string TextKind = "TEXT";
    public const string ChoiceKind = "CHOICE";
    public const string UnsupportedKind = "UNSUPPORTED";

    public static VisitorInput FromText(string text) => new(TextKind, text);

    public static VisitorInput FromChoice(string choiceId, string? label = null) =>
        new(ChoiceKind, label, choiceId);

    public static VisitorInput Unsupported() => new(UnsupportedKind);
}

public sealed record VisitorLeadUpdate(
    string? Domain = null,
    string? BusinessText = null,
    string? City = null,
    string? Goal = null,
    string? Name = null,
    string? Email = null
)
{
    public bool IsEmpty =>
        Domain is null
        && BusinessText is null
        && City is null
        && Goal is null
        && Name is null
        && Email is null;
}

public sealed record VisitorTransition(
    VisitorSnapshot Next,
    VisitorReply Reply,
    VisitorLeadUpdate Lead,
    bool WantsHandoffReference,
    string Event
);

public static class VisitorChoiceIds
{
    public const string ConsentYes = "consent_yes";
    public const string ConsentStop = "consent_stop";
    public const string SamplePlan = "sample_plan";
    public const string WhatCanItDo = "what_can_it_do";
    public const string StartTrial = "start_trial";
    public const string OtherProfessionals = "other_professionals";
    public const string GoalPrefix = "goal_";
}

/// <summary>The scripted visitor state machine. Pure: no I/O, no clock, no randomness.</summary>
public static partial class VisitorStateMachine
{
    public const string HandoffUrlToken = "{handoffUrl}";

    /// <summary>Nudge count meaning the one missing detail (city or business) has already been asked for once.</summary>
    private const int SpecificQuestionAsked = 2;

    public static VisitorTransition Start(
        VisitorContentSet content,
        VisitorSnapshot snapshot,
        int retentionDays
    ) =>
        ConsentPrompt(
            content,
            snapshot with
            {
                State = VisitorStates.ConsentPending,
            },
            retentionDays,
            "SESSION_OPENED"
        );

    public static VisitorTransition Step(
        VisitorContentSet content,
        VisitorConversationOptions options,
        VisitorSnapshot snapshot,
        VisitorInput input,
        int retentionDays
    )
    {
        var current = snapshot with { Turns = snapshot.Turns + 1 };
        var text = input.Text?.Trim() ?? string.Empty;
        var isStop = IsStop(input, text);

        if (current.State == VisitorStates.Stopped)
            return IsStart(text)
                ? ConsentPrompt(
                    content,
                    current with
                    {
                        State = VisitorStates.ConsentPending,
                        ConsentGiven = false,
                        Nudges = 0,
                    },
                    retentionDays,
                    "RESUMED",
                    resume: true
                )
                : Silent(content, current, "STOPPED_IGNORED");

        if (isStop)
            return new(
                current with
                {
                    State = VisitorStates.Stopped,
                },
                content.Protocol.Stop.Acknowledge
                    ? Reply(
                        content,
                        VisitorStates.Stopped,
                        VisitorReplyBlock.TextBlock(
                            content.ResolveFixed(content.Protocol.Stop.AcknowledgementRef)
                                ?? throw new VisitorContentException("PROTOCOL_STOP_UNRESOLVED")
                        )
                    )
                    : VisitorReply.Empty(VisitorStates.Stopped, content.VersionLabel),
                new VisitorLeadUpdate(),
                false,
                "OPT_OUT"
            );

        if (input.Kind == VisitorInput.UnsupportedKind)
            return Stay(
                content,
                current,
                [VisitorReplyBlock.TextBlock(content.Fixed.UnsupportedContent)],
                "UNSUPPORTED_CONTENT"
            );

        if (current.State is VisitorStates.New or VisitorStates.ConsentPending)
        {
            if (IsYes(input, text))
                return new(
                    current with
                    {
                        State = VisitorStates.Discover,
                        ConsentGiven = true,
                        Nudges = 0,
                    },
                    Reply(
                        content,
                        VisitorStates.Discover,
                        VisitorReplyBlock.TextBlock(content.Consent.Accepted)
                    ),
                    new VisitorLeadUpdate(),
                    false,
                    "CONSENT_RECORDED"
                );
            return current.Nudges == 0
                ? ConsentPrompt(
                    content,
                    current with
                    {
                        State = VisitorStates.ConsentPending,
                        Nudges = 1,
                    },
                    retentionDays,
                    "CONSENT_REPEATED"
                )
                : Silent(content, current, "CONSENT_WAITING");
        }

        var side = SideIntent(content, options, current, input, text);
        if (side is not null)
            return side;

        return current.State switch
        {
            VisitorStates.Discover => Discover(content, current, text),
            VisitorStates.ChooseProfessional => ChooseProfessional(content, current, text),
            VisitorStates.ProfessionalCard => ProfessionalCard(content, options, current, text),
            VisitorStates.Qualify => Qualify(content, current, input, text),
            VisitorStates.ShowValue or VisitorStates.OtherProfessionals => Menu(
                content,
                options,
                current,
                input,
                text
            ),
            VisitorStates.Handoff => Handoff(content, current, input, text),
            _ => Silent(content, current, "STATE_UNHANDLED"),
        };
    }

    // ── Consent (endpoint channels; WhatsApp consent is owned by the guest session) ─────────────

    private static VisitorTransition ConsentPrompt(
        VisitorContentSet content,
        VisitorSnapshot snapshot,
        int retentionDays,
        string eventName,
        bool resume = false
    )
    {
        var notice = resume
            ? content.ResolveFixed(content.Protocol.Start.NoticeRef) ?? content.Fixed.ResumeNotice
            : content.Consent.Notice;
        return new(
            snapshot,
            Reply(
                content,
                VisitorStates.ConsentPending,
                VisitorReplyBlock.TextBlock(
                    Fill(notice, ("retentionDays", retentionDays.ToString()))
                ),
                VisitorReplyBlock.ChoicesBlock(
                    new(VisitorChoiceIds.ConsentYes, content.Consent.YesLabel),
                    new(VisitorChoiceIds.ConsentStop, content.Consent.StopLabel)
                )
            ),
            new VisitorLeadUpdate(),
            false,
            eventName
        );
    }

    // ── Discover ────────────────────────────────────────────────────────────────────────────────

    private static VisitorTransition Discover(
        VisitorContentSet content,
        VisitorSnapshot current,
        string text
    )
    {
        var domain = DetectDomain(content, text);
        var city = DetectCity(content, text);
        var domainCode = current.Domain ?? domain?.Code;
        var cityName = current.City ?? city;

        if (domainCode is not null && cityName is not null)
            return AskGoal(
                content,
                current,
                content.DomainOrOther(domainCode),
                cityName,
                new VisitorLeadUpdate(
                    domain is null ? null : domain.Code,
                    BusinessText: null,
                    City: city
                )
            );

        if (domainCode is not null && current.Nudges >= SpecificQuestionAsked)
            // Asked for the city once already and could not read it: move on rather than ask again.
            return AskGoal(
                content,
                current,
                content.DomainOrOther(domainCode),
                null,
                new VisitorLeadUpdate(Domain: domain?.Code)
            );

        if (domainCode is not null)
        {
            var resolved = content.DomainOrOther(domainCode);
            return Stay(
                content,
                current with
                {
                    Domain = domainCode,
                    Nudges = SpecificQuestionAsked,
                },
                [
                    VisitorReplyBlock.TextBlock(
                        Fill(content.Discover.AskCity, ("domain", resolved.Label))
                    ),
                ],
                "ASK_CITY",
                new VisitorLeadUpdate(Domain: domain?.Code)
            );
        }

        if (cityName is not null && current.Nudges >= SpecificQuestionAsked)
        {
            // Asked for the business once already and could not read it: continue with a generic business.
            var generalBusiness = content.DomainOrOther("generic");
            return AskGoal(
                content,
                current,
                generalBusiness,
                cityName,
                new VisitorLeadUpdate(
                    Domain: generalBusiness.Code,
                    BusinessText: Bounded(text, 120),
                    City: city
                )
            );
        }

        if (cityName is not null)
            return Stay(
                content,
                current with
                {
                    City = cityName,
                    Nudges = SpecificQuestionAsked,
                },
                [VisitorReplyBlock.TextBlock(Fill(content.Discover.AskDomain, ("city", cityName)))],
                "ASK_DOMAIN",
                new VisitorLeadUpdate(City: city)
            );

        if (current.Nudges == 0)
            return Stay(
                content,
                current with
                {
                    Nudges = 1,
                },
                [VisitorReplyBlock.TextBlock(content.Discover.Rephrase)],
                "REPHRASE"
            );

        var generic = content.DomainOrOther("generic");
        return AskGoal(
            content,
            current,
            generic,
            null,
            new VisitorLeadUpdate(Domain: generic.Code, BusinessText: Bounded(text, 120))
        );
    }

    private static VisitorTransition AskGoal(
        VisitorContentSet content,
        VisitorSnapshot current,
        VisitorDomain domain,
        string? city,
        VisitorLeadUpdate update
    )
    {
        var where = city is null ? string.Empty : $" in {city}";
        var ask = content
            .ShowValue.QualifyAsk.Replace(" in {city}", where, StringComparison.Ordinal)
            .Replace("{domain}", domain.Label, StringComparison.Ordinal);
        return new(
            current with
            {
                State = VisitorStates.Qualify,
                Domain = domain.Code,
                City = city ?? current.City,
                BusinessText = update.BusinessText ?? current.BusinessText,
                Nudges = 0,
            },
            Reply(
                content,
                VisitorStates.Qualify,
                VisitorReplyBlock.TextBlock(ask),
                VisitorReplyBlock.ChoicesBlock(
                    content
                        .Goals.Where(goal => goal.Code != "other")
                        .Select(goal => new VisitorChoice(
                            VisitorChoiceIds.GoalPrefix + goal.Code,
                            goal.Label
                        ))
                        .ToArray()
                )
            ),
            update,
            false,
            "ASK_GOAL"
        );
    }

    // ── Qualify ─────────────────────────────────────────────────────────────────────────────────

    private static VisitorTransition Qualify(
        VisitorContentSet content,
        VisitorSnapshot current,
        VisitorInput input,
        string text
    )
    {
        var goal =
            GoalFromChoice(content, input.ChoiceId)
            ?? DetectGoal(content, text)
            ?? content.Goals.First(g => g.Code == "other");
        var domain = content.DomainOrOther(current.Domain);
        var customers = domain.CustomerPlural;
        var example = content.ShowValue.FamilyExamples.TryGetValue(domain.Family, out var family)
            ? family
            : content.ShowValue.FamilyExamples["general"];
        var intro = Fill(
            content.ShowValue.Intro,
            ("domain", domain.Label),
            ("valueLine", Fill(goal.ValueLine, ("customers", customers))),
            ("example", example)
        );
        return new(
            current with
            {
                State = VisitorStates.ShowValue,
                Goal = goal.Code,
                TurnsToFirstValue = current.TurnsToFirstValue ?? current.Turns,
                Nudges = 0,
            },
            Reply(
                content,
                VisitorStates.ShowValue,
                VisitorReplyBlock.TextBlock(intro),
                VisitorReplyBlock.ChoicesBlock(
                    new(VisitorChoiceIds.SamplePlan, content.ShowValue.SamplePlanLabel),
                    new(VisitorChoiceIds.WhatCanItDo, content.ShowValue.WhatCanItDoLabel),
                    new(VisitorChoiceIds.StartTrial, content.ShowValue.StartTrialLabel)
                )
            ),
            new VisitorLeadUpdate(Goal: goal.Code),
            false,
            "SHOW_VALUE"
        );
    }

    // ── Choose a professional, then act on its card (WhatsApp numbered journey) ─────────────────

    private static VisitorTransition ChooseProfessional(
        VisitorContentSet content,
        VisitorSnapshot current,
        string text
    )
    {
        var professionals = content.Professionals;
        if (HelpPattern().IsMatch(text))
            return Stay(
                content,
                current,
                [VisitorReplyBlock.TextBlock(content.Misc.About + "\n\n" + professionals.Menu())],
                "HELP"
            );
        var number =
            PickNumber(text, professionals.Items.Count) ?? PickByLabel(professionals, text);
        if (number is null)
            return Stay(
                content,
                current,
                [VisitorReplyBlock.TextBlock(professionals.Retry + "\n\n" + professionals.Menu())],
                "PROFESSIONAL_RETRY"
            );
        var item = professionals.Items[number.Value - 1];
        if (!item.Available)
            return Stay(
                content,
                current,
                [
                    VisitorReplyBlock.TextBlock(
                        Fill(professionals.ComingSoon, ("label", item.Label))
                            + "\n\n"
                            + professionals.Menu()
                    ),
                ],
                "PROFESSIONAL_COMING_SOON"
            );
        return new(
            current with
            {
                State = VisitorStates.ProfessionalCard,
                Nudges = 0,
            },
            Reply(content, VisitorStates.ProfessionalCard, VisitorReplyBlock.TextBlock(item.Card!)),
            new VisitorLeadUpdate(),
            false,
            "PROFESSIONAL_SELECTED"
        );
    }

    private static VisitorTransition ProfessionalCard(
        VisitorContentSet content,
        VisitorConversationOptions options,
        VisitorSnapshot current,
        string text
    )
    {
        var professionals = content.Professionals;
        var url = options.HandoffBaseUrl;
        var label = professionals.Items.First(item => item.Available).Label;
        if (BackPattern().IsMatch(text))
            return new(
                current with
                {
                    State = VisitorStates.ChooseProfessional,
                },
                Reply(
                    content,
                    VisitorStates.ChooseProfessional,
                    VisitorReplyBlock.TextBlock(professionals.Menu())
                ),
                new VisitorLeadUpdate(),
                false,
                "PROFESSIONAL_MENU"
            );
        switch (PickNumber(text, 4))
        {
            case 1:
                return Stay(
                    content,
                    current,
                    [
                        VisitorReplyBlock.TextBlock(
                            Fill(professionals.Interview, ("url", url), ("label", label))
                        ),
                    ],
                    "CARD_INTERVIEW"
                );
            case 2:
                return ToHandoff(content, current);
            case 3:
                return Stay(
                    content,
                    current,
                    [
                        VisitorReplyBlock.TextBlock(
                            Fill(professionals.Hire, ("url", url), ("label", label))
                        ),
                    ],
                    "CARD_HIRE"
                );
            case 4:
                return Stay(
                    content,
                    current,
                    [
                        VisitorReplyBlock.TextBlock(
                            Fill(professionals.Callback, ("url", url), ("label", label))
                        ),
                    ],
                    "CARD_CALLBACK"
                );
            default:
                var card = professionals.Items.First(item => item.Available).Card!;
                return Stay(
                    content,
                    current,
                    [VisitorReplyBlock.TextBlock(professionals.CardRetry + "\n\n" + card)],
                    "CARD_RETRY"
                );
        }
    }

    /// <summary>Reads a menu number, tolerating the keycap emoji form (1️⃣) and trailing punctuation.</summary>
    private static int? PickNumber(string text, int maximum)
    {
        var match = NumberPattern().Match(text);
        return
            match.Success
            && int.TryParse(match.Groups[1].Value, out var number)
            && number >= 1
            && number <= maximum
            ? number
            : null;
    }

    private static int? PickByLabel(VisitorProfessionalsContent professionals, string text)
    {
        var lower = text.Trim().ToLowerInvariant();
        if (lower.Length < 4)
            return null;
        for (var index = 0; index < professionals.Items.Count; index++)
            if (
                professionals.Items[index].Label.Contains(lower, StringComparison.OrdinalIgnoreCase)
            )
                return index + 1;
        return null;
    }

    // ── Show value and other professionals ──────────────────────────────────────────────────────

    private static VisitorTransition Menu(
        VisitorContentSet content,
        VisitorConversationOptions options,
        VisitorSnapshot current,
        VisitorInput input,
        string text
    )
    {
        var choice = input.ChoiceId;
        var lower = text.ToLowerInvariant();
        if (choice == VisitorChoiceIds.StartTrial || TrialPattern().IsMatch(lower))
            return ToHandoff(content, current);
        if (
            choice == VisitorChoiceIds.OtherProfessionals
            || OtherProfessionalsPattern().IsMatch(lower)
        )
            return new(
                current with
                {
                    State = VisitorStates.OtherProfessionals,
                },
                Reply(
                    content,
                    VisitorStates.OtherProfessionals,
                    VisitorReplyBlock.TextBlock(content.OtherProfessionals.Text),
                    VisitorReplyBlock.ChoicesBlock(
                        new(VisitorChoiceIds.StartTrial, content.ShowValue.StartTrialLabel),
                        new(VisitorChoiceIds.WhatCanItDo, content.ShowValue.WhatCanItDoLabel)
                    )
                ),
                new VisitorLeadUpdate(),
                false,
                "OTHER_PROFESSIONALS"
            );
        if (choice == VisitorChoiceIds.SamplePlan || SamplePlanPattern().IsMatch(lower))
        {
            var goal =
                content.Goals.FirstOrDefault(g => g.Code == current.Goal)
                ?? content.Goals.First(g => g.Code == "other");
            var domain = content.DomainOrOther(current.Domain);
            return Stay(
                content,
                current with
                {
                    State = VisitorStates.ShowValue,
                },
                [
                    VisitorReplyBlock.TextBlock(
                        Fill(goal.SamplePlan, ("customers", domain.CustomerPlural))
                    ),
                    VisitorReplyBlock.ChoicesBlock(
                        new(VisitorChoiceIds.StartTrial, content.ShowValue.StartTrialLabel),
                        new(
                            VisitorChoiceIds.OtherProfessionals,
                            content.ShowValue.OtherProfessionalsLabel
                        )
                    ),
                ],
                "SAMPLE_PLAN"
            );
        }
        if (choice == VisitorChoiceIds.WhatCanItDo || SkillsPattern().IsMatch(lower))
            return Stay(
                content,
                current with
                {
                    State = VisitorStates.ShowValue,
                },
                [
                    VisitorReplyBlock.TextBlock(content.ShowValue.Skills),
                    VisitorReplyBlock.ChoicesBlock(
                        new(VisitorChoiceIds.SamplePlan, content.ShowValue.SamplePlanLabel),
                        new(VisitorChoiceIds.StartTrial, content.ShowValue.StartTrialLabel)
                    ),
                ],
                "SKILLS"
            );
        return Stay(
            content,
            current,
            [
                VisitorReplyBlock.TextBlock(content.ShowValue.MenuPrompt),
                VisitorReplyBlock.ChoicesBlock(
                    new(VisitorChoiceIds.SamplePlan, content.ShowValue.SamplePlanLabel),
                    new(VisitorChoiceIds.WhatCanItDo, content.ShowValue.WhatCanItDoLabel),
                    new(VisitorChoiceIds.StartTrial, content.ShowValue.StartTrialLabel)
                ),
            ],
            "MENU"
        );
    }

    // ── Handoff ─────────────────────────────────────────────────────────────────────────────────

    private static VisitorTransition ToHandoff(
        VisitorContentSet content,
        VisitorSnapshot current
    ) =>
        new(
            current with
            {
                State = VisitorStates.Handoff,
            },
            Reply(
                content,
                VisitorStates.Handoff,
                VisitorReplyBlock.TextBlock(content.Handoff.Text),
                VisitorReplyBlock.LinkBlock(content.Handoff.LinkLabel, HandoffUrlToken)
            ),
            new VisitorLeadUpdate(),
            true,
            "HANDOFF"
        );

    private static VisitorTransition Handoff(
        VisitorContentSet content,
        VisitorSnapshot current,
        VisitorInput input,
        string text
    )
    {
        var email = EmailPattern().Match(text) is { Success: true } match
            ? match.Value.ToLowerInvariant()
            : null;
        var name = email is null
            ? null
            : DetectName(text.Replace(email, string.Empty, StringComparison.OrdinalIgnoreCase));
        if (
            email is null
            && input.ChoiceId != VisitorChoiceIds.StartTrial
            && !TrialPattern().IsMatch(text.ToLowerInvariant())
        )
            name = DetectName(text);
        if ((email is not null && !current.HasEmail) || (name is not null && !current.HasName))
            return new(
                current with
                {
                    HasEmail = current.HasEmail || email is not null,
                    HasName = current.HasName || name is not null,
                },
                Reply(
                    content,
                    VisitorStates.Handoff,
                    VisitorReplyBlock.TextBlock(content.Handoff.ContactThanks),
                    VisitorReplyBlock.LinkBlock(content.Handoff.LinkLabel, HandoffUrlToken)
                ),
                new VisitorLeadUpdate(Name: name, Email: email),
                true,
                "CONTACT_CAPTURED"
            );
        return new(
            current,
            Reply(
                content,
                VisitorStates.Handoff,
                VisitorReplyBlock.TextBlock(content.Handoff.Reminder),
                VisitorReplyBlock.LinkBlock(content.Handoff.LinkLabel, HandoffUrlToken)
            ),
            new VisitorLeadUpdate(),
            true,
            "HANDOFF_REMINDER"
        );
    }

    // ── Side intents (pricing, about, human, off-topic) ─────────────────────────────────────────

    private static VisitorTransition? SideIntent(
        VisitorContentSet content,
        VisitorConversationOptions options,
        VisitorSnapshot current,
        VisitorInput input,
        string text
    )
    {
        if (input.Kind == VisitorInput.ChoiceKind || text.Length == 0)
            return null;
        var lower = text.ToLowerInvariant();
        var url = options.HandoffBaseUrl;
        if (PricingPattern().IsMatch(lower))
            return Stay(
                content,
                current,
                [VisitorReplyBlock.TextBlock(Fill(content.ShowValue.PricingPointer, ("url", url)))],
                "PRICING_POINTER"
            );
        if (HumanPattern().IsMatch(lower))
            return Stay(
                content,
                current,
                [VisitorReplyBlock.TextBlock(Fill(content.Misc.Human, ("url", url)))],
                "HUMAN_REQUEST"
            );
        if (AboutPattern().IsMatch(lower) && current.State is not VisitorStates.Handoff)
        {
            var next = current.State switch
            {
                VisitorStates.Discover => content.Consent.Accepted,
                VisitorStates.Qualify => null,
                VisitorStates.ChooseProfessional => content.Professionals.Menu(),
                VisitorStates.ProfessionalCard => content
                    .Professionals.Items.First(item => item.Available)
                    .Card,
                _ => content.ShowValue.MenuPrompt,
            };
            var blocks = new List<VisitorReplyBlock>
            {
                VisitorReplyBlock.TextBlock(
                    next is null ? content.Misc.About : content.Misc.About + "\n\n" + next
                ),
            };
            if (current.State is VisitorStates.ShowValue or VisitorStates.OtherProfessionals)
                blocks.Add(
                    VisitorReplyBlock.ChoicesBlock(
                        new(VisitorChoiceIds.SamplePlan, content.ShowValue.SamplePlanLabel),
                        new(VisitorChoiceIds.WhatCanItDo, content.ShowValue.WhatCanItDoLabel),
                        new(VisitorChoiceIds.StartTrial, content.ShowValue.StartTrialLabel)
                    )
                );
            return Stay(content, current, blocks, "ABOUT");
        }
        return null;
    }

    // ── Helpers ─────────────────────────────────────────────────────────────────────────────────

    public static bool IsStop(VisitorInput input, string text) =>
        input.ChoiceId == VisitorChoiceIds.ConsentStop || StopPattern().IsMatch(text);

    public static bool IsStart(string text) => StartPattern().IsMatch(text);

    public static bool IsYes(VisitorInput input, string text) =>
        input.ChoiceId == VisitorChoiceIds.ConsentYes || YesPattern().IsMatch(text);

    private static VisitorTransition Stay(
        VisitorContentSet content,
        VisitorSnapshot current,
        IReadOnlyList<VisitorReplyBlock> blocks,
        string eventName,
        VisitorLeadUpdate? lead = null
    ) =>
        new(
            current,
            new VisitorReply
            {
                State = current.State,
                ContentVersion = content.VersionLabel,
                Blocks = blocks,
            },
            lead ?? new VisitorLeadUpdate(),
            false,
            eventName
        );

    private static VisitorTransition Silent(
        VisitorContentSet content,
        VisitorSnapshot current,
        string eventName
    ) =>
        new(
            current,
            VisitorReply.Empty(current.State, content.VersionLabel),
            new VisitorLeadUpdate(),
            false,
            eventName
        );

    private static VisitorReply Reply(
        VisitorContentSet content,
        string state,
        params VisitorReplyBlock[] blocks
    ) =>
        new()
        {
            State = state,
            ContentVersion = content.VersionLabel,
            Blocks = blocks,
        };

    public static string Fill(string template, params (string Name, string Value)[] values)
    {
        var result = template;
        foreach (var (name, value) in values)
            result = result.Replace("{" + name + "}", value, StringComparison.Ordinal);
        return result;
    }

    private static string? Bounded(string text, int length)
    {
        var cleaned = WhitespacePattern().Replace(text.Trim(), " ");
        return cleaned.Length == 0 ? null
            : cleaned.Length <= length ? cleaned
            : cleaned[..length];
    }

    public static VisitorDomain? DetectDomain(VisitorContentSet content, string text)
    {
        var lower = text.ToLowerInvariant();
        VisitorDomain? best = null;
        var bestLength = 0;
        foreach (var domain in content.Discover.Domains)
        foreach (var keyword in domain.Keywords)
        {
            if (keyword.Length <= bestLength)
                continue;
            if (
                Regex.IsMatch(
                    lower,
                    $@"(?<![a-z]){Regex.Escape(keyword.ToLowerInvariant())}",
                    RegexOptions.CultureInvariant
                )
            )
            {
                best = domain;
                bestLength = keyword.Length;
            }
        }
        return best;
    }

    public static string? DetectCity(VisitorContentSet content, string text)
    {
        foreach (var city in content.Discover.Cities.OrderByDescending(city => city.Length))
            if (
                Regex.IsMatch(
                    text,
                    $@"(?<![A-Za-z]){Regex.Escape(city)}(?![A-Za-z])",
                    RegexOptions.IgnoreCase | RegexOptions.CultureInvariant
                )
            )
                return city;
        var match = InCityPattern().Match(text);
        if (match.Success)
        {
            var candidate = Bounded(match.Groups[1].Value, 80);
            if (candidate is { Length: >= 3 })
                return candidate;
        }
        return null;
    }

    private static VisitorGoal? GoalFromChoice(VisitorContentSet content, string? choiceId) =>
        choiceId is not null
        && choiceId.StartsWith(VisitorChoiceIds.GoalPrefix, StringComparison.Ordinal)
            ? content.Goals.FirstOrDefault(goal =>
                goal.Code == choiceId[VisitorChoiceIds.GoalPrefix.Length..]
            )
            : null;

    private static VisitorGoal? DetectGoal(VisitorContentSet content, string text)
    {
        var lower = text.ToLowerInvariant();
        return content.Goals.FirstOrDefault(goal =>
            goal.Keywords.Any(keyword => lower.Contains(keyword, StringComparison.Ordinal))
        );
    }

    private static readonly HashSet<string> NameStopWords = new(StringComparer.OrdinalIgnoreCase)
    {
        "thanks",
        "thank",
        "you",
        "ok",
        "okay",
        "yes",
        "no",
        "hi",
        "hello",
        "hey",
        "bye",
        "sure",
        "great",
        "nice",
        "cool",
        "later",
        "please",
        "not",
        "now",
    };

    private static string? DetectName(string text)
    {
        var trimmed = text.Trim();
        var hadPrefix = NamePrefixPattern().IsMatch(trimmed);
        var cleaned = NamePrefixPattern()
            .Replace(trimmed, string.Empty)
            .Trim(' ', ',', '.', '-', ':');
        var words = cleaned.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        if (!NamePattern().IsMatch(cleaned) || words.Length is 0 or > 4)
            return null;
        if (words.Any(word => NameStopWords.Contains(word.Trim('.', ','))))
            return null;
        return hadPrefix || words.Length >= 2 ? cleaned : null;
    }

    [GeneratedRegex(@"^\s*stop[\s.!]*$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex StopPattern();

    [GeneratedRegex(
        @"^\s*(start|hi+|hello|hey)[\s.!]*$",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant
    )]
    private static partial Regex StartPattern();

    [GeneratedRegex(@"^\s*([1-9])[\uFE0F\u20E3\s.!)]*$", RegexOptions.CultureInvariant)]
    private static partial Regex NumberPattern();

    [GeneratedRegex(
        @"^\s*(help|\?)[\s.!]*$",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant
    )]
    private static partial Regex HelpPattern();

    [GeneratedRegex(
        @"^\s*(0|menu|back|home)[\s.!]*$",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant
    )]
    private static partial Regex BackPattern();

    [GeneratedRegex(
        @"^\s*(yes|y|yeah|yep|ok|okay|sure|i agree|i consent)[\s.!]*$",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant
    )]
    private static partial Regex YesPattern();

    [GeneratedRegex(
        @"\b(price|pricing|cost|costs|how much|fee|fees|charge|charges|pay|payment|subscription|rates?)\b",
        RegexOptions.CultureInvariant
    )]
    private static partial Regex PricingPattern();

    [GeneratedRegex(
        @"\b(human|real person|someone|talk to a person|call me|phone number)\b",
        RegexOptions.CultureInvariant
    )]
    private static partial Regex HumanPattern();

    [GeneratedRegex(
        @"\b(what is waooaw|who are you|what is this|how does it work|how it works|tell me about waooaw|what do you do|is this chatgpt|is this just chatgpt)\b",
        RegexOptions.CultureInvariant
    )]
    private static partial Regex AboutPattern();

    [GeneratedRegex(
        @"\b(trial|start|sign up|signup|register|try it|get started|let's go|lets go|ready)\b",
        RegexOptions.CultureInvariant
    )]
    private static partial Regex TrialPattern();

    [GeneratedRegex(
        @"\b(farm|farming|crop|agri|agriculture|trading|trader|stock|share market|shares|tutor|tutoring|tuition|other professionals?)\b",
        RegexOptions.CultureInvariant
    )]
    private static partial Regex OtherProfessionalsPattern();

    [GeneratedRegex(@"\b(sample|plan|first month|example)\b", RegexOptions.CultureInvariant)]
    private static partial Regex SamplePlanPattern();

    [GeneratedRegex(
        @"\b(skills?|what can it do|what can you do|features?|capabilit|summary)\b",
        RegexOptions.CultureInvariant
    )]
    private static partial Regex SkillsPattern();

    [GeneratedRegex(
        @"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
        RegexOptions.CultureInvariant
    )]
    private static partial Regex EmailPattern();

    [GeneratedRegex(
        @"\b(?:in|at|from|based in|located in)\s+([A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)?)",
        RegexOptions.CultureInvariant
    )]
    private static partial Regex InCityPattern();

    [GeneratedRegex(
        @"^(?:(?:my name is|name is|i am|i'm|this is|it's|its)\s+)",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant
    )]
    private static partial Regex NamePrefixPattern();

    [GeneratedRegex(@"^\p{L}[\p{L}\s.'\-]{1,38}$", RegexOptions.CultureInvariant)]
    private static partial Regex NamePattern();

    [GeneratedRegex(@"\s+", RegexOptions.CultureInvariant)]
    private static partial Regex WhitespacePattern();
}
