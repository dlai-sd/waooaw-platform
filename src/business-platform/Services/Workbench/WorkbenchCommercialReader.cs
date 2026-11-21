// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01, C6-02
// Constitutional basis: C-023, C-059, C-063, ADR-051

using System.Net;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services.Workbench;

/// <summary>The authenticated caller of one workbench request; the audience is derived server-side from the role.</summary>
public sealed record WorkbenchContext(
    Guid TenantId,
    Guid RelationshipId,
    string ActorSubject,
    Guid ParticipantId,
    RelationshipParticipantRole Role,
    string Audience,
    string CorrelationId
)
{
    public string EffectiveRole => RelationshipRoleCodec.ToDatabase(Role);
}

/// <summary>Wallet facts the billing owner reports; components stay empty when the owner does not report them.</summary>
public sealed record WorkbenchCommercialSnapshot(
    bool Available,
    string ProjectionVersion,
    DateTimeOffset? PeriodEnd,
    IReadOnlyList<WorkbenchComponentBalance> Components,
    bool TopUpAvailable,
    string? Limitation
)
{
    public static WorkbenchCommercialSnapshot Unavailable(string limitation) =>
        new(false, string.Empty, null, [], false, limitation);
}

public sealed record WorkbenchCommercialCommandResult(
    string Status,
    Guid CommandId,
    bool Replayed,
    string? ProblemCode,
    JsonElement? Outcome
);

public interface IWorkbenchCommercialReader
{
    Task<WorkbenchCommercialSnapshot> GetWalletAsync(
        WorkbenchContext context,
        CancellationToken ct
    );

    /// <summary>Submits one commercial command to the billing owner; returns null when the owner cannot be reached.</summary>
    Task<WorkbenchCommercialCommandResult?> SubmitAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        string expectedProjectionVersion,
        JsonObject payload,
        CancellationToken ct
    );
}

public sealed class UnconfiguredWorkbenchCommercialReader : IWorkbenchCommercialReader
{
    public const string Limitation = "Billing is not reachable, so wallet figures are not shown.";

    public Task<WorkbenchCommercialSnapshot> GetWalletAsync(
        WorkbenchContext context,
        CancellationToken ct
    ) => Task.FromResult(WorkbenchCommercialSnapshot.Unavailable(Limitation));

    public Task<WorkbenchCommercialCommandResult?> SubmitAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        string expectedProjectionVersion,
        JsonObject payload,
        CancellationToken ct
    ) => Task.FromResult<WorkbenchCommercialCommandResult?>(null);
}

/// <summary>Reads and commands the billing owner through the private workload-identity routes of the commercial projection.</summary>
public sealed class AuthenticatedWorkbenchCommercialReader : IWorkbenchCommercialReader, IDisposable
{
    public const string FiguresMayBeStale = "Billing says these wallet figures may be out of date.";
    public const string BillingUnavailable =
        "Billing did not answer, so wallet figures are not shown.";

    private const string EmptyDigest =
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
    private const string ProjectionRoute =
        "/internal/v1/relationships/{relationshipId}/commercial-projection";
    private const string CommandRoute =
        "/internal/v1/relationships/{relationshipId}/commercial-commands";
    private const string CommandOutcomeRoute =
        "/internal/v1/relationships/{relationshipId}/commercial-commands/{commandId}";

    private readonly WorkloadIdentityClient _identity;
    private readonly HttpClient _client;

    public AuthenticatedWorkbenchCommercialReader(WorkloadIdentityClient identity, Uri endpoint)
    {
        _identity = identity;
        _client = identity.CreateClient(endpoint, "billing-engine");
    }

