// Implements: work-contracts/WC-134-runtime-generation-and-reconciliation-policy.md §Bounded canonical resume
// constitutional_basis: C-023, C-026, C-059, C-063

using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public static class ConversationResumeContextReader
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    public static async Task<JsonElement> ReadAsync(
        ConversationStoreDbContext db,
        ConversationMessage input,
        CancellationToken ct
    )
    {
        var cutoff = input.AcceptedAt.AddDays(-7);
        var prior = await db
            .Messages.AsNoTracking()
            .Where(row =>
                row.TenantId == input.TenantId
                && row.RelationshipId == input.RelationshipId
                && row.ConversationId == input.ConversationId
                && row.SkillId == input.SkillId
                && row.Sequence < input.Sequence
                && row.AcceptedAt >= cutoff
                && row.CompletedAt != null
                && row.CompletedAt <= input.AcceptedAt
                && row.ProcessingState == "COMPLETED"
                && !row.Partial
                && (row.Actor == "CUSTOMER" || row.Actor == "PROFESSIONAL")
            )
            .OrderByDescending(row => row.Sequence)
            .Take(12)
            .ToListAsync(ct);
        var turns = new List<ResumeTurn>();
        var remaining = 8000;
        foreach (var message in prior)
        {
            var blocks =
                JsonSerializer.Deserialize<List<ConversationTextBlockV1>>(message.ContentJson, Json)
                ?? throw new ConversationStateConflictException();
            var language = blocks.Count == 1 ? blocks[0].Language : null;
            if (
                blocks.Count != 1
                || string.IsNullOrWhiteSpace(blocks[0].Text)
                || blocks[0].Text.Contains('\0')
                || language is null
                || language.Length is < 2 or > 35
            )
                throw new ConversationStateConflictException();
            if (blocks[0].Text.Length > remaining)
                break;
            turns.Add(
                new(message.MessageId, message.Sequence, message.Actor, blocks[0].Text, language)
            );
            remaining -= blocks[0].Text.Length;
        }
        turns.Reverse();
        var context = JsonSerializer.SerializeToElement(
            new
            {
                schemaVersion = "1.0",
                tenantId = input.TenantId,
                relationshipId = input.RelationshipId,
                conversationId = input.ConversationId,
                originalMessageId = input.MessageId,
                skillId = input.SkillId,
                beforeSequence = input.Sequence,
                turns,
            },
            Json
        );
        var fields =
            JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(context.GetRawText(), Json)
            ?? throw new ConversationStateConflictException();
        fields["digest"] = JsonSerializer.SerializeToElement(
            AgentAdmissionCanonicalizer.Digest(context)
        );
        return JsonSerializer.SerializeToElement(fields, Json);
    }

    private sealed record ResumeTurn(
        Guid MessageId,
        long Sequence,
        string Actor,
        string Text,
        string Language
    );
}
