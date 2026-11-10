// Implements: WC-134 R006/R007; runtime event stream identity and framing.
// constitutional_basis: C-023, C-059, C-063
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class RuntimeEventStreamReaderTests
{
    private static readonly Guid Conversation = Guid.Parse("10000000-0000-0000-0000-000000000001");
    private static readonly Guid Execution = Guid.Parse("20000000-0000-0000-0000-000000000002");
    private static readonly Guid Message = Guid.Parse("30000000-0000-0000-0000-000000000003");

    private static string EventId(long sequence) => $"{Execution:D}:{sequence}";

    private static JsonObject Body(long sequence, string type = "response.delta") =>
        new()
        {
            ["schemaVersion"] = "1.0",
            ["eventId"] = EventId(sequence),
            ["eventType"] = type,
            ["conversationId"] = Conversation,
            ["executionId"] = Execution,
            ["messageId"] = Message,
            ["sequence"] = sequence,
            ["occurredAt"] = "2026-01-01T00:00:00Z",
            ["data"] =
                type == "execution.completed"
                    ? new JsonObject
                    {
                        ["state"] = "COMPLETED",
                        ["completionReason"] = "COMPLETE",
                        ["partial"] = false,
                    }
                    : new JsonObject
                    {
                        ["contentIndex"] = 0,
                        ["appendText"] = "hello",
                        ["partial"] = true,
                    },
        };

    private static string Frame(JsonObject body, string? id = null, string? type = null) =>
        $"id: {id ?? body["eventId"]!.GetValue<string>()}\nevent: {type ?? body["eventType"]!.GetValue<string>()}\ndata: {body.ToJsonString()}\n\n";

    private static RuntimeEventStreamReader Reader(string input, long afterSequence = 0) =>
        new(
            new MemoryStream(Encoding.UTF8.GetBytes(input)),
            Conversation,
            Message,
            Execution,
            afterSequence
        );

    [Fact]
    public async Task ReadsContiguousEventsAndStopsAtTerminal()
    {
        var reader = Reader(
            ": keepalive\n\n" + Frame(Body(1)) + Frame(Body(2, "execution.completed"))
        );
        var first = await reader.NextAsync(CancellationToken.None);
        var terminal = await reader.NextAsync(CancellationToken.None);
        Assert.Equal("response.delta", first!.EventType);
        Assert.Equal("execution.completed", terminal!.EventType);
        Assert.Null(await reader.NextAsync(CancellationToken.None));
    }

    [Theory]
    [InlineData("schemaVersion", "2.0")]
    [InlineData("eventType", "unknown")]
    [InlineData("conversationId", "10000000-0000-0000-0000-000000000099")]
    [InlineData("executionId", "20000000-0000-0000-0000-000000000099")]
    [InlineData("messageId", "30000000-0000-0000-0000-000000000099")]
    [InlineData("eventId", "unbound")]
    [InlineData("occurredAt", "0001-01-01T00:00:00Z")]
    public async Task RejectsWrongIdentityOrContract(string field, string value)
    {
        var body = Body(1);
        body[field] = value;
        var reader = Reader(Frame(body, EventId(1), "response.delta"));
        await Assert.ThrowsAsync<JsonException>(() => reader.NextAsync(CancellationToken.None));
    }

    [Fact]
    public async Task RejectsGapAndRepeatedFrameFields()
    {
        await Assert.ThrowsAsync<IOException>(() =>
            Reader(Frame(Body(2))).NextAsync(CancellationToken.None)
        );
        await Assert.ThrowsAsync<IOException>(() =>
            Reader("id: a\nid: b\n\n").NextAsync(CancellationToken.None)
        );
        await Assert.ThrowsAsync<IOException>(() =>
            Reader("event: a\nevent: b\n\n").NextAsync(CancellationToken.None)
        );
    }

    [Fact]
    public async Task RejectsTruncatedAndOversizedFrames()
    {
        await Assert.ThrowsAsync<IOException>(() =>
            Reader("data: incomplete").NextAsync(CancellationToken.None)
        );
        await Assert.ThrowsAsync<IOException>(() =>
            Reader("data: " + new string('x', 262145) + "\n\n").NextAsync(CancellationToken.None)
        );
    }

    [Fact]
    public async Task RejectsDuplicateNestedProperties()
    {
        var json = Body(1)
            .ToJsonString()
            .Replace("\"partial\":true", "\"partial\":true,\"Partial\":true");
        var reader = Reader($"id: {EventId(1)}\nevent: response.delta\ndata: {json}\n\n");
        await Assert.ThrowsAsync<JsonException>(() => reader.NextAsync(CancellationToken.None));
    }
}
