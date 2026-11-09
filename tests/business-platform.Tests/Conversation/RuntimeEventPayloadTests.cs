// Implements: WC-134 R006/R007; runtime event payload boundary.
// constitutional_basis: C-023, C-059, C-063
using System.Text.Json;
using System.Text.Json.Nodes;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class RuntimeEventPayloadTests
{
    private static RuntimeExecutionEventV1 Event(string type, JsonNode data) =>
        new(
            "1.0",
            "test",
            type,
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            1,
            DateTimeOffset.UtcNow,
            JsonSerializer.SerializeToElement(data)
        );

    public static IEnumerable<object[]> ValidPayloads()
    {
        foreach (var type in new[] { "execution.accepted", "processing.started", "heartbeat" })
            yield return [type, """{"serverTime":"2026-01-01T00:00:00Z"}"""];
        yield return ["response.delta", """{"contentIndex":0,"appendText":"","partial":true}"""];
        yield return ["response.system", """{"text":"Unavailable","code":"MODEL_UNAVAILABLE"}"""];
        yield return
        [
            "card.proposed",
            """{"schemaVersion":"1.0","cardType":"ACTION","cardId":"00000000-0000-0000-0000-000000000001","owner":"CUSTOMER","state":"DRAFT","effect":"review","data":{}}""",
        ];
        yield return ["evidence.pending", """{"state":"PENDING"}"""];
        yield return
        [
            "evidence.recorded",
            """{"state":"RECORDED","evidenceRecordId":"00000000-0000-0000-0000-000000000001"}""",
        ];
        yield return ["reconciliation.required", """{"reason":"EVENT_GAP"}"""];
        yield return
        [
            "execution.completed",
            """{"state":"COMPLETED","completionReason":"COMPLETE","partial":false}""",
        ];
        yield return
        [
            "execution.failed",
            """{"state":"FAILED","completionReason":"PARTIAL_FAILURE","partial":true,"errorCode":null}""",
        ];
        yield return
        [
            "execution.cancelled",
            """{"state":"CANCELLED","completionReason":"CANCELLED","partial":false,"errorCode":"cancelled"}""",
        ];
        yield return
        [
            "execution.stopped",
            """{"state":"STOPPED","completionReason":"EMERGENCY_STOPPED","partial":false}""",
        ];
    }

    [Theory]
    [MemberData(nameof(ValidPayloads))]
    public void ValidPayloadIsAcceptedAndMissingFieldsAreRejected(string type, string json)
    {
        var data = JsonNode.Parse(json)!.AsObject();
        RuntimeEventStreamReader.ValidatePayload(Event(type, data));
        foreach (
            var field in data.Select(pair => pair.Key).Where(key => key != "errorCode").ToArray()
        )
        {
            var changed = JsonNode.Parse(json)!.AsObject();
            changed.Remove(field);
            Assert.Throws<JsonException>(() =>
                RuntimeEventStreamReader.ValidatePayload(Event(type, changed))
            );
        }
    }

    [Theory]
    [InlineData("response.delta", """{"contentIndex":-1,"appendText":"x","partial":true}""")]
    [InlineData("response.delta", """{"contentIndex":0,"appendText":"x","partial":false}""")]
    [InlineData("response.system", """{"text":"","code":"MODEL_UNAVAILABLE"}""")]
    [InlineData("response.system", """{"text":"x","code":"OTHER"}""")]
    [InlineData(
        "card.proposed",
        """{"schemaVersion":"1.0","cardType":"ACTION","cardId":"00000000-0000-0000-0000-000000000000","owner":"CUSTOMER","state":"DRAFT","effect":"review","data":{}}"""
    )]
    [InlineData(
        "card.proposed",
        """{"schemaVersion":"1.0","cardType":"ACTION","cardId":"00000000-0000-0000-0000-000000000001","owner":"OTHER","state":"DRAFT","effect":"review","data":{}}"""
    )]
    [InlineData(
        "evidence.recorded",
        """{"state":"RECORDED","evidenceRecordId":"00000000-0000-0000-0000-000000000000"}"""
    )]
    [InlineData("reconciliation.required", """{"reason":"OTHER"}""")]
    [InlineData(
        "execution.completed",
        """{"state":"COMPLETED","completionReason":"COMPLETE","partial":false,"errorCode":123}"""
    )]
    [InlineData("heartbeat", """{"serverTime":"not-a-time"}""")]
    [InlineData("unknown", "{}")]
    public void RejectsWrongValuesAndUnknownEventTypes(string type, string json) =>
        Assert.Throws<JsonException>(() =>
            RuntimeEventStreamReader.ValidatePayload(Event(type, JsonNode.Parse(json)!))
        );

    [Fact]
    public void RejectsOversizedAndNullContainingText()
    {
        var oversized = new JsonObject
        {
            ["text"] = new string('x', 8001),
            ["code"] = "MODEL_UNAVAILABLE",
        };
        var embeddedNull = new JsonObject { ["text"] = "a\0b", ["code"] = "MODEL_UNAVAILABLE" };
        Assert.Throws<JsonException>(() =>
            RuntimeEventStreamReader.ValidatePayload(Event("response.system", oversized))
        );
        Assert.Throws<JsonException>(() =>
            RuntimeEventStreamReader.ValidatePayload(Event("response.system", embeddedNull))
        );
    }
}
