// Implements: WC-134 customer request-boundary clarification.
// constitutional_basis: C-023, C-026, C-059, C-063
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class ConversationRequestClarificationTests
{
    [Theory]
    [InlineData("ONE", "OneRequest")]
    [InlineData(" one ", "OneRequest")]
    [InlineData("SEPARATE", "SeparateRequests")]
    [InlineData(" separate ", "SeparateRequests")]
    public void OnlyExplicitOptionsResolveTheBoundary(string response, string expected) =>
        Assert.Equal(expected, ConversationRequestClarification.Interpret(response).ToString());

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("  ")]
    [InlineData("YES")]
    [InlineData("NO")]
    [InlineData("one or separate")]
    [InlineData("one more request")]
    [InlineData("separate, but combine these")]
    [InlineData("1")]
    public void AmbiguousTextDoesNotResolveTheBoundary(string? response) =>
        Assert.Equal(
            ConversationRequestBoundary.Unclear,
            ConversationRequestClarification.Interpret(response)
        );

    [Fact]
    public void QuestionDisplaysBothExplicitOptions()
    {
        Assert.Contains("ONE", ConversationRequestClarification.Question);
        Assert.Contains("SEPARATE", ConversationRequestClarification.Question);
    }

    [Fact]
    public void ClarificationReplayDigestBindsTheExactOrderedSourceSet()
    {
        var contribution = new OutboundConversationContributionV1(
            "SYSTEM",
            "TEXT",
            "ASK",
            ConversationRequestClarification.Question,
            "skill",
            "1.0",
            "WHATSAPP",
            Guid.NewGuid(),
            "canonical-question",
            new string('a', 64),
            true,
            new(
                true,
                false,
                false,
                DateTimeOffset.UtcNow,
                "CUSTOMER_REQUEST",
                new string('b', 64),
                null,
                null,
                null,
                null,
                false
            )
        );
        var first = Guid.NewGuid();
        var second = Guid.NewGuid();
        var original = ConversationOutboundContributionService.DigestClarificationQuestion(
            contribution,
            [first, second]
        );

        Assert.Equal(
            original,
            ConversationOutboundContributionService.DigestClarificationQuestion(
                contribution,
                [first, second]
            )
        );
        Assert.NotEqual(
            original,
            ConversationOutboundContributionService.DigestClarificationQuestion(
                contribution,
                [second, first]
            )
        );
        Assert.NotEqual(
            original,
            ConversationOutboundContributionService.DigestClarificationQuestion(
                contribution,
                [first, Guid.NewGuid()]
            )
        );
    }
}
