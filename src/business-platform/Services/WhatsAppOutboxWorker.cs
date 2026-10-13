// Implements: WC120-R010, WC120-R013, WC120-R017
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using System.Security.Cryptography;
using System.Text;

namespace Waooaw.BusinessPlatform.Services;

public sealed record WhatsAppProviderDispatchRequest(
    Guid OutboxId,
    string Environment,
    Guid TenantId,
    Guid RelationshipId,
    Guid ConversationId,
    long Sequence,
    string PayloadReference,
    string PayloadDigest,
    int AttemptNumber
);

public interface IWhatsAppProviderAdapter
{
    Task<WhatsAppDispatchObservation> DispatchAsync(
        WhatsAppProviderDispatchRequest request,
        CancellationToken cancellationToken
    );

    Task<WhatsAppDispatchObservation> ReconcileAsync(
        WhatsAppProviderDispatchRequest request,
        CancellationToken cancellationToken
    );
}

public sealed class DisabledWhatsAppProviderAdapter : IWhatsAppProviderAdapter
{
    public Task<WhatsAppDispatchObservation> DispatchAsync(
        WhatsAppProviderDispatchRequest request,
        CancellationToken cancellationToken
    ) => throw new ConversationExecutionUnavailableException();

    public Task<WhatsAppDispatchObservation> ReconcileAsync(
        WhatsAppProviderDispatchRequest request,
        CancellationToken cancellationToken
    ) => throw new ConversationExecutionUnavailableException();
}

public sealed class WhatsAppOutboxWorker(
    WhatsAppOutboxService outbox,
    IWhatsAppProviderAdapter provider,
    TimeProvider timeProvider
)
{
    private static readonly TimeSpan HeartbeatInterval = TimeSpan.FromSeconds(20);

    public async Task<bool> ProcessOneAsync(string workerId, CancellationToken cancellationToken)
    {
        var lease = await outbox.LeaseNextAsync(
            workerId,
            timeProvider.GetUtcNow(),
            cancellationToken
        );
        if (lease is null)
            return false;

        var request = new WhatsAppProviderDispatchRequest(
            lease.OutboxId,
            lease.Environment,
            lease.TenantId,
            lease.RelationshipId,
            lease.ConversationId,
            lease.Sequence,
            lease.PayloadReference,
            lease.PayloadDigest,
            lease.AttemptNumber
        );
        WhatsAppDispatchObservation observation;
        try
        {
            if (lease.ReconciliationRequired)
            {
                observation = await ExecuteWithHeartbeatAsync(
                    lease.OutboxId,
                    workerId,
                    token => provider.ReconcileAsync(request, token),
                    cancellationToken
                );
            }
            else
            {
                if (
                    !await outbox.BeginDispatchAsync(
                        lease.OutboxId,
                        workerId,
                        timeProvider.GetUtcNow(),
                        cancellationToken
                    )
                )
                    return true;
                observation = await ExecuteWithHeartbeatAsync(
                    lease.OutboxId,
                    workerId,
                    token => provider.DispatchAsync(request, token),
                    cancellationToken
                );
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch
        {
            var observedAt = timeProvider.GetUtcNow();
            observation = new WhatsAppDispatchObservation(
                "UNKNOWN",
                Sha256($"unknown-provider-reference:{lease.OutboxId:D}"),
                Sha256($"unknown-dispatch:{lease.OutboxId:D}:{lease.AttemptNumber}:{observedAt:O}"),
                observedAt
            );
        }
        await outbox.RecordResultAsync(lease.OutboxId, workerId, observation, cancellationToken);
        return true;
    }

    private async Task<WhatsAppDispatchObservation> ExecuteWithHeartbeatAsync(
        Guid outboxId,
        string workerId,
        Func<CancellationToken, Task<WhatsAppDispatchObservation>> operation,
        CancellationToken cancellationToken
    )
    {
        var operationTask = operation(cancellationToken);
        using var timer = new PeriodicTimer(HeartbeatInterval, timeProvider);
        while (!operationTask.IsCompleted)
        {
            var heartbeatTask = timer.WaitForNextTickAsync(cancellationToken).AsTask();
            var completed = await Task.WhenAny(operationTask, heartbeatTask);
            if (completed == operationTask)
                break;
            if (!await heartbeatTask)
                break;
            await outbox.HeartbeatAsync(
                outboxId,
                workerId,
                timeProvider.GetUtcNow(),
                cancellationToken
            );
        }
        return await operationTask;
    }

    private static string Sha256(string value) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
}
