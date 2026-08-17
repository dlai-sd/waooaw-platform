// Implements: work-contracts/WC-034-goal005-webportal-founder-admin.md § WC034-08
// constitutional_basis: C-005, C-023, C-026, C-059

using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class ConversationMigrationTests
{
    [Fact]
    public void MigrationDefinesDurableOrderingOutcomesPositionsCursorsAndForcedRls()
    {
        var sql = File.ReadAllText(
            RepositoryPaths.Resolve("infrastructure/postgres/init/21-conversation-core.sql"));

        Assert.Contains("business.conversations", sql);
        Assert.Contains("next_message_sequence", sql);
        Assert.Contains("next_event_sequence", sql);
        Assert.Contains("business.conversation_idempotency_outcomes", sql);
        Assert.Contains("request_hash", sql);
        Assert.Contains("response_json", sql);
        Assert.Contains("business.conversation_read_positions", sql);
        Assert.Contains("business.conversation_events", sql);
        Assert.Contains("FORCE ROW LEVEL SECURITY", sql);
        Assert.Contains("current_setting('app.current_tenant_id', TRUE)", sql);
        Assert.DoesNotContain("DROP TABLE", sql, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("TRUNCATE", sql, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("DELETE FROM", sql, StringComparison.OrdinalIgnoreCase);
    }
}
