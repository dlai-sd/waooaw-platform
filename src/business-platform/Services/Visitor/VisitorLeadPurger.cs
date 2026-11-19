// Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R008
// Constitutional basis: C-023, C-026, C-048, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services.Visitor;

public sealed record VisitorPurgeResult(bool Ran, int Leads, int Sessions, int HandoffReferences);

/// <summary>
/// Deletes expired visitor data for one tenant. Retention is read from options at run time so a change applies
/// at once. Converted leads are excluded; they follow the customer record. Logs counts only.
/// </summary>
public sealed class VisitorLeadPurger(
    IDbContextFactory<ConversationStoreDbContext> factory,
    IOptionsMonitor<VisitorLeadOptions> options,
    TimeProvider clock,
    ILogger<VisitorLeadPurger> logger
)
{
    public async Task<VisitorPurgeResult> PurgeAsync(Guid tenantId, CancellationToken ct)
    {
        var current = options.CurrentValue;
        var now = clock.GetUtcNow();
        var cutoff = now.AddDays(-current.RetentionDaysFor(tenantId));
        var simulationCutoff = now.AddDays(-current.SimulationRetentionDays);

        await using var db = await factory.CreateDbContextAsync(ct);
        await using var transaction = db.Database.IsRelational()
            ? await db.Database.BeginTransactionAsync(ct)
            : null;
        if (db.Database.IsNpgsql())
        {
            // One purger at a time across replicas; a second runner skips instead of waiting.
            var key = $"visitor-purge:{tenantId:D}";
            var locked = await db
                .Database.SqlQuery<bool>(
                    $"SELECT pg_try_advisory_xact_lock(hashtextextended({key}, 0)) AS \"Value\""
                )
                .SingleAsync(ct);
            if (!locked)
                return new VisitorPurgeResult(false, 0, 0, 0);
        }

        var leads = 0;
        var sessions = 0;
        for (var batch = 0; batch < 20; batch++)
        {
            var leadIds = await db
                .VisitorLeads.Where(value =>
                    value.TenantId == tenantId
                    && value.Status != VisitorLeadStatus.Converted
                    && (
                        value.SourceChannel == VisitorChannels.Simulation
                            ? value.UpdatedAt < simulationCutoff
                            : value.UpdatedAt < cutoff
                    )
                )
                .OrderBy(value => value.UpdatedAt)
                .Select(value => value.LeadId)
                .Take(current.PurgeBatchSize)
                .ToListAsync(ct);
            if (leadIds.Count == 0)
                break;
            await db
                .VisitorHandoffReferences.Where(value => leadIds.Contains(value.LeadId))
                .ExecuteDeleteAsync(ct);
            leads += await db
                .VisitorLeads.Where(value => leadIds.Contains(value.LeadId))
                .ExecuteDeleteAsync(ct);
        }
        for (var batch = 0; batch < 20; batch++)
        {
            var sessionIds = await db
                .VisitorSessions.Where(value =>
                    value.TenantId == tenantId
                    && (
                        value.Channel == VisitorChannels.Simulation
                            ? value.UpdatedAt < simulationCutoff
                            : value.UpdatedAt < cutoff
                    )
                )
                .OrderBy(value => value.UpdatedAt)
                .Select(value => value.SessionId)
                .Take(current.PurgeBatchSize)
                .ToListAsync(ct);
            if (sessionIds.Count == 0)
                break;
            await db
                .VisitorTurns.Where(value => sessionIds.Contains(value.SessionId))
                .ExecuteDeleteAsync(ct);
            sessions += await db
                .VisitorSessions.Where(value => sessionIds.Contains(value.SessionId))
                .ExecuteDeleteAsync(ct);
        }
        var references = await db
            .VisitorHandoffReferences.Where(value =>
                value.TenantId == tenantId && value.ExpiresAt < now
            )
            .ExecuteDeleteAsync(ct);
        // Render hints only matter until the message is sent, well inside the WhatsApp service window.
        await db
            .VisitorRenderHints.Where(value =>
                value.TenantId == tenantId && value.CreatedAt < now.AddDays(-2)
            )
            .ExecuteDeleteAsync(ct);
        if (transaction is not null)
            await transaction.CommitAsync(ct);
        logger.LogInformation(
            "visitor.purge.completed leads={Leads} sessions={Sessions} references={References}",
            leads,
            sessions,
            references
        );
        return new VisitorPurgeResult(true, leads, sessions, references);
    }
}

public sealed class VisitorLeadPurgeHostedService(
    IServiceScopeFactory scopes,
    IOptionsMonitor<VisitorLeadOptions> options,
    IOptionsMonitor<VisitorConversationOptions> conversation,
    ILogger<VisitorLeadPurgeHostedService> logger,
    WhatsAppTenantExecutionScope? tenantExecution = null
) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await Task.Delay(
                    TimeSpan.FromMinutes(options.CurrentValue.PurgeIntervalMinutes),
                    stoppingToken
                );
                await RunOnceAsync(stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
            catch (Exception exception)
            {
                logger.LogWarning(
                    "visitor.purge.failed errorType={ErrorType}",
                    exception.GetType().Name
                );
            }
        }
    }

    internal async Task RunOnceAsync(CancellationToken ct)
    {
        IDisposable? scope = null;
        Guid? tenant = conversation.CurrentValue.DefaultTenantId;
        try
        {
            scope = tenantExecution?.Begin();
            tenant = tenantExecution?.ServiceTenantId ?? tenant;
        }
        catch (WhatsAppCapabilityUnavailableException)
        {
            scope = null;
        }
        using (scope)
        {
            if (tenant is not { } tenantId)
                return;
            await using var serviceScope = scopes.CreateAsyncScope();
            await serviceScope
                .ServiceProvider.GetRequiredService<VisitorLeadPurger>()
                .PurgeAsync(tenantId, ct);
        }
    }
}
