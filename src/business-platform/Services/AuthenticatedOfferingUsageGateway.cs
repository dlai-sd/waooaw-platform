// Implements: work-contracts/WC-134-batching-offering-and-spend-work-component.md §9.3
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-05
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-09
// Constitutional basis: C-023, C-059, C-063
using System.Net;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;
using Waooaw.BusinessPlatform.Services.Spend;

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
    : Exception(message, inner)
{
    public string ReasonCode => SpendRefusalCodes.CommercialUnavailable;
}

/// <summary>Reserve request for the platform-owned classes that have no relationship scope.</summary>
public sealed record PlatformAccountReserveRequest(
    Guid TenantId,
    Guid ActorId,
    SpendAccountClass AccountClass,
    string? Environment,
    string? CampaignRef,
    string? LeadRef,
    string ComponentId,
    long MaximumPaise,
    string? Purpose,
    Guid InvocationId,
    Guid IdempotencyKey,
    Guid OwnerEvidenceId
);

public sealed record PlatformAccountReceipt(
    string AccountClass,
    Guid ReservationId,
    Guid AccountId,
    string State,
    long ReservedPaise,
    bool Replayed
);

public sealed record SetupGrantReceipt(
    string Status,
    Guid AccountId,
    Guid? LotId,
    long CreditedPaise,
    bool Created
);

/// <summary>Result of an onboarding draw; SETUP_GRANT_EXHAUSTED is an outcome, not a failure.</summary>
public sealed record SetupGrantDrawReceipt(
    string Status,
    Guid AccountId,
    Guid? ReservationId,
    long ReservedPaise,
    bool Replayed
)
{
    public const string Reserved = "RESERVED";
    public const string Exhausted = "SETUP_GRANT_EXHAUSTED";

    public bool IsExhausted => Status == Exhausted;
}

public sealed record WalletReservationOutcome(
    Guid ReservationId,
    Guid AccountId,
    string State,
    long ReservedPaise,
    long? ActualPaise,
    long OverrunPaise,
    bool Fenced,
    bool Replayed
);

/// <summary>The wallet owner refused the request, for example ACQUISITION_BUDGET_EXHAUSTED naming a level.</summary>
public sealed class PlatformAccountRefusedException(string code, string? level) : Exception(code)
{
    public string Code { get; } = code;

    public string? Level { get; } = level;
}

public interface IPlatformAccountGateway
{
    Task<PlatformAccountReceipt> ReserveAccountAsync(
        PlatformAccountReserveRequest request,
        CancellationToken ct
    );
    Task<SetupGrantReceipt> OpenSetupGrantAsync(
        Guid tenantId,
        Guid actorId,
        Guid relationshipId,
        string agentType,
        string agentVersion,
        Guid idempotencyKey,
        CancellationToken ct
    );
    Task<SetupGrantDrawReceipt> ReserveSetupGrantAsync(
        Guid tenantId,
        Guid actorId,
        Guid relationshipId,
        string agentType,
        string agentVersion,
        string componentId,
        long maximumPaise,
        Guid invocationId,
        Guid ownerEvidenceId,
        Guid idempotencyKey,
        CancellationToken ct
    );
    Task<WalletReservationOutcome> SettleAccountAsync(
        Guid tenantId,
        Guid actorId,
        Guid reservationId,
        long actualPaise,
        Guid evidenceId,
        Guid idempotencyKey,
        CancellationToken ct
    );
    Task<WalletReservationOutcome> ReleaseAccountAsync(
        Guid tenantId,
        Guid actorId,
        Guid reservationId,
        Guid nonDispatchEvidenceId,
        Guid idempotencyKey,
        CancellationToken ct
    );
}

