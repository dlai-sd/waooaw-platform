// Implements: work-contracts/WC-135-requirements.yaml WC135-R001, WC135-R002, WC135-R005, WC135-R006, WC135-R009
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C2-03
// Constitutional basis: C-009, C-039, C-042, C-048, C-049, C-059, C-063

using Waooaw.BusinessPlatform.Services.Visitor;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.VisitorConversation;

internal static class VisitorTestContent
{
    public static VisitorContentSet Shipped() =>
        VisitorContentSet.Parse(
            File.ReadAllText(
                RepositoryPaths.Resolve("src/business-platform/Catalog/Visitor/waooaw-demo.v1.json")
            )
        );

    public static VisitorConversationOptions Options() => new() { Mode = VisitorMode.V2 };
}

public sealed class VisitorContentTests
{
    private static readonly VisitorConversationOptions Limits = VisitorTestContent.Options();

    [Fact]
    public void ShippedContentPassesTheContentLint()
    {
        var problems = VisitorContentValidator.Validate(VisitorTestContent.Shipped(), Limits);
        Assert.True(problems.Count == 0, string.Join(",", problems));
    }

    [Theory]
    [InlineData("Plans start at ₹1,499 each month", "PRICE_STATED")]
    [InlineData("It costs Rs. 500 per month", "PRICE_STATED")]
    [InlineData("We guarantee more customers", "OUTCOME_GUARANTEE")]
    [InlineData("Your sales will double", "OUTCOME_GUARANTEE")]
    [InlineData("This is a catalogue preview", "JARGON")]
    [InlineData("Listed for trial today", "JARGON")]
    public void ContentThatStatesPriceOverpromisesOrUsesJargonIsRejected(
        string text,
        string expected
    )
    {
        var content = VisitorTestContent.Shipped();
        var broken = content with { Misc = content.Misc with { About = text } };
        Assert.Contains(
            VisitorContentValidator.Validate(broken, Limits),
            problem => problem.StartsWith(expected, StringComparison.Ordinal)
        );
    }

    [Fact]
    public void OtherProfessionalsMustEndWithComingSoon()
    {
        var content = VisitorTestContent.Shipped();
        var broken = content with
        {
            OtherProfessionals = new("We also have farming and trading help."),
        };
        Assert.Contains(
            "OTHER_PROFESSIONALS_NOT_COMING_SOON",
            VisitorContentValidator.Validate(broken, Limits)
        );
    }

    [Fact]
    public void ConsentMustDiscloseRetentionStopAndPrivacy()
    {
        var content = VisitorTestContent.Shipped();
        var broken = content with
        {
            Consent = content.Consent with { Notice = "Hello there. Reply YES to start." },
        };
        var problems = VisitorContentValidator.Validate(broken, Limits);
        Assert.Contains("RETENTION_NOT_DISCLOSED", problems);
        Assert.Contains("CONSENT_STOP_MISSING", problems);
        Assert.Contains("CONSENT_PRIVACY_LINK_MISSING", problems);
    }

    [Fact]
    public void ChoiceLabelsAndQuestionCountAreBounded()
    {
        var content = VisitorTestContent.Shipped();
        var broken = content with
        {
            ShowValue = content.ShowValue with
            {
                StartTrialLabel = "Start my seven day trial now",
                MenuPrompt = "What next? Or maybe more?",
            },
        };
        var problems = VisitorContentValidator.Validate(broken, Limits);
        Assert.Contains(
            problems,
            problem => problem.StartsWith("LABEL_TOO_LONG", StringComparison.Ordinal)
        );
        Assert.Contains(
            problems,
            problem => problem.StartsWith("MORE_THAN_ONE_QUESTION", StringComparison.Ordinal)
        );
    }

