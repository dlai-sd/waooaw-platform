// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-02, C6-03
// Constitutional basis: C-023, C-059, C-063, ADR-051

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services.Workbench;

public enum WorkbenchLedgerClaimKind
{
    Claimed,
    Replay,
    Conflict,
    InProgress,
}

public sealed record WorkbenchLedgerClaim(WorkbenchLedgerClaimKind Kind, string? ResultJson = null);

/// <summary>The durable store of workbench command receipts; every replica answers a retry from the same rows.</summary>
public interface IWorkbenchLedgerStore
{
    /// <summary>Claims the key for this request, or reports the earlier receipt, a conflicting request or a run in flight.</summary>
    Task<WorkbenchLedgerClaim> ClaimAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        string digest,
        DateTimeOffset now,
        DateTimeOffset leaseUntil,
        CancellationToken ct
    );

    Task CompleteAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        string resultJson,
        DateTimeOffset now,
        CancellationToken ct
    );

    /// <summary>Releases a claim whose command failed so that a retry runs it again.</summary>
    Task AbandonAsync(WorkbenchContext context, Guid idempotencyKey, CancellationToken ct);
}

/// <summary>
/// Keeps the receipt of each workbench command by caller and idempotency key so a retry returns the same answer and a
/// reused key with a different request is refused. Receipts are durable and shared by every replica; a command that is
/// still running on another replica is awaited briefly and then reported as unavailable, never run twice.
/// </summary>
public sealed class WorkbenchCommandLedger(IWorkbenchLedgerStore store, TimeProvider clock)
{
    private const int InFlightAttempts = 40;
    private static readonly TimeSpan InFlightPause = TimeSpan.FromMilliseconds(250);
    private static readonly TimeSpan Lease = TimeSpan.FromMinutes(2);
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    public static string Digest(string operation, string resource, object request)
    {
        var text = $"{operation}|{resource}|{JsonSerializer.Serialize(request, Json)}";
        return Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(text)));
    }

    public async Task<(T Result, bool Replayed)> RunAsync<T>(
        WorkbenchContext context,
        Guid idempotencyKey,
        string digest,
        Func<Task<T>> execute,
        CancellationToken ct
    )
        where T : class
    {
        for (var attempt = 0; ; attempt++)
        {
            var now = clock.GetUtcNow();
            var claim = await store.ClaimAsync(
                context,
                idempotencyKey,
                digest,
                now,
                now + Lease,
                ct
            );
            switch (claim.Kind)
            {
                case WorkbenchLedgerClaimKind.Conflict:
                    throw new WorkbenchException(409, WorkbenchProblemCodes.IdempotencyConflict);
                case WorkbenchLedgerClaimKind.Replay:
                    var stored =
                        JsonSerializer.Deserialize<T>(claim.ResultJson ?? "null", Json)
                        ?? throw new WorkbenchException(503, WorkbenchProblemCodes.Unavailable);
                    return (stored, true);
                case WorkbenchLedgerClaimKind.InProgress:
                    if (attempt >= InFlightAttempts)
                        throw new WorkbenchException(503, WorkbenchProblemCodes.Unavailable);
                    await Task.Delay(InFlightPause, ct);
                    continue;
            }

            T result;
            try
            {
                result = await execute();
            }
            catch
            {
                await store.AbandonAsync(context, idempotencyKey, CancellationToken.None);
                throw;
            }
            await store.CompleteAsync(
                context,
                idempotencyKey,
                JsonSerializer.Serialize(result, Json),
                clock.GetUtcNow(),
                CancellationToken.None
            );
            return (result, false);
        }
    }
}

/// <summary>
/// Issues short-lived single-use handoff references that move a conversation to the web workbench. A handoff names a
/// destination only; it never carries authority, so the web still requires the customer's own signed-in session.
/// </summary>
public sealed record WorkbenchHandoffRecord(
    Guid HandoffRef,
    string TokenHash,
    Guid TenantId,
    Guid RelationshipId,
    Guid ParticipantId,
    string Purpose,
    string? ContextRef,
    DateTimeOffset CreatedAt,
    DateTimeOffset ExpiresAt
);

