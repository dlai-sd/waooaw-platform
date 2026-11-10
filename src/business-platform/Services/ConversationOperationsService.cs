// Implements: work-contracts/WC-120-requirements.yaml WC120-R017 and WC120-R041
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record ConversationOperationalAlert(
    string Code,
    string Severity,
    DateTimeOffset TriggeredAt,
    TimeSpan ResponseDeadline
);

public sealed record ConversationOperationalSnapshot(
    string Environment,
    int OpenSignalCount,
    int BlockedOutboxCount,
    int UnresolvedOutboxCount,
    TimeSpan? OldestQueuedAge,
    TimeSpan? OldestUnknownAge,
    TimeSpan? OldestDeadLetterAge,
    IReadOnlyList<ConversationOperationalAlert> Alerts
);

public sealed class ConversationOperationsService(
    IDbContextFactory<ConversationStoreDbContext> dbFactory,
    IOptions<Wc120ConversationOptions> options
)
{
    public async Task<ConversationOperationalSnapshot> EvaluateAsync(
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var environment = options.Value.Environment;
        var queue = db
            .ConversationOutbox.AsNoTracking()
            .Where(value => value.Environment == environment);
        var oldestQueuedAt = await queue
            .Where(value => value.State == "PENDING" || value.State == "LEASED")
            .MinAsync(value => (DateTimeOffset?)value.CreatedAt, cancellationToken);
        var oldestUnknownAt = await queue
            .Where(value => value.State == "UNRESOLVED")
            .MinAsync(value => (DateTimeOffset?)value.UpdatedAt, cancellationToken);
        var oldestBlockedAt = await queue
            .Where(value => value.State == "BLOCKED")
            .MinAsync(value => (DateTimeOffset?)value.UpdatedAt, cancellationToken);
        var blockedCount = await queue.CountAsync(
            value => value.State == "BLOCKED",
            cancellationToken
        );
        var unresolvedCount = await queue.CountAsync(
            value => value.State == "UNRESOLVED",
            cancellationToken
        );
        var openSignals = await db
            .OperationalSignals.AsNoTracking()
            .CountAsync(
                value => value.Environment == environment && value.State == "OPEN",
                cancellationToken
            );
        var oldestQueuedAge = Age(now, oldestQueuedAt);
        var oldestUnknownAge = Age(now, oldestUnknownAt);
        var oldestDeadLetterAge = Age(now, oldestBlockedAt);
        var alerts = new List<ConversationOperationalAlert>();
        if (oldestQueuedAge > TimeSpan.FromSeconds(120) && oldestQueuedAt is { } queuedAt)
        {
            alerts.Add(
                new(
                    "OUTBOUND_QUEUE_AGE_BREACH",
                    "PAGE",
                    queuedAt.AddSeconds(120),
                    TimeSpan.FromMinutes(5)
                )
            );
        }
        if (oldestUnknownAge > TimeSpan.FromMinutes(15) && oldestUnknownAt is { } unknownAt)
        {
            alerts.Add(
                new(
                    "OUTBOUND_RECONCILIATION_BREACH",
                    "PAGE",
                    unknownAt.AddMinutes(15),
                    TimeSpan.FromMinutes(5)
                )
            );
        }
        if (oldestDeadLetterAge > TimeSpan.FromMinutes(30) && oldestBlockedAt is { } pagedAt)
        {
            alerts.Add(
                new(
                    "DEAD_LETTER_AGE_BREACH",
                    "PAGE",
                    pagedAt.AddMinutes(30),
                    TimeSpan.FromMinutes(5)
                )
            );
        }
        else if (
            oldestDeadLetterAge > TimeSpan.FromMinutes(15)
            && oldestBlockedAt is { } notifiedAt
        )
        {
            alerts.Add(
                new(
                    "DEAD_LETTER_ACTION_REQUIRED",
                    "NOTIFY",
                    notifiedAt.AddMinutes(15),
                    TimeSpan.FromMinutes(5)
                )
            );
        }
        var oldestCriticalAt = await db
            .OperationalSignals.AsNoTracking()
            .Where(value =>
                value.Environment == environment
                && value.State == "OPEN"
                && (
                    value.Code.Contains("PRIVACY")
                    || value.Code.Contains("ISOLATION")
                    || value.Code.Contains("PRODUCTION_DARK")
                    || value.Code.Contains("RESTORE_EGRESS")
                    || value.Code.Contains("STOP_HARD_CEILING")
                )
            )
            .MinAsync(value => (DateTimeOffset?)value.OccurredAt, cancellationToken);
        if (oldestCriticalAt is { } criticalAt)
        {
            alerts.Add(
                new("IMMEDIATE_FENCE_REQUIRED", "PAGE", criticalAt, TimeSpan.FromMinutes(5))
            );
        }
        var oldestStopReconciliationAt = await db
            .OperationalSignals.AsNoTracking()
            .Where(value =>
                value.Environment == environment
                && value.State == "OPEN"
                && value.Category == "EMERGENCY_STOP"
                && value.Code == "EVIDENCE_RECONCILIATION_PENDING"
            )
            .MinAsync(value => (DateTimeOffset?)value.OccurredAt, cancellationToken);
        if (oldestStopReconciliationAt is { } stopReconciliationAt)
        {
            alerts.Add(
                new(
                    "STOP_EVIDENCE_RECONCILIATION_REQUIRED",
                    "PAGE",
                    stopReconciliationAt,
                    TimeSpan.FromMinutes(5)
                )
            );
        }
        return new(
            environment,
            openSignals,
            blockedCount,
            unresolvedCount,
            oldestQueuedAge,
            oldestUnknownAge,
            oldestDeadLetterAge,
            alerts
        );
    }

    private static TimeSpan? Age(DateTimeOffset now, DateTimeOffset? occurredAt) =>
        occurredAt.HasValue ? now - occurredAt.Value : null;
}

