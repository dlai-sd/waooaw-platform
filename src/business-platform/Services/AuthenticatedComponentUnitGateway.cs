// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-08
// Constitutional basis: C-023, C-059, C-063, ADR-051

using System.Net;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

/// <summary>One owner-confirmed deliverable that consumes a unit of a package component.</summary>
public sealed record ComponentUnitCompletion(
    Guid TenantId,
    Guid RelationshipId,
    string ComponentId,
    Guid CompletionEvidenceId,
    string ActorSubject
);

public sealed record ComponentUnitReceipt(
    string ComponentId,
    int Quantity,
    int Used,
    int Remaining,
    int Released,
    bool Replayed
);

public sealed class ComponentUnitRefusedException(string code) : Exception(code)
{
    public string Code { get; } = code;
}

public sealed class ComponentUnitOwnerUnavailableException : Exception
{
    public ComponentUnitOwnerUnavailableException(string message, Exception? inner = null)
        : base(message, inner) { }
}

public interface IComponentUnitGateway
{
    Task<ComponentUnitReceipt> ConsumeAsync(
        ComponentUnitCompletion completion,
        CancellationToken ct
    );
}

/// <summary>Receives owner-confirmed completions without ever blocking the work that produced them.</summary>
public interface IComponentUnitCompletionSink
{
    void Completed(ComponentUnitCompletion completion);
}

public sealed class NoopComponentUnitCompletionSink : IComponentUnitCompletionSink
{
    public void Completed(ComponentUnitCompletion completion) { }
}

public sealed class UnconfiguredComponentUnitGateway : IComponentUnitGateway
{
    public Task<ComponentUnitReceipt> ConsumeAsync(
        ComponentUnitCompletion completion,
        CancellationToken ct
    ) =>
        throw new ComponentUnitOwnerUnavailableException(
            "The component-unit owner is not configured."
        );
}

/// <summary>
/// A completed command counts a component unit only when the Constitutional Engine step's evidence reference is
/// <c>component-unit:{componentId}:{evidenceGuid}</c>. Any other evidence counts nothing, so a unit is never
/// consumed by transport acceptance, model output or a guessed component.
/// </summary>
public static partial class ComponentUnitEvidence
{
    public const string Prefix = "component-unit:";

    [GeneratedRegex(
        @"^component-unit:(?<component>[A-Za-z0-9_.\-]{1,100}):(?<evidence>[0-9a-fA-F\-]{36})$"
    )]
    private static partial Regex Pattern();

    public static bool TryParse(string? evidenceRef, out string componentId, out Guid evidenceId)
    {
        componentId = string.Empty;
        evidenceId = Guid.Empty;
        if (string.IsNullOrWhiteSpace(evidenceRef))
            return false;
        var match = Pattern().Match(evidenceRef);
        if (
            !match.Success
            || !Guid.TryParseExact(match.Groups["evidence"].Value, "D", out var parsed)
            || parsed == Guid.Empty
        )
            return false;
        evidenceId = parsed;
        componentId = match.Groups["component"].Value;
        return true;
    }

    public static Guid IdempotencyKey(Guid relationshipId, string componentId, Guid evidenceId)
    {
        var hash = SHA256.HashData(
            System.Text.Encoding.UTF8.GetBytes(
                $"component-unit:{relationshipId:D}:{componentId}:{evidenceId:D}"
            )
        );
        return new Guid(hash.AsSpan(0, 16));
    }
}

public sealed class AuthenticatedComponentUnitGateway : IComponentUnitGateway, IDisposable
{
    public const string Route =
        "/internal/v1/relationships/{relationshipId}/component-units/consume";
    public const string Operation = "applyRelationshipComponentUnit";
    public const string Purpose = "COMPONENT_UNIT_USAGE";

    private readonly WorkloadIdentityClient _identity;
    private readonly HttpClient _client;

    public AuthenticatedComponentUnitGateway(WorkloadIdentityClient identity, Uri endpoint)
    {
        _identity = identity;
        _client = identity.CreateClient(endpoint, "billing-engine");
    }

