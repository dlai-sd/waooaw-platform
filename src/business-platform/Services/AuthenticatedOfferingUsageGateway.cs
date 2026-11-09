// Implements: work-contracts/WC-134-batching-offering-and-spend-work-component.md §9.3
using System.Net;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Waooaw.BusinessPlatform.Services;

public sealed record OfferingUsageIdentity(
    Guid TenantId,
    Guid RelationshipId,
    Guid ActorId,
    Guid AgentInstanceId,
    string ProfessionalType,
    string ProfessionalVersion,
    string SkillId,
    string SkillVersion,
    Guid WorkItemId,
    Guid InvocationId,
    string ComponentId,
    Guid IdempotencyKey,
    string RequestDigest,
    Guid OwnerEvidenceId
);

public sealed record OfferingUsageReceipt(
    Guid ReservationId,
    string State,
    long MaximumUnits,
    long ReservedRawPaise,
    long ReservedMarkedUpPaise,
    string CatalogueThreadId,
    Guid ProviderAccountId,
    string RateVersion,
    bool Replayed
);

public interface IAuthenticatedOfferingUsageGateway
{
    Task<OfferingUsageReceipt> ReserveAsync(
        OfferingUsageIdentity identity,
        long maximumUnits,
        CancellationToken ct
    );
    Task<OfferingUsageReceipt> SettleAsync(
        OfferingUsageIdentity identity,
        Guid reservationId,
        long actualUnits,
        Guid evidenceId,
        CancellationToken ct
    );
    Task<OfferingUsageReceipt> ReleaseAsync(
        OfferingUsageIdentity identity,
        Guid reservationId,
        Guid nonDispatchEvidenceId,
        CancellationToken ct
    );
    Task<OfferingUsageReceipt?> ReconcileAsync(
        OfferingUsageIdentity identity,
        Guid? reservationId,
        CancellationToken ct
    );
}

public sealed class OfferingUsageOwnerUnavailableException(string message, Exception? inner = null)
    : Exception(message, inner);

