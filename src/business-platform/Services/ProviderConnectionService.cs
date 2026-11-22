// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R007, WC149-R008, WC149-R009
// Constitutional basis: C-023, C-059, C-063, C-083, C-084

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record ProviderConnectionSummary(
    Guid Id,
    string Provider,
    string Status,
    string AccountName,
    string AccountId,
    IReadOnlyList<string> Scopes,
    DateTimeOffset? ExpiresAt,
    DateTimeOffset ConnectedAt
);

public sealed record ProviderConnectionStart(string AuthorizationUrl, DateTimeOffset ExpiresAt);

public sealed record ProviderConnectionCallbackRequest(string? Code, string? State)
{
    public override string ToString() => "ProviderConnectionCallbackRequest { [redacted] }";
}

public sealed record ProviderConnectionPublishRequest(
    string? Message,
    bool? Approved,
    string? ApprovalNote
);

public sealed record ProviderConnectionPublishResult(
    string ProviderPostId,
    DateTimeOffset PublishedAt
);

public sealed class ProviderConnectionException(int status, string code, string detail)
    : Exception(detail)
{
    public int Status { get; } = status;
    public string Code { get; } = code;
}

public interface IProviderConnectionService
{
    Task<IReadOnlyList<ProviderConnectionSummary>> ListAsync(Guid tenantId, CancellationToken ct);

    Task<ProviderConnectionStart> StartMetaAsync(Guid tenantId, Guid actorId, CancellationToken ct);

    Task<ProviderConnectionSummary> CompleteMetaAsync(
        Guid tenantId,
        Guid actorId,
        ProviderConnectionCallbackRequest request,
        CancellationToken ct
    );

    Task RevokeAsync(Guid tenantId, Guid actorId, Guid connectionId, CancellationToken ct);

    Task<ProviderConnectionPublishResult> PublishAsync(
        Guid tenantId,
        Guid actorId,
        Guid connectionId,
        ProviderConnectionPublishRequest request,
        CancellationToken ct
    );
}

