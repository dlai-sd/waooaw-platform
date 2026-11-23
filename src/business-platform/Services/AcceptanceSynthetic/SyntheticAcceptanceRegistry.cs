// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §5 and adr/ADR-055-synthetic-acceptance-tenants-and-evidence.md decision 4
// Constitutional basis: C-059 (Implementation Traceability)

using System.Diagnostics.Metrics;
using System.Security.Cryptography;
using System.Text;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Caching.Memory;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services.AcceptanceSynthetic;

public enum SyntheticSubjectRegistration
{
    Created,
    AlreadyRegistered,
    RunConflict,
    LimitReached,
}

public enum SandboxRecipientRegistration
{
    Created,
    AlreadyRegistered,
    LimitReached,
}

public sealed record SyntheticRunDeactivation(int Subjects, int Recipients);

public static class SyntheticAcceptanceTelemetry
{
    public const string MeterName = "Waooaw.BusinessPlatform.AcceptanceSynthetic";
    public const string SuppressedMetric = "acceptance_synthetic_delivery_suppressed";

    private static readonly Meter Meter = new(MeterName);
    private static readonly Counter<long> Suppressed = Meter.CreateCounter<long>(SuppressedMetric);

    public static void DeliverySuppressed() => Suppressed.Add(1);
}

public static class SyntheticRecipient
{
    /// <summary>One-way digest of a recipient's digits, so the registry never stores a phone number.</summary>
    public static string Digest(string recipient) =>
        Convert.ToHexStringLower(
            SHA256.HashData(
                Encoding.UTF8.GetBytes(
                    "waooaw.synthetic.sandbox-recipient.v1:"
                        + new string(recipient.Where(char.IsAsciiDigit).ToArray())
                )
            )
        );
}

/// <summary>
/// Server-side registry of synthetic acceptance subjects, keyed by Keycloak (iss, sub) and a run identifier
/// (ADR-055 decision 4). Registrations are written only by the acceptance-provisioner route. A registration is
/// never deleted: it is deactivated, and the tenant label it produced stays so evidence remains attributable.
/// </summary>
public interface ISyntheticAcceptanceRegistry
{
    Task<SyntheticSubjectRegistration> RegisterSubjectAsync(
        string issuer,
        string subject,
        string runId,
        string registeredBy,
        CancellationToken ct
    );

    Task<SandboxRecipientRegistration> RegisterSandboxRecipientAsync(
        string runId,
        string recipient,
        string registeredBy,
        CancellationToken ct
    );

    Task<SyntheticRunDeactivation> DeactivateRunAsync(string runId, CancellationToken ct);

    Task<bool> IsSyntheticActorAsync(string issuer, string subject, CancellationToken ct);

    /// <summary>The run a tenant belongs to when it was labelled synthetic at creation; null for every real customer.</summary>
    Task<string?> FindTenantRunAsync(Guid tenantId, CancellationToken ct);

    Task<bool> IsSandboxRecipientAsync(string runId, string recipientDigest, CancellationToken ct);

    Task RecordSuppressionAsync(
        Guid tenantId,
        string runId,
        Guid outboxId,
        int attemptNumber,
        string recipientDigest,
        CancellationToken ct
    );
}

