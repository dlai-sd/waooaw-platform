// Implements: work-contracts/WC-134-runtime-generation-and-reconciliation-policy.md §Bounded canonical resume
// constitutional_basis: C-023, C-026, C-059, C-063

using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class ConversationResumeContextReaderTests
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    private static ConversationStoreDbContext Database() =>
        new(
            new DbContextOptionsBuilder<ConversationStoreDbContext>()
                .UseInMemoryDatabase(Guid.NewGuid().ToString())
                .Options
        );

    private static ConversationMessage Input() =>
        new()
        {
            TenantId = Guid.NewGuid(),
            RelationshipId = Guid.NewGuid(),
            ConversationId = Guid.NewGuid(),
            SkillId = "dma:customer-profiling",
            Sequence = 100,
            AcceptedAt = DateTimeOffset.UtcNow,
        };

    private static ConversationMessage Prior(
        ConversationMessage input,
        long sequence,
        string text = "Prior turn",
        string defect = ""
    ) =>
        new()
        {
            TenantId = defect == "tenant" ? Guid.NewGuid() : input.TenantId,
            RelationshipId = defect == "relationship" ? Guid.NewGuid() : input.RelationshipId,
            ConversationId = defect == "conversation" ? Guid.NewGuid() : input.ConversationId,
            SkillId = defect == "skill" ? "trading:research" : input.SkillId,
            Sequence = defect == "future-sequence" ? 101 : sequence,
            Actor =
                defect == "actor" ? "SYSTEM"
                : sequence % 2 == 0 ? "PROFESSIONAL"
                : "CUSTOMER",
            Partial = defect == "partial",
            ProcessingState = defect == "pending" ? "RUNNING" : "COMPLETED",
            AcceptedAt = input.AcceptedAt.AddDays(defect == "retention" ? -8 : -1),
            CompletedAt =
                defect == "late-completion"
                    ? input.AcceptedAt.AddMinutes(1)
                    : input.AcceptedAt.AddHours(-1),
            ContentJson = JsonSerializer.Serialize(
                new[] { new ConversationTextBlockV1("1.0", "TEXT", text, "en") },
                Json
            ),
        };

    [Fact]
    public async Task ResumeIsNewestTwelveOrderedCanonicalTurnsAndStableAcrossIdleTime()
    {
        await using var db = Database();
        var input = Input();
        db.Messages.AddRange(Enumerable.Range(1, 20).Select(sequence => Prior(input, sequence)));
        await db.SaveChangesAsync();
        var context = await ConversationResumeContextReader.ReadAsync(
            db,
            input,
            CancellationToken.None
        );
        var turns = context.GetProperty("turns").EnumerateArray().ToArray();
        Assert.Equal(12, turns.Length);
        Assert.Equal(9, turns[0].GetProperty("sequence").GetInt64());
        Assert.Equal(20, turns[^1].GetProperty("sequence").GetInt64());
        Assert.Contains(turns, turn => turn.GetProperty("actor").GetString() == "PROFESSIONAL");
        Assert.Equal(input.MessageId, context.GetProperty("originalMessageId").GetGuid());
        var replay = await ConversationResumeContextReader.ReadAsync(
            db,
            input,
            CancellationToken.None
        );
        Assert.Equal(context.GetRawText(), replay.GetRawText());
    }

    [Theory]
    [InlineData("tenant")]
    [InlineData("relationship")]
    [InlineData("conversation")]
    [InlineData("skill")]
    [InlineData("actor")]
    [InlineData("partial")]
    [InlineData("pending")]
    [InlineData("retention")]
    [InlineData("late-completion")]
    [InlineData("future-sequence")]
    public async Task ResumeDoesNotReadForeignUnfinishedOrOutOfWindowHistory(string defect)
    {
        await using var db = Database();
        var input = Input();
        db.Messages.Add(Prior(input, 1, defect: defect));
        await db.SaveChangesAsync();
        var context = await ConversationResumeContextReader.ReadAsync(
            db,
            input,
            CancellationToken.None
        );
        Assert.Equal(0, context.GetProperty("turns").GetArrayLength());
    }

    [Fact]
    public async Task ResumeHonorsAggregateUtf16LimitWithoutSplittingOrSkippingTurns()
    {
        await using var db = Database();
        var input = Input();
        db.Messages.AddRange(
            Prior(input, 1, "Earlier"),
            Prior(input, 2, string.Concat(Enumerable.Repeat(char.ConvertFromUtf32(0x1f600), 4000)))
        );
        await db.SaveChangesAsync();
        var context = await ConversationResumeContextReader.ReadAsync(
            db,
            input,
            CancellationToken.None
        );
        Assert.Equal(1, context.GetProperty("turns").GetArrayLength());
        Assert.Equal(8000, context.GetProperty("turns")[0].GetProperty("text").GetString()!.Length);
    }

    [Fact]
    public async Task MalformedSelectedCanonicalHistoryFailsExplicitly()
    {
        await using var db = Database();
        var input = Input();
        db.Messages.Add(Prior(input, 1, "Bad\0history"));
        await db.SaveChangesAsync();
        await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
            ConversationResumeContextReader.ReadAsync(db, input, CancellationToken.None)
        );
    }
}