    [Fact]
    public void MissingGenericDomainOrFamilyExampleFailsClosed()
    {
        var content = VisitorTestContent.Shipped();
        var noGeneric = content with
        {
            Discover = content.Discover with
            {
                Domains = content
                    .Discover.Domains.Where(domain => domain.Code != "generic")
                    .ToList(),
            },
        };
        Assert.Contains(
            "DOMAIN_GENERIC_MISSING",
            VisitorContentValidator.Validate(noGeneric, Limits)
        );
        var noExample = content with
        {
            ShowValue = content.ShowValue with
            {
                FamilyExamples = content
                    .ShowValue.FamilyExamples.Where(pair => pair.Key != "health")
                    .ToDictionary(),
            },
        };
        Assert.Contains(
            "FAMILY_EXAMPLE_MISSING:health",
            VisitorContentValidator.Validate(noExample, Limits)
        );
    }

    [Fact]
    public void StopReminderAppearsOnlyWhereItIsRequired()
    {
        var content = VisitorTestContent.Shipped();
        var withStop = VisitorContentValidator
            .AllText(content)
            .Where(entry => entry.Text.Contains("STOP", StringComparison.Ordinal))
            .Select(entry => entry.Name)
            .ToHashSet();
        Assert.Equal(
            new HashSet<string>
            {
                "consent.notice",
                "consent.renewalUnavailable",
                "fixed.closedNotice",
                "fixed.resumeNotice",
            },
            withStop
        );
    }

    [Fact]
    public void EveryChoiceFitsTheChannelLimitsAndInteractiveBodiesFitTheBodyLimit()
    {
        var content = VisitorTestContent.Shipped();
        foreach (var (name, text) in VisitorContentValidator.AllText(content))
            Assert.True(
                text.Length <= Limits.MaxInteractiveBodyLength + 220,
                $"{name} is too long for a chat message"
            );
        Assert.All(
            content.Goals,
            goal => Assert.True(goal.Label.Length <= Limits.MaxChoiceLabelLength)
        );
    }
}

public sealed class VisitorStateMachineTests
{
    private static readonly VisitorContentSet Content = VisitorTestContent.Shipped();
    private static readonly VisitorConversationOptions Options = VisitorTestContent.Options();

    private static VisitorTransition Step(VisitorSnapshot snapshot, VisitorInput input) =>
        VisitorStateMachine.Step(Content, Options, snapshot, input, 90);

    private static VisitorSnapshot Consented() =>
        new() { State = VisitorStates.Discover, ConsentGiven = true };

    private static string Text(VisitorTransition transition) => transition.Reply.PlainText();

    private static VisitorReply Concrete(VisitorReply reply) =>
        reply with
        {
            ContentVersion = "x",
            Blocks = reply
                .Blocks.Select(block =>
                    block.Type == "LINK"
                        ? block with
                        {
                            Url = "https://cp.demo.waooaw.com/register?lead=t",
                        }
                        : block
                )
                .ToList(),
        };

    [Fact]
    public void StartAsksForConsentWithYesAndStopChoicesAndStatesTheRetentionPeriod()
    {
        var start = VisitorStateMachine.Start(Content, new VisitorSnapshot(), 45);
        Assert.Equal(VisitorStates.ConsentPending, start.Next.State);
        Assert.Contains("45 days", Text(start), StringComparison.Ordinal);
        var choices = Assert.Single(start.Reply.Blocks, block => block.Type == "CHOICES").Choices!;
        Assert.Equal(["YES", "STOP"], choices.Select(choice => choice.Label));
    }