public sealed class AuthenticatedOfferingUsageGateway
    : IAuthenticatedOfferingUsageGateway,
        IDisposable
{
    private readonly WorkloadIdentityClient _identity;
    private readonly HttpClient _client;

    public AuthenticatedOfferingUsageGateway(WorkloadIdentityClient identity, Uri endpoint)
    {
        _identity = identity;
        _client = identity.CreateClient(endpoint, "billing-engine");
    }

    public Task<OfferingUsageReceipt> ReserveAsync(
        OfferingUsageIdentity identity,
        long maximumUnits,
        CancellationToken ct
    ) => SendAsync(identity, "reserve", maximumUnits, null, null, null, ct);

    public Task<OfferingUsageReceipt> SettleAsync(
        OfferingUsageIdentity identity,
        Guid reservationId,
        long actualUnits,
        Guid evidenceId,
        CancellationToken ct
    ) => SendAsync(identity, "settle", null, reservationId, actualUnits, evidenceId, ct);

    public Task<OfferingUsageReceipt> ReleaseAsync(
        OfferingUsageIdentity identity,
        Guid reservationId,
        Guid nonDispatchEvidenceId,
        CancellationToken ct
    ) => SendAsync(identity, "release", null, reservationId, null, nonDispatchEvidenceId, ct);

    public async Task<OfferingUsageReceipt?> ReconcileAsync(
        OfferingUsageIdentity identity,
        Guid? reservationId,
        CancellationToken ct
    )
    {
        try
        {
            return await SendAsync(identity, "reconcile", null, reservationId, null, null, ct);
        }
        catch (OfferingUsageOwnerUnavailableException exception)
            when (exception.InnerException is WbeOfferingNotFoundException)
        {
            return null;
        }
    }

    private async Task<OfferingUsageReceipt> SendAsync(
        OfferingUsageIdentity value,
        string action,
        long? maximumUnits,
        Guid? reservationId,
        long? actualUnits,
        Guid? outcomeEvidenceId,
        CancellationToken ct
    )
    {
        var route = $"/internal/v1/relationships/{{relationshipId}}/offering-usage/{action}";
        var operation = $"{action}OfferingComponentUsage";
        var body = new SortedDictionary<string, object?>(StringComparer.Ordinal)
        {
            ["actualUnits"] = actualUnits,
            ["agentInstanceId"] = value.AgentInstanceId,
            ["componentId"] = value.ComponentId,
            ["invocationId"] = value.InvocationId,
            ["maximumUnits"] = maximumUnits,
            ["outcomeEvidenceId"] = outcomeEvidenceId,
            ["ownerEvidenceId"] = value.OwnerEvidenceId,
            ["professionalType"] = value.ProfessionalType,
            ["professionalVersion"] = value.ProfessionalVersion,
            ["requestDigest"] = value.RequestDigest,
            ["reservationId"] = reservationId,
            ["schemaVersion"] = "1.0",
            ["skillId"] = value.SkillId,
            ["skillVersion"] = value.SkillVersion,
            ["workItemId"] = value.WorkItemId,
        };
        var bytes = JsonSerializer.SerializeToUtf8Bytes(
            body,
            new JsonSerializerOptions
            {
                DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
            }
        );
        var digest = Convert.ToHexStringLower(SHA256.HashData(bytes));
        var correlation = value.InvocationId.ToString("D");
        var context = new DelegatedRequestContext(
            value.ActorId.ToString("D"),
            "PROFESSIONAL",
            value.TenantId.ToString("D"),
            value.RelationshipId.ToString("D"),
            "OFFERING_COMPONENT_USAGE",
            value.ComponentId,
            correlation,
            value.IdempotencyKey.ToString("D"),
            new Dictionary<string, string>
            {
                ["component"] = value.ComponentId,
                ["professional"] = value.ProfessionalVersion,
                ["skill"] = value.SkillVersion,
            },
            correlation
        );
        var envelope = _identity.Sign(
            context,
            _identity.GetAudience("billing-engine"),
            "POST",
            route,
            operation,
            1,
            digest,
            DateTimeOffset.UtcNow
        );
        using var request = new HttpRequestMessage(
            HttpMethod.Post,
            route.Replace("{relationshipId}", value.RelationshipId.ToString("D"))
        )
        {
            Content = new ByteArrayContent(bytes),
        };
        request.Content.Headers.ContentType = new("application/json");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", envelope);
        request.Headers.Add("X-Correlation-ID", correlation);
        request.Headers.Add("Idempotency-Key", value.IdempotencyKey.ToString("D"));
        try
        {
            using var response = await _client.SendAsync(request, ct);
            if (response.StatusCode == HttpStatusCode.NotFound)
                throw new WbeOfferingNotFoundException();
            if (!response.IsSuccessStatusCode)
                throw new OfferingUsageOwnerUnavailableException(
                    $"WBE offering owner returned {(int)response.StatusCode}."
                );
            return await response.Content.ReadFromJsonAsync<OfferingUsageReceipt>(ct)
                ?? throw new OfferingUsageOwnerUnavailableException(
                    "WBE offering owner returned no receipt."
                );
        }
        catch (Exception exception)
            when (exception
                    is HttpRequestException
                        or TaskCanceledException
                        or WbeOfferingNotFoundException
            )
        {
            throw new OfferingUsageOwnerUnavailableException(
                "WBE offering usage outcome is unresolved.",
                exception
            );
        }
    }

    public void Dispose() => _client.Dispose();

    private sealed class WbeOfferingNotFoundException : Exception;
}

public sealed class UnconfiguredOfferingUsageGateway : IAuthenticatedOfferingUsageGateway
{
    private static OfferingUsageOwnerUnavailableException Unavailable() =>
        new("Authenticated WBE offering owner is not configured.");

    public Task<OfferingUsageReceipt> ReserveAsync(
        OfferingUsageIdentity identity,
        long maximumUnits,
        CancellationToken ct
    ) => Task.FromException<OfferingUsageReceipt>(Unavailable());

    public Task<OfferingUsageReceipt> SettleAsync(
        OfferingUsageIdentity identity,
        Guid reservationId,
        long actualUnits,
        Guid evidenceId,
        CancellationToken ct
    ) => Task.FromException<OfferingUsageReceipt>(Unavailable());

    public Task<OfferingUsageReceipt> ReleaseAsync(
        OfferingUsageIdentity identity,
        Guid reservationId,
        Guid nonDispatchEvidenceId,
        CancellationToken ct
    ) => Task.FromException<OfferingUsageReceipt>(Unavailable());

    public Task<OfferingUsageReceipt?> ReconcileAsync(
        OfferingUsageIdentity identity,
        Guid? reservationId,
        CancellationToken ct
    ) => Task.FromException<OfferingUsageReceipt?>(Unavailable());
}