/// <summary>What a redeemed handoff names: the purpose it was issued for and the optional item it points to.</summary>
public sealed record WorkbenchHandoffRedemption(string Purpose, string? ContextRef);

/// <summary>The durable store of handoffs, keyed by the hash of the token; the token itself is never stored.</summary>
public interface IWorkbenchHandoffStore
{
    Task InsertAsync(WorkbenchHandoffRecord record, CancellationToken ct);

    /// <summary>Atomically marks the handoff used; null when it is unknown, expired, used or issued to someone else.</summary>
    Task<WorkbenchHandoffRedemption?> ConsumeAsync(
        string tokenHash,
        Guid tenantId,
        Guid relationshipId,
        Guid participantId,
        DateTimeOffset now,
        CancellationToken ct
    );
}

/// <summary>
/// Issues short-lived single-use handoff references that move a conversation to the web workbench. A handoff names a
/// destination only; it never carries authority, so the web still requires the customer's own signed-in session.
/// </summary>
public sealed class WorkbenchHandoffService(
    IWorkbenchHandoffStore store,
    IOptions<WorkbenchOptions> options,
    TimeProvider clock
)
{
    private static readonly HashSet<string> Purposes = new(StringComparer.Ordinal)
    {
        "WEB_WORKBENCH",
        "APPROVAL",
        "PAYMENT",
        "EVIDENCE",
    };

    public static bool IsPurpose(string purpose) => Purposes.Contains(purpose);

    public async Task<WorkbenchHandoff> CreateAsync(
        WorkbenchContext context,
        string purpose,
        string? contextRef,
        CancellationToken ct
    )
    {
        var ttl = TimeSpan.FromSeconds(Math.Clamp(options.Value.HandoffTtlSeconds, 60, 3600));
        var now = clock.GetUtcNow();
        var token = "h" + Base64Url(RandomNumberGenerator.GetBytes(32));
        var record = new WorkbenchHandoffRecord(
            Guid.NewGuid(),
            Hash(token),
            context.TenantId,
            context.RelationshipId,
            context.ParticipantId,
            purpose,
            contextRef,
            now,
            now + ttl
        );
        await store.InsertAsync(record, ct);
        return new WorkbenchHandoff(
            WorkbenchProjectionService.SchemaVersion,
            record.HandoffRef,
            token,
            record.ExpiresAt,
            true
        );
    }

    /// <summary>Redeems a handoff once for the participant it was issued to; any other caller or a second use fails.</summary>
    public Task<WorkbenchHandoffRedemption?> TryConsumeAsync(
        string token,
        Guid tenantId,
        Guid relationshipId,
        Guid participantId,
        CancellationToken ct
    ) =>
        string.IsNullOrWhiteSpace(token) || token.Length > 128
            ? Task.FromResult<WorkbenchHandoffRedemption?>(null)
            : store.ConsumeAsync(
                Hash(token),
                tenantId,
                relationshipId,
                participantId,
                clock.GetUtcNow(),
                ct
            );

    /// <summary>The absolute web address of the handoff, or null when no web base address is configured.</summary>
    public string? UrlFor(WorkbenchHandoff handoff, Guid relationshipId)
    {
        var baseUrl = options.Value.HandoffBaseUrl.Trim().TrimEnd('/');
        if (
            baseUrl.Length == 0
            || !Uri.TryCreate(baseUrl, UriKind.Absolute, out var uri)
            || uri.Scheme is not ("https" or "http")
        )
            return null;
        return $"{baseUrl}/relationships/{relationshipId:D}?handoff={Uri.EscapeDataString(handoff.DestinationRef)}";
    }

    private static string Hash(string token) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(token)));

    private static string Base64Url(byte[] bytes) =>
        Convert.ToBase64String(bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_');
}