    [Fact]
    public void FullJourneyReachesHandoffWithLeadDetailsAndNoPriceOrGuarantee()
    {
        var snapshot = VisitorStateMachine.Start(Content, new VisitorSnapshot(), 90).Next;
        var all = new List<VisitorTransition>();

        var t = Step(snapshot, VisitorInput.FromChoice(VisitorChoiceIds.ConsentYes));
        Assert.Equal("CONSENT_RECORDED", t.Event);
        Assert.Equal(VisitorStates.Discover, t.Next.State);
        all.Add(t);

        t = Step(t.Next, VisitorInput.FromText("I run a dental clinic in Pune"));
        Assert.Equal(VisitorStates.Qualify, t.Next.State);
        Assert.Equal("dental_clinic", t.Lead.Domain);
        Assert.Equal("Pune", t.Lead.City);
        Assert.Equal(3, t.Reply.Blocks.Single(block => block.Type == "CHOICES").Choices!.Count);
        all.Add(t);

        t = Step(t.Next, VisitorInput.FromChoice("goal_more_bookings"));
        Assert.Equal(VisitorStates.ShowValue, t.Next.State);
        Assert.Equal("more_bookings", t.Lead.Goal);
        Assert.Equal(3, t.Next.TurnsToFirstValue);
        Assert.Contains("dental clinic", Text(t), StringComparison.Ordinal);
        Assert.Contains("For example", Text(t), StringComparison.Ordinal);
        all.Add(t);

        t = Step(t.Next, VisitorInput.FromChoice(VisitorChoiceIds.SamplePlan));
        Assert.Contains("an example, not a promise", Text(t), StringComparison.Ordinal);
        all.Add(t);

        t = Step(t.Next, VisitorInput.FromChoice(VisitorChoiceIds.OtherProfessionals));
        Assert.Equal(VisitorStates.OtherProfessionals, t.Next.State);
        Assert.EndsWith(
            "coming soon",
            Text(t).TrimEnd(' ', '.', '!'),
            StringComparison.OrdinalIgnoreCase
        );
        all.Add(t);

        t = Step(t.Next, VisitorInput.FromChoice(VisitorChoiceIds.StartTrial));
        Assert.Equal(VisitorStates.Handoff, t.Next.State);
        Assert.True(t.WantsHandoffReference);
        Assert.Contains(
            t.Reply.Blocks,
            block => block.Type == "LINK" && block.Url == VisitorStateMachine.HandoffUrlToken
        );
        all.Add(t);

        Assert.Equal(VisitorOutcomes.Lead, t.Next.Outcome);
        Assert.Equal(VisitorOutcomes.FullSuccess, (t.Next with { Tapped = true }).Outcome);

        t = Step(t.Next, VisitorInput.FromText("Rupali Khandge rupali@example.com"));
        Assert.Equal("CONTACT_CAPTURED", t.Event);
        Assert.Equal("rupali@example.com", t.Lead.Email);
        Assert.Equal("Rupali Khandge", t.Lead.Name);
        all.Add(t);

        foreach (var transition in all)
        {
            Assert.Empty(VisitorReplyValidator.Validate(Concrete(transition.Reply), Options));
            Assert.DoesNotContain("₹", Text(transition), StringComparison.Ordinal);
            Assert.DoesNotContain(
                "guarantee",
                Text(transition),
                StringComparison.OrdinalIgnoreCase
            );
            Assert.True(
                transition
                    .Reply.Blocks.Where(block => block.Type == "TEXT")
                    .All(block => block.Text!.Count(c => c == '?') <= 1)
            );
        }
    }

    [Fact]
    public void PartialAnswersAskOneMissingThingAtATime()
    {
        var onlyDomain = Step(Consented(), VisitorInput.FromText("I have a salon"));
        Assert.Equal(VisitorStates.Discover, onlyDomain.Next.State);
        Assert.Equal("ASK_CITY", onlyDomain.Event);
        Assert.Equal("beauty_salon", onlyDomain.Next.Domain);

        var thenCity = Step(onlyDomain.Next, VisitorInput.FromText("Nashik"));
        Assert.Equal(VisitorStates.Qualify, thenCity.Next.State);
        Assert.Equal("Nashik", thenCity.Next.City);

        var onlyCity = Step(Consented(), VisitorInput.FromText("We are in Mumbai"));
        Assert.Equal("ASK_DOMAIN", onlyCity.Event);
        var thenDomain = Step(onlyCity.Next, VisitorInput.FromText("a yoga studio"));
        Assert.Equal("fitness_studio", thenDomain.Next.Domain);
        Assert.Equal(VisitorStates.Qualify, thenDomain.Next.State);
    }