public sealed class AuthenticatedOfferingUsageGateway
    : IAuthenticatedOfferingUsageGateway,
        IPlatformAccountGateway,
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

    public Task<PlatformAccountReceipt> ReserveAccountAsync(
        PlatformAccountReserveRequest request,
        CancellationToken ct
    )
    {
        if (
            request.AccountClass
            is not (
                SpendAccountClass.Acquisition
                or SpendAccountClass.Simulation
                or SpendAccountClass.PlatformFloor
            )
        )
            throw new ArgumentOutOfRangeException(
                nameof(request),
                "Relationship-scoped account classes reserve through the offering usage route."
            );
        var body = new SortedDictionary<string, object?>(StringComparer.Ordinal)
        {
            ["accountClass"] = request.AccountClass.ToStorage(),
            ["campaignRef"] = request.CampaignRef,
            ["componentId"] = request.ComponentId,
            ["environment"] = request.Environment,
            ["invocationId"] = request.InvocationId,
            ["leadRef"] = request.LeadRef,
            ["maximumPaise"] = request.MaximumPaise,
            ["ownerEvidenceId"] = request.OwnerEvidenceId,
            ["purpose"] = request.Purpose,
        };
        foreach (
            var absent in body.Where(item => item.Value is null).Select(item => item.Key).ToList()
        )
            body.Remove(absent);
        return PostWalletAsync<PlatformAccountReceipt>(
            "/internal/v1/wallet/accounts/reserve",
            "wbeReserveWalletAccount",
            request.TenantId,
            string.Empty,
            request.ActorId,
            request.IdempotencyKey,
            request.InvocationId,
            "PLATFORM_ACCOUNT_RESERVE",
            request.ComponentId,
            body,
            ct
        );
    }

    public Task<SetupGrantReceipt> OpenSetupGrantAsync(
        Guid tenantId,
        Guid actorId,
        Guid relationshipId,
        string agentType,
        string agentVersion,
        Guid idempotencyKey,
        CancellationToken ct
    )
    {
        var body = new SortedDictionary<string, object?>(StringComparer.Ordinal)
        {
            ["agentType"] = agentType,
            ["agentVersion"] = agentVersion,
        };
        return PostWalletAsync<SetupGrantReceipt>(
            "/internal/v1/relationships/{relationshipId}/setup-grant",
            "wbeOpenSetupGrant",
            tenantId,
            relationshipId.ToString("D"),
            actorId,
            idempotencyKey,
            idempotencyKey,
            "SETUP_GRANT_OPEN",
            agentType,
            body,
            ct
        );
    }

    public Task<SetupGrantDrawReceipt> ReserveSetupGrantAsync(
        Guid tenantId,
        Guid actorId,
        Guid relationshipId,
        string agentType,
        string agentVersion,
        string componentId,
        long maximumPaise,
        Guid invocationId,
        Guid ownerEvidenceId,
        Guid idempotencyKey,
        CancellationToken ct
    )
    {
        var body = new SortedDictionary<string, object?>(StringComparer.Ordinal)
        {
            ["agentType"] = agentType,
            ["agentVersion"] = agentVersion,
            ["componentId"] = componentId,
            ["invocationId"] = invocationId,
            ["maximumPaise"] = maximumPaise,
            ["ownerEvidenceId"] = ownerEvidenceId,
        };
        return PostWalletAsync<SetupGrantDrawReceipt>(
            "/internal/v1/relationships/{relationshipId}/setup-grant/reserve",
            "wbeReserveSetupGrant",
            tenantId,
            relationshipId.ToString("D"),
            actorId,
            idempotencyKey,
            invocationId,
            "SETUP_GRANT_RESERVE",
            componentId,
            body,
            ct
        );
    }

    public Task<WalletReservationOutcome> SettleAccountAsync(
        Guid tenantId,
        Guid actorId,
        Guid reservationId,
        long actualPaise,
        Guid evidenceId,
        Guid idempotencyKey,
        CancellationToken ct
    )
    {
        var body = new SortedDictionary<string, object?>(StringComparer.Ordinal)
        {
            ["actualPaise"] = actualPaise,
            ["evidenceId"] = evidenceId,
            ["reservationId"] = reservationId,
        };
        return PostWalletAsync<WalletReservationOutcome>(
            "/internal/v1/wallet/reservations/settle",
            "wbeSettleWalletReservation",
            tenantId,
            string.Empty,
            actorId,
            idempotencyKey,
            evidenceId,
            "WALLET_RESERVATION_SETTLE",
            reservationId.ToString("D"),
            body,
            ct
        );
    }

    public Task<WalletReservationOutcome> ReleaseAccountAsync(
        Guid tenantId,
        Guid actorId,
        Guid reservationId,
        Guid nonDispatchEvidenceId,
        Guid idempotencyKey,
        CancellationToken ct
    )
    {
        var body = new SortedDictionary<string, object?>(StringComparer.Ordinal)
        {
            ["nonDispatchEvidenceId"] = nonDispatchEvidenceId,
            ["reservationId"] = reservationId,
        };
        return PostWalletAsync<WalletReservationOutcome>(
            "/internal/v1/wallet/reservations/release",
            "wbeReleaseWalletReservation",
            tenantId,
            string.Empty,
            actorId,
            idempotencyKey,
            nonDispatchEvidenceId,
            "WALLET_RESERVATION_RELEASE",
            reservationId.ToString("D"),
            body,
            ct
        );
    }

    private async Task<T> PostWalletAsync<T>(
        string route,
        string operation,
        Guid tenantId,
        string relationshipId,
        Guid actorId,
        Guid idempotencyKey,
        Guid correlationId,
        string purpose,
        string subject,
        SortedDictionary<string, object?> body,
        CancellationToken ct
    )
    {
        var bytes = JsonSerializer.SerializeToUtf8Bytes(
            body,
            new JsonSerializerOptions
            {
                DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
            }
        );
        var digest = Convert.ToHexStringLower(SHA256.HashData(bytes));
        var correlation = correlationId.ToString("D");
        var context = new DelegatedRequestContext(
            actorId.ToString("D"),
            "PROFESSIONAL",
            tenantId.ToString("D"),
            relationshipId,
            purpose,
            subject,
            correlation,
            idempotencyKey.ToString("D"),
            new Dictionary<string, string>(),
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
            route.Replace("{relationshipId}", relationshipId)
        )
        {
            Content = new ByteArrayContent(bytes),
        };
        request.Content.Headers.ContentType = new("application/json");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", envelope);
        request.Headers.Add("X-Correlation-ID", correlation);
        request.Headers.Add("Idempotency-Key", idempotencyKey.ToString("D"));
        try
        {
            using var response = await _client.SendAsync(request, ct);
            if (
                response.StatusCode is HttpStatusCode.Conflict or HttpStatusCode.UnprocessableEntity
            )
                throw await ReadRefusalAsync(response, ct);
            if (!response.IsSuccessStatusCode)
                throw new OfferingUsageOwnerUnavailableException(
                    $"WBE wallet owner returned {(int)response.StatusCode}."
                );
            return await response.Content.ReadFromJsonAsync<T>(ct)
                ?? throw new OfferingUsageOwnerUnavailableException(
                    "WBE wallet owner returned no receipt."
                );
        }
        catch (Exception exception)
            when (exception is HttpRequestException or TaskCanceledException or JsonException)
        {
            throw new OfferingUsageOwnerUnavailableException(
                "WBE wallet outcome is unresolved.",
                exception
            );
        }
    }

    private static async Task<PlatformAccountRefusedException> ReadRefusalAsync(
        HttpResponseMessage response,
        CancellationToken ct
    )
    {
        try
        {
            await using var stream = await response.Content.ReadAsStreamAsync(ct);
            using var document = await JsonDocument.ParseAsync(stream, cancellationToken: ct);
            if (document.RootElement.TryGetProperty("detail", out var detail))
            {
                if (detail.ValueKind == JsonValueKind.String && detail.GetString() is { } text)
                    return new PlatformAccountRefusedException(text, null);
                if (
                    detail.ValueKind == JsonValueKind.Object
                    && detail.TryGetProperty("code", out var code)
                    && code.ValueKind == JsonValueKind.String
                    && code.GetString() is { } value
                )
                {
                    var level =
                        detail.TryGetProperty("level", out var node)
                        && node.ValueKind == JsonValueKind.String
                            ? node.GetString()
                            : null;
                    return new PlatformAccountRefusedException(value, level);
                }
            }
        }
        catch (JsonException) { }
        return new PlatformAccountRefusedException("WALLET_REFUSED", null);
    }

    public void Dispose() => _client.Dispose();

    private sealed class WbeOfferingNotFoundException : Exception;
}