    public async Task<ComponentUnitReceipt> ConsumeAsync(
        ComponentUnitCompletion completion,
        CancellationToken ct
    )
    {
        var key = ComponentUnitEvidence.IdempotencyKey(
            completion.RelationshipId,
            completion.ComponentId,
            completion.CompletionEvidenceId
        );
        var body = new SortedDictionary<string, object?>(StringComparer.Ordinal)
        {
            ["action"] = "CONSUME",
            ["completionEvidenceId"] = completion.CompletionEvidenceId.ToString("D"),
            ["componentId"] = completion.ComponentId,
            ["outcome"] = "COMPLETED",
            ["schemaVersion"] = "1.0",
        };
        var bytes = JsonSerializer.SerializeToUtf8Bytes(body);
        var digest = Convert.ToHexStringLower(SHA256.HashData(bytes));
        var correlation = Guid.NewGuid().ToString("D");
        var envelope = _identity.Sign(
            new DelegatedRequestContext(
                completion.ActorSubject,
                "SYSTEM",
                completion.TenantId.ToString("D"),
                completion.RelationshipId.ToString("D"),
                Purpose,
                completion.ComponentId,
                correlation,
                key.ToString("D"),
                new Dictionary<string, string>(),
                correlation
            ),
            _identity.GetAudience("billing-engine"),
            "POST",
            Route,
            Operation,
            1,
            digest,
            DateTimeOffset.UtcNow
        );
        using var request = new HttpRequestMessage(
            HttpMethod.Post,
            Route.Replace("{relationshipId}", completion.RelationshipId.ToString("D"))
        )
        {
            Content = new ByteArrayContent(bytes),
        };
        request.Content.Headers.ContentType = new("application/json");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", envelope);
        request.Headers.Add("X-Correlation-ID", correlation);
        request.Headers.Add("Idempotency-Key", key.ToString("D"));
        try
        {
            using var response = await _client.SendAsync(request, ct);
            if (
                response.StatusCode is HttpStatusCode.Conflict or HttpStatusCode.UnprocessableEntity
            )
                throw new ComponentUnitRefusedException(await ReadCodeAsync(response, ct));
            if (!response.IsSuccessStatusCode)
                throw new ComponentUnitOwnerUnavailableException(
                    $"Component-unit owner returned {(int)response.StatusCode}."
                );
            using var document = await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(ct),
                cancellationToken: ct
            );
            var root = document.RootElement;
            return new ComponentUnitReceipt(
                root.GetProperty("componentId").GetString() ?? completion.ComponentId,
                root.GetProperty("quantity").GetInt32(),
                root.GetProperty("used").GetInt32(),
                root.GetProperty("remaining").GetInt32(),
                root.GetProperty("released").GetInt32(),
                root.GetProperty("replayed").GetBoolean()
            );
        }
        catch (Exception exception)
            when (exception
                    is HttpRequestException
                        or TaskCanceledException
                        or JsonException
                        or KeyNotFoundException
                        or InvalidOperationException
            )
        {
            throw new ComponentUnitOwnerUnavailableException(
                "The component-unit outcome is unresolved.",
                exception
            );
        }
    }

    private static async Task<string> ReadCodeAsync(
        HttpResponseMessage response,
        CancellationToken ct
    )
    {
        try
        {
            using var document = await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(ct),
                cancellationToken: ct
            );
            if (
                document.RootElement.ValueKind == JsonValueKind.Object
                && document.RootElement.TryGetProperty("detail", out var detail)
                && detail.ValueKind == JsonValueKind.String
                && detail.GetString() is { Length: > 0 } code
            )
                return code;
        }
        catch (JsonException) { }
        return "COMPONENT_UNIT_REFUSED";
    }

    public void Dispose() => _client.Dispose();
}

/// <summary>One durable completion leased to a worker; <see cref="Attempt"/> counts the retries already made.</summary>
public sealed record ComponentUnitWork(
    Guid OutboxId,
    ComponentUnitCompletion Completion,
    int Attempt
);