/// <summary>
/// Customer Meta Page connections. The Page access token is written to Key Vault under customer-connection-{id}
/// and read back only inside Publish; it never reaches a response, a log line, an exception message or the database.
/// </summary>
public sealed partial class ProviderConnectionService(
    IDbContextFactory<CustomerConnectionsDbContext> dbFactory,
    ISecretVault vault,
    IProviderCredentialResolver appCredentials,
    IMetaGraphClient graph,
    MetaConnectionOptions options,
    TimeProvider clock,
    ILogger<ProviderConnectionService> logger
) : IProviderConnectionService
{
    public const string MetaProvider = "meta";
    public static readonly TimeSpan StateLifetime = TimeSpan.FromMinutes(10);
    public const int MaximumMessageLength = 2000;
    private const int MaximumLiveStates = 10;
    private const int MaximumApprovalNoteLength = 500;

    [GeneratedRegex("^[A-Za-z0-9_-]{32,128}$")]
    private static partial Regex StatePattern();

    [GeneratedRegex("^[^\\s\\p{C}]{1,2048}$")]
    private static partial Regex CodePattern();

    public async Task<IReadOnlyList<ProviderConnectionSummary>> ListAsync(
        Guid tenantId,
        CancellationToken ct
    ) =>
        await InTenantAsync(
            tenantId,
            async db =>
            {
                var rows = await db
                    .Connections.AsNoTracking()
                    .Where(c => c.TenantId == tenantId)
                    .OrderByDescending(c => c.ConnectedAt)
                    .ThenBy(c => c.Id)
                    .ToListAsync(ct);
                return (IReadOnlyList<ProviderConnectionSummary>)rows.Select(Summary).ToList();
            },
            ct
        );

    public async Task<ProviderConnectionStart> StartMetaAsync(
        Guid tenantId,
        Guid actorId,
        CancellationToken ct
    )
    {
        if (options.RedirectUriValue is null)
            throw new ProviderConnectionException(
                503,
                "CONNECTION_PROVIDER_NOT_CONFIGURED",
                "Meta connections are not configured."
            );
        var (appId, _) = await AppAsync(ct);
        var now = clock.GetUtcNow();
        var state = Base64Url(RandomNumberGenerator.GetBytes(32));
        var expires = now + StateLifetime;
        await InTenantAsync(
            tenantId,
            async db =>
            {
                var live = await db.States.CountAsync(
                    s =>
                        s.TenantId == tenantId
                        && s.ActorId == actorId
                        && s.ConsumedAt == null
                        && s.ExpiresAt > now,
                    ct
                );
                if (live >= MaximumLiveStates)
                    throw new ProviderConnectionException(
                        429,
                        "CONNECTION_TOO_MANY_ATTEMPTS",
                        "Too many connection attempts are in progress. Try again in a few minutes."
                    );
                db.States.Add(
                    new ProviderConnectionState
                    {
                        StateHash = Digest(state),
                        TenantId = tenantId,
                        ActorId = actorId,
                        Provider = MetaProvider,
                        CreatedAt = now,
                        ExpiresAt = expires,
                    }
                );
                await db.SaveChangesAsync(ct);
                return true;
            },
            ct
        );
        return new ProviderConnectionStart(
            options.AuthorizationUrl(appId, state).ToString(),
            expires
        );
    }

    public async Task<ProviderConnectionSummary> CompleteMetaAsync(
        Guid tenantId,
        Guid actorId,
        ProviderConnectionCallbackRequest request,
        CancellationToken ct
    )
    {
        if (
            request.State is null
            || request.Code is null
            || !StatePattern().IsMatch(request.State)
            || !CodePattern().IsMatch(request.Code)
        )
            throw new ProviderConnectionException(
                400,
                "CONNECTION_INVALID",
                "The authorization response is not valid."
            );
        var redirect =
            options.RedirectUriValue
            ?? throw new ProviderConnectionException(
                503,
                "CONNECTION_PROVIDER_NOT_CONFIGURED",
                "Meta connections are not configured."
            );
        var now = clock.GetUtcNow();
        var hash = Digest(request.State);
        // The state is consumed before anything else so a replay, a wrong tenant or a wrong actor can never succeed.
        var consumed = await InTenantAsync(
            tenantId,
            db =>
                db.States.Where(s =>
                        s.StateHash == hash
                        && s.TenantId == tenantId
                        && s.ActorId == actorId
                        && s.Provider == MetaProvider
                        && s.ConsumedAt == null
                        && s.ExpiresAt > now
                    )
                    .ExecuteUpdateAsync(set => set.SetProperty(s => s.ConsumedAt, now), ct),
            ct
        );
        if (consumed != 1)
            throw new ProviderConnectionException(
                400,
                "CONNECTION_STATE_INVALID",
                "The connection attempt is invalid or has expired. Start again."
            );

        var (appId, appSecret) = await AppAsync(ct);
        MetaPage page;
        try
        {
            var shortLived = await graph.ExchangeCodeAsync(
                appId,
                appSecret,
                redirect.ToString(),
                request.Code,
                ct
            );
            var longLived = await graph.ExtendUserTokenAsync(appId, appSecret, shortLived, ct);
            var pages = await graph.ListPagesAsync(longLived, ct);
            page =
                pages.FirstOrDefault()
                ?? throw new ProviderConnectionException(
                    400,
                    "CONNECTION_NO_PAGE",
                    "No Facebook Page is available to connect for this account."
                );
        }
        catch (MetaGraphException failure)
        {
            throw Translate(failure, "CONNECTION_AUTHORIZATION_REFUSED");
        }

        var existingId = await InTenantAsync(
            tenantId,
            db =>
                db.Connections.AsNoTracking()
                    .Where(c =>
                        c.TenantId == tenantId
                        && c.Provider == MetaProvider
                        && c.AccountId == page.Id
                        && c.Status != CustomerConnectionStatuses.Revoked
                    )
                    .Select(c => (Guid?)c.Id)
                    .SingleOrDefaultAsync(ct),
            ct
        );
        var connectionId = existingId ?? Guid.NewGuid();
        var secretName = ProviderSecretNames.ForConnection(connectionId);
        string version;
        try
        {
            version = await vault.SetSecretAsync(secretName, page.AccessToken, ct);
        }
        catch (ProviderSecretStoreException)
        {
            throw VaultUnavailable();
        }

        try
        {
            var summary = await InTenantAsync(
                tenantId,
                async db =>
                {
                    var row = existingId is null
                        ? null
                        : await db.Connections.SingleOrDefaultAsync(
                            c => c.Id == connectionId && c.TenantId == tenantId,
                            ct
                        );
                    if (row is null)
                    {
                        row = new CustomerProviderConnection
                        {
                            Id = connectionId,
                            TenantId = tenantId,
                            Provider = MetaProvider,
                            AccountId = page.Id,
                            SecretName = secretName,
                        };
                        db.Connections.Add(row);
                    }
                    row.Status = CustomerConnectionStatuses.Connected;
                    row.AccountName = page.Name;
                    row.Scopes = [.. MetaConnectionOptions.Scopes];
                    row.SecretVersion = version;
                    row.ExpiresAt = null;
                    row.ConnectedAt = now;
                    row.RevokedAt = null;
                    row.CreatedBy = actorId;
                    await db.SaveChangesAsync(ct);
                    return Summary(row);
                },
                ct
            );
            logger.LogInformation(
                "Provider connection {Outcome}: tenant={TenantId} connection={ConnectionId} actor={ActorId}",
                existingId is null ? "connected" : "reconnected",
                tenantId,
                connectionId,
                actorId
            );
            return summary;
        }
        catch (DbUpdateException failure)
            when (failure.InnerException
                    is PostgresException { SqlState: PostgresErrorCodes.UniqueViolation }
            )
        {
            if (existingId is null)
                await TryDeleteAsync(secretName);
            throw new ProviderConnectionException(
                409,
                "CONNECTION_CONFLICT",
                "This account is already being connected. Try again."
            );
        }
    }

    public async Task RevokeAsync(
        Guid tenantId,
        Guid actorId,
        Guid connectionId,
        CancellationToken ct
    )
    {
        var connection = await FindAsync(tenantId, connectionId, ct);
        if (connection.Status == CustomerConnectionStatuses.Revoked)
            return;
        try
        {
            await vault.DeleteSecretAsync(connection.SecretName, ct);
        }
        catch (ProviderSecretStoreException)
        {
            throw VaultUnavailable();
        }
        var now = clock.GetUtcNow();
        await InTenantAsync(
            tenantId,
            db =>
                db.Connections.Where(c =>
                        c.Id == connectionId
                        && c.TenantId == tenantId
                        && c.Status != CustomerConnectionStatuses.Revoked
                    )
                    .ExecuteUpdateAsync(
                        set =>
                            set.SetProperty(c => c.Status, CustomerConnectionStatuses.Revoked)
                                .SetProperty(c => c.RevokedAt, now),
                        ct
                    ),
            ct
        );
        logger.LogInformation(
            "Provider connection revoked: tenant={TenantId} connection={ConnectionId} actor={ActorId}",
            tenantId,
            connectionId,
            actorId
        );
    }

    public async Task<ProviderConnectionPublishResult> PublishAsync(
        Guid tenantId,
        Guid actorId,
        Guid connectionId,
        ProviderConnectionPublishRequest request,
        CancellationToken ct
    )
    {
        if (request.Approved != true)
            throw new ProviderConnectionException(
                400,
                "CONNECTION_APPROVAL_REQUIRED",
                "Publishing needs an explicit approval."
            );
        if (
            request.Message is not { Length: > 0 and <= MaximumMessageLength } message
            || string.IsNullOrWhiteSpace(message)
            || request.ApprovalNote is { Length: > MaximumApprovalNoteLength }
        )
            throw new ProviderConnectionException(
                400,
                "CONNECTION_INVALID",
                $"The message must be between 1 and {MaximumMessageLength} characters."
            );
        var connection = await FindAsync(tenantId, connectionId, ct);
        switch (connection.Status)
        {
            case CustomerConnectionStatuses.Revoked:
                throw new ProviderConnectionException(
                    409,
                    "CONNECTION_REVOKED",
                    "This connection has been revoked."
                );
            case CustomerConnectionStatuses.NeedsRepair:
                throw NeedsRepair();
        }

        string? token;
        try
        {
            token = await vault.GetSecretAsync(connection.SecretName, connection.SecretVersion, ct);
        }
        catch (ProviderSecretStoreException)
        {
            throw VaultUnavailable();
        }
        if (string.IsNullOrEmpty(token))
        {
            await MarkNeedsRepairAsync(tenantId, connectionId, ct);
            throw NeedsRepair();
        }

        string postId;
        try
        {
            postId = await graph.PublishAsync(connection.AccountId, token, message, ct);
        }
        catch (MetaGraphException failure) when (failure.Failure == MetaGraphFailure.AuthRejected)
        {
            await MarkNeedsRepairAsync(tenantId, connectionId, ct);
            throw NeedsRepair();
        }
        catch (MetaGraphException failure)
        {
            throw Translate(failure, "CONNECTION_PUBLISH_REJECTED");
        }
        logger.LogInformation(
            "Provider connection published: tenant={TenantId} connection={ConnectionId} actor={ActorId} messageLength={Length} approvalNotePresent={Note}",
            tenantId,
            connectionId,
            actorId,
            message.Length,
            !string.IsNullOrWhiteSpace(request.ApprovalNote)
        );
        return new ProviderConnectionPublishResult(postId, clock.GetUtcNow());
    }

    private async Task<CustomerProviderConnection> FindAsync(
        Guid tenantId,
        Guid connectionId,
        CancellationToken ct
    ) =>
        await InTenantAsync(
            tenantId,
            db =>
                db.Connections.AsNoTracking()
                    .SingleOrDefaultAsync(c => c.Id == connectionId && c.TenantId == tenantId, ct),
            ct
        )
        ?? throw new ProviderConnectionException(
            404,
            "CONNECTION_NOT_FOUND",
            "The connection was not found."
        );

    private Task MarkNeedsRepairAsync(Guid tenantId, Guid connectionId, CancellationToken ct) =>
        InTenantAsync(
            tenantId,
            db =>
                db.Connections.Where(c =>
                        c.Id == connectionId
                        && c.TenantId == tenantId
                        && c.Status == CustomerConnectionStatuses.Connected
                    )
                    .ExecuteUpdateAsync(
                        set =>
                            set.SetProperty(c => c.Status, CustomerConnectionStatuses.NeedsRepair),
                        ct
                    ),
            ct
        );

    private async Task<(string AppId, string AppSecret)> AppAsync(CancellationToken ct)
    {
        var resolved = await appCredentials.ResolveAsync(MetaProvider, ct);
        if (resolved is null)
            throw NotConfigured();
        string? value;
        try
        {
            value = await vault.GetSecretAsync(resolved.SecretName, resolved.SecretVersion, ct);
        }
        catch (ProviderSecretStoreException)
        {
            throw VaultUnavailable();
        }
        try
        {
            using var document = JsonDocument.Parse(value ?? string.Empty);
            var root = document.RootElement;
            if (
                root.ValueKind == JsonValueKind.Object
                && root.TryGetProperty("appId", out var id)
                && id.GetString() is { Length: > 0 } appId
                && root.TryGetProperty("appSecret", out var secret)
                && secret.GetString() is { Length: > 0 } appSecret
            )
                return (appId, appSecret);
        }
        catch (JsonException) { }
        throw NotConfigured();
    }

    private async Task TryDeleteAsync(string secretName)
    {
        try
        {
            await vault.DeleteSecretAsync(secretName, CancellationToken.None);
        }
        catch (ProviderSecretStoreException)
        {
            logger.LogWarning("An orphaned customer connection secret could not be removed.");
        }
    }

    private async Task<T> InTenantAsync<T>(
        Guid tenantId,
        Func<CustomerConnectionsDbContext, Task<T>> work,
        CancellationToken ct
    )
    {
        await using var db = await dbFactory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT set_config('app.current_tenant_id', {tenantId.ToString("D")}, true)",
            ct
        );
        var result = await work(db);
        await transaction.CommitAsync(ct);
        return result;
    }

    private static ProviderConnectionException Translate(
        MetaGraphException failure,
        string refused
    ) =>
        failure.Failure switch
        {
            MetaGraphFailure.Unavailable => new ProviderConnectionException(
                503,
                "CONNECTION_PROVIDER_UNAVAILABLE",
                "Meta could not be reached. Try again shortly."
            ),
            MetaGraphFailure.AuthRejected => new ProviderConnectionException(
                400,
                refused,
                "Meta refused the authorization."
            ),
            _ => new ProviderConnectionException(502, refused, "Meta did not accept the request."),
        };

    private static ProviderConnectionException NeedsRepair() =>
        new(
            409,
            "CONNECTION_NEEDS_REPAIR",
            "Meta no longer accepts this connection. Reconnect it to continue."
        );

    private static ProviderConnectionException NotConfigured() =>
        new(503, "CONNECTION_PROVIDER_NOT_CONFIGURED", "Meta connections are not configured.");

    private static ProviderConnectionException VaultUnavailable() =>
        new(
            503,
            "CONNECTION_VAULT_UNAVAILABLE",
            "The secure store is unavailable. Try again shortly."
        );

    private static ProviderConnectionSummary Summary(CustomerProviderConnection row) =>
        new(
            row.Id,
            row.Provider,
            row.Status,
            row.AccountName,
            row.AccountId,
            row.Scopes,
            row.ExpiresAt,
            row.ConnectedAt
        );

    private static string Digest(string state) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(state)));

    private static string Base64Url(byte[] value) =>
        Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');
}
