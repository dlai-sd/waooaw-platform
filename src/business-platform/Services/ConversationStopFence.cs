// Implements: architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md §9.4
// Constitutional basis: C-001, C-005, C-023, C-024, C-059

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed class ConversationStopFence(
    IDbContextFactory<ConversationStoreDbContext> dbFactory,
    IOptions<Wc120ConversationOptions> options
)
{
    public async Task<bool> IsLatchedAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        return await db
            .EmergencyStopLatches.AsNoTracking()
            .AnyAsync(
                value =>
                    value.Environment == options.Value.Environment
                    && value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && (value.State == "LATCHED" || value.State == "EVIDENCE_CONFIRMED"),
                cancellationToken
            );
    }

    public async Task ThrowIfLatchedAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        if (await IsLatchedAsync(tenantId, relationshipId, cancellationToken))
            throw new ConversationStoppedException();
    }
}