/// <summary>
/// Durable hand-off of completions to the background drain, so the completing request never waits for billing
/// and a restart never loses a unit. The owner counts idempotently on the evidence id, so a re-delivery after an
/// unresolved outcome (or after a lease expires) is always safe.
/// </summary>
public interface IComponentUnitOutbox : IComponentUnitCompletionSink
{
    Task<IReadOnlyList<ComponentUnitWork>> ClaimAsync(
        int limit,
        TimeSpan lease,
        CancellationToken ct
    );

    Task DeliveredAsync(Guid outboxId, CancellationToken ct);

    Task RefusedAsync(Guid outboxId, string code, CancellationToken ct);

    Task RetryAsync(Guid outboxId, TimeSpan delay, string code, CancellationToken ct);

    Task UnresolvedAsync(Guid outboxId, string code, CancellationToken ct);
}

/// <summary>In-process outbox with the same semantics as the Postgres one; for unit tests only.</summary>
public sealed class InMemoryComponentUnitOutbox(TimeProvider? clock = null) : IComponentUnitOutbox
{
    private sealed class Row(ComponentUnitCompletion completion)
    {
        public Guid Id { get; } = Guid.NewGuid();
        public ComponentUnitCompletion Completion { get; } = completion;
        public string State { get; set; } = "PENDING";
        public int Attempt { get; set; }
        public DateTimeOffset NextAttemptAt { get; set; }
        public DateTimeOffset? LeaseExpiresAt { get; set; }
        public string? Code { get; set; }
    }

    private readonly TimeProvider _clock = clock ?? TimeProvider.System;
    private readonly object _sync = new();
    private readonly Dictionary<(Guid, Guid, string, Guid), Row> _rows = [];

    public void Completed(ComponentUnitCompletion completion)
    {
        lock (_sync)
        {
            var key = (
                completion.TenantId,
                completion.RelationshipId,
                completion.ComponentId,
                completion.CompletionEvidenceId
            );
            if (!_rows.ContainsKey(key))
                _rows[key] = new Row(completion) { NextAttemptAt = _clock.GetUtcNow() };
        }
    }

    public Task<IReadOnlyList<ComponentUnitWork>> ClaimAsync(
        int limit,
        TimeSpan lease,
        CancellationToken ct
    )
    {
        lock (_sync)
        {
            var now = _clock.GetUtcNow();
            var due = _rows
                .Values.Where(row =>
                    (row.State == "PENDING" && row.NextAttemptAt <= now)
                    || (row.State == "LEASED" && row.LeaseExpiresAt <= now)
                )
                .OrderBy(row => row.NextAttemptAt)
                .Take(limit)
                .ToList();
            foreach (var row in due)
            {
                row.State = "LEASED";
                row.LeaseExpiresAt = now + lease;
            }
            return Task.FromResult<IReadOnlyList<ComponentUnitWork>>(
                due.Select(row => new ComponentUnitWork(row.Id, row.Completion, row.Attempt))
                    .ToList()
            );
        }
    }

    public Task DeliveredAsync(Guid outboxId, CancellationToken ct) =>
        Mark(outboxId, "DELIVERED", null, null);

    public Task RefusedAsync(Guid outboxId, string code, CancellationToken ct) =>
        Mark(outboxId, "REFUSED", code, null);

    public Task RetryAsync(Guid outboxId, TimeSpan delay, string code, CancellationToken ct) =>
        Mark(outboxId, "RETRY", code, delay);

    public Task UnresolvedAsync(Guid outboxId, string code, CancellationToken ct) =>
        Mark(outboxId, "UNRESOLVED", code, null);

    public IReadOnlyList<(ComponentUnitCompletion Completion, string State, int Attempt)> Snapshot()
    {
        lock (_sync)
            return _rows.Values.Select(row => (row.Completion, row.State, row.Attempt)).ToList();
    }