public sealed class WhatsAppOperationsHostedService(
    IServiceScopeFactory scopes,
    WhatsAppTenantExecutionScope tenantExecution,
    IWhatsAppCapabilityGate capability,
    TimeProvider clock,
    ILogger<WhatsAppOperationsHostedService> logger
) : BackgroundService
{
    private WhatsAppCapabilityState? _lastInactiveState;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        await EvaluateOnceAsync(stoppingToken);
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(30), clock);
        while (await timer.WaitForNextTickAsync(stoppingToken))
            await EvaluateOnceAsync(stoppingToken);
    }

    internal async Task EvaluateOnceAsync(CancellationToken cancellationToken)
    {
        var now = clock.GetUtcNow();
        var capabilityState = capability.Evaluate(now);
        if (capabilityState.State != "ACTIVE")
        {
            if (capabilityState != _lastInactiveState)
            {
                logger.LogWarning(
                    "WhatsApp operations evaluation inactive: State={State} ReasonCode={ReasonCode}",
                    capabilityState.State,
                    capabilityState.ReasonCode
                );
                _lastInactiveState = capabilityState;
            }
            return;
        }
        _lastInactiveState = null;
        try
        {
            var authority = capability.RequireActive(now);
            using var tenant = tenantExecution.Begin();
            if (tenantExecution.CurrentTenantId != authority.TenantId)
                throw new WhatsAppCapabilityUnavailableException("OPERATIONS_AUTHORITY_CHANGED");
            await using var scope = scopes.CreateAsyncScope();
            var snapshot = await scope
                .ServiceProvider.GetRequiredService<ConversationOperationsService>()
                .EvaluateAsync(now, cancellationToken);
            var observedAt = clock.GetUtcNow();
            if (
                capability.RequireActive(observedAt) != authority
                || snapshot.Environment != authority.Environment
            )
                throw new WhatsAppCapabilityUnavailableException("OPERATIONS_AUTHORITY_CHANGED");
            logger.LogInformation(
                "WhatsApp operations evaluation heartbeat: Environment={Environment} OpenSignalCount={OpenSignalCount} BlockedOutboxCount={BlockedOutboxCount} UnresolvedOutboxCount={UnresolvedOutboxCount} AlertCount={AlertCount} WC134_OBSERVATION={ObservationJson}",
                snapshot.Environment,
                snapshot.OpenSignalCount,
                snapshot.BlockedOutboxCount,
                snapshot.UnresolvedOutboxCount,
                snapshot.Alerts.Count,
                Observation(authority, observedAt, "HEARTBEAT", null)
            );
            foreach (var alert in snapshot.Alerts)
            {
                logger.LogWarning(
                    "WhatsApp operations alert: Environment={Environment} Code={Code} Severity={Severity} TriggeredAt={TriggeredAt} ResponseDeadlineSeconds={ResponseDeadlineSeconds} WC134_OBSERVATION={ObservationJson}",
                    snapshot.Environment,
                    alert.Code,
                    alert.Severity,
                    alert.TriggeredAt,
                    alert.ResponseDeadline.TotalSeconds,
                    Observation(authority, observedAt, "ALERT", alert.Code)
                );
            }
        }
        catch (WhatsAppCapabilityUnavailableException failure)
        {
            logger.LogWarning(
                "WhatsApp operations evaluation fenced: ReasonCode={ReasonCode}",
                failure.ReasonCode
            );
        }
        catch (DbUpdateException)
        {
            logger.LogError("WhatsApp operations evaluation failed; heartbeat unavailable.");
        }
        catch (Npgsql.NpgsqlException)
        {
            logger.LogError("WhatsApp operations database unavailable; heartbeat unavailable.");
        }
    }

    private static string Observation(
        WhatsAppActivationAuthority authority,
        DateTimeOffset observedAt,
        string kind,
        string? code
    ) =>
        JsonSerializer.Serialize(
            new
            {
                schemaVersion = "1.0",
                environment = authority.Environment,
                activationDigest = WhatsAppGuestTrafficEventIdentity.Activation(
                    authority.ActivationReference
                ),
                releaseDigest = authority.ReleaseDigest,
                configurationDigest = authority.ConfigurationDigest,
                observedAt,
                kind,
                code,
            }
        );
}
