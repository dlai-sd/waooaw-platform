// Implements: work-contracts/WC-121-demo-whatsapp-provider-enablement-work-component.md S07, S11-S13
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed class WhatsAppTenantExecutionScope(
    IWhatsAppCapabilityGate capability,
    TimeProvider clock
)
{
    private readonly AsyncLocal<WhatsAppActivationAuthority?> _current = new();
    private readonly AsyncLocal<Guid?> _databaseTenantOverride = new();
    private readonly AsyncLocal<WhatsAppRelationshipRoute?> _relationshipCandidate = new();
    private readonly AsyncLocal<WhatsAppCurrentRelationshipRoute?> _relationshipRoute = new();
    public Guid? CurrentTenantId
    {
        get
        {
            if (_relationshipCandidate.Value is { } candidate)
            {
                RequireUnchangedAuthority();
                return candidate.TenantId;
            }
            return _current.Value?.TenantId;
        }
    }
    public Guid? ServiceTenantId => _current.Value?.TenantId;
    public Guid? DatabaseTenantOverrideId => _databaseTenantOverride.Value;

    internal WhatsAppCurrentRelationshipRoute RequireConfirmedRelationshipRoute()
    {
        var route =
            _relationshipRoute.Value
            ?? throw new WhatsAppCapabilityUnavailableException("RELATIONSHIP_ROUTE_DENIED");
        RequireRelationshipRoute(route);
        return route;
    }

    public IDisposable Begin()
    {
        if (_current.Value is not null)
            throw new InvalidOperationException("WhatsApp tenant execution scopes cannot nest.");
        _current.Value = capability.RequireActive(clock.GetUtcNow());
        return new Scope(this);
    }

    public void RequireUnchangedAuthority()
    {
        var authority =
            _current.Value
            ?? throw new InvalidOperationException("WhatsApp tenant execution scope is required.");
        if (capability.RequireActive(clock.GetUtcNow()) != authority)
            throw new WhatsAppCapabilityUnavailableException("EXECUTION_AUTHORITY_CHANGED");
    }

    public IDisposable BeginDatabaseTenantOverride(Guid tenantId)
    {
        if (_current.Value?.TenantId != tenantId || _databaseTenantOverride.Value is not null)
            throw new InvalidOperationException(
                "Database tenant override must match the active WhatsApp authority and cannot nest."
            );
        _databaseTenantOverride.Value = tenantId;
        return new DatabaseTenantOverrideScope(this);
    }

    internal IDisposable BeginRelationshipValidation(WhatsAppRelationshipRoute candidate)
    {
        RequireUnchangedAuthority();
        if (_relationshipCandidate.Value is not null || _databaseTenantOverride.Value is not null)
            throw new InvalidOperationException(
                "WhatsApp relationship routing scopes cannot nest."
            );
        var authority = _current.Value!;
        if (
            candidate.ServiceTenantId != authority.TenantId
            || candidate.TenantId == Guid.Empty
            || candidate.BindingId == Guid.Empty
            || candidate.ActorId == Guid.Empty
            || candidate.ServiceTenantId == Guid.Empty
        )
            throw new WhatsAppCapabilityUnavailableException("RELATIONSHIP_ROUTE_DENIED");
        capability.RequireRecipient(authority.TenantId, candidate.SenderHash, clock.GetUtcNow());
        _relationshipCandidate.Value = candidate;
        return new RelationshipScope(this);
    }

    internal void ConfirmRelationshipRoute(WhatsAppCurrentRelationshipRoute route)
    {
        RequireUnchangedAuthority();
        var candidate = _relationshipCandidate.Value;
        if (
            candidate is null
            || _relationshipRoute.Value is not null
            || candidate.ServiceTenantId != route.ServiceTenantId
            || candidate.TenantId != route.TenantId
            || candidate.BindingId != route.BindingId
            || candidate.ActorId != route.ParticipantId
            || candidate.SenderHash != route.SenderHash
            || route.RelationshipId == Guid.Empty
            || route.ConversationId == Guid.Empty
            || route.RelationshipVersion < 0
            || route.Environment != _current.Value!.Environment
        )
            throw new WhatsAppCapabilityUnavailableException("RELATIONSHIP_ROUTE_DENIED");
        _relationshipRoute.Value = route;
    }

    internal void RequireRelationshipRecipient(
        Guid tenantId,
        Guid relationshipId,
        Guid bindingId,
        string senderHash
    )
    {
        RequireUnchangedAuthority();
        var route = _relationshipRoute.Value;
        if (
            route is null
            || route.TenantId != tenantId
            || route.RelationshipId != relationshipId
            || route.BindingId != bindingId
            || route.SenderHash != senderHash
        )
            throw new WhatsAppCapabilityUnavailableException("RELATIONSHIP_ROUTE_DENIED");
        capability.RequireRecipient(route.ServiceTenantId, senderHash, clock.GetUtcNow());
    }

    internal void RequireRelationshipRoute(WhatsAppCurrentRelationshipRoute route)
    {
        if (_current.Value is null)
            throw new WhatsAppCapabilityUnavailableException("RELATIONSHIP_ROUTE_DENIED");
        RequireUnchangedAuthority();
        if (_relationshipRoute.Value != route)
            throw new WhatsAppCapabilityUnavailableException("RELATIONSHIP_ROUTE_DENIED");
        RequireRelationshipRecipient(
            route.TenantId,
            route.RelationshipId,
            route.BindingId,
            route.SenderHash
        );
    }

    private sealed class Scope(WhatsAppTenantExecutionScope owner) : IDisposable
    {
        public void Dispose()
        {
            owner._relationshipRoute.Value = null;
            owner._relationshipCandidate.Value = null;
            owner._databaseTenantOverride.Value = null;
            owner._current.Value = null;
        }
    }

    private sealed class RelationshipScope(WhatsAppTenantExecutionScope owner) : IDisposable
    {
        public void Dispose()
        {
            owner._relationshipRoute.Value = null;
            owner._relationshipCandidate.Value = null;
        }
    }

    private sealed class DatabaseTenantOverrideScope(WhatsAppTenantExecutionScope owner)
        : IDisposable
    {
        public void Dispose() => owner._databaseTenantOverride.Value = null;
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
    private bool _preferCustomer;

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
                _preferCustomer = !_preferCustomer;
                await scope
                    .ServiceProvider.GetRequiredService<WhatsAppOutboxWorker>()
                    .ProcessOneAsync(_workerId, stoppingToken, _preferCustomer);
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
            catch (ConstitutionalActionDeniedException)
            {
                logger.LogWarning(
                    "WhatsApp customer work fenced: CURRENT_RELATIONSHIP_AUTHORITY_DENIED."
                );
            }
            catch (WhatsAppChannelBindingUnavailableException)
            {
                logger.LogError(
                    "WhatsApp customer routing dependency unavailable; work remains recoverable."
                );
            }
            catch (ConversationStateConflictException)
            {
                logger.LogWarning(
                    "WhatsApp worker lease ownership changed; work remains recoverable."
                );
            }
            catch (ConversationIdempotencyConflictException)
            {
                logger.LogError(
                    "WhatsApp worker source correlation conflict; dispatch remains fenced."
                );
            }
        }
    }
}