public sealed class UnconfiguredOfferingUsageGateway
    : IAuthenticatedOfferingUsageGateway,
        IPlatformAccountGateway
{
    private static OfferingUsageOwnerUnavailableException Unavailable() =>
        new("Authenticated WBE offering owner is not configured.");

    public Task<PlatformAccountReceipt> ReserveAccountAsync(
        PlatformAccountReserveRequest request,
        CancellationToken ct
    ) => Task.FromException<PlatformAccountReceipt>(Unavailable());

    public Task<SetupGrantReceipt> OpenSetupGrantAsync(
        Guid tenantId,
        Guid actorId,
        Guid relationshipId,
        string agentType,
        string agentVersion,
        Guid idempotencyKey,
        CancellationToken ct
    ) => Task.FromException<SetupGrantReceipt>(Unavailable());

    public Task<SetupGrantDrawReceipt> ReserveSetupGrantAsync(
        Guid tenantId,
        Guid actorId,
        Guid relationshipId,
        string agentType,
        string agentVersion,
        string componentId,
        long maximumPaise,
        Guid invocationId,
        Guid ownerEvidenceId,
        Guid idempotencyKey,
        CancellationToken ct
    ) => Task.FromException<SetupGrantDrawReceipt>(Unavailable());

    public Task<WalletReservationOutcome> SettleAccountAsync(
        Guid tenantId,
        Guid actorId,
        Guid reservationId,
        long actualPaise,
        Guid evidenceId,
        Guid idempotencyKey,
        CancellationToken ct
    ) => Task.FromException<WalletReservationOutcome>(Unavailable());

    public Task<WalletReservationOutcome> ReleaseAccountAsync(
        Guid tenantId,
        Guid actorId,
        Guid reservationId,
        Guid nonDispatchEvidenceId,
        Guid idempotencyKey,
        CancellationToken ct
    ) => Task.FromException<WalletReservationOutcome>(Unavailable());

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
