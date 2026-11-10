// Implements: WC-134 R006/R008; verified-work capability tenant scope for Web and WhatsApp.
// constitutional_basis: C-023, C-026, C-059
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record ConversationRuntimeWork
{
    internal ConversationRuntimeWork(Guid tenantId, Guid executionId) =>
        (TenantId, ExecutionId) = (tenantId, executionId);

    public Guid TenantId { get; }
    public Guid ExecutionId { get; }
}

public sealed class ConversationRuntimeWorkScope
{
    private readonly AsyncLocal<ConversationRuntimeWork?> _current = new();
    public ConversationRuntimeWork? Current => _current.Value;

    internal IDisposable Begin(ConversationRuntimeWork work)
    {
        if (
            _current.Value is not null
            || work.TenantId == Guid.Empty
            || work.ExecutionId == Guid.Empty
        )
            throw new InvalidOperationException(
                "Runtime work scopes require a non-nested owner capability."
            );
        _current.Value = work;
        return new Scope(this);
    }

    private sealed class Scope(ConversationRuntimeWorkScope owner) : IDisposable
    {
        public void Dispose() => owner._current.Value = null;
    }
}

public sealed class ConversationRuntimeWorkDirectory(
    IDbContextFactory<ConversationStoreDbContext> conversations,
    IOptions<Wc120ConversationOptions> options,
    ILogger<ConversationRuntimeWorkDirectory> logger
)
{
    public async Task<ConversationRuntimeWork?> ClaimAsync(CancellationToken cancellationToken)
    {
        if (!options.Value.Enabled || !options.Value.RuntimeEventIngestionEnabled)
            return null;
        await using var db = await conversations.CreateDbContextAsync(cancellationToken);
        var candidates = await db
            .Database.SqlQuery<WorkRow>(
                $"""
                SELECT execution_id AS "ExecutionId", tenant_id AS "TenantId", authorized AS "Authorized"
                FROM business.claim_conversation_runtime_work({options.Value.Environment})
                """
            )
            .ToListAsync(cancellationToken);
        if (candidates.Count == 0)
            return null;
        if (
            candidates.Count != 1
            || candidates[0].TenantId == Guid.Empty
            || candidates[0].ExecutionId == Guid.Empty
        )
            throw new ConversationStateConflictException();
        var candidate = candidates[0];
        if (!candidate.Authorized)
        {
            logger.LogWarning("Runtime work deferred: CURRENT_IDENTITY_AUTHORITY_DENIED.");
            return null;
        }
        return new(candidate.TenantId, candidate.ExecutionId);
    }

    private sealed class WorkRow
    {
        public Guid TenantId { get; init; }
        public Guid ExecutionId { get; init; }
        public bool Authorized { get; init; }
    }
}
