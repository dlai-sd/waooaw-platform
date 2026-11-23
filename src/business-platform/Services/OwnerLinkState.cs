// Implements: ADR-046 sections 5.3 and 12.2 D6, D9; workload-identity-cloud-issuance-contract.md section 8
// constitutional_basis: C-023, C-059, C-063, C-083, C-084

using System.Collections.Concurrent;
using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services;

public enum OwnerLinkStatus
{
    Unconfigured,
    Unavailable,
    Ready,
}

internal sealed record OwnerLinkTarget(string Owner, string Target, Uri? BaseUrl);

/// <summary>Coarse, non-gating state of the signed-transport link to each private owner.</summary>
public sealed class OwnerLinkState
{
    private readonly ConcurrentDictionary<string, OwnerLinkStatus> _states = new();

    public void Set(string owner, OwnerLinkStatus status) => _states[owner] = status;

    public bool AnyUnavailable =>
        _states.Values.Any(status => status == OwnerLinkStatus.Unavailable);

    public IReadOnlyDictionary<string, string> Snapshot() =>
        _states
            .OrderBy(entry => entry.Key, StringComparer.Ordinal)
            .ToDictionary(entry => entry.Key, entry => entry.Value.ToString().ToUpperInvariant());
}

/// <summary>Probes GET /internal/v1/service-link over the mutual-TLS client; no delegated envelope is sent.</summary>
internal sealed class OwnerLinkProber(
    WorkloadIdentityClient identity,
    OwnerLinkState state,
    IReadOnlyList<OwnerLinkTarget> owners,
    Func<Uri, string, HttpClient>? clientFactory = null
) : IDisposable
{
    public const string ProbeRoute = "/internal/v1/service-link";

    private readonly Dictionary<string, HttpClient> _clients = new(StringComparer.Ordinal);
    private readonly Func<Uri, string, HttpClient> _factory =
        clientFactory ?? identity.CreateClient;

    public bool AnyUnavailable => state.AnyUnavailable;

    public async Task ProbeAllAsync(CancellationToken cancellationToken)
    {
        foreach (var owner in owners)
            state.Set(owner.Owner, await ProbeAsync(owner, cancellationToken));
    }

    private async Task<OwnerLinkStatus> ProbeAsync(
        OwnerLinkTarget owner,
        CancellationToken cancellationToken
    )
    {
        if (owner.BaseUrl is null)
            return OwnerLinkStatus.Unconfigured;
        if (!identity.IsAvailable)
            return OwnerLinkStatus.Unavailable;
        try
        {
            if (!_clients.TryGetValue(owner.Owner, out var client))
                _clients[owner.Owner] = client = _factory(owner.BaseUrl, owner.Target);
            using var response = await client.GetAsync(ProbeRoute, cancellationToken);
            if (!response.IsSuccessStatusCode)
                return OwnerLinkStatus.Unavailable;
            using var document = JsonDocument.Parse(
                await response.Content.ReadAsStringAsync(cancellationToken)
            );
            var root = document.RootElement;
            // The owner echoes the identity of its caller, which is this workload.
            var ownIdentity = identity.GetOwnIdentityUri();
            return
                ownIdentity is not null
                && root.ValueKind == JsonValueKind.Object
                && root.TryGetProperty("status", out var status)
                && status.ValueKind == JsonValueKind.String
                && status.GetString() == "ok"
                && root.TryGetProperty("peer_identity_uri", out var peer)
                && peer.ValueKind == JsonValueKind.String
                && peer.GetString() == ownIdentity
                ? OwnerLinkStatus.Ready
                : OwnerLinkStatus.Unavailable;
        }
        catch (Exception exception)
            when (exception
                    is HttpRequestException
                        or TaskCanceledException
                        or JsonException
                        or InvalidOperationException
            )
        {
            return OwnerLinkStatus.Unavailable;
        }
    }

    public void Dispose()
    {
        foreach (var client in _clients.Values)
            client.Dispose();
    }
}