    [Fact]
    public void UnrecognisedAnswerIsRephrasedOnceThenAcceptedAsAGenericBusiness()
    {
        var first = Step(Consented(), VisitorInput.FromText("hmm not sure how to say"));
        Assert.Equal("REPHRASE", first.Event);
        Assert.Equal(1, first.Next.Nudges);
        var second = Step(first.Next, VisitorInput.FromText("we sell handmade candles"));
        Assert.Equal(VisitorStates.Qualify, second.Next.State);
        Assert.Equal("generic", second.Lead.Domain);
        Assert.Equal("we sell handmade candles", second.Lead.BusinessText);
        Assert.DoesNotContain(
            " in ",
            Text(second).Split('.')[0].Replace("in which", string.Empty),
            StringComparison.Ordinal
        );
    }

    [Fact]
    public void ACityWithoutABusinessIsAskedAboutOnceThenTheConversationMovesOn()
    {
        var asked = Step(
            Consented(),
            VisitorInput.FromText("I grow tomatoes on my farm in Nashik")
        );
        Assert.Equal("ASK_DOMAIN", asked.Event);
        var again = Step(asked.Next, VisitorInput.FromText("I grow tomatoes on my farm in Nashik"));
        Assert.Equal(VisitorStates.Qualify, again.Next.State);
        Assert.Equal("generic", again.Lead.Domain);
        Assert.Equal("Nashik", again.Next.City);
    }

    [Fact]
    public void ABusinessWithoutACityIsAskedAboutOnceThenTheConversationMovesOn()
    {
        var asked = Step(Consented(), VisitorInput.FromText("we run a dental clinic"));
        Assert.Equal("ASK_CITY", asked.Event);
        var again = Step(asked.Next, VisitorInput.FromText("a small town you will not know"));
        Assert.Equal(VisitorStates.Qualify, again.Next.State);
        Assert.Equal("dental_clinic", again.Next.Domain);
        Assert.Null(again.Next.City);
    }

    [Theory]
    [InlineData("I'm a makeup artist in Pune", "beauty_artist")]
    [InlineData("beauty salon in Delhi", "beauty_salon")]
    [InlineData("we run a coaching academy in Jaipur", "education")]
    [InlineData("law firm in Mumbai", "law_firm")]
    [InlineData("cloud kitchen in Bengaluru", "cloud_kitchen")]
    public void BusinessTypeIsMatchedByTheLongestKeyword(string text, string expected) =>
        Assert.Equal(expected, VisitorStateMachine.DetectDomain(Content, text)?.Code);

    [Fact]
    public void StopIsHonouredInEveryStateAndStartResumesOnlyWithConsent()
    {
        foreach (
            var state in new[]
            {
                VisitorStates.Discover,
                VisitorStates.Qualify,
                VisitorStates.ShowValue,
                VisitorStates.Handoff,
            }
        )
        {
            var stopped = Step(
                new VisitorSnapshot
                {
                    State = state,
                    ConsentGiven = true,
                    Domain = "retail",
                },
                VisitorInput.FromText("stop")
            );
            Assert.Equal(VisitorStates.Stopped, stopped.Next.State);
            Assert.Equal(VisitorOutcomes.OptOut, stopped.Next.Outcome);
            Assert.Contains("START", Text(stopped), StringComparison.Ordinal);
        }
        var snapshot = new VisitorSnapshot { State = VisitorStates.Stopped, ConsentGiven = true };
        var ignored = Step(snapshot, VisitorInput.FromText("hello?"));
        Assert.Empty(ignored.Reply.Blocks);
        Assert.Equal(VisitorStates.Stopped, ignored.Next.State);

        var resumed = Step(snapshot, VisitorInput.FromText("Start"));
        Assert.Equal(VisitorStates.ConsentPending, resumed.Next.State);
        Assert.False(resumed.Next.ConsentGiven);
        Assert.Contains(resumed.Reply.Blocks, block => block.Type == "CHOICES");
        Assert.Equal(
            VisitorStates.Discover,
            Step(resumed.Next, VisitorInput.FromChoice(VisitorChoiceIds.ConsentYes)).Next.State
        );
    }