    private Task Mark(Guid outboxId, string outcome, string? code, TimeSpan? delay)
    {
        lock (_sync)
        {
            var row = _rows.Values.SingleOrDefault(candidate => candidate.Id == outboxId);
            if (row is null || row.State != "LEASED")
                return Task.CompletedTask;
            row.LeaseExpiresAt = null;
            row.Code = code;
            if (outcome == "RETRY")
            {
                row.State = "PENDING";
                row.Attempt++;
                row.NextAttemptAt = _clock.GetUtcNow() + delay!.Value;
            }
            else
                row.State = outcome;
        }
        return Task.CompletedTask;
    }
}

public sealed class ComponentUnitCompletionWorker(
    IComponentUnitOutbox outbox,
    IComponentUnitGateway gateway,
    ILogger<ComponentUnitCompletionWorker> logger,
    TimeProvider clock,
    IReadOnlyList<TimeSpan>? retryDelays = null,
    TimeSpan? pollInterval = null
) : BackgroundService
{
    public static readonly TimeSpan[] DefaultRetryDelays =
    [
        TimeSpan.FromSeconds(2),
        TimeSpan.FromSeconds(10),
        TimeSpan.FromSeconds(60),
        TimeSpan.FromMinutes(5),
        TimeSpan.FromMinutes(15),
        TimeSpan.FromHours(1),
        TimeSpan.FromHours(6),
    ];

    private const int BatchSize = 10;
    private static readonly TimeSpan Lease = TimeSpan.FromMinutes(5);
    private static readonly TimeSpan DefaultPollInterval = TimeSpan.FromSeconds(5);

    private readonly IReadOnlyList<TimeSpan> _delays = retryDelays ?? DefaultRetryDelays;
    private readonly TimeSpan _poll = pollInterval ?? DefaultPollInterval;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                if (await DrainOnceAsync(stoppingToken) == 0)
                    await Task.Delay(_poll, clock, stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                return;
            }
        }
    }

    /// <summary>Claims one batch and delivers it; a storage failure is logged and the leased rows expire back.</summary>
    internal async Task<int> DrainOnceAsync(CancellationToken ct)
    {
        IReadOnlyList<ComponentUnitWork> batch;
        try
        {
            batch = await outbox.ClaimAsync(BatchSize, Lease, ct);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            logger.LogWarning(exception, "component_unit decision=claim_failed");
            return 0;
        }
        foreach (var work in batch)
        {
            try
            {
                await DeliverAsync(work, ct);
            }
            catch (Exception exception) when (exception is not OperationCanceledException)
            {
                // The lease expires and the row is claimed again; the owner counts idempotently.
                logger.LogWarning(
                    exception,
                    "component_unit decision=mark_failed relationship={Relationship}",
                    work.Completion.RelationshipId
                );
            }
        }
        return batch.Count;
    }

    internal async Task<bool> DeliverAsync(ComponentUnitWork work, CancellationToken ct)
    {
        var completion = work.Completion;
        try
        {
            await gateway.ConsumeAsync(completion, ct);
        }
        catch (ComponentUnitRefusedException refusal)
        {
            // A refusal is final: the owner answered (not yet released, unknown component, kind mismatch).
            logger.LogInformation(
                "component_unit decision=refused code={Code} relationship={Relationship}",
                refusal.Code,
                completion.RelationshipId
            );
            await outbox.RefusedAsync(work.OutboxId, refusal.Code, ct);
            return false;
        }
        catch (ComponentUnitOwnerUnavailableException) when (work.Attempt < _delays.Count)
        {
            await outbox.RetryAsync(work.OutboxId, _delays[work.Attempt], "OWNER_UNAVAILABLE", ct);
            return false;
        }
        catch (ComponentUnitOwnerUnavailableException)
        {
            logger.LogWarning(
                "component_unit decision=unresolved relationship={Relationship} component={Component}",
                completion.RelationshipId,
                completion.ComponentId
            );
            await outbox.UnresolvedAsync(work.OutboxId, "OWNER_UNAVAILABLE", ct);
            return false;
        }
        await outbox.DeliveredAsync(work.OutboxId, ct);
        return true;
    }
}