    public async Task<WorkbenchCommercialSnapshot> GetWalletAsync(
        WorkbenchContext context,
        CancellationToken ct
    )
    {
        var envelope = Sign(
            context,
            "GET",
            ProjectionRoute,
            "getRelationshipCommercialProjection",
            null,
            EmptyDigest,
            new Dictionary<string, string>()
        );
        using var request = new HttpRequestMessage(
            HttpMethod.Get,
            ProjectionRoute.Replace("{relationshipId}", context.RelationshipId.ToString("D"))
        );
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", envelope);
        request.Headers.Add("X-Correlation-ID", context.CorrelationId);
        try
        {
            using var response = await _client.SendAsync(request, ct);
            if (!response.IsSuccessStatusCode)
                return WorkbenchCommercialSnapshot.Unavailable(BillingUnavailable);
            using var document = await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(ct),
                cancellationToken: ct
            );
            return Parse(document.RootElement, context.RelationshipId);
        }
        catch (Exception exception)
            when (exception
                    is HttpRequestException
                        or TaskCanceledException
                        or JsonException
                        or InvalidOperationException
                        or FormatException
            )
        {
            return WorkbenchCommercialSnapshot.Unavailable(BillingUnavailable);
        }
    }

    public async Task<WorkbenchCommercialCommandResult?> SubmitAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        string expectedProjectionVersion,
        JsonObject payload,
        CancellationToken ct
    )
    {
        var body = new JsonObject
        {
            ["schemaVersion"] = "1.0",
            ["expectedProjectionVersion"] = expectedProjectionVersion,
            ["payload"] = payload,
        };
        var bytes = Encoding.UTF8.GetBytes(body.ToJsonString());
        var digest = Convert.ToHexStringLower(SHA256.HashData(bytes));
        var envelope = Sign(
            context,
            "POST",
            CommandRoute,
            "submitRelationshipCommercialCommand",
            idempotencyKey.ToString("D"),
            digest,
            new Dictionary<string, string> { ["projection"] = expectedProjectionVersion }
        );
        using var request = new HttpRequestMessage(
            HttpMethod.Post,
            CommandRoute.Replace("{relationshipId}", context.RelationshipId.ToString("D"))
        )
        {
            Content = new ByteArrayContent(bytes),
        };
        request.Content.Headers.ContentType = new("application/json");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", envelope);
        request.Headers.Add("X-Correlation-ID", context.CorrelationId);
        request.Headers.Add("Idempotency-Key", idempotencyKey.ToString("D"));
        try
        {
            using var response = await _client.SendAsync(request, ct);
            using var document = await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(ct),
                cancellationToken: ct
            );
            var root = document.RootElement;
            if (response.StatusCode is HttpStatusCode.OK or HttpStatusCode.Accepted)
            {
                var commandId =
                    root.TryGetProperty("commandId", out var id) && id.TryGetGuid(out var parsed)
                        ? parsed
                        : Guid.Empty;
                var status =
                    root.TryGetProperty("status", out var state)
                    && state.ValueKind == JsonValueKind.String
                        ? state.GetString()!
                        : "UNKNOWN";
                var replayed =
                    root.TryGetProperty("replayed", out var replay)
                    && replay.ValueKind == JsonValueKind.True;
                var outcome =
                    commandId == Guid.Empty ? null : await GetOutcomeAsync(context, commandId, ct);
                if (
                    outcome is { } resolved
                    && resolved.TryGetProperty("status", out var final)
                    && final.ValueKind == JsonValueKind.String
                )
                    status = final.GetString()!;
                return new WorkbenchCommercialCommandResult(
                    status,
                    commandId,
                    replayed,
                    null,
                    outcome
                );
            }
            var code = ProblemCode(root);
            return new WorkbenchCommercialCommandResult(
                response.StatusCode == HttpStatusCode.Conflict ? "CONFLICT" : "REJECTED",
                Guid.Empty,
                false,
                code ?? $"HTTP_{(int)response.StatusCode}",
                null
            );
        }
        catch (Exception exception)
            when (exception
                    is HttpRequestException
                        or TaskCanceledException
                        or JsonException
                        or InvalidOperationException
            )
        {
            return null;
        }
    }

    /// <summary>The billing owner answers a submitted command with a receipt only; the settled facts (effective date, fees, blocked reason) are read from the command's outcome.</summary>
    private async Task<JsonElement?> GetOutcomeAsync(
        WorkbenchContext context,
        Guid commandId,
        CancellationToken ct
    )
    {
        var envelope = Sign(
            context,
            "GET",
            CommandOutcomeRoute,
            "getRelationshipCommercialCommand",
            null,
            EmptyDigest,
            new Dictionary<string, string>()
        );
        using var request = new HttpRequestMessage(
            HttpMethod.Get,
            CommandOutcomeRoute
                .Replace("{relationshipId}", context.RelationshipId.ToString("D"))
                .Replace("{commandId}", commandId.ToString("D"))
        );
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", envelope);
        request.Headers.Add("X-Correlation-ID", context.CorrelationId);
        try
        {
            using var response = await _client.SendAsync(request, ct);
            if (!response.IsSuccessStatusCode)
                return null;
            using var document = await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(ct),
                cancellationToken: ct
            );
            return
                document.RootElement.ValueKind == JsonValueKind.Object
                && document.RootElement.TryGetProperty("commandId", out var id)
                && id.TryGetGuid(out var echoed)
                && echoed == commandId
                ? document.RootElement.Clone()
                : null;
        }
        catch (Exception exception)
            when (exception is HttpRequestException or TaskCanceledException or JsonException)
        {
            return null;
        }
    }

    /// <summary>The billing owner reports a refusal as <c>{"detail": "CODE"}</c> or <c>{"detail": {"code": "CODE"}}</c>.</summary>
    internal static string? ProblemCode(JsonElement root)
    {
        if (root.ValueKind != JsonValueKind.Object)
            return null;
        if (root.TryGetProperty("detail", out var detail))
        {
            if (detail.ValueKind == JsonValueKind.String)
                return detail.GetString();
            if (
                detail.ValueKind == JsonValueKind.Object
                && detail.TryGetProperty("code", out var nested)
                && nested.ValueKind == JsonValueKind.String
            )
                return nested.GetString();
        }
        return root.TryGetProperty("code", out var code) && code.ValueKind == JsonValueKind.String
            ? code.GetString()
            : null;
    }

    private string Sign(
        WorkbenchContext context,
        string method,
        string route,
        string operation,
        string? idempotencyKey,
        string digest,
        IReadOnlyDictionary<string, string> expectedVersions
    ) =>
        _identity.Sign(
            new DelegatedRequestContext(
                context.ActorSubject,
                context.EffectiveRole,
                context.TenantId.ToString("D"),
                context.RelationshipId.ToString("D"),
                operation,
                context.RelationshipId.ToString("D"),
                Guid.NewGuid().ToString("D"),
                idempotencyKey,
                expectedVersions,
                context.CorrelationId
            ),
            _identity.GetAudience("billing-engine"),
            method,
            route,
            operation,
            1,
            digest,
            DateTimeOffset.UtcNow
        );

    internal static WorkbenchCommercialSnapshot Parse(JsonElement root, Guid relationshipId)
    {
        if (
            root.ValueKind != JsonValueKind.Object
            || !root.TryGetProperty("schemaVersion", out var schema)
            || schema.GetString() != "1.0"
            || !root.TryGetProperty("relationshipId", out var relationship)
            || !relationship.TryGetGuid(out var parsedRelationship)
            || parsedRelationship != relationshipId
            || !root.TryGetProperty("projectionVersion", out var version)
            || version.ValueKind != JsonValueKind.String
        )
            return WorkbenchCommercialSnapshot.Unavailable(BillingUnavailable);
        var wallet =
            root.TryGetProperty("wallet", out var nested)
            && nested.ValueKind == JsonValueKind.Object
                ? nested
                : root;
        DateTimeOffset? periodEnd =
            wallet.TryGetProperty("periodEnd", out var end) && end.TryGetDateTimeOffset(out var at)
                ? at
                : null;
        var components = new List<WorkbenchComponentBalance>();
        if (
            wallet.TryGetProperty("components", out var items)
            && items.ValueKind == JsonValueKind.Array
            && periodEnd is not null
        )
            foreach (var item in items.EnumerateArray())
            {
                if (
                    item.ValueKind == JsonValueKind.Object
                    && item.TryGetProperty("componentId", out var componentId)
                    && componentId.ValueKind == JsonValueKind.String
                    && item.TryGetProperty("label", out var label)
                    && label.ValueKind == JsonValueKind.String
                    && item.TryGetProperty("remaining", out var remaining)
                    && remaining.TryGetInt32(out var remainingUnits)
                    && item.TryGetProperty("quantity", out var quantity)
                    && quantity.TryGetInt32(out var quantityUnits)
                )
                    components.Add(
                        new WorkbenchComponentBalance(
                            componentId.GetString()!,
                            label.GetString()!,
                            remainingUnits,
                            quantityUnits,
                            periodEnd.Value
                        )
                    );
            }
        var topUp =
            wallet.TryGetProperty("topUpAvailable", out var flag)
            && flag.ValueKind == JsonValueKind.True;
        var state =
            root.TryGetProperty("currencyState", out var currency)
            && currency.ValueKind == JsonValueKind.String
                ? currency.GetString()
                : null;
        return new WorkbenchCommercialSnapshot(
            true,
            version.GetString()!,
            periodEnd,
            components,
            topUp,
            state is "STALE" or "UNKNOWN" or "UNAVAILABLE" ? FiguresMayBeStale : null
        );
    }

    public void Dispose() => _client.Dispose();
}