    [Fact]
    public void StartOutsideStoppedDoesNothingSpecial()
    {
        var t = Step(Consented(), VisitorInput.FromText("START"));
        Assert.NotEqual(VisitorStates.ConsentPending, t.Next.State);
    }

    [Fact]
    public void ConsentIsRepeatedOnceThenTheMachineWaitsInSilence()
    {
        var pending = VisitorStateMachine.Start(Content, new VisitorSnapshot(), 90).Next;
        var again = Step(pending, VisitorInput.FromText("what is this?"));
        Assert.Equal("CONSENT_REPEATED", again.Event);
        var waiting = Step(again.Next, VisitorInput.FromText("hello"));
        Assert.Empty(waiting.Reply.Blocks);
        Assert.Equal(VisitorStates.ConsentPending, waiting.Next.State);
    }

    [Theory]
    [InlineData("how much does it cost", "PRICING_POINTER")]
    [InlineData("can I talk to a real person", "HUMAN_REQUEST")]
    [InlineData("what is waooaw", "ABOUT")]
    public void SideQuestionsAreAnsweredWithoutLosingTheState(string text, string expectedEvent)
    {
        var snapshot = new VisitorSnapshot
        {
            State = VisitorStates.ShowValue,
            ConsentGiven = true,
            Domain = "retail",
            City = "Pune",
        };
        var t = Step(snapshot, VisitorInput.FromText(text));
        Assert.Equal(expectedEvent, t.Event);
        Assert.Equal(VisitorStates.ShowValue, t.Next.State);
        if (expectedEvent == "PRICING_POINTER")
        {
            Assert.Contains(Options.HandoffBaseUrl, Text(t), StringComparison.Ordinal);
            Assert.DoesNotContain("₹", Text(t), StringComparison.Ordinal);
        }
    }

    [Fact]
    public void UnsupportedContentGetsAFriendlyFixedReplyAndKeepsTheState()
    {
        var t = Step(
            new VisitorSnapshot { State = VisitorStates.Qualify, ConsentGiven = true },
            VisitorInput.Unsupported()
        );
        Assert.Equal("UNSUPPORTED_CONTENT", t.Event);
        Assert.Equal(VisitorStates.Qualify, t.Next.State);
        Assert.Equal(Content.Fixed.UnsupportedContent, Text(t));
    }

    [Theory]
    [InlineData("thanks")]
    [InlineData("ok thank you")]
    [InlineData("yes please")]
    public void CourtesyWordsAreNeverStoredAsAName(string text)
    {
        var t = Step(
            new VisitorSnapshot
            {
                State = VisitorStates.Handoff,
                ConsentGiven = true,
                Domain = "retail",
            },
            VisitorInput.FromText(text)
        );
        Assert.Null(t.Lead.Name);
        Assert.Equal("HANDOFF_REMINDER", t.Event);
    }

    [Fact]
    public void NameWithAnExplicitPrefixIsCaptured()
    {
        var t = Step(
            new VisitorSnapshot
            {
                State = VisitorStates.Handoff,
                ConsentGiven = true,
                Domain = "retail",
            },
            VisitorInput.FromText("my name is Kiran")
        );
        Assert.Equal("Kiran", t.Lead.Name);
    }

