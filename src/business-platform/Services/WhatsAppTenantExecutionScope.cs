// Implements: work-contracts/WC-121-demo-whatsapp-provider-enablement-work-component.md S07, S11-S13
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

namespace Waooaw.BusinessPlatform.Services;

public sealed class WhatsAppTenantExecutionScope(
    IWhatsAppCapabilityGate capability,
    TimeProvider clock
)
{
    private readonly AsyncLocal<Guid?> _current = new();
    public Guid? CurrentTenantId => _current.Value;

    public IDisposable Begin()
    {
        if (_current.Value is not null)
            throw new InvalidOperationException("WhatsApp tenant execution scopes cannot nest.");
        _current.Value = capability.RequireActive(clock.GetUtcNow()).TenantId;
        return new Scope(this);
    }

    private sealed class Scope(WhatsAppTenantExecutionScope owner) : IDisposable
    {
        public void Dispose() => owner._current.Value = null;
    }
}

public sealed class WhatsAppOutboxHostedService(
    IServiceScopeFactory scopes,
    WhatsAppTenantExecutionScope tenantExecution,
    IWhatsAppCapabilityGate capability,
    TimeProvider clock,
    ILogger<WhatsAppOutboxHostedService> logger
) : BackgroundService
{
    private readonly string _workerId = $"whatsapp-{Guid.NewGuid():N}";

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(1), clock);
        while (await timer.WaitForNextTickAsync(stoppingToken))
        {
            if (capability.Evaluate(clock.GetUtcNow()).State != "ACTIVE")
                continue;
            try
            {
                using var tenant = tenantExecution.Begin();
                await using var scope = scopes.CreateAsyncScope();
                await scope
                    .ServiceProvider.GetRequiredService<WhatsAppOutboxWorker>()
                    .ProcessOneAsync(_workerId, stoppingToken);
            }
            catch (WhatsAppCapabilityUnavailableException failure)
            {
                logger.LogWarning("WhatsApp worker fenced: {ReasonCode}", failure.ReasonCode);
            }
            catch (Microsoft.EntityFrameworkCore.DbUpdateException)
            {
                logger.LogError(
                    "WhatsApp worker database operation failed; work remains recoverable."
                );
            }
            catch (Npgsql.NpgsqlException)
            {
                logger.LogError(
                    "WhatsApp worker database dependency unavailable; work remains recoverable."
                );
            }
        }
    }
}
