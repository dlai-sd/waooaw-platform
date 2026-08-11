// Implements: ADR-046 sections 3.2, 3.3, 5.1, 6, and 10.1
// constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-083, C-084, C-085

using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services;

public sealed record RelationshipOwnerContext(
    string ActorSubject,
    string EffectiveRole,
    Guid TenantId,
    Guid RelationshipId,
    int RelationshipVersion,
    string CorrelationId);

public sealed record ExecutionOwnerProjection(
    string ProjectionVersion,
    string State,
    DateTimeOffset ProducedAt);

public sealed record CommercialOwnerProjection(
    string ProjectionVersion,
    string CurrencyState,
    string Actuals,
    string Forecast,
    string Thresholds,
    DateTimeOffset ProducedAt);

public interface IRelationshipWorkspaceOwnerGateway
{
    Task<ExecutionOwnerProjection?> GetExecutionAsync(RelationshipOwnerContext context, CancellationToken cancellationToken);
    Task<CommercialOwnerProjection?> GetCommercialAsync(RelationshipOwnerContext context, CancellationToken cancellationToken);
}

public sealed class UnconfiguredRelationshipWorkspaceOwnerGateway : IRelationshipWorkspaceOwnerGateway
{
    public Task<ExecutionOwnerProjection?> GetExecutionAsync(
        RelationshipOwnerContext context, CancellationToken cancellationToken) => Task.FromResult<ExecutionOwnerProjection?>(null);

    public Task<CommercialOwnerProjection?> GetCommercialAsync(
        RelationshipOwnerContext context, CancellationToken cancellationToken) => Task.FromResult<CommercialOwnerProjection?>(null);
}

public sealed class AuthenticatedRelationshipWorkspaceOwnerGateway : IRelationshipWorkspaceOwnerGateway, IDisposable
{
    private const string EmptyDigest = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
    private readonly WorkloadIdentityClient _identity;
    private readonly HttpClient _professionalRuntime;
    private readonly HttpClient _billingEngine;

    public AuthenticatedRelationshipWorkspaceOwnerGateway(
        WorkloadIdentityClient identity,
        Uri professionalRuntimeBaseAddress,
        Uri billingEngineBaseAddress)
    {
        _identity = identity;
        _professionalRuntime = identity.CreateClient(professionalRuntimeBaseAddress, "professional-runtime");
        _billingEngine = identity.CreateClient(billingEngineBaseAddress, "billing-engine");
    }

    public async Task<ExecutionOwnerProjection?> GetExecutionAsync(
        RelationshipOwnerContext context, CancellationToken cancellationToken)
    {
        const string route = "/api/v1/internal/relationships/{relationshipId}/workspace-execution";
        using var response = await SendAsync(
            _professionalRuntime,
            route.Replace("{relationshipId}", context.RelationshipId.ToString()),
            "professional-runtime",
            route,
            "getRelationshipExecutionProjection",
            context,
            cancellationToken);
        if (response is null || !response.IsSuccessStatusCode) return null;
        try
        {
            using var document = await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(cancellationToken), cancellationToken: cancellationToken);
            var root = document.RootElement;
            if (root.GetProperty("schemaVersion").GetString() != "1.0"
                || root.GetProperty("relationshipId").GetGuid() != context.RelationshipId) return null;
            return new ExecutionOwnerProjection(
                root.GetProperty("projectionVersion").GetString()!,
                root.GetProperty("state").GetString()!,
                root.GetProperty("producedAt").GetDateTimeOffset());
        }
        catch (Exception exception) when (exception is JsonException or InvalidOperationException or FormatException)
        {
            return null;
        }
    }

    public async Task<CommercialOwnerProjection?> GetCommercialAsync(
        RelationshipOwnerContext context, CancellationToken cancellationToken)
    {
        const string route = "/internal/v1/relationships/{relationshipId}/commercial-projection";
        using var response = await SendAsync(
            _billingEngine,
            route.Replace("{relationshipId}", context.RelationshipId.ToString()),
            "billing-engine",
            route,
            "getRelationshipCommercialProjection",
            context,
            cancellationToken);
        if (response is null || !response.IsSuccessStatusCode) return null;
        try
        {
            using var document = await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(cancellationToken), cancellationToken: cancellationToken);
            var root = document.RootElement;
            if (root.GetProperty("schemaVersion").GetString() != "1.0"
                || root.GetProperty("relationshipId").GetGuid() != context.RelationshipId) return null;
            return new CommercialOwnerProjection(
                root.GetProperty("projectionVersion").GetString()!,
                root.GetProperty("currencyState").GetString()!,
                root.GetProperty("actuals").GetString()!,
                root.GetProperty("forecast").GetString()!,
                root.GetProperty("thresholds").GetString()!,
                root.GetProperty("producedAt").GetDateTimeOffset());
        }
        catch (Exception exception) when (exception is JsonException or InvalidOperationException or FormatException)
        {
            return null;
        }
    }

    private async Task<HttpResponseMessage?> SendAsync(
        HttpClient client,
        string requestPath,
        string targetName,
        string route,
        string operation,
        RelationshipOwnerContext context,
        CancellationToken cancellationToken)
    {
        var delegatedContext = new DelegatedRequestContext(
            context.ActorSubject,
            context.EffectiveRole,
            context.TenantId.ToString(),
            context.RelationshipId.ToString(),
            operation,
            context.RelationshipId.ToString(),
            Guid.NewGuid().ToString(),
            null,
            new Dictionary<string, string> { ["relationship"] = context.RelationshipVersion.ToString() },
            context.CorrelationId);
        var envelope = _identity.Sign(
            delegatedContext,
            _identity.GetAudience(targetName),
            HttpMethod.Get.Method,
            route,
            operation,
            1,
            EmptyDigest,
            DateTimeOffset.UtcNow);
        using var request = new HttpRequestMessage(HttpMethod.Get, requestPath);
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", envelope);
        request.Headers.Add("X-Correlation-ID", context.CorrelationId);
        try
        {
            return await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
        }
        catch (Exception exception) when (exception is HttpRequestException or TaskCanceledException)
        {
            return null;
        }
    }

    public void Dispose()
    {
        _professionalRuntime.Dispose();
        _billingEngine.Dispose();
    }
}