public sealed class PostgresSyntheticAcceptanceRegistry(
    IDbContextFactory<ConversationStoreDbContext> factory,
    IMemoryCache cache,
    TimeProvider clock
) : ISyntheticAcceptanceRegistry
{
    public const int MaximumActiveSubjects = 20;
    public const int MaximumRecipientsPerRun = 4;
    public static readonly TimeSpan RegistrationLifetime = TimeSpan.FromHours(24);
    private const int RegistryLockKey = 1_590_001;
    private static readonly TimeSpan LookupCache = TimeSpan.FromSeconds(15);

    public async Task<SyntheticSubjectRegistration> RegisterSubjectAsync(
        string issuer,
        string subject,
        string runId,
        string registeredBy,
        CancellationToken ct
    )
    {
        var now = clock.GetUtcNow();
        await using var db = await factory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_catalog.pg_advisory_xact_lock({RegistryLockKey})",
            ct
        );
        var existing = await db
            .Database.SqlQuery<string>(
                $"""
                SELECT CASE WHEN deactivated_at IS NULL THEN run_id ELSE '' END AS "Value"
                FROM business.synthetic_subjects WHERE issuer = {issuer} AND subject = {subject}
                """
            )
            .SingleOrDefaultAsync(ct);
        if (existing is not null)
            return existing == runId
                ? SyntheticSubjectRegistration.AlreadyRegistered
                : SyntheticSubjectRegistration.RunConflict;
        var active = await db
            .Database.SqlQuery<int>(
                $"""
                SELECT count(*)::int AS "Value" FROM business.synthetic_subjects
                WHERE deactivated_at IS NULL AND expires_at > {now}
                """
            )
            .SingleAsync(ct);
        if (active >= MaximumActiveSubjects)
            return SyntheticSubjectRegistration.LimitReached;
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.synthetic_subjects
                (registration_id, issuer, subject, run_id, registered_by, registered_at, expires_at)
            VALUES ({Guid.NewGuid()}, {issuer}, {subject}, {runId}, {registeredBy}, {now},
                    {now.Add(RegistrationLifetime)})
            """,
            ct
        );
        await transaction.CommitAsync(ct);
        return SyntheticSubjectRegistration.Created;
    }

    public async Task<SandboxRecipientRegistration> RegisterSandboxRecipientAsync(
        string runId,
        string recipient,
        string registeredBy,
        CancellationToken ct
    )
    {
        var now = clock.GetUtcNow();
        var digest = SyntheticRecipient.Digest(recipient);
        await using var db = await factory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_catalog.pg_advisory_xact_lock({RegistryLockKey})",
            ct
        );
        var known = await db
            .Database.SqlQuery<bool>(
                $"""
                SELECT EXISTS (SELECT 1 FROM business.synthetic_sandbox_recipients
                    WHERE run_id = {runId} AND recipient_digest = {digest} AND deactivated_at IS NULL) AS "Value"
                """
            )
            .SingleAsync(ct);
        if (known)
            return SandboxRecipientRegistration.AlreadyRegistered;
        var registered = await db
            .Database.SqlQuery<int>(
                $"""
                SELECT count(*)::int AS "Value" FROM business.synthetic_sandbox_recipients
                WHERE run_id = {runId} AND deactivated_at IS NULL
                """
            )
            .SingleAsync(ct);
        if (registered >= MaximumRecipientsPerRun)
            return SandboxRecipientRegistration.LimitReached;
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.synthetic_sandbox_recipients
                (recipient_id, run_id, recipient_digest, registered_by, registered_at, expires_at)
            VALUES ({Guid.NewGuid()}, {runId}, {digest}, {registeredBy}, {now}, {now.Add(
                RegistrationLifetime
            )})
            ON CONFLICT (run_id, recipient_digest) DO UPDATE SET deactivated_at = NULL,
                expires_at = EXCLUDED.expires_at
            """,
            ct
        );
        await transaction.CommitAsync(ct);
        return SandboxRecipientRegistration.Created;
    }

    public async Task<SyntheticRunDeactivation> DeactivateRunAsync(
        string runId,
        CancellationToken ct
    )
    {
        var now = clock.GetUtcNow();
        await using var db = await factory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        var subjects = await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.synthetic_subjects SET deactivated_at = {now}
            WHERE run_id = {runId} AND deactivated_at IS NULL
            """,
            ct
        );
        var recipients = await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.synthetic_sandbox_recipients SET deactivated_at = {now}
            WHERE run_id = {runId} AND deactivated_at IS NULL
            """,
            ct
        );
        await transaction.CommitAsync(ct);
        return new SyntheticRunDeactivation(subjects, recipients);
    }

    public Task<bool> IsSyntheticActorAsync(string issuer, string subject, CancellationToken ct) =>
        CachedAsync(
            $"synthetic-actor:{issuer}:{subject}",
            async () =>
            {
                await using var db = await factory.CreateDbContextAsync(ct);
                return await db
                    .Database.SqlQuery<bool>(
                        $"""
                        SELECT EXISTS (SELECT 1 FROM business.synthetic_subjects
                            WHERE issuer = {issuer} AND subject = {subject}) AS "Value"
                        """
                    )
                    .SingleAsync(ct);
            }
        );

    public Task<string?> FindTenantRunAsync(Guid tenantId, CancellationToken ct) =>
        CachedAsync(
            $"synthetic-tenant:{tenantId:N}",
            async () =>
            {
                await using var db = await factory.CreateDbContextAsync(ct);
                return await db
                    .Database.SqlQuery<string>(
                        $"""
                        SELECT run_id AS "Value" FROM business.synthetic_tenants
                        WHERE tenant_id = {tenantId}
                        """
                    )
                    .SingleOrDefaultAsync(ct);
            }
        );

    public async Task<bool> IsSandboxRecipientAsync(
        string runId,
        string recipientDigest,
        CancellationToken ct
    )
    {
        var now = clock.GetUtcNow();
        await using var db = await factory.CreateDbContextAsync(ct);
        return await db
            .Database.SqlQuery<bool>(
                $"""
                SELECT EXISTS (SELECT 1 FROM business.synthetic_sandbox_recipients
                    WHERE run_id = {runId} AND recipient_digest = {recipientDigest}
                      AND deactivated_at IS NULL AND expires_at > {now}) AS "Value"
                """
            )
            .SingleAsync(ct);
    }

    public async Task RecordSuppressionAsync(
        Guid tenantId,
        string runId,
        Guid outboxId,
        int attemptNumber,
        string recipientDigest,
        CancellationToken ct
    )
    {
        var now = clock.GetUtcNow();
        await using var db = await factory.CreateDbContextAsync(ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.synthetic_delivery_suppressions
                (suppression_id, tenant_id, run_id, outbox_id, attempt_number, recipient_digest, reason, suppressed_at)
            VALUES ({Guid.NewGuid()}, {tenantId}, {runId}, {outboxId}, {attemptNumber}, {recipientDigest},
                    'RECIPIENT_NOT_SANDBOX', {now})
            ON CONFLICT (outbox_id, attempt_number) DO NOTHING
            """,
            ct
        );
    }

    private async Task<T> CachedAsync<T>(string key, Func<Task<T>> read)
    {
        if (cache.TryGetValue(key, out T? cached))
            return cached!;
        var value = await read();
        cache.Set(key, value, LookupCache);
        return value;
    }
}