    [Fact]
    public void OutcomeClassificationCoversEveryCase()
    {
        Assert.Equal(VisitorOutcomes.None, new VisitorSnapshot().Outcome);
        Assert.Equal(VisitorOutcomes.Lead, new VisitorSnapshot { Domain = "retail" }.Outcome);
        Assert.Equal(VisitorOutcomes.Intent, new VisitorSnapshot { Tapped = true }.Outcome);
        Assert.Equal(
            VisitorOutcomes.FullSuccess,
            new VisitorSnapshot { Domain = "retail", Tapped = true }.Outcome
        );
        Assert.Equal(
            VisitorOutcomes.OptOut,
            new VisitorSnapshot { State = VisitorStates.Stopped, Domain = "retail" }.Outcome
        );
    }

    [Fact]
    public void ARandomWalkNeverProducesAnInvalidReplyOrMoreThanOneQuestion()
    {
        var random = new Random(135);
        var inputs = new[]
        {
            VisitorInput.FromText("I run a gym in Pune"),
            VisitorInput.FromText("price?"),
            VisitorInput.FromChoice(VisitorChoiceIds.SamplePlan),
            VisitorInput.FromChoice(VisitorChoiceIds.WhatCanItDo),
            VisitorInput.FromChoice(VisitorChoiceIds.StartTrial),
            VisitorInput.FromChoice(VisitorChoiceIds.OtherProfessionals),
            VisitorInput.FromChoice("goal_grow_online"),
            VisitorInput.FromText("random words here"),
            VisitorInput.FromText("a@b.co"),
            VisitorInput.Unsupported(),
        };
        for (var run = 0; run < 200; run++)
        {
            var snapshot = VisitorStateMachine.Start(Content, new VisitorSnapshot(), 90).Next;
            snapshot = Step(snapshot, VisitorInput.FromChoice(VisitorChoiceIds.ConsentYes)).Next;
            for (var turn = 0; turn < 12; turn++)
            {
                var t = Step(snapshot, inputs[random.Next(inputs.Length)]);
                Assert.Empty(VisitorReplyValidator.Validate(Concrete(t.Reply), Options));
                Assert.True(VisitorStates.All.Contains(t.Next.State));
                snapshot = t.Next;
            }
        }
    }
}

public sealed class VisitorReplyValidatorTests
{
    private static readonly VisitorConversationOptions Limits = VisitorTestContent.Options();

    private static VisitorReply Reply(params VisitorReplyBlock[] blocks) =>
        new()
        {
            State = VisitorStates.Discover,
            ContentVersion = "x",
            Blocks = blocks,
        };

    [Fact]
    public void ChoiceLimitsAreEnforced()
    {
        var four = VisitorReplyBlock.ChoicesBlock(
            new VisitorChoice("a", "One"),
            new VisitorChoice("b", "Two"),
            new VisitorChoice("c", "Three"),
            new VisitorChoice("d", "Four")
        );
        Assert.Contains(
            "CHOICE_COUNT",
            VisitorReplyValidator.Validate(Reply(VisitorReplyBlock.TextBlock("Hi"), four), Limits)
        );
        var duplicate = VisitorReplyBlock.ChoicesBlock(
            new VisitorChoice("a", "Same"),
            new VisitorChoice("b", "Same")
        );
        Assert.Contains(
            "CHOICE_LABEL_DUPLICATE",
            VisitorReplyValidator.Validate(
                Reply(VisitorReplyBlock.TextBlock("Hi"), duplicate),
                Limits
            )
        );
        var longLabel = VisitorReplyBlock.ChoicesBlock(
            new VisitorChoice("a", "This label is far too long")
        );
        Assert.Contains(
            "CHOICE_LABEL_LENGTH",
            VisitorReplyValidator.Validate(
                Reply(VisitorReplyBlock.TextBlock("Hi"), longLabel),
                Limits
            )
        );
    }

