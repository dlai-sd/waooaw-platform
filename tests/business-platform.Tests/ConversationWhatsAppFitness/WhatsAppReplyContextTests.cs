// Implements: WC-134 signed inbound clarification context.
// constitutional_basis: C-023, C-026, C-059, C-063
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppReplyContextTests
{
    [Fact]
    public void ProviderReferenceIsDigestedExactlyAsTheOutboundOwnerStoresIt()
    {
        using var document = JsonDocument.Parse(
            """{"context":{"from":"synthetic-sender","id":"synthetic-provider-message"}}"""
        );
        var expected = Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes("synthetic-provider-message"))
        );
        Assert.Equal(expected, WhatsAppJourneyService.ReadReplyContextDigest(document.RootElement));
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("""{"context":null}""")]
    [InlineData("""{"context":{}}""")]
    [InlineData("""{"context":{"id":""}}""")]
    [InlineData("""{"context":{"id":"  "}}""")]
    [InlineData("""{"context":{"id":123}}""")]
    public void MissingOrMalformedReferenceCannotIdentifyAQuestion(string json)
    {
        using var document = JsonDocument.Parse(json);
        Assert.Null(WhatsAppJourneyService.ReadReplyContextDigest(document.RootElement));
    }

    [Fact]
    public void LongReferenceUsesTheSameDigestAsTheOutboundOwner()
    {
        var id = new string('x', 257);
        using var document = JsonDocument.Parse(
            JsonSerializer.Serialize(new { context = new { id } })
        );
        var expected = Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(id)));
        Assert.Equal(expected, WhatsAppJourneyService.ReadReplyContextDigest(document.RootElement));
    }

    [Fact]
    public void ProviderParsingCarriesReplyContextWithoutChangingExistingEventDigest()
    {
        static string Payload(string? replyId) =>
            JsonSerializer.Serialize(
                new
                {
                    entry = new[]
                    {
                        new
                        {
                            id = "synthetic-waba",
                            changes = new[]
                            {
                                new
                                {
                                    value = new
                                    {
                                        metadata = new { phone_number_id = "synthetic-phone" },
                                        messages = new[]
                                        {
                                            new
                                            {
                                                id = "synthetic-inbound",
                                                from = "synthetic-sender",
                                                timestamp = "1767225600",
                                                type = "text",
                                                text = new { body = "ONE" },
                                                context = replyId is null
                                                    ? null
                                                    : new { id = replyId },
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                }
            );
        using var first = JsonDocument.Parse(Payload("question-one"));
        using var second = JsonDocument.Parse(Payload("question-two"));
        using var noContext = JsonDocument.Parse(Payload(null));
        var firstMessage = Assert.Single(
            WhatsAppJourneyService.ParseProviderMessages(first.RootElement)
        );
        var secondMessage = Assert.Single(
            WhatsAppJourneyService.ParseProviderMessages(second.RootElement)
        );
        var plainMessage = Assert.Single(
            WhatsAppJourneyService.ParseProviderMessages(noContext.RootElement)
        );

        Assert.NotEqual(firstMessage.ReplyContextDigest, secondMessage.ReplyContextDigest);
        Assert.Null(plainMessage.ReplyContextDigest);
        Assert.Equal(firstMessage.PayloadDigest, secondMessage.PayloadDigest);
        Assert.Equal(firstMessage.PayloadDigest, plainMessage.PayloadDigest);
    }
}
