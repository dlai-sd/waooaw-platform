// Implements: WC-134 R006/R007; tenant-scoped recoverable runtime consumption.
// constitutional_basis: C-001, C-005, C-023, C-059, C-063
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed class ConversationRuntimeEventWorker(
    IDbContextFactory<ConversationStoreDbContext> conversations,
    ConversationRuntimeEventIngestion ingestion,
    IConversationExecutionEventSource source,
    WhatsAppTenantExecutionScope tenantScope,
    IOptions<Wc120ConversationOptions> options,
    TimeProvider clock,
    ILogger<ConversationRuntimeEventWorker> logger,
    ConversationRuntimeWorkScope? runtimeScope = null
)
{
    public async Task<bool> ProcessOneAsync(CancellationToken cancellationToken)
    {
        if (!options.Value.Enabled || !options.Value.RuntimeEventIngestionEnabled)
            return false;
        var work = runtimeScope?.Current;
        var tenantId =
            work?.TenantId
            ?? tenantScope.CurrentTenantId
            ?? throw new InvalidOperationException(
                "Runtime recovery requires current tenant authority."
            );
        RequireAuthority();
        await using var db = await conversations.CreateDbContextAsync(cancellationToken);
        var now = clock.GetUtcNow();
        var execution = await (
            from row in StartedCandidates(db)
            join input in db.Messages on row.MessageId equals input.MessageId
            where
                row.TenantId == tenantId
                && input.TenantId == tenantId
                && input.Environment == options.Value.Environment
                && !row.RuntimeTerminal
                && (work == null || row.ExecutionId == work.ExecutionId)
                && row.ProcessingState != "STOPPED"
                && row.ProcessingState != "CANCELLED"
                && (row.RuntimeNextAttemptAt == null || row.RuntimeNextAttemptAt <= now)
            orderby row.RuntimeNextAttemptAt, row.CreatedAt, row.ExecutionId
            select row
        ).FirstOrDefaultAsync(cancellationToken);
        if (execution is null)
            return false;
        execution.RuntimeNextAttemptAt = now.AddSeconds(45);
        await db.SaveChangesAsync(cancellationToken);
        try
        {
            var origin = await ingestion.GetSourceAsync(
                tenantId,
                execution.ExecutionId,
                cancellationToken
            );
            await foreach (
                var value in source.ReadEventsAsync(
                    origin.ConversationId,
                    origin.MessageId,
                    origin.Caller,
                    origin.IdempotencyKey,
                    origin.AfterSequence,
                    cancellationToken
                )
            )
            {
                RequireAuthority();
                await ingestion.ApplyAsync(origin, value, cancellationToken);
            }
        }
        catch (ConversationStoppedException)
        {
            await SignalAsync(db, tenantId, "RUNTIME_STOP_FENCED", cancellationToken);
        }
        catch (ConversationCursorExpiredException)
        {
            await SignalAsync(
                db,
                tenantId,
                "RUNTIME_CURSOR_RECONCILIATION_REQUIRED",
                cancellationToken
            );
        }
        catch (ConversationNotAccessibleException)
        {
            await SignalAsync(
                db,
                tenantId,
                "RUNTIME_AUTHORITY_RECONCILIATION_REQUIRED",
                cancellationToken
            );
        }
        catch (Exception failure)
            when (failure
                    is ConversationExecutionUnavailableException
                        or ConversationStateConflictException
                        or ConversationIdempotencyConflictException
                        or System.Text.Json.JsonException
            )
        {
            logger.LogWarning(
                "Runtime ingestion deferred. FailureType={FailureType}",
                failure.GetType().Name
            );
            await SignalAsync(
                db,
                tenantId,
                "RUNTIME_EVENT_RECONCILIATION_REQUIRED",
                cancellationToken
            );
        }
        return true;

        void RequireAuthority()
        {
            if (work is null)
                tenantScope.RequireUnchangedAuthority();
            else if (runtimeScope?.Current != work)
                throw new ConversationNotAccessibleException();
        }
    }

    internal static IQueryable<ConversationExecution> StartedCandidates(
        ConversationStoreDbContext db
    ) =>
        db.Executions.Where(row =>
            !db.PendingStarts.Any(pending =>
                pending.TenantId == row.TenantId && pending.ExecutionId == row.ExecutionId
            )
        );

    private async Task SignalAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        string code,
        CancellationToken cancellationToken
    )
    {
        logger.LogWarning("Runtime recovery requires attention. Code={Code}", code);
        if (
            await db.OperationalSignals.AnyAsync(
                signal =>
                    signal.Environment == options.Value.Environment
                    && signal.Category == "RUNTIME"
                    && signal.Code == code
                    && signal.State == "OPEN",
                cancellationToken
            )
        )
            return;
        db.OperationalSignals.Add(
            new()
            {
                Environment = options.Value.Environment,
                Category = "RUNTIME",
                Code = code,
                OccurredAt = clock.GetUtcNow(),
            }
        );
        await db.SaveChangesAsync(cancellationToken);
    }
}

public sealed class ConversationRuntimeEventHostedService(
    IServiceScopeFactory scopes,
    ConversationRuntimeWorkScope tenantScope,
    TimeProvider clock,
    ILogger<ConversationRuntimeEventHostedService> logger
) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(1), clock);
        while (await timer.WaitForNextTickAsync(stoppingToken))
        {
            try
            {
                await using var scope = scopes.CreateAsyncScope();
                var work = await scope
                    .ServiceProvider.GetRequiredService<ConversationRuntimeWorkDirectory>()
                    .ClaimAsync(stoppingToken);
                if (work is null)
                    continue;
                using var tenant = tenantScope.Begin(work);
                await scope
                    .ServiceProvider.GetRequiredService<ConversationRuntimeEventWorker>()
                    .ProcessOneAsync(stoppingToken);
            }
            catch (WhatsAppCapabilityUnavailableException failure)
            {
                logger.LogWarning(
                    "Runtime worker authority fenced: {ReasonCode}",
                    failure.ReasonCode
                );
            }
            catch (Exception failure)
                when (failure
                        is ConversationStateConflictException
                            or ConversationNotAccessibleException
                            or ConversationExecutionUnavailableException
                )
            {
                logger.LogWarning(
                    "Runtime work recovery deferred. FailureType={FailureType}",
                    failure.GetType().Name
                );
            }
            catch (Exception failure) when (failure is DbUpdateException or Npgsql.NpgsqlException)
            {
                logger.LogError(
                    "Runtime worker database unavailable; committed cursor retained. FailureType={FailureType}",
                    failure.GetType().Name
                );
            }
        }
    }
}
