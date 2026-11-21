// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01, C6-02
// Constitutional basis: C-023, C-059, C-063, ADR-051

using System.Collections.Concurrent;
using System.Net;
using System.Net.Http.Headers;
using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services.Workbench;

public sealed class WorkbenchOptions
{
    public const string SectionName = "Workbench";

    public bool Enabled { get; set; }
    public string HandoffBaseUrl { get; set; } = string.Empty;
    public int HandoffTtlSeconds { get; set; } = 900;
}

/// <summary>Identifies the admitted agent whose experience manifest a relationship is bound to.</summary>
public sealed record AdmittedManifestRequest(
    string AgentType,
    string AgentVersion,
    string ManifestVersion,
    string ActorSubject,
    string EffectiveRole,
    Guid TenantId,
    Guid RelationshipId,
    string CorrelationId
);

public interface IAdmittedExperienceManifestSource
{
    /// <summary>Returns the admitted manifest document, or null when the domain owner cannot supply it.</summary>
    Task<JsonDocument?> GetAsync(AdmittedManifestRequest request, CancellationToken ct);
}

public sealed class UnconfiguredAdmittedExperienceManifestSource : IAdmittedExperienceManifestSource
{
    public Task<JsonDocument?> GetAsync(AdmittedManifestRequest request, CancellationToken ct) =>
        Task.FromResult<JsonDocument?>(null);
}

/// <summary>
/// Reads the admitted manifest from the domain adapter that owns it, through the workload identity channel.
/// A manifest version is immutable once admitted, so one successful read is cached for the process lifetime.
/// </summary>
public sealed class DomainAdapterExperienceManifestSource
    : IAdmittedExperienceManifestSource,
        IDisposable
{
    private const string Route = "/internal/v1/employment-interface/manifest";
    private const string Operation = "getEmploymentInterfaceManifest";
    private const string EmptyDigest =
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

    private readonly WorkloadIdentityClient _identity;
    private readonly HttpClient _client;
    private readonly ConcurrentDictionary<(string, string, string), JsonDocument> _cache = new();

    public DomainAdapterExperienceManifestSource(WorkloadIdentityClient identity, Uri endpoint)
    {
        _identity = identity;
        _client = identity.CreateClient(endpoint, "domain-adapter");
    }

    public async Task<JsonDocument?> GetAsync(AdmittedManifestRequest request, CancellationToken ct)
    {
        var key = (request.AgentType, request.AgentVersion, request.ManifestVersion);
        if (_cache.TryGetValue(key, out var cached))
            return cached;
        var context = new DelegatedRequestContext(
            request.ActorSubject,
            request.EffectiveRole,
            request.TenantId.ToString("D"),
            request.RelationshipId.ToString("D"),
            Operation,
            request.RelationshipId.ToString("D"),
            Guid.NewGuid().ToString("D"),
            null,
            new Dictionary<string, string> { ["manifest"] = request.ManifestVersion },
            request.CorrelationId
        );
        var envelope = _identity.Sign(
            context,
            _identity.GetAudience("domain-adapter"),
            HttpMethod.Get.Method,
            Route,
            Operation,
            1,
            EmptyDigest,
            DateTimeOffset.UtcNow
        );
        var query =
            $"?agentType={Uri.EscapeDataString(request.AgentType)}"
            + $"&agentVersion={Uri.EscapeDataString(request.AgentVersion)}"
            + $"&manifestVersion={Uri.EscapeDataString(request.ManifestVersion)}";
        using var message = new HttpRequestMessage(HttpMethod.Get, Route + query);
        message.Headers.Authorization = new AuthenticationHeaderValue("Bearer", envelope);
        message.Headers.Add("X-Correlation-ID", request.CorrelationId);
        try
        {
            using var response = await _client.SendAsync(message, ct);
            if (response.StatusCode != HttpStatusCode.OK)
                return null;
            var document = await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(ct),
                cancellationToken: ct
            );
            _cache[key] = document;
            return document;
        }
        catch (Exception exception)
            when (exception is HttpRequestException or TaskCanceledException or JsonException)
        {
            return null;
        }
    }

    public void Dispose()
    {
        _client.Dispose();
        foreach (var document in _cache.Values)
            document.Dispose();
        _cache.Clear();
    }
}
