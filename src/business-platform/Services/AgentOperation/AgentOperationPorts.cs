// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R010, R018, R022, R023, R034
// Constitutional basis: C-001, C-023, C-059, C-063, C-083, C-084

using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.Alerts;
using Waooaw.BusinessPlatform.Services.Workbench;

namespace Waooaw.BusinessPlatform.Services.AgentOperation;

/// <summary>What Agent Operation needs to know of the relationship; the agent's identity stays inside the declaration.</summary>
public sealed record OperationRelationship(
    string ProfessionalType,
    bool Stopped,
    ExperienceDeclaration? Declaration
);

public interface IOperationRelationshipSource
{
    Task<OperationRelationship?> GetAsync(OperationCaller caller, CancellationToken ct);
}

public sealed class WorkbenchOperationRelationshipSource(
    EmploymentRelationshipService relationships,
    WorkbenchProjectionService projection
) : IOperationRelationshipSource
{
    public async Task<OperationRelationship?> GetAsync(OperationCaller caller, CancellationToken ct)
    {
        var relationship = await relationships.GetAsync(caller.TenantId, caller.RelationshipId, ct);
        if (relationship is null)
            return null;
        var declaration = caller.Workbench is null
            ? null
            : await projection.GetDeclarationAsync(caller.Workbench, ct);
        return new OperationRelationship(
            relationship.ProfessionalType,
            relationship.State
                is EmploymentRelationshipState.StoppedEmergency
                    or EmploymentRelationshipState.Terminated,
            declaration
        );
    }
}

/// <summary>What the owner (the billing engine, through the workbench reader) says is left of each counted component.</summary>
public interface IOperationPackageLimits
{
    /// <summary>Remaining quantity per component id, or null when the owner cannot be read (never guessed).</summary>
    Task<IReadOnlyDictionary<string, int>?> RemainingAsync(
        OperationCaller caller,
        CancellationToken ct
    );
}

public sealed class WorkbenchOperationPackageLimits(IWorkbenchCommercialReader reader)
    : IOperationPackageLimits
{
    public async Task<IReadOnlyDictionary<string, int>?> RemainingAsync(
        OperationCaller caller,
        CancellationToken ct
    )
    {
        if (caller.Workbench is null)
            return null;
        var wallet = await reader.GetWalletAsync(caller.Workbench, ct);
        return wallet.Available
            ? wallet.Components.ToDictionary(
                component => component.ComponentId,
                component => component.Remaining,
                StringComparer.Ordinal
            )
            : null;
    }
}

/// <summary>Alerts go through the WC-171 policy; this port only names the situation.</summary>
public interface IOperationAlertSink
{
    Task RaiseAsync(
        Guid tenantId,
        Guid relationshipId,
        string signal,
        string severity,
        string period,
        string meaning,
        CancellationToken ct
    );
}

public sealed class PolicyOperationAlertSink(AlertPolicyService policy) : IOperationAlertSink
{
    public async Task RaiseAsync(
        Guid tenantId,
        Guid relationshipId,
        string signal,
        string severity,
        string period,
        string meaning,
        CancellationToken ct
    ) =>
        await policy.RaiseAsync(
            new AlertEvent(
                AlertSources.AgentDeclared,
                tenantId,
                relationshipId,
                signal,
                severity,
                period,
                meaning,
                Category: "OPERATION",
                DestinationSurface: "ALERTS"
            ),
            whatsAppConsent: false,
            stopReceived: false,
            ct
        );
}

public sealed record ConnectionFacts(
    Guid ConnectionId,
    string Connector,
    string Status,
    string AccountId,
    string AccountName
);

public sealed record ConnectedPost(string ProviderPostId, DateTimeOffset PublishedAt);

public sealed class ConnectionNeedsRepairException() : Exception("The connection needs repair.");

/// <summary>
/// The only way any agent or platform part obtains a customer's connected account (WC174-R034, FD7). It returns facts
/// and results, never a key. What sits behind it (today the WC-149 custody) can change without touching a caller.
/// </summary>
public interface ICustomerConnectionInterface
{
    Task<IReadOnlyList<ConnectionFacts>> ListAsync(Guid tenantId, CancellationToken ct);

    Task<ConnectedPost> PublishAsync(
        Guid tenantId,
        Guid actorId,
        Guid connectionId,
        string message,
        string approvalNote,
        CancellationToken ct
    );
}

/// <summary>The as-built custody (WC-149) behind the interface: a Meta Page connection held in the platform's key custody.</summary>
public sealed class ProviderCustodyConnectionInterface(IProviderConnectionService custody)
    : ICustomerConnectionInterface
{
    public const string InstagramPublishScope = "instagram_content_publish";

    public async Task<IReadOnlyList<ConnectionFacts>> ListAsync(Guid tenantId, CancellationToken ct)
    {
        var connections = await custody.ListAsync(tenantId, ct);
        var facts = new List<ConnectionFacts>();
        foreach (
            var connection in connections.Where(connection =>
                connection.Provider == ProviderConnectionService.MetaProvider
                && connection.Status != CustomerConnectionStatuses.Revoked
            )
        )
        {
            facts.Add(
                new ConnectionFacts(
                    connection.Id,
                    "META_FACEBOOK",
                    connection.Status,
                    connection.AccountId,
                    connection.AccountName
                )
            );
            if (connection.Scopes.Contains(InstagramPublishScope, StringComparer.Ordinal))
                facts.Add(
                    new ConnectionFacts(
                        connection.Id,
                        "META_INSTAGRAM",
                        connection.Status,
                        connection.AccountId,
                        connection.AccountName
                    )
                );
        }
        return facts;
    }

    public async Task<ConnectedPost> PublishAsync(
        Guid tenantId,
        Guid actorId,
        Guid connectionId,
        string message,
        string approvalNote,
        CancellationToken ct
    )
    {
        try
        {
            var result = await custody.PublishAsync(
                tenantId,
                actorId,
                connectionId,
                new ProviderConnectionPublishRequest(message, true, approvalNote),
                ct
            );
            return new ConnectedPost(result.ProviderPostId, result.PublishedAt);
        }
        catch (ProviderConnectionException failure)
            when (failure.Code is "CONNECTION_NEEDS_REPAIR" or "CONNECTION_REVOKED")
        {
            throw new ConnectionNeedsRepairException();
        }
    }
}
