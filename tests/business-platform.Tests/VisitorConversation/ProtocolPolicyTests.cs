// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C1-01
// Constitutional basis: C-009, C-039, C-059, C-063

using Waooaw.BusinessPlatform.Services.Visitor;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.VisitorConversation;

public sealed class ProtocolPolicyTests
{
    private static readonly VisitorConversationOptions Limits = VisitorTestContent.Options();

    private static VisitorTransition Step(
        VisitorContentSet content,
        VisitorSnapshot snapshot,
        string text
    ) => VisitorStateMachine.Step(content, Limits, snapshot, VisitorInput.FromText(text), 90);

    private static VisitorContentSet WithProtocol(
        Func<VisitorProtocolContent, VisitorProtocolContent> change
    )
    {
        var content = VisitorTestContent.Shipped();
        return content with { Protocol = change(content.Protocol) };
    }

    [Fact]
    public void ShippedProtocolPolicyIsValidAndAcknowledgesStopOnEveryChannel()
    {
        var content = VisitorTestContent.Shipped();

        Assert.Empty(VisitorContentValidator.Validate(content, Limits));
        Assert.Equal("1.0.0", content.Protocol.Version);
        Assert.Equal(1, content.Protocol.Stop.MaximumAcknowledgementsPerStop);
        Assert.True(content.Protocol.Start.ConsentRequiredAgain);
        foreach (var channel in new[] { "API", "WHATSAPP", "SIMULATION" })
            Assert.True(content.Protocol.AcknowledgesStopOn(channel));
        Assert.False(content.Protocol.AcknowledgesStopOn("SMS"));
        Assert.Equal(
            content.Fixed.StopAcknowledged,
            content.ResolveFixed(content.Protocol.Stop.AcknowledgementRef)
        );
        Assert.Equal(
            content.Fixed.ResumeNotice,
            content.ResolveFixed(content.Protocol.Start.NoticeRef)
        );
    }

    [Fact]
    public void ContentWithoutAProtocolPolicyFailsClosed()
    {
        var broken = VisitorTestContent.Shipped() with { Protocol = null! };

        Assert.Contains("PROTOCOL_MISSING", VisitorContentValidator.Validate(broken, Limits));
    }

    [Fact]
    public void EachInvalidProtocolPolicyIsRejectedWithItsOwnProblemCode()
    {
        Assert.Contains(
            "PROTOCOL_VERSION_MISSING",
            VisitorContentValidator.Validate(WithProtocol(p => p with { Version = " " }), Limits)
        );
        Assert.Contains(
            "PROTOCOL_STOP_ACKNOWLEDGEMENT_UNRESOLVED",
            VisitorContentValidator.Validate(
                WithProtocol(p =>
                    p with
                    {
                        Stop = p.Stop with { AcknowledgementRef = "fixed.doesNotExist" },
                    }
                ),
                Limits
            )
        );
        Assert.Contains(
            "PROTOCOL_STOP_MAXIMUM_INVALID",
            VisitorContentValidator.Validate(
                WithProtocol(p =>
                    p with
                    {
                        Stop = p.Stop with { MaximumAcknowledgementsPerStop = 2 },
                    }
                ),
                Limits
            )
        );
        Assert.Contains(
            "PROTOCOL_STOP_CHANNELS_EMPTY",
            VisitorContentValidator.Validate(
                WithProtocol(p => p with { Stop = p.Stop with { Channels = [] } }),
                Limits
            )
        );
        Assert.Contains(
            "PROTOCOL_START_NOTICE_UNRESOLVED",
            VisitorContentValidator.Validate(
                WithProtocol(p => p with { Start = p.Start with { NoticeRef = "" } }),
                Limits
            )
        );
        Assert.Contains(
            "PROTOCOL_START_CONSENT_REQUIRED",
            VisitorContentValidator.Validate(
                WithProtocol(p => p with { Start = p.Start with { ConsentRequiredAgain = false } }),
                Limits
            )
        );
    }

    [Fact]
    public void StopWithAcknowledgementEmitsTheReferencedTextExactlyOnce()
    {
        var content = VisitorTestContent.Shipped();
        var snapshot = new VisitorSnapshot
        {
            State = VisitorStates.Discover,
            ConsentGiven = true,
            Domain = "retail",
        };

        var stopped = Step(content, snapshot, "STOP");

        Assert.Equal(VisitorStates.Stopped, stopped.Next.State);
        Assert.Equal(VisitorOutcomes.OptOut, stopped.Next.Outcome);
        var block = Assert.Single(stopped.Reply.Blocks);
        Assert.Equal(content.Fixed.StopAcknowledged, block.Text);

        var after = Step(content, stopped.Next, "are you there?");
        Assert.Empty(after.Reply.Blocks);
        Assert.Equal(VisitorStates.Stopped, after.Next.State);
        Assert.Empty(Step(content, stopped.Next, "STOP").Reply.Blocks);
    }

    [Fact]
    public void StopWithoutAcknowledgementIsSilentButStillOptsOut()
    {
        var content = WithProtocol(p => p with { Stop = p.Stop with { Acknowledge = false } });
        var snapshot = new VisitorSnapshot { State = VisitorStates.Discover, ConsentGiven = true };

        var stopped = Step(content, snapshot, "STOP");

        Assert.Equal(VisitorStates.Stopped, stopped.Next.State);
        Assert.Equal(VisitorOutcomes.OptOut, stopped.Next.Outcome);
        Assert.Empty(stopped.Reply.Blocks);
    }

    [Fact]
    public void ResumeNoticeComesFromTheStartPolicyAndConsentIsRequiredAgain()
    {
        var content = WithProtocol(p =>
            p with
            {
                Start = p.Start with { NoticeRef = "fixed.closedNotice" },
            }
        );
        var stoppedSnapshot = new VisitorSnapshot
        {
            State = VisitorStates.Stopped,
            ConsentGiven = true,
        };

        var resumed = Step(content, stoppedSnapshot, "START");

        Assert.Equal(VisitorStates.ConsentPending, resumed.Next.State);
        Assert.False(resumed.Next.ConsentGiven);
        Assert.Contains(resumed.Reply.Blocks, block => block.Text == content.Fixed.ClosedNotice);
        Assert.Contains(resumed.Reply.Blocks, block => block.Type == "CHOICES");
    }

    [Fact]
    public void GuestCopyCarriesThePolicyAndTheLegacyCopyStaysSilent()
    {
        var content = VisitorTestContent.Shipped();
        var copy = GuestCopy.FromContent(content, 90);

        Assert.True(copy.Protocol.AcknowledgesStopOn("WHATSAPP"));
        Assert.Equal(content.Fixed.StopAcknowledged, copy.StopAcknowledged);
        Assert.Contains(content.Fixed.StopAcknowledged, copy.PreConsentTexts());
        Assert.False(GuestCopy.Legacy.Protocol.AcknowledgesStopOn("WHATSAPP"));
    }
}
