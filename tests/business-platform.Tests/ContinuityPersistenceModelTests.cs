// Implements: architecture/reference/product/ae01-relationship-data-contract.md § Migration 22
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata;
using Waooaw.BusinessPlatform.Infrastructure;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ContinuityPersistenceModelTests
{
    private static EmploymentRelationshipDbContext BuildContext()
    {
        var options = new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options;
        return new EmploymentRelationshipDbContext(options);
    }

    [Fact]
    public void Migration22EntitiesMapToTenantScopedBusinessTables()
    {
        using var context = BuildContext();

        AssertEntity(context, typeof(ChannelBinding), "channel_bindings", "business");
        AssertEntity(context, typeof(ContinuityCheckpoint), "continuity_checkpoints", "business");
        AssertEntity(context, typeof(DeliveryAcknowledgement), "delivery_acknowledgements", "business");
        AssertEntity(context, typeof(ChannelMessageDeduplication), "channel_message_deduplication", "business");
    }

    [Fact]
    public void ChannelBinding_HasCompositePkAndConversationIndex()
    {
        using var context = BuildContext();
        var entity = context.Model.FindEntityType(typeof(ChannelBinding))!;

        // Alternate key (tenant_id, binding_id) mirrors composite FK target in SQL
        var ak = entity.GetKeys().FirstOrDefault(k => !k.IsPrimaryKey()
            && k.Properties.Any(p => p.Name == "TenantId")
            && k.Properties.Any(p => p.Name == "BindingId"));
        Assert.NotNull(ak);

        // (tenant_id, conversation_id) index required by data contract
        var idx = entity.GetIndexes().FirstOrDefault(i =>
            i.Properties.Count == 2
            && i.Properties.Any(p => p.Name == "TenantId")
            && i.Properties.Any(p => p.Name == "ConversationId"));
        Assert.NotNull(idx);
    }

    [Fact]
    public void ContinuityCheckpoint_HasCompositeFKsAndAllRequiredIndexes()
    {
        using var context = BuildContext();
        var entity = context.Model.FindEntityType(typeof(ContinuityCheckpoint))!;

        // Composite FK to channel_bindings for source and target
        var fks = entity.GetForeignKeys().ToList();
        var sourceBindingFk = fks.FirstOrDefault(fk =>
            fk.PrincipalEntityType.ClrType == typeof(ChannelBinding)
            && fk.Properties.Any(p => p.Name == "SourceBindingId"));
        var targetBindingFk = fks.FirstOrDefault(fk =>
            fk.PrincipalEntityType.ClrType == typeof(ChannelBinding)
            && fk.Properties.Any(p => p.Name == "TargetBindingId"));
        Assert.NotNull(sourceBindingFk);
        Assert.NotNull(targetBindingFk);

        // Unique causal marker index
        var causalIdx = entity.GetIndexes().FirstOrDefault(i =>
            i.IsUnique
            && i.Properties.Any(p => p.Name == "CausalMarker"));
        Assert.NotNull(causalIdx);

        // Status + target binding indexes
        var statusIdx = entity.GetIndexes().FirstOrDefault(i =>
            !i.IsUnique
            && i.Properties.Any(p => p.Name == "Status")
            && i.Properties.Any(p => p.Name == "RelationshipId"));
        Assert.NotNull(statusIdx);

        var targetIdx = entity.GetIndexes().FirstOrDefault(i =>
            i.Properties.Any(p => p.Name == "TargetBindingId")
            && i.Properties.Any(p => p.Name == "Status"));
        Assert.NotNull(targetIdx);
    }

    [Fact]
    public void DeliveryAcknowledgement_HasCompositeFKsAndTimelineIndexes()
    {
        using var context = BuildContext();
        var entity = context.Model.FindEntityType(typeof(DeliveryAcknowledgement))!;

        var fks = entity.GetForeignKeys().ToList();
        Assert.Contains(fks, fk => fk.PrincipalEntityType.ClrType == typeof(EmploymentRelationship));
        Assert.Contains(fks, fk => fk.PrincipalEntityType.ClrType == typeof(ContinuityCheckpoint));
        Assert.Contains(fks, fk => fk.PrincipalEntityType.ClrType == typeof(ChannelBinding));

        // (tenant_id, relationship_id, acknowledged_at) timeline index
        var timelineIdx = entity.GetIndexes().FirstOrDefault(i =>
            i.Properties.Any(p => p.Name == "AcknowledgedAt"));
        Assert.NotNull(timelineIdx);

        // (tenant_id, checkpoint_id) index
        var checkpointIdx = entity.GetIndexes().FirstOrDefault(i =>
            i.Properties.Count == 2
            && i.Properties.Any(p => p.Name == "CheckpointId"));
        Assert.NotNull(checkpointIdx);
    }

    [Fact]
    public void ChannelMessageDeduplication_HasCompositeFKsAndExpiryIndex()
    {
        using var context = BuildContext();
        var entity = context.Model.FindEntityType(typeof(ChannelMessageDeduplication))!;

        var fks = entity.GetForeignKeys().ToList();
        Assert.Contains(fks, fk => fk.PrincipalEntityType.ClrType == typeof(EmploymentRelationship));
        Assert.Contains(fks, fk => fk.PrincipalEntityType.ClrType == typeof(ChannelBinding));

        // expires_at index required for maintenance cleanup
        var expiryIdx = entity.GetIndexes().FirstOrDefault(i =>
            i.Properties.Count == 1
            && i.Properties.Any(p => p.Name == "ExpiresAt"));
        Assert.NotNull(expiryIdx);
    }

    private static void AssertEntity(
        EmploymentRelationshipDbContext context,
        Type entityType,
        string tableName,
        string schema)
    {
        var entity = context.Model.FindEntityType(entityType);

        Assert.NotNull(entity);
        Assert.Equal(tableName, entity.GetTableName());
        Assert.Equal(schema, entity.GetSchema());
        Assert.NotNull(entity.FindProperty("TenantId"));
        Assert.NotNull(entity.FindProperty("RelationshipId"));
    }
}