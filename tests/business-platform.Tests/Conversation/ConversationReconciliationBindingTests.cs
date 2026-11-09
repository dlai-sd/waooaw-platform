// Implements: architecture/reference/components/conversation-core.md section 4.2.
// constitutional_basis: C-023, C-026, C-059, C-063
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class ConversationReconciliationBindingTests
{
    [Fact]
    public void RecoveryDigestMatchesPythonAsciiCanonicalizationIncludingSurrogatePairsAndDel()
    {
        const string json = """
            {
              "schemaVersion":"1.0",
              "conversationId":"00000000-0000-4000-8000-000000000001",
              "executionId":"00000000-0000-4000-8000-000000000001",
              "originalMessageId":"00000000-0000-4000-8000-000000000001",
              "originalSourceDigest":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
              "reconciliationAuthorityId":"00000000-0000-4000-8000-000000000001",
              "state":"COMPLETED",
              "events":[
                {
                  "schemaVersion":"1.0","eventId":"00000000-0000-4000-8000-000000000001:1",
                  "eventType":"response.delta","conversationId":"00000000-0000-4000-8000-000000000001",
                  "executionId":"00000000-0000-4000-8000-000000000001",
                  "messageId":"00000000-0000-4000-8000-000000000001","sequence":1,
                  "occurredAt":"2026-11-08T00:00:00+00:00",
                  "data":{"contentIndex":0,"appendText":"\u0939\u093f \ud83d\ude00\u007f","partial":true}
                },
                {
                  "schemaVersion":"1.0","eventId":"00000000-0000-4000-8000-000000000001:2",
                  "eventType":"execution.completed","conversationId":"00000000-0000-4000-8000-000000000001",
                  "executionId":"00000000-0000-4000-8000-000000000001",
                  "messageId":"00000000-0000-4000-8000-000000000001","sequence":2,
                  "occurredAt":"2026-11-08T00:00:00+00:00",
                  "data":{"state":"COMPLETED","partial":false,"completionReason":"COMPLETE"}
                }
              ],
              "nextAction":"RECONCILE_CANONICAL_PROJECTION",
              "originalRequestDigest":"sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
              "resultDigest":"sha256:1d10f4e99b05551bdaafd8f360b870bccbe51fe1281acb23059f839c6302c047"
            }
            """;
        var id = Guid.Parse("00000000-0000-4000-8000-000000000001");
        var source = new ConversationOriginalSourceV1("1.0", id, id, id, id, id, id, id, "sha256:" + new string('a', 64));
        var permission = new ConversationReconciliationAuthority
        {
            AuthorityId = id, SourceDigest = "sha256:" + new string('a', 64),
        };
        using var wire = JsonDocument.Parse(json);
        var result = wire.RootElement.Deserialize<RuntimeReconciliationResultV1>(ConversationReconciliationBinding.Json)!;
        HttpConversationExecutionGateway.ValidateReconciliationResult(result, wire.RootElement, source, permission, 0);
        using var altered = JsonDocument.Parse(json.Replace("\\u007f", "\\u0080", StringComparison.Ordinal));
        var drift = altered.RootElement.Deserialize<RuntimeReconciliationResultV1>(ConversationReconciliationBinding.Json)!;
        Assert.Throws<ConversationStateConflictException>(() =>
            HttpConversationExecutionGateway.ValidateReconciliationResult(drift, altered.RootElement, source, permission, 0));
    }

    [Theory]
    [InlineData(4096, true)]
    [InlineData(4097, false)]
    public void RetainedRecoveryEventBoundIsInclusiveAndRejectsOneExtraEvent(int count, bool allowed)
    {
        var source = Source();
        var permission = Permission(source);
        var events = Enumerable.Range(1, count).Select(sequence => new RuntimeExecutionEventV1(
            "1.0", $"{source.ExecutionId:D}:{sequence}", sequence == count ? "execution.completed" : "response.delta",
            source.ConversationId, source.ExecutionId, source.OriginalMessageId, sequence,
            new DateTimeOffset(2026, 11, 8, 0, 0, 0, TimeSpan.Zero),
            sequence == count
                ? JsonSerializer.SerializeToElement(new { state = "COMPLETED", partial = false, completionReason = "COMPLETE" })
                : JsonSerializer.SerializeToElement(new { contentIndex = 0, appendText = "a", partial = true }))).ToArray();
        var result = new RuntimeReconciliationResultV1("1.0", source.ConversationId, source.ExecutionId,
            source.OriginalMessageId, permission.SourceDigest, permission.AuthorityId, "COMPLETED", events,
            "RECONCILE_CANONICAL_PROJECTION", "sha256:" + new string('b', 64));
        result = result with { ResultDigest = ConversationReconciliationBinding.Digest(result) };
        using var wire = JsonDocument.Parse(JsonSerializer.Serialize(result, ConversationReconciliationBinding.Json));
        if (allowed)
            HttpConversationExecutionGateway.ValidateReconciliationResult(result, wire.RootElement, source, permission, 0);
        else
            Assert.Throws<ConversationStateConflictException>(() =>
                HttpConversationExecutionGateway.ValidateReconciliationResult(result, wire.RootElement, source, permission, 0));
    }

    [Fact]
    public async Task ExecutionVersionAdvancesOnlyWhenExecutionMutates()
    {
        await using var db = new ConversationStoreDbContext(
            new DbContextOptionsBuilder<ConversationStoreDbContext>()
                .UseInMemoryDatabase(Guid.NewGuid().ToString()).Options);
        var execution = new ConversationExecution { TenantId = Guid.NewGuid(), RelationshipId = Guid.NewGuid() };
        db.Executions.Add(execution);
        await db.SaveChangesAsync();
        Assert.Equal(0, execution.ProjectionVersion);
        execution.RuntimeSequence = 1;
        db.AdvanceProjectionVersions();
        Assert.Equal(1, execution.ProjectionVersion);
        db.AdvanceProjectionVersions();
        Assert.Equal(1, execution.ProjectionVersion);
        await db.SaveChangesAsync();
        Assert.Equal(1, execution.ProjectionVersion);
        db.SaveChanges();
        Assert.Equal(1, execution.ProjectionVersion);
        execution.ProcessingState = "CANCELLED";
        db.SaveChanges();
        Assert.Equal(2, execution.ProjectionVersion);
    }

    [Fact]
    public void PublicRecoveryRequestCannotCarryCallerSuppliedAuthority()
    {
        var value = $$"""{"schemaVersion":"1.0","expectedMessageId":"{{Guid.NewGuid()}}","expectedProjectionVersion":1,"tenantId":"{{Guid.NewGuid()}}"}""";
        Assert.Throws<JsonException>(() =>
            JsonSerializer.Deserialize<ReconcileConversationExecutionRequestV1>(value, ConversationReconciliationBinding.Json));
    }

    [Theory]
    [InlineData("")]
    [InlineData(",\"expectedProjectionVersion\":\"0\"")]
    [InlineData(",\"expectedProjectionVersion\":0.5")]
    public void RecoveryVersionIsRequiredAndCannotUsePermissiveWebNumberCoercion(string version)
    {
        var value = $$"""{"schemaVersion":"1.0","expectedMessageId":"{{Guid.NewGuid()}}"{{version}}}""";
        Assert.Throws<JsonException>(() =>
            JsonSerializer.Deserialize<ReconcileConversationExecutionRequestV1>(value, ConversationReconciliationBinding.Json));
    }

    [Fact]
    public void OriginalSourceFingerprintBindsOriginalActorAndMandateNotFreshRequester()
    {
        var source = Source();
        var digest = ConversationReconciliationBinding.Digest(source);
        Assert.StartsWith("sha256:", digest);
        Assert.NotEqual(digest, ConversationReconciliationBinding.Digest(source with { OriginalActorId = Guid.NewGuid() }));
        Assert.NotEqual(digest, ConversationReconciliationBinding.Digest(source with { MandateDigest = "sha256:" + new string('b', 64) }));
        Assert.Equal(digest, ConversationReconciliationBinding.Digest(source with { }));
    }

    [Fact]
    public void UnknownResultCannotCarrySuccessContentOrUsageProof()
    {
        var source = Source();
        var permission = Permission(source);
        var unknown = new RuntimeReconciliationResultV1("1.0", source.ConversationId, source.ExecutionId,
            source.OriginalMessageId, permission.SourceDigest, permission.AuthorityId, "UNKNOWN", [],
            "OPERATOR_RECONCILIATION_REQUIRED");
        using var wire = JsonDocument.Parse(JsonSerializer.Serialize(unknown, ConversationReconciliationBinding.Json));
        HttpConversationExecutionGateway.ValidateReconciliationResult(unknown, wire.RootElement, source, permission, 0);
        var falseSuccess = unknown with { OriginalRequestDigest = "sha256:" + new string('c', 64) };
        Assert.Throws<ConversationStateConflictException>(() =>
            HttpConversationExecutionGateway.ValidateReconciliationResult(falseSuccess, wire.RootElement, source, permission, 0));
    }

    [Fact]
    public void RetainedResultCannotChangeSourceOrAuthority()
    {
        var source = Source();
        var permission = Permission(source);
        var unknown = new RuntimeReconciliationResultV1("1.0", source.ConversationId, source.ExecutionId,
            source.OriginalMessageId, permission.SourceDigest, Guid.NewGuid(), "UNKNOWN", [],
            "OPERATOR_RECONCILIATION_REQUIRED");
        using var wire = JsonDocument.Parse(JsonSerializer.Serialize(unknown, ConversationReconciliationBinding.Json));
        Assert.Throws<ConversationStateConflictException>(() =>
            HttpConversationExecutionGateway.ValidateReconciliationResult(unknown, wire.RootElement, source, permission, 0));
    }

    private static ConversationOriginalSourceV1 Source() => new("1.0", Guid.NewGuid(), Guid.NewGuid(),
        Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), "sha256:" + new string('a', 64));

    private static ConversationReconciliationAuthority Permission(ConversationOriginalSourceV1 source) => new()
    {
        AuthorityId = Guid.NewGuid(), TenantId = source.TenantId, RelationshipId = source.RelationshipId,
        SourceDigest = ConversationReconciliationBinding.Digest(source),
    };
}