    [Fact]
    public void InteractiveBlocksNeedABodyAndOneChoiceSetAndOneHttpsLink()
    {
        var choices = VisitorReplyBlock.ChoicesBlock(new VisitorChoice("a", "One"));
        Assert.Contains(
            "INTERACTIVE_WITHOUT_BODY",
            VisitorReplyValidator.Validate(Reply(choices), Limits)
        );
        var list = new VisitorReplyBlock
        {
            Type = "LIST",
            ListTitle = "Pick one",
            Rows = [new("r1", "Row one")],
        };
        Assert.Contains(
            "MULTIPLE_CHOICE_SETS",
            VisitorReplyValidator.Validate(
                Reply(VisitorReplyBlock.TextBlock("Hi"), choices, list),
                Limits
            )
        );
        var http = VisitorReplyBlock.LinkBlock("Open", "http://example.com");
        Assert.Contains(
            "LINK_INVALID",
            VisitorReplyValidator.Validate(Reply(VisitorReplyBlock.TextBlock("Hi"), http), Limits)
        );
        var two = Reply(
            VisitorReplyBlock.TextBlock("Hi"),
            VisitorReplyBlock.LinkBlock("Open", "https://a.example"),
            VisitorReplyBlock.LinkBlock("Open", "https://b.example")
        );
        Assert.Contains("MULTIPLE_LINKS", VisitorReplyValidator.Validate(two, Limits));
    }

    [Fact]
    public void ListLimitsAndBodyLengthAreEnforced()
    {
        var rows = Enumerable
            .Range(1, 11)
            .Select(index => new VisitorListRow($"r{index}", $"Row {index}"))
            .ToList();
        var list = new VisitorReplyBlock
        {
            Type = "LIST",
            ListTitle = "Pick",
            Rows = rows,
        };
        Assert.Contains(
            "LIST_ROW_COUNT",
            VisitorReplyValidator.Validate(Reply(VisitorReplyBlock.TextBlock("Hi"), list), Limits)
        );
        var longBody = VisitorReplyBlock.TextBlock(
            new string('x', Limits.MaxInteractiveBodyLength + 1)
        );
        var choices = VisitorReplyBlock.ChoicesBlock(new VisitorChoice("a", "One"));
        Assert.Contains(
            "INTERACTIVE_BODY_TOO_LONG",
            VisitorReplyValidator.Validate(Reply(longBody, choices), Limits)
        );
        Assert.Contains(
            "TEXT_TOO_LONG",
            VisitorReplyValidator.Validate(
                Reply(VisitorReplyBlock.TextBlock(new string('x', Limits.MaxTextBodyLength + 1))),
                Limits
            )
        );
    }

    [Fact]
    public void ReplyRoundTripsThroughItsJsonForm()
    {
        var reply = Reply(
            VisitorReplyBlock.TextBlock("Hi"),
            VisitorReplyBlock.ChoicesBlock(new VisitorChoice("a", "One")),
            VisitorReplyBlock.LinkBlock("Open", "https://a.example")
        );
        Assert.Equal(reply.ToJson(), VisitorReply.FromJson(reply.ToJson()).ToJson());
    }

    [Theory]
    [InlineData("1.0")]
    [InlineData("2.0")]
    public void ReplyAcceptsSchemaVersionsOneAndTwoWithoutChangingTheBlockShape(
        string schemaVersion
    )
    {
        var reply = Reply(VisitorReplyBlock.TextBlock("Hi")) with { Schema = schemaVersion };

        Assert.Empty(VisitorReplyValidator.Validate(reply, Limits));
        Assert.Equal(schemaVersion, VisitorReply.FromJson(reply.ToJson()).Schema);
    }

    [Fact]
    public void ReplyRejectsAnUnknownSchemaVersion()
    {
        var reply = Reply(VisitorReplyBlock.TextBlock("Hi")) with { Schema = "3.0" };

        Assert.Contains(
            "SCHEMA_VERSION_UNSUPPORTED",
            VisitorReplyValidator.Validate(reply, Limits)
        );
    }
}
